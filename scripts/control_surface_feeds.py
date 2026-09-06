#!/usr/bin/env python3
# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Generate the six Control Surface data feeds from real operational sources.

Feeds (contract: docs/control-surface-event-contract.md):
  metrics.json   Metric[]     workflow success rate, deploys, site pages, fleet size
  activity.json  FeedItem[]   recent workflow events, newest first
  pipeline.json  Counter[]    pass-through of owner-maintained pipeline-source.json
  health.json    Health       live site probes + deploy success rate
  alerts.json    AlertItem[]  workflows whose latest completed run failed
  runs.json      FeedItem[]   latest workflow executions

Real mode (CI): GitHub Actions API via GITHUB_TOKEN + live HTTPS probes of the
published site. Offline mode (--offline): deterministic stub inputs through the
same shaping functions — used by tests and local development.

Outputs self-validate against docs/contracts/control-surface-events.schema.json
when jsonschema is importable; with --strict a validation failure (or missing
validator) aborts the run so invalid data is never published.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "control-surface"
SCHEMA_PATH = ROOT / "docs" / "contracts" / "control-surface-events.schema.json"
SITEMAP_PATH = ROOT / "sitemap.xml"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
PIPELINE_SOURCE = OUT_DIR / "pipeline-source.json"

API = "https://api.github.com"
SITE = "https://www.clearglassinc.com"
PROBE_PATHS = ["/", "/saas-platform.html", "/artemis-percival.html", "/percival-os.html"]

ACTIVITY_LIMIT = 12
RUNS_LIMIT = 20


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hhmm(stamp: str) -> str:
    return stamp[11:16] if len(stamp) >= 16 else stamp


# ── transport ─────────────────────────────────────────────────────────────────

