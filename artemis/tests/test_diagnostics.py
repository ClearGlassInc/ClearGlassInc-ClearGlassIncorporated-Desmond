from datetime import datetime, timezone

import pytest

from artemis.intelligence.diagnostics import (
    BoundaryObservation,
    FailureDomain,
    diagnose,
    reconstruct_trace,
)


def observation(sequence: int, component: str, expected: str, actual: str, **kwargs):
    return BoundaryObservation(
        sequence=sequence,
        component=component,
        expected=expected,
        actual=actual,
        trace_id="trace-123",
        timestamp=datetime(2026, 8, 3, 12, 0, sequence, tzinfo=timezone.utc),
        **kwargs,
    )


def test_diagnosis_uses_earliest_boundary_divergence():
    diagnosis = diagnose(
        [
            observation(2, "postgres-query", "one row", "zero rows"),
            observation(0, "api-gateway", "validated request", "validated request"),
            observation(1, "opa-policy", "allow", "deny"),
        ]
    )

    assert diagnosis.first_divergence is not None
    assert diagnosis.first_divergence.component == "opa-policy"
    assert diagnosis.failure_domain is FailureDomain.AUTHORIZATION
    assert diagnosis.hypotheses[0].priority >= diagnosis.hypotheses[1].priority


def test_high_latency_is_classified_as_performance():
    diagnosis = diagnose([observation(0, "api-service", "200", "504", latency_ms=2_500)])

    assert diagnosis.failure_domain is FailureDomain.PERFORMANCE


def test_no_divergence_does_not_fabricate_root_cause():
    diagnosis = diagnose([observation(0, "api-service", "200", "200")])

    assert diagnosis.first_divergence is None
    assert diagnosis.hypotheses == ()
    assert diagnosis.failure_domain is FailureDomain.UNKNOWN


def test_trace_reconstruction_rejects_cross_trace_correlation():
    other_trace = BoundaryObservation(
        sequence=1,
        component="worker",
        expected="accepted",
        actual="accepted",
        trace_id="trace-other",
        timestamp=datetime(2026, 8, 3, 12, 0, 1, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="different traces"):
        reconstruct_trace([observation(0, "api", "accepted", "accepted"), other_trace])


def test_observation_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        BoundaryObservation(
            sequence=0,
            component="api",
            expected="accepted",
            actual="accepted",
            trace_id="trace-123",
            timestamp=datetime(2026, 8, 3),
        )
