"""Operator CLI for connecting the Etsy shop: ``python -m app.etsy_connect``.

Connecting a shop is a human act — Etsy will only mint a token after the shop owner
approves the requested scopes in a browser. This CLI drives that handshake and hands
back the env vars the control plane needs. It is the one and only path from "we have an
Etsy app" to "``/etsy/connection`` reports connected".

    python -m app.etsy_connect              # full consent flow (prints URL, takes the redirect)
    python -m app.etsy_connect --status     # what is configured, what is missing
    python -m app.etsy_connect --refresh    # new access token from the stored refresh token
    python -m app.etsy_connect --exchange --code ... --verifier ...   # split-machine exchange

Nothing here writes to Etsy and nothing here persists a secret: the tokens are printed
once for the operator to paste into their secret store (Render env group, GitHub Actions
secret, local ``.env`` that is *not* committed).
"""
from __future__ import annotations

import argparse
import secrets
import sys
import urllib.parse

from .config import get_settings
from .etsy import REQUIRED_SCOPES, connection_status
from .etsy_oauth import (
    EtsyOAuthError,
    build_authorize_url,
    env_exports,
    exchange_code,
    generate_pkce,
    generate_state,
    refresh_access_token,
)


def _print_status() -> int:
    """Show what is configured for the connection, and the first thing still blocking it."""
    settings = get_settings()
    status = connection_status(settings)
    print("Etsy connection")
    print(f"  state           : {status['state']}")
    print(f"  declared profile: {status['shop']['declared_profile_url'] or '(none)'}")
    print(f"  shop id         : {status['shop']['shop_id'] or '(unknown until connected)'}")
    print(f"  keystring set   : {'yes' if settings.etsy_keystring else 'NO'}")
    print(f"  redirect uri    : {settings.etsy_redirect_uri or 'NOT SET'}")
    print(f"  granted scopes  : {', '.join(status['granted_scopes']) or '(none)'}")
    if status["scope_gap"]:
        print(f"  missing scopes  : {', '.join(status['scope_gap'])}")
    for item in status["missing"]:
        print(f"  missing         : {item}")
    print(f"\n{status['next_step']}")
    return 0 if status["connected"] else 1


def _parse_redirect(raw: str) -> tuple[str, str | None]:
    """Split a pasted redirect URL (or a bare code) into ``(code, returned_state)``.

    ``returned_state`` is ``None`` when only the code was supplied — which is exactly why
    the interactive flow insists on the full URL, so :func:`_check_state` has something
    to verify against.
    """
    raw = raw.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
        if "error" in params:
            raise EtsyOAuthError(f"Etsy returned an error on the redirect: {params['error'][0]}")
        if "code" not in params:
            raise EtsyOAuthError("That redirect URL has no ?code= parameter.")
        return params["code"][0], (params["state"][0] if "state" in params else None)
    return raw, None


def _check_state(returned: str | None, expected: str) -> None:
    """Fail closed unless the redirect's state matches the one we generated.

    This binds the response to *this* request. It is checked in code rather than left to
    the operator's eyes, so a mismatched or absent state aborts before any exchange.
    """
    if returned is None:
        raise EtsyOAuthError(
            "The redirect carried no ?state= value, so it cannot be bound to this "
            "request. Paste the full redirect URL exactly as the browser received it."
        )
    if not secrets.compare_digest(returned, expected):
        raise EtsyOAuthError(
            f"state mismatch (expected {expected!r}, got {returned!r}) — this response "
            "did not originate from this request. Nothing was exchanged."
        )


def _scopes_after_refresh(tokens: dict, settings) -> tuple[str, ...] | None:
    """The scopes to report after a refresh — never the *requested* set.

    A refresh carries the original grant forward unchanged and cannot widen it, so the
    only honest sources are what Etsy returned or what was already stored. Returns
    ``None`` when neither exists, so the ``ETSY_SCOPES`` line is omitted rather than
    guessed — ``verify_connection`` reads that value to decide what the token may do.
    """
    if tokens.get("scope"):
        return tuple(tokens["scope"])
    stored = tuple(s.strip() for s in settings.etsy_scopes.split(",") if s.strip())
    return stored or None


