# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Invariants of the CI/CD layer described in AUTOMATION.md.

The layer was adapted from an external blueprint whose literal form would have
broken this repository: it replaced ci.yml, called reusable workflows from
steps, deployed per-PR through environments holding no secrets, ran the PR's
code beside a write token, rolled production back on its own, reformatted the
whole site with black and prettier, and added a .github/CODEOWNERS that shadows
the root one. Each test below pins one of those decisions, so a later edit that
quietly reintroduces it fails here rather than in production.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from scripts.audit_github_actions import GitHubLoader, audit, load

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
ACTIONS = ROOT / ".github" / "actions"

LAYER = [
    "reusable-ci.yml",
    "reusable-deploy.yml",
    "deploy-staging.yml",
    "deploy-promotion.yml",
    "auto-fix.yml",
    "heal-pipeline.yml",
    "ci-telemetry.yml",
]
COMPOSITES = ["setup-node-python", "run-smoke-tests", "post-pr-comment"]


def workflow(name: str) -> dict:
    return yaml.load((WORKFLOWS / name).read_text(encoding="utf-8"), Loader=GitHubLoader)


def steps(job: dict) -> list[dict]:
    return [step for step in job.get("steps") or [] if isinstance(step, dict)]


@pytest.mark.parametrize("name", LAYER)
def test_layer_passes_the_safety_audit_with_no_warnings(name: str) -> None:
    result = load(WORKFLOWS / name)
    audit(result)
    assert result.errors == [] and result.warnings == [], result.errors + result.warnings
    assert result.status == "valid and ready"


def test_existing_ci_workflow_is_not_replaced() -> None:
    """ci.yml's job names are the checks branch protection reads."""
    jobs = workflow("ci.yml")["jobs"]
    assert {"python-tests", "lint", "site-audit", "search-integrity", "workflow-doctor"} <= set(jobs)
    assert not any("uses" in job for job in jobs.values()), "ci.yml must not become a caller"


def test_reusable_workflows_are_only_ever_called_at_job_level() -> None:
    """A step cannot call a reusable workflow; GitHub fails the run."""
    offenders = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=GitHubLoader) or {}
        for job_name, job in (data.get("jobs") or {}).items():
            for step in steps(job) if isinstance(job, dict) else []:
                uses = step.get("uses")
                if isinstance(uses, str) and uses.startswith("./.github/workflows/"):
                    offenders.append(f"{path.name}:{job_name}")
    assert offenders == []


def test_reusable_ci_runs_the_same_gates_as_ci_yml() -> None:
    gate = workflow("reusable-ci.yml")["jobs"]["repo-gates"]
    assert any(step.get("run") == "python3 scripts/ci_local.py" for step in steps(gate))
    checkout = steps(gate)[0]
    assert checkout["with"]["fetch-depth"] == 0, "sitemap dates need full history"


def test_reusable_ci_requests_no_extra_permissions() -> None:
    """A callee asking for more than a caller grants fails to load at all."""
    data = workflow("reusable-ci.yml")
    assert data["permissions"] == {"contents": "read"}
    assert all("permissions" not in job for job in data["jobs"].values())


def test_per_pr_deploys_go_through_the_staging_environment() -> None:
    """A pr-<n> environment would inherit none of staging's secrets."""
    deploy = workflow("reusable-deploy.yml")["jobs"]["deploy"]
    assert deploy["environment"]["name"] == "${{ inputs.target_env }}"
    staging = workflow("deploy-staging.yml")["jobs"]["deploy"]
    assert staging["with"]["target_env"] == "staging"
    assert "environment" not in staging


def test_deploys_are_opt_in() -> None:
    assert "vars.CG_PR_STAGING_DEPLOY == 'true'" in workflow("deploy-staging.yml")["jobs"]["deploy"]["if"]
    promotion = workflow("deploy-promotion.yml")["jobs"]
    assert promotion["resolve"]["if"] == "vars.CG_PROMOTION_ENABLED == 'true'"
    for name in ("ci", "staging", "production"):
        assert "resolve" in promotion[name]["needs"], f"{name} must inherit the opt-in"


def test_fork_prs_are_never_deployed() -> None:
    condition = workflow("deploy-staging.yml")["jobs"]["deploy"]["if"]
    assert "github.event.pull_request.head.repo.full_name == github.repository" in condition


def test_production_follows_gates_and_a_real_staging_deploy() -> None:
    jobs = workflow("deploy-promotion.yml")["jobs"]
    assert "ci" in jobs["staging"]["needs"]
    assert "staging" in jobs["production"]["needs"]
    assert jobs["production"]["if"] == "needs.staging.outputs.deployed == 'true'"
    assert jobs["production"]["with"]["target_env"] == "production"


