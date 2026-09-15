"""PayPal Orders v2 — server-priced orders, capture, and fail-closed webhooks.

The second customer-facing payment processor alongside Stripe, built to the same
three rules that make the Stripe path safe:

1. **The browser names SKUs, the server names prices.** :func:`create_order` is
   handed line items that :mod:`app.pricebook` already priced. Nothing a caller
   sent contributes to what PayPal is told to charge.
2. **A redirect is not a receipt.** PayPal returns the buyer to the site as soon
   as they approve, which happens *before* the money is captured — and
   ``CHECKOUT.ORDER.APPROVED`` means approved, not paid. Fulfillment starts only
   on a verified ``PAYMENT.CAPTURE.COMPLETED``; see :data:`SETTLED_EVENTS`.
3. **Unverified means unhandled.** :func:`verify_webhook` fails closed. Without a
   configured webhook id there is no way to tell a real notification from a forged
   one, so every event is reported unverified and the router refuses it, rather
   than booking revenue on an anonymous POST.

Like :mod:`app.printful` and :mod:`app.etsy`, every call takes an optional
``request`` transport so the whole module is testable offline, and like
:mod:`app.payments` it runs in **mock mode** with no credentials configured: no
network call is made and no order exists at PayPal.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid
from base64 import b64encode
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from .config import Settings, get_settings

#: ``(method, path, body, headers) -> (status_code, decoded_json_body)``
Requester = Callable[[str, str, Any, dict[str, str] | None], tuple[int, dict[str, Any]]]

#: The only event that means money arrived and a parcel may be sent.
CAPTURE_COMPLETED = "PAYMENT.CAPTURE.COMPLETED"

#: Events that settle a payment into the ledger, mapped to the resulting order status.
#: ``PENDING`` is deliberately booked as ``pending``: PayPal holds captures for
#: review, and treating a held capture as revenue reports money that may never land.
SETTLED_EVENTS: dict[str, str] = {
    CAPTURE_COMPLETED: "paid",
    "PAYMENT.CAPTURE.PENDING": "pending",
    "PAYMENT.CAPTURE.DENIED": "failed",
    "PAYMENT.CAPTURE.DECLINED": "failed",
}

#: Events that need a human but move no money on our side, mapped to the audit
#: action they are recorded under. Refunds and reversals run through the approval
#: gate like every other money-out action; they are never actioned from a webhook.
ATTENTION_EVENTS: dict[str, str] = {
    "PAYMENT.CAPTURE.REFUNDED": "refund_settled",
    "PAYMENT.CAPTURE.REVERSED": "capture_reversed",
    "CUSTOMER.DISPUTE.CREATED": "dispute_opened",
    "CUSTOMER.DISPUTE.RESOLVED": "dispute_closed",
    "CUSTOMER.DISPUTE.UPDATED": "dispute_updated",
    # Approval is the buyer clicking "Pay" — it is not payment, and it is recorded
    # only so an abandoned checkout is visible against the captures that followed.
    "CHECKOUT.ORDER.APPROVED": "paypal_order_approved",
}

#: Signature headers PayPal sends on every webhook. All are required: verification
#: without any one of them cannot be performed, so a missing header is a rejection.
REQUIRED_WEBHOOK_HEADERS = (
    "paypal-transmission-id",
    "paypal-transmission-time",
    "paypal-transmission-sig",
    "paypal-cert-url",
    "paypal-auth-algo",
)

#: Hosts the signing certificate may be fetched from. PayPal names the cert URL in
#: an attacker-reachable header, and it is handed to PayPal's verification API — so
#: it is checked against PayPal's own domains first rather than forwarded blindly.
TRUSTED_CERT_HOSTS = ("api.paypal.com", "api.sandbox.paypal.com", "www.paypal.com", "www.sandbox.paypal.com")


class PayPalError(RuntimeError):
    """A PayPal API call failed or returned something unusable."""


class PayPalNotConnected(PayPalError):
    """PayPal credentials are not configured; the store is in mock mode."""


def _missing_credentials(settings: Settings) -> bool:
    return not (settings.paypal_client_id and settings.paypal_client_secret)


def is_live(settings: Settings | None = None) -> bool:
    """True when a real PayPal client id and secret are configured."""
    return not _missing_credentials(settings or get_settings())


def webhook_id_set(settings: Settings | None = None) -> bool:
    """True when the webhook id needed to verify a notification is configured."""
    return bool((settings or get_settings()).paypal_webhook_id)


def connection_state(settings: Settings | None = None) -> dict[str, Any]:
    """Non-sensitive connection state for the operator surface.

    Credential *presence* only — no secret is echoed, and nothing here proves the
    credentials work. That is what :func:`verify_connection` is for.
    """
    settings = settings or get_settings()
    live = is_live(settings)
    warnings: list[str] = []
    if not live:
        warnings.append(
            "PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are unset: PayPal runs in mock mode "
            "and creates no real orders."
        )
    if live and not webhook_id_set(settings):
        warnings.append(
            "PAYPAL_WEBHOOK_ID is unset: webhook signatures cannot be verified, so every "
            "notification is refused and no PayPal payment will ever be booked."
        )
    if live and "sandbox" in settings.paypal_api_base:
        warnings.append("PAYPAL_API_BASE points at the sandbox; no real money will move.")
    return {
        "connected": live,
        "mode": "live" if live else "mock",
        "api_base": settings.paypal_api_base,
        "webhook_verification": "enabled" if webhook_id_set(settings) else "unconfigured",
        "warnings": warnings,
    }


def _decode_body(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PayPalError(f"PayPal returned a body that is not valid UTF-8: {exc}") from exc
    if not text.strip():
        return {}
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise PayPalError(f"PayPal returned a body that is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PayPalError(f"PayPal returned {type(payload).__name__}, expected a JSON object")
    return payload


def _default_requester(settings: Settings) -> Requester:
    """urllib-backed transport. Credentials travel in headers and are never logged."""

    def request(
        method: str, path: str, body: Any = None, headers: dict[str, str] | None = None
    ) -> tuple[int, dict[str, Any]]:
        url = f"{settings.paypal_api_base.rstrip('/')}{path}"
        if isinstance(body, (dict, list)):
            data: bytes | None = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            data = body.encode("utf-8")
        else:
            data = None
        req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.status, _decode_body(response.read())
        except urllib.error.HTTPError as exc:  # PayPal puts the reason in the body
            try:
                payload = _decode_body(exc.read())
            except (PayPalError, OSError):
                payload = {}
            return exc.code, payload
        except urllib.error.URLError as exc:
            raise PayPalError(f"could not reach PayPal: {exc.reason}") from exc
        except OSError as exc:  # socket timeouts and connection resets
            raise PayPalError(f"could not reach PayPal: {exc}") from exc

    return request


def _access_token(settings: Settings, request: Requester) -> str:
    """Exchange the client credentials for a short-lived OAuth2 access token.

    Deliberately not cached. A cached token is a credential held in process memory
    for hours and one more thing that can be stale at the worst moment; the token
    call is cheap next to the order call it precedes, and PayPal's own SDKs make it
    per-request too.
    """
    basic = b64encode(
        f"{settings.paypal_client_id}:{settings.paypal_client_secret}".encode()
    ).decode()
    status, payload = request(
        "POST",
        "/v1/oauth2/token",
        "grant_type=client_credentials",
        {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    token = payload.get("access_token")
    if status >= 400 or not token:
        # The body can echo the client id; report the status and PayPal's error
        # code only, never the payload.
        raise PayPalError(
            f"PayPal rejected the client credentials (HTTP {status}, "
            f"{payload.get('error', 'no error code')})"
        )
    return str(token)


def _call(
    settings: Settings,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    request: Requester | None = None,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Make one authenticated Orders-API call, raising on a non-2xx response."""
    if _missing_credentials(settings):
        raise PayPalNotConnected(
            "PayPal is not connected: set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET. "
            "Until then the store runs in mock mode and creates no PayPal orders."
        )
    requester = request or _default_requester(settings)
    headers = {
        "Authorization": f"Bearer {_access_token(settings, requester)}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    headers.update(extra_headers or {})
    status, payload = requester(method, path, body, headers)
    if status >= 400:
        raise PayPalError(
            f"PayPal {method} {path} failed (HTTP {status}): "
            f"{payload.get('name') or payload.get('message') or 'unknown error'}"
        )
    return payload


def _major_units(cents: int) -> str:
    """PayPal takes decimal strings ("49.99"), not Stripe's integer cents."""
    return f"{Decimal(cents) / Decimal(100):.2f}"


def sku_spec(line_items: list[dict[str, Any]]) -> str:
    """Compact ``sku x quantity`` record carried on the order as ``custom_id``.

    PayPal echoes ``custom_id`` back on the capture webhook, which is the only way
    the webhook can know what was bought without a second API round-trip — and the
    only way it can check the captured amount against the price book.
    """
    return ",".join(
        f"{item.get('sku', 'item')}x{int(item.get('quantity', 1))}" for item in line_items
    )[:127]  # PayPal caps custom_id at 127 characters


def parse_sku_spec(spec: str) -> list[dict[str, Any]]:
    """Inverse of :func:`sku_spec`. Unparseable entries are dropped, not guessed."""
    parsed: list[dict[str, Any]] = []
    for chunk in (spec or "").split(","):
        sku, separator, quantity = chunk.rpartition("x")
        if not separator or not sku or not quantity.isdigit():
            continue
        parsed.append({"sku": sku, "quantity": int(quantity)})
    return parsed


def create_order(
    line_items: list[dict[str, Any]],
    *,
    customer_email: str | None = None,
    return_url: str | None = None,
    cancel_url: str | None = None,
    request_id: str | None = None,
    settings: Settings | None = None,
    request: Requester | None = None,
) -> dict[str, Any]:
    """Create a PayPal order for an already-priced cart, or a deterministic mock.

    ``line_items`` come from :func:`app.pricebook.resolve_line_items`; each carries
    ``amount`` (cents), ``currency``, ``name`` and ``quantity``. The intent is
    ``CAPTURE``, so approval and capture are two distinct steps and neither is
    implied by the buyer returning to the site.
    """
    settings = settings or get_settings()
    if not line_items:
        raise PayPalError("a PayPal order needs at least one line item")

    currency = str(line_items[0].get("currency", "cad")).upper()
    mixed = {str(i.get("currency", "cad")).upper() for i in line_items}
    if len(mixed) > 1:
        raise PayPalError("a single PayPal order cannot mix currencies: " + ", ".join(sorted(mixed)))

    amount_total = sum(int(i.get("amount", 0)) * int(i.get("quantity", 1)) for i in line_items)
    spec = sku_spec(line_items)

    if _missing_credentials(settings):
        return {
            "id": f"PAYPAL-MOCK-{abs(hash((spec, amount_total))) % 10**10:010d}",
            "approve_url": f"{return_url or settings.paypal_return_url}?mock=1",
            "mode": "mock",
            "status": "CREATED",
            "amount_total": amount_total,
            "currency": currency,
        }

    items = [
        {
            "name": str(item.get("name", item.get("sku", "item")))[:127],
            "quantity": str(int(item.get("quantity", 1))),
            "unit_amount": {
                "currency_code": currency,
                "value": _major_units(int(item.get("amount", 0))),
            },
            "sku": str(item.get("sku", ""))[:127],
        }
        for item in line_items
    ]
    body: dict[str, Any] = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "custom_id": spec,
                "amount": {
                    "currency_code": currency,
                    "value": _major_units(amount_total),
                    "breakdown": {
                        "item_total": {
                            "currency_code": currency,
                            "value": _major_units(amount_total),
                        }
                    },
                },
                "items": items,
            }
        ],
        "payment_source": {
            "paypal": {
                "experience_context": {
                    "return_url": return_url or settings.paypal_return_url,
                    "cancel_url": cancel_url or settings.paypal_cancel_url,
                    "shipping_preference": (
                        "GET_FROM_FILE" if settings.paypal_collect_shipping else "NO_SHIPPING"
                    ),
                    # The buyer must take an explicit action to pay; nothing is
                    # captured as a side effect of approving.
                    "user_action": "PAY_NOW",
                }
            }
        },
    }
    if customer_email:
        body["payment_source"]["paypal"]["email_address"] = customer_email

    payload = _call(
        settings,
        "POST",
        "/v2/checkout/orders",
        body,
        request=request,
        # A double-clicked or retried create returns the original order instead of
        # opening a second one for the same cart.
        extra_headers={"PayPal-Request-Id": request_id or str(uuid.uuid4())},
    )
    approve = next(
        (link.get("href") for link in payload.get("links", []) if link.get("rel") in {"approve", "payer-action"}),
        None,
    )
    if not approve:
        raise PayPalError("PayPal created the order but returned no approval link")
    return {
        "id": str(payload.get("id", "")),
        "approve_url": approve,
        "mode": "live",
        "status": str(payload.get("status", "CREATED")),
        "amount_total": amount_total,
        "currency": currency,
    }


