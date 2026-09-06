#!/usr/bin/env python3
"""Priority Sequence Alpha control engine for ClearGlassInc Artemis.

This module turns the June 30, 2026 operator packet into deterministic,
auditable Python objects. It intentionally does not send messages, sign vendor
packages, block networks, or mutate calendars; it returns human-approval-ready
execution packets with policy gates and lineage hashes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import ipaddress
import json
from typing import Any


class Classification(StrEnum):
    BLOCKED_CONTAINED = "Security Event — Blocked / Contained"
    REQUIRES_ESCALATION = "Security Incident — Escalation Required"


class ApprovalState(StrEnum):
    DRAFT = "draft"
    READY_FOR_HUMAN_APPROVAL = "ready_for_human_approval"
    BLOCKED = "blocked"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class BaselineConstraint:
    """Grounds Artemis planning in approved 2026 technology baselines."""

    spd_smartglass: str = "2026-proven SPD-SmartGlass control surface assumptions only"
    pdlc: str = "2026-proven PDLC privacy/switching assumptions only"
    ibm_quantum: str = "IBM quantum capabilities treated as bounded research/optimization baseline"
    neuralink_bci: str = "Neuralink BCI treated as human-interface research baseline, not autonomous authority"
    siemens_ai_glass: str = "Siemens AI-GLASS treated as industrial AI/edge-inspection baseline"
    policy: str = "zero-trust, OSINT-only enrichment, human-approved external effects"


@dataclass(frozen=True)
class SecurityEventReport:
    event_id: str
    source_ip: str
    asn: str
    endpoint: str
    packet_count: int
    window_seconds: int
    auth_status: str
    waf_rule: str
    related_failed_attempts_24h: int
    reached_backend: bool
    indicators: dict[str, Any]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def classify(self) -> Classification:
        if self.reached_backend or self.indicators.get("data_exposure") is True:
            return Classification.REQUIRES_ESCALATION
        return Classification.BLOCKED_CONTAINED

    def recommended_hardening(self) -> list[str]:
        network = ipaddress.ip_network(f"{self.source_ip}/24", strict=False)
        return [
            f"Block {network} at Cloudflare WAF and staging host deny lists after human approval.",
            "Require mTLS or strict IP allow-list for staging API access.",
            "Add AEGIS rule: auth-failure burst from low-reputation ASN on staging API.",
            "Reject JWTs with future iat, missing subject, missing audience, or missing issuer claims.",
            "Mirror staging auth failures to AEGIS Threats log and Slack/Teams alert channel.",
        ]

    @property
    def lineage_hash(self) -> str:
        return stable_hash(asdict(self))


@dataclass(frozen=True)
class VendorCriterion:
    name: str
    passed: bool
    evidence: str
    risk: str


@dataclass(frozen=True)
class VendorRiskAssessment:
    vendor: str
    deadline_utc: datetime
    criteria: tuple[VendorCriterion, ...]

    def decision(self) -> ApprovalState:
        if all(c.passed and c.risk.lower() in {"low", "accepted"} for c in self.criteria):
            return ApprovalState.READY_FOR_HUMAN_APPROVAL
        return ApprovalState.ESCALATE

    def signoff_language(self, signatory: str, signed_at_label: str = "[Time] EDT") -> str:
        if self.decision() != ApprovalState.READY_FOR_HUMAN_APPROVAL:
            return "Escalation required: one or more mandatory vendor criteria failed."
        return (
            f"I have personally reviewed the {self.vendor} vendor documentation against "
            "ClearGlass Inc. requirements. All five mandatory criteria (data access scope, "
            "subprocessor exposure, compliance evidence, incident notification, and "
            "termination/data deletion) are satisfied with no critical gaps. I authorize "
            f"execution of the agreement on behalf of ClearGlass Inc. Signed: {signatory} — "
            f"2026-06-30 {signed_at_label}"
        )


@dataclass(frozen=True)
class CalendarConflictResolution:
    primary_event_ids: tuple[str, ...]
    prioritized_event: str
    delegated_event: str
    migration_delay_percent: float

    def approval_state(self) -> ApprovalState:
        if len(self.primary_event_ids) < 2:
            return ApprovalState.BLOCKED
        return ApprovalState.READY_FOR_HUMAN_APPROVAL

    def delegation_note(self) -> str:
        return (
            "Subject: Conflict at 15:30 — Prioritizing Engineering Architecture Sync (Q3 Migration Risk)\n\n"
            "Hi [Budget Review Lead / Team],\n\n"
            "I have a direct conflict at 15:30 and must prioritize the Engineering Architecture Sync. "
            f"The Q3 infrastructure migration is currently {self.migration_delay_percent:.0f}% behind schedule, "
            "and any further slippage directly threatens our Q4 code freeze window and the foundation for "
            "the Quantum-Neural Smart Glass control plane work.\n\n"
            "Please send me the full budget review notes and any decision items requiring my approval. "
            "I will review and respond with decisions today before EOD.\n\n"
            "Thank you,\nDesmond Otieno\nCOO & Founder, ClearGlass Inc."
        )


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def build_priority_alpha_packet() -> dict[str, Any]:
    baselines = BaselineConstraint()
    security = SecurityEventReport(
        event_id="SEC-20260630-0014",
        source_ip="185.234.72.187",
        asn="AS9009 M247 Ltd / Global Layer",
        endpoint="POST /v1/packets/analyze",
        packet_count=4,
        window_seconds=4,
        auth_status="failed_missing_or_malformed_bearer_jwt",
        waf_rule="cf-4721",
        related_failed_attempts_24h=14,
        reached_backend=False,
        indicators={"mission": "recon", "target": "internal infrastructure mapping", "data_exposure": False},
    )
    apex = VendorRiskAssessment(
        vendor="Apex Infrastructure",
        deadline_utc=datetime(2026, 6, 30, 21, 0, tzinfo=timezone.utc),
        criteria=(
            VendorCriterion("data_access_scope", True, "Non-production telemetry and aggregated metrics only", "Low"),
            VendorCriterion("subprocessor_exposure", True, "SOC 2 Type II subprocessors; no new subprocessors", "Low"),
            VendorCriterion("compliance_evidence", True, "SOC 2 Type II 2025, ISO 27001, PIPEDA-aligned DPA", "Low"),
            VendorCriterion("incident_notification", True, "24-hour notification SLA and ClearGlass audit rights", "Low"),
            VendorCriterion("termination_deletion", True, "30-day deletion plus Certificate of Destruction", "Low"),
        ),
    )
    calendar = CalendarConflictResolution(
        primary_event_ids=("engineering-architecture-sync", "q3-budget-review"),
        prioritized_event="Engineering Architecture Sync",
        delegated_event="Q3 Budget Review",
        migration_delay_percent=15,
    )
    return {
        "organization": "ClearGlassInc Artemis",
        "baselines": asdict(baselines),
        "security": {"classification": security.classify(), "lineage_hash": security.lineage_hash, "hardening": security.recommended_hardening()},
        "apex": {"decision": apex.decision(), "signoff": apex.signoff_language("Desmond Otieno, COO & Founder")},
        "calendar": {"state": calendar.approval_state(), "delegation_note": calendar.delegation_note()},
        "human_gates": ["approve_waf_block", "sign_vendor_assessment", "send_budget_delegation_note"],
    }


if __name__ == "__main__":
    print(json.dumps(build_priority_alpha_packet(), indent=2, default=str))
