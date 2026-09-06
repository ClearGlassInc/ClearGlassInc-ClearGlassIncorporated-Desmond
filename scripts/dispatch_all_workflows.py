#!/usr/bin/env python3
"""Dispatch every manually-runnable GitHub Actions workflow.

This is intentionally stdlib-only so it can run from any GitHub-hosted runner
or an operator workstation with Python. It dispatches workflows that declare
``workflow_dispatch`` and reports workflows that cannot be dispatched.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    print("Missing dependency: pyyaml. Install with: python -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
API_ROOT = "https://api.github.com"


@dataclass(frozen=True)
class WorkflowDispatch:
    path: Path
    name: str
    dispatchable: bool
    reason: str = ""

    @property
    def file_name(self) -> str:
        return self.path.name


def _on_block(document: dict[str, Any]) -> Any:
    # PyYAML 1.1 treats the bare key `on` as True.
    return document.get("on", document.get(True))


def _dispatch_inputs(on_block: Any) -> dict[str, Any]:
    if not isinstance(on_block, dict):
        return {}
    workflow_dispatch = on_block.get("workflow_dispatch")
    if not isinstance(workflow_dispatch, dict):
        return {}
    inputs = workflow_dispatch.get("inputs")
    return inputs if isinstance(inputs, dict) else {}


def _required_inputs(inputs: dict[str, Any]) -> list[str]:
    required: list[str] = []
    for name, spec in inputs.items():
        if isinstance(spec, dict) and spec.get("required") is True and "default" not in spec:
            required.append(str(name))
    return required


def discover_dispatchable(workflows_dir: Path = WORKFLOWS) -> list[WorkflowDispatch]:
    plans: list[WorkflowDispatch] = []
    for path in sorted(workflows_dir.glob("*.y*ml")):
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            plans.append(WorkflowDispatch(path, path.stem, False, f"YAML parse failed: {exc}"))
            continue
        if not isinstance(document, dict):
            plans.append(WorkflowDispatch(path, path.stem, False, "root document is not a mapping"))
            continue
        name = str(document.get("name") or path.stem)
        on_block = _on_block(document)
        has_dispatch = on_block == "workflow_dispatch" or (
            isinstance(on_block, list) and "workflow_dispatch" in on_block
        ) or (isinstance(on_block, dict) and "workflow_dispatch" in on_block)
        if not has_dispatch:
            plans.append(WorkflowDispatch(path, name, False, "missing workflow_dispatch trigger"))
            continue
        required = _required_inputs(_dispatch_inputs(on_block))
        if required:
            plans.append(
                WorkflowDispatch(path, name, False, "requires explicit input(s): " + ", ".join(required))
            )
            continue
        plans.append(WorkflowDispatch(path, name, True))
    return plans


def _request(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> tuple[int, str]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "clearglass-workflow-dispatcher",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - GitHub API URL only
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def dispatch(
    repo: str, ref: str, token: str, plans: list[WorkflowDispatch], delay: float, exclude: set[str]
) -> int:
    failures = 0
    for plan in plans:
        if plan.file_name in exclude:
            print(f"SKIP {plan.file_name}: excluded")
            continue
        if not plan.dispatchable:
            print(f"SKIP {plan.file_name}: {plan.reason}")
            continue
        url = f"{API_ROOT}/repos/{repo}/actions/workflows/{plan.file_name}/dispatches"
        status, body = _request("POST", url, token, {"ref": ref})
        if status == 204:
            print(f"OK   {plan.file_name}: dispatched {plan.name!r} on {ref}")
        else:
            failures += 1
            print(f"FAIL {plan.file_name}: HTTP {status} {body[:500]}", file=sys.stderr)
        if delay > 0:
            time.sleep(delay)
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch all workflow_dispatch GitHub Actions workflows.")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"), help="owner/repo")
    parser.add_argument("--ref", default=os.environ.get("GITHUB_REF_NAME", "main"), help="branch or tag to run")
    parser.add_argument("--token", default=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--dry-run", action="store_true", help="print dispatch plan without calling GitHub")
    parser.add_argument("--delay", type=float, default=0.25, help="seconds to wait between dispatch calls")
    parser.add_argument(
        "--exclude",
        action="append",
        default=["dispatch-all-workflows.yml"],
        help="workflow file name to skip; can be supplied multiple times",
    )
    args = parser.parse_args()

    plans = discover_dispatchable()
    if args.dry_run:
        exclude = set(args.exclude or [])
        for plan in plans:
            excluded = plan.file_name in exclude
            status = "SKIP" if excluded else ("DISPATCH" if plan.dispatchable else "SKIP")
            reason = "excluded" if excluded else plan.reason
            suffix = f" ({reason})" if reason else ""
            print(f"{status} {plan.file_name}: {plan.name}{suffix}")
        return 0
    if not args.repo or "/" not in args.repo:
        print("--repo or GITHUB_REPOSITORY must be set to owner/repo", file=sys.stderr)
        return 2
    if not args.token:
        print("--token, GH_TOKEN, or GITHUB_TOKEN is required to dispatch workflows", file=sys.stderr)
        return 2
    return dispatch(args.repo, args.ref, args.token, plans, args.delay, set(args.exclude or []))


if __name__ == "__main__":
    raise SystemExit(main())
