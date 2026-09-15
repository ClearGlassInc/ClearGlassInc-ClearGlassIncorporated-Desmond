#!/usr/bin/env python3
"""Wire the shared article enhancement layer into every ClearGlass blog article.

The blog grew one article at a time, so the advanced reading features were
attached inconsistently: only some articles carried ``insights.css`` /
``insights.js``, and only some were tagged ``data-ix-page="article"`` — which is
the flag ``insights.js`` checks before it builds the table of contents, heading
anchors, share/cite/save row and related-brief rail. This script brings every
article up to the same baseline.

It is idempotent and additive:

* it never removes or reorders existing markup,
* it never edits the generated ``<!-- cg-related -->`` blocks,
* it only adds an attribute, a stylesheet link, or a script tag when the file
  does not already have it.

Run from the repository root::

    python3 tools/article_enhance_wire.py            # apply
    python3 tools/article_enhance_wire.py --check    # report only, exit 1 if stale
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

BLOG = pathlib.Path(__file__).resolve().parent.parent / "blog"

# The hub runs its own layer; the resume builder is a tool shell, not a brief.
SKIP = {"index.html", "resume-builder.html"}

CSS_LINKS = ('<link rel="stylesheet" href="insights.css"/>',
             '<link rel="stylesheet" href="article-enhance.css"/>')

# article-enhance.js must load BEFORE insights.js: it creates the .endbar and
# #ixRelated mount points that insights.js then fills. Both are deferred, so
# document order is execution order.
ENHANCE_JS = '<script defer src="article-enhance.js"></script>'
INSIGHTS_JS = '<script defer src="insights.js"></script>'


def slug_for(path: pathlib.Path) -> str:
    return path.stem


def ensure_body_attrs(html: str, slug: str) -> tuple[str, list[str]]:
    """Give <body> the data-ix-page / data-ix-slug flags insights.js needs."""
    notes: list[str] = []
    m = re.search(r"<body\b([^>]*)>", html, re.I)
    if not m:
        return html, notes
    attrs = m.group(1)
    new = attrs

    if "data-ix-page" not in attrs:
        new += ' data-ix-page="article"'
        notes.append("data-ix-page")
    if "data-ix-slug" not in attrs:
        new += f' data-ix-slug="{slug}"'
        notes.append("data-ix-slug")

    if new != attrs:
        html = html[: m.start()] + f"<body{new}>" + html[m.end():]
    return html, notes


def ensure_head_css(html: str) -> tuple[str, list[str]]:
    """Add the stylesheets just before </head>, preserving whatever is there."""
    notes: list[str] = []
    missing = [link for link in CSS_LINKS
               if re.search(r'href="[^"]*' + re.escape(link.split('href="')[1].split('"')[0]) + r'"', html) is None]
    if not missing:
        return html, notes

    idx = html.lower().find("</head>")
    if idx == -1:
        return html, notes

    block = "\n" + "\n".join(missing) + "\n"
    html = html[:idx] + block + html[idx:]
    notes.extend(link.split('href="')[1].split('"')[0] for link in missing)
    return html, notes


def ensure_scripts(html: str) -> tuple[str, list[str]]:
    """Ensure article-enhance.js runs, and runs ahead of insights.js."""
    notes: list[str] = []
    has_enhance = "article-enhance.js" in html
    insights = re.search(r'<script[^>]*src="insights\.js"[^>]*>\s*</script>', html, re.I)

    if not has_enhance:
        if insights:
            # slot it immediately before the existing insights.js tag
            html = html[: insights.start()] + ENHANCE_JS + "\n" + html[insights.start():]
            notes.append("article-enhance.js (before insights.js)")
        else:
            idx = html.lower().rfind("</body>")
            if idx == -1:
                return html, notes
            html = html[:idx] + ENHANCE_JS + "\n" + INSIGHTS_JS + "\n" + html[idx:]
            notes.append("article-enhance.js + insights.js")
            return html, notes

    if not insights and "insights.js" not in html:
        idx = html.lower().rfind("</body>")
        if idx != -1:
            html = html[:idx] + INSIGHTS_JS + "\n" + html[idx:]
            notes.append("insights.js")

    return html, notes


def process(path: pathlib.Path, apply: bool) -> list[str]:
    original = path.read_text(encoding="utf-8")
    html = original
    notes: list[str] = []

    html, n = ensure_body_attrs(html, slug_for(path))
    notes += n
    html, n = ensure_head_css(html)
    notes += n
    html, n = ensure_scripts(html)
    notes += n

    if notes and apply:
        path.write_text(html, encoding="utf-8")
    return notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="report what is missing without writing; exit 1 if any file is stale")
    args = ap.parse_args()

    files = sorted(p for p in BLOG.glob("*.html") if p.name not in SKIP)
    stale = 0
    for path in files:
        notes = process(path, apply=not args.check)
        if notes:
            stale += 1
            verb = "needs" if args.check else "wired"
            print(f"{verb}: {path.name} -> {', '.join(notes)}")

    total = len(files)
    if args.check:
        print(f"\n{total - stale}/{total} articles already carry the enhancement layer.")
        return 1 if stale else 0
    print(f"\n{stale} article(s) updated; {total} checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
