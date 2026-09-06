"""Events route — read the append-only audit ledger."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Event
from ..schemas import EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventOut])
def list_events(limit: int = 100, session: Session = Depends(get_session)) -> list[Event]:
    """Return the most recent audit events (newest first)."""
    limit = max(1, min(limit, 500))
    return list(
        session.execute(select(Event).order_by(Event.id.desc()).limit(limit)).scalars().all()
    )
