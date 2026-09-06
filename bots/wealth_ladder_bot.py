# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Wealth Ladder Bot — sequenced wealth-building engine for ClearGlass.

Encodes the standing strategy:

    Revenue → Corporation → Business Credit → Investment Assets → Trust

The governing thesis is simple: *a trust with no assets is like a vault with
nothing inside.* So the Trust stage is intentionally gated — it stays locked
until real, fundable assets exist. Starting with a trust usually creates legal
bills before it creates income.

The bot is deterministic and data-driven. It reads an optional ledger override
from ``operations/wealth_ladder/ledger.json`` describing the current state of
each rung, computes which rung deserves focus today, and emits a "fastest legal
way to get paid now" plan. It writes Markdown (human review) and JSON
(downstream automation), with a rolling ``latest.*`` plus a timestamped archive.

NOTE: The benefit-eligibility items below are *review prompts*, not legal,
medical, or financial advice. They flag programs to evaluate with a qualified
professional — they do not assert eligibility.

Usage:
    python -m bots.wealth_ladder_bot              # render + write outputs
    python -m bots.wealth_ladder_bot --print      # render to stdout only
    python -m bots.wealth_ladder_bot --ledger path/to/ledger.json
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "wealth_ladder"
ARCHIVE_DIR = OUTPUT_DIR / "archive"
LEDGER_PATH = OUTPUT_DIR / "ledger.json"

TWOPLACES = Decimal("0.01")

# The point below which a trust is usually not the highest-return move. Many
# Canadian accountants and lawyers point out that most people asking about
# trusts have a simpler, cheaper solution available.
TRUST_ASSET_FLOOR = Decimal("100000")


def d(value: str | float | int | Decimal) -> Decimal:
    return Decimal(str(value))


def money(value: Decimal) -> str:
    return f"${value.quantize(TWOPLACES, rounding=ROUND_HALF_UP):,.2f}"


# ---------------------------------------------------------------------------
# Ledger — the current state of the climb
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Ledger:
    """Snapshot of where the operator stands on each rung."""
    monthly_revenue: Decimal = field(default_factory=lambda: d(0))
    revenue_target: Decimal = field(default_factory=lambda: d(5000))
    incorporated: bool = False
    business_credit_score: int = 0          # 0 means no business credit file yet
    business_credit_target: int = 80        # PAYDEX-style 0-100 target
    investable_assets: Decimal = field(default_factory=lambda: d(0))
    trust_established: bool = False

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> "Ledger":
        defaults = Ledger()
        return Ledger(
            monthly_revenue=d(raw.get("monthly_revenue", defaults.monthly_revenue)),
            revenue_target=d(raw.get("revenue_target", defaults.revenue_target)),
            incorporated=bool(raw.get("incorporated", defaults.incorporated)),
            business_credit_score=int(raw.get("business_credit_score", defaults.business_credit_score)),
            business_credit_target=int(raw.get("business_credit_target", defaults.business_credit_target)),
            investable_assets=d(raw.get("investable_assets", defaults.investable_assets)),
            trust_established=bool(raw.get("trust_established", defaults.trust_established)),
        )


# ---------------------------------------------------------------------------
# The ladder
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Rung:
    order: int
    key: str
    label: str
    satisfied: bool
    locked: bool
    progress_pct: int
    rationale: str
    next_actions: tuple[str, ...]


@dataclass(frozen=True)
class WealthPlan:
    run_utc: str
    date: str
    headline: str
    thesis: str
    sequence: str
    rungs: list[Rung]
    focus_key: str
    focus_label: str
    fast_cash_track: list[str]
    benefit_reviews: list[str]
    clearglass_services: list[dict[str, str]]
    strategic_reality: str
    mantra: str


THESIS = "A trust with no assets is like a vault with nothing inside."
SEQUENCE = "ClearGlass Inc. → Revenue → Corporate Credit → Holding Company → Family Trust"

