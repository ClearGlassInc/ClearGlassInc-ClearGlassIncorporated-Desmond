#!/usr/bin/env python3
"""Fail-closed, offline audit for this repository's GitHub Actions workflows.

The checker deliberately avoids GitHub API access and never executes a workflow.
It validates the controls that can be proven from the checked-out source. Runtime
secrets, environment protection rules, and remote action provenance still require
an authorized repository administrator to verify before production execution.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
SHA = re.compile(r"^[0-9a-f]{40}$")
USES = re.compile(r"^(?P<target>[^@]+)(?:@(?P<ref>.+))?$")
SECRET_IN_RUN = re.compile(r"\$\{\{\s*secrets\.")


class GitHubLoader(yaml.SafeLoader):
    """YAML 1.2-like loader which preserves GitHub's literal ``on`` key."""


# Loader subclasses inherit this mapping by reference. Copy it before removing
# YAML 1.1 booleans so importing the auditor cannot mutate PyYAML's SafeLoader
# process-wide and make unrelated validation order-dependent.
GitHubLoader.yaml_implicit_resolvers = copy.deepcopy(GitHubLoader.yaml_implicit_resolvers)
for first, resolvers in list(GitHubLoader.yaml_implicit_resolvers.items()):
    GitHubLoader.yaml_implicit_resolvers[first] = [
        (tag, pattern)
        for tag, pattern in resolvers
        if tag != "tag:yaml.org,2002:bool"
    ]


@dataclass
class Result:
    path: Path
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.errors:
            return "broken and requiring immediate patching"
        if any(item.startswith("GOVERNANCE:") for item in self.warnings):
            return "unsafe and requiring governance changes before execution"
        if self.warnings:
            return "valid but needs improvement"
        return "valid and ready"


def load(path: Path) -> Result:
    result = Result(path)
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=GitHubLoader)
    except yaml.YAMLError as exc:
        result.errors.append(f"invalid YAML: {exc}")
        return result
    if not isinstance(value, dict):
        result.errors.append("workflow root must be a mapping")
        return result
    result.data = value
    if not value.get("on"):
        result.errors.append("missing or empty trigger (`on`)")
    if not isinstance(value.get("jobs"), dict) or not value["jobs"]:
        result.errors.append("missing or empty jobs map")
    return result


