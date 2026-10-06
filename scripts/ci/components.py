#!/usr/bin/env python3
"""The one table of build components that CI, previews and auto-fix share.

``ci.yml`` turns it into the ``stack`` matrix, ``deploy-staging.yml`` into the set
of services a pull request previews, and ``auto-fix.yml`` into which fixers run for
which failing check. Keeping it in one place is the point: three workflows that each
carried their own idea of "the storefront lives in storefront/" would drift.

Selection is fail-safe in the direction of running *more*: no base commit, an
unknown base, a shallow clone that cannot diff, or a change to the shared CI
plumbing all select every component. Skipping a component that did change is the
expensive mistake; building one that did not is only slow.

Stdlib only, no network.

    python3 scripts/ci/components.py matrix --base <sha> --head <sha>
    python3 scripts/ci/components.py services --base <sha> --head <sha>
    python3 scripts/ci/components.py get control-plane
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

#: Every component the stack matrix knows about. ``path`` is repository-relative.
#: ``python_format`` / ``python_typecheck`` are opt-ins: the root pyproject.toml
#: carries a strict ``[tool.mypy]`` block that nothing has ever enforced, so turning
#: it on is its own change, not a side effect of adding CI.
#: ``deploy`` is what the preview/promotion pipeline needs; absent = not deployable.
COMPONENTS: dict[str, dict[str, Any]] = {
    "control-plane": {
        "language": "python",
        "path": "control-plane",
        "python_version": "3.11",
        "requirements": "control-plane/requirements.txt",
        "python_format": "none",
        "python_typecheck": False,
        "deploy": {
            "port": 8000,
            # Preview revisions run in mock mode against a throwaway SQLite file:
            # no Stripe key, no database to provision, nothing shared between PRs.
            # ADMIN_API_KEY is mandatory: unset means open dev mode, which on a
            # public preview URL would expose approvals, pricing and refunds.
            # "@random" is replaced per deploy by release.py and never stored.
            "preview_env": {
                "APP_ENV": "preview",
                "ADMIN_API_KEY": "@random",
                "DATABASE_URL": "sqlite:////tmp/preview.db",
                "AUTO_CREATE_TABLES": "true",
                "RUN_MIGRATIONS": "false",
            },
            # METHOD PATH EXPECTED — the last line proves the admin gate is live
            # in the deployed artefact, not just in the test suite.
            "smoke": [
                "GET /health 200",
                "GET /ready 200",
                "GET /openapi.json 200",
                "GET /events 401,403",
            ],
        },
    },
    "storefront": {
        "language": "node",
        "path": "storefront",
        "node_version": "20",
        "deploy": {"port": 3000, "preview_env": {}, "smoke": ["GET / 200"]},
    },
    "admin": {
        "language": "node",
        "path": "admin",
        "node_version": "20",
        "deploy": {"port": 3000, "preview_env": {}, "smoke": ["GET / 200,302,307,401"]},
    },
}

#: A change to any of these can change how *every* component is built or checked,
#: so it selects them all.
SHARED_PATHS = (
    ".github/workflows/ci.yml",
    ".github/workflows/reusable-ci.yml",
    ".github/workflows/reusable-deploy.yml",
    ".github/workflows/deploy-staging.yml",
    ".github/actions/setup-node-python/",
    ".github/actions/run-smoke-tests/",
    "scripts/ci/components.py",
    "scripts/ci/deploy_target.sh",
    "pyproject.toml",
)

ZERO_SHA = "0" * 40


def changed_files(base: str | None, head: str) -> list[str] | None:
    """Files changed between two commits, or None when that cannot be known."""
    if not base or base == ZERO_SHA:
        return None
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", base, head],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return [line for line in proc.stdout.splitlines() if line.strip()]


def select(files: list[str] | None) -> list[str]:
    """Component names a change touches. None (unknown) selects everything."""
    if files is None:
        return list(COMPONENTS)
    if any(f == shared or f.startswith(shared) for f in files for shared in SHARED_PATHS):
        return list(COMPONENTS)
    picked = []
    for name, spec in COMPONENTS.items():
        prefix = spec["path"].rstrip("/") + "/"
        if any(f.startswith(prefix) for f in files):
            picked.append(name)
    return picked


def matrix_entry(name: str) -> dict[str, Any]:
    spec = COMPONENTS[name]
    return {
        "component": name,
        "language": spec["language"],
        "path": spec["path"],
        "python-version": spec.get("python_version", ""),
        "node-version": spec.get("node_version", ""),
        "requirements": spec.get("requirements", ""),
        "python-format": spec.get("python_format", "none"),
        "python-typecheck": bool(spec.get("python_typecheck", False)),
    }


def service_entry(name: str) -> dict[str, Any]:
    spec = COMPONENTS[name]
    deploy = spec["deploy"]
    return {
        "service": name,
        "path": spec["path"],
        "port": deploy["port"],
        "preview-env": ",".join(f"{k}={v}" for k, v in deploy["preview_env"].items()),
        "smoke": "\n".join(deploy["smoke"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("matrix", "services"):
        p = sub.add_parser(command)
        p.add_argument("--base", default="", help="base commit; empty or all-zero selects everything")
        p.add_argument("--head", default="HEAD")
        p.add_argument("--all", action="store_true", help="select every component")
        p.add_argument(
            "--only",
            default="",
            help="comma-separated allow-list applied after selection (e.g. a PREVIEW_SERVICES variable)",
        )
    get = sub.add_parser("get")
    get.add_argument("name", choices=sorted(COMPONENTS))
    args = parser.parse_args(argv)

    if args.command == "get":
        print(json.dumps({"name": args.name, **COMPONENTS[args.name]}, indent=2))
        return 0

    names = list(COMPONENTS) if args.all else select(changed_files(args.base, args.head))
    if args.only:
        allowed = {item.strip() for item in args.only.split(",") if item.strip()}
        names = [name for name in names if name in allowed]

    if args.command == "matrix":
        include = [matrix_entry(name) for name in names]
    else:
        include = [service_entry(name) for name in names if "deploy" in COMPONENTS[name]]

    # GITHUB_OUTPUT format: one key=value per line, JSON kept on a single line.
    print(f"matrix={json.dumps({'include': include}, separators=(',', ':'))}")
    print(f"any={'true' if include else 'false'}")
    print(f"names={','.join(entry.get('component') or entry['service'] for entry in include)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
