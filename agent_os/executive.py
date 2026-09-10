# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Executive Agent — expected-value strategy ranking + priority queue.

Implements decision-framework steps 4-8: generate strategies, estimate
probability / cost / risk, and choose the highest expected value. Deterministic
and stdlib-only.

    expected_value = probability * value - cost - risk_penalty

where ``risk_penalty = risk * value`` so a risky high-upside play is discounted
proportionally to what is at stake.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Strategy:
    """A candidate course of action with its estimates (all 0..1 except value)."""

    name: str
    value: float          # upside if it fully succeeds (arbitrary positive units)
    probability: float    # 0..1 chance of success
    cost: float           # same units as value
    risk: float = 0.0     # 0..1 chance-weighted downside multiplier

    def expected_value(self) -> float:
        p = max(0.0, min(1.0, self.probability))
        r = max(0.0, min(1.0, self.risk))
        return round(p * self.value - self.cost - r * self.value, 6)


@dataclass(frozen=True)
class RankedStrategy:
    name: str
    expected_value: float
    rank: int

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "expected_value": self.expected_value, "rank": self.rank}


def rank_strategies(strategies: list[Strategy]) -> list[RankedStrategy]:
    """Rank strategies by expected value, highest first (ties broken by name)."""
    if not strategies:
        return []
    ordered = sorted(strategies, key=lambda s: (-s.expected_value(), s.name))
    return [
        RankedStrategy(s.name, s.expected_value(), i + 1)
        for i, s in enumerate(ordered)
    ]


def choose(strategies: list[Strategy]) -> RankedStrategy | None:
    """Return the highest-expected-value strategy, or None if none supplied."""
    ranked = rank_strategies(strategies)
    return ranked[0] if ranked else None


def priority_queue(items: list[tuple[str, float]]) -> list[str]:
    """Order (label, weight) items by descending weight (ties broken by label)."""
    return [label for label, _ in sorted(items, key=lambda x: (-x[1], x[0]))]
