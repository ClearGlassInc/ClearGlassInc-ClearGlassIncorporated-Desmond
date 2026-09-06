"""Server-side price authority for checkout.

The storefront names *what* the customer wants to buy (a SKU and a quantity). This
module decides *what it costs*. That split is the whole point: a price that arrives
from the browser is a price the buyer can edit, and `/checkout/session` hands its
line items straight to Stripe. Resolving amounts here means a tampered request fails
with a 400 instead of charging a self-selected amount.

Stdlib-only (like ``governance.py`` and ``daily_loop.py``) so it imports in the
minimal CI environments that run the governance gate without the web stack.

The price book ships in the image at ``app/data/pricebook.json`` and can be pointed
elsewhere with ``PRICEBOOK_PATH`` for staging or per-tenant catalogues.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_PRICEBOOK = Path(__file__).parent / "data" / "pricebook.json"

#: Offer kinds that Stripe bills once. Anything else recurs.
ONE_TIME_KINDS = frozenset({"one_time", "deposit"})

#: Recurring intervals Stripe accepts on a price.
VALID_INTERVALS = frozenset({"day", "week", "month", "year"})


class PricebookError(ValueError):
    """A checkout request that the price book refuses to price.

    Raised for unknown/inactive SKUs, out-of-range quantities and carts Stripe
    cannot represent in a single session. Callers translate this into a 400 —
    these are all client mistakes, not server faults.
    """


@dataclass(frozen=True)
class Offer:
    """One purchasable thing, at the price the business set.

    ``stripe_price_id`` points at a real Stripe Price. When it is set, live checkout
    passes that id to Stripe instead of an inline amount, which makes the Price the
    single source of truth for what is charged — ``amount`` below is then display and
    mock-mode arithmetic only, and drift between the two cannot overcharge anyone.
    """

    sku: str
    name: str
    description: str
    amount: int          # unit price in the smallest currency unit (cents)
    currency: str        # lowercase ISO-4217, as Stripe expects
    kind: str            # one_time | deposit | recurring
    max_quantity: int
    tax_behavior: str    # exclusive | inclusive — required when Stripe Tax is on
    interval: str | None = None            # recurring only
    stripe_price_id: str | None = None     # authoritative price in live mode
    stripe_product_id: str | None = None   # informational; for reconciliation
    active: bool = True

    @property
    def recurring(self) -> bool:
        return self.kind not in ONE_TIME_KINDS


def _parse_offer(raw: dict[str, Any]) -> Offer:
    sku = str(raw.get("sku", "")).strip()
    if not sku:
        raise PricebookError("price book entry is missing a sku")

    kind = str(raw.get("kind", "one_time"))
    interval = raw.get("interval")
    if kind not in ONE_TIME_KINDS:
        if interval not in VALID_INTERVALS:
            raise PricebookError(f"{sku}: recurring offer needs a valid interval, got {interval!r}")
    else:
        interval = None

    amount = int(raw.get("amount", 0))
    if amount <= 0:
        raise PricebookError(f"{sku}: amount must be a positive integer of cents")

    return Offer(
        sku=sku,
        name=str(raw.get("name", sku)),
        description=str(raw.get("description", "")),
        amount=amount,
        currency=str(raw.get("currency", "cad")).lower(),
        kind=kind,
        max_quantity=max(1, int(raw.get("max_quantity", 1))),
        tax_behavior=str(raw.get("tax_behavior", "exclusive")),
        interval=interval,
        stripe_price_id=raw.get("stripe_price_id") or None,
        stripe_product_id=raw.get("stripe_product_id") or None,
        active=bool(raw.get("active", True)),
    )


def _pricebook_path() -> Path:
    override = os.environ.get("PRICEBOOK_PATH", "").strip()
    return Path(override) if override else DEFAULT_PRICEBOOK


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Offer]:
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)

    offers: dict[str, Offer] = {}
    for raw in document.get("offers", []):
        offer = _parse_offer(raw)
        if offer.sku in offers:
            raise PricebookError(f"duplicate sku in price book: {offer.sku}")
        offers[offer.sku] = offer
    return offers


def all_offers(*, include_inactive: bool = False) -> list[Offer]:
    """Every offer in the price book, in file order."""
    offers = _load(str(_pricebook_path())).values()
    return [o for o in offers if include_inactive or o.active]


def get_offer(sku: str) -> Offer:
    """Look up one offer, or raise :class:`PricebookError`."""
    offers = _load(str(_pricebook_path()))
    offer = offers.get(sku)
    if offer is None:
        raise PricebookError(f"unknown sku: {sku!r}")
    if not offer.active:
        raise PricebookError(f"sku is not currently for sale: {sku!r}")
    return offer


def reload() -> None:
    """Drop the cached price book (tests, and after a deploy-time swap)."""
    _load.cache_clear()


def resolve_line_items(requested: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    """Turn ``[{"sku": ..., "quantity": ...}]`` into priced Stripe line items.

    Returns the line items alongside the Stripe Checkout ``mode`` the cart implies
    (``payment`` or ``subscription``). Every amount comes from the price book; nothing
    the caller supplied contributes to what the customer is charged.
    """
    if not requested:
        raise PricebookError("checkout requires at least one line item")

    line_items: list[dict[str, Any]] = []
    currencies: set[str] = set()
    recurring = 0

    for entry in requested:
        offer = get_offer(str(entry.get("sku", "")))
        quantity = int(entry.get("quantity", 1))
        if quantity < 1:
            raise PricebookError(f"{offer.sku}: quantity must be at least 1")
        if quantity > offer.max_quantity:
            raise PricebookError(
                f"{offer.sku}: quantity {quantity} exceeds the maximum of {offer.max_quantity}"
            )

        currencies.add(offer.currency)
        recurring += 1 if offer.recurring else 0
        line_items.append(
            {
                "sku": offer.sku,
                "name": offer.name,
                "description": offer.description,
                "amount": offer.amount,
                "currency": offer.currency,
                "quantity": quantity,
                "tax_behavior": offer.tax_behavior,
                "interval": offer.interval,
                "stripe_price_id": offer.stripe_price_id,
            }
        )

    if len(currencies) > 1:
        raise PricebookError(
            "a single checkout cannot mix currencies: " + ", ".join(sorted(currencies))
        )

    # Stripe bills a session either once or on a schedule. A cart holding both a
    # subscription and a one-off would need an invoice-item flow we do not run, so
    # reject it here rather than letting Stripe fail the session creation.
    if recurring and recurring != len(line_items):
        raise PricebookError(
            "a single checkout cannot mix recurring and one-time items; "
            "check out the subscription separately"
        )

    return line_items, ("subscription" if recurring else "payment")
