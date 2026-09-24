"""The one place a verified payment becomes an order row.

Two processors now settle money into the same ledger — Stripe Checkout and PayPal
Orders — and a third (Etsy receipts) reconciles against it. Each arrives with its
own event vocabulary, but the booking rules are identical and are the rules that
decide whether revenue is counted once, twice, or not at all:

* **Idempotent on redelivery.** Both processors retry webhooks, and both will
  redeliver an event that was already handled. Booking is keyed on the
  processor's own identifier (``orders.external_ref``, unique), so a retry is a
  no-op instead of a second sale.
* **Promotion, not duplication.** The one case that is *not* a no-op is an order
  that was booked ``pending`` and whose payment later settles. That promotes the
  existing row; inserting a second row would double-count the same money.
* **Every transition is logged.** The append-only ``events`` ledger is what the
  daily reconciliation reads, so a skipped duplicate is recorded as explicitly as
  a booked sale.
* **Money that leaves is subtracted.** A refund or a dispute changes the order it
  reverses (:func:`record_refund`, :func:`record_dispute`), and a refunded order
  is never promoted back to ``paid`` by a late or redelivered settlement event.
  :func:`revenue_breakdown` is the one definition of what counts as confirmed.

Keeping this in one module instead of one copy per processor is deliberate: two
implementations of "book this payment exactly once" drift, and the way they drift
is that one of them starts counting a retry as revenue.
"""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import log_event
from .models import Order

#: Stripe dispute statuses in which the money is held, not ours.
OPEN_DISPUTE_STATUSES = frozenset(
    {"warning_needs_response", "warning_under_review", "needs_response", "under_review"}
)
#: The dispute was lost: the money went back to the cardholder.
LOST_DISPUTE_STATUSES = frozenset({"lost"})
#: Order statuses that mean money was received at some point.
SETTLED_STATUSES = frozenset({"paid", "refunded"})

#: Normalized destination-address keys every processor maps its own shape onto.
SHIPPING_FIELDS = (
    "name",
    "address1",
    "address2",
    "city",
    "state_code",
    "country_code",
    "zip",
    "email",
)


def apply_shipping(order: Order, shipping: Mapping[str, Any]) -> None:
    """Copy a normalized destination address onto the order."""
    order.ship_to_name = shipping.get("name")
    order.ship_to_address1 = shipping.get("address1")
    order.ship_to_address2 = shipping.get("address2")
    order.ship_to_city = shipping.get("city")
    order.ship_to_state = shipping.get("state_code")
    order.ship_to_country = shipping.get("country_code")
    order.ship_to_zip = shipping.get("zip")
    order.ship_to_email = shipping.get("email")


def record_payment_order(
    session: Session,
    *,
    actor: str,
    external_ref: str | None,
    total: Decimal,
    currency: str,
    source: str,
    status: str,
    verified: bool,
    event: str,
    shipping: Mapping[str, Any] | None = None,
    environment: str = "unknown",
    payment_intent: str | None = None,
    attribution: Mapping[str, str] | None = None,
) -> Order | None:
    """Book (or promote) an order idempotently, keyed on the processor's own id.

    ``actor`` names the processor for the audit trail (``stripe``, ``paypal``).
    ``status`` is this platform's payment state (``paid`` | ``pending`` |
    ``failed``), already translated from the processor's vocabulary by the caller —
    this function does not know what any given event type means.

    Returns the affected :class:`~app.models.Order`, or ``None`` when the event was
    a duplicate and nothing changed. A caller that starts fulfillment must treat
    ``None`` as "already handled" and do nothing, or a redelivered capture ships a
    second parcel for one payment.
    """
    existing = (
        session.scalar(select(Order).where(Order.external_ref == external_ref))
        if external_ref
        else None
    )

    if existing is not None:
        # A refund is final. Without this, a redelivered or late settlement event
        # (status "paid" != "refunded") would promote the order back to paid and
        # count the returned money as revenue again.
        if existing.status == "refunded":
            log_event(
                session,
                actor=actor,
                action="order_event_after_refund_skipped",
                target=str(existing.id),
                payload={"verified": verified, "external_ref": external_ref, "event": event},
                result="skipped",
            )
            return None
        if existing.status == status:
            log_event(
                session,
                actor=actor,
                action="order_event_duplicate_skipped",
                target=str(existing.id),
                payload={"verified": verified, "external_ref": external_ref, "event": event},
                result="skipped",
            )
            return None
        previous, existing.status = existing.status, status
        existing.total = total
        existing.environment = environment
        # A pending order settling is the point at which an asynchronous payment
        # method finally yields a shippable order, so re-apply the address here
        # too: the promoting event carries it and the original may not have.
        if shipping is not None:
            apply_shipping(existing, shipping)
        existing.payment_intent = existing.payment_intent or payment_intent
        if attribution and not existing.utm_campaign:
            _apply_attribution(existing, attribution)
        session.flush()
        log_event(
            session,
            actor=actor,
            action=f"order_{status}",
            target=str(existing.id),
            payload={
                "verified": verified,
                "event": event,
                "from_status": previous,
                "amount_total": str(total),
            },
            result="executed",
        )
        return existing

    order = Order(
        status=status,
        total=total,
        currency=currency,
        source=source,
        external_ref=external_ref,
        environment=environment,
        payment_intent=payment_intent,
        amount_refunded=Decimal(0),
    )
    if shipping is not None:
        apply_shipping(order, shipping)
    if attribution:
        _apply_attribution(order, attribution)
    session.add(order)
    session.flush()
    log_event(
        session,
        actor=actor,
        action=f"order_{status}",
        target=str(order.id),
        payload={"verified": verified, "event": event, "amount_total": str(total)},
        result="executed",
    )
    return order


