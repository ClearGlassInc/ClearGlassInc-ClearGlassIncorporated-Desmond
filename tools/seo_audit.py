#!/usr/bin/env python3
"""ClearGlass technical-SEO auditor.

Crawls the committed static site the way a search engine would read it — from
the filesystem, without executing JavaScript — and records every condition that
can keep a page out of an index or weaken how it ranks:

  - indexability      : robots meta, robots.txt rules, canonical target
  - discoverability   : sitemap coverage, dead sitemap entries, link orphans
  - on-page signals   : title, meta description, H1, heading order
  - structured data   : JSON-LD parses, @type inventory, required-field checks
  - crawl hygiene     : internal links pointing at files that do not exist
  - media             : images missing alt text
  - weight            : raw HTML bytes, as a Core Web Vitals proxy

Findings are graded `error` (blocks or badly distorts indexing), `warn`
(measurable ranking or presentation loss) or `info`. The exit code is non-zero
only for errors, so this is safe to gate CI on.

    python3 tools/seo_audit.py               # human-readable report
    python3 tools/seo_audit.py --json        # full findings as JSON
    python3 tools/seo_audit.py --write       # refresh data/seo/audit.json
    python3 tools/seo_audit.py --strict      # exit 1 on warnings too

stdlib only, so it runs in the same minimal CI images as the other gates.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import posixpath
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://www.clearglassinc.com"
OUT = ROOT / "data" / "seo" / "audit.json"

# Directories that are not part of the indexable marketing site.
SKIP_DIRS = {
    ".git", "node_modules", "clearglass-commerce", "apps", "tools",
    "bots", ".github", "assets", "docs",
}


def _published_pages() -> frozenset[str]:
    """Relative paths the site's own page registry declares published.

    ``SKIP_DIRS`` exists to keep source/vendor trees out of the audit, but some of
    those directories have since gained genuinely published pages (``apps/`` and
    ``docs/`` each hold one). Skipping them wholesale desynchronised two gates that
    must agree: ``tools/generate_search_assets.py`` dropped those URLs from
    ``sitemap.xml`` on every regeneration, while ``tools/authority_network.py``
    requires every registered page to appear in a sitemap — so regenerating broke the
    authority gate and not regenerating broke the ``git diff --exit-code`` freshness
    gate. Deferring to the registry keeps discovery and the site graph in step, and
    new pages under a skipped directory are picked up automatically.
    """
    try:
        from tools import internal_links
    except ImportError:  # pragma: no cover - standalone execution without the package
        try:
            import internal_links  # type: ignore[no-redef]
        except ImportError:
            return frozenset()
    return frozenset(internal_links.PAGES)


PUBLISHED_PAGES = _published_pages()

# Pages that are intentionally not indexable and must not be judged as content.
# Verification files and app shells are excluded from on-page scoring entirely.
UTILITY_PAGES = {
    "404.html", "offline.html", "loader.html", "cg-loader.html",
    "header-mockup-2040.html",
}

# Search-engine ownership-verification files: fixed content dictated by the
# search engine, so title/description rules do not apply.
VERIFICATION_RE = re.compile(r"^(google[0-9a-zA-Z]{16,}|BingSiteAuth|yandex_)", re.I)

TITLE_MIN, TITLE_MAX = 25, 62
DESC_MIN, DESC_MAX = 70, 165
# Bytes of raw HTML above which a page is worth splitting or deferring.
WEIGHT_WARN = 200_000


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
class PageParser(HTMLParser):
    """Collects the SEO-relevant surface of a page in one pass."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.description: str | None = None
        self.canonical: str | None = None
        self.robots: str = ""
        self.headings: list[tuple[int, str]] = []
        self.links: list[str] = []
        self.images: list[dict] = []
        self.jsonld: list[str] = []
        self.lang: str | None = None
        self.viewport: str | None = None
        self._capture: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list) -> None:
        attrs = {k.lower(): (v or "") for k, v in attrs_list}
        if tag == "html":
            self.lang = attrs.get("lang")
        elif tag == "title" and self.title is None:
            self._capture, self._buf = "title", []
        elif tag == "meta":
            name = attrs.get("name", "").lower()
            if name == "description" and self.description is None:
                self.description = attrs.get("content", "").strip()
            elif name == "robots":
                self.robots = attrs.get("content", "").lower()
            elif name == "viewport":
                self.viewport = attrs.get("content", "")
        elif tag == "link":
            rels = attrs.get("rel", "").lower().split()
            if "canonical" in rels and self.canonical is None:
                self.canonical = attrs.get("href", "").strip()
        elif tag == "script":
            if attrs.get("type", "").lower() == "application/ld+json":
                self._capture, self._buf = "jsonld", []
        elif re.fullmatch(r"h[1-6]", tag):
            self._capture, self._buf = tag, []
        elif tag == "a":
            href = attrs.get("href", "").strip()
            if href:
                self.links.append(href)
        elif tag == "img":
            self.images.append({"src": attrs.get("src", ""), "alt": attrs.get("alt")})

    def handle_endtag(self, tag: str) -> None:
        if self._capture is None:
            return
        text = "".join(self._buf)
        if tag == "title" and self._capture == "title":
            self.title = re.sub(r"\s+", " ", text).strip()
        elif tag == "script" and self._capture == "jsonld":
            self.jsonld.append(text)
        elif tag == self._capture and re.fullmatch(r"h[1-6]", tag):
            clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()
            self.headings.append((int(tag[1]), clean))
        else:
            return
        self._capture, self._buf = None, []

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._buf.append(data)


