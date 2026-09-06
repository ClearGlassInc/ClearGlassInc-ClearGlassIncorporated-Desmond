"""Fulfillment orchestration — paid order to tracked parcel, with the gate intact.

The property under test throughout: money arriving never implies a parcel
leaving. An order that cannot ship is recorded as unfulfillable and stays
visible; it is never quietly marked done.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import fulfillment, printful
from app.config import Settings
from app.models import Approval, Base, Event, Order, Shipment


@pytest.fixture()
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


def connected(**overrides) -> Settings:
    base = {"printful_api_key": "pf_test_placeholder", "require_approval_for_high_risk": True}
    base.update(overrides)
    return Settings(**base)


def make_order(session: Session, **overrides) -> Order:
    fields = {
        "status": "paid",
        "total": Decimal("34.00"),
        "currency": "CAD",
        "external_ref": "cs_test_1",
        "ship_to_name": "Desmond Odhiambo",
        "ship_to_address1": "100 King St W",
        "ship_to_city": "Burlington",
        "ship_to_state": "ON",
        "ship_to_country": "CA",
        "ship_to_zip": "L7R 3N2",
        "ship_to_email": "buyer@example.test",
    }
    fields.update(overrides)
    order = Order(**fields)
    session.add(order)
    session.flush()
    return order


ITEMS = [{"sync_variant_id": 501, "quantity": 1, "retail_price": "34.00"}]


def draft_responder(order_id: int = 999):
    def request(method: str, path: str, body: dict | None):
        return 200, {"result": {"id": order_id, "external_id": "cs_test_1", "status": "draft",
                                "costs": {"total": "12.50", "currency": "cad"}}}

    return request


class TestStripeAddressCapture:
    def test_reads_the_modern_collected_information_shape(self):
        shipping = fulfillment.shipping_from_stripe_session(
            {
                "collected_information": {
                    "shipping_details": {
                        "name": "Buyer",
                        "address": {
                            "line1": "1 Main St",
                            "city": "Toronto",
                            "state": "ON",
                            "country": "ca",
                            "postal_code": "M5V 1A1",
                        },
                    }
                },
                "customer_details": {"email": "buyer@example.test"},
            }
        )
        assert shipping["address1"] == "1 Main St"
        assert shipping["country_code"] == "CA", "country is upper-cased for Printful"
        assert shipping["email"] == "buyer@example.test"

    def test_reads_the_older_top_level_shape(self):
        # An API-version bump must not silently start dropping addresses.
        shipping = fulfillment.shipping_from_stripe_session(
            {"shipping_details": {"name": "Buyer", "address": {"line1": "2 Main St", "country": "CA"}}}
        )
        assert shipping["address1"] == "2 Main St"

    def test_a_session_with_no_address_yields_no_address(self):
        shipping = fulfillment.shipping_from_stripe_session({"customer_details": {"email": "a@b.test"}})
        assert shipping["address1"] is None
        assert shipping["email"] == "a@b.test"

    def test_applies_the_address_to_an_order(self, session):
        order = make_order(session, ship_to_address1=None, ship_to_country=None)
        fulfillment.apply_shipping_details(
            order,
            {"shipping_details": {"name": "Buyer", "address": {"line1": "3 Main St", "country": "ca"}}},
        )
        assert order.ship_to_address1 == "3 Main St"
        assert order.ship_to_country == "CA"


class TestBookingADraft:
    def test_books_a_draft_and_records_the_shipment(self, session):
        order = make_order(session)
        result = fulfillment.book_supplier_draft(
            session, order, ITEMS, settings=connected(), request=draft_responder()
        )

        assert result["supplier_order_id"] == "999"
        shipment = session.scalar(select(Shipment).where(Shipment.order_id == order.id))
        assert shipment.supplier == "printful"
        assert shipment.supplier_cost == Decimal("12.50"), "margin needs the supplier's cost"
        # `drafted`, not `awaiting_approval` — no Approval row exists until
        # confirmation is requested, so naming that state here would advertise
        # something the approval queue cannot show.
        assert order.fulfillment_status == "drafted"

    def test_a_second_call_does_not_book_a_second_parcel(self, session):
        # Payment webhooks are redelivered; double-booking would print twice.
        order = make_order(session)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=connected(), request=draft_responder())
        again = fulfillment.book_supplier_draft(
            session, order, ITEMS, settings=connected(), request=draft_responder()
        )

        assert again["skipped"] == "shipment already recorded"
        assert len(session.scalars(select(Shipment)).all()) == 1

    def test_a_settled_order_is_left_alone(self, session):
        order = make_order(session, fulfillment_status="shipped")
        result = fulfillment.book_supplier_draft(
            session, order, ITEMS, settings=connected(), request=draft_responder()
        )
        assert result["skipped"] == "already settled"
        assert session.scalars(select(Shipment)).all() == []


class TestOrdersThatCannotShip:
    def test_an_unusable_address_is_recorded_not_swallowed(self, session):
        order = make_order(session, ship_to_address1=None)
        result = fulfillment.book_supplier_draft(
            session, order, ITEMS, settings=connected(), request=draft_responder()
        )

        assert result["status"] == "unfulfillable"
        assert "missing address1" in result["reason"]
        assert order.fulfillment_status == "unfulfillable"
        # The customer has been charged, so this is an open obligation and it
        # belongs in the ledger where the daily loop will surface it.
        event = session.scalars(select(Event)).all()[-1]
        assert event.result == "rejected"

    def test_no_supplier_connection_is_unfulfillable_not_pretend_shipped(self, session):
        order = make_order(session)
        result = fulfillment.book_supplier_draft(
            session, order, ITEMS, settings=Settings(printful_api_key=""), request=draft_responder()
        )
        assert result["status"] == "unfulfillable"
        assert "not connected" in result["reason"]
        assert session.scalars(select(Shipment)).all() == []

    def test_an_order_with_no_supplier_items_is_unfulfillable(self, session):
        order = make_order(session)
        result = fulfillment.book_supplier_draft(
            session, order, [], settings=connected(), request=draft_responder()
        )
        assert result["status"] == "unfulfillable"

    def test_a_supplier_rejection_is_recorded_not_raised(self, session):
        # An exception escaping here would abort the request and roll the
        # transaction back, leaving a *paid* order at `pending` with nothing
        # written anywhere — the exact silent failure this module prevents.
        order = make_order(session)

        def rejecting(method: str, path: str, body: dict | None):
            return 400, {"error": {"message": "Variant 501 is out of stock"}}

        result = fulfillment.book_supplier_draft(
            session, order, ITEMS, settings=connected(), request=rejecting
        )

        assert result["status"] == "unfulfillable"
        assert "out of stock" in result["reason"]
        assert order.fulfillment_status == "unfulfillable"
        assert session.scalars(select(Event)).all()[-1].result == "rejected"

    def test_a_supplier_outage_is_recorded_not_raised(self, session):
        order = make_order(session)

        def unreachable(method: str, path: str, body: dict | None):
            raise printful.PrintfulError("could not reach Printful: timed out")

        result = fulfillment.book_supplier_draft(
            session, order, ITEMS, settings=connected(), request=unreachable
        )
        assert result["status"] == "unfulfillable"
        assert order.fulfillment_status == "unfulfillable"


class TestConfirmation:
    def test_confirming_queues_an_approval_instead_of_spending_money(self, session):
        order = make_order(session)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=connected(), request=draft_responder())
        shipment = session.scalar(select(Shipment))

        calls: list[str] = []

        def request(method: str, path: str, body: dict | None):
            calls.append(path)
            return 200, {"result": {"id": 999, "status": "pending"}}

        result = fulfillment.confirm_shipment(session, shipment, settings=connected(), request=request)

        assert result["requires_approval"] is True
        assert result["approval_id"] is not None
        assert calls == [], "no supplier call may happen before a human approves"
        assert shipment.status == "draft"

        approval = session.get(Approval, result["approval_id"])
        assert approval.action == "printful_confirm_order"
        assert approval.status == "pending"

    def test_auto_confirm_setting_still_queues_an_approval(self, session):
        # The flag records operator intent; it is not a way around the gate.
        order = make_order(session)
        settings = connected(printful_auto_confirm=True)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=settings, request=draft_responder())
        shipment = session.scalar(select(Shipment))

        result = fulfillment.confirm_shipment(
            session, shipment, settings=settings, request=draft_responder()
        )
        assert result["requires_approval"] is True

    def test_an_approved_confirmation_actually_reaches_the_supplier(self, session):
        # The gate is only a gate if approving something makes it happen. Without
        # a path that consumes the approved row, every retry would queue another
        # pending approval and the supplier would never be called at all.
        order = make_order(session)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=connected(), request=draft_responder())
        shipment = session.scalar(select(Shipment))

        queued = fulfillment.confirm_shipment(session, shipment, settings=connected())
        approval = session.get(Approval, queued["approval_id"])
        approval.status = "approved"
        session.flush()

        calls: list[str] = []

        def request(method: str, path: str, body: dict | None):
            calls.append(path)
            return 200, {"result": {"id": 999, "status": "pending", "costs": {"total": "12.50", "currency": "cad"}}}

        result = fulfillment.confirm_shipment(session, shipment, settings=connected(), request=request)

        assert result["confirmed"] is True
        assert calls == ["/orders/999/confirm"]
        # Local lifecycle, not the supplier's word for it: Printful says
        # "pending" right after a successful confirm, and storing that would make
        # the already-confirmed guard fail to recognise its own work.
        assert shipment.status == "confirmed"
        assert result["supplier_status"] == "pending"
        assert order.fulfillment_status == "confirmed"

    def test_a_confirmed_shipment_is_not_reconfirmed_by_a_second_approval(self, session):
        # The guard has to hold against the supplier's own vocabulary, or a
        # second approved request pays for the same print run twice.
        order = make_order(session)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=connected(), request=draft_responder())
        shipment = session.scalar(select(Shipment))

        queued = fulfillment.confirm_shipment(session, shipment, settings=connected())
        session.get(Approval, queued["approval_id"]).status = "approved"
        session.flush()

        calls: list[str] = []

        def request(method: str, path: str, body: dict | None):
            calls.append(path)
            return 200, {"result": {"id": 999, "status": "pending"}}

        fulfillment.confirm_shipment(session, shipment, settings=connected(), request=request)
        again = fulfillment.confirm_shipment(session, shipment, settings=connected(), request=request)

        assert again["skipped"] == "already confirmed"
        assert len(calls) == 1

    def test_an_approval_is_spent_exactly_once(self, session):
        # One human decision must not be replayable into two supplier charges.
        order = make_order(session)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=connected(), request=draft_responder())
        shipment = session.scalar(select(Shipment))

        queued = fulfillment.confirm_shipment(session, shipment, settings=connected())
        session.get(Approval, queued["approval_id"]).status = "approved"
        session.flush()

        calls: list[str] = []

        def request(method: str, path: str, body: dict | None):
            calls.append(path)
            return 200, {"result": {"id": 999, "status": "pending"}}

        fulfillment.confirm_shipment(session, shipment, settings=connected(), request=request)
        shipment.status = "draft"  # pretend the supplier state was reverted
        again = fulfillment.confirm_shipment(session, shipment, settings=connected(), request=request)

        assert len(calls) == 1, "the spent approval must not authorise a second confirmation"
        assert again["requires_approval"] is True
        assert session.get(Approval, queued["approval_id"]).status == "executed"

    def test_an_approval_for_another_shipment_does_not_authorise_this_one(self, session):
        order_a = make_order(session)
        order_b = make_order(session, external_ref="cs_test_2")
        fulfillment.book_supplier_draft(session, order_a, ITEMS, settings=connected(), request=draft_responder(1))
        fulfillment.book_supplier_draft(session, order_b, ITEMS, settings=connected(), request=draft_responder(2))
        first, second = session.scalars(select(Shipment).order_by(Shipment.id)).all()

        queued = fulfillment.confirm_shipment(session, first, settings=connected())
        session.get(Approval, queued["approval_id"]).status = "approved"
        session.flush()

        calls: list[str] = []

        def request(method: str, path: str, body: dict | None):
            calls.append(path)
            return 200, {"result": {"id": 2, "status": "pending"}}

        result = fulfillment.confirm_shipment(session, second, settings=connected(), request=request)
        assert result["requires_approval"] is True
        assert calls == [], "approvals are bound to their target shipment"

    def test_a_supplier_failure_during_confirmation_is_recorded(self, session):
        order = make_order(session)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=connected(), request=draft_responder())
        shipment = session.scalar(select(Shipment))
        queued = fulfillment.confirm_shipment(session, shipment, settings=connected())
        session.get(Approval, queued["approval_id"]).status = "approved"
        session.flush()

        def failing(method: str, path: str, body: dict | None):
            return 400, {"error": {"message": "insufficient funds in wallet"}}

        result = fulfillment.confirm_shipment(session, shipment, settings=connected(), request=failing)

        assert "insufficient funds" in result["error"]
        assert order.fulfillment_status != "confirmed"
        event = session.scalars(select(Event)).all()[-1]
        assert event.result == "error"

    def test_an_already_confirmed_shipment_is_not_confirmed_twice(self, session):
        order = make_order(session)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=connected(), request=draft_responder())
        shipment = session.scalar(select(Shipment))
        shipment.status = "confirmed"

        result = fulfillment.confirm_shipment(session, shipment, settings=connected())
        assert result["skipped"] == "already confirmed"


class TestShipmentNotices:
    def test_applies_tracking_to_the_matching_order(self, session):
        order = make_order(session)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=connected(), request=draft_responder())

        result = fulfillment.record_shipment_notice(
            session,
            {
                "supplier": "printful",
                "external_id": "cs_test_1",
                "supplier_order_id": "999",
                "tracking_number": "1Z999",
                "tracking_url": "https://track.test/1Z999",
                "carrier": "UPS",
            },
        )

        assert result["matched"] is True
        shipment = session.get(Shipment, result["shipment_id"])
        assert shipment.tracking_number == "1Z999"
        assert shipment.status == "shipped"
        assert order.fulfillment_status == "shipped"

    def test_redelivery_updates_rather_than_duplicating(self, session):
        order = make_order(session)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=connected(), request=draft_responder())
        notice = {
            "supplier": "printful",
            "external_id": "cs_test_1",
            "supplier_order_id": "999",
            "supplier_shipment_id": "ship_1",
            "tracking_number": "1Z999",
        }
        fulfillment.record_shipment_notice(session, notice)
        fulfillment.record_shipment_notice(session, notice)

        assert len(session.scalars(select(Shipment)).all()) == 1

    def test_a_split_order_gets_a_row_per_parcel(self, session):
        # Print-on-demand routes items to whichever facility can make them, so
        # one order arrives as several parcels. Keying idempotency on the order
        # id would let the second parcel overwrite the first one's tracking and
        # leave a customer chasing a parcel we never told them about.
        order = make_order(session)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=connected(), request=draft_responder())

        for parcel, tracking in (("ship_1", "1Z111"), ("ship_2", "1Z222")):
            fulfillment.record_shipment_notice(
                session,
                {
                    "supplier": "printful",
                    "external_id": "cs_test_1",
                    "supplier_order_id": "999",
                    "supplier_shipment_id": parcel,
                    "tracking_number": tracking,
                },
            )

        shipments = session.scalars(select(Shipment)).all()
        assert len(shipments) == 2
        assert sorted(s.tracking_number for s in shipments) == ["1Z111", "1Z222"]
        assert {s.supplier_order_id for s in shipments} == {"999"}

    def test_a_notice_without_a_parcel_id_still_lands_on_the_draft_row(self, session):
        order = make_order(session)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=connected(), request=draft_responder())

        fulfillment.record_shipment_notice(
            session,
            {"supplier": "printful", "external_id": "cs_test_1", "supplier_order_id": "999",
             "tracking_number": "1Z999"},
        )
        shipments = session.scalars(select(Shipment)).all()
        assert len(shipments) == 1
        assert shipments[0].tracking_number == "1Z999"

    def test_a_parcel_belonging_to_another_order_is_refused(self, session):
        # The parcel lookup spans every order, so a replayed or inconsistent
        # notice could name order B's external_id alongside order A's parcel.
        # Attaching it would rewrite A's tracking *and* mark B shipped — two
        # customers wrong from one bad message.
        order_a = make_order(session)
        order_b = make_order(session, external_ref="cs_test_2")
        fulfillment.book_supplier_draft(session, order_a, ITEMS, settings=connected(), request=draft_responder(1))
        fulfillment.book_supplier_draft(session, order_b, ITEMS, settings=connected(), request=draft_responder(2))

        fulfillment.record_shipment_notice(
            session,
            {"supplier": "printful", "external_id": "cs_test_1", "supplier_order_id": "1",
             "supplier_shipment_id": "parcel_a", "tracking_number": "1Z-A"},
        )

        result = fulfillment.record_shipment_notice(
            session,
            {"supplier": "printful", "external_id": "cs_test_2", "supplier_order_id": "2",
             "supplier_shipment_id": "parcel_a", "tracking_number": "1Z-HIJACK"},
        )

        assert result["matched"] is False
        assert result["conflict"] == "parcel_order_mismatch"
        assert order_b.fulfillment_status != "shipped"
        parcel = session.scalar(select(Shipment).where(Shipment.supplier_shipment_id == "parcel_a"))
        assert parcel.tracking_number == "1Z-A", "order A's tracking must be untouched"
        assert parcel.order_id == order_a.id
        assert session.scalars(select(Event)).all()[-1].result == "rejected"

    def test_the_suppliers_ship_date_is_preferred_over_receipt_time(self, session):
        # A webhook can arrive hours late or be retried, so receipt time would
        # quietly misdate the shipment.
        order = make_order(session)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=connected(), request=draft_responder())

        fulfillment.record_shipment_notice(
            session,
            {"supplier": "printful", "external_id": "cs_test_1", "supplier_shipment_id": "p1",
             "tracking_number": "1Z999", "shipped_at": "2026-08-01"},
        )
        shipment = session.scalar(select(Shipment))
        assert shipment.shipped_at.year == 2026
        assert (shipment.shipped_at.month, shipment.shipped_at.day) == (8, 1)

    def test_an_unparseable_ship_date_falls_back_to_now(self, session):
        order = make_order(session)
        fulfillment.book_supplier_draft(session, order, ITEMS, settings=connected(), request=draft_responder())
        fulfillment.record_shipment_notice(
            session,
            {"supplier": "printful", "external_id": "cs_test_1", "supplier_shipment_id": "p1",
             "tracking_number": "1Z999", "shipped_at": "not-a-date"},
        )
        assert session.scalar(select(Shipment)).shipped_at is not None

    def test_an_unmatched_notice_is_logged_not_guessed_at(self, session):
        # Attaching this to the closest-looking order would send one customer
        # another customer's tracking number.
        make_order(session)
        result = fulfillment.record_shipment_notice(
            session, {"external_id": "cs_unknown", "supplier_order_id": "42"}
        )

        assert result["matched"] is False
        assert session.scalars(select(Shipment)).all() == []
        event = session.scalars(select(Event)).all()[-1]
        assert event.result == "rejected"


class TestSchemaMatchesProduction:
    def test_the_parcel_uniqueness_constraint_exists_in_the_orm_schema(self, session):
        """The migration creates a partial unique index on
        (supplier, supplier_shipment_id). If the ORM metadata did not mirror it,
        SQLite dev/demo/test databases would be weaker than production and this
        idempotency would go untested exactly where it is cheapest to test."""
        order = make_order(session)
        session.add(Shipment(order_id=order.id, supplier="printful", supplier_shipment_id="dup"))
        session.flush()
        session.add(Shipment(order_id=order.id, supplier="printful", supplier_shipment_id="dup"))

        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_several_parcels_without_an_id_are_still_allowed(self, session):
        """The index is partial — NULL parcel ids must not collide, or an order
        could never hold two rows before their shipment ids arrive."""
        order = make_order(session)
        session.add(Shipment(order_id=order.id, supplier="printful"))
        session.add(Shipment(order_id=order.id, supplier="printful"))
        session.flush()
        assert len(session.scalars(select(Shipment)).all()) == 2
