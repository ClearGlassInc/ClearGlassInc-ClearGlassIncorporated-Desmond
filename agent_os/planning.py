# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Planning Agent — turn an objective into an executable DAG.

Pure stdlib. Produces parallel execution *waves* (Kahn topological layering) and
detects dependency cycles, which fail closed rather than silently dropping work.
"""
from __future__ import annotations

from dataclasses import dataclass


class CycleError(ValueError):
    """Raised when the task graph contains a dependency cycle."""


@dataclass(frozen=True)
class Task:
    """A unit of work with upstream dependencies and a coarse cost estimate."""

    id: str
    depends_on: tuple[str, ...] = ()
    est_minutes: int = 5


def plan_waves(tasks: list[Task]) -> list[list[str]]:
    """Layer tasks into parallelizable waves via Kahn's algorithm.

    Each returned wave is a list of task ids with no unmet dependencies given the
    prior waves. Raises :class:`CycleError` if the graph cannot be fully ordered,
    or :class:`KeyError` if a task depends on an unknown id (fail closed).
    """
    ids = {t.id for t in tasks}
    for t in tasks:
        for dep in t.depends_on:
            if dep not in ids:
                raise KeyError(f"task '{t.id}' depends on unknown task '{dep}'")

    remaining = {t.id: set(t.depends_on) for t in tasks}
    waves: list[list[str]] = []
    while remaining:
        ready = sorted(tid for tid, deps in remaining.items() if not deps)
        if not ready:
            raise CycleError(f"dependency cycle among: {sorted(remaining)}")
        waves.append(ready)
        for tid in ready:
            del remaining[tid]
        for deps in remaining.values():
            deps.difference_update(ready)
    return waves


def critical_path_minutes(tasks: list[Task]) -> int:
    """Longest-duration dependency chain through the graph, in minutes."""
    by_id = {t.id: t for t in tasks}
    memo: dict[str, int] = {}

    def cost(tid: str, seen: frozenset[str]) -> int:
        if tid in seen:
            raise CycleError(f"dependency cycle at '{tid}'")
        if tid in memo:
            return memo[tid]
        task = by_id[tid]
        upstream = max((cost(d, seen | {tid}) for d in task.depends_on), default=0)
        memo[tid] = upstream + task.est_minutes
        return memo[tid]

    return max((cost(t.id, frozenset()) for t in tasks), default=0)
