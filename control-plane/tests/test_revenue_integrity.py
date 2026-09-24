"""Money that leaves must leave the revenue figure too.

Before migration 009, ``charge.refunded`` and ``charge.dispute.*`` were written
to the audit ledger and nothing else. The order stayed ``paid``, and the CRCS
cockpit counted every live ``paid`` order as confirmed revenue, so a refunded
or charged-back sale kept being reported as money the business had. A
redelivered ``checkout.session.completed`` could also have promoted a refunded
order back to ``paid``.

These drive signed Stripe events through ``/webhooks/stripe`` and read the
result back from the cockpit, the same path the owner sees. They also cover
two paths the CRCS design package listed as untested: checkout-webhook
redelivery, and the rule that only a verified *live* payment opens delivery
work.
"""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

try:
    import os as _os

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, select
    from sqlalchemy import text as sa_text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    _os.environ.setdefault("DATABASE_URL", "sqlite://")
    from app.main import create_app
    from app.models import Base, Event, Lead, Order, ServiceOrder

    from app import attribution, payments, security
    from app import config as config_module
    from app import db as db_module
    _HAS_WEB_STACK = True
except (ImportError, RuntimeError):  # pragma: no cover - minimal env runs pure tests only
    _HAS_WEB_STACK = False

_SECRET = "whsec_test_revenue_integrity"
_MONTHLY_PRICE = "price_1U0wlFL8uR92FksUG6ZT87rG"   # business-protection-monthly, CAD 100
_ANNUAL_PRICE = "price_1U0wlOL8uR92FksUJjFEMvGT"    # business-protection-annual, CAD 1,000


@pytest.fixture()
def env(monkeypatch):
    if not _HAS_WEB_STACK:
        pytest.skip("fastapi/sqlalchemy not installed")
    monkeypatch.setattr(security, "_limiter", security.SlidingWindowLimiter())
    monkeypatch.setattr(payments, "_webhook_secret", lambda: _SECRET)
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)   # open dev mode for the cockpit
    monkeypatch.delenv("CRCS_RAPID_DIAGNOSTIC_ENABLED", raising=False)
    config_module.get_settings.cache_clear()

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
    yield TestClient(app, raise_server_exceptions=False), Factory, engine
    config_module.get_settings.cache_clear()


def _send(client, etype: str, obj: dict, *, livemode: bool = True, event_id: str = "evt_1"):
    body = json.dumps({"id": event_id, "type": etype, "livemode": livemode, "data": {"object": obj}}).encode()
    response = client.post(
        "/webhooks/stripe",
        content=body,
        headers={"stripe-signature": payments.sign_payload(body, _SECRET)},
    )
    assert response.status_code == 200, response.text
    return response


def _paid_session(**overrides) -> dict:
    session = {
        "id": "cs_live_1",
        "payment_intent": "pi_1",
        "payment_status": "paid",
        "amount_total": 12500,
        "currency": "cad",
        "customer_details": {"email": "buyer@example.com"},
        "metadata": {},
    }
    session.update(overrides)
    return session


def _orders(Factory) -> list:
    with Factory() as s:
        return list(s.scalars(select(Order)).all())


def _actions(Factory) -> list[str]:
    with Factory() as s:
        return [e.action for e in s.scalars(select(Event).order_by(Event.id)).all()]


def _cockpit(client) -> dict:
    response = client.get("/revenue/cockpit")
    assert response.status_code == 200, response.text
    return response.json()


# ── Redelivery and live-only provisioning ──────────────────────────────────────

def test_redelivered_checkout_books_one_order(env) -> None:
    client, Factory, _ = env
    _send(client, "checkout.session.completed", _paid_session(), event_id="evt_a")
    _send(client, "checkout.session.completed", _paid_session(), event_id="evt_a_retry")
    orders = _orders(Factory)
    assert len(orders) == 1
    assert orders[0].payment_intent == "pi_1"
    assert "order_event_duplicate_skipped" in _actions(Factory)
    assert _cockpit(client)["confirmed_revenue_cad"] == 125.0


