"""The primary offer's buy button must open the live checkout.

The Security Quick-Audit is the one entry offer (revenue decision D2), and its
Payment Link was live in the catalog, on store.html and on pricing.html. Until
2026-10-01 the offer's own page still sent "Buy a Quick-Audit" to a mailto
asking for a checkout link to be emailed back, so a buyer ready to pay had to
wait for a reply. The button now carries the catalog's checkout_url; this test
fails if the two drift, or if the button falls back to email.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "offers" / "security-quick-audit.html"
CATALOG = ROOT / "data" / "store" / "catalog.json"

BUY_BUTTON = re.compile(r'<a\b[^>]*\bdata-cg-stripe="quickaudit"[^>]*>', re.IGNORECASE)
HREF = re.compile(r'\bhref="([^"]*)"', re.IGNORECASE)


def catalog_checkout_url() -> str:
    products = json.loads(CATALOG.read_text(encoding="utf-8"))["products"]
    (quick_audit,) = [p for p in products if p["sku"] == "quick-audit"]
    assert quick_audit["live_checkout"], "the catalog no longer marks the Quick-Audit live"
    return quick_audit["checkout_url"]


def buy_button_hrefs() -> list[str]:
    html = PAGE.read_text(encoding="utf-8")
    hrefs = []
    for tag in BUY_BUTTON.findall(html):
        match = HREF.search(tag)
        assert match, f"buy button has no href: {tag}"
        hrefs.append(match.group(1))
    return hrefs


def test_buy_button_opens_the_catalog_checkout():
    hrefs = buy_button_hrefs()
    assert hrefs, "the Quick-Audit page has no data-cg-stripe=\"quickaudit\" button"
    expected = catalog_checkout_url()
    assert expected.startswith("https://buy.stripe.com/"), expected
    for href in hrefs:
        assert href == expected, (
            f"buy button points at {href!r}, the catalog's live checkout is {expected!r}"
        )


def test_no_paste_link_placeholder_left_on_the_page():
    html = PAGE.read_text(encoding="utf-8")
    assert "paste $249 Quick-Audit Payment Link" not in html
