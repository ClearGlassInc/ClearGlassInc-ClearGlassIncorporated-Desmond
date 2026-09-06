"""SENTINEL charter enforcement tests (SENTINEL_CHARTER.md → policy.py)."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.policy import (
    PolicyOutcome,
    PrivacyPolicy,
    Report,
    RequestClass,
    RequestContext,
)

POL = PrivacyPolicy()


def test_owned_camera_intrusion_allowed():
    d = POL.evaluate(RequestContext(
        actor_role="soc_analyst", purpose="perimeter intrusion monitoring",
        data_source="owned_camera_network", intent="monitor",
    ))
    assert d.outcome is PolicyOutcome.ALLOW
    assert d.request_class in (RequestClass.ASSET_PROTECTION, RequestClass.INCIDENT_RESPONSE)
    assert d.audit_ref.startswith("SENT-")


def test_brand_mention_correlation_allowed():
    d = POL.evaluate(RequestContext(
        actor_role="threat_intel", purpose="brand and domain mention correlation",
        data_source="public_source_brand_mentions", intent="correlate",
    ))
    assert d.outcome is PolicyOutcome.ALLOW


def test_identify_private_person_without_authority_denied():
    d = POL.evaluate(RequestContext(
        actor_role="analyst", purpose="find this person",
        data_source="public_source_brand_mentions", intent="monitor",
        targets_private_individual=True,
    ))
    assert d.outcome is PolicyOutcome.DENY
    assert any("documented authorization" in r for r in d.reasons)
    assert d.requires_human_review


def test_face_recognition_on_nonconsenting_denied():
    d = POL.evaluate(RequestContext(
        actor_role="analyst", purpose="match faces in crowd",
        data_source="owned_camera_network", intent="monitor",
        uses_face_recognition=True, subject_consenting=False,
    ))
    assert d.outcome is PolicyOutcome.DENY
    assert any("face-recognition" in r for r in d.reasons)


def test_cross_source_matching_nonconsenting_denied():
    d = POL.evaluate(RequestContext(
        actor_role="analyst", purpose="link identities across sources",
        data_source="authorized_telemetry", intent="correlate",
        cross_source_matching=True, subject_consenting=False,
    ))
    assert d.outcome is PolicyOutcome.DENY


def test_osint_deanonymization_denied():
    d = POL.evaluate(RequestContext(
        actor_role="analyst", purpose="unmask anonymous account",
        data_source="public_source_brand_mentions", intent="de_anonymize",
    ))
    assert d.outcome is PolicyOutcome.DENY
    assert any("prohibited intent" in r for r in d.reasons)


def test_unapproved_source_denied():
    d = POL.evaluate(RequestContext(
        actor_role="analyst", purpose="monitor",
        data_source="random_scraped_dataset", intent="monitor",
    ))
    assert d.outcome is PolicyOutcome.DENY
    assert any("not approved" in r for r in d.reasons)


def test_missing_role_or_purpose_denied():
    d = POL.evaluate(RequestContext(
        actor_role="", purpose="", data_source="owned_camera_network",
    ))
    assert d.outcome is PolicyOutcome.DENY
    assert any("role" in r for r in d.reasons)
    assert any("purpose" in r for r in d.reasons)


def test_consented_watchlist_escalates():
    d = POL.evaluate(RequestContext(
        actor_role="security_lead", purpose="pre-approved watchlist under written policy",
        data_source="consented_watchlist", intent="monitor",
        targets_private_individual=True, subject_consenting=True,
        authorization_ref="POLICY-2026-014", jurisdiction="US-CA",
    ))
    assert d.outcome is PolicyOutcome.ESCALATE
    assert d.requires_human_review


def test_covert_access_denied():
    d = POL.evaluate(RequestContext(
        actor_role="analyst", purpose="brand monitoring",
        data_source="public_source_brand_mentions", intent="correlate",
        access_method="covert",
    ))
    assert d.outcome is PolicyOutcome.DENY
    assert any("access method" in r for r in d.reasons)


def test_unauthorized_scraping_denied():
    d = POL.evaluate(RequestContext(
        actor_role="analyst", purpose="collect data",
        data_source="public_source_brand_mentions", intent="correlate",
        access_method="unauthorized_scraping",
    ))
    assert d.outcome is PolicyOutcome.DENY


def test_geospatial_fusion_to_locate_person_denied():
    d = POL.evaluate(RequestContext(
        actor_role="analyst", purpose="locate subject via imagery + posts",
        data_source="lawful_satellite_imagery", intent="monitor",
        combines_geospatial_sources=True, targets_private_individual=True,
        jurisdiction="US-CA",
    ))
    assert d.outcome is PolicyOutcome.DENY
    assert any("de-anonymize or locate a person" in r for r in d.reasons)


def test_satellite_change_detection_on_owned_site_allowed():
    d = POL.evaluate(RequestContext(
        actor_role="facilities_soc", purpose="storm damage change detection on owned site",
        data_source="lawful_satellite_imagery", intent="monitor",
    ))
    assert d.outcome is PolicyOutcome.ALLOW
    assert d.request_class is RequestClass.EMERGENCY_RESPONSE


def test_individual_scope_without_jurisdiction_denied():
    d = POL.evaluate(RequestContext(
        actor_role="security_lead", purpose="watchlist check",
        data_source="consented_watchlist", intent="monitor",
        targets_private_individual=True, subject_consenting=True,
        authorization_ref="POLICY-1", jurisdiction=None,
    ))
    assert d.outcome is PolicyOutcome.DENY
    assert any("jurisdiction" in r for r in d.reasons)


def test_profiling_private_person_intent_denied():
    d = POL.evaluate(RequestContext(
        actor_role="analyst", purpose="build profile",
        data_source="public_source_brand_mentions", intent="profile_private_person",
    ))
    assert d.outcome is PolicyOutcome.DENY


# ---- charter v2.1 additions ----

def test_situational_awareness_class_allowed():
    d = POL.evaluate(RequestContext(
        actor_role="ops_center", purpose="situational awareness for owned infrastructure",
        data_source="authorized_sensor_feeds", intent="monitor",
    ))
    assert d.outcome is PolicyOutcome.ALLOW
    assert d.request_class is RequestClass.SITUATIONAL_AWARENESS


def test_locate_individual_intent_denied_without_authority():
    d = POL.evaluate(RequestContext(
        actor_role="analyst", purpose="find subject",
        data_source="lawful_satellite_imagery", intent="locate_individual",
        jurisdiction="US-CA",
    ))
    assert d.outcome is PolicyOutcome.DENY
    assert any("documented authorization" in r for r in d.reasons)


def test_track_individual_intent_requires_jurisdiction():
    d = POL.evaluate(RequestContext(
        actor_role="security_lead", purpose="approved watchlist tracking",
        data_source="consented_watchlist", intent="track_individual",
        subject_consenting=True, authorization_ref="POLICY-9", jurisdiction=None,
    ))
    assert d.outcome is PolicyOutcome.DENY
    assert any("jurisdiction" in r for r in d.reasons)


def test_impersonation_access_denied():
    d = POL.evaluate(RequestContext(
        actor_role="analyst", purpose="collect",
        data_source="public_source_brand_mentions", intent="correlate",
        access_method="impersonation",
    ))
    assert d.outcome is PolicyOutcome.DENY
    assert any("access method" in r for r in d.reasons)


def test_vulnerability_intel_for_owned_assets_allowed():
    from sentinel.policy import THREAT_INTEL_FEEDS
    assert THREAT_INTEL_FEEDS["exploit_db"] == "https://www.exploit-db.com/"
    d = POL.evaluate(RequestContext(
        actor_role="vuln_mgmt", purpose="assess published-exploit exposure for owned infrastructure",
        data_source="vulnerability_intel", intent="correlate",
    ))
    assert d.outcome is PolicyOutcome.ALLOW
    assert d.request_class is RequestClass.ASSET_PROTECTION


def test_vulnerability_intel_cannot_target_individual():
    d = POL.evaluate(RequestContext(
        actor_role="analyst", purpose="exploit research to locate a person",
        data_source="vulnerability_intel", intent="locate_individual", jurisdiction="US-CA",
    ))
    assert d.outcome is PolicyOutcome.DENY


def test_emergency_response_with_authorized_source_allowed():
    d = POL.evaluate(RequestContext(
        actor_role="emergency_ops", purpose="flood damage assessment of owned facility",
        data_source="lawful_satellite_imagery", intent="monitor",
    ))
    assert d.outcome is PolicyOutcome.ALLOW
    assert d.request_class is RequestClass.EMERGENCY_RESPONSE


def test_sensitive_inference_escalates():
    d = POL.evaluate(RequestContext(
        actor_role="soc_analyst", purpose="incident timeline",
        data_source="authorized_logs", intent="monitor",
        sensitive_inference=True,
    ))
    assert d.outcome is PolicyOutcome.ESCALATE


def test_failclosed_on_none_context():
    d = POL.evaluate(None)
    assert d.outcome is PolicyOutcome.DENY
    assert any("fail-closed" in r for r in d.reasons)


def test_report_render_has_charter_sections():
    r = Report(
        top_line="Perimeter breach at dock 3",
        evidence=["cam-07 motion 02:14Z", "badge log gap"],
        confidence="HIGH",
        risk_notes=["possible tailgating"],
        next_step="dispatch on-site guard; preserve clip",
        audit_ref="SENT-ABCDEF123456",
    )
    out = r.render()
    for section in ("TOP-LINE", "EVIDENCE", "CONFIDENCE", "RISK NOTES", "NEXT STEP", "AUDIT REF"):
        assert section in out
