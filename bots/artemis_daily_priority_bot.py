# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "daily_priority"
ARCHIVE_DIR = OUTPUT_DIR / "archive"


@dataclass(frozen=True)
class PriorityItem:
    priority: str
    domain: str
    specific_action: str
    time_block: str
    success_metric: str


@dataclass(frozen=True)
class DailyBrief:
    run_utc: str
    date: str
    outcome_prompt: str
    strategic_priorities: list[PriorityItem]
    yesterday_review_prompt: str
    intelligence_brief: list[str]
    mental_priming: list[str]
    non_negotiables: list[str]
    edge_case_prep: list[str]
    mantra: str


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def build_daily_brief() -> DailyBrief:
    return DailyBrief(
        run_utc=_now_utc().isoformat(),
        date=_now_utc().date().isoformat(),
        outcome_prompt="Good morning. ONE outcome for today?",
        strategic_priorities=[
            PriorityItem("P0", "AI Automation", "Implement self-healing test tool (e.g. TestBooster.ai)", "8-10am", "1 workflow automated, tested"),
            PriorityItem("P1", "Cybersecurity", "Patch PAN-OS & review supply-chain risks", "10-11am", "Zero critical vulns open"),
            PriorityItem("P2", "ClearGlassInc/Brand", "LinkedIn post on AI-cyber edge", "2-2:30pm", "5+ engagements"),
        ],
        yesterday_review_prompt=(
            "What were your 3 key commitments? Rate ✓/~ /✗. Blockers & fixes? Carry over P0."
        ),
        intelligence_brief=[
            "AI: Self-healing tools dominant (TestBooster, Applitools).",
            "Cyber: PAN-OS zero-day exploited; supply-chain breaches via vendors.",
            "Quantum: Cryoelectronics milestone for scalable ion traps.",
        ],
        mental_priming=[
            "Box breathe 2min.",
            "5 gratitudes 3min.",
            "Visualize P0 flawless 5min.",
        ],
        non_negotiables=[
            "Complete P0 by 10am.",
            "90min deep AI work.",
            "No phone first hour.",
        ],
        edge_case_prep=[
            "Phone in another room.",
            "Snacks ready.",
            "Move P2 if overloaded.",
        ],
        mantra="I own this day. My P0 tasks get done. Let's execute.",
    )


def _serialize(brief: DailyBrief) -> dict:
    payload = asdict(brief)
    payload["strategic_priorities"] = [asdict(item) for item in brief.strategic_priorities]
    return payload


def build_markdown(brief: DailyBrief) -> str:
    lines = [
        "# ClearGlassInc Artemis Daily Priority Brief",
        "",
        f"- Generated (UTC): {brief.run_utc}",
        f"- Date: {brief.date}",
        "",
        f"## {brief.outcome_prompt}",
        "",
        "## TODAY'S STRATEGIC PRIORITY MATRIX",
        "| Priority | Domain | Specific Action | Time Block | Success Metric |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in brief.strategic_priorities:
        lines.append(
            f"| {row.priority} | {row.domain} | {row.specific_action} | {row.time_block} | {row.success_metric} |"
        )

    lines += [
        "",
        "## YESTERDAY'S PLEDGE REVIEW",
        brief.yesterday_review_prompt,
        "",
        "## CRITICAL INTELLIGENCE BRIEF",
    ]
    lines.extend([f"- {item}" for item in brief.intelligence_brief])

    lines += ["", "## MENTAL PRIMING PROTOCOL"]
    lines.extend([f"- {item}" for item in brief.mental_priming])

    lines += ["", "## TODAY'S NON-NEGOTIABLES"]
    lines.extend([f"- {item}" for item in brief.non_negotiables])

    lines += ["", "## EDGE CASE PREP"]
    lines.extend([f"- {item}" for item in brief.edge_case_prep])

    lines += ["", f"**REPEAT:** {brief.mantra}", ""]
    return "\n".join(lines)


def write_outputs(brief: DailyBrief) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    stamp = brief.run_utc.replace("+00:00", "Z").replace(":", "")
    markdown = build_markdown(brief)
    payload = json.dumps(_serialize(brief), indent=2) + "\n"

    (OUTPUT_DIR / "latest.md").write_text(markdown, encoding="utf-8")
    (OUTPUT_DIR / "latest.json").write_text(payload, encoding="utf-8")
    (ARCHIVE_DIR / f"{stamp}.md").write_text(markdown, encoding="utf-8")
    (ARCHIVE_DIR / f"{stamp}.json").write_text(payload, encoding="utf-8")


def should_publish() -> bool:
    return os.getenv("ARTEMIS_DAILY_PRIORITY_ENABLED", "true").strip().lower() == "true"


if __name__ == "__main__":
    if not should_publish():
        print("Daily priority brief generation disabled via ARTEMIS_DAILY_PRIORITY_ENABLED=false")
    else:
        brief = build_daily_brief()
        write_outputs(brief)
        print(f"Daily priority brief generated: {brief.run_utc}")
        print(f"Output directory: {OUTPUT_DIR}")
