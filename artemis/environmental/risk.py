"""Deterministic Environmental Cyber-Risk scoring primitives.

These functions intentionally avoid network calls so the Phase 1 dashboard and
AIP tools can be tested, replayed, and audited from the same threshold contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

RiskBand = Literal["GREEN", "YELLOW", "RED"]


@dataclass(frozen=True)
class EnvironmentalObservation:
    """Normalized ionospheric state sample used by Artemis Phase 1."""

    log_nf2: float
    kp_index: float = 4.0
    solar_wind_kms: float = 432.0
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "simulated-public-feed"


@dataclass(frozen=True)
class ThreatVector:
    """Human-readable threat vector row for dashboard and brief generation."""

    vector: str
    threat_level: str
    impact: str
    mitigation: str


def classify_log_nf2(log_nf2: float) -> tuple[RiskBand, str]:
    """Classify log N_F2 using the auditable Phase 1 threshold contract."""

    if log_nf2 < 5.4:
        return "GREEN", "Normal environmental cyber-risk posture"
    if log_nf2 <= 5.8:
        return "YELLOW", "Elevated propagation uncertainty; monitor GNSS/HF dependencies"
    return "RED", "High environmental cyber-risk; prepare mitigations and client notification"


def build_threat_vectors(band: RiskBand) -> list[ThreatVector]:
    """Return operational threat vectors calibrated by the current risk band."""

    if band == "GREEN":
        gnss, hf, othr = "LOW", "LOW", "LOW-MODERATE"
    elif band == "YELLOW":
        gnss, hf, othr = "HIGH", "MODERATE-HIGH", "HIGH"
    else:
        gnss, hf, othr = "SEVERE", "HIGH", "SEVERE"

    return [
        ThreatVector(
            "GNSS/GPS",
            gnss,
            "Positioning drift, timing instability, and survey-quality degradation",
            "Validate fixes against control points; keep inertial/manual fallbacks ready",
        ),
        ThreatVector(
            "HF Radio",
            hf,
            "Reduced usable frequencies and intermittent link reliability",
            "Use frequency agility, alternate bands, and secondary comms paths",
        ),
        ThreatVector(
            "OTHR Radar",
            othr,
            "Propagation deflection and reduced track-quality confidence",
            "Cross-check with alternate sensors and defer non-urgent conclusions",
        ),
    ]


def dashboard_snapshot(observation: EnvironmentalObservation) -> dict[str, object]:
    """Build the serializable payload consumed by Streamlit, APIs, and tests."""

    band, rationale = classify_log_nf2(observation.log_nf2)
    return {
        "band": band,
        "status": f"{band} - {rationale}",
        "rationale": rationale,
        "observation": observation,
        "threat_vectors": build_threat_vectors(band),
    }