def _crcs_session(lead_id: int, **overrides) -> dict:
    return _paid_session(metadata={
        "crcs_revenue_system": "v1",
        "crcs_sku": "rapid-website-deployment-diagnostic",
        "crcs_lead_id": str(lead_id),
    }, **overrides)


def _make_lead(Factory) -> int:
    with Factory() as s:
        lead = Lead(full_name="Buyer", email="buyer@example.com", service_interest="Rapid Diagnostic",
                    utm_last_source="linkedin", utm_last_medium="social",
                    utm_last_campaign="CG-LINKEDIN-SMB-DIAGNOSTIC-2026-Q4")
        s.add(lead)
        s.commit()
        return lead.id


def test_only_a_live_payment_opens_delivery_work(env) -> None:
    """A test-mode payment exercises the ledger but commits no one to delivery."""
    client, Factory, _ = env
    lead_id = _make_lead(Factory)

    _send(client, "checkout.session.completed", _crcs_session(lead_id, id="cs_test_x", payment_intent="pi_test"),
          livemode=False, event_id="evt_test")
    with Factory() as s:
        assert s.scalars(select(ServiceOrder)).all() == []

    _send(client, "checkout.session.completed", _crcs_session(lead_id), event_id="evt_live")
    _send(client, "checkout.session.completed", _crcs_session(lead_id), event_id="evt_live_retry")
    with Factory() as s:
        services = s.scalars(select(ServiceOrder)).all()
        assert len(services) == 1, "a redelivered payment must not open a second delivery"
        assert services[0].lead_id == lead_id
        assert s.get(Lead, lead_id).stage == "CUSTOMER_ACTIVE"


# ── Refunds ────────────────────────────────────────────────────────────────────

def _charge(amount_refunded: int, refunded: bool, **overrides) -> dict:
    charge = {"id": "ch_1", "payment_intent": "pi_1", "amount": 12500,
              "amount_refunded": amount_refunded, "refunded": refunded, "currency": "cad"}
    charge.update(overrides)
    return charge


def test_a_full_refund_leaves_confirmed_revenue(env) -> None:
    client, Factory, _ = env
    _send(client, "checkout.session.completed", _paid_session())
    _send(client, "charge.refunded", _charge(12500, True), event_id="evt_r")

    [order] = _orders(Factory)
    assert order.status == "refunded"
    assert Decimal(order.amount_refunded) == Decimal("125.00")
    cockpit = _cockpit(client)
    assert cockpit["gross_revenue_cad"] == 125.0
    assert cockpit["refunded_cad"] == 125.0
    assert cockpit["confirmed_revenue_cad"] == 0.0
    # The existing audit vocabulary is kept alongside the ledger change.
    assert {"refund_settled", "order_refunded"} <= set(_actions(Factory))


def test_partial_refunds_are_cumulative_and_redelivery_does_not_subtract_twice(env) -> None:
    client, Factory, _ = env
    _send(client, "checkout.session.completed", _paid_session())
    _send(client, "charge.refunded", _charge(2500, False), event_id="evt_r1")
    _send(client, "charge.refunded", _charge(2500, False), event_id="evt_r1_retry")
    assert _cockpit(client)["confirmed_revenue_cad"] == 100.0
    [order] = _orders(Factory)
    assert order.status == "paid", "a partial refund leaves the sale in place"
    assert "refund_duplicate_skipped" in _actions(Factory)

    _send(client, "charge.refunded", _charge(7500, False), event_id="evt_r2")
    assert _cockpit(client)["confirmed_revenue_cad"] == 50.0


def test_a_late_settlement_event_cannot_revive_a_refunded_order(env) -> None:
    client, Factory, _ = env
    _send(client, "checkout.session.completed", _paid_session())
    _send(client, "charge.refunded", _charge(12500, True), event_id="evt_r")
    _send(client, "checkout.session.completed", _paid_session(), event_id="evt_late")
    [order] = _orders(Factory)
    assert order.status == "refunded"
    assert "order_event_after_refund_skipped" in _actions(Factory)
    assert _cockpit(client)["confirmed_revenue_cad"] == 0.0


