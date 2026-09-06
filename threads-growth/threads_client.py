"""Official Meta Threads API client.

Compliant scope only. This client:
  * authenticates as a single user via the official OAuth flow,
  * publishes posts to *that user's own* account,
  * reads *that user's own* insights.

It deliberately does NOT implement follower automation, mass-follow/unfollow,
scraping of other users, bulk commenting, or any control-bypass behaviour.
Those violate Meta's Platform Terms and are out of scope by design.

Docs: https://developers.facebook.com/docs/threads

Standard library only (urllib) so it runs in minimal environments without
extra dependencies, matching the repo convention for stdlib modules.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

GRAPH_BASE = "https://graph.threads.net"
API_VERSION = "v1.0"

# Text posts publish in two steps: create a media container, then publish it.
# https://developers.facebook.com/docs/threads/posts
_CONTAINER_POLL_SECONDS = 2
_CONTAINER_MAX_POLLS = 15


class ThreadsAPIError(RuntimeError):
    """Raised when the Threads API returns an error payload."""

    def __init__(self, status: int, message: str, payload: Any = None):
        super().__init__(f"[{status}] {message}")
        self.status = status
        self.payload = payload


@dataclass
class ThreadsClient:
    """Thin, typed wrapper over the Threads Graph API.

    Parameters
    ----------
    access_token:
        A long-lived user access token obtained via the OAuth flow
        (see :meth:`exchange_code` / :meth:`refresh_long_lived_token`).
    user_id:
        The Threads user id ("me" resolves to the token owner).
    timeout:
        Per-request timeout in seconds.
    """

    access_token: str
    user_id: str = "me"
    timeout: float = 30.0
    _last_request_ts: float = field(default=0.0, repr=False)
    # Be a polite client: never burst faster than this many seconds apart.
    min_request_interval: float = 0.5

    # -- low level ---------------------------------------------------------

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self._last_request_ts = time.monotonic()

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        *,
        authed: bool = True,
    ) -> dict[str, Any]:
        self._throttle()
        params = dict(params or {})
        if authed:
            params.setdefault("access_token", self.access_token)

        url = f"{GRAPH_BASE}/{path.lstrip('/')}"
        data = None
        if method.upper() == "GET":
            if params:
                url = f"{url}?{urllib.parse.urlencode(params)}"
        else:
            data = urllib.parse.urlencode(params).encode("utf-8")

        req = urllib.request.Request(url, data=data, method=method.upper())
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8") or "{}"
                return json.loads(body)
        except urllib.error.HTTPError as exc:  # pragma: no cover - network
            raw = exc.read().decode("utf-8", "replace")
            try:
                payload = json.loads(raw)
                message = payload.get("error", {}).get("message", raw)
            except json.JSONDecodeError:
                payload, message = raw, raw
            raise ThreadsAPIError(exc.code, message, payload) from exc
        except urllib.error.URLError as exc:  # pragma: no cover - network
            raise ThreadsAPIError(0, str(exc.reason)) from exc

    # -- OAuth helpers -----------------------------------------------------

    @classmethod
    def exchange_code(
        cls,
        *,
        app_id: str,
        app_secret: str,
        redirect_uri: str,
        code: str,
    ) -> dict[str, Any]:
        """Exchange an OAuth ``code`` for a short-lived access token.

        Returns the raw token payload (``access_token``, ``user_id``).
        """
        params = {
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        }
        url = f"{GRAPH_BASE}/oauth/access_token"
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def exchange_for_long_lived_token(self, app_secret: str) -> dict[str, Any]:
        """Upgrade a short-lived token to a long-lived (60 day) token."""
        return self._request(
            "GET",
            "access_token",
            {
                "grant_type": "th_exchange_token",
                "client_secret": app_secret,
            },
        )

    def refresh_long_lived_token(self) -> dict[str, Any]:
        """Refresh an unexpired long-lived token for another 60 days."""
        return self._request(
            "GET",
            "refresh_access_token",
            {"grant_type": "th_refresh_token"},
        )

    # -- profile -----------------------------------------------------------

    def get_profile(
        self,
        fields: Iterable[str] = (
            "id",
            "username",
            "threads_profile_picture_url",
            "threads_biography",
        ),
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"{API_VERSION}/{self.user_id}",
            {"fields": ",".join(fields)},
        )

    # -- publishing (own account only) ------------------------------------

    def create_text_container(
        self,
        text: str,
        *,
        reply_to_id: Optional[str] = None,
        link_attachment: Optional[str] = None,
    ) -> str:
        """Create a TEXT media container and return its container id."""
        if not text or not text.strip():
            raise ValueError("Post text must not be empty.")
        params: dict[str, Any] = {"media_type": "TEXT", "text": text}
        if reply_to_id:
            params["reply_to_id"] = reply_to_id
        if link_attachment:
            params["link_attachment"] = link_attachment
        resp = self._request(
            "POST", f"{API_VERSION}/{self.user_id}/threads", params
        )
        return resp["id"]

    def _wait_until_ready(self, container_id: str) -> None:
        """Poll a container's status until it is FINISHED (or fail loudly)."""
        for _ in range(_CONTAINER_MAX_POLLS):
            status = self._request(
                "GET",
                f"{API_VERSION}/{container_id}",
                {"fields": "status,error_message"},
            )
            state = status.get("status")
            if state == "FINISHED":
                return
            if state in {"ERROR", "EXPIRED"}:
                raise ThreadsAPIError(
                    0, status.get("error_message", state), status
                )
            time.sleep(_CONTAINER_POLL_SECONDS)
        raise ThreadsAPIError(0, "Container did not become ready in time.")

    def publish_container(self, container_id: str) -> str:
        """Publish a previously created container. Returns the media id."""
        resp = self._request(
            "POST",
            f"{API_VERSION}/{self.user_id}/threads_publish",
            {"creation_id": container_id},
        )
        return resp["id"]

    def publish_text(
        self,
        text: str,
        *,
        reply_to_id: Optional[str] = None,
        link_attachment: Optional[str] = None,
    ) -> str:
        """Convenience: create + wait + publish a text post in one call.

        Returns the published media id.
        """
        container_id = self.create_text_container(
            text, reply_to_id=reply_to_id, link_attachment=link_attachment
        )
        self._wait_until_ready(container_id)
        return self.publish_container(container_id)

    # -- insights (own data only) -----------------------------------------

    def account_insights(
        self,
        metrics: Iterable[str] = (
            "views",
            "likes",
            "replies",
            "reposts",
            "quotes",
            "followers_count",
        ),
        *,
        since: Optional[int] = None,
        until: Optional[int] = None,
    ) -> dict[str, Any]:
        """Fetch account-level insights for the authenticated user."""
        params: dict[str, Any] = {"metric": ",".join(metrics)}
        if since is not None:
            params["since"] = since
        if until is not None:
            params["until"] = until
        return self._request(
            "GET",
            f"{API_VERSION}/{self.user_id}/threads_insights",
            params,
        )

    def media_insights(
        self,
        media_id: str,
        metrics: Iterable[str] = (
            "views",
            "likes",
            "replies",
            "reposts",
            "quotes",
            "shares",
        ),
    ) -> dict[str, Any]:
        """Fetch per-post insights for one of the user's own posts."""
        return self._request(
            "GET",
            f"{API_VERSION}/{media_id}/insights",
            {"metric": ",".join(metrics)},
        )

    def list_own_posts(
        self,
        *,
        limit: int = 25,
        fields: Iterable[str] = (
            "id",
            "text",
            "media_type",
            "permalink",
            "timestamp",
        ),
    ) -> dict[str, Any]:
        """List the authenticated user's own recent posts."""
        return self._request(
            "GET",
            f"{API_VERSION}/{self.user_id}/threads",
            {"fields": ",".join(fields), "limit": limit},
        )
