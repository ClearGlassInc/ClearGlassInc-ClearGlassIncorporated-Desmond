# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for bots/alert_dispatcher_bot.py."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bots.alert_dispatcher_bot import (  # noqa: E402
    CONSECUTIVE_FAILURE_THRESHOLD,
    Alert,
    _check_orchestrator,
    _check_run_log,
    _check_site_health,
    _create_github_issue,
    run,
)


class TestAlert:
    def test_dataclass_construction(self) -> None:
        a = Alert(
            severity="critical", source="site_health",
            message="down", detail="{}", detected_utc="2026-01-01T00:00:00+00:00",
        )
        assert a.severity == "critical"
        assert a.source == "site_health"


class TestCheckSiteHealth:
    def test_healthy_yields_no_alerts(self) -> None:
        assert _check_site_health({"overall_healthy": True}) == []

    def test_unreachable_pages_yield_critical(self) -> None:
        data = {
            "overall_healthy": False,
            "pages_unreachable": 1,
            "pages": [{"path": "/down", "reachable": False}],
        }
        alerts = _check_site_health(data)
        assert any(a.severity == "critical" for a in alerts)
        assert "/down" in alerts[0].message

    def test_local_issues_yield_warnings(self) -> None:
        data = {
            "overall_healthy": False,
            "pages_unreachable": 0,
            "local_issues": ["missing robots.txt"],
        }
        alerts = _check_site_health(data)
        assert alerts and all(a.severity == "warning" for a in alerts)


class TestCheckOrchestrator:
    def test_no_failures_yields_no_alerts(self) -> None:
        assert _check_orchestrator({"failed": 0}) == []

    def test_failures_yield_warning(self) -> None:
        data = {
            "failed": 2,
            "bots": [
                {"bot_id": "alpha", "status": "error"},
                {"bot_id": "beta", "status": "error"},
                {"bot_id": "gamma", "status": "ok"},
            ],
        }
        alerts = _check_orchestrator(data)
        assert len(alerts) == 1
        assert alerts[0].severity == "warning"
        assert "alpha" in alerts[0].message and "beta" in alerts[0].message


class TestCheckRunLog:
    def test_consecutive_failures_yield_critical(self) -> None:
        entries = [
            {"bot": "x", "status": "error"} for _ in range(CONSECUTIVE_FAILURE_THRESHOLD)
        ]
        alerts = _check_run_log(entries)
        assert any(a.severity == "critical" for a in alerts)

    def test_mixed_statuses_yield_no_alert(self) -> None:
        entries = [
            {"bot": "x", "status": "ok"},
            {"bot": "x", "status": "error"},
            {"bot": "x", "status": "ok"},
        ]
        assert _check_run_log(entries) == []


class TestCreateGithubIssue:
    def test_no_token_returns_false(self) -> None:
        with patch.dict("os.environ", {"GITHUB_TOKEN": ""}, clear=False):
            critical = Alert("critical", "x", "m", "", "t")
            assert _create_github_issue([critical]) is False

    def test_no_critical_returns_false(self) -> None:
        with patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}, clear=False):
            warning = Alert("warning", "x", "m", "", "t")
            assert _create_github_issue([warning]) is False


class TestRun:
    def test_run_writes_manifest(self, tmp_path: Path) -> None:
        out = tmp_path / "output"
        with patch("bots.alert_dispatcher_bot.OUTPUT_DIR", out):
            manifest = run()
        assert (out / "alerts.json").exists()
        assert manifest["total_alerts"] == manifest["critical"] + manifest["warnings"]
        assert manifest["github_issue_created"] is False
