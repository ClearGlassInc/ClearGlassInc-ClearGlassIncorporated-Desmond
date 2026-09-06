"""The Side Store cart is priced on the server, and its arithmetic must match the page.

Two separate guarantees live here:

1. **The browser cannot choose a price.** Ids and quantities in, catalogue prices
   out — the same property `test_pricebook.py` pins for services.
2. **The page and the server agree.** `side-store.html` shows a total before the
   customer commits; this module computes the one they are charged. A silent
   disagreement between them is a customer-facing lie, so the constants are
   asserted against the storefront's own values.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from app import cart

REPO_ROOT = Path(__file__).resolve().parents[3]
SIDE_STORE_HTML = REPO_ROOT / "side-store.html"


# ------------------------------------------------------------------ pure pricing


def test_catalog_loads_every_item() -> None:
    items = cart.catalog()
    assert len(items) == 57
    for item in items:
        assert item["amount"] > 0, item["id"]


def test_single_item_has_no_discount_and_pays_shipping() -> None:
    totals = cart.price_cart([{"id": "sku_001", "quantity": 1}])
    assert totals.subtotal == 699
    assert totals.discount == 0
    assert totals.shipping == 499          # under the free-shipping threshold
    assert totals.tax == cart._round_cents(Decimal(699 + 499) * Decimal("0.13"))
    assert totals.total == 699 + 499 + totals.tax


def test_three_items_earn_the_ten_percent_tier() -> None:
    totals = cart.price_cart([{"id": "sku_001", "quantity": 3}])
    assert totals.quantity == 3
    assert totals.discount_rate == "0.10"
    assert totals.discount == cart._round_cents(Decimal(699 * 3) * Decimal("0.10"))


def test_five_items_earn_the_fifteen_percent_tier() -> None:
    totals = cart.price_cart([{"id": "sku_001", "quantity": 5}])
    assert totals.discount_rate == "0.15"


def test_tier_is_the_better_of_two_thresholds() -> None:
    """A 6-item cart qualifies for both tiers and must get the generous one."""
    assert cart.price_cart([{"id": "sku_001", "quantity": 6}]).discount_rate == "0.15"


def test_free_shipping_above_the_threshold() -> None:
    totals = cart.price_cart([{"id": "sku_002", "quantity": 5}])   # 5 x $8.49
    assert totals.discounted_subtotal >= 2500
    assert totals.free_shipping_applied is True
    assert totals.shipping == 0


def test_free_shipping_uses_the_discounted_subtotal_not_the_gross() -> None:
    """The discount is applied first, so a cart can drop back under the threshold.

    This is the subtle one: charging free shipping on a gross subtotal that the
    bundle discount then pulls below $25 gives away shipping the rules did not.
    """
    rules = cart.pricing_rules()
    threshold = rules["free_shipping_threshold"]
    totals = cart.price_cart([{"id": "sku_002", "quantity": 3}])   # 3 x $8.49 = $25.47
    assert totals.subtotal >= threshold, "gross subtotal should clear the threshold"
    assert totals.discounted_subtotal < threshold, "discount should pull it back under"
    assert totals.free_shipping_applied is False
    assert totals.shipping == rules["flat_shipping"]


def test_tax_applies_to_shipping_too() -> None:
    totals = cart.price_cart([{"id": "sku_001", "quantity": 1}])
    expected = cart._round_cents(
        Decimal(totals.discounted_subtotal + totals.shipping) * Decimal("0.13")
    )
    assert totals.tax == expected


def test_totals_are_internally_consistent() -> None:
    totals = cart.price_cart(
        [{"id": "sku_001", "quantity": 2}, {"id": "sku_003", "quantity": 2}]
    )
    assert totals.discounted_subtotal == totals.subtotal - totals.discount
    assert totals.total == totals.discounted_subtotal + totals.shipping + totals.tax
    assert totals.subtotal == sum(i.line_total for i in totals.items)


# ------------------------------------------------------------------- refusals


def test_client_supplied_price_is_ignored() -> None:
    """The core guarantee — a price in the request changes nothing."""
    totals = cart.price_cart([{"id": "sku_001", "quantity": 1, "amount": 1, "price": 0.01}])
    assert totals.subtotal == 699


def test_unknown_item_is_refused() -> None:
    with pytest.raises(cart.CartError, match="unknown item"):
        cart.price_cart([{"id": "sku_999", "quantity": 1}])


def test_empty_cart_is_refused() -> None:
    with pytest.raises(cart.CartError, match="empty"):
        cart.price_cart([])


def test_zero_or_negative_quantity_is_refused() -> None:
    with pytest.raises(cart.CartError, match="at least 1"):
        cart.price_cart([{"id": "sku_001", "quantity": 0}])


def test_absurd_quantity_is_refused() -> None:
    with pytest.raises(cart.CartError, match="exceeds the maximum"):
        cart.price_cart([{"id": "sku_001", "quantity": 10_000}])


def test_duplicate_line_is_refused() -> None:
    """Two lines for one id would double-count against the quantity tiers."""
    with pytest.raises(cart.CartError, match="twice"):
        cart.price_cart([{"id": "sku_001", "quantity": 1}, {"id": "sku_001", "quantity": 1}])


# ------------------------------------------------------------ Stripe line items


def test_stripe_line_items_carry_the_discounted_unit_price() -> None:
    """5 x $6.99 at 15% off.

    The naive unit price is round(699 x 0.85) = 594, which extends to 2970 against
    a quote of 2971. So the line is split — one unit absorbs the odd cent — and the
    prices stay within a cent of the discounted unit either way.
    """
    totals = cart.price_cart([{"id": "sku_001", "quantity": 5}])
    lines = cart.to_stripe_line_items(totals)
    naive = cart._round_cents(Decimal(699) * Decimal("0.85"))
    assert sum(li["quantity"] for li in lines) == 5
    assert all(abs(li["amount"] - naive) <= 1 for li in lines)
    assert all(li["currency"] == "cad" for li in lines)
    assert sum(li["amount"] * li["quantity"] for li in lines) == totals.discounted_subtotal


def test_stripe_line_items_match_the_undiscounted_price_without_a_tier() -> None:
    totals = cart.price_cart([{"id": "sku_001", "quantity": 1}])
    assert cart.to_stripe_line_items(totals)[0]["amount"] == 699


# --------------------------------------------------- parity with the storefront


def _storefront_constants() -> dict[str, int | str]:
    html = SIDE_STORE_HTML.read_text(encoding="utf-8")
    m = re.search(
        r"var\s+FREE_SHIP\s*=\s*(\d+)\s*,\s*FLAT_SHIP\s*=\s*(\d+)\s*,\s*TAX_RATE\s*=\s*([0-9.]+)",
        html,
    )
    assert m, "could not read pricing constants out of side-store.html"
    return {"free_ship": int(m.group(1)), "flat_ship": int(m.group(2)), "tax_rate": m.group(3)}


def test_server_rules_match_the_storefront_constants() -> None:
    """If the page and the server disagree, the customer is shown a lie."""
    page = _storefront_constants()
    rules = cart.pricing_rules()
    assert rules["free_shipping_threshold"] == page["free_ship"]
    assert rules["flat_shipping"] == page["flat_ship"]
    assert Decimal(str(rules["tax_rate"])) == Decimal(str(page["tax_rate"]))


def test_server_bundle_tiers_match_the_storefront() -> None:
    html = SIDE_STORE_HTML.read_text(encoding="utf-8")
    m = re.search(r"function bundleRate\(q\)\{([^}]*)\}", html)
    assert m, "could not read bundleRate() out of side-store.html"
    body = m.group(1)
    assert "q>=5" in body.replace(" ", "") and "0.15" in body
    assert "q>=3" in body.replace(" ", "") and "0.10" in body

    tiers = {int(t["min_qty"]): Decimal(str(t["rate"])) for t in cart.pricing_rules()["bundle_tiers"]}
    assert tiers == {5: Decimal("0.15"), 3: Decimal("0.10")}


def test_server_catalog_matches_the_storefront_catalog() -> None:
    """Every id, and every price, identical on both sides."""
    html = SIDE_STORE_HTML.read_text(encoding="utf-8")
    embedded = json.loads(
        re.search(r'<script[^>]*id="catalog"[^>]*>(.*?)</script>', html, re.S).group(1)
    )
    page = {i["id"]: int(round(float(i["price"]) * 100)) for i in embedded}
    server = {i["id"]: i["amount"] for i in cart.catalog()}
    assert server == page


def test_full_cart_total_matches_the_storefront_arithmetic() -> None:
    """Recompute a representative cart the way the page does, and compare."""
    basket = [{"id": "sku_001", "quantity": 2}, {"id": "sku_002", "quantity": 2}]
    totals = cart.price_cart(basket)

    server_catalog = {i["id"]: i["amount"] for i in cart.catalog()}
    sub = sum(server_catalog[b["id"]] * b["quantity"] for b in basket)
    qty = sum(b["quantity"] for b in basket)
    rate = Decimal("0.15") if qty >= 5 else Decimal("0.10") if qty >= 3 else Decimal("0")
    disc = cart._round_cents(Decimal(sub) * rate)
    dsub = sub - disc
    ship = 0 if dsub >= 2500 else 499
    tax = cart._round_cents(Decimal(dsub + ship) * Decimal("0.13"))

    assert (totals.subtotal, totals.discount, totals.shipping, totals.tax) == (sub, disc, ship, tax)
    assert totals.total == dsub + ship + tax


# ------------------------------------------------------------------- the API

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import os as _os
    _os.environ.setdefault("DATABASE_URL", "sqlite://")
    from app import db as db_module
    from app.main import create_app
    from app.models import Base

    _HAS_WEB_STACK = True
except (ImportError, RuntimeError):  # pragma: no cover - minimal env runs pure tests only
    _HAS_WEB_STACK = False


@pytest.fixture()
def client():
    if not _HAS_WEB_STACK:
        pytest.skip("fastapi/sqlalchemy not installed")
    engine = create_engine(
        "sqlite://", future=True,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_session():
        session = TestingSession()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[db_module.get_session] = override_session
    return TestClient(app)


def test_catalog_endpoint_lists_every_item(client) -> None:
    body = client.get("/sidestore/catalog").json()
    assert len(body) == 57
    assert all(i["amount"] > 0 for i in body)


def test_quote_endpoint_matches_the_pricing_module(client) -> None:
    basket = {"items": [{"id": "sku_001", "quantity": 3}]}
    body = client.post("/sidestore/quote", json=basket).json()
    expected = cart.price_cart(basket["items"])
    assert body["total"] == expected.total
    assert body["discount_rate"] == "0.10"


def test_quote_ignores_a_client_supplied_price(client) -> None:
    body = client.post(
        "/sidestore/quote",
        json={"items": [{"id": "sku_001", "quantity": 1, "amount": 1, "price": 0.01}]},
    ).json()
    assert body["subtotal"] == 699


def test_quote_rejects_an_unknown_item(client) -> None:
    r = client.post("/sidestore/quote", json={"items": [{"id": "sku_999", "quantity": 1}]})
    assert r.status_code == 400
    assert "unknown item" in r.json()["detail"]


def test_checkout_totals_include_shipping(client) -> None:
    """Mock mode must report what a live session would charge, shipping included."""
    r = client.post("/sidestore/checkout/session", json={"items": [{"id": "sku_001", "quantity": 1}]})
    assert r.status_code == 200
    totals = cart.price_cart([{"id": "sku_001", "quantity": 1}])
    lines = sum(li["amount"] * li["quantity"] for li in cart.to_stripe_line_items(totals))
    assert r.json()["amount_total"] == lines + totals.shipping


def test_checkout_contract_exposes_no_price_field(client) -> None:
    """Drift guard: a price-shaped field here would hand pricing back to the browser."""
    schema = client.get("/openapi.json").json()
    props = schema["components"]["schemas"]["SideStoreCartLine"]["properties"]
    assert set(props) == {"id", "quantity"}, sorted(props)


def test_live_checkout_refuses_while_stripe_tax_is_off(client, monkeypatch) -> None:
    """The page quotes HST. Charging live without Tax under-collects it.

    Rather than silently pocket the difference (and owe it), the endpoint fails
    closed with an explanation.
    """
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_not_a_real_key")
    monkeypatch.delenv("STRIPE_AUTOMATIC_TAX", raising=False)
    r = client.post("/sidestore/checkout/session", json={"items": [{"id": "sku_001", "quantity": 1}]})
    assert r.status_code == 503
    assert "Stripe Tax" in r.json()["detail"]


def test_stripe_line_items_extend_to_the_quoted_subtotal_across_many_baskets() -> None:
    """The rounding remainder must be allocated, not dropped.

    The quote rounds the discount once over the subtotal; Stripe multiplies a
    rounded unit price by quantity. 5 x $6.99 at 15% off quotes $29.71 and naively
    extends to $29.70 — a customer charged something other than what they saw.
    """
    ids = [i["id"] for i in cart.catalog()]
    baskets = [[{"id": i, "quantity": q}] for i in ids[:10] for q in range(1, 13)]
    baskets.append([{"id": ids[0], "quantity": 5}, {"id": ids[1], "quantity": 3}])
    for basket in baskets:
        totals = cart.price_cart(basket)
        lines = cart.to_stripe_line_items(totals)
        extended = sum(li["amount"] * li["quantity"] for li in lines)
        assert extended == totals.discounted_subtotal, basket
        # Splitting a line to absorb the remainder must not invent or lose units.
        assert sum(li["quantity"] for li in lines) == totals.quantity, basket


def test_the_known_one_cent_divergence_is_gone() -> None:
    totals = cart.price_cart([{"id": "sku_001", "quantity": 5}])
    assert totals.discounted_subtotal == 2971
    assert sum(li["amount"] * li["quantity"] for li in cart.to_stripe_line_items(totals)) == 2971


def test_quote_marks_tax_as_an_ontario_estimate() -> None:
    """The store ships Canada-wide; Stripe Tax charges the destination's rate."""
    totals = cart.price_cart([{"id": "sku_001", "quantity": 1}])
    assert totals.tax_basis == "CA-ON"
    assert totals.tax_is_estimate is True


