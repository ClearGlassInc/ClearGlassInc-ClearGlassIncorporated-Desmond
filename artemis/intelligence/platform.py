"""Reference implementation skeleton for ClearGlassInc Artemis.

The module is intentionally dependency-light so it can act as executable
architecture documentation for ontology-driven intelligence workflows,
policy checks, feedback capture, and human-approved self-improvement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from hmac import compare_digest
import json
from statistics import fmean
from typing import Any, Callable, Protocol
from uuid import uuid4


class WorkflowState(StrEnum):
    """Human-gated lifecycle for operationally significant AI work."""

    RECEIVED = "received"
    TRIAGED = "triaged"
    ENRICHED = "enriched"
    RECOMMENDED = "recommended"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class AccessContext:
    """Signed request context propagated through gateway, tools, and agents."""

    operator_id: str
    roles: frozenset[str]
    mission_ids: frozenset[str]
    compartments: frozenset[str]
    coalition: str
    purpose: str


@dataclass(frozen=True)
class OntologyEntity:
    """Foundry/Gotham-style typed object with lineage, markings, and confidence."""

    entity_id: str
    kind: str
    canonical_name: str
    confidence: float
    markings: frozenset[str]
    lineage: tuple[str, ...]
    valid_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class Alert:
    alert_id: str
    mission_id: str
    severity: str
    hypothesis: str
    entity_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    markings: frozenset[str]
    workflow_state: WorkflowState = WorkflowState.RECEIVED


@dataclass(frozen=True)
class AgentAction:
    """Action proposal produced by an agent; execution may require approval."""

    action_id: str
    action_type: str
    mission_id: str
    risk_tier: str
    summary: str
    required_approval: bool
    evidence_refs: tuple[str, ...]
    parameters: dict[str, Any]


@dataclass(frozen=True)
class FeedbackEvent:
    feedback_id: str
    operator_id: str
    artifact_id: str
    workflow_version: str
    rating: int
    correction: str
    outcome: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    redactions: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuditRecord:
    """Tamper-evident audit event for operator, policy, and upgrade decisions."""

    record_id: str
    actor: str
    action: str
    resource: str
    decision: str
    created_at: datetime
    previous_hash: str
    payload_hash: str
    chain_hash: str


@dataclass(frozen=True)
class ModelRoute:
    """Selected inference path with policy-readable rationale."""

    task_type: str
    model_id: str
    execution_tier: str
    reason: str


@dataclass(frozen=True)
class ApprovalToken:
    """Short-lived human approval token bound to a specific action package."""

    token_id: str
    operator_id: str
    action_id: str
    package_hash: str
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class ReleaseCandidate:
    """Apollo-promotable artifact bundle for a self-improvement proposal."""

    candidate_id: str
    proposal_id: str
    artifact_type: str
    baseline_version: str
    candidate_version: str
    rollback_version: str
    eval_metrics: dict[str, float]
    human_approved: bool


@dataclass(frozen=True)
class PromotionDecision:
    """Final promotion decision with explicit rollback target and denial reasons."""

    safe_to_review: bool
    canary_allowed: bool
    rollback_version: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ImprovementProposal:
    proposal_id: str
    target: str
    current_version: str
    candidate_version: str
    diff_summary: str
    eval_metrics: dict[str, float]
    requires_human_approval: bool = True


@dataclass(frozen=True)
class EvalGateResult:
    """Auditable result of the pre-promotion evaluation gate.

    A candidate upgrade may only carry a ``candidate_version`` when it passed
    every quality/latency/policy check and a human approved it; otherwise the
    gate records why it was blocked and the version to roll back to.
    """

    passed: bool
    reasons: tuple[str, ...]
    rollback_version: str
    candidate_version: str | None = None


class ImmutableAuditLog:
    """Append-only hash chain suitable for WORM export or ledger anchoring."""

    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def append(
        self, *, actor: str, action: str, resource: str, decision: str, payload: dict[str, Any]
    ) -> AuditRecord:
        previous_hash = self.records[-1].chain_hash if self.records else "GENESIS"
        payload_hash = sha256(repr(sorted(payload.items())).encode("utf-8")).hexdigest()
        chain_hash = sha256(
            f"{previous_hash}:{actor}:{action}:{resource}:{decision}:{payload_hash}".encode("utf-8")
        ).hexdigest()
        record = AuditRecord(
            record_id=str(uuid4()),
            actor=actor,
            action=action,
            resource=resource,
            decision=decision,
            created_at=datetime.now(UTC),
            previous_hash=previous_hash,
            payload_hash=payload_hash,
            chain_hash=chain_hash,
        )
        self.records.append(record)
        return record

    def verify(self) -> bool:
        previous_hash = "GENESIS"
        for record in self.records:
            expected = sha256(
                f"{previous_hash}:{record.actor}:{record.action}:{record.resource}:{record.decision}:{record.payload_hash}".encode(
                    "utf-8"
                )
            ).hexdigest()
            if not compare_digest(expected, record.chain_hash):
                return False
            previous_hash = record.chain_hash
        return True


class WorkflowStateMachine:
    """Deterministic mission workflow guardrail for agent and operator actions."""

    ALLOWED_TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
        WorkflowState.RECEIVED: frozenset({WorkflowState.TRIAGED}),
        WorkflowState.TRIAGED: frozenset({WorkflowState.ENRICHED, WorkflowState.REJECTED}),
        WorkflowState.ENRICHED: frozenset({WorkflowState.RECOMMENDED, WorkflowState.REJECTED}),
        WorkflowState.RECOMMENDED: frozenset(
            {WorkflowState.AWAITING_APPROVAL, WorkflowState.REJECTED}
        ),
        WorkflowState.AWAITING_APPROVAL: frozenset(
            {WorkflowState.APPROVED, WorkflowState.REJECTED}
        ),
        WorkflowState.APPROVED: frozenset({WorkflowState.DEPLOYED, WorkflowState.ROLLED_BACK}),
        WorkflowState.DEPLOYED: frozenset({WorkflowState.ROLLED_BACK}),
        WorkflowState.REJECTED: frozenset(),
        WorkflowState.ROLLED_BACK: frozenset(),
    }

    def __init__(self, audit_log: ImmutableAuditLog) -> None:
        self.audit_log = audit_log

    def transition(
        self,
        workflow_id: str,
        current: WorkflowState,
        target: WorkflowState,
        *,
        actor: str,
        reason: str,
    ) -> WorkflowState:
        """Move a workflow only through approved states and audit denied jumps."""

        allowed = target in self.ALLOWED_TRANSITIONS[current]
        self.audit_log.append(
            actor=actor,
            action="workflow.transition",
            resource=workflow_id,
            decision="ALLOW" if allowed else "DENY",
            payload={"from": current.value, "to": target.value, "reason": reason},
        )
        if not allowed:
            raise ValueError(f"invalid workflow transition: {current.value} -> {target.value}")
        return target


class ModelRouter:
    """Deterministic, policy-aware model routing for latency-sensitive missions."""

    def route(
        self,
        *,
        task_type: str,
        classification: str,
        latency_budget_ms: int,
        requires_deep_reasoning: bool,
    ) -> ModelRoute:
        if classification in {"SECRET", "COALITION_RESTRICTED"}:
            return ModelRoute(
                task_type,
                "aip-secure-reasoner",
                "isolated",
                "restricted classification requires hardened AIP path",
            )
        if requires_deep_reasoning or latency_budget_ms >= 1_200:
            return ModelRoute(
                task_type,
                "aip-frontier-reasoner",
                "standard",
                "deep reasoning or relaxed latency budget",
            )
        return ModelRoute(task_type, "aip-fast-mini", "low-latency", "tight latency budget")


class PolicyEngine:
    """Policy-as-code enforcement for need-to-know and coalition boundaries."""

    def authorize_entity(self, context: AccessContext, entity: OntologyEntity) -> PolicyDecision:
        denied_markings = entity.markings.difference(context.compartments)
        if denied_markings:
            return PolicyDecision(False, f"missing compartments: {sorted(denied_markings)}")
        if context.purpose not in {"investigation", "triage", "command_briefing", "evaluation"}:
            return PolicyDecision(False, f"unsupported purpose: {context.purpose}")
        return PolicyDecision(True, "authorized")

    def authorize_action(self, context: AccessContext, action: AgentAction) -> PolicyDecision:
        if action.mission_id not in context.mission_ids:
            return PolicyDecision(False, "operator is not assigned to mission")
        if not action.evidence_refs:
            return PolicyDecision(False, "action requires cited evidence")
        if action.risk_tier in {"high", "critical"} and "commander" not in context.roles:
            return PolicyDecision(False, "high-risk action requires commander role")
        return PolicyDecision(True, "authorized")


class OntologyStore(Protocol):
    def fetch_entities(self, entity_ids: tuple[str, ...]) -> list[OntologyEntity]: ...

    def write_alert(self, alert: Alert) -> None: ...


class InMemoryOntologyStore:
    """Testable ontology adapter; replace with Foundry/Gotham SDK calls in production."""

    def __init__(self) -> None:
        self.entities: dict[str, OntologyEntity] = {}
        self.alerts: dict[str, Alert] = {}

    def fetch_entities(self, entity_ids: tuple[str, ...]) -> list[OntologyEntity]:
        return [self.entities[entity_id] for entity_id in entity_ids if entity_id in self.entities]

    def write_alert(self, alert: Alert) -> None:
        self.alerts[alert.alert_id] = alert


class ArtemisEventBus:
    """Small synchronous event bus standing in for Kafka/Pulsar topics.

    Handler failures are isolated into a dead-letter queue so one fragile
    integration cannot prevent other mission consumers from receiving an event.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
        self.dead_letters: list[dict[str, Any]] = []
        self.telemetry: dict[str, int] = {
            "events.published": 0,
            "events.delivered": 0,
            "events.handler_failed": 0,
        }

    def subscribe(self, topic: str, handler: Callable[[dict[str, Any]], None]) -> None:
        self._subscribers.setdefault(topic, []).append(handler)

    def publish(self, topic: str, event: dict[str, Any]) -> str:
        event.setdefault("event_id", str(uuid4()))
        event.setdefault("emitted_at", datetime.now(UTC).isoformat())
        self.telemetry["events.published"] += 1
        for handler in self._subscribers.get(topic, []):
            try:
                handler(event)
            except Exception as exc:
                self.telemetry["events.handler_failed"] += 1
                self.dead_letters.append(
                    {
                        "topic": topic,
                        "event": dict(event),
                        "handler": getattr(handler, "__name__", handler.__class__.__name__),
                        "error": str(exc),
                    }
                )
            else:
                self.telemetry["events.delivered"] += 1
        return str(event["event_id"])


