# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
from __future__ import annotations

import csv
import io
import json

from scripts.repo_audit import (
    CSV_FIELDS,
    audit_node_deps,
    audit_python_deps,
    bot_status,
    build_row,
    main,
    rows_to_csv,
    score_repo,
    summarize,
    workflow_health,
)


# ── workflow_health ───────────────────────────────────────────────────────────

def test_workflow_health_latest_per_workflow():
    runs = [
        {"name": "CI", "status": "completed", "conclusion": "success"},
        {"name": "CI", "status": "completed", "conclusion": "failure"},   # older dup ignored
        {"name": "Deploy", "status": "completed", "conclusion": "failure"},
        {"name": "Nightly", "status": "in_progress", "conclusion": None},  # not completed
    ]
    h = workflow_health(runs)
    assert h["workflows_completed"] == 2          # CI + Deploy
    assert h["success_rate"] == 50
    assert h["failing"] == ["Deploy"]


def test_workflow_health_empty_is_perfect():
    h = workflow_health([])
    assert h["success_rate"] == 100 and h["failing"] == []
    assert h["last_successful_execution"] is None
    assert h["failure_evidence"] == []


def test_workflow_health_preserves_execution_evidence():
    h = workflow_health([
        {"name": "CI", "status": "completed", "conclusion": "success", "created_at": "2026-07-25T10:00:00Z"},
        {"name": "Deploy", "status": "completed", "conclusion": "failure", "created_at": "2026-07-26T10:00:00Z", "html_url": "https://example.test/run/7"},
    ])
    assert h["last_successful_execution"] == "2026-07-25T10:00:00Z"
    assert h["last_failed_execution"] == "2026-07-26T10:00:00Z"
    assert h["failure_evidence"] == ["https://example.test/run/7"]


# ── bot_status ──────────────────────────────────────────────────────────────

def test_bot_status_thresholds():
    assert bot_status(100, 3) == "healthy"
    assert bot_status(90, 3) == "healthy"
    assert bot_status(75, 3) == "degraded"
    assert bot_status(10, 3) == "failing"
    assert bot_status(100, 0) == "none"
    assert bot_status(100, 3, 0) == "unverified"


# ── dependency audits ─────────────────────────────────────────────────────────

def test_audit_python_deps_classifies():
    r = audit_python_deps("pytest==8.0\nrequests>=2,<3\nflask\n# comment\n-r other.txt\n")
    assert r["pinned"] == 2
    assert r["unpinned"] == 1
    assert r["offenders"] == ["flask"]


def test_audit_node_deps_flags_moving_targets():
    r = audit_node_deps('{"dependencies":{"a":"^1.0.0","b":"*"},"devDependencies":{"c":"latest"}}')
    assert r["deps"] == 3
    assert r["risky"] == 2
    assert r["offenders"] == ["b", "c"]


def test_audit_node_deps_bad_json():
    assert audit_node_deps("not json")["deps"] == 0


# ── scoring ───────────────────────────────────────────────────────────────────

def test_score_repo_grades():
    assert score_repo(5, 100, 0, 0)["grade"] == "A"
    failing = score_repo(5, 0, 0, 0)
    assert failing["score"] == 50 and failing["grade"] == "F"
    assert score_repo(0, 100, 0, 0)["score"] == 75   # no workflows → -25
    assert score_repo(5, 100, 0, 0, completed_count=0)["score"] == 75


def test_score_repo_clamped():
    assert 0 <= score_repo(0, 0, 9, 9)["score"] <= 100


# ── row + csv + summary ───────────────────────────────────────────────────────

def _row():
    return build_row(
        "demo", 2,
        workflow_health([{"name": "CI", "status": "completed", "conclusion": "success"}]),
        audit_python_deps("flask"),
        audit_node_deps("{}"),
    )


def test_build_row_shape():
    row = _row()
    assert set(row) == set(CSV_FIELDS)
    assert row["bot_status"] in {"healthy", "degraded", "failing", "none", "unverified"}
    assert row["current_status"] == "RUNNING_BUT_UNVERIFIED"


def test_build_row_never_claims_live_from_workflow_success():
    row = build_row("demo", 1, workflow_health([
        {"name": "CI", "status": "completed", "conclusion": "success"}
    ]), audit_python_deps(""), audit_node_deps("{}"))
    assert row["current_status"] == "RUNNING_BUT_UNVERIFIED"
    assert row["last_successful_execution"] == "UNVERIFIED"


def test_rows_to_csv_roundtrip():
    text = rows_to_csv([_row()])
    parsed = list(csv.DictReader(io.StringIO(text)))
    assert len(parsed) == 1
    assert parsed[0]["repo"] == "demo"


def test_summarize_counts():
    s = summarize([
        build_row("a", 1, workflow_health([{"name": "CI", "status": "completed", "conclusion": "failure"}]),
                  audit_python_deps("flask"), audit_node_deps("{}")),
        build_row("b", 1, workflow_health([{"name": "CI", "status": "completed", "conclusion": "success"}]),
                  audit_python_deps("pytest==8"), audit_node_deps("{}")),
    ])
    assert s["repos_audited"] == 2
    assert s["repos_with_failing_ci"] == 1
    assert s["repos_with_unpinned_deps"] == 1
    assert s["repos_without_execution_evidence"] == 2
    assert sum(s["grade_distribution"].values()) == 2


# ── end-to-end ────────────────────────────────────────────────────────────────

def test_offline_run_writes_reports(tmp_path):
    rc = main(["--offline", "--out", str(tmp_path)])
    assert rc == 0
    rows = list(csv.DictReader(io.StringIO((tmp_path / "repo_audit.csv").read_text())))
    assert {r["repo"] for r in rows} == {"repo-green", "repo-degraded"}
    doc = json.loads((tmp_path / "repo_audit.json").read_text())
    assert doc["summary"]["repos_audited"] == 2
    assert "repos" in doc


def test_self_run_audits_this_repo(tmp_path):
    rc = main(["--self", "--out", str(tmp_path)])
    assert rc == 0
    doc = json.loads((tmp_path / "repo_audit.json").read_text())
    assert doc["summary"]["repos_audited"] == 1
    row = doc["repos"][0]
    assert row["workflows"] >= 1          # this repo has workflows
    assert row["py_deps_pinned"] >= 1     # requirements.txt is pinned
