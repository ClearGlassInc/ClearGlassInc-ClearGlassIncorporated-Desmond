"""Printful connector — print-on-demand catalogue, order routing, and tracking.

This is the fulfillment supplier: ClearGlass sells, Printful prints and ships.
That makes it the one integration that can spend money and put a physical parcel
in front of a customer, so the safety model is deliberate:

* **Reads are free.** Connection detection is offline (credential presence only).
  Catalogue and order-status reads touch the network but change nothing.
* **A draft order is not a purchase.** ``create_draft_order`` posts with
  ``confirm=0``. Printful holds it, charges nothing, prints nothing, and the
  draft can be deleted. That is why booking a draft when a customer pays is an
  auto-executable action — it costs nothing and losing it costs an order.
* **Confirmation is the money.** ``confirm_order`` is what debits the Printful
  wallet and starts production. It is in ``ALWAYS_ESCALATE`` and cannot run
  without a human approval row, by design.

Never invent product data here. Everything a customer sees — the image, the
price, the variant, the shipping estimate — comes from Printful's own response.
A catalogue this module cannot read is a catalogue that does not get published.

The HTTP layer is stdlib ``urllib`` so the module needs no extra dependency and
is trivially testable by injecting a ``request`` callable (no network in tests).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from .config import Settings, get_settings

#: Credentials without which no connection is possible.
REQUIRED_CREDENTIALS = ("printful_api_key",)

#: A requester takes (method, path, body) and returns (status, decoded json).
Requester = Callable[[str, str, "dict[str, Any] | None"], "tuple[int, dict[str, Any]]"]

#: Printful rejects an order with no destination country; these are the minimum
#: fields its address validator needs for every supported country.
REQUIRED_RECIPIENT_FIELDS = ("name", "address1", "city", "country_code", "zip")

#: Countries where Printful additionally requires a state/province code.
STATE_REQUIRED_COUNTRIES = frozenset({"US", "CA", "AU"})


class PrintfulError(RuntimeError):
    """A Printful call failed, or returned something this module will not act on."""


class PrintfulNotConnected(PrintfulError):
    """No Printful credential is configured, so no live call is possible."""


def _missing_credentials(settings: Settings) -> list[str]:
    labels = {"printful_api_key": "printful_api_key (Printful OAuth token)"}
    return [labels[name] for name in REQUIRED_CREDENTIALS if not getattr(settings, name, "")]


def connection_status(settings: Settings | None = None) -> dict[str, Any]:
    """Detect connection state **offline** — credential presence, no network call.

    ``verified`` is always ``False`` here; a live identity check is
    :func:`verify_connection`. Mirrors the Etsy connector so the admin surface
    can treat every supplier the same way.
    """
    settings = settings or get_settings()
    missing = _missing_credentials(settings)
    return {
        "supplier": "printful",
        "connected": not missing,
        "verified": False,
        "missing": missing,
        "store_id": settings.printful_store_id or None,
        "auto_confirm": bool(settings.printful_auto_confirm),
        "mode": "live" if not missing else "mock",
    }


def _decode_body(raw: bytes) -> dict[str, Any]:
    """Decode a response body into a JSON object, or raise ``PrintfulError``.

    A 200 carrying truncated JSON or invalid UTF-8 must not escape as a bare
    ``ValueError``: callers catch ``PrintfulError`` to turn a failed booking into
    a recorded ``unfulfillable`` obligation, and anything else propagates out,
    rolls the transaction back, and leaves a paid order looking untouched.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PrintfulError(f"Printful returned a body that is not valid UTF-8: {exc}") from exc
    if not text.strip():
        return {}
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise PrintfulError(f"Printful returned a body that is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PrintfulError(f"Printful returned {type(payload).__name__}, expected a JSON object")
    return payload


def _default_requester(settings: Settings) -> Requester:
    """urllib-backed transport. The token goes in a header and is never logged."""

    def request(method: str, path: str, body: dict[str, Any] | None) -> tuple[int, dict[str, Any]]:
        url = f"{settings.printful_api_base.rstrip('/')}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {
            "Authorization": f"Bearer {settings.printful_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "clearglass-commerce/1.0",
        }
        if settings.printful_store_id:
            headers["X-PF-Store-Id"] = settings.printful_store_id
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310 - fixed https base
                raw = response.read()
                return response.status, _decode_body(raw)
        except urllib.error.HTTPError as exc:  # Printful puts the reason in the body
            try:
                payload = _decode_body(exc.read())
            except (PrintfulError, OSError):
                payload = {}
            return exc.code, payload
        except urllib.error.URLError as exc:
            raise PrintfulError(f"could not reach Printful: {exc.reason}") from exc
        except OSError as exc:  # socket timeouts and connection resets
            raise PrintfulError(f"could not reach Printful: {exc}") from exc

    return request


