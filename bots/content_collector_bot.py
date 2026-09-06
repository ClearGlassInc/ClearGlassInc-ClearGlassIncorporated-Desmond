# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Content collector bot — crawls every page and stores all site information.

Walks all local HTML pages in the repository, extracts the full information
each page provides (title, meta tags, Open Graph data, headings, visible body
text, links, images and JSON-LD structured data) and persists it into a single
structured knowledge store (JSON) plus a human-readable Markdown index.

The store is the source of truth for "everything the website says" and can be
fed to downstream bots (search, SEO, marketing, chat) without re-parsing HTML.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "output"
STORE_FILE = OUTPUT_DIR / "site_content_store.json"
INDEX_FILE = OUTPUT_DIR / "site_content_collection.md"

SITE_URL = "https://www.clearglassinc.com"

# Directories we never crawl for page content (build artifacts, deps, assets).
SKIP_DIRS = {
    ".git", ".github", "node_modules", "assets", "downloads",
    "__pycache__", ".pytest_cache", "tests", "bots", "scripts",
}

# Tags whose text content is never part of the visible page information.
NON_CONTENT_TAGS = {"script", "style", "noscript", "template", "head"}

META_FIELDS = ["description", "keywords", "author", "robots"]
OG_FIELDS = ["og:title", "og:description", "og:image", "og:url", "og:type"]
TWITTER_FIELDS = ["twitter:title", "twitter:description", "twitter:card"]


@dataclass
class Link:
    href: str
    text: str


@dataclass
class Image:
    src: str
    alt: str


@dataclass
class PageRecord:
    """Everything collected from a single page."""

    path: str
    url: str
    content_hash: str
    title: str | None
    lang: str | None
    meta: dict[str, str]
    open_graph: dict[str, str]
    twitter: dict[str, str]
    canonical: str | None
    headings: list[dict[str, str]]
    links: list[dict[str, str]]
    images: list[dict[str, str]]
    json_ld: list[Any]
    text: str
    word_count: int
    collected_utc: str


@dataclass
class CollectionReport:
    run_utc: str
    site_url: str
    pages_collected: int
    total_words: int
    total_links: int
    total_images: int
    pages: list[dict[str, Any]] = field(default_factory=list)


class _PageExtractor(HTMLParser):
    """Streaming HTML parser that harvests structured content from a page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.lang: str | None = None
        self.meta: dict[str, str] = {}
        self.canonical: str | None = None
        self.headings: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.json_ld: list[Any] = []
        self._text_parts: list[str] = []

        self._tag_stack: list[str] = []
        self._capture_title = False
        self._current_heading: str | None = None
        self._heading_text: list[str] = []
        self._current_link: str | None = None
        self._link_text: list[str] = []
        self._capture_jsonld = False
        self._jsonld_buffer: list[str] = []

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _attr(attrs: list[tuple[str, str | None]], name: str) -> str | None:
        for key, value in attrs:
            if key == name:
                return value
        return None

    def _in_non_content(self) -> bool:
        return any(t in NON_CONTENT_TAGS for t in self._tag_stack)

    # -- parser callbacks ------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag_stack.append(tag)

        if tag == "html" and self.lang is None:
            self.lang = self._attr(attrs, "lang")

        elif tag == "title":
            self._capture_title = True

        elif tag == "meta":
            name = (self._attr(attrs, "name") or self._attr(attrs, "property") or "").lower()
            content = self._attr(attrs, "content")
            if name and content:
                self.meta.setdefault(name, content.strip())

        elif tag == "link":
            rel = (self._attr(attrs, "rel") or "").lower()
            if rel == "canonical":
                self.canonical = self._attr(attrs, "href")

        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._current_heading = tag
            self._heading_text = []

        elif tag == "a":
            href = self._attr(attrs, "href")
            if href:
                self._current_link = href
                self._link_text = []

        elif tag == "img":
            src = self._attr(attrs, "src")
            if src:
                self.images.append({"src": src, "alt": (self._attr(attrs, "alt") or "").strip()})

        elif tag == "script":
            script_type = (self._attr(attrs, "type") or "").lower()
            if script_type == "application/ld+json":
                self._capture_jsonld = True
                self._jsonld_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._capture_title = False

        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._current_heading == tag:
            text = _normalize(" ".join(self._heading_text))
            if text:
                self.headings.append({"level": tag, "text": text})
            self._current_heading = None
            self._heading_text = []

        elif tag == "a" and self._current_link is not None:
            text = _normalize(" ".join(self._link_text))
            self.links.append({"href": self._current_link, "text": text})
            self._current_link = None
            self._link_text = []

        elif tag == "script" and self._capture_jsonld:
            raw = "".join(self._jsonld_buffer).strip()
            self._capture_jsonld = False
            self._jsonld_buffer = []
            if raw:
                try:
                    self.json_ld.append(json.loads(raw))
                except (json.JSONDecodeError, ValueError):
                    pass  # Malformed structured data is skipped, not fatal.

        # Pop the most recent matching tag from the stack.
        for i in range(len(self._tag_stack) - 1, -1, -1):
            if self._tag_stack[i] == tag:
                del self._tag_stack[i]
                break

    def handle_data(self, data: str) -> None:
        if self._capture_jsonld:
            self._jsonld_buffer.append(data)
            return
        if self._capture_title:
            self.title = (self.title or "") + data
            return
        if self._current_heading is not None:
            self._heading_text.append(data)
        if self._current_link is not None:
            self._link_text.append(data)
        if not self._in_non_content():
            stripped = data.strip()
            if stripped:
                self._text_parts.append(stripped)

    # -- result ----------------------------------------------------------
    def text(self) -> str:
        return _normalize(" ".join(self._text_parts))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _relative_url(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return f"{SITE_URL}/"
    return f"{SITE_URL}/{rel}"


def _split_meta(meta: dict[str, str]) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Separate raw meta tags into standard / Open Graph / Twitter buckets."""
    standard = {k: v for k, v in meta.items() if k in META_FIELDS}
    open_graph = {k: v for k, v in meta.items() if k in OG_FIELDS}
    twitter = {k: v for k, v in meta.items() if k in TWITTER_FIELDS}
    return standard, open_graph, twitter


