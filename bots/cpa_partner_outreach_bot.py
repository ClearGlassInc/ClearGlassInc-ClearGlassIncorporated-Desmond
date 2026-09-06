# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""
ClearGlass CPA / Fractional CFO Partner Outreach Bot

Automates the CPA partner-channel motion: compliant outreach templates,
the CPA Partner Program one-pager, a weekly micro execution plan, the
partner revenue model, and KPI targets.

Positioning guardrails (baked in, non-negotiable):
  - Legal AI is assistive / decision-support only — never legal advice.
  - PIPEDA-aligned explicit consent; API-based access (no screen scraping).
  - Revenue figures are illustrative partner potential, not guarantees.

Outputs structured JSON + Markdown to marketing/output/cpa_partner/ for
analyst review and deployment. Designed to run on the bot scheduler.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "marketing" / "output" / "cpa_partner"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TRIAL_CTA = "Start a 14-day partner trial"
LANDING_LINK = "https://www.clearglassinc.com/revenue-engine.html"

COMPLIANCE_NOTES = [
    "PIPEDA-aligned explicit consent flows",
    "No screen scraping — secure API-based data access (Flinks)",
    "Legal AI positioned as assistive / decision-support only, not legal advice",
    "Stripe / Gumroad approved payment processing",
]


# ── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class OutreachTemplate:
    key: str
    name: str
    channel: str          # "linkedin" | "email"
    angle: str
    subject: str          # may be empty for short DMs
    body: str


@dataclass
class PartnerTier:
    tier: str
    description: str
    revenue_potential: str


@dataclass
class ExecutionStep:
    days: str
    focus: str
    actions: list[str]


@dataclass
class OnePager:
    title: str
    tagline: str
    what_it_does: list[str]
    who_its_for: list[str]
    partner_benefits: dict[str, list[str]]
    core_features: list[str]
    compliance: list[str]
    partner_tiers: list[PartnerTier]
    pilot_offer: list[str]
    trial_link: str


@dataclass
class CpaPartnerRun:
    run_utc: str
    program: str
    templates: list[OutreachTemplate]
    one_pager: OnePager
    execution_plan: list[ExecutionStep]
    revenue_model: dict[str, str]
    kpis: dict[str, str]
    compliance_notes: list[str] = field(default_factory=lambda: list(COMPLIANCE_NOTES))


# ── Copy Generation ───────────────────────────────────────────────────────────

def build_templates() -> list[OutreachTemplate]:
    value_first = OutreachTemplate(
        key="value_first_linkedin",
        name="Value-first (LinkedIn DM)",
        channel="linkedin",
        angle="value-first",
        subject="Helping your SMB clients with real-time cash flow + compliance",
        body="""Hi {{first_name}},

I'm building ClearGlass, a platform combining real-time bank data (via Flinks) + AI forecasting + compliance-safe legal insights for Canadian SMBs.

We're partnering with CPAs & fractional CFOs to:
- Deliver live cash flow forecasting dashboards to clients
- Reduce prep time on reporting
- Add a white-label recurring revenue stream ($999+/mo per client cluster)

Important: We position the Legal AI as assistive only (no legal advice) and fully aligned with PIPEDA consent + explicit data permissions.

Would you be open to a quick walkthrough? I can also set you up with a 14-day partner trial.

— {{sender_name}}""",
    )

    revenue_angle = OutreachTemplate(
        key="revenue_angle_email",
        name="Revenue angle (Email)",
        channel="email",
        angle="revenue",
        subject="Add $5K–$15K MRR from your existing client base",
        body="""Hi {{first_name}},

Quick idea for your practice:

We've built a white-label platform for CPAs that combines:
- Flinks-powered real-time banking data
- AI-driven cash flow + forecasting
- Built-in compliance-safe legal guidance layer

Partners are using it to:
- Upsell clients into $99–$299/mo reporting tiers
- Bundle services → increasing retention + margins
- Add predictable MRR without extra headcount

Everything is structured to stay compliant:
- Explicit client consent (PIPEDA aligned)
- No screen scraping
- Legal AI positioned as decision support only

Would it make sense to show you how 3–5 clients could cover your cost immediately?

Best,
{{sender_name}}""",
    )

    pilot_focused = OutreachTemplate(
        key="pilot_focused",
        name="Pilot-focused (Short + direct)",
        channel="linkedin",
        angle="pilot",
        subject="",
        body="""Hi {{first_name}},

I'm inviting a small group of CPAs to pilot a ClearGlass white-label dashboard powered by Flinks + AI forecasting.

You'll get:
- 14-day free access
- Branded client dashboards
- Revenue share model

Goal: Help you turn existing clients into monthly recurring revenue while staying fully compliant (PIPEDA + assistive AI positioning).

Interested in testing it with 2–3 clients this month?

— {{sender_name}}""",
    )

    return [value_first, revenue_angle, pilot_focused]


