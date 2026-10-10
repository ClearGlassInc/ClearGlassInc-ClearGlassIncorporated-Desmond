"""APEX planning, evidence lineage, policy scoring and quantum-claim discipline.

This module composes the existing ClearGlass control-plane governance kernel.
It does not execute tools, fetch source URLs, call a model or submit quantum jobs.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
import math
import re
import secrets
from typing import Sequence
from urllib.parse import urlsplit

from .governance import RiskAssessment, score_action

_SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
_ALLOWED_SCHEMES = {"https", "http", "repo", "artifact", "dataset", "urn"}
_SECURITY_TERMS = (
    "security", "threat", "incident", "vulnerability", "defense", "defence", "attack", "audit"
)
_QUANTUM_TERMS = ("quantum", "optimization", "optimisation", "schedule", "scheduling", "routing")


class APEXInputError(ValueError):
    """An invalid mission or provenance reference was supplied."""


@dataclass(frozen=True)
class EvidenceRef:
    """A reference to evidence, never the evidence contents themselves."""

    source_id: str
    uri: str
    sha256: str | None = None

    def __post_init__(self) -> None:
        if not _SOURCE_ID.fullmatch(self.source_id):
            raise APEXInputError("source_id must be 1-64 safe identifier characters")
        if not self.uri or len(self.uri) > 1024:
            raise APEXInputError("uri must contain 1-1024 characters")
        parsed = urlsplit(self.uri)
        if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
            raise APEXInputError("uri scheme is not allowed for a provenance reference")
        if parsed.username or parsed.password:
            raise APEXInputError("credentials must not be embedded in provenance URIs")
        if self.sha256 is not None and not _SHA256.fullmatch(self.sha256):
            raise APEXInputError("sha256 must be a 64-character hexadecimal digest")

    @property
    def digest_status(self) -> str:
        # A supplied digest is a declaration until the underlying bytes are independently read.
        return "declared_not_verified" if self.sha256 else "missing"


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    specialist: str
    objective: str
    expected_output: str
    evidence_required: bool = True
    human_review_required: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class APEXPlan:
    mission_id: str
    plan_id: str
    plan_fingerprint: str
    status: str
    requested_action: str
    action_assessment: RiskAssessment
    plan_assessment: RiskAssessment
    sources: tuple[dict[str, str], ...]
    steps: tuple[PlanStep, ...]
    quantum_research_included: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "mission_id": self.mission_id,
            "plan_id": self.plan_id,
            "plan_fingerprint": self.plan_fingerprint,
            "status": self.status,
            "execution_status": "not_executed",
            "external_side_effects": False,
            "requested_action": self.requested_action,
            "action_assessment": self.action_assessment.to_dict(),
            "plan_assessment": self.plan_assessment.to_dict(),
            "sources": list(self.sources),
            "steps": [step.to_dict() for step in self.steps],
            "quantum_research": {
                "included": self.quantum_research_included,
                "status": (
                    "benchmark_design_only"
                    if self.quantum_research_included
                    else "not_requested"
                ),
                "quantum_job_submitted": False,
                "quantum_advantage_claimed": False,
            },
        }


def _make_steps(objective: str, quantum_requested: bool) -> tuple[PlanStep, ...]:
    """Build a deterministic specialist plan; no specialist is actually invoked."""
    normalized = objective.casefold()
    security = any(term in normalized for term in _SECURITY_TERMS)
    rows: list[tuple[str, str, str]] = [
        (
            "CORTEX",
            "Decompose the objective into testable acceptance criteria, assumptions and unknowns.",
            "Acceptance criteria and explicit assumption register",
        ),
        (
            "ARTEMIS",
            (
                "Map each supplied source to its provenance; correlate supported facts "
                "and preserve contradictions."
            ),
            "Evidence map with source identifiers, limitations and unresolved conflicts",
        ),
        (
            "AEGIS",
            (
                "Apply the existing fail-closed risk policy; identify actions requiring "
                "a human decision."
            ),
            "Policy decision and approval boundary",
        ),
    ]
    if security:
        rows.append(
            (
                "SENTINEL",
                (
                    "Review defensive security implications and independently identify "
                    "unsupported threat claims."
                ),
                "Defensive findings, counterevidence and remediation options",
            )
        )
    else:
        rows.append(
            (
                "SENTINEL",
                "Independently critique the proposed reasoning, evidence gaps and failure modes.",
                "Independent critique and residual-risk list",
            )
        )
    if quantum_requested:
        rows.append(
            (
                "QUANTUM_RESEARCH",
                (
                    "Specify a reproducible classical-versus-quantum or quantum-inspired "
                    "benchmark before selecting a backend."
                ),
                "Benchmark protocol, equal-constraint baseline and claim limitations",
            )
        )
    rows.append(
        (
            "CORTEX",
            (
                "Synthesize a traceable recommendation and distinguish verified facts, "
                "hypotheses and missing evidence."
            ),
            "Decision brief with confidence limits and next human review",
        )
    )
    return tuple(
        PlanStep(
            step_id=f"APEX-{index:02d}",
            specialist=specialist,
            objective=task,
            expected_output=output,
        )
        for index, (specialist, task, output) in enumerate(rows, start=1)
    )


def create_plan(
    *,
    mission_id: str,
    objective: str,
    requested_action: str = "apex_plan_mission",
    sources: Sequence[EvidenceRef] = (),
    fingerprint_key: str = "local-development-key-change-in-production",
) -> APEXPlan:
    """Create a plan-only mission envelope, using the control plane's policy kernel."""
    if not _SOURCE_ID.fullmatch(mission_id):
        raise APEXInputError("mission_id must be 1-64 safe identifier characters")
    if not objective or len(objective.strip()) < 8 or len(objective) > 2000:
        raise APEXInputError("objective must contain 8-2000 characters")
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", requested_action):
        raise APEXInputError("requested_action must be a snake_case action identifier")

    quantum_requested = any(term in objective.casefold() for term in _QUANTUM_TERMS)
    steps = _make_steps(objective, quantum_requested)
    source_summary = tuple(
        {
            "source_id": ref.source_id,
            "digest_status": ref.digest_status,
            "digest": ref.sha256.lower() if ref.sha256 else "",
        }
        for ref in sources
    )

    # Missing evidence raises the risk score and hard-gates the requested action.
    action_assessment = score_action(
        requested_action,
        payload={},
        low_confidence=not bool(sources),
    )
    plan_assessment = score_action("apex_plan_mission", {})
    plan_id = "APX-" + secrets.token_hex(6).upper()
    material = {
        "mission_id": mission_id,
        "objective": objective.strip(),
        "requested_action": requested_action,
        "sources": source_summary,
        "steps": [step.to_dict() for step in steps],
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    fingerprint = hmac.new(
        fingerprint_key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return APEXPlan(
        mission_id=mission_id,
        plan_id=plan_id,
        plan_fingerprint=fingerprint,
        status="planned_only",
        requested_action=requested_action,
        action_assessment=action_assessment,
        plan_assessment=plan_assessment,
        sources=source_summary,
        steps=steps,
        quantum_research_included=quantum_requested,
    )


@dataclass(frozen=True)
class BenchmarkSummary:
    """Aggregate from an externally run benchmark; APEX does not run backends."""

    problem_fingerprint: str
    constraints_fingerprint: str
    backend: str
    mean_runtime_ms: float
    mean_objective_value: float
    sample_count: int

    def __post_init__(self) -> None:
        supported_backends = {
            "classical", "quantum_simulator", "quantum_hardware", "quantum_inspired"
        }
        if self.backend not in supported_backends:
            raise APEXInputError("unsupported benchmark backend label")
        if not self.problem_fingerprint or not self.constraints_fingerprint:
            raise APEXInputError("problem and constraints fingerprints are required")
        if not math.isfinite(self.mean_runtime_ms) or self.mean_runtime_ms <= 0:
            raise APEXInputError("mean_runtime_ms must be a finite positive number")
        if not math.isfinite(self.mean_objective_value):
            raise APEXInputError("mean_objective_value must be finite")
        if self.sample_count < 1:
            raise APEXInputError("sample_count must be at least 1")


def compare_benchmarks(
    candidate: BenchmarkSummary, baseline: BenchmarkSummary
) -> dict[str, object]:
    """Report candidate signals without ever asserting quantum advantage.

    Lower runtime and lower objective value are treated as better for this generic
    screening rubric. Real workloads must document their actual objective function.
    """
    if baseline.backend != "classical":
        raise APEXInputError("baseline backend must be classical")
    if candidate.backend == "classical":
        raise APEXInputError("candidate backend must not be classical")
    if (
        candidate.problem_fingerprint != baseline.problem_fingerprint
        or candidate.constraints_fingerprint != baseline.constraints_fingerprint
    ):
        status = "not_comparable"
        rationale = "Problem and constraints fingerprints must match exactly."
    elif min(candidate.sample_count, baseline.sample_count) < 30:
        status = "insufficient_repetitions"
        rationale = "At least 30 samples per backend are required for preliminary screening."
    elif (
        candidate.mean_runtime_ms < baseline.mean_runtime_ms
        and candidate.mean_objective_value <= baseline.mean_objective_value
    ):
        status = "candidate_improvement_requires_independent_review"
        rationale = (
            "Aggregate metrics favor the candidate; variation, hardware costs, reproducibility "
            "and independent review are still required."
        )
    else:
        status = "no_candidate_improvement_detected"
        rationale = "The supplied aggregate metrics do not favor the candidate on both measures."

    return {
        "status": status,
        "rationale": rationale,
        "candidate_backend": candidate.backend,
        "baseline_backend": baseline.backend,
        "quantum_advantage_claimed": False,
        "permitted_claim": "No quantum advantage demonstrated by this screening result.",
    }
