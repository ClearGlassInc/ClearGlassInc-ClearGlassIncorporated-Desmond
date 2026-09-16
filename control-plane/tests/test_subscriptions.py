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
