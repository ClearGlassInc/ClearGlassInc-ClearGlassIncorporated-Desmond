"""Shared governed-action runner used by every router.

Pipeline: score → (gate ? queue approval : execute) → audit. This guarantees no
high/critical action can execute without an approval, and that every path is logged.
"""
from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .audit import log_event
from .config import get_settings
from .governance import RiskTier, score_action
from .models import Approval
from .schemas import ActionResult


def run_governed_action(
    session: Session,
    *,
    actor: str,
    action: str,
    target: str | None,
    payload: dict,
    execute: Callable[[], dict] | None = None,
    low_confidence: bool = False,
) -> ActionResult:
    """Score an action and either execute it (low/medium) or queue an approval (high/critical).

    ``execute`` is the side-effecting callable; it is only invoked when the action is
    cleared to run. Read-only/drafting actions pass an ``execute`` that returns their data.
    """
    settings = get_settings()
    assessment = score_action(
        action,
        payload,
        require_approval_for_high_risk=settings.require_approval_for_high_risk,
        low_confidence=low_confidence,
    )

    if assessment.requires_approval:
        approval = Approval(
            action=action,
            target=target,
            payload=payload,
            risk_score=assessment.score,
            risk_tier=assessment.tier.value,
            status="pending",
            requested_by=actor,
        )
        session.add(approval)
        session.flush()
        log_event(
            session,
            actor=actor,
            action=action,
            target=target,
            payload=payload,
            result="queued_for_approval",
            assessment=assessment,
        )
        return ActionResult(
            status="queued_for_approval",
            action=action,
            risk_score=assessment.score,
            risk_tier=assessment.tier.value,
            requires_approval=True,
            approval_id=approval.id,
            reasons=assessment.reasons,
            data={"escalation": "human approval required before execution"},
        )

    data = execute() if execute else {}
    result = "drafted" if assessment.tier == RiskTier.LOW and action.startswith("draft") else "executed"
    log_event(
        session,
        actor=actor,
        action=action,
        target=target,
        payload=payload,
        result=result,
        assessment=assessment,
    )
    return ActionResult(
        status=result,
        action=action,
        risk_score=assessment.score,
        risk_tier=assessment.tier.value,
        requires_approval=False,
        reasons=assessment.reasons,
        data=data,
    )


def claim_approval(session: Session, *, action: str, target: str) -> Approval | None:
    """Atomically claim one approved approval for this action and target.

    The gate only works if an approval is spent exactly once. The claim is a
    conditional ``UPDATE ... WHERE status = 'approved'`` whose row count is the
    proof: two concurrent confirmations race on the same row and exactly one
    wins, so a single human decision cannot be replayed into two supplier
    charges. An approval is bound to its target, so approving one shipment can
    never confirm a different one.
    """
    candidate = session.scalar(
        select(Approval)
        .where(Approval.action == action, Approval.target == target, Approval.status == "approved")
        .order_by(Approval.id)
        .limit(1)
    )
    if candidate is None:
        return None

    claimed = session.execute(
        update(Approval)
        .where(Approval.id == candidate.id, Approval.status == "approved")
        .values(status="executed")
    )
    if claimed.rowcount != 1:
        return None  # another worker claimed it first

    # Commit the claim *before* the caller spends money. A flush alone lives
    # inside the request transaction, so a crash between the supplier accepting
    # the confirmation and the request committing would roll the row back to
    # `approved` and let the same decision authorise a second charge.
    # Committing here trades that for the opposite failure: a claim that is
    # spent without the call having demonstrably happened, which needs a fresh
    # human decision rather than silently paying twice.
    session.commit()
    return candidate
