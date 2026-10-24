"""No sitemap may list a page that tells crawlers not to index it.

tools/generate_search_assets.py already skips noindex pages when it writes
sitemap.xml, but the three other sitemaps robots.txt advertises are
hand-maintained, and tools/seo_audit.py reads only sitemap.xml and treats a
conflict as a warning. This holds all four to the rule.

artemis-vi.html is pinned explicitly: the owner decided on 2026-10-23 to keep it
noindex, and its name is a substring of products/opal-koboi/artemis-vi.html,
an indexable page that is in sitemap.xml.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ROBOTS = re.compile(
    r"<meta\b(?=[^>]*\bname=[\"']robots[\"'])[^>]*\bcontent=[\"']([^\"']*)[\"']", re.I
)


def _advertised_sitemaps() -> list[Path]:
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    names = re.findall(r"^Sitemap:\s*\S+/([^/\s]+)$", robots, re.M)
    assert names, "robots.txt advertises no sitemap"
    return [ROOT / name for name in names]


def _page_for(loc: str) -> Path:
    path = urlparse(loc).path.lstrip("/")
    if not path or path.endswith("/"):
        path += "index.html"
    return ROOT / path


def _noindex(page: Path) -> bool:
    match = ROBOTS.search(page.read_text(encoding="utf-8", errors="ignore"))
    return bool(match) and "noindex" in match.group(1).lower()


def test_no_sitemap_lists_a_noindex_page() -> None:
    conflicts = []
    for sitemap in _advertised_sitemaps():
        for loc in re.findall(r"<loc>([^<]+)</loc>", sitemap.read_text(encoding="utf-8")):
            page = _page_for(loc.strip())
            if page.suffix == ".html" and page.exists() and _noindex(page):
                conflicts.append(f"{sitemap.name}: {loc}")
    assert not conflicts, conflicts


def test_artemis_vi_stays_noindex_and_out_of_every_sitemap() -> None:
    assert _noindex(ROOT / "artemis-vi.html")
    for sitemap in _advertised_sitemaps():
        assert "clearglassinc.com/artemis-vi.html<" not in sitemap.read_text(encoding="utf-8"), sitemap.name
