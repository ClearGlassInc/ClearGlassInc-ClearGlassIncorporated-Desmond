# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for bots/store_smoke_bot.py."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bots.store_smoke_bot import (  # noqa: E402
    REQUIRED_CONFIG_MAPS,
    STRIPE_LINK_RE,
    check_checkout_links,
    check_pricing,
    check_storefront,
    extract_card_skus,
    extract_checkout_links,
    extract_map_keys,
    live_checkout_skus,
    run,
)

GOOD_STORE = """
<article class="card" data-sku="alpha"><div class="price">$1</div><a data-buy>Buy</a></article>
<article class="card" data-sku="beta"><div class="price">$2</div><a data-buy>Buy</a></article>
<script>
  var CHECKOUT   = { "alpha": "", "beta": "" };
  var LABEL      = { "alpha": "Alpha", "beta": "Beta" };
  var SHORT      = { "alpha": "A", "beta": "B" };
  var ETX_AMOUNT = { "alpha": "$1", "beta": "$2" };
  if (/^https:\\/\\/(buy|book|checkout)\\.stripe\\.com\\//.test(link)) {}
</script>
<p>Nothing is auto-charged, and no funds are ever auto-sent.</p>
"""

GOOD_PRICING = """
<a href="store.html">Book</a>
<article class="plan" data-sku="alpha"></article>
<article class="plan" data-sku="beta"></article>
<script>var CHECKOUT = { "alpha": "", "beta": "" };</script>
"""

EXPECTED_REAL_SKUS = {
    "quick-audit",
    "hardening",
    "phipa",
    "monitoring",
    "critical-minerals-compliance",
}


class TestExtractCardSkus:
    def test_finds_declared_skus(self) -> None:
        assert extract_card_skus(GOOD_STORE) == ["alpha", "beta"]

    def test_empty_when_no_cards(self) -> None:
        assert extract_card_skus("<html>no products</html>") == []

    def test_real_store_has_expected_skus(self) -> None:
        html = (ROOT / "store.html").read_text(encoding="utf-8")
        assert set(extract_card_skus(html)) == EXPECTED_REAL_SKUS


class TestExtractMapKeys:
    def test_reads_flat_object_keys(self) -> None:
        assert extract_map_keys(GOOD_STORE, "CHECKOUT") == {"alpha", "beta"}

    def test_missing_map_returns_empty(self) -> None:
        assert extract_map_keys(GOOD_STORE, "DOES_NOT_EXIST") == set()


class TestCheckStorefront:
    def test_healthy_storefront_has_no_errors(self) -> None:
        assert check_storefront(GOOD_STORE) == []

    def test_no_cards_is_an_error(self) -> None:
        errors = check_storefront("<html>nothing</html>")
        assert errors and "no product cards" in errors[0]

    def test_unwired_sku_is_detected(self) -> None:
        broken = GOOD_STORE.replace(
            'var CHECKOUT   = { "alpha": "", "beta": "" };',
            'var CHECKOUT   = { "alpha": "" };',
        )
        errors = check_storefront(broken)
        assert any("CHECKOUT" in e and "beta" in e for e in errors)

    def test_missing_stripe_guard_is_detected(self) -> None:
        broken = GOOD_STORE.replace("(buy|book|checkout)", "")
        assert any("Stripe checkout-link guard" in e for e in check_storefront(broken))

    def test_payment_copy_wording_does_not_control_checkout_health(self) -> None:
        rewritten = GOOD_STORE.replace("Nothing is auto-charged, and no funds are ever auto-sent.", "Pay securely.")
        assert check_storefront(rewritten) == []

    def test_real_store_html_is_healthy(self) -> None:
        html = (ROOT / "store.html").read_text(encoding="utf-8")
        assert check_storefront(html) == []