STRATEGIC_REALITY = (
    "If net worth is under roughly six figures, a trust is usually not the "
    "highest-return move. The stronger sequence builds the assets first, then "
    "wraps protection around them. Starting with the trust usually creates "
    "legal bills before it creates income."
)

# Income that can be pursued far faster than establishing a trust. These are
# review prompts — evaluate eligibility with a qualified professional.
BENEFIT_REVIEWS = [
    "Review eligibility for the Canada Disability Benefit, if applicable.",
    "Review Disability Tax Credit (DTC) eligibility.",
    "Review CPP Disability eligibility if unable to work consistently.",
]

# ClearGlass income-producing services, ordered fastest-to-cash first.
CLEARGLASS_SERVICES: list[dict[str, str]] = [
    {
        "service": "AI risk assessments",
        "speed": "fast",
        "offer": "Fixed-scope AI risk assessment with a written findings pack.",
    },
    {
        "service": "Cybersecurity audits",
        "speed": "fast",
        "offer": "Endpoint / posture audit with prioritized remediation report.",
    },
    {
        "service": "Compliance consulting",
        "speed": "medium",
        "offer": "Gap analysis against the client's target framework.",
    },
    {
        "service": "AI automation implementation",
        "speed": "medium",
        "offer": "Build-and-deploy of one revenue-saving workflow per engagement.",
    },
]


def _pct(current: Decimal, target: Decimal) -> int:
    if target <= 0:
        return 100
    raw = (current / target) * d(100)
    return max(0, min(100, int(raw.to_integral_value(rounding=ROUND_HALF_UP))))


def evaluate_ladder(ledger: Ledger) -> list[Rung]:
    """Evaluate every rung in priority order, honoring the trust asset-gate."""
    revenue_ok = ledger.monthly_revenue >= ledger.revenue_target
    corp_ok = ledger.incorporated
    credit_ok = ledger.business_credit_score >= ledger.business_credit_target
    assets_ok = ledger.investable_assets >= TRUST_ASSET_FLOOR
    trust_unlocked = assets_ok
    trust_ok = ledger.trust_established and trust_unlocked

    rungs = [
        Rung(
            order=1,
            key="revenue",
            label="Revenue",
            satisfied=revenue_ok,
            locked=False,
            progress_pct=_pct(ledger.monthly_revenue, ledger.revenue_target),
            rationale=(
                f"{money(ledger.monthly_revenue)} / {money(ledger.revenue_target)} "
                "monthly. Cash funds every rung above it."
            ),
            next_actions=(
                "Ship one ClearGlass paid offer this week (fixed scope, fast close).",
                "Reply to inbound leads inside 5 minutes; book the call same day.",
            ) if not revenue_ok else ("Hold the line; reinvest surplus into the next rung.",),
        ),
        Rung(
            order=2,
            key="corporation",
            label="Corporation",
            satisfied=corp_ok,
            locked=not revenue_ok,
            progress_pct=100 if corp_ok else 0,
            rationale=(
                "Incorporated — ClearGlass Inc. is the legal container for revenue."
                if corp_ok else
                "Incorporate once revenue is proven, so the corp wraps real income."
            ),
            next_actions=(
                "Open a dedicated business bank account; route all revenue through it.",
            ) if corp_ok else (
                "Prove revenue first, then file articles of incorporation for ClearGlass Inc.",
            ),
        ),
        Rung(
            order=3,
            key="business_credit",
            label="Business Credit",
            satisfied=credit_ok,
            locked=not corp_ok,
            progress_pct=_pct(d(ledger.business_credit_score), d(ledger.business_credit_target)),
            rationale=(
                f"Business credit score {ledger.business_credit_score} / "
                f"{ledger.business_credit_target}."
            ),
            next_actions=(
                "Establish trade lines under the corp; pay early to build the file.",
            ) if not credit_ok else (
                "Leverage credit for asset-acquiring, cash-flowing purchases only.",
            ),
        ),
        Rung(
            order=4,
            key="investment_assets",
            label="Investment Assets",
            satisfied=assets_ok,
            locked=not credit_ok,
            progress_pct=_pct(ledger.investable_assets, TRUST_ASSET_FLOOR),
            rationale=(
                f"Investable assets {money(ledger.investable_assets)} "
                f"vs {money(TRUST_ASSET_FLOOR)} trust floor."
            ),
            next_actions=(
                "Move retained earnings into a holding company; accumulate appreciating assets.",
            ),
        ),
        Rung(
            order=5,
            key="trust",
            label="Trust",
            satisfied=trust_ok,
            locked=not trust_unlocked,
            progress_pct=100 if trust_ok else (50 if trust_unlocked else 0),
            rationale=(
                THESIS if not trust_unlocked else
                "Assets clear the floor — a trust now protects something real."
            ),
            next_actions=(
                f"Locked until investable assets reach {money(TRUST_ASSET_FLOOR)}. "
                "Build the vault's contents first.",
            ) if not trust_unlocked else (
                "Engage counsel to settle a family trust around the holding company.",
            ),
        ),
    ]
    return rungs


