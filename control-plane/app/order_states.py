"""ClearGlass order ids and the payment state machine.

A ClearGlass order (``CG-ORD-2026-7K3M9QXT``) exists before the buyer picks a
processor, so one record can say which offer was bought, at what server-set
price, from which campaign, and through Stripe or PayPal. Its payment state
moves only along :data:`TRANSITIONS`, and every state that asserts something
about money (:data:`PROVIDER_STATES`) can be entered only on verified processor
evidence: a signed webhook, never a browser redirect or a request body.

Fulfillment is not stored here. It is derived from the service order or the
shipment that actually exists (:func:`fulfillment_state`), so the two can never
disagree.

Stdlib only, like ``governance.py``, so it can be tested without a database.
"""
from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime

# --- payment states -----------------------------------------------------------
CREATED = "CREATED"
CHECKOUT_STARTED = "CHECKOUT_STARTED"
PAYMENT_PENDING = "PAYMENT_PENDING"
PAYMENT_PROCESSING = "PAYMENT_PROCESSING"
PAID = "PAID"
PAYMENT_FAILED = "PAYMENT_FAILED"
CANCELED = "CANCELED"
REFUNDED = "REFUNDED"
PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
DISPUTED = "DISPUTED"
CHARGEBACK = "CHARGEBACK"

PAYMENT_STATES = (
    CREATED,
    CHECKOUT_STARTED,
    PAYMENT_PENDING,
    PAYMENT_PROCESSING,
    PAID,
    PAYMENT_FAILED,
    CANCELED,
    REFUNDED,
    PARTIALLY_REFUNDED,
    DISPUTED,
    CHARGEBACK,
)

# --- fulfillment states (derived, never stored) ---------------------------------
NOT_STARTED = "NOT_STARTED"
FULFILLMENT_PENDING = "FULFILLMENT_PENDING"
FULFILLING = "FULFILLING"
COMPLETED = "COMPLETED"
HELD = "HELD"

FULFILLMENT_STATES = (NOT_STARTED, FULFILLMENT_PENDING, FULFILLING, COMPLETED, HELD)

#: Allowed moves. Anything not listed is refused.
TRANSITIONS: dict[str, frozenset[str]] = {
    CREATED: frozenset({CHECKOUT_STARTED, CANCELED}),
    # CHECKOUT_STARTED -> CHECKOUT_STARTED is the buyer switching processor.
    CHECKOUT_STARTED: frozenset(
        {CHECKOUT_STARTED, PAYMENT_PENDING, PAYMENT_PROCESSING, PAID, PAYMENT_FAILED, CANCELED}
    ),
    PAYMENT_PENDING: frozenset({PAYMENT_PROCESSING, PAID, PAYMENT_FAILED, CANCELED}),
    PAYMENT_PROCESSING: frozenset({PAID, PAYMENT_FAILED}),
    PAYMENT_FAILED: frozenset(
        {CHECKOUT_STARTED, PAYMENT_PENDING, PAYMENT_PROCESSING, PAID, CANCELED}
    ),
    # Money that arrives after a cancel is still money: it is recorded, and the
    # order is flagged for reconciliation by the caller.
    CANCELED: frozenset({PAID}),
    PAID: frozenset({PARTIALLY_REFUNDED, REFUNDED, DISPUTED}),
    PARTIALLY_REFUNDED: frozenset({PARTIALLY_REFUNDED, REFUNDED, DISPUTED}),
    # Won -> back to what it was; lost -> CHARGEBACK.
    DISPUTED: frozenset({PAID, PARTIALLY_REFUNDED, REFUNDED, CHARGEBACK}),
    REFUNDED: frozenset({DISPUTED}),
    CHARGEBACK: frozenset(),
}

#: States that assert something about money. Only verified processor evidence
#: may move an order into one of them.
PROVIDER_STATES = frozenset(
    {
        PAYMENT_PENDING,
        PAYMENT_PROCESSING,
        PAID,
        PAYMENT_FAILED,
        REFUNDED,
        PARTIALLY_REFUNDED,
        DISPUTED,
        CHARGEBACK,
    }
)