def iter_steps(data: dict[str, Any]):
    for job_name, job in (data.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        for index, step in enumerate(job.get("steps") or []):
            if isinstance(step, dict):
                yield job_name, index, step


def audit(result: Result) -> None:
    data = result.data
    if result.errors:
        return
    permissions = data.get("permissions")
    if not isinstance(permissions, dict):
        result.errors.append("top-level permissions must be an explicit mapping")
    elif any(value == "write" for value in permissions.values()):
        result.warnings.append(
            "top-level write permission applies to every job; move each write grant to its consuming job"
        )

    triggers = data.get("on") or {}
    if isinstance(triggers, dict) and "pull_request_target" in triggers:
        result.errors.append("pull_request_target is prohibited without a documented trust-boundary review")

    jobs = data.get("jobs") or {}
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            result.errors.append(f"job {job_name!r} must be a mapping")
            continue
        if "uses" not in job and "timeout-minutes" not in job:
            result.warnings.append(f"job {job_name!r} has no timeout-minutes")
        local_call = job.get("uses")
        if isinstance(local_call, str) and local_call.startswith("./"):
            target = ROOT / local_call.removeprefix("./")
            if not target.is_file():
                result.errors.append(f"job {job_name!r} references missing reusable workflow {local_call}")

    deploy_jobs_detected: set[str] = set()
    artifact_uploads: set[str] = set()
    artifact_downloads: set[str] = set()
    pages_upload_jobs: set[str] = set()
    pages_deploy_jobs: set[str] = set()
    for job_name, _, step in iter_steps(data):
        uses = step.get("uses")
        if isinstance(uses, str):
            match = USES.match(uses)
            assert match
            target, ref = match.group("target"), match.group("ref")
            if target.startswith("./"):
                local = ROOT / target.removeprefix("./")
                if not local.exists():
                    result.errors.append(f"job {job_name!r} references missing local action {target}")
            elif not ref or not SHA.fullmatch(ref):
                result.errors.append(f"external action is not pinned to a full commit SHA: {uses}")
            if "deploy" in target or "build-push-action" in target:
                deploy_jobs_detected.add(job_name)
            action_inputs = step.get("with") or {}
            if target == "actions/upload-artifact" and isinstance(action_inputs, dict):
                artifact_uploads.add(str(action_inputs.get("name", "artifact")))
            if target == "actions/download-artifact" and isinstance(action_inputs, dict):
                artifact_downloads.add(str(action_inputs.get("name", "artifact")))
            if target == "actions/upload-pages-artifact":
                pages_upload_jobs.add(job_name)
            if target == "actions/deploy-pages":
                pages_deploy_jobs.add(job_name)
            if target == "actions/checkout":
                persist = (step.get("with") or {}).get("persist-credentials")
                job = jobs[job_name]
                job_pushes = any(
                    isinstance(candidate.get("run"), str) and "git push" in candidate["run"]
                    for candidate in job.get("steps", [])
                    if isinstance(candidate, dict)
                )
                if persist is None:
                    result.warnings.append(
                        f"job {job_name!r} leaves checkout credentials enabled implicitly; set "
                        f"persist-credentials: {'true with a justification' if job_pushes else 'false'}"
                    )
        run = step.get("run")
        step_name = str(step.get("name", "")).lower()
        continue_on_error = step.get("continue-on-error")
        critical_label = " ".join((step_name, str(step.get("uses", "")))).lower()
        if str(continue_on_error).lower() == "true" and any(
            keyword in critical_label
            for keyword in ("security", "secret", "dependency", "test", "build", "deploy")
        ):
            result.warnings.append(
                f"job {job_name!r} makes critical step {step.get('name')!r} non-blocking; "
                "remove continue-on-error after its prerequisite is enabled"
            )
        if isinstance(run, str):
            if SECRET_IN_RUN.search(run):
                result.errors.append(
                    f"job {job_name!r} interpolates a secret directly into a run script; pass it through env"
                )
            if "curl " in run and "HOOK" in run:
                deploy_jobs_detected.add(job_name)

    missing_artifacts = artifact_downloads - artifact_uploads
    if missing_artifacts:
        result.errors.append(
            "downloaded artifacts have no same-workflow producer: "
            + ", ".join(sorted(missing_artifacts))
        )

    for job_name in pages_deploy_jobs:
        job = jobs[job_name]
        needs = job.get("needs")
        dependencies = {needs} if isinstance(needs, str) else set(needs or [])
        if not pages_upload_jobs.intersection(dependencies):
            result.errors.append(
                f"Pages deploy job {job_name!r} must need a job that uploads the Pages artifact"
            )
        environment = job.get("environment")
        environment_name = environment.get("name") if isinstance(environment, dict) else environment
        if environment_name != "github-pages":
            result.errors.append(
                f"Pages deploy job {job_name!r} must use the github-pages environment"
            )
        job_permissions = job.get("permissions")
        if (
            not isinstance(job_permissions, dict)
            or job_permissions.get("pages") != "write"
            or job_permissions.get("id-token") != "write"
        ):
            result.errors.append(
                f"Pages deploy job {job_name!r} must scope pages: write and id-token: write locally"
            )

    deploy_jobs = [
        (name, job)
        for name, job in jobs.items()
        if isinstance(job, dict) and name in deploy_jobs_detected
    ]
    for job_name, job in deploy_jobs:
        if "environment" not in job:
            result.warnings.append(
                f"GOVERNANCE: deployment job {job_name!r} has no protected environment binding"
            )
        if len(jobs) > 1 and "needs" not in job:
            result.errors.append(f"deployment job {job_name!r} is not gated by job dependencies")

    scheduled = isinstance(triggers, dict) and "schedule" in triggers
    chained = isinstance(triggers, dict) and "workflow_run" in triggers
    if scheduled or chained:
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            job_permissions = job.get("permissions", permissions)
            has_write = (
                isinstance(job_permissions, dict)
                and job_permissions.get("contents") == "write"
            )
            direct_push = any(
                isinstance(step.get("run"), str) and "git push" in step["run"]
                for step in job.get("steps") or []
                if isinstance(step, dict)
            )
            if has_write and direct_push and "environment" not in job:
                result.warnings.append(
                    f"GOVERNANCE: unattended job {job_name!r} can push repository content "
                    "without a protected approval environment"
                )


def scalar_keys(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(str(key) for key in value) or "none"
    if isinstance(value, list):
        return ", ".join(map(str, value)) or "none"
    return str(value or "none")


def inventory(result: Result) -> str:
    data = result.data
    jobs = data.get("jobs") or {}
    permissions = data.get("permissions") or {}
    secret_names = sorted(set(re.findall(r"secrets\.([A-Z0-9_]+)", result.path.read_text())))
    actions = [step["uses"] for _, _, step in iter_steps(data) if isinstance(step.get("uses"), str)]
    artifacts = [action for action in actions if "artifact" in action]
    caches = [
        f"{name}:{step.get('with', {}).get('cache')}"
        for name, _, step in iter_steps(data)
        if isinstance(step.get("with"), dict) and step["with"].get("cache")
    ]
    environments = [str(job["environment"]) for job in jobs.values() if isinstance(job, dict) and "environment" in job]
    needs = [
        f"{name}<-{job['needs']}"
        for name, job in jobs.items()
        if isinstance(job, dict) and "needs" in job
    ]
    deployment_targets = []
    text = result.path.read_text(encoding="utf-8")
    if "deploy-pages" in text:
        deployment_targets.append("GitHub Pages")
    if "RENDER_DEPLOY_HOOK_URL" in text:
        deployment_targets.append("Render")
    if "ghcr.io" in text:
        deployment_targets.append("GHCR")
    risk = "; ".join(result.errors + result.warnings) or "No source-verifiable failure risk found."
    remediation = []
    if result.errors:
        remediation.append("Patch every ERROR before execution")
    if any("checkout credentials" in warning for warning in result.warnings):
        remediation.append("set checkout persist-credentials explicitly")
    if any("top-level write" in warning for warning in result.warnings):
        remediation.append("move write scopes to the consuming job")
    if any("non-blocking" in warning for warning in result.warnings):
        remediation.append("restore fail-closed enforcement for the critical step")
    if any(warning.startswith("GOVERNANCE:") for warning in result.warnings):
        remediation.append("bind mutation/deployment to an approved protected environment")
    return (
        f"| `{result.path.name}` | {result.status} | {scalar_keys(data.get('on'))} | "
        f"{scalar_keys(permissions)} | {', '.join(secret_names) or 'none'} | "
        f"{', '.join(jobs) or 'none'}; needs: {', '.join(needs) or 'none'} | "
        f"{', '.join(actions) or 'none'} | {len(artifacts)} artifact step(s); "
        f"cache: {', '.join(caches) or 'none'} | {', '.join(environments) or 'none'} | "
        f"{', '.join(deployment_targets) or 'none'} | {scalar_keys(data.get('concurrency'))} | "
        f"{risk} | {'; '.join(remediation) or 'No patch required.'} |"
    )


def json_inventory(result: Result) -> dict[str, Any]:
    """Return a machine-readable record without exposing secret values."""
    data = result.data
    jobs = data.get("jobs") or {}
    actions = [step["uses"] for _, _, step in iter_steps(data) if isinstance(step.get("uses"), str)]
    artifact_actions = [action for action in actions if "artifact" in action]
    caches = [
        {"job": name, "type": step["with"]["cache"]}
        for name, _, step in iter_steps(data)
        if isinstance(step.get("with"), dict) and step["with"].get("cache")
    ]
    return {
        "workflow": result.path.name,
        "status": result.status,
        "triggers": list((data.get("on") or {}).keys()) if isinstance(data.get("on"), dict) else data.get("on"),
        "permissions": data.get("permissions"),
        "secret_names": sorted(set(re.findall(r"secrets\.([A-Z0-9_]+)", result.path.read_text()))),
        "actions": actions,
        "artifact_actions": artifact_actions,
        "caches": caches,
        "concurrency": data.get("concurrency"),
        "jobs": {
            name: {
                "needs": job.get("needs"),
                "permissions": job.get("permissions"),
                "environment": job.get("environment"),
                "timeout_minutes": job.get("timeout-minutes"),
            }
            for name, job in jobs.items()
            if isinstance(job, dict)
        },
        "errors": result.errors,
        "warnings": result.warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", action="store_true", help="emit exhaustive Markdown inventory")
    parser.add_argument("--json", action="store_true", help="emit machine-readable inventory")
    args = parser.parse_args()
    paths = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    if not paths:
        print("ERROR: no workflows found", file=sys.stderr)
        return 1
    results = [load(path) for path in paths]
    for result in results:
        audit(result)
    if args.json:
        print(json.dumps([json_inventory(result) for result in results], indent=2, sort_keys=True))
    elif args.markdown:
        print("| Workflow | Status | Triggers | Permissions | Secrets | Jobs / needs | Actions | Artifacts / caches | Environments | Targets | Concurrency | Exact risk | Exact remediation |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for result in results:
            print(inventory(result))
    else:
        for result in results:
            print(f"{result.path.relative_to(ROOT)}: {result.status}")
            for item in result.errors:
                print(f"  ERROR: {item}")
            for item in result.warnings:
                print(f"  WARNING: {item}")
    return 1 if any(result.errors for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
