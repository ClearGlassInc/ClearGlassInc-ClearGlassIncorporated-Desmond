from __future__ import annotations

import json

import pytest

from bots.burlington_exposure_automation import build_report, run_agents, validate_snapshot


SNAPSHOT = {
    "gbp_impressions": 100,
    "gbp_actions": 10,
    "local_sessions": 40,
    "qualified_leads": 2,
    "social_followers": 200,
    "social_engagements": 20,
    "grid_green_cells": 8,
    "grid_total_cells": 25,
}


def test_snapshot_rejects_personal_or_unknown_fields() -> None:
    with pytest.raises(ValueError, match="unsupported snapshot fields"):
        validate_snapshot({**SNAPSHOT, "customer_email": "person@example.com"})


def test_snapshot_rejects_impossible_grid() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        validate_snapshot({**SNAPSHOT, "grid_green_cells": 26})


def test_report_is_evidence_cautious() -> None:
    report = build_report(SNAPSHOT, {**SNAPSHOT, "local_sessions": 50}, "2026_07")
    assert "local_sessions | 40 | 50 | +25.0%" in report
    assert "do not attribute causation" in report


def test_agents_generate_report_and_non_mutating_manifest(tmp_path) -> None:
    results = run_agents(tmp_path, SNAPSHOT, SNAPSHOT, "2026_07")
    manifest = json.loads((tmp_path / "run-manifest.json").read_text())
    assert (tmp_path / "BURLINGTON_GROWTH_REPORT_2026_07.md").exists()
    assert results[0].status == "completed"
    assert manifest["external_mutations"] is False
    assert manifest["mode"] == "analysis_and_draft_only"
