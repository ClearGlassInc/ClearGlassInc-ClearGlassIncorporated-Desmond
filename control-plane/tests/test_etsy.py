"""Tests for the Etsy connector — offline, no network, no real credentials.

Covers: connection detection when nothing is configured, read-only verification via
an injected fetcher, governance gating of every Etsy write, and the connection guard
that blocks writes until Etsy is connected.
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app import etsy
from app.config import Settings
from app.governance import RiskTier, score_action

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app import db as db_module
    from app.main import create_app
    from app.models import Base

    _HAS_WEB_STACK = True
except (ImportError, RuntimeError):  # pragma: no cover - minimal env still runs the pure tests
    _HAS_WEB_STACK = False

import pytest


# --- pure connection detection (no DB, no network) -------------------------------

def test_not_connected_when_credentials_missing() -> None:
    status = etsy.connection_status(Settings())
    assert status["connected"] is False
    assert status["state"] == "not_connected"
    assert any("etsy_keystring" in m for m in status["missing"])
    assert any("etsy_access_token" in m for m in status["missing"])


def test_connected_when_credentials_present_but_unverified() -> None:
    s = Settings(etsy_keystring="key123", etsy_access_token="42.tok", etsy_scopes="listings_r,listings_w")
    status = etsy.connection_status(s)
    assert status["connected"] is True
    assert status["verified"] is False          # offline check never claims verification
    assert status["missing"] == []
    assert status["shop"]["shop_id"] == "42"     # derived from the token prefix
    assert "transactions_r" in status["scope_gap"]


def test_writes_blocked_until_connected() -> None:
    ready, reason = etsy.is_ready_for_writes(Settings())
    assert ready is False
    assert "not connected" in reason.lower()

    ready, _ = etsy.is_ready_for_writes(Settings(etsy_keystring="k", etsy_access_token="1.t"))
    assert ready is True


# --- read-only verification with an injected fetcher -----------------------------

def _fake_get(mapping: dict[str, tuple[int, dict]]):
    def get(path: str) -> tuple[int, dict]:
        return mapping.get(path, (404, {}))
    return get


def test_verify_reports_identity_permissions_and_sync() -> None:
    s = Settings(
        etsy_keystring="key123",
        etsy_access_token="42.tok",
        etsy_shop_id="7",
        etsy_shop_name="ClearGlassGoods",
        etsy_scopes="listings_r,listings_w,transactions_r,transactions_w",
    )
    get = _fake_get({
        "/application/openapi-ping": (200, {"application_id": 1}),
        "/application/users/me": (200, {"user_id": 42, "shop_id": 7}),
        "/application/shops/7": (200, {"shop_name": "ClearGlassGoods", "listing_active_count": 12}),
    })
    result = etsy.verify_connection(s, get=get)
    assert result["verified"] is True
    assert result["shop"]["shop_name"] == "ClearGlassGoods"
    assert result["shop"]["identity_match"] is True
    assert result["permissions"]["can_list_products"] is True
    assert result["permissions"]["can_manage_orders"] is True
    assert result["sync_status"]["active_listings"] == 12
    assert result["sync_status"]["state"] == "in_sync"


def test_verify_missing_order_scope_flags_no_order_management() -> None:
    s = Settings(
        etsy_keystring="key123",
        etsy_access_token="42.tok",
        etsy_shop_id="7",
        etsy_scopes="listings_r,listings_w",   # no transactions scopes
    )
    get = _fake_get({
        "/application/openapi-ping": (200, {}),
        "/application/users/me": (200, {"user_id": 42, "shop_id": 7}),
        "/application/shops/7": (200, {"shop_name": "Shop", "listing_active_count": 3}),
    })
    result = etsy.verify_connection(s, get=get)
    assert result["permissions"]["can_list_products"] is True
    assert result["permissions"]["can_manage_orders"] is False
    assert result["verified"] is False          # a required capability is missing
    assert "transactions_r" in result["permissions"]["scope_gap"]


def test_verify_without_credentials_makes_no_call() -> None:
    called = {"n": 0}

    def get(path: str):
        called["n"] += 1
        return (200, {})

    result = etsy.verify_connection(Settings(), get=get)
    assert result["connected"] is False
    assert called["n"] == 0                      # never touched the network


# --- governance: every Etsy write is gated ---------------------------------------

def test_all_etsy_writes_require_approval() -> None:
    for action in ("etsy_publish_listing", "etsy_update_listing", "etsy_sync_inventory", "etsy_manage_order"):
        a = score_action(action, {})
        assert a.requires_approval is True, action
        assert a.tier in (RiskTier.HIGH, RiskTier.CRITICAL), action


def test_etsy_reads_are_auto_executable() -> None:
    for action in ("etsy_connection_check", "etsy_verify_connection"):
        assert score_action(action, {}).requires_approval is False


# --- router integration ----------------------------------------------------------

@pytest.fixture()
def client(monkeypatch):
    if not _HAS_WEB_STACK:
        pytest.skip("fastapi/sqlalchemy not installed")
    engine = create_engine(
        "sqlite://", future=True,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
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
    return TestClient(app)


def test_connection_endpoint_reports_not_connected(client) -> None:
    resp = client.get("/etsy/connection")
    assert resp.status_code == 200
    assert resp.json()["connected"] is False


def test_publish_listing_blocked_when_not_connected(client) -> None:
    resp = client.post("/etsy/publish-listing", json={"sku": "CG-1", "title": "Lens", "price": 20})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "blocked_not_connected"
    assert body["requires_approval"] is True
    # nothing was queued and nothing executed
    assert client.get("/approvals").json() == []


def test_publish_listing_queues_approval_when_connected(client, monkeypatch) -> None:
    from app.config import get_settings

    connected = Settings(etsy_keystring="k", etsy_access_token="1.t", etsy_scopes=",".join(etsy.REQUIRED_SCOPES))
    monkeypatch.setattr("app.routers.etsy.get_settings", lambda: connected)
    monkeypatch.setattr("app.service.get_settings", get_settings)  # keep governance defaults

    resp = client.post("/etsy/publish-listing", json={"sku": "CG-1", "title": "Lens", "price": 20})
    body = resp.json()
    assert body["status"] == "queued_for_approval"
    assert body["requires_approval"] is True
    pending = client.get("/approvals").json()
    assert len(pending) == 1
    assert pending[0]["action"] == "etsy_publish_listing"