def test_checkout_contract_has_no_caller_supplied_return_urls(client) -> None:
    """A public endpoint that accepts success_url lets anyone mint a genuine
    ClearGlass Stripe session that redirects the buyer to their own domain."""
    schema = client.get("/openapi.json").json()
    for model in ("SideStoreCartRequest", "CheckoutRequest"):
        props = set(schema["components"]["schemas"][model]["properties"])
        assert "success_url" not in props, model
        assert "cancel_url" not in props, model


def test_live_session_forwards_shipping_and_metadata(monkeypatch) -> None:
    """Exercise the live Stripe branch, which mock mode never reaches.

    A malformed shipping payload would otherwise pass CI and only surface after
    activation, on a real customer's order.
    """
    import sys
    import types

    captured: dict = {}

    class _Session:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            return types.SimpleNamespace(
                id="cs_live_stub", url="https://checkout.stripe.com/c/stub",
                amount_total=1234, currency="cad",
            )

    stub = types.ModuleType("stripe")
    stub.api_key = None
    stub.checkout = types.SimpleNamespace(Session=_Session)
    monkeypatch.setitem(sys.modules, "stripe", stub)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_stub")

    from app import payments

    totals = cart.price_cart([{"id": "sku_001", "quantity": 1}])
    payments.create_checkout_session(
        cart.to_stripe_line_items(totals),
        shipping_countries=["CA"],
        shipping_amount=totals.shipping,
        shipping_label="Standard shipping",
        extra_metadata={"store": "side_store", "bundle_rate": totals.discount_rate},
    )

    assert captured["shipping_address_collection"] == {"allowed_countries": ["CA"]}
    rate = captured["shipping_options"][0]["shipping_rate_data"]
    assert rate["type"] == "fixed_amount"
    assert rate["fixed_amount"] == {"amount": totals.shipping, "currency": "cad"}
    assert rate["display_name"] == "Standard shipping"
    assert captured["metadata"]["store"] == "side_store"
    assert captured["metadata"]["bundle_rate"] == totals.discount_rate
    # The return URL must come from config, never from a caller.
    assert captured["success_url"].startswith("http")
    assert "{CHECKOUT_SESSION_ID}" in captured["success_url"]


def test_free_shipping_session_sends_a_zero_rate(monkeypatch) -> None:
    """Free shipping still needs an explicit option, or Stripe offers none."""
    import sys
    import types

    captured: dict = {}

    class _Session:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            return types.SimpleNamespace(
                id="cs", url="https://checkout.stripe.com/c/x", amount_total=1, currency="cad"
            )

    stub = types.ModuleType("stripe")
    stub.api_key = None
    stub.checkout = types.SimpleNamespace(Session=_Session)
    monkeypatch.setitem(sys.modules, "stripe", stub)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_stub")

    from app import payments

    totals = cart.price_cart([{"id": "sku_002", "quantity": 5}])
    assert totals.free_shipping_applied is True
    payments.create_checkout_session(
        cart.to_stripe_line_items(totals),
        shipping_countries=["CA"],
        shipping_amount=totals.shipping,
        shipping_label="Free shipping",
    )
    rate = captured["shipping_options"][0]["shipping_rate_data"]
    assert rate["fixed_amount"]["amount"] == 0
    assert rate["display_name"] == "Free shipping"
