# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
from __future__ import annotations

import json

import pytest

from scripts import store_sync
from scripts.store_sync import (
    ROOT,
    StoreSyncError,
    _parse_amount_cents,
    _strip_tags,
    build_catalog,
    content_hash,
    render_document,
)


def _store_html(products: dict[str, dict]) -> str:
    """Build a minimal but valid store.html for the given SKUs.

    products maps sku -> {"name", "price", "link", "label", "short", "etx"}.
    """
    cards = "\n".join(
        f'<article class="card" data-sku="{sku}"><h3>{p["name"]}</h3>'
        f'<div class="price">{p["price"]}</div><a class="buy" data-buy>Buy</a></article>'
        for sku, p in products.items()
    )

    def _obj(field: str) -> str:
        body = ", ".join(f'"{sku}": "{p[field]}"' for sku, p in products.items())
        return "{ " + body + " }"

    return (
        "<html><body><section id='store'>" + cards + "</section>"
        "<p>nothing is auto-charged</p>"
        "<script>"
        f"var CHECKOUT = {_obj('link')};"
        f"var LABEL = {_obj('label')};"
        f"var SHORT = {_obj('short')};"
        f"var ETX_AMOUNT = {_obj('etx')};"
        "var guard = /https:\\/\\/(buy|book|checkout)\\.stripe\\.com\\//;"
        "</script></body></html>"
    )


def _product(name="Thing", price="CAD $249 one-time", link="", **kw) -> dict:
    base = {"name": name, "price": price, "link": link,
            "label": f"{name} label", "short": name, "etx": "CAD $249"}
    base.update(kw)
    return base


@pytest.fixture
def temp_root(tmp_path, monkeypatch):
    """A throwaway repo root with a store.html and data dir wired into module globals."""
    data_dir = tmp_path / "data" / "store"
    monkeypatch.setattr(store_sync, "DATA_DIR", data_dir)
    monkeypatch.setattr(store_sync, "CATALOG_PATH", data_dir / "catalog.json")
    monkeypatch.setattr(store_sync, "LKG_PATH", data_dir / "last-known-good.json")

    def _write(products: dict[str, dict]) -> None:
        (tmp_path / "store.html").write_text(_store_html(products), encoding="utf-8")

    return tmp_path, _write


# ── pure helpers ────────────────────────────────────────────────────────────

def test_strip_tags_normalizes_entities_and_whitespace():
    assert _strip_tags("CAD&nbsp;$249 <small>one-time</small>") == "CAD $249 one-time"
    assert _strip_tags("A &amp; B") == "A & B"


@pytest.mark.parametrize("price,cents", [
    ("CAD $249 one-time", 24900),
    ("from CAD $2,500 fixed fee", 250000),
    ("from CAD $600 / month", 60000),
    ("CAD $19.99", 1999),
    ("contact us", None),
])
def test_parse_amount_cents(price, cents):
    assert _parse_amount_cents(price) == cents


# ── build_catalog on the real shipped storefront ────────────────────────────

def test_real_store_html_is_catalog_ready():
    catalog = build_catalog(ROOT)
    skus = {p["sku"] for p in catalog["products"]}
    assert {"quick-audit", "hardening", "phipa", "monitoring"} <= skus
    quick = next(p for p in catalog["products"] if p["sku"] == "quick-audit")
    assert quick["amount_cents"] == 24900
    assert quick["currency"] == "CAD"
    assert catalog["summary"]["sku_count"] == len(catalog["products"])


# ── build_catalog behaviour ─────────────────────────────────────────────────

def test_paused_checkout_records_fallback_note(temp_root):
    root, write = temp_root
    write({"a": _product(link=""), "b": _product(link="")})
    catalog = build_catalog(root)
    assert catalog["live_checkout_enabled"] is False
    assert catalog["summary"]["live_checkout_skus"] == 0
    assert "fallback_note" in catalog  # revenue-continuity state is explicit


def test_live_stripe_link_flips_enabled_and_drops_fallback(temp_root):
    root, write = temp_root
    write({
        "a": _product(link="https://buy.stripe.com/test_123"),
        "b": _product(link=""),
    })
    catalog = build_catalog(root)
    assert catalog["live_checkout_enabled"] is True
    assert catalog["summary"]["live_checkout_skus"] == 1
    assert "fallback_note" not in catalog


def test_unsafe_checkout_url_fails_closed(temp_root):
    root, write = temp_root
    write({"a": _product(link="http://evil.example/pay")})
    with pytest.raises(StoreSyncError, match="not a safe Stripe URL"):
        build_catalog(root)


