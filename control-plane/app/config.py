"""Environment-driven settings for the commerce control plane."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration, sourced from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "clearglass-commerce"
    log_level: str = "info"

    database_url: str = "postgresql+psycopg://commerce:commerce@localhost:5432/commerce"
    # Create tables from ORM metadata on startup (handy for SQLite/dev/demo; prod uses migrations).
    auto_create_tables: bool = False
    # Apply pending migrations/*.sql at startup (Postgres only; see app/migrate.py).
    # create_all never adds a column to an existing table, so without this a deployed
    # database drifts behind the ORM with every additive migration.
    run_migrations: bool = False
    # Comma-separated browser origins allowed to call the API (storefront/admin).
    cors_allow_origins: str = (
        "https://www.clearglassinc.com,"
        "https://clearglass-commerce-storefront.onrender.com,"
        "https://clearglass-commerce-admin.onrender.com,"
        "http://localhost:3000,http://localhost:3001"
    )

    # Governance
    require_approval_for_high_risk: bool = True
    inventory_low_threshold: int = 10

    # Admin authentication. The approval gate is only meaningful if not everyone can
    # open it, so mutating/administrative endpoints (approvals, pricing, refunds,
    # catalog writes) require a bearer token when this is set. Unset = open dev/mock
    # mode (consistent with no-Stripe-key mock payments); production must set it or the
    # app fails closed at startup. Comma-separated to allow rotation / per-operator keys.
    admin_api_key: str = ""

    # Per-client-IP sliding-window request limits (per minute); 0 disables a throttle.
    rate_limit_checkout_per_minute: int = 30
    rate_limit_webhook_per_minute: int = 240
    rate_limit_decisions_per_minute: int = 60
    # The public CRCS lead form, POST /revenue/leads.
    revenue_lead_rate_limit_per_minute: int = 30
    # Number of trusted reverse proxies in front of this service (Render/Cloudflare = 1).
    # 0 (default) = direct exposure: the throttles key on the TCP peer address.
    # >0 = read the caller from X-Forwarded-For, counting this many hops back from the
    # right, so only the entries *your* proxies appended are trusted. Leaving this at 0
    # behind a proxy is a real outage risk: every customer collapses into one bucket
    # keyed on the proxy's address, so one abusive caller 429s the whole storefront.
    trusted_proxy_hops: int = 0
    # Addresses/CIDRs the proxies above actually connect from. The hop count alone is
    # NOT enough to trust the header: a request arriving on any other ingress (a private
    # service address, an internal mesh, a directly reachable container port) has no
    # proxy appending the real peer, so the caller controls every hop and can rotate the
    # rightmost value to get a fresh throttle bucket per request. X-Forwarded-For is
    # therefore honoured only when the TCP peer matches this allowlist; every other peer
    # falls back to its own address, which fails toward over-throttling rather than
    # silent bypass. Unset = the header is never trusted.
    trusted_proxy_ips: str = ""

    # Payments (never logged, never echoed in responses)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""

    # ── PayPal Orders v2 (second customer-facing processor) ─────────────────
    # Unset client id/secret = mock mode: no order is created at PayPal and no
    # network call is made, mirroring the no-Stripe-key behaviour of payments.
    paypal_client_id: str = ""
    paypal_client_secret: str = ""     # never logged, never echoed
    # The id of the webhook subscription PayPal delivers to. Signature verification
    # is impossible without it, so an unset value means every PayPal notification is
    # refused — deliberately, since an unverified notification is indistinguishable
    # from a forged one and would otherwise book revenue on an anonymous POST.
    paypal_webhook_id: str = ""
    # Sandbox by default: going live is a deliberate, reviewable config change, not
    # something that happens the moment credentials appear.
    paypal_api_base: str = "https://api-m.sandbox.paypal.com"
    paypal_return_url: str = "http://localhost:3000/paypal/return"
    paypal_cancel_url: str = "http://localhost:3000/cancel"
    # Ask PayPal for the buyer's stored address. Needed for physical goods; off for
    # a services/digital catalogue, which should not collect an address it never uses.
    paypal_collect_shipping: bool = False

    escalation_email: str = "info@clearglassinc.com"
    slack_webhook_url: str = ""

    # Etsy Open API v3 connection (never logged; secrets are runtime env vars only).
    # A connection is "present" once keystring + access token are set; identity and
    # permissions are confirmed by a read-only verification call (see app/etsy.py).
    etsy_keystring: str = ""          # app API key (x-api-key header)
    etsy_shared_secret: str = ""      # OAuth app shared secret (never echoed)
    etsy_access_token: str = ""       # OAuth2 access token, format "<user_id>.<token>"
    etsy_refresh_token: str = ""      # OAuth2 refresh token (access tokens expire hourly)
    etsy_shop_id: str = ""            # numeric shop id; derived from the token if blank
    etsy_shop_name: str = ""          # declared shop name, cross-checked on verify
    etsy_login_email: str = ""        # declared Etsy account email (informational)
    # Public profile of the Etsy account this control plane is meant to operate. Purely
    # declarative: Etsy exposes no API to resolve a /people/ handle, so it documents
    # intent and is echoed back on /etsy/connection for the operator to eyeball against
    # the account the token actually resolves to.
    etsy_profile_url: str = "https://www.etsy.com/people/7is7jsngx568dcve"
    # Comma-separated OAuth scopes granted at token-exchange time.
    etsy_scopes: str = ""
    etsy_api_base: str = "https://openapi.etsy.com/v3"

    # OAuth2 (PKCE) handshake — see app/etsy_oauth.py and `python -m app.etsy_connect`.
    # The redirect URI must match a callback registered on the Etsy app exactly.
    etsy_redirect_uri: str = ""
    etsy_oauth_authorize_url: str = "https://www.etsy.com/oauth/connect"
    etsy_token_url: str = "https://api.etsy.com/v3/public/oauth/token"

    # ── Printful (print-on-demand fulfillment) ──────────────────────────────
    # Unset = mock mode: no supplier order is ever placed and no network call is
    # made, mirroring the no-Stripe-key behaviour of payments.
    printful_api_key: str = ""         # OAuth token, sent as `Authorization: Bearer`
    printful_store_id: str = ""        # required only on multi-store accounts
    printful_api_base: str = "https://api.printful.com"
    # Confirming a draft debits the Printful wallet and starts production, so it
    # is an ALWAYS_ESCALATE action gated on a human approval. This flag does NOT
    # bypass that gate — it exists so the admin surface can show operators
    # whether hands-off confirmation has been requested, and so enabling it is a
    # deliberate, reviewable change rather than a silent default.
    printful_auto_confirm: bool = False
    # Shared secret on the webhook URL Printful calls with shipment notices.
    printful_webhook_secret: str = ""

    # ClearGlass Revenue Command System (CRCS). Defaults mirror .env.example.
    # The first offer is priced from the server-side price book, never the request.
    crcs_first_offer_sku: str = "rapid-website-deployment-diagnostic"
    # Live purchase is refused (409) until the owner confirms price, refund policy,
    # delivery promise, payment route and support route. See
    # docs/REVENUE_COMMAND_SYSTEM.md.
    crcs_rapid_diagnostic_enabled: bool = False
    crcs_rapid_diagnostic_payment_link: str = ""
    crcs_calendar_booking_url: str = ""
    # HMAC key for the pseudonymous buyer reference written to the audit ledger
    # when a checkout has no lead. The ledger holds IDs, not email addresses
    # (docs/crcs/DATA_MODEL.md rule 1). Empty uses a fixed development key.
    crcs_audit_hash_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
