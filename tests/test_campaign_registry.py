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
