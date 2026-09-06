"""GitHub connector: exposes a handful of REST API operations as agent Tools.

Requires `httpx` (`pip install clearglassinc-sdk[http]`). The dependency is
only imported when the connector is instantiated.
"""

from __future__ import annotations

from typing import Any

from clearglassinc_sdk.tools import Tool

_API_BASE = "https://api.github.com"


class GitHubConnector:
    def __init__(self, token: str, base_url: str = _API_BASE) -> None:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "GitHubConnector requires 'httpx': pip install clearglassinc-sdk[http]"
            ) from exc

        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=30.0,
        )

    def list_issues(self, repo: str, state: str = "open") -> list[dict[str, Any]]:
        """List issues for `owner/repo` (state: open|closed|all)."""
        response = self._client.get(f"/repos/{repo}/issues", params={"state": state})
        response.raise_for_status()
        return response.json()

    def create_issue(self, repo: str, title: str, body: str = "") -> dict[str, Any]:
        """Create an issue in `owner/repo`."""
        response = self._client.post(f"/repos/{repo}/issues", json={"title": title, "body": body})
        response.raise_for_status()
        return response.json()

    def get_file(self, repo: str, path: str, ref: str | None = None) -> dict[str, Any]:
        """Fetch file metadata/content for `path` in `owner/repo`."""
        params = {"ref": ref} if ref else None
        response = self._client.get(f"/repos/{repo}/contents/{path}", params=params)
        response.raise_for_status()
        return response.json()

    def as_tools(self) -> list[Tool]:
        return [
            Tool(
                name="github_list_issues",
                description="List issues in a GitHub repository.",
                func=self.list_issues,
            ),
            Tool(
                name="github_create_issue",
                description="Create a new issue in a GitHub repository.",
                func=self.create_issue,
            ),
            Tool(
                name="github_get_file",
                description="Fetch a file's contents from a GitHub repository.",
                func=self.get_file,
            ),
        ]
