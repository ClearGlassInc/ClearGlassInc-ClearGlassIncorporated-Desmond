"""ClearGlass orders end to end: offer -> order -> Stripe | PayPal -> verified -> ledger.

Every test drives the real routes: signed Stripe events through
``/webhooks/stripe`` and verified PayPal events through ``/webhooks/paypal``,
then reads the result back through the order status, the admin view, the
cockpit and reconciliation. What they hold:

* the server names the price, and a checkout re-checks it;
* a browser return is not a payment; only a verified webhook makes ``PAID``;
* one order is paid once: a second checkout is refused, and a second payment
  that still arrives (Stripe *and* PayPal) is kept and flagged, never deleted,
  and never fulfilled twice;
* refunds and disputes move the order, and delivery work starts only from
  verified live money on an unflagged order;
* an approved PayPal capture now executes, once.
"""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

try:
    import os as _os

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    _os.environ.setdefault("DATABASE_URL", "sqlite://")
    from app.main import create_app
    from app.models import Approval, Base, CommercialOrder, Event, Lead, Order, ServiceOrder

    from app import commerce_orders, order_states, payments, paypal, pricebook, security
    from app import config as config_module
    from app import db as db_module
    _HAS_WEB_STACK = True
except (ImportError, RuntimeError):  # pragma: no cover - minimal env runs pure tests only
    _HAS_WEB_STACK = False

_SECRET = "whsec_test_commerce_orders"
_ADMIN_KEY = "test-admin-key-not-a-real-credential"
_PAYPAL_HEADERS = {
    "paypal-transmission-id": "b9d8f0a0-0000-11ef-9f1a-000000000000",
    "paypal-transmission-time": "2026-09-15T12:00:00Z",
    "paypal-transmission-sig": "c2lnbmF0dXJl",
    "paypal-cert-url": "https://api.paypal.com/v1/notifications/certs/CERT-abc",
    "paypal-auth-algo": "SHA256withRSA",
}
SKU = "risk-audit-90"            # CAD 297.00, one-time
MONTHLY = "business-protection-monthly"


