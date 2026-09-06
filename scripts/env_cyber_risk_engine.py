"""ClearGlassInc Artemis Environmental Cyber-Risk scoring engine.

Reference Python module for Phase 1 Environmental Threat Vector Mapping.
It converts ionospheric log N_F2, D-region density, Kp, X-ray flux,
GNSS scintillation, and operational dependency context into governed
GREEN/YELLOW/RED alert states for enterprise infrastructure workflows.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Iterable, Literal

Alert = Literal["GREEN", "YELLOW", "RED"]


class ThreatVector(str, Enum):
    GNSS_SCINTILLATION = "GNSS scintillation"
    HF_ABSORPTION = "HF absorption"
    OTHR_DEFLECTION = "OTHR deflection"
    TIMING_DRIFT = "precision timing drift"


@dataclass(frozen=True)
class SpaceWeatherObservation:
    source: str
    observed_at: datetime
    log_nf2: float
    kp_index: float
    xray_flux_w_m2: float
    d_region_density: float
    s4_scintillation: float
    location: str = "Burlington/GTA"

    def lineage_hash(self) -> str:
        payload = "|".join(str(v) for v in asdict(self).values())
        return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ClientExposure:
    organization: str
    sector: str
    gnss_dependency: float
    hf_dependency: float
    timing_dependency: float
    redundancy_score: float


@dataclass(frozen=True)
class EnvironmentalCyberRiskScore:
    alert: Alert
    score_0_10: float
    primary_vectors: tuple[ThreatVector, ...]
    recommended_actions: tuple[str, ...]
    confidence: float
    lineage_hash: str
    generated_at: datetime


def threshold_from_log_nf2(log_nf2: float) -> Alert:
    """Phase 1 thresholds: GREEN <5.4, YELLOW 5.4-5.8, RED >5.8."""
    if log_nf2 > 5.8:
        return "RED"
    if log_nf2 >= 5.4:
        return "YELLOW"
    return "GREEN"


def score_observation(obs: SpaceWeatherObservation, exposure: ClientExposure) -> EnvironmentalCyberRiskScore:
    base = min(10.0, max(0.0, (obs.log_nf2 - 5.0) * 4.0))
    space_weather_pressure = min(3.0, obs.kp_index / 3.0 + obs.s4_scintillation * 2.0 + obs.d_region_density * 1.2)
    dependency = (exposure.gnss_dependency * 0.4) + (exposure.hf_dependency * 0.25) + (exposure.timing_dependency * 0.35)
    mitigated = max(0.0, 1.0 - exposure.redundancy_score)
    score = round(min(10.0, base + space_weather_pressure + dependency * mitigated * 3.0), 2)

    threshold_alert = threshold_from_log_nf2(obs.log_nf2)
    score_alert: Alert = "RED" if score >= 7.5 else "YELLOW" if score >= 4.0 else "GREEN"
    alert = "RED" if "RED" in (threshold_alert, score_alert) else "YELLOW" if "YELLOW" in (threshold_alert, score_alert) else "GREEN"

    vectors: list[ThreatVector] = []
    if obs.s4_scintillation >= 0.35 or exposure.gnss_dependency >= 0.6:
        vectors.append(ThreatVector.GNSS_SCINTILLATION)
    if obs.d_region_density >= 0.45 or exposure.hf_dependency >= 0.45:
        vectors.append(ThreatVector.HF_ABSORPTION)
    if obs.kp_index >= 5:
        vectors.append(ThreatVector.OTHR_DEFLECTION)
    if exposure.timing_dependency >= 0.55:
        vectors.append(ThreatVector.TIMING_DRIFT)

    actions = {
        "GREEN": ("Continue monitoring public CSA/NOAA feeds.", "Keep GNSS/HF fallback readiness at normal posture."),
        "YELLOW": ("Validate GNSS accuracy against terrestrial references.", "Pre-stage alternate communications and frequency agility plans."),
        "RED": ("Activate GNSS fallback and timing holdover procedures.", "Notify operations leaders and verify redundant communications paths."),
    }[alert]

    return EnvironmentalCyberRiskScore(
        alert=alert,
        score_0_10=score,
        primary_vectors=tuple(vectors),
        recommended_actions=actions,
        confidence=0.78 if obs.source.lower().startswith(("noaa", "csa")) else 0.62,
        lineage_hash=obs.lineage_hash(),
        generated_at=datetime.now(timezone.utc),
    )


def batch_score(observations: Iterable[SpaceWeatherObservation], exposure: ClientExposure) -> list[EnvironmentalCyberRiskScore]:
    return [score_observation(obs, exposure) for obs in observations]


if __name__ == "__main__":
    sample_obs = SpaceWeatherObservation(
        source="NOAA SWPC / CSA public-feed placeholder",
        observed_at=datetime.now(timezone.utc),
        log_nf2=5.72,
        kp_index=4.7,
        xray_flux_w_m2=1.4e-5,
        d_region_density=0.51,
        s4_scintillation=0.42,
    )
    sample_client = ClientExposure(
        organization="Burlington Logistics Pilot",
        sector="logistics",
        gnss_dependency=0.82,
        hf_dependency=0.2,
        timing_dependency=0.58,
        redundancy_score=0.35,
    )
    print(score_observation(sample_obs, sample_client))
