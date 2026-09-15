"""PayPal Orders — verification, replay protection, and the money-in/parcel-out rule.

The properties under test, in the order they matter:

1. An unverified webhook books nothing. There is no development shortcut.
2. A redelivered capture books nothing a second time.
3. Approval is not payment, and a held capture is not revenue.
4. A capture that does not reconcile to the catalogue never becomes shippable.
5. The browser cannot choose what PayPal charges.

Everything here runs offline: the transport is injected, so no test needs
credentials or reaches PayPal.
"""
from __future__ import annotations

import json
from decimal import Decimal

import pytest
from app.config import Settings
from app.governance import RiskTier, score_action
from app.models import Base, Event, Order
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import paypal

CONNECTED = {
    "paypal_client_id": "test-client-id-not-a-real-credential",
    "paypal_client_secret": "test-client-secret-not-a-real-credential",
    "paypal_webhook_id": "WH-TEST-0001",
    "paypal_api_base": "https://api-m.sandbox.paypal.com",
}

SIGNED_HEADERS = {
    "paypal-transmission-id": "b9d8f0a0-0000-11ef-9f1a-000000000000",
    "paypal-transmission-time": "2026-09-15T12:00:00Z",
    "paypal-transmission-sig": "c2lnbmF0dXJl",
    "paypal-cert-url": "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-abc",
    "paypal-auth-algo": "SHA256withRSA",
}

# The catalogue SKU these tests transact against, and what it actually costs.
SKU = "risk-audit-90"
SKU_CENTS = 29700


def connected(**overrides) -> Settings:
    return Settings(**{**CONNECTED, **overrides})


def responder(*, token: str = "A21AA-test-token", verification: str = "SUCCESS", **routes):
    """A transport that answers the token call, the verification call, and any route given.

    Records every call it saw on ``.calls`` so a test can assert what was actually
    sent to PayPal rather than what the code claims it sends.
    """
    calls: list[tuple[str, str, object]] = []

    def request(method: str, path: str, body=None, headers=None):
        calls.append((method, path, body))
        if path == "/v1/oauth2/token":
            return 200, {"access_token": token, "expires_in": 32400}
        if path == "/v1/notifications/verify-webhook-signature":
            return 200, {"verification_status": verification}
        if path in routes:
            return routes[path]
        return 404, {"name": "RESOURCE_NOT_FOUND"}

    request.calls = calls  # type: ignore[attr-defined]
    return request


def capture_event(
    *,
    event_type: str = paypal.CAPTURE_COMPLETED,
    capture_id: str = "3C679366HH908993F",
    value: str = "297.00",
    currency: str = "CAD",
    custom_id: str = f"{SKU}x1",
) -> dict:
    return {
        "id": "WH-EVENT-0001",
        "event_type": event_type,
        "resource": {
            "id": capture_id,
            "status": "COMPLETED",
            "custom_id": custom_id,
            "amount": {"currency_code": currency, "value": value},
        },
    }


# ── Webhook verification: fail closed, every time ──────────────────────────


def test_no_webhook_id_configured_means_no_event_is_ever_verified() -> None:
    """The one configuration that would otherwise accept anonymous settlement events."""
    result = paypal.verify_webhook(
        json.dumps(capture_event()).encode(),
        SIGNED_HEADERS,
        settings=connected(paypal_webhook_id=""),
        request=responder(),
    )
    assert result["verified"] is False
    assert "webhook id" in result["reason"]


def test_missing_signature_headers_are_refused() -> None:
    for omitted in paypal.REQUIRED_WEBHOOK_HEADERS:
        headers = {k: v for k, v in SIGNED_HEADERS.items() if k != omitted}
        result = paypal.verify_webhook(
            json.dumps(capture_event()).encode(),
            headers,
            settings=connected(),
            request=responder(),
        )
        assert result["verified"] is False, f"a webhook missing {omitted} was accepted"
        assert omitted in result["reason"]


def test_a_valid_signature_verifies() -> None:
    result = paypal.verify_webhook(
        json.dumps(capture_event()).encode(),
        SIGNED_HEADERS,
        settings=connected(),
        request=responder(verification="SUCCESS"),
    )
    assert result["verified"] is True
    assert result["event"]["event_type"] == paypal.CAPTURE_COMPLETED


