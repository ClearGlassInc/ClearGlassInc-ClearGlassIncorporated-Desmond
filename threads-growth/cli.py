"""Command-line interface for the compliant Threads growth toolkit.

Usage:
    export THREADS_ACCESS_TOKEN=...        # long-lived user token
    export THREADS_USER_ID=me              # optional, defaults to "me"

    python cli.py profile
    python cli.py post "Shipping something new today. Here's the story..."
    python cli.py schedule "Weekly tip thread" 2026-07-10T14:00:00Z
    python cli.py run-due --calendar content_calendar.json
    python cli.py run-due --calendar content_calendar.json --dry-run
    python cli.py report

Every command operates only on the authenticated user's own account.
"""

from __future__ import annotations

import argparse
import os
import sys

from analytics import build_report
from scheduler import ContentCalendar
from threads_client import ThreadsClient, ThreadsAPIError


def _client() -> ThreadsClient:
    token = os.environ.get("THREADS_ACCESS_TOKEN")
    if not token:
        sys.exit(
            "THREADS_ACCESS_TOKEN is not set. Obtain a long-lived token via "
            "the OAuth flow (see README) and export it first."
        )
    return ThreadsClient(
        access_token=token,
        user_id=os.environ.get("THREADS_USER_ID", "me"),
    )


def cmd_profile(args: argparse.Namespace) -> int:
    prof = _client().get_profile()
    print(f"@{prof.get('username', '?')}  (id={prof.get('id')})")
    bio = prof.get("threads_biography")
    if bio:
        print(bio)
    return 0


def cmd_post(args: argparse.Namespace) -> int:
    media_id = _client().publish_text(args.text, link_attachment=args.link)
    print(f"Published. media_id={media_id}")
    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    cal = ContentCalendar.load(args.calendar)
    post = cal.add(args.text, args.when, link_attachment=args.link)
    cal.save()
    print(f"Scheduled {post.id} for {post.scheduled_for}")
    return 0


def cmd_run_due(args: argparse.Namespace) -> int:
    cal = ContentCalendar.load(args.calendar)
    client = None if args.dry_run else _client()
    processed = cal.run_due(client, dry_run=args.dry_run, limit=args.limit)
    if not processed:
        print("No posts are due.")
        return 0
    for post in processed:
        marker = {
            "published": "OK",
            "failed": "ERR",
            "skipped": "DRY",
        }.get(post.status, post.status)
        detail = post.published_media_id or post.error or ""
        print(f"[{marker}] {post.id}  {detail}")
    print(f"\nCalendar status: {cal.summary()}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    print(build_report(_client(), post_limit=args.limit))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compliant Threads growth toolkit (official API only)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("profile", help="Show the authenticated profile.")

    p_post = sub.add_parser("post", help="Publish a text post now.")
    p_post.add_argument("text")
    p_post.add_argument("--link", default=None, help="Optional link attachment.")

    p_sched = sub.add_parser("schedule", help="Queue a post for later.")
    p_sched.add_argument("text")
    p_sched.add_argument("when", help="ISO 8601 time, e.g. 2026-07-10T14:00:00Z")
    p_sched.add_argument("--link", default=None)
    p_sched.add_argument("--calendar", default="content_calendar.json")

    p_run = sub.add_parser("run-due", help="Publish all due queued posts.")
    p_run.add_argument("--calendar", default="content_calendar.json")
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--limit", type=int, default=None)

    p_report = sub.add_parser("report", help="Print a performance report.")
    p_report.add_argument("--limit", type=int, default=25)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {
        "profile": cmd_profile,
        "post": cmd_post,
        "schedule": cmd_schedule,
        "run-due": cmd_run_due,
        "report": cmd_report,
    }
    try:
        return handlers[args.command](args)
    except ThreadsAPIError as exc:
        sys.exit(f"Threads API error: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
