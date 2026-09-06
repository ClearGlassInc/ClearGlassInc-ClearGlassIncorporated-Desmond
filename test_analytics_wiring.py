# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests that the site-wide analytics loader is wired correctly.

These are static checks: analytics.js itself stays config-gated (off until the
owner sets a provider), but it must be (a) present and idempotent, (b) loaded
site-wide via stealth-glass.js, and (c) reachable on the buying funnel pages.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The pages a visitor actually moves through on the way to paying. Analytics is
# worthless if it is missing from these, so they are asserted explicitly.
FUNNEL_PAGES = ("index.html", "store.html", "pricing.html")


def test_analytics_file_present_and_idempotent() -> None:
    js = (ROOT / "analytics.js").read_text(encoding="utf-8")
    assert "__cgAnalytics" in js, "analytics.js must guard against double-init"
    assert "CONFIG" in js, "analytics.js must expose a CONFIG block to switch on"


def test_stealth_glass_loads_analytics() -> None:
    js = (ROOT / "stealth-glass.js").read_text(encoding="utf-8")
    assert "/analytics.js" in js, "stealth-glass.js must inject the analytics loader"


def test_funnel_pages_carry_the_universal_loader() -> None:
    missing = [
        page for page in FUNNEL_PAGES
        if "stealth-glass.js" not in (ROOT / page).read_text(encoding="utf-8")
    ]
    assert not missing, f"funnel pages missing /stealth-glass.js (lose analytics): {missing}"
