# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for bots/defender/alerting.py (fully offline)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bots.defender import alerting  # noqa: E402
from bots.defender.engine import DefenderReport, Finding  # noqa: E402

POLICY = {"enforcement": {"open_issue_on": ["critical"]},
          "severity_actions": {"critical": ["alert_owner"]}}


def _report(*findings: Finding) -> DefenderReport:
    return DefenderReport(
        run_utc="2026-01-01T00:00:00+00:00", repo="acme/site", scanned_files=10,
        summary={"critical": sum(f.severity == "critical" for f in findings),
                 "high": sum(f.severity == "high" for f in findings),
                 "medium": 0, "low": 0, "info": 0},
        response_plan=["alert_owner"], fail_build=False, findings=list(findings),
    )


@pytest.fixture(autouse=True)
def _no_channel_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("GITHUB_TOKEN", "SLACK_WEBHOOK_URL", "DISCORD_WEBHOOK_URL"):
        monkeypatch.delenv(var, raising=False)


class TestAlertable:
    def test_filters_by_open_issue_on(self) -> None:
        report = _report(
            Finding("a", "secret", "critical", "t", "d"),
            Finding("b", "workflow", "high", "t", "d"),
        )
        alertable = alerting._alertable(report, POLICY)
        assert [f.severity for f in alertable] == ["critical"]


class TestDispatch:
    def test_offline_no_op_writes_manifest(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(alerting, "OUTPUT_DIR", tmp_path)
        report = _report(Finding("a", "secret", "critical", "Secret", "d", "x.py", 3))
        manifest = alerting.dispatch(report, POLICY)
        assert manifest["alertable_findings"] == 1
        assert manifest["channels"] == {"github_issue": False, "slack": False, "discord": False}
        written = json.loads((tmp_path / "alerts.json").read_text())
        assert written["alertable_findings"] == 1

    def test_high_only_with_critical_gate_is_silent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(alerting, "OUTPUT_DIR", tmp_path)
        report = _report(Finding("b", "workflow", "high", "t", "d", "w.yml"))
        manifest = alerting.dispatch(report, POLICY)
        assert manifest["alertable_findings"] == 0
        assert not any(manifest["channels"].values())


class TestIssueBody:
    def test_body_lists_rules_and_keeps_redaction(self) -> None:
        findings = [Finding("aws_access_key_id", "secret", "critical", "AWS key",
                            "d", "x.py", 3, evidence="AKIA…LE (redacted)")]
        report = _report(*findings)
        body = alerting._issue_body(report, findings)
        assert "aws_access_key_id" in body
        assert "x.py:3" in body
        assert "redacted" in body  # evidence stays masked in the issue
        assert "branch protection" in body.lower()  # advisory framing preserved
