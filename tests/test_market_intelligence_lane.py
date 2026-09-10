"""Tests for the Market Intelligence lane runner (scripts/market_intelligence_lane.py).

Verifies the governed, no-fabrication contract: the lane produces a structured
delta *scaffold* whose every intelligence field is an explicit unverified
placeholder, computes real watchlist deltas, and stays READ_ONLY.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "scripts" / "market_intelligence_lane.py"

_spec = importlib.util.spec_from_file_location("market_intelligence_lane", MODULE_PATH)
mil = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mil)


NOW = dt.datetime(2026, 8, 1, 13, 0, 0)


def _config():
    return {
        "topics": ["governed AI", "agent security"],
        "competitors": [{"name": "Acme Sec"}, {"name": ""}],
        "emerging_keywords_seed": ["agent insider risk"],
        "sources": [{"kind": "search_trends", "query": "x"}],
    }


def test_config_on_disk_is_valid_json():
    cfg = mil._load_config()
    assert isinstance(cfg["topics"], list) and cfg["topics"], "watchlist must list topics"
    assert cfg["governance"]["no_fabrication"] is True


def test_report_is_a_governed_readonly_draft():
    report = mil.build_report(_config(), None, NOW)
    gov = report["governance"]
    assert gov["authority"] == "READ_ONLY"
    assert gov["tier"] == "low"
    assert gov["no_fabrication"] is True
    assert "not published" in gov["status"]
    assert report["report_type"] == "weekly_delta_scaffold"


def test_every_intelligence_field_is_unverified_placeholder():
    """No fabrication: signals/moves/trends must all be explicit placeholders."""
    report = mil.build_report(_config(), None, NOW)
    for opp in report["opportunities"]:
        assert opp["signal"] == mil.UNVERIFIED
        assert opp["why_it_matters"] == mil.UNVERIFIED
        assert opp["confidence"] == "assumed"
    for c in report["competitive_intel"]:
        assert c["observed_move"] == mil.UNVERIFIED
    for kw in report["emerging_keywords"]:
        assert kw["trend"] == mil.UNVERIFIED


def test_empty_names_are_dropped():
    report = mil.build_report(_config(), None, NOW)
    # the {"name": ""} competitor must not appear
    assert report["watchlist_snapshot"]["competitors"] == ["Acme Sec"]


def test_delta_against_previous_report():
    prev = mil.build_report(_config(), None, NOW)
    changed = _config()
    changed["topics"] = ["governed AI", "new topic"]  # drop "agent security", add "new topic"
    report = mil.build_report(changed, prev, NOW)
    d = report["delta_since_last_report"]["topics"]
    assert d["added"] == ["new topic"]
    assert d["removed"] == ["agent security"]
    assert report["delta_since_last_report"]["previous_report_at"] == prev["generated_at"]


def test_markdown_renders_and_flags_scaffold():
    report = mil.build_report(_config(), None, NOW)
    md = mil.render_markdown(report)
    assert "Weekly Delta" in md
    assert mil.UNVERIFIED in md
    assert "not published" in md


def test_write_report_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(mil, "OUT_DIR", tmp_path)
    report = mil.build_report(_config(), None, NOW)
    md = mil.render_markdown(report)
    written = mil.write_report(report, md, NOW)
    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "latest.md").exists()
    # dated snapshot present
    assert any("2026-08-01" in p.name for p in written)
    # latest.json is valid JSON and round-trips
    reloaded = json.loads((tmp_path / "latest.json").read_text())
    assert reloaded["iso_week"] == report["iso_week"]
