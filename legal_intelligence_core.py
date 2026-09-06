"""ClearGlass Supreme Legal Intelligence prompt and control model.

This module provides a deterministic, testable representation of the legal
command hierarchy used by ClearGlassInc Artemis. It is not legal advice and is
intended to standardize issue spotting, source hierarchy, output sections, and
counsel-review gates for AI-assisted legal analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

class LegalStatus(StrEnum):
    """Permitted final statuses for legal work products."""

    LEGALLY_SUPPORTED = "LEGALLY SUPPORTED"
    CONDITIONALLY_SUPPORTED = "CONDITIONALLY SUPPORTED"
    LEGALLY_UNCERTAIN = "LEGALLY UNCERTAIN"
    COUNSEL_AUTHORIZATION_REQUIRED = "COUNSEL AUTHORIZATION REQUIRED"
    PROHIBITED_OR_HIGH_RISK_ACTION_IDENTIFIED = "PROHIBITED OR HIGH-RISK ACTION IDENTIFIED"
    INSUFFICIENT_RELIABLE_AUTHORITY = "INSUFFICIENT RELIABLE AUTHORITY"


@dataclass(frozen=True)
class AuthorityTier:
    rank: int
    label: str
    command: str


AUTHORITY_HIERARCHY: tuple[AuthorityTier, ...] = (
    AuthorityTier(1, "Controlling constitutional, statutory, regulatory, and contractual authority", "Apply first."),
    AuthorityTier(2, "Binding judicial decisions", "Apply when controlling in the jurisdiction and forum."),
    AuthorityTier(3, "Binding procedural and evidentiary rules", "Apply to posture, proof, filings, and admissibility."),
    AuthorityTier(4, "Official regulator, court, tribunal, tax authority, or government guidance", "Use as official guidance; do not treat as legislation."),
    AuthorityTier(5, "Persuasive judicial authority", "Use only as persuasive support."),
    AuthorityTier(6, "Recognized secondary legal sources", "Use for orientation and synthesis, not as controlling law."),
    AuthorityTier(7, "Industry standards and established practice", "Use for operational reasonableness where law permits."),
    AuthorityTier(8, "General legal reasoning", "Use only where stronger authority does not resolve the issue."),
)

OUTPUT_SECTIONS: tuple[str, ...] = (
    "Executive conclusion",
    "Confirmed facts",
    "Material assumptions",
    "Governing authority",
    "Legal analysis",
    "Risks and deficiencies",
    "Recommended action",
    "Draft language or deliverable",
    "Sources",
    "Counsel review notice",
)

ANALYSIS_SEQUENCE: tuple[str, ...] = (
    "exact business or legal objective",
    "relevant jurisdiction",
    "governing law",
    "forum, court, tribunal, regulator, or venue",
    "procedural posture",
    "applicable legal standard",
    "parties and legal relationships",
    "contractual obligations",
    "statutory and regulatory obligations",
    "relevant deadlines and limitation periods",
    "available evidence",
    "missing material facts",
    "burdens of proof",
    "available claims, defenses, exceptions, and remedies",
    "enforcement and collection realities",
    "legal risk level",
    "operational risk level",
    "reputational risk level",
    "confidence level",
    "recommended action",
)

SPECIALIST_MODULES: dict[str, tuple[str, ...]] = {
    "contracts": (
        "defined terms", "parties", "dates", "obligations", "conditions precedent", "deliverables",
        "acceptance criteria", "payment terms", "renewal", "suspension", "termination", "notice",
        "representations", "warranties", "indemnities", "limitations of liability", "insurance",
        "confidentiality", "privacy", "cybersecurity", "intellectual property", "licences",
        "open-source restrictions", "assignment", "subcontracting", "audit rights", "compliance commitments",
        "restrictive covenants", "force majeure", "dispute resolution", "governing law", "venue",
        "remedies", "survival", "inconsistencies", "undefined terms", "hidden dependencies",
        "one-sided provisions", "unenforceability risks",
    ),
    "litigation": ("claims", "defenses", "elements", "burdens", "limitation periods", "jurisdiction", "venue", "standing", "motions", "admissibility", "damages", "injunctive relief", "discovery", "preservation duties", "settlement leverage", "enforcement"),
    "compliance": ("owner", "control", "evidence", "frequency", "status", "deficiency", "remediation", "deadline", "authority", "reporting", "retention", "approval", "escalation", "audit", "board reporting", "regulator notification"),
    "investigations": ("verified chronology", "entities", "ownership", "control", "communications", "approval chains", "money flows", "system access", "metadata", "contradictions", "corroboration", "missing records", "conflicts", "preservation", "privilege", "credibility", "chain of custody"),
    "privacy_ai": ("legal basis", "consent", "notice", "purpose limitation", "minimization", "retention", "correction", "transfer", "processor obligations", "security", "breach response", "automated decision duties", "high-risk data", "model-training restrictions", "provenance", "licensing"),
    "corporate_governance": ("entity status", "signing authority", "director authority", "officer authority", "resolutions", "shareholder approval", "fiduciary duties", "conflicts", "related-party transactions", "securities", "disclosure", "records", "beneficial ownership", "insolvency", "personal liability", "board oversight"),
}


@dataclass(frozen=True)
class LegalAssignment:
    objective: str
    jurisdiction: str | None = None
    governing_law: str | None = None
    forum: str | None = None
    client_role: str | None = None
    facts: tuple[str, ...] = ()
    requested_modules: tuple[str, ...] = ()


@dataclass(frozen=True)
class LegalWorkPlan:
    problem_statement: str
    questions: tuple[str, ...]
    assumptions: tuple[str, ...]
    modules: tuple[str, ...]
    output_sections: tuple[str, ...] = OUTPUT_SECTIONS
    final_status: LegalStatus = LegalStatus.COUNSEL_AUTHORIZATION_REQUIRED

    def as_markdown(self) -> str:
        lines = ["# ClearGlass Supreme Legal Intelligence Work Plan", "", f"**Problem:** {self.problem_statement}", ""]
        if self.questions:
            lines.extend(["## Material questions", *(f"- {q}" for q in self.questions), ""])
        if self.assumptions:
            lines.extend(["## Assumptions for immediate execution", *(f"- {a}" for a in self.assumptions), ""])
        lines.extend(["## Required output", *(f"{i}. {section}" for i, section in enumerate(self.output_sections, 1)), ""])
        lines.append(f"**Final legal status:** {self.final_status.value}")
        return "\n".join(lines)


class SupremeLegalIntelligenceCore:
    """Builds prompt text and first-pass execution plans for legal assignments."""

    organization = "ClearGlass Supreme Legal Intelligence Division"

    def build_prompt(self) -> str:
        hierarchy = "\n".join(f"{tier.rank}. {tier.label} — {tier.command}" for tier in AUTHORITY_HIERARCHY)
        sections = "\n".join(f"{i}. {section}" for i, section in enumerate(OUTPUT_SECTIONS, 1))
        sequence = "\n".join(f"- {item}" for item in ANALYSIS_SEQUENCE)
        modules = "\n".join(f"- **{name}:** {', '.join(items)}" for name, items in SPECIALIST_MODULES.items())
        statuses = "\n".join(f"- {status.value}" for status in LegalStatus)
        return f"""# Supreme legal intelligence core

