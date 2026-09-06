# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Executive orchestration layer — the deterministic mission runner.

Takes an objective plus optional strategies, evidence claims, and proposed
actions, and produces the platform's mandated Output Requirements as a
reproducible :class:`MissionReport`. It composes the advanced sub-agents:

* Executive  — ranks strategies by expected value (highest-EV choice).
* Intelligence — cross-references multi-source claims, flags contradictions,
  and contributes a confidence that never inflates the mission's certainty.
* Governance  — routes every proposed action; high/critical, unverifiable, or
  evidence-free actions are held behind the human approval gate.
* Audit       — every decision is written to a tamper-evident hash chain.

No side effects: this layer *decides and reports*; it never executes external
actions itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .audit import AuditLedger
from .executive import Strategy, rank_strategies
from .governance import RiskAssessment, score_action
from .intelligence import Claim, aggregate_confidence, cross_reference
from .planning import Task, critical_path_minutes, plan_waves

DECISION_FRAMEWORK: tuple[str, ...] = (
    "understand objective", "identify constraints", "gather evidence",
    "generate multiple strategies", "estimate probability of success",
    "estimate cost", "estimate risk", "choose highest expected value",
    "verify", "execute", "audit", "learn",
)

EXECUTION_LOOP: tuple[str, ...] = (
    "observe", "analyze", "prioritize", "plan", "execute", "validate",
    "audit", "optimize", "learn",
)

OUTPUT_FIELDS: tuple[str, ...] = (
    "mission_summary", "objective", "assumptions", "dependencies",
    "execution_plan", "risk_assessment", "evidence", "confidence_score",
    "artifacts_produced", "validation_results", "rollback_plan",
    "optimization_opportunities", "next_recommended_actions",
)


@dataclass
class ProposedAction:
    """An action a sub-agent wants to take, with the signals governance needs."""

    action: str
    summary: str = ""
    payload: dict[str, object] = field(default_factory=dict)
    confidence: float | None = None
    evidence: tuple[str, ...] = ()


@dataclass
class MissionReport:
    """The mandated Output Requirements for a completed workflow."""

    mission_summary: str
    objective: str
    assumptions: list[str]
    dependencies: list[list[str]]
    execution_plan: list[dict[str, object]]
    risk_assessment: list[dict[str, object]]
    evidence: list[str]
    confidence_score: float | None
    artifacts_produced: list[str]
    validation_results: dict[str, object]
    rollback_plan: str
    optimization_opportunities: list[str]
    next_recommended_actions: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class AgentOS:
    """The executive orchestration layer.

    Deterministic given the same inputs; produces a full mission report and never
    lets a gated action auto-execute.
    """

    decision_framework = DECISION_FRAMEWORK
    execution_loop = EXECUTION_LOOP

    def run_mission(
        self,
        objective: str,
        *,
        tasks: list[Task] | None = None,
        proposed_actions: list[ProposedAction] | None = None,
        assumptions: list[str] | None = None,
        strategies: list[Strategy] | None = None,
        claims: list[Claim] | None = None,
        ledger: AuditLedger | None = None,
    ) -> MissionReport:
        tasks = tasks or []
        proposed_actions = proposed_actions or []
        assumptions = assumptions or []
        strategies = strategies or []
        claims = claims or []
        ledger = ledger if ledger is not None else AuditLedger()

        ledger.append("mission_start", {"objective": objective})

        waves = plan_waves(tasks) if tasks else []
        est_minutes = critical_path_minutes(tasks) if tasks else 0

        # Executive: rank candidate strategies by expected value.
        ranked = rank_strategies(strategies)
        chosen = ranked[0] if ranked else None

        # Intelligence: cross-reference evidence, detect contradictions.
        findings = cross_reference(claims)
        intel_conf = aggregate_confidence(findings)
        contradictions = [f.to_dict() for f in findings if f.contradicted]

        assessments: list[RiskAssessment] = []
        evidence: list[str] = [c.value for c in claims]
        confidences: list[float] = []
        auto: list[str] = []
        gated: list[str] = []

        for pa in proposed_actions:
            assessment = score_action(
                pa.action,
                pa.payload,
                confidence=pa.confidence,
                has_evidence=bool(pa.evidence),
            )
            assessments.append(assessment)
            evidence.extend(pa.evidence)
            if pa.confidence is not None:
                confidences.append(pa.confidence)
            (gated if assessment.requires_approval else auto).append(pa.action)
            ledger.append(
                "action_assessed",
                {"action": pa.action, "requires_approval": assessment.requires_approval,
                 "tier": assessment.tier.value},
            )

        # Mission confidence is the *minimum* observed signal — never inflate.
        signals = list(confidences)
        if intel_conf is not None:
            signals.append(intel_conf)
        confidence_score = round(min(signals), 4) if signals else None

        execution_plan: list[dict[str, object]] = [
            {"wave": i + 1, "tasks": w} for i, w in enumerate(waves)
        ]
        if est_minutes:
            execution_plan.append({"critical_path_minutes": est_minutes})
        if chosen is not None:
            execution_plan.append(
                {"chosen_strategy": chosen.name, "expected_value": chosen.expected_value}
            )

        next_actions: list[str] = []
        if gated:
            next_actions.append(
                f"Request human approval for {len(gated)} gated action(s): "
                + ", ".join(sorted(set(gated)))
            )
        if auto:
            next_actions.append("Auto-executable (logged): " + ", ".join(sorted(set(auto))))
        if contradictions:
            next_actions.append(
                f"Resolve {len(contradictions)} evidence contradiction(s) before acting"
            )
        if not proposed_actions and not contradictions:
            next_actions.append("No actions proposed — read-only analysis only.")

        optimization: list[str] = [
            f"Consider fallback strategy '{r.name}' (EV {r.expected_value})"
            for r in ranked[1:3]
        ]

        ledger.append(
            "mission_complete",
            {"auto": sorted(set(auto)), "gated": sorted(set(gated)),
             "confidence": confidence_score},
        )
        chain_ok, bad_index = ledger.verify()

        summary = (
            f"Read-only orchestration complete for objective: {objective!r}. "
            f"{len(auto)} action(s) auto-executable, {len(gated)} gated behind "
            f"human approval, {len(contradictions)} contradiction(s) flagged. "
            f"No irreversible action taken."
        )

        return MissionReport(
            mission_summary=summary,
            objective=objective,
            assumptions=assumptions,
            dependencies=waves,
            execution_plan=execution_plan,
            risk_assessment=[a.to_dict() for a in assessments],
            evidence=evidence,
            confidence_score=confidence_score,
            artifacts_produced=[f"audit_chain_head:{ledger.head}"],
            validation_results={
                "governance_gate": "enforced",
                "gated_actions": sorted(set(gated)),
                "auto_actions": sorted(set(auto)),
                "audit_chain_verified": chain_ok,
                "audit_chain_bad_index": bad_index,
                "contradictions": contradictions,
                "intelligence_confidence": intel_conf,
            },
            rollback_plan=(
                "Revert the mission's committed artifacts; no external side effects "
                "were performed by the orchestrator itself."
            ),
            optimization_opportunities=optimization,
            next_recommended_actions=next_actions,
        )