@pytest.fixture()
def env(monkeypatch):
    if not _HAS_WEB_STACK:
        pytest.skip("fastapi/sqlalchemy not installed")
    monkeypatch.setattr(security, "_limiter", security.SlidingWindowLimiter())
    monkeypatch.setattr(payments, "_webhook_secret", lambda: _SECRET)
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    # Live PayPal base: verified PayPal events are booked as live money.
    monkeypatch.setenv("PAYPAL_API_BASE", "https://api-m.paypal.com")
    config_module.get_settings.cache_clear()
    pricebook.reload()

    def accept(payload, headers, **kwargs):
        return {"verified": True, "event": json.loads(payload.decode()), "reason": "ok"}

    monkeypatch.setattr(paypal, "verify_webhook", accept)

    engine = create_engine(
        "sqlite://", future=True,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_session():
        session = Factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[db_module.get_session] = override_session
    yield TestClient(app, raise_server_exceptions=False), Factory
    config_module.get_settings.cache_clear()
    pricebook.reload()


# --- helpers ------------------------------------------------------------------------


def _new_order(client, sku: str = SKU, **body) -> dict:
    response = client.post("/commerce/orders", json={"sku": sku, **body})
    assert response.status_code == 201, response.text
    return response.json()


def _checkout(client, ref: str, provider: str = "stripe", email: str = "buyer@example.com"):
    return client.post(f"/commerce/orders/{ref}/checkout", json={"provider": provider, "customer_email": email})


def _stripe(client, etype: str, obj: dict, *, livemode: bool = True, sign: bool = True):
    body = json.dumps({"id": f"evt_{obj.get('id')}_{etype}", "type": etype, "livemode": livemode,
                       "data": {"object": obj}}).encode()
    headers = {"stripe-signature": payments.sign_payload(body, _SECRET)} if sign else {}
    return client.post("/webhooks/stripe", content=body, headers=headers)


def _stripe_paid(client, ref: str, *, amount: int = 29700, session_id: str = "cs_live_1",
                 intent: str = "pi_1", livemode: bool = True, **extra):
    obj = {
        "id": session_id, "payment_intent": intent, "payment_status": "paid",
        "amount_total": amount, "currency": "cad",
        "customer_details": {"email": "buyer@example.com"},
        "metadata": {"cg_order_ref": ref, **extra.pop("metadata", {})}, **extra,
    }
    response = _stripe(client, "checkout.session.completed", obj, livemode=livemode)
    assert response.status_code == 200, response.text
    return response


def _paypal(client, event: dict):
    response = client.post("/webhooks/paypal", content=json.dumps(event), headers=_PAYPAL_HEADERS)
    assert response.status_code == 200, response.text
    return response


def _paypal_capture(client, ref: str, *, capture_id: str = "3C679366HH908993F", value: str = "297.00"):
    return _paypal(client, {
        "id": f"WH-{capture_id}",
        "event_type": paypal.CAPTURE_COMPLETED,
        "resource": {
            "id": capture_id, "status": "COMPLETED", "custom_id": f"{SKU}x1", "invoice_id": ref,
            "amount": {"currency_code": "CAD", "value": value},
        },
    })


def _status(client, ref: str) -> dict:
    response = client.get(f"/commerce/orders/{ref}/status")
    assert response.status_code == 200, response.text
    return response.json()


def _admin(client, ref: str) -> dict:
    response = client.get(f"/commerce/orders/{ref}")
    assert response.status_code == 200, response.text
    return response.json()


def _count(Factory, model) -> int:
    with Factory() as s:
        return len(s.scalars(select(model)).all())


def _actions(Factory) -> list[str]:
    with Factory() as s:
        return [e.action for e in s.scalars(select(Event).order_by(Event.id)).all()]


# --- the order and its price ---------------------------------------------------------


def test_an_order_is_priced_by_the_server_not_the_request(env) -> None:
    client, Factory = env
    response = client.post("/commerce/orders", json={"sku": SKU, "amount": 1, "price": "0.01"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert order_states.is_order_ref(body["order_ref"])
    assert body["amount"] == 297.0 and body["currency"] == "CAD"
    assert body["payment_state"] == "CREATED"
    assert body["providers"] == ["stripe", "paypal"]
    with Factory() as s:
        assert s.scalar(select(CommercialOrder)).amount == Decimal("297.00")


def test_unknown_offers_are_refused(env) -> None:
    client, Factory = env
    assert client.post("/commerce/orders", json={"sku": "no-such-offer"}).status_code == 400
    assert _count(Factory, CommercialOrder) == 0


def test_subscriptions_are_card_only(env) -> None:
    client, _ = env
    order = _new_order(client, MONTHLY)
    assert order["providers"] == ["stripe"]
    assert _checkout(client, order["order_ref"], "paypal").status_code == 400


def test_a_lead_link_needs_the_leads_own_email_and_its_campaign_wins(env) -> None:
    client, Factory = env
    with Factory() as s:
        lead = Lead(full_name="B", email="buyer@example.com", service_interest="audit",
                    utm_last_source="linkedin", utm_last_medium="social",
                    utm_last_campaign="CG-LINKEDIN-SECURITY-QUICKAUDIT-2026-Q4")
        s.add(lead)
        s.commit()
        reference = str(lead.public_ref)

    forged = {"utm_source": "google", "utm_campaign": "CG-GOOGLE-SMB-AUDIT-2026-Q4"}
    wrong = client.post("/commerce/orders", json={"sku": SKU, "reference": reference,
                                                  "customer_email": "other@example.com"})
    assert wrong.status_code == 403
    order = _new_order(client, reference=reference, customer_email="Buyer@Example.com", attribution=forged)
    view = _admin(client, order["order_ref"])
    assert view["utm_campaign"] == "CG-LINKEDIN-SECURITY-QUICKAUDIT-2026-Q4"
    assert view["lead_id"] is not None


def test_status_is_public_and_leaks_nothing(env) -> None:
    client, _ = env
    order = _new_order(client)
    _checkout(client, order["order_ref"])
    status = _status(client, order["order_ref"])
    assert set(status) == {"order_ref", "offer", "amount", "currency", "provider", "payment_state",
                           "payment_verified", "fulfillment_state", "state"}
    assert "buyer@example.com" not in json.dumps(status)
    assert client.get("/commerce/orders/CG-ORD-2026-ZZZZZZZZ/status").status_code == 404
    assert client.get("/commerce/orders/not-a-ref/status").status_code == 404


# --- checkout ------------------------------------------------------------------------


def test_stripe_checkout_carries_the_order_ref_and_is_idempotent_per_buyer(env, monkeypatch) -> None:
    client, _ = env
    sent: list[dict] = []

    def fake(line_items, **kwargs):
        sent.append({"line_items": line_items, **kwargs})
        return {"id": "cs_test_1", "url": "https://checkout.example/1", "mode": "mock",
                "checkout_mode": "payment", "amount_total": 29700, "currency": "cad"}

    monkeypatch.setattr(payments, "create_checkout_session", fake)
    order = _new_order(client)
    ref = order["order_ref"]
    first = _checkout(client, ref)
    again = _checkout(client, ref)
    assert first.status_code == again.status_code == 200
    assert sent[0]["client_reference_id"] == ref
    assert sent[0]["extra_metadata"]["cg_order_ref"] == ref
    assert sent[0]["idempotency_key"] == sent[1]["idempotency_key"]
    assert sent[0]["line_items"][0]["amount"] == 29700
    assert _status(client, ref)["payment_state"] == "CHECKOUT_STARTED"


def test_paypal_checkout_carries_the_order_ref_as_invoice_id(env, monkeypatch) -> None:
    client, _ = env
    sent: dict = {}

    def fake(line_items, **kwargs):
        sent.update(kwargs)
        return {"id": "5O190127TN364715T", "approve_url": "https://paypal.example/approve",
                "mode": "mock", "status": "CREATED", "amount_total": 29700, "currency": "CAD"}

    monkeypatch.setattr(paypal, "create_order", fake)
    ref = _new_order(client)["order_ref"]
    response = _checkout(client, ref, "paypal")
    assert response.status_code == 200, response.text
    assert response.json()["url"] == "https://paypal.example/approve"
    assert sent["invoice_id"] == ref
    assert _admin(client, ref)["provider_checkout_ref"] == "5O190127TN364715T"


def test_the_paypal_request_body_names_the_order(env) -> None:
    """The real adapter puts the reference where PayPal echoes it on the capture."""
    calls = []

    def transport(method, path, body=None, headers=None):
        calls.append(body)
        if path == "/v1/oauth2/token":
            return 200, {"access_token": "t", "expires_in": 100}
        return 201, {"id": "PP-1", "status": "CREATED", "links": [{"rel": "payer-action", "href": "https://p/1"}]}

    settings = config_module.Settings(paypal_client_id="id", paypal_client_secret="secret")
    items, _ = pricebook.resolve_line_items([{"sku": SKU, "quantity": 1}])
    paypal.create_order(items, invoice_id="CG-ORD-2026-ABCDEFGH", settings=settings, request=transport)
    unit = calls[-1]["purchase_units"][0]
    assert unit["invoice_id"] == "CG-ORD-2026-ABCDEFGH"
    assert unit["amount"]["value"] == "297.00"


def test_a_changed_price_refuses_checkout_instead_of_charging_it(env, monkeypatch, tmp_path) -> None:
    client, _ = env
    ref = _new_order(client)["order_ref"]
    document = json.loads(pricebook.DEFAULT_PRICEBOOK.read_text())
    for offer in document["offers"]:
        if offer["sku"] == SKU:
            offer["amount"] = 39700
    changed = tmp_path / "pricebook.json"
    changed.write_text(json.dumps(document))
    monkeypatch.setenv("PRICEBOOK_PATH", str(changed))
    pricebook.reload()
    response = _checkout(client, ref)
    assert response.status_code == 409
    assert "price" in response.json()["detail"]


def test_a_stripe_failure_is_a_clean_refusal_not_a_500(env, monkeypatch) -> None:
    client, Factory = env

    def broken(line_items, **kwargs):
        raise RuntimeError("stripe unavailable")

    monkeypatch.setattr(payments, "create_checkout_session", broken)
    ref = _new_order(client)["order_ref"]
    response = _checkout(client, ref)
    assert response.status_code == 502
    assert _status(client, ref)["payment_state"] == "CREATED"
    assert "checkout_start_failed" in _actions(Factory)


def test_a_malformed_email_is_refused(env) -> None:
    client, _ = env
    ref = _new_order(client)["order_ref"]
    assert _checkout(client, ref, email="not an email").status_code == 422


# --- verification: a redirect is not a payment -------------------------------------


def test_returning_from_checkout_is_not_payment(env) -> None:
    client, _ = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref)
    status = _status(client, ref)
    assert status["payment_verified"] is False
    assert status["payment_state"] == "CHECKOUT_STARTED"


def test_a_verified_live_stripe_payment_pays_the_order_and_opens_delivery(env) -> None:
    client, Factory = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref)
    _stripe_paid(client, ref)

    status = _status(client, ref)
    assert status["payment_verified"] is True
    assert status["payment_state"] == "PAID"
    assert status["fulfillment_state"] == "FULFILLMENT_PENDING"
    assert status["provider"] == "stripe"
    assert _count(Factory, ServiceOrder) == 1
    assert "operator_action_required" in _actions(Factory)
    with Factory() as s:
        payment = s.scalar(select(Order))
        assert payment.order_ref == ref and payment.environment == "live"


def test_an_unsigned_stripe_event_cannot_pay_an_order(env, monkeypatch) -> None:
    """With no webhook secret (dev), the ledger records what it is told; the order does not move."""
    client, Factory = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref)
    monkeypatch.setattr(payments, "_webhook_secret", lambda: "")
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    _stripe_paid(client, ref)
    assert _status(client, ref)["payment_state"] == "CHECKOUT_STARTED"
    assert "unverified_payment_not_applied" in _actions(Factory)
    assert _count(Factory, ServiceOrder) == 0


