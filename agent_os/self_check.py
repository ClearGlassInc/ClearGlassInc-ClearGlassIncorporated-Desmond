# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Governance self-check + executive report for the Autonomous Agent OS.

Runs stdlib-only so it executes inside GitHub Actions as a dry-run assurance
pass. It proves the safety invariant (every always-escalate action is gated,
unknown actions are gated, unverifiable actions are gated), verifies the audit
chain is tamper-evident, and then emits a demonstration mission report. Exit
code is non-zero if any invariant fails, so CI fails closed.

    python -m agent_os.self_check          # human-readable
    python -m agent_os.self_check --json   # machine-readable
"""
from __future__ import annotations

import argparse
import json

from .audit import AuditLedger
from .executive import Strategy
from .governance import ALWAYS_ESCALATE, score_action
from .intelligence import Claim
from .orchestrator import (
    DECISION_FRAMEWORK,
    EXECUTION_LOOP,
    OUTPUT_FIELDS,
    AgentOS,
    ProposedAction,
)
from .planning import Task
from .roster import ROSTER


def governance_selfcheck() -> list[str]:
    """Assert the safety invariant. Returns a list of violations (empty == pass)."""
    failures: list[str] = []
    for action in sorted(ALWAYS_ESCALATE):
        if not score_action(action, {}).requires_approval:
            failures.append(f"INVARIANT VIOLATED: '{action}' did not require approval")
    if not score_action("totally_unknown_action", {}).requires_approval:
        failures.append("INVARIANT VIOLATED: unknown action was not gated")
    if not score_action("read_metrics", {}, confidence=None).requires_approval:
        failures.append("INVARIANT VIOLATED: unverifiable-confidence action was not gated")
    if not score_action("generate_copy", {}, has_evidence=False).requires_approval:
        failures.append("INVARIANT VIOLATED: evidence-free conclusion was not gated")
    return failures


def structural_selfcheck() -> list[str]:
    """Assert the OS structure matches the specification."""
    failures: list[str] = []
    if len(ROSTER) != 13:
        failures.append(f"roster has {len(ROSTER)} agents, expected 13")
    if len(DECISION_FRAMEWORK) != 12:
        failures.append(f"decision framework has {len(DECISION_FRAMEWORK)} steps, expected 12")
    if len(OUTPUT_FIELDS) != 13:
        failures.append(f"output template has {len(OUTPUT_FIELDS)} fields, expected 13")
    if len(EXECUTION_LOOP) != 9:
        failures.append(f"execution loop has {len(EXECUTION_LOOP)} phases, expected 9")
    return failures


def audit_selfcheck() -> list[str]:
    """Assert the audit ledger is tamper-evident."""
    failures: list[str] = []
    ledger = AuditLedger()
    ledger.append("a", {"n": 1})
    ledger.append("b", {"n": 2})
    ok, _ = ledger.verify()
    if not ok:
        failures.append("audit chain failed to verify a clean ledger")
    # Tamper with an entry and confirm detection.
    ledger.entries[0] = ledger.entries[0].__class__(
        index=0, kind="a", payload={"n": 999},
        prev_hash=ledger.entries[0].prev_hash, hash=ledger.entries[0].hash,
    )
    tampered_ok, bad = ledger.verify()
    if tampered_ok or bad != 0:
        failures.append("audit chain did not detect tampering (fail closed)")
    return failures


def demo_mission() -> dict[str, object]:
    """A representative read-only mission exercising the advanced sub-agents."""
    report = AgentOS().run_mission(
        "Improve top-product conversion without touching live pricing",
        tasks=[
            Task("collect", est_minutes=5),
            Task("analyze", depends_on=("collect",), est_minutes=8),
            Task("draft", depends_on=("analyze",), est_minutes=4),
        ],
        strategies=[
            Strategy("faq_block", value=100, probability=0.7, cost=10, risk=0.1),
            Strategy("price_cut", value=140, probability=0.6, cost=20, risk=0.5),
        ],
        claims=[
            Claim("hero_cvr", "1.2%", source="analytics", authority=0.9),
            Claim("hero_cvr", "1.2%", source="warehouse", authority=0.8),
        ],
        proposed_actions=[
            ProposedAction(
                "generate_copy", "Draft an improved hero-product FAQ block",
                confidence=0.82, evidence=("hero page CVR 1.2% vs site 2.1%",),
            ),
            ProposedAction(
                "update_pricing", "Cut hero SKU price 15%",
                payload={"old_price": 100, "new_price": 85},
                confidence=0.7, evidence=("competitor scan",),
            ),
        ],
        assumptions=["analytics feed is current", "no active promo overlaps"],
    )
    return report.to_dict()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ClearGlass Agent OS self-check")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    failures = governance_selfcheck() + structural_selfcheck() + audit_selfcheck()
    report = demo_mission()

    if args.json:
        print(json.dumps({"failures": failures, "demo_mission": report}, indent=2))
    else:
        print("# ClearGlass Autonomous Agent OS v8.0 — Self-Check\n")
        print(f"- Sub-agents online: {len(ROSTER)}/13")
        print(f"- Governance invariant: {'PASS' if not failures else 'FAIL'}")
        print(f"- Audit chain verified: {report['validation_results']['audit_chain_verified']}")
        print(f"- Demo mission gate: {report['validation_results']['gated_actions']} gated, "
              f"{report['validation_results']['auto_actions']} auto")
        print(f"\n{report['mission_summary']}")
        if failures:
            print("\n## Violations")
            print("\n".join(failures))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
