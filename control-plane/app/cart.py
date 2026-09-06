"""Side Store cart pricing — the rules a Payment Link cannot express.

A Stripe Payment Link sells one fixed basket. The Side Store does not have one:
its price depends on how much you buy (bundle tiers), and its shipping depends on
what the discounted subtotal comes to. That arithmetic has to happen somewhere
the customer cannot edit, which is here.

This mirrors the rules in ``side-store.html`` and
``apps/autostore/storefront/lib/pricing.mjs``. The page may compute a total to
*show* you; this module computes the total you are actually *charged*. When they
disagree, this one wins — ``tests/test_cart.py`` pins them together so they
should not disagree in the first place.

Money is integer cents throughout. Floats do not belong in a total, and the
rounding order below (discount on the subtotal, then shipping, then tax on the
sum) is the same order the storefront uses — change one, change both.

Stdlib-only, like ``governance.py`` and ``pricebook.py``, so it imports in the
minimal CI environments that run the governance gate without the web stack.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_CATALOG = Path(__file__).parent / "data" / "sidestore.json"

#: Nobody needs 500 USB cables, and an unbounded quantity is a denial-of-wallet
#: waiting to happen on a card that turns out to be stolen.
MAX_QUANTITY_PER_LINE = 25
MAX_LINES = 40


class CartError(ValueError):
    """A cart the store refuses to price. Callers translate this into a 400."""


@dataclass(frozen=True)
class CartItem:
    """One priced line, resolved from the catalogue rather than the request."""

    id: str
    sku: str
    name: str
    description: str
    unit_amount: int
    quantity: int

    @property
    def line_total(self) -> int:
        return self.unit_amount * self.quantity


@dataclass(frozen=True)
class CartTotals:
    """What the customer owes, broken out so a receipt can explain itself."""

    items: list[CartItem] = field(default_factory=list)
    quantity: int = 0
    subtotal: int = 0
    discount_rate: str = "0"       # e.g. "0.10" — string so it survives JSON intact
    discount: int = 0
    discounted_subtotal: int = 0
    shipping: int = 0
    tax: int = 0
    total: int = 0
    currency: str = "cad"
    free_shipping_applied: bool = False
    #: The rate basis this quote used, and whether it is final. The catalogue
    #: carries a single Ontario HST rate, but the store ships Canada-wide and
    #: Stripe Tax charges the destination's rate. Outside Ontario this figure
    #: is an estimate and the real tax is computed at checkout — callers must
    #: not present it as the definitive total.
    tax_basis: str = "CA-ON"
    tax_is_estimate: bool = True


def _catalog_path() -> Path:
    override = os.environ.get("SIDESTORE_CATALOG_PATH", "").strip()
    return Path(override) if override else DEFAULT_CATALOG


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)

    items: dict[str, dict[str, Any]] = {}
    for raw in document.get("items", []):
        item_id = str(raw.get("id", "")).strip()
        if not item_id:
            raise CartError("side store catalogue entry is missing an id")
        if item_id in items:
            raise CartError(f"duplicate id in side store catalogue: {item_id}")
        if int(raw.get("amount", 0)) <= 0:
            raise CartError(f"{item_id}: amount must be a positive integer of cents")
        items[item_id] = raw

    document["_by_id"] = items
    return document


def reload() -> None:
    """Drop the cached catalogue (tests, and after a deploy-time swap)."""
    _load.cache_clear()


def catalog() -> list[dict[str, Any]]:
    """Every purchasable item, in file order."""
    return list(_load(str(_catalog_path()))["items"])


def pricing_rules() -> dict[str, Any]:
    return dict(_load(str(_catalog_path())).get("pricing", {}))


def _bundle_rate(quantity: int, tiers: list[dict[str, Any]]) -> Decimal:
    """The best tier the cart qualifies for, or zero.

    Tiers are evaluated most-generous-first so the customer always gets the
    better of two overlapping thresholds.
    """
    best = Decimal("0")
    for tier in sorted(tiers, key=lambda t: int(t.get("min_qty", 0)), reverse=True):
        if quantity >= int(tier.get("min_qty", 0)):
            best = max(best, Decimal(str(tier.get("rate", "0"))))
            break
    return best


def _round_cents(value: Decimal) -> int:
    """Half-up, the way a till rounds — banker's rounding surprises people."""
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def price_cart(requested: list[dict[str, Any]]) -> CartTotals:
    """Turn ``[{"id": ..., "quantity": ...}]`` into what the customer owes.

    Nothing in ``requested`` contributes a price. Ids are looked up in the
    catalogue and quantities are bounds-checked; everything else is derived.
    """
    if not requested:
        raise CartError("cart is empty")
    if len(requested) > MAX_LINES:
        raise CartError(f"cart has more than {MAX_LINES} distinct items")

    document = _load(str(_catalog_path()))
    by_id = document["_by_id"]
    rules = document.get("pricing", {})

    items: list[CartItem] = []
    seen: set[str] = set()
    subtotal = 0
    quantity = 0

    for entry in requested:
        item_id = str(entry.get("id", "")).strip()
        raw = by_id.get(item_id)
        if raw is None:
            raise CartError(f"unknown item: {item_id!r}")
        if item_id in seen:
            raise CartError(f"item appears twice in the cart: {item_id}")
        seen.add(item_id)

        qty = int(entry.get("quantity", 1))
        if qty < 1:
            raise CartError(f"{item_id}: quantity must be at least 1")
        if qty > MAX_QUANTITY_PER_LINE:
            raise CartError(
                f"{item_id}: quantity {qty} exceeds the maximum of {MAX_QUANTITY_PER_LINE}"
            )

        item = CartItem(
            id=item_id,
            sku=str(raw.get("sku", item_id)),
            name=str(raw.get("name", item_id)),
            description=str(raw.get("description", "")),
            unit_amount=int(raw["amount"]),
            quantity=qty,
        )
        items.append(item)
        subtotal += item.line_total
        quantity += qty

    rate = _bundle_rate(quantity, list(rules.get("bundle_tiers", [])))
    discount = _round_cents(Decimal(subtotal) * rate)
    discounted = subtotal - discount

    threshold = int(rules.get("free_shipping_threshold", 0))
    flat = int(rules.get("flat_shipping", 0))
    free_shipping = bool(threshold) and discounted >= threshold
    shipping = 0 if free_shipping else flat

    tax_rate = Decimal(str(rules.get("tax_rate", "0")))
    tax = _round_cents(Decimal(discounted + shipping) * tax_rate)

    return CartTotals(
        items=items,
        quantity=quantity,
        subtotal=subtotal,
        discount_rate=str(rate),
        discount=discount,
        discounted_subtotal=discounted,
        shipping=shipping,
        tax=tax,
        total=discounted + shipping + tax,
        currency=str(document.get("currency", "cad")).lower(),
        free_shipping_applied=free_shipping,
        tax_basis=str(rules.get("tax_basis", "CA-ON")),
        tax_is_estimate=True,
    )