def strip_noise(html: str) -> str:
    """Remove style/script bodies so heading + link scans see real content."""
    html = re.sub(r"<style\b.*?</style>", "", html, flags=re.S | re.I)
    return re.sub(
        r"<script\b(?![^>]*application/ld\+json).*?</script>", "", html, flags=re.S | re.I
    )


# ---------------------------------------------------------------------------
# Site inventory
# ---------------------------------------------------------------------------
def discover_pages() -> list[Path]:
    pages: list[Path] = []
    for path in ROOT.rglob("*.html"):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in SKIP_DIRS and rel.as_posix() not in PUBLISHED_PAGES:
            continue
        if any(part == "node_modules" for part in rel.parts):
            continue
        pages.append(path)
    return sorted(pages)


def sitemap_urls() -> tuple[set[str], list[str]]:
    """Return (relative paths in sitemap, raw <loc> values)."""
    sm = ROOT / "sitemap.xml"
    if not sm.exists():
        return set(), []
    raw = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", sm.read_text(encoding="utf-8"))
    rels: set[str] = set()
    for loc in raw:
        rel = loc.replace(SITE, "").lstrip("/")
        rel = "index.html" if rel in ("", "/") else rel
        if rel.endswith("/"):
            rel += "index.html"
        rels.add(rel)
    return rels, raw


def robots_rules() -> list[str]:
    """Disallow paths that apply to the wildcard user-agent."""
    rp = ROOT / "robots.txt"
    if not rp.exists():
        return []
    rules, in_star = [], False
    for line in rp.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip().lower(), val.strip()
        if key == "user-agent":
            in_star = val == "*"
        elif key == "disallow" and in_star and val:
            rules.append(val)
    return rules


# ---------------------------------------------------------------------------
# Structured-data validation
# ---------------------------------------------------------------------------
# Minimum fields Google needs before a type is eligible for a rich result.
REQUIRED_FIELDS = {
    "Organization": ["name", "url"],
    "LocalBusiness": ["name", "address"],
    "ProfessionalService": ["name", "address"],
    "Service": ["name"],
    "Product": ["name"],
    "FAQPage": ["mainEntity"],
    "BreadcrumbList": ["itemListElement"],
    "Article": ["headline"],
    "TechArticle": ["headline"],
}


def walk_nodes(node, out: list[dict]) -> None:
    if isinstance(node, dict):
        if "@type" in node:
            out.append(node)
        for value in node.values():
            walk_nodes(value, out)
    elif isinstance(node, list):
        for item in node:
            walk_nodes(item, out)


def audit_structured_data(parser: PageParser, rel: str, findings: list[dict]) -> list[str]:
    types: list[str] = []
    for block in parser.jsonld:
        try:
            data = json.loads(block)
        except json.JSONDecodeError as exc:
            findings.append({
                "page": rel, "level": "error", "check": "schema.parse",
                "message": f"JSON-LD block does not parse: {exc}",
            })
            continue
        nodes: list[dict] = []
        walk_nodes(data, nodes)
        for node in nodes:
            raw_type = node.get("@type")
            for t in (raw_type if isinstance(raw_type, list) else [raw_type]):
                if not isinstance(t, str):
                    continue
                types.append(t)
                for field in REQUIRED_FIELDS.get(t, []):
                    if field not in node:
                        findings.append({
                            "page": rel, "level": "warn", "check": "schema.required",
                            "message": f"{t} is missing required property '{field}'",
                        })
    return types


