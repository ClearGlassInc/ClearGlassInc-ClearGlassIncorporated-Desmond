"""Stripe payments — checkout sessions, webhook verification, refunds.

Design goals:
- **Import-safe & testable** without the ``stripe`` package or a live key. The module reads
  config from the environment and implements Stripe's webhook-signature scheme with stdlib
  ``hmac`` so it can be unit-tested offline.
- **Mock mode**: when ``STRIPE_SECRET_KEY`` is unset the checkout call returns a deterministic
  mock session instead of hitting the network, so local/dev/CI never require credentials.
- The live path lazily imports ``stripe`` only when a key is present.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

PAYOUT_EVENT_TYPES = frozenset(
    {"payout.created", "payout.updated", "payout.paid", "payout.failed", "payout.canceled"}
)


def _secret_key() -> str:
    return os.environ.get("STRIPE_SECRET_KEY", "")


def _webhook_secret() -> str:
    return os.environ.get("STRIPE_WEBHOOK_SECRET", "")


def is_live() -> bool:
    """True when a real Stripe secret key is configured."""
    return bool(_secret_key())


def webhook_secret_set() -> bool:
    return bool(_webhook_secret())


def automatic_tax_enabled() -> bool:
    """Whether to ask Stripe Tax to calculate tax on each session.

    Off by default and opt-in per environment: Stripe rejects a session with
    ``automatic_tax`` when the account has no origin address or tax settings yet, so
    defaulting this on would break checkout for an account that has not finished the
    Tax setup. See ``STRIPE_SETUP.md``.
    """
    return os.environ.get("STRIPE_AUTOMATIC_TAX", "").strip().lower() in {"1", "true", "yes"}


def subscription_metadata(line_items: list[dict[str, Any]]) -> dict[str, str]:
    """Return the stable, non-sensitive metadata contract used by billing automation."""
    recurring = [item for item in line_items if item.get("interval")]
    plan = str(recurring[0].get("sku", "subscription")) if len(recurring) == 1 else "multi_plan"
    return {
        "source": "website",
        "business": "ClearGlassInc",
        "subscription_type": "recurring",
        "environment": "production" if _secret_key().startswith(("sk_live_", "rk_live_")) else "test",
        "billing_channel": "stripe",
        "customer_source": "direct_web",
        "integration_version": os.environ.get("STRIPE_INTEGRATION_VERSION", "v1")[:40],
        "plan": plan[:500],
        "product": str(recurring[0].get("product", "clearglass"))[:500] if recurring else "clearglass",
    }


def _with_session_placeholder(url: str) -> str:
    """Ensure the success URL carries Stripe's ``{CHECKOUT_SESSION_ID}`` template.

    The success page needs the session id to show a real confirmation. Fulfilment
    still hangs off the webhook — the redirect is not proof of payment and anyone can
    open it — but without the id the page cannot even look the order up.
    """
    if "{CHECKOUT_SESSION_ID}" in url:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}session_id={{CHECKOUT_SESSION_ID}}"


def create_checkout_session(
    line_items: list[dict[str, Any]],
    *,
    customer_email: str | None = None,
    success_url: str | None = None,
    cancel_url: str | None = None,
    checkout_mode: str = "payment",
    client_reference_id: str | None = None,
    idempotency_key: str | None = None,
    shipping_countries: list[str] | None = None,
    shipping_amount: int | None = None,
    shipping_label: str = "Standard shipping",
    extra_metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a Stripe Checkout session, or a deterministic mock when no key is set.

    ``line_items`` are **already priced** — see :mod:`app.pricebook`. Each item carries
    ``amount`` (cents), ``currency``, ``name`` and ``quantity``, and optionally ``sku``,
    ``description``, ``tax_behavior`` and ``interval``. This function never accepts an
    amount from a caller that got it from the browser.

    ``checkout_mode`` is Stripe's session mode (``payment`` or ``subscription``); the
    returned ``mode`` field is this module's live/mock indicator, which is a different
    thing and is kept for the existing storefront contract.
    """
    amount_total = sum(int(i.get("amount", 0)) * int(i.get("quantity", 1)) for i in line_items)
    # Stripe adds the shipping rate to the session total, so the mock must too —
    # otherwise mock mode quietly under-reports what a live session would charge.
    amount_total += int(shipping_amount or 0)
    success_url = success_url or os.environ.get("CHECKOUT_SUCCESS_URL", "http://localhost:3000/success")
    cancel_url = cancel_url or os.environ.get("CHECKOUT_CANCEL_URL", "http://localhost:3000/cancel")
    success_url = _with_session_placeholder(success_url)
    currency = (line_items[0].get("currency", "cad") if line_items else "cad")

    # A compact record of what was bought, so the webhook can reconstruct the order
    # without a second API round-trip. Stripe caps a metadata value at 500 chars.
    skus = ",".join(
        f"{i.get('sku') or i.get('name', 'item')}x{int(i.get('quantity', 1))}" for i in line_items
    )[:500]

    if not is_live():
        return {
            "id": f"cs_mock_{abs(hash((amount_total, customer_email))) % 10**10:010d}",
            "url": f"{success_url}?mock=1",
            "mode": "mock",
            "checkout_mode": checkout_mode,
            "amount_total": amount_total,
            "currency": currency,
        }

    import stripe  # noqa: PLC0415 — lazy import; only needed in live mode

    stripe.api_key = _secret_key()

    stripe_line_items = []
    for item in line_items:
        quantity = int(item.get("quantity", 1))

        # Preferred path: reference a real Stripe Price. Stripe then owns the amount,
        # currency, recurrence, tax behaviour and tax code, so there is exactly one
        # place a price lives and no local value can contradict what is charged.
        if item.get("stripe_price_id"):
            stripe_line_items.append(
                {"quantity": quantity, "price": item["stripe_price_id"]}
            )
            continue

        # Fallback for offers with no Stripe Price yet: build the price inline from
        # the price book. Still server-side, still not caller-supplied.
        price_data: dict[str, Any] = {
            "currency": item.get("currency", "cad"),
            "unit_amount": int(item.get("amount", 0)),
            "product_data": {"name": item.get("name", "item")},
        }
        if item.get("description"):
            price_data["product_data"]["description"] = item["description"]
        if item.get("tax_behavior"):
            price_data["tax_behavior"] = item["tax_behavior"]
        if checkout_mode == "subscription" and item.get("interval"):
            price_data["recurring"] = {"interval": item["interval"]}
        stripe_line_items.append({"quantity": quantity, "price_data": price_data})

    metadata = {"skus": skus, "source": "website", "business": "ClearGlassInc"}
    if checkout_mode == "subscription":
        metadata.update(subscription_metadata(line_items))
    if extra_metadata:
        # e.g. the bundle tier a Side Store cart earned, so reconciliation can
        # explain a discounted unit price months later.
        metadata.update({k: str(v)[:500] for k, v in extra_metadata.items()})
    params: dict[str, Any] = {
        "mode": checkout_mode,
        "customer_email": customer_email,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "line_items": stripe_line_items,
        "metadata": metadata,
        # Stripe Tax reads the customer's location from an address, and services
        # collect no shipping address — so the billing address is the only signal.
        "billing_address_collection": "required",
        "client_reference_id": client_reference_id,
    }
    # Physical goods need somewhere to go. Collecting the address here is the only
    # chance to get it: the webhook can read it off the session afterwards, but
    # nothing can invent it later, and a paid parcel with no destination is a
    # refund waiting to happen.
    if shipping_countries:
        params["shipping_address_collection"] = {"allowed_countries": shipping_countries}
    if shipping_amount is not None:
        params["shipping_options"] = [
            {
                "shipping_rate_data": {
                    "type": "fixed_amount",
                    "display_name": shipping_label,
                    "fixed_amount": {"amount": int(shipping_amount), "currency": currency},
                }
            }
        ]

    if automatic_tax_enabled():
        params["automatic_tax"] = {"enabled": True}
        params["customer_creation"] = "always"
    # Carry the metadata onto the object that outlives the session, so a refund or
    # dispute months later still says what was sold.
    if checkout_mode == "subscription":
        params["subscription_data"] = {"metadata": metadata}
    else:
        params["payment_intent_data"] = {"metadata": metadata}

    request_options: dict[str, Any] = {}
    if idempotency_key:
        # A retried or double-clicked checkout returns the original session instead
        # of opening a second one against the same cart.
        request_options["idempotency_key"] = idempotency_key

    session = stripe.checkout.Session.create(**params, **request_options)
    return {
        "id": session.id,
        "url": session.url,
        "mode": "live",
        "checkout_mode": checkout_mode,
        "amount_total": session.amount_total,
        "currency": session.currency,
    }


