"""Slack revenue events: real steps only, after commit, with no personal data.

The revenue channel is only useful if it can be trusted, so these pin the rules
that make it trustworthy: nothing is sent without a Slack URL, a redelivered
webhook announces nothing, a rolled-back transaction announces nothing, test-mode
money is labelled TEST DATA, refunds are announced as loudly as payments, no
message carries a name or email, text from public form fields cannot ping the
channel or forge a line, and Slack being down never fails the request.

Payments go through the signed ``/webhooks/stripe`` route and leads through the
public ``/revenue/leads`` route: the paths real money and real leads take.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal

import pytest

try:
    import os as _os

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    _os.environ.setdefault("DATABASE_URL", "sqlite://")
    from app.audit import log_event
    from app.main import create_app
    from app.models import Base, Event, Lead, Order, ServiceOrder
    from app.revenue_service import confirm_delivery

    from app import config as config_module
    from app import db as db_module
    from app import payments, revenue_notify, security
    _HAS_WEB_STACK = True
except (ImportError, RuntimeError):  # pragma: no cover - minimal env runs pure tests only
    _HAS_WEB_STACK = False

_SECRET = "whsec_test_revenue_notify"
_SLACK_URL = "https://hooks.slack.com/services/T000/B000/XXXXXXXX"
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")

LEAD = {
    "full_name": "Test Buyer",
    "work_email": "buyer@example.com",
    "company": "Example Manufacturing",
    "service_interest": "Rapid Website & Deployment Diagnostic",
    "primary_goal": "Understand deployment risk before launch",
    "current_challenge": "Releases break the checkout without warning",
}


@pytest.fixture()
def env(monkeypatch):
    if not _HAS_WEB_STACK:
        pytest.skip("fastapi/sqlalchemy not installed")
    monkeypatch.setattr(security, "_limiter", security.SlidingWindowLimiter())
    monkeypatch.setattr(payments, "_webhook_secret", lambda: _SECRET)
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    monkeypatch.delenv("CRCS_RAPID_DIAGNOSTIC_ENABLED", raising=False)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", _SLACK_URL)
    config_module.get_settings.cache_clear()

    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(revenue_notify, "transport", lambda url, text: sent.append((url, text)))

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
    yield TestClient(app, raise_server_exceptions=False), Factory, sent
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
        "amount_total": 24900,
        "currency": "cad",
        "customer_details": {"email": "buyer@example.com", "name": "Test Buyer"},
        "metadata": {},
    }
    session.update(overrides)
    return session


def _stages(sent) -> list[str]:
    return [re.search(r"^Stage: (.+)$", text, re.M).group(1) for _, text in sent]


def _no_personal_data(sent) -> None:
    for _, text in sent:
        assert not _EMAIL.search(text), f"an email address reached Slack: {text}"
        assert "Test Buyer" not in text, f"a buyer's name reached Slack: {text}"


# ── Off unless configured ──────────────────────────────────────────────────────

def test_nothing_is_sent_without_a_slack_url(env, monkeypatch) -> None:
    client, _, sent = env
    monkeypatch.delenv("SLACK_WEBHOOK_URL")
    config_module.get_settings.cache_clear()
    _send(client, "checkout.session.completed", _paid_session())
    assert sent == []


def test_a_url_that_is_not_a_slack_webhook_is_refused(env, monkeypatch) -> None:
    """A mistyped setting must not turn the notifier into a request to any host."""
    client, _, sent = env
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.com/collect")
    config_module.get_settings.cache_clear()
    _send(client, "checkout.session.completed", _paid_session())
    assert sent == []


# ── Payments ───────────────────────────────────────────────────────────────────

def test_a_verified_live_payment_is_announced_once(env) -> None:
    client, Factory, sent = env
    _send(client, "checkout.session.completed", _paid_session(), event_id="evt_a")
    _send(client, "checkout.session.completed", _paid_session(), event_id="evt_a_retry")

    assert _stages(sent) == ["PAYMENT RECEIVED"], "a redelivered webhook announced a second payment"
    url, text = sent[0]
    assert url == _SLACK_URL
    assert text.startswith("CLEARGLASS REVENUE EVENT\n")
    assert "Mode: LIVE" in text
    assert "Amount: CAD $249.00" in text
    assert "Payment: cs_live_1" in text
    assert "Next Action: Begin delivery" in text
    _no_personal_data(sent)
    with Factory() as s:
        assert len(s.scalars(select(Order)).all()) == 1


def test_test_mode_money_is_labelled_test_data_not_revenue(env) -> None:
    client, _, sent = env
    _send(client, "checkout.session.completed", _paid_session(id="cs_test_1", payment_intent="pi_t"),
          livemode=False)
    [(_, text)] = sent
    assert text.startswith("CLEARGLASS REVENUE EVENT (TEST DATA)\n")
    assert "Mode: TEST DATA" in text
    assert "Begin delivery" not in text


def test_a_paid_diagnostic_announces_payment_then_delivery(env) -> None:
    """Delivery work opens only on verified live money, and the channel sees both steps."""
    client, Factory, sent = env
    with Factory() as s:
        lead = Lead(full_name="Test Buyer", email="buyer@example.com", service_interest="Rapid Diagnostic")
        s.add(lead)
        s.commit()
        lead_id = lead.id
    _send(client, "checkout.session.completed", _paid_session(metadata={
        "crcs_revenue_system": "v1",
        "crcs_sku": "risk-audit-90",
        "crcs_lead_id": str(lead_id),
    }))

    assert _stages(sent) == ["PAYMENT RECEIVED", "DELIVERY STARTED"]
    assert "Offer: ClearGlass 90-Minute Cyber Risk Audit" in sent[1][1]
    _no_personal_data(sent)


def test_refunds_are_announced_as_loudly_as_payments(env) -> None:
    """A channel that reports money in but not money out overstates revenue."""
    client, _, sent = env
    _send(client, "checkout.session.completed", _paid_session())
    charge = {"id": "ch_1", "payment_intent": "pi_1", "amount": 24900,
              "amount_refunded": 24900, "refunded": True, "currency": "cad"}
    _send(client, "charge.refunded", charge, event_id="evt_r")
    _send(client, "charge.refunded", charge, event_id="evt_r_retry")

    assert _stages(sent) == ["PAYMENT RECEIVED", "REFUNDED"]
    assert "Refunded: CAD $249.00" in sent[1][1]


def test_slack_being_down_never_fails_the_webhook(env, monkeypatch) -> None:
    client, Factory, _ = env

    def broken(url: str, text: str) -> None:
        raise OSError("slack unreachable")

    monkeypatch.setattr(revenue_notify, "transport", broken)
    _send(client, "checkout.session.completed", _paid_session())
    with Factory() as s:
        [order] = s.scalars(select(Order)).all()
        assert order.status == "paid", "a Slack outage lost a verified payment"

    # FastAPI commits the request session after the response is sent, so the route
    # above cannot see an error raised at commit. Code that commits itself can.
    with Factory() as s:
        lead = Lead(full_name="Test Buyer", email="buyer@example.com", service_interest="Quick-Audit")
        s.add(lead)
        s.flush()
        log_event(s, actor="admin", action="lead_stage_changed", target=str(lead.id),
                  payload={"from": "NEW", "to": "QUALIFIED"}, result="executed")
        s.commit()   # must not raise


def test_a_failing_lookup_cannot_touch_the_payment_transaction(env, monkeypatch) -> None:
    """The lookups run after commit on their own session, so a query error there
    cannot abort the transaction that is recording the payment."""
    client, Factory, sent = env

    def failing(session, row):
        raise RuntimeError("lookup failed")

    monkeypatch.setattr(revenue_notify, "describe", failing)
    _send(client, "checkout.session.completed", _paid_session())
    with Factory() as s:
        [order] = s.scalars(select(Order)).all()
        assert order.status == "paid"
    assert sent == []


# ── Leads and the rest of the chain ────────────────────────────────────────────

def test_a_public_lead_is_announced_without_personal_data(env) -> None:
    client, _, sent = env
    response = client.post("/revenue/leads", json=LEAD)
    assert response.status_code == 201, response.text

    assert _stages(sent) == ["NEW LEAD"]
    assert "Offer: Rapid Website &amp; Deployment Diagnostic" in sent[0][1]
    _no_personal_data(sent)
    assert "Example Manufacturing" not in sent[0][1]


def test_a_rolled_back_step_is_never_announced(env) -> None:
    _, Factory, sent = env
    with Factory() as s:
        lead = Lead(full_name="Test Buyer", email="buyer@example.com", service_interest="Quick-Audit")
        s.add(lead)
        s.flush()
        log_event(s, actor="admin", action="lead_stage_changed", target=str(lead.id),
                  payload={"from": "NEW", "to": "QUALIFIED"}, result="executed")
        s.rollback()
        # The next transaction on the same session must not carry the dropped step.
        s.add(Lead(full_name="Other", email="other@example.com", service_interest="Quick-Audit"))
        s.commit()
    assert sent == []


@pytest.mark.parametrize(("to", "expected"), [
    ("QUALIFIED", ["QUALIFIED"]),
    ("BOOKED", ["MEETING BOOKED"]),
    ("PROPOSAL_SENT", ["PROPOSAL SENT"]),
    ("NURTURE", []),
    ("LOST", []),
])
def test_only_commercial_milestones_reach_the_channel(env, to, expected) -> None:
    _, Factory, sent = env
    with Factory() as s:
        lead = Lead(full_name="Test Buyer", email="buyer@example.com", service_interest="Quick-Audit",
                    next_action="Call Test Buyer on Tuesday")
        s.add(lead)
        s.flush()
        log_event(s, actor="admin", action="lead_stage_changed", target=str(lead.id),
                  payload={"from": "NEW", "to": to}, result="executed")
        s.commit()
    assert _stages(sent) == expected
    _no_personal_data(sent)   # the admin's free-text next action can name a person


def test_confirmed_delivery_is_revenue_confirmed_net_of_refunds(env) -> None:
    _, Factory, sent = env
    with Factory() as s:
        order = Order(status="partially_refunded", total=Decimal("297.00"),
                      amount_refunded=Decimal("47.00"), currency="CAD", environment="live")
        s.add(order)
        s.flush()
        service = ServiceOrder(order_id=order.id, sku="risk-audit-90", status="IN_PROGRESS")
        s.add(service)
        s.flush()
        confirm_delivery(s, service)
        s.commit()
    [(_, text)] = sent
    assert "Stage: REVENUE CONFIRMED" in text
    assert "Amount: CAD $250.00" in text


def test_untrusted_text_cannot_ping_the_channel_or_forge_a_line(env) -> None:
    client, _, sent = env
    response = client.post("/revenue/leads", json={
        **LEAD, "source": "<!channel>\nStage: PAYMENT RECEIVED\nAmount: CAD $99,999",
    })
    assert response.status_code == 201, response.text
    [(_, text)] = sent
    assert "<!channel>" not in text
    assert "&lt;!channel&gt;" in text
    assert len(re.findall(r"^Stage:", text, re.M)) == 1
    assert not re.search(r"^Amount:", text, re.M)


def test_the_real_transport_posts_slack_json() -> None:
    """The production sender, against a local server: one JSON body with ``text``."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    if not _HAS_WEB_STACK:
        pytest.skip("fastapi/sqlalchemy not installed")
    received: list[tuple[str, dict]] = []

    class Hook(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - http.server naming
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append((self.headers["Content-Type"], json.loads(body)))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Hook)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    revenue_notify._post(f"http://127.0.0.1:{server.server_port}/", "CLEARGLASS REVENUE EVENT")
    thread.join(timeout=5)
    server.server_close()
    assert received == [("application/json", {"text": "CLEARGLASS REVENUE EVENT"})]