def test_paypal_saying_failure_is_a_rejection() -> None:
    result = paypal.verify_webhook(
        json.dumps(capture_event()).encode(),
        SIGNED_HEADERS,
        settings=connected(),
        request=responder(verification="FAILURE"),
    )
    assert result["verified"] is False


def test_an_unreachable_verification_api_is_a_rejection_not_a_pass() -> None:
    """The failure mode that would otherwise open the endpoint during an outage."""

    def broken(method, path, body=None, headers=None):
        raise paypal.PayPalError("could not reach PayPal: connection reset")

    result = paypal.verify_webhook(
        json.dumps(capture_event()).encode(),
        SIGNED_HEADERS,
        settings=connected(),
        request=broken,
    )
    assert result["verified"] is False
    assert "verification call failed" in result["reason"]


def test_unparseable_payloads_are_refused() -> None:
    for payload in (b"not json", b"[]", b"\xff\xfe"):
        result = paypal.verify_webhook(
            payload, SIGNED_HEADERS, settings=connected(), request=responder()
        )
        assert result["verified"] is False


@pytest.mark.parametrize(
    "cert_url,trusted",
    [
        ("https://api.paypal.com/v1/notifications/certs/CERT-1", True),
        ("https://api.sandbox.paypal.com/v1/notifications/certs/CERT-1", True),
        # Suffix matching would accept this one — the check is on the exact host.
        ("https://api.paypal.com.attacker.test/certs/CERT-1", False),
        ("https://attacker.test/certs/CERT-1", False),
        ("http://api.paypal.com/certs/CERT-1", False),  # plaintext
        ("file:///etc/passwd", False),
        ("", False),
    ],
)
def test_only_paypals_own_hosts_may_serve_the_signing_certificate(cert_url, trusted) -> None:
    assert paypal.cert_url_is_trusted(cert_url) is trusted


def test_a_forged_certificate_url_is_refused_before_it_is_forwarded() -> None:
    transport = responder()
    result = paypal.verify_webhook(
        json.dumps(capture_event()).encode(),
        {**SIGNED_HEADERS, "paypal-cert-url": "https://attacker.test/certs/CERT-1"},
        settings=connected(),
        request=transport,
    )
    assert result["verified"] is False
    assert "certificate url" in result["reason"]
    assert transport.calls == [], "the forged cert url reached PayPal's API"


# ── Order creation: the server owns the price ──────────────────────────────


def test_no_credentials_means_a_mock_order_and_no_network_call() -> None:
    transport = responder()
    order = paypal.create_order(
        [{"sku": SKU, "name": "Risk audit", "amount": SKU_CENTS, "currency": "cad", "quantity": 1}],
        settings=Settings(paypal_client_id="", paypal_client_secret=""),
        request=transport,
    )
    assert order["mode"] == "mock"
    assert order["amount_total"] == SKU_CENTS
    assert transport.calls == []


def test_the_amount_sent_to_paypal_comes_from_the_priced_line_items() -> None:
    transport = responder(
        **{
            "/v2/checkout/orders": (
                201,
                {
                    "id": "5O190127TN364715T",
                    "status": "CREATED",
                    "links": [{"rel": "payer-action", "href": "https://paypal.test/approve"}],
                },
            )
        }
    )
    order = paypal.create_order(
        [{"sku": SKU, "name": "Risk audit", "amount": SKU_CENTS, "currency": "cad", "quantity": 2}],
        settings=connected(),
        request=transport,
    )

    body = next(body for method, path, body in transport.calls if path == "/v2/checkout/orders")
    unit = body["purchase_units"][0]
    assert unit["amount"]["value"] == "594.00"  # 2 x 297.00, computed here
    assert unit["amount"]["currency_code"] == "CAD"
    assert unit["custom_id"] == f"{SKU}x2"
    assert body["intent"] == "CAPTURE", "intent must not authorize-and-forget"
    assert order["approve_url"] == "https://paypal.test/approve"
    assert order["amount_total"] == SKU_CENTS * 2


