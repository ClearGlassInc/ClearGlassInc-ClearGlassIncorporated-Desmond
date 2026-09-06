"""Inventory routes — stock check (low) and reorder (high, gated)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_session
from ..models import Inventory, Variant
from ..schemas import ActionResult, InventoryCheckRequest
from ..service import run_governed_action

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("/check", response_model=ActionResult)
def check(req: InventoryCheckRequest, session: Session = Depends(get_session)) -> ActionResult:
    """Report low-stock SKUs. If ``reorder`` is requested, that is escalated as HIGH risk."""
    settings = get_settings()
    rows = session.execute(
        select(Variant.sku, Inventory.on_hand, Inventory.reorder_threshold).join(
            Inventory, Inventory.variant_id == Variant.id
        )
    ).all()
    low = [
        {"sku": sku, "on_hand": on_hand, "threshold": threshold}
        for sku, on_hand, threshold in rows
        if on_hand <= max(threshold, settings.inventory_low_threshold)
    ]

    if req.reorder:
        # Reorder spends money — always a gated, escalated action.
        return run_governed_action(
            session,
            actor="operations_agent",
            action="inventory_reorder",
            target="inventory",
            payload={"low_skus": low},
            execute=None,
            low_confidence=not low,
        )

    def execute() -> dict:
        return {"low_stock": low, "low_count": len(low)}

    return run_governed_action(
        session,
        actor="operations_agent",
        action="inventory_check",
        target="inventory",
        payload={"reorder": False},
        execute=execute,
    )
