"""ClearGlassInc Artemis reference implementation skeleton.

This module is intentionally dependency-light so the architecture can be reviewed,
versioned, evaluated, and promoted through Apollo-style deployment rings before
it is wired to production Palantir Gotham, Foundry, AIP, and Apollo services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from math import exp, isfinite
from statistics import fmean, pstdev
from typing import Any, Literal
from uuid import uuid4

Classification = Literal["UNCLASS", "CUI", "SECRET", "TOP_SECRET"]
Decision = Literal["approve", "reject", "revise"]


class ApprovalGate(str, Enum):
    READ_ONLY = "read_only"
    CASE_WRITEBACK = "case_writeback"
    OPERATIONAL_EFFECT = "operational_effect"
    MODEL_OR_PROMPT_CHANGE = "model_or_prompt_change"


@dataclass(frozen=True)
class LineageRef:
    source_system: str
    dataset_rid: str
    transform_version: str
    observed_at: datetime
    checksum: str

    @classmethod
    def from_payload(
        cls,
        source_system: str,
        dataset_rid: str,
        transform_version: str,
        payload: dict[str, Any],
    ) -> "LineageRef":
        digest = sha256(repr(sorted(payload.items())).encode("utf-8")).hexdigest()
        return cls(
            source_system,
            dataset_rid,
            transform_version,
            datetime.now(timezone.utc),
            digest,
        )


@dataclass
class OntologyObject:
    object_id: str
    object_type: str
    classification: Classification
    compartments: set[str]
    coalition_releasability: set[str]
    confidence: float
    valid_from: datetime
    valid_to: datetime | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    lineage: list[LineageRef] = field(default_factory=list)


@dataclass
class MissionContext:
    mission_id: str
    objective: str
    commander_intent: str
    allowed_actions: set[str]
    prohibited_actions: set[str]
    latency_budget_ms: int
    compartments: set[str]


@dataclass
class AgentAction:
    action_id: str
    agent_name: str
    gate: ApprovalGate
    tool_name: str
    arguments: dict[str, Any]
    rationale: str
    confidence: float
    policy_labels: set[str]


@dataclass
class OperatorFeedback:
    feedback_id: str
    mission_id: str
    action_id: str
    decision: Decision
    correction: str
    outcome_score: float
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class EnvironmentalCyberRiskSignal:
    """Enterprise-facing space-weather feature vector for Phase 1 risk mapping.

    log_nm_f2 follows the ClearGlassInc Artemis launch thresholds:
    GREEN < 5.4, YELLOW 5.4..5.8, RED > 5.8. Additional features raise
    confidence and recommended mitigations without overriding the audited band.
    """

    signal_id: str
    site_id: str
    log_nm_f2: float
    kp_index: float
    scintillation_s4: float
    hf_absorption_db: float
    gnss_error_m: float
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class EnvironmentalCyberRiskAssessment:
    signal_id: str
    band: Literal["GREEN", "YELLOW", "RED"]
    score: float
    affected_services: tuple[str, ...]
    mitigation_playbook: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class IonosphereSample:
    """Precision feature vector for radio-propagation and space-weather triage."""

    total_electron_content_tecu: float
    fof2_mhz: float
    scintillation_s4: float
    kp_index: float
    frequency_mhz: float
    path_length_km: float


@dataclass
class IonosphericObservation:
    """Research observation for space-weather and radio-propagation studies."""

    observation_id: str
    station_id: str
    fo_f2_mhz: float | None
    tec_units: float | None
    scintillation_s4: float | None
    kp_index: float | None
    solar_flux_f107: float | None
    affected_systems: set[Literal["HF_COMMS", "OTH_RADAR", "GNSS_NAV", "TIMING"]]
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    classification: Classification = "UNCLASS"
    compartments: set[str] = field(default_factory=lambda: {"IONO_RESEARCH"})
    coalition_releasability: set[str] = field(default_factory=lambda: {"OPEN_RESEARCH"})
    confidence: float = 0.85

    def to_ontology_object(self) -> OntologyObject:
        payload = {
            "observation_id": self.observation_id,
            "station_id": self.station_id,
            "fo_f2_mhz": self.fo_f2_mhz,
            "tec_units": self.tec_units,
            "scintillation_s4": self.scintillation_s4,
            "kp_index": self.kp_index,
            "solar_flux_f107": self.solar_flux_f107,
            "affected_systems": sorted(self.affected_systems),
        }
        return OntologyObject(
            object_id=self.observation_id,
            object_type="IONOSPHERIC_OBSERVATION",
            classification=self.classification,
            compartments=self.compartments,
            coalition_releasability=self.coalition_releasability,
            confidence=self.confidence,
            valid_from=self.observed_at,
            attributes=payload,
            lineage=[
                LineageRef.from_payload(
                    source_system="ionosphere_research_feed",
                    dataset_rid="foundry.dataset.ionosphere.observations",
                    transform_version="iono-normalizer.v1",
                    payload=payload,
                )
            ],
        )


RiskBand = Literal["GREEN", "YELLOW", "RED"]


def environmental_risk_band(log_nf2: float) -> RiskBand:
    """Map the approved Phase 1 log N_F2 thresholds to alert bands."""

    if not isfinite(log_nf2):
        raise ValueError("log_nf2 must be finite")
    if log_nf2 < 5.4:
        return "GREEN"
    if log_nf2 <= 5.8:
        return "YELLOW"
    return "RED"


def environmental_risk_score(signal: EnvironmentalCyberRiskSignal) -> float:
    """Return a 0..10 auditable Environmental Cyber-Risk score.

    The score preserves the launch threshold band as the dominant factor, then
    adds bounded pressure from geomagnetic activity, scintillation, HF
    absorption, and GNSS error so operators can review each contributing term.
    """

    band_base = {"GREEN": 2.0, "YELLOW": 5.8, "RED": 8.4}[
        environmental_risk_band(signal.log_nm_f2)
    ]
    kp_component = _clamp_probability(signal.kp_index / 9.0) * 0.7
    scintillation_component = _clamp_probability(signal.scintillation_s4) * 0.6
    hf_component = _clamp_probability(signal.hf_absorption_db / 20.0) * 0.3
    gnss_component = _clamp_probability(signal.gnss_error_m / 25.0) * 0.4
    return round(
        min(
            10.0,
            band_base
            + kp_component
            + scintillation_component
            + hf_component
            + gnss_component,
        ),
        2,
    )


@dataclass
class UpgradeProposal:
    proposal_id: str
    target: Literal["prompt", "workflow", "heuristic", "model_route"]
    current_version: str
    candidate_version: str
    diff_summary: str
    eval_metrics: dict[str, float]
    rollback_pointer: str
    requires_gate: ApprovalGate = ApprovalGate.MODEL_OR_PROMPT_CHANGE


class PolicyEngine:
    """Policy-as-code facade for entity, row, column, and action-level checks."""

    def authorize(
        self,
        subject: dict[str, Any],
        obj: OntologyObject | AgentAction,
        mission: MissionContext,
    ) -> bool:
        subject_clearance = subject.get("clearance", "UNCLASS")
        clearance_order = ["UNCLASS", "CUI", "SECRET", "TOP_SECRET"]
        obj_classification = getattr(obj, "classification", "UNCLASS")
        if clearance_order.index(subject_clearance) < clearance_order.index(
            obj_classification
        ):
            return False
        subject_compartments = set(subject.get("compartments", []))
        obj_compartments = getattr(
            obj, "compartments", getattr(obj, "policy_labels", set())
        )
        if not set(obj_compartments).issubset(
            subject_compartments | mission.compartments
        ):
            return False
        if isinstance(obj, AgentAction) and obj.tool_name in mission.prohibited_actions:
            return False
        return True


class ArtemisWorkflow:
    """Machine-speed workflow with explicit human gates for significant effects."""

    def __init__(self, policy: PolicyEngine) -> None:
        self.policy = policy

    def triage_event(
        self, event: OntologyObject, mission: MissionContext, subject: dict[str, Any]
    ) -> AgentAction:
        if not self.policy.authorize(subject, event, mission):
            raise PermissionError("Subject is not authorized for the event context")
        severity = float(event.attributes.get("severity", 0.0))
        action = "open_gotham_case" if severity >= 0.75 else "append_watchlist_note"
        gate = (
            ApprovalGate.CASE_WRITEBACK if severity >= 0.75 else ApprovalGate.READ_ONLY
        )
        return AgentAction(
            action_id=str(uuid4()),
            agent_name="triage_agent.v1",
            gate=gate,
            tool_name=action,
            arguments={"event_id": event.object_id, "mission_id": mission.mission_id},
            rationale=f"Severity {severity:.2f} event linked to mission objective: {mission.objective}",
            confidence=min(0.99, max(0.01, severity)),
            policy_labels=event.compartments,
        )

    def approval_required(self, action: AgentAction) -> bool:
        return action.gate in {
            ApprovalGate.CASE_WRITEBACK,
            ApprovalGate.OPERATIONAL_EFFECT,
            ApprovalGate.MODEL_OR_PROMPT_CHANGE,
        }


class IonosphericResearchWorkflow(ArtemisWorkflow):
    """Domain workflow for ionospheric physics, space weather, and propagation impacts."""

    def triage_ionospheric_observation(
        self,
        observation: IonosphericObservation,
        mission: MissionContext,
        subject: dict[str, Any],
    ) -> AgentAction:
        event = observation.to_ontology_object()
        if not self.policy.authorize(subject, event, mission):
            raise PermissionError(
                "Subject is not authorized for the ionospheric observation"
            )

        propagation_risk = self._propagation_risk(observation)
        if propagation_risk >= 0.80:
            tool_name = "open_gotham_case"
            gate = ApprovalGate.CASE_WRITEBACK
        else:
            tool_name = "publish_research_summary"
            gate = ApprovalGate.READ_ONLY

        rationale = (
            f"Ionospheric propagation risk {propagation_risk:.2f}; "
            f"affected systems={','.join(sorted(observation.affected_systems))}; "
            f"Kp={observation.kp_index}; S4={observation.scintillation_s4}; "
            f"mission objective={mission.objective}"
        )
        return AgentAction(
            action_id=str(uuid4()),
            agent_name="ionosphere_research_agent.v1",
            gate=gate,
            tool_name=tool_name,
            arguments={
                "observation_id": observation.observation_id,
                "station_id": observation.station_id,
                "affected_systems": sorted(observation.affected_systems),
                "risk_score": propagation_risk,
                "mission_id": mission.mission_id,
            },
            rationale=rationale,
            confidence=min(0.99, max(0.01, observation.confidence * propagation_risk)),
            policy_labels=observation.compartments,
        )

    @staticmethod
    def _propagation_risk(observation: IonosphericObservation) -> float:
        kp_component = min((observation.kp_index or 0.0) / 9.0, 1.0)
        scintillation_component = min(observation.scintillation_s4 or 0.0, 1.0)
        tec_component = min((observation.tec_units or 0.0) / 100.0, 1.0)
        system_component = min(len(observation.affected_systems) / 4.0, 1.0)
        return round(
            0.35 * kp_component
            + 0.30 * scintillation_component
            + 0.20 * tec_component
            + 0.15 * system_component,
            4,
        )


class SelfImprovementLoop:
    """Converts feedback and outcomes into safe, evaluated upgrade proposals."""

    def propose_upgrade(
        self, feedback: list[OperatorFeedback], current_version: str
    ) -> UpgradeProposal | None:
        rejected = [f for f in feedback if f.decision in {"reject", "revise"}]
        if len(rejected) < 3:
            return None
        avg_outcome = sum(f.outcome_score for f in feedback) / max(len(feedback), 1)
        candidate_version = f"{current_version}+feedback.{len(feedback)}"
        return UpgradeProposal(
            proposal_id=str(uuid4()),
            target="workflow",
            current_version=current_version,
            candidate_version=candidate_version,
            diff_summary="Add mission schedule and legal-hold checks before operational containment recommendations.",
            eval_metrics={
                "precision": min(0.99, avg_outcome + 0.08),
                "recall": max(0.0, avg_outcome - 0.02),
                "p95_latency_ms": 420.0,
                "operator_trust": min(1.0, avg_outcome + 0.10),
            },
            rollback_pointer=current_version,
        )

    def promotion_decision(self, proposal: UpgradeProposal) -> Decision:
        if (
            proposal.eval_metrics["precision"] >= 0.90
            and proposal.eval_metrics["operator_trust"] >= 0.80
        ):
            return "approve"
        if proposal.eval_metrics["p95_latency_ms"] > 750:
            return "reject"
        return "revise"


def _clamp_probability(value: float) -> float:
    if not isfinite(value):
        raise ValueError("probability feature must be finite")
    return max(0.0, min(1.0, value))


def ionospheric_disruption_score(sample: IonosphereSample) -> float:
    """Return an auditable 0..1 disruption score before ML model routing.

    The deterministic baseline is intentionally simple enough to review in
    classified or coalition environments, while still capturing the main
    propagation stressors used by the Artemis ionospheric research mission pack.
    """

    scintillation_component = _clamp_probability(sample.scintillation_s4)
    geomagnetic_component = _clamp_probability(sample.kp_index / 9.0)
    hf_component = (
        _clamp_probability((10.0 - sample.fof2_mhz) / 10.0)
        if sample.frequency_mhz < 30.0
        else 0.15
    )
    path_component = _clamp_probability(sample.path_length_km / 5000.0)
    linear_score = (
        1.35 * scintillation_component
        + 1.10 * geomagnetic_component
        + 0.85 * hf_component
        + 0.45 * path_component
        - 1.25
    )
    return _clamp_probability(1.0 / (1.0 + exp(-linear_score)))


def environmental_cyber_risk_assessment(
    signal: EnvironmentalCyberRiskSignal,
) -> EnvironmentalCyberRiskAssessment:
    """Map ionospheric conditions to an enterprise mitigation-ready risk band."""

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
        raise ValueError("environmental cyber-risk features must be finite")

    if signal.log_nm_f2 < 5.4:
        band: Literal["GREEN", "YELLOW", "RED"] = "GREEN"
    elif signal.log_nm_f2 <= 5.8:
        band = "YELLOW"
    else:
        band = "RED"

    normalized_pressure = (
        0.36 * _clamp_probability((signal.log_nm_f2 - 5.0) / 1.2)
        + 0.24 * _clamp_probability(signal.kp_index / 9.0)
        + 0.18 * _clamp_probability(signal.scintillation_s4)
        + 0.12 * _clamp_probability(signal.hf_absorption_db / 20.0)
        + 0.10 * _clamp_probability(signal.gnss_error_m / 25.0)
    )

    affected = ["GNSS_NAVIGATION", "PRECISION_TIMING"]
    if signal.hf_absorption_db >= 6.0 or band == "RED":
        affected.append("HF_COMMUNICATIONS")
    if signal.scintillation_s4 >= 0.45 or signal.gnss_error_m >= 8.0:
        affected.append("SURVEYING_AND_LOGISTICS")

    mitigations = [
        "validate GNSS-dependent operations against terrestrial timing or inertial fallback",
        "increase monitoring cadence for affected Burlington/GTA sites",
    ]
    if band in {"YELLOW", "RED"}:
        mitigations.extend(
            [
                "notify operations leads of possible propagation-driven degradation",
                "enable alternate communication paths and frequency-agility procedures",
            ]
        )
    if band == "RED":
        mitigations.append(
            "open a reviewed Gotham case and prepare a client action package before operational changes"
        )

    return EnvironmentalCyberRiskAssessment(
        signal_id=signal.signal_id,
        band=band,
        score=round(_clamp_probability(normalized_pressure), 4),
        affected_services=tuple(affected),
        mitigation_playbook=tuple(mitigations),
        rationale=(
            f"logNmF2={signal.log_nm_f2:.2f} maps to {band}; "
            f"Kp={signal.kp_index:.1f}, S4={signal.scintillation_s4:.2f}, "
            f"HF absorption={signal.hf_absorption_db:.1f} dB, GNSS error={signal.gnss_error_m:.1f} m"
        ),
    )


def drift_zscore(current_window: list[float], baseline_window: list[float]) -> float:
    """Measure drift between live and baseline ionospheric feature windows."""

    if len(current_window) < 5 or len(baseline_window) < 5:
        raise ValueError("drift windows require at least five samples")
    baseline_sigma = pstdev(baseline_window) or 1e-6
    return abs(fmean(current_window) - fmean(baseline_window)) / baseline_sigma


ElectricalDefectSeverity = Literal[
    "immediate_danger",
    "critical_repair",
    "code_correction",
    "reliability_improvement",
    "preventive_maintenance",
    "cosmetic_organization",
    "future_upgrade",
]


@dataclass(frozen=True)
class ElectricalFinding:
    """Evidence-backed electrical-system finding for maintenance planning.

    This object is deliberately documentation-only. It must not be used as an
    instruction to contact, move, terminate, test, or repair exposed energized
    conductors. Physical electrical work remains a licensed-electrician,
    permit-and-inspection workflow with lockout/tagout and verified absence of
    voltage before contact.
    """

    finding_id: str
    asset_id: str
    description: str
    evidence_refs: tuple[str, ...]
    observed_hazards: frozenset[str]
    circuit_status: Literal["unknown", "isolated", "restricted", "restored"] = "unknown"


@dataclass(frozen=True)
class ElectricalWorkOrder:
    work_order_id: str
    finding_id: str
    severity: ElectricalDefectSeverity
    required_controls: tuple[str, ...]
    repair_objective: str
    approval_gates: tuple[str, ...]
    final_report_sections: tuple[str, ...]


_IMMEDIATE_DANGER_HAZARDS = frozenset(
    {
        "arcing",
        "burning_odour",
        "active_overheating",
        "water_intrusion",
        "damaged_service_equipment",
        "exposed_live_parts",
        "evidence_of_fire",
    }
)

_CRITICAL_REPAIR_HAZARDS = frozenset(
    {
        "aluminium_wiring_defect",
        "knob_and_tube_wiring",
        "damaged_insulation",
        "double_tapped_breaker",
        "overheated_conductor",
        "open_neutral",
        "improper_grounding",
        "unapproved_modification",
        "bootleg_ground",
        "neutral_ground_fault",
    }
)

_REQUIRED_ELECTRICAL_CONTROLS = (
    "qualified licensed electrician",
    "required AHJ permits and inspections",
    "de-energize before physical contact",
    "lockout/tagout",
    "approved meter live-dead-live absence-of-voltage verification",
    "appropriate PPE, insulated tools, barriers, and safe approach distances",
    "re-energize only after covers, guards, protective devices, testing, and approvals are restored",
)

_FINAL_ELECTRICAL_REPORT_SECTIONS = (
    "Immediate hazards",
    "Circuits that must remain isolated",
    "Existing system condition",
    "Defects found",
    "Root causes",
    "Repairs required",
    "Materials required",
    "Technology upgrades recommended",
    "Applicable permit and inspection requirements",
    "Testing performed",
    "Exact test results",
    "Circuits safely restored",
    "Circuits still restricted",
    "Final code-compliance status",
    "Remaining owner actions",
    "Preventive-maintenance schedule",
)


def classify_electrical_finding(finding: ElectricalFinding) -> ElectricalDefectSeverity:
    """Risk-rank a finding without guessing conductor identity or code status."""

    if finding.observed_hazards & _IMMEDIATE_DANGER_HAZARDS:
        return "immediate_danger"
    if finding.observed_hazards & _CRITICAL_REPAIR_HAZARDS:
        return "critical_repair"
    if (
        "missing_label" in finding.observed_hazards
        or "incorrect_panel_directory" in finding.observed_hazards
    ):
        return "code_correction"
    if (
        "unsupported_cable" in finding.observed_hazards
        or "missing_cover" in finding.observed_hazards
    ):
        return "reliability_improvement"
    if "obsolete_monitoring" in finding.observed_hazards:
        return "future_upgrade"
    return "preventive_maintenance"


def build_electrical_work_order(finding: ElectricalFinding) -> ElectricalWorkOrder:
    """Create an audit-ready electrical remediation workflow for Artemis."""

    severity = classify_electrical_finding(finding)
    if severity == "immediate_danger":
        objective = "isolate the affected circuit/equipment and stop work until qualified evaluation approves the next step"
    elif severity == "critical_repair":
        objective = "trace, document, repair root cause, test, inspect, and restore only when safe"
    else:
        objective = "schedule documentation, correction, verification, and preventive maintenance without bypassing safety controls"

    return ElectricalWorkOrder(
        work_order_id=f"ewo-{finding.finding_id}",
        finding_id=finding.finding_id,
        severity=severity,
        required_controls=_REQUIRED_ELECTRICAL_CONTROLS,
        repair_objective=objective,
        approval_gates=(
            "licensed_electrician_acceptance",
            "permit_or_AHJ_requirement_review",
            "pre_energization_test_record",
            "owner_or_operator_restore_authorization",
        ),
        final_report_sections=_FINAL_ELECTRICAL_REPORT_SECTIONS,
    )


PostQuantumAlgorithm = Literal[
    "RSA", "ECC", "DH", "DSA", "ML-KEM", "ML-DSA", "SLH-DSA", "AES"
]
MigrationUrgency = Literal["inventory", "plan", "migrate", "monitor"]


@dataclass(frozen=True)
class CryptographicAsset:
    """Ontology-ready cryptographic dependency for PQC readiness scoring."""

    asset_id: str
    owner: str
    algorithm: PostQuantumAlgorithm
    key_size_bits: int
    protocol: str
    data_classification: Classification
    stores_long_lived_secrets: bool
    external_exposure: bool
    business_criticality: float
    certificate_expires_at: datetime | None = None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PostQuantumFinding:
    asset_id: str
    urgency: MigrationUrgency
    risk_score: float
    recommended_target: str
    rationale: str
    evidence_sources: tuple[str, ...]
    confidence_drivers: tuple[str, ...]
    approval_gate: ApprovalGate = ApprovalGate.CASE_WRITEBACK


def post_quantum_readiness_score(asset: CryptographicAsset) -> float:
    """Return an auditable 0..1 score for harvest-now/decrypt-later exposure.

    The baseline is intentionally deterministic for high-assurance review: legacy
    public-key cryptography, long-lived protected data, external reachability, and
    business criticality dominate the score. NIST-standardized PQC algorithms are
    treated as monitoring items rather than migration blockers.
    """

    legacy_public_key = asset.algorithm in {"RSA", "ECC", "DH", "DSA"}
    standardized_pqc = asset.algorithm in {"ML-KEM", "ML-DSA", "SLH-DSA"}
    if standardized_pqc:
        return round(0.15 + 0.10 * _clamp_probability(asset.business_criticality), 4)

    algorithm_component = 0.45 if legacy_public_key else 0.12
    secret_lifetime_component = 0.22 if asset.stores_long_lived_secrets else 0.06
    exposure_component = 0.18 if asset.external_exposure else 0.05
    criticality_component = 0.15 * _clamp_probability(asset.business_criticality)
    weak_key_component = (
        0.08 if asset.algorithm == "RSA" and asset.key_size_bits < 3072 else 0.0
    )
    return round(
        _clamp_probability(
            algorithm_component
            + secret_lifetime_component
            + exposure_component
            + criticality_component
            + weak_key_component
        ),
        4,
    )


def advise_post_quantum_migration(asset: CryptographicAsset) -> PostQuantumFinding:
    """Create a human-reviewable PQC remediation recommendation."""

    score = post_quantum_readiness_score(asset)
    if asset.algorithm in {"ML-KEM", "ML-DSA", "SLH-DSA"}:
        urgency: MigrationUrgency = "monitor"
        target = (
            "maintain NIST PQC implementation, patch cadence, and crypto-agility tests"
        )
    elif score >= 0.78:
        urgency = "migrate"
        target = (
            "prioritize hybrid TLS/PKI pilot and migration to ML-KEM/ML-DSA profiles"
        )
    elif score >= 0.55:
        urgency = "plan"
        target = "create migration backlog, dependency owners, and certificate rotation windows"
    else:
        urgency = "inventory"
        target = "complete crypto inventory and monitor standards/vendor support"

    drivers = [
        f"algorithm={asset.algorithm}",
        f"external_exposure={asset.external_exposure}",
        f"long_lived_secrets={asset.stores_long_lived_secrets}",
        f"criticality={asset.business_criticality:.2f}",
    ]
    return PostQuantumFinding(
        asset_id=asset.asset_id,
        urgency=urgency,
        risk_score=score,
        recommended_target=target,
        rationale=(
            f"{asset.protocol} dependency uses {asset.algorithm}-{asset.key_size_bits}; "
            f"PQC readiness score {score:.2f} maps to {urgency}."
        ),
        evidence_sources=asset.evidence_refs,
        confidence_drivers=tuple(drivers),
    )


MetricName = Literal[
    "precision",
    "recall",
    "citation_accuracy",
    "policy_violation_rate",
    "operator_trust",
    "p95_latency_ms",
]


@dataclass(frozen=True)
class EvaluationResult:
    """Auditable scorecard for a candidate prompt, workflow, or route."""

    candidate_version: str
    baseline_version: str
    metrics: dict[MetricName, float]
    sample_count: int
    drift_zscore: float
    policy_bundle_version: str
    passed: bool
    failure_reasons: tuple[str, ...]


@dataclass(frozen=True)
class SelfUpgradeGuardrails:
    """Human-approved bounds that self-improvement proposals cannot relax."""

    min_precision: float = 0.92
    min_recall: float = 0.85
    min_citation_accuracy: float = 0.98
    max_policy_violation_rate: float = 0.0
    min_operator_trust: float = 0.80
    max_p95_latency_ms: float = 2500.0
    max_drift_zscore: float = 3.0
    min_eval_samples: int = 30


class PrecisionEvaluationHarness:
    """Deterministic promotion gate for Artemis self-evolving artifacts.

    AIP may generate candidates, but this harness decides whether a proposal is
    eligible for human review. It never changes objectives, widens access, lowers
    approval gates, or promotes artifacts by itself.
    """

    def __init__(self, guardrails: SelfUpgradeGuardrails | None = None) -> None:
        self.guardrails = guardrails or SelfUpgradeGuardrails()

    def evaluate_candidate(
        self,
        candidate_version: str,
        baseline_version: str,
        metrics: dict[MetricName, float],
        sample_count: int,
        live_window: list[float],
        baseline_window: list[float],
        policy_bundle_version: str,
    ) -> EvaluationResult:
        failures: list[str] = []
        zscore = drift_zscore(live_window, baseline_window)

        checks = {
            "precision below guardrail": metrics.get("precision", 0.0)
            >= self.guardrails.min_precision,
            "recall below guardrail": metrics.get("recall", 0.0)
            >= self.guardrails.min_recall,
            "citation accuracy below guardrail": metrics.get("citation_accuracy", 0.0)
            >= self.guardrails.min_citation_accuracy,
            "policy violation rate above guardrail": metrics.get(
                "policy_violation_rate", 1.0
            )
            <= self.guardrails.max_policy_violation_rate,
            "operator trust below guardrail": metrics.get("operator_trust", 0.0)
            >= self.guardrails.min_operator_trust,
            "p95 latency above guardrail": metrics.get("p95_latency_ms", float("inf"))
            <= self.guardrails.max_p95_latency_ms,
            "drift above guardrail": zscore <= self.guardrails.max_drift_zscore,
            "insufficient eval samples": sample_count
            >= self.guardrails.min_eval_samples,
        }
        failures.extend(reason for reason, ok in checks.items() if not ok)
        return EvaluationResult(
            candidate_version=candidate_version,
            baseline_version=baseline_version,
            metrics=metrics,
            sample_count=sample_count,
            drift_zscore=round(zscore, 4),
            policy_bundle_version=policy_bundle_version,
            passed=not failures,
            failure_reasons=tuple(failures),
        )


def build_apollo_promotion_manifest(
    proposal: UpgradeProposal,
    evaluation: EvaluationResult,
    approver_id: str,
) -> dict[str, Any]:
    """Create a signed-artifact-ready manifest for Apollo progressive delivery."""

    if not evaluation.passed:
        raise ValueError("candidate failed evaluation and cannot be promoted")
    if proposal.candidate_version != evaluation.candidate_version:
        raise ValueError("proposal and evaluation candidate versions do not match")
    manifest = {
        "artifact": proposal.target,
        "candidate_version": proposal.candidate_version,
        "rollback_version": proposal.rollback_pointer,
        "baseline_version": evaluation.baseline_version,
        "policy_bundle_version": evaluation.policy_bundle_version,
        "approval_gate": proposal.requires_gate.value,
        "approver_id": approver_id,
        "canary_rings": ["lab", "mission-shadow", "limited-operators", "production"],
        "stop_promotion_on": [
            "policy_violation_rate > 0",
            "citation_accuracy < 0.98",
            "precision < 0.92",
            "p95_latency_ms > 2500",
            "operator_trust < 0.80",
        ],
    }
    manifest["manifest_hash"] = sha256(
        repr(sorted(manifest.items())).encode("utf-8")
    ).hexdigest()
    return manifest