def test_an_order_with_no_approval_link_is_an_error_not_a_silent_success() -> None:
    transport = responder(
        **{"/v2/checkout/orders": (201, {"id": "5O190127TN364715T", "links": []})}
    )
    with pytest.raises(paypal.PayPalError, match="approval link"):
        paypal.create_order(
            [{"sku": SKU, "name": "Risk audit", "amount": SKU_CENTS, "currency": "cad", "quantity": 1}],
            settings=connected(),
            request=transport,
        )


def test_mixed_currency_carts_are_refused() -> None:
    with pytest.raises(paypal.PayPalError, match="mix currencies"):
        paypal.create_order(
            [
                {"sku": "a", "amount": 100, "currency": "cad", "quantity": 1},
                {"sku": "b", "amount": 100, "currency": "usd", "quantity": 1},
            ],
            settings=connected(),
            request=responder(),
        )


def test_bad_credentials_do_not_leak_the_response_body() -> None:
    def rejecting(method, path, body=None, headers=None):
        return 401, {"error": "invalid_client", "client_id": CONNECTED["paypal_client_id"]}

    with pytest.raises(paypal.PayPalError) as exc:
        paypal.create_order(
            [{"sku": SKU, "amount": SKU_CENTS, "currency": "cad", "quantity": 1}],
            settings=connected(),
            request=rejecting,
        )
    assert CONNECTED["paypal_client_id"] not in str(exc.value)
    assert CONNECTED["paypal_client_secret"] not in str(exc.value)


# ── Catalogue reconciliation ───────────────────────────────────────────────


def test_a_capture_matching_the_catalogue_reconciles() -> None:
    matches, why = paypal.check_against_catalog(f"{SKU}x1", Decimal("297.00"), "CAD")
    assert matches is True, why


def test_a_capture_for_the_wrong_amount_does_not_reconcile() -> None:
    matches, why = paypal.check_against_catalog(f"{SKU}x1", Decimal("1.00"), "CAD")
    assert matches is False
    assert "amount mismatch" in why


def test_a_capture_in_the_wrong_currency_does_not_reconcile() -> None:
    matches, why = paypal.check_against_catalog(f"{SKU}x1", Decimal("297.00"), "USD")
    assert matches is False
    assert "currency mismatch" in why


@pytest.mark.parametrize("custom_id", ["", "   ", "not-a-sku-spec", "unknown-skux1", f"{SKU}xNaN"])
def test_a_capture_with_no_usable_catalogue_reference_does_not_reconcile(custom_id) -> None:
    matches, _why = paypal.check_against_catalog(custom_id, Decimal("297.00"), "CAD")
    assert matches is False


def test_sku_spec_round_trips_and_drops_what_it_cannot_read() -> None:
    items = [{"sku": "alpha", "quantity": 2}, {"sku": "beta", "quantity": 1}]
    assert paypal.parse_sku_spec(paypal.sku_spec(items)) == items
    assert paypal.parse_sku_spec("alphax2,garbage,betax1") == items


def test_an_unreadable_capture_amount_raises_rather_than_booking_zero() -> None:
    with pytest.raises(paypal.PayPalError):
        paypal.capture_amount({"amount": {"value": "not-a-number", "currency_code": "CAD"}})


def test_capture_shipping_is_normalized_for_the_shared_ledger() -> None:
    shipping = paypal.shipping_from_capture(
        {
            "shipping": {
                "name": {"full_name": "Desmond Odhiambo"},
                "address": {
                    "address_line_1": "100 King St W",
                    "admin_area_2": "Burlington",
                    "admin_area_1": "ON",
                    "postal_code": "L7R 3N2",
                    "country_code": "ca",
                },
            },
            "payer": {"email_address": "buyer@example.test"},
        }
    )
    assert shipping["address1"] == "100 King St W"
    assert shipping["city"] == "Burlington"
    assert shipping["state_code"] == "ON"
    assert shipping["country_code"] == "CA"
    assert shipping["email"] == "buyer@example.test"


