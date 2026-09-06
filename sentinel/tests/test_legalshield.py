"""Tests for AEGIS — the legal-process compliance / rights-protection agent."""
from __future__ import annotations

import datetime as _dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.legalshield import (
    DISCLAIMER,
    LegalProcessShield,
    LegalRequest,
    Outcome,
    RequestKind,
)


def _req(**kw) -> LegalRequest:
    base = dict(
        id="LR-1", kind=RequestKind.WARRANT, issuing_authority="Ontario Court of Justice",
        jurisdiction="ON, CA", target="ClearGlass Inc.", scope=("user X email logs 2026-01..03",),
        signed=True, warrant_number="CR-2026-0420", received_utc="2026-06-04T10:00:00Z",
    )
    base.update(kw)
    return LegalRequest(**base)


def test_valid_scoped_warrant_complies_pending_counsel_with_minimization():
    a = LegalProcessShield().assess(_req())
    assert a.outcome is Outcome.COMPLY_PENDING_COUNSEL
    assert a.requires_counsel_review is True
    assert a.permitted_disclosure == ["user X email logs 2026-01..03"]  # minimized to scope
    assert a.protected_principal is True                                # ClearGlass Inc.
    assert a.audit_ref and a.disclaimer == DISCLAIMER


def test_unsigned_warrant_is_challenged():
    a = LegalProcessShield().assess(_req(signed=False))
    assert a.outcome is Outcome.CHALLENGE
    assert any("unsigned" in r for r in a.reasons)
    assert a.permitted_disclosure == []                                 # nothing disclosed


def test_overbroad_scope_is_challenged():
    a = LegalProcessShield().assess(_req(scope=("any and all data",)))
    assert a.outcome is Outcome.CHALLENGE
    assert any("overbroad" in r for r in a.reasons)


def test_expired_process_is_challenged():
    past = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=2)).isoformat()
    a = LegalProcessShield().assess(_req(expiry_utc=past))
    assert a.outcome is Outcome.CHALLENGE
    assert any("expired" in r for r in a.reasons)


def test_missing_authority_or_jurisdiction_challenged():
    a = LegalProcessShield().assess(_req(issuing_authority="", jurisdiction=""))
    assert a.outcome is Outcome.CHALLENGE


def test_informal_request_refused_no_legal_basis():
    a = LegalProcessShield().assess(_req(kind=RequestKind.INFORMAL_REQUEST))
    assert a.outcome is Outcome.REFUSE_NO_LEGAL_BASIS
    assert a.permitted_disclosure == []


def test_preservation_demand_holds_in_place_never_deletes():
    a = LegalProcessShield().assess(_req(kind=RequestKind.PRESERVATION_DEMAND))
    assert a.outcome is Outcome.PRESERVE_IN_PLACE
    assert any("legal hold" in r.lower() for r in a.reasons)
    assert a.permitted_disclosure == []


def test_emergency_request_routes_to_counsel_never_auto_discloses():
    a = LegalProcessShield().assess(_req(kind=RequestKind.EMERGENCY_DISCLOSURE_REQUEST))
    assert a.outcome is Outcome.ACKNOWLEDGE_ROUTE_COUNSEL
    assert a.permitted_disclosure == []
    assert any("never auto-disclose" in r for r in a.reasons)


def test_protected_individual_is_tagged():
    a = LegalProcessShield().assess(_req(target="Desmond Otieno Odhiambo"))
    assert a.protected_principal is True


def test_assess_always_requires_counsel_review():
    sh = LegalProcessShield()
    for kind in RequestKind:
        a = sh.assess(_req(kind=kind))
        assert a.requires_counsel_review is True
        assert a.disclaimer == DISCLAIMER


# ---- guard our own conduct: refuse obstruction ----------------------------

def test_guard_refuses_obstruction_actions():
    sh = LegalProcessShield()
    for bad in ("destroy_evidence", "delete_records_under_hold", "tip_off_subject",
                "evade_warrant", "conceal_assets", "falsify_records"):
        a = sh.guard_action(bad)
        assert a.outcome is Outcome.REFUSE_UNLAWFUL
        assert "will not assist" in a.reasons[0]


def test_guard_permits_lawful_compliance_actions():
    a = LegalProcessShield().guard_action("preserve_in_place")
    assert a.outcome is not Outcome.REFUSE_UNLAWFUL


# ---- posture + rights + audit ---------------------------------------------

def test_posture_and_rights_present():
    assert len(LegalProcessShield.posture_recommendations()) >= 6
    rights = LegalProcessShield.rights_summary()
    assert rights["disclaimer"] == DISCLAIMER
    assert any("Challenge" in r for r in rights["your_rights"])


def test_audit_chain_intact():
    sh = LegalProcessShield()
    sh.assess(_req())
    sh.guard_action("destroy_evidence")
    assert sh.audit.verify() is True
    assert len(sh.audit.entries) == 2