# ---------------------------------------------------------------------------
# Per-page audit
# ---------------------------------------------------------------------------
def audit_page(path: Path, in_sitemap: set[str], disallow: list[str],
               findings: list[dict]) -> dict:
    rel = path.relative_to(ROOT).as_posix()
    raw = path.read_text(encoding="utf-8", errors="ignore")
    parser = PageParser()
    parser.feed(strip_noise(raw))

    noindex = "noindex" in parser.robots
    verification = bool(VERIFICATION_RE.match(path.name))
    utility = rel in UTILITY_PAGES or noindex or verification
    listed = rel in in_sitemap
    blocked = next((r for r in disallow if ("/" + rel).startswith(r)), None)

    record = {
        "page": rel,
        "url": f"{SITE}/{'' if rel == 'index.html' else rel}",
        "indexable": not noindex and not blocked,
        "noindex": noindex,
        "in_sitemap": listed,
        "robots_blocked": blocked,
        "title": parser.title,
        "title_length": len(parser.title or ""),
        "description": parser.description,
        "description_length": len(parser.description or ""),
        "canonical": parser.canonical,
        "h1_count": sum(1 for lvl, _ in parser.headings if lvl == 1),
        "schema_types": [],
        "internal_links": 0,
        "images_missing_alt": sum(1 for i in parser.images if not (i["alt"] or "").strip()),
        "bytes": len(raw.encode("utf-8")),
    }

    record["schema_types"] = audit_structured_data(parser, rel, findings)

    # --- indexability conflicts -------------------------------------------
    if noindex and listed:
        # Warning, not error: noindex wins, so the page stays out of the index
        # either way. The cost is wasted crawl budget and a contradictory
        # signal — worth fixing, but it breaks nothing.
        findings.append({
            "page": rel, "level": "warn", "check": "index.conflict",
            "message": "Page is noindex but listed in sitemap.xml — decide whether the page "
                       "should be public (drop the noindex) or internal (drop it from the "
                       "sitemap and the authority-network registry).",
        })
    if blocked and listed:
        findings.append({
            "page": rel, "level": "error", "check": "index.conflict",
            "message": f"Page is in sitemap.xml but blocked by robots.txt rule '{blocked}'.",
        })

    if utility:
        # Utility pages are deliberately thin; stop before content scoring.
        return record

    if not listed:
        findings.append({
            "page": rel, "level": "warn", "check": "sitemap.missing",
            "message": "Indexable page is absent from sitemap.xml — search engines may not discover it.",
        })

    # --- on-page signals ---------------------------------------------------
    if not parser.title:
        findings.append({"page": rel, "level": "error", "check": "title.missing",
                         "message": "Page has no <title>."})
    else:
        n = len(parser.title)
        if n > TITLE_MAX:
            findings.append({
                "page": rel, "level": "warn", "check": "title.length",
                "message": f"Title is {n} chars; over ~{TITLE_MAX} it is truncated in results.",
            })
        elif n < TITLE_MIN:
            findings.append({
                "page": rel, "level": "warn", "check": "title.length",
                "message": f"Title is only {n} chars — too little to carry a keyword and the brand.",
            })

    if not parser.description:
        findings.append({"page": rel, "level": "error", "check": "description.missing",
                         "message": "Page has no meta description."})
    else:
        n = len(parser.description)
        if n > DESC_MAX:
            findings.append({
                "page": rel, "level": "warn", "check": "description.length",
                "message": f"Meta description is {n} chars; Google truncates near {DESC_MAX}.",
            })
        elif n < DESC_MIN:
            findings.append({
                "page": rel, "level": "warn", "check": "description.length",
                "message": f"Meta description is only {n} chars — thin for a snippet.",
            })

    if not parser.canonical:
        findings.append({"page": rel, "level": "warn", "check": "canonical.missing",
                         "message": "No rel=canonical — duplicate URLs may split ranking signals."})

    h1s = [t for lvl, t in parser.headings if lvl == 1]
    if not h1s:
        findings.append({"page": rel, "level": "warn", "check": "h1.missing",
                         "message": "Page has no <h1>."})
    elif len(h1s) > 1:
        findings.append({
            "page": rel, "level": "warn", "check": "h1.multiple",
            "message": f"Page has {len(h1s)} <h1> elements — one primary heading is clearer.",
        })

    # Heading order: flag jumps deeper than one level (h2 -> h4).
    levels = [lvl for lvl, _ in parser.headings]
    for prev, cur in zip(levels, levels[1:]):
        if cur - prev > 1:
            findings.append({
                "page": rel, "level": "info", "check": "heading.order",
                "message": f"Heading level jumps from h{prev} to h{cur} — skipped levels weaken outline parsing.",
            })
            break

    if parser.lang is None:
        findings.append({"page": rel, "level": "warn", "check": "lang.missing",
                         "message": "<html> has no lang attribute."})
    if parser.viewport is None:
        findings.append({"page": rel, "level": "warn", "check": "viewport.missing",
                         "message": "No viewport meta — page will not be treated as mobile-friendly."})

    if record["images_missing_alt"]:
        findings.append({
            "page": rel, "level": "info", "check": "image.alt",
            "message": f"{record['images_missing_alt']} image(s) missing alt text.",
        })

    if record["bytes"] > WEIGHT_WARN:
        findings.append({
            "page": rel, "level": "warn", "check": "weight",
            "message": f"{record['bytes'] // 1024} KB of HTML — heavy enough to hurt LCP on mobile.",
        })

    return record


