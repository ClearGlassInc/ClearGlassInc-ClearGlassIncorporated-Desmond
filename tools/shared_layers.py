#!/usr/bin/env python3
"""Ensure every deployable page loads the site's shared front-end layers.

Two layers ship on every page and are asserted site-wide by the test suite:

* the future-glass button enhancement — ``/assets/css/future-buttons.css`` and
  ``/assets/js/future-buttons.js``, each referenced exactly once
  (``tests/test_future_buttons.py``);
* the ClearGlass corner badge — ``/logo-badge.js``, the shared proof that a
  page carries the brand mark (``tests/test_site_health_bot.py``).

Both were pasted in by hand, so pages added outside the site pipeline shipped
without them: nine pages had drifted on all three files when this script was
written. The invariants are mechanical, so a generator enforces them the way
``tab_icons.py`` and ``internal_links.py`` enforce theirs.

It is strictly **additive** and idempotent. A page that already satisfies a
layer is left byte-identical; stylesheets go immediately before ``</head>``
and scripts immediately before ``</body>``, matching placement on the pages
that already carry them. Running it twice changes nothing.

The badge is only added to a page carrying *no* brand mark at all: the
homepage proves its mark with a direct ``clearglass-logo`` image instead, and
that hero is left alone. This mirrors ``bots.site_health_bot._page_has_logo``.

Usage::

    python3 tools/shared_layers.py            # add missing references in place
    python3 tools/shared_layers.py --check    # exit 1 if any page is missing one
    python3 tools/shared_layers.py --dry-run  # report changes, write nothing

Stdlib only, so it runs in the minimal CI images.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Mirrors tests/test_future_buttons.py::deployable_html_pages and
# bots.site_health_bot.IGNORED_HTML_DIRS.
SKIP_DIRS = {".git", ".next", "node_modules", "vendor"}

HEAD_CLOSE_RE = re.compile(r"</head\s*>", re.IGNORECASE)
BODY_CLOSE_RE = re.compile(r"</body\s*>", re.IGNORECASE)

# A layer is (name, markers proving it is present, tag to add, where to add it).
# `markers` is a tuple because a layer can be satisfied more than one way: the
# badge is equally satisfied by a direct logo image.
LAYERS: tuple[tuple[str, tuple[str, ...], str, re.Pattern[str]], ...] = (
    (
        "future-buttons.css",
        ("/assets/css/future-buttons.css",),
        '<link rel="stylesheet" href="/assets/css/future-buttons.css">',
        HEAD_CLOSE_RE,
    ),
    (
        "future-buttons.js",
        ("/assets/js/future-buttons.js",),
        '<script defer src="/assets/js/future-buttons.js"></script>',
        BODY_CLOSE_RE,
    ),
    (
        "logo-badge.js",
        ("logo-badge.js", "clearglass-logo"),
        '<script defer src="/logo-badge.js"></script>',
        BODY_CLOSE_RE,
    ),
)

# Layers whose reference must appear exactly once, so a duplicate is a defect
# in its own right. The badge is exempt: `clearglass-logo` legitimately recurs
# on pages that show the mark in both a nav and a footer.
SINGLETON_LAYERS = {"future-buttons.css", "future-buttons.js"}


def iter_pages(root: pathlib.Path):
    for path in sorted(root.rglob("*.html")):
        if SKIP_DIRS & set(path.relative_to(root).parts):
            continue
        yield path


def is_deployable(text: str) -> bool:
    """A page ships only if it closes both a head and a body.

    Fragments and bare-string files carrying a ``.html`` suffix (Google's
    site-verification token, for one) must stay byte-exact — and that token is
    the site's sole legitimate logo exemption for exactly this reason.
    """
    return bool(HEAD_CLOSE_RE.search(text) and BODY_CLOSE_RE.search(text))


def insert_before(text: str, pattern: re.Pattern[str], tag: str) -> str:
    """Insert ``tag`` on its own line immediately before ``pattern``.

    The closing tag's own indentation is reused so the addition reads as if it
    had always been there.
    """
    match = pattern.search(text)
    if match is None:  # pragma: no cover - guarded by is_deployable
        return text
    line_start = text.rfind("\n", 0, match.start()) + 1
    indent = re.match(r"[ \t]*", text[line_start:match.start()]).group(0)
    return f"{text[:line_start]}{indent}{tag}\n{text[line_start:]}"


def apply(text: str) -> tuple[str, list[str]]:
    """Return the page with any missing layer added, plus the tags added."""
    if not is_deployable(text):
        return text, []

    added: list[str] = []
    for _name, markers, tag, anchor in LAYERS:
        if any(marker in text for marker in markers):
            continue
        text = insert_before(text, anchor, tag)
        added.append(tag)
    return text, added


def duplicates(text: str) -> list[str]:
    """Singleton references appearing more than once — never auto-corrected.

    De-duplicating markup automatically risks deleting a page-specific tag, so
    these are reported for a human instead.
    """
    return [
        markers[0]
        for name, markers, _tag, _anchor in LAYERS
        if name in SINGLETON_LAYERS and text.count(markers[0]) > 1
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if any page is missing a layer.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change without writing.")
    args = parser.parse_args()

    incomplete = 0
    duplicated = 0
    for path in iter_pages(REPO_ROOT):
        original = path.read_text(encoding="utf-8")
        if not is_deployable(original):
            continue
        rel = path.relative_to(REPO_ROOT)

        for href in duplicates(original):
            duplicated += 1
            print(f"{rel}: {href} referenced more than once", file=sys.stderr)

        updated, added = apply(original)
        if not added:
            continue
        incomplete += 1
        print(f"{rel}: +{len(added)} tag(s)")
        for line in added:
            print(f"    {line}")
        if not (args.check or args.dry_run):
            path.write_text(updated, encoding="utf-8")

    if duplicated:
        print(f"\n{duplicated} duplicate reference(s) need a human; "
              f"nothing was removed automatically", file=sys.stderr)

    if args.check:
        if incomplete or duplicated:
            print(f"\n{incomplete} page(s) missing a shared layer; "
                  f"run python3 tools/shared_layers.py", file=sys.stderr)
            return 1
        print("all deployable pages carry every shared layer")
    elif args.dry_run:
        print(f"\ndry run: {incomplete} page(s) would change")
    elif incomplete:
        print(f"\nupdated {incomplete} page(s) — "
              f"bump VERSION in sw.js so cached tabs refetch the layers")
    else:
        print("all deployable pages already carry every shared layer")
    return 1 if duplicated else 0


if __name__ == "__main__":
    raise SystemExit(main())
