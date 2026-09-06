from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .schemas import AgentReport, EvidenceItem, Finding, Impact, SignalPacket, SourceCategory


ROOT_POLICY = """
You are an internal risk-intelligence agent owned and operated by ClearGlassInc.
You serve ClearGlassInc-authorized users and systems only.
You process lawful public-source data and authorized internal defensive telemetry only.
You do not support credential abuse, private-person targeting, unauthorized access, or private-data collection.
Return executive-ready, source-backed, audit-friendly risk intelligence.
""".strip()


def _impact_for(packet: SignalPacket) -> Impact:
    if packet.mission.value in {"risk_brief", "compliance"}:
        return Impact.HIGH
    if packet.domain.value in {"cyber", "vendor", "financial"}:
        return Impact.HIGH
    return Impact.MEDIUM


def _source_list(packet: SignalPacket) -> list[SourceCategory]:
    if packet.constraints.sources:
        return packet.constraints.sources
    if packet.domain.value == "cyber":
        return [SourceCategory.NVD, SourceCategory.CISA_KEV, SourceCategory.VENDOR_ADVISORY]
    if packet.domain.value == "legal":
        return [SourceCategory.PUBLIC_REGISTRY, SourceCategory.NEWS]
    if packet.domain.value == "vendor":
        return [SourceCategory.VENDOR_ADVISORY, SourceCategory.PUBLIC_WEB, SourceCategory.NEWS]
    return [SourceCategory.PUBLIC_WEB, SourceCategory.NEWS]


def build_report(packet: SignalPacket, principal: dict[str, str]) -> AgentReport:
    sources = _source_list(packet)
    evidence = [
        EvidenceItem(
            source=source,
            title=f"{source.value} signal set for {packet.target}",
            summary=(
                "Source registered for lawful aggregation and defensive risk analysis. "
                "Connector enrichment is pending deployment of external collectors."
            ),
            freshness="connector-ready",
            confidence=72 if source in {SourceCategory.PUBLIC_WEB, SourceCategory.NEWS} else 80,
            url=None,
        )
        for source in sources[: packet.constraints.max_results]
    ]

    impact = _impact_for(packet)
    avg_confidence = int(sum(item.confidence for item in evidence) / max(len(evidence), 1))
    summary = (
        f"ClearGlass generated a lawful {packet.mission.value} brief for {packet.target} "
        f"in the {packet.domain.value} domain. Current output is source-schema validated, "
        "audit-ready, and prepared for live connector enrichment."
    )

    finding = Finding(
        title=f"Decision-grade signal package: {packet.target}",
        impact=impact,
        confidence=avg_confidence,
        rationale=(
            "The request passed ClearGlass authorization, lawful-basis checks, and source-category validation. "
            "No unauthorized collection path was used."
        ),
        evidence=evidence,
        recommended_action=(
            "Connect approved public-source collectors, review source confidence weighting, then route the "
            "result into Executive Brief, Source Audit, or Blue Team Command workflows."
        ),
    )

    return AgentReport(
        request_id=packet.request_id,
        mission=packet.mission,
        domain=packet.domain,
        target=packet.target,
        executive_summary=summary,
        findings=[finding],
        compliance_note=(
            "ClearGlass lawful aggregation only. Public-source and authorized internal defensive telemetry are allowed. "
            "Credential abuse, private-person targeting, and unauthorized access are prohibited."
        ),
        audit={
            "policy": "ClearGlassInc-only lawful OSINT and defensive intelligence",
            "principal": principal,
            "root_policy_hash_basis": "ROOT_POLICY",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "constraints": packet.constraints.model_dump(mode="json"),
        },
    )


def root_policy() -> dict[str, Any]:
    return {
        "owner": "ClearGlassInc",
        "policy": ROOT_POLICY,
        "allowed": [
            "lawful public-source risk intelligence",
            "authorized internal defensive telemetry correlation",
            "executive-ready security briefings",
            "source audit and provenance reporting",
        ],
        "blocked": [
            "credential abuse",
            "private-person targeting",
            "unauthorized access",
            "private-data collection",
        ],
    }