def capture_order(
    paypal_order_id: str,
    *,
    request_id: str | None = None,
    settings: Settings | None = None,
    request: Requester | None = None,
) -> dict[str, Any]:
    """Capture an approved order. This is the call that takes the money.

    Idempotent at PayPal via ``PayPal-Request-Id``, so a retried capture returns
    the original result instead of charging twice. The resulting order row is still
    booked by the webhook, not here: the capture response and the webhook carry the
    same capture id, so whichever arrives first books it and the other is a
    no-op — and a capture whose response is lost in transit is not a lost sale.
    """
    settings = settings or get_settings()
    if _missing_credentials(settings):
        return {"id": paypal_order_id, "status": "COMPLETED", "mode": "mock", "captures": []}

    payload = _call(
        settings,
        "POST",
        f"/v2/checkout/orders/{urllib.parse.quote(paypal_order_id, safe='')}/capture",
        {},
        request=request,
        extra_headers={"PayPal-Request-Id": request_id or f"capture-{paypal_order_id}"},
    )
    captures = [
        capture
        for unit in payload.get("purchase_units", [])
        for capture in (unit.get("payments") or {}).get("captures", [])
    ]
    return {
        "id": str(payload.get("id", paypal_order_id)),
        "status": str(payload.get("status", "")),
        "mode": "live",
        "captures": captures,
    }


