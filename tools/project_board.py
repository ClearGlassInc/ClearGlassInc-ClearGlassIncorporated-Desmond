#!/usr/bin/env python3
# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Validate the ClearGlass Project Board feed and report what the board contains.

``data/project-board/board.json`` is the single source of truth for
``project-board.html``: the page ships an empty shell and ``project-board.js`` renders
every column, card, time-sheet row, gauge segment, feed item and calendar slot
from this file. Nothing is duplicated inline, so a broken reference in the feed
is a blank region on the page rather than a stale-but-plausible fallback — which
is exactly why the references are checked here instead of being discovered in a
browser.

What it enforces:

* the schema tag and the required top-level collections
* ids are unique within every collection
* every task points at a real column, board (or board child) and sprint, and
  every assignee is a real member
* priorities are drawn from the set the card renderer knows how to draw
* dates are ISO ``YYYY-MM-DD`` and a task never ends before it starts
* time-sheet, activity and calendar rows reference real members, and the
  calendar's schedule only lands on days the week strip actually shows
* the page is wired to the feed, the stylesheet and the script

Usage::

    python3 tools/project_board.py            # validate; exit 1 on failure
    python3 tools/project_board.py --summary  # validate, then print the board
    python3 tools/project_board.py --json     # machine-readable report

Stdlib only, so it runs in the minimal CI images.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FEED = REPO_ROOT / "data" / "project-board" / "board.json"
PAGE = REPO_ROOT / "project-board.html"
SCRIPT = REPO_ROOT / "project-board.js"
STYLES = REPO_ROOT / "project-board.css"

SCHEMA = "clearglass.project-board/v1"
FEED_URL = "/data/project-board/board.json"

PRIORITIES = {"high", "medium", "low", "none"}
ACTIVITY_KINDS = {"upload", "comment", "move"}
SPRINT_STATES = {"done", "active", "planned"}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

TOP_LEVEL = (
    "schema", "workspace", "projects", "boards", "sprints", "members",
    "columns", "tasks", "timesheet", "velocity", "activity", "calendar",
    "pricing", "promo",
)


def load(path: pathlib.Path = FEED) -> dict:
    """Read the feed. Raises on malformed JSON so callers fail loudly."""
    return json.loads(path.read_text(encoding="utf-8"))


def _ids(rows: list[dict]) -> list[str]:
    return [str(row.get("id", "")) for row in rows]


