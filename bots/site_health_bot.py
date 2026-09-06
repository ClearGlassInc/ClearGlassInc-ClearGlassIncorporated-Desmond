# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Site health bot — checks live page availability and SEO structure.

Health policy:
  * FAILURES (flip overall_healthy -> False): any monitored page unreachable,
    a required root file missing, or a shipped HTML page missing the ClearGlass
    logo. These are genuine availability / branding problems.
  * WARNINGS (reported, do NOT fail health): HTML pages not referenced in
    sitemap.xml. The repo intentionally ships many utility / non-indexed pages
    (404, button-system, hover-menu, component demos, etc.), so sitemap drift
    is informational, not an outage.
"""
from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "output"

SITE_URL = "https://www.clearglassinc.com"
REQUEST_TIMEOUT = 15
USER_AGENT = "ClearGlass-HealthBot/1.0"

PAGES_TO_CHECK = [
    "/",
    "/artemis.html",
    "/artemis-iv.html",
    "/guardian.html",
    "/clearglass-nexus.html",
    "/government.html",
]

REQUIRED_META_TAGS = ["description", "og:title", "og:description"]
REQUIRED_ROOT_FILES = ["sitemap.xml", "robots.txt", "schema.json", ".nojekyll"]

# Pages that are intentionally not in the sitemap (utility / demo / fragments).
# Drift on anything else is still surfaced as a warning, never a failure.
SITEMAP_EXEMPT = {
    "404.html",
    "button-system.html",
    "button-lab.html",            # component showcase / demo, not a landing page
    "hover-menu.html",
    "smb.html",
    "index.html",                 # homepage is indexed as "/" — avoid duplicate
    "cg-loader.html",             # session preloader fragment, not a landing page
    "loader.html",                # noindex initializer, not a landing page
    "offline.html",               # service-worker offline shell (noindex)
    "platform-command-center.html",  # internal platform HUD dashboard (noindex, not a landing page)
    "ClearGlass-NEXUS-v12-FINAL.html",  # build artifact of clearglass-nexus.html
    # Google Search Console verification token — must NOT be in the sitemap
    "google23RWyXWkoxqgArev8achU8IfVxYC5EIUAYBsuTYKLFM.html",
}

# Pages exempt from the "logo on every page" guarantee. The Google Search
# Console verification file must contain ONLY its token — any extra markup
# breaks domain verification — so it is the sole legitimate exemption.
LOGO_EXEMPT = {
    "google23RWyXWkoxqgArev8achU8IfVxYC5EIUAYBsuTYKLFM.html",
}


IGNORED_HTML_DIRS = {
    ".git",
    ".next",
    "node_modules",
}


def _is_shipped_html(path: Path) -> bool:
    """Return True for source-controlled HTML pages, not generated deps/builds."""
    return not any(part in IGNORED_HTML_DIRS for part in path.relative_to(ROOT).parts)

# Proof that a page carries the ClearGlass logo: either the shared corner-badge
# script (injected on every non-home page via <script src="/logo-badge.js">) or
# a direct reference to the logo image asset (the homepage's nav/footer mark).
LOGO_MARKERS = ("logo-badge.js", "clearglass-logo")


def _page_has_logo(html: str) -> bool:
    """True if the page carries the ClearGlass logo (badge script or logo img)."""
    return any(marker in html for marker in LOGO_MARKERS)


@dataclass
class PageHealth:
    path: str
    url: str
    status_code: int | None
    reachable: bool
    response_ms: int
    has_title: bool
    missing_meta: list[str]
    error: str | None = None


@dataclass
class HealthReport:
    run_utc: str
    site_url: str
    overall_healthy: bool
    pages_checked: int
    pages_healthy: int
    pages_unreachable: int
    pages: list[dict[str, Any]]
    local_issues: list[str]                       # failures
    local_warnings: list[str] = field(default_factory=list)  # non-failing


def _check_page(path: str) -> PageHealth:
    url = f"{SITE_URL}{path}"
    start = time.monotonic()
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            status = resp.status
            html = resp.read().decode("utf-8", errors="replace")
        elapsed = int((time.monotonic() - start) * 1000)

        has_title = bool(re.search(r"<title[^>]*>.+?</title>", html, re.IGNORECASE | re.DOTALL))
        missing_meta = [
            tag for tag in REQUIRED_META_TAGS
            if not re.search(
                rf'(?:name|property)=["\'](?:og:)?{re.escape(tag.replace("og:", ""))}["\']',
                html,
                re.IGNORECASE,
            )
        ]

        return PageHealth(
            path=path, url=url, status_code=status,
            reachable=status < 400, response_ms=elapsed,
            has_title=has_title, missing_meta=missing_meta,
        )
    except (HTTPError, URLError, Exception) as exc:  # noqa: BLE001
        elapsed = int((time.monotonic() - start) * 1000)
        return PageHealth(
            path=path, url=url, status_code=None, reachable=False,
            response_ms=elapsed, has_title=False,
            missing_meta=list(REQUIRED_META_TAGS), error=str(exc),
        )


def _check_local_files() -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Missing required files are errors; sitemap
    drift is a warning."""
    errors: list[str] = []
    warnings: list[str] = []

    for fname in REQUIRED_ROOT_FILES:
        if not (ROOT / fname).exists():
            errors.append(f"Missing required file: {fname}")

    sitemap_path = ROOT / "sitemap.xml"
    if sitemap_path.exists():
        sitemap = sitemap_path.read_text()
        for html_file in sorted(ROOT.glob("*.html")):
            if html_file.name in SITEMAP_EXEMPT:
                continue
            if html_file.name not in sitemap:
                warnings.append(f"HTML page not referenced in sitemap.xml: {html_file.name}")

    # Every shipped HTML page must carry the ClearGlass logo — via the shared
    # /logo-badge.js corner badge or a direct logo image (homepage nav/footer).
    # A missing logo is a real branding regression, so it fails health. Scanned
    # recursively so nested pages (legal/, offers/, products/, …) are covered.
    for html_file in sorted(ROOT.rglob("*.html")):
        if html_file.name in LOGO_EXEMPT or not _is_shipped_html(html_file):
            continue
        try:
            page = html_file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:  # pragma: no cover - unreadable file is itself a fault
            errors.append(f"Could not read {html_file.relative_to(ROOT)}: {exc}")
            continue
        if not _page_has_logo(page):
            errors.append(f"Page missing ClearGlass logo: {html_file.relative_to(ROOT)}")

    return errors, warnings


