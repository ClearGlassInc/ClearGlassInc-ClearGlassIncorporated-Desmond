"""Regression tests for the generated ClearGlass Insights hub.

Each test pins a defect the hub actually shipped with, so a regression names
the symptom rather than a diff. See tools/insights_index.py.
"""

from __future__ import annotations

import importlib.util
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BLOG = ROOT / "blog"

SPEC = importlib.util.spec_from_file_location("insights_index", ROOT / "tools/insights_index.py")
assert SPEC and SPEC.loader
insights_index = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(insights_index)


@pytest.fixture(scope="module")
def index() -> dict:
    return json.loads((BLOG / "posts.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def hub() -> str:
    return (BLOG / "index.html").read_text(encoding="utf-8")


def brief_pages() -> list[Path]:
    return sorted(p for p in BLOG.glob("*.html") if p.name != "index.html")


def card_slugs(markup: str) -> list[str]:
    return re.findall(r'<a class="article-card[^"]*"[^>]*data-slug="([^"]+)"', markup)


def jsonld_graphs(markup: str) -> list[dict]:
    return [
        json.loads(block)
        for block in re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', markup, re.S
        )
    ]


# --------------------------------------------------------------------------
# the generator is the source of truth
# --------------------------------------------------------------------------
def test_generated_assets_are_current() -> None:
    """`--check` must pass on a clean tree, or the hub has drifted again."""
    assert insights_index.main(["--check"]) == 0


def test_generator_is_deterministic() -> None:
    """Two builds of the index must agree — otherwise --check is meaningless."""
    assert insights_index.build_index() == insights_index.build_index()


# --------------------------------------------------------------------------
# content discovery
# --------------------------------------------------------------------------
def test_every_brief_is_indexed(index: dict) -> None:
    indexed = {post["slug"] for post in index["posts"]}
    on_disk = {path.stem for path in brief_pages()}
    assert on_disk - indexed == set(), "briefs missing from posts.json"


def test_every_brief_is_reachable_from_the_hub(hub: str, index: dict) -> None:
    """20 of 43 briefs once had no card at all: in sitemap.xml, but with zero
    internal links, so no reader or crawler could reach them from /blog/."""
    linked = set(card_slugs(hub))
    missing = {post["slug"] for post in index["posts"]} - linked
    assert missing == set(), f"briefs with no hub card: {sorted(missing)}"


def test_hub_has_no_duplicate_cards(hub: str) -> None:
    """The archive used to repeat 12 spotlight cards, so those briefs matched
    every search twice."""
    slugs = card_slugs(hub)
    duplicates = {slug for slug in slugs if slugs.count(slug) > 1}
    assert duplicates == set(), f"duplicated cards: {sorted(duplicates)}"


def test_every_hub_card_link_resolves(hub: str) -> None:
    hrefs = re.findall(r'<a class="article-card[^"]*" href="([^"]+)"', hub)
    assert hrefs
    assert [h for h in hrefs if not (BLOG / h).is_file()] == []


def test_archive_and_spotlight_partition_the_corpus(index: dict) -> None:
    archive = {post["slug"] for post in insights_index.archive_posts(index)}
    featured = {post["slug"] for post in index["posts"] if post.get("featured")}
    assert archive & featured == set()
    assert archive | featured == {post["slug"] for post in index["posts"]}


def test_pagination_covers_every_archive_card(hub: str, index: dict) -> None:
    """Page links were hardcoded to 3 while the archive needed more, so the
    tail of the archive had no numbered page."""
    pages = [int(n) for n in re.findall(r'data-page="(\d+)"', hub)]
    needed = -(-len(insights_index.archive_posts(index)) // insights_index.ARCHIVE_PAGE_SIZE)
    assert pages == list(range(1, needed + 1))


def test_every_topic_with_briefs_has_a_chip(hub: str, index: dict) -> None:
    """Cards carried 13 topics while the hub offered 8 chips, so ?topic=frontier
    and five others were unreachable from the UI."""
    used = {topic for post in index["posts"] for topic in post.get("topics", [])}
    chips = set(re.findall(r'class="chip[^"]*" href="\?topic=([^"]+)"', hub))
    assert used - chips == set(), f"topics with no chip: {sorted(used - chips)}"


# --------------------------------------------------------------------------
# structured data
# --------------------------------------------------------------------------
@pytest.mark.parametrize("path", brief_pages() + [BLOG / "index.html"], ids=lambda p: p.name)
def test_jsonld_parses_and_lists_are_ordered(path: Path) -> None:
    """The hub shipped a BreadcrumbList with two position-1 entries and an
    ItemList with three; a duplicate position invalidates the whole list."""
    for graph in jsonld_graphs(path.read_text(encoding="utf-8")):
        for node in _walk(graph):
            elements = node.get("itemListElement")
            if not isinstance(elements, list) or not elements:
                continue
            positions = [item.get("position") for item in elements if isinstance(item, dict)]
            assert positions == list(range(1, len(positions) + 1)), (
                f"{path.name}: {node.get('@type')} positions {positions[:6]}"
            )
            if node.get("@type") == "BreadcrumbList":
                assert all("name" in item for item in elements), f"{path.name}: unnamed crumb"


def _walk(node: object):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def test_hub_blog_graph_lists_every_article(hub: str, index: dict) -> None:
    articles = {p["canonicalUrl"] + "#article" for p in index["posts"] if p["kind"] == "brief"}
    listed: set[str] = set()
    for graph in jsonld_graphs(hub):
        for node in _walk(graph):
            if node.get("@type") == "Blog":
                listed = {entry["@id"] for entry in node.get("blogPost", [])}
    assert listed == articles


# --------------------------------------------------------------------------
# metadata every brief needs for a link preview
# --------------------------------------------------------------------------
REQUIRED_META = (
    ('property="og:title"', "Open Graph title"),
    ('property="og:description"', "Open Graph description"),
    ('property="og:url"', "Open Graph URL"),
    ('property="og:image"', "Open Graph image"),
    ('name="twitter:card"', "Twitter card type"),
    ('name="twitter:title"', "Twitter title"),
    ('rel="canonical"', "canonical URL"),
)


@pytest.mark.parametrize("path", brief_pages(), ids=lambda p: p.name)
def test_brief_carries_preview_metadata(path: Path) -> None:
    markup = path.read_text(encoding="utf-8")
    if path.stem in insights_index.NON_ARTICLE_SLUGS:
        pytest.skip("tool page, not an article")
    missing = [label for needle, label in REQUIRED_META if needle not in markup]
    assert missing == [], f"{path.name} is missing: {', '.join(missing)}"


@pytest.mark.parametrize("path", brief_pages(), ids=lambda p: p.name)
def test_brief_has_a_related_rail(path: Path) -> None:
    """Only 8 of 42 briefs had the #ixRelated container, so the related-article
    feature was dead on the rest — and with it their outbound internal links."""
    if path.stem in insights_index.NON_ARTICLE_SLUGS:
        pytest.skip("tool page, not an article")
    markup = path.read_text(encoding="utf-8")
    assert insights_index.RELATED_START in markup, f"{path.name} has no related rail"
    block = markup.split(insights_index.RELATED_START)[1].split(insights_index.RELATED_END)[0]
    hrefs = re.findall(r'<a class="ix-related-card" href="([^"]+)"', block)
    assert hrefs, f"{path.name} related rail is empty"
    assert [h for h in hrefs if not (BLOG / h).is_file()] == []
    assert path.name not in hrefs, f"{path.name} links to itself"


@pytest.mark.parametrize("path", brief_pages(), ids=lambda p: p.name)
def test_brief_loads_the_insights_layer(path: Path) -> None:
    if path.stem in insights_index.NON_ARTICLE_SLUGS:
        pytest.skip("tool page, not an article")
    markup = path.read_text(encoding="utf-8")
    assert "insights.css" in markup, f"{path.name} does not load insights.css"
    assert "insights.js" in markup, f"{path.name} does not load insights.js"


# --------------------------------------------------------------------------
# the feed
# --------------------------------------------------------------------------
def test_feed_is_well_formed_xml() -> None:
    """blog/feed.xml carried a bare `&` in <title>, so it was not XML at all
    and every reader rejected the whole document."""
    ET.parse(BLOG / "feed.xml")


def test_feed_lists_every_dated_article(index: dict) -> None:
    tree = ET.parse(BLOG / "feed.xml")
    links = {item.findtext("link") for item in tree.iter("item")}
    expected = {
        post["canonicalUrl"]
        for post in index["posts"]
        if post["kind"] == "brief" and post.get("publishedAt")
    }
    assert links == expected


def test_feed_build_date_matches_the_newest_brief(index: dict) -> None:
    tree = ET.parse(BLOG / "feed.xml")
    newest = max(
        post["publishedAt"]
        for post in index["posts"]
        if post["kind"] == "brief" and post.get("publishedAt")
    )
    assert tree.findtext(".//lastBuildDate") == insights_index.rfc822(newest)


# --------------------------------------------------------------------------
# no fabricated facts in the index
# --------------------------------------------------------------------------
def test_index_claims_match_the_pages(index: dict) -> None:
    """Every date and author in the index must appear in the brief it
    describes. The index derives facts; it never supplies them."""
    for post in index["posts"]:
        markup = (BLOG / f"{post['slug']}.html").read_text(encoding="utf-8")
        if post.get("publishedAt"):
            assert post["publishedAt"] in markup, f"{post['slug']}: unsourced publishedAt"
        if post.get("author"):
            assert post["author"] in markup, f"{post['slug']}: unsourced author"
        assert post["canonicalUrl"] in markup, f"{post['slug']}: canonical mismatch"


def test_reading_time_is_derived_not_guessed(index: dict) -> None:
    for post in index["posts"]:
        parser = insights_index.BriefParser()
        parser.feed(
            insights_index.BOILERPLATE_RE.sub(
                " ", (BLOG / f"{post['slug']}.html").read_text(encoding="utf-8")
            )
        )
        expected = max(1, round(parser.words / insights_index.WORDS_PER_MINUTE))
        assert post["readMinutes"] == expected, post["slug"]


# --------------------------------------------------------------------------
# the client layer
# --------------------------------------------------------------------------
def test_escaper_encodes_entities() -> None:
    """esc() in blog/insights.js mapped every character to itself ('&' -> '&'),
    making it a no-op, and its output goes into innerHTML."""
    source = (BLOG / "insights.js").read_text(encoding="utf-8")
    entities = re.search(r"var ENTITIES = \{([^}]+)\}", source)
    assert entities, "insights.js no longer defines an ENTITIES map"
    for char, entity in (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ('"', "&quot;")):
        assert f"'{char}': '{entity}'" in entities.group(1), f"{char!r} is not escaped"


def test_untrusted_urls_pass_through_a_scheme_allowlist() -> None:
    """Escaping an href stops attribute breakout but not `javascript:`."""
    source = (BLOG / "insights.js").read_text(encoding="utf-8")
    assert "function safeHref(" in source
    for sink in ('esc(safeHref(it.href))', 'esc(safeHref(p.url))'):
        assert sink in source, f"missing scheme check at {sink}"


def test_hidden_cards_actually_hide() -> None:
    """`.article-card{display:flex}` is an author rule, so it outranks the
    user-agent `[hidden]{display:none}` and pagination rendered nothing: all
    archive cards painted while the status line claimed six."""
    css = (BLOG / "insights.css").read_text(encoding="utf-8")
    assert ".article-card[hidden]{display:none!important}" in css


def test_search_highlighting_never_uses_innerhtml() -> None:
    source = (BLOG / "insights.js").read_text(encoding="utf-8")
    body = source.split("function highlight(", 1)[1].split("\n  function debounce", 1)[0]
    assert "innerHTML" not in body, "highlight() must build marks from text nodes"
    assert "createTextNode" in body and "createElement('mark')" in body


def test_reduced_motion_is_honoured() -> None:
    css = (BLOG / "insights.css").read_text(encoding="utf-8")
    assert "@media(prefers-reduced-motion:reduce)" in css
