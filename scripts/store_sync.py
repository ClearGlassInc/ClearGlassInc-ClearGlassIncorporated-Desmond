# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Store-data sync — derive a canonical machine-readable catalog from the shop.

`store.html` is the single source of truth for the public storefront: the
product cards, prices, Stripe checkout links, and Interac e-Transfer amounts all
live there. This module distils that HTML into a deterministic JSON catalog
(`data/store/catalog.json`) that downstream consumers (the autostore control
plane, analytics, the cockpit) can read **without re-parsing HTML on every
request** — which is both faster and far less brittle.

It is the "sync store data" step of the auto-store workflow, and it is the
rollback anchor: `--promote` records the current validated catalog as the
last-known-good release marker (`data/store/last-known-good.json`) that a
failed deploy rolls back to.

Design goals (mirrors the repo's static-check philosophy — no network, no
secrets, deterministic):

  * The content hash covers only the *catalog content*, never the wall-clock
    timestamp, so `--check` is reproducible in CI and a docs-only change never
    spuriously reports drift.
  * `--check` fails closed: if the committed catalog no longer matches
    `store.html`, the build stops and tells you to re-run `--write`. This keeps
    the published data and the storefront from silently diverging.
  * Live card checkout being *off* is a valid, healthy state. When Stripe
    capabilities are paused, every checkout link is empty and the storefront
    falls back to Interac e-Transfer / invoice — revenue keeps flowing. The
    catalog records this explicitly instead of treating it as a defect.

Usage:
  python scripts/store_sync.py --check     # CI gate: committed catalog in sync?
  python scripts/store_sync.py --write      # regenerate catalog.json
  python scripts/store_sync.py --promote    # record last-known-good (rollback anchor)
  python scripts/store_sync.py              # print catalog JSON to stdout (dry run)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE_HTML = ROOT / "store.html"
PRICING_HTML = ROOT / "pricing.html"
DATA_DIR = ROOT / "data" / "store"
CATALOG_PATH = DATA_DIR / "catalog.json"
LKG_PATH = DATA_DIR / "last-known-good.json"

SCHEMA = "clearglass.store.catalog/v1"

# The only checkout-link shape the storefront runtime guard accepts (kept in
# lockstep with bots/store_smoke_bot.py). Anything else must never be published
# as a live link — it would silently bypass the money-safety guard.
STRIPE_LINK_RE = re.compile(r"^https://(?:buy|book|checkout)\.stripe\.com/\S+$")


class StoreSyncError(RuntimeError):
    """Raised when the storefront cannot be turned into a valid catalog."""


def _strip_tags(fragment: str) -> str:
    """Collapse an HTML fragment to clean single-spaced text."""
    text = re.sub(r"<[^>]+>", " ", fragment)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def _extract_map(html: str, name: str) -> dict[str, str]:
    """Parse `var NAME = { "k": "v", ... }` into a dict (values may be empty)."""
    match = re.search(rf"var\s+{re.escape(name)}\s*=\s*\{{(.*?)\}}", html, re.DOTALL)
    if not match:
        return {}
    return dict(re.findall(r"""["']([\w-]+)["']\s*:\s*"([^"]*)\"""", match.group(1)))


def _extract_articles(html: str) -> list[tuple[str, str]]:
    """Return (sku, inner_html) for every product card, in document order."""
    return re.findall(r'<article[^>]*data-sku="([\w-]+)"(.*?)</article>', html, re.DOTALL)


def _parse_amount_cents(price_display: str) -> int | None:
    """First `$1,234` style figure in the price line, as integer cents."""
    match = re.search(r"\$\s*([\d,]+)(?:\.(\d{2}))?", price_display)
    if not match:
        return None
    dollars = int(match.group(1).replace(",", ""))
    cents = int(match.group(2)) if match.group(2) else 0
    return dollars * 100 + cents