class TriageAgent:
    """Ontology-grounded triage agent that emits approval-gated recommendations."""

    def __init__(self, ontology: OntologyStore, policy: PolicyEngine) -> None:
        self.ontology = ontology
        self.policy = policy

    def triage(self, context: AccessContext, alert: Alert) -> AgentAction:
        visible_entities = []
        for entity in self.ontology.fetch_entities(alert.entity_ids):
            if self.policy.authorize_entity(context, entity).allowed:
                visible_entities.append(entity)

        confidence = (
            fmean([entity.confidence for entity in visible_entities]) if visible_entities else 0.0
        )
        risk_tier = (
            "high" if alert.severity in {"high", "critical"} and confidence >= 0.75 else "medium"
        )
        return AgentAction(
            action_id=str(uuid4()),
            action_type="open_case_and_request_review",
            mission_id=alert.mission_id,
            risk_tier=risk_tier,
            summary=f"{alert.hypothesis} based on {len(alert.evidence_refs)} cited observations.",
            required_approval=True,
            evidence_refs=alert.evidence_refs,
            parameters={
                "visible_entity_count": len(visible_entities),
                "mean_confidence": confidence,
            },
        )


class SelfImprovementEngine:
    """Converts feedback into eval-backed, human-approved upgrade proposals."""

    def __init__(
        self,
        minimum_precision: float = 0.92,
        maximum_latency_ms: float = 2_000,
        minimum_recall: float = 0.85,
        maximum_policy_denials_delta: float = 0.0,
    ) -> None:
        self.minimum_precision = minimum_precision
        self.maximum_latency_ms = maximum_latency_ms
        self.minimum_recall = minimum_recall
        self.maximum_policy_denials_delta = maximum_policy_denials_delta

    def evaluate_candidate(
        self,
        *,
        current_version: str,
        candidate_version: str,
        eval_metrics: dict[str, float],
        human_approved: bool,
    ) -> EvalGateResult:
        """Return an auditable gate result before Apollo canary or promotion.

        The gate is intentionally strict: Artemis may propose prompt, workflow, or
        routing upgrades, but a candidate cannot pass unless offline evals meet
        quality/latency/policy thresholds and a human has approved the change.
        """

        reasons: list[str] = []
        if eval_metrics.get("precision", 0.0) < self.minimum_precision:
            reasons.append("precision below required threshold")
        if eval_metrics.get("recall", 0.0) < self.minimum_recall:
            reasons.append("recall below required threshold")
        if eval_metrics.get("p95_latency_ms", float("inf")) > self.maximum_latency_ms:
            reasons.append("p95 latency exceeds budget")
        if eval_metrics.get("policy_denials_delta", 0.0) > self.maximum_policy_denials_delta:
            reasons.append("policy denial rate regressed")
        if not human_approved:
            reasons.append("human approval is required")

        return EvalGateResult(
            passed=not reasons,
            reasons=tuple(reasons),
            rollback_version=current_version,
            candidate_version=candidate_version if not reasons else None,
        )

    def proposal_from_feedback(
        self,
        feedback: list[FeedbackEvent],
        target: str,
        current_version: str,
        candidate_prompt: str,
        eval_metrics: dict[str, float],
    ) -> ImprovementProposal | None:
        if not feedback:
            return None
        rejected_or_corrected = [item for item in feedback if item.rating <= 2 or item.correction]
        if not rejected_or_corrected:
            return None
        gate = self.evaluate_candidate(
            current_version=current_version,
            candidate_version="candidate-pre-approval",
            eval_metrics=eval_metrics,
            human_approved=True,
        )
        if not gate.passed:
            return None

        candidate_hash = sha256(candidate_prompt.encode("utf-8")).hexdigest()[:12]
        return ImprovementProposal(
            proposal_id=str(uuid4()),
            target=target,
            current_version=current_version,
            candidate_version=f"{current_version}+{candidate_hash}",
            diff_summary=(
                "Add operator-correction-derived guardrail requiring maintenance, lineage, "
                "and coalition checks before severity escalation."
            ),
            eval_metrics=eval_metrics,
        )


