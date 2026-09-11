#!/usr/bin/env python3
"""Run every gate ``.github/workflows/ci.yml`` defines, locally.

Why this exists
---------------
GitHub Actions has not dispatched a runner for this repository since
2026-09-06 (``PRODUCTION-RECOVERY.md`` §1.1: ``runner_id 0``, 0 billable ms,
every head since). Jobs are assigned a runner, die in 3-5 seconds and produce
no retrievable logs. The remaining explanation is an organisation-level
entitlement problem - billing hold, spending limit, or an allowed-actions
policy - which is a settings change, not a code change.

The practical consequence is worse than a red badge: every gate silently stops
reporting, so regressions land unobserved. Six merges went in behind that
block, and the state they left behind was 7 failing tests, 6 ruff errors and
three separate generated-asset drifts - none of which anything told anyone
about.

This script restores the signal without Actions. It is the same commands
ci.yml runs, in the same order, against the working tree.

Usage
-----
    python3 scripts/ci_local.py              # offline gates (the default)
    python3 scripts/ci_local.py --list       # show the gates and exit
    python3 scripts/ci_local.py --with-network   # also run Lighthouse

Exit status is 0 only when every gate that ran passed, so it is usable as a
pre-push hook or a release check.

Keep this file in step with ci.yml. If a job is added there and not here, this
script will quietly under-report - the same failure mode it exists to prevent.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


class Gate:
    """One CI job, or one step of one, reduced to a runnable command."""

    def __init__(
        self,
        job: str,
        name: str,
        command: list[str],
        *,
        needs_network: bool = False,
        needs: str | None = None,
    ) -> None:
        self.job = job
        self.name = name
        self.command = command
        self.needs_network = needs_network
        self.needs = needs  # executable that must be on PATH

    def skip_reason(self, with_network: bool) -> str | None:
        if self.needs_network and not with_network:
            return "network gate; re-run with --with-network"
        if self.needs and shutil.which(self.needs) is None:
            return f"{self.needs} not on PATH"
        return None


# Mirrors .github/workflows/ci.yml. The search-integrity job is expanded into
# its three steps because the first is a generator + drift check, and knowing
# which of the three failed is the whole point of running it.
GATES: list[Gate] = [
    Gate("python-tests", "pytest tests/", [sys.executable, "-m", "pytest", "tests/", "-q"]),
    Gate("lint", "ruff check .", [sys.executable, "-m", "ruff", "check", "."]),
    Gate(
        "site-audit",
        "site reliability audit",
        [sys.executable, "scripts/site_reliability_audit.py"],
    ),
    Gate(
        "search-integrity",
        "generated search assets are current",
        [sys.executable, "scripts/_ci_local_search_assets.py"],
    ),
    Gate(
        "search-integrity",
        "indexability, metadata and JSON-LD",
        [sys.executable, "tools/seo_audit.py"],
    ),
    Gate(
        "search-integrity",
        "generated internal links",
        [sys.executable, "tools/internal_links.py", "--check"],
    ),
    Gate(
        "workflow-doctor",
        "workflow doctor",
        [sys.executable, "scripts/workflow_doctor.py"],
    ),
    Gate(
        "workflow-doctor",
        "workflow safety invariants",
        [sys.executable, "scripts/audit_github_actions.py"],
    ),
    Gate(
        "osint-deck",
        "OSINT deck release gate",
        [sys.executable, "scripts/osint_deck_release.py", "--strict"],
    ),
    Gate(
        "lighthouse",
        "Lighthouse budgets",
        ["npx", "--yes", "@lhci/cli@0.15.1", "autorun", "--config=lighthouserc.json"],
        needs_network=True,
        needs="npx",
    ),
]


def run(gate: Gate) -> tuple[str, float, str]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            gate.command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=1800,
        )
    except subprocess.TimeoutExpired:
        return FAIL, time.monotonic() - started, "timed out after 1800s"
    except FileNotFoundError as exc:
        return FAIL, time.monotonic() - started, str(exc)

    elapsed = time.monotonic() - started
    if proc.returncode == 0:
        return PASS, elapsed, ""

    # Show the end of the output: these gates put the verdict last.
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    return FAIL, elapsed, "\n".join(tail[-25:])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--with-network",
        action="store_true",
        help="also run gates that download or fetch (Lighthouse)",
    )
    parser.add_argument("--list", action="store_true", help="list the gates and exit")
    args = parser.parse_args()

    if args.list:
        for gate in GATES:
            marker = " (network)" if gate.needs_network else ""
            print(f"{gate.job:<18} {gate.name}{marker}")
        return 0

    print(f"Running {len(GATES)} CI gates from .github/workflows/ci.yml\n")

    results: list[tuple[Gate, str, float, str]] = []
    for gate in GATES:
        reason = gate.skip_reason(args.with_network)
        if reason:
            results.append((gate, SKIP, 0.0, reason))
            print(f"  SKIP  {gate.name} - {reason}")
            continue

        status, elapsed, detail = run(gate)
        results.append((gate, status, elapsed, detail))
        print(f"  {status}  {gate.name}  ({elapsed:.1f}s)")
        if detail:
            for line in detail.splitlines():
                print(f"        | {line}")

    failed = [r for r in results if r[1] == FAIL]
    passed = [r for r in results if r[1] == PASS]
    skipped = [r for r in results if r[1] == SKIP]

    print(
        f"\n{len(passed)} passed, {len(failed)} failed, {len(skipped)} skipped"
    )
    if failed:
        print("\nFailed gates:")
        for gate, _status, _elapsed, _detail in failed:
            print(f"  - {gate.job}: {gate.name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
