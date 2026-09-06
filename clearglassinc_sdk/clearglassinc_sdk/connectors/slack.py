"""Slack connector: exposes Web API operations as agent Tools.

Requires `httpx` (`pip install clearglassinc-sdk[http]`). The dependency is
only imported when the connector is instantiated.
"""

from __future__ import annotations

from typing import Any

from clearglassinc_sdk.tools import Tool

_API_BASE = "https://slack.com/api"


class SlackConnector:
    def __init__(self, bot_token: str, base_url: str = _API_BASE) -> None:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "SlackConnector requires 'httpx': pip install clearglassinc-sdk[http]"
            ) from exc

        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {bot_token}"},
            timeout=30.0,
        )

    def send_message(self, channel: str, text: str) -> dict[str, Any]:
        """Post a message to a Slack channel."""
        response = self._client.post("/chat.postMessage", json={"channel": channel, "text": text})
        response.raise_for_status()
        return response.json()

    def list_channels(self) -> list[dict[str, Any]]:
        """List channels visible to the bot."""
        response = self._client.get("/conversations.list")
        response.raise_for_status()
        return response.json().get("channels", [])

    def as_tools(self) -> list[Tool]:
        return [
            Tool(
                name="slack_send_message",
                description="Send a message to a Slack channel.",
                func=self.send_message,
            ),
            Tool(
                name="slack_list_channels",
                description="List Slack channels visible to the bot.",
                func=self.list_channels,
            ),
        ]
