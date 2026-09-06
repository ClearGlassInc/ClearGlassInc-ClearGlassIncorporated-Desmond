# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""
ClearGlassInc Sales Outreach Bot

Generates hyper-personalized cold email sequences, LinkedIn messages, and
follow-up cadences for three enterprise verticals:
  - Government / Defense
  - Financial Institutions
  - Enterprise Technology

Outputs structured JSON + Markdown to marketing/output/sales/ for analyst
review and deployment. Designed to run on a weekly GitHub Actions schedule.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "marketing" / "output" / "sales"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Verticals ─────────────────────────────────────────────────────────────────

VERTICALS = {
    "government_defense": {
        "label": "Government / Defense",
        "icp": "CISOs, Deputy CIOs, Procurement Officers at federal agencies and defense contractors",
        "pain_points": [
            "CMMC 2.0 and FedRAMP compliance gaps creating audit liability",
            "Lateral movement risks from legacy system exposure",
            "Manual threat triage consuming analyst bandwidth during budget freeze",
            "Insufficient audit trails for IG reviews and congressional oversight",
        ],
        "urgency_triggers": [
            "Recent breach at peer agency (visibility + accountability pressure)",
            "Annual FISMA reporting cycle",
            "FY budget close / new fiscal year procurement window",
            "CMMC 2.0 enforcement deadline approaching",
        ],
        "value_props": [
            "Zero-trust architecture validated against NIST SP 800-207",
            "Continuous compliance monitoring with automated evidence collection",
            "Autonomous threat triage — reduces analyst queue by 70%+",
            "Full audit trail with cryptographic integrity for IG-grade accountability",
        ],
        "social_proof": "Trusted by organizations operating under ITAR, FedRAMP, and CMMC frameworks",
        "cta_primary": "Request a 20-minute classified-architecture briefing",
        "cta_secondary": "Download our FedRAMP alignment datasheet",
    },
    "financial_institutions": {
        "label": "Financial Institutions",
        "icp": "CISOs, CROs, Head of Information Security at banks, credit unions, asset managers",
        "pain_points": [
            "SOC/DORA/FFIEC audit findings creating regulatory capital risk",
            "Third-party vendor exposure invisible to current monitoring stack",
            "Ransomware dwell time averaging 21 days before detection",
            "Alert fatigue causing SOC analysts to miss high-severity events",
        ],
        "urgency_triggers": [
            "Upcoming OCC / FDIC examination cycle",
            "Peer institution breach (board-level scrutiny spike)",
            "New DORA compliance deadline (EU institutions)",
            "Cyber insurance renewal requiring risk reduction evidence",
        ],
        "value_props": [
            "Real-time third-party risk surface monitoring across entire vendor chain",
            "AI-driven alert correlation — 90% noise reduction, zero false-negative SLA",
            "Mean time to detect (MTTD) < 4 hours vs. industry average 21 days",
            "Audit-ready compliance dashboard exportable to examiners on-demand",
        ],
        "social_proof": "Built to satisfy FFIEC CAT, SOC 2 Type II, and DORA technical requirements",
        "cta_primary": "Book a risk exposure assessment (no obligation, 30 minutes)",
        "cta_secondary": "See the FFIEC compliance dashboard live",
    },
    "enterprise_technology": {
        "label": "Enterprise Technology",
        "icp": "CISOs, VP Engineering, Head of Platform Security at Series C+ tech companies",
        "pain_points": [
            "CI/CD pipeline compromise enabling supply chain attacks at scale",
            "Cloud misconfiguration exposure growing faster than security headcount",
            "Secrets sprawl across repos, containers, and ephemeral environments",
            "Compliance overhead consuming 30%+ of engineering security cycles",
        ],
        "urgency_triggers": [
            "Recent supply chain incident at competitor (board asking hard questions)",
            "SOC 2 audit scheduled in next 90 days",
            "Series D / IPO requiring institutional-grade security posture",
            "Customer enterprise deal blocked by security questionnaire failure",
        ],
        "value_props": [
            "Continuous pipeline integrity monitoring — detects poisoned builds in < 60s",
            "Automated cloud posture management across AWS, GCP, Azure simultaneously",
            "Secrets detection and rotation with zero-touch developer workflow",
            "SOC 2 evidence automation — cut audit prep from 6 weeks to 3 days",
        ],
        "social_proof": "Integrated with GitHub, GitLab, Terraform, and the OWASP DevSecOps maturity model",
        "cta_primary": "Schedule a pipeline security walkthrough (your stack, live demo)",
        "cta_secondary": "Get our DevSecOps maturity assessment checklist",
    },
}

# ── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class EmailVariant:
    variant: str          # "A" or "B"
    subject: str
    body: str


@dataclass
class FollowUpStep:
    day: int
    channel: str          # "email" | "linkedin" | "phone"
    subject: str
    body: str


@dataclass
class LinkedInMessage:
    connection_request: str
    follow_up_dm: str


