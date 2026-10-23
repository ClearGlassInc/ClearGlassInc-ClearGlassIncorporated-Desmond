# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Deployment readiness — what would ship, and whether the tree is clean.

The deployment agent runs this and nothing else. It never deploys: production
deployment is manual and approval-gated (``DEPLOY.md``; ``deploy_production``
is in ``ALWAYS_ESCALATE``). What it contributes is the fact a human approving a
deploy needs — the exact commit, and that the working tree holds nothing that
commit does not.

    python -m agent_os.readiness    # JSON; exit 0 when clean, 1 when not

Stdlib only.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA = "clearglass.agent_os.readiness/1"
_ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str, root: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return proc.returncode, proc.stdout.strip()


def report(root: Path | str | None = None) -> dict[str, Any]:
    base = Path(root) if root is not None else _ROOT
    code_head, head = _git("rev-parse", "HEAD", root=base)
    _, branch = _git("rev-parse", "--abbrev-ref", "HEAD", root=base)
    code_status, status = _git("status", "--porcelain", root=base)
    dirty = [line for line in status.splitlines() if line.strip()] if code_status == 0 else []
    known = code_head == 0 and code_status == 0
    return {
        "schema": SCHEMA,
        "head": head if code_head == 0 else None,
        "branch": branch or None,
        "clean": known and not dirty,
        "uncommitted_paths": len(dirty),
        "deploy_executed": False,
        "note": "Readiness only. Deployment stays manual and approval-gated (DEPLOY.md).",
    }


def validate(document: object) -> list[str]:
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        return ["not a readiness report"]
    if document.get("deploy_executed") is not False:
        return ["readiness report claims a deployment ran"]
    head = document.get("head")
    if not (isinstance(head, str) and len(head) == 40):
        return ["readiness report has no commit"]
    return []


def main() -> int:
    result = report()
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if result["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