def test_missing_map_entry_fails_closed(temp_root):
    root, write = temp_root
    root.joinpath("store.html").write_text(
        '<article data-sku="a"><h3>A</h3><div class="price">CAD $1</div></article>'
        "<script>var CHECKOUT={\"a\":\"\"};var LABEL={};var SHORT={};var ETX_AMOUNT={};</script>",
        encoding="utf-8",
    )
    with pytest.raises(StoreSyncError, match="missing from"):
        build_catalog(root)


def test_no_product_cards_fails_closed(temp_root):
    root, _ = temp_root
    root.joinpath("store.html").write_text("<html>no cards</html>", encoding="utf-8")
    with pytest.raises(StoreSyncError, match="no product cards"):
        build_catalog(root)


def test_missing_store_html_fails_closed(tmp_path):
    with pytest.raises(StoreSyncError, match="store.html not found"):
        build_catalog(tmp_path)


# ── hashing + document shape ────────────────────────────────────────────────

def test_content_hash_is_stable_and_timestamp_independent():
    catalog = build_catalog(ROOT)
    h1 = content_hash(catalog)
    doc = render_document(catalog)
    # The wrapped document carries a timestamp but its hash matches the content.
    assert doc["content_hash"] == h1
    assert "generated_utc" in doc
    # Re-rendering at a different time must not change the content hash.
    import datetime as _dt
    later = render_document(catalog, now=_dt.datetime(2030, 1, 1, tzinfo=_dt.timezone.utc))
    assert later["content_hash"] == h1
    assert later["generated_utc"] != doc["generated_utc"]


def test_content_hash_changes_when_a_price_changes(temp_root):
    root, write = temp_root
    write({"a": _product(price="CAD $249")})
    before = content_hash(build_catalog(root))
    write({"a": _product(price="CAD $299")})
    assert content_hash(build_catalog(root)) != before


# ── command surface: write / check / promote ────────────────────────────────

def test_write_then_check_round_trips(temp_root):
    root, write = temp_root
    write({"a": _product(), "b": _product(name="Two")})
    assert store_sync.cmd_write(root) == 0
    assert store_sync.CATALOG_PATH.exists()
    assert store_sync.cmd_check(root) == 0


def test_check_fails_when_missing(temp_root):
    root, write = temp_root
    write({"a": _product()})
    assert store_sync.cmd_check(root) == 1  # never written


def test_check_detects_drift(temp_root):
    root, write = temp_root
    write({"a": _product(price="CAD $249")})
    store_sync.cmd_write(root)
    # storefront price changes but catalog.json is not regenerated -> drift
    write({"a": _product(price="CAD $999")})
    assert store_sync.cmd_check(root) == 1


def test_promote_records_last_known_good(temp_root):
    root, write = temp_root
    write({"a": _product()})
    store_sync.cmd_write(root)
    assert store_sync.cmd_promote(root) == 0
    anchor = json.loads(store_sync.LKG_PATH.read_text(encoding="utf-8"))
    catalog_doc = json.loads(store_sync.CATALOG_PATH.read_text(encoding="utf-8"))
    assert anchor["content_hash"] == catalog_doc["content_hash"]


def test_promote_refuses_out_of_sync_catalog(temp_root):
    root, write = temp_root
    write({"a": _product(price="CAD $1")})
    store_sync.cmd_write(root)
    write({"a": _product(price="CAD $2")})  # drift without re-write
    assert store_sync.cmd_promote(root) == 1
    assert not store_sync.LKG_PATH.exists()


def test_main_routes_each_flag_to_its_command(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(store_sync, "cmd_write", lambda *_a, **_k: calls.append("write") or 0)
    monkeypatch.setattr(store_sync, "cmd_check", lambda *_a, **_k: calls.append("check") or 0)
    monkeypatch.setattr(store_sync, "cmd_promote", lambda *_a, **_k: calls.append("promote") or 0)
    assert store_sync.main(["--write"]) == 0
    assert store_sync.main(["--check"]) == 0
    assert store_sync.main(["--promote"]) == 0
    assert calls == ["write", "check", "promote"]


def test_main_surfaces_sync_errors_as_exit_1(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(store_sync, "build_catalog",
                        lambda *_a, **_k: (_ for _ in ()).throw(StoreSyncError("boom")))
    assert store_sync.main([]) == 1


def test_real_repo_catalog_is_committed_in_sync():
    # The shipped data/store/catalog.json must match the shipped store.html.
    # This is the same invariant the auto-store CI gate enforces.
    assert store_sync.cmd_check(ROOT) == 0
