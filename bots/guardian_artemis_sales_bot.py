# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""
ClearGlassInc Guardian & Artemis Sales Bot

Generates audience-tuned sales narratives for Project Guardian (defensive
intelligence shield) and Project Artemis (offensive / predictive execution
engine) using the "Sales Brain" system prompt in
`prompts/sales_guardian_artemis_system_prompt.md`.

For each audience (investors, enterprise, government) it produces:
  1. A long-form sales pitch (2-4 minute read)
  2. A 30-second elevator pitch
  3. A one-paragraph investor / partner hook
  4. Tagline options for Guardian + Artemis

Outputs Markdown + JSON to marketing/output/sales_guardian_artemis/ so the
content engine and CRM exporters can consume the latest run.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "prompts" / "sales_guardian_artemis_system_prompt.md"
OUTPUT_DIR = ROOT / "marketing" / "output" / "sales_guardian_artemis"
ARCHIVE_DIR = OUTPUT_DIR / "archive"


# ── Audience Profiles ─────────────────────────────────────────────────────────

AUDIENCES: dict[str, dict] = {
    "investors": {
        "label": "Investors",
        "decision_maker": "GPs, principals, and corp-dev leads at funds investing in AI, cyber, and dual-use defense tech",
        "hook": (
            "Cybersecurity hasn't been hard in a decade — it's been *unwinnable*. "
            "The attack surface compounds; the defender headcount doesn't. "
            "The only category left with venture-scale returns is the one that breaks that equation."
        ),
        "problem": (
            "Enterprises now operate inside a permanent intelligence deficit. "
            "Adversaries automate; defenders schedule meetings. The average dwell time "
            "is still measured in weeks, the average SOC is still staffed in tens, and "
            "the average board is still briefed in quarters. That math doesn't survive "
            "the next decade of AI-powered offense."
        ),
        "value": [
            "Guardian collapses detection-to-response from days to seconds — a 100x defensive multiplier with zero added headcount.",
            "Artemis turns intelligence into action: it predicts, prioritizes, and executes inside the same loop the adversary is running.",
            "Together they replace a category, not a tool — the same way Palantir replaced consulting and Crowdstrike replaced AV.",
            "AI-native from line one. No legacy SIEM debt, no human-in-the-loop tax, no integration penalty.",
        ],
        "objections": {
            "Market timing": "Federal AI procurement just unlocked. Every Fortune 500 CISO budget reorganized around autonomy in the last 18 months.",
            "Moat": "Proprietary signal fusion across cyber + legal + intelligence layers — none of the incumbents own all three.",
            "Capital efficiency": "Bot-led GTM. Content, outreach, and ops are already automated inside the company.",
        },
        "close": (
            "We are not raising to *build* — we are raising to *capture*. "
            "The pilots that close in the next two quarters compound into the category-defining position."
        ),
        "cta": "Open a data room conversation — 30 minutes, founder + architecture deep-dive.",
    },
    "enterprise": {
        "label": "Enterprise & Financial Institutions",
        "decision_maker": "CISOs, CROs, Heads of Information Security, VPs of Platform Security",
        "hook": (
            "Your SOC is not understaffed. It is *under-architected*. "
            "Throwing analysts at a probabilistic attack surface is a budget line, not a strategy."
        ),
        "problem": (
            "The cost of a breach now lands in three places simultaneously: regulatory capital, "
            "cyber insurance premium, and brand equity. None of those bills are paid by a 21-day "
            "mean-time-to-detect. Your auditors know it, your insurers know it, and the next "
            "examiner to walk in the door will price it."
        ),
        "value": [
            "Guardian gives you a continuously-evidenced compliance posture — SOC 2, FFIEC, DORA, ISO 27001 — exportable to examiners in one click.",
            "Artemis autonomously correlates and acts on threat signal across cloud, identity, endpoint, and vendor surface — 90% alert-noise reduction, sub-4-hour MTTD.",
            "Zero rip-and-replace. API-first. Integrates with your existing SIEM, EDR, IAM, and ticketing stack.",
            "ROI compounds: every quarter the model is in your environment, MTTD drops, false positives drop, audit prep drops, and analyst attrition drops.",
        ],
        "objections": {
            "Complexity": "Fully abstracted. Your team operates a dashboard; the autonomy runs underneath.",
            "Integration": "API-first and modular. We deploy in days, not quarters.",
            "Security": "Zero-trust architecture, customer-tenant isolation, BYO-key, full audit trail.",
            "ROI": "Customers recover platform cost inside the first audit cycle.",
        },
        "close": (
            "The cost of waiting is exponential. The next examination, the next ransomware "
            "headline, the next insurance renewal will not move at your timeline."
        ),
        "cta": "Book a 30-minute risk exposure assessment — your environment, no slides.",
    },
    "government": {
        "label": "Government & Defense",
        "decision_maker": "Deputy CIOs, CISOs, Procurement Officers, Program Managers at federal agencies, primes, and allied governments",
        "hook": (
            "Adversaries are now operating at machine speed inside the FCEB perimeter. "
            "We are responding at human speed. That asymmetry is a national-security failure mode, "
            "and no amount of additional staffing closes it."
        ),
        "problem": (
            "Legacy enclave architectures, manual triage, and procurement cycles measured in years "
            "have produced a structural intelligence gap. Every IG report, every CISA advisory, and "
            "every congressional hearing for the last 36 months has named the same root cause: "
            "the defender cannot see, prioritize, and act inside the adversary's decision loop."
        ),
        "value": [
            "Guardian is a continuous-monitoring intelligence shield aligned to NIST SP 800-207 zero-trust, FedRAMP, and CMMC 2.0 — designed for IG-grade auditability from day one.",
            "Artemis is an autonomous decision and execution engine: it ingests classified-grade signal, prioritizes by mission impact, and acts inside policy-bound guardrails.",
            "Fusion of cyber, legal, and intelligence layers in a single sovereign stack — no foreign data residency, no third-party telemetry leakage.",
            "Deployable inside air-gapped, IL5, and IL6 enclaves. Operates without phone-home dependency.",
        ],
        "objections": {
            "Procurement vehicle": "Accessible via GSA, OTA, SBIR Phase III, and prime subcontract paths.",
            "Classification posture": "Architecture is classification-aware; deployment patterns exist for IL4 through IL6.",
            "Sovereignty": "100% US-based infrastructure, US-cleared engineering, ITAR-aware data handling.",
            "Mission risk": "Policy-bound autonomy — every action is auditable, reversible, and constrained by mission rules of engagement.",
        },
        "close": (
            "The adversary is not waiting for the next budget cycle. Early-adopter agencies will "
            "set the doctrine the rest of the government inherits."
        ),
        "cta": "Request a classified-environment architecture briefing — 30 minutes, cleared personnel.",
    },
}


