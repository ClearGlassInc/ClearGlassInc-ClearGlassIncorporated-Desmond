"""PayPal — customer order creation, verified webhook ingest, gated capture.

The surface mirrors the Stripe router's split of responsibilities:

* ``POST /paypal/order`` is a **customer** flow — public, throttled, and priced
  entirely from the server-side price book.
* ``POST /webhooks/paypal`` is authenticated by PayPal's signature and books
  revenue idempotently. It is the *only* thing that books a PayPal payment.
* ``POST /paypal/capture`` is an **operator** action that moves money, so it goes
  through the approval gate like every other money-movement action.

What this router deliberately does not do is fulfill on approval. PayPal returns
the buyer to the site the moment they approve, and ``CHECKOUT.ORDER.APPROVED``
fires at the same point — neither means the money arrived. Only a verified
``PAYMENT.CAPTURE.COMPLETED`` whose amount reconciles against the catalogue
produces a shippable order.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import paypal, pricebook
from ..audit import log_event
from ..config import get_settings
from ..db import get_session
from ..order_ledger import record_payment_order
from ..schemas import ActionResult, CheckoutRequest, PayPalCaptureRequest, PayPalOrderOut
from ..security import rate_limit, require_admin
from ..service import run_governed_action

router = APIRouter(tags=["paypal"])

_checkout_throttle = rate_limit("paypal_checkout", "rate_limit_checkout_per_minute")
_webhook_throttle = rate_limit("paypal_webhook", "rate_limit_webhook_per_minute")


@router.get("/paypal/connection", dependencies=[Depends(require_admin)])
def paypal_connection() -> dict:
    """Credential presence and verification posture. Echoes no secret."""
    return paypal.connection_state()


@router.post(
    "/paypal/order",
    response_model=PayPalOrderOut,
    dependencies=[Depends(_checkout_throttle)],
)
def create_paypal_order(
    req: CheckoutRequest, session: Session = Depends(get_session)
) -> PayPalOrderOut:
    """Create a PayPal order for a customer cart.

    Takes SKUs and quantities only — exactly the contract ``/checkout/session``
    uses — so the amount PayPal is told to charge comes from the price book and
    never from the request. Returns a mock order when no PayPal credentials are
    configured.
    """
    try:
        line_items, checkout_mode = pricebook.resolve_line_items(
            [i.model_dump() for i in req.items]
        )
    except pricebook.PricebookError as exc:
        log_event(
            session,
            actor="storefront",
            action="create_paypal_order",
            target=req.customer_email,
            payload={"rejected": str(exc), "items": [i.model_dump() for i in req.items]},
            result="rejected",
        )
        # Commit before raising: get_session rolls back on exception, which would
        # discard the record of someone probing the catalogue.
        session.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if checkout_mode == "subscription":
        # PayPal bills recurring plans through Subscriptions, a different API with
        # its own plan objects. Quietly charging a subscription once as a one-off
        # would take the first payment and silently never take another.
        log_event(
            session,
            actor="storefront",
            action="create_paypal_order",
            target=req.customer_email,
            payload={"rejected": "recurring cart", "skus": [i["sku"] for i in line_items]},
            result="rejected",
        )
        session.commit()
        raise HTTPException(
            status_code=400,
            detail="recurring plans are not available through PayPal; use card checkout",
        )

    try:
        result = paypal.create_order(
            line_items,
            customer_email=req.customer_email,
            request_id=req.client_reference_id,
        )
    except paypal.PayPalError as exc:
        log_event(
            session,
            actor="storefront",
            action="create_paypal_order",
            target=req.customer_email,
            payload={"error": str(exc)},
            result="error",
        )
        session.commit()
        raise HTTPException(status_code=502, detail=f"PayPal could not create the order: {exc}") from exc

    log_event(
        session,
        actor="storefront",
        action="create_paypal_order",
        target=req.customer_email,
        payload={
            "paypal_order_id": result["id"],
            "amount_total": result["amount_total"],
            "mode": result["mode"],
            "skus": [i["sku"] for i in line_items],
        },
        result="executed",
    )
    return PayPalOrderOut(**result)


@router.post("/webhooks/paypal", dependencies=[Depends(_webhook_throttle)])
async def paypal_webhook(request: Request, session: Session = Depends(get_session)) -> dict:
    """Ingest a PayPal webhook. Unverified events are refused, never processed."""
    payload = await request.body()
    check = paypal.verify_webhook(payload, dict(request.headers))

    if not check["verified"]:
        # Refused before anything is read out of the body. Logged, because a run of
        # these is either a misconfigured webhook id or someone posting forged
        # settlement events at the endpoint — and both need to be visible.
        log_event(
            session,
            actor="paypal",
            action="paypal_webhook_rejected",
            target=str((check["event"] or {}).get("event_type") or "unknown"),
            payload={"reason": check["reason"]},
            result="rejected",
        )
        session.commit()
        raise HTTPException(status_code=400, detail=f"webhook rejected: {check['reason']}")

    event = check["event"]
    etype = str(event.get("event_type") or "unknown")
    resource = event.get("resource") or {}

    if etype in paypal.SETTLED_EVENTS:
        return _settle_capture(session, etype, resource)

    if etype in paypal.ATTENTION_EVENTS:
        # Refunds, reversals and disputes do not move this ledger — a refund runs
        # through the approval gate — but they must be visible in the audit trail
        # rather than only in the PayPal dashboard.
        log_event(
            session,
            actor="paypal",
            action=paypal.ATTENTION_EVENTS[etype],
            target=str(resource.get("id") or ""),
            payload={
                "verified": True,
                "event": etype,
                "amount": (resource.get("amount") or {}).get("value"),
                "currency": (resource.get("amount") or {}).get("currency_code"),
                "status": resource.get("status"),
            },
            result="flagged",
        )
        return {"received": True, "type": etype, "verified": True}

    log_event(
        session,
        actor="paypal",
        action="paypal_webhook",
        target=etype,
        payload={"verified": True},
        result="ok",
    )
    return {"received": True, "type": etype, "verified": True}


def _settle_capture(session: Session, etype: str, resource: dict) -> dict:
    """Book a capture into the shared order ledger and reconcile it to the catalogue."""
    capture_id = str(resource.get("id") or "")
    if not capture_id:
        # No idempotency key means no way to avoid booking this twice on redelivery.
        log_event(
            session,
            actor="paypal",
            action="paypal_capture_unidentified",
            target=etype,
            payload={"reason": "capture carries no id"},
            result="rejected",
        )
        raise HTTPException(status_code=400, detail="capture event carries no capture id")

    try:
        amount, currency = paypal.capture_amount(resource)
    except paypal.PayPalError as exc:
        log_event(
            session,
            actor="paypal",
            action="paypal_capture_unreadable",
            target=capture_id,
            payload={"reason": str(exc), "event": etype},
            result="rejected",
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    settings = get_settings()
    status = paypal.SETTLED_EVENTS[etype]
    order = record_payment_order(
        session,
        actor="paypal",
        # Key on the capture id, not the order id: one PayPal order can produce
        # several captures, and each is its own money movement.
        external_ref=f"paypal_capture_{capture_id}",
        total=amount,
        currency=currency,
        source="paypal_orders",
        status=status,
        verified=True,
        event=etype,
        shipping=(
            paypal.shipping_from_capture(resource) if settings.paypal_collect_shipping else None
        ),
    )

    if order is None:
        # Redelivery of an event already handled. Nothing changed, and nothing
        # downstream may run again — a second fulfillment for one payment is a
        # parcel the business pays for and the customer did not buy.
        return {"received": True, "type": etype, "verified": True, "duplicate": True}

    if status != "paid":
        return {"received": True, "type": etype, "verified": True, "order_status": status}

    matches, explanation = paypal.check_against_catalog(
        str(resource.get("custom_id") or ""), amount, currency
    )
    if not matches:
        # The money has arrived and cannot be un-received, so the order is real.
        # What stops here is fulfillment: a payment that does not reconcile to a
        # catalogue entry is exactly the case that must reach a human before
        # anything ships. Mirrors fulfillment.py's rule that money in does not
        # imply a parcel out.
        order.fulfillment_status = "unfulfillable"
        session.flush()
        log_event(
            session,
            actor="paypal",
            action="paypal_capture_catalog_mismatch",
            target=str(order.id),
            payload={
                "capture_id": capture_id,
                "reason": explanation,
                "amount": str(amount),
                "currency": currency,
                "custom_id": str(resource.get("custom_id") or ""),
            },
            result="flagged",
        )
        return {
            "received": True,
            "type": etype,
            "verified": True,
            "order_id": order.id,
            "fulfillment": "held_for_review",
        }

    log_event(
        session,
        actor="paypal",
        action="paypal_capture_reconciled",
        target=str(order.id),
        payload={"capture_id": capture_id, "detail": explanation},
        result="executed",
    )
    return {"received": True, "type": etype, "verified": True, "order_id": order.id}


@router.post(
    "/paypal/capture", response_model=ActionResult, dependencies=[Depends(require_admin)]
)
def capture(req: PayPalCaptureRequest, session: Session = Depends(get_session)) -> ActionResult:
    """Capture an approved PayPal order — always routed to the human approval gate.

    Taking a customer's money is not something automation does unwatched, so this
    endpoint queues the action and never calls PayPal inline. The capture itself
    runs once the approval is approved downstream.
    """
    return run_governed_action(
        session,
        actor="operations_agent",
        action="paypal_capture_order",
        target=req.paypal_order_id,
        payload=req.model_dump(),
        execute=None,
    )
