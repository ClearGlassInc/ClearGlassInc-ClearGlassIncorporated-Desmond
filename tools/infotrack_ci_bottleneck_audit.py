#!/usr/bin/env python3
"""ClearGlass proof-of-work: CI/CD bottleneck audit.

Designed for public, non-invasive repository inspection. It does not deploy,
modify infrastructure, access credentials, or contact external systems.

Use:
    python tools/infotrack_ci_bottleneck_audit.py [repo_root]
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

CI_FILES = {
    ".github/workflows": "GitHub Actions",
    ".circleci/config.yml": "CircleCI",
    ".gitlab-ci.yml": "GitLab CI",
    "Jenkinsfile": "Jenkins",
}
IAC_MARKERS = ("terraform", "pulumi", "cloudformation", "ansible")
CONTAINER_MARKERS = ("docker", "kubernetes", "helm", "kustomize")
OBS_MARKERS = ("prometheus", "grafana", "datadog", "opentelemetry", "elastic")
SCRIPT_EXTENSIONS = {".py", ".ps1", ".sh", ".bash"}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def scan(root: Path) -> dict:
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if ".git/" in f"{rel}/" or "node_modules/" in f"{rel}/":
            continue
        files.append(path)

    ci = []
    scripts = []
    markers = set()
    for path in files:
        rel = path.relative_to(root).as_posix()
        lower = rel.lower()
        if any(lower == key.lower() or lower.startswith(key.lower().rstrip("/") + "/") for key in CI_FILES):
            ci.append(rel)
        if path.suffix.lower() in SCRIPT_EXTENSIONS:
            scripts.append(rel)
        text = read_text(path).lower()
        for marker in IAC_MARKERS + CONTAINER_MARKERS + OBS_MARKERS + ("gcp", "aws", "azure", "github actions", "ci/cd"):
            if marker in text:
                markers.add(marker)

    workflow_steps = []
    workflow_dir = root / ".github" / "workflows"
    if workflow_dir.exists():
        for path in workflow_dir.glob("*.y*ml"):
            text = read_text(path)
            jobs = re.findall(r"^  ([A-Za-z0-9_-]+):\s*$", text, flags=re.M)
            runs_on = re.findall(r"runs-on:\s*([^\n]+)", text)
            workflow_steps.append({"file": path.relative_to(root).as_posix(), "jobs": jobs, "runners": runs_on})

    return {
        "repo": str(root.resolve()),
        "ci_files": sorted(ci),
        "automation_scripts": sorted(scripts),
        "detected_stack_markers": sorted(markers),
        "github_actions": workflow_steps,
        "assessment": {
            "primary_bottleneck": "CI/CD build and deployment latency plus reproducibility of staging/production environments",
            "eighty_percent_solution": [
                "inventory pipeline jobs and runners",
                "identify serial jobs that can be parallelized",
                "surface repeated dependency/setup work",
                "verify infrastructure-as-code entry points",
                "emit a deterministic audit artifact without changing production",
            ],
            "safety": "read-only local analysis; no credentials, deploys, network calls, or production mutations",
        },
    }


def main() -> int:
    root = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.cwd()
    if not root.exists() or not root.is_dir():
        print(json.dumps({"error": f"Repository path not found: {root}"}, indent=2))
        return 2
    print(json.dumps(scan(root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
