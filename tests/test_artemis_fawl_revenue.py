from decimal import Decimal

import pytest

from agents.artemis_fawl_revenue import Gate, Opportunity, rank


def sample(**changes):
    values = dict(
        opportunity_id="o-1",
        title="Evidence review",
        source_ids=("s-1",),
        evidence_quality=90,
        expected_value_cad=Decimal("5000"),
        strategic_fit=90,
        effort=20,
        risk=10,
        source_authorized=True,
        human_gate=Gate.REVIEW,
    )
    values.update(changes)
    return Opportunity(**values)


def test_is_deterministic_and_review_gated():
    first = rank(sample())
    second = rank(sample())
    assert first.score == 79
    assert first.audit_hash == second.audit_hash
    assert first.status is Gate.REVIEW


def test_unauthorized_source_fails_closed():
    result = rank(sample(source_authorized=False, human_gate=Gate.APPROVED))
    assert result.status is Gate.BLOCKED


def test_low_quality_evidence_is_blocked():
    assert rank(sample(evidence_quality=59)).status is Gate.BLOCKED


def test_validation_rejects_invalid_range():
    with pytest.raises(ValueError):
        rank(sample(risk=101))
