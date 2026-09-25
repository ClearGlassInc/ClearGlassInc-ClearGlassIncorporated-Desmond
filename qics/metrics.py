"""Process-local counters. No tenant payloads."""

from __future__ import annotations

from collections import Counter

_COUNTS: Counter[str] = Counter()


def inc(name: str, n: int = 1) -> None:
    _COUNTS[name] += n


def snapshot() -> dict[str, int]:
    keys = (
        "qics_ingestion_success_total",
        "qics_ingestion_failure_total",
        "qics_evidence_items_total",
        "qics_unverified_claims_total",
        "qics_conflicting_claims_total",
        "qics_scanner_runs_total",
        "qics_recommendations_total",
        "qics_approval_requests_total",
        "qics_agent_errors_total",
    )
    return {k: int(_COUNTS.get(k, 0)) for k in keys}


def reset() -> None:
    _COUNTS.clear()