class TestCheckPricing:
    def test_consistent_pages_have_no_errors(self) -> None:
        assert check_pricing(GOOD_STORE, GOOD_PRICING) == []

    def test_curated_pricing_subset_is_allowed(self) -> None:
        subset = GOOD_PRICING.replace('<article class="plan" data-sku="beta"></article>', "").replace(
            ', "beta": ""', ""
        )
        assert check_pricing(GOOD_STORE, subset) == []

    def test_pricing_cannot_invent_unknown_sku(self) -> None:
        drifted = GOOD_PRICING.replace('data-sku="beta"', 'data-sku="gamma"')
        assert any("pricing-only" in e for e in check_pricing(GOOD_STORE, drifted))

    def test_missing_store_link_is_detected(self) -> None:
        no_link = GOOD_PRICING.replace('<a href="store.html">Book</a>', "")
        assert any("links to store.html" in e for e in check_pricing(GOOD_STORE, no_link))

    def test_real_pages_are_consistent(self) -> None:
        store = (ROOT / "store.html").read_text(encoding="utf-8")
        pricing = (ROOT / "pricing.html").read_text(encoding="utf-8")
        assert check_pricing(store, pricing) == []

    @staticmethod
    def _pages(store_url: str, pricing_url: str) -> tuple[str, str]:
        store = GOOD_STORE.replace(
            '"alpha": "", "beta": ""',
            f'"alpha": "{store_url}", "beta": ""',
            1,
        )
        pricing = GOOD_PRICING.replace(
            '"alpha": "", "beta": ""',
            f'"alpha": "{pricing_url}", "beta": ""',
        )
        return store, pricing

    def test_swapped_checkout_url_is_detected(self) -> None:
        store, pricing = self._pages("https://buy.stripe.com/aaa", "https://buy.stripe.com/bbb")
        errors = check_pricing(store, pricing)
        assert any("charges for the wrong product" in e for e in errors), errors

    def test_identical_checkout_urls_pass(self) -> None:
        same = "https://buy.stripe.com/aaa"
        store, pricing = self._pages(same, same)
        assert not any("charges for the wrong product" in e for e in check_pricing(store, pricing))

    def test_real_pages_agree_on_every_statically_shared_checkout_url(self) -> None:
        store = (ROOT / "store.html").read_text(encoding="utf-8")
        pricing = (ROOT / "pricing.html").read_text(encoding="utf-8")
        store_links = extract_checkout_links(store)
        pricing_links = extract_checkout_links(pricing)
        shared = set(extract_card_skus(pricing)) & set(extract_card_skus(store))
        assert shared
        for sku in sorted(shared):
            assert bool(store_links.get(sku, "").strip()) == bool(pricing_links.get(sku, "").strip()), sku
            if store_links.get(sku, "").strip():
                assert store_links[sku].strip() == pricing_links[sku].strip(), sku


LIVE_LINK = "https://buy.stripe.com/test_abc123"
STORE_WITH_LIVE = GOOD_STORE.replace(
    '"alpha": "", "beta": ""',
    f'"alpha": "{LIVE_LINK}", "beta": ""',
    1,
)


class TestCheckoutLinks:
    def test_extract_links_as_dict(self) -> None:
        assert extract_checkout_links(GOOD_STORE) == {"alpha": "", "beta": ""}

    def test_live_skus_are_the_non_empty_ones(self) -> None:
        assert live_checkout_skus(GOOD_STORE) == set()
        assert live_checkout_skus(STORE_WITH_LIVE) == {"alpha"}

    def test_empty_links_pass(self) -> None:
        assert check_checkout_links(GOOD_STORE) == []

    def test_valid_stripe_link_passes(self) -> None:
        assert check_checkout_links(STORE_WITH_LIVE) == []
        assert STRIPE_LINK_RE.match(LIVE_LINK)

    def test_wrong_domain_is_rejected(self) -> None:
        bad = GOOD_STORE.replace('"alpha": ""', '"alpha": "https://evil.example/x"')
        errors = check_checkout_links(bad, "store.html")
        assert any("alpha" in e and "not a valid" in e for e in errors)

    def test_plain_http_is_rejected(self) -> None:
        bad = GOOD_STORE.replace('"alpha": ""', '"alpha": "http://buy.stripe.com/x"')
        assert check_checkout_links(bad) != []

    def test_bare_host_without_path_is_rejected(self) -> None:
        bad = GOOD_STORE.replace('"alpha": ""', '"alpha": "https://buy.stripe.com/"')
        assert check_checkout_links(bad) != []

    def test_real_pages_have_only_valid_or_empty_links(self) -> None:
        store = (ROOT / "store.html").read_text(encoding="utf-8")
        pricing = (ROOT / "pricing.html").read_text(encoding="utf-8")
        assert check_checkout_links(store, "store.html") == []
        assert check_checkout_links(pricing, "pricing.html") == []

    def test_shared_sku_live_checkout_must_match_across_pages(self) -> None:
        errors = check_pricing(STORE_WITH_LIVE, GOOD_PRICING)
        assert any("state" in e for e in errors)


class TestRun:
    def test_real_repo_storefront_passes(self) -> None:
        report = run()
        assert report["healthy"] is True, report["errors"]
        assert set(report["skus"]) == EXPECTED_REAL_SKUS

    def test_run_reports_missing_store(self, tmp_path: Path) -> None:
        report = run(root=tmp_path)
        assert report["healthy"] is False
        assert any("store.html" in e for e in report["errors"])


class TestConstants:
    def test_required_config_maps_not_empty(self) -> None:
        assert len(REQUIRED_CONFIG_MAPS) >= 1
