"""Regression checks for the static homepage's critical UI wiring."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
HOMEPAGE = ROOT / "index.html"


class HomepageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.local_references: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if element_id := attributes.get("id"):
            self.ids.append(element_id)
        if tag == "script" and (source := attributes.get("src")):
            self.scripts.append(source)
        for name in ("href", "src", "poster"):
            reference = attributes.get(name)
            if not reference:
                continue
            parsed = urlparse(reference)
            if parsed.scheme or parsed.netloc or reference.startswith(("#", "mailto:", "tel:")):
                continue
            self.local_references.append(unquote(parsed.path).lstrip("/"))


def parse_homepage() -> HomepageParser:
    parser = HomepageParser()
    parser.feed(HOMEPAGE.read_text(encoding="utf-8"))
    return parser


def test_homepage_has_unique_ids() -> None:
    parser = parse_homepage()
    duplicates = sorted({element_id for element_id in parser.ids if parser.ids.count(element_id) > 1})
    assert duplicates == []


def test_homepage_local_assets_and_routes_exist() -> None:
    parser = parse_homepage()
    missing = sorted({reference for reference in parser.local_references if reference and not (ROOT / reference).exists()})
    assert missing == []


def test_homepage_does_not_load_global_navigation_replacement() -> None:
    """The homepage owns its nav; nav.js replaces it and creates duplicate controls."""
    parser = parse_homepage()
    assert "nav.js" not in parser.scripts


def test_subscription_request_fails_closed() -> None:
    source = HOMEPAGE.read_text(encoding="utf-8")
    assert "if(!r.ok)throw new Error" in source
    assert "controller.abort()" in source
    assert ".finally(function()" in source
