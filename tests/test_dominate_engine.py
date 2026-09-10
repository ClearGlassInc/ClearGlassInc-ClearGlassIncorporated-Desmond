# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for the D.O.M.I.N.A.T.E. revenue decision engine."""

from __future__ import annotations

import pytest

from bots.dominate_engine import (
    CapitalStack,
    DominateError,
    Market,
    Opportunity,
    dominate_day,
    offer_stage,
    rank_opportunities,
    select_market,
)


def test_market_score_is_normalized_and_attackable() -> None:
    market = Market(
        name="cybersecurity compliance automation",
        pain=10,
        urgency=10,
        ability_to_pay=9,
        access=8,
        competition=8,
    )
    assert market.score == 9.0
    assert market.attackable is True


def test_market_rejects_zero_competition_to_avoid_fake_math() -> None:
    with pytest.raises(DominateError, match="competition"):
        Market(name="bad market", pain=8, urgency=8, ability_to_pay=8, access=8, competition=0)


def test_select_market_returns_highest_score() -> None:
    weak = Market(name="weak", pain=4, urgency=4, ability_to_pay=4, access=4, competition=8)
    strong = Market(name="strong", pain=10, urgency=9, ability_to_pay=9, access=8, competition=7)
    assert select_market([weak, strong]).name == "strong"


def test_opportunity_ranking_prefers_risk_adjusted_profit() -> None:
    service = Opportunity(
        name="productized security audit",
        expected_profit=5000,
        probability_of_success=0.45,
        speed_to_cash=8,
        risk=2,
        complexity=3,
        capital_required=500,
    )
    moonshot = Opportunity(
        name="unfunded platform build",
        expected_profit=50000,
        probability_of_success=0.05,
        speed_to_cash=1,
        risk=9,
        complexity=10,
        capital_required=10000,
    )
    assert rank_opportunities([moonshot, service])[0] == service


def test_dominate_day_blocks_weak_market() -> None:
    market = Market(name="weak market", pain=3, urgency=3, ability_to_pay=3, access=3, competition=9)
    opp = Opportunity(
        name="pilot",
        expected_profit=1000,
        probability_of_success=0.5,
        speed_to_cash=5,
        risk=2,
        complexity=2,
        capital_required=100,
    )
    command = dominate_day([market], [opp])
    assert command.action.startswith("Do not attack")
    assert "required threshold" in command.notes[0]


def test_dominate_day_returns_daily_command_and_capital_stack() -> None:
    market = Market(
        name="B2B security operations",
        pain=10,
        urgency=9,
        ability_to_pay=9,
        access=8,
        competition=7,
    )
    opp = Opportunity(
        name="paid incident-readiness pilot",
        expected_profit=7500,
        probability_of_success=0.4,
        speed_to_cash=8,
        risk=2,
        complexity=3,
        capital_required=750,
    )
    command = dominate_day([market], [opp], available_profit=10000)
    assert "B2B security operations" in command.focus
    assert command.capital_stack == CapitalStack(
        reinvest=5000,
        cash_reserve=2000,
        tax_reserve=1500,
        long_term_assets=1000,
        high_risk_experiments=500,
    )
    assert command.capital_stack.total == 10000


def test_capital_stack_rejects_non_positive_profit() -> None:
    with pytest.raises(DominateError, match="profit"):
        CapitalStack.from_profit(0)


@pytest.mark.parametrize(
    "contacted, serious_calls, buyers, expected",
    [
        (10, 0, 0, "Change message. The market is not reacting."),
        (20, 2, 0, "Change offer. Buyers are not voting with money."),
        (25, 5, 3, "Build delivery system. Demand is validated."),
        (3, 1, 0, "Keep selling and collecting evidence."),
    ],
)
def test_offer_stage(contacted: int, serious_calls: int, buyers: int, expected: str) -> None:
    assert offer_stage(contacted, serious_calls, buyers) == expected


def test_offer_stage_rejects_negative_metrics() -> None:
    with pytest.raises(DominateError, match="cannot be negative"):
        offer_stage(-1, 0, 0)
