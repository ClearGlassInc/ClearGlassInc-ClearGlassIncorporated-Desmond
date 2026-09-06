"""Etsy OAuth2 (PKCE) — the handshake that turns an Etsy app into a live connection.

``app/etsy.py`` can *detect* and *verify* a connection but it cannot create one: it
needs an access token that only Etsy can mint, and only after the shop owner grants
consent in a browser. This module is that missing step, and nothing more.

Safety properties:

* **No writes, ever.** The only Etsy calls here are the OAuth token endpoint. Grant
  requests, listing publishes, inventory pushes and order changes stay in the governed
  ``/etsy`` router behind the human-approval gate.
* **No secret persistence.** Tokens are returned to the caller and never written to
  disk, logged, or echoed into the audit ledger. They belong in runtime env vars.
* **PKCE, public-client style.** Etsy's OAuth2 uses PKCE, so the app's shared secret is
  never transmitted during the exchange — only the keystring plus a one-time verifier.

Stdlib only (``urllib``/``hashlib``/``secrets``), matching the other minimal-CI modules,
and every network call is injectable so the tests run fully offline.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

from .config import Settings, get_settings
from .etsy import REQUIRED_SCOPES

# A poster takes (url, json_body) and returns (status, parsed_json).
Poster = Callable[[str, dict], "tuple[int, dict]"]


class EtsyOAuthError(RuntimeError):
    """Raised when the OAuth handshake cannot be completed."""


def _b64url(raw: bytes) -> str:
    """Base64url without padding — the encoding PKCE and Etsy both expect."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def generate_pkce() -> tuple[str, str]:
    """Return a fresh ``(code_verifier, code_challenge)`` PKCE pair (S256).

    The verifier is the secret half: it never leaves the machine until the token
    exchange, which is what stops an intercepted authorization code from being
    redeemable by anyone else.
    """
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def generate_state() -> str:
    """Opaque anti-CSRF value; must come back unchanged on the redirect."""
    return _b64url(secrets.token_bytes(16))


