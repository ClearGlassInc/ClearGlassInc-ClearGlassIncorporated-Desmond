# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Invariants of the CI/CD layer described in AUTOMATION.md.

The layer arrived as several overlapping pull requests (#187, #188, #190). Two of
their decisions conflicted and one merge left ci.yml calling a reusable workflow
with inputs it does not declare, which GitHub rejects as an invalid workflow
file. Each test below pins one decision, so a later edit that quietly reverses
it fails here rather than in a run nobody can see while Actions dispatches no
runners. The two contract tests at the top would have caught that merge.
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
    "ci.yml",
    "reusable-ci.yml",
    "reusable-component-ci.yml",
    "reusable-deploy.yml",
    "deploy-staging.yml",
    "deploy-promotion.yml",
    "auto-fix.yml",
    "heal-pipeline.yml",
    "ci-telemetry.yml",
]
COMPOSITES = ["setup-node-python", "run-smoke-tests", "post-pr-comment"]
SCOPES = {"none": 0, "read": 1, "write": 2}


def workflow(name: str) -> dict:
    return yaml.load((WORKFLOWS / name).read_text(encoding="utf-8"), Loader=GitHubLoader)


def steps(job: dict) -> list[dict]:
    return [step for step in job.get("steps") or [] if isinstance(step, dict)]


def local_calls():
    """(caller file, job name, job, callee file) for every local reusable-workflow call."""
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=GitHubLoader) or {}
        for name, job in (data.get("jobs") or {}).items():
            uses = job.get("uses") if isinstance(job, dict) else None
            if isinstance(uses, str) and uses.startswith("./.github/workflows/"):
                yield path.name, name, job, Path(uses).name


# ── Contracts GitHub enforces at load time ────────────────────────────────


def test_every_reusable_call_passes_only_declared_inputs_and_all_required_ones() -> None:
    problems = []
    for caller, name, job, callee in local_calls():
        declared = (workflow(callee)["on"].get("workflow_call") or {}).get("inputs") or {}
        given = set(job.get("with") or {})
        problems += [f"{caller}:{name} passes undeclared {callee} input {key!r}" for key in given - set(declared)]
        problems += [
            f"{caller}:{name} omits required {callee} input {key!r}"
            for key, spec in declared.items()
            if str(spec.get("required")).lower() == "true" and key not in given
        ]
    assert problems == []


def test_every_caller_grants_what_its_callee_requests() -> None:
    """A callee job asking for more than the calling job grants fails to load."""
    problems = []
    for caller, name, job, callee in local_calls():
        granted = job.get("permissions", workflow(caller).get("permissions")) or {}
        for callee_job_name, callee_job in workflow(callee)["jobs"].items():
            for scope, level in (callee_job.get("permissions") or {}).items():
                if SCOPES[level] > SCOPES[granted.get(scope, "none")]:
                    problems.append(f"{caller}:{name} -> {callee}:{callee_job_name} needs {scope}: {level}")
    assert problems == []


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


@pytest.mark.parametrize("name", LAYER)
def test_layer_passes_the_safety_audit_with_no_warnings(name: str) -> None:
    result = load(WORKFLOWS / name)
    audit(result)
    assert result.errors == [] and result.warnings == [], result.errors + result.warnings
    assert result.status == "valid and ready"


# ── ci.yml ────────────────────────────────────────────────────────────────


def test_existing_ci_jobs_are_kept_and_one_result_check_covers_them() -> None:
    """Job names are the checks branch protection reads; `result` is the one to require."""
    jobs = workflow("ci.yml")["jobs"]
    existing = {"python-tests", "lint", "site-audit", "search-integrity", "lighthouse", "workflow-doctor", "osint-deck"}
    assert existing <= set(jobs)
    assert set(jobs["result"]["needs"]) == existing | {"changes", "stack"}
    assert jobs["result"]["if"] == "always()"
    callers = {name: job["uses"] for name, job in jobs.items() if "uses" in job}
    assert callers == {"stack": "./.github/workflows/reusable-component-ci.yml"}


def test_ci_cancels_superseded_pr_runs_but_never_a_push() -> None:
    concurrency = workflow("ci.yml")["concurrency"]
    assert concurrency["group"] == "ci-${{ github.event.pull_request.number || github.sha }}"
    assert concurrency["cancel-in-progress"] == "${{ github.event_name == 'pull_request' }}"


# ── Deploys ───────────────────────────────────────────────────────────────


