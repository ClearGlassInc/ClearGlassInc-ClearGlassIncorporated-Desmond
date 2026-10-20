"""Signed Stripe webhook ingress into a durable, account-scoped inbox.

The endpoint does no payment/fulfillment work. It verifies the untouched raw request,
inserts once, commits, and only then acknowledges Stripe. Workers own business effects.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .. import payments
from ..config import get_settings
from ..db import get_session
from ..models import StripeInboxEvent
from ..security import rate_limit, require_admin

router = APIRouter(tags=["stripe-payment-ops"])
logger = logging.getLogger("clearglass.stripe_inbox")
_webhook_throttle = rate_limit("stripe_payment_ops_ingress", "rate_limit_webhook_per_minute")


def _expected_livemode() -> bool | None:
    """Resolve the configured mode without ever guessing from event contents."""
    settings = get_settings()
    explicit = settings.stripe_expected_livemode.strip().lower()
    if explicit in {"live", "true", "1"}:
        return True
    if explicit in {"test", "false", "0"}:
        return False
    key = settings.stripe_secret_key.strip()
    if key.startswith(("sk_live_", "rk_live_")):
        return True
    if key.startswith(("sk_test_", "rk_test_")):
        return False
    return None


def _signature_check(payload: bytes, signature: str) -> tuple[dict, str]:
    """Verify current secret or the previous one before its explicit rotation cutoff."""
    if not payments._webhook_secret():  # same module boundary as the legacy integration
        raise HTTPException(status_code=503, detail="Stripe webhook verification is not configured")
    check = payments.verify_webhook(payload, signature)
    if check["verified"]:
        return check, "current_secret"

    settings = get_settings()
    previous = settings.stripe_webhook_previous_secret.strip()
    cutoff_raw = settings.stripe_webhook_previous_secret_accept_until.strip()
    if previous and cutoff_raw:
        try:
            cutoff = datetime.fromisoformat(cutoff_raw.replace("Z", "+00:00"))
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=UTC)
        except ValueError:
            cutoff = datetime.min.replace(tzinfo=UTC)
        if datetime.now(UTC) <= cutoff:
            previous_check = payments.verify_webhook(payload, signature, secret_override=previous)
            if previous_check["verified"]:
                return previous_check, "previous_secret"
    raise HTTPException(status_code=400, detail="Stripe signature verification failed")


async def _bounded_raw_body(request: Request, max_bytes: int) -> bytes:
    parts: list[bytes] = []
    size = 0
    async for part in request.stream():
        size += len(part)
        if size > max_bytes:
            raise HTTPException(status_code=413, detail="Stripe webhook payload is too large")
        parts.append(part)
    return b"".join(parts)


async def _ingest(request: Request, session: Session) -> dict[str, object]:
    settings = get_settings()
    payload = await _bounded_raw_body(request, max(1024, settings.stripe_webhook_max_payload_bytes))
    signature = request.headers.get("stripe-signature", "")
    check, verification_method = _signature_check(payload, signature)
    event = check.get("event")
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="Invalid Stripe event")
    event_id = str(event.get("id") or "").strip()
    event_type = str(event.get("type") or "").strip()
    if not event_id.startswith("evt_") or len(event_id) > 255 or not event_type or len(event_type) > 160:
        raise HTTPException(status_code=400, detail="Invalid Stripe event identity")

    livemode = event.get("livemode")
    if not isinstance(livemode, bool):
        raise HTTPException(status_code=400, detail="Stripe event environment is missing")
    expected = _expected_livemode()
    if expected is not None and livemode is not expected:
        raise HTTPException(status_code=400, detail="Stripe event environment mismatch")
    if settings.app_env.strip().lower() in {"production", "prod"} and expected is None:
        raise HTTPException(status_code=503, detail="Stripe expected environment is not configured")

    account_id = str(event.get("account") or "").strip()
    expected_account = settings.stripe_account_id.strip()
    if expected_account:
        if account_id != expected_account:
            raise HTTPException(status_code=400, detail="Stripe account scope mismatch")
        account_scope = expected_account
    else:
        if account_id:
            raise HTTPException(status_code=400, detail="Connected-account events are not enabled")
        account_scope = "platform"

    data = event.get("data")
    obj = data.get("object") if isinstance(data, dict) else None
    is_snapshot = isinstance(obj, dict) and bool(event.get("data"))
    # Thin notifications have an object reference but no snapshot data.object. They
    # are persisted distinctly and routed to an explicit dead-letter path unless a
    # configured thin-event adapter can safely retrieve their referenced resource.
    event_format = "snapshot" if is_snapshot else "thin"
    related_object_id = None
    if is_snapshot:
        related_object_id = str(obj.get("id") or "") or None
    else:
        related = event.get("related_object")
        if isinstance(related, dict):
            related_object_id = str(related.get("id") or "") or None
        elif isinstance(event.get("object"), str):
            related_object_id = event.get("object")

    row = StripeInboxEvent(
        account_scope=account_scope,
        stripe_event_id=event_id,
        event_type=event_type,
        related_object_id=related_object_id,
        livemode=livemode,
        event_format=event_format,
        source="webhook",
        verification_method=verification_method,
        verified_at=datetime.now(UTC),
        payload_sha256=hashlib.sha256(payload).hexdigest(),
        raw_payload=payload.decode("utf-8"),
        # Persist thin notifications too. The worker will explicitly dead-letter
        # them with a sanitized operator alert instead of parsing them as snapshots.
        state="pending",
        last_error_code=None if event_format == "snapshot" else "thin_event_adapter_required",
    )

    try:
        session.add(row)
        session.flush()
        session.commit()  # Receipt is acknowledged only after this durable commit.
        return {
            "received": True,
            "duplicate": False,
            "event_id": event_id,
            "state": row.state,
            "event_format": event_format,
        }
    except SQLAlchemyError as exc:
        session.rollback()
        # The unique conflict path is a harmless redelivery. Query only after rollback
        # so Postgres is not left in an aborted transaction.
        try:
            existing = session.execute(
                text("""
                    SELECT state FROM stripe_event_inbox
                     WHERE account_scope = :account_scope AND stripe_event_id = :event_id
                """),
                {"account_scope": account_scope, "event_id": event_id},
            ).first()
            if existing is not None:
                session.commit()
                return {
                    "received": True,
                    "duplicate": True,
                    "event_id": event_id,
                    "state": existing[0],
                    "event_format": event_format,
                }
        except SQLAlchemyError:
            session.rollback()
        logger.warning("Stripe inbox persistence failed; event_id_hash=%s", hashlib.sha256(event_id.encode()).hexdigest()[:16])
        raise HTTPException(status_code=503, detail="Stripe event could not be durably stored") from exc


@router.post("/webhooks/stripe", dependencies=[Depends(_webhook_throttle)])
async def stripe_payment_webhook(request: Request, session: Session = Depends(get_session)) -> dict[str, object]:
    """Signed ingress for payment, refund, dispute, payout and checkout events."""
    return await _ingest(request, session)


@router.post("/subscriptions/webhook", dependencies=[Depends(_webhook_throttle)])
async def stripe_subscription_webhook(request: Request, session: Session = Depends(get_session)) -> dict[str, object]:
    """The legacy subscription URL remains valid but now shares the same durable inbox."""
    return await _ingest(request, session)


@router.get("/ops/stripe-inbox")
def list_inbox(
    state: str | None = None,
    limit: int = 100,
    session: Session = Depends(get_session),
    _admin: str = Depends(require_admin),
) -> dict[str, object]:
    """Inspect inbox work without exposing the raw Stripe payload."""
    allowed = {"pending", "processing", "retry", "succeeded", "dead_letter"}
    if state and state not in allowed:
        raise HTTPException(status_code=400, detail="Invalid inbox state")
    stmt = (
        session.query(StripeInboxEvent)
        .filter(StripeInboxEvent.state == state) if state else session.query(StripeInboxEvent)
    )
    rows = stmt.order_by(StripeInboxEvent.received_at.desc()).limit(max(1, min(limit, 250))).all()
    return {
        "items": [{
            "event_id": r.stripe_event_id,
            "type": r.event_type,
            "state": r.state,
            "attempt_count": r.attempt_count,
            "last_error_code": r.last_error_code,
            "received_at": r.received_at.isoformat() if r.received_at else None,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
        } for r in rows]
    }


@router.post("/ops/stripe-inbox/{event_id}/replay")
def replay_dead_letter(
    event_id: str,
    session: Session = Depends(get_session),
    _admin: str = Depends(require_admin),
) -> dict[str, object]:
    """Explicitly requeue one dead-letter snapshot, with audit trail."""
    from sqlalchemy import select
    from ..audit import log_event

    row = session.scalar(
        select(StripeInboxEvent).where(StripeInboxEvent.stripe_event_id == event_id).with_for_update()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Inbox event not found")
    if row.state != "dead_letter":
        raise HTTPException(status_code=409, detail="Only dead-letter events may be replayed")
    if not row.raw_payload:
        raise HTTPException(status_code=409, detail="The retained event payload has expired; reconcile it from Stripe instead")
    row.state = "retry"
    row.next_attempt_at = datetime.now(UTC)
    row.last_error_code = None
    row.lease_owner = None
    row.lease_expires_at = None
    row.updated_at = datetime.now(UTC)
    log_event(
        session,
        actor="operator",
        action="stripe_inbox_replay_requested",
        target=row.stripe_event_id,
        payload={"event_type": row.event_type, "fencing_token": row.fencing_token},
        result="executed",
    )
    session.commit()
    return {"requeued": True, "event_id": row.stripe_event_id, "state": row.state}
