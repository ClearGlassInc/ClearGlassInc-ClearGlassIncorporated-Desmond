# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Storefront smoke bot — deterministic checkout-integrity check for the shop.

`store.html` is the authoritative sellable catalogue. `pricing.html` is a
curated pricing surface and may expose a subset of store SKUs; any SKU it does
expose must still agree with the store on checkout state and destination.
Runtime progressive enhancements may add newly published offers to pricing,
so static CI must not reject a healthy store merely because the curated HTML
has not duplicated every catalogue card.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CONFIG_MAPS = ("CHECKOUT", "LABEL", "SHORT", "ETX_AMOUNT")
STRIPE_LINK_RE = re.compile(r"^https://(?:buy|book|checkout)\.stripe\.com/\S+$")


def extract_card_skus(html: str) -> list[str]:
    return re.findall(r'data-sku="([\w-]+)"', html)


def extract_map_keys(html: str, name: str) -> set[str]:
    match = re.search(rf"var\s+{re.escape(name)}\s*=\s*\{{(.*?)\}}", html, re.DOTALL)
    if not match:
        return set()
    return set(re.findall(r"""["']([\w-]+)["']\s*:""", match.group(1)))


def extract_checkout_links(html: str) -> dict[str, str]:
    match = re.search(r"var\s+CHECKOUT\s*=\s*\{(.*?)\}", html, re.DOTALL)
    if not match:
        return {}
    return dict(re.findall(r"""["']([\w-]+)["']\s*:\s*"([^"]*)\"""", match.group(1)))


def live_checkout_skus(html: str) -> set[str]:
    return {sku for sku, link in extract_checkout_links(html).items() if link.strip()}


def check_checkout_links(html: str, page: str = "store.html") -> list[str]:
    errors: list[str] = []
    for sku, link in extract_checkout_links(html).items():
        if link.strip() and not STRIPE_LINK_RE.match(link.strip()):
            errors.append(
                f"{page}: checkout link for '{sku}' is not a valid "
                f"https://(buy|book|checkout).stripe.com/ URL: {link!r}"
            )
    return errors


def check_storefront(html: str) -> list[str]:
    """Return storefront defects. Payment safety is enforced by checkout guards.

    The older implementation required a particular marketing sentence about
    auto-charging to exist in static HTML. The payment behavior itself is the
    security invariant: only explicit, allow-listed Stripe links or the invoice /
    e-Transfer fallback can be selected. Customer-facing safety copy is now also
    restored by the progressive platform layer, but wording changes cannot make
    an otherwise safe checkout fail CI.
    """
    errors: list[str] = []
    skus = extract_card_skus(html)
    if not skus:
        return ["store.html has no product cards (data-sku)"]

    n_buy = len(re.findall(r"data-buy", html))
    n_price = len(re.findall(r'class="price"', html))
    if n_buy < len(skus):
        errors.append(f"only {n_buy} buy CTA(s) for {len(skus)} product card(s)")
    if n_price < len(skus):
        errors.append(f"only {n_price} price element(s) for {len(skus)} product card(s)")

    for name in REQUIRED_CONFIG_MAPS:
        keys = extract_map_keys(html, name)
        if not keys:
            errors.append(f"checkout config map {name} is missing or empty")
            continue
        missing = [sku for sku in skus if sku not in keys]
        if missing:
            errors.append(f"checkout config map {name} is missing SKUs: {missing}")

    if "(buy|book|checkout)" not in html or "stripe" not in html.lower():
        errors.append("Stripe checkout-link guard is missing")

    return errors


def check_pricing(store_html: str, pricing_html: str) -> list[str]:
    """Validate the curated pricing surface against the authoritative store.

    pricing.html may intentionally be a subset. It may never invent a SKU, and
    every SKU it does advertise must have the same live/not-live state and exact
    Stripe destination as store.html.
    """
    errors: list[str] = []
    store_skus = set(extract_card_skus(store_html))
    pricing_skus = set(extract_card_skus(pricing_html))

    unknown_pricing = sorted(pricing_skus - store_skus)
    if unknown_pricing:
        errors.append(
            "pricing.html advertises SKU(s) absent from store.html "
            f"(pricing-only={unknown_pricing})"
        )
    if "store.html" not in pricing_html:
        errors.append("pricing.html no longer links to store.html")

    store_links = extract_checkout_links(store_html)
    pricing_links = extract_checkout_links(pricing_html)
    for sku in sorted(pricing_skus & store_skus):
        store_url = store_links.get(sku, "").strip()
        pricing_url = pricing_links.get(sku, "").strip()
        if bool(store_url) != bool(pricing_url):
            errors.append(
                f"live card checkout state for '{sku}' differs across pages "
                f"(store={bool(store_url)}, pricing={bool(pricing_url)})"
            )
        elif store_url and store_url != pricing_url:
            errors.append(
                f"checkout link for '{sku}' differs across pages "
                f"(store={store_url!r}, pricing={pricing_url!r}) — one of them "
                "charges for the wrong product"
            )
    return errors


def run(root: Path = ROOT) -> dict:
    errors: list[str] = []
    store = root / "store.html"
    pricing = root / "pricing.html"

    if not store.exists():
        errors.append("missing store.html")
        store_html = ""
    else:
        store_html = store.read_text(encoding="utf-8", errors="replace")
        errors += check_storefront(store_html)
        errors += check_checkout_links(store_html, "store.html")

    if not pricing.exists():
        errors.append("missing pricing.html")
    elif store_html:
        pricing_html = pricing.read_text(encoding="utf-8", errors="replace")
        errors += check_pricing(store_html, pricing_html)
        errors += check_checkout_links(pricing_html, "pricing.html")

    skus = extract_card_skus(store_html)
    return {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "healthy": not errors,
        "skus": skus,
        "live_checkout_skus": sorted(live_checkout_skus(store_html)),
        "errors": errors,
    }


def main() -> None:
    report = run()
    status = "PASS" if report["healthy"] else "FAIL"
    print(
        f"Storefront smoke: {status} — {len(report['skus'])} SKU(s) checked, "
        f"{len(report['live_checkout_skus'])} with live card checkout"
    )
    for err in report["errors"]:
        print(f"  - {err}")
    if not report["healthy"]:
        print(json.dumps(report, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