def test_a_forged_stripe_signature_is_refused(env) -> None:
    client, _ = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref)
    body = json.dumps({"id": "evt_x", "type": "checkout.session.completed", "livemode": True,
                       "data": {"object": {"id": "cs_x", "payment_status": "paid", "amount_total": 29700,
                                           "currency": "cad", "metadata": {"cg_order_ref": ref}}}}).encode()
    forged = client.post("/webhooks/stripe", content=body,
                         headers={"stripe-signature": payments.sign_payload(body, "whsec_wrong")})
    assert forged.status_code == 400
    assert _status(client, ref)["payment_state"] == "CHECKOUT_STARTED"


def test_a_test_mode_payment_is_verified_but_opens_no_delivery(env) -> None:
    client, Factory = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref)
    _stripe_paid(client, ref, session_id="cs_test_1", intent="pi_test", livemode=False)
    view = _admin(client, ref)
    assert view["payment_state"] == "PAID" and view["environment"] == "test"
    assert view["fulfillment_state"] == "NOT_STARTED"
    assert _count(Factory, ServiceOrder) == 0
    cockpit = client.get("/revenue/cockpit").json()
    assert cockpit["confirmed_revenue_cad"] == 0.0     # test money is never revenue


def test_redelivery_changes_nothing(env) -> None:
    client, Factory = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref)
    _stripe_paid(client, ref)
    _stripe_paid(client, ref)
    assert _count(Factory, Order) == 1
    assert _count(Factory, ServiceOrder) == 1
    assert _admin(client, ref)["reconciliation_required"] is False


