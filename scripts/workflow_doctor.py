#!/usr/bin/env python3
"""Audit and repair this repository's GitHub Actions workflows.

Two jobs, deliberately kept separate:

* **audit** (the default, and what ``workflow-doctor.yml`` runs on every push)
  reports drift without touching the tree — unparseable YAML, external actions
  that are not pinned to a full commit SHA, and action majors that have moved
  on. Exits non-zero when it finds anything, so it can gate a pull request.
* **repair** (``--fix``) rewrites only what it can rewrite safely: action
  version bumps, applied to the raw text so every comment, blank line and
  quoting style in the file survives untouched.

Pinning is the control that matters most here. A tag such as ``@v4`` is a
*mutable* reference: whoever owns the action can repoint it at any commit, at
any time, and every workflow in this repository would run that code with the
permissions it was granted. A 40-character commit SHA cannot be repointed. So
an unpinned external action is reported as an ERROR, and ``--fix`` will never
"helpfully" turn a SHA back into a tag — the SHA branch is a hard no-op.

``scripts/audit_github_actions.py`` is the companion gate: it enforces the
safety invariants (permissions, credentials, approval environments) that this
script does not. Run both; ``workflow-doctor.yml`` does.

Usage::

    python scripts/workflow_doctor.py           # audit, exit 1 on findings
    python scripts/workflow_doctor.py --fix     # apply version bumps in place
    python scripts/workflow_doctor.py --json    # audit, machine-readable

Requires PyYAML, which ``workflow-doctor.yml`` installs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - dependency guard
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
ACTION_DIR = ROOT / ".github" / "actions"

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
USES_RE = re.compile(r"^(?P<indent>\s*-?\s*uses:\s*)(?P<ref>\S+)(?P<rest>.*)$")

# Current stable major for each action this repository uses, taken from the
# versions already pinned across .github/workflows/ rather than invented. A
# bump only ever moves a *tag* forward; SHA pins are never touched, so this
# table cannot silently downgrade a pin into a mutable reference.
STABLE_MAJORS: dict[str, str] = {
    "actions/checkout": "v6",
    "actions/upload-artifact": "v7",
    "actions/download-artifact": "v4",
    "actions/setup-python": "v6",
    "actions/setup-node": "v6",
    "actions/github-script": "v9",
    "actions/configure-pages": "v6",
    "actions/deploy-pages": "v5",
    "actions/upload-pages-artifact": "v5",
    "actions/dependency-review-action": "v5",
    "actions/attest-build-provenance": "v4",
}


def dump_yaml(data: Any) -> str:
    """Serialise a parsed workflow, preserving GitHub's literal ``on`` key.

    PyYAML implements YAML 1.1, where a bare ``on:`` is the *boolean* True.
    Round-tripping a workflow therefore renames its trigger block to ``true:``
    and GitHub silently stops running it — the workflow becomes a no-op that
    still looks fine in review. Rename the key back on the way out.
    """
    if isinstance(data, dict) and True in data:
        data = {("on" if key is True else key): value for key, value in data.items()}
    text = yaml.safe_dump(data, sort_keys=False, default_flow_style=False, width=4096)
    # safe_dump quotes 'on' because it is a YAML 1.1 boolean. GitHub accepts the
    # quoted form, but every workflow in this repo writes it bare; match them.
    return re.sub(r"^'on':", "on:", text, flags=re.MULTILINE)


def patch_action_versions(text: str) -> tuple[str, list[str]]:
    """Bump known action majors in raw workflow text.

    Returns ``(new_text, changes)``. Operating on text rather than a parsed
    document is deliberate: a parse/dump round-trip would reformat the whole
    file and bury the one-line change it was asked to make.
    """
    changes: list[str] = []
    lines = text.splitlines(keepends=True)

    for index, line in enumerate(lines):
        match = USES_RE.match(line.rstrip("\n"))
        if not match:
            continue
        ref = match.group("ref")
        if "@" not in ref:
            continue
        target, _, version = ref.partition("@")
        # A pinned SHA is the desired end state — never rewrite one.
        if SHA_RE.match(version):
            continue
        wanted = STABLE_MAJORS.get(target)
        if wanted is None or version == wanted:
            continue
        newline = "\n" if line.endswith("\n") else ""
        lines[index] = (
            f"{match.group('indent')}{target}@{wanted}{match.group('rest')}{newline}"
        )
        changes.append(f"{target}: {version} -> {wanted}")

    return "".join(lines), changes


def _steps_of(data: Any) -> list[dict[str, Any]]:
    """Every step in a workflow or a composite action definition."""
    steps: list[dict[str, Any]] = []
    if not isinstance(data, dict):
        return steps

    # Composite action: runs.steps
    runs = data.get("runs")
    if isinstance(runs, dict):
        for step in runs.get("steps") or []:
            if isinstance(step, dict):
                steps.append(step)

    # Workflow: jobs.<id>.steps, plus a reusable-workflow job's own `uses`
    for job in (data.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        if isinstance(job.get("uses"), str):
            steps.append({"uses": job["uses"]})
        for step in job.get("steps") or []:
            if isinstance(step, dict):
                steps.append(step)
    return steps


def unpinned_external_actions(path: Path, text: str) -> list[str]:
    """Report every external action reference not pinned to a full commit SHA.

    Local actions (``./.github/actions/...``) and reusable workflows in this
    repository are exempt: they are versioned by the commit being run. Docker
    references are out of scope for a SHA pin check.
    """
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"ERROR {path}: unparseable YAML: {exc}"]

    findings: list[str] = []
    for step in _steps_of(data):
        ref = step.get("uses")
        if not isinstance(ref, str):
            continue
        if ref.startswith("./") or ref.startswith("docker://"):
            continue
        _, _, version = ref.partition("@")
        if SHA_RE.match(version):
            continue
        findings.append(
            f"ERROR {path}: external action is not pinned to a full commit SHA: {ref}"
        )
    return findings


def iter_targets() -> list[Path]:
    """Every workflow and composite action definition, in a stable order."""
    targets = sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))
    for pattern in ("*/action.yml", "*/action.yaml"):
        targets.extend(sorted(ACTION_DIR.glob(pattern)))
    return targets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true",
                        help="Apply action version bumps in place.")
    parser.add_argument("--json", action="store_true",
                        help="Emit findings as JSON.")
    args = parser.parse_args(argv)

    if not WORKFLOW_DIR.is_dir():
        print(f"no workflow directory at {WORKFLOW_DIR}", file=sys.stderr)
        return 1

    errors: list[str] = []
    bumps: list[str] = []
    changed: list[str] = []

    for path in iter_targets():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)

        errors.extend(unpinned_external_actions(rel, text))

        updated, changes = patch_action_versions(text)
        if changes:
            bumps.extend(f"{rel}: {change}" for change in changes)
            if args.fix:
                path.write_text(updated, encoding="utf-8")
                changed.append(str(rel))

    if args.json:
        print(json.dumps({
            "targets": len(iter_targets()),
            "errors": errors,
            "available_bumps": bumps,
            "files_changed": changed,
        }, indent=2))
    else:
        for error in errors:
            print(error, file=sys.stderr)
        for bump in bumps:
            print(("FIXED " if args.fix else "BUMP  ") + bump)
        verb = "repaired" if args.fix else "audited"
        print(f"{verb} {len(iter_targets())} file(s): "
              f"{len(errors)} error(s), {len(bumps)} version bump(s)")

    if errors:
        return 1
    # In audit mode an available bump is drift worth failing on; --fix has
    # already applied it, so the run is clean.
    return 1 if bumps and not args.fix else 0


if __name__ == "__main__":
    raise SystemExit(main())
