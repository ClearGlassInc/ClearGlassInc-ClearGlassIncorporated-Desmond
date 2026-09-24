"""Reconciliation finds every disagreement, reports it, and changes nothing.

The core is stdlib-only and works on plain dicts, so most of these run without
a database. The last two drive it through the CLI and the snapshot adapter.
"""
from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app import reconciliation as r

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
REF = "CG-ORD-2026-ABCDEFGH"


def payment(pid: int = 1, **overrides) -> dict:
    row = {
        "id": pid, "source": "stripe_checkout", "status": "paid", "total": Decimal("297.00"),
        "currency": "CAD", "environment": "live", "external_ref": f"cs_live_{pid}",
        "payment_intent": f"pi_{pid}", "amount_refunded": Decimal(0), "dispute_status": None,
        "order_ref": REF,
    }
    row.update(overrides)
    return row


def order(**overrides) -> dict:
    row = {
        "order_ref": REF, "payment_state": "PAID", "amount": Decimal("297.00"), "currency": "CAD",
        "environment": "live", "payment_order_id": 1, "reconciliation_required": False,
        "reconciliation_reason": None, "fulfillment_state": "FULFILLMENT_PENDING",
        "created_at": NOW, "updated_at": NOW,
    }
    row.update(overrides)
    return row


def snap(payments=None, orders=None, services=None, events=None) -> dict:
    return {
        "payments": payments if payments is not None else [payment()],
        "commercial_orders": orders if orders is not None else [order()],
        "service_orders": services if services is not None else [{"id": 1, "order_id": 1, "status": "INTAKE_REQUIRED"}],
        "events": events or [],
    }


def codes(report: dict) -> set[str]:
    return {f["code"] for f in report["findings"]}


def test_a_consistent_ledger_is_clean_but_says_the_processors_were_not_checked() -> None:
    report = r.reconcile(snap(), now=NOW)
    assert report["findings"] == []
    assert report["clean"] is True
    assert report["provider_comparison"]["status"] == "NOT VERIFIED"


def test_it_never_mutates_what_it_reads() -> None:
    data = snap(payments=[payment(), payment(2, source="paypal_orders", external_ref="paypal_capture_X")])
    before = copy.deepcopy(data)
    r.reconcile(data, [{"provider": "stripe", "reference": "pi_9", "amount": "1", "currency": "CAD",
                        "status": "paid"}], now=NOW)
    assert data == before


def test_stripe_and_paypal_on_one_order_is_a_critical_duplicate() -> None:
    report = r.reconcile(snap(payments=[
        payment(), payment(2, source="paypal_orders", external_ref="paypal_capture_X", payment_intent=None),
    ]), now=NOW)
    duplicate = next(f for f in report["findings"] if f["code"] == "DUPLICATE_PAYMENT")
    assert duplicate["severity"] == "critical"
    assert duplicate["providers"] == ["paypal", "stripe"]
    assert "do not delete" in duplicate["detail"]
    assert report["clean"] is False


def test_a_duplicate_in_test_mode_is_not_critical() -> None:
    report = r.reconcile(snap(payments=[
        payment(environment="test"), payment(2, environment="test"),
    ], orders=[order(environment="test")]), now=NOW)
    duplicate = next(f for f in report["findings"] if f["code"] == "DUPLICATE_PAYMENT")
    assert duplicate["severity"] == "medium"


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (snap(payments=[]), "ORDER_PAID_WITHOUT_PAYMENT"),
        (snap(orders=[order(payment_state="CHECKOUT_STARTED", payment_order_id=None,
                            fulfillment_state="NOT_STARTED")]), "PAYMENT_NOT_APPLIED_TO_ORDER"),
        (snap(payments=[payment(currency="USD")]), "CURRENCY_MISMATCH"),
        (snap(payments=[payment(total=Decimal("1.00"))]), "AMOUNT_MISMATCH"),
        (snap(payments=[payment(environment="test")]), "ENVIRONMENT_MISMATCH"),
        (snap(orders=[order(reconciliation_required=True, reconciliation_reason="DUPLICATE_PAYMENT: x")]),
         "OPEN_RECONCILIATION_FLAG"),
        (snap(orders=[order(fulfillment_state="NOT_STARTED")], services=[]), "PAID_WITHOUT_FULFILLMENT"),
        (snap(payments=[payment(order_ref="CG-ORD-2026-ZZZZZZZZ")]), "UNKNOWN_ORDER_REF"),
        (snap(payments=[payment(status="failed")], orders=[order(payment_state="PAYMENT_FAILED",
                                                                  payment_order_id=None)]),
         "FULFILLMENT_WITHOUT_PAYMENT"),
        (snap(payments=[payment(), payment(9, order_ref=None)]), "UNLINKED_PAYMENT"),
        (snap(events=[{"id": 4, "action": "refund_unmatched", "target": "ch_1"}]), "UNMATCHED_PROCESSOR_EVENT"),
        (snap(events=[{"id": 5, "action": "paypal_webhook_rejected", "target": "x"}]), "WEBHOOK_REJECTED"),
    ],
)
def test_each_ledger_discrepancy_is_named(data, code) -> None:
    assert code in codes(r.reconcile(data, now=NOW))


