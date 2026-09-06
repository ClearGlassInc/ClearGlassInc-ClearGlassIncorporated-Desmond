# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""
ClearGlassInc Content Validator

Reads the latest content bundle and enforces quality gates before the
content is routed to scheduling and publishing. A failed validation
blocks the downstream pipeline and writes a detailed failure report.

Quality gates:
  1. Platform character limits (min / max per platform).
  2. Weak phrase detection — generic language that dilutes authority.
  3. Brand keyword presence — every piece must anchor to ClearGlass.
  4. CTA presence — each platform output must contain a URL.
  5. Repetition guard — rejects hashes seen within the last 30 runs.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "marketing" / "output"
METRICS_DIR = OUTPUT_DIR / "metrics"

PLATFORM_LIMITS: dict[str, dict[str, int]] = {
    "linkedin": {"min": 300, "max": 3000},
    "threads": {"min": 50, "max": 500},
    "x": {"min": 30, "max": 280},
    "email": {"min": 200, "max": 5000},
    "website": {"min": 60, "max": 400},
}

# Phrases that signal generic, low-authority copy.
WEAK_PHRASES: list[str] = [
    "game-changer",
    "revolutionary",
    "cutting-edge",
    "next-gen",
    "synergy",
    "leverage",
    "ecosystem",
    "best-in-class",
    "world-class",
    "industry-leading",
    "innovative solution",
    "transformative",
    "disruptive",
    "paradigm shift",
    "holistic approach",
]

# At least one must appear in every piece of content.
BRAND_KEYWORDS: list[str] = [
    "clearglass",
    "artemis",
    "guardian",
    "cybersecurity",
    "security",
    "intelligence",
]

# Every external-facing platform output must contain a URL pointing to the ClearGlass site.
# Website copy is exempt: it IS the site and updating it doesn't require a self-referential URL.
# Matches the primary domain www.clearglassinc.com (and the bare apex) after the migration
# off the clearglassinc.github.io Pages URL.
REQUIRED_URL_PATTERN = re.compile(r"clearglassinc\.com", re.IGNORECASE)
URL_CHECK_EXEMPT_PLATFORMS = {"website"}

# How many recent hashes to check for repetition.
REPETITION_WINDOW = 30


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class PlatformResult:
    platform: str
    passed: bool
    char_count: int
    failures: list[str]


@dataclass
class ValidationReport:
    run_utc: str
    pillar: str
    content_hash: str
    overall_passed: bool
    platform_results: list[PlatformResult]
    global_failures: list[str]

    def summary(self) -> str:
        lines = [
            f"Validation: {'PASSED' if self.overall_passed else 'FAILED'}",
            f"Pillar: {self.pillar}  Hash: {self.content_hash}",
        ]
        for pr in self.platform_results:
            status = "✓" if pr.passed else "✗"
            lines.append(f"  {status} {pr.platform} ({pr.char_count} chars)")
            for f in pr.failures:
                lines.append(f"      → {f}")
        for gf in self.global_failures:
            lines.append(f"  GLOBAL → {gf}")
        return "\n".join(lines)


# ── Per-platform validation ───────────────────────────────────────────────────

def _extract_text(platform: str, content: dict) -> str:
    if platform == "threads":
        return " ".join(content.get("posts", []))
    if platform == "x":
        return content.get("text", "")
    if platform == "website":
        return content.get("copy", "")
    if platform == "email":
        return (
            content.get("subject", "")
            + " "
            + content.get("preview", "")
            + " "
            + content.get("body", "")
        )
    # linkedin
    return content.get("headline", "") + " " + content.get("body", "")