def test_async_payment_is_processing_until_it_settles(env) -> None:
    client, _ = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref)
    _stripe_paid(client, ref, payment_status="unpaid")
    assert _status(client, ref)["payment_state"] == "PAYMENT_PROCESSING"
    assert _checkout(client, ref).status_code == 409      # in flight: no second checkout
    _stripe(client, "checkout.session.async_payment_succeeded", {
        "id": "cs_live_1", "payment_intent": "pi_1", "payment_status": "paid", "amount_total": 29700,
        "currency": "cad", "metadata": {"cg_order_ref": ref},
    })
    assert _status(client, ref)["payment_state"] == "PAID"


# --- one order, one payment ---------------------------------------------------------


def test_a_paid_order_refuses_a_second_checkout(env) -> None:
    client, _ = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref)
    _stripe_paid(client, ref)
    for provider in ("stripe", "paypal"):
        response = _checkout(client, ref, provider)
        assert response.status_code == 409
        assert "already been paid" in response.json()["detail"]


def test_stripe_and_paypal_both_paying_is_flagged_not_deleted_or_fulfilled_twice(env) -> None:
    client, Factory = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref, "stripe")
    _checkout(client, ref, "paypal")        # buyer switched processor before paying
    _stripe_paid(client, ref)
    _paypal_capture(client, ref)

    assert _count(Factory, Order) == 2                   # both payments kept
    assert _count(Factory, ServiceOrder) == 1            # delivered once
    view = _admin(client, ref)
    assert view["reconciliation_required"] is True
    assert "DUPLICATE_PAYMENT" in view["reconciliation_reason"]
    assert view["fulfillment_state"] == "HELD"
    assert {p["provider"] for p in view["payments"]} == {"stripe", "paypal"}

    cockpit = client.get("/revenue/cockpit").json()
    assert cockpit["reconciliation_required"] == 1
    by_provider = {row["provider"]: row for row in cockpit["revenue_by_provider"]}
    assert by_provider["stripe"]["confirmed_revenue_cad"] == 297.0
    assert by_provider["paypal"]["confirmed_revenue_cad"] == 297.0
    assert cockpit["confirmed_revenue_cad"] == 594.0     # both really arrived; nothing hidden

    report = client.post("/commerce/reconciliation", json={}).json()["data"]
    codes = {f["code"]: f for f in report["findings"]}
    assert codes["DUPLICATE_PAYMENT"]["severity"] == "critical"
    assert codes["DUPLICATE_PAYMENT"]["providers"] == ["paypal", "stripe"]
    assert report["clean"] is False

    # Refunding the duplicate at PayPal is recorded against it; the order stays PAID and flagged.
    _paypal(client, {
        "id": "WH-REFUND", "event_type": "PAYMENT.CAPTURE.REFUNDED",
        "resource": {"id": "RF1", "status": "COMPLETED", "amount": {"currency_code": "CAD", "value": "297.00"},
                     "links": [{"rel": "up", "href": "https://api.paypal.com/v2/payments/captures/3C679366HH908993F"}]},
    })
    view = _admin(client, ref)
    assert view["payment_state"] == "PAID"
    assert view["reconciliation_required"] is True
    assert "duplicate_payment_adjusted" in _actions(Factory)