def cert_url_is_trusted(cert_url: str) -> bool:
    """True when the signing certificate is being fetched from PayPal itself.

    The cert URL arrives in a header anyone can set. PayPal's verification API is
    what ultimately validates the signature, but handing it an arbitrary URL makes
    this service a request forwarder for whatever an attacker names, so the host is
    checked against PayPal's own domains before the URL goes anywhere.
    """
    try:
        parsed = urllib.parse.urlparse(cert_url)
    except ValueError:
        return False
    if parsed.scheme != "https":
        return False
    # Compare the host exactly: a suffix match would accept api.paypal.com.evil.test.
    return parsed.hostname in TRUSTED_CERT_HOSTS


def verify_webhook(
    payload: bytes,
    headers: dict[str, str],
    *,
    settings: Settings | None = None,
    request: Requester | None = None,
) -> dict[str, Any]:
    """Verify a PayPal webhook and return ``{"verified", "event", "reason"}``.

    Fails closed at every step. PayPal signs with a certificate chain rather than a
    shared secret, and the supported way to check it is PayPal's own
    ``verify-webhook-signature`` API — so verification requires working credentials
    *and* a configured webhook id. Where either is missing this returns
    ``verified=False`` with the reason, and the caller refuses the event. There is
    no development shortcut that accepts an unverified PayPal event: unlike a
    signature we compute ourselves, there is nothing to fall back to.
    """
    settings = settings or get_settings()
    lowered = {key.lower(): value for key, value in headers.items()}

    try:
        event = json.loads(payload.decode() or "{}")
    except (ValueError, UnicodeDecodeError):
        return {"verified": False, "event": {}, "reason": "unparseable payload"}
    if not isinstance(event, dict):
        return {"verified": False, "event": {}, "reason": "payload is not a JSON object"}

    missing = [header for header in REQUIRED_WEBHOOK_HEADERS if not lowered.get(header)]
    if missing:
        return {"verified": False, "event": event, "reason": f"missing headers: {', '.join(missing)}"}

    if not webhook_id_set(settings):
        return {"verified": False, "event": event, "reason": "no webhook id configured"}
    if _missing_credentials(settings):
        return {"verified": False, "event": event, "reason": "no PayPal credentials configured"}

    cert_url = lowered["paypal-cert-url"]
    if not cert_url_is_trusted(cert_url):
        return {"verified": False, "event": event, "reason": "certificate url is not a PayPal host"}

    body = {
        "transmission_id": lowered["paypal-transmission-id"],
        "transmission_time": lowered["paypal-transmission-time"],
        "cert_url": cert_url,
        "auth_algo": lowered["paypal-auth-algo"],
        "transmission_sig": lowered["paypal-transmission-sig"],
        "webhook_id": settings.paypal_webhook_id,
        # PayPal re-serializes this to check the signature, so it must be the event
        # as an object — not the raw bytes, and not a re-encoded string.
        "webhook_event": event,
    }
    try:
        result = _call(
            settings,
            "POST",
            "/v1/notifications/verify-webhook-signature",
            body,
            request=request,
        )
    except PayPalError as exc:
        # An unreachable or unhappy verification API means we cannot tell a real
        # event from a forged one. That is a rejection, not a pass.
        return {"verified": False, "event": event, "reason": f"verification call failed: {exc}"}

    verified = result.get("verification_status") == "SUCCESS"
    return {
        "verified": verified,
        "event": event,
        "reason": "ok" if verified else f"verification_status={result.get('verification_status')!r}",
    }