def current_focus(rungs: list[Rung]) -> Rung:
    """First unsatisfied, unlocked rung — that's today's battle."""
    for rung in rungs:
        if not rung.satisfied and not rung.locked:
            return rung
    # Everything reachable is satisfied; focus on the highest reachable rung.
    reachable = [r for r in rungs if not r.locked]
    return reachable[-1] if reachable else rungs[0]


def build_plan(ledger: Ledger | None = None) -> WealthPlan:
    ledger = ledger or Ledger()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    rungs = evaluate_ladder(ledger)
    focus = current_focus(rungs)

    fast_cash = [
        "Revenue is the fastest legal way to get paid now — it beats waiting on a trust.",
        f"Today's rung: {focus.label}. {focus.next_actions[0]}",
        "Stack benefit-eligibility reviews in parallel; they need no capital to start.",
    ]

    headline = (
        f"Focus: {focus.label} "
        f"({focus.progress_pct}% there) — climb in order, skip nothing."
    )

    return WealthPlan(
        run_utc=now.isoformat(),
        date=now.date().isoformat(),
        headline=headline,
        thesis=THESIS,
        sequence=SEQUENCE,
        rungs=rungs,
        focus_key=focus.key,
        focus_label=focus.label,
        fast_cash_track=fast_cash,
        benefit_reviews=list(BENEFIT_REVIEWS),
        clearglass_services=[dict(s) for s in CLEARGLASS_SERVICES],
        strategic_reality=STRATEGIC_REALITY,
        mantra="Fill the vault before you build it. Revenue first. Always.",
    )


# ---------------------------------------------------------------------------
# Config / IO
# ---------------------------------------------------------------------------

def load_ledger(ledger_path: Path | None = None) -> Ledger:
    path = ledger_path if ledger_path is not None else LEDGER_PATH
    if path and path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Ledger at {path} must be a JSON object")
        return Ledger.from_dict(raw)
    return Ledger()


def _serialize(plan: WealthPlan) -> dict:
    payload = asdict(plan)
    payload["rungs"] = [asdict(r) for r in plan.rungs]
    return payload


