#!/usr/bin/env python3
"""ClearGlass Marketing Command OS — Market Intelligence lane runner.

Governed, READ_ONLY, stdlib-only. Produces a **weekly Market Intelligence delta
scaffold** into ``marketing/output/market-intelligence/`` from the committed
watchlist (``marketing/config/market_intelligence_watchlist.json``).

Non-negotiable design (mirrors the OS guardrails):

* **Never fabricates findings.** The lane cannot browse the web in CI, so it does
  not invent competitor moves, metrics, or trends. Every intelligence field is
  emitted as a structured slot flagged ``unverified -- analyst input required``.
  A human (or an authorized, tool-equipped run) fills the verified values; the
  scaffold only organizes *what to look at* and *what changed in the watchlist*.
* **Delta, not restate.** Each run diffs the current watchlist against the
  previous report's captured watchlist and reports added/removed topics,
  competitors, and keyword seeds — the only facts the lane can assert on its own.
* **Fail-closed & logged.** Output is a draft (governance tier: low). It is
  auto-produced and logged; nothing is published, sent, or spent.

Usage::

    python3 scripts/market_intelligence_lane.py            # write report
    python3 scripts/market_intelligence_lane.py --json     # also print JSON to stdout
    python3 scripts/market_intelligence_lane.py --check    # validate config only, no write
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "marketing" / "config" / "market_intelligence_watchlist.json"
OUT_DIR = ROOT / "marketing" / "output" / "market-intelligence"
UNVERIFIED = "unverified -- analyst input required"


def _load_config() -> dict:
    if not CONFIG.exists():
        raise SystemExit(f"ERROR: watchlist config not found: {CONFIG}")
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise SystemExit(f"ERROR: watchlist config is not valid JSON: {exc}")
    for key in ("topics", "sources"):
        if not isinstance(data.get(key), list):
            raise SystemExit(f"ERROR: watchlist config missing list field '{key}'")
    return data


def _previous_report() -> dict | None:
    latest = OUT_DIR / "latest.json"
    if not latest.exists():
        return None
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:  # pragma: no cover - defensive
        return None


def _names(items: list) -> list[str]:
    """Normalize a list of strings-or-{name} dicts to non-empty names."""
    out = []
    for it in items:
        if isinstance(it, str):
            name = it.strip()
        elif isinstance(it, dict):
            name = str(it.get("name", "")).strip()
        else:
            name = ""
        if name:
            out.append(name)
    return out


def _delta(current: list[str], previous: list[str]) -> dict:
    cur, prev = set(current), set(previous)
    return {
        "added": sorted(cur - prev),
        "removed": sorted(prev - cur),
        "unchanged_count": len(cur & prev),
    }


def build_report(config: dict, previous: dict | None, now: _dt.datetime) -> dict:
    topics = _names(config.get("topics", []))
    competitors = _names(config.get("competitors", []))
    keywords = _names(config.get("emerging_keywords_seed", []))

    prev_watch = (previous or {}).get("watchlist_snapshot", {})
    topic_delta = _delta(topics, prev_watch.get("topics", []))
    competitor_delta = _delta(competitors, prev_watch.get("competitors", []))
    keyword_delta = _delta(keywords, prev_watch.get("emerging_keywords_seed", []))

    # Analyst worklist: one unverified slot per watched item. These are the ONLY
    # facts the lane asserts (structure), never the findings themselves.
    opportunities = [
        {
            "topic": t,
            "signal": UNVERIFIED,
            "why_it_matters": UNVERIFIED,
            "content_idea": UNVERIFIED,
            "confidence": "assumed",
        }
        for t in topics
    ]
    competitive = [
        {"competitor": c, "observed_move": UNVERIFIED, "opening_for_us": UNVERIFIED,
         "confidence": "assumed"}
        for c in competitors
    ] or [{"competitor": UNVERIFIED, "observed_move": UNVERIFIED,
           "opening_for_us": UNVERIFIED, "confidence": "assumed"}]
    keyword_watch = [
        {"keyword": k, "trend": UNVERIFIED, "intent": UNVERIFIED, "confidence": "assumed"}
        for k in keywords
    ]

    iso_week = now.isocalendar()
    return {
        "lane": "Market Intelligence (INTEL-01)",
        "agent_os": "ClearGlass Marketing Command OS",
        "report_type": "weekly_delta_scaffold",
        "generated_at": now.replace(microsecond=0).isoformat() + "Z",
        "iso_week": f"{iso_week[0]}-W{iso_week[1]:02d}",
        "governance": {
            "authority": "READ_ONLY",
            "tier": "low",
            "invariant": "read-only analysis -> draft -> human approval -> execution",
            "no_fabrication": True,
            "status": "draft -- auto-produced and logged; not published",
        },
        "notice": (
            "This is a SCAFFOLD, not intelligence. Every 'signal', 'move', and "
            "'trend' field is a placeholder marked '" + UNVERIFIED + "'. An "
            "analyst (or an authorized tool-equipped run) must fill verified "
            "values before any of this informs a published decision."
        ),
        "watchlist_snapshot": {
            "topics": topics,
            "competitors": competitors,
            "emerging_keywords_seed": keywords,
            "sources": config.get("sources", []),
        },
        "delta_since_last_report": {
            "previous_report_at": (previous or {}).get("generated_at"),
            "topics": topic_delta,
            "competitors": competitor_delta,
            "emerging_keywords_seed": keyword_delta,
        },
        "opportunities": opportunities,
        "competitive_intel": competitive,
        "emerging_keywords": keyword_watch,
        "analyst_worklist": [
            "Fill each 'signal' / 'observed_move' / 'trend' slot from public "
            "sources only; label verified vs estimated.",
            "Promote high-confidence opportunities into the Content Strategy "
            "(PLAN-03) editorial queue.",
            "Flag anything legal/financial/reputational for human review before use.",
        ],
    }


def render_markdown(report: dict) -> str:
    d = report["delta_since_last_report"]
    lines = [
        f"# Market Intelligence — Weekly Delta ({report['iso_week']})",
        "",
        f"> **{report['governance']['status']}** · authority "
        f"`{report['governance']['authority']}` · generated "
        f"{report['generated_at']}",
        "",
        report["notice"],
        "",
        "## Delta since last report",
        f"- Previous report: {d['previous_report_at'] or '_none (first run)_'}",
        f"- Topics: +{len(d['topics']['added'])} / "
        f"-{len(d['topics']['removed'])} "
        f"({d['topics']['unchanged_count']} unchanged)",
        f"- Competitors: +{len(d['competitors']['added'])} / "
        f"-{len(d['competitors']['removed'])}",
        f"- Keyword seeds: +{len(d['emerging_keywords_seed']['added'])} / "
        f"-{len(d['emerging_keywords_seed']['removed'])}",
    ]
    if d["topics"]["added"]:
        lines.append(f"  - New topics: {', '.join(d['topics']['added'])}")
    lines += ["", "## Opportunity slots (analyst to verify)"]
    for opp in report["opportunities"]:
        lines.append(f"- **{opp['topic']}** — signal: _{opp['signal']}_")
    lines += ["", "## Emerging keyword watch (analyst to verify)"]
    for kw in report["emerging_keywords"]:
        lines.append(f"- `{kw['keyword']}` — trend: _{kw['trend']}_")
    lines += ["", "## Analyst worklist"]
    lines += [f"{i}. {task}" for i, task in enumerate(report["analyst_worklist"], 1)]
    lines.append("")
    return "\n".join(lines)


def write_report(report: dict, markdown: str, now: _dt.datetime) -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y-%m-%d")
    written = []
    for path, content in (
        (OUT_DIR / "latest.json", json.dumps(report, indent=2) + "\n"),
        (OUT_DIR / "latest.md", markdown),
        (OUT_DIR / f"{stamp}-market-intelligence.json", json.dumps(report, indent=2) + "\n"),
        (OUT_DIR / f"{stamp}-market-intelligence.md", markdown),
    ):
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Market Intelligence lane (governed, READ_ONLY).")
    parser.add_argument("--json", action="store_true", help="print the report JSON to stdout")
    parser.add_argument("--check", action="store_true", help="validate config only; write nothing")
    args = parser.parse_args(argv)

    config = _load_config()
    if args.check:
        print(f"OK: watchlist config valid ({len(_names(config.get('topics', [])))} topics).")
        return 0

    now = _dt.datetime.utcnow()
    report = build_report(config, _previous_report(), now)
    markdown = render_markdown(report)
    written = write_report(report, markdown, now)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Market Intelligence delta scaffold written ({report['iso_week']}):")
        for p in written:
            print(f"  - {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