GUARDIAN_TAGLINES = [
    "Guardian: the intelligence shield that never sleeps.",
    "Guardian: see everything. Miss nothing. Act first.",
    "Guardian: zero-trust, machine-speed, mission-grade.",
    "Guardian: continuous evidence, compounding defense.",
]

ARTEMIS_TAGLINES = [
    "Artemis: the autonomous execution engine for the next decade of cyber.",
    "Artemis: predict. Decide. Act. Inside the adversary's loop.",
    "Artemis: intelligence that closes the gap between signal and action.",
    "Artemis: machine-speed strategy, human-grade judgment.",
]


# ── Data Models ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AudienceNarrative:
    audience_key: str
    audience_label: str
    decision_maker: str
    long_pitch: str
    elevator_pitch: str
    investor_hook: str
    guardian_taglines: list[str]
    artemis_taglines: list[str]


@dataclass
class SalesBrainRun:
    run_utc: str
    prompt_source: str
    total_audiences: int
    output_dir: str
    narratives: list[AudienceNarrative] = field(default_factory=list)


# ── Narrative Builders ────────────────────────────────────────────────────────

def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def build_long_pitch(audience_key: str, a: dict) -> str:
    objections = "\n".join(f"- **{k}** — {v}" for k, v in a["objections"].items())
    return (
        f"## Hook\n{a['hook']}\n\n"
        f"## The Problem\n{a['problem']}\n\n"
        "## The Solution\n"
        "**Project Guardian** is the defensive intelligence shield — continuous "
        "monitoring, AI-driven detection, zero-trust enforcement, and audit-grade "
        "evidence collection across every layer of the environment.\n\n"
        "**Project Artemis** is the offensive / predictive execution engine — "
        "autonomous correlation, mission-aware prioritization, and policy-bound "
        "action inside the same loop the adversary is running.\n\n"
        f"## Why This Wins for {a['label']}\n{_bullets(a['value'])}\n\n"
        f"## Objection Handling\n{objections}\n\n"
        f"## The Close\n{a['close']}\n\n"
        f"**CTA:** {a['cta']}"
    )


