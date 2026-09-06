#!/usr/bin/env python3
"""ClearGlass self-auditing authority-network controller.

This module extends the established ``tools.internal_links`` graph without
replacing it. The legacy generator remains responsible for the existing static
related-content blocks. This controller adds four production controls:

1. discover every indexable HTML page from every ``sitemap*.xml`` file;
2. register new pages as supplemental members without reshuffling stable links;
3. analyse native + generated links for orphans, crawl depth and conversion paths;
4. emit deterministic recommendations when the network needs to evolve.

The system is intentionally conservative. It never invents links or rewrites
article copy. New relationships are explicit, auditable and semantically scoped.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import posixpath
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

try:
    from tools import internal_links as legacy
except ModuleNotFoundError:  # allow `python3 tools/authority_network.py` from repo root
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools import internal_links as legacy

ROOT = legacy.ROOT
SITE_HOSTS = {"clearglassinc.com", "www.clearglassinc.com"}
MAX_CRAWL_DEPTH = 4

# New indexable pages are attached as supplemental depth. Core member order is
# deliberately frozen so publishing a new page cannot silently reshuffle every
# existing page's generated sibling links.
#
# A page listed here must NOT also live in the legacy graph (tools/internal_links.py):
# validate() rejects that as "duplicates legacy graph". Once a supplemental page is
# promoted to a full cluster member in internal_links.py it graduates out of this map.
# products.html, command-center.html and platform-command-center.html were promoted
# in that way, so they are registered only in the legacy graph now.
SUPPLEMENTAL_PAGES: dict[str, tuple[str, str, str]] = {}

# Explicit lateral relationships for new pages. These are not inferred at run
# time; they are reviewed architecture decisions with descriptive destinations.
SUPPLEMENTAL_BRIDGES: dict[str, list[str]] = {}

CONVERSION_TARGETS = {
    "offers/index.html",
    "store.html",
    "pricing.html",
    "operations/client-onboarding.html",
    "offers/autonomous-threat-modeling.html",
}

GENERIC_ANCHORS = {
    "click here",
    "learn more",
    "read more",
    "more",
    "here",
    "details",
    "go",
}

PAGES: dict[str, tuple[str, str]] = dict(legacy.PAGES)
for path, (title, description, _cluster) in SUPPLEMENTAL_PAGES.items():
    PAGES[path] = (title, description)


@dataclass(frozen=True)
class LinkRecord:
    source: str
    target: str
    anchor: str
    generated: bool


class PageLinkParser(HTMLParser):
    """Extract title, description and visible anchors with stdlib HTML parsing."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.description = ""
        self._in_title = False
        self._href: str | None = None
        self._anchor_parts: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "title":
            self._in_title = True
        elif tag.lower() == "meta":
            if values.get("name", "").lower() == "description":
                self.description = values.get("content", "").strip()
        elif tag.lower() == "a":
            self._href = values.get("href")
            self._anchor_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
        elif tag.lower() == "a" and self._href is not None:
            anchor = " ".join("".join(self._anchor_parts).split())
            self.links.append((self._href, anchor))
            self._href = None
            self._anchor_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._href is not None:
            self._anchor_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())


def sitemap_path(url: str) -> str | None:
    parsed = urlsplit(url.strip())
    if parsed.netloc and parsed.netloc.lower() not in SITE_HOSTS:
        return None
    path = unquote(parsed.path).lstrip("/")
    if not path or path.endswith("/"):
        path += "index.html"
    if not path.lower().endswith((".html", ".htm")):
        return None
    return posixpath.normpath(path)


def discover_sitemap_pages() -> tuple[set[str], dict[str, list[str]]]:
    pages: set[str] = set()
    provenance: dict[str, list[str]] = defaultdict(list)
    files = sorted(ROOT.glob("sitemap*.xml"))
    if not files:
        raise RuntimeError("no sitemap*.xml files found")
    for sitemap in files:
        root = ET.parse(sitemap).getroot()
        for loc in root.findall(".//{*}loc"):
            path = sitemap_path((loc.text or "").strip())
            if path:
                pages.add(path)
                provenance[path].append(sitemap.name)
    return pages, dict(provenance)


def cluster_of(page: str) -> str:
    if page in legacy.PAGES:
        return legacy.cluster_of(page)
    try:
        return SUPPLEMENTAL_PAGES[page][2]
    except KeyError as exc:
        raise KeyError(f"page not registered in authority network: {page}") from exc


