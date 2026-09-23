"""The automation ROI calculator is a product asset, so its arithmetic is pinned.

This calculator exists to sell a specific claim: that pricing an automation without
pricing its approval gate overstates the return. If the tier ceilings or the review
cost stop being applied, the tool silently becomes the generic hours-removed
calculator it was built to replace — and the product's differentiation goes with it.

Two things are load-bearing and asserted here:

* the mandated estimates disclaimer appears on every output path, and
* a high-risk workflow never scores as well as the same workflow at low risk.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1] / "mvp" / "governed-automation-kit" / "tools"
if str(KIT) not in sys.path:
    sys.path.insert(0, str(KIT))

import automation_roi as roi  # noqa: E402


def _task(**overrides) -> roi.Task:
    base = dict(
        name="Example workflow",
        runs_per_month=40,
        minutes_per_run=15,
        hourly_cost=50.0,
        implementation_hours=20,
        risk_tier="low",
    )
    base.update(overrides)
    return roi.Task(**base)


# --------------------------------------------------------------- the core claim


def test_the_approval_gate_reduces_the_return() -> None:
    """The product's whole argument: the same work is worth less when it is gated."""
    savings = {
        tier: roi.evaluate(_task(risk_tier=tier)).monthly_saving
        for tier in ("low", "medium", "high", "critical")
    }
    assert savings["low"] > savings["medium"] > savings["high"] > savings["critical"], savings


def test_a_gated_workflow_can_be_worth_less_than_doing_it_by_hand() -> None:
    """The finding a generic hours-removed calculator cannot produce."""
    result = roi.evaluate(
        _task(
            name="Customer refund approval",
            runs_per_month=15, minutes_per_run=12,
            hourly_cost=45.0, implementation_hours=25,
            risk_tier="critical", maintenance_hours_per_month=1.5,
        )
    )
    assert result.monthly_saving < 0
    assert result.verdict == "DO_NOT_AUTOMATE"
    assert result.payback_months is None


def test_review_time_is_charged_only_where_the_tier_is_gated() -> None:
    assert roi.evaluate(_task(risk_tier="low")).gated is False
    for tier in ("medium", "high", "critical"):
        assert roi.evaluate(_task(risk_tier=tier)).gated is True


def test_tier_thresholds_match_the_production_governance_model() -> None:
    """Mirrors control-plane/app/governance.py::_tier_for_score."""
    assert roi.tier_for_score(100) == "critical"
    assert roi.tier_for_score(90) == "critical"
    assert roi.tier_for_score(89) == "high"
    assert roi.tier_for_score(60) == "high"
    assert roi.tier_for_score(59) == "medium"
    assert roi.tier_for_score(30) == "medium"
    assert roi.tier_for_score(29) == "low"
    assert roi.tier_for_score(0) == "low"


def test_unspecified_risk_fails_closed_to_high() -> None:
    """A task whose risk nobody set must not be priced as if it were safe."""
    assert roi.Task(
        name="Unclassified", runs_per_month=10, minutes_per_run=10,
        hourly_cost=50.0, implementation_hours=5,
    ).risk_tier == "high"


# --------------------------------------------------------------- the disclaimer


def test_every_output_path_carries_the_disclaimer(capsys) -> None:
    """Required by the MVP approval: no number ships without it."""
    assert "planning aids only" in roi.DISCLAIMER

    assert roi.evaluate(_task()).disclaimer == roi.DISCLAIMER

    assert roi.main(["--demo"]) == 0
    assert roi.DISCLAIMER in capsys.readouterr().out

    assert roi.main(["--demo", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["disclaimer"] == roi.DISCLAIMER


# --------------------------------------------------------------- failing closed


@pytest.mark.parametrize(
    "overrides",
    [
        {"hourly_cost": 0.0},
        {"runs_per_month": 0},
        {"minutes_per_run": 0},
        {"people_per_run": 0},
        {"name": "   "},
        {"risk_tier": "catastrophic"},
        {"rework_rate": 1.5},
        {"implementation_hours": -1},
    ],
)
def test_meaningless_inputs_are_refused_rather_than_answered(overrides) -> None:
    """A zero or a typo must not come back as a confident '$0 saved'."""
    with pytest.raises(ValueError):
        roi.evaluate(_task(**overrides))


def test_unknown_fields_are_rejected(capsys) -> None:
    with pytest.raises(ValueError, match="unknown field"):
        roi.Task.from_dict({"name": "x", "runs_per_month": 1, "minutes_per_run": 1,
                            "hourly_cost": 1, "implementation_hours": 1, "typo_field": 9})

    assert roi.main(["--input", "/nonexistent/path.json"]) == 2
    assert "cannot read input" in capsys.readouterr().err


# --------------------------------------------------------------- the arithmetic


def test_baseline_cost_is_hours_times_rate() -> None:
    result = roi.evaluate(_task(runs_per_month=10, minutes_per_run=60, hourly_cost=100.0))
    assert result.current_monthly_hours == 10.0
    assert result.current_monthly_cost == 1000.0


def test_rework_adds_runs_to_the_baseline() -> None:
    plain = roi.evaluate(_task(rework_rate=0.0))
    reworked = roi.evaluate(_task(rework_rate=0.25))
    assert reworked.current_monthly_hours == pytest.approx(plain.current_monthly_hours * 1.25)


def test_twelve_month_net_nets_off_the_build() -> None:
    result = roi.evaluate(_task())
    assert result.net_12_month == pytest.approx(
        result.monthly_saving * 12 - result.implementation_cost, abs=0.01
    )


def test_portfolio_is_ranked_by_twelve_month_net() -> None:
    results = roi.evaluate_all(list(roi.DEMO_TASKS))
    assert [r.net_12_month for r in results] == sorted(
        (r.net_12_month for r in results), reverse=True
    )