def test_a_refund_with_no_matching_order_is_flagged_not_dropped(env) -> None:
    client, Factory, _ = env
    _send(client, "charge.refunded", _charge(5000, False, payment_intent="pi_unknown"))
    assert _orders(Factory) == []
    assert "refund_unmatched" in _actions(Factory)


# ── Disputes ───────────────────────────────────────────────────────────────────

def _dispute(status: str) -> dict:
    return {"id": "dp_1", "charge": "ch_1", "payment_intent": "pi_1", "amount": 12500,
            "currency": "cad", "status": status, "reason": "fraudulent"}


@pytest.mark.parametrize(
    ("final_status", "confirmed", "disputed_open", "dispute_lost"),
    [("won", 125.0, 0.0, 0.0), ("lost", 0.0, 0.0, 125.0)],
)
def test_disputed_money_is_held_out_until_the_dispute_is_won(
    env, final_status, confirmed, disputed_open, dispute_lost,
) -> None:
    client, Factory, _ = env
    _send(client, "checkout.session.completed", _paid_session())
    _send(client, "charge.dispute.created", _dispute("needs_response"), event_id="evt_d1")
    open_state = _cockpit(client)
    assert open_state["confirmed_revenue_cad"] == 0.0
    assert open_state["disputed_open_cad"] == 125.0

    _send(client, "charge.dispute.closed", _dispute(final_status), event_id="evt_d2")
    closed = _cockpit(client)
    assert closed["confirmed_revenue_cad"] == confirmed
    assert closed["disputed_open_cad"] == disputed_open
    assert closed["dispute_lost_cad"] == dispute_lost


def test_test_mode_money_never_reaches_confirmed_revenue(env) -> None:
    client, _, _ = env
    _send(client, "checkout.session.completed", _paid_session(id="cs_test_1", payment_intent="pi_t"),
          livemode=False)
    cockpit = _cockpit(client)
    assert cockpit["confirmed_revenue_cad"] == 0.0
    assert cockpit["test_revenue_cad"] == 125.0


# ── Attribution ────────────────────────────────────────────────────────────────

def test_attribution_is_cleaned_before_it_reaches_stripe() -> None:
    raw = {"utm_source": "linkedin", "utm_medium": "paid social",   # space: dropped
           "utm_campaign": "CG-LINKEDIN-SMB-DIAGNOSTIC-2026-Q4", "email": "a@b.c"}  # unknown key: dropped
    assert attribution.to_metadata(raw) == {
        "cg_utm_source": "linkedin",
        "cg_utm_campaign": "CG-LINKEDIN-SMB-DIAGNOSTIC-2026-Q4",
    }
    assert attribution.from_metadata({"cg_utm_campaign": "<script>"}) == {}
    assert attribution.from_metadata(None) == {}


def test_the_crcs_checkout_carries_the_leads_campaign_to_stripe(env, monkeypatch) -> None:
    client, Factory, _ = env
    monkeypatch.setenv("CRCS_RAPID_DIAGNOSTIC_ENABLED", "true")
    config_module.get_settings.cache_clear()
    sent: dict = {}

    def fake_checkout(line_items, **kwargs):
        sent.update(kwargs)
        return {"id": "cs_test_x", "url": "https://checkout.example/x", "mode": "mock",
                "checkout_mode": "payment", "amount_total": 12500, "currency": "cad"}

    monkeypatch.setattr(payments, "create_checkout_session", fake_checkout)
    lead_id = _make_lead(Factory)
    with Factory() as s:
        reference = str(s.get(Lead, lead_id).public_ref)
    response = client.post("/revenue/checkout", json={"customer_email": "buyer@example.com", "reference": reference})
    assert response.status_code == 200, response.text
    assert sent["extra_metadata"]["cg_utm_campaign"] == "CG-LINKEDIN-SMB-DIAGNOSTIC-2026-Q4"
    assert sent["extra_metadata"]["cg_utm_source"] == "linkedin"


