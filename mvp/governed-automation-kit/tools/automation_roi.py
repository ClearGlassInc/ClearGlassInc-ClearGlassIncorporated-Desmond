#!/usr/bin/env python3
"""Governance-aware automation ROI and effort calculator (planning aid).

Most automation ROI calculators answer "how many hours does this remove?" and stop
there. That is the question that produces automation nobody is allowed to run,
because it prices the *execution* of a task and ignores the *decision* inside it.

This one prices the gate. An action that moves money, touches customer data, or
cannot be reversed does not stop needing a human when you automate it — the human
moves from doing the work to approving it. That review time is a permanent
operating cost of the automation, and it is why high-risk workflows routinely
return a fraction of the savings their business case promised.

The risk tiers and thresholds mirror the ones ClearGlass runs in production in
``control-plane/app/governance.py``: score 0-100, CRITICAL at >=90, HIGH at >=60,
MEDIUM at >=30, LOW below that, and unknown actions failing closed to HIGH. The
coverage figures below are this kit's own planning assumptions layered on top of
that model — they are estimates, not measurements, and the caller is told so on
every output.

Stdlib only, so it runs anywhere the rest of the ClearGlass tooling runs.

    python3 -m mvp.governed-automation-kit.tools.automation_roi --demo
    python3 mvp/governed-automation-kit/tools/automation_roi.py --json < tasks.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from typing import Any

#: Required on every output that carries a number. Non-negotiable: these figures
#: are arithmetic on user-supplied assumptions, not a forecast of results.
DISCLAIMER = (
    "Outputs are estimates based on user-entered assumptions. They are planning "
    "aids only and do not guarantee savings, financial results, return on "
    "investment, operational performance, or business outcomes."
)

#: Tier thresholds, mirroring control-plane/app/governance.py::_tier_for_score.
TIER_THRESHOLDS: list[tuple[int, str]] = [(90, "critical"), (60, "high"), (30, "medium")]

#: Share of hands-on time automation can realistically remove, by risk tier.
#: A gated action keeps its decision with a person, so the ceiling falls as the
#: tier rises. Planning assumptions — revise them against your own measurements.
AUTOMATABLE_SHARE: dict[str, float] = {
    "low": 0.95,       # reversible, no approval — automation runs unattended
    "medium": 0.80,    # queued for review; most items pass without intervention
    "high": 0.50,      # every action is read by a human before it executes
    "critical": 0.30,  # reviewed, and the review itself is checked
}

#: Minutes a human spends reviewing one gated run. Low tier is ungated (0).
REVIEW_MINUTES: dict[str, float] = {
    "low": 0.0,
    "medium": 0.5,
    "high": 2.0,
    "critical": 5.0,
}

VALID_TIERS = tuple(AUTOMATABLE_SHARE)


def tier_for_score(score: int) -> str:
    """Map a 0-100 risk score to a tier, mirroring the production governance model."""
    for threshold, tier in TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return "low"


@dataclass
class Task:
    """One candidate workflow, described in the numbers its owner actually knows."""

    name: str
    runs_per_month: float
    minutes_per_run: float
    hourly_cost: float
    implementation_hours: float
    risk_tier: str = "high"          # fail closed: unknown risk is not low risk
    people_per_run: float = 1.0
    rework_rate: float = 0.0         # 0-1: share of runs redone because of an error
    maintenance_hours_per_month: float = 0.0

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Task:
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(raw) - known
        if unknown:
            raise ValueError(f"unknown field(s): {', '.join(sorted(unknown))}")
        return cls(**raw)


@dataclass
class Result:
    """What the arithmetic says, plus why it says it."""

    name: str
    risk_tier: str
    gated: bool
    current_monthly_hours: float
    current_monthly_cost: float
    residual_monthly_cost: float
    monthly_saving: float
    implementation_cost: float
    payback_months: float | None
    net_12_month: float
    verdict: str
    reasons: list[str] = field(default_factory=list)
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate(task: Task) -> None:
    """Refuse to compute on inputs that cannot produce a meaningful number.

    Failing closed matters more here than it looks. A calculator that silently
    accepts a zero hourly cost returns a confident "saves $0/month" and the
    workflow gets deprioritised on a typo.
    """
    if not task.name or not task.name.strip():
        raise ValueError("task name is required")
    if task.risk_tier not in VALID_TIERS:
        raise ValueError(
            f"risk_tier must be one of {', '.join(VALID_TIERS)}; got {task.risk_tier!r}"
        )
    negatives = {
        "runs_per_month": task.runs_per_month,
        "minutes_per_run": task.minutes_per_run,
        "hourly_cost": task.hourly_cost,
        "implementation_hours": task.implementation_hours,
        "people_per_run": task.people_per_run,
        "maintenance_hours_per_month": task.maintenance_hours_per_month,
    }
    for label, value in negatives.items():
        if value < 0:
            raise ValueError(f"{label} cannot be negative (got {value})")
    if not 0.0 <= task.rework_rate <= 1.0:
        raise ValueError(f"rework_rate must be between 0 and 1 (got {task.rework_rate})")
    for label, value in (
        ("runs_per_month", task.runs_per_month),
        ("minutes_per_run", task.minutes_per_run),
        ("hourly_cost", task.hourly_cost),
        ("people_per_run", task.people_per_run),
    ):
        if value == 0:
            raise ValueError(
                f"{label} is zero — the result would be meaningless rather than free. "
                "Supply a real estimate, or leave the task out of the model."
            )


def evaluate(task: Task) -> Result:
    """Price a candidate workflow with its approval gate included."""
    _validate(task)

    tier = task.risk_tier
    gated = tier != "low"

    # Effective runs: rework means the same job is done more than once.
    effective_runs = task.runs_per_month * (1.0 + task.rework_rate)
    hours_per_run = (task.minutes_per_run / 60.0) * task.people_per_run
    current_hours = effective_runs * hours_per_run
    current_cost = current_hours * task.hourly_cost

    # What automation can actually take off the table at this tier.
    share = AUTOMATABLE_SHARE[tier]
    removed_hours = current_hours * share
    remaining_hours = current_hours - removed_hours

    # The gate is a new, permanent cost: a person reads every run that is gated.
    # It is charged on the real run count, not the reworked one — automation is
    # assumed to remove the rework, which is usually why it is being considered.
    review_hours = (REVIEW_MINUTES[tier] / 60.0) * task.runs_per_month
    maintenance_hours = task.maintenance_hours_per_month

    residual_hours = remaining_hours + review_hours + maintenance_hours
    residual_cost = residual_hours * task.hourly_cost
    monthly_saving = current_cost - residual_cost

    implementation_cost = task.implementation_hours * task.hourly_cost

    payback: float | None
    if monthly_saving <= 0:
        payback = None
    else:
        payback = implementation_cost / monthly_saving

    net_12 = (monthly_saving * 12.0) - implementation_cost

    reasons: list[str] = []
    if gated:
        reasons.append(
            f"{tier} risk: a human approves each run, so at most "
            f"{share:.0%} of hands-on time is removable and "
            f"{REVIEW_MINUTES[tier]:g} min/run of review is permanent"
        )
    else:
        reasons.append("low risk: reversible and ungated, so automation can run unattended")
    if task.rework_rate > 0:
        reasons.append(
            f"rework at {task.rework_rate:.0%} adds "
            f"{effective_runs - task.runs_per_month:.1f} runs/month to the baseline"
        )
    if maintenance_hours > 0:
        reasons.append(
            f"{maintenance_hours:g} h/month maintenance is charged against the saving"
        )

    # Verdict. Thresholds are deliberately conservative: an automation that takes
    # more than a year to pay back is competing with the possibility that the
    # workflow changes before it ever does.
    if monthly_saving <= 0:
        verdict = "DO_NOT_AUTOMATE"
        reasons.append("the gate and upkeep cost at least as much as the manual work")
    elif payback is not None and payback > 12:
        verdict = "DOCUMENT_FIRST"
        reasons.append(
            f"payback is {payback:.1f} months — standardise and re-measure before building"
        )
    elif payback is not None and payback > 6:
        verdict = "PILOT"
        reasons.append(f"payback is {payback:.1f} months — worth a scoped pilot, not a rollout")
    else:
        verdict = "AUTOMATE"
        reasons.append(f"payback is {payback:.1f} months on current assumptions")

    return Result(
        name=task.name,
        risk_tier=tier,
        gated=gated,
        current_monthly_hours=round(current_hours, 2),
        current_monthly_cost=round(current_cost, 2),
        residual_monthly_cost=round(residual_cost, 2),
        monthly_saving=round(monthly_saving, 2),
        implementation_cost=round(implementation_cost, 2),
        payback_months=None if payback is None else round(payback, 1),
        net_12_month=round(net_12, 2),
        verdict=verdict,
        reasons=reasons,
    )


def evaluate_all(tasks: list[Task]) -> list[Result]:
    """Evaluate a portfolio, best 12-month net first."""
    return sorted((evaluate(t) for t in tasks), key=lambda r: r.net_12_month, reverse=True)


DEMO_TASKS = [
    Task(
        name="Weekly access review (illustrative)",
        runs_per_month=4, minutes_per_run=90, hourly_cost=65,
        implementation_hours=20, risk_tier="high", rework_rate=0.10,
        maintenance_hours_per_month=1,
    ),
    Task(
        name="Invoice data entry (illustrative)",
        runs_per_month=120, minutes_per_run=6, hourly_cost=38,
        implementation_hours=30, risk_tier="medium", rework_rate=0.15,
        maintenance_hours_per_month=2,
    ),
    Task(
        name="Status report assembly (illustrative)",
        runs_per_month=20, minutes_per_run=25, hourly_cost=55,
        implementation_hours=12, risk_tier="low",
        maintenance_hours_per_month=0.5,
    ),
    Task(
        name="Customer refund approval (illustrative)",
        runs_per_month=15, minutes_per_run=12, hourly_cost=45,
        implementation_hours=25, risk_tier="critical",
        maintenance_hours_per_month=1.5,
    ),
]


def _render(results: list[Result]) -> str:
    rows = [
        f"{'Workflow':<38} {'Tier':<9} {'Save/mo':>10} {'Payback':>9}  Verdict",
        f"{'-' * 38} {'-' * 9} {'-' * 10} {'-' * 9}  {'-' * 16}",
    ]
    for r in results:
        payback = "never" if r.payback_months is None else f"{r.payback_months:.1f} mo"
        rows.append(
            f"{r.name[:38]:<38} {r.risk_tier:<9} "
            f"{r.monthly_saving:>9,.0f}  {payback:>9}  {r.verdict}"
        )
    rows.append("")
    for r in results:
        rows.append(f"{r.name} — {r.verdict}")
        for reason in r.reasons:
            rows.append(f"    · {reason}")
        rows.append("")
    rows.append(DISCLAIMER)
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Governance-aware automation ROI calculator (planning aid).",
        epilog=DISCLAIMER,
    )
    parser.add_argument("--demo", action="store_true",
                        help="run the illustrative example portfolio")
    parser.add_argument("--json", action="store_true",
                        help="emit JSON instead of a table")
    parser.add_argument("--input", metavar="PATH",
                        help="JSON file with a list of task objects (default: stdin)")
    args = parser.parse_args(argv)

    if args.demo:
        tasks = list(DEMO_TASKS)
    else:
        try:
            raw = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
        except OSError as exc:
            print(f"error: cannot read input: {exc}", file=sys.stderr)
            return 2
        if not raw.strip():
            print("error: no input. Use --demo, --input PATH, or pipe JSON on stdin.",
                  file=sys.stderr)
            return 2
        try:
            payload = json.loads(raw)
            tasks = [Task.from_dict(item) for item in payload]
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            print(f"error: invalid input: {exc}", file=sys.stderr)
            return 2

    try:
        results = evaluate_all(tasks)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(
            {"disclaimer": DISCLAIMER, "results": [r.to_dict() for r in results]},
            indent=2,
        ))
    else:
        print(_render(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