def build_markdown(plan: WealthPlan) -> str:
    lines = [
        "# ClearGlass Wealth Ladder",
        "",
        f"- Generated (UTC): {plan.run_utc}",
        f"- Date: {plan.date}",
        "",
        f"> **{plan.thesis}**",
        "",
        f"**Sequence:** {plan.sequence}",
        "",
        f"## {plan.headline}",
        "",
        "## THE LADDER (priority order)",
        "| # | Rung | Status | Progress | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in plan.rungs:
        if r.satisfied:
            status = "✓ done"
        elif r.locked:
            status = "🔒 locked"
        elif r.key == plan.focus_key:
            status = "▶ FOCUS"
        else:
            status = "… pending"
        lines.append(f"| {r.order} | {r.label} | {status} | {r.progress_pct}% | {r.rationale} |")

    lines += ["", "## TODAY'S NEXT ACTIONS"]
    for action in plan.rungs[plan.rungs.index(next(r for r in plan.rungs if r.key == plan.focus_key))].next_actions:
        lines.append(f"- {action}")

    lines += ["", "## FASTEST LEGAL WAY TO GET PAID NOW"]
    lines += [f"- {item}" for item in plan.fast_cash_track]

    lines += ["", "### Benefit-eligibility reviews (not advice — evaluate with a professional)"]
    lines += [f"- {item}" for item in plan.benefit_reviews]

    lines += ["", "### ClearGlass income-producing services (fastest to cash first)"]
    for svc in plan.clearglass_services:
        lines.append(f"- **{svc['service']}** ({svc['speed']}): {svc['offer']}")

    lines += ["", "## STRATEGIC REALITY", plan.strategic_reality]
    lines += ["", f"**REPEAT:** {plan.mantra}", ""]
    return "\n".join(lines)


def render_terminal(plan: WealthPlan) -> str:
    bar = "=" * 64
    out = [bar, f"  CLEARGLASS WEALTH LADDER — {plan.date}", bar, "", f"  {plan.thesis}", ""]
    for r in plan.rungs:
        mark = "✓" if r.satisfied else ("🔒" if r.locked else ("▶" if r.key == plan.focus_key else "·"))
        out.append(f"  {mark} {r.order}. {r.label:<18} {r.progress_pct:>3}%  {r.rationale}")
    out += ["", f"  FOCUS: {plan.focus_label}", ""]
    out += ["  Fastest legal way to get paid now:"]
    out += [f"    - {i}" for i in plan.fast_cash_track]
    out += ["", bar, f"  {plan.mantra}", bar]
    return "\n".join(out)


def write_outputs(plan: WealthPlan) -> dict[str, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    stamp = plan.run_utc.replace("+00:00", "Z").replace(":", "")
    markdown = build_markdown(plan)
    payload = json.dumps(_serialize(plan), indent=2) + "\n"

    paths = {
        "latest_md": OUTPUT_DIR / "latest.md",
        "latest_json": OUTPUT_DIR / "latest.json",
        "archive_md": ARCHIVE_DIR / f"{stamp}.md",
        "archive_json": ARCHIVE_DIR / f"{stamp}.json",
    }
    paths["latest_md"].write_text(markdown, encoding="utf-8")
    paths["latest_json"].write_text(payload, encoding="utf-8")
    paths["archive_md"].write_text(markdown, encoding="utf-8")
    paths["archive_json"].write_text(payload, encoding="utf-8")
    return paths


def should_publish() -> bool:
    return os.getenv("WEALTH_LADDER_ENABLED", "true").strip().lower() == "true"


def run() -> None:
    """Entry point for the universal bot runner (no CLI args)."""
    if not should_publish():
        print("Wealth ladder generation disabled via WEALTH_LADDER_ENABLED=false")
        return
    plan = build_plan(load_ledger())
    paths = write_outputs(plan)
    print(f"Wealth ladder focus: {plan.focus_label} → {paths['latest_md']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the ClearGlass wealth-ladder plan.")
    parser.add_argument("--ledger", type=Path, default=None, help="Path to a JSON ledger override.")
    parser.add_argument("--print", action="store_true", help="Render to stdout, do not write files.")
    args = parser.parse_args(argv)

    if not should_publish():
        print("Wealth ladder generation disabled via WEALTH_LADDER_ENABLED=false")
        return 0

    plan = build_plan(load_ledger(args.ledger))
    print(render_terminal(plan))

    if args.print:
        return 0

    paths = write_outputs(plan)
    print(f"\nWrote: {paths['latest_md']}")
    print(f"Wrote: {paths['latest_json']}")
    print(f"Archived: {paths['archive_md'].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
