"""The public CRCS routes must answer, not crash.

``POST /revenue/leads`` is the front of the CRCS funnel. It shipped raising
``AttributeError`` on every request because five settings it depends on were
never added to ``Settings``, and its own tests never called it. These drive the
three public routes through the app, so a missing setting, table or dependency
surfaces here instead of in front of a prospect.

The admin cockpit shipped broken the same way: it read ``recent_stripe``, a
local variable of another route, so every call raised ``NameError``.

CRCS Phase 0 (docs/crcs/IMPLEMENTATION_SEQUENCE.md 0.3-0.5) narrowed what the
public routes give away: a receipt with an opaque reference instead of the
lead record, a honeypot answer identical to a real one, and no email address
in the audit ledger.
"""
from __future__ import annotations

import uuid

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

    from app import payments

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


RECEIPT_KEYS = {"status", "reference", "next_step", "booking_url"}


def _leads(client) -> list[dict]:
    response = client.get("/revenue/leads")
    assert response.status_code == 200, response.text
    return response.json()


def test_the_lead_form_accepts_a_valid_submission(client) -> None:
    response = client.post("/revenue/leads", json=LEAD)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "received"
    [lead] = _leads(client)
    assert lead["stage"] in {"QUALIFIED", "REVIEW_REQUIRED"}
    assert lead["public_ref"] == body["reference"]


def test_the_receipt_reveals_nothing_about_the_pipeline(client) -> None:
    """The visitor gets a reference and a next step, not the CRM record.

    A sequential id let anyone read the lead count off their own receipt; the
    score, stage and owner are internal routing, not the visitor's business.
    """
    first = client.post("/revenue/leads", json=LEAD).json()
    second = client.post("/revenue/leads", json={**LEAD, "work_email": "other@example.com"}).json()
    assert set(first) == RECEIPT_KEYS
    assert uuid.UUID(first["reference"]) != uuid.UUID(second["reference"])
    assert "id" not in first and "stage" not in first and "lead_score" not in first


def test_every_submitter_is_offered_the_same_next_step(client, monkeypatch) -> None:
    """The fit score orders review; it never decides who may book a call."""
    assert client.post("/revenue/leads", json=LEAD).json()["next_step"] == "owner_review"

    monkeypatch.setenv("CRCS_CALENDAR_BOOKING_URL", "https://booking.example/discovery")
    config_module.get_settings.cache_clear()
    strong = client.post("/revenue/leads", json={**LEAD, "desired_timeline": "0-7 days"}).json()
    weak = client.post(
        "/revenue/leads",
        json={**LEAD, "work_email": "weak@example.com", "primary_goal": "Just looking", "company": None},
    ).json()
    assert strong["next_step"] == weak["next_step"] == "book_discovery_call"
    assert strong["booking_url"] == weak["booking_url"] == "https://booking.example/discovery"


def test_the_honeypot_answers_like_a_real_submission_and_stores_nothing(client) -> None:
    """A 400 taught bots which field to leave empty."""
    real = client.post("/revenue/leads", json=LEAD)
    trapped = client.post("/revenue/leads", json={**LEAD, "website_honeypot": "filled by a bot"})
    assert trapped.status_code == real.status_code == 201, trapped.text
    assert set(trapped.json()) == set(real.json())
    assert trapped.json()["next_step"] == real.json()["next_step"]
    assert len(_leads(client)) == 1
    lead_events = [e for e in client.get("/events").json() if e["action"] == "lead_created"]
    assert len(lead_events) == 1


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
    """If an unknown reference answered differently from a known reference with
    the wrong email, anyone holding a reference could confirm which address had
    submitted the qualification form."""
    monkeypatch.setenv("CRCS_RAPID_DIAGNOSTIC_ENABLED", "true")
    config_module.get_settings.cache_clear()
    reference = client.post("/revenue/leads", json=LEAD).json()["reference"]

    wrong_email = client.post(
        "/revenue/checkout", json={"customer_email": "someone@else.test", "reference": reference}
    )
    unknown_lead = client.post(
        "/revenue/checkout", json={"customer_email": "someone@else.test", "reference": str(uuid.uuid4())}
    )
    assert wrong_email.status_code == unknown_lead.status_code == 403
    assert wrong_email.json() == unknown_lead.json()

    owner = client.post("/revenue/checkout", json={"customer_email": LEAD["work_email"], "reference": reference})
    assert owner.status_code == 200, owner.text


