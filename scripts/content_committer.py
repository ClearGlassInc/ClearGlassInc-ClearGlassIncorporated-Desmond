#!/usr/bin/env python3
# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Auto-commit bot-generated output files.

Stages changed files under marketing/output/ and operations/output/,
then creates a signed commit with [skip ci] to avoid re-triggering CI.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIRS = [
    "marketing/output",
    "operations/output",
]

BOT_AUTHOR_NAME = "github-actions[bot]"
BOT_AUTHOR_EMAIL = "github-actions[bot]@users.noreply.github.com"


def _git(*args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def commit_outputs(dry_run: bool = False, message: str | None = None) -> bool:
    _git("config", "user.name", BOT_AUTHOR_NAME)
    _git("config", "user.email", BOT_AUTHOR_EMAIL)

    staged_any = False
    for output_dir in OUTPUT_DIRS:
        path = ROOT / output_dir
        if path.exists():
            code, _ = _git("add", str(path))
            if code == 0:
                staged_any = True

    if not staged_any:
        print("No output directories found — nothing to stage")
        return False

    code, diff = _git("diff", "--staged", "--stat")
    if not diff.strip():
        print("Outputs unchanged — nothing to commit")
        return False

    print(f"Staged changes:\n{diff}")

    if dry_run:
        print("[DRY-RUN] Would commit the above changes")
        return False

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    commit_msg = message or f"bot: update generated outputs — {ts} [skip ci]"

    code, out = _git("commit", "-m", commit_msg)
    if code != 0:
        print(f"Commit failed: {out}", file=sys.stderr)
        return False

    print(f"Committed: {commit_msg}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Commit bot-generated output files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be committed")
    parser.add_argument("--message", "-m", help="Custom commit message")
    args = parser.parse_args()

    committed = commit_outputs(dry_run=args.dry_run, message=args.message)
    sys.exit(0 if committed or args.dry_run else 0)


if __name__ == "__main__":
    main()
