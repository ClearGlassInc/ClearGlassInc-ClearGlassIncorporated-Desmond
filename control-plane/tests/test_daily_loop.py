"""Tests for the daily loop governance self-check."""
from __future__ import annotations

from app.daily_loop import build_report, governance_selfcheck


def test_governance_selfcheck_passes() -> None:
    assert governance_selfcheck() == []


def test_report_has_required_sections() -> None:
    report = build_report("2026-06-14")
    for key in (
        "store_health",
        "drafted_optimization",
        "drafted_content_improvement",
        "flagged_operational_risk",
        "executive_summary",
    ):
        assert key in report