# ── Governance ─────────────────────────────────────────────────────────────


def test_capturing_and_refunding_always_need_a_human() -> None:
    for action in ("paypal_capture_order", "paypal_refund_capture"):
        assessment = score_action(action)
        assert assessment.requires_approval is True, f"{action} can auto-execute"
        assert assessment.tier in (RiskTier.HIGH, RiskTier.CRITICAL)


def test_reading_paypal_state_is_not_gated() -> None:
    assert score_action("paypal_connection_check").requires_approval is False


def test_connection_state_warns_when_payments_could_never_be_booked() -> None:
    state = paypal.connection_state(connected(paypal_webhook_id=""))
    assert state["webhook_verification"] == "unconfigured"
    assert any("will ever be booked" in w for w in state["warnings"])


def test_connection_state_never_echoes_a_secret() -> None:
    serialized = json.dumps(paypal.connection_state(connected()))
    assert CONNECTED["paypal_client_secret"] not in serialized
    assert CONNECTED["paypal_client_id"] not in serialized


# ── The webhook endpoint: booking, replay, and the fulfillment gate ────────

try:
    import os as _os

    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool
    _os.environ.setdefault("DATABASE_URL", "sqlite://")
    from app.main import create_app

    from app import config as config_module
    from app import db as db_module

    _HAS_WEB_STACK = True
except (ImportError, RuntimeError):  # pragma: no cover - minimal env runs pure tests only
    _HAS_WEB_STACK = False


@pytest.fixture()
def client(monkeypatch):
    """App + in-memory DB, with PayPal signature verification stubbed to succeed.

    Verification itself is covered above against the real implementation; stubbing
    it here keeps these tests about what the *router* does with a verified event.

    Credentials are deliberately left unset, so order creation runs in mock mode
    and no test can reach the network. That costs nothing here: what these tests
    assert is the booking, replay and gating behaviour, none of which depends on
    the transport. The live request body is asserted directly against an injected
    transport in ``test_the_amount_sent_to_paypal_comes_from_the_priced_line_items``.
    """
    if not _HAS_WEB_STACK:
        pytest.skip("fastapi/sqlalchemy not installed")

    config_module.get_settings.cache_clear()

    def accept(payload, headers, **kwargs):
        return {"verified": True, "event": json.loads(payload.decode()), "reason": "ok"}

    monkeypatch.setattr(paypal, "verify_webhook", accept)

    engine = create_engine(
        "sqlite://", future=True,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine, autoflush=False, expire_on_commit=False)

    def override_session():
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

    app = create_app()
    app.dependency_overrides[db_module.get_session] = override_session
    try:
        test_client = TestClient(app, raise_server_exceptions=False)
        test_client.db = db  # type: ignore[attr-defined]
        yield test_client
    finally:
        db.close()
        config_module.get_settings.cache_clear()


def post_event(client, event: dict):
    return client.post("/webhooks/paypal", content=json.dumps(event), headers=SIGNED_HEADERS)


def orders(db) -> list[Order]:
    return list(db.scalars(select(Order)).all())


def actions(db) -> list[str]:
    return list(db.scalars(select(Event.action)).all())


def test_a_verified_capture_books_exactly_one_paid_order(client) -> None:
    response = post_event(client, capture_event())
    assert response.status_code == 200

    booked = orders(client.db)
    assert len(booked) == 1
    assert booked[0].status == "paid"
    assert booked[0].total == Decimal("297.00")
    assert booked[0].currency == "CAD"
    assert booked[0].external_ref == "paypal_capture_3C679366HH908993F"


def test_redelivering_the_same_capture_books_nothing_twice(client) -> None:
    """PayPal retries. A retry must not be a second sale."""
    first = post_event(client, capture_event())
    second = post_event(client, capture_event())

    assert first.status_code == second.status_code == 200
    assert second.json()["duplicate"] is True
    assert client.db.scalar(select(func.count()).select_from(Order)) == 1
    assert "order_event_duplicate_skipped" in actions(client.db)


