#!/usr/bin/env python3
"""ClearGlass Insights content index + hub generator.

The blog hub used to be hand-maintained, and the hand drifted from the content:
20 of 43 published briefs had no card on /blog/ at all, `posts.json` described
12 of them, `blog/feed.xml` was not well-formed XML, and the hub's JSON-LD
carried three `position: 1` entries. Everything that can be derived from the
briefs themselves is derived here instead, so the hub cannot drift again.

What this generates
-------------------
  blog/posts.json   the normalized content index (the single source of truth)
  blog/index.html   topic chips, the archive grid, pagination, and the
                    Blog/ItemList/BreadcrumbList JSON-LD — each between
                    `cg-insights-*` marker comments
  blog/feed.xml     a well-formed RSS 2.0 feed of every published brief

Where the facts come from
-------------------------
Title, description, author, publication date, modification date, canonical URL
and reading time are read out of each brief's own markup — never invented. A
brief missing a field simply has no such key in the index. The only authored
layer is `CURATED`: the editorial taxonomy (category label, topic chips, pull
quote, call to action, desk ranking). That is the same shape as the site graph
in `tools/internal_links.py`: explicit, reviewable, and diffable.

Usage
-----
    python3 tools/insights_index.py           # regenerate everything in place
    python3 tools/insights_index.py --check   # exit 1 if any output is stale

stdlib only, and offline: no network, no clock, no Git reads. Running it twice
produces the same bytes, which is what makes `--check` a usable CI gate.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOG = ROOT / "blog"
SITE = "https://www.clearglassinc.com"

POSTS_JSON = BLOG / "posts.json"
HUB = BLOG / "index.html"
FEED = BLOG / "feed.xml"

INDEX_VERSION = 3
WORDS_PER_MINUTE = 200
ARCHIVE_PAGE_SIZE = 6

# Marker pairs delimiting generated regions in blog/index.html, mirroring the
# `cg-related` convention already used by tools/internal_links.py.
MARKERS = {
    "chips": ("<!-- cg-insights-chips:start -->", "<!-- cg-insights-chips:end -->"),
    "archive": ("<!-- cg-insights-archive:start -->", "<!-- cg-insights-archive:end -->"),
    "pagination": ("<!-- cg-insights-pagination:start -->", "<!-- cg-insights-pagination:end -->"),
    "jsonld": ("<!-- cg-insights-jsonld:start -->", "<!-- cg-insights-jsonld:end -->"),
}

# Pages under blog/ that are not editorial briefs. They stay linked from the hub
# but never enter the RSS feed or the Blog JSON-LD, which describe articles.
NON_ARTICLE_SLUGS = {"resume-builder"}

# Topic vocabulary. The hub previously shipped chips for 8 of these while cards
# carried 13, so `?topic=frontier` and friends were unreachable from the UI.
TOPICS = {
    "governed-ai": "Governed AI",
    "agents": "Autonomous agents",
    "cyber": "Cyber architecture",
    "osint": "OSINT workflows",
    "automation": "AI automation",
    "systems": "High-trust systems",
    "growth": "Revenue growth systems",
    "frontier": "Frontier intelligence",
    "cross-border": "Canada–US controls",
    "strategic-resilience": "Strategic resilience",
    "culture": "Technology culture",
    "fincrime": "Financial crime detection",
    "information-integrity": "Information integrity",
}

# Editorial overlay: category label, topic chips, pull quote and CTA per brief.
# Entries for the 23 briefs that already had hub cards preserve their authored
# copy verbatim; the rest were written from what each brief actually argues.
CURATED: dict[str, dict] = {
    "clearglass-workplace-surveillance-intelligence-defense-system": dict(
        category="Worker Rights",
        quote="Transparency over concealment.",
        cta="Read the WSIDS brief →",
        topics="osint systems cyber governed-ai",
        series="ClearGlass Public-Interest Intelligence",
        featured=True,
        deskRank=11,
    ),
    "canada-digital-control-architecture-charter": dict(
        category="Law &amp; Technology",
        quote="Safety. Surveillance. The Charter.",
        cta="Open the systems brief →",
        topics="systems cyber osint",
        series="ClearGlass Legal Desk",
        featured=True,
        deskRank=12,
    ),
    "ai-generated-phishing-54-percent-click-rate": dict(
        category="Cyber Defense",
        quote="&ldquo;Assume the click. Design so the click is survivable.&rdquo;",
        cta="Read the brief &rarr;",
        topics="cyber governed-ai systems",
        featured=True,
    ),
    "ontario-accountability-sealed-evidence": dict(
        category="OSINT &amp; Accountability",
        quote="What the record says. What remains sealed.",
        cta="Open the appeal guide →",
        topics="osint systems",
        featured=True,
    ),
    "coffee-and-technology-digital-revolution": dict(
        category="Technology Culture",
        quote="From the coffeehouse to the cloud.",
        cta="Brew the story →",
        topics="culture systems automation",
        featured=True,
    ),
    "greenbelt-92-percent-access-beats-process": dict(
        category="OSINT &amp; Accountability",
        quote="92%. Access beat process.",
        cta="Inspect the evidence →",
        topics="osint systems",
        featured=True,
    ),
    "clearglassinc-artemis-palantir-self-evolving-ai-intelligence-platform": dict(
        category="AI Architecture",
        quote="Human-approved self-evolution",
        cta="Read the blueprint →",
        topics="governed-ai agents automation systems cyber",
        featured=True,
    ),
    "clearglassinc-artemis-full-stack-ai-intelligence-platform-blueprint": dict(
        category="AI Architecture",
        quote="Architecture, end to end",
        cta="Read the blueprint →",
        topics="governed-ai agents systems cyber",
        featured=True,
    ),
    "post-quantum-security-advisor-clearglass-artemis": dict(
        category="Frontier Security",
        quote="&ldquo;Security readiness is the quantum wedge.&rdquo;",
        cta="Read the thesis →",
        topics="frontier cyber systems governed-ai",
        featured=True,
    ),
    "clearglass-secure-deployment-agent": dict(
        category="Secure Deployment",
        quote="&ldquo;Access is not authorization.&rdquo;",
        cta="Read the model →",
        topics="cyber agents automation systems governed-ai",
        featured=True,
    ),
    "clearglassinc-0-to-1m-corporate-execution-plan": dict(
        category="Revenue",
        quote="&ldquo;Cash collected, not vanity.&rdquo;",
        cta="Read the plan →",
        topics="growth systems governed-ai",
        featured=True,
    ),
    "frontier-intelligence-briefing-quantum-gravity-asi-biosecurity": dict(
        category="Frontier Intelligence",
        quote="&ldquo;Watch the intersections, not the headlines.&rdquo;",
        cta="Open the briefing →",
        topics="frontier governed-ai systems",
        featured=True,
    ),
    "ethical-sales-system-100k-revenue-prompt": dict(
        category="Revenue",
        quote="Ethical revenue architecture",
        cta="Read the prompt system →",
        topics="automation systems governed-ai growth",
        featured=True,
    ),
    "clearglass-agentops-microsoft-foundry-future-stack": dict(
        category="AgentOps",
        quote="&ldquo;AgentOps is the control plane for intelligent work.&rdquo;",
        cta="Read the future stack →",
        topics="governed-ai agents cyber automation systems",
        featured=True,
    ),
    "ai-agent-governance-governed-autonomy": dict(
        category="AI &amp; Autonomy",
        quote="&ldquo;The bottleneck is not intelligence. It is accountability.&rdquo;",
        cta="Read the playbook →",
        topics="governed-ai agents cyber",
        featured=True,
    ),
    "clearglass-platform-audit-2026": dict(
        category="Platform Engineering",
        quote="&ldquo;Audit the verbs, not the vibes.&rdquo;",
        cta="Read the doctrine →",
        topics="systems governed-ai agents automation",
    ),
    "clearglassinc-artemis-resume-builder-self-evolving-intelligence-platform": dict(
        category="AI Architecture",
        quote="Artemis resume builder",
        cta="Read the blueprint →",
        topics="governed-ai agents automation systems",
    ),
    "ai-agents-insider-threat": dict(
        category="AI &amp; Security",
        quote="&ldquo;The newest insider isn&rsquo;t human.&rdquo;",
        cta="Read the framework →",
        topics="agents cyber governed-ai",
    ),
    "zero-trust-is-outdated": dict(
        category="Cyber Architecture",
        quote="&ldquo;Authentication is not alignment.&rdquo;",
        cta="Read the doctrine →",
        topics="cyber systems agents",
    ),
    "clearglassinc-artemis-self-evolving-ai-intelligence-platform": dict(
        category="AI Architecture",
        quote="Artemis systems blueprint",
        cta="Read the architecture →",
        topics="governed-ai automation systems",
    ),
    "osint-workflow-that-survives-contact-with-reality": dict(
        category="OSINT",
        quote="OSINT with provenance",
        cta="Read brief 01 →",
        topics="osint systems",
    ),
    "cybersecurity-architecture-for-agentic-software": dict(
        category="Cyber",
        quote="Zero-trust agents",
        cta="Read brief 01 →",
        topics="cyber agents systems",
    ),
    "resume-builder": dict(
        category="PDF Export",
        quote="Print-safe resume export",
        cta="Open the builder →",
        topics="systems automation",
    ),
    # --- briefs that were published but never linked from the hub ---
    "2026-09-15-strategic-chokepoint-sitrep": dict(
        category="Strategic Intelligence",
        quote="Verification before narrative.",
        cta="Read the sitrep →",
        topics="osint strategic-resilience systems",
        series="ClearGlass Strategic Intelligence",
    ),
    "ai-safety-black-box-activation-analysis-gavel": dict(
        category="AI Safety",
        quote="Inspect the activations, not the output.",
        cta="Read the long read →",
        topics="governed-ai frontier systems",
    ),
    "almach-scalp-engine": dict(
        category="Market Systems",
        quote="Governed, read-only, observable.",
        cta="Open the concept →",
        topics="automation systems fincrime",
    ),
    "artemis-governed-ai-gtm-visual-growth-engine": dict(
        category="Growth Engineering",
        quote="Threat modeling as a go-to-market motion.",
        cta="Read the growth spec →",
        topics="growth governed-ai automation",
    ),
    "autonomous-threat-modeling-2026": dict(
        category="Threat Modeling",
        quote="Continuous, architecture-grounded, executable.",
        cta="Read the method →",
        topics="cyber governed-ai agents systems",
    ),
    "canada-multipolar-sovereignty-resilience-strategy": dict(
        category="Strategic Resilience",
        quote="Uncertainty is a market.",
        cta="Read the strategy brief →",
        topics="strategic-resilience governed-ai cyber osint systems automation",
        series="ClearGlass Strategic Intelligence",
        deskRank=1,
    ),
    "canada-us-cross-border-cybersecurity-evidence-controls": dict(
        category="Cross-Border Controls",
        quote="North American operations fail at the evidence layer.",
        cta="Read the operating model →",
        topics="cross-border cyber systems",
        series="ClearGlass Legal Desk",
    ),
    "chatgpt-prompt-shortcuts-supercharge-ai-results": dict(
        category="Applied AI",
        quote="Prompting is a control surface.",
        cta="Open the composer →",
        topics="automation governed-ai systems",
    ),
    "clearglass-command-center-cyber-defense-console": dict(
        category="Design Engineering",
        quote="Every animation has to earn trust.",
        cta="Read the build notes →",
        topics="cyber systems",
    ),
    "cpcsc-vs-cmmc-residency-split": dict(
        category="Cross-Border Controls",
        quote="Reuse the controls. Not the location.",
        cta="Read the split →",
        topics="cross-border cyber systems",
        series="ClearGlass Legal Desk",
    ),
    "digital-twin-simulation-tools-storm-adaptive-transit-2026": dict(
        category="Resilient Infrastructure",
        quote="Simulate the storm before it arrives.",
        cta="Compare the platforms →",
        topics="systems automation strategic-resilience",
    ),
    "dual-clock-incident-runbook-ccspa-circia-pipeda": dict(
        category="Incident Response",
        quote="Two jurisdictions. Two clocks.",
        cta="Open the runbook →",
        topics="cross-border cyber systems",
        series="ClearGlass Legal Desk",
    ),
    "master-investigator-legal-tech-osint-government-accountability": dict(
        category="OSINT &amp; Accountability",
        quote="Factual, non-partisan, sourced.",
        cta="Read the blueprint →",
        topics="osint systems automation",
    ),
    "network-orchestration-ai-automation-cybersecurity": dict(
        category="AI Automation",
        quote="Staged autonomy, human in the loop.",
        cta="Read the briefing →",
        topics="automation cyber governed-ai systems",
    ),
    "ontario-influence-environment-august-2026": dict(
        category="OSINT &amp; Accountability",
        quote="Map the messaging. Grade the sources.",
        cta="Open the workstation →",
        topics="osint information-integrity systems",
    ),
    "rethinking-security-age-of-ai-cyber-stack": dict(
        category="Cyber Defense",
        quote="Continuous perception over periodic scanning.",
        cta="Read the strategic brief →",
        topics="cyber governed-ai agents",
    ),
    "shadow-ai-enterprise-security-blind-spot": dict(
        category="AI Governance",
        quote="You cannot govern what you cannot see.",
        cta="Read the briefing →",
        topics="governed-ai cyber systems",
    ),
    "shadow-ai-incident-response-logs-gone": dict(
        category="Incident Response",
        quote="Forensic readiness before the incident.",
        cta="Read the long read →",
        topics="governed-ai cyber systems",
    ),
    "telecommunications-legal-briefing-30-july-2026": dict(
        category="Law &amp; Technology",
        quote="CRTC, Ofcom, and the switching-fee record.",
        cta="Read the briefing →",
        topics="systems information-integrity",
        series="ClearGlass Legal Desk",
    ),
    "zero-trust-is-outdated-adaptive-trust": dict(
        category="Cyber Architecture",
        quote="Verify the action, not just the actor.",
        cta="Read the case →",
        topics="cyber systems agents",
    ),
}


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------
class BriefParser(HTMLParser):
    """Pulls the index-relevant surface out of one brief in a single pass."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.meta: dict[str, str] = {}
        self.canonical: str | None = None
        self.robots = ""
        self.jsonld: list[str] = []
        self.h1: str | None = None
        self.words = 0
        self._capture: str | None = None
        self._buf: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs_list: list) -> None:
        attrs = {k.lower(): (v or "") for k, v in attrs_list}
        if tag in ("script", "style") and attrs.get("type", "").lower() != "application/ld+json":
            self._skip += 1
        elif tag == "title" and self.title is None:
            self._capture, self._buf = "title", []
        elif tag == "h1" and self.h1 is None:
            self._capture, self._buf = "h1", []
        elif tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self._capture, self._buf = "jsonld", []
        elif tag == "meta":
            key = attrs.get("name") or attrs.get("property") or ""
            if key and "content" in attrs:
                self.meta.setdefault(key.lower(), attrs["content"].strip())
            if (attrs.get("name") or "").lower() == "robots":
                self.robots = attrs.get("content", "").lower()
        elif tag == "link":
            if "canonical" in attrs.get("rel", "").lower().split() and self.canonical is None:
                self.canonical = attrs.get("href", "").strip()

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip and self._capture != "jsonld":
            self._skip -= 1
            return
        if self._capture is None:
            return
        text = "".join(self._buf)
        if tag == "title" and self._capture == "title":
            self.title = collapse(text)
        elif tag == "h1" and self._capture == "h1":
            self.h1 = collapse(text)
        elif tag == "script" and self._capture == "jsonld":
            self.jsonld.append(text)
            self._skip = max(0, self._skip)
        else:
            return
        self._capture, self._buf = None, []

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._buf.append(data)
        elif not self._skip:
            self.words += len(data.split())


def collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def jsonld_values(parser: BriefParser, *keys: str) -> dict[str, object]:
    """First value seen for each key anywhere in the page's JSON-LD graphs."""
    found: dict[str, object] = {}
    wanted = set(keys)

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in wanted and key not in found and value not in (None, "", []):
                    found[key] = value
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for raw in parser.jsonld:
        try:
            walk(json.loads(raw))
        except (ValueError, TypeError):
            continue
    return found


DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def as_date(value: object) -> str | None:
    if isinstance(value, str):
        match = DATE_RE.search(value)
        if match:
            return match.group(1)
    return None


def as_tags(value: object) -> list[str]:
    if isinstance(value, str):
        parts = value.split(",")
    elif isinstance(value, list):
        parts = [str(item) for item in value]
    else:
        return []
    seen: list[str] = []
    for part in parts:
        tag = collapse(part).lower()
        if tag and tag not in seen:
            seen.append(tag)
    return seen[:12]


def clean_title(raw: str) -> str:
    """Drop the site suffix a browser tab needs but a card does not."""
    for sep in (" | ", " — ", " – "):
        if sep in raw:
            head, tail = raw.rsplit(sep, 1)
            if re.search(r"clearglass", tail, re.I) and len(head) > 12:
                return head.strip()
    return raw.strip()


