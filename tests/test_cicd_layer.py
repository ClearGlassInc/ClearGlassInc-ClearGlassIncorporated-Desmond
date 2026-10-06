# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Invariants of the CI/CD layer on main (AUTOMATION.md).

Three implementations of the same CI/CD blueprint were merged on 2026-10-06
(#187, #188 and #190) and their conflicts were resolved by hand. Afterwards
workflow_doctor.py and audit_github_actions.py still passed, yet ci.yml was
calling a reusable workflow with inputs it does not declare and another that
declares no workflow_call, so GitHub would have rejected the whole file: the
original CI gates included. auto-fix.yml also ran the PR's own copy of its
local actions while holding a write token.

Neither gate looks at those contracts, so these tests do: reusable-workflow
inputs and permissions at every call site, the trust boundary of jobs that hold
a write token, opt-in deploys, a manual-only rollback, and the original gates.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.audit_github_actions import GitHubLoader, audit, load

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
ACTIONS = ROOT / ".github" / "actions"
DEFAULT_BRANCH = "${{ github.event.repository.default_branch }}"

LAYER = [
    "reusable-ci.yml",
    "reusable-component-ci.yml",
    "reusable-deploy.yml",
    "deploy-staging.yml",
    "deploy-promotion.yml",
    "auto-fix.yml",
    "heal-pipeline.yml",
    "ci-telemetry.yml",
]
LAYER_ACTIONS = [
    "setup-node-python",
    "setup-component-toolchain",
    "run-smoke-tests",
    "post-pr-comment",
    "verified-commit",
]
# Triggers whose jobs check out code a pull request controls.
PR_TRIGGERS = {"pull_request", "pull_request_target", "workflow_run"}
LEVEL = {"none": 0, "read": 1, "write": 2}


def parse(text: str) -> dict[str, Any]:
    return yaml.load(text, Loader=GitHubLoader) or {}


def workflow(name: str) -> dict[str, Any]:
    return parse((WORKFLOWS / name).read_text(encoding="utf-8"))


def triggers(data: dict[str, Any]) -> set[str]:
    on = data.get("on") or {}
    if isinstance(on, str):
        return {on}
    return set(on)


def steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [step for step in job.get("steps") or [] if isinstance(step, dict)]


def needs(job: dict[str, Any]) -> set[str]:
    value = job.get("needs") or []
    return {value} if isinstance(value, str) else set(value)


def scopes(grant: Any) -> dict[str, str] | None:
    """A permissions value as {scope: level}; None when GitHub's default applies."""
    if grant is None:
        return None
    if isinstance(grant, str):
        level = {"read-all": "read", "write-all": "write"}.get(grant, "none")
        return {"*": level}
    return {str(scope): str(level) for scope, level in grant.items()}


def level_of(grant: dict[str, str], scope: str) -> int:
    return LEVEL[grant.get(scope, grant.get("*", "none"))]


def call_sites() -> list[tuple[str, str, dict[str, Any], dict[str, Any]]]:
    """Every job in every workflow that calls a reusable workflow in this repo."""
    sites = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        data = parse(path.read_text(encoding="utf-8"))
        for job_id, job in (data.get("jobs") or {}).items():
            if isinstance(job, dict) and str(job.get("uses", "")).startswith("./"):
                sites.append((f"{path.name}:{job_id}", job_id, job, data))
    return sites


CALL_SITES = call_sites()


def untrusted_local_actions(data: dict[str, Any]) -> list[str]:
    """Local actions run with a write token from code a pull request controls.

    A local action (`uses: ./...`) runs whatever sits at that path in the
    workspace. In a job triggered by a pull request or by a run of one, that is
    the PR's code unless the job checked out the default branch or restored
    .github/actions from it. verified-commit ends with `git reset --hard` to the
    PR branch, so it undoes such a restore. A checkout with no ref is treated as
    untrusted: on pull_request it is the PR's merge commit.
    """
    if not triggers(data) & PR_TRIGGERS:
        return []
    top = scopes(data.get("permissions"))
    findings = []
    for job_id, job in (data.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        grant = scopes(job.get("permissions")) or top or {}
        if "write" not in grant.values():
            continue
        trusted = False
        for step in steps(job):
            uses = str(step.get("uses", ""))
            run = str(step.get("run", ""))
            if uses.startswith("actions/checkout@"):
                trusted = (step.get("with") or {}).get("ref") == DEFAULT_BRANCH
            elif "git restore --source=FETCH_HEAD" in run and ".github/actions" in run:
                trusted = True
            elif uses.startswith("./"):
                if not trusted:
                    findings.append(f"{job_id}: {uses}")
                if uses.rstrip("/").endswith("verified-commit"):
                    trusted = False
    return findings


# ── The repository's own gates ─────────────────────────────────────────────


@pytest.mark.parametrize("name", LAYER)
def test_layer_passes_the_safety_audit_with_no_warnings(name: str) -> None:
    result = load(WORKFLOWS / name)
    audit(result)
    assert result.errors == [] and result.warnings == [], result.errors + result.warnings


def test_the_original_ci_gates_are_kept() -> None:
    """These job names are the check names branch protection reads."""
    jobs = workflow("ci.yml")["jobs"]
    original = {
        "python-tests": "Python Tests",
        "lint": "Lint (ruff)",
        "site-audit": "Site Reliability Audit",
        "search-integrity": "Search discovery and structured data",
        "lighthouse": "Lighthouse budgets",
        "workflow-doctor": "Workflow Doctor (dry-run)",
        "osint-deck": "OSINT Deck Validator",
    }
    for job_id, name in original.items():
        assert job_id in jobs, f"ci.yml lost the {job_id} gate"
        assert jobs[job_id].get("name") == name, f"{job_id} renamed: its required check would orphan"
        assert "uses" not in jobs[job_id], f"{job_id} became a reusable call"


# ── Reusable-workflow contracts (GitHub rejects the caller when broken) ────


def test_reusable_workflows_are_only_called_at_job_level() -> None:
    """A step cannot call a reusable workflow; GitHub fails the run."""
    offenders = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        for job_id, job in (parse(path.read_text(encoding="utf-8")).get("jobs") or {}).items():
            for step in steps(job) if isinstance(job, dict) else []:
                if str(step.get("uses", "")).startswith("./.github/workflows/"):
                    offenders.append(f"{path.name}:{job_id}")
    assert offenders == []


def test_there_are_call_sites_to_check() -> None:
    """Guards the parametrised contract tests below against silently checking nothing."""
    assert {site for site, *_ in CALL_SITES} >= {"ci.yml:stack", "deploy-promotion.yml:gate"}


@pytest.mark.parametrize(("site", "job_id", "job", "caller"), CALL_SITES, ids=[s[0] for s in CALL_SITES])
def test_every_call_passes_only_declared_inputs(site, job_id, job, caller) -> None:
    callee_path = ROOT / job["uses"].removeprefix("./")
    assert callee_path.is_file(), f"{site} calls a missing workflow"
    callee = parse(callee_path.read_text(encoding="utf-8"))
    on = callee.get("on") or {}
    assert isinstance(on, dict) and "workflow_call" in on, (
        f"{site}: {callee_path.name} declares no workflow_call, so it cannot be called"
    )
    declared = (on["workflow_call"] or {}).get("inputs") or {}
    passed = set((job.get("with") or {}).keys())
    assert passed <= set(declared), f"{site} passes undeclared inputs {sorted(passed - set(declared))}"
    required = {
        name for name, spec in declared.items()
        if isinstance(spec, dict) and spec.get("required") and "default" not in spec
    }
    assert required <= passed, f"{site} omits required inputs {sorted(required - passed)}"


@pytest.mark.parametrize(("site", "job_id", "job", "caller"), CALL_SITES, ids=[s[0] for s in CALL_SITES])
def test_no_called_job_asks_for_more_than_its_caller_grants(site, job_id, job, caller) -> None:
    """Checked when the caller loads, even for callee jobs that would be skipped."""
    grant = scopes(job.get("permissions")) or scopes(caller.get("permissions"))
    if grant is None:
        pytest.skip(f"{site} inherits the repository default token permissions")
    callee = parse((ROOT / job["uses"].removeprefix("./")).read_text(encoding="utf-8"))
    callee_top = scopes(callee.get("permissions"))
    for callee_job_id, callee_job in (callee.get("jobs") or {}).items():
        wanted = scopes(callee_job.get("permissions")) or callee_top or {}
        for scope, level in wanted.items():
            assert LEVEL[level] <= level_of(grant, scope), (
                f"{site} -> {callee_job_id} asks for {scope}: {level}, "
                f"caller grants {grant.get(scope, grant.get('*', 'none'))}"
            )


# ── Trust boundary of jobs that hold a write token ─────────────────────────


def test_write_token_jobs_never_run_pr_controlled_actions() -> None:
    findings = {
        path.name: untrusted_local_actions(parse(path.read_text(encoding="utf-8")))
        for path in sorted(WORKFLOWS.glob("*.y*ml"))
    }
    assert {name: found for name, found in findings.items() if found} == {}


def test_the_trust_boundary_check_catches_what_it_guards() -> None:
    """Without this the check above could pass by never matching anything."""
    pr_head_checkout = """
on: {workflow_run: {workflows: [CI], types: [completed]}}
permissions: {contents: read}
jobs:
  fix:
    permissions: {contents: write}
    steps:
      - uses: actions/checkout@0000000000000000000000000000000000000000
        with: {ref: "${{ github.event.workflow_run.head_sha }}"}
      - uses: ./.github/actions/verified-commit
"""
    assert untrusted_local_actions(parse(pr_head_checkout)) == ["fix: ./.github/actions/verified-commit"]

    restored_once = """
on: {workflow_run: {workflows: [CI], types: [completed]}}
permissions: {contents: read}
jobs:
  fix:
    permissions: {contents: write, pull-requests: write}
    steps:
      - uses: actions/checkout@0000000000000000000000000000000000000000
        with: {ref: "${{ github.event.workflow_run.head_sha }}"}
      - run: git restore --source=FETCH_HEAD --worktree -- .github/actions
      - uses: ./.github/actions/verified-commit
      - uses: ./.github/actions/post-pr-comment
"""
    # verified-commit resets the worktree to the PR branch, undoing the restore.
    assert untrusted_local_actions(parse(restored_once)) == ["fix: ./.github/actions/post-pr-comment"]


def test_auto_fix_runs_behind_the_approval_environment_and_its_guards() -> None:
    job = workflow("auto-fix.yml")["jobs"]["auto-fix"]
    assert job["environment"] == "automation-write"
    assert "head_repository.full_name == github.repository" in job["if"]
    script = steps(job)[0]["with"]["script"]
    assert "no-autofix" in script and "autoFixCount >= 2" in script
    restores = [step for step in steps(job) if "git diff --quiet FETCH_HEAD -- .github/actions" in str(step.get("run", ""))]
    assert len(restores) == 2, "actions must be restored before the commit and again after it"


# ── Deploys ─────────────────────────────────────────────────────────────────


def test_deploys_are_opt_in() -> None:
    promotion = workflow("deploy-promotion.yml")["jobs"]
    condition = promotion["resolve"]["if"]
    assert "github.event_name == 'workflow_dispatch'" in condition
    assert "vars.PROMOTION_PIPELINE_ENABLED == 'true'" in condition
    for job_id in ("gate", "staging", "production"):
        assert "resolve" in needs(promotion[job_id]), f"{job_id} must inherit the opt-in"

    preview = workflow("deploy-staging.yml")["jobs"]["preview"]
    assert "vars.PR_PREVIEW_URL_TEMPLATE != ''" in preview["if"]
    assert "github.event.pull_request.head.repo.full_name == github.repository" in preview["if"]


def test_production_follows_gates_and_staging() -> None:
    jobs = workflow("deploy-promotion.yml")["jobs"]
    assert "gate" in needs(jobs["staging"])
    assert "staging" in needs(jobs["production"])
    assert jobs["staging"]["with"]["environment"] == "staging"
    assert jobs["production"]["with"]["environment"] == "production"
    deploy = workflow("reusable-deploy.yml")["jobs"]["deploy"]
    assert deploy["environment"]["name"] == "${{ inputs.environment }}"


def test_promotion_is_started_in_one_place_only() -> None:
    """A second caller would deploy every commit twice."""
    callers = [site for site, _, job, _ in CALL_SITES if job["uses"].endswith("/deploy-promotion.yml")]
    assert callers == []


def test_rollback_is_never_automatic() -> None:
    """docs/INCIDENT_RESPONSE.md: a person dispatches rollback.yml."""
    assert triggers(workflow("rollback.yml")) == {"workflow_dispatch"}
    dispatch_rollback = re.compile(r"\s*gh\s+workflow\s+run\s+['\"]?(rollback(\.ya?ml)?|Rollback)\b")
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        assert not ("createWorkflowDispatch" in text and "rollback.yml" in text), (
            f"{path.name} dispatches rollback.yml"
        )
        for job in (parse(text).get("jobs") or {}).values():
            for step in steps(job) if isinstance(job, dict) else []:
                for line in str(step.get("run", "")).splitlines():
                    assert not dispatch_rollback.match(line), f"{path.name} runs: {line.strip()}"


def test_smoke_checks_only_hit_real_control_plane_routes() -> None:
    action = (ACTIONS / "run-smoke-tests" / "action.yml").read_text(encoding="utf-8")
    main = (ROOT / "control-plane" / "app" / "main.py").read_text(encoding="utf-8")
    routers = ROOT / "control-plane" / "app" / "routers"
    routes = {
        "/health": '@app.get("/health"' in main,
        "/ready": '@app.get("/ready"' in main,
        "/events": 'prefix="/events"' in (routers / "events.py").read_text(encoding="utf-8"),
        "/metrics/overview": '@router.get("/overview"' in (routers / "metrics.py").read_text(encoding="utf-8"),
    }
    for path, exists in routes.items():
        assert path in action, f"smoke action no longer probes {path}; update this test"
        assert exists, f"smoke action probes {path}, which the control plane does not serve"


# ── Composite actions and ownership ────────────────────────────────────────


@pytest.mark.parametrize("name", LAYER_ACTIONS)
def test_layer_actions_never_interpolate_into_code(name: str) -> None:
    data = yaml.safe_load((ACTIONS / name / "action.yml").read_text(encoding="utf-8"))
    for step in data["runs"]["steps"]:
        code = str(step.get("run", "")) + str((step.get("with") or {}).get("script", ""))
        assert "${{" not in code, f"{name}: expression interpolated into code in {step.get('name')!r}"


def test_setup_action_matches_ci_yml_toolchain() -> None:
    action = yaml.safe_load((ACTIONS / "setup-node-python" / "action.yml").read_text(encoding="utf-8"))
    ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert action["inputs"]["node_version"]["default"] == "22"
    assert action["inputs"]["python_version"]["default"] == "3.11"
    assert 'node-version: "22"' in ci and 'python-version: "3.11"' in ci


def test_codeowners_is_not_shadowed() -> None:
    """GitHub uses the first CODEOWNERS of .github/, root, docs/; only root exists."""
    assert (ROOT / "CODEOWNERS").is_file()
    assert not (ROOT / ".github" / "CODEOWNERS").exists()
    assert not (ROOT / "docs" / "CODEOWNERS").exists()
    assert "/.github/actions/" in (ROOT / "CODEOWNERS").read_text(encoding="utf-8")
