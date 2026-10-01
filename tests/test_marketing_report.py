"""The executive marketing report states only what the repository proves.

``tools/marketing_report.py`` is the command centre's data: campaign
readiness, the analytics switch, the lead form, the funnel and its blockers.
Everything it cannot see is ``NOT VERIFIED``. The first draft of it read the
example ``provider: "ga4"`` in ``analytics.js``'s header comment and reported
analytics as on; these tests pin the switch to the live ``CONFIG`` object.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("marketing_report", ROOT / "tools" / "marketing_report.py")
report_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(report_tool)  # type: ignore[union-attr]

SECTIONS = (
    "## CURRENT STATE", "## VERIFIED SIGNALS", "## MARKET OPPORTUNITIES", "## ACTIVE CAMPAIGNS",
    "## CONVERSION FUNNEL", "## BLOCKERS", "## EXPERIMENTS", "## NEXT ACTIONS", "## REVENUE EVIDENCE",
)


def test_the_committed_state_is_reported_as_it_is() -> None:
    report = report_tool.collect()
    state = report["current_state"]
    assert state["analytics"] == "OFF", "the header comment's example must not read as analytics being on"
    assert state["attributed_lead_form"] == "OFF"
    assert (state["campaigns"], state["ready_for_approval"], state["approved_or_active"]) == (5, 2, 0)
    assert "revenue-command.html" in state["pages_keeping_campaign_tags"]
    assert report["revenue_evidence"]["state"] == "NOT VERIFIED"
    assert report["market_opportunities"] == [] and report["experiments"] == []


def test_the_report_has_every_executive_section_and_claims_no_results() -> None:
    text = report_tool.render(report_tool.collect())
    for heading in SECTIONS:
        assert heading in text
    lowered = text.lower()
    for claim in ("leads generated", "revenue generated", "campaign successful", "viral"):
        assert claim not in lowered
    assert "No campaign is approved and no spend is authorized." in text


def test_the_analytics_switch_is_read_from_config_only(tmp_path, monkeypatch) -> None:
    js = tmp_path / "analytics.js"
    monkeypatch.setattr(report_tool, "ANALYTICS", js)
    header = '/* set:\n       provider: "ga4",  measurementId: "G-X" */\n'
    js.write_text(header + 'var CONFIG = {\n    provider: "",\n    domain: "x"\n  };')
    assert report_tool.analytics_provider() == ""
    js.write_text(header + 'var CONFIG = {\n    provider: "Plausible",\n    domain: "x"\n  };')
    assert report_tool.analytics_provider() == "plausible"


def test_an_approved_campaign_is_listed_with_its_ceiling(tmp_path, monkeypatch) -> None:
    packages = json.loads((ROOT / "data" / "campaigns" / "burlington-campaign-packages.json").read_text())
    approved = {**packages["campaigns"][0], "approval_status": "approved", "spend_ceiling_cad": 300}
    (tmp_path / "c.json").write_text(json.dumps({"campaigns": [approved]}))
    monkeypatch.setattr(report_tool.campaign_registry, "CAMPAIGN_DIR", tmp_path)
    text = report_tool.render(report_tool.collect())
    assert "- burlington-cyber-risk-checkup (CG-LINKEDIN-BURLSMB-QUICKAUDIT-2026-Q4), ceiling CAD 300" in text


def test_json_output_is_the_same_report(capsys) -> None:
    assert report_tool.main(["--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert set(data) >= {"current_state", "conversion_funnel", "blockers", "next_actions", "revenue_evidence"}