def create_billing_portal_session(checkout_session_id: str, return_url: str | None = None) -> dict[str, str]:
    """Open the hosted portal for the customer attached to a subscription Checkout session."""
    safe_return_url = return_url or os.environ.get(
        "STRIPE_PORTAL_RETURN_URL", "http://localhost:3000/account"
    )
    if not is_live():
        return {"url": f"{safe_return_url}?portal=mock", "mode": "mock"}

    import stripe  # noqa: PLC0415 — lazy import; only needed in live mode

    stripe.api_key = _secret_key()
    checkout = stripe.checkout.Session.retrieve(checkout_session_id)
    customer = getattr(checkout, "customer", None)
    if getattr(checkout, "mode", None) != "subscription" or not customer:
        raise ValueError("checkout session is not a customer-backed subscription")
    portal = stripe.billing_portal.Session.create(customer=customer, return_url=safe_return_url)
    return {"url": portal.url, "mode": "live"}


def payout_bank_info() -> dict[str, Any]:
    """Return the non-sensitive payout bank configuration exposed to operators.

    Real bank wiring is configured in Stripe/Apollo-managed secrets, not committed to this
    repository and not accepted over the API. The control plane only surfaces masked metadata
    so operators can confirm earned revenue is settling to the intended external account.
    """
    external_account_id = os.environ.get("PAYOUT_EXTERNAL_ACCOUNT_ID", "")
    last4 = os.environ.get("PAYOUT_BANK_LAST4", "")
    routing_hint = os.environ.get("PAYOUT_BANK_ROUTING_HINT", "")
    bank_name = os.environ.get("PAYOUT_BANK_NAME", "")
    country = os.environ.get("PAYOUT_BANK_COUNTRY", "CA")
    currencies = [
        c.strip().upper()
        for c in os.environ.get("PAYOUT_BANK_CURRENCIES", "CAD,USD").split(",")
        if c.strip()
    ]

    warnings: list[str] = []
    if not external_account_id:
        warnings.append(
            "PAYOUT_EXTERNAL_ACCOUNT_ID is not configured; "
            "payouts cannot be matched to a destination token."
        )
    elif not external_account_id.startswith(("ba_", "card_")):
        warnings.append(
            "PAYOUT_EXTERNAL_ACCOUNT_ID should be Stripe's opaque external-account token, "
            "not raw bank digits."
        )

    if last4 and (not last4.isdigit() or len(last4) != 4):
        warnings.append("PAYOUT_BANK_LAST4 must contain only the final four account digits.")
    if any(ch.isdigit() for ch in routing_hint):
        warnings.append(
            "PAYOUT_BANK_ROUTING_HINT must be a non-sensitive label, "
            "never a routing/transit number."
        )

    configured = bool(external_account_id and not warnings)
    return {
        "configured": configured,
        "processor": "stripe",
        "settlement_mode": "automatic_stripe_payouts",
        "external_account_id": external_account_id or None,
        "bank_name": bank_name or None,
        "account_last4": last4 or None,
        "routing_hint": routing_hint or None,
        "country": country,
        "currencies": currencies,
        "warnings": warnings,
    }


