# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Learning Agent — capture outcomes, compute metrics, extract lessons.

After each workflow the OS records what happened, rolls up deterministic metrics
(success rate, mean duration), and turns failures into forward-looking lessons
and optimization opportunities. Stdlib-only; feeds the Memory Agent.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Outcome:
    """The result of one completed workflow branch."""

    workflow: str
    success: bool
    duration_minutes: float
    note: str = ""


@dataclass
class LearningLog:
    """Accumulates outcomes and summarises them deterministically."""

    outcomes: list[Outcome] = field(default_factory=list)

    def record(self, workflow: str, success: bool, duration_minutes: float,
               note: str = "") -> Outcome:
        if duration_minutes < 0:
            raise ValueError("duration_minutes must be >= 0")
        outcome = Outcome(workflow, success, float(duration_minutes), note)
        self.outcomes.append(outcome)
        return outcome

    def metrics(self) -> dict[str, float]:
        n = len(self.outcomes)
        if n == 0:
            return {"count": 0.0, "success_rate": 0.0, "mean_duration_minutes": 0.0}
        successes = sum(1 for o in self.outcomes if o.success)
        total = sum(o.duration_minutes for o in self.outcomes)
        return {
            "count": float(n),
            "success_rate": round(successes / n, 4),
            "mean_duration_minutes": round(total / n, 4),
        }

    def lessons(self) -> list[str]:
        """Forward-looking lessons derived only from recorded failures."""
        out: list[str] = []
        for o in self.outcomes:
            if not o.success:
                detail = f": {o.note}" if o.note else ""
                out.append(f"Harden '{o.workflow}' — it failed{detail}")
        return out

    def optimization_opportunities(self, *, slow_threshold_minutes: float = 10.0) -> list[str]:
        """Flag slow successful workflows as candidates for automation/speedup."""
        return [
            f"Optimize '{o.workflow}' — {o.duration_minutes:.0f}m exceeds "
            f"{slow_threshold_minutes:.0f}m target"
            for o in self.outcomes
            if o.success and o.duration_minutes > slow_threshold_minutes
        ]