def _call(
    settings: Settings,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    request: Requester | None = None,
) -> dict[str, Any]:
    """Make one API call and unwrap Printful's ``{code, result}`` envelope."""
    if _missing_credentials(settings):
        raise PrintfulNotConnected(
            "Printful is not connected: set PRINTFUL_API_KEY. "
            "Until then the store runs in mock mode and places no supplier orders."
        )
    requester = request or _default_requester(settings)
    status, payload = requester(method, path, body)
    if status >= 400:
        error = payload.get("error") or {}
        reason = error.get("message") or error.get("reason") or payload.get("result") or "unknown error"
        raise PrintfulError(f"Printful {method} {path} failed (HTTP {status}): {reason}")
    result = payload.get("result")
    return result if isinstance(result, dict) else {"items": result}


def verify_connection(
    settings: Settings | None = None,
    request: Requester | None = None,
) -> dict[str, Any]:
    """Read-only identity check against ``GET /store``. Writes nothing."""
    settings = settings or get_settings()
    status = connection_status(settings)
    if not status["connected"]:
        return status

    try:
        result = _call(settings, "GET", "/store", None, request)
    except PrintfulError as exc:
        return {**status, "verified": False, "error": str(exc)}

    return {
        **status,
        "verified": True,
        "store_id": str(result.get("id") or settings.printful_store_id or ""),
        "store_name": result.get("name"),
        "website": result.get("website"),
        "currency": (result.get("currency") or "").upper() or None,
    }


def _decimal(value: Any) -> Decimal | None:
    """Printful sends money as decimal strings; refuse anything else.

    ``Decimal`` happily accepts ``"NaN"`` and ``"Infinity"``. The first makes the
    comparison below raise, and the second would sail through as a valid price —
    so finiteness is checked before anything else. A price is a finite number or
    it is not a price.
    """
    if value is None or value == "":
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not amount.is_finite():
        return None
    return amount if amount >= 0 else None


def normalize_sync_product(raw: dict[str, Any], variants: list[dict[str, Any]]) -> dict[str, Any]:
    """Turn one Printful sync product + its variants into a catalogue entry.

    Every field is copied from Printful's response. Nothing is defaulted,
    inferred, or filled in: a variant with no retail price is reported as having
    no price rather than being given one, because the alternative is publishing a
    number the supplier never quoted.
    """
    normalized_variants: list[dict[str, Any]] = []
    for variant in variants:
        retail = _decimal(variant.get("retail_price"))
        cost = _decimal((variant.get("product") or {}).get("price")) or _decimal(variant.get("price"))
        files = variant.get("files") or []
        preview = next(
            (f.get("preview_url") for f in files if f.get("type") == "preview" and f.get("preview_url")),
            None,
        )
        normalized_variants.append(
            {
                "sync_variant_id": variant.get("id"),
                "catalog_variant_id": variant.get("variant_id"),
                "name": variant.get("name"),
                "sku": variant.get("sku"),
                "retail_price": str(retail) if retail is not None else None,
                "supplier_cost": str(cost) if cost is not None else None,
                "currency": (variant.get("currency") or "").upper() or None,
                "image": preview,
                "available": variant.get("availability_status") in (None, "active"),
            }
        )

    return {
        "supplier": "printful",
        "sync_product_id": raw.get("id"),
        "external_id": raw.get("external_id"),
        "name": raw.get("name"),
        "image": raw.get("thumbnail_url"),
        "variant_count": raw.get("variants"),
        "variants": normalized_variants,
    }


