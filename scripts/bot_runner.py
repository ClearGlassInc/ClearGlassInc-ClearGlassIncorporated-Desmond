#!/usr/bin/env python3
# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Universal bot runner — single entry-point for all ClearGlass bots.

Usage:
    python scripts/bot_runner.py <bot_id>           # run one bot
    python scripts/bot_runner.py --all              # run all scheduled bots
    python scripts/bot_runner.py --all --schedule daily
    python scripts/bot_runner.py --list             # list registered bots
    python scripts/bot_runner.py --list-json        # GH Actions matrix JSON
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / "operations" / "output"
LOG_FILE = LOG_DIR / "bot_run_log.json"
LOG_MAX_ENTRIES = 500

# Registry: bot_id → {module, group, schedule}
BOT_REGISTRY: dict[str, dict[str, str]] = {
    "marketing": {
        "module": "bots.marketing_bot",
        "group": "content",
        "schedule": "daily",
    },
    "growth": {
        "module": "bots.artemis_growth_bot",
        "group": "analytics",
        "schedule": "daily",
    },
    "daily_priority": {
        "module": "bots.artemis_daily_priority_bot",
        "group": "ops",
        "schedule": "daily",
    },
    "sales": {
        "module": "bots.guardian_artemis_sales_bot",
        "group": "content",
        "schedule": "daily",
    },
    "cpa_partner": {
        "module": "bots.cpa_partner_outreach_bot",
        "group": "content",
        "schedule": "weekly",
    },
    "operations": {
        "module": "bots.operations_finance_bot",
        "group": "ops",
        "schedule": "daily",
    },
    "campaign_reporter": {
        "module": "bots.campaign_reporter",
        "group": "analytics",
        "schedule": "daily",
    },
    "site_health": {
        "module": "bots.site_health_bot",
        "group": "monitoring",
        "schedule": "daily",
    },
    "content_collector": {
        "module": "bots.content_collector_bot",
        "group": "content",
        "schedule": "daily",
    },
    "lead_draft": {
        "module": "bots.lead_draft_bot",
        "group": "sales",
        "schedule": "daily",
    },
    "seo_optimizer": {
        "module": "bots.seo_optimizer_bot",
        "group": "seo",
        "schedule": "weekly",
    },
    "release_notes": {
        "module": "bots.release_notes_bot",
        "group": "ops",
        "schedule": "weekly",
    },
    "alert_dispatcher": {
        "module": "bots.alert_dispatcher_bot",
        "group": "monitoring",
        "schedule": "daily",
    },
    "defender": {
        "module": "bots.defender",
        "group": "monitoring",
        "schedule": "daily",
    },
    "wealth_ladder": {
        "module": "bots.wealth_ladder_bot",
        "group": "strategy",
        "schedule": "daily",
    },
    "smb_cyber_trust_kit": {
        "module": "bots.smb_cyber_trust_kit_bot",
        "group": "content",
        "schedule": "weekly",
    },
    "self_evolving": {
        "module": "bots.self_evolving_engine",
        "group": "orchestration",
        "schedule": "daily",
    },
    "master_orchestrator": {
        "module": "bots.master_orchestrator",
        "group": "orchestration",
        "schedule": "daily",
    },
}


def _find_entry(module: Any) -> Any:
    for name in ("run", "main"):
        fn = getattr(module, name, None)
        if callable(fn):
            return fn
    return None


def run_bot(bot_id: str) -> dict[str, Any]:
    if bot_id not in BOT_REGISTRY:
        return {
            "bot": bot_id,
            "module": None,
            "group": None,
            "status": "error",
            "error": f"Unknown bot: {bot_id}",
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "duration_s": 0.0,
        }

    meta = BOT_REGISTRY[bot_id]
    start = time.monotonic()
    ts = datetime.now(timezone.utc).isoformat()
    error = None

    try:
        mod = importlib.import_module(meta["module"])
        entry = _find_entry(mod)
        if entry:
            entry()
        status = "ok"
    except SystemExit as exc:
        status = "ok" if exc.code in (0, None) else "error"
        if exc.code not in (0, None):
            error = f"SystemExit({exc.code})"
    except Exception as exc:  # noqa: BLE001
        status = "error"
        error = f"{type(exc).__name__}: {exc}"

    duration = round(time.monotonic() - start, 2)
    return {
        "bot": bot_id,
        "module": meta["module"],
        "group": meta["group"],
        "status": status,
        "error": error,
        "started_utc": ts,
        "duration_s": duration,
    }


def append_log(result: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    history: list[dict[str, Any]] = []
    if LOG_FILE.exists():
        try:
            history = json.loads(LOG_FILE.read_text())
        except Exception:  # noqa: BLE001
            history = []
    history.append(result)
    LOG_FILE.write_text(json.dumps(history[-LOG_MAX_ENTRIES:], indent=2))


def build_matrix(schedule: str | None = None) -> dict[str, list[dict[str, str]]]:
    bots = [
        {"bot": bid}
        for bid, meta in BOT_REGISTRY.items()
        if bid != "master_orchestrator"
        if schedule is None or meta.get("schedule") == schedule
    ]
    return {"include": bots}


def main() -> None:
    parser = argparse.ArgumentParser(description="ClearGlass bot runner")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("bot_id", nargs="?", help="Bot ID to run")
    group.add_argument("--all", action="store_true", help="Run all bots matching --schedule")
    group.add_argument("--list", action="store_true", help="List registered bots")
    group.add_argument("--list-json", action="store_true", help="Output GH Actions matrix JSON")
    parser.add_argument("--schedule", choices=["daily", "weekly"], help="Filter by schedule")
    args = parser.parse_args()

    if args.list:
        for bid, meta in BOT_REGISTRY.items():
            print(f"  {bid:25s}  [{meta['group']:15s}]  {meta['schedule']}")
        return

    if args.list_json:
        matrix = build_matrix(args.schedule)
        print(f"matrix={json.dumps(matrix)}")
        return

    if args.all:
        bots = [bid for bid in BOT_REGISTRY if bid != "master_orchestrator"]
        if args.schedule:
            bots = [b for b in bots if BOT_REGISTRY[b].get("schedule") == args.schedule]
        failed: list[str] = []
        for bot_id in bots:
            result = run_bot(bot_id)
            append_log(result)
            icon = "✓" if result["status"] == "ok" else "✗"
            print(f"{icon} {bot_id} ({result['duration_s']}s)")
            if result["status"] != "ok":
                failed.append(bot_id)
        if failed:
            print(f"\nFailed bots: {', '.join(failed)}", file=sys.stderr)
            sys.exit(1)
        return

    if not args.bot_id:
        parser.print_help()
        sys.exit(1)

    result = run_bot(args.bot_id)
    append_log(result)
    if result["status"] != "ok":
        print(f"ERROR [{args.bot_id}]: {result['error']}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: {args.bot_id} completed in {result['duration_s']}s")


if __name__ == "__main__":
    main()
