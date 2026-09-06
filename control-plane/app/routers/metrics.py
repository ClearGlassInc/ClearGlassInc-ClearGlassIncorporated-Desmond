"""Metrics routes — KPI overview (read-only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Approval, MetricsDaily
from ..schemas import MetricsOverview

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/overview", response_model=MetricsOverview)
def overview(window_days: int = 7, session: Session = Depends(get_session)) -> MetricsOverview:
    """Aggregate the most recent KPI snapshots plus open-approval count."""
    rows = session.execute(
        select(MetricsDaily).order_by(MetricsDaily.day.desc()).limit(window_days)
    ).scalars().all()

    revenue = float(sum((r.revenue for r in rows), start=0))
    orders = sum(r.orders for r in rows)
    aov = float(rows[0].aov) if rows else 0.0
    conversion = float(rows[0].conversion_rate) if rows else 0.0
    refund = float(rows[0].refund_rate) if rows else 0.0

    open_approvals = session.scalar(
        select(func.count()).select_from(Approval).where(Approval.status == "pending")
    ) or 0

    return MetricsOverview(
        revenue=round(revenue, 2),
        orders=orders,
        conversion_rate=conversion,
        aov=aov,
        refund_rate=refund,
        open_approvals=open_approvals,
        window_days=window_days,
    )