def capture_amount(resource: dict[str, Any]) -> tuple[Decimal, str]:
    """Pull ``(amount, currency)`` off a capture resource.

    Raises :class:`PayPalError` rather than defaulting to zero: an unreadable
    amount on a settlement event is a reconciliation failure, and booking it as
    0.00 would hide a real payment behind a plausible-looking row.
    """
    amount = resource.get("amount") or {}
    try:
        value = Decimal(str(amount.get("value")))
    except (InvalidOperation, TypeError) as exc:
        raise PayPalError(f"capture has an unreadable amount: {amount.get('value')!r}") from exc
    currency = str(amount.get("currency_code") or "CAD").upper()
    return value, currency


def shipping_from_capture(resource: dict[str, Any]) -> dict[str, Any]:
    """Normalize a capture's destination address for the shared order ledger.

    PayPal nests the address under ``shipping.address`` with ``address_line_1`` /
    ``admin_area_1`` naming; the ledger stores one shape regardless of processor.
    """
    shipping = resource.get("shipping") or {}
    address = shipping.get("address") or {}
    name = (shipping.get("name") or {}).get("full_name")
    payer = resource.get("payer") or {}
    return {
        "name": name or (payer.get("name") or {}).get("given_name"),
        "address1": address.get("address_line_1"),
        "address2": address.get("address_line_2"),
        "city": address.get("admin_area_2"),
        "state_code": address.get("admin_area_1"),
        "country_code": (address.get("country_code") or "").upper() or None,
        "zip": address.get("postal_code"),
        "email": shipping.get("email_address") or payer.get("email_address"),
    }