# Regions that are generated onto a page rather than written by its author.
# They are stripped before the reading time is measured, both because chrome is
# not reading material and because counting the block this generator injects
# would make reading time feed back into its own input.
BOILERPLATE_RE = re.compile(
    r"<!-- cg-insights-related:start -->.*?<!-- cg-insights-related:end -->"
    r"|<!-- cg-related:start -->.*?<!-- cg-related:end -->"
    r'|<section class="ix-related" id="ixRelated".*?</section>'
    r"|<nav\b.*?</nav>"
    r"|<footer\b.*?</footer>",
    re.S | re.I,
)


def read_brief(path: Path) -> dict | None:
    """Build one index entry, or None if the page is not an indexable brief."""
    parser = BriefParser()
    parser.feed(BOILERPLATE_RE.sub(" ", path.read_text(encoding="utf-8", errors="ignore")))
    if "noindex" in parser.robots:
        return None

    slug = path.stem
    ld = jsonld_values(
        parser,
        "headline",
        "description",
        "datePublished",
        "dateModified",
        "articleSection",
        "keywords",
        "author",
    )

    raw_title = parser.meta.get("og:title") or parser.title or parser.h1 or ""
    title = clean_title(html.unescape(raw_title))
    if not title:
        return None

    description = html.unescape(
        parser.meta.get("description") or parser.meta.get("og:description") or ""
    ).strip()

    published = (
        as_date(parser.meta.get("article:published_time"))
        or as_date(ld.get("datePublished"))
        or as_date(slug)
    )
    modified = as_date(parser.meta.get("article:modified_time")) or as_date(ld.get("dateModified"))

    author = parser.meta.get("author") or ""
    if not author:
        node = ld.get("author")
        if isinstance(node, dict):
            author = str(node.get("name") or "")
        elif isinstance(node, list) and node and isinstance(node[0], dict):
            author = str(node[0].get("name") or "")
        elif isinstance(node, str):
            author = node
    author = collapse(html.unescape(author))

    curated = CURATED.get(slug, {})
    category = curated.get("category") or html.escape(str(ld.get("articleSection") or ""), quote=False)
    topics = [t for t in str(curated.get("topics", "")).split() if t in TOPICS]
    tags = as_tags(ld.get("keywords") or parser.meta.get("keywords"))

    entry: dict[str, object] = {
        "slug": slug,
        "url": f"/blog/{path.name}",
        "canonicalUrl": parser.canonical or f"{SITE}/blog/{path.name}",
        "title": title,
        "kind": "tool" if slug in NON_ARTICLE_SLUGS else "brief",
    }
    if description:
        entry["description"] = description
    if category:
        entry["category"] = category
    if curated.get("series"):
        entry["series"] = curated["series"]
    if topics:
        entry["topics"] = topics
    if tags:
        entry["tags"] = tags
    if author:
        entry["author"] = author
    if published:
        entry["publishedAt"] = published
    if modified and modified != published:
        entry["updatedAt"] = modified
    entry["readMinutes"] = max(1, round(parser.words / WORDS_PER_MINUTE))
    if curated.get("featured"):
        entry["featured"] = True
    if curated.get("deskRank"):
        entry["deskRank"] = curated["deskRank"]
    entry["quote"] = curated.get("quote", "")
    entry["cta"] = curated.get("cta", "Read the brief →")
    entry["status"] = "published"
    return entry


