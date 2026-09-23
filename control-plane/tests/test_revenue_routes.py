"""The public CRCS routes must answer, not crash.

``POST /revenue/leads`` is the front of the CRCS funnel. It shipped raising
``AttributeError`` on every request because five settings it depends on were
never added to ``Settings``, and its own tests never called it. These drive the
three public routes through the app, so a missing setting, table or dependency
surfaces here instead of in front of a prospect.

The admin cockpit shipped broken the same way: it read ``recent_stripe``, a
local variable of another route, so every call raised ``NameError``.
"""
from __future__ import annotations

import pytest

try:
    import os as _os

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    _os.environ.setdefault("DATABASE_URL", "sqlite://")
    from app.main import create_app
    from app.models import Base

    from app import config as config_module
    from app import db as db_module
    from app import pricebook

    _HAS_WEB_STACK = True
except (ImportError, RuntimeError):  # pragma: no cover - minimal env runs pure tests only
    _HAS_WEB_STACK = False

LEAD = {
    "full_name": "Test Buyer",
    "work_email": "buyer@example.com",
    "company": "Example Manufacturing",
    "service_interest": "Rapid Website & Deployment Diagnostic",
    "primary_goal": "Understand deployment risk before launch",
    "current_challenge": "Releases break the checkout without warning",
}


@pytest.fixture()
def client(monkeypatch):
    if not _HAS_WEB_STACK:
        pytest.skip("fastapi/sqlalchemy not installed")
    monkeypatch.delenv("CRCS_RAPID_DIAGNOSTIC_ENABLED", raising=False)
    # Open dev mode, so the admin-gated cockpit is reachable without a credential.
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    config_module.get_settings.cache_clear()

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
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        config_module.get_settings.cache_clear()


def test_the_lead_form_accepts_a_valid_submission(client) -> None:
    response = client.post("/revenue/leads", json=LEAD)
    assert response.status_code == 200, response.text
    assert response.json()["stage"] in {"QUALIFIED", "REVIEW_REQUIRED"}


def test_the_lead_form_rejects_the_honeypot(client) -> None:
    response = client.post("/revenue/leads", json={**LEAD, "website_honeypot": "filled by a bot"})
    assert response.status_code == 400, response.text


def test_the_public_offer_is_priced_from_the_price_book(client) -> None:
    response = client.get("/revenue/public-offer")
    assert response.status_code == 200, response.text
    body = response.json()
    offer = pricebook.get_offer(config_module.get_settings().crcs_first_offer_sku)
    assert body["sku"] == offer.sku
    assert body["amount_cad"] == offer.amount / 100


def test_checkout_is_refused_until_the_owner_enables_it(client) -> None:
    """Fail closed: live purchase needs an explicit owner decision, not a default."""
    response = client.post("/revenue/checkout", json={"customer_email": "buyer@example.com"})
    assert response.status_code == 409, response.text


def test_checkout_does_not_reveal_which_leads_exist(client, monkeypatch) -> None:
    """Lead ids are sequential. If an unknown id answered differently from a
    known id with the wrong email, anyone could count the leads or confirm that
    a given address had submitted the qualification form."""
    monkeypatch.setenv("CRCS_RAPID_DIAGNOSTIC_ENABLED", "true")
    config_module.get_settings.cache_clear()
    lead_id = client.post("/revenue/leads", json=LEAD).json()["id"]

    wrong_email = client.post(
        "/revenue/checkout", json={"customer_email": "someone@else.test", "lead_id": lead_id}
    )
    unknown_lead = client.post(
        "/revenue/checkout", json={"customer_email": "someone@else.test", "lead_id": lead_id + 1}
    )
    assert wrong_email.status_code == unknown_lead.status_code == 403
    assert wrong_email.json() == unknown_lead.json()

    owner = client.post("/revenue/checkout", json={"customer_email": LEAD["work_email"], "lead_id": lead_id})
    assert owner.status_code == 200, owner.text


def test_the_admin_cockpit_renders(client) -> None:
    response = client.get("/revenue/cockpit")
    assert response.status_code == 200, response.text
    assert response.json()["webhook_health"] == "NO_RECENT_EVIDENCE"
