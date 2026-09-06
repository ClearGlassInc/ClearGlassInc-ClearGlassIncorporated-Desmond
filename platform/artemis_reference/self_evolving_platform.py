"""Reference implementation skeleton for ClearGlassInc Artemis self-evolving AI platform.

This module is intentionally dependency-light so the architecture can be tested in
CI while mirroring production patterns used with Foundry ontology objects, AIP
agents/evals, Apollo rollouts, and Gotham case workflows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
import json
import math
from statistics import fmean
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4


class Classification(StrEnum):
    UNCLASSIFIED = "UNCLASSIFIED"
    CONTROLLED = "CONTROLLED"
    SECRET = "SECRET"
    TOP_SECRET = "TOP_SECRET"


class Decision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REDACT = "allow_with_redaction"
    APPROVAL = "require_approval"


class WorkflowStage(StrEnum):
    TRIAGE = "triage"
    ENRICH = "enrich"
    CORRELATE = "correlate"
    HYPOTHESIZE = "hypothesize"
    BRIEF = "brief"
    RECOMMEND = "recommend"
    POLICY_CHECK = "policy_check"
    APPROVAL = "approval"
    EXECUTE = "execute"
    OUTCOME = "outcome"
    CLOSED = "closed"


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str
    clearance: Classification
    coalitions: frozenset[str]
    compartments: frozenset[str]
    mission_scope: frozenset[str]


@dataclass(frozen=True)
class MissionContext:
    mission_id: str
    classification: Classification
    required_compartments: frozenset[str]
    coalitions: frozenset[str]
    latency_budget_ms: int


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reason: str
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    redactions: tuple[str, ...] = ()


@dataclass(frozen=True)
class OntologyEnvelope:
    confidence: float
    source_system: str
    pipeline_version: str
    prompt_version: str | None
    model_route: str | None
    valid_time_start: datetime
    classification: Classification
    compartments: frozenset[str]
    coalitions: frozenset[str]
    mission_ids: frozenset[str]


@dataclass(frozen=True)
class SignalObserved:
    signal_id: str
    source_system: str
    event_ts: datetime
    payload_hash: str
    envelope: OntologyEnvelope


@dataclass(frozen=True)
class EvalMetrics:
    precision: float
    recall: float
    hallucination_rate: float
    latency_p95_ms: float
    policy_violations: int
    operator_trust: float


@dataclass(frozen=True)
class EvalGates:
    precision_min: float = 0.90
    recall_min: float = 0.82
    hallucination_rate_max: float = 0.02
    latency_p95_ms_max: float = 2500
    policy_violations_max: int = 0
    operator_trust_min: float = 0.78


@dataclass
class UpgradeProposal:
    proposal_id: str
    target: str
    current_version: str
    candidate_version: str
    evidence_metrics: EvalMetrics
    risk_notes: tuple[str, ...]
    status: str = "draft"


CLASSIFICATION_ORDER = {
    Classification.UNCLASSIFIED: 0,
    Classification.CONTROLLED: 1,
    Classification.SECRET: 2,
    Classification.TOP_SECRET: 3,
}

ALLOWED_TRANSITIONS: Mapping[WorkflowStage, frozenset[WorkflowStage]] = {
    WorkflowStage.TRIAGE: frozenset({WorkflowStage.ENRICH}),
    WorkflowStage.ENRICH: frozenset({WorkflowStage.CORRELATE}),
    WorkflowStage.CORRELATE: frozenset({WorkflowStage.HYPOTHESIZE}),
    WorkflowStage.HYPOTHESIZE: frozenset({WorkflowStage.BRIEF}),
    WorkflowStage.BRIEF: frozenset({WorkflowStage.RECOMMEND}),
    WorkflowStage.RECOMMEND: frozenset({WorkflowStage.POLICY_CHECK}),
    WorkflowStage.POLICY_CHECK: frozenset({WorkflowStage.APPROVAL, WorkflowStage.EXECUTE}),
    WorkflowStage.APPROVAL: frozenset({WorkflowStage.EXECUTE, WorkflowStage.CLOSED}),
    WorkflowStage.EXECUTE: frozenset({WorkflowStage.OUTCOME}),
    WorkflowStage.OUTCOME: frozenset({WorkflowStage.CLOSED}),
    WorkflowStage.CLOSED: frozenset(),
}


def hash_payload(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(canonical).hexdigest()


def dominates(user: Classification, required: Classification) -> bool:
    return CLASSIFICATION_ORDER[user] >= CLASSIFICATION_ORDER[required]


def evaluate_need_to_know(
    principal: Principal,
    mission: MissionContext,
    action: str,
    operationally_significant: bool,
) -> PolicyDecision:
    if mission.mission_id not in principal.mission_scope:
        return PolicyDecision(Decision.DENY, "mission out of scope")
    if not dominates(principal.clearance, mission.classification):
        return PolicyDecision(Decision.DENY, "insufficient clearance")
    if not mission.required_compartments.issubset(principal.compartments):
        return PolicyDecision(Decision.DENY, "missing compartment")
    if principal.coalitions.isdisjoint(mission.coalitions):
        return PolicyDecision(Decision.DENY, "coalition boundary")
    if operationally_significant or action in {"publish_product", "notify_commander", "execute_response"}:
        return PolicyDecision(Decision.APPROVAL, "human approval required")
    return PolicyDecision(Decision.ALLOW, "policy satisfied")


def transition(current: WorkflowStage, target: WorkflowStage) -> WorkflowStage:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"invalid workflow transition: {current} -> {target}")
    return target


def make_signal(payload: Mapping[str, Any], mission_id: str, source_system: str) -> SignalObserved:
    if not mission_id.strip():
        raise ValueError("mission_id must not be empty")
    if not source_system.strip():
        raise ValueError("source_system must not be empty")

    confidence = float(payload.get("confidence", 0.5))
    if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be a finite value between 0.0 and 1.0")

    now = datetime.now(UTC)
    envelope = OntologyEnvelope(
        confidence=confidence,
        source_system=source_system,
        pipeline_version="foundry-silver-v1",
        prompt_version=None,
        model_route=None,
        valid_time_start=now,
        classification=Classification(str(payload.get("classification", "CONTROLLED"))),
        compartments=frozenset(payload.get("compartments", ["ARTEMIS-ALPHA"])),
        coalitions=frozenset(payload.get("coalitions", ["US"])),
        mission_ids=frozenset({mission_id}),
    )
    return SignalObserved(
        signal_id=f"sig_{uuid4().hex}",
        source_system=source_system,
        event_ts=now,
        payload_hash=hash_payload(payload),
        envelope=envelope,
    )


def passes_eval_gates(metrics: EvalMetrics, gates: EvalGates = EvalGates()) -> bool:
    return (
        metrics.precision >= gates.precision_min
        and metrics.recall >= gates.recall_min
        and metrics.hallucination_rate <= gates.hallucination_rate_max
        and metrics.latency_p95_ms <= gates.latency_p95_ms_max
        and metrics.policy_violations <= gates.policy_violations_max
        and metrics.operator_trust >= gates.operator_trust_min
    )


def build_eval_metrics(cases: Iterable[Mapping[str, float]]) -> EvalMetrics:
    rows = list(cases)
    if not rows:
        raise ValueError("cannot build eval metrics from an empty case set")
    return EvalMetrics(
        precision=fmean(row["precision"] for row in rows),
        recall=fmean(row["recall"] for row in rows),
        hallucination_rate=fmean(row["hallucination_rate"] for row in rows),
        latency_p95_ms=max(row["latency_ms"] for row in rows),
        policy_violations=int(sum(row["policy_violations"] for row in rows)),
        operator_trust=fmean(row["operator_trust"] for row in rows),
    )


def submit_upgrade_proposal(proposal: UpgradeProposal, reviewer: Callable[[UpgradeProposal], bool]) -> UpgradeProposal:
    if not passes_eval_gates(proposal.evidence_metrics):
        proposal.status = "rejected_by_eval_gate"
        return proposal
    proposal.status = "pending_human_review"
    proposal.status = "approved_for_apollo_canary" if reviewer(proposal) else "rejected_by_review_board"
    return proposal