def build_index() -> dict:
    briefs = [
        read_brief(path)
        for path in sorted(BLOG.glob("*.html"))
        if path.name != "index.html"
    ]
    posts = [b for b in briefs if b]
    # Newest first; slug breaks ties so the ordering never depends on the
    # filesystem. Undated briefs sort last rather than pretending to be new.
    posts.sort(key=lambda p: (p.get("publishedAt") or "0000-00-00", p["slug"]), reverse=True)
    latest = max((p.get("publishedAt") or "" for p in posts), default="")
    return {
        "version": INDEX_VERSION,
        "generator": "tools/insights_index.py",
        "updated": latest,
        "site": SITE,
        "topics": TOPICS,
        "posts": posts,
    }


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
def e(value: object) -> str:
    """Escape for text content and attribute values alike."""
    return html.escape(str(value), quote=True)


def pre_escaped(value: str) -> str:
    """Curated copy is authored with entities already in it; leave it alone."""
    return value


def search_haystack(post: dict) -> str:
    """Plain-text search corpus for one card, entity-free so `&` matches `&`."""
    parts = [
        html.unescape(post["title"]),
        html.unescape(post.get("description", "")),
        html.unescape(post.get("category", "")),
        post.get("series", ""),
        " ".join(post.get("tags", [])),
        " ".join(TOPICS[t] for t in post.get("topics", [])),
        post.get("author", ""),
        post.get("publishedAt", ""),
    ]
    return collapse(" ".join(p for p in parts if p))


