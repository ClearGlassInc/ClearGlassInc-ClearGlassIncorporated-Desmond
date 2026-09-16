#!/usr/bin/env python3
"""Conservative GitHub Actions self-healing controller."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / ".github" / "auto-heal"
PATTERNS_PATH = CONTROL / "error-patterns.json"
STRATEGIES_PATH = CONTROL / "healing-strategies.json"
HISTORY_PATH = CONTROL / "run-history.json"
FLAKY_PATH = CONTROL / "flaky-tests.json"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
API_URL = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
TARGET_RUN_ID = os.environ.get("AUTO_HEAL_RUN_ID", "").strip()
SELF_WORKFLOW = os.environ.get("AUTO_HEAL_WORKFLOW_NAME", "Auto Heal")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def api(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    if not TOKEN or not REPOSITORY:
        raise RuntimeError("GITHUB_TOKEN and GITHUB_REPOSITORY are required")
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{API_URL}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "clearglass-auto-heal/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = response.read()
        ctype = response.headers.get("content-type", "")
        if not raw:
            return None
        if "json" in ctype:
            return json.loads(raw.decode("utf-8"))
        return raw.decode("utf-8", errors="replace")


def try_api(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    try:
        return api(method, path, payload)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"API {method} {path} failed: HTTP {exc.code}: {detail[:500]}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"API {method} {path} failed: {exc}", file=sys.stderr)
        return None


def write_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def compile_patterns(config: dict[str, Any]) -> list[tuple[re.Pattern[str], dict[str, Any]]]:
    compiled: list[tuple[re.Pattern[str], dict[str, Any]]] = []
    for item in config.get("patterns", []):
        try:
            compiled.append((re.compile(item["pattern"], re.IGNORECASE | re.MULTILINE), item))
        except (KeyError, re.error) as exc:
            print(f"Skipping invalid error pattern: {exc}", file=sys.stderr)
    return compiled


def classify(log_text: str, compiled: list[tuple[re.Pattern[str], dict[str, Any]]]) -> tuple[str, str]:
    for regex, item in compiled:
        if regex.search(log_text):
            return item.get("category", "UNKNOWN_FAILURE"), item.get("strategy", "Escalate with diagnostics.")
    return "UNKNOWN_FAILURE", "No trusted deterministic repair pattern matched; escalate with diagnostics."


def signature(log_text: str) -> str:
    lines = [line.strip() for line in log_text.splitlines() if line.strip()]
    interesting = [
        line for line in lines
        if re.search(r"error|failed|failure|exception|fatal|timed out|cancelled|cannot|invalid", line, re.IGNORECASE)
    ]
    candidate = interesting[-1] if interesting else (lines[-1] if lines else "unknown failure")
    candidate = re.sub(r"\b[0-9a-f]{40}\b", "<sha>", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\d{4}-\d{2}-\d{2}T\S+", "<timestamp>", candidate)
    return candidate[:300]


def learn_unknown(patterns: dict[str, Any], sig: str) -> bool:
    if not sig or sig == "unknown failure":
        return False
    literal = re.escape(sig[:160])
    if any(item.get("pattern") == literal for item in patterns.get("patterns", [])):
        return False
    patterns.setdefault("patterns", []).append({
        "pattern": literal,
        "category": "UNKNOWN_FAILURE",
        "strategy": "Recurring unknown signature; preserve diagnostics and require human review.",
        "learned_at": now(),
    })
    return True


def ensure_labels() -> None:
    definitions = {
        "auto-heal": "1f6feb",
        "bot": "6f42c1",
        "ci": "0e8a16",
        "tests": "5319e7",
        "deps": "0366d6",
    }
    for name, color in definitions.items():
        try:
            api("POST", f"/repos/{REPOSITORY}/labels", {"name": name, "color": color})
        except urllib.error.HTTPError as exc:
            if exc.code != 422:
                print(f"Could not ensure label {name}: HTTP {exc.code}", file=sys.stderr)
        except Exception as exc:
            print(f"Could not ensure label {name}: {exc}", file=sys.stderr)


def existing_issue_for_run(run_id: int) -> bool:
    issues = try_api("GET", f"/repos/{REPOSITORY}/issues?state=all&per_page=100") or []
    marker = f"auto-heal-run:{run_id}"
    return any(marker in (item.get("body") or "") for item in issues if "pull_request" not in item)


def create_issue(run: dict[str, Any], category: str, strategy: str, diagnostics: list[dict[str, Any]]) -> int | None:
    run_id = int(run["id"])
    if existing_issue_for_run(run_id):
        return None
    labels = ["auto-heal", "bot", "ci"]
    if category == "TEST_FAILURE":
        labels.append("tests")
    if category == "DEPENDENCY_ERROR":
        labels.append("deps")
    excerpt_lines: list[str] = []
    for diag in diagnostics[:8]:
        clean_sig = str(diag.get("signature", "")).replace("`", "'")
        excerpt_lines.append(f"- `{diag.get('job', 'unknown')}`: `{clean_sig}`")
    excerpts = "\n".join(excerpt_lines) or "- No failed-job log excerpt was available."
    body = f"""<!-- auto-heal-run:{run_id} -->
