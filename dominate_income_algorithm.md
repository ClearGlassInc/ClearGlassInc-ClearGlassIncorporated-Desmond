# D.O.M.I.N.A.T.E. Income Algorithm

D.O.M.I.N.A.T.E. is ClearGlassInc's deterministic revenue decision engine for choosing markets, validating offers, ranking opportunities, and allocating realized profit. It is not a trading bot and it does not promise guaranteed profit.

## Doctrine

**Cash-flow beats prediction. Ownership beats labor. Risk control beats ego.**

The engine converts ambition into operational constraints:

1. Select a painful market with urgent buying power.
2. Sell before building.
3. Rank opportunities by risk-adjusted economics.
4. Block weak markets below the 7/10 attack threshold.
5. Protect survival capital.
6. Allocate realized profit with a fixed capital stack.

## Production module

Source: `bots/dominate_engine.py`

Test coverage: `tests/test_dominate_engine.py`

## Core market formula

```text
Market Score = Pain × Urgency × Ability_to_Pay × Access / Competition
```

The implementation normalizes the result to a 0-10 scale. A market must score at least 7/10 before the engine issues an attack command.

## Opportunity scoring

```text
Opportunity Score =
(Expected Profit × Probability of Success × Speed to Cash × Strategic Fit)
/
(Risk × Complexity × Capital Required)
```

The highest score is not automatically a command to build. The command remains: sell first, prove demand, then systematize delivery.

## Offer validation gates

```text
If 10 prospects contacted and 0 serious calls:
    change message
If 20 prospects contacted and 0 buyers:
    change offer
If 3+ buyers:
    build delivery system
```

These gates prevent fantasy builds, unfunded platform drift, and speculation disguised as strategy.

## Kill-switch doctrine

The operating command must stop when any of the following is true:

- Survival capital is required.
- Risk exceeds reserves.
- Buyer demand is not validated.
- The move depends on guaranteed-profit assumptions.
- The action is boredom-driven rather than evidence-driven.

## Capital stack

For realized profit, the default allocation is:

| Allocation | Percentage |
| --- | ---: |
| Reinvest into proven income engine | 50% |
| Cash reserve | 20% |
| Tax reserve | 15% |
| Long-term assets | 10% |
| High-risk experiments | 5% |

High-risk experiments include speculative crypto research or other asymmetric bets. They are capped at 5% of realized profit by default.

## Example usage

```python
from bots.dominate_engine import Market, Opportunity, dominate_day

markets = [
    Market(
        name="B2B security operations",
        pain=10,
        urgency=9,
        ability_to_pay=9,
        access=8,
        competition=7,
    )
]

opportunities = [
    Opportunity(
        name="paid incident-readiness pilot",
        expected_profit=7500,
        probability_of_success=0.4,
        speed_to_cash=8,
        risk=2,
        complexity=3,
        capital_required=750,
    )
]

command = dominate_day(markets, opportunities, available_profit=10000)
print(command)
```

## Daily execution command

```text
20 qualified outreaches
3 direct offers
1 close attempt
1 delivery improvement
0 speculative builds without buyer evidence
```

## Final standard

D.O.M.I.N.A.T.E. does not chase magic. It removes weakness, blocks reckless capital exposure, and forces repeatable evidence before scale.