def run() -> HealthReport:
    pages = [_check_page(p) for p in PAGES_TO_CHECK]
    local_errors, local_warnings = _check_local_files()

    healthy_count = sum(1 for p in pages if p.reachable and not p.missing_meta)
    unreachable_count = sum(1 for p in pages if not p.reachable)

    report = HealthReport(
        run_utc=datetime.now(timezone.utc).isoformat(),
        site_url=SITE_URL,
        # Only true availability problems fail health; sitemap drift is a warning.
        overall_healthy=(unreachable_count == 0 and not local_errors),
        pages_checked=len(pages),
        pages_healthy=healthy_count,
        pages_unreachable=unreachable_count,
        pages=[asdict(p) for p in pages],
        local_issues=local_errors,
        local_warnings=local_warnings,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "site_health_report.json").write_text(json.dumps(asdict(report), indent=2))

    md: list[str] = [
        "# Site Health Report",
        "",
        f"**Run:** {report.run_utc}",
        f"**Status:** {'✅ Healthy' if report.overall_healthy else '⚠️ Issues Detected'}",
        f"**Pages:** {report.pages_healthy}/{report.pages_checked} healthy",
        "",
        "## Pages",
        "",
    ]
    for p in pages:
        icon = "✅" if p.reachable else "❌"
        timing = f"{p.response_ms}ms" if p.reachable else "—"
        md.append(f"- {icon} `{p.path}` ({timing})")
        if p.missing_meta:
            md.append(f"  - Missing meta: {', '.join(p.missing_meta)}")
        if p.error:
            md.append(f"  - Error: {p.error}")

    if local_errors:
        md += ["", "## Local Issues", ""]
        for issue in local_errors:
            md.append(f"- ❌ {issue}")

    if local_warnings:
        md += ["", "## Warnings (non-failing)", ""]
        for warn in local_warnings:
            md.append(f"- ⚠️ {warn}")

    (OUTPUT_DIR / "site_health_report.md").write_text("\n".join(md))
    return report


def main() -> None:
    report = run()
    status = "HEALTHY" if report.overall_healthy else "ISSUES DETECTED"
    print(f"Site Health: {status} — {report.pages_healthy}/{report.pages_checked} pages OK")
    if report.local_warnings:
        print(f"  ({len(report.local_warnings)} non-failing sitemap warning(s))")
    if not report.overall_healthy:
        sys.exit(1)


if __name__ == "__main__":
    main()
