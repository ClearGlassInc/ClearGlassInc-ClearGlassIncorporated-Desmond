# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
#!/usr/bin/env python3
"""Repository reliability audit for ClearGlassInc.github.io.

Checks:
- Broken local links (href/src in html files)
- Missing core documentation files
- Workflow hygiene (permissions + trigger existence)
- Sitemap URL sanity
- GitHub Pages custom domain readiness (CNAME + canonical domain usage)
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DOMAIN = "www.clearglassinc.com"
IGNORED_AUDIT_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "__pycache__",
    "coverage",
    "dist",
    "node_modules",
}


def iter_repo_html_files() -> list[Path]:
    """Return repository-owned HTML files, excluding dependency/build output trees."""

    return sorted(
        path
        for path in REPO_ROOT.rglob("*.html")
        if not any(part in IGNORED_AUDIT_DIRS for part in path.relative_to(REPO_ROOT).parts)
    )


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[tuple[str, int]] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if attr_map.get("id"):
            self.ids.add(attr_map["id"])
        if tag == "a" and attr_map.get("name"):
            self.ids.add(attr_map["name"])
        if tag in {"a", "link"} and attr_map.get("href"):
            self.references.append((attr_map["href"], self.getpos()[0]))
        elif tag in {"img", "script", "source"} and attr_map.get("src"):
            self.references.append((attr_map["src"], self.getpos()[0]))


class AnchorParser(HTMLParser):
    """Collect addressable element IDs and legacy named anchors."""

    def __init__(self) -> None:
        super().__init__()
        self.anchors: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if attr_map.get("id"):
            self.anchors.add(attr_map["id"])
        if tag == "a" and attr_map.get("name"):
            self.anchors.add(attr_map["name"])


@dataclass
class AuditIssue:
    level: str
    message: str


def is_local_ref(ref: str) -> bool:
    prefixes = ("http://", "https://", "//", "mailto:", "tel:", "#", "javascript:", "data:")
    return not ref.startswith(prefixes)


def resolve_page_target(path: Path) -> Path:
    """Resolve a Pages-style directory URL to its checked-in entry document."""

    return path / "index.html" if path.is_dir() else path


def check_links() -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    html_files = iter_repo_html_files()

    for html_file in html_files:
        parser = LinkParser()
        parser.feed(html_file.read_text(encoding="utf-8", errors="ignore"))
        for ref, line_number in parser.references:
            parsed_ref = urlparse(ref)
            is_same_site_absolute = (
                parsed_ref.scheme in {"http", "https"}
                and parsed_ref.hostname == EXPECTED_DOMAIN
            )
            if not is_local_ref(ref) and not is_same_site_absolute and not ref.startswith("#"):
                continue

            local_ref = unquote(parsed_ref.path)

            if not local_ref:
                target = html_file
            elif local_ref.startswith("/"):
                target = (REPO_ROOT / local_ref.lstrip("/")).resolve()
            else:
                target = (html_file.parent / local_ref).resolve()

            if not str(target).startswith(str(REPO_ROOT.resolve())):
                issues.append(AuditIssue("ERROR", f"Invalid path outside repository in {html_file.relative_to(REPO_ROOT)}:{line_number} -> {ref}"))
                continue

            target = resolve_page_target(target)
            if not target.is_file():
                issues.append(
                    AuditIssue(
                        "ERROR",
                        f"Broken local reference {html_file.relative_to(REPO_ROOT)}:{line_number} -> {ref}",
                    )
                )
                continue

            fragment = urlparse(ref).fragment
            if fragment and target.is_file() and target.suffix.lower() in {".html", ".htm"}:
                anchor_parser = AnchorParser()
                anchor_parser.feed(target.read_text(encoding="utf-8", errors="ignore"))
                if fragment not in anchor_parser.anchors:
                    issues.append(
                        AuditIssue(
                            "ERROR",
                            f"Missing fragment target {html_file.relative_to(REPO_ROOT)}:"
                            f"{line_number} -> {ref}",
                        )
                    )

    return issues


def check_required_docs() -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    required_files = [
        "README.md",
        "SECURITY.md",
        "legal/privacy.html",
        "legal/terms.html",
    ]

    for rel_path in required_files:
        if not (REPO_ROOT / rel_path).exists():
            issues.append(AuditIssue("ERROR", f"Missing required file: {rel_path}"))

    return issues


def check_workflows() -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    workflow_dir = REPO_ROOT / ".github" / "workflows"
    workflow_files = sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml"))

    if not workflow_files:
        return [AuditIssue("ERROR", "No GitHub Actions workflows found in .github/workflows")]

    for wf in workflow_files:
        text = wf.read_text(encoding="utf-8", errors="ignore")

        if "on:" not in text:
            issues.append(AuditIssue("ERROR", f"Workflow missing triggers: {wf.relative_to(REPO_ROOT)}"))

        if "permissions:" not in text:
            issues.append(AuditIssue("WARN", f"Workflow missing explicit permissions: {wf.relative_to(REPO_ROOT)}"))

    return issues


def check_sitemap() -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    sitemap = REPO_ROOT / "sitemap.xml"
    if not sitemap.exists():
        return [AuditIssue("WARN", "No sitemap.xml found")]

    try:
        tree = ET.parse(sitemap)
        root = tree.getroot()
    except ET.ParseError as exc:
        return [AuditIssue("ERROR", f"Invalid sitemap.xml: {exc}")]

    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = root.findall("sm:url/sm:loc", namespace)
    if not urls:
        issues.append(AuditIssue("WARN", "sitemap.xml has no <loc> entries"))

    seen: set[str] = set()
    for loc in urls:
        value = (loc.text or "").strip()
        if not value:
            issues.append(AuditIssue("ERROR", "Empty URL in sitemap"))
            continue
        if " " in value:
            issues.append(AuditIssue("ERROR", f"Invalid URL in sitemap (contains whitespace): {value}"))
        if value in seen:
            issues.append(AuditIssue("ERROR", f"Duplicate URL in sitemap: {value}"))
        seen.add(value)

        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.hostname != EXPECTED_DOMAIN:
            issues.append(AuditIssue("ERROR", f"Sitemap URL is outside the canonical HTTPS origin: {value}"))
            continue
        route = unquote(parsed.path).lstrip("/") or "index.html"
        target = resolve_page_target((REPO_ROOT / route).resolve())
        if not target.is_file():
            issues.append(AuditIssue("ERROR", f"Sitemap URL has no published file: {value}"))

    return issues


def check_robots() -> list[AuditIssue]:
    """Validate crawl directives and every sitemap connection declared to bots."""

    robots = REPO_ROOT / "robots.txt"
    if not robots.is_file():
        return [AuditIssue("ERROR", "Missing robots.txt")]

    issues: list[AuditIssue] = []
    for line_number, raw_line in enumerate(robots.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            issues.append(AuditIssue("ERROR", f"Malformed robots.txt directive at line {line_number}: {line}"))
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        if field.lower() != "sitemap":
            continue
        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.hostname != EXPECTED_DOMAIN:
            issues.append(AuditIssue("ERROR", f"robots.txt declares a non-canonical sitemap: {value}"))
            continue
        sitemap_path = REPO_ROOT / unquote(parsed.path).lstrip("/")
        if not sitemap_path.is_file():
            issues.append(AuditIssue("ERROR", f"robots.txt declares a missing sitemap: {value}"))

    return issues


def check_pages_domain() -> list[AuditIssue]:
    issues: list[AuditIssue] = []

    index_file = REPO_ROOT / "index.html"
    if not index_file.exists():
        issues.append(AuditIssue("ERROR", "Missing index.html at repository root"))

    cname_file = REPO_ROOT / "CNAME"
    if not cname_file.exists():
        issues.append(
            AuditIssue(
                "WARN",
                (
                    "CNAME file missing while repository is configured for the custom domain "
                    f"('{EXPECTED_DOMAIN}')."
                ),
            )
        )
    else:
        cname_value = cname_file.read_text(encoding="utf-8", errors="ignore").strip()
        if cname_value != EXPECTED_DOMAIN:
            issues.append(
                AuditIssue(
                    "WARN",
                    (
                        f"CNAME value does not match the expected custom domain ('{EXPECTED_DOMAIN}'). "
                        f"Current CNAME value: '{cname_value or '(empty)'}'"
                    ),
                )
            )

    searchable_files = (
        sorted(REPO_ROOT.glob("*.html"))
        + sorted(REPO_ROOT.glob("*.xml"))
        + sorted(REPO_ROOT.glob("*.json"))
        + sorted((REPO_ROOT / "legal").glob("*.html"))
    )
    legacy_domain = "clearglassinc.io"
    url_pattern = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)

    for file_path in searchable_files:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for raw_url in url_pattern.findall(text):
            host = urlparse(raw_url).hostname
            if host and (host == legacy_domain or host.endswith(f".{legacy_domain}")):
                issues.append(
                    AuditIssue(
                        "WARN",
                        f"Legacy custom-domain reference found in {file_path.relative_to(REPO_ROOT)}",
                    )
                )
                break

    return issues


def check_seo_accessibility() -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    html_files = iter_repo_html_files()
    script_block = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)

    for html_file in html_files:
        rel = html_file.relative_to(REPO_ROOT)
        text = html_file.read_text(encoding="utf-8", errors="ignore")

        # Search-engine ownership-verification files (e.g. Google's
        # google<token>.html) are bare verification strings, not real pages, and
        # must keep their exact required content — skip page-level SEO/a11y checks.
        if text.lstrip().lower().startswith("google-site-verification:"):
            continue

        if not re.search(r"<html[^>]*\blang=", text, re.IGNORECASE):
            issues.append(AuditIssue("WARN", f"Missing <html lang> attribute in {rel}"))

        if not re.search(r'name=["\']viewport["\']', text, re.IGNORECASE):
            issues.append(AuditIssue("WARN", f"Missing <meta name=viewport> in {rel}"))

        if not re.search(r"<title", text, re.IGNORECASE):
            issues.append(AuditIssue("WARN", f"Missing <title> in {rel}"))

        if not re.search(r'name=["\']description["\']', text, re.IGNORECASE):
            issues.append(AuditIssue("WARN", f"Missing <meta name=description> in {rel}"))

        # Strip <script> blocks before the <img> scan: inline JavaScript can
        # contain regex/string literals like /<img[^>]*>/ that would otherwise
        # trip the alt-attribute check (false positive on real, alt'd markup).
        markup = script_block.sub("", text)
        for img in re.findall(r"<img\b[^>]*>", markup, re.IGNORECASE):
            if not re.search(r"\balt=", img, re.IGNORECASE):
                issues.append(AuditIssue("WARN", f"Image missing alt attribute in {rel}"))

    return issues


def print_report(issues: list[AuditIssue]) -> int:
    errors = [issue for issue in issues if issue.level == "ERROR"]
    warns = [issue for issue in issues if issue.level == "WARN"]

    print("== ClearGlassInc Site Reliability Audit ==")
    print(f"Repository: {REPO_ROOT}")
    print(f"Errors: {len(errors)} | Warnings: {len(warns)}")
    print()

    for issue in errors + warns:
        icon = "❌" if issue.level == "ERROR" else "⚠️"
        print(f"{icon} {issue.level}: {issue.message}")

    if not issues:
        print("✅ No issues detected.")

    return 1 if errors else 0


def main() -> int:
    all_issues: list[AuditIssue] = []
    all_issues.extend(check_links())
    all_issues.extend(check_required_docs())
    all_issues.extend(check_workflows())
    all_issues.extend(check_sitemap())
    all_issues.extend(check_robots())
    all_issues.extend(check_pages_domain())
    all_issues.extend(check_seo_accessibility())
    return print_report(all_issues)


if __name__ == "__main__":
    sys.exit(main())
