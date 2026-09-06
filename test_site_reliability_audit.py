# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Regression tests for scripts/site_reliability_audit.py."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from scripts import site_reliability_audit as audit


def test_iter_repo_html_files_ignores_dependency_and_build_dirs(tmp_path: Path) -> None:
    """Generated dependency/build HTML must not create false audit failures."""

    (tmp_path / "index.html").write_text("<html></html>")
    ignored_html = tmp_path / "app" / "node_modules" / "pkg" / "broken.html"
    ignored_html.parent.mkdir(parents=True)
    ignored_html.write_text('<script src="/_next/static/chunks/missing.js"></script>')
    next_html = tmp_path / ".next" / "server" / "app.html"
    next_html.parent.mkdir(parents=True)
    next_html.write_text('<link href="/_next/static/chunks/missing.css" rel="stylesheet">')

    with patch.object(audit, "REPO_ROOT", tmp_path):
        assert audit.iter_repo_html_files() == [tmp_path / "index.html"]


def test_check_links_rejects_missing_fragment_targets(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        '<a href="details.html#available">Working</a>'
        '<a href="details.html#missing">Broken</a>',
        encoding="utf-8",
    )
    (tmp_path / "details.html").write_text(
        '<section id="available"></section>', encoding="utf-8"
    )

    with patch.object(audit, "REPO_ROOT", tmp_path):
        issues = audit.check_links()

    assert [issue.message for issue in issues] == [
        "Missing fragment target index.html:1 -> details.html#missing"
    ]


def test_check_sitemap_rejects_duplicates_and_unpublished_routes(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "sitemap.xml").write_text(
        """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.clearglassinc.com/</loc></url>
  <url><loc>https://www.clearglassinc.com/</loc></url>
  <url><loc>https://www.clearglassinc.com/missing.html</loc></url>
  <url><loc>http://example.com/index.html</loc></url>
</urlset>
""",
        encoding="utf-8",
    )

    with patch.object(audit, "REPO_ROOT", tmp_path):
        messages = [issue.message for issue in audit.check_sitemap()]

    assert "Duplicate URL in sitemap: https://www.clearglassinc.com/" in messages
    assert any("missing.html" in message for message in messages)
    assert any("outside the canonical HTTPS origin" in message for message in messages)


def test_check_robots_rejects_malformed_and_missing_sitemaps(tmp_path: Path) -> None:
    (tmp_path / "robots.txt").write_text(
        "User-agent: *\nmalformed\nSitemap: https://www.clearglassinc.com/missing.xml\n",
        encoding="utf-8",
    )
    with patch.object(audit, "REPO_ROOT", tmp_path):
        messages = [issue.message for issue in audit.check_robots()]
    assert any("Malformed robots.txt directive" in message for message in messages)
    assert any("declares a missing sitemap" in message for message in messages)