def test_a_held_capture_is_not_revenue_and_promotes_when_it_completes(client) -> None:
    """PENDING books a pending order; the later COMPLETED promotes that same row."""
    post_event(client, capture_event(event_type="PAYMENT.CAPTURE.PENDING"))
    booked = orders(client.db)
    assert len(booked) == 1
    assert booked[0].status == "pending"

    post_event(client, capture_event(event_type=paypal.CAPTURE_COMPLETED))
    client.db.expire_all()
    booked = orders(client.db)
    assert len(booked) == 1, "the settling capture inserted a second order"
    assert booked[0].status == "paid"


def test_a_denied_capture_is_never_paid(client) -> None:
    post_event(client, capture_event(event_type="PAYMENT.CAPTURE.DENIED"))
    booked = orders(client.db)
    assert len(booked) == 1
    assert booked[0].status == "failed"


def test_approval_is_not_payment(client) -> None:
    """CHECKOUT.ORDER.APPROVED fires when the buyer clicks pay — before the money moves."""
    response = post_event(
        client, {"id": "WH-2", "event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": "5O1"}}
    )
    assert response.status_code == 200
    assert orders(client.db) == []
    assert "paypal_order_approved" in actions(client.db)


def test_a_capture_that_does_not_match_the_catalogue_is_paid_but_not_shippable(client) -> None:
    """Money arrived and cannot be un-received; what stops is fulfillment."""
    response = post_event(client, capture_event(value="1.00"))
    assert response.status_code == 200
    assert response.json()["fulfillment"] == "held_for_review"

    booked = orders(client.db)
    assert len(booked) == 1
    assert booked[0].status == "paid", "the payment is real and must stay on the books"
    assert booked[0].fulfillment_status == "unfulfillable"
    assert "paypal_capture_catalog_mismatch" in actions(client.db)


def test_a_capture_with_no_id_is_refused_because_it_cannot_be_deduplicated(client) -> None:
    event = capture_event()
    event["resource"].pop("id")
    response = post_event(client, event)
    assert response.status_code == 400
    assert orders(client.db) == []


def test_an_unverified_webhook_books_nothing(client, monkeypatch) -> None:
    monkeypatch.setattr(
        paypal,
        "verify_webhook",
        lambda payload, headers, **kwargs: {
            "verified": False,
            "event": json.loads(payload.decode()),
            "reason": "signature mismatch",
        },
    )
    response = post_event(client, capture_event())
    assert response.status_code == 400
    assert orders(client.db) == []
    assert "paypal_webhook_rejected" in actions(client.db)


# ── The customer-facing order endpoint ─────────────────────────────────────


def test_the_order_endpoint_prices_from_the_catalogue(client) -> None:
    response = client.post("/paypal/order", json={"items": [{"sku": SKU, "quantity": 1}]})
    assert response.status_code == 200
    assert response.json()["amount_total"] == SKU_CENTS
    assert response.json()["mode"] == "mock", "no credentials are set, so nothing left the process"


def test_the_order_endpoint_refuses_a_sku_the_business_does_not_sell(client) -> None:
    response = client.post(
        "/paypal/order", json={"items": [{"sku": "free-money", "quantity": 1}]}
    )
    assert response.status_code == 400
    assert "create_paypal_order" in actions(client.db), "the probe was not recorded"


def test_the_order_endpoint_refuses_a_recurring_cart(client) -> None:
    """Charging a subscription once would take one payment and never take another."""
    response = client.post(
        "/paypal/order", json={"items": [{"sku": "business-protection-monthly", "quantity": 1}]}
    )
    assert response.status_code == 400
    assert "recurring" in response.json()["detail"]


def test_the_order_request_contract_carries_no_price_field(client) -> None:
    """A line item that could name its own amount would let the browser choose what to pay."""
    schema = client.app.openapi()["components"]["schemas"]["CheckoutLineItem"]
    assert set(schema["properties"]) == {"sku", "quantity"}


def test_capturing_an_order_is_queued_for_approval_not_executed(client) -> None:
    response = client.post(
        "/paypal/capture",
        json={"paypal_order_id": "5O190127TN364715T"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["requires_approval"] is True
    assert body["status"] == "queued_for_approval"