def related_targets(page: str) -> tuple[list[str], list[tuple[str, str]], str]:
    """Return stable related targets, CTA pairs and pillar for any registered page."""
    if page in legacy.PAGES:
        return legacy.related_targets(page)

    cid = cluster_of(page)
    cluster = legacy.CLUSTERS[cid]
    pillar = cluster["pillar"]
    targets: list[str] = []
    seen = {page}

    if page == "authority-network.html":
        candidates = SUPPLEMENTAL_BRIDGES[page]
    else:
        candidates = [
            pillar,
            *SUPPLEMENTAL_BRIDGES.get(page, []),
            *cluster["members"][: legacy.SIBLING_WINDOW],
        ]

    for target in candidates:
        if target in PAGES and target not in seen:
            targets.append(target)
            seen.add(target)

    return targets, list(cluster["cta"]), pillar


def relative_href(source: str, target: str) -> str:
    start = posixpath.dirname(source) or "."
    return posixpath.relpath(target, start)


def descriptive_anchor(source: str, target: str) -> str:
    title, description = PAGES[target]
    href = html.escape(relative_href(source, target), quote=True)
    return f'<li><a href="{href}"><b>{html.escape(title)}</b> — {html.escape(description)}</a></li>'


def supplemental_block(page: str) -> str:
    targets, ctas, pillar = related_targets(page)
    cid = cluster_of(page)
    cluster_name = legacy.CLUSTERS[cid]["name"]
    home = html.escape(relative_href(page, "index.html"), quote=True)
    pillar_href = html.escape(relative_href(page, pillar), quote=True)
    items = "\n      ".join(descriptive_anchor(page, target) for target in targets)
    cta_html = " · ".join(
        f'<a href="{html.escape(relative_href(page, path), quote=True)}">{html.escape(label)}</a>'
        for path, label in ctas
    )
    return (
        f"{legacy.START}\n"
        f'<aside id="cg-related">\n'
        f"  <style>{legacy.CSS}</style>\n"
        f'  <nav class="cgr-box" aria-label="Related ClearGlass pages">\n'
        f'    <p class="cgr-crumb"><a href="{home}">ClearGlass Inc.</a>'
        f' › <a href="{pillar_href}">{html.escape(cluster_name)}</a></p>\n'
        f"    <h2>Continue through the authority network</h2>\n"
        f"    <ul>\n      {items}\n    </ul>\n"
        f'    <p class="cgr-cta">Next step: {cta_html}</p>\n'
        f"  </nav>\n"
        f"</aside>\n"
        f"{legacy.END}"
    )


def expected_block(page: str) -> str:
    return legacy.build_block(page) if page in legacy.PAGES else supplemental_block(page)


def parse_page(page: str) -> PageLinkParser:
    parser = PageLinkParser()
    parser.feed((ROOT / page).read_text(encoding="utf-8", errors="surrogateescape"))
    return parser


def normalize_internal_target(source: str, href: str) -> str | None:
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    parsed = urlsplit(href)
    if parsed.netloc and parsed.netloc.lower() not in SITE_HOSTS:
        return None
    raw_path = unquote(parsed.path)
    if raw_path.startswith("/"):
        target = raw_path.lstrip("/")
    else:
        target = posixpath.join(posixpath.dirname(source), raw_path)
    target = posixpath.normpath(target)
    if target in ("", "."):
        target = "index.html"
    if target.endswith("/"):
        target += "index.html"
    return target if target in PAGES else None


def native_link_records() -> list[LinkRecord]:
    records: list[LinkRecord] = []
    for page in PAGES:
        parser = parse_page(page)
        for href, anchor in parser.links:
            target = normalize_internal_target(page, href)
            if target and target != page:
                records.append(LinkRecord(page, target, anchor, False))
    return records


def generated_link_records() -> list[LinkRecord]:
    records: list[LinkRecord] = []
    for page in PAGES:
        targets, ctas, pillar = related_targets(page)
        all_targets = [*targets, *(path for path, _label in ctas), "index.html"]
        if pillar:
            all_targets.append(pillar)
        for target in dict.fromkeys(all_targets):
            if target in PAGES and target != page:
                label = PAGES[target][0]
                records.append(LinkRecord(page, target, label, True))
    return records