def test_storefront_checkout_forwards_only_clean_attribution(env, monkeypatch) -> None:
    client, _, _ = env
    sent: dict = {}

    def fake_checkout(line_items, **kwargs):
        sent.update(kwargs)
        return {"id": "cs_test_y", "url": "https://checkout.example/y", "mode": "mock",
                "checkout_mode": "payment", "amount_total": 29700, "currency": "cad"}

    monkeypatch.setattr(payments, "create_checkout_session", fake_checkout)
    response = client.post("/checkout/session", json={
        "items": [{"sku": "risk-audit-90", "quantity": 1}],
        "attribution": {"utm_source": "google", "utm_campaign": "bad value!"},
    })
    assert response.status_code == 200, response.text
    assert sent["extra_metadata"] == {"cg_utm_source": "google"}


def test_paid_orders_are_grouped_by_the_campaign_that_produced_them(env) -> None:
    client, Factory, _ = env
    campaign = "CG-LINKEDIN-SMB-DIAGNOSTIC-2026-Q4"
    _send(client, "checkout.session.completed",
          _paid_session(metadata={"cg_utm_source": "linkedin", "cg_utm_campaign": campaign}))
    _send(client, "checkout.session.completed", _paid_session(id="cs_live_2", payment_intent="pi_2"),
          event_id="evt_2")
    [first, _] = sorted(_orders(Factory), key=lambda o: o.id)
    assert first.utm_campaign == campaign and first.utm_source == "linkedin"
    rows = {r["campaign"]: r for r in _cockpit(client)["revenue_by_campaign"]}
    assert rows[campaign]["confirmed_revenue_cad"] == 125.0
    assert rows["unattributed"]["orders"] == 1


# ── Verified MRR ───────────────────────────────────────────────────────────────

def test_mrr_comes_from_verified_subscriptions_not_from_leads(env) -> None:
    client, _, engine = env
    assert _cockpit(client)["verified_mrr_cad"] is None, "no subscriptions table is no data, not zero"

    with engine.begin() as conn:
        conn.execute(sa_text("""
            CREATE TABLE subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_customer_id VARCHAR(120) NOT NULL UNIQUE,
                plan VARCHAR(120) NOT NULL,
                stripe_price_id VARCHAR(120),
                status VARCHAR(32) NOT NULL
            )
        """))
        rows = [
            ("cus_1", _MONTHLY_PRICE, "active"),       # 100.00
            ("cus_2", _ANNUAL_PRICE, "active"),        # 1000 / 12 = 83.33
            ("cus_3", _MONTHLY_PRICE, "past_due"),     # not MRR, counted as at risk
            ("cus_4", "price_test_abc", "active"),     # test-mode Price: not ours to count
            ("cus_5", _MONTHLY_PRICE, "canceled"),
        ]
        for customer, price, status in rows:
            conn.execute(sa_text(
                "INSERT INTO subscriptions (stripe_customer_id, plan, stripe_price_id, status) "
                "VALUES (:c, 'x', :p, :s)"), {"c": customer, "p": price, "s": status})

    cockpit = _cockpit(client)
    assert cockpit["verified_mrr_cad"] == 183.33
    assert cockpit["active_subscriptions"] == 2
    assert cockpit["past_due_subscriptions"] == 1
    assert cockpit["unpriced_subscriptions"] == 1


def test_the_daily_sales_briefing_reports_revenue_net_of_refunds(env) -> None:
    """The briefing summed `paid` totals, so a partial refund or a chargeback
    never reduced the month-to-date figure it emails."""
    from datetime import UTC, datetime

    from app.sales_ops_briefing import compute_briefing

    client, Factory, _ = env
    _send(client, "checkout.session.completed", _paid_session())
    _send(client, "checkout.session.completed", _paid_session(id="cs_live_2", payment_intent="pi_2"),
          event_id="evt_2")
    _send(client, "charge.refunded", _charge(2500, False), event_id="evt_r")          # 25 back on order 1
    _send(client, "charge.dispute.created", {**_dispute("needs_response"), "payment_intent": "pi_2"},
          event_id="evt_d")                                                             # order 2 held
    with Factory() as s:
        briefing = compute_briefing(s, datetime.now(UTC), live=True)
    assert briefing.mtd_revenue == 100.0
    assert briefing.mtd_orders == 2
