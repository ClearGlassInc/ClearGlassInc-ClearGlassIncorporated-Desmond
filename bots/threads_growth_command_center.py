# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Threads Growth Command Center V3.

A local, compliant, Python-first execution system for planning high-volume manual
Threads growth work. It creates a 30-day content calendar, daily manual action
briefs, draft prompts, KPI logs, engagement logs, and a self-contained HTML
command dashboard.

Rules of engagement are intentionally hard-coded into generated assets:
zero botting, zero scraping, no automated follows/likes/comments, and no storage
of platform cookies or session secrets. The system automates planning,
measurement, and review only; humans perform all platform actions.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import random
import shutil
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Literal, Sequence

Mode = Literal["init", "daily", "add-kpi", "dashboard", "all"]

DEFAULT_BRAND = "ClearGlassInc"
DEFAULT_NICHE = "AI security, business systems, cryptocurrency, discipline, strategy"
DEFAULT_ROOT = Path.home() / "Desktop" / "ThreadsGrowthCommandCenter_V3"

HOOKS = (
    "You are being outworked by people with half your talent and twice your discipline.",
    "Your business does not have a traffic problem. It has a trust problem.",
    "Stop building in secret. Nobody cares about your launch if they did not see the struggle.",
    "Most crypto accounts are not destroyed by volatility. They are destroyed by position size.",
    "If you rely on motivation to run your company, one bad day can break the system.",
    "Most AI tools are liabilities disguised as assets. Here is what real security looks like:",
    "Stop posting generic advice. Show the system, the data, the decision, and the lesson.",
    "The market pays for systems, leverage, and proof. Everything else is noise.",
)

PILLARS = (
    "AI Security",
    "Business Systems",
    "Crypto Discipline",
    "Mindset",
    "Operations",
    "Financial Freedom",
)

TOPICS: dict[str, tuple[str, ...]] = {
    "AI Security": (
        "Exposing the silent data leaks in your AI wrappers",
        "Why AI automation without audit trails is corporate suicide",
        "The exact framework ClearGlassInc uses to lock down AI workflows",
    ),
    "Business Systems": (
        "Productize or die: why service businesses stall at ten thousand dollars monthly",
        "The exact three-tool stack to replace a junior operations manager",
        "Licensing knowledge versus selling time",
    ),
    "Crypto Discipline": (
        "The cold math of risk management: why one percent sizing wins",
        "Stop trading the five-minute chart. Here is the macro truth.",
        "How to build an iron stomach for thirty percent drawdowns",
    ),
    "Mindset": (
        "Burn your plan B because it is stealing your attention",
        "If you are not tracking it daily, you do not actually care about it",
        "The ROI of saying no to almost every opportunity",
    ),
    "Operations": (
        "Friction is the enemy of scale. Here is how to kill it.",
        "The weekly review system that forces execution",
        "Why your SOPs are useless and how to fix them",
    ),
    "Financial Freedom": (
        "Cash flow over vanity metrics, always",
        "Building digital real estate versus renting algorithms",
        "The three-year timeline to exit velocity",
    ),
}

FORMATS = (
    "High-Signal Thread",
    "Raw Metric Screenshot",
    "Contrarian Opinion",
    "Tear-down / Analysis",
)

CALENDAR_HEADERS = ("date", "pillar", "topic", "format", "status")
KPI_HEADERS = (
    "date",
    "followers",
    "posts",
    "replies",
    "likes",
    "reposts",
    "impressions",
    "profile_visits",
    "engagement_rate",
    "profile_visit_rate",
    "notes",
)
ENGAGEMENT_HEADERS = ("date", "target_account", "conversation_url", "reply_angle", "outcome", "notes")


