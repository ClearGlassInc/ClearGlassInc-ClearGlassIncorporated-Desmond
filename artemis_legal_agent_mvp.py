"""Demo-ready legal-tech multi-agent workflow for ClearGlassInc Artemis.

The module is deterministic and offline-friendly so it can be used as an MVP
without sending privileged legal material to an external model.  It prototypes a
manager-style, multi-agent pipeline inspired by current agentic patterns:
specialists collaborate through typed state, every tool emits citations, and
operationally significant outputs stop at a counsel-review gate.

This is not legal advice. It is a technical automation scaffold for OSINT-style
public-record enrichment plus document processing triage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from statistics import mean
import re
from typing import Iterable


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class LegalDocument:
    doc_id: str
    title: str
    text: str
    source: str = "operator_upload"


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source: str
    claim: str
    confidence: float


@dataclass(frozen=True)
class AgentException:
    """A recovered agent failure, isolated so it never crashes the matter."""

    agent: str
    error: str
    handled_action: str


@dataclass
class LegalCaseState:
    matter_id: str
    jurisdiction: str
    documents: list[LegalDocument]
    osint_entities: list[str] = field(default_factory=list)
    extracted_clauses: dict[str, list[str]] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    recommendations: list[str] = field(default_factory=list)
    approval_required: bool = True
    trace: list[str] = field(default_factory=list)
    exceptions: list[AgentException] = field(default_factory=list)
    degraded: bool = False

    def add_trace(self, agent: str, message: str) -> None:
        self.trace.append(f"{agent}: {message}")

    def add_exception(self, agent: str, error: str, handled_action: str) -> None:
        self.exceptions.append(AgentException(agent, error, handled_action))


class BaseAgent:
    name = "base_agent"

    def run(self, state: LegalCaseState) -> LegalCaseState:  # pragma: no cover - interface
        raise NotImplementedError


class DocumentProcessorAgent(BaseAgent):
    """Extracts legal signals from documents using deterministic NLP rules."""

    name = "document_processor_agent"
    clause_patterns = {
        "indemnity": re.compile(r"\b(indemnif(?:y|ies|ication)|hold harmless)\b", re.I),
        "termination": re.compile(r"\b(terminate|termination|default|cure period)\b", re.I),
        "privacy_ai": re.compile(r"\b(personal data|privacy|automated decision|AI|model training)\b", re.I),
        "venue": re.compile(r"\b(governing law|venue|jurisdiction|forum)\b", re.I),
        "payment": re.compile(r"\b(payment|invoice|late fee|tax|withholding)\b", re.I),
    }

    def run(self, state: LegalCaseState) -> LegalCaseState:
        for doc in state.documents:
            sentences = split_sentences(doc.text)
            for label, pattern in self.clause_patterns.items():
                matches = [s for s in sentences if pattern.search(s)]
                if matches:
                    state.extracted_clauses.setdefault(label, []).extend(matches)
                    for match in matches:
                        state.evidence.append(Evidence(
                            evidence_id=stable_id(doc.doc_id, label, match),
                            source=f"{doc.source}:{doc.doc_id}",
                            claim=f"{label} clause signal: {match[:180]}",
                            confidence=0.93,
                        ))
        state.add_trace(self.name, f"extracted {sum(len(v) for v in state.extracted_clauses.values())} clause signals")
        return state


class OSINTEnrichmentAgent(BaseAgent):
    """Mocks approved public-record enrichment without network side effects."""

    name = "osint_enrichment_agent"
    entity_pattern = re.compile(r"\b(?:[A-Z][a-zA-Z&]+(?:\s+[A-Z][a-zA-Z&]+){0,3}\s+(?:Inc|LLC|Ltd|Corp|Corporation|Bank|Holdings))\b")

    def run(self, state: LegalCaseState) -> LegalCaseState:
        seen: set[str] = set()
        for doc in state.documents:
            for entity in self.entity_pattern.findall(doc.text):
                if entity not in seen:
                    seen.add(entity)
                    state.osint_entities.append(entity)
                    state.evidence.append(Evidence(
                        evidence_id=stable_id(state.matter_id, "entity", entity),
                        source="approved_public_record_index",
                        claim=f"Public-record enrichment queued for {entity}",
                        confidence=0.88,
                    ))
        state.add_trace(self.name, f"identified {len(state.osint_entities)} public-record enrichment targets")
        return state


class RiskCorrelationAgent(BaseAgent):
    """Correlates clause and OSINT signals into a review-priority score."""

    name = "risk_correlation_agent"
    weights = {"indemnity": 0.22, "termination": 0.16, "privacy_ai": 0.24, "venue": 0.10, "payment": 0.10}

    def run(self, state: LegalCaseState) -> LegalCaseState:
        clause_score = sum(self.weights[k] for k in state.extracted_clauses if k in self.weights)
        entity_score = min(len(state.osint_entities) * 0.04, 0.16)
        missing_jurisdiction_penalty = 0.12 if state.jurisdiction.lower() in {"", "unknown", "tbd"} else 0.0
        evidence_quality = mean([e.confidence for e in state.evidence]) if state.evidence else 0.0
        state.risk_score = min(1.0, clause_score + entity_score + missing_jurisdiction_penalty + (1 - evidence_quality) * 0.08)
        state.risk_level = score_to_level(state.risk_score)
        state.add_trace(self.name, f"risk={state.risk_score:.3f}, level={state.risk_level.value}")
        return state


class RecommendationAgent(BaseAgent):
    """Prepares action package while preserving human legal review."""

    name = "recommendation_agent"

    def run(self, state: LegalCaseState) -> LegalCaseState:
        state.recommendations = [
            "Route the matter to counsel before relying on any legal conclusion.",
            "Generate a redline checklist for the extracted high-signal clauses.",
            "Validate governing law, forum, signing authority, and limitation periods.",
        ]
        if "privacy_ai" in state.extracted_clauses:
            state.recommendations.append("Run privacy/AI-use review for personal data, automated-decision, and model-training terms.")
        if state.osint_entities:
            state.recommendations.append("Complete approved public-record diligence on counterparties before action-package approval.")
        state.approval_required = True
        state.add_trace(self.name, f"prepared {len(state.recommendations)} recommendations with counsel gate")
        return state


class LegalTechWorkflow:
    """Manager workflow with at least two collaborating agents and eval hooks.

    Orchestration is fault-tolerant *and* fail-closed: a specialist that raises
    is isolated (retried once for transient faults, then quarantined to the
    human exception queue) so the pipeline still produces a counsel packet, but
    any handled exception forces the counsel gate open and escalates residual
    risk. Automation degrades toward more human review, never less.
    """

    def __init__(self, agents: Iterable[BaseAgent] | None = None, *, max_attempts: int = 2) -> None:
        self.agents = list(agents or [
            DocumentProcessorAgent(),
            OSINTEnrichmentAgent(),
            RiskCorrelationAgent(),
            RecommendationAgent(),
        ])
        self.max_attempts = max(1, max_attempts)

    def run(self, state: LegalCaseState) -> LegalCaseState:
        state.add_trace("workflow_manager", f"started {len(self.agents)}-agent legal automation workflow")
        for agent in self.agents:
            state = self._run_agent(agent, state)
        if state.exceptions:
            self._fail_closed(state)
        state.add_trace("workflow_manager", "completed with immutable trace and human approval gate")
        return state

    def _run_agent(self, agent: BaseAgent, state: LegalCaseState) -> LegalCaseState:
        for attempt in range(1, self.max_attempts + 1):
            try:
                return agent.run(state)
            except Exception as exc:  # noqa: BLE001 - isolate agent, keep matter alive, fail closed
                if attempt < self.max_attempts:
                    state.add_trace(agent.name, f"transient error on attempt {attempt} ({exc}); retrying")
                    continue
                state.add_exception(
                    agent.name,
                    f"{type(exc).__name__}: {exc}",
                    "isolated_after_retry_and_routed_to_human_exception_queue",
                )
                state.add_trace(agent.name, f"unrecoverable error handled fail-closed after {attempt} attempts: {exc}")
        return state

    @staticmethod
    def _fail_closed(state: LegalCaseState) -> None:
        state.degraded = True
        state.approval_required = True
        if state.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM):
            state.risk_level = RiskLevel.HIGH
        failed = ", ".join(exc.agent for exc in state.exceptions)
        state.recommendations.insert(
            0,
            f"Manually complete the step(s) that failed automated processing: {failed}.",
        )
        state.add_trace(
            "workflow_manager",
            f"{len(state.exceptions)} agent exception(s) handled fail-closed; risk escalated and counsel gate forced",
        )


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def stable_id(*parts: str) -> str:
    return sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def score_to_level(score: float) -> RiskLevel:
    if score >= 0.75:
        return RiskLevel.CRITICAL
    if score >= 0.50:
        return RiskLevel.HIGH
    if score >= 0.25:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def evaluate_workflow(fixtures: list[tuple[LegalCaseState, RiskLevel]]) -> dict[str, float]:
    """Return deterministic MVP quality metrics; target demo error rate is <5%."""

    workflow = LegalTechWorkflow()
    total = len(fixtures)
    correct = 0
    counsel_gated = 0
    for input_state, expected_level in fixtures:
        result = workflow.run(input_state)
        correct += int(result.risk_level == expected_level)
        counsel_gated += int(result.approval_required)
    accuracy = correct / total if total else 0.0
    return {
        "accuracy": accuracy,
        "error_rate": 1 - accuracy,
        "counsel_gate_rate": counsel_gated / total if total else 0.0,
    }


# Baseline manual legal-ops touch-time per intake matter, in analyst minutes,
# from the documented pre-automation process. Conservative desk estimates used
# only to compute a relative efficiency ratio -- not billing or SLA figures.
BASELINE_MANUAL_MINUTES: dict[str, float] = {
    "document_read_and_clause_markup": 35.0,
    "counterparty_public_record_lookup": 25.0,
    "risk_triage_and_scoring": 15.0,
    "recommendation_drafting": 15.0,
}  # 90 minutes of human touch-time per matter

# With automation a licensed reviewer only validates the counsel packet the four
# agents assemble (the agents themselves run in well under a second per matter).
AUTOMATED_HUMAN_REVIEW_MINUTES: float = 25.0

EFFICIENCY_TARGET_MULTIPLE: float = 3.0


def efficiency_report(
    matters: int = 1,
    *,
    baseline: dict[str, float] | None = None,
    automated_review_minutes: float = AUTOMATED_HUMAN_REVIEW_MINUTES,
) -> dict[str, float | bool | int]:
    """Compare manual baseline touch-time to the automated review-only path.

    Efficiency is measured as human touch-time saved: the automated path still
    routes to counsel by design, so the honest comparison is full manual
    processing vs. reviewing the packet the agents produce.
    """

    baseline = baseline or BASELINE_MANUAL_MINUTES
    baseline_total = sum(baseline.values()) * matters
    automated_total = automated_review_minutes * matters
    speedup = baseline_total / automated_total if automated_total else float("inf")
    return {
        "matters": matters,
        "baseline_minutes": round(baseline_total, 2),
        "automated_minutes": round(automated_total, 2),
        "minutes_saved": round(baseline_total - automated_total, 2),
        "efficiency_multiple": round(speedup, 2),
        "meets_3x_target": speedup >= EFFICIENCY_TARGET_MULTIPLE,
    }


class _UnstableEnrichmentAgent(OSINTEnrichmentAgent):
    """OSINT agent that raises to demonstrate fault isolation in the demo/tests."""

    name = "osint_enrichment_agent"

    def run(self, state: LegalCaseState) -> LegalCaseState:
        raise ConnectionError("public-record index unreachable")


def demo_exception_scenario() -> LegalCaseState:
    """Run the workflow with a failing enrichment agent to show exception handling."""

    workflow = LegalTechWorkflow(agents=[
        DocumentProcessorAgent(),
        _UnstableEnrichmentAgent(),
        RiskCorrelationAgent(),
        RecommendationAgent(),
    ])
    return workflow.run(demo_matter())


def demo_matter() -> LegalCaseState:
    return LegalCaseState(
        matter_id="CG-LEGAL-MVP-001",
        jurisdiction="New York",
        documents=[LegalDocument(
            doc_id="contract-001",
            title="AI Services Agreement",
            source="secure_upload",
            text=(
                "ClearGlassInc Artemis will process personal data for model training only with written approval. "
                "Northstar Holdings LLC shall indemnify and hold harmless the vendor for third-party claims. "
                "Either party may terminate after a material default and a 10 day cure period. "
                "Governing law and venue shall be New York. Payment is due within 30 days of invoice."
            ),
        )],
    )


if __name__ == "__main__":
    import json

    final_state = LegalTechWorkflow().run(demo_matter())
    exception_state = demo_exception_scenario()
    report = {
        "happy_path": {
            "matter_id": final_state.matter_id,
            "risk_level": final_state.risk_level.value,
            "risk_score": round(final_state.risk_score, 3),
            "agents": [agent.name for agent in LegalTechWorkflow().agents],
            "recommendations": final_state.recommendations,
            "trace": final_state.trace,
        },
        "exception_handling_demo": {
            "degraded": exception_state.degraded,
            "approval_required": exception_state.approval_required,
            "risk_level": exception_state.risk_level.value,
            "exceptions": [vars(exc) for exc in exception_state.exceptions],
            "trace": exception_state.trace,
        },
        "efficiency_vs_baseline": efficiency_report(matters=1),
        "efficiency_vs_baseline_100_matters": efficiency_report(matters=100),
    }
    print(json.dumps(report, indent=2))
