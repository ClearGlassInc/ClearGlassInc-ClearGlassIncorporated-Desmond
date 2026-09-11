#!/usr/bin/env python3
"""Build the GraphQL ``FileChanges`` payload for createCommitOnBranch.

Reads the currently staged git diff (must be run after ``git add``) and prints a
compact JSON object of the form::

    {"additions": [{"path": "...", "contents": "<base64>"}], "deletions": [{"path": "..."}]}

createCommitOnBranch requires added/modified file contents base64-encoded and
deletions listed by path. Renames are handled by git as delete + add via the
ACMR/D filters. stdlib only — GitHub runners always have python3.
"""
from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path


def _staged(diff_filter: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", f"--diff-filter={diff_filter}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def main() -> int:
    additions = []
    for path in _staged("ACMR"):  # added, copied, modified, renamed (new name)
        data = Path(path).read_bytes()
        additions.append({"path": path, "contents": base64.b64encode(data).decode("ascii")})
    deletions = [{"path": path} for path in _staged("D")]
    print(json.dumps({"additions": additions, "deletions": deletions}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
