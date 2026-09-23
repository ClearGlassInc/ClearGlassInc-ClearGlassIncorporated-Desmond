"""Transparent planning calculator for automation value estimates."""

from __future__ import annotations

import math
from typing import Mapping

NOTICE = (
    "Outputs are estimates based on user-entered assumptions. They are planning aids "
    "only and do not guarantee savings, financial results, return on investment, "
    "operational performance, or business outcomes."
)


def _number(inputs: Mapping[str, float], name: str, default: float = 0.0) -> float:
    value = float(inputs.get(name, default))
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return value


def estimate_annual_hours_saved(
    hours_per_run: float, runs_per_week: float, automation_fraction: float
) -> float:
    for name, value in (
        ("hours_per_run", hours_per_run),
        ("runs_per_week", runs_per_week),
        ("automation_fraction", automation_fraction),
    ):
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be a finite non-negative number")
    if automation_fraction > 1:
        raise ValueError("automation_fraction must be between 0 and 1")
    return hours_per_run * runs_per_week * 52.0 * automation_fraction


def estimate_annual_labor_value(hours_saved: float, hourly_cost: float) -> float:
    if not math.isfinite(hours_saved) or hours_saved < 0:
        raise ValueError("hours_saved must be a finite non-negative number")
    if not math.isfinite(hourly_cost) or hourly_cost < 0:
        raise ValueError("hourly_cost must be a finite non-negative number")
    return hours_saved * hourly_cost


def estimate_net_annual_value(
    annual_labor_value: float, annual_automation_cost: float
) -> float:
    if not math.isfinite(annual_labor_value) or annual_labor_value < 0:
        raise ValueError("annual_labor_value must be a finite non-negative number")
    if not math.isfinite(annual_automation_cost) or annual_automation_cost < 0:
        raise ValueError("annual_automation_cost must be a finite non-negative number")
    return annual_labor_value - annual_automation_cost


def estimate_simple_payback_months(
    initial_cost: float, monthly_net_value: float
) -> float | None:
    if not math.isfinite(initial_cost) or initial_cost < 0:
        raise ValueError("initial_cost must be a finite non-negative number")
    if not math.isfinite(monthly_net_value):
        raise ValueError("monthly_net_value must be finite")
    if monthly_net_value <= 0:
        return None
    return initial_cost / monthly_net_value


def calculate(inputs: Mapping[str, float]) -> dict[str, float | None | str]:
    hours_per_run = _number(inputs, "hours_per_run")
    runs_per_week = _number(inputs, "runs_per_week")
    automation_fraction = _number(inputs, "automation_fraction")
    hourly_cost = _number(inputs, "hourly_cost")
    annual_automation_cost = _number(inputs, "annual_automation_cost")
    initial_cost = _number(inputs, "initial_cost")

    annual_hours_saved = estimate_annual_hours_saved(
        hours_per_run, runs_per_week, automation_fraction
    )
    annual_labor_value = estimate_annual_labor_value(annual_hours_saved, hourly_cost)
    net_annual_value = estimate_net_annual_value(
        annual_labor_value, annual_automation_cost
    )
    monthly_net_value = net_annual_value / 12.0

    return {
        "annual_hours_saved": annual_hours_saved,
        "annual_labor_value": annual_labor_value,
        "net_annual_value": net_annual_value,
        "payback_months": estimate_simple_payback_months(
            initial_cost, monthly_net_value
        ),
        "notice": NOTICE,
    }
