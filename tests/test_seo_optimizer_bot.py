# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for bots/seo_optimizer_bot.py."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bots.seo_optimizer_bot import (  # noqa: E402
    SEOReport,
    _audit_file,
    _extract_meta_content,
    run,
)

PERFECT_HTML = """<!doctype html>
<html lang="en"><head>
<title>ClearGlass Intelligent Compliance Automation Platform</title>
<meta name="description" content="ClearGlass delivers intelligent compliance automation, security tooling and revenue operations for modern regulated enterprises today.">
<link rel="canonical" href="https://www.clearglassinc.com/">
<meta property="og:title" content="ClearGlass">
<meta property="og:description" content="Compliance automation">
<meta property="og:image" content="/logo.png">
</head><body>
<h1>ClearGlass</h1>
<img src="/logo.png" alt="ClearGlass logo">
</body></html>
"""

POOR_HTML = "<html><head></head><body><img src='/a.png'></body></html>"


class TestExtractMetaContent:
    def test_name_then_content(self) -> None:
        html = '<meta name="description" content="hello world">'
        assert _extract_meta_content(html, "description") == "hello world"

    def test_content_then_name(self) -> None:
        html = '<meta content="hello world" name="description">'
        assert _extract_meta_content(html, "description") == "hello world"

    def test_missing_returns_none(self) -> None:
        assert _extract_meta_content("<head></head>", "description") is None


class TestAuditFile:
    def test_perfect_page_scores_high(self, tmp_path: Path) -> None:
        f = tmp_path / "good.html"
        f.write_text(PERFECT_HTML)
        result = _audit_file(f)
        assert result.file == "good.html"
        assert result.h1_count == 1
        assert result.canonical_present is True
        assert result.img_without_alt == 0
        assert result.score == 100
        assert result.issues == []

    def test_poor_page_reports_issues(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.html"
        f.write_text(POOR_HTML)
        result = _audit_file(f)
        assert result.score < 50
        assert "Missing <title>" in result.issues
        assert any("alt text" in i for i in result.issues)


class TestRun:
    def test_run_writes_reports(self, tmp_path: Path) -> None:
        site = tmp_path / "site"
        site.mkdir()
        (site / "index.html").write_text(PERFECT_HTML)
        (site / "bad.html").write_text(POOR_HTML)
        out = tmp_path / "output"
        with patch("bots.seo_optimizer_bot.ROOT", site), \
             patch("bots.seo_optimizer_bot.OUTPUT_DIR", out):
            report = run()
        assert isinstance(report, SEOReport)
        assert report.files_audited == 2
        assert (out / "seo_report.json").exists()
        assert (out / "seo_report.md").exists()
        assert 0 <= report.average_score <= 100

    def test_run_handles_no_html(self, tmp_path: Path) -> None:
        site = tmp_path / "empty"
        site.mkdir()
        out = tmp_path / "output"
        with patch("bots.seo_optimizer_bot.ROOT", site), \
             patch("bots.seo_optimizer_bot.OUTPUT_DIR", out):
            report = run()
        assert report.files_audited == 0
        assert report.average_score == 0.0
