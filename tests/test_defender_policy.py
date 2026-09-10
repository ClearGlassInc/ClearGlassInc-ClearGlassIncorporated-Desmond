# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for bots/defender/policy.py."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bots.defender.engine import Finding  # noqa: E402
from bots.defender.policy import (  # noqa: E402
    DEFAULT_POLICY_PATH,
    is_allowlisted,
    load_policy,
    max_severity,
    rank,
    response_actions,
    response_plan,
    severity_counts,
    should_fail_build,
    should_open_issue,
)


def _f(severity: str, rule_id: str = "r", file: str = "") -> Finding:
    return Finding(rule_id=rule_id, category="workflow", severity=severity,
                   title="t", detail="d", file=file)


class TestLoadPolicy:
    def test_default_policy_loads(self) -> None:
        policy = load_policy()
        assert policy["version"]
        assert "secret_patterns" in policy
        assert "workflow_rules" in policy
        assert policy["enforcement"]["fail_build_on"] == ["critical"]

    def test_default_path_points_at_config(self) -> None:
        assert DEFAULT_POLICY_PATH.name == "defender_policy.json"
        assert DEFAULT_POLICY_PATH.exists()


class TestRank:
    def test_ordering(self) -> None:
        assert rank("critical") > rank("high") > rank("medium") > rank("low") > rank("info")

    def test_unknown_is_lowest(self) -> None:
        assert rank("bogus") == 0

    def test_max_severity(self) -> None:
        assert max_severity([_f("low"), _f("high"), _f("medium")]) == "high"
        assert max_severity([]) == "info"


class TestAllowlist:
    POLICY = {"scan": {"allowlist_paths": [
        "downloads/", "**/*.example.json", "tests/", "secret/endpoints.json",
    ]}}

    def test_directory_prefix(self) -> None:
        assert is_allowlisted("downloads/tool.ps1", self.POLICY)
        assert is_allowlisted("downloads", self.POLICY)

    def test_glob(self) -> None:
        assert is_allowlisted("a/b/config.example.json", self.POLICY)

    def test_exact(self) -> None:
        assert is_allowlisted("secret/endpoints.json", self.POLICY)

    def test_not_allowlisted(self) -> None:
        assert not is_allowlisted("scripts/deploy.sh", self.POLICY)


class TestResponseActions:
    POLICY = {"severity_actions": {
        "critical": ["quarantine_for_review", "alert_owner"],
        "high": ["require_review"],
    }}

    def test_actions_for_severity(self) -> None:
        assert response_actions("critical", self.POLICY) == ["quarantine_for_review", "alert_owner"]
        assert response_actions("low", self.POLICY) == []

    def test_plan_dedup_and_orders_by_severity(self) -> None:
        findings = [_f("high"), _f("critical")]
        plan = response_plan(findings, self.POLICY)
        # critical actions come first, no duplicates
        assert plan == ["quarantine_for_review", "alert_owner", "require_review"]


class TestSeverityCounts:
    def test_counts_include_all_labels(self) -> None:
        counts = severity_counts([_f("high"), _f("high"), _f("critical")])
        assert counts == {"critical": 1, "high": 2, "medium": 0, "low": 0, "info": 0}


class TestGates:
    POLICY = {"enforcement": {"fail_build_on": ["critical"], "open_issue_on": ["critical", "high"]}}

    def test_fail_build_only_on_critical(self) -> None:
        assert should_fail_build([_f("critical")], self.POLICY) is True
        assert should_fail_build([_f("high"), _f("medium")], self.POLICY) is False

    def test_open_issue_on_critical_or_high(self) -> None:
        assert should_open_issue([_f("high")], self.POLICY) is True
        assert should_open_issue([_f("medium")], self.POLICY) is False
