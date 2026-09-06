#!/usr/bin/env python3
"""ClearGlass CI Doctor Bot.

Audits GitHub Actions workflow files for common failure causes before CI burns time:
- stale action versions
- missing reusable workflow_call triggers
- validate-site jobs that do not install pytest/pytest-cov
- workflow YAML files with no jobs

This bot is intentionally read-only. It reports findings and exits non-zero only for
high-confidence breakages that can stop CI execution.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required. Install with: python -m pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
REPORT_MD = ROOT / "ci-doctor-report.md"
REPORT_JSON = ROOT / "ci-doctor-report.json"

STALE_ACTION_HINTS = {
    "actions/checkout@v1",
    "actions/checkout@v2",
    "actions/checkout@v3",
    "actions/setup-python@v1",
    "actions/setup-python@v2",
    "actions/setup-python@v3",
    "actions/setup-python@v4",
    "actions/setup-node@v1",
    "actions/setup-node@v2",
    "actions/setup-node@v3",
}


def load_workflow(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("workflow root must be a mapping")
    return data


def workflow_on(data: dict[str, Any]) -> Any:
    # YAML 1.1 parses key "on" as True under some loaders.
    return data.get("on", data.get(True, {}))


def has_workflow_call(data: dict[str, Any]) -> bool:
    on_block = workflow_on(data)
    if isinstance(on_block, dict):
        return "workflow_call" in on_block
    if isinstance(on_block, list):
        return "workflow_call" in on_block
    return False


def collect_run_text(job: dict[str, Any]) -> str:
    chunks: list[str] = []
    for step in job.get("steps", []) or []:
        if isinstance(step, dict) and isinstance(step.get("run"), str):
            chunks.append(step["run"])
    return "\n".join(chunks)


def audit_workflow(path: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    text = path.read_text(encoding="utf-8")

    try:
        data = load_workflow(path)
    except Exception as exc:
        return [{"severity": "error", "file": str(path.relative_to(ROOT)), "message": f"YAML parse failure: {exc}"}]

    rel = str(path.relative_to(ROOT))
    jobs = data.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        findings.append({"severity": "error", "file": rel, "message": "workflow has no jobs mapping"})
        return findings

    for stale in sorted(STALE_ACTION_HINTS):
        if stale in text:
            findings.append({"severity": "warning", "file": rel, "message": f"stale action detected: {stale}"})

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            findings.append({"severity": "error", "file": rel, "message": f"job {job_name!r} is not a mapping"})
            continue

        uses = job.get("uses")
        if isinstance(uses, str) and uses.startswith("./.github/workflows/"):
            called = WORKFLOW_DIR / Path(uses).name
            if not called.exists():
                findings.append({"severity": "error", "file": rel, "message": f"reusable workflow target missing: {uses}"})
            else:
                try:
                    called_data = load_workflow(called)
                    if not has_workflow_call(called_data):
                        findings.append({"severity": "error", "file": rel, "message": f"reusable workflow lacks workflow_call trigger: {uses}"})
                except Exception as exc:
                    findings.append({"severity": "error", "file": rel, "message": f"cannot inspect reusable workflow {uses}: {exc}"})

        if "validate" in str(job_name).lower() or "validate" in str(job.get("name", "")).lower():
            run_text = collect_run_text(job)
            if "python -m pytest" in run_text or "pytest" in run_text:
                install_block_present = bool(re.search(r"pip\s+install[\s\S]*(pytest|requirements\.txt)", run_text))
                if not install_block_present:
                    findings.append({"severity": "warning", "file": rel, "message": f"validate job {job_name!r} runs pytest but no dependency install was detected in run blocks"})

    return findings


def main() -> int:
    all_findings: list[dict[str, str]] = []
    if not WORKFLOW_DIR.exists():
        all_findings.append({"severity": "error", "file": str(WORKFLOW_DIR.relative_to(ROOT)), "message": "workflow directory missing"})
    else:
        for path in sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml")):
            all_findings.extend(audit_workflow(path))

    errors = [f for f in all_findings if f["severity"] == "error"]
    warnings = [f for f in all_findings if f["severity"] == "warning"]

    lines = ["# ClearGlass CI Doctor Bot Report", "", f"Errors: {len(errors)}", f"Warnings: {len(warnings)}", ""]
    if all_findings:
        for finding in all_findings:
            lines.append(f"- **{finding['severity'].upper()}** `{finding['file']}` — {finding['message']}")
    else:
        lines.append("No CI workflow defects detected.")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    import json
    REPORT_JSON.write_text(json.dumps({"findings": all_findings}, indent=2) + "\n", encoding="utf-8")
    print(REPORT_MD.read_text(encoding="utf-8"))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