@dataclass
class VerticalSequence:
    vertical_key: str
    vertical_label: str
    icp: str
    cold_email_variants: list[EmailVariant]
    follow_up_sequence: list[FollowUpStep]
    linkedin: LinkedInMessage
    kpis: dict[str, str]


@dataclass
class SalesRun:
    run_utc: str
    total_verticals: int
    output_dir: str
    sequences: list[VerticalSequence] = field(default_factory=list)


# ── Copy Generation ───────────────────────────────────────────────────────────

def build_cold_email_variants(vk: str, v: dict) -> list[EmailVariant]:
    pain = v["pain_points"][0]
    trigger = v["urgency_triggers"][0]
    prop_a = v["value_props"][0]
    prop_b = v["value_props"][2]
    cta = v["cta_primary"]

    variant_a = EmailVariant(
        variant="A",
        subject=f"[{v['label']}] The compliance gap your next audit will find",
        body=f"""{{{{first_name}}}},

Most {v['label'].lower()} leaders I speak with say the same thing: {pain}.

The problem isn't awareness — it's that your current stack wasn't built to surface that risk automatically.

ClearGlassInc Artemis was. {prop_a}.

{v['social_proof']}.

I'd like to show you a 20-minute live view of what your exposure looks like right now — no slides, just your threat surface.

{cta}?

— {{{{sender_name}}}}
ClearGlassInc | Clarity Is Power
www.clearglassinc.com
""",
    )

    variant_b = EmailVariant(
        variant="B",
        subject=f"Quick question about your {['Q3', 'Q4', 'Q1'][hash(vk) % 3]} security posture",
        body=f"""{{{{first_name}}}},

{trigger} — which means your board is probably asking tougher questions than they were 90 days ago.

Here's what we consistently find when we run a posture review for organizations in your position: {prop_b}.

ClearGlassInc Artemis closes that gap autonomously — no new headcount, no rip-and-replace.

Worth 20 minutes to see it on your environment?

{cta}.

— {{{{sender_name}}}}
ClearGlassInc | www.clearglassinc.com
""",
    )

    return [variant_a, variant_b]


def build_follow_up_sequence(v: dict) -> list[FollowUpStep]:
    pain_b = v["pain_points"][1]
    prop_c = v["value_props"][2]
    cta_sec = v["cta_secondary"]
    cta_pri = v["cta_primary"]

    return [
        FollowUpStep(
            day=3,
            channel="email",
            subject="One number that usually surprises {{first_name}}",
            body=f"""{{{{first_name}}}},

Sent a note 3 days ago — wanted to add one data point before you close the loop.

Organizations in your vertical average 21 days of attacker dwell time before detection. ClearGlassInc Artemis customers detect in under 4 hours.

That gap is the difference between a contained incident and a regulatory headline.

{cta_sec} — takes 5 minutes, no commitment.

— {{{{sender_name}}}}
""",
        ),
        FollowUpStep(
            day=7,
            channel="linkedin",
            subject="LinkedIn follow-up (Day 7)",
            body=f"""Hi {{{{first_name}}}},

Reached out by email last week — dropping a quick note here in case that's a better channel.

We've been helping {v['label'].lower()} teams solve {pain_b.lower()} — without adding headcount or replacing existing tooling.

Happy to send a 2-page brief if that's useful, or jump on a 15-minute call whenever your schedule opens up.

Best,
{{{{sender_name}}}}
""",
        ),
        FollowUpStep(
            day=14,
            channel="email",
            subject="Closing the loop, {{first_name}}",
            body=f"""{{{{first_name}}}},

I'll keep this short — following up one last time before I close out my outreach to you.

If {prop_c} isn't on your radar right now, no problem — timing matters.

But if it is, I'd hate for you to navigate that without seeing what Artemis can do.

{cta_pri}? I'll send a calendar link, takes 20 minutes.

Either way — appreciate your time, and hope to connect when the moment is right.

— {{{{sender_name}}}}
ClearGlassInc | www.clearglassinc.com
""",
        ),
        FollowUpStep(
            day=30,
            channel="email",
            subject="[Re-engaging] New capability relevant to {{company_name}}",
            body=f"""{{{{first_name}}}},

Reaching back out — we recently released a capability directly relevant to {v['label'].lower()} teams: {v['value_props'][3]}.

Given what your organization is navigating, I thought it was worth a quick note.

If now is a better time to connect, {cta_pri}.

— {{{{sender_name}}}}
ClearGlassInc
""",
        ),
    ]


def build_linkedin(v: dict) -> LinkedInMessage:
    prop = v["value_props"][0]

    first_pain_word = v["pain_points"][0].split()[0]

    return LinkedInMessage(
        connection_request=(
            f"Hi {{{{first_name}}}}, I work with {v['label'].lower()} teams on "
            f"{first_pain_word} risk — we've built something that addresses "
            f"this without adding headcount. Would value connecting."
        ),
        follow_up_dm=(
            f"Thanks for connecting, {{{{first_name}}}}.\n\n"
            f"Quick context on why I reached out: {prop}.\n\n"
            f"We built ClearGlassInc Artemis specifically for organizations "
            f"in your position — {v['social_proof']}.\n\n"
            f"Worth a 15-minute conversation? Happy to send a brief first "
            f"if you'd prefer to review before committing time.\n\n"
            f"— {{{{sender_name}}}}"
        ),
    )


