# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Opt-in live checks against the two real data providers.

Skipped unless ``CG_LIVE_FEEDS=1``. Each test makes one read-only GET to the
provider the site already depends on, through the same fetch and parse code
the feed scripts use, and writes nothing. Offline parser behaviour is covered
by ``test_ieso_public_feed.py`` and ``test_minerals_intelligence.py``; these
exist to prove the providers still answer in the shape those parsers expect.

    CG_LIVE_FEEDS=1 python -m pytest tests/test_live_feeds.py -q

A failure here is information about the provider or the network, not about
this repository — so it never runs in CI by default.
"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("CG_LIVE_FEEDS") != "1",
                                reason="live provider checks are opt-in: set CG_LIVE_FEEDS=1")


def test_ieso_demand_report_is_reachable_and_parses() -> None:
    from scripts.ieso_public_feed import DEMAND, fetch, parse_demand

    body, final_url, _last_modified = fetch(DEMAND["url"], timeout=30)
    assert final_url.startswith("https://reports-public.ieso.ca/")
    parsed = parse_demand(body)
    assert parsed, "IESO demand report parsed to nothing"


def test_government_of_canada_news_feed_is_reachable_and_parses() -> None:
    from scripts.minerals_data_sync import NRCAN_ATOM, fetch_bytes, parse_atom

    entries = parse_atom(fetch_bytes(NRCAN_ATOM, timeout=30, retries=1))
    assert isinstance(entries, list)
    assert all(e.get("url") is None or str(e["url"]).startswith("https://") for e in entries)
