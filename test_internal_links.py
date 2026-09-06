"""Regression tests for the generated site-wide journey navigation."""

from __future__ import annotations

import importlib.util
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("internal_links", ROOT / "tools/internal_links.py")
assert SPEC and SPEC.loader
internal_links = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(internal_links)


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


def test_every_page_has_one_current_journey_module() -> None:
    for page in internal_links.PAGES:
        document = (ROOT / page).read_text(encoding="utf-8", errors="surrogateescape")
        assert document.count(internal_links.START) == 1, page
        assert document.count(internal_links.END) == 1, page
        assert internal_links.build_block(page) in document, page


def test_generated_journey_destinations_exist() -> None:
    for page in internal_links.PAGES:
        parser = LinkParser()
        parser.feed(internal_links.build_block(page))
        source_directory = (ROOT / page).parent
        for href in parser.hrefs:
            path = urlsplit(href).path
            assert path and not path.startswith("/"), (page, href)
            assert (source_directory / path).resolve().is_file(), (page, href)


def test_journey_rail_is_complete_and_never_self_links() -> None:
    for page in internal_links.PAGES:
        previous, hub, following = internal_links.journey_targets(page)
        assert previous in internal_links.PAGES
        assert hub in internal_links.PAGES
        assert following in internal_links.PAGES
        assert previous != page
        assert following != page


def test_flow_report_is_current() -> None:
    assert internal_links.REPORT_PATH.read_text(encoding="utf-8") == internal_links.build_report()


def test_every_html_page_is_mapped_or_explicitly_excluded() -> None:
    discovered = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*.html")
        if not {".git", "node_modules", ".next"} & set(path.parts)
    }
    mapped = set(internal_links.PAGES)
    excluded = set(internal_links.EXCLUDED_PAGES)

    assert not mapped & excluded
    assert discovered == mapped | excluded