def to_stripe_line_items(totals: CartTotals) -> list[dict[str, Any]]:
    """Priced line items in the shape ``payments.create_checkout_session`` expects.

    The bundle discount is applied to each unit price rather than sent as a Stripe
    coupon. A coupon would be cleaner on the receipt, but it is a separate live
    object that can drift out of step with the tiers in the catalogue — and a
    discount the customer can see on the page but not on the invoice is worse than
    one folded into the price. ``discount_rate`` rides along in the session
    metadata so the reconciliation still knows a tier was applied.

    **The rounding has to be allocated, not just applied.** The quote rounds the
    discount once over the whole subtotal; Stripe multiplies a rounded unit price
    by the quantity. Those are not the same number — 5 x $6.99 at 15% off quotes
    $29.71 but extends to $29.70 — and the gap is a customer charged something
    other than what they were shown. So the remainder is distributed a cent at a
    time across individual units, splitting a line where necessary, until the
    extended total equals ``discounted_subtotal`` exactly.
    """
    rate = Decimal(totals.discount_rate)

    def _line(item: CartItem, unit: int, quantity: int) -> dict[str, Any]:
        return {
            "sku": item.sku,
            "name": item.name,
            "description": item.description,
            "amount": unit,
            "currency": totals.currency,
            "quantity": quantity,
            "tax_behavior": "exclusive",
        }

    if not rate:
        line_items = [_line(i, i.unit_amount, i.quantity) for i in totals.items]
    else:
        draft = [
            (item, _round_cents(Decimal(item.unit_amount) * (Decimal("1") - rate)), item.quantity)
            for item in totals.items
        ]
        delta = totals.discounted_subtotal - sum(unit * qty for _, unit, qty in draft)

        line_items = []
        for item, unit, qty in draft:
            if delta:
                # Each adjusted unit absorbs exactly one cent, so at most `qty` of
                # this line's units are needed before moving to the next.
                step = 1 if delta > 0 else -1
                adjusted = min(abs(delta), qty)
                line_items.append(_line(item, unit + step, adjusted))
                delta -= step * adjusted
                qty -= adjusted
            if qty:
                line_items.append(_line(item, unit, qty))

        if delta:  # pragma: no cover - impossible while |delta| < total units
            raise CartError(
                f"could not allocate the rounding remainder ({delta} cents left over)"
            )

    # The invariant this function exists to hold. A silent mismatch here is the
    # customer being charged a different number from the one on the page.
    extended = sum(li["amount"] * li["quantity"] for li in line_items)
    if extended != totals.discounted_subtotal:  # pragma: no cover - guarded above
        raise CartError(
            f"line items extend to {extended} but the cart quotes "
            f"{totals.discounted_subtotal}"
        )
    return line_items
