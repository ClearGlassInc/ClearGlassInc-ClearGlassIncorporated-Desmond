"""Regression tests for durable Stripe ingress, duplicate delivery, and worker recovery."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite://")

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app import config as config_module
    from app import db as db_module
    from app import payments, security
    from app.main import create_app
    from app.models import Base, Order, StripeInboxEvent, StripeOutboxJob
    from app.stripe_worker import _claim_event, process_one_event
    _HAS_WEB_STACK = True
except (ImportError, RuntimeError):  # pragma: no cover
    _HAS_WEB_STACK = False

_SECRET = "whsec_test_secret_for_local_tests_only"


@pytest.fixture()
def ops_env(monkeypatch):
    if not _HAS_WEB_STACK:
        pytest.skip("FastAPI/SQLAlchemy stack is not installed")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_EXPECTED_LIVEMODE", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_PREVIOUS_SECRET", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_PREVIOUS_SECRET_ACCEPT_UNTIL", raising=False)
    monkeypatch.setattr(payments, "_webhook_secret", lambda: _SECRET)
    monkeypatch.setattr(security, "_limiter", security.SlidingWindowLimiter())
    config_module.get_settings.cache_clear()

    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, Factory
    config_module.get_settings.cache_clear()
    engine.dispose()


def _event(*, event_id="evt_test_001", event_type="checkout.session.completed", obj=None, livemode=False):
    obj = obj or {
        "id": "cs_test_001",
        "object": "checkout.session",
        "mode": "payment",
        "payment_status": "unpaid",
        "status": "complete",
        "amount_total": 29700,
        "currency": "cad",
        "metadata": {},
    }
    return {
        "id": event_id,
        "type": event_type,
        "livemode": livemode,
        "data": {"object": obj},
    }


def _post(client, event: dict, secret: str = _SECRET):
    body = json.dumps(event, separators=(",", ":")).encode()
    return client.post(
        "/webhooks/stripe",
        content=body,
        headers={"stripe-signature": payments.sign_payload(body, secret)},
    )


def test_signed_event_is_committed_before_ack_and_duplicate_does_not_reset_state(ops_env):
    client, Factory = ops_env
    event = _event()
    first = _post(client, event)
    assert first.status_code == 200, first.text
    assert first.json()["duplicate"] is False
    with Factory() as session:
        row = session.scalar(select(StripeInboxEvent))
        assert row is not None
        assert row.state == "pending"
        assert row.raw_payload == json.dumps(event, separators=(",", ":"))
        row.state = "retry"
        row.attempt_count = 2
        row.last_error_code = "SyntheticRetry"
        session.commit()

    duplicate = _post(client, event)
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["duplicate"] is True
    with Factory() as session:
        row = session.scalar(select(StripeInboxEvent))
        assert row.state == "retry"
        assert row.attempt_count == 2
        assert row.last_error_code == "SyntheticRetry"
        assert len(session.scalars(select(StripeInboxEvent)).all()) == 1


def test_invalid_signature_is_rejected_without_inbox_row(ops_env):
    client, Factory = ops_env
    body = json.dumps(_event()).encode()
    response = client.post(
        "/webhooks/stripe",
        content=body,
        headers={"stripe-signature": payments.sign_payload(body, "wrong-secret")},
    )
    assert response.status_code == 400
    with Factory() as session:
        assert session.scalar(select(StripeInboxEvent.id)) is None


def test_worker_commits_order_ledger_and_inbox_success_together(ops_env):
    client, Factory = ops_env
    response = _post(client, _event())
    assert response.status_code == 200, response.text

    assert process_one_event(factory=Factory, worker_id="test-worker") is True
    with Factory() as session:
        inbox = session.scalar(select(StripeInboxEvent))
        payment = session.scalar(select(Order))
        assert inbox is not None and inbox.state == "succeeded"
        assert inbox.processed_at is not None
        assert payment is not None
        assert payment.external_ref == "cs_test_001"
        assert payment.status == "pending"


def test_completed_session_with_no_payment_required_is_not_paid_by_default(ops_env):
    client, Factory = ops_env
    event = _event(event_id="evt_zero_001", obj={
        "id": "cs_test_zero", "object": "checkout.session", "mode": "payment",
        "payment_status": "no_payment_required", "status": "complete",
        "amount_total": 0, "currency": "cad", "metadata": {},
    })
    assert _post(client, event).status_code == 200
    assert process_one_event(factory=Factory, worker_id="test-worker") is True
    with Factory() as session:
        payment = session.scalar(select(Order))
        assert payment is not None
        assert payment.status == "failed"


def test_expired_worker_lease_is_reclaimed_with_a_new_fencing_token(ops_env):
    client, Factory = ops_env
    assert _post(client, _event(event_id="evt_lease_001")).status_code == 200
    first = _claim_event(Factory, "worker-old")
    assert first is not None
    with Factory() as session:
        row = session.scalar(select(StripeInboxEvent))
        row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
    second = _claim_event(Factory, "worker-new")
    assert second is not None
    assert second["fencing_token"] == first["fencing_token"] + 1
    assert second["lease_owner"] == "worker-new"


def test_thin_notification_is_never_processed_as_snapshot(ops_env):
    client, Factory = ops_env
    thin = {
        "id": "evt_thin_001",
        "type": "v2.core.account.updated",
        "object": "v2.core.event",
        "livemode": False,
        "related_object": {"id": "acct_test", "type": "account"},
    }
    response = _post(client, thin)
    assert response.status_code == 200, response.text
    assert response.json()["event_format"] == "thin"
    assert process_one_event(factory=Factory, worker_id="test-worker") is False
    with Factory() as session:
        inbox = session.scalar(select(StripeInboxEvent))
        alert = session.scalar(select(StripeOutboxJob))
        assert inbox is not None and inbox.state == "dead_letter"
        assert inbox.last_error_code == "thin_event_adapter_required"
        assert alert is not None and alert.job_type == "operator_alert"


def test_configured_environment_mismatch_is_rejected(ops_env, monkeypatch):
    client, Factory = ops_env
    monkeypatch.setenv("STRIPE_EXPECTED_LIVEMODE", "live")
    config_module.get_settings.cache_clear()
    response = _post(client, _event(livemode=False))
    assert response.status_code == 400
    with Factory() as session:
        assert session.scalar(select(StripeInboxEvent.id)) is None