def test_an_underpayment_is_flagged_and_holds_delivery(env) -> None:
    client, Factory = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref)
    _stripe_paid(client, ref, amount=100)
    view = _admin(client, ref)
    assert view["payment_state"] == "PAID"
    assert "AMOUNT_MISMATCH" in view["reconciliation_reason"]
    assert view["fulfillment_state"] == "HELD"
    assert _count(Factory, ServiceOrder) == 0
    assert "fulfillment_held" in _actions(Factory)


def test_a_payment_for_an_unknown_order_is_booked_and_flagged(env) -> None:
    client, Factory = env
    _stripe_paid(client, "CG-ORD-2026-ZZZZZZZZ")
    assert _count(Factory, Order) == 1                    # the money is real
    assert "payment_for_unknown_order" in _actions(Factory)
    report = client.post("/commerce/reconciliation", json={}).json()["data"]
    assert "UNKNOWN_ORDER_REF" in {f["code"] for f in report["findings"]}


def test_a_malformed_order_ref_in_metadata_is_ignored(env) -> None:
    client, Factory = env
    _stripe_paid(client, "CG-ORD-2026-<script>")
    with Factory() as s:
        assert s.scalar(select(Order)).order_ref is None


# --- refunds and disputes ------------------------------------------------------------


@pytest.mark.parametrize(
    ("etype", "obj", "expected"),
    [
        ("charge.refunded", {"amount_refunded": 29700, "refunded": True}, "REFUNDED"),
        ("charge.refunded", {"amount_refunded": 9700, "refunded": False}, "PARTIALLY_REFUNDED"),
        ("charge.dispute.created", {"status": "needs_response"}, "DISPUTED"),
    ],
)
def test_refunds_and_disputes_move_the_order(env, etype, obj, expected) -> None:
    client, _ = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref)
    _stripe_paid(client, ref)
    _stripe(client, etype, {"id": "ch_1", "payment_intent": "pi_1", "currency": "cad", **obj})
    assert _status(client, ref)["payment_state"] == expected


