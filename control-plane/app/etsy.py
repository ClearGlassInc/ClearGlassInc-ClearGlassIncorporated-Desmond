"""Etsy Open API v3 connector — connection detection + read-only verification.

Safety: this module NEVER writes to Etsy (listings, inventory, orders). It only
detects whether credentials are present and performs *read-only* verification of
shop identity, granted permissions, and sync status. Every write path lives in the
``/etsy`` router and routes through :func:`app.service.run_governed_action`, so
publishing listings, changing prices, syncing inventory, or managing orders all
stay behind the human-approval gate (see ``ALWAYS_ESCALATE`` in ``governance.py``).

The HTTP layer uses stdlib ``urllib`` so the module needs no extra dependency and
is trivially testable by injecting a ``get`` fetcher (no network in unit tests).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from .config import Settings, get_settings

# OAuth2 scopes this operator needs to run the shop end to end.
LISTING_SCOPES = ("listings_r", "listings_w")
ORDER_SCOPES = ("transactions_r", "transactions_w")
REQUIRED_SCOPES = LISTING_SCOPES + ORDER_SCOPES

# Credentials without which no connection is possible.
REQUIRED_CREDENTIALS = ("etsy_keystring", "etsy_access_token")

# A fetcher takes an API path (relative to the v3 base) and returns (status, json).
Fetcher = Callable[[str], "tuple[int, dict]"]


class EtsyError(RuntimeError):
    """Raised when a read-only verification call to Etsy fails."""


def _missing_credentials(settings: Settings) -> list[str]:
    """Human-readable list of the hard-required credentials that are still blank."""
    labels = {
        "etsy_keystring": "etsy_keystring (Etsy app API key / keystring)",
        "etsy_access_token": "etsy_access_token (OAuth2 access token)",
    }
    return [labels[name] for name in REQUIRED_CREDENTIALS if not getattr(settings, name, "")]


def _granted_scopes(settings: Settings) -> list[str]:
    return [s.strip() for s in settings.etsy_scopes.split(",") if s.strip()]


def _user_id_from_token(token: str) -> str | None:
    """Etsy access tokens are ``<user_id>.<token>`` — pull the user id prefix."""
    if token and "." in token:
        prefix = token.split(".", 1)[0]
        if prefix.isdigit():
            return prefix
    return None


def _resolved_shop_id(settings: Settings) -> str | None:
    return settings.etsy_shop_id or None


def connection_status(settings: Settings | None = None) -> dict:
    """Detect connection state **offline** — no network call, just credential presence.

    Returns ``connected`` (all required credentials present), the list of anything
    ``missing``, the declared shop identity, and the scope gap. ``verified`` is always
    ``False`` here; a live check happens in :func:`verify_connection`.
    """
    settings = settings or get_settings()
    missing = _missing_credentials(settings)
    connected = not missing
    granted = _granted_scopes(settings)
    scope_gap = [s for s in REQUIRED_SCOPES if s not in granted]

    status: dict = {
        "connected": connected,
        "state": "connected" if connected else "not_connected",
        "verified": False,
        "missing": missing,
        "shop": {
            "declared_name": settings.etsy_shop_name or None,
            "shop_id": _resolved_shop_id(settings) or _user_id_from_token(settings.etsy_access_token),
            "login_email": settings.etsy_login_email or None,
            "declared_profile_url": settings.etsy_profile_url or None,
        },
        "required_scopes": list(REQUIRED_SCOPES),
        "granted_scopes": granted,
        "scope_gap": scope_gap,
    }
    if connected:
        status["next_step"] = (
            "Credentials present. POST /etsy/verify to confirm shop identity, "
            "listing/order permissions, and sync status before any writes."
        )
    else:
        status["next_step"] = (
            "Etsy is NOT connected. A profile URL cannot authorise anything — the shop "
            "owner must grant OAuth consent. Run `python -m app.etsy_connect` to walk "
            "the PKCE handshake, set the resulting ETSY_KEYSTRING / ETSY_ACCESS_TOKEN / "
            "ETSY_SCOPES as runtime env vars, then POST /etsy/verify."
        )
    return status


def _default_get(settings: Settings) -> Fetcher:
    """Build a read-only GET fetcher bound to the configured keystring + token."""

    def get(path: str) -> tuple[int, dict]:
        url = settings.etsy_api_base.rstrip("/") + path
        req = urllib.request.Request(
            url,
            headers={
                "x-api-key": settings.etsy_keystring,
                "Authorization": f"Bearer {settings.etsy_access_token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 (fixed https base)
                body = resp.read() or b"{}"
                return resp.status, json.loads(body)
        except urllib.error.HTTPError as exc:  # 4xx/5xx still carry a useful status + body
            try:
                body = json.loads(exc.read() or b"{}")
            except (ValueError, OSError):
                body = {}
            return exc.code, body
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise EtsyError(f"Etsy request to {path} failed: {exc}") from exc

    return get


def verify_connection(settings: Settings | None = None, *, get: Fetcher | None = None) -> dict:
    """Read-only verification of the Etsy connection.

    Confirms, without mutating anything on Etsy:
      1. **shop identity** — keystring pings, token resolves to a shop
      2. **listing permissions** — ``listings_r``/``listings_w`` granted
      3. **order management permissions** — ``transactions_r``/``transactions_w`` granted
      4. **sync status** — active/draft listing counts read back from the shop

    If required credentials are missing, returns immediately with ``connected: False``
    and never touches the network. Network failures are reported, not raised.
    """
    settings = settings or get_settings()
    missing = _missing_credentials(settings)
    if missing:
        result = connection_status(settings)
        result["verified"] = False
        result["error"] = "cannot verify — required credentials missing"
        return result

    get = get or _default_get(settings)
    granted = _granted_scopes(settings)
    checks: list[dict] = []
    ok = True

    def record(name: str, passed: bool, detail: str) -> None:
        nonlocal ok
        checks.append({"check": name, "ok": passed, "detail": detail})
        ok = ok and passed

    # 1. keystring ping (validates the API key independent of the token)
    try:
        status, _ = get("/application/openapi-ping")
        record("api_key_ping", status == 200, f"ping status {status}")
    except EtsyError as exc:
        record("api_key_ping", False, str(exc))

    # 2. shop identity via the token, then the shop record
    shop: dict = {}
    shop_id = _resolved_shop_id(settings)
    try:
        status, me = get("/application/users/me")
        if status == 200:
            shop_id = shop_id or (str(me.get("shop_id")) if me.get("shop_id") is not None else None)
            record("token_identity", True, f"token resolves to user {me.get('user_id')}")
        else:
            record("token_identity", False, f"users/me status {status}")
    except EtsyError as exc:
        record("token_identity", False, str(exc))

    if shop_id:
        try:
            status, shop = get(f"/application/shops/{shop_id}")
            record("shop_lookup", status == 200, f"shop {shop_id} status {status}")
        except EtsyError as exc:
            record("shop_lookup", False, str(exc))
    else:
        record("shop_lookup", False, "no shop_id available (set ETSY_SHOP_ID)")

    # 3 + 4. permissions (from granted scopes) and sync status (listing counts)
    can_list = all(s in granted for s in LISTING_SCOPES)
    can_manage_orders = all(s in granted for s in ORDER_SCOPES)
    record(
        "listing_permissions",
        can_list,
        "granted: " + (", ".join(s for s in LISTING_SCOPES if s in granted) or "none"),
    )
    record(
        "order_permissions",
        can_manage_orders,
        "granted: " + (", ".join(s for s in ORDER_SCOPES if s in granted) or "none"),
    )

    declared = settings.etsy_shop_name or None
    reported_name = shop.get("shop_name") if isinstance(shop, dict) else None
    identity_match = bool(reported_name) and (declared is None or declared == reported_name)

    return {
        "connected": True,
        "state": "connected",
        "verified": ok,
        "missing": [],
        "shop": {
            "shop_id": shop_id,
            "shop_name": reported_name or declared,
            "declared_name": declared,
            "identity_match": identity_match,
            "login_email": settings.etsy_login_email or None,
        },
        "permissions": {
            "can_list_products": can_list,
            "can_manage_orders": can_manage_orders,
            "required_scopes": list(REQUIRED_SCOPES),
            "granted_scopes": granted,
            "scope_gap": [s for s in REQUIRED_SCOPES if s not in granted],
        },
        "sync_status": {
            "active_listings": shop.get("listing_active_count") if isinstance(shop, dict) else None,
            "digital_listings": shop.get("digital_listing_count") if isinstance(shop, dict) else None,
            "state": "in_sync" if ok else "unverified",
        },
        "checks": checks,
    }


def is_ready_for_writes(settings: Settings | None = None) -> tuple[bool, str]:
    """Guard used by every Etsy write endpoint.

    A write may only be *proposed* (and then only after human approval) once the
    connection has the required credentials. Returns ``(ready, reason)``; when not
    ready, the reason names what to do, and no listing/order call should be attempted.
    """
    settings = settings or get_settings()
    missing = _missing_credentials(settings)
    if missing:
        return False, "Etsy is not connected — missing: " + "; ".join(missing) + ". Connect and verify first."
    return True, "connected"
