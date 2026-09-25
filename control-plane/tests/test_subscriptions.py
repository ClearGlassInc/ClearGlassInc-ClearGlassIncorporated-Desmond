from __future__ import annotations

import sys
import types

import pytest

from app.routers.subscriptions import ACTIVE_STATUSES, _price_plan

try:
    import os as _os

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy import text as sa_text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    _os.environ.setdefault("DATABASE_URL", "sqlite://")
    from app.main import create_app
    from app.models import Base

    from app import db as db_module
    _HAS_WEB_STACK = True
except (ImportError, RuntimeError):  # pragma: no cover - minimal env runs pure tests only
    _HAS_WEB_STACK = False


def test_active_subscription_statuses_are_entitled() -> None:
    assert "active" in ACTIVE_STATUSES
    assert "trialing" in ACTIVE_STATUSES
    assert "canceled" not in ACTIVE_STATUSES
    assert "unpaid" not in ACTIVE_STATUSES


def test_price_id_maps_to_server_owned_subscription_sku() -> None:
    assert _price_plan("price_1U0wlFL8uR92FksUG6ZT87rG") == "business-protection-monthly"
    assert _price_plan("price_1U0wlOL8uR92FksUJjFEMvGT") == "business-protection-annual"
    assert _price_plan("price_not_in_pricebook") == "unknown"


# --------------------------------------------------------------- throttle regression
#
# `GET /subscriptions/status` is unauthenticated and calls Stripe on every request.
# It is exempt from `require_admin` for the same reason `/subscriptions/portal` is —
# the customer has no account with us — but `test_route_auth_coverage.py` only walks
# *mutating* methods, so a read endpoint that reaches Stripe never had to justify
# itself there. Every other open endpoint that makes an outbound Stripe call carries
# a per-IP throttle; this one did not, so an anonymous caller could amplify one cheap
# HTTP request into one Stripe API call without limit and exhaust the account's rate
# budget, taking checkout and the webhooks down with it.