def _dupes(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen and value not in out:
            out.append(value)
        seen.add(value)
    return out


def board_ids(feed: dict) -> set[str]:
    """Every selectable board id — parents and their children alike."""
    out: set[str] = set()
    for board in feed.get("boards", []):
        out.add(board.get("id", ""))
        for child in board.get("children", []):
            out.add(child.get("id", ""))
    return out


def validate(feed: dict) -> list[str]:
    """Return a list of problems. Empty means the feed is sound."""
    problems: list[str] = []

    if feed.get("schema") != SCHEMA:
        problems.append(f"schema is {feed.get('schema')!r}, expected {SCHEMA!r}")

    for key in TOP_LEVEL:
        if key not in feed:
            problems.append(f"missing top-level key {key!r}")
    if problems:
        # Later checks index into these collections; stop while the shape is wrong.
        return problems

    for name in ("projects", "sprints", "members", "columns", "tasks", "activity"):
        dupes = _dupes(_ids(feed[name]))
        if dupes:
            problems.append(f"{name}: duplicate ids {dupes}")

    all_boards = board_ids(feed)
    # Parents and children share one id space — a child that shadows a parent
    # would make the tree's board filter ambiguous.
    board_list = [b.get("id", "") for b in feed["boards"]]
    board_list += [c.get("id", "") for b in feed["boards"] for c in b.get("children", [])]
    dupes = _dupes(board_list)
    if dupes:
        problems.append(f"boards: duplicate ids {dupes}")

    members = set(_ids(feed["members"]))
    columns = set(_ids(feed["columns"]))
    sprints = set(_ids(feed["sprints"]))

    for sprint in feed["sprints"]:
        state = sprint.get("state")
        if state not in SPRINT_STATES:
            problems.append(f"sprint {sprint.get('id')!r}: state {state!r} not in {sorted(SPRINT_STATES)}")
        for field in ("start", "end"):
            value = sprint.get(field)
            if value and not ISO_DATE.match(str(value)):
                problems.append(f"sprint {sprint.get('id')!r}: {field} {value!r} is not YYYY-MM-DD")

    for column in feed["columns"]:
        colour = str(column.get("color", ""))
        if not re.match(r"^#[0-9a-fA-F]{6}$", colour):
            problems.append(f"column {column.get('id')!r}: color {colour!r} is not a 6-digit hex")

    for task in feed["tasks"]:
        tid = task.get("id")
        if not task.get("title", "").strip():
            problems.append(f"task {tid!r}: empty title")
        if task.get("column") not in columns:
            problems.append(f"task {tid!r}: unknown column {task.get('column')!r}")
        if task.get("board") not in all_boards:
            problems.append(f"task {tid!r}: unknown board {task.get('board')!r}")
        if task.get("sprint") not in sprints:
            problems.append(f"task {tid!r}: unknown sprint {task.get('sprint')!r}")
        if task.get("priority", "none") not in PRIORITIES:
            problems.append(f"task {tid!r}: priority {task.get('priority')!r} not in {sorted(PRIORITIES)}")
        for who in task.get("assignees", []):
            if who not in members:
                problems.append(f"task {tid!r}: unknown assignee {who!r}")
        start, end = task.get("start"), task.get("end")
        for field, value in (("start", start), ("end", end)):
            if value and not ISO_DATE.match(str(value)):
                problems.append(f"task {tid!r}: {field} {value!r} is not YYYY-MM-DD")
        if start and end and ISO_DATE.match(str(start)) and ISO_DATE.match(str(end)) and end < start:
            problems.append(f"task {tid!r}: ends {end} before it starts {start}")
        for sub in task.get("subtasks", []):
            if not str(sub.get("title", "")).strip():
                problems.append(f"task {tid!r}: subtask with an empty title")

    for entry in feed["timesheet"].get("entries", []):
        if entry.get("member") not in members:
            problems.append(f"timesheet: unknown member {entry.get('member')!r}")
        if not isinstance(entry.get("seconds"), int) or entry["seconds"] < 0:
            problems.append(f"timesheet {entry.get('member')!r}: seconds must be a non-negative int")

    velocity = feed["velocity"]
    if not isinstance(velocity.get("average"), (int, float)) or velocity["average"] <= 0:
        problems.append("velocity: average must be a positive number")
    labels = [s.get("label") for s in velocity.get("series", [])]
    if not labels:
        problems.append("velocity: needs at least one series")
    if _dupes([str(item) for item in labels]):
        problems.append(f"velocity: duplicate series labels {_dupes([str(x) for x in labels])}")
    if velocity.get("selected") and velocity["selected"] not in labels:
        problems.append(f"velocity: selected {velocity['selected']!r} is not one of {labels}")
    for series in velocity.get("series", []):
        pct = series.get("percent")
        if not isinstance(pct, (int, float)) or not 0 <= pct <= 100:
            problems.append(f"velocity {series.get('label')!r}: percent {pct!r} outside 0-100")

    for item in feed["activity"]:
        aid = item.get("id")
        if item.get("kind") not in ACTIVITY_KINDS:
            problems.append(f"activity {aid!r}: kind {item.get('kind')!r} not in {sorted(ACTIVITY_KINDS)}")
        if item.get("member") not in members:
            problems.append(f"activity {aid!r}: unknown member {item.get('member')!r}")
        hours = item.get("hours")
        if not isinstance(hours, (int, float)) or hours < 0:
            problems.append(f"activity {aid!r}: hours must be a non-negative number")
        upload = item.get("file")
        if upload is not None:
            pct = upload.get("percent")
            if not isinstance(pct, (int, float)) or not 0 <= pct <= 100:
                problems.append(f"activity {aid!r}: upload percent {pct!r} outside 0-100")

    calendar = feed["calendar"]
    days = {day.get("date") for day in calendar.get("days", [])}
    for day in calendar.get("days", []):
        if not ISO_DATE.match(str(day.get("date", ""))):
            problems.append(f"calendar: day {day.get('date')!r} is not YYYY-MM-DD")
    if calendar.get("selected") not in days:
        problems.append(f"calendar: selected {calendar.get('selected')!r} is not in the week strip")
    for slot in calendar.get("schedule", []):
        if slot.get("date") not in days:
            problems.append(f"calendar: slot {slot.get('title')!r} on {slot.get('date')!r} is off the week strip")
        if not re.match(r"^\d{2}:\d{2}$", str(slot.get("time", ""))):
            problems.append(f"calendar: slot {slot.get('title')!r} time {slot.get('time')!r} is not HH:MM")
        for who in slot.get("attendees", []):
            if who not in members:
                problems.append(f"calendar: slot {slot.get('title')!r} has unknown attendee {who!r}")

    return problems


def validate_wiring() -> list[str]:
    """The page must actually reach the feed it is documented to render from."""
    problems: list[str] = []
    for path in (PAGE, SCRIPT, STYLES):
        if not path.exists():
            problems.append(f"missing {path.relative_to(REPO_ROOT).as_posix()}")
    if problems:
        return problems

    page = PAGE.read_text(encoding="utf-8")
    for asset in ("/project-board.css", "/project-board.js"):
        if asset not in page:
            problems.append(f"project-board.html does not reference {asset}")
    if FEED_URL not in SCRIPT.read_text(encoding="utf-8"):
        problems.append(f"project-board.js does not reference {FEED_URL}")
    return problems


def summarise(feed: dict) -> dict:
    """Counts the board renders, for the CLI report and for tests to assert on."""
    by_column: dict[str, int] = {c["id"]: 0 for c in feed["columns"]}
    by_priority: dict[str, int] = {p: 0 for p in sorted(PRIORITIES)}
    by_sprint: dict[str, int] = {s["id"]: 0 for s in feed["sprints"]}
    for task in feed["tasks"]:
        by_column[task["column"]] = by_column.get(task["column"], 0) + 1
        by_priority[task.get("priority", "none")] += 1
        by_sprint[task["sprint"]] = by_sprint.get(task["sprint"], 0) + 1

    logged = sum(e.get("seconds", 0) for e in feed["timesheet"].get("entries", []))
    return {
        "schema": feed["schema"],
        "generated": feed.get("generated"),
        "projects": len(feed["projects"]),
        "boards": len(board_ids(feed)),
        "members": len(feed["members"]),
        "columns": len(feed["columns"]),
        "tasks": len(feed["tasks"]),
        "subtasks": sum(len(t.get("subtasks", [])) for t in feed["tasks"]),
        "activity": len(feed["activity"]),
        "schedule": len(feed["calendar"].get("schedule", [])),
        "logged_seconds": logged,
        "logged_hours": round(logged / 3600, 2),
        "by_column": by_column,
        "by_priority": by_priority,
        "by_sprint": by_sprint,
    }


def _print_summary(report: dict) -> None:
    print(f"ClearGlass Project Board · {report['schema']} · generated {report['generated']}")
    print(
        f"  {report['tasks']} tasks ({report['subtasks']} subtasks) across "
        f"{report['columns']} columns and {report['boards']} boards"
    )
    print(f"  {report['members']} members · {report['logged_hours']}h logged · "
          f"{report['activity']} activity items · {report['schedule']} calendar slots")
    print("  by column:   " + ", ".join(f"{k}={v}" for k, v in report["by_column"].items()))
    print("  by priority: " + ", ".join(f"{k}={v}" for k, v in report["by_priority"].items()))
    print("  by sprint:   " + ", ".join(f"{k}={v}" for k, v in report["by_sprint"].items()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--summary", action="store_true", help="print the board's contents")
    parser.add_argument("--json", action="store_true", help="emit the summary as JSON")
    args = parser.parse_args(argv)

    try:
        feed = load()
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL  {FEED.relative_to(REPO_ROOT).as_posix()}: {exc}", file=sys.stderr)
        return 1

    problems = validate(feed) + validate_wiring()
    if problems:
        print(f"FAIL  {len(problems)} problem(s) in the project board feed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    report = summarise(feed)
    if args.json:
        print(json.dumps(report, indent=2))
    elif args.summary:
        _print_summary(report)
    else:
        print(f"OK    project board feed is sound — {report['tasks']} tasks, "
              f"{report['columns']} columns, {report['members']} members")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