def human_date(date: str) -> str:
    import datetime as dt

    day = dt.date.fromisoformat(date)
    return f"{day.day} {RFC822_MONTHS[day.month - 1]} {day.year}"


def render_card(post: dict, badge: str | None) -> str:
    meta = []
    if badge:
        meta.append(f"<span>{e(badge)}</span>")
    if post.get("category"):
        meta.append(f"<span>{pre_escaped(post['category'])}</span>")
    meta.append(f"<span>{post['readMinutes']} min read</span>")
    date_attr = ""
    if post.get("publishedAt"):
        published = post["publishedAt"]
        date_attr = f' data-date="{e(published)}"'
        # Wrapped in a span because `.meta span` carries the pill styling; the
        # inner <time> is what makes the date machine-readable.
        meta.append(
            f'<span><time datetime="{e(published)}">{e(human_date(published))}</time></span>'
        )
    return (
        '<a class="article-card tilt-card" '
        f'href="{e(post["url"].rsplit("/", 1)[-1])}" '
        f'data-slug="{e(post["slug"])}" '
        f'data-title="{e(search_haystack(post))}" '
        f'data-tags="{e(" ".join(post.get("tags", [])))}" '
        f'data-topics="{e(" ".join(post.get("topics", [])))}"'
        f'{date_attr}>'
        f'<div class="card-art"><div class="quote">{pre_escaped(post.get("quote", ""))}</div></div>'
        '<div class="card-body">'
        f'<div class="meta">{"".join(meta)}</div>'
        f'<h3>{e(post["title"])}</h3>'
        f'<p>{e(post.get("description", ""))}</p>'
        f'<span class="read">{pre_escaped(post.get("cta", "Read the brief →"))}</span>'
        "</div></a>"
    )


def archive_posts(index: dict) -> list[dict]:
    """Everything the featured spotlight does not already show.

    The archive used to repeat 12 of the spotlight's cards verbatim, so a search
    for them returned the same brief twice while 20 other briefs had no card at
    all. Excluding the spotlight keeps every brief reachable exactly once.
    """
    return [p for p in index["posts"] if not p.get("featured")]


def render_archive(index: dict) -> str:
    posts = archive_posts(index)
    dated = sorted(
        (p for p in posts if p.get("publishedAt")),
        key=lambda p: p["publishedAt"],
        reverse=True,
    )
    fresh = {p["slug"] for p in dated[:3]}
    cards = [render_card(p, "New" if p["slug"] in fresh else None) for p in posts]
    return "\n      ".join(cards)