@dataclass(frozen=True)
class CommandCenterPaths:
    root: Path
    drafts: Path
    calendars: Path
    analytics: Path
    engagement: Path
    reports: Path
    daily_plans: Path
    backups: Path

    @classmethod
    def from_root(cls, root: Path) -> "CommandCenterPaths":
        return cls(
            root=root,
            drafts=root / "Drafts",
            calendars=root / "Calendars",
            analytics=root / "Analytics",
            engagement=root / "Engagement",
            reports=root / "Reports",
            daily_plans=root / "DailyPlans",
            backups=root / "Backups",
        )

    @property
    def calendar_path(self) -> Path:
        return self.calendars / "ContentCalendar.csv"

    @property
    def kpi_path(self) -> Path:
        return self.analytics / "ThreadsKPITracker.csv"

    @property
    def engagement_path(self) -> Path:
        return self.engagement / "EngagementTracker.csv"

    @property
    def dashboard_path(self) -> Path:
        return self.reports / "ThreadsGrowthDashboard.html"

    @property
    def manifest_path(self) -> Path:
        return self.root / "command_center_manifest.json"


@dataclass(frozen=True)
class KpiEntry:
    followers: int = 0
    posts: int = 0
    replies: int = 0
    likes: int = 0
    reposts: int = 0
    impressions: int = 0
    profile_visits: int = 0
    notes: str = "Manual update"


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def today_iso() -> str:
    return date.today().isoformat()


def status(message: str) -> None:
    print(f"[Threads V3] {message}")


def safe_file_name(text: str) -> str:
    safe = "".join(char if char.isalnum() or char in {" ", "-", "_"} else "" for char in text)
    safe = "_".join(safe.split()).strip("_")
    return safe or "Untitled"


def ensure_workspace(paths: CommandCenterPaths) -> None:
    for folder in asdict(paths).values():
        Path(folder).mkdir(parents=True, exist_ok=True)


def backup_file(paths: CommandCenterPaths, file_path: Path) -> Path | None:
    if not file_path.exists():
        return None
    stamp = utc_now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = paths.backups / f"{stamp}_{file_path.name}"
    shutil.copy2(file_path, backup_path)
    return backup_path


def write_csv_if_missing(path: Path, headers: Sequence[str], rows: Iterable[dict[str, object]]) -> None:
    if path.exists():
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        writer.writeheader()
        writer.writerows(rows)


def append_csv_row(path: Path, headers: Sequence[str], row: dict[str, object]) -> None:
    should_write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        if should_write_header:
            writer.writeheader()
        writer.writerow(row)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def content_plan_rows(start: date | None = None, days: int = 30) -> list[dict[str, str]]:
    start_date = start or date.today()
    rows: list[dict[str, str]] = []
    for offset in range(days):
        pillar = PILLARS[offset % len(PILLARS)]
        topic_list = TOPICS[pillar]
        rows.append(
            {
                "date": (start_date + timedelta(days=offset)).isoformat(),
                "pillar": pillar,
                "topic": topic_list[offset % len(topic_list)],
                "format": FORMATS[offset % len(FORMATS)],
                "status": "Pending Manual Execution",
            }
        )
    return rows


def engagement_seed_rows() -> list[dict[str, str]]:
    return [
        {
            "date": today_iso(),
            "target_account": "",
            "conversation_url": "",
            "reply_angle": "Add missing context, counterexample, or practical proof",
            "outcome": "Pending",
            "notes": "Manual engagement only. No bots. No scraping.",
        }
    ]


def calculate_rates(entry: KpiEntry) -> tuple[float, float]:
    engagements = entry.likes + entry.replies + entry.reposts
    engagement_rate = engagements / entry.impressions if entry.impressions else 0.0
    profile_visit_rate = entry.profile_visits / entry.impressions if entry.impressions else 0.0
    return engagement_rate, profile_visit_rate


def initialize_workspace(paths: CommandCenterPaths, brand_name: str, niche: str) -> None:
    ensure_workspace(paths)
    write_csv_if_missing(paths.calendar_path, CALENDAR_HEADERS, content_plan_rows())
    engagement_rate, profile_visit_rate = calculate_rates(KpiEntry())
    write_csv_if_missing(
        paths.kpi_path,
        KPI_HEADERS,
        [
            {
                "date": today_iso(),
                "followers": 0,
                "posts": 0,
                "replies": 0,
                "likes": 0,
                "reposts": 0,
                "impressions": 0,
                "profile_visits": 0,
                "engagement_rate": f"{engagement_rate:.4f}",
                "profile_visit_rate": f"{profile_visit_rate:.4f}",
                "notes": "Ground Zero",
            }
        ],
    )
    write_csv_if_missing(paths.engagement_path, ENGAGEMENT_HEADERS, engagement_seed_rows())
    manifest = {
        "system": "Threads Growth Command Center V3",
        "brand_name": brand_name,
        "niche": niche,
        "root": str(paths.root),
        "generated_at_utc": utc_now().isoformat(),
        "rules_of_engagement": [
            "Zero botting",
            "Zero scraping",
            "No automated follows, likes, comments, reposts, or DMs",
            "Manual posting and manual engagement only",
            "Use official/approved analytics exports or manually entered KPIs",
        ],
    }
    paths.manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    status(f"Workspace initialized at {paths.root}")


