# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""SEO optimizer bot — audits all HTML pages for on-page SEO compliance."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "output"

TITLE_MIN, TITLE_MAX = 30, 60
DESC_MIN, DESC_MAX = 120, 160


@dataclass
class PageSEO:
    file: str
    title: str | None
    title_length: int
    title_ok: bool
    description: str | None
    description_length: int
    description_ok: bool
    canonical_present: bool
    h1_count: int
    h1_ok: bool
    img_without_alt: int
    og_title: bool
    og_description: bool
    og_image: bool
    score: int
    issues: list[str]


@dataclass
class SEOReport:
    run_utc: str
    files_audited: int
    average_score: float
    pages: list[dict[str, Any]]
    top_issues: list[str]


def _extract_meta_content(html: str, name: str) -> str | None:
    for pattern in (
        rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\'](?P<content>[^"\']*)["\']',
        rf'<meta[^>]+content=["\'](?P<content>[^"\']*)["\'][^>]+name=["\']{re.escape(name)}["\']',
    ):
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            return m.group("content").strip()
    return None


def _audit_file(html_path: Path) -> PageSEO:
    content = html_path.read_text(errors="replace")
    issues: list[str] = []

    # Title
    title_m = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
    title = title_m.group(1).strip() if title_m else None
    title_len = len(title) if title else 0
    title_ok = TITLE_MIN <= title_len <= TITLE_MAX
    if not title:
        issues.append("Missing <title>")
    elif not title_ok:
        issues.append(f"Title length {title_len} chars (ideal {TITLE_MIN}–{TITLE_MAX})")

    # Meta description
    description = _extract_meta_content(content, "description")
    desc_len = len(description) if description else 0
    desc_ok = DESC_MIN <= desc_len <= DESC_MAX
    if not description:
        issues.append("Missing meta description")
    elif not desc_ok:
        issues.append(f"Description length {desc_len} chars (ideal {DESC_MIN}–{DESC_MAX})")

    # Canonical
    canonical = bool(re.search(r'<link[^>]+rel=["\']canonical["\']', content, re.IGNORECASE))
    if not canonical:
        issues.append("Missing canonical link tag")

    # H1
    h1_count = len(re.findall(r"<h1[\s>]", content, re.IGNORECASE))
    h1_ok = h1_count == 1
    if h1_count == 0:
        issues.append("No <h1> tag found")
    elif h1_count > 1:
        issues.append(f"Multiple <h1> tags ({h1_count})")

    # Images without alt
    imgs = re.findall(r"<img[^>]*>", content, re.IGNORECASE)
    imgs_no_alt = sum(
        1 for img in imgs
        if not re.search(r'alt=["\'][^"\']+["\']', img, re.IGNORECASE)
    )
    if imgs_no_alt:
        issues.append(f"{imgs_no_alt} image(s) missing alt text")

    # Open Graph
    og_title = bool(re.search(r'property=["\']og:title["\']', content, re.IGNORECASE))
    og_desc = bool(re.search(r'property=["\']og:description["\']', content, re.IGNORECASE))
    og_img = bool(re.search(r'property=["\']og:image["\']', content, re.IGNORECASE))
    if not og_title:
        issues.append("Missing og:title")
    if not og_desc:
        issues.append("Missing og:description")
    if not og_img:
        issues.append("Missing og:image")

    checks = [bool(title), title_ok, bool(description), desc_ok,
              canonical, h1_ok, imgs_no_alt == 0, og_title, og_desc, og_img]
    score = int(sum(checks) / len(checks) * 100)

    return PageSEO(
        file=html_path.name,
        title=title, title_length=title_len, title_ok=title_ok,
        description=description, description_length=desc_len, description_ok=desc_ok,
        canonical_present=canonical,
        h1_count=h1_count, h1_ok=h1_ok,
        img_without_alt=imgs_no_alt,
        og_title=og_title, og_description=og_desc, og_image=og_img,
        score=score, issues=issues,
    )


def run() -> SEOReport:
    html_files = sorted(ROOT.glob("*.html"))
    pages = [_audit_file(f) for f in html_files]

    avg_score = round(sum(p.score for p in pages) / max(len(pages), 1), 1)

    issue_counts: dict[str, int] = {}
    for p in pages:
        for issue in p.issues:
            key = re.sub(r"\d+", "N", issue)
            issue_counts[key] = issue_counts.get(key, 0) + 1
    top_issues = [
        f"{v}x — {k}"
        for k, v in sorted(issue_counts.items(), key=lambda x: -x[1])[:10]
    ]

    report = SEOReport(
        run_utc=datetime.now(timezone.utc).isoformat(),
        files_audited=len(pages),
        average_score=avg_score,
        pages=[asdict(p) for p in pages],
        top_issues=top_issues,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "seo_report.json").write_text(json.dumps(asdict(report), indent=2))

    md: list[str] = [
        "# SEO Optimization Report",
        "",
        f"**Run:** {report.run_utc}",
        f"**Average Score:** {avg_score}/100",
        f"**Files Audited:** {len(pages)}",
        "",
        "## Page Scores",
        "",
        "| File | Score | Issues |",
        "|------|-------|--------|",
    ]
    for p in sorted(pages, key=lambda x: x.score):
        md.append(f"| `{p.file}` | {p.score}/100 | {len(p.issues)} |")

    if top_issues:
        md += ["", "## Top Issues Across All Pages", ""]
        for issue in top_issues:
            md.append(f"- {issue}")

    (OUTPUT_DIR / "seo_report.md").write_text("\n".join(md))
    return report


def main() -> None:
    report = run()
    print(f"SEO Audit: {report.files_audited} pages, avg score {report.average_score}/100")
    if report.top_issues:
        print("Top issues:")
        for issue in report.top_issues[:5]:
            print(f"  {issue}")


if __name__ == "__main__":
    main()