def test_an_abandoned_checkout_is_reported_as_information_only() -> None:
    old = NOW - timedelta(hours=30)
    report = r.reconcile(snap(payments=[], services=[], orders=[
        order(payment_state="CHECKOUT_STARTED", payment_order_id=None, fulfillment_state="NOT_STARTED",
              created_at=old, updated_at=old),
    ]), now=NOW)
    stale = next(f for f in report["findings"] if f["code"] == "STALE_CHECKOUT")
    assert stale["severity"] == "info"
    assert report["clean"] is True


# --- processor comparison ------------------------------------------------------------


def stripe_record(**overrides) -> dict:
    row = {"provider": "stripe", "reference": "pi_1", "amount": "297.00", "currency": "CAD",
           "status": "paid", "amount_refunded": "0", "livemode": True}
    row.update(overrides)
    return row


def test_matching_processor_records_compare_clean() -> None:
    report = r.reconcile(snap(), [stripe_record()], now=NOW)
    assert report["provider_comparison"] == {"status": "COMPARED", "providers": ["stripe"], "records": 1}
    assert report["findings"] == []


@pytest.mark.parametrize(
    ("record", "code"),
    [
        (stripe_record(reference="pi_404"), "PROVIDER_PAYMENT_MISSING_FROM_LEDGER"),
        (stripe_record(amount="300.00"), "PROVIDER_AMOUNT_MISMATCH"),
        (stripe_record(currency="USD"), "PROVIDER_CURRENCY_MISMATCH"),
        (stripe_record(amount_refunded="297.00", status="refunded"), "PROVIDER_REFUND_MISMATCH"),
        (stripe_record(status="failed"), "PROVIDER_STATUS_MISMATCH"),
        (stripe_record(livemode=False), "PROVIDER_ENVIRONMENT_MISMATCH"),
        (stripe_record(disputed=True), "PROVIDER_DISPUTE_MISSING_FROM_LEDGER"),
    ],
)
def test_each_processor_disagreement_is_named(record, code) -> None:
    assert code in codes(r.reconcile(snap(), [record], now=NOW))


def test_a_ledger_payment_the_processor_does_not_have_is_critical() -> None:
    report = r.reconcile(snap(), [stripe_record(reference="pi_other")], now=NOW)
    missing = next(f for f in report["findings"] if f["code"] == "LEDGER_PAYMENT_MISSING_AT_PROVIDER")
    assert missing["severity"] == "critical"


def test_only_the_processors_supplied_are_judged() -> None:
    """A Stripe export says nothing about PayPal; PayPal rows are not called missing."""
    data = snap(payments=[payment(), payment(2, source="paypal_orders", order_ref=None,
                                             external_ref="paypal_capture_CAP9", payment_intent=None)])
    report = r.reconcile(data, [stripe_record()], now=NOW)
    assert "LEDGER_PAYMENT_MISSING_AT_PROVIDER" not in codes(report)


def test_paypal_records_match_on_the_capture_id() -> None:
    data = snap(payments=[payment(source="paypal_orders", external_ref="paypal_capture_CAP9", payment_intent=None)])
    record = {"provider": "paypal", "reference": "CAP9", "amount": "297.00", "currency": "CAD", "status": "paid"}
    assert r.reconcile(data, [record], now=NOW)["findings"] == []


def test_a_raw_stripe_charge_is_normalized() -> None:
    charge = {"object": "charge", "id": "ch_1", "payment_intent": "pi_1", "amount": 29700,
              "amount_refunded": 9700, "currency": "cad", "status": "succeeded", "refunded": False,
              "livemode": True, "metadata": {"cg_order_ref": REF}, "disputed": False}
    record = r.normalize_provider_record(charge)
    assert record["reference"] == "pi_1"
    assert record["amount"] == Decimal("297")
    assert record["amount_refunded"] == Decimal("97")
    assert record["status"] == "paid"
    assert record["order_ref"] == REF


# --- CLI and database adapter ---------------------------------------------------------


def test_the_cli_reads_the_database_and_an_export(monkeypatch, tmp_path, capsys) -> None:
    sqlalchemy = pytest.importorskip("sqlalchemy")
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app import db as db_module
    from app.models import Base, CommercialOrder, Order

    engine = sqlalchemy.create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Factory = sessionmaker(bind=engine, expire_on_commit=False)
    with Factory() as s:
        s.add(Order(status="paid", total=Decimal("297.00"), currency="CAD", source="stripe_checkout",
                    environment="live", external_ref="cs_live_1", payment_intent="pi_1",
                    amount_refunded=Decimal(0), order_ref=REF))
        s.add(CommercialOrder(order_ref=REF, sku="risk-audit-90", offer_name="Audit", amount=Decimal("297.00"),
                              currency="CAD", payment_state="PAID", payment_order_id=1, environment="live"))
        s.commit()
    monkeypatch.setattr(db_module, "SessionLocal", Factory)

    export = tmp_path / "stripe.json"
    export.write_text(json.dumps({"object": "list", "data": [
        {"object": "charge", "payment_intent": "pi_1", "amount": 29700, "amount_refunded": 0,
         "currency": "cad", "status": "succeeded", "livemode": True},
    ]}))
    code = r.main(["--json", "--provider-export", str(export)])
    report = json.loads(capsys.readouterr().out)
    assert report["provider_comparison"]["status"] == "COMPARED"
    # Paid, live, and no service order: the one real gap in this ledger.
    assert codes(report) == {"PAID_WITHOUT_FULFILLMENT"}
    assert code == 2