# ── Recurring revenue ──────────────────────────────────────────────────────────

def _subscription_row(action: str, **payload) -> Event:
    return Event(actor="stripe", action=action, target="cus_1", payload=payload, result="executed")


@pytest.mark.parametrize(("action", "from_status", "expected"), [
    ("subscription_active", None, "MRR CREATED"),
    ("subscription_active", "incomplete", "MRR CREATED"),
    ("subscription_active", "active", None),
    ("subscription_canceled", "active", "MRR CANCELLED"),
    ("subscription_canceled", "past_due", None),
])
def test_mrr_is_announced_only_when_it_starts_or_stops(env, action, from_status, expected) -> None:
    _, Factory, _ = env
    row = _subscription_row(action, plan="business-protection-annual", from_status=from_status, livemode=True)
    with Factory() as s:
        fields = revenue_notify.describe(s, row)
    if expected is None:
        assert fields is None
    else:
        assert fields["Stage"] == expected
        assert fields["Mode"] == "LIVE"
        assert fields["MRR"] == "CAD $83.33", "an annual plan's MRR is a twelfth of its price"


def test_a_test_mode_subscription_is_labelled_test_data(env) -> None:
    _, Factory, _ = env
    row = _subscription_row("subscription_active", plan="business-protection-monthly", from_status=None)
    with Factory() as s:
        fields = revenue_notify.describe(s, row)
    assert fields["Mode"] == "TEST DATA"
    assert fields["MRR"] == "CAD $100.00"
