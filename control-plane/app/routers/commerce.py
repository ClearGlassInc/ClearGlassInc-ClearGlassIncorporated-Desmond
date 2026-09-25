"""ClearGlass orders: one checkout, the buyer's choice of Stripe or PayPal.

Public (rate limited, server-priced, no processor secret or PII in any answer):

* ``POST /commerce/orders`` opens a ClearGlass order for one offer.
* ``POST /commerce/orders/{order_ref}/checkout`` starts Stripe or PayPal for it.
* ``GET  /commerce/orders/{order_ref}/status`` says whether the payment is
  *verified*, which only a signed processor webhook can make true.

Admin (``require_admin``): list, detail with every linked payment, cancel an
unpaid order, and run reconciliation. Nothing here moves money: captures and
refunds keep their own approval-gated routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import commerce_orders, order_states, pricebook, reconciliation
from ..db import get_session
from ..models import CommercialOrder, Lead
from ..schemas import (
    ActionResult,
    CommerceCheckoutOut,
    CommerceCheckoutRequest,
    CommerceOrderOut,
    CommerceOrderRequest,
    CommerceOrderStatusOut,
    ReconciliationRequest,
)
from ..security import rate_limit, require_admin
from ..service import run_governed_action

router = APIRouter(prefix="/commerce", tags=["commerce"])

_order_throttle = rate_limit("commerce_order", "rate_limit_checkout_per_minute")
_checkout_throttle = rate_limit("commerce_checkout", "rate_limit_checkout_per_minute")
_status_throttle = rate_limit("commerce_status", "rate_limit_checkout_per_minute")


def _order_or_404(session: Session, order_ref: str, *, lock: bool = False) -> CommercialOrder:
    # One answer for "malformed" and "unknown", so the endpoint confirms nothing.
    co = commerce_orders.get_by_ref(session, order_ref, lock=lock)
    if co is None:
        raise HTTPException(status_code=404, detail="order not found")
    return co


@router.post(
    "/orders",
    response_model=CommerceOrderOut,
    status_code=201,
    dependencies=[Depends(_order_throttle)],
)
def create_order(req: CommerceOrderRequest, session: Session = Depends(get_session)) -> CommerceOrderOut:
    lead = None
    if req.reference:
        lead = session.scalar(select(Lead).where(Lead.public_ref == req.reference))
        email = (req.customer_email or "").strip().lower()
        # Same answer for "no such lead" and "not your lead" (as /revenue/checkout).
        if lead is None or not email or lead.email != email:
            raise HTTPException(status_code=403, detail="order email does not match lead")
    try:
        co = commerce_orders.create_order(
            session,
            sku=req.sku,
            quantity=req.quantity,
            lead=lead,
            raw_attribution=req.attribution.model_dump() if req.attribution else None,
        )
    except pricebook.PricebookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CommerceOrderOut(
        order_ref=co.order_ref,
        sku=co.sku,
        offer=co.offer_name,
        quantity=co.quantity,
        amount=float(co.amount),
        currency=co.currency,
        checkout_mode=co.checkout_mode,
        payment_state=co.payment_state,
        providers=["stripe"] if co.checkout_mode == "subscription" else ["stripe", "paypal"],
    )


@router.post(
    "/orders/{order_ref}/checkout",
    response_model=CommerceCheckoutOut,
    dependencies=[Depends(_checkout_throttle)],
)
def start_checkout(
    order_ref: str, req: CommerceCheckoutRequest, session: Session = Depends(get_session)
) -> CommerceCheckoutOut:
    co = _order_or_404(session, order_ref, lock=True)
    try:
        result = commerce_orders.start_checkout(
            session, co, provider=req.provider, customer_email=req.customer_email
        )
    except commerce_orders.CheckoutRefused as exc:
        # Keep the audit record of a failed processor call; get_session would roll it back.
        session.commit()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return CommerceCheckoutOut(**result)


@router.get(
    "/orders/{order_ref}/status",
    response_model=CommerceOrderStatusOut,
    dependencies=[Depends(_status_throttle)],
)
def order_status(order_ref: str, session: Session = Depends(get_session)) -> CommerceOrderStatusOut:
    return CommerceOrderStatusOut(**commerce_orders.public_status(session, _order_or_404(session, order_ref)))


@router.get("/orders", dependencies=[Depends(require_admin)])
def list_orders(
    state: str | None = None,
    reconciliation_required: bool | None = None,
    limit: int = 100,
    session: Session = Depends(get_session),
) -> list[dict]:
    stmt = select(CommercialOrder).order_by(CommercialOrder.id.desc()).limit(max(1, min(limit, 500)))
    if state:
        if state not in order_states.PAYMENT_STATES:
            raise HTTPException(status_code=400, detail="unknown payment state")
        stmt = stmt.where(CommercialOrder.payment_state == state)
    if reconciliation_required is not None:
        stmt = stmt.where(CommercialOrder.reconciliation_required == reconciliation_required)
    return [commerce_orders.admin_view(session, co) for co in session.scalars(stmt).all()]


@router.get("/orders/{order_ref}", dependencies=[Depends(require_admin)])
def get_order(order_ref: str, session: Session = Depends(get_session)) -> dict:
    return commerce_orders.admin_view(session, _order_or_404(session, order_ref))


@router.post("/orders/{order_ref}/cancel", dependencies=[Depends(require_admin)])
def cancel_order(
    order_ref: str,
    principal: str = Depends(require_admin),
    session: Session = Depends(get_session),
) -> dict:
    co = _order_or_404(session, order_ref, lock=True)
    if not commerce_orders.cancel(session, co, actor=principal):
        session.commit()  # keep the refusal in the audit trail
        raise HTTPException(status_code=409, detail=f"an order in state {co.payment_state} cannot be canceled")
    return commerce_orders.admin_view(session, co)


@router.post("/reconciliation", response_model=ActionResult, dependencies=[Depends(require_admin)])
def run_reconciliation(req: ReconciliationRequest, session: Session = Depends(get_session)) -> ActionResult:
    """Ledger-internal checks, plus a processor comparison when records are supplied."""
    records = [r.model_dump() for r in req.provider_records]
    return run_governed_action(
        session,
        actor="reconciliation_agent",
        action="reconcile_orders",
        target="commerce",
        payload={"provider_records": len(records)},
        execute=lambda: reconciliation.reconcile(reconciliation.snapshot(session), records),
    )
