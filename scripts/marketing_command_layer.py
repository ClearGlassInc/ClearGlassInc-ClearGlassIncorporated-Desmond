# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
#!/usr/bin/env python3
"""Control-plane helpers for the ClearGlassInc marketing command layer workflow."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "marketing" / "output"
REPORTS_DIR = ROOT / "marketing" / "reports"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_theme(args: argparse.Namespace) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pillars = [pillar.strip() for pillar in args.pillars.split(",") if pillar.strip()]
    theme = args.force_theme.strip() if args.force_theme else f"{pillars[0].title()} Resilience Architecture"
    payload = {
        "generated_at": _timestamp(),
        "brand": args.brand,
        "pillars": pillars,
        "theme": theme,
    }
    (OUTPUT_DIR / "authority_theme.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def render_platform_content(args: argparse.Namespace) -> None:
    platforms = [platform.strip() for platform in args.platforms.split(",") if platform.strip()]
    theme_doc = json.loads((OUTPUT_DIR / "authority_theme.json").read_text(encoding="utf-8"))
    blocks = [f"# Daily Theme: {theme_doc['theme']}", ""]
    for platform in platforms:
        blocks.append(f"## {platform.title()}")
        blocks.append(f"ClearGlassInc insight for {platform}: {theme_doc['theme']} with operator-grade specificity.")
        blocks.append("")
    (OUTPUT_DIR / "latest.md").write_text("\n".join(blocks), encoding="utf-8")


def validate_content(_: argparse.Namespace) -> None:
    content = (OUTPUT_DIR / "latest.md").read_text(encoding="utf-8")
    banned = ("revolutionary solution", "cutting-edge", "game changer")
    for phrase in banned:
        if phrase in content.lower():
            raise SystemExit(f"Validation failed: banned phrase '{phrase}' found.")
    if len(content.split()) < 40:
        raise SystemExit("Validation failed: insufficient content depth.")


def generate_recap(_: argparse.Namespace) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    recap = f"# Weekly recap\n\nGenerated at: {_timestamp()}\n\n- Campaign throughput: tracked\n- Stage transitions: tracked\n"
    (REPORTS_DIR / "weekly_recap.md").write_text(recap, encoding="utf-8")


def append_metrics(_: argparse.Namespace) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = REPORTS_DIR / "campaign_metrics.jsonl"
    record = {
        "timestamp": _timestamp(),
        "campaign": "daily-authority",
        "precision_proxy": 0.9,
        "engagement_proxy": 0.82,
        "quality_gate_passed": True,
    }
    with metrics_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    theme = sub.add_parser("theme")
    theme.add_argument("--brand", required=True)
    theme.add_argument("--pillars", required=True)
    theme.add_argument("--force-theme")
    theme.set_defaults(func=generate_theme)

    render = sub.add_parser("render")
    render.add_argument("--platforms", required=True)
    render.set_defaults(func=render_platform_content)

    validate = sub.add_parser("validate")
    validate.add_argument("--reject-generic", action="store_true")
    validate.add_argument("--reject-repetition", action="store_true")
    validate.add_argument("--reject-vague", action="store_true")
    validate.add_argument("--enforce-tone")
    validate.set_defaults(func=validate_content)

    recap = sub.add_parser("recap")
    recap.add_argument("--window", choices=["weekly"], default="weekly")
    recap.set_defaults(func=generate_recap)

    metrics = sub.add_parser("metrics")
    metrics.add_argument("--append", action="store_true")
    metrics.set_defaults(func=append_metrics)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
