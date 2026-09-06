#!/usr/bin/env python3
"""Generate deterministic search-discovery assets from committed HTML.

Dates come from Git history, not the wall clock. Indexability comes from each
document's robots meta directive. This keeps sitemap and feed claims aligned
with content that is actually deployed by GitHub Pages.
"""
from __future__ import annotations

import json
import subprocess
import datetime as dt
import xml.etree.ElementTree as ET
from pathlib import Path

import seo_audit

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://www.clearglassinc.com"
ATOM = "http://www.w3.org/2005/Atom"

# seo_audit.SKIP_DIRS excludes whole trees (apps/, docs/, tools/, …) from on-page
# scoring because they are mostly app shells and internal notes. A few documents
# inside those trees are published, registered in the authority graph, and must
# stay in the sitemap — list them here so discovery does not silently drop them.
EXTRA_INDEXABLE_PAGES = (
    "apps/command-center/index.html",
    "docs/guardian_command_nexus_spec.html",
)


def git_date(path: Path) -> str:
    relative = str(path.relative_to(ROOT))
    dirty = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", relative], cwd=ROOT, check=False
    )
    if dirty.returncode == 1:
        # The generated assets ship in the same commit as the content edit.
        return dt.datetime.now(dt.timezone.utc).date().isoformat()
    if dirty.returncode != 0:
        raise RuntimeError(f"Unable to inspect Git state for {path}")
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", relative],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    if not value:
        raise ValueError(f"No committed modification date for {path}")
    return value


def page_url(relative: str) -> str:
    return f"{SITE}/" if relative == "index.html" else f"{SITE}/{relative}"


def parse_page(path: Path) -> seo_audit.PageParser:
    parser = seo_audit.PageParser()
    parser.feed(seo_audit.strip_noise(path.read_text(encoding="utf-8", errors="ignore")))
    return parser


def discovered_paths() -> list[Path]:
    paths = list(seo_audit.discover_pages())
    known = {path.resolve() for path in paths}
    for relative in EXTRA_INDEXABLE_PAGES:
        extra = ROOT / relative
        if extra.is_file() and extra.resolve() not in known:
            paths.append(extra)
    return sorted(paths)


def indexable_pages() -> list[tuple[Path, seo_audit.PageParser]]:
    pages = []
    for path in discovered_paths():
        rel = path.relative_to(ROOT).as_posix()
        parser = parse_page(path)
        if (rel in seo_audit.UTILITY_PAGES or seo_audit.VERIFICATION_RE.match(path.name)
                or "noindex" in parser.robots):
            continue
        pages.append((path, parser))
    return pages


def write_sitemap(pages: list[tuple[Path, seo_audit.PageParser]]) -> None:
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    root = ET.Element("{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")
    for path, _ in sorted(pages, key=lambda item: page_url(item[0].relative_to(ROOT).as_posix())):
        url = ET.SubElement(root, "{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        ET.SubElement(url, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = page_url(
            path.relative_to(ROOT).as_posix()
        )
        ET.SubElement(url, "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod").text = git_date(path)
    ET.indent(root)
    (ROOT / "sitemap.xml").write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))


def article_metadata(parser: seo_audit.PageParser) -> dict | None:
    for block in parser.jsonld:
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue
        nodes: list[dict] = []
        seo_audit.walk_nodes(value, nodes)
        for node in nodes:
            kinds = node.get("@type", [])
            kinds = [kinds] if isinstance(kinds, str) else kinds
            if any(kind in {"Article", "BlogPosting", "TechArticle"} for kind in kinds):
                return node
    return None


def write_feed(pages: list[tuple[Path, seo_audit.PageParser]]) -> None:
    entries = []
    for path, parser in pages:
        article = article_metadata(parser)
        if article and article.get("datePublished") and parser.title:
            entries.append((str(article["datePublished"])[:10], path, parser, article))
    entries.sort(key=lambda item: (item[0], item[1].as_posix()), reverse=True)
    entries = entries[:20]
    ET.register_namespace("", ATOM)
    feed = ET.Element(f"{{{ATOM}}}feed")
    ET.SubElement(feed, f"{{{ATOM}}}id").text = f"{SITE}/feed.xml"
    ET.SubElement(feed, f"{{{ATOM}}}title").text = "ClearGlass Inc. Insights"
    ET.SubElement(feed, f"{{{ATOM}}}link", {"href": f"{SITE}/feed.xml", "rel": "self"})
    ET.SubElement(feed, f"{{{ATOM}}}link", {"href": f"{SITE}/blog/"})
    latest = entries[0][0] if entries else git_date(ROOT / "index.html")
    ET.SubElement(feed, f"{{{ATOM}}}updated").text = f"{latest}T00:00:00Z"
    for published, path, parser, article in entries:
        url = page_url(path.relative_to(ROOT).as_posix())
        entry = ET.SubElement(feed, f"{{{ATOM}}}entry")
        ET.SubElement(entry, f"{{{ATOM}}}id").text = article.get("@id", url)
        ET.SubElement(entry, f"{{{ATOM}}}title").text = str(article.get("headline", parser.title))
        ET.SubElement(entry, f"{{{ATOM}}}link", {"href": url})
        ET.SubElement(entry, f"{{{ATOM}}}published").text = f"{published}T00:00:00Z"
        modified = str(article.get("dateModified", published))[:10]
        ET.SubElement(entry, f"{{{ATOM}}}updated").text = f"{modified}T00:00:00Z"
        ET.SubElement(entry, f"{{{ATOM}}}summary").text = str(
            article.get("description", parser.description or "")
        )
    ET.indent(feed)
    (ROOT / "feed.xml").write_bytes(ET.tostring(feed, encoding="utf-8", xml_declaration=True))


def write_intent_map(pages: list[tuple[Path, seo_audit.PageParser]]) -> None:
    records = []
    for path, parser in pages:
        rel = path.relative_to(ROOT).as_posix()
        h1 = next((text for level, text in parser.headings if level == 1), "")
        records.append({
            "route": "/" if rel == "index.html" else f"/{rel}",
            "intent": h1 or parser.title or rel,
            "title": parser.title,
            "description": parser.description,
            "canonical": parser.canonical,
            "h1": h1,
        })
    output = {"site": SITE, "generated_from": "committed HTML", "pages": records}
    target = ROOT / "data" / "seo" / "page-intents.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    pages = indexable_pages()
    write_sitemap(pages)
    write_feed(pages)
    write_intent_map(pages)
    print(f"Generated sitemap, Atom feed, and intent map for {len(pages)} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
