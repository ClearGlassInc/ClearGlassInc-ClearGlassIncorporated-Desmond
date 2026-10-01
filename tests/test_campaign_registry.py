"""Campaign packages are checked against the playbook before they can launch.

``growth-system/campaign-playbook.md`` lists what a campaign must define, and
nothing enforced it: of the five packages in ``data/campaigns``, one names a
landing page and that page has no element with the id its anchor points at.
``tools/campaign_registry.py`` checks the list, the campaign code that
``utm_campaign`` carries through to paid orders, and that the destination
exists. Drafts may be incomplete; an approved or active campaign may not.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("campaign_registry", ROOT / "tools" / "campaign_registry.py")
registry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(registry)  # type: ignore[union-attr]

COMPLETE = {
    "id": "example",
    "campaign_code": "CG-LINKEDIN-SMB-RISKAUDIT-2026-Q4",
    "objective": "Booked discovery calls from Burlington SMB owners",
    "audience": "Burlington businesses with 5-100 employees",
    "offer": "risk-audit-90",
    "cta": "Book a risk review",
    "landing_page": "/revenue-command.html",
    "measurement_plan": ["qualified_lead", "booked_consultation", "won_revenue"],
    "success_criteria": "Set by the owner before approval",
    "shutdown_thresholds": "Set by the owner before approval",
    "approval_status": "approved",
    "spend_ceiling_cad": 0,
}


@pytest.mark.parametrize("code", [
    "CG-LINKEDIN-SMB-RISKAUDIT-2026-Q4",
    "CG-GOOGLE-NONPROFIT-M365-2027-Q1",
])
def test_valid_campaign_codes_parse(code) -> None:
    assert registry.parse_code(code) is not None


@pytest.mark.parametrize("code", [
    "CG-TIKTOK-SMB-RISKAUDIT-2026-Q4",     # channel not in the list
    "CG-LINKEDIN-SMB-RISKAUDIT-2026-Q5",   # no fifth quarter
    "cg-linkedin-smb-riskaudit-2026-q4",   # case matters: one spelling per campaign
    "LINKEDIN-SMB-RISKAUDIT-2026-Q4",
    "",
])
def test_invalid_campaign_codes_are_refused(code) -> None:
    assert registry.parse_code(code) is None


def test_a_complete_campaign_has_no_problems() -> None:
    assert registry.problems(COMPLETE) == []


def test_a_missing_page_or_anchor_is_reported() -> None:
    assert "does not exist" in registry.problems({**COMPLETE, "landing_page": "/no-such-page.html"})[0]
    [issue] = registry.problems({**COMPLETE, "landing_page": "/revenue-command.html#no-such-anchor"})
    assert "no element with id 'no-such-anchor'" in issue
    assert registry.problems({**COMPLETE, "landing_page": "https://elsewhere.example/"}) == [
        "landing_page must be a path on this site"
    ]


def test_an_offer_clearglass_does_not_sell_cannot_be_advertised() -> None:
    [issue] = registry.problems({**COMPLETE, "offer": "Affordable security workshop"})
    assert "not a SKU ClearGlass sells" in issue
    assert registry.problems({**COMPLETE, "offer": "quick-audit"}) == [], "service catalogue ids count"


def test_a_landing_page_that_drops_the_tags_is_refused() -> None:
    """index.html does not load the attribution script: an ad landing there
    would reach the lead form as "direct"."""
    assert registry.ATTRIBUTION_SCRIPT not in (ROOT / "index.html").read_text(encoding="utf-8")
    [issue] = registry.problems({**COMPLETE, "landing_page": "/index.html"})
    assert "does not load /assets/js/cg-attribution.js" in issue


def test_every_offer_page_can_receive_campaign_traffic() -> None:
    """The pages that sell something keep the tags a campaign link carries."""
    pages = sorted(p for p in (ROOT / "offers").glob("*.html") if p.name != "thank-you.html")
    pages += [ROOT / "store.html", ROOT / "pricing.html", ROOT / "revenue-command.html"]
    missing = [
        str(p.relative_to(ROOT)) for p in pages
        if registry.destination_problem("/" + str(p.relative_to(ROOT)))
    ]
    assert not missing, f"offer pages that would lose campaign attribution: {missing}"


def test_an_approved_campaign_has_an_owner_set_spend_ceiling() -> None:
    """The playbook: no launch without an approved spend ceiling."""
    for ceiling in (None, -1, "500", True):
        [issue] = registry.problems({**COMPLETE, "spend_ceiling_cad": ceiling})
        assert "spend_ceiling_cad" in issue
    assert registry.problems({**COMPLETE, "spend_ceiling_cad": 750}) == []
    draft = {**COMPLETE, "approval_status": "draft", "spend_ceiling_cad": None}
    assert registry.problems(draft) == [], "the owner sets the ceiling when approving, not before"


def test_ad_copy_over_googles_limits_is_caught_before_approval() -> None:
    long_ads = {**COMPLETE, "google_search_ads": [{"headline": "H" * 31, "description": "D" * 91}]}
    assert registry.problems(long_ads) == [
        "google_search_ads[1].headline is over Google's 30-character limit",
        "google_search_ads[1].description is over Google's 90-character limit",
    ]


def test_the_ready_packages_sell_a_real_offer_and_spend_nothing_yet() -> None:
    """Two packages are complete enough for an owner to judge. None is approved,
    and none carries a spend ceiling: approving and funding are the owner's."""
    campaigns = {c["id"]: c for _, c in registry.load()}
    ready = {name for name, c in campaigns.items() if not registry.problems(c)}
    assert ready == {"burlington-cyber-risk-checkup", "m365-account-protection"}
    for name in ready:
        assert campaigns[name]["approval_status"] == "draft"
        assert campaigns[name]["spend_ceiling_cad"] is None
        assert registry.tracked_url(campaigns[name]).startswith(registry.SITE + campaigns[name]["landing_page"])
    for name in set(campaigns) - ready:
        assert campaigns[name].get("blockers"), f"{name} is incomplete and must say why"