def test_a_dispute_that_is_lost_is_a_chargeback_and_one_that_is_won_is_paid_again(env) -> None:
    client, _ = env
    for outcome, expected in (("won", "PAID"), ("lost", "CHARGEBACK")):
        ref = _new_order(client)["order_ref"]
        _checkout(client, ref)
        intent = f"pi_{outcome}"
        _stripe_paid(client, ref, session_id=f"cs_{outcome}", intent=intent)
        _stripe(client, "charge.dispute.created", {"id": f"dp_{outcome}", "payment_intent": intent,
                                                    "status": "needs_response"})
        _stripe(client, "charge.dispute.closed", {"id": f"dp_{outcome}", "payment_intent": intent,
                                                   "status": outcome})
        status = _status(client, ref)
        assert status["payment_state"] == expected
        if expected == "PAID":
            assert status["fulfillment_state"] == "FULFILLMENT_PENDING"


# --- PayPal approval and capture -----------------------------------------------------


def _approved(ref: str, paypal_order_id: str = "5O190127TN364715T") -> dict:
    return {
        "id": f"WH-APPROVED-{paypal_order_id}",
        "event_type": "CHECKOUT.ORDER.APPROVED",
        "resource": {"id": paypal_order_id, "status": "APPROVED",
                     "purchase_units": [{"invoice_id": ref, "custom_id": f"{SKU}x1"}]},
    }


def test_buyer_approval_queues_one_capture_approval(env) -> None:
    client, Factory = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref, "paypal")
    _paypal(client, _approved(ref))
    _paypal(client, _approved(ref))           # redelivered
    assert _status(client, ref)["payment_state"] == "PAYMENT_PENDING"
    with Factory() as s:
        approvals = s.scalars(select(Approval).where(Approval.action == "paypal_capture_order")).all()
    assert len(approvals) == 1
    assert approvals[0].status == "pending"
    assert approvals[0].payload["order_ref"] == ref


