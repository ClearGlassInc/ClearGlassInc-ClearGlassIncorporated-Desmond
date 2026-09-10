"""Prices are resolved server-side, and the checkout contract cannot carry one.

``/checkout/session`` hands its line items straight to Stripe: a line item's
``amount`` becomes Stripe's ``unit_amount``. If the request schema ever accepts
a price-shaped field, an anonymous caller on a public endpoint chooses what to
pay, and every layer downstream — including the audit ledger — faithfully
records the amount they picked.

So the contract is pinned two ways here:

* structurally, by asserting the ``CheckoutLineItem`` OpenAPI schema has
  exactly ``{sku, quantity}`` and nothing else, and
* behaviourally, by sending a request that names its own amount and checking
  the resolved line item ignores it.

The structural half is what catches the dangerous change, because adding a
field to a Pydantic model is a one-line diff that breaks no existing test.
"""

from __future__ import annotations

import pytest

from app import pricebook

try:
    from app.schemas import CheckoutLineItem
    _HAS_PYDANTIC = True
except ImportError:  # pragma: no cover - minimal env runs the stdlib half only
    _HAS_PYDANTIC = False

pydantic_only = pytest.mark.skipif(not _HAS_PYDANTIC, reason="pydantic not installed")

# Anything a caller might use to smuggle a price past the server.
PRICE_SHAPED = {
    "amount", "unit_amount", "price", "amount_cents", "total", "subtotal",
    "cost", "value", "currency", "discount", "stripe_price_id", "tax_behavior",
}


def _first_active_sku() -> str:
    offers = pricebook.all_offers()
    assert offers, "the price book must ship at least one active offer"
    return offers[0].sku


@pydantic_only
def test_checkout_line_item_schema_is_exactly_sku_and_quantity() -> None:
    """The load-bearing assertion. Do not relax this to a subset check."""
    fields = set(CheckoutLineItem.model_json_schema()["properties"])
    assert fields == {"sku", "quantity"}, (
        "CheckoutLineItem must expose exactly {sku, quantity}. A checkout line "
        f"item's amount becomes Stripe's unit_amount, so any extra field here is "
        f"a path for the browser to choose what it pays. Found: {sorted(fields)}"
    )


@pydantic_only
def test_no_price_shaped_field_can_be_added_to_the_checkout_contract() -> None:
    fields = set(CheckoutLineItem.model_json_schema()["properties"])
    smuggled = sorted(fields & PRICE_SHAPED)
    assert not smuggled, f"price-shaped fields on the checkout contract: {smuggled}"


@pydantic_only
def test_the_schema_rejects_unknown_fields_or_drops_them() -> None:
    """A caller naming an amount must not get that amount through.

    Pydantic either forbids the extra field or discards it; both are safe. What
    would not be safe is retaining it for a downstream layer to read.
    """
    try:
        parsed = CheckoutLineItem(sku="anything", quantity=1, amount=1)
    except Exception:
        return  # extra="forbid" — rejected outright, which is the stronger posture
    assert not hasattr(parsed, "amount"), (
        "CheckoutLineItem retained a caller-supplied amount"
    )


def test_amounts_come_from_the_price_book_not_the_request() -> None:
    sku = _first_active_sku()
    expected = pricebook.get_offer(sku)

    # A request that tries to name its own price, in several shapes at once.
    line_items, _mode = pricebook.resolve_line_items(
        [{"sku": sku, "quantity": 1, "amount": 1, "unit_amount": 1, "currency": "XXX"}]
    )

    assert len(line_items) == 1
    assert line_items[0]["amount"] == expected.amount, (
        "resolve_line_items must price from the book, not from the request"
    )
    assert line_items[0]["currency"] == expected.currency


def test_an_unknown_sku_is_refused_rather_than_priced_at_zero() -> None:
    with pytest.raises(pricebook.PricebookError):
        pricebook.resolve_line_items([{"sku": "no-such-sku-exists", "quantity": 1}])


def test_an_empty_cart_is_refused() -> None:
    with pytest.raises(pricebook.PricebookError):
        pricebook.resolve_line_items([])


@pytest.mark.parametrize("quantity", [0, -1, -1000])
def test_non_positive_quantities_are_refused(quantity: int) -> None:
    """A negative quantity against a positive amount is a negative line total."""
    sku = _first_active_sku()
    with pytest.raises(pricebook.PricebookError):
        pricebook.resolve_line_items([{"sku": sku, "quantity": quantity}])


def test_quantity_is_capped_per_offer() -> None:
    sku = _first_active_sku()
    offer = pricebook.get_offer(sku)
    with pytest.raises(pricebook.PricebookError):
        pricebook.resolve_line_items([{"sku": sku, "quantity": offer.max_quantity + 1}])


def test_every_shipped_offer_has_a_positive_amount_and_a_currency() -> None:
    for offer in pricebook.all_offers():
        assert offer.amount > 0, f"{offer.sku}: amount must be positive"
        assert offer.currency, f"{offer.sku}: currency is required"
        assert offer.max_quantity >= 1, f"{offer.sku}: max_quantity must allow one"


def test_a_cart_cannot_mix_currencies() -> None:
    """Stripe prices one session in one currency; a mixed cart must fail here."""
    by_currency: dict[str, str] = {}
    for offer in pricebook.all_offers():
        by_currency.setdefault(offer.currency, offer.sku)
    if len(by_currency) < 2:
        pytest.skip("the shipped price book is single-currency")
    skus = list(by_currency.values())[:2]
    with pytest.raises(pricebook.PricebookError):
        pricebook.resolve_line_items([{"sku": s, "quantity": 1} for s in skus])


def test_a_cart_cannot_mix_recurring_and_one_time_items() -> None:
    """Stripe bills a session either once or on a schedule, never both."""
    recurring = next((o.sku for o in pricebook.all_offers() if o.recurring), None)
    one_time = next((o.sku for o in pricebook.all_offers() if not o.recurring), None)
    if not recurring or not one_time:
        pytest.skip("the shipped price book has only one billing mode")
    with pytest.raises(pricebook.PricebookError):
        pricebook.resolve_line_items(
            [{"sku": recurring, "quantity": 1}, {"sku": one_time, "quantity": 1}]
        )


def test_checkout_mode_follows_the_cart() -> None:
    sku = _first_active_sku()
    offer = pricebook.get_offer(sku)
    _items, mode = pricebook.resolve_line_items([{"sku": sku, "quantity": 1}])
    assert mode == ("subscription" if offer.recurring else "payment")
