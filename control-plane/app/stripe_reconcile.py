"""Read-only Stripe reconciliation and safe inbox backfill.

This command only reads Stripe, adds missing event jobs, and raises local operator
exceptions. It never charges, refunds, changes prices, alters payouts, or sends money.
Schedule the recent profile every 15 minutes and the daily profile once per day.
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .audit import log_event
from .config import get_settings
from .db import SessionLocal
from .models import (
    CommercialOrder,
    Order,
    ServiceOrder,
    StripeInboxEvent,
    StripeOutboxJob,
    StripeReconciliationCheckpoint,
)

logger = logging.getLogger("clearglass.stripe_reconcile")
EVENT_TYPES = [
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
    "checkout.session.async_payment_failed",
    "invoice.paid",
    "invoice.payment_failed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "customer.subscription.paused",
    "customer.subscription.resumed",
    "payment_intent.payment_failed",
    "charge.refunded",
    "charge.dispute.created",
    "charge.dispute.updated",
    "charge.dispute.closed",
    "payout.created",
    "payout.updated",
    "payout.paid",
    "payout.failed",
    "payout.canceled",
]


def _now() -> datetime:
    return datetime.now(UTC)


def _dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict_recursive"):
        return value.to_dict_recursive()
    if isinstance(value, dict):
        return value
    return dict(value)


def _enqueue_alert(session: Session, key: str, payload: dict[str, Any]) -> None:
    if session.scalar(select(StripeOutboxJob.id).where(StripeOutboxJob.operation_key == key)) is None:
        session.add(StripeOutboxJob(
            operation_key=key, job_type="operator_alert", payload=payload, state="pending",
        ))
        session.flush()


def _record_event(session: Session, event: dict[str, Any], account_scope: str) -> bool:
    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")
    data = event.get("data")
    obj = data.get("object") if isinstance(data, dict) else None
    snapshot = isinstance(obj, dict)
    related = obj.get("id") if snapshot else (
        (event.get("related_object") or {}).get("id")
        if isinstance(event.get("related_object"), dict) else None
    )
    raw = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
    row = StripeInboxEvent(
        account_scope=account_scope,
        stripe_event_id=event_id,
        event_type=event_type,
        related_object_id=str(related) if related else None,
        livemode=bool(event.get("livemode")),
        event_format="snapshot" if snapshot else "thin",
        source="reconciliation",
        verification_method="stripe_api_read",
        verified_at=_now(),
        payload_sha256=__import__("hashlib").sha256(raw.encode("utf-8")).hexdigest(),
        raw_payload=raw,
        state="pending",
        last_error_code=None if snapshot else "thin_event_adapter_required",
    )
    try:
        # Savepoint preserves the page/checkpoint transaction if webhook ingress won
        # the uniqueness race after this API page was read.
        with session.begin_nested():
            session.add(row)
            session.flush()
        return True
    except IntegrityError:
        return False


def _client():
    settings = get_settings()
    key = settings.stripe_secret_key.strip()
    if not key:
        raise RuntimeError("Stripe reconciliation requires STRIPE_SECRET_KEY")
    if key.startswith(("sk_live_", "rk_live_")):
        expected_live = True
    elif key.startswith(("sk_test_", "rk_test_")):
        expected_live = False
    else:
        raise RuntimeError("Stripe API key environment cannot be established")
    import stripe
    stripe.api_key = key
    return stripe, expected_live


def reconcile_events(*, profile: str = "recent", max_pages: int = 20, factory=SessionLocal) -> dict[str, Any]:
    """Page through an overlapping Stripe Events API window and enqueue unseen events."""
    settings = get_settings()
    stripe, expected_live = _client()
    account_scope = settings.stripe_account_id.strip() or "platform"
    window = timedelta(days=30) if profile == "daily" else timedelta(hours=2)
    checkpoint_name = f"stripe-events-{profile}"

    with factory() as session:
        cp = session.get(StripeReconciliationCheckpoint, checkpoint_name)
        if cp is None:
            cp = StripeReconciliationCheckpoint(name=checkpoint_name)
            session.add(cp)
            session.flush()
        if cp.cursor_event_id and cp.window_start_at:
            start = cp.window_start_at
            cursor = cp.cursor_event_id
        else:
            start = _now() - window
            cursor = None
            cp.window_start_at = start
            cp.cursor_event_id = None
            cp.last_result = "running"
            session.commit()

    pages = seen = inserted = 0
    has_more = True
    while has_more and pages < max(1, min(max_pages, 100)):
        params: dict[str, Any] = {
            "created": {"gte": int(start.timestamp())},
            "limit": 100,
            "types": EVENT_TYPES,
        }
        if cursor:
            params["starting_after"] = cursor
        if settings.stripe_account_id:
            params["stripe_account"] = settings.stripe_account_id
        page = stripe.Event.list(**params)
        events = list(getattr(page, "data", []) or [])
        has_more = bool(getattr(page, "has_more", False))
        pages += 1

        with factory() as session:
            for item in events:
                event = _dict(item)
                if bool(event.get("livemode")) is not expected_live:
                    # Do not silently mix modes even if account configuration was changed
                    # while a sweep was in progress.
                    continue
                event_id = str(event.get("id") or "")
                if not event_id.startswith("evt_"):
                    continue
                if _record_event(session, event, account_scope):
                    inserted += 1
                seen += 1
                cursor = event_id
            cp = session.get(StripeReconciliationCheckpoint, checkpoint_name)
            cp.window_start_at = start
            cp.cursor_event_id = cursor if has_more and events else None
            cp.last_result = f"running; profile={profile}; pages={pages}; scanned={seen}; inserted={inserted}"
            if not has_more:
                cp.last_completed_at = _now()
                cp.last_result = f"complete; profile={profile}; pages={pages}; scanned={seen}; inserted={inserted}"
            session.commit()
        if not events:
            has_more = False

    # Keep a cursor when page cap is reached; the next invocation resumes this scan.
    with factory() as session:
        cp = session.get(StripeReconciliationCheckpoint, checkpoint_name)
        if has_more:
            cp.cursor_event_id = cursor
            cp.window_start_at = start
            cp.last_result = f"partial; profile={profile}; pages={pages}; scanned={seen}; inserted={inserted}; cursor retained"
        session.commit()
    return {"profile": profile, "pages": pages, "events_scanned": seen, "events_enqueued": inserted, "partial": has_more}


def _current_checkout_snapshot(stripe, checkout_id: str, account_id: str | None) -> dict[str, Any]:
    options = {"stripe_account": account_id} if account_id else {}
    return _dict(stripe.checkout.Session.retrieve(checkout_id, **options))


def reconcile_paid_checkouts(*, limit: int = 200, factory=SessionLocal) -> dict[str, int]:
    """Compare current Stripe Checkout state against the local paid-order ledger."""
    settings = get_settings()
    stripe, expected_live = _client()
    if not expected_live:
        return {"checked": 0, "mismatches": 0, "skipped": 0}
    account = settings.stripe_account_id.strip() or None
    with factory() as session:
        orders = session.execute(
            select(
                CommercialOrder.order_ref,
                CommercialOrder.provider_checkout_ref,
                CommercialOrder.amount,
                CommercialOrder.currency,
                CommercialOrder.payment_order_id,
                CommercialOrder.payment_state,
                CommercialOrder.reconciliation_required,
                CommercialOrder.created_at,
            ).where(
                CommercialOrder.provider == "stripe",
                CommercialOrder.environment == "live",
                CommercialOrder.provider_checkout_ref.is_not(None),
                CommercialOrder.payment_state.in_({"PAID", "PARTIALLY_REFUNDED", "REFUNDED", "DISPUTED", "CHARGEBACK"}),
            ).order_by(CommercialOrder.created_at.desc()).limit(max(1, min(limit, 500))
        ).all()

    checked = mismatches = skipped = 0
    for record in orders:
        order_ref, session_id = record.order_ref, record.provider_checkout_ref
        if not session_id or not str(session_id).startswith("cs_"):
            skipped += 1
            continue
        try:
            current = _current_checkout_snapshot(stripe, str(session_id), account)
        except Exception as exc:
            with factory() as session:
                _enqueue_alert(session, f"reconcile:checkout-read-failed:{order_ref}", {
                    "event_type": "reconciliation", "event_id": str(session_id),
                    "order_ref": str(order_ref), "error_code": f"stripe_read_{type(exc).__name__}"[:80],
                    "summary": "Could not read the current Stripe Checkout Session during reconciliation.",
                })
                session.commit()
            skipped += 1
            continue
        checked += 1
        issues: list[str] = []
        if current.get("payment_status") not in {"paid", "no_payment_required"}:
            issues.append("STRIPE_SESSION_NOT_PAID")
        if (current.get("client_reference_id") or "") != order_ref:
            issues.append("CHECKOUT_ORDER_REFERENCE_MISMATCH")
        if ((current.get("metadata") or {}).get("cg_order_ref") or "") != order_ref:
            issues.append("CHECKOUT_METADATA_MISMATCH")
        if str(current.get("currency") or "").upper() != str(record.currency or "").upper():
            issues.append("CHECKOUT_CURRENCY_MISMATCH")
        amount_total = current.get("amount_total")
        if amount_total is None:
            issues.append("CHECKOUT_AMOUNT_MISSING")
        elif record.payment_order_id is not None:
            with factory() as session:
                payment = session.get(Order, record.payment_order_id)
                if payment is None or int(Decimal(payment.total) * 100) != int(amount_total):
                    issues.append("CHECKOUT_LEDGER_AMOUNT_MISMATCH")
        elif record.payment_state in {"PAID", "PARTIALLY_REFUNDED", "REFUNDED", "DISPUTED", "CHARGEBACK"}:
            issues.append("CHECKOUT_PAYMENT_LEDGER_LINK_MISSING")
        if amount_total is not None and Decimal(int(amount_total)) < Decimal(record.amount) * 100:
            issues.append("CHECKOUT_BELOW_CATALOG_PRICE")
        if not issues:
            continue
        mismatches += 1
        reason = ",".join(sorted(set(issues)))
        with factory() as session:
            co = session.scalar(select(CommercialOrder).where(CommercialOrder.order_ref == order_ref).with_for_update())
            if co is not None:
                co.reconciliation_required = True
                co.reconciliation_reason = reason
                log_event(session, actor="stripe_reconciler", action="checkout_reconciliation_mismatch",
                          target=co.order_ref,
                          payload={"stripe_session": str(session_id), "issues": sorted(set(issues))},
                          result="flagged")
                _enqueue_alert(session, f"reconcile:checkout-mismatch:{order_ref}:{reason}", {
                    "event_type": "checkout_reconciliation",
                    "event_id": str(session_id),
                    "order_ref": str(order_ref),
                    "error_code": "checkout_state_mismatch",
                    "summary": "Current Stripe Checkout state and the local payment/order ledger disagree: " + reason,
                })
                session.commit()
    return {"checked": checked, "mismatches": mismatches, "skipped": skipped}


def flag_incomplete_fulfillment(*, grace_minutes: int = 5, factory=SessionLocal) -> dict[str, int]:
    """Create operator alerts for paid live service orders that lack delivery records."""
    cutoff = _now() - timedelta(minutes=max(1, grace_minutes))
    with factory() as session:
        rows = session.execute(
            select(CommercialOrder.order_ref, CommercialOrder.payment_order_id, CommercialOrder.sku)
            .where(
                CommercialOrder.payment_state == "PAID",
                CommercialOrder.environment == "live",
                CommercialOrder.reconciliation_required.is_(False),
                CommercialOrder.created_at < cutoff,
            ).order_by(CommercialOrder.created_at.asc()).limit(500)
        ).all()
    flagged = 0
    for row in rows:
        if not row.payment_order_id:
            reason = "paid_order_missing_payment_ledger_link"
        else:
            with factory() as session:
                service = session.scalar(select(ServiceOrder).where(ServiceOrder.order_id == row.payment_order_id))
            if service is not None:
                continue
            reason = "paid_service_missing_fulfillment_record"
        with factory() as session:
            _enqueue_alert(session, f"reconcile:fulfillment:{row.order_ref}:{reason}", {
                "event_type": "fulfillment_reconciliation",
                "event_id": str(row.order_ref),
                "order_ref": str(row.order_ref),
                "error_code": reason,
                "summary": "A paid live ClearGlass service order has no matching service-delivery record. Review before manual repair.",
            })
            log_event(session, actor="stripe_reconciler", action="paid_fulfillment_missing",
                      target=str(row.order_ref), payload={"sku": row.sku, "reason": reason}, result="flagged")
            session.commit()
        flagged += 1
    return {"incomplete_fulfillment": flagged}


def run(profile: str, *, max_pages: int = 20) -> dict[str, Any]:
    events = reconcile_events(profile=profile, max_pages=max_pages)
    results: dict[str, Any] = {"events": events}
    results["checkout_comparison"] = reconcile_paid_checkouts()
    results["fulfillment_review"] = flag_incomplete_fulfillment()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="ClearGlass Stripe reconciliation and missing-event backfill")
    parser.add_argument("--profile", choices=("recent", "daily"), default="recent")
    parser.add_argument("--max-pages", type=int, default=20)
    args = parser.parse_args()
    logging.basicConfig(level=get_settings().log_level.upper())
    print(json.dumps(run(args.profile, max_pages=args.max_pages), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