def build_one_pager() -> OnePager:
    return OnePager(
        title="ClearGlass CPA Partner Program",
        tagline="Turn your client base into recurring revenue with real-time financial intelligence",
        what_it_does=[
            "Flinks Open Banking API → real-time financial data",
            "AI forecasting engine → predictive cash flow insights",
            "ClearBank Legal AI layer → compliance-aware guidance (assistive only)",
        ],
        who_its_for=[
            "CPAs",
            "Fractional CFOs",
            "Bookkeeping firms",
            "Accounting consultancies serving SMBs in Canada",
        ],
        partner_benefits={
            "New Revenue Streams": [
                "$99–$299/month per SMB client",
                "$999+/month white-label packages",
            ],
            "Stronger Client Retention": [
                "Always-on dashboards",
                "Continuous value beyond tax season",
            ],
            "Operational Efficiency": [
                "Automated reporting",
                "Reduced manual reconciliation",
            ],
            "White-Label Ready": [
                "Your branding",
                "Your client relationships",
                "Your pricing control",
            ],
        },
        core_features=[
            "Live bank data (Flinks integration)",
            "AI-powered forecasting dashboards",
            "Cash flow alerts + insights",
            "Compliance-safe legal assist layer",
            "Client-ready reporting interface",
        ],
        compliance=list(COMPLIANCE_NOTES),
        partner_tiers=[
            PartnerTier("Starter", "3–10 clients", "$300–$3K MRR"),
            PartnerTier("Growth", "10–50 clients", "$3K–$15K MRR"),
            PartnerTier("White-label", "Full deployment", "$999+/mo per bundle"),
        ],
        pilot_offer=[
            "Full dashboard access",
            "2–3 client onboarding",
            "Guided setup",
            "No commitment",
        ],
        trial_link=LANDING_LINK,
    )


def build_execution_plan() -> list[ExecutionStep]:
    return [
        ExecutionStep(
            days="Day 1–2",
            focus="Update landing page",
            actions=[
                '"Flinks-powered real-time data" headline',
                "Demo screenshot (even staging/mock)",
                f"CTA: {TRIAL_CTA}",
            ],
        ),
        ExecutionStep(
            days="Day 3–5",
            focus="Send 50 outreach messages",
            actions=[
                "30 LinkedIn",
                "20 email",
                "Target: Ontario CPAs, fractional CFOs, firms with 5–50 SMB clients",
            ],
        ),
        ExecutionStep(
            days="Day 6–7",
            focus="Convert",
            actions=[
                "5–10 demos booked",
                "2–3 pilot partners",
            ],
        ),
    ]


def build_revenue_model() -> dict[str, str]:
    return {
        "early_baseline": "3 CPAs × 5 clients × $99 = ~$1,500 MRR",
        "white_label_add": "+$999 MRR per white-label deal",
        "ramp_60_90_days": "Realistic trajectory toward $8K–$25K MRR",
        "disclaimer": "Figures are illustrative partner potential, not guarantees.",
    }


def build_kpis() -> dict[str, str]:
    return {
        "outreach_volume_per_week": "50 touches (30 LinkedIn + 20 email)",
        "target_demos_booked": "5–10 per week",
        "target_pilot_partners": "2–3 per week",
        "trial_length_days": "14",
        "per_client_pricing": "$99–$299/mo",
        "white_label_pricing": "$999+/mo per client cluster",
        "icp_qualifier": "Canadian CPAs / fractional CFOs / bookkeeping firms with 5–50 SMB clients",
        "disqualifier": "No SMB book of business; unwilling to obtain explicit client consent",
    }


# ── Run Builder ───────────────────────────────────────────────────────────────

def build_run() -> CpaPartnerRun:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return CpaPartnerRun(
        run_utc=now,
        program="ClearGlass CPA Partner Program",
        templates=build_templates(),
        one_pager=build_one_pager(),
        execution_plan=build_execution_plan(),
        revenue_model=build_revenue_model(),
        kpis=build_kpis(),
    )


