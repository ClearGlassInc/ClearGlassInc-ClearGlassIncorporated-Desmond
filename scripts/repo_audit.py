#!/usr/bin/env python3
# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""ClearGlass multi-repo audit pack.

Discovers repositories, then audits each for workflow health, dependency
hygiene, and bot/automation status — emitting a machine-readable CSV + JSON
so "patched / clean / actively executing" is measurable per repo.

Modes
  --self            Audit the current checkout only (no network). Default.
  --org OWNER       Discover + audit every repo in an org/user via the GitHub
                    REST API (requires GITHUB_TOKEN in the environment).
  --offline         Deterministic stub inputs through the same shaping
                    functions — used by the test suite.

Output (default audit-reports/)
  repo_audit.csv    one row per repo: workflows, success rate, dep findings,
                    bot status, score, grade
  repo_audit.json   same data, structured, plus a portfolio summary

Auth: GITHUB_TOKEN is read from the environment only. This tool never reads
token files and never runs `gh auth login` — keep secrets in CI secrets.
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com"
DEFAULT_OUT = ROOT / "audit-reports"
RUN_SAMPLE = 50

# ── transport ───────────────────────────────────────────────────────────────


def _get(path: str, token: str, timeout: int = 20) -> Any:
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "clearglass-repo-audit",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def discover_repos(owner: str, token: str) -> list[dict[str, Any]]:
    """List every non-archived repo for an org (falling back to a user)."""
    repos: list[dict[str, Any]] = []
    for kind in ("orgs", "users"):
        try:
            page = 1
            while True:
                batch = _get(f"/{kind}/{owner}/repos?per_page=100&page={page}", token)
                if not batch:
                    break
                repos.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
            if repos:
                return [r for r in repos if not r.get("archived")]
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and kind == "orgs":
                continue  # not an org — try as a user
            raise
    return repos


def fetch_text(owner: str, repo: str, path: str, token: str) -> str | None:
    try:
        data = _get(f"/repos/{owner}/{repo}/contents/{path}", token)
    except (urllib.error.URLError, OSError):
        return None
    if isinstance(data, dict) and data.get("encoding") == "base64":
        try:
            return base64.b64decode(data["content"]).decode("utf-8", "replace")
        except Exception:
            return None
    return None


# ── shaping (pure, unit-tested) ───────────────────────────────────────────────


