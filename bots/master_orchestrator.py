# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Master bot orchestrator.

Coordinates all bots using a dependency graph to determine execution order.
Independent bots run in parallel; dependent bots wait for their prerequisites.
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUTPUT_DIR = ROOT / "operations" / "output"

# Dependency graph: bot_id → list of bot_ids that must complete first
DEPENDENCY_GRAPH: dict[str, list[str]] = {
    "marketing": [],
    "growth": [],
    "daily_priority": [],
    "lead_draft": [],
    "campaign_reporter": ["marketing"],
    "sales": ["growth"],
    "operations": ["daily_priority"],
    "site_health": [],
    "seo_optimizer": [],
    "release_notes": [],
    "alert_dispatcher": ["site_health", "growth", "operations"],
    "wealth_ladder": [],
    # The self-evolving engine reads the fleet's run history, so it runs last —
    # after the bots whose outcomes it scores.
    "self_evolving": ["wealth_ladder", "operations", "site_health"],
}

MAX_PARALLEL_WORKERS = 4


@dataclass
class BotResult:
    bot_id: str
    status: str  # "ok" | "error" | "skipped" | "dry-run"
    duration_s: float
    error: str | None = None


def _topo_sort(graph: dict[str, list[str]]) -> list[list[str]]:
    """Group bots into parallel execution waves via Kahn's algorithm."""
    in_degree = {node: 0 for node in graph}
    for deps in graph.values():
        for dep in deps:
            if dep in in_degree:
                in_degree[dep] = in_degree.get(dep, 0)

    # Build forward adjacency
    dependents: dict[str, list[str]] = {node: [] for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            if dep in dependents:
                dependents[dep].append(node)

    # Recompute in-degrees correctly
    in_deg: dict[str, int] = {node: 0 for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            if dep in graph:
                in_deg[node] += 1

    waves: list[list[str]] = []
    remaining = set(graph)

    while remaining:
        wave = sorted(node for node in remaining if in_deg[node] == 0)
        if not wave:
            # Circular dependency — add all remaining to break the cycle
            wave = sorted(remaining)
        waves.append(wave)
        for node in wave:
            remaining.discard(node)
            for dep in dependents.get(node, []):
                if dep in remaining:
                    in_deg[dep] = max(0, in_deg[dep] - 1)

    return waves


def _run_single(bot_id: str) -> BotResult:
    from scripts.bot_runner import run_bot
    raw = run_bot(bot_id)
    return BotResult(
        bot_id=bot_id,
        status=raw["status"],
        duration_s=raw["duration_s"],
        error=raw.get("error"),
    )


def run(target_bots: list[str] | None = None) -> dict[str, Any]:
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    target_set: set[str] = set(target_bots) if target_bots else set(DEPENDENCY_GRAPH)

    # Build subgraph for requested bots
    graph = {
        k: [d for d in v if d in target_set]
        for k, v in DEPENDENCY_GRAPH.items()
        if k in target_set
    }
    waves = _topo_sort(graph)

    results: list[BotResult] = []
    failed: set[str] = set()

    for wave in waves:
        # Bots whose dependencies all succeeded
        runnable = [b for b in wave if not (set(graph.get(b, [])) & failed)]
        skipped = [b for b in wave if b not in runnable]

        for bot_id in skipped:
            results.append(BotResult(
                bot_id=bot_id, status="skipped", duration_s=0.0,
                error="dependency failed",
            ))
            print(f"⊘ {bot_id} (skipped — dependency failed)")

        if dry_run:
            for bot_id in runnable:
                print(f"[DRY-RUN] {bot_id}")
                results.append(BotResult(bot_id=bot_id, status="dry-run", duration_s=0.0))
            continue

        with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_WORKERS, len(runnable) or 1)) as pool:
            futures = {pool.submit(_run_single, bid): bid for bid in runnable}
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                if result.status == "error":
                    failed.add(result.bot_id)
                icon = "✓" if result.status == "ok" else "✗"
                print(f"{icon} {result.bot_id} ({result.duration_s}s)")

    summary: dict[str, Any] = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "total": len(results),
        "ok": sum(1 for r in results if r.status == "ok"),
        "failed": sum(1 for r in results if r.status == "error"),
        "skipped": sum(1 for r in results if r.status in ("skipped", "dry-run")),
        "bots": [asdict(r) for r in results],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "orchestrator_summary.json").write_text(json.dumps(summary, indent=2))

    return summary


def main() -> None:
    target_env = os.getenv("TARGET_BOTS", "").strip()
    target_bots: list[str] | None = None
    if target_env:
        target_bots = [b.strip() for b in target_env.split(",") if b.strip()]

    summary = run(target_bots)

    ok = summary["ok"]
    total = summary["total"]
    failed = summary["failed"]
    print(f"\nOrchestration complete: {ok}/{total} succeeded, {failed} failed")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