# ── Output Writers ────────────────────────────────────────────────────────────

def _md_template(t: OutreachTemplate) -> str:
    header = f"### {t.name} — {t.channel.title()}\n\n"
    subject = f"**Subject:** `{t.subject}`\n\n" if t.subject else ""
    return f"{header}{subject}```\n{t.body.strip()}\n```\n\n"


def build_markdown(run: CpaPartnerRun) -> str:
    op = run.one_pager
    lines: list[str] = [
        f"# {run.program}\n",
        f"**Generated:** {run.run_utc}  \n",
        f"**Trial CTA:** {TRIAL_CTA} → {op.trial_link}\n\n",
        "> Compliance positioning is non-negotiable: Legal AI is assistive only "
        "(not legal advice); PIPEDA-aligned explicit consent; API-based access, no screen scraping.\n",
        "\n---\n",
        "\n## 1) Outreach Templates (Compliant)\n\n",
    ]
    for t in run.templates:
        lines.append(_md_template(t))

    lines.append("---\n\n")
    lines.append("## 2) CPA Partner One-Pager\n\n")
    lines.append(f"### {op.title}\n")
    lines.append(f"_{op.tagline}_\n\n")

    lines.append("**What ClearGlass Does**\n\n")
    for item in op.what_it_does:
        lines.append(f"- {item}\n")
    lines.append("\n**Who It's For**\n\n")
    for item in op.who_its_for:
        lines.append(f"- {item}\n")

    lines.append("\n**Partner Benefits**\n\n")
    for benefit, points in op.partner_benefits.items():
        lines.append(f"- **{benefit}**\n")
        for p in points:
            lines.append(f"  - {p}\n")

    lines.append("\n**Core Features**\n\n")
    for item in op.core_features:
        lines.append(f"- {item}\n")

    lines.append("\n**Compliance & Trust**\n\n")
    for item in op.compliance:
        lines.append(f"- ✅ {item}\n")

    lines.append("\n**Partner Model**\n\n")
    lines.append("| Tier | Description | Revenue Potential |\n|---|---|---|\n")
    for tier in op.partner_tiers:
        lines.append(f"| {tier.tier} | {tier.description} | {tier.revenue_potential} |\n")

    lines.append("\n**14-Day Pilot Offer**\n\n")
    for item in op.pilot_offer:
        lines.append(f"- {item}\n")
    lines.append(f"\n👉 {TRIAL_CTA}: {op.trial_link}\n\n")

    lines.append("---\n\n")
    lines.append("## 3) Weekly Micro Execution Plan\n\n")
    for step in run.execution_plan:
        lines.append(f"**{step.days} — {step.focus}**\n\n")
        for action in step.actions:
            lines.append(f"- {action}\n")
        lines.append("\n")

    lines.append("---\n\n")
    lines.append("## Revenue Model (Illustrative)\n\n")
    for k, v in run.revenue_model.items():
        lines.append(f"- **{k.replace('_', ' ').title()}:** {v}\n")

    lines.append("\n## KPI Targets\n\n")
    lines.append("| Metric | Target |\n|---|---|\n")
    for k, v in run.kpis.items():
        lines.append(f"| {k.replace('_', ' ').title()} | {v} |\n")
    lines.append("\n---\n")

    return "".join(lines)


def write_outputs(run: CpaPartnerRun, output_dir: Path = OUTPUT_DIR) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = run.run_utc.replace(":", "").replace("-", "")[:15]

    md_path = output_dir / f"cpa_partner_{slug}.md"
    json_path = output_dir / f"cpa_partner_{slug}.json"

    md_path.write_text(build_markdown(run), encoding="utf-8")
    json_path.write_text(json.dumps(asdict(run), indent=2, default=str), encoding="utf-8")

    (output_dir / "latest.md").write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    (output_dir / "latest.json").write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")

    return md_path, json_path


# ── Entry Point ───────────────────────────────────────────────────────────────

def main() -> CpaPartnerRun:
    run = build_run()
    md_path, json_path = write_outputs(run)

    print(f"[cpa-partner-bot] Run complete: {run.run_utc}")
    print(f"  Templates: {len(run.templates)}")
    print(f"  Markdown : {md_path.relative_to(ROOT)}")
    print(f"  JSON     : {json_path.relative_to(ROOT)}")

    return run


if __name__ == "__main__":
    main()
