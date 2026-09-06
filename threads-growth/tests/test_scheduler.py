"""Tests for the content scheduler and analytics helpers.

No network: the Threads client is replaced with a fake that records calls.
Run from the toolkit directory:  python -m pytest tests/ -q
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics import _metric_map, best_posting_hours, engagement_rate  # noqa: E402
from scheduler import ContentCalendar  # noqa: E402


class FakeClient:
    """Records publish calls; never touches the network."""

    def __init__(self, fail_on: set[str] | None = None):
        self.published: list[str] = []
        self.fail_on = fail_on or set()
        self._counter = 0

    def publish_text(self, text, *, reply_to_id=None, link_attachment=None):
        if text in self.fail_on:
            raise RuntimeError("boom")
        self._counter += 1
        self.published.append(text)
        return f"media-{self._counter}"


def _dt(hour: int) -> datetime:
    return datetime(2026, 7, 8, hour, 0, 0, tzinfo=timezone.utc)


def test_due_detection_respects_time_and_status(tmp_path):
    cal = ContentCalendar(path=str(tmp_path / "cal.json"))
    cal.add("past", "2026-07-08T10:00:00Z")
    cal.add("future", "2026-07-08T20:00:00Z")
    due = cal.due(now=_dt(12))
    assert [p.text for p in due] == ["past"]


def test_run_due_publishes_and_persists(tmp_path):
    path = str(tmp_path / "cal.json")
    cal = ContentCalendar(path=path)
    cal.add("hello", "2026-07-08T10:00:00Z")
    client = FakeClient()

    processed = cal.run_due(client, now=_dt(12))

    assert len(processed) == 1
    assert processed[0].status == "published"
    assert processed[0].published_media_id == "media-1"
    assert client.published == ["hello"]

    # persisted to disk and won't re-publish
    reloaded = ContentCalendar.load(path)
    assert reloaded.summary() == {"published": 1}
    assert reloaded.run_due(client, now=_dt(12)) == []


def test_run_due_records_failures_without_crashing(tmp_path):
    cal = ContentCalendar(path=str(tmp_path / "cal.json"))
    cal.add("ok", "2026-07-08T10:00:00Z")
    cal.add("bad", "2026-07-08T10:00:00Z")
    client = FakeClient(fail_on={"bad"})

    cal.run_due(client, now=_dt(12))

    statuses = {p.text: p.status for p in cal.posts}
    assert statuses == {"ok": "published", "bad": "failed"}


def test_dry_run_does_not_publish(tmp_path):
    cal = ContentCalendar(path=str(tmp_path / "cal.json"))
    cal.add("draft", "2026-07-08T10:00:00Z")
    processed = cal.run_due(None, now=_dt(12), dry_run=True)
    assert processed[0].status == "skipped"


def test_limit_caps_processed_posts(tmp_path):
    cal = ContentCalendar(path=str(tmp_path / "cal.json"))
    for i in range(3):
        cal.add(f"p{i}", "2026-07-08T10:00:00Z")
    processed = cal.run_due(FakeClient(), now=_dt(12), limit=2)
    assert len(processed) == 2


def test_engagement_rate_and_metric_map():
    insights = {
        "data": [
            {"name": "views", "total_value": {"value": 1000}},
            {"name": "likes", "total_value": {"value": 80}},
            {"name": "replies", "total_value": {"value": 20}},
        ]
    }
    metrics = _metric_map(insights)
    assert metrics == {"views": 1000.0, "likes": 80.0, "replies": 20.0}
    assert engagement_rate(metrics) == 0.1


def test_engagement_rate_none_without_views():
    assert engagement_rate({"likes": 5.0}) is None


def test_best_posting_hours_counts_by_utc_hour():
    posts = [
        {"timestamp": "2026-07-08T14:00:00Z"},
        {"timestamp": "2026-07-09T14:30:00Z"},
        {"timestamp": "2026-07-09T09:00:00Z"},
    ]
    ranked = best_posting_hours(posts)
    assert ranked[0] == (14, 2)
