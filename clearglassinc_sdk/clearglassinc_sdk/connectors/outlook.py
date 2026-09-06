"""Outlook/Microsoft 365 connector (Microsoft Graph API): exposes mail and
calendar operations as agent Tools.

Requires `httpx` (`pip install clearglassinc-sdk[http]`). The dependency is
only imported when the connector is instantiated. Pass a valid Graph API
OAuth2 access token — this connector does not perform the OAuth flow itself.
"""

from __future__ import annotations

from typing import Any

from clearglassinc_sdk.tools import Tool

_API_BASE = "https://graph.microsoft.com/v1.0"


class OutlookConnector:
    def __init__(self, access_token: str, base_url: str = _API_BASE) -> None:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "OutlookConnector requires 'httpx': pip install clearglassinc-sdk[http]"
            ) from exc

        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )

    def send_mail(self, to: str, subject: str, body: str) -> dict[str, Any]:
        """Send an email via the signed-in user's mailbox."""
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": to}}],
            }
        }
        response = self._client.post("/me/sendMail", json=payload)
        response.raise_for_status()
        return {"status": "sent", "to": to, "subject": subject}

    def list_events(self, top: int = 10) -> list[dict[str, Any]]:
        """List upcoming calendar events."""
        response = self._client.get("/me/events", params={"$top": top})
        response.raise_for_status()
        return response.json().get("value", [])

    def as_tools(self) -> list[Tool]:
        return [
            Tool(name="outlook_send_mail", description="Send an email via Outlook.", func=self.send_mail),
            Tool(
                name="outlook_list_events",
                description="List upcoming Outlook calendar events.",
                func=self.list_events,
            ),
        ]
