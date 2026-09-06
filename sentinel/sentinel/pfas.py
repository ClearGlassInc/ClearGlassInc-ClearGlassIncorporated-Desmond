"""PERCIVAL · PFAS — compliance + decision intelligence agent (Ontario).

Defensive, evidence-based intelligence for water/property/infrastructure PFAS
risk. Implements the narrow Phase-One workflow described in the operator brief:

    upload report -> detect PFAS -> score risk -> generate compliance package
                  -> recommend next action

Anchored to Health Canada's interim drinking-water objective:
  * Sum of 25 listed PFAS  ≤  30 ng/L                    (30 = exceedance)
  * Detected PFAS analytes individually carry an LOQ floor; analytes <LOQ
    are NOT summed (operator-conservative: report range when applicable).

This module does NOT identify private individuals; it operates on samples,
sites, and assets only. Fail-closed: any missing authorization/scope/owner
returns a denied compliance package with reasons.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

# Health Canada interim drinking-water objective for the sum of 25 PFAS (ng/L).
# Source: Health Canada (May 2024) interim objective. The list below is the
# 25 analytes used to compute the sum; analyte spelling is normalized.
HC_25_PFAS_NGL = 30.0

HC_25_PFAS = frozenset({
    "PFBA", "PFPeA", "PFHxA", "PFHpA", "PFOA", "PFNA", "PFDA", "PFUnDA",
    "PFDoDA", "PFTrDA", "PFTeDA",
    "PFBS", "PFPeS", "PFHxS", "PFHpS", "PFOS", "PFNS", "PFDS",
    "4:2 FTS", "6:2 FTS", "8:2 FTS",
    "PFOSA", "N-MeFOSAA", "N-EtFOSAA", "HFPO-DA",
})

# Likely source categories — informational only. Used to bucket findings for
# downstream source-tracing work; never used to accuse a party.
SOURCE_CATEGORIES = (
    "AFFF / fire-training site",
    "Industrial coatings / textile",
    "Plating / metal finishing",
    "Landfill / leachate",
    "Wastewater / biosolids",
    "Airport / military legacy",
    "Unknown / mixed urban",
)


class Risk(str, Enum):
    LOW = "LOW"                  # all detected < HC objective and < 0.5x
    ELEVATED = "ELEVATED"        # >= 0.5x objective, below objective
    EXCEEDANCE = "EXCEEDANCE"    # >= objective
    INSUFFICIENT = "INSUFFICIENT"  # missing/invalid data — fail-closed


class PFASError(Exception):
    """Raised when a screening request is missing mandatory authorization/scope."""


@dataclass(frozen=True)
class AnalyteResult:
    """One analyte from a lab report (ng/L). ``loq`` is the lab limit of
    quantitation. ``below_loq=True`` means the analyte was not quantified."""

    analyte: str
    value_ngL: float
    loq_ngL: float = 0.0
    below_loq: bool = False
    units: str = "ng/L"


@dataclass(frozen=True)
class Sample:
    sample_id: str
    site_id: str
    collected_utc: str           # ISO 8601 (UTC)
    matrix: str = "drinking_water"   # drinking_water | groundwater | surface | wastewater
    results: tuple[AnalyteResult, ...] = ()
    lab: str = ""
    method: str = ""


@dataclass(frozen=True)
class ScreeningRequest:
    """Mandatory scope context — fail-closed if any field missing."""

    client_id: str
    site_owner_ref: str          # documented owner / authorization to test
    jurisdiction: str            # e.g. "ON, CA"
    purpose: str                 # e.g. "annual compliance screening"
    requester_role: str


@dataclass
class Finding:
    sum_25_ngL: float
    sum_25_ngL_max: float        # upper bound treating <LOQ as = LOQ
    risk: Risk
    detected_analytes: list[str]
    exceedance_ratio: float
    matrix: str
    source_category_hints: list[str] = field(default_factory=list)


@dataclass
class CompliancePackage:
    accepted: bool
    reasons: tuple[str, ...]
    sample_id: Optional[str]
    finding: Optional[Finding]
    next_actions: list[str] = field(default_factory=list)
    resample_after_days: Optional[int] = None
    treatment_options: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    audit_ref: str = ""
    generated_utc: str = ""

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "reasons": list(self.reasons),
            "sample_id": self.sample_id,
            "finding": None if not self.finding else {
                "sum_25_ngL": round(self.finding.sum_25_ngL, 2),
                "sum_25_ngL_max": round(self.finding.sum_25_ngL_max, 2),
                "risk": self.finding.risk.value,
                "detected_analytes": list(self.finding.detected_analytes),
                "exceedance_ratio": round(self.finding.exceedance_ratio, 2),
                "matrix": self.finding.matrix,
                "source_category_hints": list(self.finding.source_category_hints),
            },
            "next_actions": list(self.next_actions),
            "resample_after_days": self.resample_after_days,
            "treatment_options": list(self.treatment_options),
            "references": list(self.references),
            "audit_ref": self.audit_ref,
            "generated_utc": self.generated_utc,
        }


_HC_REF = ("Health Canada — Objective for Canadian drinking water: per- and "
           "polyfluoroalkyl substances (PFAS), interim objective 30 ng/L "
           "(sum of 25 PFAS).")
_MECP_REF = "Ontario MECP — Drinking Water Quality Standards (PFAS where applicable)."


def _normalize_analyte(name: str) -> str:
    n = (name or "").strip().upper().replace("FTSA", "FTS").replace(" ", " ")
    # accept common spellings/synonyms -> canonical form used in HC_25_PFAS
    alias = {
        "PFOA": "PFOA", "PFOS": "PFOS", "PFHXS": "PFHxS", "PFHXA": "PFHxA",
        "PFHPA": "PFHpA", "PFHPS": "PFHpS", "PFPEA": "PFPeA", "PFPES": "PFPeS",
        "PFNS": "PFNS", "PFNA": "PFNA", "PFBS": "PFBS", "PFBA": "PFBA",
        "PFDA": "PFDA", "PFDS": "PFDS", "PFUNDA": "PFUnDA", "PFDODA": "PFDoDA",
        "PFTRDA": "PFTrDA", "PFTEDA": "PFTeDA", "HFPO-DA": "HFPO-DA",
        "GENX": "HFPO-DA", "PFOSA": "PFOSA",
        "N-MEFOSAA": "N-MeFOSAA", "N-ETFOSAA": "N-EtFOSAA",
        "4:2 FTS": "4:2 FTS", "6:2 FTS": "6:2 FTS", "8:2 FTS": "8:2 FTS",
    }
    return alias.get(n, name.strip())


def _audit_ref(req: ScreeningRequest, sample: Optional[Sample]) -> str:
    base = f"{req.client_id}|{req.site_owner_ref}|{sample.sample_id if sample else 'no-sample'}|{datetime.now(timezone.utc).isoformat()}"
    return "PFAS-" + hex(abs(hash(base)) & 0xFFFFFFFFFF).upper().lstrip("0X").zfill(10)


def _source_hints(matrix: str, detected: list[str]) -> list[str]:
    hints: list[str] = []
    if any(a.startswith(("4:2", "6:2", "8:2")) or a == "PFHxS" for a in detected):
        hints.append("AFFF / fire-training site")
    if "PFOS" in detected or "PFOA" in detected:
        hints.append("Industrial coatings / textile")
    if matrix in ("groundwater", "surface"):
        hints.append("Landfill / leachate")
    if matrix == "wastewater":
        hints.append("Wastewater / biosolids")
    return hints or ["Unknown / mixed urban"]


def _treatment_options(risk: Risk) -> list[str]:
    if risk is Risk.LOW:
        return []
    if risk is Risk.ELEVATED:
        return [
            "Increase monitoring frequency to monthly",
            "Pre-design study: GAC vs ion-exchange screening",
        ]
    # EXCEEDANCE
    return [
        "Granular activated carbon (GAC) — proven for long-chain PFAS",
        "Ion exchange (selective) — strong for short-chain + PFOS/PFOA",
        "Reverse osmosis — high removal, residual management required",
        "Source isolation + connect to alternate supply (interim)",
    ]


def screen(request: ScreeningRequest, sample: Sample) -> CompliancePackage:
    """Run the full Phase-One PFAS screening workflow on a single sample."""
    now = datetime.now(timezone.utc).isoformat()

    # Fail-closed scope checks
    missing = [k for k in ("client_id", "site_owner_ref", "jurisdiction", "purpose", "requester_role")
               if not (getattr(request, k) or "").strip()]
    if missing:
        return CompliancePackage(
            accepted=False,
            reasons=(f"missing scope field(s): {', '.join(missing)}",),
            sample_id=getattr(sample, "sample_id", None),
            finding=None,
            audit_ref="PFAS-DENIED",
            generated_utc=now,
            references=[_HC_REF, _MECP_REF],
        )
    if not sample.results:
        return CompliancePackage(
            accepted=False,
            reasons=("sample has no analyte results",),
            sample_id=sample.sample_id,
            finding=Finding(0.0, 0.0, Risk.INSUFFICIENT, [], 0.0, sample.matrix),
            audit_ref=_audit_ref(request, sample),
            generated_utc=now,
            references=[_HC_REF, _MECP_REF],
        )

    # Sum-of-25 (LOQ-aware). Lower bound: <LOQ = 0. Upper bound: <LOQ = LOQ.
    sum_lo = 0.0
    sum_hi = 0.0
    detected: list[str] = []
    for r in sample.results:
        canon = _normalize_analyte(r.analyte)
        if canon not in HC_25_PFAS:
            continue
        if r.below_loq:
            sum_hi += max(r.loq_ngL, 0.0)
            continue
        sum_lo += max(r.value_ngL, 0.0)
        sum_hi += max(r.value_ngL, 0.0)
        if r.value_ngL > 0:
            detected.append(canon)

    if sum_hi >= HC_25_PFAS_NGL:
        risk = Risk.EXCEEDANCE
    elif sum_hi >= 0.5 * HC_25_PFAS_NGL:
        risk = Risk.ELEVATED
    else:
        risk = Risk.LOW

    finding = Finding(
        sum_25_ngL=sum_lo,
        sum_25_ngL_max=sum_hi,
        risk=risk,
        detected_analytes=detected,
        exceedance_ratio=sum_hi / HC_25_PFAS_NGL,
        matrix=sample.matrix,
        source_category_hints=_source_hints(sample.matrix, detected),
    )

    next_actions: list[str] = []
    if risk is Risk.EXCEEDANCE:
        next_actions += [
            "Notify utility / property owner and document chain of custody",
            "Open compliance ticket: HC interim objective exceedance",
            "Initiate source characterization (sampling plan + receptor map)",
            "Evaluate treatment options and capital-planning brief",
        ]
        resample = 7
    elif risk is Risk.ELEVATED:
        next_actions += [
            "Increase monitoring frequency (monthly)",
            "Pre-design study: treatment screening (GAC / IEX)",
            "Notify operator + draft watch-status report",
        ]
        resample = 30
    else:
        next_actions += ["Maintain annual screening cadence"]
        resample = 365

    return CompliancePackage(
        accepted=True,
        reasons=("screening complete", f"risk: {risk.value}"),
        sample_id=sample.sample_id,
        finding=finding,
        next_actions=next_actions,
        resample_after_days=resample,
        treatment_options=_treatment_options(risk),
        references=[_HC_REF, _MECP_REF],
        audit_ref=_audit_ref(request, sample),
        generated_utc=now,
    )
