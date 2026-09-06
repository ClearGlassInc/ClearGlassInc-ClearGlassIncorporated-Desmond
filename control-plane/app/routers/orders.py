"""Order routes — reconciliation (read/draft, low risk)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Order
from ..schemas import ActionResult
from ..service import run_governed_action

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/reconcile", response_model=ActionResult)
def reconcile(session: Session = Depends(get_session)) -> ActionResult:
    """Reconcile order records against expected state (read-only summary)."""
    def execute() -> dict:
        total = session.scalar(select(func.count()).select_from(Order)) or 0
        pending = session.scalar(
            select(func.count()).select_from(Order).where(Order.status == "pending")
        ) or 0
        exceptions = session.scalar(
            select(func.count()).select_from(Order).where(Order.status == "exception")
        ) or 0
        return {"orders": total, "pending": pending, "exceptions": exceptions}

    return run_governed_action(
        session,
        actor="operations_agent",
        action="reconcile_orders",
        target="orders",
        payload={},
        execute=execute,
    )
