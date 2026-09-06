"""ClearGlassInc Artemis self-evolving intelligence platform blueprint and runtime.

The module is a dependency-light Python reference implementation for a Palantir
Gotham, Foundry, AIP, and Apollo deployment.  It intentionally models only
safe, human-gated intelligence workflows: agents may triage, enrich, recommend,
and propose upgrades, but operational effects and prompt/workflow changes must
pass policy checks and explicit human approval before activation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from statistics import fmean, pstdev
from typing import Any, Literal
from uuid import uuid4

Classification = Literal["UNCLASS", "CUI", "SECRET", "TOP_SECRET"]
Decision = Literal["approve", "reject", "revise"]
EntityType = Literal["person", "organization", "asset", "event", "location", "case", "intel_product"]


class ApprovalGate(str, Enum):
    """Human-control checkpoints for agent actions."""

    READ_ONLY = "read_only"
    CASE_WRITEBACK = "case_writeback"
    EXTERNAL_RELEASE = "external_release"
    OPERATIONAL_EFFECT = "operational_effect"
    SELF_UPGRADE = "self_upgrade"


@dataclass(frozen=True)
class ArchitectureLayer:
    name: str
    palantir_role: str
    responsibilities: tuple[str, ...]
    implementation: tuple[str, ...]


@dataclass(frozen=True)
class ArtemisArchitecture:
    """End-to-end production architecture for ClearGlassInc Artemis."""

    organization: str = "ClearGlassInc Artemis"
    layers: tuple[ArchitectureLayer, ...] = (
        ArchitectureLayer(
            name="Frontend command surface",
            palantir_role="Gotham operational UI plus Foundry workshop applications",
            responsibilities=(
                "analyst workbench, commander dashboard, case board, alert queue",
                "explainable AI recommendations with evidence, lineage, and approval buttons",
                "mission timelines, entity graph exploration, and intel-product authoring",
            ),
            implementation=("TypeScript/React", "GraphQL subscriptions", "signed action review forms"),
        ),
        ArchitectureLayer(
            name="Backend services",
            palantir_role="Foundry application logic and Gotham case writeback adapters",
            responsibilities=(
                "API gateway, workflow state machines, entity-resolution services",
                "tool execution broker, case package builder, audit event producer",
                "latency-aware query planning and cache hydration",
            ),
            implementation=("Python FastAPI", "Temporal-style workflows", "PostgreSQL/Foundry Object APIs"),
        ),
        ArchitectureLayer(
            name="Data and ontology",
            palantir_role="Foundry datasets, transforms, object sets, and Ontology",
            responsibilities=(
                "live and historical ingestion, lineage, quality checks, semantic objects",
                "entity, relationship, confidence, temporal-state, and permission modeling",
                "object-driven workflows consumed by humans and AIP agents",
            ),
            implementation=("PySpark/SQL transforms", "ontology actions", "vector/search indexes"),
        ),
        ArchitectureLayer(
            name="AI orchestration",
            palantir_role="AIP copilots, agents, tools, evals, and model routing",
            responsibilities=(
                "triage, enrichment, correlation, summarization, recommendation",
                "retrieval-augmented generation with policy-filtered context",
                "prompt/workflow/model-route experiments behind approval gates",
            ),
            implementation=("tool registry", "model router", "eval harness", "prompt registry"),
        ),
        ArchitectureLayer(
            name="Deployment and runtime control",
            palantir_role="Apollo deployment rings, health checks, rollback, and configuration",
            responsibilities=(
                "secure promotion from dev to staging to mission rings",
                "versioned prompts, workflows, tools, policies, and containers",
                "canary analysis, rollback pointers, and runtime kill switches",
            ),
            implementation=("Apollo-style release channels", "signed artifacts", "immutable audit log"),
        ),
    )

    def as_markdown(self) -> str:
        lines = [f"# {self.organization} — Self-Evolving Intelligence Platform", ""]
        for layer in self.layers:
            lines.extend(
                [
                    f"## {layer.name}",
                    f"**Palantir role:** {layer.palantir_role}",
                    "",
                    "Responsibilities:",
                    *(f"- {item}" for item in layer.responsibilities),
                    "",
                    "Implementation:",
                    *(f"- {item}" for item in layer.implementation),
                    "",
                ]
            )
        return "\n".join(lines)


@dataclass(frozen=True)
class LineageRef:
    source: str
    dataset_rid: str
    transform_version: str
    checksum: str
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_payload(cls, source: str, dataset_rid: str, version: str, payload: dict[str, Any]) -> "LineageRef":
        digest = sha256(repr(sorted(payload.items())).encode("utf-8")).hexdigest()
        return cls(source=source, dataset_rid=dataset_rid, transform_version=version, checksum=digest)


@dataclass
class OntologyEntity:
    entity_id: str
    entity_type: EntityType
    name: str
    classification: Classification
    compartments: frozenset[str]
    coalition_releasability: frozenset[str]
    confidence: float
    valid_from: datetime
    attributes: dict[str, Any] = field(default_factory=dict)
    lineage: tuple[LineageRef, ...] = ()


@dataclass(frozen=True)
class OntologyRelationship:
    source_id: str
    target_id: str
    relation_type: str
    confidence: float
    valid_from: datetime
    valid_to: datetime | None = None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class MissionContext:
    mission_id: str
    objective: str
    commander_intent: str
    allowed_tools: frozenset[str]
    prohibited_tools: frozenset[str]
    compartments: frozenset[str]
    coalition: frozenset[str]
    latency_budget_ms: int = 750


@dataclass(frozen=True)
class Principal:
    principal_id: str
    clearance: Classification
    compartments: frozenset[str]
    coalition: frozenset[str]
    purpose: str


class PolicyEngine:
    """Need-to-know, compartment, coalition, and tool policy checks."""

    clearance_order = {"UNCLASS": 0, "CUI": 1, "SECRET": 2, "TOP_SECRET": 3}

    def can_read(self, principal: Principal, entity: OntologyEntity, mission: MissionContext) -> bool:
        if self.clearance_order[principal.clearance] < self.clearance_order[entity.classification]:
            return False
        if not entity.compartments.issubset(principal.compartments | mission.compartments):
            return False
        if entity.coalition_releasability and not entity.coalition_releasability.intersection(principal.coalition | mission.coalition):
            return False
        return True

    def can_execute(self, principal: Principal, tool_name: str, gate: ApprovalGate, mission: MissionContext) -> bool:
        if tool_name in mission.prohibited_tools:
            return False
        if tool_name not in mission.allowed_tools:
            return False
        if gate is ApprovalGate.READ_ONLY:
            return True
        return principal.purpose in {"mission_operations", "approved_evaluation", "commander_review"}


@dataclass(frozen=True)
class IntelEvent:
    event_id: str
    entity: OntologyEntity
    severity: float
    text: str
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class AgentRecommendation:
    recommendation_id: str
    agent: str
    tool_name: str
    gate: ApprovalGate
    rationale: str
    confidence: float
    evidence_entity_ids: tuple[str, ...]
    arguments: dict[str, Any]


class ArtemisAgentMesh:
    """Deterministic, auditable agent mesh for triage-to-action workflows."""

    def __init__(self, policy: PolicyEngine) -> None:
        self.policy = policy

    def triage(self, event: IntelEvent, principal: Principal, mission: MissionContext) -> AgentRecommendation:
        if not self.policy.can_read(principal, event.entity, mission):
            raise PermissionError("principal lacks need-to-know for event entity")
        if event.severity >= 0.85:
            tool_name, gate = "prepare_action_package", ApprovalGate.OPERATIONAL_EFFECT
        elif event.severity >= 0.65:
            tool_name, gate = "open_gotham_case", ApprovalGate.CASE_WRITEBACK
        else:
            tool_name, gate = "append_watchlist_note", ApprovalGate.READ_ONLY
        if not self.policy.can_execute(principal, tool_name, gate, mission):
            raise PermissionError(f"tool {tool_name} is not authorized for mission")
        return AgentRecommendation(
            recommendation_id=str(uuid4()),
            agent="clear_glass_artemis_triage_agent.v1",
            tool_name=tool_name,
            gate=gate,
            rationale=(
                f"Severity={event.severity:.2f}; entity={event.entity.name}; "
                f"mission={mission.objective}; commander_intent={mission.commander_intent}"
            ),
            confidence=max(0.01, min(0.99, event.severity * event.entity.confidence)),
            evidence_entity_ids=(event.entity.entity_id,),
            arguments={"event_id": event.event_id, "entity_id": event.entity.entity_id, "mission_id": mission.mission_id},
        )


@dataclass(frozen=True)
class PolicyDecision:
    """Auditable, redacted tool authorization result for AIP tool calls."""

    audit_id: str
    allowed: bool
    tool_name: str
    gate: ApprovalGate
    recommendation_id: str
    approved_by: str | None
    redacted_reason: str


class ToolExecutionBroker:
    """Policy gate between agent recommendations and side-effecting tools.

    The broker deliberately separates model output from execution. Read-only
    tools may run when mission policy allows them; case writeback, operational
    effects, external release, and self-upgrade actions additionally require a
    human approval identifier so unsafe autonomous execution fails closed.
    """

    _human_gated = {
        ApprovalGate.CASE_WRITEBACK,
        ApprovalGate.EXTERNAL_RELEASE,
        ApprovalGate.OPERATIONAL_EFFECT,
        ApprovalGate.SELF_UPGRADE,
    }

    def __init__(self, policy_engine: PolicyEngine) -> None:
        self.policy_engine = policy_engine

    def evaluate(
        self,
        principal: Principal,
        mission: MissionContext,
        recommendation: AgentRecommendation,
        approved_by: str | None = None,
    ) -> PolicyDecision:
        audit_id = str(uuid4())
        if not self.policy_engine.can_execute(principal, recommendation.tool_name, recommendation.gate, mission):
            return PolicyDecision(
                audit_id=audit_id,
                allowed=False,
                tool_name=recommendation.tool_name,
                gate=recommendation.gate,
                recommendation_id=recommendation.recommendation_id,
                approved_by=None,
                redacted_reason="Tool is not authorized for this mission context.",
            )
        if recommendation.gate in self._human_gated and not approved_by:
            return PolicyDecision(
                audit_id=audit_id,
                allowed=False,
                tool_name=recommendation.tool_name,
                gate=recommendation.gate,
                recommendation_id=recommendation.recommendation_id,
                approved_by=None,
                redacted_reason="Human approval is required before execution.",
            )
        return PolicyDecision(
            audit_id=audit_id,
            allowed=True,
            tool_name=recommendation.tool_name,
            gate=recommendation.gate,
            recommendation_id=recommendation.recommendation_id,
            approved_by=approved_by,
            redacted_reason="allowed",
        )

    def dispatch(self, decision: PolicyDecision) -> dict[str, str]:
        if not decision.allowed:
            raise PermissionError(decision.redacted_reason)
        return {
            "audit_id": decision.audit_id,
            "tool_name": decision.tool_name,
            "status": "queued_for_adapter_dispatch",
        }


@dataclass(frozen=True)
class OperatorFeedback:
    recommendation_id: str
    decision: Decision
    correction: str
    outcome_score: float
    latency_ms: int
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class EvalResult:
    precision: float
    recall: float
    operator_trust: float
    p95_latency_ms: float
    drift_zscore: float


@dataclass(frozen=True)
class UpgradeProposal:
    proposal_id: str
    target: Literal["prompt", "workflow", "heuristic", "model_route"]
    current_version: str
    candidate_version: str
    diff_summary: str
    eval_result: EvalResult
    rollback_pointer: str
    gate: ApprovalGate = ApprovalGate.SELF_UPGRADE


class SelfImprovementEngine:
    """Converts feedback into evaluated, rollback-safe upgrade proposals."""

    def build_evals(self, feedback: list[OperatorFeedback], baseline_scores: list[float]) -> EvalResult:
        if not feedback:
            raise ValueError("feedback is required to build evals")
        approved = [item for item in feedback if item.decision == "approve"]
        high_outcome = [item for item in feedback if item.outcome_score >= 0.7]
        outcomes = [item.outcome_score for item in feedback]
        latencies = sorted(item.latency_ms for item in feedback)
        p95_index = min(len(latencies) - 1, int(round(0.95 * (len(latencies) - 1))))
        drift = self._drift_zscore(outcomes, baseline_scores) if len(outcomes) >= 5 and len(baseline_scores) >= 5 else 0.0
        return EvalResult(
            precision=round(len(approved) / len(feedback), 4),
            recall=round(len(high_outcome) / len(feedback), 4),
            operator_trust=round(fmean(outcomes), 4),
            p95_latency_ms=float(latencies[p95_index]),
            drift_zscore=round(drift, 4),
        )

    def propose(self, feedback: list[OperatorFeedback], current_version: str, baseline_scores: list[float]) -> UpgradeProposal | None:
        revise_or_reject = [item for item in feedback if item.decision in {"reject", "revise"}]
        if len(feedback) < 5 or len(revise_or_reject) < 2:
            return None
        eval_result = self.build_evals(feedback, baseline_scores)
        return UpgradeProposal(
            proposal_id=str(uuid4()),
            target="workflow",
            current_version=current_version,
            candidate_version=f"{current_version}+operator-feedback.{len(feedback)}",
            diff_summary="Add stricter source-corroboration and commander-intent checks before case writeback or action-package recommendations.",
            eval_result=eval_result,
            rollback_pointer=current_version,
        )

    def promotion_decision(self, proposal: UpgradeProposal) -> Decision:
        metrics = proposal.eval_result
        if metrics.drift_zscore > 3.0 or metrics.p95_latency_ms > 750:
            return "reject"
        if metrics.precision >= 0.80 and metrics.operator_trust >= 0.72:
            return "approve"
        return "revise"

    @staticmethod
    def _drift_zscore(current: list[float], baseline: list[float]) -> float:
        sigma = pstdev(baseline) or 1e-6
        return abs(fmean(current) - fmean(baseline)) / sigma


def run_cinematic_scenario() -> dict[str, Any]:
    """Run an end-to-end safe event-to-learning demonstration."""

    policy = PolicyEngine()
    mission = MissionContext(
        mission_id="ARTEMIS-MSN-001",
        objective="Protect coalition logistics from live multi-domain disruption",
        commander_intent="Move fast, preserve attribution, and require review for operational effects",
        allowed_tools=frozenset({"append_watchlist_note", "open_gotham_case", "prepare_action_package"}),
        prohibited_tools=frozenset({"auto_execute_countermeasure", "external_release_without_review"}),
        compartments=frozenset({"LOGISTICS", "CYBER"}),
        coalition=frozenset({"FVEY"}),
    )
    principal = Principal(
        principal_id="operator.artemis.watchfloor",
        clearance="SECRET",
        compartments=frozenset({"LOGISTICS", "CYBER"}),
        coalition=frozenset({"FVEY"}),
        purpose="mission_operations",
    )
    payload = {"sensor": "foundry.live.alerts", "severity": 0.88, "route": "north-corridor"}
    entity = OntologyEntity(
        entity_id="evt-bridge-telemetry-anomaly",
        entity_type="event",
        name="North corridor telemetry anomaly",
        classification="SECRET",
        compartments=frozenset({"LOGISTICS", "CYBER"}),
        coalition_releasability=frozenset({"FVEY"}),
        confidence=0.91,
        valid_from=datetime.now(timezone.utc),
        attributes=payload,
        lineage=(LineageRef.from_payload("foundry_stream", "ri.foundry.main.dataset.live_alerts", "normalize.v7", payload),),
    )
    event = IntelEvent(event_id="live-0001", entity=entity, severity=0.88, text="Unexpected telemetry pattern on coalition logistics corridor")
    recommendation = ArtemisAgentMesh(policy).triage(event, principal, mission)
    feedback = [
        OperatorFeedback(recommendation.recommendation_id, "revise", "Add second-source corroboration before action package.", 0.62, 410),
        OperatorFeedback(recommendation.recommendation_id, "approve", "Case package was useful after corroboration.", 0.86, 430),
        OperatorFeedback(recommendation.recommendation_id, "reject", "Initial rationale over-weighted single sensor.", 0.55, 390),
        OperatorFeedback(recommendation.recommendation_id, "approve", "Lineage view increased trust.", 0.84, 440),
        OperatorFeedback(recommendation.recommendation_id, "revise", "Prefer watchfloor summary before commander alert.", 0.66, 425),
    ]
    engine = SelfImprovementEngine()
    proposal = engine.propose(feedback, "triage_workflow.v1", baseline_scores=[0.76, 0.79, 0.81, 0.78, 0.80])
    return {
        "mission": mission.mission_id,
        "recommendation": recommendation,
        "approval_required": recommendation.gate is not ApprovalGate.READ_ONLY,
        "upgrade_proposal": proposal,
        "promotion_decision": engine.promotion_decision(proposal) if proposal else None,
    }
