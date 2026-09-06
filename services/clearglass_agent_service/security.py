from __future__ import annotations

import hmac
import os
from hashlib import sha256

from fastapi import Header, HTTPException, Request, status


CLEARGLASS_ORG_HEADER = "ClearGlassInc"


def _configured_keys() -> set[str]:
    raw = os.getenv("CLEARGLASS_AGENT_API_KEYS", "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def _allowed_orgs() -> set[str]:
    raw = os.getenv("CLEARGLASS_ALLOWED_ORGS", CLEARGLASS_ORG_HEADER)
    return {item.strip() for item in raw.split(",") if item.strip()}


def _fingerprint(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:12]


def verify_clear_glass_request(
    request: Request,
    x_clear_glass_org: str | None = Header(default=None, alias="X-ClearGlass-Org"),
    x_clear_glass_api_key: str | None = Header(default=None, alias="X-ClearGlass-API-Key"),
) -> dict[str, str]:
    """Enforce ClearGlass-only service access.

    This is intentionally simple for a deployable starter. In production, put this
    behind an API gateway with SSO/JWT verification, IP allowlists, mTLS, and WAF
    policy. This function still blocks public unauthenticated calls.
    """

    allowed_orgs = _allowed_orgs()
    configured = _configured_keys()

    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="agent service is not configured with CLEARGLASS_AGENT_API_KEYS",
        )

    if not x_clear_glass_org or x_clear_glass_org not in allowed_orgs:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ClearGlass authorization required")

    if not x_clear_glass_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing ClearGlass API key")

    matched = any(hmac.compare_digest(x_clear_glass_api_key, candidate) for candidate in configured)
    if not matched:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid ClearGlass API key")

    return {
        "org": x_clear_glass_org,
        "key_fingerprint": _fingerprint(x_clear_glass_api_key),
        "client_host": request.client.host if request.client else "unknown",
    }
