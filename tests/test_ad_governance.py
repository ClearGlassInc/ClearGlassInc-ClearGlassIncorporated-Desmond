"""Advertising controls are checked before a campaign can be approved.

``data/compliance/advertising-sources.json`` ties each control to the Canadian
law, platform policy or standard it rests on, and ``tools/campaign_registry.py``
enforces them. Content problems (claims, sensitive targeting, tracking the
privacy policy rules out, a landing page without a privacy link or basic
accessibility) block a draft from READY FOR APPROVAL. Owner attestations
(policy review, verification, MFA, CASL basis, legal review) are required only
once a campaign is approved, like its spend ceiling.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("campaign_registry", ROOT / "tools" / "campaign_registry.py")
registry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(registry)  # type: ignore[union-attr]

SOURCES = ROOT / "data" / "compliance" / "advertising-sources.json"
CONTROLS_DOC = ROOT / "growth-system" / "compliance-controls.md"

APPROVED = {
    "id": "example",
    "campaign_code": "CG-GOOGLE-SMB-QUICKAUDIT-2026-Q4",
    "objective": "Paid Quick-Audits",
    "audience": "Burlington businesses with 5-100 employees",
    "offer": "quick-audit",
    "cta": "Book a scoping call",
    "landing_page": "/offers/security-quick-audit.html",
    "measurement_plan": ["booking_start"],
    "success_criteria": "Set by the owner",
    "shutdown_thresholds": "Set by the owner",
    "approval_status": "approved",
    "spend_ceiling_cad": 300,
    "google_search_ads": [{"headline": "Security Quick-Audit", "description": "Read-only review."}],
    "governance": {
        "policy_reviewed_on": {"google_ads": "2026-10-01"},
        "advertiser_verification": {"google_ads": "verified"},
        "account_mfa": True,
    },
}


def tagged(issues: list[str], control: str) -> list[str]:
    return [issue for issue in issues if f"[{control}]" in issue]


def test_a_fully_attested_campaign_passes() -> None:
    assert registry.problems(APPROVED) == []


# --- AD-CLAIMS -------------------------------------------------------------

@pytest.mark.parametrize("copy", [
    "Guaranteed protection for your firm",
    "Unhackable Microsoft 365",
    "100% secure in two weeks",
    "Fully compliant with PIPEDA",
    "Burlington's best security team",
    "Limited time: book today",
    "Only 3 spots left this month",
    "Industry-leading assessments",
])
def test_an_unsubstantiated_claim_blocks_the_campaign(copy) -> None:
    campaign = {**APPROVED, "google_search_ads": [{"headline": "Audit", "description": copy}]}
    assert tagged(registry.problems(campaign), "AD-CLAIMS")


@pytest.mark.parametrize("copy", [
    "Hardening to CIS best practices",
    "Top 10 risk-ranked findings in 3 days",
    "Book a free scoping call",
    "Read-only security posture review",
])
def test_plain_offer_descriptions_are_not_claims(copy) -> None:
    campaign = {**APPROVED, "google_search_ads": [{"headline": "Audit", "description": copy}]}
    assert tagged(registry.problems(campaign), "AD-CLAIMS") == []


def test_negative_keywords_are_not_copy() -> None:
    ads = [{"headline": "Audit", "description": "Review.", "negative_keywords": ["guaranteed", "best"]}]
    assert tagged(registry.problems({**APPROVED, "google_search_ads": ads}), "AD-CLAIMS") == []


def test_a_claim_with_evidence_in_the_repository_is_allowed() -> None:
    ads = [{"headline": "Audit", "description": "Certified assessor."}]
    # Any file in the repository counts as evidence here; this one is a fixture,
    # not a claim that ClearGlass holds a certification.
    backed = {"claim": "Certified assessor", "evidence": "tests/test_ad_governance.py"}
    assert (ROOT / backed["evidence"]).is_file()
    assert tagged(registry.problems({**APPROVED, "google_search_ads": ads, "substantiation": [backed]}),
                  "AD-CLAIMS") == []
    for evidence in ("docs/no-such-file.md", "/etc/hostname", "../outside.md", ""):
        entry = {**backed, "evidence": evidence}
        assert tagged(registry.problems({**APPROVED, "google_search_ads": ads, "substantiation": [entry]}),
                      "AD-CLAIMS"), f"evidence {evidence!r} must not count"


# --- AD-TARGETING / AD-TRACKING ---------------------------------------------

@pytest.mark.parametrize("audience", [
    "Ontario residents with a medical condition",
    "Owners in financial hardship",
    "People by religion",
])
def test_an_audience_built_on_a_sensitive_trait_is_refused(audience) -> None:
    assert tagged(registry.problems({**APPROVED, "audience": audience}), "AD-TARGETING")


def test_sensitive_traits_in_targeting_values_are_refused_too() -> None:
    campaign = {**APPROVED, "targeting": {"interests": ["debt consolidation"]}}
    assert tagged(registry.problems(campaign), "AD-TARGETING")


def test_an_industry_is_not_a_sensitive_trait() -> None:
    for audience in ("Healthcare clinics in Halton", "Law, accounting and real-estate firms"):
        assert tagged(registry.problems({**APPROVED, "audience": audience}), "AD-TARGETING") == []


def test_tracking_is_refused_while_the_privacy_policy_says_there_is_none() -> None:
    """legal/privacy.html section 10 promises no advertising cookies or pixels."""
    assert registry.privacy_policy_refuses_ad_tracking()
    for key in registry.TRACKING_TARGETING:
        campaign = {**APPROVED, "approval_status": "draft", "targeting": {key: True}}
        assert tagged(registry.problems(campaign), "AD-TRACKING"), key


def test_once_the_policy_allows_tracking_it_still_needs_legal_review(tmp_path, monkeypatch) -> None:
    policy = tmp_path / "privacy.html"
    policy.write_text("<p>We use advertising cookies with your consent.</p>")
    monkeypatch.setattr(registry, "PRIVACY_POLICY", policy)
    campaign = {**APPROVED, "targeting": {"remarketing": True}}
    issues = registry.problems(campaign)
    assert tagged(issues, "AD-TRACKING") == []
    assert tagged(issues, "AD-LEGAL")
    reviewed = {**campaign, "governance": {**APPROVED["governance"], "legal_review_on": "2026-10-01"}}
    assert registry.problems(reviewed) == []


# --- AD-DESTINATION -----------------------------------------------------------

GOOD_PAGE = (
    '<html lang="en"><body><img src="a.png" alt="">'
    '<form><label>Email<input name="email"></label>'
    '<label for="org">Company</label><input id="org" name="company">'
    '<input type="text" name="_honey" aria-hidden="true" tabindex="-1">'
    '<input type="hidden" name="source"><button type="submit">Send</button></form>'
    '<a href="../legal/privacy.html">Privacy policy</a>'
    '<script src="/assets/js/cg-attribution.js"></script></body></html>'
)


@pytest.mark.parametrize("change, expected", [
    (('<a href="../legal/privacy.html">Privacy policy</a>', ""), "no link to the privacy policy"),
    (("href=\"../legal/privacy.html\"", "href=\"https://evil.example/legal/privacy.html\""), "no link to the privacy policy"),
    (("href=\"../legal/privacy.html\"", "href=\"/fake/legal/privacy.html\""), "no link to the privacy policy"),
    (('<html lang="en">', "<html>"), "does not declare its language"),
    (('alt=""', ""), "1 image(s) without alt text"),
    (('<label>Email<input name="email"></label>', '<input name="email">'), "without a label: email"),
])
def test_a_landing_page_needs_a_privacy_link_and_basic_accessibility(tmp_path, monkeypatch, change, expected) -> None:
    monkeypatch.setattr(registry, "ROOT", tmp_path)
    (tmp_path / "offers").mkdir()
    (tmp_path / "offers" / "good.html").write_text(GOOD_PAGE)
    assert registry.destination_problem("/offers/good.html") is None
    (tmp_path / "offers" / "bad.html").write_text(GOOD_PAGE.replace(*change))
    problem = registry.destination_problem("/offers/bad.html")
    assert problem and expected in problem and "[AD-DESTINATION]" in problem


# --- owner attestations at approval ------------------------------------------

def test_a_draft_needs_no_attestations_but_the_report_lists_them(tmp_path, monkeypatch, capsys) -> None:
    draft = {**APPROVED, "approval_status": "draft", "spend_ceiling_cad": None}
    del draft["governance"]
    assert registry.problems(draft) == []
    (tmp_path / "c.json").write_text(json.dumps({"campaigns": [draft]}))
    monkeypatch.setattr(registry, "CAMPAIGN_DIR", tmp_path)
    assert registry.main(["--check"]) == 0
    out = capsys.readouterr().out
    assert "READY FOR APPROVAL" in out
    assert "at approval, record governance.policy_reviewed_on.google_ads" in out


def test_an_approved_campaign_without_attestations_fails_the_gate(tmp_path, monkeypatch, capsys) -> None:
    unattested = {key: value for key, value in APPROVED.items() if key != "governance"}
    issues = registry.problems(unattested)
    assert tagged(issues, "AD-PLATFORM") and tagged(issues, "AD-ACCOUNT")
    (tmp_path / "c.json").write_text(json.dumps({"campaigns": [unattested]}))
    monkeypatch.setattr(registry, "CAMPAIGN_DIR", tmp_path)
    assert registry.main(["--check"]) == 1
    assert "missing governance.account_mfa" in capsys.readouterr().out


@pytest.mark.parametrize("governance", [
    {"policy_reviewed_on": {"google_ads": "2999-01-01"}},   # a review in the future
    {"policy_reviewed_on": {"google_ads": "01/10/2026"}},   # not YYYY-MM-DD
    {"advertiser_verification": {"google_ads": "pending"}},
    {"account_mfa": "yes"},                                 # true, not truthy
])
def test_attestations_must_be_real_values(governance) -> None:
    campaign = {**APPROVED, "governance": {**APPROVED["governance"], **governance}}
    assert registry.attestations_missing(campaign)


def test_every_ad_platform_in_the_package_is_attested() -> None:
    campaign = {**APPROVED, "linkedin_ads": [{"headline": "Audit", "body": "Read-only review."}]}
    assert [i for i in registry.attestations_missing(campaign) if "linkedin_ads" in i]


def test_email_needs_a_casl_consent_basis() -> None:
    campaign = {**APPROVED, "outreach_emails": ["Initial: share the checklist."]}
    assert tagged(registry.problems(campaign), "AD-CASL")
    assert tagged(registry.problems({**APPROVED, "campaign_code": "CG-EMAIL-SMB-QUICKAUDIT-2026-Q4"}), "AD-CASL")
    ok = {**campaign, "governance": {**APPROVED["governance"], "casl_consent_basis": "express"}}
    assert registry.problems(ok) == []


def test_legal_topics_in_copy_need_a_dated_legal_review() -> None:
    campaign = {**APPROVED, "cta": "Get PIPEDA-ready"}
    assert tagged(registry.problems(campaign), "AD-LEGAL")
    ok = {**campaign, "governance": {**APPROVED["governance"], "legal_review_on": "2026-09-30"}}
    assert registry.problems(ok) == []


def test_the_ready_packages_are_unchanged_by_the_controls() -> None:
    """Both READY packages still pass every content control; what they need at
    approval is the owner's to record."""
    campaigns = {c["id"]: c for _, c in registry.load()}
    for name in ("burlington-cyber-risk-checkup", "m365-account-protection"):
        assert registry.problems(campaigns[name]) == []
        assert registry.attestations_missing(campaigns[name])


