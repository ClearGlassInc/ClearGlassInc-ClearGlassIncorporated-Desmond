"""ClearGlassInc Artemis Supreme Legal Intelligence Core.

This module provides typed primitives for a governed legal analysis workflow. It is
not legal advice and does not replace licensed counsel; it helps applications keep
legal work structured, sourced, risk-rated, and reviewable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class AuthorityLevel(int, Enum):
    """Ordered legal authority hierarchy from strongest to weakest."""

    CONTROLLING_TEXT = 1
    BINDING_CASELAW = 2
    BINDING_PROCEDURAL_EVIDENTIARY_RULE = 3
    OFFICIAL_GOVERNMENT_GUIDANCE = 4
    PERSUASIVE_CASELAW = 5
    RECOGNIZED_SECONDARY_SOURCE = 6
    INDUSTRY_STANDARD = 7
    GENERAL_LEGAL_REASONING = 8


class RiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NEGOTIATION_OPPORTUNITY = "NEGOTIATION_OPPORTUNITY"


class FinalLegalStatus(str, Enum):
    LEGALLY_SUPPORTED = "LEGALLY_SUPPORTED"
    CONDITIONALLY_SUPPORTED = "CONDITIONALLY_SUPPORTED"
    LEGALLY_UNCERTAIN = "LEGALLY_UNCERTAIN"
    COUNSEL_AUTHORIZATION_REQUIRED = "COUNSEL_AUTHORIZATION_REQUIRED"
    PROHIBITED_OR_HIGH_RISK_ACTION_IDENTIFIED = "PROHIBITED_OR_HIGH_RISK_ACTION_IDENTIFIED"
    INSUFFICIENT_RELIABLE_AUTHORITY = "INSUFFICIENT_RELIABLE_AUTHORITY"


@dataclass(frozen=True)
class LegalAuthority:
    level: AuthorityLevel
    citation: str
    proposition: str
    jurisdiction: str
    binding: bool
    url: str | None = None


@dataclass(frozen=True)
class LegalRisk:
    issue: str
    level: RiskLevel
    rationale: str
    mitigation: str
    authority_citations: tuple[str, ...] = ()


@dataclass
class LegalMatterContext:
    objective: str
    jurisdiction: str
    governing_law: str | None = None
    forum: str | None = None
    procedural_posture: str | None = None
    client_role: str | None = None
    deadlines: list[str] = field(default_factory=list)
    confirmed_facts: list[str] = field(default_factory=list)
    material_assumptions: list[str] = field(default_factory=list)
    missing_facts: list[str] = field(default_factory=list)


@dataclass
class LegalAnalysisPacket:
    context: LegalMatterContext
    authorities: list[LegalAuthority]
    analysis: str
    risks: list[LegalRisk]
    recommended_action: str
    draft_language: str | None = None
    final_status: FinalLegalStatus = FinalLegalStatus.LEGALLY_UNCERTAIN
    counsel_review_notice: str = (
        "This structured analysis supports legal review but is not a substitute "
        "for advice from licensed counsel in the relevant jurisdiction."
    )

    def sorted_authorities(self) -> list[LegalAuthority]:
        return sorted(self.authorities, key=lambda authority: authority.level.value)

    def strongest_authority(self) -> LegalAuthority | None:
        ordered = self.sorted_authorities()
        return ordered[0] if ordered else None

    def requires_counsel_authorization(self) -> bool:
        high_risk = {RiskLevel.CRITICAL, RiskLevel.HIGH}
        return (
            self.final_status
            in {
                FinalLegalStatus.COUNSEL_AUTHORIZATION_REQUIRED,
                FinalLegalStatus.PROHIBITED_OR_HIGH_RISK_ACTION_IDENTIFIED,
                FinalLegalStatus.INSUFFICIENT_RELIABLE_AUTHORITY,
            }
            or any(risk.level in high_risk for risk in self.risks)
        )

    def render_markdown(self) -> str:
        authority_lines = [
            f"- {authority.level.name}: {authority.citation} — {authority.proposition}"
            for authority in self.sorted_authorities()
        ] or ["- No reliable authority supplied."]
        risk_lines = [
            f"- **{risk.level.value}** — {risk.issue}: {risk.rationale} Mitigation: {risk.mitigation}"
            for risk in self.risks
        ] or ["- No material risks recorded."]
        return "\n".join(
            [
                "# Legal Analysis Packet",
                "",
                "## 1. Executive conclusion",
                self.recommended_action,
                "",
                "## 2. Confirmed facts",
                *[f"- {fact}" for fact in self.context.confirmed_facts],
                "",
                "## 3. Material assumptions",
                *[f"- {assumption}" for assumption in self.context.material_assumptions],
                "",
                "## 4. Governing authority",
                *authority_lines,
                "",
                "## 5. Legal analysis",
                self.analysis,
                "",
                "## 6. Risks and deficiencies",
                *risk_lines,
                "",
                "## 7. Recommended action",
                self.recommended_action,
                "",
                "## 8. Draft language or deliverable",
                self.draft_language or "No draft language requested.",
                "",
                "## 9. Sources",
                *[f"- {authority.citation}" for authority in self.sorted_authorities()],
                "",
                "## 10. Counsel review notice",
                self.counsel_review_notice,
                "",
                "## 11. Final legal status",
                self.final_status.value,
            ]
        )


def rank_authorities(authorities: Iterable[LegalAuthority]) -> list[LegalAuthority]:
    """Return authorities in controlling-to-persuasive order."""

    return sorted(authorities, key=lambda authority: authority.level.value)


def classify_status(authorities: list[LegalAuthority], risks: list[LegalRisk]) -> FinalLegalStatus:
    """Conservative status classifier for legal workflow automation."""

    if not authorities:
        return FinalLegalStatus.INSUFFICIENT_RELIABLE_AUTHORITY
    if any(risk.level is RiskLevel.CRITICAL for risk in risks):
        return FinalLegalStatus.PROHIBITED_OR_HIGH_RISK_ACTION_IDENTIFIED
    if any(risk.level is RiskLevel.HIGH for risk in risks):
        return FinalLegalStatus.COUNSEL_AUTHORIZATION_REQUIRED
    strongest = rank_authorities(authorities)[0]
    if strongest.level.value <= AuthorityLevel.BINDING_PROCEDURAL_EVIDENTIARY_RULE.value:
        return FinalLegalStatus.CONDITIONALLY_SUPPORTED if risks else FinalLegalStatus.LEGALLY_SUPPORTED
    return FinalLegalStatus.LEGALLY_UNCERTAIN