def test_deploys_are_opt_in() -> None:
    staging = workflow("deploy-staging.yml")["jobs"]
    assert "vars.PR_PREVIEW_URL_TEMPLATE != ''" in staging["preview"]["if"]
    assert "vars.DEPLOY_PROVIDER == 'cloudrun'" in staging["plan-cloudrun"]["if"]
    assert "vars.DEPLOY_PROVIDER == 'cloudrun'" in staging["teardown"]["if"]
    promotion = workflow("deploy-promotion.yml")["jobs"]
    assert "vars.PROMOTION_PIPELINE_ENABLED == 'true'" in promotion["resolve"]["if"]
    for name in ("gate", "staging", "production"):
        assert "resolve" in promotion[name]["needs"], f"{name} must inherit the opt-in"


def test_fork_prs_are_never_deployed() -> None:
    jobs = workflow("deploy-staging.yml")["jobs"]
    for name in ("preview", "plan-cloudrun", "teardown"):
        assert "github.event.pull_request.head.repo.full_name == github.repository" in jobs[name]["if"], name


def test_production_follows_gates_staging_and_end_to_end_checks() -> None:
    jobs = workflow("deploy-promotion.yml")["jobs"]
    assert "gate" in jobs["staging"]["needs"]
    assert {"staging", "e2e"} <= set(jobs["production"]["needs"])
    assert "staging" in jobs["e2e"]["needs"]
    e2e_runs = " ".join(str(step.get("run", "")) for step in steps(jobs["e2e"]))
    assert "scripts/ci/e2e_staging.py" in e2e_runs
    # GitHubLoader keeps YAML booleans as strings, the way GitHub reads `on:`.
    assert str(jobs["production"]["with"]["build"]) == "false", "production must deploy staging's digest, not rebuild"
    assert str(jobs["staging"]["with"]["build"]) == "true"


def test_unknown_providers_never_report_a_deploy() -> None:
    deploy = workflow("reusable-deploy.yml")["jobs"]["deploy"]
    guard = next(step for step in steps(deploy) if step.get("name") == "Refuse an unknown provider")
    assert "render|cloudrun)" in guard["run"] and "exit 1" in guard["run"]
    for step in steps(deploy)[2:]:
        condition = str(step.get("if", ""))
        assert "env.PROVIDER == 'render'" in condition or "env.PROVIDER == 'cloudrun'" in condition, step.get("name")


def test_render_never_rolls_back_on_its_own() -> None:
    """docs/INCIDENT_RESPONSE.md: on Render a person dispatches rollback.yml."""
    for step in steps(workflow("reusable-deploy.yml")["jobs"]["deploy"]):
        if "env.PROVIDER == 'render'" in str(step.get("if", "")):
            assert "rollback" not in str(step.get("run", "")).lower() or step["name"] == "Record the rollback path"
            assert "createWorkflowDispatch" not in str(step)


def test_cloud_run_rolls_back_automatically_only_without_migrations() -> None:
    jobs = workflow("deploy-promotion.yml")["jobs"]
    assert jobs["production"]["with"]["auto_rollback"] == "${{ needs.resolve.outputs.auto_rollback == 'true' }}"
    decide = next(step for step in steps(jobs["resolve"]) if step.get("id") == "rollback")["run"]
    assert 'auto=false' in decide.splitlines()[1], "the default must be no automatic rollback"
    assert 'git diff --quiet "$PREVIOUS" "$REF" -- control-plane/migrations' in decide
    assert '[ "$PROVIDER" = "cloudrun" ]' in decide
    release = next(s for s in steps(workflow("reusable-deploy.yml")["jobs"]["deploy"]) if s.get("id") == "release")
    assert 'if [ "$AUTO_ROLLBACK" = "true" ]; then args+=(--auto-rollback); fi' in release["run"]


def test_cloud_run_uses_oidc_and_no_long_lived_key() -> None:
    text = (WORKFLOWS / "reusable-deploy.yml").read_text(encoding="utf-8")
    assert "google-github-actions/auth@" in text and "workload_identity_provider:" in text
    assert "credentials_json" not in text and "GCP_SA_KEY" not in text
    assert workflow("reusable-deploy.yml")["jobs"]["deploy"]["permissions"]["id-token"] == "write"


def test_deploy_builds_but_never_executes_the_revision_it_deploys() -> None:
    """The release scripts come from the caller's commit; the released ref is only a build context."""
    deploy = workflow("reusable-deploy.yml")["jobs"]["deploy"]
    checkouts = [s for s in steps(deploy) if str(s.get("uses", "")).startswith("actions/checkout@")]
    assert "ref" not in checkouts[0].get("with", {})
    source = [s for s in checkouts if (s.get("with") or {}).get("ref") == "${{ inputs.ref }}"]
    assert len(source) == 1 and source[0]["with"]["path"] == "source"
    release = next(s for s in steps(deploy) if s.get("id") == "release")["run"]
    assert "python3 scripts/ci/release.py" in release and "--source source" in release


