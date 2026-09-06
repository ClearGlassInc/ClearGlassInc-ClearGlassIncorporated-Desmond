"""Fulfillment routes — supplier connection, catalogue, and order routing.

Only ``/connection`` is open: it reports whether a credential is configured and
touches nothing. The other reads are admin-gated even though they mutate nothing
— ``/catalog`` because each call is a full paginated scan of the supplier store,
and ``/orders/{id}`` because it exposes tracking, supplier ids and our cost basis
behind a guessable integer.

Confirming a supplier order — the step that spends money and starts an
irreversible print run — requires an *approved* approval row bound to that
shipment, which the confirm path claims exactly once.

The shipment webhook is the one open mutating route, for the same reason the
Stripe one is: a supplier callback cannot carry an operator credential. It is
authenticated by a shared secret in the path, rate limited per IP, and
idempotent on redelivery.
"""
from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import fulfillment, printful
from ..audit import log_event
from ..config import get_settings
from ..db import get_session
from ..governance import score_action
from ..models import Order, Shipment
from ..security import rate_limit, require_admin

router = APIRouter(prefix="/fulfillment", tags=["fulfillment"])


@router.get("/connection")
def get_connection() -> dict:
    """Supplier connection state (credential presence only — no network call)."""
    return printful.connection_status(get_settings())


@router.post("/verify", dependencies=[Depends(require_admin)])
def verify(session: Session = Depends(get_session)) -> dict:
    """Read-only supplier identity check. Writes nothing at the supplier."""
    settings = get_settings()
    result = printful.verify_connection(settings)
    action = "printful_verify_connection"
    log_event(
        session,
        actor="fulfillment_agent",
        action=action,
        target=str(result.get("store_id") or "unconnected"),
        payload={"connected": result.get("connected"), "verified": result.get("verified")},
        result="verified" if result.get("verified") else "not_verified",
        assessment=score_action(action, {}),
    )
    return result


@router.get("/catalog", dependencies=[Depends(require_admin)])
def catalog(session: Session = Depends(get_session)) -> dict:
    """The supplier's real catalogue: their products, variants, images, prices.

    Read-only, and the only source of product data fit to publish. Nothing here
    is synthesised — a supplier we cannot read is a catalogue we do not show.

    Admin-gated, because one call is a full paginated scan of the supplier store
    plus a detail request per product. Anonymous access would let a stranger
    burn the Printful API quota and tie up workers for minutes at a time.
    """
    settings = get_settings()
    status = printful.connection_status(settings)
    if not status["connected"]:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "printful_not_connected",
                "missing": status["missing"],
                "hint": "Set PRINTFUL_API_KEY. Until then there is no catalogue to publish.",
            },
        )
    products = printful.store_products(settings)
    action = "printful_catalog_snapshot"
    log_event(
        session,
        actor="fulfillment_agent",
        action=action,
        target="printful_store",
        payload={"product_count": len(products)},
        result="executed",
        assessment=score_action(action, {}),
    )
    return {"supplier": "printful", "count": len(products), "products": products}


@router.get("/exceptions", dependencies=[Depends(require_admin)])
def exceptions(session: Session = Depends(get_session)) -> dict:
    """Paid orders that cannot ship, oldest first.

    Marking an order ``unfulfillable`` and writing an audit event is not enough
    on its own — nothing queries either, so the obligation would sit unnoticed
    while the customer's money stays taken. This is the queue that makes it
    visible, and every row here is an open debt to someone.
    """
    orders = session.scalars(
        select(Order)
        .where(Order.fulfillment_status == "unfulfillable")
        .order_by(Order.created_at)
    ).all()
    return {
        "count": len(orders),
        "orders": [
            {
                "order_id": o.id,
                "external_ref": o.external_ref,
                "status": o.status,
                "total": str(o.total),
                "currency": o.currency,
                "ship_to_country": o.ship_to_country,
                "created_utc": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ],
        "note": "each of these is a paid order with no parcel — resolve or refund",
    }


@router.get("/orders/{order_id}", dependencies=[Depends(require_admin)])
def order_fulfillment(order_id: int, session: Session = Depends(get_session)) -> dict:
    """Fulfillment state and tracking for one order. Read-only, admin-gated.

    The order id is a sequential integer, and this returns tracking, supplier
    order ids and what the supplier charged us — so an open version of this
    route would let anyone walk the range and read the whole order book, cost
    basis included. A customer-facing "where is my parcel" view needs a
    per-order capability token rather than an integer; until that exists this
    stays behind the admin credential.
    """
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    shipments = session.scalars(select(Shipment).where(Shipment.order_id == order_id)).all()
    return {
        "order_id": order.id,
        "fulfillment_status": order.fulfillment_status,
        "ship_to_country": order.ship_to_country,
        "shipments": [
            {
                "id": s.id,
                "supplier": s.supplier,
                "supplier_order_id": s.supplier_order_id,
                "status": s.status,
                "tracking_number": s.tracking_number,
                "tracking_url": s.tracking_url,
                "carrier": s.carrier,
                "supplier_cost": str(s.supplier_cost) if s.supplier_cost is not None else None,
                "currency": s.currency,
            }
            for s in shipments
        ],
    }


@router.post("/shipments/{shipment_id}/confirm", dependencies=[Depends(require_admin)])
def confirm(shipment_id: int, session: Session = Depends(get_session)) -> dict:
    """Confirm a drafted supplier order — **spends money and starts production**.

    Always escalates: without an approved approval row this queues one and
    returns its id rather than confirming.
    """
    shipment = session.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="shipment not found")
    return fulfillment.confirm_shipment(session, shipment)


@router.post(
    "/webhooks/printful/{secret}",
    dependencies=[Depends(rate_limit("printful_webhook", "rate_limit_webhook_per_minute"))],
)
async def printful_webhook(
    secret: str,
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    """Supplier shipment notices (``package_shipped``).

    Authenticated by a shared secret in the path — Printful's webhooks carry no
    signature header, so the URL itself is the credential. It is compared in
    constant time, and an unset secret rejects every call rather than accepting
    all of them: failing open here would let anyone mark orders shipped.
    """
    settings = get_settings()
    configured = settings.printful_webhook_secret
    if not configured or not hmac.compare_digest(secret, configured):
        raise HTTPException(status_code=404, detail="not found")

    payload = await request.json()
    try:
        notice = printful.parse_shipment_webhook(payload)
    except printful.PrintfulError as exc:
        # Acknowledge so the supplier stops retrying, but record why we ignored it.
        log_event(
            session,
            actor="printful",
            action="printful_order_status",
            target="webhook",
            payload={"reason": str(exc), "type": payload.get("type")},
            result="rejected",
            assessment=score_action("printful_order_status", {}),
        )
        return {"received": True, "applied": False, "reason": str(exc)}

    return {"received": True, **fulfillment.record_shipment_notice(session, notice)}