def parse_payout(obj: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Stripe ``payout`` object into the fields we persist.

    ``amount`` is converted from Stripe's integer cents to major units (dollars). ``destination``
    is kept as Stripe's opaque external-account token — no account/routing numbers are ever
    extracted or stored. ``arrival_date`` (unix seconds) becomes a tz-aware datetime.
    """
    raw_dest = obj.get("destination")
    # Stripe sometimes expands destination into an object; keep only its id token.
    destination = raw_dest.get("id") if isinstance(raw_dest, dict) else raw_dest

    arrival_ts = obj.get("arrival_date")
    arrival = (
        datetime.fromtimestamp(int(arrival_ts), tz=timezone.utc)
        if isinstance(arrival_ts, (int, float))
        else None
    )

    return {
        "stripe_payout_id": obj.get("id"),
        "amount": Decimal(str(obj.get("amount", 0))) / Decimal("100"),
        "currency": (obj.get("currency") or "cad").upper(),
        "status": obj.get("status") or "pending",
        "destination": destination,
        "arrival_date": arrival,
    }


def sign_payload(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    """Produce a Stripe-style ``Stripe-Signature`` header value (used in tests and dev tooling)."""
    ts = timestamp if timestamp is not None else int(time.time())
    signed = f"{ts}.".encode() + payload
    sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def verify_webhook(payload: bytes, sig_header: str, *, tolerance: int = 300) -> dict[str, Any]:
    """Verify a Stripe webhook signature and return ``{"verified": bool, "event": dict}``.

    When no webhook secret is configured (dev), the payload is parsed but marked unverified so
    callers can decide whether to accept it.
    """
    try:
        event = json.loads(payload.decode() or "{}")
    except (ValueError, UnicodeDecodeError):
        return {"verified": False, "event": {}, "reason": "unparseable payload"}

    secret = _webhook_secret()
    if not secret:
        return {"verified": False, "event": event, "reason": "no webhook secret configured"}

    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    ts, given = parts.get("t"), parts.get("v1")
    if not ts or not given:
        return {"verified": False, "event": event, "reason": "malformed signature header"}

    try:
        ts_int = int(ts)
    except ValueError:
        # Attacker-controlled header; a non-numeric timestamp is malformed, not a
        # server error. Fail closed with a clean rejection instead of raising.
        return {"verified": False, "event": event, "reason": "malformed signature header"}

    if tolerance and abs(int(time.time()) - ts_int) > tolerance:
        return {"verified": False, "event": event, "reason": "timestamp outside tolerance"}

    signed = f"{ts}.".encode() + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    verified = hmac.compare_digest(expected, given)
    return {"verified": verified, "event": event, "reason": "ok" if verified else "signature mismatch"}
