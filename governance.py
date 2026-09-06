# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Governance core for the Autonomous Agent OS — risk scoring + approval gating.

Dependency-free (stdlib only) so it can be unit-tested and reused by automation
jobs without a database or web framework. It is the single place that decides
whether a proposed agent action may auto-execute or must be escalated to a
human, enforcing the platform invariant:

    read-only analysis -> draft -> human approval -> execution

Doctrine: fail closed. An unknown action, a missing confidence signal, or any
scoring error resolves to "approval required", never to auto-execute.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RiskTier(str, Enum):
    """Coarse risk classification that maps to an execution policy."""

    LOW = "low"            # auto-execute + log
    MEDIUM = "medium"      # queue for review
    HIGH = "high"          # approval required
    CRITICAL = "critical"  # approval required, highest scrutiny


# Proposed action types the OS sub-agents can emit, mapped to a base risk score
# (0-100). Anything touching money, production, secrets, destructive state, or
# mass outbound is gated regardless of score (see ALWAYS_ESCALATE).
ACTION_RISK: dict[str, int] = {
    # low — analysis / drafting, fully reversible
    "read_metrics": 0,
    "collect_evidence": 5,
    "generate_copy": 5,
    "draft_plan": 10,
    "reconcile_records": 10,
    "run_audit": 10,
    "update_knowledge_graph": 15,
    "draft_campaign": 20,
    # medium — reversible but customer-visible / stateful
    "update_catalog": 40,
    "publish_content": 45,
    "open_pull_request": 35,
    "run_ab_experiment": 40,
    # high — financial / outbound / infra, hard to reverse
    "update_pricing": 80,
    "send_outbound": 78,
    "launch_campaign": 70,
    "provision_infrastructure": 75,
    "rotate_secret": 82,
    # critical — irreversible or platform-level exposure
    "update_payment_settings": 100,
    "trigger_refund": 95,
    "delete_data": 96,
    "deploy_production": 92,
    "modify_access_control": 94,
}

# Always-escalate triggers, independent of computed score. Mirrors the OS
# governance rules: never move money, touch production, alter access, delete
# data, mass-message, or rotate credentials without explicit human approval.
ALWAYS_ESCALATE: frozenset[str] = frozenset(
    {
        "update_pricing",
        "update_payment_settings",
        "trigger_refund",
        "send_outbound",
        "launch_campaign",
        "deploy_production",
        "provision_infrastructure",
        "rotate_secret",
        "delete_data",
        "modify_access_control",
    }
)

_UNKNOWN_ACTION_SCORE = 85


@dataclass
class RiskAssessment:
    """Result of scoring a proposed action."""

    action: str
    score: int
    tier: RiskTier
    requires_approval: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "score": self.score,
            "tier": self.tier.value,
            "requires_approval": self.requires_approval,
            "reasons": list(self.reasons),
        }


def _tier_for_score(score: int) -> RiskTier:
    if score >= 90:
        return RiskTier.CRITICAL
    if score >= 60:
        return RiskTier.HIGH
    if score >= 30:
        return RiskTier.MEDIUM
    return RiskTier.LOW


def score_action(
    action: str,
    payload: dict[str, object] | None = None,
    *,
    confidence: float | None = None,
    has_evidence: bool = True,
) -> RiskAssessment:
    """Score an action 0-100 and decide whether it needs human approval.

    Fail closed on every axis:
      * unknown action            -> defaults to HIGH and is gated
      * ``confidence`` is None     -> treated as unverifiable, escalated
      * ``has_evidence`` is False  -> unsupported conclusion, escalated
      * any internal error         -> gated (see the guard below)
    """
    try:
        payload = payload or {}
        reasons: list[str] = []

        base = ACTION_RISK.get(action)
        if base is None:
            reasons.append(
                f"unknown action '{action}' — defaulting to high risk (fail closed)"
            )
            base = _UNKNOWN_ACTION_SCORE

        score = base

        if _money_delta(payload) >= 0.20:
            score = min(100, score + 10)
            reasons.append("price/amount change exceeds 20%")
        if payload.get("audience") == "all" or payload.get("bulk") is True:
            score = min(100, score + 8)
            reasons.append("affects all customers / bulk operation")
        if confidence is None:
            score = min(100, score + 12)
            reasons.append("confidence unavailable — escalate (fail closed)")
        elif confidence < 0.60:
            score = min(100, score + 12)
            reasons.append(f"low confidence {confidence:.2f} < 0.60 — escalate")
        if not has_evidence:
            score = min(100, score + 15)
            reasons.append("conclusion lacks supporting evidence — escalate")

        tier = _tier_for_score(score)
        requires_approval = (
            tier in (RiskTier.HIGH, RiskTier.CRITICAL)
            or action in ALWAYS_ESCALATE
            or confidence is None
            or not has_evidence
        )

        if action in ALWAYS_ESCALATE:
            reasons.append("action is in the always-escalate set (money / prod / access / data)")
        reasons.append(
            "hard gate — cannot auto-execute" if requires_approval
            else "auto-executable: reversible, low risk, evidence-backed"
        )

        return RiskAssessment(action, score, tier, requires_approval, reasons)
    except Exception as exc:  # pragma: no cover - defensive; any error fails closed
        return RiskAssessment(
            action=str(action),
            score=100,
            tier=RiskTier.CRITICAL,
            requires_approval=True,
            reasons=[f"scoring raised {type(exc).__name__}: fail closed"],
        )


def _money_delta(payload: dict[str, object]) -> float:
    """Relative magnitude of a price change, if both old and new prices exist."""
    old = payload.get("old_price")
    new = payload.get("new_price")
    try:
        old_f = float(old)  # type: ignore[arg-type]
        new_f = float(new)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    if old_f <= 0:
        return 1.0
    return abs(new_f - old_f) / old_f