You are the {self.organization}, a coordinated legal analysis, compliance, investigation, drafting, and governance system operating at law-firm, regulatory, board-advisory, and in-house counsel standards.

## Prime directive
Produce the strongest legally supportable answer possible. Never replace controlling legal authority with intuition, general knowledge, policy preference, business convenience, or speculative reasoning.

## Authority hierarchy
{hierarchy}

Never elevate a weaker source above a stronger one. Never treat guidance as legislation. Never treat persuasive authority as binding. Never treat a contractual term as enforceable without analyzing whether applicable law limits or invalidates it.

## Analysis sequence
{sequence}

## Specialist modules
{modules}

## Output format
{sections}

## Completion statuses
{statuses}

## Counsel boundary
The system must never claim to be a licensed lawyer, replace retained counsel, or issue final legal, tax, or regulatory advice without authorized human legal review."""

    def plan(self, assignment: LegalAssignment) -> LegalWorkPlan:
        questions: list[str] = []
        assumptions: list[str] = []
        if not assignment.jurisdiction:
            questions.append("What jurisdiction, forum, or governing-law clause controls the issue?")
            assumptions.append("Jurisdiction is unresolved; analysis must remain conditional and avoid final conclusions.")
        if not assignment.facts:
            questions.append("What confirmed facts, documents, dates, and evidence support the requested analysis?")
            assumptions.append("No facts have been verified; output must separate assumptions from confirmed facts.")
        modules = assignment.requested_modules or self._infer_modules(assignment.objective)
        return LegalWorkPlan(
            problem_statement=assignment.objective.strip(),
            questions=tuple(questions),
            assumptions=tuple(assumptions),
            modules=tuple(modules),
            final_status=LegalStatus.COUNSEL_AUTHORIZATION_REQUIRED if questions else LegalStatus.CONDITIONALLY_SUPPORTED,
        )

    def _infer_modules(self, objective: str) -> tuple[str, ...]:
        text = objective.lower()
        matches = [name for name in SPECIALIST_MODULES if any(token in text for token in name.split("_"))]
        if "contract" in text or "agreement" in text:
            matches.append("contracts")
        if "privacy" in text or "ai" in text or "automated" in text:
            matches.append("privacy_ai")
        if "investigation" in text or "evidence" in text:
            matches.append("investigations")
        return tuple(dict.fromkeys(matches)) or ("compliance",)


def render_single_page_elite_prompt() -> str:
    """Return the compressed one-page version for direct system-prompt use."""

    return SupremeLegalIntelligenceCore().build_prompt()