def validate_platform(platform: str, content: dict, char_count: int) -> PlatformResult:
    failures: list[str] = []
    limits = PLATFORM_LIMITS.get(platform, {})
    text = _extract_text(platform, content)

    # Character limits
    min_chars = limits.get("min", 0)
    max_chars = limits.get("max", 99_999)
    if char_count < min_chars:
        failures.append(f"Too short: {char_count} chars (min {min_chars})")
    if char_count > max_chars:
        failures.append(f"Too long: {char_count} chars (max {max_chars})")

    # Weak phrases
    text_lower = text.lower()
    found_weak = [p for p in WEAK_PHRASES if p in text_lower]
    if found_weak:
        failures.append(f"Weak phrases detected: {', '.join(found_weak)}")

    # Brand keyword presence
    if not any(kw in text_lower for kw in BRAND_KEYWORDS):
        failures.append(f"No brand keyword found (expected one of: {', '.join(BRAND_KEYWORDS)})")

    # CTA / URL presence (website platform is the site itself — exempt)
    if platform not in URL_CHECK_EXEMPT_PLATFORMS and not REQUIRED_URL_PATTERN.search(text):
        failures.append("Missing www.clearglassinc.com URL")

    return PlatformResult(
        platform=platform,
        passed=len(failures) == 0,
        char_count=char_count,
        failures=failures,
    )


# ── Repetition guard ─────────────────────────────────────────────────────────

def _recent_hashes() -> list[str]:
    runs_file = METRICS_DIR / "runs.json"
    if not runs_file.exists():
        return []
    try:
        runs: list[dict] = json.loads(runs_file.read_text(encoding="utf-8"))
        return [r.get("content_hash", "") for r in runs[-REPETITION_WINDOW:]]
    except (json.JSONDecodeError, ValueError):
        return []


# ── Main validation entry ─────────────────────────────────────────────────────

def validate_bundle(bundle: dict) -> ValidationReport:
    run_utc = bundle.get("run_utc", "")
    pillar = bundle.get("pillar", "unknown")
    content_hash = bundle.get("content_hash", "")
    platforms_data: list[dict] = bundle.get("platforms", [])

    global_failures: list[str] = []

    # Repetition check
    recent = _recent_hashes()
    if content_hash and recent.count(content_hash) > 1:
        global_failures.append(
            f"Content hash {content_hash} appears {recent.count(content_hash)} times "
            f"in the last {REPETITION_WINDOW} runs — possible repetition."
        )

    platform_results: list[PlatformResult] = []
    for pd in platforms_data:
        platform = pd.get("platform", "")
        char_count = pd.get("char_count", 0)
        content = pd.get("content", {})
        result = validate_platform(platform, content, char_count)
        platform_results.append(result)

    overall_passed = (
        all(r.passed for r in platform_results) and len(global_failures) == 0
    )

    return ValidationReport(
        run_utc=run_utc,
        pillar=pillar,
        content_hash=content_hash,
        overall_passed=overall_passed,
        platform_results=platform_results,
        global_failures=global_failures,
    )


def emit_github_output(report: ValidationReport) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        return
    passed_str = "true" if report.overall_passed else "false"
    with open(output_file, "a", encoding="utf-8") as fh:
        fh.write(f"passed={passed_str}\n")
        fh.write(f"pillar={report.pillar}\n")


if __name__ == "__main__":
    bundle_file = OUTPUT_DIR / "latest.json"
    if not bundle_file.exists():
        print("ERROR: marketing/output/latest.json not found — run content_engine.py first.")
        raise SystemExit(1)

    bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
    report = validate_bundle(bundle)

    print(report.summary())

    report_path = OUTPUT_DIR / "validation_report.json"
    report_path.write_text(
        json.dumps(
            {
                "run_utc": report.run_utc,
                "pillar": report.pillar,
                "content_hash": report.content_hash,
                "overall_passed": report.overall_passed,
                "platform_results": [
                    {"platform": r.platform, "passed": r.passed, "char_count": r.char_count, "failures": r.failures}
                    for r in report.platform_results
                ],
                "global_failures": report.global_failures,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    emit_github_output(report)

    if not report.overall_passed:
        raise SystemExit(1)