# --- the source registry ----------------------------------------------------

def test_every_control_rests_on_a_recorded_source() -> None:
    data = json.loads(SOURCES.read_text(encoding="utf-8"))
    sources = {s["id"]: s for s in data["sources"]}
    assert len(sources) == len(data["sources"]), "source ids are unique"
    for source in sources.values():
        assert source["url"].startswith("https://"), source["id"]
        assert source["fetched"] is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}", source["fetched"])
    cited = set()
    for control in data["controls"]:
        assert control["sources"], control["id"]
        assert set(control["sources"]) <= set(sources), control["id"]
        cited |= set(control["sources"])
    assert cited == set(sources), f"sources no control uses: {set(sources) - cited}"


def test_every_control_is_enforced_where_it_says_and_documented() -> None:
    data = json.loads(SOURCES.read_text(encoding="utf-8"))
    doc = CONTROLS_DOC.read_text(encoding="utf-8")
    tool = (ROOT / "tools" / "campaign_registry.py").read_text(encoding="utf-8")
    for control in data["controls"]:
        assert (ROOT / control["enforced_by"]).is_file(), control["id"]
        assert control["id"] in doc, f"{control['id']} is not in {CONTROLS_DOC.name}"
        if control["enforced_by"] == "tools/campaign_registry.py":
            assert f"[{control['id']}]" in tool, f"no problem message names {control['id']}"
