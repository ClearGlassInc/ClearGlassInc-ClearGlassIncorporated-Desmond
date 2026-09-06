# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for bots/content_collector_bot.py."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bots.content_collector_bot import (  # noqa: E402
    CollectionReport,
    PageRecord,
    _PageExtractor,
    _normalize,
    collect_page,
    discover_pages,
    run,
)

RICH_HTML = """<!doctype html>
<html lang="en"><head>
<title>ClearGlass Platform</title>
<meta name="description" content="Compliance automation platform.">
<meta name="keywords" content="compliance, automation">
<meta property="og:title" content="ClearGlass">
<meta property="og:image" content="/logo.png">
<meta name="twitter:card" content="summary">
<link rel="canonical" href="https://www.clearglassinc.com/">
<script type="application/ld+json">{"@type": "Organization", "name": "ClearGlass"}</script>
<style>.x{color:red}</style>
</head><body>
<h1>Welcome to ClearGlass</h1>
<h2>Our Products</h2>
<p>We deliver intelligent compliance automation.</p>
<a href="/artemis.html">Artemis</a>
<img src="/logo.png" alt="ClearGlass logo">
<script>console.log("ignore me");</script>
</body></html>
"""


class TestNormalize:
    def test_collapses_whitespace(self) -> None:
        assert _normalize("  hello   world\n\t ") == "hello world"

    def test_empty(self) -> None:
        assert _normalize("   ") == ""


class TestPageExtractor:
    def test_extracts_core_fields(self) -> None:
        p = _PageExtractor()
        p.feed(RICH_HTML)
        assert p.title.strip() == "ClearGlass Platform"
        assert p.lang == "en"
        assert p.meta["description"] == "Compliance automation platform."
        assert p.meta["og:title"] == "ClearGlass"
        assert p.canonical == "https://www.clearglassinc.com/"

    def test_extracts_headings_links_images(self) -> None:
        p = _PageExtractor()
        p.feed(RICH_HTML)
        assert {"level": "h1", "text": "Welcome to ClearGlass"} in p.headings
        assert {"level": "h2", "text": "Our Products"} in p.headings
        assert p.links == [{"href": "/artemis.html", "text": "Artemis"}]
        assert p.images == [{"src": "/logo.png", "alt": "ClearGlass logo"}]

    def test_extracts_json_ld(self) -> None:
        p = _PageExtractor()
        p.feed(RICH_HTML)
        assert p.json_ld == [{"@type": "Organization", "name": "ClearGlass"}]

    def test_excludes_script_and_style_text(self) -> None:
        p = _PageExtractor()
        p.feed(RICH_HTML)
        text = p.text()
        assert "intelligent compliance automation" in text
        assert "ignore me" not in text
        assert "color:red" not in text

    def test_malformed_json_ld_is_skipped(self) -> None:
        p = _PageExtractor()
        p.feed('<script type="application/ld+json">{not valid}</script>')
        assert p.json_ld == []


class TestCollectPage:
    def test_builds_record(self, tmp_path: Path) -> None:
        f = tmp_path / "index.html"
        f.write_text(RICH_HTML)
        with patch("bots.content_collector_bot.ROOT", tmp_path):
            record = collect_page(f)
        assert isinstance(record, PageRecord)
        assert record.path == "index.html"
        assert record.url == "https://www.clearglassinc.com/"
        assert record.title == "ClearGlass Platform"
        assert record.word_count > 0
        assert len(record.content_hash) == 16
        assert record.twitter == {"twitter:card": "summary"}


class TestDiscoverPages:
    def test_skips_configured_dirs(self, tmp_path: Path) -> None:
        (tmp_path / "page.html").write_text("<html></html>")
        skip = tmp_path / "bots"
        skip.mkdir()
        (skip / "internal.html").write_text("<html></html>")
        with patch("bots.content_collector_bot.ROOT", tmp_path):
            pages = discover_pages()
        names = {p.name for p in pages}
        assert "page.html" in names
        assert "internal.html" not in names


class TestRun:
    def test_run_writes_store_and_index(self, tmp_path: Path) -> None:
        site = tmp_path / "site"
        site.mkdir()
        (site / "index.html").write_text(RICH_HTML)
        (site / "about.html").write_text("<html><head><title>About</title></head>"
                                         "<body><p>About us</p></body></html>")
        out = tmp_path / "output"
        with patch("bots.content_collector_bot.ROOT", site), \
             patch("bots.content_collector_bot.OUTPUT_DIR", out), \
             patch("bots.content_collector_bot.STORE_FILE", out / "site_content_store.json"), \
             patch("bots.content_collector_bot.INDEX_FILE", out / "site_content_collection.md"):
            report = run()
        assert isinstance(report, CollectionReport)
        assert report.pages_collected == 2
        assert report.total_words > 0
        assert (out / "site_content_store.json").exists()
        assert (out / "site_content_collection.md").exists()

    def test_run_handles_no_pages(self, tmp_path: Path) -> None:
        site = tmp_path / "empty"
        site.mkdir()
        out = tmp_path / "output"
        with patch("bots.content_collector_bot.ROOT", site), \
             patch("bots.content_collector_bot.OUTPUT_DIR", out), \
             patch("bots.content_collector_bot.STORE_FILE", out / "site_content_store.json"), \
             patch("bots.content_collector_bot.INDEX_FILE", out / "site_content_collection.md"):
            report = run()
        assert report.pages_collected == 0
        assert report.total_words == 0
