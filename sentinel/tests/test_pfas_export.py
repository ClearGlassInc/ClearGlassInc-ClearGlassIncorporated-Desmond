"""Tests for the PERCIVAL · PFAS evidence-pack exporter."""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.pfas import AnalyteResult, Sample, ScreeningRequest, screen
from sentinel.pfas_export import export_json, export_markdown, package_filename

REQ = ScreeningRequest(
    client_id="city-of-burlington-water",
    site_owner_ref="WO-2026-014",
    jurisdiction="ON, CA",
    purpose="annual compliance screening",
    requester_role="water_quality_lead",
)


def _exceedance_pkg():
    return screen(REQ, Sample(
        sample_id="S-2001", site_id="BURL-WTP-A",
        collected_utc="2026-06-04T10:00:00Z", matrix="drinking_water",
        results=(
            AnalyteResult("PFOA", 12.0),
            AnalyteResult("PFOS", 12.0),
            AnalyteResult("PFHxS", 10.0),
        ),
    ))


def test_json_export_is_parseable_and_complete():
    pkg = _exceedance_pkg()
    s = export_json(pkg)
    parsed = json.loads(s)
    assert parsed["accepted"] is True
    assert parsed["finding"]["risk"] == "EXCEEDANCE"
    assert parsed["sample_id"] == "S-2001"
    assert "audit_ref" in parsed and parsed["audit_ref"].startswith("PFAS-")
    assert any("Health Canada" in r for r in parsed["references"])


def test_markdown_export_has_required_sections():
    md = export_markdown(_exceedance_pkg())
    for section in ("# PERCIVAL", "Audit ref", "## Top line",
                    "## Detected analytes", "## Next actions",
                    "Treatment options", "## References"):
        assert section in md
    assert "EXCEEDANCE" in md
    assert "30 ng/L" in md             # threshold cited


def test_denied_package_exports_reasons_not_finding():
    bad_req = ScreeningRequest("", "", "", "", "")
    pkg = screen(bad_req, Sample(
        sample_id="S-X", site_id="SITE-X",
        collected_utc="2026-06-04T10:00:00Z",
        results=(AnalyteResult("PFOA", 5.0),),
    ))
    md = export_markdown(pkg)
    assert "DENIED" in md
    assert "missing scope" in md
    # JSON round-trip still works for denials
    parsed = json.loads(export_json(pkg))
    assert parsed["accepted"] is False


def test_filename_is_safe_and_stable():
    pkg = _exceedance_pkg()
    fn = package_filename(pkg, "md")
    assert fn.startswith("pfas-S-2001-PFAS-") and fn.endswith(".md")
    # no path traversal / unsafe chars
    assert "/" not in fn and ".." not in fn and " " not in fn