def workflow_health(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Latest-per-workflow conclusion → success rate + failing names."""
    latest: dict[str, dict[str, Any]] = {}
    for r in runs:
        name = str(r.get("name") or r.get("path") or "")
        if name and r.get("status") == "completed" and name not in latest:
            latest[name] = r
    total = len(latest)
    green = sum(1 for r in latest.values() if r.get("conclusion") == "success")
    failing = sorted(
        name for name, r in latest.items()
        if r.get("conclusion") in ("failure", "timed_out", "startup_failure")
    )
    rate = round(100 * green / total) if total else 100
    successful_runs = [r for r in latest.values() if r.get("conclusion") == "success"]
    failed_runs = [
        r for r in latest.values()
        if r.get("conclusion") in ("failure", "timed_out", "startup_failure")
    ]

    def newest_timestamp(items: list[dict[str, Any]]) -> str | None:
        timestamps = [str(r["created_at"]) for r in items if r.get("created_at")]
        return max(timestamps, default=None)

    failure_evidence = sorted(
        {
            str(r.get("html_url") or r.get("name") or r.get("path"))
            for r in failed_runs
            if r.get("html_url") or r.get("name") or r.get("path")
        }
    )
    return {
        "workflows_completed": total,
        "success_rate": rate,
        "failing": failing,
        "last_successful_execution": newest_timestamp(successful_runs),
        "last_failed_execution": newest_timestamp(failed_runs),
        "failure_evidence": failure_evidence,
    }


def bot_status(success_rate: int, workflow_count: int, completed_count: int | None = None) -> str:
    if workflow_count == 0:
        return "none"
    if completed_count == 0:
        return "unverified"
    if success_rate >= 90:
        return "healthy"
    if success_rate >= 50:
        return "degraded"
    return "failing"


_REQ_LINE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*(.*)$")


def audit_python_deps(text: str) -> dict[str, Any]:
    """Classify requirements.txt lines: pinned (==/range) vs unpinned (bare)."""
    pinned = unpinned = 0
    offenders: list[str] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = _REQ_LINE.match(line)
        if not m:
            continue
        name, spec = m.group(1), m.group(2)
        if any(op in spec for op in ("==", ">=", "<=", "~=", ">", "<")):
            pinned += 1
        else:
            unpinned += 1
            offenders.append(name)
    return {"pinned": pinned, "unpinned": unpinned, "offenders": offenders}


def audit_node_deps(package_json: str) -> dict[str, Any]:
    """Flag node deps pinned to a moving target ('*' or 'latest')."""
    try:
        pkg = json.loads(package_json)
    except (json.JSONDecodeError, TypeError):
        return {"deps": 0, "risky": 0, "offenders": []}
    deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies"):
        section = pkg.get(key)
        if isinstance(section, dict):
            deps.update(section)
    offenders = [n for n, v in deps.items() if str(v).strip() in ("*", "latest", "")]
    return {"deps": len(deps), "risky": len(offenders), "offenders": sorted(offenders)}


def score_repo(
    workflow_count: int,
    success_rate: int,
    unpinned: int,
    risky_node: int,
    completed_count: int | None = None,
) -> dict[str, Any]:
    """Composite 0–100 health score → letter grade."""
    score = 100
    if workflow_count == 0:
        score -= 25
    elif completed_count == 0:
        score -= 25  # absence of run evidence must not receive a perfect score
    score -= (100 - success_rate) // 2          # up to -50 for all-red CI
    score -= min(20, unpinned * 5)              # dependency drift
    score -= min(15, risky_node * 5)
    score = max(0, min(100, score))
    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 55 else "F"
    return {"score": score, "grade": grade}


def build_row(repo: str, workflow_count: int, wf: dict[str, Any], py: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    sr = wf["success_rate"]
    completed = wf["workflows_completed"]
    sc = score_repo(workflow_count, sr, py["unpinned"], node["risky"], completed)
    evidence_status = bot_status(sr, workflow_count, completed)
    current_status = (
        "DISABLED" if workflow_count == 0
        else "RUNNING_BUT_UNVERIFIED" if completed == 0 or sr >= 90
        else "CODE_FAILURE"
    )
    return {
        "repo": repo,
        "workflows": workflow_count,
        "workflows_completed": wf["workflows_completed"],
        "success_rate_pct": sr,
        "failing_workflows": ";".join(wf["failing"]) or "-",
        "py_deps_pinned": py["pinned"],
        "py_deps_unpinned": py["unpinned"],
        "node_deps": node["deps"],
        "node_deps_risky": node["risky"],
        "bot_status": evidence_status,
        "current_status": current_status,
        "last_successful_execution": wf.get("last_successful_execution") or "UNVERIFIED",
        "last_failed_execution": wf.get("last_failed_execution") or "UNVERIFIED",
        "exact_failure_evidence": ";".join(wf.get("failure_evidence", [])) or "UNVERIFIED",
        "score": sc["score"],
        "grade": sc["grade"],
    }


CSV_FIELDS = [
    "repo", "workflows", "workflows_completed", "success_rate_pct", "failing_workflows",
    "py_deps_pinned", "py_deps_unpinned", "node_deps", "node_deps_risky",
    "bot_status", "current_status", "last_successful_execution", "last_failed_execution",
    "exact_failure_evidence", "score", "grade",
]


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    w.writeheader()
    for row in rows:
        w.writerow(row)
    return buf.getvalue()


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    avg = round(sum(r["score"] for r in rows) / n) if n else 0
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repos_audited": n,
        "avg_score": avg,
        "repos_with_failing_ci": sum(1 for r in rows if r["current_status"] == "CODE_FAILURE"),
        "repos_without_execution_evidence": sum(
            1 for r in rows if r["last_successful_execution"] == "UNVERIFIED"
        ),
        "repos_with_unpinned_deps": sum(1 for r in rows if r["py_deps_unpinned"] or r["node_deps_risky"]),
        "grade_distribution": {g: sum(1 for r in rows if r["grade"] == g) for g in "ABCDF"},
    }


# ── collectors ────────────────────────────────────────────────────────────────


def audit_local(root: Path) -> dict[str, Any]:
    """Audit the current checkout without any network calls."""
    wf_dir = root / ".github" / "workflows"
    workflow_count = len(list(wf_dir.glob("*.y*ml"))) if wf_dir.exists() else 0
    req = root / "requirements.txt"
    py = audit_python_deps(req.read_text(encoding="utf-8")) if req.exists() else {"pinned": 0, "unpinned": 0, "offenders": []}
    pkg = root / "package.json"
    node = audit_node_deps(pkg.read_text(encoding="utf-8")) if pkg.exists() else {"deps": 0, "risky": 0, "offenders": []}
    # No API in self mode → CI health unknown; report neutrally.
    wf = workflow_health([])
    return build_row(root.name, workflow_count, wf, py, node)


def audit_remote(owner: str, repo: str, token: str) -> dict[str, Any]:
    try:
        wf_list = _get(f"/repos/{owner}/{repo}/actions/workflows", token)
        workflow_count = wf_list.get("total_count", 0) if isinstance(wf_list, dict) else 0
    except (urllib.error.URLError, OSError):
        workflow_count = 0
    try:
        runs = _get(f"/repos/{owner}/{repo}/actions/runs?per_page={RUN_SAMPLE}", token).get("workflow_runs", [])
    except (urllib.error.URLError, OSError):
        runs = []
    wf = workflow_health(runs)
    req_text = fetch_text(owner, repo, "requirements.txt", token) or ""
    pkg_text = fetch_text(owner, repo, "package.json", token) or ""
    py = audit_python_deps(req_text)
    node = audit_node_deps(pkg_text)
    return build_row(repo, workflow_count, wf, py, node)


def collect_offline() -> list[dict[str, Any]]:
    runs_a = [{"name": "CI", "status": "completed", "conclusion": "success"},
              {"name": "Deploy", "status": "completed", "conclusion": "success"}]
    runs_b = [{"name": "CI", "status": "completed", "conclusion": "failure"},
              {"name": "Nightly", "status": "completed", "conclusion": "success"}]
    a = build_row("repo-green", 2, workflow_health(runs_a),
                  audit_python_deps("pytest==8.0\nrequests>=2,<3"), audit_node_deps("{}"))
    b = build_row("repo-degraded", 2, workflow_health(runs_b),
                  audit_python_deps("flask\nrequests"), audit_node_deps('{"dependencies":{"left-pad":"*"}}'))
    return [a, b]


# ── main ──────────────────────────────────────────────────────────────────────


def run(mode: str, owner: str, out_dir: Path) -> dict[str, Any]:
    if mode == "offline":
        rows = collect_offline()
    elif mode == "org":
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise SystemExit("ERROR: --org mode requires GITHUB_TOKEN in the environment")
        repos = discover_repos(owner, token)
        rows = [audit_remote(owner, r["name"], token) for r in repos]
    else:  # self
        rows = [audit_local(ROOT)]
    rows.sort(key=lambda r: r["score"])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "repo_audit.csv").write_text(rows_to_csv(rows), encoding="utf-8")
    summary = summarize(rows)
    (out_dir / "repo_audit.json").write_text(
        json.dumps({"summary": summary, "repos": rows}, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--self", dest="mode", action="store_const", const="self", help="audit current checkout (default)")
    g.add_argument("--org", metavar="OWNER", help="discover + audit all repos in an org/user")
    g.add_argument("--offline", dest="mode", action="store_const", const="offline", help="deterministic stub inputs (tests)")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    args = p.parse_args(argv)

    mode = "org" if args.org else (args.mode or "self")
    summary = run(mode, args.org or "", args.out)
    print(json.dumps(summary, indent=2))
    print(f"\nWrote {args.out / 'repo_audit.csv'} and {args.out / 'repo_audit.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