def check_against_catalog(
    custom_id: str, amount: Decimal, currency: str
) -> tuple[bool, str]:
    """Re-price the captured cart from the price book and compare what was paid.

    Returns ``(matches, explanation)``. This is the control that makes a PayPal
    capture trustworthy: the amount on the webhook is whatever PayPal says was
    charged, and the ``custom_id`` naming the SKUs is the only link back to what
    the business actually offered. A mismatch is not fatal to the *payment* — the
    money has already moved and cannot be un-received — but it must stop
    fulfillment and reach a human, which is what the caller does with a ``False``.

    An empty or unparseable ``custom_id`` fails the check. An order that cannot be
    tied to a catalogue entry is exactly the case that must not auto-ship.
    """
    from . import pricebook  # local import: keeps this module importable without the price book

    items = parse_sku_spec(custom_id)
    if not items:
        return False, f"capture carries no recognizable catalogue reference (custom_id={custom_id!r})"

    try:
        line_items, _mode = pricebook.resolve_line_items(items)
    except pricebook.PricebookError as exc:
        return False, f"capture references something the catalogue will not sell: {exc}"

    expected_cents = sum(int(i["amount"]) * int(i["quantity"]) for i in line_items)
    expected = (Decimal(expected_cents) / Decimal(100)).quantize(Decimal("0.01"))
    paid = amount.quantize(Decimal("0.01"))
    expected_currency = str(line_items[0]["currency"]).upper()

    if expected_currency != currency.upper():
        return False, f"currency mismatch: catalogue prices in {expected_currency}, captured {currency}"
    if expected != paid:
        return False, f"amount mismatch: catalogue total {expected} {expected_currency}, captured {paid}"
    return True, f"matches catalogue total {expected} {expected_currency}"
