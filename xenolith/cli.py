# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""XENOLITH operator CLI — governance self-check and command-surface feed.

    python -m xenolith.cli                 # human-readable status report
    python -m xenolith.cli --json          # full lattice state as JSON
    python -m xenolith.cli --check         # invariants only; exit 1 on failure
    python -m xenolith.cli --write PATH    # regenerate the operator feed

The ``--check`` mode is what CI runs: it exits non-zero if any governance
invariant fails, so a change that opens an ungoverned execution path breaks the
build rather than shipping quietly.

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .constellation import build

#: Where the static command surface reads its feed from.
DEFAULT_FEED = Path(__file__).resolve().parent.parent / "data" / "xenolith" / "lattice.json"


def _feed(state: dict[str, Any]) -> dict[str, Any]:
    """Trim the full state into the payload the command surface consumes.

    The page never needs the whole ledger; it needs posture, population, the
    approval queue and enough recent history to feel live. Keeping the feed
    small also keeps the committed JSON diffable.
    """
    return {
        "platform": state["platform"],
        "subtitle": state["subtitle"],
        "generated_at": state["generated_at"],
        "governance": state["governance"],
        "registry": state["registry"],
        "agents": state["agents"],
        "policy": state["policy"],
        "bus": state["bus"],
        "graph": state["graph"],
        "fusion": state["fusion"],
        "memory": state["memory"],
        "executive": state["executive"],
        "telemetry": {
            "ledger_entries": state["telemetry"]["ledger_entries"],
            "ledger_head": state["telemetry"]["ledger_head"],
            "ledger_intact": state["telemetry"]["ledger_intact"],
            "anomalies": state["telemetry"]["anomalies"],
            "recent": state["telemetry"]["recent"],
        },
    }


def _report(state: dict[str, Any]) -> str:
    gov = state["governance"]
    reg = state["registry"]
    lines = [
        "XENOLITH — ClearGlass sovereign intelligence lattice",
        "=" * 56,
        f"governance   {gov['passed']}/{gov['total']} invariants hold "
        f"({'FAIL-CLOSED' if gov['fail_closed'] else 'DEGRADED'})",
        f"population   {reg['population']} agents · {reg['actionable']} actionable "
        f"· mean health {reg['mean_health']}",
        f"policy       {state['policy']['rules']} rules · "
        f"{state['policy']['approvals_pending']} pending approval(s)",
        f"fusion       {state['fusion']['observations']} observations → "
        f"{state['fusion']['packets']} packet(s) from {state['fusion']['connectors']} connector(s)",
        f"graph        {state['graph']['entities']} entities · "
        f"{state['graph']['relationships']} edges · "
        f"{state['graph']['contradictions']} contradiction(s)",
        f"ledger       {state['telemetry']['ledger_entries']} entries · chain "
        f"{'intact' if state['telemetry']['ledger_intact'] else 'BROKEN'}",
        f"posture      {state['executive']['posture']}",
        "",
        "Invariants",
        "-" * 56,
    ]
    for check in gov["checks"]:
        lines.append(f"  [{'PASS' if check['passed'] else 'FAIL'}] {check['name']} — {check['detail']}")

    queue = state["policy"]["queue"]
    if queue:
        lines += ["", "Awaiting human authority", "-" * 56]
        for item in queue:
            lines.append(
                f"  {item['approval_id']}  {item['action']:<24} "
                f"risk {item['risk_score']:>3}/{item['tier']}  requested by {item['requested_by']}"
            )

    actions = state["executive"]["next_actions"]
    if actions:
        lines += ["", "Next actions by priority", "-" * 56]
        for item in actions:
            lines.append(
                f"  {item['priority']:.3f}  {item['task_id']}  "
                f"{item['action']:<24} {item['summary']}"
            )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="xenolith", description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="emit the full lattice state as JSON")
    parser.add_argument("--check", action="store_true", help="run invariants only; exit 1 on failure")
    parser.add_argument(
        "--write",
        nargs="?",
        const=str(DEFAULT_FEED),
        metavar="PATH",
        help=f"write the command-surface feed (default: {DEFAULT_FEED})",
    )
    parser.add_argument(
        "--no-traffic", action="store_true", help="build an empty lattice with no seeded activity"
    )
    args = parser.parse_args(argv)

    lattice = build(seed_traffic=not args.no_traffic)
    state = lattice.state()
    failed = [c for c in state["governance"]["checks"] if not c["passed"]]

    if args.check:
        for check in state["governance"]["checks"]:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']} — {check['detail']}")
        if failed:
            print(f"\n{len(failed)} governance invariant(s) FAILED", file=sys.stderr)
            return 1
        print(f"\nAll {len(state['governance']['checks'])} governance invariants hold.")
        return 0

    if args.write:
        target = Path(args.write)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(_feed(state), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {target}")
        return 1 if failed else 0

    print(json.dumps(state, indent=2, sort_keys=True) if args.json else _report(state))
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main())
