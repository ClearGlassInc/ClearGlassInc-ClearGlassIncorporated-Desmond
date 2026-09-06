#!/usr/bin/env python3
"""ClearGlassInc Artemis self-improvement control-loop simulator.

This module models the safe, human-approved learning loop requested for the
System 2040 architecture. It does not autonomously alter production behavior;
it converts feedback signals into signed change proposals that must pass evals,
policy checks, canary thresholds, and approval gates before activation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import statistics
from typing import Any, Iterable


class SignalType(str, Enum):
    OPERATOR_CORRECTION = "operator_correction"
    QUERY_LOG = "query_log"
    ALERT_OUTCOME = "alert_outcome"
    MISSION_RESULT = "mission_result"
    LATENCY_SAMPLE = "latency_sample"
    ENTITY_MERGE_CORRECTION = "entity_merge_correction"
    TRUST_RATING = "trust_rating"


class ProposalType(str, Enum):
    PROMPT_PATCH = "prompt_patch"
    WORKFLOW_PATCH = "workflow_patch"
    ROUTING_PATCH = "routing_patch"
    HEURISTIC_PATCH = "heuristic_patch"
    ONTOLOGY_MERGE_REVIEW = "ontology_merge_review"


class ApprovalState(str, Enum):
    DRAFT = "draft"
    EVAL_FAILED = "eval_failed"
    NEEDS_HUMAN_APPROVAL = "needs_human_approval"
    APPROVED_FOR_CANARY = "approved_for_canary"
    REJECTED = "rejected"
    BLOCKED_POLICY_BOUNDARY = "blocked_policy_boundary"
    CANARY_ACTIVE = "canary_active"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class FeedbackSignal:
    signal_id: str
    signal_type: SignalType
    mission_id: str
    ontology_object_id: str
    actor: str
    classification: str
    compartment: str
    payload: dict[str, Any]
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def lineage_hash(self) -> str:
        canonical = json.dumps(
            {
                "signal_id": self.signal_id,
                "signal_type": self.signal_type.value,
                "mission_id": self.mission_id,
                "object": self.ontology_object_id,
                "payload": self.payload,
                "observed_at": self.observed_at.isoformat(),
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvalResult:
    precision: float
    recall: float
    p95_latency_ms: float
    operator_trust: float
    policy_violations: int
    sample_size: int

    def passes(self) -> bool:
        return (
            self.precision >= 0.92
            and self.recall >= 0.86
            and self.p95_latency_ms <= 1200
            and self.operator_trust >= 0.80
            and self.policy_violations == 0
            and self.sample_size >= 25
        )


@dataclass(frozen=True)
class ChangeProposal:
    proposal_id: str
    proposal_type: ProposalType
    target_component: str
    current_version: str
    proposed_version: str
    rationale: str
    patch: dict[str, Any]
    evidence_hashes: list[str]
    eval_result: EvalResult
    approval_required: bool = True
    rollout_ring: str = "staging-canary"
    approval_state: ApprovalState = ApprovalState.NEEDS_HUMAN_APPROVAL
    policy_decision: str = "human_approval_required"
    drift_score: float = 0.0
    risk_tier: str = "medium"
    rollback_version: str | None = None

    @property
    def signed_manifest(self) -> dict[str, Any]:
        manifest = asdict(self)
        manifest["eval_result"] = asdict(self.eval_result)
        manifest["signature"] = hashlib.sha256(
            json.dumps(manifest, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        return manifest


@dataclass(frozen=True)
class ApprovalDecision:
    """Human decision bound to one immutable proposal manifest."""

    proposal_id: str
    manifest_digest: str
    reviewer: str
    reviewer_roles: frozenset[str]
    decision: str
    rationale: str
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class AuditRecord:
    """Append-only lifecycle evidence with hash-chain integrity."""

    sequence: int
    event_type: str
    proposal_id: str
    actor: str
    payload_digest: str
    previous_hash: str
    recorded_at: datetime
    record_hash: str


class GovernedProposalLifecycle:
    """Fail-closed approval, canary, promotion, and rollback control plane.

    This reference lifecycle deliberately cannot deploy artifacts. It emits an
    audited state and release intent for an external Apollo adapter to execute.
    The adapter remains a separate trust domain and must revalidate the manifest.
    """

    REQUIRED_REVIEW_ROLES = frozenset({"mission_owner", "model_governance"})

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    @property
    def records(self) -> tuple[AuditRecord, ...]:
        return tuple(self._records)

    @staticmethod
    def manifest_digest(proposal: ChangeProposal) -> str:
        canonical = json.dumps(proposal.signed_manifest, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def approve_for_canary(
        self, proposal: ChangeProposal, decision: ApprovalDecision
    ) -> ChangeProposal:
        if proposal.approval_state != ApprovalState.NEEDS_HUMAN_APPROVAL:
            raise PermissionError("proposal is not eligible for human approval")
        if not proposal.eval_result.passes():
            raise PermissionError("proposal eval thresholds have not passed")
        if proposal.policy_decision.startswith("blocked_"):
            raise PermissionError("proposal is blocked by policy")
        if decision.proposal_id != proposal.proposal_id:
            raise PermissionError("approval is bound to a different proposal")
        if decision.manifest_digest != self.manifest_digest(proposal):
            raise PermissionError("proposal changed after approval review")
        if decision.decision != "approve":
            raise PermissionError("an explicit approval decision is required")
        if not self.REQUIRED_REVIEW_ROLES.issubset(decision.reviewer_roles):
            raise PermissionError("reviewer lacks required approval roles")
        if not decision.rationale.strip():
            raise ValueError("approval rationale is required")

        approved = replace(
            proposal,
            approval_state=ApprovalState.APPROVED_FOR_CANARY,
            policy_decision="approved_for_canary",
        )
        self._append("proposal.approved", approved, decision.reviewer)
        return approved

    def start_canary(self, proposal: ChangeProposal, actor: str) -> ChangeProposal:
        if proposal.approval_state != ApprovalState.APPROVED_FOR_CANARY:
            raise PermissionError("canary requires a valid human approval")
        active = replace(proposal, approval_state=ApprovalState.CANARY_ACTIVE)
        self._append("canary.started", active, actor)
        return active

    def complete_canary(
        self, proposal: ChangeProposal, canary_result: EvalResult, actor: str
    ) -> ChangeProposal:
        if proposal.approval_state != ApprovalState.CANARY_ACTIVE:
            raise PermissionError("proposal has no active canary")
        if canary_result.policy_violations or not canary_result.passes():
            rolled_back = replace(
                proposal,
                approval_state=ApprovalState.ROLLED_BACK,
                policy_decision="automatic_rollback_canary_gate",
            )
            self._append("canary.rolled_back", rolled_back, actor)
            return rolled_back
        promoted = replace(
            proposal,
            approval_state=ApprovalState.PROMOTED,
            policy_decision="canary_passed_release_intent",
        )
        self._append("proposal.promotion_intent", promoted, actor)
        return promoted

    def verify_audit_chain(self) -> bool:
        previous_hash = "GENESIS"
        for expected_sequence, record in enumerate(self._records, start=1):
            if record.sequence != expected_sequence or record.previous_hash != previous_hash:
                return False
            material = self._audit_material(
                record.sequence,
                record.event_type,
                record.proposal_id,
                record.actor,
                record.payload_digest,
                record.previous_hash,
                record.recorded_at,
            )
            if hashlib.sha256(material.encode("utf-8")).hexdigest() != record.record_hash:
                return False
            previous_hash = record.record_hash
        return True

    def _append(self, event_type: str, proposal: ChangeProposal, actor: str) -> None:
        if not actor.strip():
            raise ValueError("audit actor is required")
        sequence = len(self._records) + 1
        previous_hash = self._records[-1].record_hash if self._records else "GENESIS"
        recorded_at = datetime.now(timezone.utc)
        payload_digest = self.manifest_digest(proposal)
        material = self._audit_material(
            sequence,
            event_type,
            proposal.proposal_id,
            actor,
            payload_digest,
            previous_hash,
            recorded_at,
        )
        self._records.append(
            AuditRecord(
                sequence=sequence,
                event_type=event_type,
                proposal_id=proposal.proposal_id,
                actor=actor,
                payload_digest=payload_digest,
                previous_hash=previous_hash,
                recorded_at=recorded_at,
                record_hash=hashlib.sha256(material.encode("utf-8")).hexdigest(),
            )
        )

    @staticmethod
    def _audit_material(
        sequence: int,
        event_type: str,
        proposal_id: str,
        actor: str,
        payload_digest: str,
        previous_hash: str,
        recorded_at: datetime,
    ) -> str:
        return json.dumps(
            {
                "sequence": sequence,
                "event_type": event_type,
                "proposal_id": proposal_id,
                "actor": actor,
                "payload_digest": payload_digest,
                "previous_hash": previous_hash,
                "recorded_at": recorded_at.isoformat(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )


class ArtemisImprovementEngine:
    """Transforms operator and mission telemetry into governed proposals."""

    def __init__(self, component_versions: dict[str, str]) -> None:
        self.component_versions = component_versions

    def synthesize_proposals(self, signals: Iterable[FeedbackSignal]) -> list[ChangeProposal]:
        grouped: dict[str, list[FeedbackSignal]] = {}
        for signal in signals:
            grouped.setdefault(signal.mission_id, []).append(signal)

        proposals: list[ChangeProposal] = []
        for mission_id, mission_signals in grouped.items():
            sanitized_signals = [self._sanitize_signal(signal) for signal in mission_signals]
            corrections = [
                s for s in sanitized_signals if s.signal_type == SignalType.OPERATOR_CORRECTION
            ]
            outcomes = [s for s in sanitized_signals if s.signal_type == SignalType.ALERT_OUTCOME]
            latency = [
                float(s.payload.get("latency_ms", 0))
                for s in sanitized_signals
                if s.signal_type == SignalType.LATENCY_SAMPLE
            ]

            merge_corrections = [
                s for s in sanitized_signals if s.signal_type == SignalType.ENTITY_MERGE_CORRECTION
            ]

            if len(corrections) >= 3:
                eval_result = self._offline_eval(corrections, outcomes, latency)
                drift_score = self._drift_score(corrections)
                patch = self._build_prompt_patch(corrections, drift_score)
                approval_state, policy_decision = self._proposal_gate(eval_result, drift_score)
                proposals.append(
                    ChangeProposal(
                        proposal_id=self._proposal_id(mission_id, "triage-copilot", patch),
                        proposal_type=ProposalType.PROMPT_PATCH,
                        target_component="aip.agent.triage_copilot",
                        current_version=self.component_versions.get(
                            "aip.agent.triage_copilot", "0.0.0"
                        ),
                        proposed_version=self._next_patch_version(
                            self.component_versions.get("aip.agent.triage_copilot", "0.0.0")
                        ),
                        rationale="Repeated operator corrections indicate the triage prompt needs stricter evidence thresholds and uncertainty language.",
                        patch=patch,
                        evidence_hashes=[s.lineage_hash for s in sanitized_signals],
                        eval_result=eval_result,
                        approval_state=approval_state,
                        policy_decision=policy_decision,
                        drift_score=drift_score,
                        risk_tier=self._risk_tier(drift_score, eval_result),
                        rollback_version=self.component_versions.get(
                            "aip.agent.triage_copilot", "0.0.0"
                        ),
                    )
                )

            proposals.extend(self._synthesize_merge_review(mission_id, merge_corrections))
        return proposals


    @staticmethod
    def _sanitize_signal(signal: FeedbackSignal) -> FeedbackSignal:
        """Return a signal with recursively redacted user-provided display fields.

        The simulator intentionally keeps sanitization deterministic and stdlib-only so
        examples can run in constrained CI while still modelling the production rule:
        user-facing strings are escaped before being copied into proposal manifests.
        """
        def clean(value: Any) -> Any:
            if isinstance(value, str):
                return (
                    value.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#x27;")
                )
            if isinstance(value, dict):
                return {str(k): clean(v) for k, v in value.items()}
            if isinstance(value, list):
                return [clean(v) for v in value]
            return value

        return FeedbackSignal(
            signal.signal_id,
            signal.signal_type,
            signal.mission_id,
            signal.ontology_object_id,
            signal.actor,
            signal.classification,
            signal.compartment,
            clean(signal.payload),
            signal.observed_at,
        )

    def _synthesize_merge_review(
        self, mission_id: str, merge_corrections: list[FeedbackSignal]
    ) -> list[ChangeProposal]:
        if len(merge_corrections) < 2:
            return []
        compartments = {signal.compartment for signal in merge_corrections}
        if len(compartments) != 1:
            eval_result = EvalResult(0.0, 0.0, 0.0, 0.0, 1, len(merge_corrections))
            return [
                ChangeProposal(
                    proposal_id=self._proposal_id(
                        mission_id, "entity-merge-review", {"compartments": sorted(compartments)}
                    ),
                    proposal_type=ProposalType.ONTOLOGY_MERGE_REVIEW,
                    target_component="ontology.entity_resolution",
                    current_version=self.component_versions.get(
                        "ontology.entity_resolution", "0.0.0"
                    ),
                    proposed_version=self.component_versions.get(
                        "ontology.entity_resolution", "0.0.0"
                    ),
                    rationale="Entity merge proposal blocked because corrections span compartments and require manual compartment authority review.",
                    patch={"blocked_merge_compartments": sorted(compartments)},
                    evidence_hashes=[s.lineage_hash for s in merge_corrections],
                    eval_result=eval_result,
                    approval_state=ApprovalState.BLOCKED_POLICY_BOUNDARY,
                    policy_decision="blocked_cross_compartment_merge",
                    risk_tier="critical",
                    rollback_version=self.component_versions.get(
                        "ontology.entity_resolution", "0.0.0"
                    ),
                )
            ]

        eval_result = EvalResult(0.97, 0.91, 300.0, 0.88, 0, len(merge_corrections))
        current_version = self.component_versions.get("ontology.entity_resolution", "0.0.0")
        patch = {
            "candidate_pairs": [s.payload.get("candidate_pair", []) for s in merge_corrections],
            "minimum_independent_corrections": 2,
            "required_review": "entity_steward_and_mission_owner",
            "merge_execution": "draft_only_until_approved",
        }
        return [
            ChangeProposal(
                proposal_id=self._proposal_id(mission_id, "entity-merge-review", patch),
                proposal_type=ProposalType.ONTOLOGY_MERGE_REVIEW,
                target_component="ontology.entity_resolution",
                current_version=current_version,
                proposed_version=self._next_patch_version(current_version),
                rationale="Repeated operator corrections indicate possible duplicate ontology entities; Artemis drafts a merge review but never merges automatically.",
                patch=patch,
                evidence_hashes=[s.lineage_hash for s in merge_corrections],
                eval_result=eval_result,
                approval_state=ApprovalState.NEEDS_HUMAN_APPROVAL,
                policy_decision="human_approval_required_entity_merge",
                drift_score=self._drift_score(merge_corrections),
                risk_tier="high",
                rollback_version=current_version,
            )
        ]

    @staticmethod
    def _offline_eval(
        corrections: list[FeedbackSignal], outcomes: list[FeedbackSignal], latency: list[float]
    ) -> EvalResult:
        true_positive = sum(
            1 for s in outcomes if s.payload.get("final_disposition") == "validated"
        )
        false_positive = sum(
            1 for s in corrections if s.payload.get("correction") == "false_positive"
        )
        missed = sum(1 for s in corrections if s.payload.get("correction") == "missed_context")
        precision = true_positive / max(true_positive + false_positive, 1)
        recall = true_positive / max(true_positive + missed, 1)
        p95_latency = (
            statistics.quantiles(latency or [250.0], n=20)[-1]
            if len(latency) >= 2
            else (latency[0] if latency else 250.0)
        )
        trust = 1.0 - min(len(corrections) * 0.025, 0.2)
        return EvalResult(
            precision=round(precision, 4),
            recall=round(recall, 4),
            p95_latency_ms=round(p95_latency, 2),
            operator_trust=round(trust, 4),
            policy_violations=0,
            sample_size=len(corrections) + len(outcomes) + len(latency),
        )

    @staticmethod
    def _drift_score(corrections: list[FeedbackSignal]) -> float:
        """Estimate workflow drift from correction-theme concentration.

        A higher score means operators are repeatedly correcting the same failure
        mode, which is useful evidence for proposing a change but should slow
        rollout until a human reviews root cause and regression coverage.
        """
        if not corrections:
            return 0.0
        themes = [str(s.payload.get("theme", "evidence_threshold")) for s in corrections]
        dominant_theme_count = max(themes.count(theme) for theme in set(themes))
        return round(dominant_theme_count / len(themes), 4)

    @staticmethod
    def _proposal_gate(eval_result: EvalResult, drift_score: float) -> tuple[ApprovalState, str]:
        if eval_result.policy_violations:
            return ApprovalState.EVAL_FAILED, "blocked_policy_violation"
        if not eval_result.passes():
            return ApprovalState.EVAL_FAILED, "blocked_eval_threshold"
        if drift_score >= 0.67:
            return ApprovalState.NEEDS_HUMAN_APPROVAL, "human_review_required_high_drift"
        return ApprovalState.NEEDS_HUMAN_APPROVAL, "human_approval_required"

    @staticmethod
    def _risk_tier(drift_score: float, eval_result: EvalResult) -> str:
        if eval_result.policy_violations or drift_score >= 0.9:
            return "critical"
        if drift_score >= 0.67 or eval_result.precision < 0.94:
            return "high"
        return "medium"

    @staticmethod
    def _build_prompt_patch(
        corrections: list[FeedbackSignal], drift_score: float
    ) -> dict[str, Any]:
        themes = sorted({str(s.payload.get("theme", "evidence_threshold")) for s in corrections})
        return {
            "guardrail_additions": [
                "Cite at least two independent ontology-linked evidence artifacts before recommending escalation.",
                "Use explicit uncertainty bands when confidence is below 0.78.",
                "Never convert a recommendation into an operational action without a recorded human approval token.",
            ],
            "observed_correction_themes": themes,
            "requires_eval_suite": "mission_triage_regression_v3",
            "drift_score": drift_score,
            "rollout_controls": {
                "canary_percentage": 5,
                "rollback_on_policy_violation": True,
                "rollback_on_p95_latency_ms": 1200,
            },
        }

    @staticmethod
    def _proposal_id(mission_id: str, component: str, patch: dict[str, Any]) -> str:
        digest = hashlib.sha256(json.dumps(patch, sort_keys=True).encode("utf-8")).hexdigest()[:12]
        return f"prop-{mission_id}-{component}-{digest}"

    @staticmethod
    def _next_patch_version(version: str) -> str:
        parts = version.split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise ValueError(f"component version must use MAJOR.MINOR.PATCH, got {version!r}")
        major, minor, patch = (int(part) for part in parts)
        return f"{major}.{minor}.{patch + 1}"


def demo() -> None:
    signals = [
        FeedbackSignal(
            "s1",
            SignalType.OPERATOR_CORRECTION,
            "m-2040",
            "case-7",
            "analyst.a",
            "SECRET",
            "ARTEMIS",
            {"correction": "missed_context", "theme": "temporal_linkage"},
        ),
        FeedbackSignal(
            "s2",
            SignalType.OPERATOR_CORRECTION,
            "m-2040",
            "case-7",
            "analyst.b",
            "SECRET",
            "ARTEMIS",
            {"correction": "false_positive", "theme": "evidence_threshold"},
        ),
        FeedbackSignal(
            "s3",
            SignalType.OPERATOR_CORRECTION,
            "m-2040",
            "case-7",
            "analyst.c",
            "SECRET",
            "ARTEMIS",
            {"correction": "missed_context", "theme": "coalition_caveat"},
        ),
        FeedbackSignal(
            "s4",
            SignalType.ALERT_OUTCOME,
            "m-2040",
            "case-7",
            "commander.x",
            "SECRET",
            "ARTEMIS",
            {"final_disposition": "validated"},
        ),
        FeedbackSignal(
            "s5",
            SignalType.LATENCY_SAMPLE,
            "m-2040",
            "case-7",
            "system",
            "SECRET",
            "ARTEMIS",
            {"latency_ms": 412},
        ),
    ]
    engine = ArtemisImprovementEngine({"aip.agent.triage_copilot": "2.4.9"})
    print(
        json.dumps(
            [p.signed_manifest for p in engine.synthesize_proposals(signals)], indent=2, default=str
        )
    )


if __name__ == "__main__":
    demo()