def render_chips(index: dict) -> str:
    counts = {t: 0 for t in TOPICS}
    for post in index["posts"]:
        for topic in post.get("topics", []):
            counts[topic] += 1
    chips = ['<a class="chip on" href="?" data-topic="all">All briefs</a>']
    for topic, label in TOPICS.items():
        if not counts[topic]:
            continue
        chips.append(
            f'<a class="chip" href="?topic={e(topic)}" data-topic="{e(topic)}">{e(label)}</a>'
        )
    chips.append('<a class="chip" href="?topic=saved" data-topic="saved">★ Saved</a>')
    return "".join(chips)


def render_pagination(index: dict) -> str:
    total = len(archive_posts(index))
    pages = max(1, -(-total // ARCHIVE_PAGE_SIZE))
    current = ' aria-current="page"'
    links = "".join(
        f'<a href="?page={n}#postGrid" data-page="{n}"'
        + (current if n == 1 else "")
        + f">{n}</a>"
        for n in range(1, pages + 1)
    )
    return (
        f'<p id="postPageStatus" aria-live="polite" aria-atomic="true">'
        f"Showing the first {min(ARCHIVE_PAGE_SIZE, total)} of {total} briefs.</p>\n"
        '      <div class="future-page-links">'
        f"{links}"
        '<button id="loadMorePosts" type="button">Load the next briefing page '
        '<span aria-hidden="true">↓</span></button></div>'
    )


def render_jsonld(index: dict) -> str:
    articles = [p for p in index["posts"] if p["kind"] == "brief"]
    graph = [
        {
            "@type": "WebSite",
            "@id": f"{SITE}/#website",
            "name": "ClearGlass Inc.",
            "url": f"{SITE}/",
            "publisher": {"@id": f"{SITE}/#org"},
            "potentialAction": {
                "@type": "SearchAction",
                "target": f"{SITE}/blog/?q={{search_term_string}}",
                "query-input": "required name=search_term_string",
            },
        },
        {
            "@type": "Organization",
            "@id": f"{SITE}/#org",
            "name": "ClearGlass Inc.",
            "url": f"{SITE}/",
            "logo": f"{SITE}/assets/images/clearglass-holographic-seal.png",
        },
        {
            "@type": "Blog",
            "@id": f"{SITE}/blog/#blog",
            "name": "ClearGlass Insights",
            "description": (
                "Governed AI, cybersecurity, autonomy, OSINT, and high-trust software systems."
            ),
            "url": f"{SITE}/blog/",
            "publisher": {"@id": f"{SITE}/#org"},
            "blogPost": [{"@id": f"{p['canonicalUrl']}#article"} for p in articles],
        },
        {
            "@type": "VideoObject",
            "@id": f"{SITE}/blog/#desk-film",
            "name": "Inside a ClearGlass intelligence desk",
            "description": (
                "A cinematic illustration of an analyst reviewing holographic panels — a global "
                "network grid, a cyber threat map, financial models, and actor telemetry — in a "
                "dark glass operations room. Rendered scene, not a recording of live systems or "
                "customer data."
            ),
            "thumbnailUrl": [f"{SITE}/assets/video/insights-intelligence-desk-poster.jpg"],
            "contentUrl": f"{SITE}/assets/video/insights-intelligence-desk.mp4",
            "uploadDate": "2026-08-02",
            "duration": "PT6S",
            "isFamilyFriendly": True,
            "publisher": {"@id": f"{SITE}/#org"},
        },
        {
            # Previously carried two position-1 entries, one of them an unnamed
            # article URL, which invalidates the whole list for a consumer.
            "@type": "BreadcrumbList",
            "@id": f"{SITE}/blog/#breadcrumbs",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
                {"@type": "ListItem", "position": 2, "name": "Insights", "item": f"{SITE}/blog/"},
            ],
        },
        {
            "@type": "ItemList",
            "@id": f"{SITE}/blog/#postlist",
            "name": "ClearGlass Insights — latest briefs",
            "itemListOrder": "https://schema.org/ItemListOrderDescending",
            "numberOfItems": len(articles),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": n,
                    "url": p["canonicalUrl"],
                    "name": p["title"],
                }
                for n, p in enumerate(articles, start=1)
            ],
        },
    ]
    payload = json.dumps(
        {"@context": "https://schema.org", "@graph": graph}, indent=2, ensure_ascii=False
    )
    return f'<script type="application/ld+json">\n{payload}\n</script>'


RFC822_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
RFC822_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def rfc822(date: str) -> str:
    import datetime as dt

    day = dt.date.fromisoformat(date)
    return (
        f"{RFC822_DAYS[day.weekday()]}, {day.day:02d} "
        f"{RFC822_MONTHS[day.month - 1]} {day.year} 00:00:00 GMT"
    )