def build_elevator_pitch(a: dict) -> str:
    return (
        f"Most {a['label'].lower()} leaders are running 2020 architectures against "
        f"2026 adversaries. ClearGlassInc built two systems to close that gap. "
        f"Guardian is the autonomous intelligence shield — it sees, evidences, and "
        f"defends in real time. Artemis is the predictive execution engine — it "
        f"prioritizes and acts inside the adversary's decision loop. Together they "
        f"replace a category, not a tool. {a['cta']}"
    )


def build_investor_hook(a: dict) -> str:
    return (
        "ClearGlassInc is building the AI-native defense + execution stack the "
        "next decade of cybersecurity will be measured against. Guardian is the "
        "intelligence shield; Artemis is the autonomous execution engine. "
        "Together they collapse detection-to-response from days to seconds, fuse "
        "cyber, legal, and intelligence signal into a single sovereign platform, "
        "and replace categories — not products — across enterprise, financial, "
        f"and government markets. We are positioned to capture the {a['label'].lower()} "
        "buyer at the exact procurement inflection point that defines the next "
        "decade of cyber spend."
    )


def build_narrative(audience_key: str, a: dict) -> AudienceNarrative:
    return AudienceNarrative(
        audience_key=audience_key,
        audience_label=a["label"],
        decision_maker=a["decision_maker"],
        long_pitch=build_long_pitch(audience_key, a),
        elevator_pitch=build_elevator_pitch(a),
        investor_hook=build_investor_hook(a),
        guardian_taglines=list(GUARDIAN_TAGLINES),
        artemis_taglines=list(ARTEMIS_TAGLINES),
    )


# ── Output Writers ────────────────────────────────────────────────────────────

def build_markdown(run: SalesBrainRun) -> str:
    lines: list[str] = [
        "# ClearGlassInc — Guardian & Artemis Sales Brain Output",
        "",
        f"- Generated (UTC): {run.run_utc}",
        f"- Prompt source: `{run.prompt_source}`",
        f"- Audiences covered: {run.total_audiences}",
        "",
        "---",
    ]

    for n in run.narratives:
        lines += [
            "",
            f"## {n.audience_label}",
            f"**Decision maker:** {n.decision_maker}",
            "",
            "### Long-Form Pitch (2–4 minute read)",
            n.long_pitch,
            "",
            "### 30-Second Elevator Pitch",
            n.elevator_pitch,
            "",
            "### Investor / Partner Hook (1 paragraph)",
            n.investor_hook,
            "",
            "### Tagline Options",
            "",
            "**Guardian:**",
            _bullets(n.guardian_taglines),
            "",
            "**Artemis:**",
            _bullets(n.artemis_taglines),
            "",
            "---",
        ]

    return "\n".join(lines) + "\n"


def _serialize(run: SalesBrainRun) -> dict:
    payload = asdict(run)
    payload["narratives"] = [asdict(n) for n in run.narratives]
    return payload


def write_outputs(run: SalesBrainRun) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    stamp = run.run_utc.replace("+00:00", "Z").replace(":", "").replace("-", "")[:15]
    markdown = build_markdown(run)
    payload = json.dumps(_serialize(run), indent=2) + "\n"

    latest_md = OUTPUT_DIR / "latest.md"
    latest_json = OUTPUT_DIR / "latest.json"

    latest_md.write_text(markdown, encoding="utf-8")
    latest_json.write_text(payload, encoding="utf-8")
    (ARCHIVE_DIR / f"{stamp}.md").write_text(markdown, encoding="utf-8")
    (ARCHIVE_DIR / f"{stamp}.json").write_text(payload, encoding="utf-8")

    return latest_md, latest_json


# ── Entry Point ───────────────────────────────────────────────────────────────

def build_run() -> SalesBrainRun:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    narratives = [build_narrative(k, v) for k, v in AUDIENCES.items()]
    return SalesBrainRun(
        run_utc=now,
        prompt_source=str(PROMPT_PATH.relative_to(ROOT)),
        total_audiences=len(narratives),
        output_dir=str(OUTPUT_DIR.relative_to(ROOT)),
        narratives=narratives,
    )


def main() -> SalesBrainRun:
    run = build_run()
    md_path, json_path = write_outputs(run)
    print(f"[guardian-artemis-sales-bot] Run complete: {run.run_utc}")
    print(f"  Audiences: {run.total_audiences}")
    print(f"  Markdown : {md_path.relative_to(ROOT)}")
    print(f"  JSON     : {json_path.relative_to(ROOT)}")
    return run


if __name__ == "__main__":
    main()
