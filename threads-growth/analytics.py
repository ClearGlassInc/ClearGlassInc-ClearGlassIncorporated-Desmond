"""Analytics over your *own* Threads account data.

Pulls first-party insights via the official API and produces a plain-text
performance summary: engagement rate, best posting hours, and top posts.
All input is the authenticated user's own data — nothing is scraped from
other accounts.

Standard library only.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from threads_client import ThreadsClient

# Metrics we treat as "engagement" when computing an engagement rate.
_ENGAGEMENT_METRICS = ("likes", "replies", "reposts", "quotes", "shares")


def _metric_map(insights: dict[str, Any]) -> dict[str, float]:
    """Flatten a Threads insights payload into {metric: total_value}."""
    out: dict[str, float] = {}
    for item in insights.get("data", []):
        name = item.get("name")
        if not name:
            continue
        total = 0.0
        # total_value form
        tv = item.get("total_value")
        if isinstance(tv, dict) and "value" in tv:
            total += float(tv["value"])
        # time-series form
        for point in item.get("values", []) or []:
            val = point.get("value")
            if isinstance(val, (int, float)):
                total += float(val)
        out[name] = total
    return out


def engagement_rate(metrics: dict[str, float]) -> Optional[float]:
    """Engagement / views, as a fraction. None if views unknown."""
    views = metrics.get("views", 0.0)
    if views <= 0:
        return None
    engaged = sum(metrics.get(m, 0.0) for m in _ENGAGEMENT_METRICS)
    return engaged / views


def best_posting_hours(posts: list[dict[str, Any]]) -> list[tuple[int, int]]:
    """Return (hour_utc, count) sorted by how often you posted then.

    A simple, honest heuristic based on when your existing posts went out;
    pair it with per-post insights to learn which hours actually perform.
    """
    buckets: dict[int, int] = defaultdict(int)
    for post in posts:
        ts = post.get("timestamp")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        buckets[dt.astimezone(timezone.utc).hour] += 1
    return sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)


def top_posts(
    client: ThreadsClient,
    posts: list[dict[str, Any]],
    *,
    limit: int = 5,
    rank_by: str = "views",
) -> list[dict[str, Any]]:
    """Rank the user's own posts by a chosen insight metric."""
    scored: list[dict[str, Any]] = []
    for post in posts:
        media_id = post.get("id")
        if not media_id:
            continue
        try:
            metrics = _metric_map(client.media_insights(media_id))
        except Exception:  # noqa: BLE001 - skip posts without insights
            continue
        scored.append(
            {
                "id": media_id,
                "text": (post.get("text") or "").strip(),
                "permalink": post.get("permalink"),
                "metrics": metrics,
                "score": metrics.get(rank_by, 0.0),
            }
        )
    scored.sort(key=lambda p: p["score"], reverse=True)
    return scored[:limit]


def build_report(client: ThreadsClient, *, post_limit: int = 25) -> str:
    """Produce a human-readable performance report as a string."""
    profile = client.get_profile()
    account = _metric_map(client.account_insights())
    posts = client.list_own_posts(limit=post_limit).get("data", [])

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"Threads performance report — @{profile.get('username', '?')}")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("=" * 60)

    lines.append("\nAccount totals:")
    for name, val in sorted(account.items()):
        lines.append(f"  {name:<18} {val:,.0f}")

    rate = engagement_rate(account)
    if rate is not None:
        lines.append(f"\nEngagement rate: {rate * 100:.2f}%  (engaged / views)")

    lines.append("\nMost active posting hours (UTC):")
    for hour, count in best_posting_hours(posts)[:5]:
        lines.append(f"  {hour:02d}:00   {count} post(s)")

    lines.append("\nTop posts by views:")
    for i, post in enumerate(top_posts(client, posts, limit=5), start=1):
        preview = post["text"][:70].replace("\n", " ")
        views = post["metrics"].get("views", 0.0)
        lines.append(f"  {i}. [{views:,.0f} views] {preview}")
        if post.get("permalink"):
            lines.append(f"     {post['permalink']}")

    lines.append("\n" + "=" * 60)
    lines.append(
        "Tip: post consistently at your best-performing hours and reply to "
        "early comments quickly. Real engagement compounds; shortcuts get "
        "you banned."
    )
    return "\n".join(lines)
