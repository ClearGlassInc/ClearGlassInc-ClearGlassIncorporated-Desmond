"""Store routes — product refresh, copy generation, pricing (gated)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_session
from ..schemas import (
    ActionResult,
    GenerateCopyRequest,
    RefreshProductsRequest,
    UpdatePricingRequest,
)
from ..service import run_governed_action

router = APIRouter(prefix="/store", tags=["store"])


@router.post("/refresh-products", response_model=ActionResult)
def refresh_products(req: RefreshProductsRequest, session: Session = Depends(get_session)) -> ActionResult:
    """Pull the latest catalog from a supplier feed (medium risk — reversible)."""
    def execute() -> dict:
        return {"source": req.source, "dry_run": req.dry_run, "synced": 0}

    return run_governed_action(
        session,
        actor="catalog_agent",
        action="refresh_products",
        target=req.source,
        payload=req.model_dump(),
        execute=execute,
    )


@router.post("/generate-copy", response_model=ActionResult)
def generate_copy(req: GenerateCopyRequest, session: Session = Depends(get_session)) -> ActionResult:
    """Draft product copy (low risk — drafting only, never auto-published)."""
    def execute() -> dict:
        return {
            "product_slug": req.product_slug,
            "kind": req.kind,
            "draft": f"[{req.kind}] draft for {req.product_slug} in voice: {req.brand_voice}",
            "note": "draft only — publishing is a separate medium-risk action",
        }

    return run_governed_action(
        session,
        actor="content_agent",
        action="generate_copy",
        target=req.product_slug,
        payload=req.model_dump(),
        execute=execute,
    )


@router.post("/update-pricing", response_model=ActionResult)
def update_pricing(req: UpdatePricingRequest, session: Session = Depends(get_session)) -> ActionResult:
    """Change a live price (HIGH risk — always routed to human approval)."""
    return run_governed_action(
        session,
        actor="strategy_agent",
        action="update_pricing",
        target=req.sku,
        payload=req.model_dump(),
        execute=None,  # never executes inline; clears only via approved approval
    )