def collect_page(path: Path) -> PageRecord:
    html = path.read_text(encoding="utf-8", errors="replace")
    parser = _PageExtractor()
    parser.feed(html)

    standard, open_graph, twitter = _split_meta(parser.meta)
    text = parser.text()
    content_hash = hashlib.sha256(html.encode("utf-8", errors="replace")).hexdigest()[:16]

    return PageRecord(
        path=path.relative_to(ROOT).as_posix(),
        url=_relative_url(path),
        content_hash=content_hash,
        title=_normalize(parser.title) if parser.title else None,
        lang=parser.lang,
        meta=standard,
        open_graph=open_graph,
        twitter=twitter,
        canonical=parser.canonical,
        headings=parser.headings,
        links=parser.links,
        images=parser.images,
        json_ld=parser.json_ld,
        text=text,
        word_count=len(text.split()),
        collected_utc=datetime.now(timezone.utc).isoformat(),
    )


def discover_pages() -> list[Path]:
    pages: list[Path] = []
    for html_file in sorted(ROOT.rglob("*.html")):
        if any(part in SKIP_DIRS for part in html_file.relative_to(ROOT).parts[:-1]):
            continue
        pages.append(html_file)
    return pages


def run() -> CollectionReport:
    pages = discover_pages()
    records = [collect_page(p) for p in pages]

    report = CollectionReport(
        run_utc=datetime.now(timezone.utc).isoformat(),
        site_url=SITE_URL,
        pages_collected=len(records),
        total_words=sum(r.word_count for r in records),
        total_links=sum(len(r.links) for r in records),
        total_images=sum(len(r.images) for r in records),
        pages=[asdict(r) for r in records],
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STORE_FILE.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False))

    md: list[str] = [
        "# Site Content Collection",
        "",
        f"**Run:** {report.run_utc}",
        f"**Site:** {report.site_url}",
        f"**Pages collected:** {report.pages_collected}",
        f"**Total words:** {report.total_words:,}",
        f"**Total links:** {report.total_links:,}",
        f"**Total images:** {report.total_images:,}",
        "",
        "## Pages",
        "",
    ]
    for r in records:
        title = r.title or "(untitled)"
        desc = r.meta.get("description", "")
        md.append(f"### {title}")
        md.append("")
        md.append(f"- **Path:** `{r.path}`")
        md.append(f"- **URL:** {r.url}")
        md.append(f"- **Words:** {r.word_count:,} · **Links:** {len(r.links)} · "
                  f"**Images:** {len(r.images)} · **Headings:** {len(r.headings)}")
        if desc:
            md.append(f"- **Description:** {desc}")
        md.append("")

    INDEX_FILE.write_text("\n".join(md))
    return report


def main() -> None:
    report = run()
    print(
        f"Content Collector: stored {report.pages_collected} pages, "
        f"{report.total_words:,} words → {STORE_FILE.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
