"""Governance gate.

A lightweight mirror of the commerce control-plane safety model
(``clearglass-commerce/control-plane/app/governance.py``): every proposed
action is scored 0-100 and routed. Low-risk work auto-executes; anything that
would publish, deploy, move money, or send mass outbound is blocked pending a
human approval. This keeps the 4-D system inside the repository invariant of
*read-only analysis -> draft -> human approval -> execution*.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Signals that force a high/critical score — these mirror the "never do without
# approval" list in CLAUDE.md (pricing, payment, refund, fulfillment, mass
# outbound) plus any live publish/deploy.
_CRITICAL_SIGNALS = (
    "payment",
    "refund",
    "payout",
    "tax",
    "fulfillment",
    "reorder",
    "charge card",
    "wire",
)
_HIGH_SIGNALS = (
    "publish live",
    "go live",
    "deploy to production",
    "change price",
    "pricing update",
    "mass email",
    "mass outbound",
    "send to all",
)
_MEDIUM_SIGNALS = (
    "publish",
    "post ",
    "schedule",
    "commit",
    "catalog edit",
    "distribute",
)


@dataclass(frozen=True)
class GovernanceDecision:
    score: int
    level: RiskLevel
    auto_execute: bool
    requires_approval: bool
    reason: str


def score_action(description: str) -> GovernanceDecision:
    """Score a proposed action and decide how it may proceed."""
    text = description.lower()
    score = 10

    if any(sig in text for sig in _MEDIUM_SIGNALS):
        score = max(score, 45)
    if any(sig in text for sig in _HIGH_SIGNALS):
        score = max(score, 82)
    if any(sig in text for sig in _CRITICAL_SIGNALS):
        score = max(score, 95)

    if score >= 90:
        return GovernanceDecision(
            score=score,
            level=RiskLevel.CRITICAL,
            auto_execute=False,
            requires_approval=True,
            reason="critical money/fulfillment action blocked pending human approval",
        )
    if score >= 80:
        return GovernanceDecision(
            score=score,
            level=RiskLevel.HIGH,
            auto_execute=False,
            requires_approval=True,
            reason="high-impact live action blocked pending human approval",
        )
    if score >= 40:
        return GovernanceDecision(
            score=score,
            level=RiskLevel.MEDIUM,
            auto_execute=False,
            requires_approval=True,
            reason="content publish queued for approval",
        )
    return GovernanceDecision(
        score=score,
        level=RiskLevel.LOW,
        auto_execute=True,
        requires_approval=False,
        reason="read-only / low-risk analysis auto-executed and logged",
    )
