# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Self-Evolving Engine — the bot that improves the bot fleet.

This is the "automate itself" layer. Each generation it:

1. Reads the fleet's run history (``operations/output/bot_run_log.json``).
2. Loads its own persisted *genome* (weights, quarantine list, lineage) from
   ``operations/output/self_evolving/genome.json`` — the memory that lets it
   evolve across runs instead of starting cold every time.
3. Scores each bot's fitness from reliability, recency, and alignment to the
   wealth-ladder priority order (Revenue first).
4. Mutates:
   - **Low-risk, auto-applied:** nudges routing weights toward what works.
   - **Higher-risk, approval-gated:** quarantining a chronically failing bot.
5. Increments the generation counter, appends a lineage record, and persists
   the evolved genome so the next run inherits it.

Design guardrails (mirrors the existing self-improvement pattern):
- Pure/deterministic given its inputs; no network calls live here.
- Structural changes (quarantine, disable) NEVER auto-apply — they are emitted
  as a proposal with ``requires_human_approval = True``.
- Weight changes are bounded to ``[WEIGHT_FLOOR, WEIGHT_CAP]`` so the fleet
  cannot runaway-evolve in a single generation.

Usage:
    python -m bots.self_evolving_engine            # evolve one generation
    python -m bots.self_evolving_engine --print    # dry run, no genome write
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUN_LOG = ROOT / "operations" / "output" / "bot_run_log.json"
OUTPUT_DIR = ROOT / "operations" / "output" / "self_evolving"
GENOME_PATH = OUTPUT_DIR / "genome.json"

# Evolution bounds.
WEIGHT_FLOOR = 0.10
WEIGHT_CAP = 3.00
WEIGHT_STEP = 0.10
RECENT_WINDOW = 20            # most recent runs per bot considered
QUARANTINE_THRESHOLD = 0.50   # success rate below this → propose quarantine
PROMOTE_THRESHOLD = 0.95      # success rate at/above this → reward weight

# Bots whose output feeds the priority order get an alignment bias. Revenue and
# the wealth ladder sit at the top of the standing strategy, so they evolve to
# the front of the queue.
PRIORITY_BIAS: dict[str, float] = {
    "wealth_ladder": 0.40,
    "cashpulse": 0.30,
    "operations": 0.20,
    "sales": 0.20,
    "growth": 0.15,
    "daily_priority": 0.10,
}


