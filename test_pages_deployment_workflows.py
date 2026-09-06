"""Regression tests for the single-writer GitHub Pages deployment boundary."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _workflow_text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_pages_workflow_is_the_only_pages_deployer() -> None:
    deploy_action = "actions/deploy-pages@"
    deployers = [
        path.name
        for path in sorted(WORKFLOWS.glob("*.yml"))
        if deploy_action in path.read_text(encoding="utf-8")
    ]

    assert deployers == ["pages.yml"]


def test_pages_build_runs_integrity_gate_before_artifact_upload() -> None:
    workflow = _workflow_text("pages.yml")
    integrity_check = workflow.index("python3 scripts/verify_site.py")
    build = workflow.index("python3 tools/build_pages.py dist")
    upload = workflow.index("actions/upload-pages-artifact@")

    assert integrity_check < build < upload


def test_integrity_guard_has_no_pages_write_capability() -> None:
    workflow = _workflow_text("site-integrity-and-deploy.yml")

    assert "actions/upload-pages-artifact@" not in workflow
    assert "actions/deploy-pages@" not in workflow
    assert not re.search(r"^\s+(?:pages|id-token):\s*write\s*$", workflow, re.MULTILINE)
