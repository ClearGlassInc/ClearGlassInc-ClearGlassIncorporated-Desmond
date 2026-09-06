# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "marketing" / "output"
ARCHIVE_DIR = OUTPUT_DIR / "archive"

SITE_URL = "https://www.clearglassinc.com/"
PRODUCT_URLS = {
    "home": SITE_URL,
    "artemis": "https://www.clearglassinc.com/artemis.html",
    "guardian": "https://www.clearglassinc.com/guardian.html",
}

PILLARS: dict[str, dict[str, str]] = {
    "brand": {
        "headline": "Clarity is power.",
        "angle": "Position ClearGlass as the premium public-facing brand for transparent intelligence, disciplined execution, and long-horizon infrastructure thinking.",
        "cta": "Direct decision-makers to the homepage and founder contact path.",
    },
    "artemis": {
        "headline": "Artemis VI turns glass into an intelligence surface.",
        "angle": "Show how the flagship platform connects smart glass, secure computation, and digital-twin operations into one coherent system story.",
        "cta": "Route visitors from the homepage to Artemis VI for roadmap review.",
    },
    "guardian": {
        "headline": "Guardian sharpens operational control.",
        "angle": "Focus on executive-grade hardening, AI-assisted defense, and a clean deployment path anchored to the Guardian download page.",
        "cta": "Push qualified traffic to Guardian for product review and download intent.",
    },
    "founder": {
        "headline": "Leadership built for trust and execution.",
        "angle": "Elevate the founder profile as the operating center for product direction, systems thinking, and strategic credibility.",
        "cta": "Route collaborators and investors to the founder and contact sections on the homepage.",
    },
}

DEFAULT_ROTATION = ["brand", "artemis", "guardian", "founder"]


@dataclass(frozen=True)
class MarketingStatus:
    run_utc: str
    pillar: str
    facebook_enabled: bool
    facebook_ready: bool
    page_id_present: bool
    token_present: bool
    output_dir: str


def choose_pillar() -> str:
    forced = os.getenv("FORCE_PILLAR", "").strip().lower()
    if forced in PILLARS:
        return forced

    day_index = datetime.now(timezone.utc).timetuple().tm_yday % len(DEFAULT_ROTATION)
    return DEFAULT_ROTATION[day_index]


def build_status(pillar: str) -> MarketingStatus:
    facebook_enabled = os.getenv("FACEBOOK_ENABLED", "true").strip().lower() == "true"
    page_id_present = bool(os.getenv("FACEBOOK_PAGE_ID", "").strip())
    token_present = bool(os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip())
    facebook_ready = facebook_enabled and page_id_present and token_present

    return MarketingStatus(
        run_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        pillar=pillar,
        facebook_enabled=facebook_enabled,
        facebook_ready=facebook_ready,
        page_id_present=page_id_present,
        token_present=token_present,
        output_dir=str(OUTPUT_DIR.relative_to(ROOT)),
    )


def build_markdown(status: MarketingStatus) -> str:
    pillar_data = PILLARS[status.pillar]
    facebook_line = (
        "Ready for publish" if status.facebook_ready else "Skipped publish; secrets missing or publish disabled"
    )

    return "\n".join(
        [
            "# ClearGlass Marketing Bot Output",
            "",
            f"- Run (UTC): {status.run_utc}",
            f"- Content pillar: {status.pillar}",
            f"- Facebook status: {facebook_line}",
            "",
            "## Core message",
            pillar_data["headline"],
            "",
            "## Strategic angle",
            pillar_data["angle"],
            "",
            "## Primary CTA",
            pillar_data["cta"],
            "",
            "## Route map",
            f"- Home: {PRODUCT_URLS['home']}",
            f"- Artemis VI: {PRODUCT_URLS['artemis']}",
            f"- Guardian: {PRODUCT_URLS['guardian']}",
            "",
            "## Operator notes",
            "- Keep copy premium, direct, and brand-consistent.",
            "- Do not claim platform capabilities that are not visible on the public site.",
            "- Preserve GitHub Pages URLs until a verified custom domain is live.",
        ]
    ) + "\n"


def write_outputs(status: MarketingStatus) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    markdown = build_markdown(status)
    json_payload = json.dumps(asdict(status), indent=2) + "\n"

    latest_md = OUTPUT_DIR / "latest.md"
    latest_json = OUTPUT_DIR / "latest.json"
    archive_stamp = status.run_utc.replace("+00:00", "Z").replace(":", "")
    archive_md = ARCHIVE_DIR / f"{archive_stamp}.md"

    latest_md.write_text(markdown, encoding="utf-8")
    latest_json.write_text(json_payload, encoding="utf-8")
    archive_md.write_text(markdown, encoding="utf-8")


if __name__ == "__main__":
    selected_pillar = choose_pillar()
    current_status = build_status(selected_pillar)
    write_outputs(current_status)
    print(f"Marketing output generated for pillar: {selected_pillar}")
    print(f"Output directory: {OUTPUT_DIR}")