def gh_api(path: str, token: str, timeout: int = 15) -> Any:
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "clearglass-control-surface-feeds",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def probe(url: str, timeout: int = 12) -> bool:
    # Allowlist the scheme so a misconfigured/attacker-supplied target can't turn
    # this health probe into a file:// / ftp:// read (CWE-22 / SSRF).
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        return False
    req = urllib.request.Request(url, headers={"User-Agent": "clearglass-health-probe"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 - scheme allowlisted above
            return 200 <= resp.status < 400
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


# ── shaping (pure, unit-tested) ───────────────────────────────────────────────

def status_for(conclusion: str | None) -> str:
    if conclusion == "success":
        return "ok"
    if conclusion in ("failure", "timed_out", "startup_failure"):
        return "bad"
    return "warn"  # cancelled, skipped, neutral, action_required, in flight


def shape_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in runs[:RUNS_LIMIT]:
        stamp = str(r.get("created_at") or "")
        out.append({
            "title": f"{r.get('name', 'Workflow')} #{r.get('run_number', '?')}",
            "status": status_for(r.get("conclusion")),
            "detail": f"{r.get('conclusion') or r.get('status') or 'pending'} · {r.get('event', '?')} on {r.get('head_branch', '?')}",
            "time": hhmm(stamp),
            "timestamp": stamp,
        })
    return out


def shape_activity(runs: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    items = [{
        "title": "Control Surface feeds refreshed",
        "status": "ok",
        "detail": "Data plane regenerated from live sources",
        "time": hhmm(iso(now)),
        "timestamp": iso(now),
    }]
    for r in runs[:ACTIVITY_LIMIT]:
        stamp = str(r.get("created_at") or "")
        items.append({
            "title": str(r.get("name", "Workflow")),
            "status": status_for(r.get("conclusion")),
            "detail": f"{r.get('event', '?')} on {r.get('head_branch', '?')} · run #{r.get('run_number', '?')}",
            "time": hhmm(stamp),
            "timestamp": stamp,
        })
    return items[:50]


def shape_alerts(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for r in runs:
        name = str(r.get("name", ""))
        if name and r.get("status") == "completed" and name not in latest:
            latest[name] = r
    alerts: list[dict[str, Any]] = []
    for name, r in sorted(latest.items()):
        if status_for(r.get("conclusion")) == "bad":
            alerts.append({
                "status": "warn",
                "title": f"{name} failing",
                "detail": f"Latest run #{r.get('run_number', '?')} concluded {r.get('conclusion')} ({str(r.get('created_at') or '')[:10]}).",
            })
    return alerts


def shape_metrics(
    runs: list[dict[str, Any]],
    page_count: int,
    workflow_count: int,
    deploys_7d: tuple[int, int],
    now: datetime,
) -> list[dict[str, Any]]:
    cutoff = now - timedelta(hours=24)
    done = [
        r for r in runs
        if r.get("status") == "completed" and str(r.get("created_at") or "") >= iso(cutoff)
    ]
    green = sum(1 for r in done if r.get("conclusion") == "success")
    rate = round(100 * green / len(done)) if done else 100
    dep_ok, dep_total = deploys_7d
    dep_rate = round(100 * dep_ok / dep_total) if dep_total else 100
    return [
        {"label": "Workflows green (24h)", "value": f"{green}/{len(done)}", "delta": f"{rate}% success rate", "pct": rate},
        {"label": "Pages deploys (7d)", "value": str(dep_total), "delta": f"{dep_rate}% successful", "pct": dep_rate},
        {"label": "Site pages indexed", "value": str(page_count), "delta": "sitemap.xml entries", "pct": min(100, page_count)},
        {"label": "Automation fleet", "value": str(workflow_count), "delta": "active workflows", "pct": min(100, workflow_count * 5)},
    ]


def shape_health(probes: dict[str, bool], deploys_7d: tuple[int, int]) -> dict[str, Any]:
    ok = sum(1 for v in probes.values() if v)
    total = len(probes)
    dep_ok, dep_total = deploys_7d
    uptime = f"{round(100 * dep_ok / dep_total, 2)}%" if dep_total else "100%"
    return {
        "status": "Operational" if ok == total else ("Degraded" if ok else "Outage"),
        "uptime": uptime,
        "detail": f"{ok}/{total} public pages reachable · Pages deploys {dep_ok}/{dep_total} green (7d)",
    }


# ── local repo facts ──────────────────────────────────────────────────────────

def count_site_pages() -> int:
    try:
        return len(re.findall(r"<loc>", SITEMAP_PATH.read_text(encoding="utf-8")))
    except OSError:
        return 0


def count_workflows() -> int:
    return len(list(WORKFLOWS_DIR.glob("*.yml"))) if WORKFLOWS_DIR.exists() else 0


def load_pipeline() -> list[dict[str, Any]]:
    data = json.loads(PIPELINE_SOURCE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("pipeline-source.json must be a Counter[] array")
    return data


# ── collectors ────────────────────────────────────────────────────────────────

def collect_real(token: str, repo: str) -> tuple[list[dict[str, Any]], tuple[int, int], dict[str, bool]]:
    runs = gh_api(f"/repos/{repo}/actions/runs?per_page=100", token).get("workflow_runs", [])
    cutoff = iso(utc_now() - timedelta(days=7))
    pages_runs = [
        r for r in runs
        if r.get("path", "").endswith("pages.yml") and str(r.get("created_at") or "") >= cutoff
    ]
    deploys = (sum(1 for r in pages_runs if r.get("conclusion") == "success"), len(pages_runs))
    probes = {p: probe(SITE + p) for p in PROBE_PATHS}
    return runs, deploys, probes


def collect_offline(now: datetime) -> tuple[list[dict[str, Any]], tuple[int, int], dict[str, bool]]:
    mk = lambda i, name, concl: {  # noqa: E731 — compact stub factory
        "name": name, "run_number": 100 + i, "status": "completed", "conclusion": concl,
        "event": "schedule", "head_branch": "main", "path": f".github/workflows/{name.lower().replace(' ', '-')}.yml",
        "created_at": iso(now - timedelta(minutes=10 * (i + 1))),
    }
    runs = [
        mk(0, "Deploy GitHub Pages", "success"),
        mk(1, "CI", "success"),
        mk(2, "Bot Orchestrator", "success"),
        mk(3, "API Security Audit", "failure"),
        mk(4, "Health Monitor", "success"),
    ]
    runs[0]["path"] = ".github/workflows/pages.yml"
    return runs, (1, 1), {p: True for p in PROBE_PATHS}


# ── validation & output ───────────────────────────────────────────────────────

FEED_DEFS = {
    "metrics.json": "metricsResponse",
    "activity.json": "activityResponse",
    "pipeline.json": "pipelineResponse",
    "health.json": "healthResponse",
    "alerts.json": "alertsResponse",
    "runs.json": "runsResponse",
}


def validate_outputs(outputs: dict[str, Any], strict: bool) -> bool:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        if strict:
            print("ERROR: --strict requires jsonschema (pip install jsonschema)", file=sys.stderr)
            return False
        print("jsonschema unavailable — skipping contract validation")
        return True
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    ok = True
    for fname, def_name in FEED_DEFS.items():
        wrapper = {**schema, "oneOf": [{"$ref": f"#/$defs/{def_name}"}]}
        errors = list(Draft202012Validator(wrapper).iter_errors(outputs[fname]))
        if errors:
            ok = False
            print(f"ERROR: {fname} violates {def_name}: {errors[0].message}", file=sys.stderr)
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="use deterministic stub inputs")
    parser.add_argument("--strict", action="store_true", help="abort unless every feed validates")
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="output directory")
    args = parser.parse_args(argv)

    now = utc_now()
    if args.offline:
        runs, deploys, probes = collect_offline(now)
    else:
        token = os.environ.get("GITHUB_TOKEN", "")
        repo = os.environ.get("GITHUB_REPOSITORY", "ClearGlassInc/ClearGlassInc.github.io")
        if not token:
            print("ERROR: GITHUB_TOKEN is required outside --offline mode", file=sys.stderr)
            return 2
        runs, deploys, probes = collect_real(token, repo)

    outputs: dict[str, Any] = {
        "metrics.json": shape_metrics(runs, count_site_pages(), count_workflows(), deploys, now),
        "activity.json": shape_activity(runs, now),
        "pipeline.json": load_pipeline(),
        "health.json": shape_health(probes, deploys),
        "alerts.json": shape_alerts(runs),
        "runs.json": shape_runs(runs),
    }

    if not validate_outputs(outputs, strict=args.strict):
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    for fname, payload in outputs.items():
        (args.out / fname).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        size = len(payload) if isinstance(payload, list) else 1
        print(f"wrote {fname} ({size} item{'s' if size != 1 else ''})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
