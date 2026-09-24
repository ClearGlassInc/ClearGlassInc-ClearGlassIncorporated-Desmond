"""ClearGlass orders: one record from offer to verified payment to fulfillment.

The path this module owns::

    offer (price book) -> ClearGlass order (CG-ORD-...) -> Stripe | PayPal checkout
        -> signed webhook -> ledger row in ``orders`` (order_ledger)
        -> this module: PAID, fulfillment task, or a reconciliation flag

Rules, each of which a test in ``tests/test_commerce_orders.py`` holds:

* **The server names the price.** An order is priced from the price book when
  it is created, and a checkout is refused if the price book no longer agrees,
  rather than silently charging a different amount.
* **Only verified processor evidence moves money states.** A browser return,
  an unsigned webhook or a request body cannot make an order ``PAID``
  (:mod:`app.order_states`).
* **One order, one payment.** A second checkout on a paid or in-flight order is
  refused. If Stripe and PayPal both still settle for the same order (a buyer
  who paid in two tabs), both payments are kept and the order is flagged
  ``reconciliation_required``; nothing is deleted and nothing ships twice.
* **Fulfillment starts from verified live money only,** and never while the
  order is flagged.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import attribution, order_states, payments, paypal, pricebook
from .audit import log_event
from .models import Approval, CommercialOrder, Lead, Order, ServiceOrder
from .revenue_service import provision_paid_service
from .service import run_governed_action

ACTOR = "commerce"

#: Ledger rows (``orders.status``) that mean money was received.
_SETTLED = frozenset({"paid", "refunded"})
#: Ledger dispute vocabulary, mirrored from ``order_ledger`` (which imports this
#: module, so it cannot be imported back).
_OPEN_DISPUTES = frozenset(
    {"warning_needs_response", "warning_under_review", "needs_response", "under_review"}
)
_LOST_DISPUTES = frozenset({"lost"})
#: Ledger payment status -> ClearGlass payment state.
_STATUS_TO_STATE = {
    "paid": order_states.PAID,
    "pending": order_states.PAYMENT_PROCESSING,
    "failed": order_states.PAYMENT_FAILED,
}


class CheckoutRefused(Exception):
    """A checkout this order must not open. ``status_code`` is the HTTP answer."""

    def __init__(self, detail: str, status_code: int = 409) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def provider_for_source(source: str | None) -> str:
    """``stripe`` | ``paypal`` | ``other`` for an ``orders.source`` value."""
    value = (source or "").lower()
    if value.startswith("stripe"):
        return "stripe"
    if value.startswith("paypal"):
        return "paypal"
    return "other"


def get_by_ref(session: Session, order_ref: str, *, lock: bool = False) -> CommercialOrder | None:
    if not order_states.is_order_ref(order_ref):
        return None
    stmt = select(CommercialOrder).where(CommercialOrder.order_ref == order_ref)
    if lock:
        # Postgres takes a row lock, so two webhooks for one order apply in turn
        # and the second sees the first's PAID. SQLite ignores it.
        stmt = stmt.with_for_update()
    return session.scalar(stmt)


def _attribution(co: CommercialOrder) -> dict[str, str | None]:
    return {"utm_source": co.utm_source, "utm_medium": co.utm_medium, "utm_campaign": co.utm_campaign}


def _lead_attribution(lead: Lead) -> dict[str, str]:
    """Last touch when the lead has one, else first touch; re-validated."""
    if lead.utm_last_campaign or lead.utm_last_source:
        raw = {
            "utm_source": lead.utm_last_source,
            "utm_medium": lead.utm_last_medium,
            "utm_campaign": lead.utm_last_campaign,
        }
    else:
        raw = {
            "utm_source": lead.utm_first_source,
            "utm_medium": lead.utm_first_medium,
            "utm_campaign": lead.utm_first_campaign,
        }
    return attribution.clean(raw)


def _price(sku: str, quantity: int) -> tuple[list[dict[str, Any]], str, Decimal, str]:
    line_items, checkout_mode = pricebook.resolve_line_items([{"sku": sku, "quantity": quantity}])
    cents = sum(int(i["amount"]) * int(i["quantity"]) for i in line_items)
    return line_items, checkout_mode, Decimal(cents) / Decimal(100), line_items[0]["currency"].upper()


def create_order(
    session: Session,
    *,
    sku: str,
    quantity: int = 1,
    lead: Lead | None = None,
    raw_attribution: Mapping[str, Any] | None = None,
) -> CommercialOrder:
    """Price an offer server-side and open a ClearGlass order for it.

    Raises :class:`app.pricebook.PricebookError` for an unknown or inactive SKU.
    A lead's own recorded campaign wins over whatever the browser sent, so the
    campaign a sale is credited to cannot be chosen by the caller.
    """
    _, checkout_mode, amount, currency = _price(sku, quantity)
    offer = pricebook.get_offer(sku)
    tags = _lead_attribution(lead) if lead else {}
    if not tags:
        tags = attribution.clean(raw_attribution)

    order_ref = order_states.new_order_ref()
    for _ in range(5):  # 40 random bits: a collision is not expected, but is handled
        if get_by_ref(session, order_ref) is None:
            break
        order_ref = order_states.new_order_ref()
    else:  # pragma: no cover - would need five consecutive collisions
        raise RuntimeError("could not allocate a unique order reference")

    co = CommercialOrder(
        order_ref=order_ref,
        sku=offer.sku,
        offer_name=offer.name,
        quantity=quantity,
        amount=amount,
        currency=currency,
        checkout_mode=checkout_mode,
        payment_state=order_states.CREATED,
        lead_id=lead.id if lead else None,
        utm_source=tags.get("utm_source"),
        utm_medium=tags.get("utm_medium"),
        utm_campaign=tags.get("utm_campaign"),
    )
    session.add(co)
    session.flush()
    log_event(
        session,
        actor=ACTOR,
        action="commercial_order_created",
        target=order_ref,
        payload={
            "sku": co.sku,
            "quantity": quantity,
            "amount": str(amount),
            "currency": currency,
            "lead_id": co.lead_id,
            "utm_campaign": co.utm_campaign,
        },
        result="executed",
    )
    return co


def transition(
    session: Session,
    co: CommercialOrder,
    target: str,
    *,
    verified: bool,
    actor: str,
    event: str,
) -> bool:
    """Move ``co`` to ``target`` if the state machine allows it.

    Returns ``False`` (and logs the refusal) instead of raising, because the
    callers are webhooks: a late or out-of-order event must be recorded, not
    answered with a 500 that makes the processor retry it forever.
    """
    reason = order_states.check_transition(co.payment_state, target, verified=verified)
    if reason is not None:
        log_event(
            session,
            actor=actor,
            action="order_state_transition_refused",
            target=co.order_ref,
            payload={"from": co.payment_state, "to": target, "reason": reason, "event": event},
            result="skipped",
        )
        return False
    previous, co.payment_state = co.payment_state, target
    session.flush()
    log_event(
        session,
        actor=actor,
        action="order_state_changed",
        target=co.order_ref,
        payload={"from": previous, "to": target, "event": event, "verified": verified},
        result="executed",
    )
    return True


def _flag(session: Session, co: CommercialOrder, code: str, detail: str, *, actor: str) -> None:
    """Mark the order for a human. Appends; never clears an earlier reason."""
    co.reconciliation_required = True
    reason = f"{code}: {detail}"
    co.reconciliation_reason = (
        f"{co.reconciliation_reason}\n{reason}" if co.reconciliation_reason else reason
    )
    session.flush()
    log_event(
        session,
        actor=actor,
        action="reconciliation_required",
        target=co.order_ref,
        payload={"code": code, "detail": detail},
        result="flagged",
    )


# --- checkout -------------------------------------------------------------------


def start_checkout(
    session: Session,
    co: CommercialOrder,
    *,
    provider: str,
    customer_email: str | None,
) -> dict[str, Any]:
    """Open a Stripe or PayPal checkout for this order, or refuse to.

    Refused (:class:`CheckoutRefused`) when money has been received, a payment
    is already in flight, the order is canceled or flagged, the price book no
    longer agrees with the order, or PayPal is asked to bill a subscription.
    """
    if provider not in order_states.PROVIDERS:
        raise CheckoutRefused(f"unknown payment provider {provider!r}", 400)
    if co.payment_state in order_states.MONEY_RECEIVED:
        raise CheckoutRefused("this order has already been paid")
    if co.payment_state in order_states.IN_FLIGHT:
        raise CheckoutRefused("a payment for this order is already in progress")
    if co.payment_state not in order_states.CHECKOUT_OPEN:
        raise CheckoutRefused(f"checkout is closed for an order in state {co.payment_state}")
    if co.reconciliation_required:
        raise CheckoutRefused("this order is held for reconciliation")
    if provider == "paypal" and co.checkout_mode == "subscription":
        raise CheckoutRefused(
            "recurring plans are not available through PayPal; use card checkout", 400
        )

    try:
        line_items, checkout_mode, amount, currency = _price(co.sku, co.quantity)
    except pricebook.PricebookError as exc:
        raise CheckoutRefused(f"this offer is no longer for sale: {exc}") from exc
    if amount != Decimal(co.amount) or currency != co.currency:
        # The price book changed after the order was created. Charging the new
        # price under the old order would make the order's own record wrong.
        raise CheckoutRefused("the price for this offer has changed; start a new order")

    email = (customer_email or "").strip().lower() or None
    if provider == "stripe":
        email_key = hashlib.sha256((email or "").encode()).hexdigest()[:12]
        try:
            result = payments.create_checkout_session(
                line_items,
                customer_email=email,
                checkout_mode=checkout_mode,
                client_reference_id=co.order_ref,
                # Same order + same buyer = same session on a double click or retry.
                idempotency_key=f"{co.order_ref}:stripe:{email_key}",
                extra_metadata={"cg_order_ref": co.order_ref, **attribution.to_metadata(_attribution(co))},
            )
        except Exception as exc:  # the Stripe SDK's errors, at the network boundary
            log_event(
                session,
                actor=ACTOR,
                action="checkout_start_failed",
                target=co.order_ref,
                payload={"provider": provider, "error": type(exc).__name__},
                result="error",
            )
            raise CheckoutRefused("Stripe could not create the checkout; try again or use PayPal", 502) from exc
        checkout_ref, url, mode = result["id"], result["url"], result["mode"]
    else:
        try:
            result = paypal.create_order(
                line_items,
                customer_email=email,
                request_id=f"{co.order_ref}-paypal",
                invoice_id=co.order_ref,
            )
        except paypal.PayPalError as exc:
            log_event(
                session,
                actor=ACTOR,
                action="checkout_start_failed",
                target=co.order_ref,
                payload={"provider": provider, "error": str(exc)},
                result="error",
            )
            raise CheckoutRefused(f"PayPal could not create the order: {exc}", 502) from exc
        checkout_ref, url, mode = result["id"], result["approve_url"], result["mode"]

    mark_checkout_started(session, co, provider=provider, checkout_ref=checkout_ref, mode=mode)
    return {
        "order_ref": co.order_ref,
        "provider": provider,
        "url": url,
        "mode": mode,
        "amount": float(amount),
        "currency": currency,
    }


def mark_checkout_started(
    session: Session,
    co: CommercialOrder,
    *,
    provider: str,
    checkout_ref: str,
    mode: str,
    record_event: bool = True,
) -> None:
    """Record that a processor checkout now exists for this order.

    Used by :func:`start_checkout` and by the CRCS first-offer checkout, which
    builds its own Stripe session but books it against a ClearGlass order. That
    caller writes its own ``checkout_started`` event (``record_event=False``),
    so one checkout is counted once.
    """
    previous_provider = co.provider
    transition(session, co, order_states.CHECKOUT_STARTED, verified=False, actor=ACTOR, event="checkout_start")
    co.provider = provider
    co.provider_checkout_ref = checkout_ref
    session.flush()
    if not record_event:
        return
    log_event(
        session,
        actor=ACTOR,
        action="checkout_started",
        target=co.order_ref,
        payload={
            "provider": provider,
            "mode": mode,
            "checkout_ref": checkout_ref,
            "switched_from": previous_provider if previous_provider not in (None, provider) else None,
        },
        result="executed",
    )


# --- processor evidence ---------------------------------------------------------


def on_payment_booked(session: Session, payment: Order, *, verified: bool, actor: str, event: str) -> None:
    """Apply a ledger booking (new or promoted) to the ClearGlass order it names."""
    if not payment.order_ref:
        return
    co = get_by_ref(session, payment.order_ref, lock=True)
    if co is None:
        log_event(
            session,
            actor=actor,
            action="payment_for_unknown_order",
            target=str(payment.id),
            payload={"order_ref": payment.order_ref, "event": event},
            result="flagged",
        )
        return
    if not verified:
        # The ledger keeps what it was told; the order does not move on it.
        log_event(
            session,
            actor=actor,
            action="unverified_payment_not_applied",
            target=co.order_ref,
            payload={"payment_id": payment.id, "event": event},
            result="flagged",
        )
        return

    target = _STATUS_TO_STATE.get(payment.status)
    if target is None:
        return
    if target != order_states.PAID:
        if co.payment_order_id not in (None, payment.id):
            return  # another payment already settled this order; this one is noise
        transition(session, co, target, verified=True, actor=actor, event=event)
        return
    _apply_paid(session, co, payment, actor=actor, event=event)


def _apply_paid(session: Session, co: CommercialOrder, payment: Order, *, actor: str, event: str) -> None:
    provider = provider_for_source(payment.source)
    others = [
        o for o in session.scalars(
            select(Order).where(Order.order_ref == co.order_ref, Order.id != payment.id)
        ).all()
        if o.status in _SETTLED
    ]
    if others or (co.payment_order_id not in (None, payment.id)):
        first = others[0] if others else session.get(Order, co.payment_order_id)
        _flag(
            session,
            co,
            "DUPLICATE_PAYMENT",
            f"{provider} payment #{payment.id} ({payment.total} {payment.currency}) arrived for an order "
            f"already paid by {provider_for_source(first.source if first else None)} payment "
            f"#{first.id if first else co.payment_order_id}. Both are kept; refund one at the provider.",
            actor=actor,
        )
        return
    if co.payment_order_id == payment.id and co.payment_state in order_states.MONEY_RECEIVED:
        return

    if (payment.currency or "").upper() != co.currency:
        _flag(
            session, co, "CURRENCY_MISMATCH",
            f"paid in {payment.currency}, order is priced in {co.currency}", actor=actor,
        )
    elif Decimal(payment.total) < Decimal(co.amount):
        _flag(
            session, co, "AMOUNT_MISMATCH",
            f"paid {payment.total} {payment.currency}, order is {co.amount} {co.currency}", actor=actor,
        )
    if co.payment_state == order_states.CANCELED:
        _flag(session, co, "PAID_AFTER_CANCEL", f"payment #{payment.id} settled after the order was canceled", actor=actor)

    if not transition(session, co, order_states.PAID, verified=True, actor=actor, event=event):
        # Verified money arrived and the order cannot say so: a human decides.
        _flag(
            session, co, "PAYMENT_STATE_CONFLICT",
            f"verified payment #{payment.id} arrived while the order was {co.payment_state}", actor=actor,
        )
        return
    co.payment_order_id = payment.id
    co.provider = provider if provider != "other" else co.provider
    co.environment = payment.environment
    session.flush()
    _start_fulfillment(session, co, payment, actor=actor)


def _start_fulfillment(session: Session, co: CommercialOrder, payment: Order, *, actor: str) -> None:
    """Open delivery work for verified live money, and tell the operator."""
    if payment.environment != "live":
        log_event(
            session,
            actor=actor,
            action="test_payment_verified",
            target=co.order_ref,
            payload={"payment_id": payment.id, "environment": payment.environment},
            result="executed",
        )
        return
    if co.reconciliation_required:
        log_event(
            session,
            actor=actor,
            action="fulfillment_held",
            target=co.order_ref,
            payload={"reason": co.reconciliation_reason},
            result="flagged",
        )
        return
    service = provision_paid_service(
        session, payment, sku=co.sku, lead_id=co.lead_id, actor=co.provider or actor,
    )
    log_event(
        session,
        actor=actor,
        action="operator_action_required",
        target=co.order_ref,
        payload={
            "reason": "verified live payment: start fulfillment",
            "service_order_id": service.id if service else None,
            "sku": co.sku,
        },
        result="flagged",
    )


def on_payment_adjusted(session: Session, payment: Order, *, actor: str, event: str) -> None:
    """Carry a refund or dispute the ledger applied onto the ClearGlass order."""
    if not payment.order_ref:
        return
    co = get_by_ref(session, payment.order_ref, lock=True)
    if co is None:
        return
    if co.payment_order_id not in (None, payment.id):
        # The adjustment concerns the duplicate payment, which is usually how a
        # double payment is resolved. The order's own state is unaffected; the
        # flag stays for a human to clear once both providers agree.
        log_event(
            session,
            actor=actor,
            action="duplicate_payment_adjusted",
            target=co.order_ref,
            payload={"payment_id": payment.id, "event": event, "status": payment.status},
            result="flagged",
        )
        return
    target = order_states.state_for_adjustment(
        status=payment.status,
        amount_refunded=float(payment.amount_refunded or 0),
        total=float(payment.total or 0),
        dispute_status=payment.dispute_status,
        open_disputes=_OPEN_DISPUTES,
        lost_disputes=_LOST_DISPUTES,
    )
    if target != co.payment_state:
        transition(session, co, target, verified=True, actor=actor, event=event)


def on_paypal_order_approved(session: Session, resource: Mapping[str, Any], *, event: str) -> None:
    """The buyer approved on PayPal: the order awaits capture, which a human approves.

    Queues the ``paypal_capture_order`` approval so it is in the owner's queue
    the moment the buyer approves, instead of waiting for someone to notice.
    Queuing is not capturing: nothing moves money until that approval is
    approved and ``POST /paypal/capture`` is called again.
    """
    order_ref = paypal.order_ref_from_order(dict(resource))
    paypal_order_id = str(resource.get("id") or "")
    if not order_ref or not paypal_order_id:
        return
    co = get_by_ref(session, order_ref, lock=True)
    if co is None:
        log_event(
            session, actor="paypal", action="payment_for_unknown_order",
            target=paypal_order_id, payload={"order_ref": order_ref, "event": event}, result="flagged",
        )
        return
    if co.payment_state in order_states.CHECKOUT_OPEN:
        transition(session, co, order_states.PAYMENT_PENDING, verified=True, actor="paypal", event=event)
    already_queued = session.scalar(
        select(Approval.id).where(
            Approval.action == "paypal_capture_order",
            Approval.target == paypal_order_id,
            Approval.status.in_(("pending", "approved")),
        )
    )
    if already_queued is None and co.payment_state == order_states.PAYMENT_PENDING:
        run_governed_action(
            session,
            actor="paypal",
            action="paypal_capture_order",
            target=paypal_order_id,
            payload={
                "paypal_order_id": paypal_order_id,
                "order_ref": co.order_ref,
                "amount": str(co.amount),
                "currency": co.currency,
            },
            execute=None,
        )


# --- reads and operator actions -------------------------------------------------


def _service_for(session: Session, co: CommercialOrder) -> ServiceOrder | None:
    if co.payment_order_id is None:
        return None
    return session.scalar(select(ServiceOrder).where(ServiceOrder.order_id == co.payment_order_id))


def fulfillment_of(session: Session, co: CommercialOrder) -> str:
    service = _service_for(session, co)
    return order_states.fulfillment_state(
        payment_state=co.payment_state,
        reconciliation_required=co.reconciliation_required,
        service_status=service.status if service else None,
        shipment_status=None,  # the price book sells services only
    )


def public_status(session: Session, co: CommercialOrder) -> dict[str, Any]:
    """What a buyer may see: no email, no processor ids, no internal notes."""
    fulfillment = fulfillment_of(session, co)
    return {
        "order_ref": co.order_ref,
        "offer": co.offer_name,
        "amount": float(co.amount),
        "currency": co.currency,
        "provider": co.provider,
        "payment_state": co.payment_state,
        # True only once a signed processor event settled it. A return from the
        # checkout page alone leaves this False.
        "payment_verified": co.payment_state in order_states.MONEY_RECEIVED,
        "fulfillment_state": fulfillment,
        "state": order_states.display_state(co.payment_state, fulfillment),
    }


def admin_view(session: Session, co: CommercialOrder) -> dict[str, Any]:
    payments_rows = session.scalars(
        select(Order).where(Order.order_ref == co.order_ref).order_by(Order.id)
    ).all()
    view = public_status(session, co)
    view.update(
        {
            "id": co.id,
            "sku": co.sku,
            "quantity": co.quantity,
            "environment": co.environment,
            "provider_checkout_ref": co.provider_checkout_ref,
            "payment_order_id": co.payment_order_id,
            "lead_id": co.lead_id,
            "utm_source": co.utm_source,
            "utm_medium": co.utm_medium,
            "utm_campaign": co.utm_campaign,
            "reconciliation_required": co.reconciliation_required,
            "reconciliation_reason": co.reconciliation_reason,
            "created_at": co.created_at.isoformat() if co.created_at else None,
            "payments": [
                {
                    "id": p.id,
                    "provider": provider_for_source(p.source),
                    "status": p.status,
                    "total": float(p.total),
                    "currency": p.currency,
                    "amount_refunded": float(p.amount_refunded or 0),
                    "dispute_status": p.dispute_status,
                    "environment": p.environment,
                    "external_ref": p.external_ref,
                }
                for p in payments_rows
            ],
        }
    )
    return view


def cancel(session: Session, co: CommercialOrder, *, actor: str) -> bool:
    """Close an unpaid order. Money already received is never canceled here."""
    return transition(session, co, order_states.CANCELED, verified=False, actor=actor, event="operator_cancel")