def build_catalog(root: Path = ROOT) -> dict:
    """Distil store.html into the canonical catalog dict (no timestamp).

    Raises StoreSyncError on a malformed storefront so the sync fails closed
    rather than publishing a half-broken catalog.
    """
    store_path = root / "store.html"
    if not store_path.exists():
        raise StoreSyncError("store.html not found — cannot sync catalog")

    html = store_path.read_text(encoding="utf-8", errors="replace")
    articles = _extract_articles(html)
    if not articles:
        raise StoreSyncError("store.html has no product cards (data-sku)")

    checkout = _extract_map(html, "CHECKOUT")
    label = _extract_map(html, "LABEL")
    short = _extract_map(html, "SHORT")
    etx = _extract_map(html, "ETX_AMOUNT")

    products: list[dict] = []
    errors: list[str] = []
    for sku, inner in articles:
        name_match = re.search(r"<h3>(.*?)</h3>", inner, re.DOTALL)
        price_match = re.search(r'<div class="price">(.*?)</div>', inner, re.DOTALL)
        price_display = _strip_tags(price_match.group(1)) if price_match else ""
        checkout_url = (checkout.get(sku) or "").strip()

        if checkout_url and not STRIPE_LINK_RE.match(checkout_url):
            errors.append(f"{sku}: checkout link is not a safe Stripe URL: {checkout_url!r}")
        for map_name, mapping in (("LABEL", label), ("SHORT", short), ("ETX_AMOUNT", etx)):
            if sku not in mapping:
                errors.append(f"{sku}: missing from {map_name} checkout map")

        products.append({
            "sku": sku,
            "name": _strip_tags(name_match.group(1)) if name_match else sku,
            "label": label.get(sku, ""),
            "short": short.get(sku, ""),
            "price_display": price_display,
            "amount_cents": _parse_amount_cents(price_display),
            "currency": "CAD",
            "etransfer_amount": etx.get(sku, ""),
            "checkout_url": checkout_url,
            "live_checkout": bool(checkout_url),
        })

    if errors:
        raise StoreSyncError("storefront is not catalog-ready:\n  - " + "\n  - ".join(errors))

    live_skus = [p["sku"] for p in products if p["live_checkout"]]
    catalog = {
        "schema": SCHEMA,
        "source": "store.html",
        "live_checkout_enabled": bool(live_skus),
        "products": products,
        "summary": {
            "sku_count": len(products),
            "live_checkout_skus": len(live_skus),
        },
    }
    # When no live link is configured the storefront is on its e-Transfer /
    # invoice fallback (e.g. Stripe capabilities paused). Record it so the
    # health gate can treat it as a known revenue-continuity state, not a defect.
    if not live_skus:
        catalog["fallback_note"] = (
            "Live card checkout disabled (no Stripe Payment Links configured). "
            "Interac e-Transfer + confirmed-invoice flow active — revenue continuity preserved."
        )
    return catalog


def content_hash(catalog: dict) -> str:
    """Stable sha256 over catalog content, excluding any volatile metadata."""
    payload = {k: v for k, v in catalog.items() if k not in {"generated_utc", "content_hash"}}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def render_document(catalog: dict, *, now: datetime | None = None) -> dict:
    """Wrap the catalog with generated timestamp + content hash for writing."""
    stamp = (now or datetime.now(timezone.utc)).replace(microsecond=0).isoformat()
    return {
        "schema": catalog["schema"],
        "generated_utc": stamp,
        "content_hash": content_hash(catalog),
        **{k: v for k, v in catalog.items() if k != "schema"},
    }


def _serialize(document: dict) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def cmd_write(root: Path = ROOT) -> int:
    catalog = build_catalog(root)
    document = render_document(catalog)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(_serialize(document), encoding="utf-8")
    print(
        f"Wrote {CATALOG_PATH.relative_to(root)} — "
        f"{catalog['summary']['sku_count']} SKU(s), "
        f"{catalog['summary']['live_checkout_skus']} live checkout, "
        f"{document['content_hash']}"
    )
    return 0


def cmd_check(root: Path = ROOT) -> int:
    """Fail closed if the committed catalog has drifted from store.html."""
    catalog = build_catalog(root)
    want = content_hash(catalog)
    if not CATALOG_PATH.exists():
        print(f"FAIL: {CATALOG_PATH.relative_to(root)} is missing — run: "
              f"python scripts/store_sync.py --write", file=sys.stderr)
        return 1
    try:
        have = json.loads(CATALOG_PATH.read_text(encoding="utf-8")).get("content_hash")
    except json.JSONDecodeError as exc:
        print(f"FAIL: {CATALOG_PATH.relative_to(root)} is not valid JSON: {exc}", file=sys.stderr)
        return 1
    if have != want:
        print(
            "FAIL: store catalog is out of sync with store.html.\n"
            f"  committed: {have}\n  expected:  {want}\n"
            "  Re-run: python scripts/store_sync.py --write",
            file=sys.stderr,
        )
        return 1
    print(f"OK: store catalog in sync with store.html ({want})")
    return 0


def cmd_promote(root: Path = ROOT) -> int:
    """Record the current catalog as last-known-good (the rollback anchor)."""
    if cmd_check(root) != 0:
        print("Refusing to promote an out-of-sync catalog.", file=sys.stderr)
        return 1
    document = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    anchor = {
        "schema": "clearglass.store.lkg/v1",
        "promoted_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "content_hash": document["content_hash"],
        "summary": document.get("summary", {}),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LKG_PATH.write_text(_serialize(anchor), encoding="utf-8")
    print(f"Promoted last-known-good {anchor['content_hash']} -> {LKG_PATH.relative_to(root)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help="regenerate data/store/catalog.json")
    group.add_argument("--check", action="store_true", help="fail if catalog is out of sync (CI gate)")
    group.add_argument("--promote", action="store_true", help="record last-known-good rollback anchor")
    args = parser.parse_args(argv)

    try:
        if args.write:
            return cmd_write()
        if args.check:
            return cmd_check()
        if args.promote:
            return cmd_promote()
        # Default: dry-run to stdout (no files touched).
        print(_serialize(render_document(build_catalog())), end="")
        return 0
    except StoreSyncError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
