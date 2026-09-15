#!/usr/bin/env python3
# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Scan the working tree for credentials that should never be committed.

Extracted verbatim from the heredoc that used to live inside
``.github/workflows/security.yml`` so that two callers can share one pattern
list: the Security workflow's gate, and the Maintenance Review loop, which
treats a red secret scan as a circuit breaker that halts all automated change.
Two copies of this list would drift, and the way it drifts is that the copy
feeding the breaker stops matching the thing the gate was written to catch.

Exit code is the contract: 0 = clean, 1 = findings (or an unreadable tree).

    python3 scripts/secret_scan.py
    python3 scripts/secret_scan.py --json
    python3 scripts/secret_scan.py --root control-plane
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

#: What a committed credential looks like. Deliberately high-signal patterns:
#: this gate blocks merges and halts automation, so a false positive is expensive.
PATTERNS: dict[str, str] = {
    "AWS access key": r"AKIA[0-9A-Z]{16}",
    "GitHub PAT (ghp_)": r"ghp_[A-Za-z0-9]{36}",
    "GitHub PAT (ghs_)": r"ghs_[A-Za-z0-9]{36}",
    "GitLab PAT": r"glpat-[A-Za-z0-9_-]{20}",
    "Generic API key": r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9/+]{20,}['\"]",
    "Private key header": r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----",
    # Live payment credentials. A test key is not a finding — publishing one is
    # harmless and the repository documents mock-mode setup with them — but a
    # live key in source control is an incident.
    "Stripe live secret key": r"sk_live_[A-Za-z0-9]{20,}",
    "Stripe live restricted key": r"rk_live_[A-Za-z0-9]{20,}",
}

#: File types worth reading. Binary and vendored trees are skipped below.
EXTENSIONS = frozenset(
    {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".env", ".json", ".yaml", ".yml", ".sh"}
)

#: Directory names never scanned — vendored or generated, and not ours to fix.
SKIP_PARTS = frozenset({".git", "node_modules", "dist", "build", ".venv", "venv"})


def scan(root: Path) -> list[str]:
    """Return ``"path: label"`` for every credential-shaped match under ``root``."""
    findings: list[str] = []
    compiled = {label: re.compile(pattern) for label, pattern in PATTERNS.items()}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in EXTENSIONS:
            continue
        if SKIP_PARTS & set(path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            # An unreadable file is not evidence of cleanliness, but it is also
            # not a finding; the walk continues and the run stays honest.
            continue
        for label, pattern in compiled.items():
            if pattern.search(text):
                findings.append(f"{path}: {label}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="directory to scan (default: the working tree)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 1

    findings = scan(root)
    if args.json:
        print(json.dumps({"clean": not findings, "findings": findings}, indent=2))
    elif findings:
        for finding in findings:
            print(f"::error::{finding}")
    else:
        print("No hardcoded secrets detected.")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