def build_authorize_url(
    settings: Settings | None = None,
    *,
    code_challenge: str,
    state: str,
    scopes: tuple[str, ...] | list[str] | None = None,
) -> str:
    """Build the Etsy consent URL the shop owner opens in a browser.

    Opening this URL is what actually links the store: Etsy shows the shop owner which
    permissions are being requested, and on approval redirects to the configured
    ``etsy_redirect_uri`` with a short-lived ``code`` to exchange for tokens.
    """
    settings = settings or get_settings()
    if not settings.etsy_keystring:
        raise EtsyOAuthError(
            "etsy_keystring is not set — create an app at "
            "https://www.etsy.com/developers/your-apps and set ETSY_KEYSTRING first."
        )
    if not settings.etsy_redirect_uri:
        raise EtsyOAuthError(
            "etsy_redirect_uri is not set — it must exactly match a callback URL "
            "registered on the Etsy app (ETSY_REDIRECT_URI)."
        )
    params = {
        "response_type": "code",
        "client_id": settings.etsy_keystring,
        "redirect_uri": settings.etsy_redirect_uri,
        "scope": " ".join(scopes or REQUIRED_SCOPES),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return settings.etsy_oauth_authorize_url + "?" + urllib.parse.urlencode(params)


def _default_post(settings: Settings) -> Poster:
    """Build a POST caller for the Etsy token endpoint.

    Per RFC 6749 §4.1.3 — and Etsy's own documented examples — the token endpoint takes
    ``application/x-www-form-urlencoded`` parameters, not JSON. The *response* is JSON.
    """

    def post(url: str, body: dict) -> tuple[int, dict]:
        data = urllib.parse.urlencode(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 (fixed https base)
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read() or b"{}")
            except (ValueError, OSError):
                return exc.code, {}
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise EtsyOAuthError(f"Etsy token request failed: {exc}") from exc

    return post


def _token_result(status: int, body: dict, *, step: str) -> dict:
    """Normalise a token response, raising with Etsy's own error text on failure."""
    if status != 200 or not body.get("access_token"):
        detail = body.get("error_description") or body.get("error") or f"status {status}"
        raise EtsyOAuthError(f"{step} failed: {detail}")
    access_token = body["access_token"]
    # When the server reports the granted scope, it is authoritative — a refresh carries
    # the original grant forward and can never widen it, so we must not assume otherwise.
    granted = body.get("scope")
    return {
        "access_token": access_token,
        "refresh_token": body.get("refresh_token", ""),
        "expires_in": body.get("expires_in"),
        # Etsy tokens are "<user_id>.<token>", so the account id falls out for free.
        "user_id": access_token.split(".", 1)[0] if "." in access_token else None,
        "scope": tuple(granted.replace(",", " ").split()) if granted else None,
    }


def exchange_code(
    code: str,
    code_verifier: str,
    settings: Settings | None = None,
    *,
    post: Poster | None = None,
) -> dict:
    """Trade the redirect's ``code`` (plus the PKCE verifier) for live tokens.

    Returns the access token, refresh token, lifetime, and the Etsy user id parsed from
    the token prefix. The caller is responsible for putting these into the environment —
    this function deliberately does not persist them anywhere.
    """
    settings = settings or get_settings()
    if not settings.etsy_keystring:
        raise EtsyOAuthError("etsy_keystring is not set — cannot exchange the code.")
    post = post or _default_post(settings)
    status, body = post(
        settings.etsy_token_url,
        {
            "grant_type": "authorization_code",
            "client_id": settings.etsy_keystring,
            "redirect_uri": settings.etsy_redirect_uri,
            "code": code,
            "code_verifier": code_verifier,
        },
    )
    return _token_result(status, body, step="Authorization code exchange")


def refresh_access_token(
    refresh_token: str | None = None,
    settings: Settings | None = None,
    *,
    post: Poster | None = None,
) -> dict:
    """Mint a new access token from the refresh token.

    Etsy access tokens expire after roughly an hour while refresh tokens last far
    longer, so a long-running connection re-runs this rather than the full consent flow.
    """
    settings = settings or get_settings()
    refresh_token = refresh_token or settings.etsy_refresh_token
    if not refresh_token:
        raise EtsyOAuthError(
            "No refresh token available — run the full consent flow "
            "(python -m app.etsy_connect) to establish the connection."
        )
    post = post or _default_post(settings)
    status, body = post(
        settings.etsy_token_url,
        {
            "grant_type": "refresh_token",
            "client_id": settings.etsy_keystring,
            "refresh_token": refresh_token,
        },
    )
    return _token_result(status, body, step="Token refresh")


def env_exports(tokens: dict, scopes: tuple[str, ...] | list[str] | None = None) -> str:
    """Render the env vars the control plane needs, ready to paste into a secret store.

    ``scopes`` must be what Etsy actually granted, never what was merely requested:
    ``verify_connection`` derives ``can_list_products`` / ``can_manage_orders`` straight
    from ``ETSY_SCOPES``, so an overstated value would report a capability the token does
    not have. Pass ``None`` when the granted scope is unknown and the line is omitted
    rather than guessed.

    Returned as text for the operator to place in *runtime* configuration. Never write
    this to a file in the repo — the tokens are live credentials for the shop.
    """
    lines = [
        f"ETSY_ACCESS_TOKEN={tokens['access_token']}",
        f"ETSY_REFRESH_TOKEN={tokens.get('refresh_token', '')}",
    ]
    if scopes:
        lines.append(f"ETSY_SCOPES={','.join(scopes)}")
    else:
        lines.append("# ETSY_SCOPES unchanged — keep the value from the original grant.")
    if tokens.get("user_id"):
        lines.append(f"# Etsy user id from the token prefix: {tokens['user_id']}")
    return "\n".join(lines)
