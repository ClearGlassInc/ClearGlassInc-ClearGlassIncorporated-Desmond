#!/usr/bin/env python3
"""ClearGlassInc Artemis legal-tech multi-agent MVP.

Prototype: OSINT + document-processing pipeline for demo-ready legal automation.
The module is deterministic and offline by default so it can be tested in secure
or air-gapped environments. It is not legal advice; it creates counsel-review
packets with provenance, confidence, policy gates, and measurable extraction
quality.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable


class AgentName(StrEnum):
    DOCUMENT = "Document Processing Agent"
    OSINT = "OSINT Enrichment Agent"
    CORRELATION = "Risk Correlation Agent"
    REVIEW = "Counsel Review Gate Agent"


class MatterState(StrEnum):
    INTAKE = "intake"
    ENRICHED = "enriched"
    REVIEW_REQUIRED = "review_required"
    READY_FOR_COUNSEL = "ready_for_counsel"


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    source_type: str
    uri: str
    captured_at: str
    hash: str


@dataclass(frozen=True)
class LegalEntity:
    name: str
    role: str
    confidence: float
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class Obligation:
    party: str
    duty: str
    deadline: str | None
    confidence: float
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class RiskFinding:
    finding_id: str
    severity: str
    issue: str
    rationale: str
    confidence: float
    evidence: tuple[str, ...]
    approval_gate: str


@dataclass
class LegalMatterPacket:
    matter_id: str
    organization: str
    state: MatterState
    jurisdiction: str
    classification: str
    coalition_scope: tuple[str, ...]
    sources: list[SourceRef] = field(default_factory=list)
    entities: list[LegalEntity] = field(default_factory=list)
    obligations: list[Obligation] = field(default_factory=list)
    findings: list[RiskFinding] = field(default_factory=list)
    audit: list[dict[str, Any]] = field(default_factory=list)

    def record(self, agent: AgentName, action: str, payload: dict[str, Any]) -> None:
        self.audit.append(
            {
                "agent": agent.value,
                "action": action,
                "payload_hash": sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                "recorded_at": datetime.now(UTC).isoformat(),
            }
        )


class PolicyGuard:
    """Need-to-know and human-gate checks used by every agent."""

    def __init__(self, allowed_coalitions: Iterable[str], allowed_classifications: Iterable[str]) -> None:
        self.allowed_coalitions = set(allowed_coalitions)
        self.allowed_classifications = set(allowed_classifications)

    def assert_read_allowed(self, packet: LegalMatterPacket) -> None:
        if packet.classification not in self.allowed_classifications:
            raise PermissionError(f"classification denied: {packet.classification}")
        if not set(packet.coalition_scope).issubset(self.allowed_coalitions):
            raise PermissionError(f"coalition denied: {packet.coalition_scope}")

    @staticmethod
    def human_gate_for(finding: RiskFinding) -> str:
        if finding.severity in {"critical", "high"}:
            return "licensed_counsel_approval_required"
        return "analyst_review_required"


class DocumentProcessingAgent:
    PARTY_PATTERN = re.compile(r"\b(?:Client|Vendor|Counterparty|Licensor|Licensee):\s*([^\n;]+)", re.I)
    DEADLINE_PATTERN = re.compile(r"\b(?:by|within|no later than)\s+([A-Za-z0-9 ,\-]+?)(?:\.|;|\n)", re.I)

    def run(self, packet: LegalMatterPacket, document_text: str) -> LegalMatterPacket:
        source = SourceRef(
            source_id="doc-primary",
            source_type="contract_or_legal_document",
            uri="memory://uploaded-document",
            captured_at=datetime.now(UTC).isoformat(),
            hash=sha256(document_text.encode()).hexdigest(),
        )
        packet.sources.append(source)

        parties = [p.strip() for p in self.PARTY_PATTERN.findall(document_text)]
        for idx, party in enumerate(parties):
            role = "client" if idx == 0 else "counterparty"
            packet.entities.append(LegalEntity(party, role, 0.97, (source.source_id,)))

        deadline_match = self.DEADLINE_PATTERN.search(document_text)
        deadline = deadline_match.group(1).strip() if deadline_match else None
        if "terminate" in document_text.lower():
            packet.obligations.append(
                Obligation(parties[0] if parties else "unknown", "termination_notice", deadline, 0.94, (source.source_id,))
            )
        if "indemn" in document_text.lower():
            packet.obligations.append(
                Obligation(parties[1] if len(parties) > 1 else "counterparty", "indemnification", None, 0.91, (source.source_id,))
            )
        packet.record(AgentName.DOCUMENT, "extract_entities_obligations", {"parties": parties, "deadline": deadline})
        return packet


class OsintEnrichmentAgent:
    """Offline OSINT stub: replace data argument with approved APIs in production."""

    def run(self, packet: LegalMatterPacket, osint_records: list[dict[str, Any]]) -> LegalMatterPacket:
        for record in osint_records:
            blob = json.dumps(record, sort_keys=True)
            packet.sources.append(
                SourceRef(
                    source_id=f"osint-{record['id']}",
                    source_type=record.get("type", "public_record"),
                    uri=record.get("uri", "memory://osint"),
                    captured_at=datetime.now(UTC).isoformat(),
                    hash=sha256(blob.encode()).hexdigest(),
                )
            )
        packet.record(AgentName.OSINT, "attach_public_records", {"records": len(osint_records)})
        packet.state = MatterState.ENRICHED
        return packet


class RiskCorrelationAgent:
    def run(self, packet: LegalMatterPacket, osint_records: list[dict[str, Any]]) -> LegalMatterPacket:
        adverse = [r for r in osint_records if r.get("signal") in {"sanctions_candidate", "litigation", "insolvency"}]
        for idx, record in enumerate(adverse, start=1):
            severity = "critical" if record.get("signal") == "sanctions_candidate" else "high"
            finding = RiskFinding(
                finding_id=f"risk-{idx}",
                severity=severity,
                issue=f"Counterparty OSINT signal: {record['signal']}",
                rationale=record.get("summary", "Public-record signal requires legal review."),
                confidence=float(record.get("confidence", 0.8)),
                evidence=(f"osint-{record['id']}",),
                approval_gate="pending",
            )
            packet.findings.append(
                RiskFinding(**{**asdict(finding), "approval_gate": PolicyGuard.human_gate_for(finding)})
            )
        if any(o.duty == "termination_notice" and not o.deadline for o in packet.obligations):
            packet.findings.append(
                RiskFinding(
                    "risk-deadline-missing",
                    "medium",
                    "Termination clause lacks extracted deadline",
                    "Automation could not confirm a notice deadline; counsel should verify before action.",
                    0.88,
                    ("doc-primary",),
                    "analyst_review_required",
                )
            )
        packet.record(AgentName.CORRELATION, "correlate_document_osint_risks", {"findings": len(packet.findings)})
        packet.state = MatterState.REVIEW_REQUIRED if packet.findings else MatterState.READY_FOR_COUNSEL
        return packet


class CounselReviewGateAgent:
    def run(self, packet: LegalMatterPacket) -> dict[str, Any]:
        high_risk = [f for f in packet.findings if f.severity in {"critical", "high"}]
        action = "block_autonomous_action_and_prepare_counsel_packet" if high_risk else "prepare_analyst_review_packet"
        packet.record(AgentName.REVIEW, action, {"high_risk_findings": len(high_risk)})
        return {
            "matter_id": packet.matter_id,
            "state": packet.state.value,
            "recommended_next_step": action,
            "human_approval_required": True,
            "summary": {
                "entities": [asdict(e) for e in packet.entities],
                "obligations": [asdict(o) for o in packet.obligations],
                "findings": [asdict(f) for f in packet.findings],
            },
            "audit": packet.audit,
        }


class LegalTechWorkflow:
    def __init__(self, policy: PolicyGuard) -> None:
        self.policy = policy
        self.document_agent = DocumentProcessingAgent()
        self.osint_agent = OsintEnrichmentAgent()
        self.risk_agent = RiskCorrelationAgent()
        self.review_agent = CounselReviewGateAgent()

    def run(self, document_text: str, osint_records: list[dict[str, Any]]) -> dict[str, Any]:
        packet = LegalMatterPacket(
            matter_id="matter-demo-001",
            organization="ClearGlassInc Artemis",
            state=MatterState.INTAKE,
            jurisdiction="Ontario, Canada",
            classification="CONFIDENTIAL",
            coalition_scope=("CLEARGLASSINC",),
        )
        self.policy.assert_read_allowed(packet)
        packet = self.document_agent.run(packet, document_text)
        packet = self.osint_agent.run(packet, osint_records)
        packet = self.risk_agent.run(packet, osint_records)
        return self.review_agent.run(packet)


def evaluate_extraction(report: dict[str, Any], expected: dict[str, int]) -> dict[str, float]:
    actual = {
        "entities": len(report["summary"]["entities"]),
        "obligations": len(report["summary"]["obligations"]),
        "findings": len(report["summary"]["findings"]),
    }
    total = sum(expected.values())
    errors = sum(abs(actual[k] - expected[k]) for k in expected)
    error_rate = errors / max(total, 1)
    return {"error_rate": round(error_rate, 4), "accuracy": round(1 - error_rate, 4), **{f"actual_{k}": v for k, v in actual.items()}}


def demo_payload() -> tuple[str, list[dict[str, Any]], dict[str, int]]:
    return (
        "Client: ClearGlassInc Artemis\nVendor: Northstar Data Brokers Inc.\n"
        "The client may terminate the agreement by no later than 30 days after notice.\n"
        "Vendor indemnifies Client for third-party privacy claims.",
        [
            {
                "id": "1",
                "type": "court_record",
                "signal": "litigation",
                "confidence": 0.93,
                "summary": "Vendor appears in recent privacy class-action docket.",
                "uri": "https://example.invalid/court/1",
            },
            {
                "id": "2",
                "type": "registry",
                "signal": "normal_registry",
                "confidence": 0.98,
                "summary": "Corporate registry active.",
                "uri": "https://example.invalid/registry/2",
            },
        ],
        {"entities": 2, "obligations": 2, "findings": 1},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ClearGlassInc Artemis legal-tech multi-agent MVP.")
    parser.add_argument("--json-out", type=Path, help="Optional path for the demo report JSON.")
    args = parser.parse_args()
    document, osint, expected = demo_payload()
    workflow = LegalTechWorkflow(PolicyGuard({"CLEARGLASSINC"}, {"CONFIDENTIAL"}))
    report = workflow.run(document, osint)
    report["quality"] = evaluate_extraction(report, expected)
    output = json.dumps(report, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
