"""Etsy routes — connection detection, read-only verification, and gated writes.

Read paths (``/connection``, ``/verify``) are safe and always available. Every write
path (publish listing, sync inventory, manage order) first enforces the connection
guard — refusing outright if Etsy is not connected — and then routes through the
governance gate, so nothing reaches the live shop without human approval.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import etsy
from ..audit import log_event
from ..config import get_settings
from ..db import get_session
from ..governance import score_action
from ..schemas import (
    ActionResult,
    EtsyManageOrderRequest,
    EtsyPublishListingRequest,
    EtsySyncInventoryRequest,
)
from ..service import run_governed_action

router = APIRouter(prefix="/etsy", tags=["etsy"])


@router.get("/connection")
def get_connection() -> dict:
    """Detect whether Etsy is connected (credential presence only — no network)."""
    return etsy.connection_status(get_settings())


@router.post("/verify")
def verify(session: Session = Depends(get_session)) -> dict:
    """Read-only verification: shop identity, listing/order permissions, sync status.

    Logs the check to the audit ledger. If Etsy is not connected, returns the
    not-connected status with what is missing — and makes no network call.
    """
    settings = get_settings()
    result = etsy.verify_connection(settings)
    action = "etsy_verify_connection"
    log_event(
        session,
        actor="etsy_agent",
        action=action,
        target=str(result.get("shop", {}).get("shop_id") or "unconnected"),
        payload={"connected": result.get("connected"), "verified": result.get("verified")},
        result="verified" if result.get("verified") else "not_verified",
        assessment=score_action(action, {}),
    )
    return result


def _guarded_write(
    session: Session,
    *,
    actor: str,
    action: str,
    target: str | None,
    payload: dict,
) -> ActionResult:
    """Refuse the write if Etsy is not connected; otherwise route through governance.

    Every Etsy write action is in ``ALWAYS_ESCALATE``, so ``execute`` is ``None`` —
    the action can only ever be queued for human approval, never auto-run inline.
    """
    ready, reason = etsy.is_ready_for_writes(get_settings())
    if not ready:
        assessment = score_action(action, payload)
        log_event(
            session,
            actor=actor,
            action=action,
            target=target,
            payload=payload,
            result="blocked_not_connected",
            assessment=assessment,
        )
        return ActionResult(
            status="blocked_not_connected",
            action=action,
            risk_score=assessment.score,
            risk_tier=assessment.tier.value,
            requires_approval=True,
            reasons=[reason],
            data={"remedy": "Connect Etsy (POST /etsy/verify must pass) before proposing writes."},
        )
    return run_governed_action(
        session,
        actor=actor,
        action=action,
        target=target,
        payload=payload,
        execute=None,  # never runs inline — clears only via an approved approval
    )


@router.post("/publish-listing", response_model=ActionResult)
def publish_listing(
    req: EtsyPublishListingRequest, session: Session = Depends(get_session)
) -> ActionResult:
    """Propose publishing a listing to the live Etsy shop (HIGH — human-gated)."""
    return _guarded_write(
        session,
        actor="catalog_agent",
        action="etsy_publish_listing",
        target=req.sku,
        payload=req.model_dump(),
    )


@router.post("/sync-inventory", response_model=ActionResult)
def sync_inventory(
    req: EtsySyncInventoryRequest, session: Session = Depends(get_session)
) -> ActionResult:
    """Propose pushing inventory quantities to live listings (HIGH — human-gated)."""
    return _guarded_write(
        session,
        actor="operations_agent",
        action="etsy_sync_inventory",
        target="etsy_listings",
        payload=req.model_dump(),
    )


@router.post("/orders/manage", response_model=ActionResult)
def manage_order(
    req: EtsyManageOrderRequest, session: Session = Depends(get_session)
) -> ActionResult:
    """Propose a change to a live Etsy order/receipt (HIGH — human-gated)."""
    return _guarded_write(
        session,
        actor="operations_agent",
        action="etsy_manage_order",
        target=req.receipt_id,
        payload=req.model_dump(),
    )
