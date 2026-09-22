"""Focused offline tests for the ClearGlass Revenue Command System."""
from __future__ import annotations

from app.revenue_service import STAGES, score_qualification


def test_score_is_explainable_and_bounded() -> None:
    score, explanation = score_qualification({
        "website": "https://example.com",
        "desired_timeline": "0-7 days",
        "investment_range": "CAD $125-$500",
        "primary_goal": "Fix the conversion path",
        "current_challenge": "GitHub deployment breaks after release",
        "service_interest": "Rapid Diagnostic",
    })
    assert 0 <= score <= 100
    assert score >= 60
    assert "near-term timeline" in explanation
    assert "digital property supplied" in explanation


def test_score_never_uses_unrelated_identity_fields() -> None:
    base = {
        "website": "https://example.com",
        "desired_timeline": "8-30 days",
        "investment_range": "CAD $500-$2,500",
        "primary_goal": "Improve site",
        "current_challenge": "Broken release",
        "service_interest": "Rapid Diagnostic",
    }
    score_a, _ = score_qualification({**base, "full_name": "A"})
    score_b, _ = score_qualification({**base, "full_name": "B"})
    assert score_a == score_b


def test_stage_catalog_contains_required_revenue_lifecycle_states() -> None:
    required = {
        "NEW", "REVIEW_REQUIRED", "QUALIFIED", "NURTURE", "BOOKED",
        "DISCOVERY_COMPLETE", "PROPOSAL_PENDING", "PROPOSAL_SENT", "NEGOTIATION",
        "WON", "LOST", "CUSTOMER_ACTIVE", "RETENTION_RISK", "EXPANSION_OPPORTUNITY", "CLOSED",
    }
    assert required <= STAGES