#: A payment has been received at some point; a second checkout is refused.
MONEY_RECEIVED = frozenset({PAID, PARTIALLY_REFUNDED, REFUNDED, DISPUTED, CHARGEBACK})
#: A payment is in flight at the processor; a second checkout is refused.
IN_FLIGHT = frozenset({PAYMENT_PENDING, PAYMENT_PROCESSING})
#: States a buyer may start (or restart) checkout from.
CHECKOUT_OPEN = frozenset({CREATED, CHECKOUT_STARTED, PAYMENT_FAILED})

PROVIDERS = ("stripe", "paypal")

# --- order ids ------------------------------------------------------------------
#: Crockford base32: no I, L, O or U, so a reference read aloud or retyped from
#: a receipt cannot be confused with another.
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ORDER_REF = re.compile(r"^CG-ORD-(20\d\d)-([0-9A-HJKMNP-TV-Z]{8})$")


def new_order_ref(now: datetime | None = None) -> str:
    """``CG-ORD-<year>-<8 random Crockford base32 chars>`` (40 bits).

    Random rather than sequential, so a reference printed on one receipt says
    nothing about how many orders exist or what anyone else's is.
    """
    year = (now or datetime.now(UTC)).year
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(8))
    return f"CG-ORD-{year}-{suffix}"


def is_order_ref(value: object) -> bool:
    return isinstance(value, str) and bool(ORDER_REF.match(value))


def check_transition(current: str, target: str, *, verified: bool) -> str | None:
    """Why ``current -> target`` is refused, or ``None`` if it is allowed."""
    if current not in TRANSITIONS:
        return f"unknown current state {current!r}"
    if target not in TRANSITIONS:
        return f"unknown target state {target!r}"
    if target not in TRANSITIONS[current]:
        return f"{current} -> {target} is not an allowed transition"
    if target in PROVIDER_STATES and not verified:
        return f"{target} requires verified payment-provider evidence"
    return None


def state_for_adjustment(
    *, status: str, amount_refunded: float, total: float, dispute_status: str | None,
    open_disputes: frozenset[str], lost_disputes: frozenset[str],
) -> str:
    """The payment state a settled ledger row implies after refunds and disputes.

    ``status`` is the ledger row's own status (``paid`` | ``refunded`` | ...);
    the dispute vocabulary is ``order_ledger``'s, passed in to keep this module
    free of imports.
    """
    if dispute_status in lost_disputes:
        return CHARGEBACK
    if dispute_status in open_disputes:
        return DISPUTED
    if status == "refunded" or (total > 0 and amount_refunded >= total):
        return REFUNDED
    if amount_refunded > 0:
        return PARTIALLY_REFUNDED
    return PAID


def fulfillment_state(
    *,
    payment_state: str,
    reconciliation_required: bool,
    service_status: str | None,
    shipment_status: str | None,
) -> str:
    """Fulfillment as the records that exist describe it.

    ``service_status`` is the linked ``ServiceOrder.status`` (services);
    ``shipment_status`` is the paid ledger row's ``fulfillment_status`` (goods).
    Work that has not been delivered is ``HELD`` while money is in question:
    a refund, a dispute, or an unreconciled payment.
    """
    if service_status in {"DELIVERED", "CLOSED"} or shipment_status in {"shipped", "fulfilled"}:
        return COMPLETED
    if payment_state not in MONEY_RECEIVED:
        return NOT_STARTED
    if reconciliation_required or payment_state in {REFUNDED, DISPUTED, CHARGEBACK}:
        return HELD
    if service_status == "INTAKE_REQUIRED":
        return FULFILLMENT_PENDING
    if service_status:
        return FULFILLING
    if shipment_status in {"drafted", "confirmed"}:
        return FULFILLING
    if shipment_status == "unfulfillable":
        return HELD
    return FULFILLMENT_PENDING if shipment_status == "pending" else NOT_STARTED


def display_state(payment_state: str, fulfillment: str) -> str:
    """One state for dashboards: fulfillment once paid work is under way, else payment."""
    if payment_state in {PAID, PARTIALLY_REFUNDED} and fulfillment in {
        FULFILLMENT_PENDING,
        FULFILLING,
        COMPLETED,
    }:
        return fulfillment
    return payment_state
