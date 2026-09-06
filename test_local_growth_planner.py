from decimal import Decimal

import pytest

from marketing.local_growth_planner import (
    Intent,
    KeywordSignal,
    LocalGrowthPlanner,
    ReviewState,
    WeeklyMetrics,
)


def signal(**overrides):
    values = {
        "phrase": "commercial glass repair burlington",
        "intent": Intent.MONEY,
        "service": "Commercial Glass Repair",
        "location": "Burlington",
        "impressions": 120,
        "clicks": 20,
        "qualified_leads": 4,
        "evidence_ref": "search-console:query:2026-w30",
    }
    values.update(overrides)
    return KeywordSignal(**values)


def test_planner_builds_unique_evidence_linked_money_pages():
    planner = LocalGrowthPlanner()
    drafts = planner.build_page_drafts(
        [
            signal(),
            signal(phrase="storefront repair near me", qualified_leads=2),
            signal(
                phrase="what happens after glass breaks",
                intent=Intent.SUPPORT,
                qualified_leads=0,
            ),
        ]
    )

    assert len(drafts) == 1
    assert drafts[0].path == "/services/commercial-glass-repair/burlington/"
    assert drafts[0].state is ReviewState.DRAFT
    assert drafts[0].evidence_refs == ("search-console:query:2026-w30",)
    assert len(drafts[0].title) <= 60
    assert len(drafts[0].meta_description) <= 155


def test_review_is_explicit_and_hash_chained():
    planner = LocalGrowthPlanner()
    draft = planner.build_page_drafts([signal()])[0]
    approved = planner.decide_draft(
        draft, reviewer="local-marketing-owner", approve=True, rationale="Proof verified"
    )

    assert approved.state is ReviewState.APPROVED
    assert planner.audit_records[1]["previous_hash"] == planner.audit_records[0]["record_hash"]


def test_review_requires_identity_and_rationale():
    planner = LocalGrowthPlanner()
    draft = planner.build_page_drafts([signal()])[0]

    with pytest.raises(ValueError, match="reviewer and rationale"):
        planner.decide_draft(draft, reviewer="", approve=True, rationale="")


@pytest.mark.parametrize(
    "overrides",
    [
        {"impressions": -1},
        {"impressions": 5, "clicks": 6},
        {"clicks": 2, "qualified_leads": 3},
        {"evidence_ref": ""},
    ],
)
def test_invalid_or_unproven_signals_fail_closed(overrides):
    with pytest.raises(ValueError):
        signal(**overrides)


def test_weekly_conversion_rate_is_precise_and_zero_safe():
    metrics = WeeklyMetrics(1000, 30, 4, 3, 2, 5, 200)
    assert metrics.conversion_rate == Decimal("0.045")
    assert WeeklyMetrics(0, 0, 0, 0, 0, 0, 0).conversion_rate == Decimal("0")
