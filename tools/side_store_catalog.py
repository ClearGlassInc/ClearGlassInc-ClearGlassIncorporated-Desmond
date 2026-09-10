#!/usr/bin/env python3
"""Extract the Side Store catalog from ``side-store.html`` into committed JSON.

The Side Store's 57 SKUs live as a JSON array inside the page's own script
block — that is what the storefront renders from, so the page is the source of
truth and this file is a projection of it, never the other way round. The same
relationship ``data/store/catalog.json`` has with ``store.html``.

Publishing it as a file is what lets anything other than a browser check the
catalog's invariants: that every SKU is under the impulse-buy cap, that ids and
SKUs are unique, and that the currency is consistent.
``tests/test_side_store_storefront.py`` asserts exactly those.

Note this is a *different* catalog from ``data/store/catalog.json``, which
holds the five ClearGlass service engagements with their live Stripe checkout
URLs. The two must not be conflated: the service catalog's SKUs are hundreds of
dollars and would fail every Side Store invariant, and the Side Store's would
fail the service catalog's.

Usage::

    python3 tools/side_store_catalog.py            # write the catalog
    python3 tools/side_store_catalog.py --check    # exit 1 if it is stale

Stdlib only, so it runs in the minimal CI images.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "side-store.html"
OUTPUT = REPO_ROOT / "data" / "side-store" / "catalog.json"

SCHEMA = "clearglass.side-store.catalog/v1"
CURRENCY = "CAD"

# The impulse-buy cap the storefront is built around. A SKU above it is a
# product decision, not a formatting slip, so extraction fails rather than
# quietly publishing it.
PRICE_CAP = 10.0

REQUIRED_FIELDS = ("id", "sku", "name", "category", "price")

# The array opens with the first SKU; matching on that anchor avoids picking up
# an unrelated array elsewhere in a 110 KB page.
CATALOG_RE = re.compile(r'\[\s*\{"id":"sku_001".*?\}\s*\]', re.DOTALL)


class ExtractionError(RuntimeError):
    """The page's catalog could not be read, and no file should be written."""


def extract(html: str) -> list[dict]:
    match = CATALOG_RE.search(html)
    if match is None:
        raise ExtractionError(f"no catalog array found in {SOURCE.name}")
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"catalog array in {SOURCE.name} is not valid JSON: {exc}") from exc

    if not isinstance(items, list) or not items:
        raise ExtractionError("catalog array is empty")

    seen_ids: set[str] = set()
    seen_skus: set[str] = set()
    for item in items:
        for field in REQUIRED_FIELDS:
            if field not in item:
                raise ExtractionError(f"{item.get('sku', '<unknown>')}: missing {field!r}")
        if not isinstance(item["price"], (int, float)) or item["price"] <= 0:
            raise ExtractionError(f"{item['sku']}: price must be a positive number")
        if item["price"] > PRICE_CAP:
            raise ExtractionError(
                f"{item['sku']}: {item['price']} exceeds the ${PRICE_CAP:.0f} impulse cap"
            )
        if item["id"] in seen_ids:
            raise ExtractionError(f"duplicate id {item['id']!r}")
        if item["sku"] in seen_skus:
            raise ExtractionError(f"duplicate sku {item['sku']!r}")
        seen_ids.add(item["id"])
        seen_skus.add(item["sku"])

    # The page carries one currency for the whole store; stamp it per item so a
    # consumer never has to reach back up to the document to price a line.
    return [{**item, "currency": CURRENCY} for item in items]


def build(html: str) -> dict:
    items = extract(html)
    payload = json.dumps(items, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema": SCHEMA,
        "source": SOURCE.name,
        "currency": CURRENCY,
        "content_hash": "sha256:" + hashlib.sha256(payload).hexdigest(),
        "summary": {
            "sku_count": len(items),
            "categories": sorted({item["category"] for item in items}),
            "price_min": min(item["price"] for item in items),
            "price_max": max(item["price"] for item in items),
        },
        "items": items,
    }


def serialize(catalog: dict) -> str:
    return json.dumps(catalog, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if the committed catalog is stale.")
    args = parser.parse_args()

    try:
        catalog = build(SOURCE.read_text(encoding="utf-8"))
    except (ExtractionError, OSError) as exc:
        print(f"side-store catalog extraction failed: {exc}", file=sys.stderr)
        return 1

    rendered = serialize(catalog)

    if args.check:
        if not OUTPUT.is_file():
            print(f"{OUTPUT.relative_to(REPO_ROOT)} is missing; "
                  f"run python3 tools/side_store_catalog.py", file=sys.stderr)
            return 1
        if OUTPUT.read_text(encoding="utf-8") != rendered:
            print(f"{OUTPUT.relative_to(REPO_ROOT)} is stale; "
                  f"run python3 tools/side_store_catalog.py", file=sys.stderr)
            return 1
        print(f"side-store catalog current: {catalog['summary']['sku_count']} SKUs, "
              f"{len(catalog['summary']['categories'])} categories")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} — "
          f"{catalog['summary']['sku_count']} SKUs, "
          f"${catalog['summary']['price_min']}–${catalog['summary']['price_max']} {CURRENCY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
