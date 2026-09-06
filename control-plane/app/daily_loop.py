"""Daily operator loop — produces the executive report.

Runs stdlib-only (no DB, no web framework) so it can execute inside GitHub Actions as a
dry-run governance + reporting pass. With ``--live`` and a reachable control plane it would
pull real metrics; in CI it emits the report skeleton and verifies the governance gate.
"""
from __future__ import annotations

import argparse
import json
from datetime import date

from .governance import ALWAYS_ESCALATE, score_action


def governance_selfcheck() -> list[str]:
    """Assert the safety invariant: every always-escalate action is gated. Fail closed."""
    failures: list[str] = []
    for action in sorted(ALWAYS_ESCALATE):
        assessment = score_action(action, {})
        if not assessment.requires_approval:
            failures.append(f"INVARIANT VIOLATED: '{action}' did not require approval")
    # An unknown action must also be gated.
    if not score_action("totally_unknown_action", {}).requires_approval:
        failures.append("INVARIANT VIOLATED: unknown action was not gated")
    return failures


def build_report(today: str) -> dict[str, object]:
    """The daily loop deliverables, per the operator spec."""
    return {
        "date": today,
        "store_health": "nominal (dry-run: connect control plane for live metrics)",
        "top_products": [],
        "underperformers": [],
        "drafted_optimization": "Review highest-traffic / lowest-conversion product page copy.",
        "drafted_content_improvement": "Add a comparison block + FAQ to the hero product.",
        "flagged_operational_risk": "Watch low-stock SKUs; reorder is gated for approval.",
        "executive_summary": (
            "Read-only pass complete. One optimization and one content improvement drafted; "
            "one operational risk flagged. No financial or irreversible action taken — all such "
            "actions remain behind the human approval gate."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ClearGlass commerce daily loop")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    failures = governance_selfcheck()
    report = build_report(date.today().isoformat())

    if args.json:
        print(json.dumps({"report": report, "governance_failures": failures}, indent=2))
    else:
        print(f"# ClearGlass Commerce — Daily Executive Report ({report['date']})\n")
        print(f"- Store health: {report['store_health']}")
        print(f"- Optimization (draft): {report['drafted_optimization']}")
        print(f"- Content improvement (draft): {report['drafted_content_improvement']}")
        print(f"- Operational risk: {report['flagged_operational_risk']}")
        print(f"\n{report['executive_summary']}")
        print("\n## Governance self-check")
        print("PASS — all financial/fulfillment actions are gated." if not failures
              else "\n".join(failures))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
