"""Append-only audit ledger writer.

Every material action MUST call ``log_event`` with actor, action, target, payload,
result and risk score. Rows are insert-only — never mutated or deleted.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from .governance import RiskAssessment
from .models import Event


def log_event(
    session: Session,
    *,
    actor: str,
    action: str,
    target: str | None,
    payload: dict,
    result: str,
    assessment: RiskAssessment | None = None,
) -> Event:
    """Insert one immutable audit row and return it."""
    event = Event(
        actor=actor,
        action=action,
        target=target,
        payload=_redact(payload),
        result=result,
        risk_score=assessment.score if assessment else 0,
        risk_tier=assessment.tier.value if assessment else "low",
    )
    session.add(event)
    session.flush()
    return event


_SECRET_KEYS = {"stripe_secret_key", "password", "token", "secret", "api_key", "card"}


def _redact(payload: dict) -> dict:
    """Strip anything that looks like a credential before it touches the ledger."""
    clean: dict = {}
    for key, value in payload.items():
        if any(s in key.lower() for s in _SECRET_KEYS):
            clean[key] = "***redacted***"
        else:
            clean[key] = value
    return clean