def compile_feedback_to_eval(feedback: FeedbackEvent) -> dict[str, Any]:
    """Freeze operator feedback into an eval case without exposing secrets.

    The eval payload keeps only stable identifiers and operator-provided correction
    text. Production deployments should replace IDs with Foundry snapshot refs and
    apply field-level redaction before storage.
    """

    return {
        "eval_id": f"eval-{feedback.feedback_id}",
        "artifact_id": feedback.artifact_id,
        "workflow_version": feedback.workflow_version,
        "expected_behavior": {
            "correction": feedback.correction,
            "outcome": feedback.outcome,
            "rating": feedback.rating,
        },
        "source_feedback_ids": [feedback.feedback_id],
        "created_at": feedback.created_at.isoformat(),
    }


class PromotionController:
    """Blocks unsafe self-upgrades before Apollo canary deployment."""

    REVIEWER_ROLES = frozenset({"governance", "modelops"})

    def __init__(self, engine: SelfImprovementEngine, audit_log: ImmutableAuditLog) -> None:
        self.engine = engine
        self.audit_log = audit_log

    def review_for_canary(
        self, context: AccessContext, candidate: ReleaseCandidate
    ) -> PromotionDecision:
        gate = self.engine.evaluate_candidate(
            current_version=candidate.baseline_version,
            candidate_version=candidate.candidate_version,
            eval_metrics=candidate.eval_metrics,
            human_approved=candidate.human_approved,
        )
        reasons = list(gate.reasons)
        reviewer_authorized = bool(context.roles.intersection(self.REVIEWER_ROLES))
        if context.purpose != "evaluation":
            reasons.append("canary review requires evaluation purpose")
        if not reviewer_authorized:
            reasons.append("canary review requires governance or modelops role")
        if candidate.rollback_version == candidate.candidate_version:
            reasons.append("rollback version must differ from candidate version")
        if candidate.rollback_version != candidate.baseline_version:
            reasons.append("rollback version must match the last stable baseline")

        canary_allowed = gate.passed and not reasons
        self.audit_log.append(
            actor=context.operator_id,
            action="apollo.canary.review",
            resource=candidate.candidate_id,
            decision="ALLOW" if canary_allowed else "DENY",
            payload={
                "artifact_type": candidate.artifact_type,
                "proposal_id": candidate.proposal_id,
                "candidate_version": candidate.candidate_version,
                "rollback_version": candidate.rollback_version,
                "reasons": tuple(reasons),
            },
        )
        return PromotionDecision(
            safe_to_review=(
                candidate.human_approved
                and context.purpose == "evaluation"
                and reviewer_authorized
            ),
            canary_allowed=canary_allowed,
            rollback_version=candidate.rollback_version,
            reasons=tuple(reasons),
        )


