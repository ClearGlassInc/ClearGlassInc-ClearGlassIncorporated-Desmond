"""4-D Dominance pipeline entrypoint.

Runs the orchestrator across one or more of the four domains and emits a JSON
report. Everything runs in dry-run mode: the pipeline produces drafts and
plans, scores them, and routes anything risky to human approval — it never
publishes or deploys on its own.

    python -m four_d_dominance.pipeline --all --json
    python -m four_d_dominance.pipeline --domain web --output four_d_dominance/output
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .orchestrator import Orchestrator

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "output"
DOMAIN_ORDER = ("web", "ai", "corporate", "brand")


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(domains: list[str], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or load_config()
    orchestrator = Orchestrator()
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": config.get("mode", "dry-run"),
        "domains": {},
    }

    for name in domains:
        spec = config["domains"][name]
        domain_block: dict[str, Any] = {"label": spec["label"], "metric": spec["metric"], "tasks": []}
        for task in spec["tasks"]:
            outcome = orchestrator.run_task(task)
            domain_block["tasks"].append(outcome.summary())
        report["domains"][name] = domain_block

    task_summaries = [t for d in report["domains"].values() for t in d["tasks"]]
    report["totals"] = {
        "domains": len(report["domains"]),
        "tasks": len(task_summaries),
        "auto_executed": sum(1 for t in task_summaries if t["auto_executed"]),
        "awaiting_approval": sum(1 for t in task_summaries if t["requires_approval"]),
        "model_tokens": orchestrator.router.total_tokens,
    }
    return report


def _resolve_domains(args: argparse.Namespace) -> list[str]:
    if args.all or not args.domain:
        return list(DOMAIN_ORDER)
    return args.domain


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the 4-D Dominance pipeline (dry-run).")
    parser.add_argument(
        "--domain",
        action="append",
        choices=DOMAIN_ORDER,
        help="Domain to run (repeatable). Omit or use --all for every domain.",
    )
    parser.add_argument("--all", action="store_true", help="Run all four domains.")
    parser.add_argument("--json", action="store_true", help="Print the full JSON report to stdout.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Directory to write the JSON report into (default: package output/).",
    )
    args = parser.parse_args(argv)

    domains = _resolve_domains(args)
    report = run(domains)

    args.output.mkdir(parents=True, exist_ok=True)
    out_file = args.output / "4d_dominance_report.json"
    out_file.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        totals = report["totals"]
        print(f"4-D Dominance dry-run — {totals['domains']} domains, {totals['tasks']} tasks")
        for name, block in report["domains"].items():
            print(f"  [{name}] {block['label']}: {len(block['tasks'])} tasks drafted")
        print(
            f"  auto-executed: {totals['auto_executed']} | "
            f"awaiting approval: {totals['awaiting_approval']} | "
            f"model tokens: {totals['model_tokens']}"
        )
        print(f"  report -> {out_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