def _apply_attribution(order: Order, attribution: Mapping[str, str]) -> None:
    order.utm_source = attribution.get("utm_source")
    order.utm_medium = attribution.get("utm_medium")
    order.utm_campaign = attribution.get("utm_campaign")


def _order_for_payment(
    session: Session, payment_intent: str | None, external_ref: str | None,
) -> Order | None:
    """Stripe refunds name a PaymentIntent; PayPal refunds name the capture,
    which is the order's ``external_ref``."""
    if payment_intent:
        return session.scalar(select(Order).where(Order.payment_intent == payment_intent))
    if external_ref:
        return session.scalar(select(Order).where(Order.external_ref == external_ref))
    return None


def record_refund(
    session: Session,
    *,
    actor: str,
    payment_intent: str | None = None,
    external_ref: str | None = None,
    amount_refunded: Decimal,
    fully_refunded: bool,
    verified: bool,
    event: str,
    reference: str | None,
) -> Order | None:
    """Apply a processor's refund total to the order it reverses.

    ``amount_refunded`` is cumulative (Stripe's ``charge.amount_refunded``), so it
    is *set*, never added: a redelivered event lands on the same value and is
    skipped. A refund that matches no order is flagged for a human rather than
    dropped, because it is still money that left the account.

    Returns the changed order, or ``None`` when nothing changed.
    """
    order = _order_for_payment(session, payment_intent, external_ref)
    if order is None:
        log_event(
            session,
            actor=actor,
            action="refund_unmatched",
            target=reference,
            payload={
                "verified": verified,
                "event": event,
                "payment_intent": payment_intent,
                "external_ref": external_ref,
                "amount_refunded": str(amount_refunded),
            },
            result="flagged",
        )
        return None

    amount = min(amount_refunded, Decimal(order.total))
    status = "refunded" if fully_refunded else order.status
    if Decimal(order.amount_refunded or 0) == amount and order.status == status:
        log_event(
            session,
            actor=actor,
            action="refund_duplicate_skipped",
            target=str(order.id),
            payload={"verified": verified, "event": event, "reference": reference},
            result="skipped",
        )
        return None

    previous_status, previous_amount = order.status, Decimal(order.amount_refunded or 0)
    order.amount_refunded = amount
    order.status = status
    session.flush()
    log_event(
        session,
        actor=actor,
        action="order_refunded" if fully_refunded else "order_partially_refunded",
        target=str(order.id),
        payload={
            "verified": verified,
            "event": event,
            "reference": reference,
            "from_status": previous_status,
            "amount_refunded": str(amount),
            "previous_amount_refunded": str(previous_amount),
        },
        result="executed",
    )
    return order


def record_dispute(
    session: Session,
    *,
    actor: str,
    payment_intent: str | None = None,
    external_ref: str | None = None,
    dispute_status: str,
    verified: bool,
    event: str,
    reference: str | None,
) -> Order | None:
    """Record a dispute's current status on the order it concerns.

    While a dispute is open the money is held, and a lost dispute returns it, so
    :func:`revenue_breakdown` keeps both out of confirmed revenue. Won and
    warning-closed disputes count normally again.
    """
    order = _order_for_payment(session, payment_intent, external_ref)
    if order is None:
        log_event(
            session,
            actor=actor,
            action="dispute_unmatched",
            target=reference,
            payload={
                "verified": verified,
                "event": event,
                "payment_intent": payment_intent,
                "external_ref": external_ref,
                "dispute_status": dispute_status,
            },
            result="flagged",
        )
        return None
    if order.dispute_status == dispute_status:
        log_event(
            session,
            actor=actor,
            action="dispute_duplicate_skipped",
            target=str(order.id),
            payload={"verified": verified, "event": event, "reference": reference},
            result="skipped",
        )
        return None

    previous, order.dispute_status = order.dispute_status, dispute_status
    session.flush()
    log_event(
        session,
        actor=actor,
        action=f"order_dispute_{dispute_status}",
        target=str(order.id),
        payload={
            "verified": verified,
            "event": event,
            "reference": reference,
            "from_status": previous,
        },
        # An open or lost dispute needs a human; anything else is informational.
        result="flagged" if dispute_status in OPEN_DISPUTE_STATUSES | LOST_DISPUTE_STATUSES else "executed",
    )
    return order


def revenue_breakdown(orders: list[Order]) -> dict[str, Decimal]:
    """The one definition of confirmed revenue, from orders that received money.

    ``confirmed`` = ``gross`` − ``refunded`` − money held in open disputes −
    money lost to disputes. Callers filter the orders (live only, a date range);
    this decides how each one counts.
    """
    gross = refunded = disputed_open = dispute_lost = Decimal(0)
    for order in orders:
        if order.status not in SETTLED_STATUSES:
            continue
        total = Decimal(order.total)
        refund = min(Decimal(order.amount_refunded or 0), total)
        remaining = total - refund
        gross += total
        refunded += refund
        if order.dispute_status in OPEN_DISPUTE_STATUSES:
            disputed_open += remaining
        elif order.dispute_status in LOST_DISPUTE_STATUSES:
            dispute_lost += remaining
    return {
        "gross": gross,
        "refunded": refunded,
        "disputed_open": disputed_open,
        "dispute_lost": dispute_lost,
        "confirmed": gross - refunded - disputed_open - dispute_lost,
    }