def test_tracked_links_carry_the_code_as_utm_campaign() -> None:
    url = registry.tracked_url(COMPLETE)
    assert url == (
        "https://www.clearglassinc.com/revenue-command.html"
        "?utm_source=linkedin&utm_medium=social&utm_campaign=CG-LINKEDIN-SMB-RISKAUDIT-2026-Q4"
    )
    assert registry.tracked_url({**COMPLETE, "campaign_code": "bad"}) is None


def test_the_code_survives_the_control_planes_attribution_filter() -> None:
    """utm_campaign reaches Stripe metadata only if app/attribution.py accepts it."""
    spec = importlib.util.spec_from_file_location(
        "cg_attribution", ROOT / "control-plane" / "app" / "attribution.py"
    )
    attribution = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(attribution)  # type: ignore[union-attr]
    code = COMPLETE["campaign_code"]
    assert attribution.clean({"utm_campaign": code}) == {"utm_campaign": code}


def test_check_blocks_an_incomplete_approved_campaign(tmp_path, monkeypatch, capsys) -> None:
    incomplete = {**COMPLETE, "objective": ""}
    (tmp_path / "c.json").write_text(json.dumps({"campaigns": [incomplete]}))
    monkeypatch.setattr(registry, "CAMPAIGN_DIR", tmp_path)
    assert registry.main(["--check"]) == 1
    assert "missing objective" in capsys.readouterr().out

    (tmp_path / "c.json").write_text(json.dumps({"campaigns": [{**incomplete, "approval_status": "draft"}]}))
    assert registry.main(["--check"]) == 0, "a draft may be incomplete"


def test_the_committed_packages_pass_the_gate() -> None:
    """All committed packages are drafts today, so the gate passes while the
    report lists what each one still needs."""
    assert len(registry.load()) == 5
    assert registry.main(["--check"]) == 0
