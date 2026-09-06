"""Payments — Stripe checkout (customer revenue), webhook ingest, and gated refunds."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import payments, pricebook
from ..audit import log_event
from ..db import get_session
from ..fulfillment import apply_shipping_details
from ..models import Order, Payout
from ..schemas import (
    ActionResult,
    BillingPortalOut,
    BillingPortalRequest,
    CheckoutRequest,
    CheckoutSessionOut,
    OfferOut,
    PayoutBankInfoOut,
    PayoutOut,
    RefundRequest,
)
from ..security import rate_limit, require_admin
from ..service import run_governed_action

router = APIRouter(tags=["payments"])

_checkout_throttle = rate_limit("checkout", "rate_limit_checkout_per_minute")
_webhook_throttle = rate_limit("stripe_webhook", "rate_limit_webhook_per_minute")

#: Checkout events that decide whether an order's money actually arrived.
CHECKOUT_SETTLEMENT_EVENTS = frozenset(
    {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
        "checkout.session.async_payment_failed",
    }
)

#: Events that need a human eye but move no money on our side — mapped to the audit
#: action they are recorded under.
ATTENTION_EVENTS = {
    "charge.refunded": "refund_settled",
    "charge.dispute.created": "dispute_opened",
    "charge.dispute.closed": "dispute_closed",
    "payment_intent.payment_failed": "payment_failed",
    "invoice.payment_failed": "subscription_payment_failed",
    "customer.subscription.created": "subscription_created",
    "customer.subscription.updated": "subscription_updated",
    "customer.subscription.deleted": "subscription_canceled",
    "customer.subscription.paused": "subscription_paused",
    "customer.subscription.resumed": "subscription_resumed",
}


@router.get("/offers", response_model=list[OfferOut])
def list_offers() -> list[OfferOut]:
    """The catalogue the storefront may sell, at the prices the business set.

    Public and read-only: it is the same data the storefront renders, and it is the
    only place a price legitimately comes from.
    """
    return [
        OfferOut(
            sku=o.sku,
            name=o.name,
            description=o.description,
            amount=o.amount,
            currency=o.currency,
            kind=o.kind,
            interval=o.interval,
            max_quantity=o.max_quantity,
        )
        for o in pricebook.all_offers()
    ]


@router.post(
    "/checkout/session",
    response_model=CheckoutSessionOut,
    dependencies=[Depends(_checkout_throttle)],
)
def create_checkout(req: CheckoutRequest, session: Session = Depends(get_session)) -> CheckoutSessionOut:
    """Create a Stripe Checkout session for a customer cart.

    Customer-initiated purchases are normal revenue flow, not an autonomous admin action, so
    they are logged but not put behind the approval gate. Returns a mock session when no
    Stripe key is configured.

    Prices are resolved from the server-side price book — the request names SKUs and
    quantities only, so a tampered cart is rejected rather than charged.
    """
    try:
        line_items, checkout_mode = pricebook.resolve_line_items(
            [i.model_dump() for i in req.items]
        )
    except pricebook.PricebookError as exc:
        # Log the rejection: a run of these is either a broken storefront build or
        # someone probing the checkout with SKUs and quantities that do not exist.
        log_event(
            session,
            actor="storefront",
            action="create_checkout_session",
            target=req.customer_email,
            payload={"rejected": str(exc), "items": [i.model_dump() for i in req.items]},
            result="rejected",
        )
        # Commit before raising: get_session rolls back on exception, which would
        # discard the very record that shows someone probing the checkout.
        session.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = payments.create_checkout_session(
        line_items,
        customer_email=req.customer_email,
        checkout_mode=checkout_mode,
        client_reference_id=req.client_reference_id,
        idempotency_key=req.client_reference_id,
    )
    log_event(
        session,
        actor="storefront",
        action="create_checkout_session",
        target=req.customer_email,
        payload={
            "amount_total": result["amount_total"],
            "mode": result["mode"],
            "checkout_mode": checkout_mode,
            "skus": [i["sku"] for i in line_items],
        },
        result="executed",
    )
    return CheckoutSessionOut(**result)


@router.post(
    "/billing/portal",
    response_model=BillingPortalOut,
    dependencies=[Depends(_checkout_throttle)],
)
def create_billing_portal(req: BillingPortalRequest, session: Session = Depends(get_session)) -> BillingPortalOut:
    """Open the hosted portal without accepting a caller-supplied Stripe customer id."""
    try:
        result = payments.create_billing_portal_session(req.checkout_session_id)
    except ValueError as exc:
        log_event(
            session,
            actor="customer",
            action="create_billing_portal_session",
            target=req.checkout_session_id,
            payload={"reason": str(exc)},
            result="rejected",
        )
        session.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_event(
        session,
        actor="customer",
        action="create_billing_portal_session",
        target=req.checkout_session_id,
        payload={"mode": result["mode"]},
        result="executed",
    )
    return BillingPortalOut(**result)


@router.post("/webhooks/stripe", dependencies=[Depends(_webhook_throttle)])
async def stripe_webhook(request: Request, session: Session = Depends(get_session)) -> dict:
    """Ingest Stripe webhook events. Signature is verified when a webhook secret is configured."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    check = payments.verify_webhook(payload, sig)

    if payments.webhook_secret_set() and not check["verified"]:
        raise HTTPException(status_code=400, detail=f"webhook rejected: {check['reason']}")

    event = check["event"]
    etype = event.get("type", "unknown")
    obj = (event.get("data") or {}).get("object") or {}

    if etype in CHECKOUT_SETTLEMENT_EVENTS:
        # `checkout.session.completed` fires as soon as the customer finishes the page,
        # which for an asynchronous method (bank debit) is *before* the money settles.
        # Booking that as paid would report revenue that can still fail, so trust
        # payment_status and let async_payment_succeeded promote it later.
        if etype == "checkout.session.async_payment_succeeded":
            status = "paid"
        elif etype == "checkout.session.async_payment_failed":
            status = "failed"
        else:
            paid = obj.get("payment_status") in {"paid", "no_payment_required"}
            status = "paid" if paid else "pending"

        _record_order(
            session,
            # Stripe redelivers webhooks; key the order on the checkout-session id so a
            # retry never books the same revenue twice.
            external_ref=obj.get("id") or obj.get("payment_intent"),
            total=Decimal(str((obj.get("amount_total") or 0) / 100)),
            currency=(obj.get("currency") or "cad").upper(),
            source="stripe_checkout",
            status=status,
            verified=check["verified"],
            event=etype,
            # A checkout session is the only place the destination address exists.
            # If it is not captured here it is gone, and a paid physical order has
            # nowhere to ship.
            shipping_source=obj,
        )
    elif etype == "invoice.paid":
        # Subscription renewals arrive as invoices, not checkout sessions. Without this
        # every month after the first would settle in Stripe and never reach the ledger.
        if obj.get("billing_reason") != "subscription_create":
            _record_order(
                session,
                external_ref=obj.get("id"),
                total=Decimal(str((obj.get("amount_paid") or 0) / 100)),
                currency=(obj.get("currency") or "cad").upper(),
                source="stripe_subscription",
                status="paid",
                verified=check["verified"],
                event=etype,
            )
        else:
            # The first invoice of a subscription is already booked from its checkout
            # session; recording it again would double-count the same money.
            log_event(
                session,
                actor="stripe",
                action="subscription_first_invoice_skipped",
                target=obj.get("id"),
                payload={"verified": check["verified"]},
                result="skipped",
            )
    elif etype in ATTENTION_EVENTS:
        # Refunds, failed payments and disputes do not move the ledger here — refunds
        # run through the approval gate — but they must be visible in the audit trail
        # rather than only in the Stripe dashboard.
        log_event(
            session,
            actor="stripe",
            action=ATTENTION_EVENTS[etype],
            target=obj.get("id"),
            payload={
                "verified": check["verified"],
                "event": etype,
                "amount": obj.get("amount") or obj.get("amount_refunded"),
                "currency": obj.get("currency"),
                "reason": obj.get("reason") or obj.get("failure_message"),
            },
            result="flagged",
        )
    elif etype in payments.PAYOUT_EVENT_TYPES:
        payout = _upsert_payout(session, obj, tenant_id=event.get("account"))
        log_event(
            session,
            actor="stripe",
            action="payout_recorded",
            target=payout.stripe_payout_id,
            payload={
                "verified": check["verified"],
                "event": etype,
                "status": payout.status,
                "amount": str(payout.amount),
                "currency": payout.currency,
            },
            result="executed",
        )
    else:
        log_event(
            session,
            actor="stripe",
            action="stripe_webhook",
            target=etype,
            payload={"verified": check["verified"]},
            result="ok",
        )

    return {"received": True, "type": etype, "verified": check["verified"]}


