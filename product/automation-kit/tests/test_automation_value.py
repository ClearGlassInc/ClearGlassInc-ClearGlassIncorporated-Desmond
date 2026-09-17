import importlib.util
import math
from pathlib import Path

import pytest


_MODULE_PATH = Path(__file__).parents[1] / "calculators" / "automation_value.py"
_SPEC = importlib.util.spec_from_file_location("automation_value", _MODULE_PATH)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
calculate = _MODULE.calculate


NOTICE = (
    "Outputs are estimates based on user-entered assumptions. They are planning aids "
    "only and do not guarantee savings, financial results, return on investment, "
    "operational performance, or business outcomes."
)


def test_calculate_estimates_annual_hours_and_labor_value():
    result = calculate(
        {
            "hours_per_run": 2.0,
            "runs_per_week": 5.0,
            "automation_fraction": 0.5,
            "hourly_cost": 50.0,
            "annual_automation_cost": 1000.0,
            "initial_cost": 500.0,
        }
    )

    assert result["annual_hours_saved"] == 260.0
    assert result["annual_labor_value"] == 13000.0
    assert result["net_annual_value"] == 12000.0
    assert result["payback_months"] == pytest.approx(0.5)
    assert result["notice"] == NOTICE


def test_calculate_rejects_negative_inputs():
    with pytest.raises(ValueError):
        calculate({"hours_per_run": -1.0})


def test_calculate_rejects_non_finite_inputs():
    with pytest.raises(ValueError):
        calculate({"hourly_cost": math.inf})


def test_calculate_returns_no_payback_when_monthly_net_value_is_not_positive():
    result = calculate(
        {
            "initial_cost": 1000.0,
            "annual_automation_cost": 2000.0,
            "hours_per_run": 0.0,
            "runs_per_week": 1.0,
            "automation_fraction": 1.0,
            "hourly_cost": 10.0,
        }
    )

    assert result["payback_months"] is None
