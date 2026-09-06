"""Tests for the PERCIVAL PFAS compliance + decision intelligence agent."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.pfas import (
    HC_25_PFAS_NGL,
    AnalyteResult,
    Risk,
    Sample,
    ScreeningRequest,
    screen,
)

REQ = ScreeningRequest(
    client_id="city-of-burlington-water",
    site_owner_ref="WO-2026-014",
    jurisdiction="ON, CA",
    purpose="annual compliance screening",
    requester_role="water_quality_lead",
)


def _sample(results, sid="S-001", matrix="drinking_water"):
    return Sample(sample_id=sid, site_id="SITE-A", collected_utc="2026-06-04T10:00:00Z",
                  matrix=matrix, results=tuple(results), lab="Acme Labs", method="EPA 533")


def test_missing_authorization_fails_closed():
    bad = ScreeningRequest(client_id="", site_owner_ref="", jurisdiction="",
                           purpose="", requester_role="")
    pkg = screen(bad, _sample([AnalyteResult("PFOA", 5.0)]))
    assert pkg.accepted is False
    assert any("missing scope" in r for r in pkg.reasons)


def test_low_risk_below_half_objective():
    pkg = screen(REQ, _sample([
        AnalyteResult("PFOA", 2.0),
        AnalyteResult("PFOS", 3.0),
        AnalyteResult("PFHxA", 1.0),
    ]))
    assert pkg.accepted and pkg.finding.risk is Risk.LOW
    assert pkg.finding.sum_25_ngL == 6.0
    assert pkg.resample_after_days == 365
    assert pkg.treatment_options == []


def test_elevated_at_or_above_half_objective():
    pkg = screen(REQ, _sample([
        AnalyteResult("PFOA", 8.0),
        AnalyteResult("PFOS", 8.0),
    ]))
    assert pkg.finding.risk is Risk.ELEVATED
    assert pkg.finding.sum_25_ngL >= 0.5 * HC_25_PFAS_NGL
    assert pkg.resample_after_days == 30
    assert any("monthly" in a.lower() for a in pkg.next_actions)


def test_exceedance_triggers_full_response():
    pkg = screen(REQ, _sample([
        AnalyteResult("PFOA", 12.0),
        AnalyteResult("PFOS", 12.0),
        AnalyteResult("PFHxS", 10.0),
    ]))
    assert pkg.finding.risk is Risk.EXCEEDANCE
    assert pkg.finding.sum_25_ngL >= HC_25_PFAS_NGL
    assert any("compliance" in a.lower() for a in pkg.next_actions)
    assert pkg.treatment_options and "GAC" in pkg.treatment_options[0]
    assert pkg.resample_after_days == 7
    # source hints surface relevant categories
    assert any("AFFF" in h for h in pkg.finding.source_category_hints)


def test_loq_handling_is_operator_conservative():
    # below-LOQ values count toward the UPPER bound (LOQ), not the lower.
    pkg = screen(REQ, _sample([
        AnalyteResult("PFOA", 5.0),
        AnalyteResult("PFOS", 0.0, loq_ngL=10.0, below_loq=True),
    ]))
    assert pkg.finding.sum_25_ngL == 5.0
    assert pkg.finding.sum_25_ngL_max == 15.0
    # risk is computed off the upper bound
    assert pkg.finding.risk in (Risk.LOW, Risk.ELEVATED, Risk.EXCEEDANCE)


def test_non_listed_analytes_excluded_from_sum():
    pkg = screen(REQ, _sample([
        AnalyteResult("PFOA", 5.0),
        AnalyteResult("RANDOM-PFAS-X", 100.0),   # not in HC list of 25
    ]))
    assert pkg.finding.sum_25_ngL == 5.0
    assert "RANDOM-PFAS-X" not in pkg.finding.detected_analytes


def test_empty_results_returns_insufficient():
    pkg = screen(REQ, _sample([]))
    assert pkg.accepted is False
    assert pkg.finding.risk is Risk.INSUFFICIENT


def test_audit_and_references_present_on_accepted():
    pkg = screen(REQ, _sample([AnalyteResult("PFOA", 5.0)]))
    assert pkg.audit_ref.startswith("PFAS-")
    assert any("Health Canada" in r for r in pkg.references)
    d = pkg.to_dict()
    assert d["accepted"] is True and d["finding"]["risk"] in {"LOW", "ELEVATED", "EXCEEDANCE"}


def test_wastewater_matrix_adds_biosolids_hint():
    pkg = screen(REQ, _sample([AnalyteResult("PFOA", 12.0), AnalyteResult("PFOS", 12.0)],
                              matrix="wastewater"))
    assert any("Wastewater" in h for h in pkg.finding.source_category_hints)