# ---------------------------------------------------------------------------
# Link graph
# ---------------------------------------------------------------------------
def audit_links(pages: list[Path], records: dict[str, dict],
                findings: list[dict]) -> None:
    """Resolve internal links to find broken targets and orphaned pages."""
    on_disk = {p.relative_to(ROOT).as_posix() for p in pages}
    inbound = {rel: 0 for rel in records}

    for path in pages:
        rel = path.relative_to(ROOT).as_posix()
        parser = PageParser()
        parser.feed(strip_noise(path.read_text(encoding="utf-8", errors="ignore")))
        seen_broken: set[str] = set()
        count = 0

        for href in parser.links:
            if href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
                continue
            target = href.split("#", 1)[0].split("?", 1)[0]
            if not target:
                continue
            if target.startswith(("http://", "https://")):
                if not target.startswith(SITE):
                    continue
                target = target[len(SITE):]
                target = target.lstrip("/")
            elif target.startswith("/"):
                target = target.lstrip("/")
            else:
                # Relative link — resolve against the linking page's directory.
                target = posixpath.normpath(posixpath.join(posixpath.dirname(rel), target))
                if target.startswith(".."):
                    findings.append({
                        "page": rel, "level": "error", "check": "link.broken",
                        "message": f"Internal link '{href}' escapes the site root.",
                    })
                    continue
            target = "index.html" if target in ("", "/", ".") else target
            if target.endswith("/"):
                target += "index.html"
            if not target.endswith(".html"):
                continue  # asset or extensionless route — not resolved here

            count += 1
            if target in inbound:
                if target != rel:
                    inbound[target] += 1
            elif (target not in on_disk and not (ROOT / target).exists()
                  and target not in seen_broken):
                seen_broken.add(target)
                findings.append({
                    "page": rel, "level": "error", "check": "link.broken",
                    "message": f"Internal link points at '{target}', which does not exist.",
                })

        records[rel]["internal_links"] = count

    for rel, hits in inbound.items():
        rec = records[rel]
        if (hits == 0 and rec["indexable"] and rel not in UTILITY_PAGES
                and rel != "index.html" and not VERIFICATION_RE.match(Path(rel).name)):
            findings.append({
                "page": rel, "level": "warn", "check": "orphan",
                "message": "No internal links point to this page — it receives no internal link equity.",
            })
        rec["inbound_links"] = hits


def audit_sitemap(records: dict[str, dict], findings: list[dict]) -> None:
    rels, raw = sitemap_urls()
    for rel in sorted(rels):
        if rel not in records and not (ROOT / rel).exists():
            findings.append({
                "page": "sitemap.xml", "level": "error", "check": "sitemap.dead",
                "message": f"sitemap.xml lists '{rel}', which does not exist — a 404 in the sitemap.",
            })
    for loc in raw:
        if not loc.startswith(SITE):
            findings.append({
                "page": "sitemap.xml", "level": "error", "check": "sitemap.host",
                "message": f"sitemap.xml entry '{loc}' is not on the canonical host {SITE}.",
            })


