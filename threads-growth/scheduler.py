"""Content scheduler for the official Threads API.

Keeps a JSON-backed queue of *your own* draft posts with scheduled send
times, and publishes the ones that are due through :class:`ThreadsClient`.

This is legitimate first-party automation: it posts your own content on
your own schedule. It does not follow, unfollow, scrape, or comment on
other people's content.

Standard library only.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

from threads_client import ThreadsClient


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class ScheduledPost:
    """A single queued post."""

    id: str
    text: str
    scheduled_for: str  # ISO 8601, treated as UTC
    status: str = "pending"  # pending | published | failed | skipped
    reply_to_id: Optional[str] = None
    link_attachment: Optional[str] = None
    published_media_id: Optional[str] = None
    error: Optional[str] = None
    published_at: Optional[str] = None

    def is_due(self, *, now: Optional[datetime] = None) -> bool:
        if self.status != "pending":
            return False
        now = now or _now()
        return _parse_iso(self.scheduled_for) <= now


@dataclass
class ContentCalendar:
    """A JSON-backed list of scheduled posts."""

    path: str
    posts: list[ScheduledPost] = field(default_factory=list)

    # -- persistence -------------------------------------------------------

    @classmethod
    def load(cls, path: str) -> "ContentCalendar":
        if not os.path.exists(path):
            return cls(path=path, posts=[])
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        posts = [ScheduledPost(**item) for item in raw.get("posts", [])]
        return cls(path=path, posts=posts)

    def save(self) -> None:
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(
                {"posts": [asdict(p) for p in self.posts]},
                fh,
                indent=2,
                ensure_ascii=False,
            )
        os.replace(tmp, self.path)

    # -- queue management --------------------------------------------------

    def add(
        self,
        text: str,
        scheduled_for: str,
        *,
        post_id: Optional[str] = None,
        reply_to_id: Optional[str] = None,
        link_attachment: Optional[str] = None,
    ) -> ScheduledPost:
        _parse_iso(scheduled_for)  # validate early
        post = ScheduledPost(
            id=post_id or _new_id(),
            text=text,
            scheduled_for=scheduled_for,
            reply_to_id=reply_to_id,
            link_attachment=link_attachment,
        )
        self.posts.append(post)
        return post

    def due(self, *, now: Optional[datetime] = None) -> list[ScheduledPost]:
        now = now or _now()
        return sorted(
            (p for p in self.posts if p.is_due(now=now)),
            key=lambda p: _parse_iso(p.scheduled_for),
        )

    # -- execution ---------------------------------------------------------

    def run_due(
        self,
        client: ThreadsClient,
        *,
        now: Optional[datetime] = None,
        dry_run: bool = False,
        limit: Optional[int] = None,
    ) -> list[ScheduledPost]:
        """Publish all due posts. Returns the posts that were processed.

        ``dry_run`` reports what *would* be posted without calling the API.
        Every attempt (success or failure) is persisted immediately so a
        crash never double-posts.
        """
        processed: list[ScheduledPost] = []
        for post in self.due(now=now):
            if limit is not None and len(processed) >= limit:
                break
            if dry_run:
                post.status = "skipped"
                post.error = "dry_run"
                processed.append(post)
                continue
            try:
                media_id = client.publish_text(
                    post.text,
                    reply_to_id=post.reply_to_id,
                    link_attachment=post.link_attachment,
                )
                post.status = "published"
                post.published_media_id = media_id
                post.published_at = _now().isoformat()
            except Exception as exc:  # noqa: BLE001 - record and continue
                post.status = "failed"
                post.error = str(exc)
            finally:
                self.save()
            processed.append(post)
        return processed

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for post in self.posts:
            counts[post.status] = counts.get(post.status, 0) + 1
        return counts


def _new_id() -> str:
    return f"post-{int(_now().timestamp() * 1000)}"
