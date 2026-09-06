"""Side Store — a real cart, priced on the server, checked out through Stripe.

Why this exists rather than a Payment Link: the Side Store's price depends on how
much you buy (bundle tiers) and its shipping depends on the discounted subtotal.
A Payment Link sells one fixed basket and cannot express either. So the cart is
priced here and handed to Stripe as line items the customer never had a hand in.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import cart, payments
from ..audit import log_event
from ..db import get_session
from ..schemas import (
    CheckoutSessionOut,
    SideStoreCatalogItemOut,
    SideStoreCartRequest,
    SideStoreQuoteOut,
)
from ..security import rate_limit

router = APIRouter(prefix="/sidestore", tags=["sidestore"])

_checkout_throttle = rate_limit("sidestore_checkout", "rate_limit_checkout_per_minute")

#: Where the Side Store will actually post a parcel. Ontario-based, Canada-only —
#: shipping anywhere else is a promise the fulfilment side cannot keep today.
SHIPPING_COUNTRIES = ["CA"]


def _quote(items: list[dict]) -> cart.CartTotals:
    try:
        return cart.price_cart(items)
    except cart.CartError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/catalog", response_model=list[SideStoreCatalogItemOut])
def list_catalog() -> list[SideStoreCatalogItemOut]:
    """Everything for sale, at the prices the server will charge."""
    return [
        SideStoreCatalogItemOut(
            id=i["id"],
            sku=i["sku"],
            name=i["name"],
            category=i["category"],
            description=i.get("description", ""),
            amount=i["amount"],
        )
        for i in cart.catalog()
    ]


@router.post("/quote", response_model=SideStoreQuoteOut)
def quote_cart(req: SideStoreCartRequest) -> SideStoreQuoteOut:
    """Price a cart without charging anything.

    Read-only and unauthenticated by design: it is the same arithmetic the page
    already performs in the browser, and letting the storefront ask the server for
    the authoritative number is how the two stop drifting apart.
    """
    totals = _quote([i.model_dump() for i in req.items])
    return SideStoreQuoteOut(
        quantity=totals.quantity,
        subtotal=totals.subtotal,
        discount_rate=totals.discount_rate,
        discount=totals.discount,
        discounted_subtotal=totals.discounted_subtotal,
        shipping=totals.shipping,
        free_shipping_applied=totals.free_shipping_applied,
        tax=totals.tax,
        total=totals.total,
        currency=totals.currency,
        tax_basis=totals.tax_basis,
        tax_is_estimate=totals.tax_is_estimate,
    )


@router.post(
    "/checkout/session",
    response_model=CheckoutSessionOut,
    dependencies=[Depends(_checkout_throttle)],
)
def create_sidestore_checkout(
    req: SideStoreCartRequest, session: Session = Depends(get_session)
) -> CheckoutSessionOut:
    """Create a Stripe Checkout session for a Side Store cart.

    Tax is Stripe's job, not ours. The storefront quotes HST, so charging a live
    card without ``automatic_tax`` would collect less than the customer was shown
    and leave ClearGlass owing the difference. Rather than silently under-collect,
    live checkout refuses until Stripe Tax is configured — see STRIPE_SETUP.md.
    Mock mode is unaffected, so the whole flow stays testable offline.
    """
    totals = _quote([i.model_dump() for i in req.items])

    if payments.is_live() and not payments.automatic_tax_enabled():
        log_event(
            session,
            actor="sidestore",
            action="create_checkout_session",
            target=req.customer_email,
            payload={"rejected": "automatic_tax_disabled", "total": totals.total},
            result="rejected",
        )
        session.commit()
        raise HTTPException(
            status_code=503,
            detail=(
                "Side Store checkout is unavailable: the storefront quotes HST but "
                "Stripe Tax is not enabled, so a live charge would collect less than "
                "the customer was shown. Configure Tax settings and set "
                "STRIPE_AUTOMATIC_TAX=true."
            ),
        )

    result = payments.create_checkout_session(
        cart.to_stripe_line_items(totals),
        customer_email=req.customer_email,
        client_reference_id=req.client_reference_id,
        idempotency_key=req.client_reference_id,
        shipping_countries=SHIPPING_COUNTRIES,
        shipping_amount=totals.shipping,
        shipping_label=(
            "Free shipping" if totals.free_shipping_applied else "Standard shipping"
        ),
        extra_metadata={
            "store": "side_store",
            "bundle_rate": totals.discount_rate,
            "quoted_total": str(totals.total),
        },
    )
    log_event(
        session,
        actor="sidestore",
        action="create_checkout_session",
        target=req.customer_email,
        payload={
            "amount_total": result["amount_total"],
            "mode": result["mode"],
            "quantity": totals.quantity,
            "bundle_rate": totals.discount_rate,
            "shipping": totals.shipping,
            "items": [i.sku for i in totals.items],
        },
        result="executed",
    )
    return CheckoutSessionOut(**result)