def store_products(
    settings: Settings | None = None,
    request: Requester | None = None,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Read the products configured in the Printful store, with their variants.

    Read-only. Follows Printful's ``offset``/``limit`` paging to the end rather
    than taking the first page, so a store larger than one page does not silently
    import as a partial catalogue.
    """
    settings = settings or get_settings()
    products: list[dict[str, Any]] = []
    offset = 0

    while True:
        page = _call(settings, "GET", f"/store/products?offset={offset}&limit={limit}", None, request)
        items = page.get("items") if isinstance(page.get("items"), list) else []
        if not items:
            break
        for summary in items:
            product_id = summary.get("id")
            if product_id is None:
                continue
            detail = _call(settings, "GET", f"/store/products/{product_id}", None, request)
            products.append(
                normalize_sync_product(
                    detail.get("sync_product") or summary,
                    detail.get("sync_variants") or [],
                )
            )
        offset += len(items)
        if len(items) < limit:
            break

    return products


def validate_recipient(recipient: dict[str, Any]) -> list[str]:
    """Return the problems that would make Printful reject this address.

    Checked before the order is booked rather than after: a rejected address
    discovered at confirmation time means a paid customer and no parcel.
    """
    problems: list[str] = []
    for field in REQUIRED_RECIPIENT_FIELDS:
        if not str(recipient.get(field) or "").strip():
            problems.append(f"missing {field}")

    country = str(recipient.get("country_code") or "").strip().upper()
    if country and len(country) != 2:
        problems.append(f"country_code must be a 2-letter ISO code, got {country!r}")
    if country in STATE_REQUIRED_COUNTRIES and not str(recipient.get("state_code") or "").strip():
        problems.append(f"{country} orders require a state_code")
    return problems


def build_order_payload(
    *,
    external_id: str,
    recipient: dict[str, Any],
    items: list[dict[str, Any]],
    currency: str,
) -> dict[str, Any]:
    """Assemble the Printful order body. Pure — no network, no settings.

    Splitting this out is what lets the tests assert the exact shape that would
    be sent for a given cart without a credential or a live store.
    """
    problems = validate_recipient(recipient)
    if problems:
        raise PrintfulError(f"recipient address is not deliverable: {'; '.join(problems)}")
    if not items:
        raise PrintfulError("order has no items")

    line_items: list[dict[str, Any]] = []
    for item in items:
        sync_variant_id = item.get("sync_variant_id")
        if not sync_variant_id:
            raise PrintfulError(f"line item {item!r} has no sync_variant_id — cannot be fulfilled")
        quantity = item.get("quantity")
        if not isinstance(quantity, int) or quantity < 1:
            raise PrintfulError(f"line item {sync_variant_id} has a non-positive quantity {quantity!r}")
        line = {"sync_variant_id": sync_variant_id, "quantity": quantity}
        retail = _decimal(item.get("retail_price"))
        if retail is not None:
            # Printful prints this on the customs form and the packing slip, so it
            # must be what the customer actually paid.
            line["retail_price"] = str(retail)
        line_items.append(line)

    return {
        "external_id": external_id,
        "recipient": {
            key: str(recipient[key]).strip()
            for key in ("name", "address1", "address2", "city", "state_code", "country_code", "zip", "email", "phone")
            if recipient.get(key)
        },
        "items": line_items,
        "retail_costs": {"currency": currency.upper()},
    }


def estimate_shipping(
    recipient: dict[str, Any],
    items: list[dict[str, Any]],
    currency: str,
    settings: Settings | None = None,
    request: Requester | None = None,
) -> list[dict[str, Any]]:
    """Ask Printful what shipping actually costs and how long it takes.

    Read-only. The delivery estimates it returns are the only ones fit to show a
    customer — a made-up "ships in 3-5 days" is a promise nobody has made.
    """
    settings = settings or get_settings()
    body = {
        "recipient": {k: v for k, v in recipient.items() if v},
        "items": [
            {"variant_id": i.get("catalog_variant_id") or i.get("sync_variant_id"), "quantity": i.get("quantity", 1)}
            for i in items
        ],
        "currency": currency.upper(),
    }
    result = _call(settings, "POST", "/shipping/rates", body, request)
    rates = result.get("items") if isinstance(result.get("items"), list) else []
    return [
        {
            "id": rate.get("id"),
            "name": rate.get("name"),
            "rate": rate.get("rate"),
            "currency": (rate.get("currency") or currency).upper(),
            "min_delivery_days": rate.get("minDeliveryDays"),
            "max_delivery_days": rate.get("maxDeliveryDays"),
        }
        for rate in rates
    ]


def create_draft_order(
    *,
    external_id: str,
    recipient: dict[str, Any],
    items: list[dict[str, Any]],
    currency: str,
    settings: Settings | None = None,
    request: Requester | None = None,
) -> dict[str, Any]:
    """Book the order with Printful as a **draft** (``confirm=0``).

    Charges nothing and prints nothing. Idempotent on ``external_id``: Printful
    rejects a duplicate, and the caller treats that as "already booked" rather
    than as a failure, so a webhook redelivery cannot double-order.
    """
    settings = settings or get_settings()
    payload = build_order_payload(
        external_id=external_id, recipient=recipient, items=items, currency=currency
    )
    try:
        result = _call(settings, "POST", "/orders?confirm=0", payload, request)
    except PrintfulError as exc:
        if "external_id" in str(exc).lower() and "exist" in str(exc).lower():
            existing = order_status(external_id, settings=settings, request=request)
            return {**existing, "already_booked": True}
        raise
    return summarize_order(result)


def confirm_order(
    printful_order_id: int | str,
    settings: Settings | None = None,
    request: Requester | None = None,
) -> dict[str, Any]:
    """Confirm a draft for fulfillment. **This spends money and starts printing.**

    Gated: the action name is in ``ALWAYS_ESCALATE``, so it only runs from an
    approved approval row. Never call it directly from a webhook.
    """
    settings = settings or get_settings()
    result = _call(settings, "POST", f"/orders/{printful_order_id}/confirm", None, request)
    return summarize_order(result)


def order_status(
    external_id: str,
    settings: Settings | None = None,
    request: Requester | None = None,
) -> dict[str, Any]:
    """Read one order's state and tracking. Read-only.

    Looked up by our own ``external_id`` (the Stripe checkout-session id), so the
    lookup works before we have stored Printful's id.
    """
    settings = settings or get_settings()
    result = _call(settings, "GET", f"/orders/@{external_id}", None, request)
    return summarize_order(result)


def summarize_order(result: dict[str, Any]) -> dict[str, Any]:
    """Flatten a Printful order into the fields the control plane stores."""
    shipments = result.get("shipments") or []
    first = shipments[0] if shipments else {}
    costs = result.get("costs") or {}
    return {
        "supplier": "printful",
        "supplier_order_id": str(result.get("id")) if result.get("id") is not None else None,
        "external_id": result.get("external_id"),
        "status": result.get("status"),
        "shipping_service": result.get("shipping"),
        "supplier_cost": costs.get("total"),
        "currency": (costs.get("currency") or "").upper() or None,
        "tracking_number": first.get("tracking_number"),
        "tracking_url": first.get("tracking_url"),
        "carrier": first.get("carrier"),
        "shipped_at": first.get("ship_date"),
        "already_booked": False,
    }


def parse_shipment_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract tracking from a ``package_shipped`` webhook. Pure.

    Raises rather than returning a half-filled record: a shipment notice with no
    order reference cannot be matched to a customer, and guessing which order it
    belongs to would email the wrong person a tracking number.
    """
    event = payload.get("type")
    if event != "package_shipped":
        raise PrintfulError(f"not a package_shipped event: {event!r}")

    data = payload.get("data") or {}
    order = data.get("order") or {}
    shipment = data.get("shipment") or {}
    external_id = order.get("external_id")
    if not external_id:
        raise PrintfulError("package_shipped carries no order.external_id — cannot match an order")

    # Identity of this *parcel*. A split order sends one notice per parcel with
    # the same order id, so the shipment id is what keeps them apart. Printful
    # does not always populate it; the tracking number is the natural fallback,
    # being unique per parcel by definition.
    shipment_id = shipment.get("id") or shipment.get("tracking_number")

    return {
        "supplier": "printful",
        "external_id": str(external_id),
        "supplier_order_id": str(order.get("id")) if order.get("id") is not None else None,
        "supplier_shipment_id": str(shipment_id) if shipment_id is not None else None,
        "status": "shipped",
        "tracking_number": shipment.get("tracking_number"),
        "tracking_url": shipment.get("tracking_url"),
        "carrier": shipment.get("carrier"),
        "service": shipment.get("service"),
        "shipped_at": shipment.get("ship_date"),
    }
