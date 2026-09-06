# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Priority Matrix Bot.

Generates a daily execution brief from a configurable priority matrix.

The bot is data-driven: it ships with a sensible default matrix but reads an
optional JSON override from ``operations/priority_matrix/config.json`` so the
day's priorities can be updated without editing code. Outputs are written as
both Markdown (human review) and JSON (downstream automation), with a rolling
``latest.*`` plus a timestamped archive copy.

Usage:
    python -m bots.priority_matrix_bot            # render + write outputs
    python -m bots.priority_matrix_bot --print    # render to stdout only
    python -m bots.priority_matrix_bot --config path/to/config.json
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "priority_matrix"
ARCHIVE_DIR = OUTPUT_DIR / "archive"
CONFIG_PATH = OUTPUT_DIR / "config.json"


@dataclass(frozen=True)
class PriorityItem:
    priority: str
    domain: str
    action: str
    time: str
    metric: str


@dataclass(frozen=True)
class PriorityBrief:
    run_utc: str
    date: str
    greeting: str
    matrix: list[PriorityItem]
    yesterday_review: str
    intelligence: list[str]
    priming: list[str]
    non_negotiables: list[str]
    mantra: str
    extras: dict = field(default_factory=dict)


# --- Default matrix (owner's standing plan) -------------------------------
DEFAULT_CONFIG: dict = {
    "greeting": "Good morning. ONE outcome that makes today a win?",
    "matrix": [
        {
            "priority": "P0",
            "domain": "AI Automation",
            "action": "Finish core workflow script",
            "time": "8-10am",
            "metric": "Deploy-ready code",
        },
        {
            "priority": "P1",
            "domain": "Cybersecurity",
            "action": "Audit ClearGlassInc endpoint",
            "time": "10:30-11:30",
            "metric": "Report complete",
        },
        {
            "priority": "P2",
            "domain": "Personal Brand",
            "action": "1 LinkedIn post",
            "time": "1pm",
            "metric": "5+ engagements",
        },
    ],
    "yesterday_review": "Report your 3 pledges + completion.",
    "intelligence": [
        "New Grok updates for automation.",
        "Monitor CVE spikes.",
    ],
    "priming": [
        "Box breathe 2min.",
        "5 gratitudes.",
        "Visualize P0 win.",
    ],
    "non_negotiables": [
        "P0 done by 10am.",
        "90min deep work.",
        "Hydrate first hour.",
    ],
    "mantra": "I own this day. My P0 tasks get done. Let's execute.",
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def load_config(config_path: Path | None = None) -> dict:
    """Merge the optional JSON override on top of the default config."""
    path = config_path if config_path is not None else CONFIG_PATH
    config = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    if path and path.exists():
        override = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(override, dict):
            raise ValueError(f"Config at {path} must be a JSON object")
        config.update(override)
    return config


def build_brief(config: dict | None = None) -> PriorityBrief:
    cfg = config if config is not None else load_config()
    known = {
        "greeting",
        "matrix",
        "yesterday_review",
        "intelligence",
        "priming",
        "non_negotiables",
        "mantra",
    }
    now = _now_utc()
    return PriorityBrief(
        run_utc=now.isoformat(),
        date=now.date().isoformat(),
        greeting=cfg["greeting"],
        matrix=[PriorityItem(**item) for item in cfg["matrix"]],
        yesterday_review=cfg["yesterday_review"],
        intelligence=list(cfg["intelligence"]),
        priming=list(cfg["priming"]),
        non_negotiables=list(cfg["non_negotiables"]),
        mantra=cfg["mantra"],
        extras={k: v for k, v in cfg.items() if k not in known},
    )


def _serialize(brief: PriorityBrief) -> dict:
    payload = asdict(brief)
    payload["matrix"] = [asdict(item) for item in brief.matrix]
    return payload


def build_markdown(brief: PriorityBrief) -> str:
    lines = [
        "# ClearGlassInc Priority Matrix Brief",
        "",
        f"- Generated (UTC): {brief.run_utc}",
        f"- Date: {brief.date}",
        "",
        f"## {brief.greeting}",
        "",
        "## PRIORITY MATRIX",
        "| Priority | Domain | Action | Time | Metric |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in brief.matrix:
        lines.append(
            f"| {row.priority} | {row.domain} | {row.action} | {row.time} | {row.metric} |"
        )

    lines += ["", "## YESTERDAY REVIEW", brief.yesterday_review, "", "## INTELLIGENCE"]
    lines += [f"- {item}" for item in brief.intelligence]

    lines += ["", "## PRIMING"]
    lines += [f"- {item}" for item in brief.priming]

    lines += ["", "## NON-NEGOTIABLES"]
    lines += [f"- {item}" for item in brief.non_negotiables]

    lines += ["", f"**REPEAT:** {brief.mantra}", ""]
    return "\n".join(lines)


def render_terminal(brief: PriorityBrief) -> str:
    """Compact, color-free render for stdout / Slack / logs."""
    bar = "=" * 60
    out = [bar, f"  PRIORITY MATRIX — {brief.date}", bar, "", brief.greeting, ""]
    for row in brief.matrix:
        out.append(f"  [{row.priority}] {row.domain}: {row.action}")
        out.append(f"        {row.time}  ->  {row.metric}")
    out += ["", f"  Yesterday: {brief.yesterday_review}"]
    out += ["", "  Intelligence:"] + [f"    - {i}" for i in brief.intelligence]
    out += ["", "  Priming:"] + [f"    - {i}" for i in brief.priming]
    out += ["", "  Non-negotiables:"] + [f"    - {i}" for i in brief.non_negotiables]
    out += ["", bar, f"  {brief.mantra}", bar]
    return "\n".join(out)


def write_outputs(brief: PriorityBrief) -> dict[str, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    stamp = brief.run_utc.replace("+00:00", "Z").replace(":", "")
    markdown = build_markdown(brief)
    payload = json.dumps(_serialize(brief), indent=2) + "\n"

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
    return os.getenv("PRIORITY_MATRIX_ENABLED", "true").strip().lower() == "true"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the daily priority matrix brief.")
    parser.add_argument("--config", type=Path, default=None, help="Path to a JSON config override.")
    parser.add_argument("--print", action="store_true", help="Render to stdout, do not write files.")
    args = parser.parse_args(argv)

    if not should_publish():
        print("Priority matrix generation disabled via PRIORITY_MATRIX_ENABLED=false")
        return 0

    brief = build_brief(load_config(args.config))
    print(render_terminal(brief))

    if args.print:
        return 0

    paths = write_outputs(brief)
    print(f"\nWrote: {paths['latest_md']}")
    print(f"Wrote: {paths['latest_json']}")
    print(f"Archived: {paths['archive_md'].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
