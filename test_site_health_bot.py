# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for bots/site_health_bot.py."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bots.site_health_bot import (  # noqa: E402
    IGNORED_HTML_DIRS,
    LOGO_EXEMPT,
    PAGES_TO_CHECK,
    REQUIRED_ROOT_FILES,
    PageHealth,
    _check_local_files,
    _check_page,
    _page_has_logo,
)


class TestPageHealth:
    def test_dataclass_construction(self) -> None:
        ph = PageHealth(
            path="/", url="https://example.com/",
            status_code=200, reachable=True,
            response_ms=42, has_title=True, missing_meta=[],
        )
        assert ph.reachable is True
        assert ph.status_code == 200
        assert ph.error is None

    def test_unreachable_defaults(self) -> None:
        ph = PageHealth(
            path="/404", url="https://example.com/404",
            status_code=None, reachable=False,
            response_ms=0, has_title=False, missing_meta=["description"],
            error="Connection refused",
        )
        assert ph.reachable is False
        assert ph.error is not None


class TestCheckLocalFiles:
    def test_returns_errors_and_warnings(self) -> None:
        # Contract: _check_local_files() -> tuple[list[str], list[str]]
        result = _check_local_files()
        assert isinstance(result, tuple) and len(result) == 2
        errors, warnings = result
        assert isinstance(errors, list)
        assert isinstance(warnings, list)

    def test_all_strings(self) -> None:
        errors, warnings = _check_local_files()
        for issue in (*errors, *warnings):
            assert isinstance(issue, str)


class TestCheckPage:
    def test_url_error_returns_unreachable(self) -> None:
        from urllib.error import URLError
        with patch("bots.site_health_bot.urlopen", side_effect=URLError("timeout")):
            result = _check_page("/test-path")
        assert result.reachable is False
        assert result.error is not None
        assert result.path == "/test-path"

    def test_http_200_marks_reachable(self) -> None:
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        mock_resp.read.return_value = b"<html><title>Test</title></html>"

        with patch("bots.site_health_bot.urlopen", return_value=mock_resp):
            result = _check_page("/")
        assert result.reachable is True
        assert result.status_code == 200

    def test_http_404_marks_unreachable(self) -> None:
        from urllib.error import HTTPError
        err = HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
        with patch("bots.site_health_bot.urlopen", side_effect=err):
            result = _check_page("/missing")
        assert result.reachable is False


class TestLogoCoverage:
    """The ClearGlass logo must be present on every shipped webpage."""

    def test_detects_badge_script(self) -> None:
        assert _page_has_logo('<script defer src="/logo-badge.js"></script>')

    def test_detects_logo_image(self) -> None:
        assert _page_has_logo('<img src="assets/images/clearglass-logo.png">')

    def test_negative_when_no_logo(self) -> None:
        assert not _page_has_logo("<html><body>no brand here</body></html>")

    def test_every_shipped_page_has_logo(self) -> None:
        missing = [
            str(p.relative_to(ROOT))
            for p in sorted(ROOT.rglob("*.html"))
            if not any(part in IGNORED_HTML_DIRS for part in p.relative_to(ROOT).parts)
            and p.name not in LOGO_EXEMPT
            and not _page_has_logo(p.read_text(encoding="utf-8", errors="replace"))
        ]
        assert not missing, f"Pages missing the ClearGlass logo: {missing}"

    def test_missing_logo_is_reported_as_failure(self, tmp_path: Path) -> None:
        # A page without the logo must surface as an error (fails health),
        # not merely a warning.
        page = tmp_path / "no-logo.html"
        page.write_text("<html><body>nothing branded</body></html>")
        with patch("bots.site_health_bot.ROOT", tmp_path):
            errors, _warnings = _check_local_files()
        assert any("missing ClearGlass logo" in e for e in errors)


class TestConstants:
    def test_pages_to_check_not_empty(self) -> None:
        assert len(PAGES_TO_CHECK) > 0

    def test_required_root_files_not_empty(self) -> None:
        assert len(REQUIRED_ROOT_FILES) > 0

    def test_all_pages_start_with_slash(self) -> None:
        for p in PAGES_TO_CHECK:
            assert p.startswith("/"), f"Page path must start with /: {p}"