def random_hook() -> str:
    return random.choice(HOOKS)


def post_draft(topic: str, pillar: str, post_format: str, brand_name: str, niche: str) -> str:
    return f"""[HOOK: COPY/PASTE OR REWRITE TO BE SHARPER]
{random_hook()}

[TARGET INTEL]
Topic: {topic}
Pillar: {pillar}
Format: {post_format}

[THE DIRECTIVE]
1. Core point: no fluff. Make the first sentence impossible to ignore.
2. Proof: include exact numbers, screenshots, system diagrams, or code when available.
3. Takeaway: tell the reader what to change today.
4. Compliance: this is a human-written/human-posted draft. No botting. No scraping.

[CALL TO ACTION]
Follow {brand_name} for execution, {niche}, and systems that compound.

[RUTHLESS EDITING CHECKLIST]
[ ] Did I remove every useless adjective?
[ ] Is the hook specific enough to stop a scroll?
[ ] Does this build authority with proof instead of noise?
[ ] Would I still post this if vanity metrics were hidden?
"""


def daily_plan(brand_name: str, niche: str, run_date: date | None = None) -> str:
    day = run_date or date.today()
    return f"""=========================================
THREADS GROWTH BRIEF - {day.isoformat()}
=========================================
TARGET: {brand_name}
SECTOR: {niche}

RULES OF ENGAGEMENT:
1. ZERO BOTTING. ZERO SCRAPING. ZERO FAKE ENGAGEMENT.
2. PUBLISH 3X TODAY: morning, afternoon, evening.
3. 40 MANUAL REPLIES MAXIMUM-QUALITY, NOT SPAM. Add context, proof, or useful disagreement.
4. IF A FORMAT FAILS TWICE, KILL IT OR REWRITE THE HOOK.

EXECUTION BLOCKS:
[ ] 08:00 - Post 1: high-signal or contrarian post + 15 manual replies.
[ ] 13:00 - Post 2: proof, screenshot, metric, teardown, or result + 15 manual replies.
[ ] 19:00 - Post 3: short lesson, hard-earned insight, or question + 10 manual replies.

ENGAGEMENT PROTOCOL:
- Never write generic replies like "Great post!".
- Add missing context, politely disagree, show practical proof, or ask a sharp question.
- Do not mass-follow, mass-like, mass-comment, automate clicks, or scrape accounts.

EVALUATE AND ADAPT:
- Engagement rate = (likes + replies + reposts) / impressions.
- Profile visit rate = profile visits / impressions.
- If ER < 2%, rewrite the hook and opening proof.
- If profile visit rate < 0.5%, strengthen authority and CTA.
=========================================
"""


def run_daily_workflow(paths: CommandCenterPaths, brand_name: str, niche: str) -> list[Path]:
    ensure_workspace(paths)
    if not paths.calendar_path.exists():
        initialize_workspace(paths, brand_name, niche)

    today = today_iso()
    daily_plan_path = paths.daily_plans / f"DailyPlan_{today}.txt"
    daily_plan_path.write_text(daily_plan(brand_name, niche), encoding="utf-8")

    calendar = read_csv(paths.calendar_path)
    rows = [row for row in calendar if row.get("date") == today] or calendar[:3]
    written = [daily_plan_path]
    for row in rows:
        draft_path = paths.drafts / f"{today}_{safe_file_name(row.get('topic', 'Untitled'))}.txt"
        if not draft_path.exists():
            draft_path.write_text(
                post_draft(
                    row.get("topic", "Untitled"),
                    row.get("pillar", "General"),
                    row.get("format", "Post"),
                    brand_name,
                    niche,
                ),
                encoding="utf-8",
            )
        written.append(draft_path)
    status(f"Daily workflow prepared for {today}")
    return written