## Auto-heal diagnostics

- Repository: `{REPOSITORY}`
- Workflow: `{run.get('name', 'unknown')}`
- Run ID: `{run_id}`
- Commit: `{run.get('head_sha', 'unknown')}`
- Branch: `{run.get('head_branch', 'unknown')}`
- Classification: `{category}`
- Run: {run.get('html_url', '')}

### Evidence
{excerpts}

### Proposed remediation
{strategy}

Automatic mutation was not considered sufficiently deterministic or low-risk. Preserve required checks and security controls; apply the smallest reviewed repair and re-run the failed checks.
"""
    result = try_api("POST", f"/repos/{REPOSITORY}/issues", {
        "title": f"Auto-heal: investigate {category} in {run.get('name', 'workflow')}",
        "body": body,
        "labels": labels,
    })
    return result.get("number") if isinstance(result, dict) else None


def candidate_runs(scan_limit: int) -> list[dict[str, Any]]:
    if TARGET_RUN_ID.isdigit():
        one = try_api("GET", f"/repos/{REPOSITORY}/actions/runs/{TARGET_RUN_ID}")
        return [one] if isinstance(one, dict) else []
    data = try_api("GET", f"/repos/{REPOSITORY}/actions/runs?status=completed&per_page={scan_limit}") or {}
    runs = data.get("workflow_runs", []) if isinstance(data, dict) else []
    return [
        run for run in runs
        if run.get("conclusion") in {"failure", "cancelled", "timed_out"}
        and run.get("name") != SELF_WORKFLOW
    ]


def job_diagnostics(run_id: int, compiled: list[tuple[re.Pattern[str], dict[str, Any]]]) -> tuple[str, str, list[dict[str, Any]]]:
    jobs_data = try_api("GET", f"/repos/{REPOSITORY}/actions/runs/{run_id}/jobs?per_page=100") or {}
    jobs = jobs_data.get("jobs", []) if isinstance(jobs_data, dict) else []
    diagnostics: list[dict[str, Any]] = []
    categories: list[tuple[str, str]] = []
    for job in jobs:
        if job.get("conclusion") not in {"failure", "cancelled", "timed_out"}:
            continue
        log = try_api("GET", f"/repos/{REPOSITORY}/actions/jobs/{job['id']}/logs")
        text = log if isinstance(log, str) else ""
        category, strategy = classify(text, compiled)
        categories.append((category, strategy))
        diagnostics.append({
            "job": job.get("name", str(job.get("id"))),
            "job_id": job.get("id"),
            "conclusion": job.get("conclusion"),
            "category": category,
            "signature": signature(text),
        })
    if not categories:
        return "UNKNOWN_FAILURE", "No failed-job logs were available; require human review.", diagnostics
    priority = [
        "SECURITY_SCAN_FAILURE", "DEPLOYMENT_ERROR", "CONFIG_ERROR", "DEPENDENCY_ERROR",
        "BUILD_ERROR", "TEST_FAILURE", "LINT_ERROR", "INFRASTRUCTURE_ERROR", "UNKNOWN_FAILURE",
    ]
    for wanted in priority:
        for category, strategy in categories:
            if category == wanted:
                return category, strategy, diagnostics
    return categories[0][0], categories[0][1], diagnostics


def update_flaky(history: dict[str, Any], flaky: dict[str, Any]) -> None:
    counts: dict[tuple[str, str], int] = {}
    for entry in history.get("entries", []):
        if entry.get("classification") not in {"TEST_FAILURE", "UNKNOWN_FAILURE"}:
            continue
        for diag in entry.get("diagnostics", []):
            key = (entry.get("workflow", "unknown"), diag.get("job", "unknown"))
            counts[key] = counts.get(key, 0) + 1
    existing = {(x.get("workflow"), x.get("job")) for x in flaky.get("tests", [])}
    for (workflow, job), count in sorted(counts.items()):
        if count >= 2 and (workflow, job) not in existing:
            flaky.setdefault("tests", []).append({
                "workflow": workflow,
                "job": job,
                "observed_failures": count,
                "first_flagged_at": now(),
                "status": "candidate",
            })


def main() -> int:
    patterns = load_json(PATTERNS_PATH, {"schema_version": 1, "patterns": []})
    strategy_config = load_json(STRATEGIES_PATH, {"global": {}, "strategies": {}})
    history = load_json(HISTORY_PATH, {"schema_version": 1, "entries": []})
    flaky = load_json(FLAKY_PATH, {"schema_version": 1, "tests": []})
    compiled = compile_patterns(patterns)
    global_cfg = strategy_config.get("global", {})
    scan_limit = int(global_cfg.get("scan_limit", 50))
    max_cycle = int(global_cfg.get("max_failures_per_cycle", 5))
    seen = {(e.get("run_id"), e.get("run_attempt")) for e in history.get("entries", [])}
    runs = candidate_runs(scan_limit)
    ensure_labels()

    needs_doctor = False
    processed = 0
    for run in runs:
        if processed >= max_cycle:
            break
        run_id = int(run["id"])
        attempt = int(run.get("run_attempt") or 1)
        if (run_id, attempt) in seen:
            continue
        category, strategy, diagnostics = job_diagnostics(run_id, compiled)
        cfg = strategy_config.get("strategies", {}).get(
            category,
            strategy_config.get("strategies", {}).get("UNKNOWN_FAILURE", {}),
        )
        retry_limit = int(cfg.get("retry_limit", 0))
        action = "diagnosed"
        issue_number = None

        if category == "INFRASTRUCTURE_ERROR" and attempt <= retry_limit:
            try_api("POST", f"/repos/{REPOSITORY}/actions/runs/{run_id}/rerun-failed-jobs", {})
            action = "rerun_requested"
        elif category == "CONFIG_ERROR" and "workflow_doctor" in cfg.get("automatic_actions", []):
            needs_doctor = True
            action = "workflow_doctor_requested"
        else:
            issue_number = create_issue(run, category, strategy, diagnostics)
            action = "escalated_issue" if issue_number else "escalated_existing_issue"

        if category == "UNKNOWN_FAILURE":
            for diag in diagnostics:
                learn_unknown(patterns, diag.get("signature", ""))

        history.setdefault("entries", []).append({
            "handled_at": now(),
            "repo": REPOSITORY,
            "workflow": run.get("name"),
            "run_id": run_id,
            "run_attempt": attempt,
            "commit_sha": run.get("head_sha"),
            "branch": run.get("head_branch"),
            "classification": category,
            "action": action,
            "issue_number": issue_number,
            "run_url": run.get("html_url"),
            "diagnostics": diagnostics,
            "outcome": "pending_rerun" if action == "rerun_requested" else "pending_review",
        })
        print(f"Handled run {run_id} attempt {attempt}: {category} -> {action}")
        processed += 1

    update_flaky(history, flaky)
    save_json(PATTERNS_PATH, patterns)
    save_json(HISTORY_PATH, history)
    save_json(FLAKY_PATH, flaky)
    write_output("needs_workflow_doctor", "true" if needs_doctor else "false")
    write_output("processed", str(processed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