def graph_edges() -> dict[str, set[str]]:
    edges: dict[str, set[str]] = {page: set() for page in PAGES}
    for record in [*generated_link_records(), *native_link_records()]:
        edges[record.source].add(record.target)
    return edges


def crawl_depths(edges: dict[str, set[str]], start: str = "index.html") -> dict[str, int]:
    depths = {start: 0}
    queue: deque[str] = deque([start])
    while queue:
        source = queue.popleft()
        for target in sorted(edges[source]):
            if target not in depths:
                depths[target] = depths[source] + 1
                queue.append(target)
    return depths


def can_reach_conversion(page: str, edges: dict[str, set[str]]) -> bool:
    queue: deque[tuple[str, int]] = deque([(page, 0)])
    visited = {page}
    while queue:
        source, depth = queue.popleft()
        if source in CONVERSION_TARGETS:
            return True
        if depth >= MAX_CRAWL_DEPTH:
            continue
        for target in edges[source]:
            if target not in visited:
                visited.add(target)
                queue.append((target, depth + 1))
    return False


def graph_fingerprint() -> str:
    payload = {
        "pages": PAGES,
        "clusters": {
            cid: {
                "pillar": cluster["pillar"],
                "members": cluster["members"],
                "supplements": sorted(
                    page for page, (_title, _description, pcid) in SUPPLEMENTAL_PAGES.items()
                    if pcid == cid
                ),
                "cta": cluster["cta"],
            }
            for cid, cluster in legacy.CLUSTERS.items()
        },
        "bridges": SUPPLEMENTAL_BRIDGES,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def classify_candidate(path: str, title: str, description: str) -> tuple[str, int]:
    """Suggest a cluster for an unmapped sitemap page using transparent keywords."""
    text = f"{path} {title} {description}".casefold()
    keywords: dict[str, tuple[str, ...]] = {
        "security": ("cyber", "security", "threat", "defense", "risk", "zero trust"),
        "intelligence": ("osint", "intelligence", "investigation", "nexus", "signal"),
        "artemis": ("artemis", "air system", "zephyr"),
        "command": ("agent", "automation", "workflow", "orchestration", "command", "operator"),
        "legal": ("legal", "privacy", "tax", "liability", "compliance", "banking"),
        "healthcare": ("health", "phipa", "clinical"),
        "government": ("government", "procurement", "supplier", "public sector", "uas", "transit"),
        "services": ("offer", "service", "pricing", "audit", "sprint", "store"),
        "design": ("design", "interface", "glass", "button", "ui", "web"),
        "opal": ("opal", "asset library"),
        "blog": ("blog/", "article", "essay", "briefing", "playbook"),
        "company": ("investor", "company", "onboarding", "handoff", "corporate"),
    }
    scores = Counter(
        {
            cid: sum(2 if token in path.casefold() else 1 for token in tokens if token in text)
            for cid, tokens in keywords.items()
        }
    )
    cid, score = scores.most_common(1)[0] if scores else ("company", 0)
    return cid, score


def candidate_stub(page: str) -> str:
    parser = parse_page(page) if (ROOT / page).is_file() else PageLinkParser()
    title = parser.title or Path(page).stem.replace("-", " ").title()
    description = parser.description or "describe the page's strategic value"
    cid, score = classify_candidate(page, title, description)
    return (
        f'    "{page}": (\n'
        f'        {title!r},\n'
        f'        {description!r},\n'
        f'        {cid!r},  # deterministic keyword score: {score}\n'
        f"    ),"
    )


def validate() -> list[str]:
    errors = list(legacy.validate())
    sitemap_pages, provenance = discover_sitemap_pages()

    supplement_seen: set[str] = set()
    for page, (_title, _description, cid) in SUPPLEMENTAL_PAGES.items():
        if page in supplement_seen:
            errors.append(f"supplement registered more than once: {page}")
        supplement_seen.add(page)
        if cid not in legacy.CLUSTERS:
            errors.append(f"{page}: unknown cluster {cid}")
        if page in legacy.PAGES:
            errors.append(f"{page}: supplemental page duplicates legacy graph")
        if not (ROOT / page).is_file():
            errors.append(f"{page}: file not found")

    unmapped = sorted(sitemap_pages - set(PAGES))
    if unmapped:
        errors.append("indexable sitemap pages missing from authority graph: " + ", ".join(unmapped))
        for page in unmapped:
            if (ROOT / page).is_file():
                errors.append("registration suggestion:\n" + candidate_stub(page))

    unsitemapped = sorted(set(PAGES) - sitemap_pages)
    if unsitemapped:
        errors.append("authority pages missing from sitemap files: " + ", ".join(unsitemapped))

    for source, targets in SUPPLEMENTAL_BRIDGES.items():
        if source not in SUPPLEMENTAL_PAGES:
            errors.append(f"supplemental bridge source is not supplemental: {source}")
        for target in targets:
            if target not in PAGES:
                errors.append(f"{source}: unknown bridge target {target}")

    return errors


def block_errors() -> list[str]:
    errors: list[str] = []
    for page in legacy.PAGES:
        text = (ROOT / page).read_text(encoding="utf-8", errors="surrogateescape")
        match = legacy.BLOCK_RE.search(text)
        if not match:
            errors.append(f"{page}: generated authority block missing")
        elif match.group(0) != legacy.build_block(page):
            errors.append(f"{page}: generated authority block stale")
    return errors


def analysis_errors() -> tuple[list[str], dict[str, object]]:
    errors: list[str] = []
    edges = graph_edges()
    inbound = Counter(target for targets in edges.values() for target in targets)
    depths = crawl_depths(edges)

    orphans = sorted(page for page in PAGES if page != "index.html" and inbound[page] == 0)
    unreachable = sorted(set(PAGES) - set(depths))
    deep = sorted(page for page, depth in depths.items() if depth > MAX_CRAWL_DEPTH)
    no_conversion = sorted(page for page in PAGES if not can_reach_conversion(page, edges))

    if orphans:
        errors.append("orphan authority pages: " + ", ".join(orphans))
    if unreachable:
        errors.append("pages unreachable from home: " + ", ".join(unreachable))
    if deep:
        errors.append(
            f"pages deeper than {MAX_CRAWL_DEPTH} clicks: " + ", ".join(deep)
        )
    if no_conversion:
        errors.append("pages without a conversion path: " + ", ".join(no_conversion))

    records = native_link_records()
    weak_anchors = sorted(
        {
            f"{record.source} -> {record.target}: {record.anchor!r}"
            for record in records
            if record.anchor.strip().casefold() in GENERIC_ANCHORS
        }
    )

    metrics: dict[str, object] = {
        "fingerprint": graph_fingerprint(),
        "pages": len(PAGES),
        "legacy_pages": len(legacy.PAGES),
        "supplemental_pages": len(SUPPLEMENTAL_PAGES),
        "clusters": len(legacy.CLUSTERS),
        "generated_edges": len(generated_link_records()),
        "native_edges": len(records),
        "minimum_inbound": min((inbound[p] for p in PAGES if p != "index.html"), default=0),
        "maximum_crawl_depth": max(depths.values(), default=0),
        "weak_native_anchors": weak_anchors,
        "conversion_targets": sorted(CONVERSION_TARGETS),
    }
    return errors, metrics


def recommendations(metrics: dict[str, object]) -> list[str]:
    output: list[str] = []
    weak = metrics.get("weak_native_anchors", [])
    for item in list(weak)[:10]:
        output.append(f"Replace generic native anchor with destination-specific language: {item}")
    if not output:
        output.append("No structural repair required; continue adding only reviewed supplemental pages and bridges.")
    return output


def print_report(metrics: dict[str, object]) -> None:
    print("ClearGlass Authority Network")
    print("=" * 32)
    print(json.dumps({key: value for key, value in metrics.items() if key != "weak_native_anchors"}, indent=2))
    print("\nEvolution recommendations")
    for item in recommendations(metrics):
        print(f"- {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate graph, sitemaps, blocks and reachability")
    parser.add_argument("--report", action="store_true", help="print graph metrics and evolution recommendations")
    args = parser.parse_args()

    errors = validate()
    if args.check:
        errors.extend(block_errors())
        analysis_failures, metrics = analysis_errors()
        errors.extend(analysis_failures)
    else:
        _analysis_failures, metrics = analysis_errors()

    if errors:
        print("authority-network errors:")
        for error in errors:
            print(f"  - {error}")
        if args.report:
            print_report(metrics)
        return 1

    print(
        f"validated {len(PAGES)} pages across {len(legacy.CLUSTERS)} clusters; "
        f"fingerprint {metrics['fingerprint']}"
    )
    if args.report:
        print_report(metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
