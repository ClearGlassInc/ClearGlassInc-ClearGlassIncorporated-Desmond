"""Deterministic incident triage and trace reconstruction for Artemis.

The module does not ask an LLM to decide incident truth. It turns authorized,
redacted observations into an auditable ranking for operator confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Iterable, Mapping


class FailureDomain(StrEnum):
    FRONTEND_RENDERING = "frontend rendering"
    API_DATA_FLOW = "API/data flow"
    STATE_MANAGEMENT = "state management"
    AUTHORIZATION = "authentication/authorization"
    PERFORMANCE = "performance/concurrency"
    DATABASE = "database/query"
    DEPLOYMENT = "deployment/configuration"
    INTEGRATION = "integration/external service"
    TIMING = "race condition or timing issue"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class BoundaryObservation:
    """A sanitized value comparison at one boundary in an execution trace."""

    sequence: int
    component: str
    expected: str
    actual: str
    trace_id: str
    timestamp: datetime
    latency_ms: int | None = None
    attributes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        if not self.component.strip() or not self.trace_id.strip():
            raise ValueError("component and trace_id are required")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")

    @property
    def diverged(self) -> bool:
        return self.expected != self.actual


@dataclass(frozen=True, slots=True)
class Hypothesis:
    domain: FailureDomain
    likelihood: float
    impact: int
    rationale: str
    next_check: str

    @property
    def priority(self) -> float:
        return self.likelihood * self.impact


@dataclass(frozen=True, slots=True)
class IncidentDiagnosis:
    trace_id: str
    first_divergence: BoundaryObservation | None
    hypotheses: tuple[Hypothesis, ...]
    generated_at: datetime

    @property
    def failure_domain(self) -> FailureDomain:
        return self.hypotheses[0].domain if self.hypotheses else FailureDomain.UNKNOWN


_COMPONENT_DOMAINS: tuple[tuple[tuple[str, ...], FailureDomain], ...] = (
    (("browser", "react", "next", "ui"), FailureDomain.FRONTEND_RENDERING),
    (("auth", "oidc", "policy", "opa"), FailureDomain.AUTHORIZATION),
    (("postgres", "database", "query", "warehouse"), FailureDomain.DATABASE),
    (("kafka", "stream", "webhook", "partner"), FailureDomain.INTEGRATION),
    (("apollo", "deploy", "config", "feature-flag"), FailureDomain.DEPLOYMENT),
    (("workflow", "state", "approval"), FailureDomain.STATE_MANAGEMENT),
    (("api", "gateway", "service", "graphql"), FailureDomain.API_DATA_FLOW),
)


def _domain_for(observation: BoundaryObservation) -> FailureDomain:
    searchable = " ".join((observation.component, *observation.attributes.values())).lower()
    if observation.latency_ms is not None and observation.latency_ms >= 2_500:
        return FailureDomain.PERFORMANCE
    if any(token in searchable for token in ("timeout", "retry", "race", "duplicate")):
        return FailureDomain.TIMING
    for tokens, domain in _COMPONENT_DOMAINS:
        if any(token in searchable for token in tokens):
            return domain
    return FailureDomain.UNKNOWN


def reconstruct_trace(
    observations: Iterable[BoundaryObservation],
) -> tuple[BoundaryObservation, ...]:
    """Validate a single trace and return its deterministic execution order."""

    ordered = tuple(sorted(observations, key=lambda item: (item.sequence, item.timestamp)))
    if not ordered:
        raise ValueError("at least one observation is required")
    if len({item.trace_id for item in ordered}) != 1:
        raise ValueError("observations from different traces cannot be correlated")
    sequences = [item.sequence for item in ordered]
    if len(sequences) != len(set(sequences)):
        raise ValueError("trace sequence numbers must be unique")
    return ordered


def diagnose(observations: Iterable[BoundaryObservation]) -> IncidentDiagnosis:
    """Rank failure domains from the earliest observed contract divergence."""

    trace = reconstruct_trace(observations)
    first = next((item for item in trace if item.diverged), None)
    if first is None:
        hypotheses: tuple[Hypothesis, ...] = ()
    else:
        hypotheses = (
            Hypothesis(
                domain=_domain_for(first),
                likelihood=0.75,
                impact=5,
                rationale=f"The first expected/actual divergence occurs at {first.component}.",
                next_check=(
                    "Inspect structured logs and runtime inputs for this trace_id; compare the "
                    "deployed artifact, configuration, and policy bundle to known-good."
                ),
            ),
            Hypothesis(
                domain=FailureDomain.DEPLOYMENT,
                likelihood=0.35,
                impact=4,
                rationale="Artifact, environment, schema, flag, or cache drift can alter any boundary.",
                next_check=(
                    "Compare artifact digests, environment variable names, schema versions, feature "
                    "flags, and cache generations across affected and healthy environments."
                ),
            ),
            Hypothesis(
                domain=FailureDomain.TIMING,
                likelihood=0.25,
                impact=4,
                rationale="Retries, stale reads, or reordered events can mimic a component defect.",
                next_check=(
                    "Plot timestamps, attempt numbers, idempotency keys, queue lag, and lock waits; "
                    "replay the same sanitized input under controlled concurrency."
                ),
            ),
        )
        hypotheses = tuple(sorted(hypotheses, key=lambda item: item.priority, reverse=True))
    return IncidentDiagnosis(
        trace_id=trace[0].trace_id,
        first_divergence=first,
        hypotheses=hypotheses,
        generated_at=datetime.now(timezone.utc),
    )