def render_feed(index: dict) -> str:
    """RSS 2.0. The previous feed put a bare `&` in <title>, so it was not
    well-formed XML and every reader rejected it outright."""
    articles = [p for p in index["posts"] if p["kind"] == "brief" and p.get("publishedAt")]
    latest = max((p["publishedAt"] for p in articles), default=None)
    items = []
    for post in articles:
        link = post["canonicalUrl"]
        blocks = [
            f"      <title>{e(post['title'])}</title>",
            f"      <link>{e(link)}</link>",
            f'      <guid isPermaLink="true">{e(link)}</guid>',
            f"      <pubDate>{rfc822(post['publishedAt'])}</pubDate>",
        ]
        if post.get("description"):
            blocks.append(f"      <description>{e(post['description'])}</description>")
        if post.get("author"):
            blocks.append(f"      <dc:creator>{e(post['author'])}</dc:creator>")
        if post.get("category"):
            blocks.append(f"      <category>{e(html.unescape(post['category']))}</category>")
        items.append("    <item>\n" + "\n".join(blocks) + "\n    </item>")

    build = f"    <lastBuildDate>{rfc822(latest)}</lastBuildDate>\n" if latest else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        "  <channel>\n"
        "    <title>ClearGlass Insights — Governed AI, Cybersecurity &amp; Autonomy</title>\n"
        f"    <link>{SITE}/blog/</link>\n"
        f'    <atom:link href="{SITE}/blog/feed.xml" rel="self" type="application/rss+xml"/>\n'
        "    <description>A founder-led field journal for governed AI, autonomous agents, "
        "cybersecurity architecture, OSINT workflows, and high-trust software systems."
        "</description>\n"
        "    <language>en</language>\n"
        f"{build}"
        + "\n".join(items)
        + "\n  </channel>\n</rss>\n"
    )


# --------------------------------------------------------------------------
# per-article pass: social metadata + a crawlable "related" block
# --------------------------------------------------------------------------
RELATED_START = "<!-- cg-insights-related:start -->"
RELATED_END = "<!-- cg-insights-related:end -->"
RELATED_RE = re.compile(re.escape(RELATED_START) + r".*?" + re.escape(RELATED_END), re.S)
# The hand-written blocks this generator takes over from.
LEGACY_RELATED_RE = re.compile(
    r'[ \t]*<section class="ix-related" id="ixRelated">.*?</section>\n?', re.S
)
DEFAULT_OG_IMAGE = f"{SITE}/assets/images/clearglass-holographic-seal.png"


def related_posts(index: dict, post: dict, limit: int = 2) -> list[dict]:
    """Rank siblings the way blog/insights.js does, so the static block and the
    JavaScript-enhanced one agree: topic overlap counts double, then tags, then
    recency."""
    mine_topics = set(post.get("topics", []))
    mine_tags = set(post.get("tags", []))

    def score(other: dict) -> tuple[int, str]:
        overlap = len(mine_topics & set(other.get("topics", []))) * 2
        overlap += len(mine_tags & set(other.get("tags", [])))
        return (overlap, other.get("publishedAt") or "")

    pool = [
        p
        for p in index["posts"]
        if p["slug"] != post["slug"] and p["kind"] == "brief" and score(p)[0] > 0
    ]
    pool.sort(key=lambda p: (score(p), p["slug"]), reverse=True)
    return pool[:limit]


def render_related(index: dict, post: dict) -> str:
    cards = []
    for other in related_posts(index, post):
        tail = []
        if other.get("readMinutes"):
            tail.append(f"{other['readMinutes']} min read")
        if other.get("series"):
            tail.append(other["series"])
        cards.append(
            f'<a class="ix-related-card" href="{e(other["url"].rsplit("/", 1)[-1])}">'
            f'<span class="k">{pre_escaped(other.get("category", "Brief"))}</span>'
            f'<h4>{e(other["title"])}</h4>'
            f'<p>{e(other.get("description", ""))}</p>'
            f'<span class="m">{e(" · ".join(tail))}</span></a>'
        )
    cards.append(
        '<a class="ix-related-card" href="index.html"><span class="k">The hub</span>'
        "<h4>All ClearGlass Insights</h4><p>Governed AI, cybersecurity architecture, "
        "autonomy, OSINT workflows, and high-trust software systems.</p>"
        '<span class="m">Browse every brief →</span></a>'
    )
    body = "\n      ".join(cards[:2])
    return (
        f"  {RELATED_START}\n"
        '  <section class="ix-related" id="ixRelated" aria-labelledby="ixRelatedTitle">\n'
        '    <b id="ixRelatedTitle">Related from the desk</b>\n'
        '    <div class="ix-related-grid">\n'
        f"      {body}\n"
        "    </div>\n"
        "  </section>\n"
        f"  {RELATED_END}\n"
    )


# Where the related block goes, most specific anchor first. Each entry is a
# pattern whose match start is the insertion point.
RELATED_ANCHORS = (
    re.compile(r'[ \t]*<div class="endbar"'),
    re.compile(r"[ \t]*</article>"),
    re.compile(r"[ \t]*</main>"),
    re.compile(r'[ \t]*<footer\b'),
)