# ── Auto-fix ──────────────────────────────────────────────────────────────


def test_auto_fix_runs_pr_code_only_without_write_access() -> None:
    jobs = workflow("auto-fix.yml")["jobs"]
    assert jobs["fix"]["permissions"] == {"contents": "read"}
    apply = jobs["apply"]
    assert apply["permissions"]["contents"] == "write"
    runs = " ".join(str(step.get("run", "")) for step in steps(apply))
    for pr_code in ("python3 tools/", "ruff check", "pip install", "npm ci", "npm run"):
        assert pr_code not in runs, f"write job runs PR-controlled code: {pr_code!r}"
    for checkout in (s for s in steps(apply) if str(s.get("uses", "")).startswith("actions/checkout@")):
        assert str(checkout["with"]["persist-credentials"]) == "false", "no credential may be written into a checkout"
    trusted = steps(apply)[0]
    assert "ref" not in trusted["with"], "policy and driver must come from the default branch"


def test_auto_fix_refuses_protected_paths_and_never_forces() -> None:
    text = (ROOT / "scripts" / "ci" / "autofix.py").read_text(encoding="utf-8")
    assert "protected_reason(f.path)" in text and "--no-renames" in text
    apply_runs = " ".join(str(s.get("run", "")) for s in steps(workflow("auto-fix.yml")["jobs"]["apply"]))
    assert "check-patch" in apply_runs and "verify-applied" in apply_runs
    assert "git push" not in apply_runs and "--force" not in apply_runs
    assert "--head-sha \"$HEAD_SHA\"" in apply_runs, "the commit must be pinned to the failing head"


def test_auto_fix_only_runs_deterministic_repository_tools() -> None:
    text = (WORKFLOWS / "auto-fix.yml").read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))
    for tool in ("black ", "prettier", "eslint", "ruff format", "codex", "openai"):
        assert tool not in code, f"auto-fix must not run {tool.strip()}"
    assert "ruff==0.15.8" in code


def test_auto_fix_skips_forks_integration_branches_and_respects_the_kill_switch() -> None:
    condition = workflow("auto-fix.yml")["jobs"]["plan"]["if"]
    assert "head_repository.full_name == github.repository" in condition
    assert "vars.AUTOFIX_ENABLED != 'false'" in condition
    assert "head_branch != 'staging'" in condition
    assert "head_branch != github.event.repository.default_branch" in condition


# ── Composite actions and ownership ───────────────────────────────────────


def test_composite_actions_never_interpolate_inputs_into_code() -> None:
    for name in COMPOSITES:
        data = yaml.safe_load((ACTIONS / name / "action.yml").read_text(encoding="utf-8"))
        for step in data["runs"]["steps"]:
            code = str(step.get("run", "")) + str((step.get("with") or {}).get("script", ""))
            assert "${{" not in code, f"{name}: expression interpolated into code"


def control_plane_routes() -> set[str]:
    app = ROOT / "control-plane" / "app"
    routes = set(re.findall(r'@app\.get\("([^"]+)"', (app / "main.py").read_text(encoding="utf-8")))
    routes.add("/openapi.json")  # served by FastAPI itself
    for router in (app / "routers").glob("*.py"):
        text = router.read_text(encoding="utf-8")
        prefix = re.search(r'APIRouter\(prefix="([^"]*)"', text)
        for path in re.findall(r'@router\.get\(\s*"([^"]*)"', text):
            routes.add(((prefix.group(1) if prefix else "") + path) or "/")
    return routes


def test_smoke_checks_name_real_control_plane_routes() -> None:
    from scripts.ci.components import COMPONENTS

    routes = control_plane_routes()
    for line in COMPONENTS["control-plane"]["deploy"]["smoke"]:
        path = line.split()[1]
        assert path in routes, f"smoke check {path} is not a control-plane route"


def test_preview_control_plane_always_gets_an_admin_key() -> None:
    """Unset ADMIN_API_KEY is open dev mode: approvals and refunds on a public URL."""
    from scripts.ci.components import COMPONENTS

    assert COMPONENTS["control-plane"]["deploy"]["preview_env"]["ADMIN_API_KEY"] == "@random"


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