@pytest.fixture()
def live_client(monkeypatch):
    """A client whose Stripe calls are counted instead of sent."""
    if not _HAS_WEB_STACK:
        pytest.skip("fastapi/sqlalchemy not installed")

    from app import payments, security

    # A fresh limiter per test: the module singleton is shared process-wide and
    # would otherwise carry this test's hits into (or out of) unrelated ones.
    monkeypatch.setattr(security, "_limiter", security.SlidingWindowLimiter())

    calls: list[str] = []

    class _Session:
        @staticmethod
        def retrieve(session_id, *args, **kwargs):
            calls.append(session_id)          # one real Stripe API round-trip
            return {"customer": "cus_stub", "mode": "subscription"}

    stub = types.ModuleType("stripe")
    stub.api_key = None
    stub.checkout = types.SimpleNamespace(Session=_Session)
    monkeypatch.setitem(sys.modules, "stripe", stub)
    monkeypatch.setattr(payments, "is_live", lambda: True)
    monkeypatch.setattr(payments, "_secret_key", lambda: "sk_live_stub")

    engine = create_engine(
        "sqlite://", future=True,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    # `subscriptions` ships as raw DDL (migrations/006_subscriptions.sql), not ORM
    # metadata, so create_all does not build it. Mirror only the columns /status
    # reads — this fixture tests the throttle, not the schema.
    with engine.begin() as conn:
        conn.execute(sa_text("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                stripe_customer_id VARCHAR(120) PRIMARY KEY,
                plan VARCHAR(120),
                status VARCHAR(32),
                interval VARCHAR(16),
                current_period_end TIMESTAMP,
                cancel_at_period_end BOOLEAN DEFAULT 0
            )
        """))
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_session():
        session = TestingSession()
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
    return TestClient(app), calls


def _status(client, session_id="cs_test_abcdefgh"):
    return client.get("/subscriptions/status", params={"checkout_session_id": session_id})


def test_status_still_answers_a_legitimate_caller(live_client) -> None:
    """The fix must not cost a normal customer their answer."""
    client, calls = live_client
    response = _status(client)
    assert response.status_code == 200
    assert response.json() == {"status": "pending", "active": False, "mode": "live"}
    assert calls == ["cs_test_abcdefgh"]


def test_status_throttles_an_anonymous_flood(live_client) -> None:
    """The exploit: unbounded Stripe round-trips from one unauthenticated caller."""
    client, calls = live_client
    from app.config import get_settings

    limit = get_settings().rate_limit_checkout_per_minute
    codes = [_status(client).status_code for _ in range(limit * 3)]

    assert codes.count(429) > 0, "no request was throttled; the endpoint is still open"
    assert len(calls) <= limit, f"{len(calls)} Stripe calls escaped a {limit}/min ceiling"
    assert codes[:limit] == [200] * limit, "throttle fired before the budget was spent"


def test_status_has_its_own_throttle_bucket(live_client) -> None:
    """Polling status must not consume the budget for opening the billing portal."""
    client, _ = live_client
    from app.config import get_settings

    limit = get_settings().rate_limit_checkout_per_minute
    for _ in range(limit * 2):
        _status(client)
    assert _status(client).status_code == 429

    portal = client.post(
        "/subscriptions/portal", json={"checkout_session_id": "cs_test_abcdefgh"}
    )
    assert portal.status_code != 429


# ------------------------------------------------------------- audit-ledger coverage
#
# CLAUDE.md's commerce invariant is that every material change lands in the append-only
# `events` ledger. Every sibling money router honours it — payments, fulfillment,
# sidestore, etsy, order_ledger — but the subscription webhook wrote none, so a plan
# change, a cancellation or a failed payment moved a customer's billing state with no
# ledger row behind it. These tests pin the rows down so the gap cannot reopen.

_WEBHOOK_SECRET = "whsec_test_subscription_ledger"


@pytest.fixture()
def webhook_client(monkeypatch):
    """A client whose Stripe webhook signature verifies, backed by the real schema."""
    if not _HAS_WEB_STACK:
        pytest.skip("fastapi/sqlalchemy not installed")

    from sqlalchemy import event as sa_event

    from app import payments, security

    monkeypatch.setattr(security, "_limiter", security.SlidingWindowLimiter())
    monkeypatch.setattr(payments, "_webhook_secret", lambda: _WEBHOOK_SECRET)

    engine = create_engine(
        "sqlite://", future=True,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )

    # The router's upsert is Postgres-flavoured and stamps `updated_at = now()`.
    # SQLite has no now(), so register one rather than forking the SQL for tests —
    # the point is to exercise the statements that actually ship.
    @sa_event.listens_for(engine, "connect")
    def _add_now(dbapi_conn, _record):  # pragma: no cover - driver callback
        from datetime import UTC as _utc
        from datetime import datetime as _dt
        dbapi_conn.create_function("now", 0, lambda: _dt.now(_utc).isoformat(sep=" "))

    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        # Mirrors migrations/006_subscriptions.sql, which ships as raw DDL.
        conn.execute(sa_text("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_customer_id VARCHAR(120) NOT NULL UNIQUE,
                stripe_subscription_id VARCHAR(120) UNIQUE,
                customer_email VARCHAR(254),
                plan VARCHAR(120) NOT NULL,
                stripe_price_id VARCHAR(120),
                interval VARCHAR(16),
                status VARCHAR(32) NOT NULL,
                current_period_end TIMESTAMP,
                cancel_at_period_end BOOLEAN NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(sa_text("""
            CREATE TABLE IF NOT EXISTS stripe_events (
                id VARCHAR(120) PRIMARY KEY,
                event_type VARCHAR(120) NOT NULL,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_session():
        session = TestingSession()
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
    return TestClient(app), TestingSession


def _post_event(client, event: dict):
    """Deliver a correctly signed Stripe event to the subscription webhook."""
    import json

    from app import payments

    body = json.dumps(event).encode()
    return client.post(
        "/subscriptions/webhook",
        content=body,
        headers={"stripe-signature": payments.sign_payload(body, _WEBHOOK_SECRET)},
    )


def _ledger(SessionFactory, action: str | None = None) -> list:
    from sqlalchemy import select

    from app.models import Event

    with SessionFactory() as session:
        rows = session.scalars(select(Event).order_by(Event.id)).all()
    return [r for r in rows if action is None or r.action == action]


def _subscription_event(event_id: str, status: str, **overrides) -> dict:
    obj = {
        "id": "sub_test_1",
        "customer": "cus_test_1",
        "status": status,
        "cancel_at_period_end": False,
        "current_period_end": 1793000000,
        "items": {"data": [{"price": {
            "id": "price_1U0wlFL8uR92FksUG6ZT87rG",
            "recurring": {"interval": "month"},
        }}]},
    }
    obj.update(overrides)
    return {
        "id": event_id,
        "type": "customer.subscription.updated",
        "data": {"object": obj},
    }


def test_subscription_lifecycle_writes_an_audit_row(webhook_client) -> None:
    """An active subscription must leave a ledger row naming plan and status."""
    client, SessionFactory = webhook_client
    response = _post_event(client, _subscription_event("evt_1", "active"))

    assert response.status_code == 200
    assert response.json()["duplicate"] is False

    rows = _ledger(SessionFactory, "subscription_active")
    assert len(rows) == 1, "subscription lifecycle event left no audit row"
    assert rows[0].actor == "stripe"
    assert rows[0].target == "cus_test_1"
    assert rows[0].result == "executed"
    assert rows[0].payload["plan"] == "business-protection-monthly"
    assert rows[0].payload["from_status"] is None


def test_subscription_row_records_live_or_test_mode(webhook_client) -> None:
    """Without the mode, test-mode MRR could be announced as real recurring revenue."""
    client, SessionFactory = webhook_client
    _post_event(client, {**_subscription_event("evt_live", "active"), "livemode": True})
    _post_event(client, _subscription_event("evt_test", "canceled"))

    [live] = _ledger(SessionFactory, "subscription_active")
    [test] = _ledger(SessionFactory, "subscription_canceled")
    assert live.payload["livemode"] is True
    assert test.payload["livemode"] is False


def test_status_transition_records_where_it_came_from(webhook_client) -> None:
    """A cancellation is only auditable if the row says what it replaced."""
    client, SessionFactory = webhook_client
    _post_event(client, _subscription_event("evt_1", "active"))
    _post_event(client, _subscription_event("evt_2", "canceled"))

    rows = _ledger(SessionFactory, "subscription_canceled")
    assert len(rows) == 1
    assert rows[0].payload["from_status"] == "active", (
        "cancellation did not record the status it replaced"
    )


def test_redelivered_event_is_skipped_and_recorded(webhook_client) -> None:
    """Stripe retries; the second delivery must change nothing but still be visible."""
    client, SessionFactory = webhook_client
    first = _post_event(client, _subscription_event("evt_dup", "active"))
    second = _post_event(client, _subscription_event("evt_dup", "canceled"))

    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True

    # The duplicate must not have applied the canceled status.
    with SessionFactory() as session:
        status = session.execute(sa_text(
            "SELECT status FROM subscriptions WHERE stripe_customer_id = 'cus_test_1'"
        )).scalar_one()
    assert status == "active", "a redelivered event overwrote live billing state"

    skipped = _ledger(SessionFactory, "subscription_event_duplicate_skipped")
    assert len(skipped) == 1
    assert skipped[0].result == "skipped"
    assert skipped[0].target == "evt_dup"


def test_failed_payment_is_recorded_without_touching_status(webhook_client) -> None:
    """Dunning must be auditable, but `customer.subscription.updated` owns status."""
    client, SessionFactory = webhook_client
    _post_event(client, _subscription_event("evt_1", "active"))
    _post_event(client, {
        "id": "evt_invoice_1",
        "type": "invoice.payment_failed",
        "data": {"object": {
            "customer": "cus_test_1",
            "subscription": "sub_test_1",
            "attempt_count": 2,
            "next_payment_attempt": 1793600000,
            "amount_due": 19900,
            "currency": "cad",
        }},
    })

    rows = _ledger(SessionFactory, "subscription_invoice_payment_failed")
    assert len(rows) == 1, "a failed subscription payment left no audit row"
    assert rows[0].result == "flagged"
    assert rows[0].target == "cus_test_1"
    assert rows[0].payload["attempt_count"] == 2

    with SessionFactory() as session:
        status = session.execute(sa_text(
            "SELECT status FROM subscriptions WHERE stripe_customer_id = 'cus_test_1'"
        )).scalar_one()
    assert status == "active", (
        "invoice.payment_failed wrote status; that column has a single writer"
    )


def test_unsigned_webhook_is_rejected_and_writes_nothing(webhook_client) -> None:
    """The ledger must not be forgeable by an unsigned caller."""
    client, SessionFactory = webhook_client
    import json

    body = json.dumps(_subscription_event("evt_forged", "active")).encode()
    response = client.post(
        "/subscriptions/webhook",
        content=body,
        headers={"stripe-signature": "t=1,v1=deadbeef"},
    )

    assert response.status_code == 400
    assert _ledger(SessionFactory) == [], "an unverified event reached the ledger"
