# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""D.O.M.I.N.A.T.E. revenue decision engine.

This module is a deterministic operating engine for ranking markets,
opportunities, and capital allocation. It is intentionally not a trading bot and
it does not promise guaranteed profit. Its job is to force disciplined execution:
validate pain, sell before building, score risk-adjusted upside, and protect
survival capital.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


class DominateError(ValueError):
    """Raised when a DOMINATE input violates a safety or quality invariant."""


def _positive(name: str, value: float) -> float:
    if value <= 0:
        raise DominateError(f"{name} must be greater than 0")
    return float(value)


def _bounded(name: str, value: float, minimum: float = 0.0, maximum: float = 10.0) -> float:
    if not minimum <= value <= maximum:
        raise DominateError(f"{name} must be between {minimum} and {maximum}")
    return float(value)


@dataclass(frozen=True)
class Market:
    """A target market scored for pain, urgency, buying power, access, and competition."""

    name: str
    pain: float
    urgency: float
    ability_to_pay: float
    access: float
    competition: float

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DominateError("market name is required")
        _bounded("pain", self.pain)
        _bounded("urgency", self.urgency)
        _bounded("ability_to_pay", self.ability_to_pay)
        _bounded("access", self.access)
        _positive("competition", self.competition)

    @property
    def score(self) -> float:
        """Return normalized market attractiveness on a 0-10 scale."""
        raw = (self.pain * self.urgency * self.ability_to_pay * self.access) / self.competition
        return round(min(10.0, raw / 100.0), 2)

    @property
    def attackable(self) -> bool:
        return self.score >= 7.0


@dataclass(frozen=True)
class Opportunity:
    """A revenue opportunity with expected reward, probability, speed, and risk costs."""

    name: str
    expected_profit: float
    probability_of_success: float
    speed_to_cash: float
    risk: float
    complexity: float
    capital_required: float
    strategic_fit: float = 1.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DominateError("opportunity name is required")
        _positive("expected_profit", self.expected_profit)
        _bounded("probability_of_success", self.probability_of_success, 0.0, 1.0)
        _positive("speed_to_cash", self.speed_to_cash)
        _positive("risk", self.risk)
        _positive("complexity", self.complexity)
        _positive("capital_required", self.capital_required)
        _positive("strategic_fit", self.strategic_fit)

    @property
    def score(self) -> float:
        numerator = self.expected_profit * self.probability_of_success * self.speed_to_cash * self.strategic_fit
        denominator = self.risk * self.complexity * self.capital_required
        return round(numerator / denominator, 4)


@dataclass(frozen=True)
class CapitalStack:
    """Capital allocation that protects reserves and caps speculative exposure."""

    reinvest: float
    cash_reserve: float
    tax_reserve: float
    long_term_assets: float
    high_risk_experiments: float

    @classmethod
    def from_profit(cls, profit: float) -> "CapitalStack":
        _positive("profit", profit)
        return cls(
            reinvest=round(profit * 0.50, 2),
            cash_reserve=round(profit * 0.20, 2),
            tax_reserve=round(profit * 0.15, 2),
            long_term_assets=round(profit * 0.10, 2),
            high_risk_experiments=round(profit * 0.05, 2),
        )

    @property
    def total(self) -> float:
        return round(
            self.reinvest
            + self.cash_reserve
            + self.tax_reserve
            + self.long_term_assets
            + self.high_risk_experiments,
            2,
        )


@dataclass(frozen=True)
class ExecutionCommand:
    """Daily operating command produced by the engine."""

    focus: str
    action: str
    daily_target: str
    kill_switch: str
    capital_stack: CapitalStack | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


def rank_opportunities(opportunities: Iterable[Opportunity]) -> list[Opportunity]:
    ranked = sorted(opportunities, key=lambda item: item.score, reverse=True)
    if not ranked:
        raise DominateError("at least one opportunity is required")
    return ranked


def select_market(markets: Iterable[Market]) -> Market:
    ranked = sorted(markets, key=lambda item: item.score, reverse=True)
    if not ranked:
        raise DominateError("at least one market is required")
    return ranked[0]


def dominate_day(
    markets: Iterable[Market],
    opportunities: Iterable[Opportunity],
    available_profit: float | None = None,
) -> ExecutionCommand:
    """Return the strongest risk-adjusted action for the day.

    Safety doctrine:
    - Sell first, build second.
    - Reject weak markets below 7/10.
    - Do not allocate survival capital.
    - Cap high-risk experiments at 5% of realized profit.
    """

    market = select_market(markets)
    if not market.attackable:
        return ExecutionCommand(
            focus=market.name,
            action="Do not attack yet. Interview buyers, sharpen pain, or choose a stronger market.",
            daily_target="20 discovery contacts, 5 pain interviews, 0 speculative builds",
            kill_switch="No product build until buyer demand is proven.",
            notes=(f"Best market score is {market.score}/10; required threshold is 7/10.",),
        )

    best = rank_opportunities(opportunities)[0]
    capital_stack = CapitalStack.from_profit(available_profit) if available_profit is not None else None
    return ExecutionCommand(
        focus=f"{market.name} → {best.name}",
        action="Sell first, build second. Convert buyer pain into a paid pilot, productized service, or licensing path.",
        daily_target="20 qualified outreaches, 3 direct offers, 1 close attempt, 1 delivery improvement",
        kill_switch="Stop if survival capital is required, risk exceeds reserves, or buyer demand is not validated.",
        capital_stack=capital_stack,
        notes=(
            f"Market score: {market.score}/10.",
            f"Opportunity score: {best.score}.",
            "No guaranteed profit claim is allowed; this is an execution/risk engine.",
        ),
    )


def offer_stage(contacted: int, serious_calls: int, buyers: int) -> str:
    """Return the next sales-stage instruction from live demand signals."""
    if contacted < 0 or serious_calls < 0 or buyers < 0:
        raise DominateError("sales metrics cannot be negative")
    if contacted >= 20 and buyers == 0:
        return "Change offer. Buyers are not voting with money."
    if contacted >= 10 and serious_calls == 0:
        return "Change message. The market is not reacting."
    if buyers >= 3:
        return "Build delivery system. Demand is validated."
    return "Keep selling and collecting evidence."