class ApprovalGate:
    """Records human approval decisions before any significant action can execute."""

    def __init__(self, policy: PolicyEngine, audit_log: ImmutableAuditLog) -> None:
        self.policy = policy
        self.audit_log = audit_log
        self._consumed_token_ids: set[str] = set()

    @staticmethod
    def package_hash(action: AgentAction) -> str:
        """Hash the complete action package so approval cannot authorize a mutation."""

        package = {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "mission_id": action.mission_id,
            "risk_tier": action.risk_tier,
            "summary": action.summary,
            "required_approval": action.required_approval,
            "evidence_refs": action.evidence_refs,
            "parameters": action.parameters,
        }
        canonical = json.dumps(package, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return sha256(canonical.encode("utf-8")).hexdigest()

    def approve(
        self, context: AccessContext, action: AgentAction, decision: str, reason: str
    ) -> PolicyDecision:
        if decision not in {"approve", "reject"}:
            raise ValueError("decision must be approve or reject")
        policy_decision = self.policy.authorize_action(context, action)
        final_decision = (
            "REJECT" if decision == "reject" or not policy_decision.allowed else "APPROVE"
        )
        self.audit_log.append(
            actor=context.operator_id,
            action=f"human_approval.{decision}",
            resource=action.action_id,
            decision=final_decision,
            payload={
                "reason": reason,
                "policy_reason": policy_decision.reason,
                "mission_id": action.mission_id,
                "risk_tier": action.risk_tier,
            },
        )
        if final_decision == "REJECT" and policy_decision.allowed:
            return PolicyDecision(False, reason)
        return policy_decision

    def approve_and_issue(
        self,
        context: AccessContext,
        action: AgentAction,
        *,
        decision: str,
        reason: str,
        ttl: timedelta = timedelta(minutes=5),
        now: datetime | None = None,
    ) -> ApprovalToken | None:
        """Issue a short-lived token only after an attributable policy-approved decision."""

        if ttl <= timedelta(0):
            raise ValueError("approval token ttl must be positive")
        decided_at = now or datetime.now(UTC)
        if decided_at.tzinfo is None:
            raise ValueError("approval decision time must be timezone-aware")
        policy_decision = self.approve(context, action, decision, reason)
        if not policy_decision.allowed or decision != "approve":
            return None
        token = ApprovalToken(
            token_id=str(uuid4()),
            operator_id=context.operator_id,
            action_id=action.action_id,
            package_hash=self.package_hash(action),
            issued_at=decided_at,
            expires_at=decided_at + ttl,
        )
        self.audit_log.append(
            actor=context.operator_id,
            action="approval.token.issue",
            resource=action.action_id,
            decision="ALLOW",
            payload={"token_id": token.token_id, "expires_at": token.expires_at.isoformat()},
        )
        return token

    def consume(
        self, token: ApprovalToken, action: AgentAction, *, now: datetime | None = None
    ) -> PolicyDecision:
        """Atomically consume an approval token bound to the immutable action package."""

        consumed_at = now or datetime.now(UTC)
        reasons: list[str] = []
        if consumed_at.tzinfo is None:
            reasons.append("approval consumption time must be timezone-aware")
        elif consumed_at > token.expires_at:
            reasons.append("approval token expired")
        if token.token_id in self._consumed_token_ids:
            reasons.append("approval token already consumed")
        if token.action_id != action.action_id:
            reasons.append("approval token is bound to a different action")
        if not compare_digest(token.package_hash, self.package_hash(action)):
            reasons.append("action package changed after approval")

        allowed = not reasons
        if allowed:
            self._consumed_token_ids.add(token.token_id)
        reason = "approval token consumed" if allowed else "; ".join(reasons)
        self.audit_log.append(
            actor=token.operator_id,
            action="approval.token.consume",
            resource=action.action_id,
            decision="ALLOW" if allowed else "DENY",
            payload={"token_id": token.token_id, "reason": reason},
        )
        return PolicyDecision(allowed, reason)