def social_meta(post: dict) -> list[tuple[str, str, str]]:
    """(attribute, key, content) triples a brief needs for link previews."""
    title = html.unescape(post["title"])
    description = post.get("description", "")
    url = post["canonicalUrl"]
    tags: list[tuple[str, str, str]] = [
        ("property", "og:type", "article"),
        ("property", "og:site_name", "ClearGlass Inc."),
        ("property", "og:title", title),
        ("property", "og:url", url),
        ("property", "og:image", DEFAULT_OG_IMAGE),
        ("name", "twitter:card", "summary_large_image"),
        ("name", "twitter:title", title),
        ("name", "twitter:image", DEFAULT_OG_IMAGE),
    ]
    if description:
        tags.insert(4, ("property", "og:description", description))
        tags.append(("name", "twitter:description", description))
    if post.get("publishedAt"):
        tags.append(("property", "article:published_time", post["publishedAt"]))
    if post.get("updatedAt"):
        tags.append(("property", "article:modified_time", post["updatedAt"]))
    if post.get("author"):
        tags.append(("property", "article:author", post["author"]))
    if post.get("category"):
        tags.append(("property", "article:section", html.unescape(post["category"])))
    return tags


HEAD_ANCHORS = (
    re.compile(r'[ \t]*<link rel="canonical"[^>]*>\n'),
    re.compile(r'[ \t]*<meta name="description"[^>]*>\n'),
    re.compile(r"[ \t]*<title>.*?</title>\n", re.S),
)


def apply_article_pass(index: dict, post: dict, text: str) -> str:
    """Add only what a brief is missing. Existing values are never overwritten —
    a page that already declares og:title keeps the one an editor chose."""
    out = text

    missing = []
    for attribute, key, content in social_meta(post):
        if re.search(rf'<meta\s+[^>]*{attribute}="{re.escape(key)}"', out, re.I):
            continue
        missing.append(f'<meta {attribute}="{key}" content="{e(content)}">')
    if missing:
        block = "".join(f"{tag}\n" for tag in missing)
        for anchor in HEAD_ANCHORS:
            match = anchor.search(out)
            if match:
                out = out[: match.end()] + block + out[match.end() :]
                break
        else:
            out = out.replace("</head>", block + "</head>", 1)

    # The shared Insights layer (table of contents, share/save, related ranking)
    # only runs on pages that actually load it.
    if "insights.css" not in out:
        out = out.replace("</head>", '<link rel="stylesheet" href="insights.css">\n</head>', 1)
    if "insights.js" not in out:
        out = out.replace("</body>", '<script defer src="insights.js"></script>\n</body>', 1)

    block = render_related(index, post)
    if RELATED_RE.search(out):
        return RELATED_RE.sub(lambda _: block.strip("\n").strip(), out, count=1)

    out = LEGACY_RELATED_RE.sub("", out, count=1)
    for anchor in RELATED_ANCHORS:
        match = anchor.search(out)
        if match:
            return out[: match.start()] + block + out[match.start() :]
    return out


# --------------------------------------------------------------------------
# writing
# --------------------------------------------------------------------------
def replace_region(text: str, name: str, body: str) -> str:
    start, end = MARKERS[name]
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end), re.S
    )
    if not pattern.search(text):
        raise SystemExit(
            f"blog/index.html is missing the {start} … {end} markers; "
            "add them around the region this generator owns."
        )
    return pattern.sub(lambda _: f"{start}\n      {body}\n      {end}", text, count=1)


def render_hub(index: dict, current: str) -> str:
    out = replace_region(current, "chips", render_chips(index))
    out = replace_region(out, "archive", render_archive(index))
    out = replace_region(out, "pagination", render_pagination(index))
    out = replace_region(out, "jsonld", render_jsonld(index))
    return out


def outputs(index: dict) -> dict[Path, str]:
    built = {
        POSTS_JSON: json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        HUB: render_hub(index, HUB.read_text(encoding="utf-8")),
        FEED: render_feed(index),
    }
    for post in index["posts"]:
        # Tool pages (the resume builder) are listed on the hub but are not
        # articles: no article:* metadata, no related-brief rail.
        if post["kind"] != "brief":
            continue
        path = BLOG / f"{post['slug']}.html"
        built[path] = apply_article_pass(index, post, path.read_text(encoding="utf-8"))
    return built


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="exit 1 if any generated file is stale"
    )
    args = parser.parse_args(argv)

    index = build_index()
    stale: list[str] = []
    for path, body in outputs(index).items():
        rel = path.relative_to(ROOT).as_posix()
        if path.read_text(encoding="utf-8") == body:
            continue
        stale.append(rel)
        if not args.check:
            path.write_text(body, encoding="utf-8")

    posts = index["posts"]
    if args.check:
        if stale:
            print("Stale generated Insights assets:", file=sys.stderr)
            for rel in stale:
                print(f"  - {rel}", file=sys.stderr)
            print("Run: python3 tools/insights_index.py", file=sys.stderr)
            return 1
        print(f"Insights index current — {len(posts)} briefs.")
        return 0

    print(f"Indexed {len(posts)} briefs ({len(archive_posts(index))} in the archive grid).")
    for rel in stale:
        print(f"  updated {rel}")
    if not stale:
        print("  no changes")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