@dataclass
class Genome:
    generation: int = 0
    weights: dict[str, float] = field(default_factory=dict)
    quarantine: list[str] = field(default_factory=list)
    lineage: list[dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> "Genome":
        return Genome(
            generation=int(raw.get("generation", 0)),
            weights={k: float(v) for k, v in raw.get("weights", {}).items()},
            quarantine=list(raw.get("quarantine", [])),
            lineage=list(raw.get("lineage", [])),
        )


@dataclass(frozen=True)
class Fitness:
    bot_id: str
    runs: int
    success_rate: float
    avg_duration_s: float
    alignment: float
    fitness: float


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def load_genome(path: Path | None = None) -> Genome:
    path = path if path is not None else GENOME_PATH
    if path and path.exists():
        try:
            return Genome.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001 — a corrupt genome must not halt evolution
            return Genome()
    return Genome()


def load_run_log(path: Path | None = None) -> list[dict[str, Any]]:
    path = path if path is not None else RUN_LOG
    if path and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:  # noqa: BLE001
            return []
    return []


def _alignment(bot_id: str) -> float:
    return PRIORITY_BIAS.get(bot_id, 0.0)


def score_fleet(run_log: list[dict[str, Any]]) -> list[Fitness]:
    """Compute fitness per bot from the most recent runs."""
    by_bot: dict[str, list[dict[str, Any]]] = {}
    for entry in run_log:
        bot_id = entry.get("bot")
        if bot_id:
            by_bot.setdefault(bot_id, []).append(entry)

    scores: list[Fitness] = []
    for bot_id, entries in by_bot.items():
        recent = entries[-RECENT_WINDOW:]
        runs = len(recent)
        oks = sum(1 for e in recent if e.get("status") == "ok")
        success_rate = (oks / runs) if runs else 0.0
        durations = [float(e.get("duration_s", 0.0)) for e in recent]
        avg_duration = round(sum(durations) / runs, 3) if runs else 0.0
        alignment = _alignment(bot_id)
        # Fitness rewards reliability and priority alignment; very slow bots
        # bleed a little fitness so the fleet trends toward fast, reliable work.
        speed_penalty = min(0.15, avg_duration / 600.0)  # 10 min run ≈ full penalty
        fitness = round(success_rate + alignment - speed_penalty, 4)
        scores.append(Fitness(
            bot_id=bot_id,
            runs=runs,
            success_rate=round(success_rate, 4),
            avg_duration_s=avg_duration,
            alignment=alignment,
            fitness=fitness,
        ))
    scores.sort(key=lambda f: f.fitness, reverse=True)
    return scores


def evolve(genome: Genome, scores: list[Fitness]) -> dict[str, Any]:
    """Advance one generation. Returns the proposal; mutates ``genome`` in place
    for the auto-applied (low-risk) weight changes only."""
    auto_changes: list[str] = []
    proposed_changes: list[str] = []

    for f in scores:
        current = genome.weights.get(f.bot_id, 1.0)

        if f.success_rate >= PROMOTE_THRESHOLD and f.runs >= 3:
            new = _clamp(current + WEIGHT_STEP + f.alignment * 0.1, WEIGHT_FLOOR, WEIGHT_CAP)
            if new != current:
                genome.weights[f.bot_id] = round(new, 4)
                auto_changes.append(
                    f"promote {f.bot_id}: weight {current:.2f} → {new:.2f} "
                    f"(success {f.success_rate:.0%})"
                )
        elif f.success_rate < QUARANTINE_THRESHOLD and f.runs >= 3:
            new = _clamp(current - WEIGHT_STEP, WEIGHT_FLOOR, WEIGHT_CAP)
            if new != current:
                genome.weights[f.bot_id] = round(new, 4)
                auto_changes.append(
                    f"demote {f.bot_id}: weight {current:.2f} → {new:.2f} "
                    f"(success {f.success_rate:.0%})"
                )
            # Structural change is approval-gated, not auto-applied.
            if f.bot_id not in genome.quarantine:
                proposed_changes.append(
                    f"QUARANTINE {f.bot_id}: success {f.success_rate:.0%} over "
                    f"{f.runs} runs is below {QUARANTINE_THRESHOLD:.0%} threshold."
                )
        else:
            # Stable bot — ensure it has an explicit weight so lineage is complete.
            genome.weights.setdefault(f.bot_id, round(_clamp(current, WEIGHT_FLOOR, WEIGHT_CAP), 4))

    genome.generation += 1
    avg_fitness = round(sum(f.fitness for f in scores) / len(scores), 4) if scores else 0.0

    proposal = {
        "proposal_id": sha256(
            f"{datetime.now(timezone.utc).isoformat()}:{genome.generation}".encode()
        ).hexdigest()[:12],
        "generation": genome.generation,
        "evaluated_bots": len(scores),
        "avg_fitness": avg_fitness,
        "top_bot": scores[0].bot_id if scores else None,
        "auto_applied": auto_changes,
        "proposed_change_set": proposed_changes,
        "requires_human_approval": bool(proposed_changes),
    }

    genome.lineage.append({
        "generation": genome.generation,
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "avg_fitness": avg_fitness,
        "auto_applied_count": len(auto_changes),
        "proposed_count": len(proposed_changes),
    })
    # Keep lineage bounded.
    genome.lineage = genome.lineage[-200:]

    return proposal


def write_outputs(genome: Genome, proposal: dict[str, Any], scores: list[Fitness]) -> dict[str, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "genome": GENOME_PATH,
        "proposal": OUTPUT_DIR / "latest_proposal.json",
        "fitness": OUTPUT_DIR / "latest_fitness.json",
    }
    paths["genome"].write_text(json.dumps(asdict(genome), indent=2) + "\n", encoding="utf-8")
    paths["proposal"].write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    paths["fitness"].write_text(
        json.dumps([asdict(f) for f in scores], indent=2) + "\n", encoding="utf-8"
    )
    return paths


def render_terminal(proposal: dict[str, Any], scores: list[Fitness]) -> str:
    bar = "=" * 64
    out = [
        bar,
        f"  SELF-EVOLVING ENGINE — generation {proposal['generation']}",
        bar,
        f"  Evaluated {proposal['evaluated_bots']} bots | "
        f"avg fitness {proposal['avg_fitness']} | top: {proposal['top_bot']}",
        "",
        "  Fitness (sorted):",
    ]
    for f in scores:
        out.append(
            f"    {f.bot_id:<22} fit={f.fitness:<7} "
            f"success={f.success_rate:.0%} align={f.alignment:+.2f} runs={f.runs}"
        )
    out += ["", "  Auto-applied (low-risk):"]
    out += [f"    + {c}" for c in proposal["auto_applied"]] or ["    (none)"]
    out += ["", "  Proposed (needs approval):"]
    out += [f"    ! {c}" for c in proposal["proposed_change_set"]] or ["    (none)"]
    out += ["", bar]
    return "\n".join(out)


def run_once(*, dry_run: bool = False) -> dict[str, Any]:
    genome = load_genome()
    run_log = load_run_log()
    scores = score_fleet(run_log)
    proposal = evolve(genome, scores)
    print(render_terminal(proposal, scores))
    if not dry_run:
        paths = write_outputs(genome, proposal, scores)
        print(f"\nGenome persisted: {paths['genome']}")
        print(f"Proposal written: {paths['proposal']}")
    return proposal


def should_run() -> bool:
    return os.getenv("SELF_EVOLVING_ENABLED", "true").strip().lower() == "true"


def run() -> None:
    """Entry point for the universal bot runner (no CLI args)."""
    if not should_run():
        print("Self-evolving engine disabled via SELF_EVOLVING_ENABLED=false")
        return
    run_once(dry_run=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one generation of the self-evolving engine.")
    parser.add_argument("--print", action="store_true", help="Dry run; do not persist the genome.")
    args = parser.parse_args(argv)

    if not should_run():
        print("Self-evolving engine disabled via SELF_EVOLVING_ENABLED=false")
        return 0

    run_once(dry_run=args.print)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
