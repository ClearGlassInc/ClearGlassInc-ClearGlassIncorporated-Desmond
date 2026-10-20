"""Recoverable Stripe inbox/outbox worker for the ClearGlass commerce control plane."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import re
import socket
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request

from .audit import log_event
from .config import get_settings
from .db import SessionLocal
from .models import CommercialOrder, StripeInboxEvent, StripeOutboxJob

logger = logging.getLogger("clearglass.stripe_worker")
SUBSCRIPTION_EVENTS = frozenset({
    "customer.subscription.created", "customer.subscription.updated",
    "customer.subscription.deleted", "customer.subscription.paused",
    "customer.subscription.resumed", "invoice.paid", "invoice.payment_failed",
})
RETRIEVERS = {
    "checkout.session.completed": ("checkout_session", "Session"),
    "checkout.session.async_payment_succeeded": ("checkout_session", "Session"),
    "checkout.session.async_payment_failed": ("checkout_session", "Session"),
    "customer.subscription.created": ("subscription", "Subscription"),
    "customer.subscription.updated": ("subscription", "Subscription"),
    "customer.subscription.deleted": ("subscription", "Subscription"),
    "customer.subscription.paused": ("subscription", "Subscription"),
    "customer.subscription.resumed": ("subscription", "Subscription"),
    "invoice.paid": ("invoice", "Invoice"),
    "invoice.payment_failed": ("invoice", "Invoice"),
    "payment_intent.payment_failed": ("payment_intent", "PaymentIntent"),
    "charge.refunded": ("charge", "Charge"),
    "charge.dispute.created": ("dispute", "Dispute"),
    "charge.dispute.updated": ("dispute", "Dispute"),
    "charge.dispute.closed": ("dispute", "Dispute"),
    "payout.created": ("payout", "Payout"),
    "payout.updated": ("payout", "Payout"),
    "payout.paid": ("payout", "Payout"),
    "payout.failed": ("payout", "Payout"),
    "payout.canceled": ("payout", "Payout"),
}
_SAFE_CODE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")


class PermanentProcessingError(Exception):
    """Event requires configuration or operator action, not another retry."""


class LeaseLost(Exception):
    """A stale worker must not write after another worker has reclaimed the lease."""


def _now() -> datetime:
    return datetime.now(UTC)


def _backoff(attempt: int) -> timedelta:
    return timedelta(seconds=min(3600, 15 * (2 ** min(max(0, attempt - 1), 8))) * random.uniform(0.8, 1.2))


def _error_code(exc: BaseException) -> str:
    value = str(getattr(exc, "code", None) or type(exc).__name__)
    return value[:80] if _SAFE_CODE.fullmatch(value) else "processing_error"


def _enqueue_alert(session: Session, operation_key: str, payload: dict[str, Any]) -> None:
    if session.scalar(select(StripeOutboxJob.id).where(StripeOutboxJob.operation_key == operation_key)) is None:
        session.add(StripeOutboxJob(operation_key=operation_key, job_type="operator_alert", payload=payload, state="pending"))
        session.flush()


def _claim_event(factory: sessionmaker, worker: str) -> dict[str, Any] | None:
    settings, now = get_settings(), _now()
    with factory() as session:
        row = session.scalar(
            select(StripeInboxEvent).where(or_(
                (StripeInboxEvent.state.in_({"pending", "retry"}) & (StripeInboxEvent.next_attempt_at <= now)),
                (StripeInboxEvent.state == "processing") & (StripeInboxEvent.lease_expires_at <= now),
            )).order_by(StripeInboxEvent.next_attempt_at, StripeInboxEvent.received_at)
            .with_for_update(skip_locked=True).limit(1)
        )
        if row is None:
            return None
        if row.event_format != "snapshot" or not row.raw_payload:
            row.state, row.last_error_code = "dead_letter", "thin_event_adapter_required"
            row.lease_owner = row.lease_expires_at = None
            row.updated_at = now
            _enqueue_alert(session, f"stripe-event:{row.stripe_event_id}:thin-event", {
                "event_id": row.stripe_event_id, "event_type": row.event_type,
                "error_code": "thin_event_adapter_required",
                "summary": "Verified Stripe thin notification needs a dedicated adapter before processing.",
            })
            session.commit()
            return None
        row.state = "processing"
        row.attempt_count += 1
        row.fencing_token += 1
        row.lease_owner = worker
        row.lease_expires_at = now + timedelta(seconds=max(15, settings.stripe_event_lease_seconds))
        row.updated_at = now
        result = {
            "id": row.id, "event_id": row.stripe_event_id, "event_type": row.event_type,
            "account_scope": row.account_scope, "livemode": row.livemode,
            "payload": row.raw_payload, "attempt_count": row.attempt_count,
            "fencing_token": row.fencing_token, "lease_owner": worker,
        }
        session.commit()
        return result


def _refresh_current(event: dict[str, Any], account_scope: str) -> dict[str, Any]:
    """Fetch the latest Stripe resource before opening the local business transaction."""
    settings = get_settings()
    if not settings.stripe_secret_key:
        return event
    family = RETRIEVERS.get(str(event.get("type") or ""))
    data, obj = event.get("data"), None
    if isinstance(data, dict) and isinstance(data.get("object"), dict):
        obj = data["object"]
    if not family or not obj or not obj.get("id"):
        return event
    if account_scope not in {"platform", settings.stripe_account_id}:
        raise PermanentProcessingError("stripe_account_scope_mismatch")
    import stripe
    stripe.api_key = settings.stripe_secret_key
    options = {"stripe_account": settings.stripe_account_id} if settings.stripe_account_id else {}
    group, class_name = family
    resource_group = {
        "checkout_session": stripe.checkout,
        "subscription": stripe,
        "invoice": stripe,
        "payment_intent": stripe,
        "charge": stripe,
        "dispute": stripe,
        "payout": stripe,
    }[group]
    if group == "checkout_session":
        current = resource_group.Session.retrieve(str(obj["id"]), **options)
    else:
        current = getattr(resource_group, class_name).retrieve(str(obj["id"]), **options)
    latest = current.to_dict_recursive() if hasattr(current, "to_dict_recursive") else dict(current)
    event["data"]["object"] = latest
    return event


def _stale_failure(event: dict[str, Any]) -> str | None:
    event_type = str(event.get("type") or "")
    obj = ((event.get("data") or {}).get("object") or {})
    if event_type == "checkout.session.async_payment_failed" and obj.get("payment_status") == "paid":
        return "checkout_payment_is_currently_paid"
    if event_type == "invoice.payment_failed" and obj.get("status") == "paid":
        return "invoice_is_currently_paid"
    return None


def _request(path: str, body: bytes, event_id: str) -> Request:
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1", "method": "POST", "scheme": "http", "path": path,
        "raw_path": path.encode(), "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 0), "server": ("stripe-worker", 80), "state": {},
        "clearglass_verified_stripe_event_id": event_id,
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive)


async def _dispatch(session: Session, event: dict[str, Any], event_id: str) -> None:
    from .routers import payments as payments_router
    from .routers import subscriptions as subscriptions_router

    event_type = str(event.get("type") or "")
    body = json.dumps(event, separators=(",", ":"), ensure_ascii=False).encode()
    await payments_router.stripe_webhook(_request("/webhooks/stripe", body, event_id), session)
    obj = ((event.get("data") or {}).get("object") or {})
    if event_type in SUBSCRIPTION_EVENTS or (event_type == "checkout.session.completed" and obj.get("mode") == "subscription"):
        await subscriptions_router.subscription_webhook(_request("/subscriptions/webhook", body, event_id), session)


def process_one_event(factory: sessionmaker = SessionLocal, *, worker_id: str | None = None) -> bool:
    """Process one inbox row using recoverable leases and atomic local completion."""
    worker = worker_id or f"{socket.gethostname()}:{id(factory)}"
    job = _claim_event(factory, worker)
    if job is None:
        return False
    settings = get_settings()
    try:
        event = json.loads(job["payload"])
        if not isinstance(event, dict) or str(event.get("id") or "") != job["event_id"]:
            raise PermanentProcessingError("inbox_event_identity_mismatch")
        if event.get("livemode") is not job["livemode"]:
            raise PermanentProcessingError("inbox_environment_mismatch")
        if not isinstance(event.get("data"), dict) or not isinstance(event["data"].get("object"), dict):
            raise PermanentProcessingError("snapshot_event_data_missing")
        event = _refresh_current(event, job["account_scope"])
        stale = _stale_failure(event)
        with factory() as session:
            row = session.scalar(select(StripeInboxEvent).where(StripeInboxEvent.id == job["id"]).with_for_update())
            if row is None or row.state != "processing" or row.lease_owner != worker or row.fencing_token != job["fencing_token"]:
                raise LeaseLost("stripe_inbox_lease_lost")
            if row.lease_expires_at and row.lease_expires_at < _now():
                raise LeaseLost("stripe_inbox_lease_expired")
            if stale:
                log_event(session, actor="stripe_worker", action="stripe_stale_failure_suppressed",
                          target=job["event_id"], payload={"event_type": job["event_type"], "reason": stale}, result="skipped")
            else:
                await _dispatch(session, event, job["event_id"])
            obj = ((event.get("data") or {}).get("object") or {})
            order_ref = str((obj.get("metadata") or {}).get("cg_order_ref") or "")
            if order_ref:
                co = session.scalar(select(CommercialOrder).where(CommercialOrder.order_ref == order_ref).with_for_update())
                if co is not None and co.reconciliation_required:
                    _enqueue_alert(session, f"stripe-event:{job['event_id']}:order-review", {
                        "event_id": job["event_id"], "event_type": job["event_type"], "order_ref": co.order_ref,
                        "error_code": "commercial_order_reconciliation_required",
                        "summary": "Payment is recorded, but its order is held for financial/state reconciliation.",
                    })
            if job["event_type"] in {"checkout.session.async_payment_failed", "payment_intent.payment_failed", "invoice.payment_failed"}:
                _enqueue_alert(session, f"stripe-event:{job['event_id']}:payment-failure", {
                    "event_id": job["event_id"], "event_type": job["event_type"],
                    "error_code": "payment_failure",
                    "summary": "Stripe reported a payment failure. Review order state and configured customer retry policy.",
                })
            row.state, row.last_error_code, row.processed_at = "succeeded", None, _now()
            row.lease_owner = row.lease_expires_at = None
            row.updated_at = _now()
            session.commit()
        return True
    except LeaseLost:
        logger.info("Stripe inbox lease superseded; stale worker made no business commit")
        return True
    except Exception as exc:
        code = _error_code(exc)
        permanent = isinstance(exc, PermanentProcessingError)
        with factory() as session:
            row = session.scalar(select(StripeInboxEvent).where(StripeInboxEvent.id == job["id"]).with_for_update())
            if row is None or row.state != "processing" or row.lease_owner != worker or row.fencing_token != job["fencing_token"]:
                session.rollback()
                return True
            row.state = "dead_letter" if permanent or row.attempt_count >= max(1, settings.stripe_event_max_attempts) else "retry"
            if row.state == "retry":
                row.next_attempt_at = _now() + _backoff(row.attempt_count)
            row.last_error_code = code
            row.lease_owner = row.lease_expires_at = None
            row.updated_at = _now()
            if row.state == "dead_letter":
                _enqueue_alert(session, f"stripe-event:{row.stripe_event_id}:dead-letter", {
                    "event_id": row.stripe_event_id, "event_type": row.event_type,
                    "error_code": code, "summary": "Stripe event is dead-lettered. Fix the cause before operator replay.",
                })
            session.commit()
        logger.warning("Stripe event failed event_id_suffix=%s code=%s", job["event_id"][-8:], code)
        return True


def _claim_outbox(factory: sessionmaker, worker: str) -> dict[str, Any] | None:
    now, settings = _now(), get_settings()
    with factory() as session:
        row = session.scalar(select(StripeOutboxJob).where(or_(
            (StripeOutboxJob.state.in_({"pending", "retry"}) & (StripeOutboxJob.next_attempt_at <= now)),
            (StripeOutboxJob.state == "processing") & (StripeOutboxJob.lease_expires_at <= now),
        )).order_by(StripeOutboxJob.next_attempt_at, StripeOutboxJob.created_at)
          .with_for_update(skip_locked=True).limit(1))
        if row is None:
            return None
        row.state, row.attempt_count = "processing", row.attempt_count + 1
        row.fencing_token += 1
        row.lease_owner = worker
        row.lease_expires_at = now + timedelta(seconds=max(15, settings.stripe_event_lease_seconds))
        row.updated_at = now
        job = {"id": row.id, "key": row.operation_key, "type": row.job_type, "payload": dict(row.payload or {}),
               "attempt": row.attempt_count, "token": row.fencing_token, "worker": worker}
        session.commit()
        return job


def process_one_outbox(factory: sessionmaker = SessionLocal, *, worker_id: str | None = None) -> bool:
    """Deliver a sanitized operator alert; external delivery is explicitly at-least-once."""
    worker = worker_id or f"{socket.gethostname()}:{id(factory)}:outbox"
    job = _claim_outbox(factory, worker)
    if job is None:
        return False
    settings = get_settings()
    error: str | None = None
    try:
        if job["type"] != "operator_alert":
            raise PermanentProcessingError("unknown_outbox_job_type")
        url = settings.slack_webhook_url.strip()
        if not url:
            raise PermanentProcessingError("alert_destination_not_configured")
        if not url.startswith("https://hooks.slack.com/"):
            raise PermanentProcessingError("alert_destination_invalid")
        import httpx
        p = job["payload"]
        message = (
            "ClearGlass payment operations alert\n"
            f"Type: {str(p.get('event_type') or 'unknown')[:160]}\n"
            f"Event: {str(p.get('event_id') or 'unknown')[:255]}\n"
            f"Order: {str(p.get('order_ref') or 'n/a')[:64]}\n"
            f"Code: {str(p.get('error_code') or 'operator_review')[:80]}\n"
            f"Operation: {job['key'][:300]}\n"
            f"Summary: {str(p.get('summary') or 'Review the operator inbox.')[:700]}"
        )
        response = httpx.post(url, json={"text": message}, timeout=5.0)
        response.raise_for_status()
    except Exception as exc:
        error = _error_code(exc)
    with factory() as session:
        row = session.scalar(select(StripeOutboxJob).where(StripeOutboxJob.id == job["id"]).with_for_update())
        if row is None or row.state != "processing" or row.lease_owner != worker or row.fencing_token != job["token"]:
            session.rollback()
            return True
        row.lease_owner = row.lease_expires_at = None
        row.updated_at = _now()
        if error is None:
            row.state, row.delivered_at, row.last_error_code = "succeeded", _now(), None
        else:
            row.last_error_code = error
            if error in {"PermanentProcessingError", "alert_destination_not_configured", "alert_destination_invalid", "unknown_outbox_job_type"} or row.attempt_count >= max(1, settings.stripe_outbox_max_attempts):
                row.state = "dead_letter"
            else:
                row.state, row.next_attempt_at = "retry", _now() + _backoff(row.attempt_count)
        session.commit()
    return True


def run_worker(*, worker_id: str | None = None, poll_seconds: float = 1.0) -> None:
    worker = worker_id or f"{socket.gethostname()}:{int(time.time())}"
    while True:
        did = process_one_event(worker_id=worker)
        did = process_one_outbox(worker_id=worker) or did
        if not did:
            time.sleep(max(0.1, poll_seconds))


def main() -> None:
    parser = argparse.ArgumentParser(description="ClearGlass durable Stripe inbox/outbox worker")
    parser.add_argument("--once", action="store_true", help="process at most one inbox and one outbox job")
    parser.add_argument("--worker-id", default=None)
    args = parser.parse_args()
    logging.basicConfig(level=get_settings().log_level.upper())
    if args.once:
        process_one_event(worker_id=args.worker_id)
        process_one_outbox(worker_id=args.worker_id)
    else:
        run_worker(worker_id=args.worker_id)


if __name__ == "__main__":
    main()