def add_kpi_entry(paths: CommandCenterPaths, entry: KpiEntry) -> dict[str, object]:
    ensure_workspace(paths)
    if not paths.kpi_path.exists():
        initialize_workspace(paths, DEFAULT_BRAND, DEFAULT_NICHE)
    backup_file(paths, paths.kpi_path)
    engagement_rate, profile_visit_rate = calculate_rates(entry)
    row: dict[str, object] = {
        "date": today_iso(),
        "followers": entry.followers,
        "posts": entry.posts,
        "replies": entry.replies,
        "likes": entry.likes,
        "reposts": entry.reposts,
        "impressions": entry.impressions,
        "profile_visits": entry.profile_visits,
        "engagement_rate": f"{engagement_rate:.4f}",
        "profile_visit_rate": f"{profile_visit_rate:.4f}",
        "notes": entry.notes,
    }
    append_csv_row(paths.kpi_path, KPI_HEADERS, row)
    status("KPI telemetry logged")
    return row


def int_field(row: dict[str, str], key: str) -> int:
    try:
        return int(float(row.get(key, "0") or 0))
    except ValueError:
        return 0


def rows_to_table(rows: Sequence[dict[str, str]], max_rows: int = 10) -> str:
    selected = list(rows[:max_rows])
    if not selected:
        return "<p>No data available.</p>"
    headers = list(selected[0].keys())
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body = []
    for row in selected:
        cells = "".join(f"<td>{html.escape(str(row.get(header, '')))}</td>" for header in headers)
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def generate_dashboard(paths: CommandCenterPaths, brand_name: str, niche: str) -> Path:
    ensure_workspace(paths)
    if not paths.calendar_path.exists() or not paths.kpi_path.exists():
        initialize_workspace(paths, brand_name, niche)

    calendar = read_csv(paths.calendar_path)
    kpis = read_csv(paths.kpi_path)
    latest = kpis[-1] if kpis else {}
    today = date.today()
    upcoming = [row for row in calendar if date.fromisoformat(row["date"]) >= today][:10]
    recent_kpis = kpis[-10:]

    total_posts = sum(int_field(row, "posts") for row in kpis)
    total_replies = sum(int_field(row, "replies") for row in kpis)
    total_impressions = sum(int_field(row, "impressions") for row in kpis)
    total_profile_visits = sum(int_field(row, "profile_visits") for row in kpis)

    dashboard = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(brand_name)} Threads Command Center</title>
  <style>
    :root {{ --bg:#09090b; --card:#18181b; --accent:#dc2626; --ok:#22c55e; --text:#f4f4f5; --muted:#a1a1aa; --border:#27272a; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: Inter, Arial, sans-serif; background: radial-gradient(circle at top left, #1e1b4b, var(--bg) 40%); color: var(--text); padding: 40px; margin: 0; }}
    h1, h2 {{ color: #fff; text-transform: uppercase; letter-spacing: 1px; }}
    h1 {{ border-bottom: 2px solid var(--accent); display: inline-block; padding-bottom: 10px; }}
    .sub {{ color: var(--muted); max-width: 940px; line-height: 1.6; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin: 30px 0; }}
    .card {{ background: rgba(24,24,27,.92); border: 1px solid var(--border); border-left: 4px solid var(--accent); padding: 24px; border-radius: 10px; box-shadow: 0 16px 50px rgba(0,0,0,.3); }}
    .metric {{ font-size: 38px; font-weight: 900; margin-top: 10px; color: #fff; }}
    .label {{ color: var(--muted); font-size: 13px; text-transform: uppercase; font-weight: bold; letter-spacing: .5px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; background: rgba(24,24,27,.92); }}
    th, td {{ border: 1px solid var(--border); padding: 12px; text-align: left; vertical-align: top; }}
    th {{ background: #202024; color: var(--muted); text-transform: uppercase; font-size: 12px; }}
    td {{ color: #e4e4e7; }}
    .truth {{ border-left: 4px solid var(--ok); padding-left: 16px; font-size: 18px; font-weight: bold; color: #fff; font-style: italic; }}
    .warning {{ border: 1px solid #7f1d1d; background: rgba(127,29,29,.22); padding: 16px; border-radius: 10px; color: #fecaca; }}
  </style>
</head>
<body>
  <h1>System V3: {html.escape(brand_name)}</h1>
  <p class="sub">Python-generated command center for a high-velocity but compliant Threads growth workflow in {html.escape(niche)}. Planning, drafting, KPI tracking, and dashboarding are automated; all posting and engagement remain manual.</p>
  <div class="warning"><strong>Rules:</strong> zero botting, zero scraping, no fake engagement, no automated follows/likes/comments/reposts/DMs, and no storage of platform cookies or session tokens.</div>
  <div class="grid">
    <div class="card"><div class="label">Total Followers</div><div class="metric">{html.escape(str(latest.get('followers', 0)))}</div></div>
    <div class="card"><div class="label">Posts Fired</div><div class="metric">{total_posts}</div></div>
    <div class="card"><div class="label">Replies Logged</div><div class="metric">{total_replies}</div></div>
    <div class="card"><div class="label">Total Impressions</div><div class="metric">{total_impressions}</div></div>
    <div class="card"><div class="label">Profile Visits</div><div class="metric">{total_profile_visits}</div></div>
    <div class="card"><div class="label">Latest ER</div><div class="metric">{float(latest.get('engagement_rate', 0) or 0):.2%}</div></div>
  </div>
  <h2>The Standard</h2>
  <p class="truth">If a format is not generating replies, quote posts, bookmarks, or profile visits after two serious attempts, kill the format or rebuild the hook.</p>
  <h2>Upcoming Firepower</h2>
  {rows_to_table(upcoming, 10)}
  <h2>Telemetry Logs</h2>
  {rows_to_table(recent_kpis, 10)}
</body>
</html>
"""
    paths.dashboard_path.write_text(dashboard, encoding="utf-8")
    status(f"Dashboard written to {paths.dashboard_path}")
    return paths.dashboard_path


def run(mode: Mode, paths: CommandCenterPaths, brand_name: str, niche: str, kpi: KpiEntry) -> list[Path]:
    outputs: list[Path] = []
    if mode in {"init", "all"}:
        initialize_workspace(paths, brand_name, niche)
        outputs.extend([paths.calendar_path, paths.kpi_path, paths.engagement_path, paths.manifest_path])
    if mode in {"daily", "all"}:
        outputs.extend(run_daily_workflow(paths, brand_name, niche))
    if mode == "add-kpi":
        add_kpi_entry(paths, kpi)
        outputs.append(paths.kpi_path)
    if mode in {"dashboard", "all"}:
        outputs.append(generate_dashboard(paths, brand_name, niche))
    return outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Threads Growth Command Center V3 - Python automation for compliant manual growth ops.")
    parser.add_argument("--mode", choices=["init", "daily", "add-kpi", "dashboard", "all"], default="all")
    parser.add_argument("--brand-name", default=DEFAULT_BRAND)
    parser.add_argument("--niche", default=DEFAULT_NICHE)
    parser.add_argument("--root-path", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--followers", type=int, default=0)
    parser.add_argument("--posts", type=int, default=0)
    parser.add_argument("--replies", type=int, default=0)
    parser.add_argument("--likes", type=int, default=0)
    parser.add_argument("--reposts", type=int, default=0)
    parser.add_argument("--impressions", type=int, default=0)
    parser.add_argument("--profile-visits", type=int, default=0)
    parser.add_argument("--notes", default="Manual update")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    paths = CommandCenterPaths.from_root(args.root_path.expanduser().resolve())
    kpi = KpiEntry(
        followers=args.followers,
        posts=args.posts,
        replies=args.replies,
        likes=args.likes,
        reposts=args.reposts,
        impressions=args.impressions,
        profile_visits=args.profile_visits,
        notes=args.notes,
    )
    outputs = run(args.mode, paths, args.brand_name, args.niche, kpi)
    for output in outputs:
        status(f"Output: {output}")
    status("V3 execution complete. Go to work manually and ethically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
