"""Offline-first Burlington exposure planning and reporting automation.

This module automates safe analysis and draft creation. It deliberately has no
channel publishing, messaging, review submission, or profile mutation tools.
Those consequential actions remain action packages for a human approver.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any


CORE_TERMS = (
    "software architect Burlington",
    "cybersecurity consultant Burlington",
    "AI automation Burlington",
    "ClearGlass Burlington",
)


@dataclass(frozen=True)
class AgentResult:
    agent: str
    status: str
    output: str
    reason: str


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return float(value)


def validate_snapshot(snapshot: dict[str, Any]) -> dict[str, float]:
    """Validate the minimum privacy-safe aggregate measurement contract."""
    allowed = {
        "gbp_impressions", "gbp_actions", "local_sessions", "qualified_leads",
        "social_followers", "social_engagements", "grid_green_cells", "grid_total_cells",
    }
    unknown = set(snapshot) - allowed
    if unknown:
        raise ValueError(f"unsupported snapshot fields: {', '.join(sorted(unknown))}")
    values = {name: _number(snapshot.get(name, 0), name) for name in allowed}
    if values["grid_green_cells"] > values["grid_total_cells"]:
        raise ValueError("grid_green_cells cannot exceed grid_total_cells")
    return values


def percent_change(current: float, baseline: float) -> str:
    if baseline == 0:
        return "n/a" if current == 0 else "new"
    return f"{((current - baseline) / baseline) * 100:+.1f}%"


def build_report(baseline: dict[str, Any], current: dict[str, Any], period: str) -> str:
    base = validate_snapshot(baseline)
    now = validate_snapshot(current)
    rows = []
    for key in sorted(now):
        rows.append(f"| {key} | {base[key]:g} | {now[key]:g} | {percent_change(now[key], base[key])} |")
    return "\n".join([
        f"# Burlington Growth Report — {period}", "",
        "> Generated from supplied aggregate data. `0` means reported zero; missing or unavailable data must not be inferred as performance.", "",
        "## Scorecard", "", "| Metric | Baseline | Current | Change |", "|---|---:|---:|---:|", *rows, "",
        "## Core geo-grid terms", "", *[f"- {term}" for term in CORE_TERMS], "",
        "## Required operator interpretation", "",
        "- Explain material changes with source evidence; do not attribute causation from correlation.",
        "- Record experiments, policy exceptions, data gaps, and next actions.",
        "- Escalate incorrect business facts, consent failures, or GBP suspension risk immediately.", "",
    ])


def run_agents(output_dir: Path, baseline: dict[str, Any], current: dict[str, Any], period: str) -> list[AgentResult]:
    """Run bounded agents; only the analytics agent writes an autonomous artifact."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_name = f"BURLINGTON_GROWTH_REPORT_{period}.md"
    report = build_report(baseline, current, period)
    (output_dir / report_name).write_text(report, encoding="utf-8")
    results = [AgentResult("recon_analytics", "completed", report_name, "aggregate report generated")]
    for agent, artifact in (
        ("content_generator", "content-draft-package.json"),
        ("local_seo_auditor", "seo-remediation-drafts.json"),
        ("review_citation_manager", "outreach-action-packages.json"),
        ("community_partnership_scout", "partnership-drafts.json"),
    ):
        results.append(AgentResult(agent, "awaiting_configured_connector", artifact, "no verified source data supplied"))

    manifest = {
        "run_id": sha256(f"{period}|{report}".encode()).hexdigest()[:20],
        "created_at": datetime.now(UTC).isoformat(),
        "mode": "analysis_and_draft_only",
        "results": [asdict(item) for item in results],
        "external_mutations": False,
    }
    (output_dir / "run-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a governed Burlington exposure report")
    parser.add_argument("--baseline", type=Path, required=True, help="baseline aggregate JSON")
    parser.add_argument("--current", type=Path, required=True, help="current aggregate JSON")
    parser.add_argument("--output", type=Path, default=Path("operations/burlington"))
    parser.add_argument("--period", default=date.today().strftime("%Y_%m"))
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    current = json.loads(args.current.read_text(encoding="utf-8"))
    run_agents(args.output, baseline, current, args.period)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
