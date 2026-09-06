"""Tests for the PERCIVAL · PFAS CSV ingester."""
from __future__ import annotations

import pathlib
import sys
import textwrap

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.pfas import HC_25_PFAS_NGL, Risk, ScreeningRequest, screen
from sentinel.pfas_ingest import IngestError, ingest_csv

REQ = ScreeningRequest(
    client_id="city-of-burlington-water",
    site_owner_ref="WO-2026-014",
    jurisdiction="ON, CA",
    purpose="annual compliance screening",
    requester_role="water_quality_lead",
)

CSV_OK = textwrap.dedent("""\
    sample_id,site_id,matrix,collected,lab,method,analyte,value,units,loq,qualifier
    S-1001,BURL-WTP-A,drinking_water,2026-06-04T10:00:00Z,Acme Labs,EPA 533,PFOA,5.2,ng/L,2.0,
    S-1001,BURL-WTP-A,drinking_water,2026-06-04T10:00:00Z,Acme Labs,EPA 533,PFOS,7.4,ng/L,2.0,
    S-1001,BURL-WTP-A,drinking_water,2026-06-04T10:00:00Z,Acme Labs,EPA 533,PFHxS,4.0,ng/L,2.0,
    S-1001,BURL-WTP-A,drinking_water,2026-06-04T10:00:00Z,Acme Labs,EPA 533,PFBA,,ng/L,2.0,<
""")


def test_parses_long_form_csv():
    sample = ingest_csv(CSV_OK)
    assert sample.sample_id == "S-1001"
    assert sample.site_id == "BURL-WTP-A"
    assert sample.matrix == "drinking_water"
    assert sample.lab == "Acme Labs"
    assert len(sample.results) == 4
    # PFBA row is <LOQ
    pfba = [r for r in sample.results if r.analyte == "PFBA"][0]
    assert pfba.below_loq is True and pfba.loq_ngL == 2.0


def test_ingested_sample_runs_through_screen():
    sample = ingest_csv(CSV_OK)
    pkg = screen(REQ, sample)
    assert pkg.accepted is True
    # 5.2 + 7.4 + 4.0 = 16.6 ng/L upper bound (PFBA <LOQ adds 2.0 to max)
    assert abs(pkg.finding.sum_25_ngL - 16.6) < 0.01
    assert abs(pkg.finding.sum_25_ngL_max - 18.6) < 0.01
    # 16.6 ≥ 15 (0.5 × 30) → ELEVATED
    assert pkg.finding.risk is Risk.ELEVATED
    assert HC_25_PFAS_NGL == 30.0


def test_unit_conversion_ug_per_l_to_ngL():
    csv_ug = textwrap.dedent("""\
        analyte,value,units
        PFOA,0.012,µg/L
        PFOS,0.018,ug/L
    """)
    sample = ingest_csv(csv_ug)
    vals = {r.analyte: r.value_ngL for r in sample.results}
    assert vals["PFOA"] == 12.0
    assert vals["PFOS"] == 18.0


def test_ppt_treated_as_ngL():
    sample = ingest_csv("analyte,value,units\nPFOA,5,ppt\n")
    assert sample.results[0].value_ngL == 5.0


def test_unsupported_units_rejected():
    with pytest.raises(IngestError, match="unsupported units"):
        ingest_csv("analyte,value,units\nPFOA,5,mg/L\n")


def test_missing_required_column_rejected():
    with pytest.raises(IngestError, match="missing required column"):
        ingest_csv("name,result\nPFOA,5\n")     # no units column


def test_inconsistent_sample_metadata_fails_closed():
    bad = textwrap.dedent("""\
        sample_id,analyte,value,units
        S-1,PFOA,5,ng/L
        S-2,PFOS,6,ng/L
    """)
    with pytest.raises(IngestError, match="inconsistent"):
        ingest_csv(bad)


def test_non_numeric_value_rejected():
    with pytest.raises(IngestError, match="non-numeric"):
        ingest_csv("analyte,value,units\nPFOA,oops,ng/L\n")


def test_less_than_loq_prefix_handled():
    sample = ingest_csv("analyte,value,units,loq\nPFOA,<2.0,ng/L,2.0\n")
    r = sample.results[0]
    assert r.below_loq is True
    assert r.loq_ngL == 2.0
    assert r.value_ngL == 0.0


def test_empty_input_rejected():
    with pytest.raises(IngestError, match="empty"):
        ingest_csv("   ")
    with pytest.raises(IngestError, match="no analyte rows"):
        ingest_csv("analyte,value,units\n")
