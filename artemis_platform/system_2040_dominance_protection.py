"""Governed System 2040 protection and growth automation for ClearGlassInc Artemis.

This module intentionally rejects the unsafe "skeleton key" pattern.  Every
resource read is mediated by an entitlement check, every operationally
significant mitigation or revenue action becomes a human-reviewable action
package, and every decision emits an audit event that can be promoted or rolled
back through Apollo-style release controls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Literal
from uuid import uuid4

from artemis_platform.self_evolving_platform import (
    EnvironmentalCyberRiskSignal,
    environmental_cyber_risk_assessment,
    environmental_risk_score,
)

ResourceKind = Literal["dataset", "api", "research", "infrastructure", "crm", "analytics"]
ActionDomain = Literal["cyber", "environmental", "ai", "ionospheric", "revenue"]
ActionStatus = Literal["draft", "pending_human_approval", "approved", "rejected"]


class ActionGate(str, Enum):
    """Approval levels for System 2040 automation."""

    READ_ONLY = "read_only"
    CASE_WRITEBACK = "case_writeback"
    EXTERNAL_COMMUNICATION = "external_communication"
    OPERATIONAL_EFFECT = "operational_effect"
    REVENUE_PUBLICATION = "revenue_publication"


@dataclass(frozen=True)
class MissionPrincipal:
    actor_id: str
    mission_id: str
    purpose: str
    clearance: str
    compartments: frozenset[str]
    approved_resources: frozenset[str]


@dataclass(frozen=True)
class ResourceRequest:
    resource_kind: ResourceKind
    resource_name: str
    purpose: str
    classification: str = "UNCLASS"
    compartments: frozenset[str] = frozenset()
    justification: str = "mission-authorized monitoring"


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str
    lease_seconds: int = 0
    obligations: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    event_type: str
    actor_id: str
    mission_id: str
    details: dict[str, Any]
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ThreatFinding:
    finding_id: str
    domain: ActionDomain
    severity: Literal["GREEN", "YELLOW", "RED"]
    score: float
    summary: str
    evidence_refs: tuple[str, ...]
    recommended_actions: tuple[str, ...]


@dataclass(frozen=True)
class ActionPackage:
    package_id: str
    domain: ActionDomain
    gate: ActionGate
    status: ActionStatus
    title: str
    rationale: str
    recommended_steps: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    rollback_plan: str
    requires_human_approval: bool = True


class GovernedAccessBroker:
    """Least-privilege replacement for universal access.

    The broker never returns secrets.  It returns an access lease only when the
    mission principal is entitled to the named resource and compartment labels
    are satisfied.
    """

    def __init__(self) -> None:
        self.audit_log: list[AuditEvent] = []

    def request(self, principal: MissionPrincipal, request: ResourceRequest) -> AccessDecision:
        if request.resource_name not in principal.approved_resources:
            return self._deny(principal, request, "resource is not mission-entitled")
        if not request.compartments.issubset(principal.compartments):
            return self._deny(principal, request, "requested compartment is not held by principal")
        if request.purpose != principal.purpose:
            return self._deny(principal, request, "purpose binding mismatch")

        decision = AccessDecision(
            allowed=True,
            reason="granted by mission entitlement and purpose binding",
            lease_seconds=900,
            obligations=("audit_reads", "no_secret_materialization", "human_gate_external_effects"),
        )
        self._audit(principal, request, decision)
        return decision

    def _deny(
        self,
        principal: MissionPrincipal,
        request: ResourceRequest,
        reason: str,
    ) -> AccessDecision:
        decision = AccessDecision(allowed=False, reason=reason)
        self._audit(principal, request, decision)
        return decision

    def _audit(
        self,
        principal: MissionPrincipal,
        request: ResourceRequest,
        decision: AccessDecision,
    ) -> None:
        self.audit_log.append(
            AuditEvent(
                event_id=str(uuid4()),
                event_type="resource_access_decision",
                actor_id=principal.actor_id,
                mission_id=principal.mission_id,
                details={
                    "resource_kind": request.resource_kind,
                    "resource_name": request.resource_name,
                    "allowed": decision.allowed,
                    "reason": decision.reason,
                    "obligations": list(decision.obligations),
                },
            )
        )


class System2040ProtectionEngine:
    """Deterministic protection engine for cyber, AI, and environmental findings."""

    def __init__(self, access_broker: GovernedAccessBroker) -> None:
        self.access_broker = access_broker

    def assess_ionospheric_signal(
        self,
        principal: MissionPrincipal,
        signal: EnvironmentalCyberRiskSignal,
    ) -> ThreatFinding:
        decision = self.access_broker.request(
            principal,
            ResourceRequest(
                resource_kind="dataset",
                resource_name="environmental.telemetry.phase1",
                purpose=principal.purpose,
                compartments=frozenset({"ENVIRONMENTAL_CYBER_RISK"}),
                justification="score Phase 1 ionospheric threat vector",
            ),
        )
        if not decision.allowed:
            raise PermissionError(decision.reason)
        if not all(
            isfinite(value)
            for value in (
                signal.log_nm_f2,
                signal.kp_index,
                signal.scintillation_s4,
                signal.hf_absorption_db,
                signal.gnss_error_m,
            )
        ):
            raise ValueError("ionospheric signal features must be finite")

        assessment = environmental_cyber_risk_assessment(signal)
        score = environmental_risk_score(signal)
        return ThreatFinding(
            finding_id=str(uuid4()),
            domain="ionospheric",
            severity=assessment.band,
            score=score,
            summary=assessment.rationale,
            evidence_refs=(f"signal:{signal.signal_id}", f"site:{signal.site_id}"),
            recommended_actions=assessment.mitigation_playbook,
        )

    def build_action_package(self, finding: ThreatFinding) -> ActionPackage:
        gate = ActionGate.READ_ONLY
        status: ActionStatus = "draft"
        if finding.severity == "YELLOW":
            gate = ActionGate.CASE_WRITEBACK
            status = "pending_human_approval"
        if finding.severity == "RED":
            gate = ActionGate.OPERATIONAL_EFFECT
            status = "pending_human_approval"

        return ActionPackage(
            package_id=str(uuid4()),
            domain=finding.domain,
            gate=gate,
            status=status,
            title=f"{finding.severity} {finding.domain} protection package",
            rationale=finding.summary,
            recommended_steps=finding.recommended_actions,
            evidence_refs=finding.evidence_refs,
            rollback_plan="revert to previous watch posture and restore prior workflow pointer via Apollo",
            requires_human_approval=gate is not ActionGate.READ_ONLY,
        )


class GovernedDominancePushEngine:
    """Revenue and market automation that only drafts human-reviewable packages."""

    def draft_growth_package(
        self,
        principal: MissionPrincipal,
        finding: ThreatFinding,
    ) -> ActionPackage:
        return ActionPackage(
            package_id=str(uuid4()),
            domain="revenue",
            gate=ActionGate.REVENUE_PUBLICATION,
            status="pending_human_approval",
            title="Draft Environmental Cyber-Risk client education package",
            rationale=(
                "Generate a reviewed client education asset from authorized telemetry; "
                "do not publish, message prospects, or update CRM until approved."
            ),
            recommended_steps=(
                "draft cited Burlington/GTA client brief",
                "attach risk finding and uncertainty statement",
                "route LinkedIn, HubSpot, and whitepaper claims to human review",
            ),
            evidence_refs=finding.evidence_refs + (f"mission:{principal.mission_id}",),
            rollback_plan="withdraw draft, expire claims, and retain audit trail",
            requires_human_approval=True,
        )


class System2040AutomationLoop:
    """Single-cycle orchestration for sensors → findings → dashboard → gated actions."""

    def __init__(
        self,
        protection_engine: System2040ProtectionEngine,
        growth_engine: GovernedDominancePushEngine,
    ) -> None:
        self.protection_engine = protection_engine
        self.growth_engine = growth_engine

    def run_once(
        self,
        principal: MissionPrincipal,
        signal: EnvironmentalCyberRiskSignal,
    ) -> dict[str, Any]:
        finding = self.protection_engine.assess_ionospheric_signal(principal, signal)
        protection_package = self.protection_engine.build_action_package(finding)
        growth_package = self.growth_engine.draft_growth_package(principal, finding)
        return {
            "dashboard": {
                "mission_id": principal.mission_id,
                "severity": finding.severity,
                "score": finding.score,
                "summary": finding.summary,
                "evidence_refs": list(finding.evidence_refs),
            },
            "findings": [finding],
            "action_packages": [protection_package, growth_package],
        }