def build_kpis(v: dict) -> dict[str, str]:
    return {
        "target_reply_rate": "8–12%",
        "target_meeting_book_rate": "3–5% of cold touches",
        "target_pipeline_value_per_deal": "$150,000–$500,000 ACV",
        "sequence_length_days": "30",
        "ab_test_metric": "subject line open rate (variant A vs B, minimum 50 sends each)",
        "follow_up_channels": "email (D3, D14, D30) + LinkedIn (D7)",
        "icp_qualifier": v["icp"],
        "disqualifier": "SMB < 500 employees, non-regulated industry, no active compliance obligation",
    }


# ── Sequence Builder ──────────────────────────────────────────────────────────

def build_vertical_sequence(vk: str, v: dict) -> VerticalSequence:
    return VerticalSequence(
        vertical_key=vk,
        vertical_label=v["label"],
        icp=v["icp"],
        cold_email_variants=build_cold_email_variants(vk, v),
        follow_up_sequence=build_follow_up_sequence(v),
        linkedin=build_linkedin(v),
        kpis=build_kpis(v),
    )


# ── Output Writers ────────────────────────────────────────────────────────────

def _md_email(e: EmailVariant) -> str:
    return (
        f"### Variant {e.variant}\n\n"
        f"**Subject:** `{e.subject}`\n\n"
        f"```\n{e.body.strip()}\n```\n"
    )


def _md_followup(f: FollowUpStep) -> str:
    return (
        f"#### Day {f.day} — {f.channel.upper()}\n\n"
        f"**Subject / Hook:** `{f.subject}`\n\n"
        f"```\n{f.body.strip()}\n```\n"
    )


def write_markdown(run: SalesRun) -> Path:
    now_slug = run.run_utc.replace(":", "").replace("-", "")[:15]
    md_path = OUTPUT_DIR / f"sales_sequences_{now_slug}.md"

    lines: list[str] = [
        "# ClearGlassInc — Sales Outreach Sequences\n",
        f"**Generated:** {run.run_utc}  \n",
        f"**Verticals covered:** {run.total_verticals}  \n",
        f"**Output directory:** `{run.output_dir}`\n\n",
        "---\n",
    ]

    for seq in run.sequences:
        lines.append(f"\n## {seq.vertical_label}\n")
        lines.append(f"**ICP:** {seq.icp}\n\n")

        lines.append("### Cold Email — A/B Variants\n")
        for variant in seq.cold_email_variants:
            lines.append(_md_email(variant))

        lines.append("\n### Follow-Up Sequence\n")
        for step in seq.follow_up_sequence:
            lines.append(_md_followup(step))

        lines.append("\n### LinkedIn Outreach\n")
        lines.append("**Connection Request:**\n")
        lines.append(f"```\n{seq.linkedin.connection_request.strip()}\n```\n\n")
        lines.append("**Follow-Up DM (after acceptance):**\n")
        lines.append(f"```\n{seq.linkedin.follow_up_dm.strip()}\n```\n\n")

        lines.append("### KPI Targets\n\n")
        lines.append("| Metric | Target |\n|---|---|\n")
        for k, v in seq.kpis.items():
            lines.append(f"| {k.replace('_', ' ').title()} | {v} |\n")
        lines.append("\n---\n")

    md_path.write_text("".join(lines), encoding="utf-8")
    return md_path


def write_json(run: SalesRun) -> Path:
    now_slug = run.run_utc.replace(":", "").replace("-", "")[:15]
    json_path = OUTPUT_DIR / f"sales_sequences_{now_slug}.json"

    def serialise(obj):
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)
        raise TypeError(f"Not serialisable: {type(obj)}")

    json_path.write_text(
        json.dumps(asdict(run), indent=2, default=str),
        encoding="utf-8",
    )
    return json_path


def write_latest_symlinks(md_path: Path, json_path: Path) -> None:
    for dest, src in [
        (OUTPUT_DIR / "latest.md", md_path),
        (OUTPUT_DIR / "latest.json", json_path),
    ]:
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


# ── Entry Point ───────────────────────────────────────────────────────────────

def main() -> SalesRun:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    sequences = [build_vertical_sequence(k, v) for k, v in VERTICALS.items()]

    run = SalesRun(
        run_utc=now,
        total_verticals=len(sequences),
        output_dir=str(OUTPUT_DIR.relative_to(ROOT)),
        sequences=sequences,
    )

    md_path = write_markdown(run)
    json_path = write_json(run)
    write_latest_symlinks(md_path, json_path)

    print(f"[sales-bot] Run complete: {now}")
    print(f"  Verticals: {run.total_verticals}")
    print(f"  Markdown : {md_path.relative_to(ROOT)}")
    print(f"  JSON     : {json_path.relative_to(ROOT)}")

    return run


if __name__ == "__main__":
    main()
