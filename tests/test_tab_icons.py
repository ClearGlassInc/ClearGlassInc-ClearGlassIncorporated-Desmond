# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""The tab-icon block must reach every page without ever rewriting one."""
from __future__ import annotations

import pathlib

from tools.tab_icons import (
    SEAL,
    TAGS,
    apply,
    head_span,
    iter_pages,
    mask_inert,
    missing_tags,
    plan,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

BARE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>t</title>
</head>
<body></body>
</html>
"""


def full_head(body: str = "") -> str:
    tags = "\n".join(markup for _, markup in TAGS)
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8"/>\n'
        f"{tags}\n</head>\n<body>{body}</body>\n</html>\n"
    )


# ── detection ─────────────────────────────────────────────────────────────────

def test_a_complete_head_is_left_alone():
    assert missing_tags(full_head()) == []
    assert plan(full_head()) is None


def test_a_bare_head_is_missing_every_tag():
    assert len(missing_tags(BARE)) == len(TAGS)


def test_probes_ignore_attribute_order():
    head = '<link href="/x.png" sizes="any" rel="icon">'
    assert TAGS[0][0].search(head)


def test_single_quotes_count_as_declared():
    assert TAGS[3][0].search("<link rel='apple-touch-icon' href='/x.png'>")


def test_the_classic_ico_fills_the_any_size_and_fallback_slots():
    """A page on the sized icon family is complete, not "missing" the master.

    tools/generate_favicons.py cuts favicon.ico from the same seal, so a head
    that declares it already covers the resolution-independent and legacy
    fallback slots — with real 16/32/48 rasters rather than the 512px master
    downscaled by the browser. Demanding the master back would undo that.
    """
    classic = (
        '<link rel="icon" href="/favicon.ico" sizes="16x16 32x32 48x48">\n'
        '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">\n'
        '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">\n'
        '<link rel="mask-icon" href="/safari-pinned-tab.svg" color="#39ffb6">\n'
        '<link rel="manifest" href="/site.webmanifest">\n'
        '<meta name="theme-color" content="#07111f">\n'
        '<meta name="msapplication-TileColor" content="#07111f">\n'
        '<meta name="msapplication-TileImage" content="/icon-192.png">\n'
        '<meta name="msapplication-config" content="/browserconfig.xml">'
    )
    page = BARE.replace("<title>t</title>", f"{classic}\n<title>t</title>")
    assert missing_tags(page) == []
    assert apply(page) == (page, [])


def test_a_head_with_no_icons_at_all_still_fails_the_gate():
    """Widening the two probes must not blunt the gate for a bare page."""
    assert len(missing_tags(BARE)) == len(TAGS)


def test_body_copy_does_not_suppress_a_real_tag():
    """Detection reads the <head> only, so prose never fakes a declaration."""
    page = BARE.replace("<body>", '<body>we set rel="mask-icon" on every page')
    _, added = apply(page)
    assert any("mask-icon" in tag for tag in added)


# ── inert spans ───────────────────────────────────────────────────────────────

SCRIPTED = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<script>
  var l = document.createElement("link");
  l.rel = "icon";
  l.setAttribute("rel", "apple-touch-icon");
</script>
<title>t</title>
</head>
<body></body>
</html>
"""


def test_masking_preserves_every_offset():
    masked = mask_inert(SCRIPTED)
    assert len(masked) == len(SCRIPTED)
    assert masked.count("\n") == SCRIPTED.count("\n")
    assert masked.index("<title>") == SCRIPTED.index("<title>")


def test_script_text_never_becomes_the_anchor():
    """A <link> inserted mid-script would break the page."""
    updated, added = apply(SCRIPTED)
    assert added
    script = updated[updated.index("<script>"):updated.index("</script>")]
    assert SEAL not in script
    # With the script inert there is no anchor, so the block takes the charset
    # fallback and lands ahead of the script rather than inside it.
    assert updated.index("charset") < updated.index(SEAL) < updated.index("<script>")
    # the script itself is passed through verbatim
    assert '  l.setAttribute("rel", "apple-touch-icon");' in updated


def test_script_text_does_not_satisfy_a_probe():
    _, added = apply(SCRIPTED)
    assert any("apple-touch-icon" in tag for tag in added)


def test_a_commented_out_tag_is_not_counted_as_present():
    page = BARE.replace(
        "<title>", '<!-- <link rel="mask-icon" href="/x.svg"> -->\n<title>'
    )
    updated, added = apply(page)
    assert any("mask-icon" in tag for tag in added)
    # the commented line survives untouched, and nothing is inserted inside it
    assert '<!-- <link rel="mask-icon" href="/x.svg"> -->' in updated


def test_a_head_close_inside_a_script_does_not_truncate_the_head():
    page = BARE.replace(
        "<title>t</title>", '<script>var s = "</head>";</script>\n<title>t</title>'
    )
    updated, _ = apply(page)
    assert updated.index(SEAL) < updated.index("<body>")
    assert '<script>var s = "</head>";</script>' in updated


# ── additive guarantee ────────────────────────────────────────────────────────

def test_nothing_is_ever_removed():
    updated, added = apply(BARE)
    assert added
    for line in BARE.splitlines():
        assert line in updated


def test_a_page_specific_theme_color_survives():
    page = BARE.replace(
        "<title>t</title>", '<meta name="theme-color" content="#05070d"/>\n<title>t</title>'
    )
    updated, added = apply(page)
    assert '<meta name="theme-color" content="#05070d"/>' in updated
    assert 'content="#07111f">' not in "".join(
        t for t in added if "theme-color" in t
    )


def test_an_existing_icon_href_is_not_rewritten():
    page = BARE.replace(
        "<title>", '<link rel="icon" type="image/png" href="/legacy.png">\n<title>'
    )
    updated, _ = apply(page)
    assert '<link rel="icon" type="image/png" href="/legacy.png">' in updated


def test_running_twice_changes_nothing():
    once, added = apply(BARE)
    assert added
    twice, again = apply(once)
    assert again == []
    assert twice == once


# ── placement ─────────────────────────────────────────────────────────────────

def test_charset_stays_ahead_of_the_block():
    updated, _ = apply(BARE)
    assert updated.index("charset") < updated.index(SEAL)


def test_charset_remains_inside_the_first_1024_bytes():
    updated, _ = apply(BARE)
    assert updated.encode("utf-8").index(b"charset") < 1024


def test_tags_are_appended_to_an_existing_block():
    page = BARE.replace(
        "<title>", '<link rel="apple-touch-icon" href="/x.png">\n<title>'
    )
    updated, _ = apply(page)
    anchor = updated.index('rel="apple-touch-icon"')
    assert updated.index('rel="mask-icon"') > anchor
    # …and stays above the rest of the head rather than drifting into <body>.
    assert updated.index('rel="mask-icon"') < updated.index("<title>")


def test_insertions_land_inside_the_head():
    updated, _ = apply(BARE)
    start, end = head_span(updated)
    assert start < updated.index(SEAL) < end


# ── files that are not pages ──────────────────────────────────────────────────

def test_a_headless_file_is_skipped():
    """Google's verification token is .html but must stay byte-exact."""
    token = "google-site-verification: 23RWyXWkoxqgArev8achU8IfVxYC5EIUAYBsuTYKLFM\n"
    assert head_span(token) is None
    updated, added = apply(token)
    assert (updated, added) == (token, [])


# ── the live site ─────────────────────────────────────────────────────────────

def test_every_page_in_the_repo_is_complete():
    incomplete = [
        str(p.relative_to(REPO_ROOT))
        for p in iter_pages(REPO_ROOT)
        if apply(p.read_text(encoding="utf-8"))[1]
    ]
    assert incomplete == [], f"run python3 tools/tab_icons.py: {incomplete}"


def test_the_seal_asset_the_tags_point_at_exists():
    assert (REPO_ROOT / SEAL.lstrip("/")).is_file()


def test_referenced_icon_assets_exist():
    for rel in ("safari-pinned-tab.svg", "site.webmanifest",
                "icon-192.png", "browserconfig.xml"):
        assert (REPO_ROOT / rel).is_file(), rel