def _record_order(
    session: Session,
    *,
    external_ref: str | None,
    total: Decimal,
    currency: str,
    source: str,
    status: str,
    verified: bool,
    event: str,
    shipping_source: dict | None = None,
) -> None:
    """Book (or promote) an order idempotently, keyed on Stripe's own id.

    Redelivery of an event we already handled is a no-op. The one case that is *not*
    a no-op is a pending order whose payment later settles: that promotes the existing
    row instead of inserting a second one for the same money.
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
                actor="stripe",
                action="order_event_duplicate_skipped",
                target=str(existing.id),
                payload={"verified": verified, "external_ref": external_ref, "event": event},
                result="skipped",
            )
            return
        previous, existing.status = existing.status, status
        existing.total = total
        # A pending order settling is the point at which an async payment method
        # finally yields a shippable order, so re-apply the address here too:
        # the promoting event carries it and the original may not have.
        if shipping_source is not None:
            apply_shipping_details(existing, shipping_source)
        session.flush()
        log_event(
            session,
            actor="stripe",
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
        return

    order = Order(
        status=status,
        total=total,
        currency=currency,
        source=source,
        external_ref=external_ref,
    )
    if shipping_source is not None:
        apply_shipping_details(order, shipping_source)
    session.add(order)
    session.flush()
    log_event(
        session,
        actor="stripe",
        action=f"order_{status}",
        target=str(order.id),
        payload={"verified": verified, "event": event, "amount_total": str(total)},
        result="executed",
    )


def _upsert_payout(session: Session, obj: dict, *, tenant_id: str | None) -> Payout:
    """Insert or update a payout row keyed by Stripe's payout id (idempotent for retries).

    Stripe redelivers webhooks and fires several events per payout (created -> in_transit ->
    paid), so we look up by ``stripe_payout_id`` and update status/arrival in place rather than
    creating duplicate rows.
    """
    fields = payments.parse_payout(obj)
    existing = session.scalar(
        select(Payout).where(Payout.stripe_payout_id == fields["stripe_payout_id"])
    )
    if existing is None:
        payout = Payout(tenant_id=tenant_id, **fields)
        session.add(payout)
        session.flush()
        return payout

    existing.status = fields["status"]
    existing.amount = fields["amount"]
    existing.currency = fields["currency"]
    existing.destination = fields["destination"]
    existing.arrival_date = fields["arrival_date"]
    if tenant_id and not existing.tenant_id:
        existing.tenant_id = tenant_id
    session.flush()
    return existing


@router.get("/payments/payout-account", response_model=PayoutBankInfoOut)
def payout_account() -> PayoutBankInfoOut:
    """Return masked bank/payout routing metadata for earned revenue settlement.

    This endpoint never accepts or returns raw bank account/routing numbers. Stripe remains the
    system of record for the actual external bank account and performs the money movement.
    """
    return PayoutBankInfoOut(**payments.payout_bank_info())


@router.get("/payouts", response_model=list[PayoutOut])
def list_payouts(
    tenant_id: str | None = None,
    limit: int = 100,
    session: Session = Depends(get_session),
) -> list[Payout]:
    """Return recorded Stripe payouts, newest first. Optionally filter by ``tenant_id``.

    Read-only: payouts are written solely by the verified Stripe webhook, never via this API.
    """
    stmt = select(Payout).order_by(Payout.created_at.desc()).limit(max(1, min(limit, 500)))
    if tenant_id:
        stmt = stmt.where(Payout.tenant_id == tenant_id)
    return list(session.scalars(stmt).all())


@router.post("/payments/refund", response_model=ActionResult, dependencies=[Depends(require_admin)])
def refund(req: RefundRequest, session: Session = Depends(get_session)) -> ActionResult:
    """Issue a refund — CRITICAL risk, always routed to the human approval gate.

    The Stripe refund call itself runs only after the approval is approved downstream; this
    endpoint never moves money inline.
    """
    return run_governed_action(
        session,
        actor="operations_agent",
        action="trigger_refund",
        target=str(req.order_id),
        payload=req.model_dump(),
        execute=None,
    )