def audit_uniqueness(records: dict[str, dict], findings: list[dict]) -> None:
    """Detect metadata collisions that make distinct routes compete as duplicates."""
    for field in ("title", "description", "canonical"):
        owners: dict[str, list[str]] = {}
        for rel, record in records.items():
            if not record["indexable"] or rel in UTILITY_PAGES:
                continue
            value = record.get(field)
            if value:
                owners.setdefault(value.strip(), []).append(rel)
        for value, pages in owners.items():
            if len(pages) > 1:
                findings.append({
                    "page": ", ".join(sorted(pages)),
                    "level": "warn",
                    "check": f"{field}.duplicate",
                    "message": f"{len(pages)} indexable pages share the same {field}: '{value}'.",
                })


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def build_report() -> dict:
    pages = discover_pages()
    rels, _ = sitemap_urls()
    disallow = robots_rules()
    findings: list[dict] = []

    records = {}
    for path in pages:
        rec = audit_page(path, rels, disallow, findings)
        records[rec["page"]] = rec

    audit_links(pages, records, findings)
    audit_sitemap(records, findings)
    audit_uniqueness(records, findings)

    indexable = [
        r for r in records.values()
        if r["indexable"] and r["page"] not in UTILITY_PAGES
        and not VERIFICATION_RE.match(Path(r["page"]).name)
    ]
    counts = {"error": 0, "warn": 0, "info": 0}
    for f in findings:
        counts[f["level"]] += 1

    by_check: dict[str, int] = {}
    for f in findings:
        by_check[f["check"]] = by_check.get(f["check"], 0) + 1

    # Health score: errors cost 3, warnings 1, floored at 0.
    penalty = counts["error"] * 3 + counts["warn"]
    score = max(0, 100 - round(penalty * 100 / max(len(indexable) * 4, 1)))

    return {
        "generated": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "site": SITE,
        "score": score,
        "totals": {
            "pages": len(records),
            "indexable": len(indexable),
            "in_sitemap": sum(1 for r in records.values() if r["in_sitemap"]),
            "noindex": sum(1 for r in records.values() if r["noindex"]),
            "with_schema": sum(1 for r in records.values() if r["schema_types"]),
            "errors": counts["error"],
            "warnings": counts["warn"],
            "info": counts["info"],
        },
        "by_check": dict(sorted(by_check.items(), key=lambda kv: -kv[1])),
        "findings": sorted(findings, key=lambda f: ({"error": 0, "warn": 1, "info": 2}[f["level"]], f["page"])),
        "pages": [records[k] for k in sorted(records)],
    }


def print_report(report: dict) -> None:
    t = report["totals"]
    print(f"ClearGlass SEO audit · {report['generated']}")
    print(f"  health score      {report['score']}/100")
    print(f"  pages             {t['pages']} ({t['indexable']} indexable, {t['noindex']} noindex)")
    print(f"  in sitemap        {t['in_sitemap']}")
    print(f"  with structured data {t['with_schema']}")
    print(f"  findings          {t['errors']} error · {t['warnings']} warn · {t['info']} info")

    if report["by_check"]:
        print("\ntop checks:")
        for check, n in list(report["by_check"].items())[:12]:
            print(f"  {n:>4}  {check}")

    errors = [f for f in report["findings"] if f["level"] == "error"]
    if errors:
        print(f"\nerrors ({len(errors)}):")
        for f in errors[:40]:
            print(f"  {f['page']}: {f['message']}")
        if len(errors) > 40:
            print(f"  … and {len(errors) - 40} more")

    warns = [f for f in report["findings"] if f["level"] == "warn"]
    if warns:
        print(f"\nwarnings ({len(warns)}, first 25):")
        for f in warns[:25]:
            print(f"  {f['page']}: {f['message']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ClearGlass technical-SEO auditor")
    ap.add_argument("--json", action="store_true", help="emit the full report as JSON")
    ap.add_argument("--write", action="store_true", help=f"write {OUT.relative_to(ROOT)}")
    ap.add_argument("--strict", action="store_true", help="exit 1 on warnings as well as errors")
    args = ap.parse_args(argv)

    report = build_report()

    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}", file=sys.stderr)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)

    if report["totals"]["errors"]:
        return 1
    if args.strict and report["totals"]["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