def test_checkout_no_longer_accepts_the_sequential_lead_id(client, monkeypatch) -> None:
    monkeypatch.setenv("CRCS_RAPID_DIAGNOSTIC_ENABLED", "true")
    config_module.get_settings.cache_clear()
    client.post("/revenue/leads", json=LEAD)
    response = client.post("/revenue/checkout", json={"customer_email": LEAD["work_email"], "reference": 1})
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("payment_link", ["", "https://buy.stripe.com/test_placeholder"])
def test_checkout_keeps_email_addresses_out_of_the_ledger(client, monkeypatch, payment_link) -> None:
    """The ledger is append-only and kept for years; it holds IDs, not people.

    Both checkout branches are covered: the payment-link branch wrote the
    buyer's email as the event target, and the server-checkout branch wrote no
    checkout_started event at all.
    """
    monkeypatch.setenv("CRCS_RAPID_DIAGNOSTIC_ENABLED", "true")
    monkeypatch.setenv("CRCS_RAPID_DIAGNOSTIC_PAYMENT_LINK", payment_link)
    config_module.get_settings.cache_clear()
    sent_to_stripe: dict = {}

    def fake_checkout(line_items, **kwargs):
        sent_to_stripe.update(kwargs)
        return {"id": "cs_test_1", "url": "https://checkout.example/cs_test_1", "mode": "mock",
                "checkout_mode": "payment", "amount_total": 12500, "currency": "cad"}

    monkeypatch.setattr(payments, "create_checkout_session", fake_checkout)
    reference = client.post("/revenue/leads", json=LEAD).json()["reference"]

    anonymous = client.post("/revenue/checkout", json={"customer_email": "Walk-In@Example.com"})
    repeat = client.post("/revenue/checkout", json={"customer_email": "walk-in@example.com"})
    known = client.post("/revenue/checkout", json={"customer_email": LEAD["work_email"], "reference": reference})
    assert anonymous.status_code == repeat.status_code == known.status_code == 200

    started = [e for e in client.get("/events").json() if e["action"] == "checkout_started"]
    assert len(started) == 3
    assert all("@" not in (e["target"] or "") for e in started)
    anon_targets = {e["target"] for e in started if e["target"].startswith("buyer:")}
    assert len(anon_targets) == 1, "one buyer must map to one stable pseudonym"
    if not payment_link:
        assert "@" not in sent_to_stripe["client_reference_id"]
        assert sent_to_stripe["client_reference_id"] == f"crcs-{reference}"


@pytest.mark.parametrize("path", ["/events", "/metrics/overview", "/revenue/cockpit", "/revenue/leads"])
def test_the_ledger_metrics_and_pipeline_need_an_admin_credential(client, monkeypatch, path) -> None:
    """The ledger records a row per lead, order and stage change. Open, it let
    anyone count leads and watch sales as they happened."""
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key-not-a-real-credential")
    config_module.get_settings.cache_clear()
    assert client.get(path).status_code == 401
    authorised = client.get(path, headers={"Authorization": "Bearer test-admin-key-not-a-real-credential"})
    assert authorised.status_code == 200, authorised.text


def test_the_admin_cockpit_renders(client) -> None:
    response = client.get("/revenue/cockpit")
    assert response.status_code == 200, response.text
    assert response.json()["webhook_health"] == "NO_RECENT_EVIDENCE"


def test_the_cockpit_counts_leads_on_sqlite(client) -> None:
    """SQLite returns naive datetimes. The empty-database test above never
    compared one, so the cockpit shipped answering 500 once a lead existed."""
    client.post("/revenue/leads", json=LEAD)
    response = client.get("/revenue/cockpit")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["new_leads"] == 1
    assert body["due_actions"] == 1, "a new lead's review action is due immediately"
