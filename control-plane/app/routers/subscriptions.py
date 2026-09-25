"""Durable Stripe subscription synchronization and customer billing endpoints."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import payments, pricebook
from ..audit import log_event
from ..db import get_session
from ..security import rate_limit

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
_webhook_throttle = rate_limit("stripe_subscription_webhook", "rate_limit_webhook_per_minute")
# The portal is unauthenticated by design (the customer has no account with us),
# and each call costs a Stripe API round-trip, so it carries the same per-IP
# throttle as /billing/portal. Without it an anonymous caller can pin the
# endpoint and burn the account's Stripe rate budget for free.
_portal_throttle = rate_limit("subscription_portal", "rate_limit_checkout_per_minute")
# /status is unauthenticated for the same reason and makes the same Stripe round-trip
# per call, so it needs the same ceiling: without one an anonymous caller can pin it
# and burn the account's Stripe rate budget, starving checkout and the webhooks.
# Its own scope keeps a customer polling status from spending their portal budget.
_status_throttle = rate_limit("subscription_status", "rate_limit_checkout_per_minute")

ACTIVE_STATUSES = {"active", "trialing"}


class PortalRequest(BaseModel):
    checkout_session_id: str = Field(min_length=8, max_length=255)


def _price_plan(price_id: str | None) -> str:
    if not price_id:
        return "unknown"
    for offer in pricebook.all_offers():
        if offer.stripe_price_id == price_id:
            return offer.sku
    return "unknown"


def _upsert_subscription(session: Session, obj: dict, *, email: str | None = None) -> dict:
    """Write Stripe's subscription state through to our cache.

    Returns a summary of what changed (``customer_id``, ``plan``, ``status``,
    ``from_status``) so the caller can record the transition in the audit ledger.
    ``from_status`` is ``None`` for a subscription we have not seen before.
    """
    customer_id = obj.get("customer")
    subscription_id = obj.get("id")
    if isinstance(customer_id, dict):
        customer_id = customer_id.get("id")
    if not customer_id or not subscription_id:
        raise ValueError("Stripe subscription is missing customer or id")

    items = ((obj.get("items") or {}).get("data") or [])
    first = items[0] if items else {}
    price = first.get("price") or {}
    price_id = price.get("id")
    recurring = price.get("recurring") or {}
    plan = _price_plan(price_id)
    interval = recurring.get("interval")
    period_end = obj.get("current_period_end")
    period_dt = datetime.fromtimestamp(int(period_end), tz=UTC) if period_end else None

    existing = session.execute(
        text("SELECT id, status FROM subscriptions WHERE stripe_customer_id = :customer_id"),
        {"customer_id": customer_id},
    ).mappings().first()

    values = {
        "customer_id": str(customer_id),
        "subscription_id": str(subscription_id),
        "email": email,
        "plan": plan,
        "price_id": price_id,
        "interval": interval,
        "status": str(obj.get("status") or "unknown"),
        "period_end": period_dt,
        "cancel_at_period_end": bool(obj.get("cancel_at_period_end", False)),
    }

    if existing:
        session.execute(
            text("""
                UPDATE subscriptions
                   SET stripe_subscription_id = :subscription_id,
                       customer_email = COALESCE(:email, customer_email),
                       plan = :plan,
                       stripe_price_id = :price_id,
                       interval = :interval,
                       status = :status,
                       current_period_end = :period_end,
                       cancel_at_period_end = :cancel_at_period_end,
                       updated_at = now()
                 WHERE stripe_customer_id = :customer_id
            """),
            values,
        )
    else:
        session.execute(
            text("""
                INSERT INTO subscriptions
                    (stripe_customer_id, stripe_subscription_id, customer_email, plan,
                     stripe_price_id, interval, status, current_period_end,
                     cancel_at_period_end)
                VALUES
                    (:customer_id, :subscription_id, :email, :plan, :price_id, :interval,
                     :status, :period_end, :cancel_at_period_end)
                ON CONFLICT (stripe_customer_id) DO UPDATE SET
                    stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                    customer_email = COALESCE(EXCLUDED.customer_email, subscriptions.customer_email),
                    plan = EXCLUDED.plan,
                    stripe_price_id = EXCLUDED.stripe_price_id,
                    interval = EXCLUDED.interval,
                    status = EXCLUDED.status,
                    current_period_end = EXCLUDED.current_period_end,
                    cancel_at_period_end = EXCLUDED.cancel_at_period_end,
                    updated_at = now()
            """),
            values,
        )

    return {
        "customer_id": str(customer_id),
        "plan": plan,
        "status": values["status"],
        "from_status": existing["status"] if existing else None,
        "cancel_at_period_end": values["cancel_at_period_end"],
    }


def _mark_event(session: Session, event_id: str, event_type: str) -> bool:
    result = session.execute(
        text("""
            INSERT INTO stripe_events (id, event_type)
            VALUES (:id, :event_type)
            ON CONFLICT (id) DO NOTHING
        """),
        {"id": event_id, "event_type": event_type},
    )
    return result.rowcount == 1


@router.post("/portal", dependencies=[Depends(_portal_throttle)])
def billing_portal(req: PortalRequest) -> dict[str, str]:
    """Create a Stripe-hosted Billing Portal session from a subscription checkout session."""
    try:
        return payments.create_billing_portal_session(req.checkout_session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/status", dependencies=[Depends(_status_throttle)])
def subscription_status(
    checkout_session_id: str,
    session: Session = Depends(get_session),
) -> dict:
    """Return billing state for a Stripe Checkout session without exposing secrets."""
    if len(checkout_session_id) > 255:
        raise HTTPException(status_code=400, detail="invalid checkout session id")
    if not payments.is_live():
        return {"status": "unconfigured", "active": False, "mode": "mock"}

    import stripe

    stripe.api_key = payments._secret_key()  # noqa: SLF001 - same trusted module boundary
    checkout = stripe.checkout.Session.retrieve(checkout_session_id)
    customer_id = checkout.get("customer") if hasattr(checkout, "get") else getattr(checkout, "customer", None)
    if isinstance(customer_id, dict):
        customer_id = customer_id.get("id")
    if not customer_id:
        raise HTTPException(status_code=404, detail="subscription customer not found")

    row = session.execute(
        text("""
            SELECT plan, status, interval, current_period_end, cancel_at_period_end
              FROM subscriptions
             WHERE stripe_customer_id = :customer_id
        """),
        {"customer_id": customer_id},
    ).mappings().first()
    if not row:
        return {"status": "pending", "active": False, "mode": "live"}
    return {
        "plan": row["plan"],
        "status": row["status"],
        "interval": row["interval"],
        "current_period_end": row["current_period_end"].isoformat() if row["current_period_end"] else None,
        "cancel_at_period_end": bool(row["cancel_at_period_end"]),
        "active": row["status"] in ACTIVE_STATUSES,
        "mode": "live",
    }


@router.post("/webhook", dependencies=[Depends(_webhook_throttle)])
async def subscription_webhook(
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    """Verify and durably synchronize Stripe subscription lifecycle events."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    check = payments.verify_webhook(payload, signature)
    if not check["verified"]:
        raise HTTPException(status_code=400, detail="invalid Stripe webhook signature")

    event = check["event"]
    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "unknown")
    if not event_id:
        raise HTTPException(status_code=400, detail="missing Stripe event id")
    if not _mark_event(session, event_id, event_type):
        # Record the redelivery rather than dropping it silently: a run of duplicates
        # is how a misconfigured endpoint or a Stripe retry storm shows up.
        log_event(
            session,
            actor="stripe",
            action="subscription_event_duplicate_skipped",
            target=event_id,
            payload={"event": event_type},
            result="skipped",
        )
        session.commit()
        return {"received": True, "duplicate": True, "type": event_type}

    obj = (event.get("data") or {}).get("object") or {}
    if event_type == "checkout.session.completed":
        if obj.get("mode") == "subscription" and obj.get("subscription"):
            customer_id = obj.get("customer")
            email = ((obj.get("customer_details") or {}).get("email") or obj.get("customer_email"))
            session.execute(
                text("""
                    INSERT INTO subscriptions
                        (stripe_customer_id, stripe_subscription_id, customer_email, plan, status)
                    VALUES (:customer_id, :subscription_id, :email, 'pending', 'pending')
                    ON CONFLICT (stripe_customer_id) DO UPDATE SET
                        stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                        customer_email = COALESCE(EXCLUDED.customer_email, subscriptions.customer_email),
                        updated_at = now()
                """),
                {"customer_id": customer_id, "subscription_id": obj.get("subscription"), "email": email},
            )
            # The subscriptions row already holds the email, so the ledger keys on the
            # Stripe customer id instead of carrying a second copy of the address.
            log_event(
                session,
                actor="stripe",
                action="subscription_checkout_completed",
                target=str(customer_id) if customer_id else None,
                payload={"event": event_type, "subscription_id": obj.get("subscription")},
                result="executed",
            )
    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        change = _upsert_subscription(session, obj)
        log_event(
            session,
            actor="stripe",
            action=f"subscription_{change['status']}",
            target=change["customer_id"],
            payload={
                "event": event_type,
                "plan": change["plan"],
                "from_status": change["from_status"],
                "cancel_at_period_end": change["cancel_at_period_end"],
                "livemode": bool(event.get("livemode")),
            },
            result="executed",
        )
    elif event_type in {"invoice.paid", "invoice.payment_failed"}:
        # Dunning signals are recorded but deliberately do not write status:
        # `customer.subscription.updated` is the single writer for that column, and
        # Stripe sends it alongside these. Two writers would race on redelivery and
        # could park the cache on a stale status.
        customer_id = obj.get("customer")
        if isinstance(customer_id, dict):
            customer_id = customer_id.get("id")
        log_event(
            session,
            actor="stripe",
            action=f"subscription_{event_type.replace('.', '_')}",
            target=str(customer_id) if customer_id else None,
            payload={
                "event": event_type,
                "subscription_id": obj.get("subscription"),
                "attempt_count": obj.get("attempt_count"),
                "next_payment_attempt": obj.get("next_payment_attempt"),
                "amount_due": obj.get("amount_due"),
                "currency": obj.get("currency"),
            },
            # "flagged" is the ledger's existing word for an adverse payment event
            # (payments.py uses it for Stripe failures, paypal.py for adverse captures),
            # so dunning surfaces in the same query as the rest of them.
            result="executed" if event_type == "invoice.paid" else "flagged",
        )
    session.commit()
    return {"received": True, "duplicate": False, "type": event_type}
