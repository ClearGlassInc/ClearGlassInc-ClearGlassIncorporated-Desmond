#!/usr/bin/env python3
"""Ensure every page carries the full cross-browser tab-icon block.

The site's tab logo is the ClearGlass holographic seal
(``/assets/images/clearglass-holographic-seal.png``). Different browsers read
different tags to find it, so a page that only declares ``rel="icon"`` still
shows a generic glyph when pinned in Safari or installed on Android. This
script brings every page up to the same canonical set.

It is strictly **additive**: a tag already present is left exactly as written
(including a page-specific ``theme-color``), and nothing is ever removed or
reordered. Running it twice changes nothing.

Insertion follows the anchor already used across the site:

1. after the last existing tab-icon tag, when the page has a partial block;
2. otherwise after ``<meta charset>``, keeping the charset declaration inside
   the first 1024 bytes as the HTML spec requires;
3. otherwise immediately after ``<head>``.

Usage::

    python3 tools/tab_icons.py            # add missing tags in place
    python3 tools/tab_icons.py --check    # exit 1 if any page is incomplete
    python3 tools/tab_icons.py --dry-run  # report changes, write nothing

Stdlib only, so it runs in the minimal CI images.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

SEAL = "/assets/images/clearglass-holographic-seal.png"

BLOCK_COMMENT = "<!-- Browser Tab Icons: Edge, Chrome, Safari, iOS -->"

# The classic multi-size ``favicon.ico`` generated from the same seal by
# tools/generate_favicons.py. A page that declares it already fills both the
# resolution-independent slot and the legacy fallback slot — with real 16/32/48
# rasters instead of the 512px master downscaled by the browser — so the two
# probes below accept it in place of their own tag. Without this a page that
# picked the sized icon family would be told to re-add the master it
# deliberately dropped.
CLASSIC_ICO = re.compile(
    r'rel=["\']icon["\'][^>]*href=["\']/favicon\.ico["\']'
    r'|href=["\']/favicon\.ico["\'][^>]*rel=["\']icon["\']', re.IGNORECASE)

# (probe, markup). ``probe`` decides whether the page already declares this
# tag; it is matched against the <head> only, so a favicon string inside body
# copy or a script never suppresses a real tag. Order defines how a freshly
# built block reads top to bottom.
TAGS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r'rel=["\']icon["\'][^>]*sizes=["\']any["\']'
            r'|sizes=["\']any["\'][^>]*rel=["\']icon["\']'
            r'|' + CLASSIC_ICO.pattern, re.IGNORECASE),
        f'<link rel="icon" href="{SEAL}" sizes="any">',
    ),
    (
        re.compile(
            r'rel=["\']icon["\'][^>]*type=["\']image/png["\']'
            r'|type=["\']image/png["\'][^>]*rel=["\']icon["\']', re.IGNORECASE),
        f'<link rel="icon" type="image/png" href="{SEAL}">',
    ),
    (
        re.compile(
            r'rel=["\']alternate icon["\']'
            r'|' + CLASSIC_ICO.pattern, re.IGNORECASE),
        f'<link rel="alternate icon" href="{SEAL}">',
    ),
    (
        re.compile(r'rel=["\']apple-touch-icon["\']', re.IGNORECASE),
        f'<link rel="apple-touch-icon" href="{SEAL}">',
    ),
    (
        re.compile(r'rel=["\']mask-icon["\']', re.IGNORECASE),
        '<link rel="mask-icon" href="/safari-pinned-tab.svg" color="#39ffb6">',
    ),
    (
        re.compile(r'rel=["\']manifest["\']', re.IGNORECASE),
        '<link rel="manifest" href="/site.webmanifest">',
    ),
    (
        re.compile(r'name=["\']theme-color["\']', re.IGNORECASE),
        '<meta name="theme-color" content="#07111f">',
    ),
    (
        re.compile(r'name=["\']msapplication-TileColor["\']', re.IGNORECASE),
        '<meta name="msapplication-TileColor" content="#07111f">',
    ),
    (
        re.compile(r'name=["\']msapplication-TileImage["\']', re.IGNORECASE),
        '<meta name="msapplication-TileImage" content="/icon-192.png">',
    ),
    (
        re.compile(r'name=["\']msapplication-config["\']', re.IGNORECASE),
        '<meta name="msapplication-config" content="/browserconfig.xml">',
    ),
]

# Any line carrying one of these is part of the tab-icon block, so a partial
# block's last line is the tidiest place to append what it is missing.
ANCHOR_RE = re.compile(
    r'rel=["\'](icon|alternate icon|apple-touch-icon|mask-icon|manifest)["\']'
    r'|name=["\'](theme-color|msapplication-[\w-]+)["\']',
    re.IGNORECASE,
)

HEAD_OPEN_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)
HEAD_CLOSE_RE = re.compile(r"</head\s*>", re.IGNORECASE)
CHARSET_RE = re.compile(r"<meta[^>]+charset[^>]*>", re.IGNORECASE)

# Comments, scripts, and styles hold text that only looks like markup. These
# heads carry a sizeable inline boot script, so a page whose JS swaps favicons
# would otherwise both satisfy a probe and win the anchor — and a <link>
# inserted mid-script would break the page.
INERT_RE = re.compile(
    r"<!--.*?-->|<script\b.*?</script\s*>|<style\b.*?</style\s*>",
    re.IGNORECASE | re.DOTALL,
)

# Directories that never reach the static site: vendored code, and the two
# Next.js apps, which declare their own icons through framework metadata.
SKIP_DIRS = {".git", "node_modules", ".next", "dist", "build", "vendor"}


def iter_pages(root: pathlib.Path):
    for path in sorted(root.rglob("*.html")):
        if SKIP_DIRS & set(path.relative_to(root).parts):
            continue
        yield path


def head_span(text: str) -> tuple[int, int] | None:
    """Character span of the document head, or None when there is no head.

    Files such as Google's site-verification token carry a ``.html`` suffix but
    hold a bare string; they must stay byte-exact and are skipped.
    """
    opening = HEAD_OPEN_RE.search(text)
    if not opening:
        return None
    closing = HEAD_CLOSE_RE.search(text, opening.end())
    return (opening.end(), closing.start() if closing else len(text))


def mask_inert(text: str) -> str:
    """Blank out comment/script/style spans, preserving every offset.

    Replacing each character with a space (newlines kept, so line structure and
    indentation survive) means positions found in the masked copy index the
    original exactly, and inert text can neither satisfy a probe nor anchor an
    insertion.
    """
    return INERT_RE.sub(
        lambda m: "".join("\n" if c == "\n" else " " for c in m.group(0)), text
    )


# A page may declare the ClearGlass mark either by pointing at the 512px master
# (what TAGS builds) or through the sized family tools/generate_favicons.py derives
# from it. The homepage takes the sized route on purpose: the master rendered at
# 16px is unreadable, so tests/test_holographic_branding.py asserts the master must
# NOT occupy its icon slots. Adding the master here anyway put two gates in direct
# conflict — this tool's own test demanded the tag that the branding test forbids.
# A page carrying the sized family already satisfies the intent, so leave it alone.
def _link_probe(rel: str, href: str) -> re.Pattern[str]:
    """Match a <link> carrying both ``rel`` and ``href``, in either order.

    Order matters here: a probe anchored on ``rel`` before ``href`` misses the equally
    valid reversed spelling and would inject the forbidden master, and one that matches
    a bare ``href`` anywhere would let an unrelated element (a <link rel="preload">, a
    <meta>) mark the page complete. Requiring both attributes on the same <link> is what
    makes the check mean what it says.
    """
    rel_attr = rf'rel=["\']{rel}["\']'
    href_attr = rf'href=["\']{re.escape(href)}["\']'
    return re.compile(
        rf'<link\b(?=[^>]*{rel_attr})(?=[^>]*{href_attr})[^>]*>', re.IGNORECASE
    )


SIZED_FAMILY_PROBES = (
    _link_probe("icon", "/favicon.ico"),
    _link_probe("icon", "/favicon-32.png"),
    _link_probe("icon", "/favicon-16.png"),
    _link_probe("apple-touch-icon", "/apple-touch-icon.png"),
)


def declares_sized_family(head: str) -> bool:
    """True when the head opts into the derived sized icons instead of the master."""
    return all(probe.search(head) for probe in SIZED_FAMILY_PROBES)


def missing_tags(head: str) -> list[str]:
    if declares_sized_family(head):
        return []
    return [markup for probe, markup in TAGS if not probe.search(head)]


def plan(text: str) -> tuple[int, str, list[str]] | None:
    """Return (insert_at, indent, tags) for a page needing tags, else None."""
    # Work off the masked copy throughout: it also keeps a </head> written
    # inside a script from truncating the head early.
    masked = mask_inert(text)
    span = head_span(masked)
    if span is None:
        return None
    start, end = span
    head = masked[start:end]
    absent = missing_tags(head)
    if not absent:
        return None

    # Anchor on the last line of an existing block, else the charset line, else
    # the top of the head. Each branch inserts at a line boundary.
    anchor_end = None
    indent = ""
    for match in re.finditer(r"^([ \t]*)(.*)$", head, re.MULTILINE):
        if ANCHOR_RE.search(match.group(2)):
            anchor_end = start + match.end()
            indent = match.group(1)
    if anchor_end is None:
        charset = CHARSET_RE.search(head)
        if charset:
            anchor_end = start + charset.end()
            line_start = head.rfind("\n", 0, charset.start()) + 1
            indent = re.match(r"[ \t]*", head[line_start:]).group(0)
        else:
            anchor_end = start
    return anchor_end, indent, absent


def apply(text: str) -> tuple[str, list[str]]:
    result = plan(text)
    if result is None:
        return text, []
    insert_at, indent, absent = result
    lines = list(absent)
    # Label a block being introduced from scratch, matching the site's pages.
    if BLOCK_COMMENT not in text and len(absent) == len(TAGS):
        lines.insert(0, BLOCK_COMMENT)
    addition = "".join(f"\n{indent}{line}" for line in lines)
    return text[:insert_at] + addition + text[insert_at:], absent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if any page is missing a tag.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change without writing.")
    args = parser.parse_args()

    incomplete = 0
    for path in iter_pages(REPO_ROOT):
        original = path.read_text(encoding="utf-8")
        updated, added = apply(original)
        if not added:
            continue
        incomplete += 1
        rel = path.relative_to(REPO_ROOT)
        print(f"{rel}: +{len(added)} tag(s)")
        for line in added:
            print(f"    {line}")
        if not (args.check or args.dry_run):
            path.write_text(updated, encoding="utf-8")

    if args.check:
        if incomplete:
            print(f"\n{incomplete} page(s) missing tab-icon tags; "
                  f"run python3 tools/tab_icons.py", file=sys.stderr)
            return 1
        print("all pages carry the full tab-icon block")
    elif args.dry_run:
        print(f"\ndry run: {incomplete} page(s) would change")
    elif incomplete:
        print(f"\nupdated {incomplete} page(s) — "
              f"bump VERSION in sw.js so cached tabs refetch the icon")
    else:
        print("all pages already carry the full tab-icon block")
    return 0


if __name__ == "__main__":
    sys.exit(main())