def test_unconfigured_or_unknown_providers_never_report_a_deploy() -> None:
    script = next(
        step["run"] for step in steps(workflow("reusable-deploy.yml")["jobs"]["deploy"])
        if step.get("id") == "deploy"
    )
    none_branch = script.split("none)", 1)[1].split(";;", 1)[0]
    assert "deployed=false" in none_branch and "deployed=true" not in none_branch
    unknown_branch = script.split("*)", 1)[1].split(";;", 1)[0]
    assert "exit 1" in unknown_branch


def test_rollback_is_never_automatic() -> None:
    """docs/INCIDENT_RESPONSE.md: a person dispatches rollback.yml."""
    text = (WORKFLOWS / "reusable-deploy.yml").read_text(encoding="utf-8")
    for forbidden in ("createWorkflowDispatch", "rollout undo", "actions: write"):
        assert forbidden not in text
    # The rollback command is only ever printed for a person, never executed.
    for step in steps(workflow("reusable-deploy.yml")["jobs"]["deploy"]):
        assert "rollback" not in str(step.get("run", "")).lower()


def test_deploy_job_runs_no_code_from_the_revision_it_deploys() -> None:
    for step in steps(workflow("reusable-deploy.yml")["jobs"]["deploy"]):
        if str(step.get("uses", "")).startswith("actions/checkout@"):
            assert step["with"]["ref"] == "${{ github.event.repository.default_branch }}"
            assert step["with"]["sparse-checkout"] == ".github/actions"


def test_auto_fix_runs_pr_code_only_without_write_access() -> None:
    jobs = workflow("auto-fix.yml")["jobs"]
    assert jobs["fix"]["permissions"] == {"contents": "read"}
    push = jobs["push"]
    assert push["permissions"] == {"contents": "write"}
    assert push["environment"] == "automation-write"
    runs = " ".join(str(step.get("run", "")) for step in steps(push))
    for pr_code in ("python3 tools/", "ruff check", "pip install", "npm ci", "npm run"):
        assert pr_code not in runs, f"write job runs PR-controlled code: {pr_code!r}"
    assert 'sys.path.insert(0, "trusted")' in runs, "policy must load from the default branch"
    trusted = steps(push)[0]
    assert trusted["with"]["ref"] == "${{ github.event.repository.default_branch }}"


def test_auto_fix_refuses_protected_paths_and_never_forces() -> None:
    runs = " ".join(str(step.get("run", "")) for step in steps(workflow("auto-fix.yml")["jobs"]["push"]))
    assert "protected_reason" in runs and '"under .github/"' in runs
    assert "--no-renames" in runs, "a rename must not hide a protected path"
    assert "--force" not in runs and " -f " not in runs and "+HEAD" not in runs


def test_auto_fix_only_runs_deterministic_repository_tools() -> None:
    text = (WORKFLOWS / "auto-fix.yml").read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))
    for tool in ("black ", "prettier", "eslint", "ruff format", "codex", "openai"):
        assert tool not in code, f"auto-fix must not run {tool.strip()}"
    assert 'ruff==0.15.8' in code


def test_auto_fix_skips_forks_and_respects_the_iteration_cap() -> None:
    context = workflow("auto-fix.yml")["jobs"]["context"]
    assert "head_repository.full_name == github.repository" in context["if"]
    script = steps(context)[0]["with"]["script"]
    assert "no-autofix" in script and "prior >= 2" in script


def test_composite_actions_never_interpolate_inputs_into_code() -> None:
    for name in COMPOSITES:
        data = yaml.safe_load((ACTIONS / name / "action.yml").read_text(encoding="utf-8"))
        for step in data["runs"]["steps"]:
            code = str(step.get("run", "")) + str((step.get("with") or {}).get("script", ""))
            assert "${{" not in code, f"{name}: expression interpolated into code"


def test_smoke_test_defaults_are_real_control_plane_routes() -> None:
    action = yaml.safe_load((ACTIONS / "run-smoke-tests" / "action.yml").read_text(encoding="utf-8"))
    main = (ROOT / "control-plane" / "app" / "main.py").read_text(encoding="utf-8")
    for path in action["inputs"]["paths"]["default"].split():
        assert f'@app.get("{path}"' in main, f"smoke default {path} is not a control-plane route"


def test_setup_action_matches_ci_yml_toolchain() -> None:
    action = yaml.safe_load((ACTIONS / "setup-node-python" / "action.yml").read_text(encoding="utf-8"))
    ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert action["inputs"]["node_version"]["default"] == "22"
    assert action["inputs"]["python_version"]["default"] == "3.11"
    assert re.search(r'node-version: "22"', ci) and re.search(r'python-version: "3.11"', ci)


def test_codeowners_is_not_shadowed() -> None:
    """GitHub uses the first CODEOWNERS of .github/, root, docs/; only root exists."""
    assert (ROOT / "CODEOWNERS").is_file()
    assert not (ROOT / ".github" / "CODEOWNERS").exists()
    assert not (ROOT / "docs" / "CODEOWNERS").exists()
    assert "/.github/actions/" in (ROOT / "CODEOWNERS").read_text(encoding="utf-8")
