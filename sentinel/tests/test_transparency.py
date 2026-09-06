"""Tests for AEGIS register + transparency-report generator + shared audit."""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.audit import AuditLog
from sentinel.legalshield import LegalProcessShield, LegalRequest, Outcome, RequestKind
from sentinel.transparency import build_report, report_json, report_markdown


def _shield_with_mixed_register() -> LegalProcessShield:
    s = LegalProcessShield()
    # valid warrant -> COMPLY_PENDING_COUNSEL (protected principal)
    s.assess(LegalRequest("LR-1", RequestKind.WARRANT, "ON Court", "ON, CA",
                          "ClearGlass Inc.", ("logs jan",), signed=True, warrant_number="CR-1"))
    # unsigned warrant -> CHALLENGE
    s.assess(LegalRequest("LR-2", RequestKind.WARRANT, "ON Court", "ON, CA",
                          "ClearGlass Inc.", ("logs feb",), signed=False, warrant_number="CR-2"))
    # informal -> REFUSE_NO_LEGAL_BASIS
    s.assess(LegalRequest("LR-3", RequestKind.INFORMAL_REQUEST, "Some Agency", "ON, CA",
                          "Desmond Otieno Odhiambo", ("anything",)))
    # preservation -> PRESERVE_IN_PLACE
    s.assess(LegalRequest("LR-4", RequestKind.PRESERVATION_DEMAND, "ON Court", "ON, CA",
                          "ClearGlass Inc.", ("mailbox",), signed=True))
    return s


def test_register_accumulates_each_assessment():
    s = _shield_with_mixed_register()
    assert len(s.register) == 4
    assert s.register[0].request.id == "LR-1"


def test_transparency_report_counts():
    s = _shield_with_mixed_register()
    r = build_report(s.register, period="2026-Q2")
    assert r.total_requests == 4
    assert r.complied_pending_counsel == 1
    assert r.challenged == 1
    assert r.refused == 1
    assert r.preserved == 1
    assert r.protected_principal_named == 4          # all four name a protected principal
    assert r.by_kind["warrant"] == 2


def test_report_json_parseable():
    s = _shield_with_mixed_register()
    r = build_report(s.register, period="2026-Q2")
    parsed = json.loads(report_json(r))
    assert parsed["total_requests"] == 4
    assert parsed["by_outcome"][Outcome.CHALLENGE.value] == 1


def test_report_markdown_has_sections_and_disclaimer():
    s = _shield_with_mixed_register()
    md = report_markdown(build_report(s.register, period="2026-Q2"))
    for section in ("Transparency Report", "## Outcomes", "## By request type",
                    "## By outcome", "NOT legal advice"):
        assert section in md
    assert "Aggregate counts only" in md


def test_empty_register_report():
    r = build_report([], period="2026-Q2")
    assert r.total_requests == 0
    assert "Total requests received:** 0" in report_markdown(r)


def test_shared_audit_stream_wiring():
    """Passing a shared AuditLog wires AEGIS decisions into a wider stream."""
    shared = AuditLog()
    shared.record(actor="SENTINEL", action="boot", detail={})   # pre-existing stream entry
    s = LegalProcessShield(audit=shared)
    s.assess(LegalRequest("LR-9", RequestKind.WARRANT, "ON Court", "ON, CA",
                          "ClearGlass Inc.", ("logs",), signed=True, warrant_number="CR-9"))
    s.guard_action("destroy_evidence")
    actors = [e.actor for e in shared.entries]
    assert actors == ["SENTINEL", "AEGIS", "AEGIS"]              # appended to the same ledger
    assert shared.verify() is True                              # chain still intact