def test_an_approved_capture_executes_exactly_once(env, monkeypatch) -> None:
    client, Factory = env
    captured: list[str] = []

    def fake_capture(order_id, **kwargs):
        captured.append(order_id)
        return {"id": order_id, "status": "COMPLETED", "mode": "mock", "captures": [{"id": "CAP-1"}]}

    monkeypatch.setattr(paypal, "capture_order", fake_capture)
    body = {"paypal_order_id": "5O190127TN364715T"}

    first = client.post("/paypal/capture", json=body).json()
    assert first["status"] == "queued_for_approval" and captured == []
    repeat = client.post("/paypal/capture", json=body).json()
    assert repeat["approval_id"] == first["approval_id"]          # no pile-up of pending rows
    assert captured == []

    decision = client.post(f"/approvals/{first['approval_id']}/approve", json={"note": "ok"})
    assert decision.status_code == 200, decision.text
    executed = client.post("/paypal/capture", json=body).json()
    assert executed["status"] == "executed"
    assert captured == ["5O190127TN364715T"]

    again = client.post("/paypal/capture", json=body).json()
    assert again["status"] == "queued_for_approval"               # the approval was single-use
    assert captured == ["5O190127TN364715T"]
    assert "paypal_capture_executed" in _actions(Factory)


def test_a_queued_capture_is_refused_once_the_order_is_paid_another_way(env, monkeypatch) -> None:
    """Stripe tab left open, PayPal approved, then the Stripe tab completes."""
    client, Factory = env
    captured: list[str] = []
    monkeypatch.setattr(paypal, "capture_order", lambda order_id, **kw: captured.append(order_id) or {
        "id": order_id, "status": "COMPLETED", "mode": "mock", "captures": []})
    monkeypatch.setattr(paypal, "create_order", lambda items, **kw: {
        "id": "PP-SWITCH-1", "approve_url": "https://paypal.example/a", "mode": "mock",
        "status": "CREATED", "amount_total": 29700, "currency": "CAD"})
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref, "stripe")
    _checkout(client, ref, "paypal")
    _paypal(client, _approved(ref, "PP-SWITCH-1"))
    _stripe_paid(client, ref)                              # the Stripe tab completes
    assert _status(client, ref)["payment_state"] == "PAID"

    with Factory() as s:
        approval_id = s.scalar(select(Approval.id).where(Approval.target == "PP-SWITCH-1"))
    client.post(f"/approvals/{approval_id}/approve", json={"note": "ok"})
    response = client.post("/paypal/capture", json={"paypal_order_id": "PP-SWITCH-1"})
    assert response.status_code == 409
    assert "charge the buyer twice" in response.json()["detail"]
    assert captured == []
    assert "paypal_capture_refused" in _actions(Factory)


def test_a_verified_paypal_capture_pays_the_order(env) -> None:
    client, Factory = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref, "paypal")
    _paypal(client, _approved(ref))
    _paypal_capture(client, ref)
    status = _status(client, ref)
    assert status["payment_state"] == "PAID" and status["provider"] == "paypal"
    assert status["fulfillment_state"] == "FULFILLMENT_PENDING"
    with Factory() as s:
        service = s.scalar(select(ServiceOrder))
        assert service.sku == SKU


# --- operator actions and access ------------------------------------------------------


def test_only_unpaid_orders_can_be_canceled(env) -> None:
    client, _ = env
    open_ref = _new_order(client)["order_ref"]
    assert client.post(f"/commerce/orders/{open_ref}/cancel").status_code == 200
    assert _status(client, open_ref)["payment_state"] == "CANCELED"
    assert _checkout(client, open_ref).status_code == 409

    paid_ref = _new_order(client)["order_ref"]
    _checkout(client, paid_ref)
    _stripe_paid(client, paid_ref)
    assert client.post(f"/commerce/orders/{paid_ref}/cancel").status_code == 409
    assert _status(client, paid_ref)["payment_state"] == "PAID"


