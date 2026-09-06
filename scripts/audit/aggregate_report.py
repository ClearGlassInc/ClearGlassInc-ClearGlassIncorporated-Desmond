#!/usr/bin/env python3
"""Aggregate per-repo audit JSON records into a CSV summary + console report.

Reads:   ./audit-out/repos/*.json   (or $REPOS_DIR)
Writes:  ./audit-out/audit_report.csv
         ./audit-out/audit_report.md  (short markdown summary)

Exit code: 0 always (reporting tool); flags are surfaced in output.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

REPOS_DIR = Path(os.environ.get("REPOS_DIR", "./audit-out/repos"))
OUT_DIR = Path(os.environ.get("OUT_DIR", "./audit-out"))

COLUMNS = [
    "repo",
    "visibility",
    "default_branch",
    "archived",
    "workflow_count",
    "workflows_failing",
    "workflows_never_run",
    "secret_scanning",
    "secret_push_protection",
    "required_reviews",
    "required_checks",
    "enforce_admins",
    "bot_commits_30d",
    "total_commits_30d",
    "bot_open_prs",
    "total_open_prs",
    "pip_status",
    "pip_high",
    "pip_critical",
    "npm_status",
    "npm_high",
    "npm_critical",
    "risk_score",
]


def score(row: dict) -> int:
    """Crude prioritization: higher = more attention needed."""
    s = 0
    s += 5 * int(row["pip_critical"] or 0)
    s += 5 * int(row["npm_critical"] or 0)
    s += 2 * int(row["pip_high"] or 0)
    s += 2 * int(row["npm_high"] or 0)
    s += 3 * int(row["workflows_failing"] or 0)
    if row["secret_scanning"] not in ("enabled", "unknown"):
        s += 2
    if int(row["required_reviews"] or 0) == 0:
        s += 1
    if int(row["required_checks"] or 0) == 0:
        s += 1
    return s


def flatten(record: dict) -> dict:
    wfs = record.get("workflows", {}).get("items") or []
    failing = sum(1 for w in wfs if w.get("last_conclusion") == "failure")
    never_run = sum(1 for w in wfs if w.get("last_conclusion") == "none")
    sec = record.get("security", {})
    prot = sec.get("branch_protection", {}) or {}
    bot = record.get("bot_health", {})
    deps = record.get("deps", {})
    row = {
        "repo": record.get("repo", ""),
        "visibility": record.get("meta", {}).get("visibility", ""),
        "default_branch": record.get("meta", {}).get("default_branch", ""),
        "archived": record.get("meta", {}).get("archived", False),
        "workflow_count": record.get("workflows", {}).get("count", 0),
        "workflows_failing": failing,
        "workflows_never_run": never_run,
        "secret_scanning": sec.get("secret_scanning", "unknown"),
        "secret_push_protection": sec.get("secret_scanning_push_protection", "unknown"),
        "required_reviews": prot.get("required_reviews", 0),
        "required_checks": prot.get("required_checks", 0),
        "enforce_admins": prot.get("enforce_admins", False),
        "bot_commits_30d": bot.get("bot_commits", 0),
        "total_commits_30d": bot.get("total_commits", 0),
        "bot_open_prs": bot.get("bot_open_prs", 0),
        "total_open_prs": bot.get("total_open_prs", 0),
        "pip_status": deps.get("pip", {}).get("status", ""),
        "pip_high": deps.get("pip", {}).get("high", 0),
        "pip_critical": deps.get("pip", {}).get("critical", 0),
        "npm_status": deps.get("npm", {}).get("status", ""),
        "npm_high": deps.get("npm", {}).get("high", 0),
        "npm_critical": deps.get("npm", {}).get("critical", 0),
    }
    row["risk_score"] = score(row)
    return row


def main() -> int:
    if not REPOS_DIR.is_dir():
        print(f"no records dir: {REPOS_DIR}", file=sys.stderr)
        return 0

    rows = []
    for p in sorted(REPOS_DIR.glob("*.json")):
        try:
            rows.append(flatten(json.loads(p.read_text())))
        except (json.JSONDecodeError, OSError) as e:
            print(f"skip {p.name}: {e}", file=sys.stderr)

    if not rows:
        print("no records found", file=sys.stderr)
        return 0

    rows.sort(key=lambda r: (-r["risk_score"], r["repo"]))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "audit_report.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    failing_total = sum(r["workflows_failing"] for r in rows)
    crit_total = sum(r["pip_critical"] + r["npm_critical"] for r in rows)
    high_total = sum(r["pip_high"] + r["npm_high"] for r in rows)
    no_secret = sum(1 for r in rows if r["secret_scanning"] != "enabled")

    md_path = OUT_DIR / "audit_report.md"
    with md_path.open("w") as f:
        f.write(f"# Audit summary ({n} repos)\n\n")
        f.write(f"- Failing workflows (last run): **{failing_total}**\n")
        f.write(f"- Dependency critical findings: **{crit_total}**\n")
        f.write(f"- Dependency high findings: **{high_total}**\n")
        f.write(f"- Repos without secret scanning enabled: **{no_secret}**\n\n")
        f.write("## Top 10 by risk score\n\n")
        f.write("| repo | risk | wf_failing | pip H/C | npm H/C | reviews | secret_scan |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in rows[:10]:
            f.write(
                f"| {r['repo']} | {r['risk_score']} | {r['workflows_failing']} "
                f"| {r['pip_high']}/{r['pip_critical']} "
                f"| {r['npm_high']}/{r['npm_critical']} "
                f"| {r['required_reviews']} | {r['secret_scanning']} |\n"
            )

    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    print(f"summary: repos={n} failing_wf={failing_total} crit={crit_total} high={high_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
