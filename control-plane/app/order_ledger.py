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
    )
    if shipping is not None:
        apply_shipping(order, shipping)
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