def test_money_after_a_cancel_is_recorded_and_flagged(env) -> None:
    client, _ = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref)
    client.post(f"/commerce/orders/{ref}/cancel")
    _stripe_paid(client, ref)
    view = _admin(client, ref)
    assert view["payment_state"] == "PAID"
    assert "PAID_AFTER_CANCEL" in view["reconciliation_reason"]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/commerce/orders"),
        ("get", "/commerce/orders/{ref}"),
        ("post", "/commerce/orders/{ref}/cancel"),
        ("post", "/commerce/reconciliation"),
    ],
)
def test_operator_routes_need_the_admin_credential(env, monkeypatch, method, path) -> None:
    client, _ = env
    ref = _new_order(client)["order_ref"]
    monkeypatch.setenv("ADMIN_API_KEY", _ADMIN_KEY)
    config_module.get_settings.cache_clear()
    url = path.format(ref=ref)
    kwargs = {"json": {}} if method == "post" else {}
    assert getattr(client, method)(url, **kwargs).status_code == 401
    authorised = getattr(client, method)(url, headers={"Authorization": f"Bearer {_ADMIN_KEY}"}, **kwargs)
    assert authorised.status_code == 200, authorised.text
    # The buyer's own status page stays public.
    assert client.get(f"/commerce/orders/{ref}/status").status_code == 200


@pytest.mark.parametrize("path", ["/payouts", "/payments/payout-account"])
def test_settlement_records_need_the_admin_credential(env, monkeypatch, path) -> None:
    """Payout amounts and masked bank details were readable by anyone."""
    client, _ = env
    monkeypatch.setenv("ADMIN_API_KEY", _ADMIN_KEY)
    config_module.get_settings.cache_clear()
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": f"Bearer {_ADMIN_KEY}"}).status_code == 200


def test_the_crcs_first_offer_checkout_books_against_a_clearglass_order(env, monkeypatch) -> None:
    client, Factory = env
    monkeypatch.setenv("CRCS_RAPID_DIAGNOSTIC_ENABLED", "true")
    config_module.get_settings.cache_clear()
    sent: dict = {}

    def fake(line_items, **kwargs):
        sent.update(kwargs)
        return {"id": "cs_live_crcs", "url": "https://checkout.example/c", "mode": "mock",
                "checkout_mode": "payment", "amount_total": 12500, "currency": "cad"}

    monkeypatch.setattr(payments, "create_checkout_session", fake)
    response = client.post("/revenue/checkout", json={"customer_email": "walkin@example.com"})
    assert response.status_code == 200, response.text
    ref = response.json()["order_ref"]
    assert sent["extra_metadata"]["cg_order_ref"] == ref
    assert _status(client, ref)["payment_state"] == "CHECKOUT_STARTED"

    _stripe_paid(client, ref, amount=12500, session_id="cs_live_crcs", intent="pi_crcs",
                 metadata={"crcs_revenue_system": "v1", "crcs_sku": "rapid-website-deployment-diagnostic",
                           "crcs_lead_id": ""})
    assert _status(client, ref)["payment_state"] == "PAID"
    assert _count(Factory, ServiceOrder) == 1                    # provisioned once, not twice
    assert [a for a in _actions(Factory) if a == "checkout_started"] == ["checkout_started"]


def test_checkout_count_reaches_the_cockpit(env) -> None:
    client, _ = env
    ref = _new_order(client)["order_ref"]
    _checkout(client, ref)
    cockpit = client.get("/revenue/cockpit").json()
    assert cockpit["checkout_started_30d"] == 1
    assert cockpit["commercial_orders_by_state"] == {"CHECKOUT_STARTED": 1}


def test_commerce_orders_module_names_providers_consistently() -> None:
    if not _HAS_WEB_STACK:
        pytest.skip("fastapi/sqlalchemy not installed")
    assert commerce_orders.provider_for_source("stripe_checkout") == "stripe"
    assert commerce_orders.provider_for_source("stripe_subscription") == "stripe"
    assert commerce_orders.provider_for_source("paypal_orders") == "paypal"
    assert commerce_orders.provider_for_source(None) == "other"