def _print_tokens(tokens: dict, scopes: tuple[str, ...] | None) -> None:
    print("\nConnected. Set these as RUNTIME env vars (never commit them):\n")
    print(env_exports(tokens, scopes))
    if tokens.get("expires_in"):
        print(f"\n# access token expires in {tokens['expires_in']}s — "
              f"re-run with --refresh (or automate it) before it lapses")
    print("\nThen restart the control plane and POST /etsy/verify to confirm "
          "shop identity, listing/order permissions, and sync status.")


def _run_consent_flow(
    scopes: tuple[str, ...],
    code: str | None,
    verifier: str | None,
    expected_state: str | None = None,
) -> int:
    settings = get_settings()

    if code and verifier:
        # Split-machine path: the browser half happened elsewhere. If the operator
        # brought the whole redirect URL across, its state is still checkable here.
        parsed_code, returned_state = _parse_redirect(code)
        if returned_state is not None:
            if not expected_state:
                raise EtsyOAuthError(
                    "That redirect URL carries a ?state= value but --state was not given. "
                    "Pass --state <value printed by the authorize step> so it is verified."
                )
            _check_state(returned_state, expected_state)
        elif expected_state:
            raise EtsyOAuthError(
                "--state was given but --code carries no state to check it against. "
                "Pass the full redirect URL rather than the bare code."
            )
        tokens = exchange_code(parsed_code, verifier, settings)
        _print_tokens(tokens, tokens.get("scope") or scopes)
        return 0

    verifier, challenge = generate_pkce()
    state = generate_state()
    url = build_authorize_url(settings, code_challenge=challenge, state=state, scopes=scopes)

    print("1. Open this URL as the Etsy shop owner and approve the requested scopes:\n")
    print(f"   {url}\n")
    print(f"2. Etsy redirects to {settings.etsy_redirect_uri} with ?code=...&state=...")
    print("   The returned state is checked here automatically; a mismatch aborts.\n")
    print("   To finish the exchange on another machine instead:")
    print(f"   --verifier {verifier} --state {state}\n")

    try:
        raw = input("3. Paste the full redirect URL: ")
    except (EOFError, KeyboardInterrupt):
        print("\nAborted — nothing was connected.", file=sys.stderr)
        return 1

    code, returned_state = _parse_redirect(raw)
    _check_state(returned_state, state)
    tokens = exchange_code(code, verifier, settings)
    _print_tokens(tokens, tokens.get("scope") or scopes)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.etsy_connect",
        description="Connect the ClearGlass Etsy shop via OAuth2 PKCE (read-only setup; "
                    "all shop writes stay behind the approval gate).",
    )
    parser.add_argument("--status", action="store_true", help="report connection state and exit")
    parser.add_argument("--refresh", action="store_true", help="mint a new access token from the refresh token")
    parser.add_argument("--exchange", action="store_true", help="exchange a code obtained elsewhere")
    parser.add_argument("--code", help="authorization code, or the full redirect URL")
    parser.add_argument("--verifier", help="PKCE code_verifier from the authorize step")
    parser.add_argument("--state", help="state from the authorize step; verified against the redirect")
    parser.add_argument(
        "--scopes",
        default=",".join(REQUIRED_SCOPES),
        help="comma-separated OAuth scopes to request (default: the scopes this operator "
             "needs). Ignored by --refresh, which cannot widen the original grant.",
    )
    args = parser.parse_args(argv)
    scopes = tuple(s.strip() for s in args.scopes.split(",") if s.strip())

    try:
        if args.status:
            return _print_status()
        if args.refresh:
            settings = get_settings()
            tokens = refresh_access_token(settings=settings)
            # A refresh preserves the original grant, so report what was actually
            # granted — reporting the requested set would overstate the token.
            _print_tokens(tokens, _scopes_after_refresh(tokens, settings))
            return 0
        if args.exchange and not (args.code and args.verifier):
            parser.error("--exchange requires both --code and --verifier")
        return _run_consent_flow(scopes, args.code, args.verifier, args.state)
    except EtsyOAuthError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
