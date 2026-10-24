"""Ten noindex prototype pages must not scroll sideways on phones.

The owner decided on 2026-10-23 to keep these pages, keep them out of the
index, and fix their mobile overflow. Measured in Chromium phone emulation
(isMobile, 320-430px): each page's document was wider than the screen, by
2px (shield g01) to 477px (revenue OS v2). Each fix targets the layout cause
found by hiding subtrees until the overflow disappeared:

- grids with columns only from md/lg up, whose implicit `auto` column (or an
  unprefixed col-span-N label) took the min-content of a child
- flex items that kept `min-width: auto` (range inputs, a truncated path)
- headers that are one fixed-height nowrap row, or a shrink-0 brand block
- long unbroken strings, and a HUD frame that clipped nothing because it was
  not positioned

None of them hides overflow on html/body: the brief rules that out.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# page -> declarations that carry the fix
FIXES = {
    "clearGlass-revenue-os-v2.html": ("grid-template-columns: minmax(0, 1fr)", "grid-column: 1 / -1"),
    "ClearGlass-Ops-Dashboard.html": ("input[type=range].flex-1 { min-width: 0; }",),
    "Fantasy-Pool-Dashboard.html": ("flex-wrap: wrap",),
    "Gridshield-Ontario-V3-Ics.html": ("header.h-\\[60px\\] { flex-wrap: wrap; height: auto",),
    "Gridshield-V7-Ultra-Formal.html": ("header.h-\\[72px\\] > .shrink-0 { flex-shrink: 1; min-width: 0; }",),
    "Orelogic-V4-Ultra-Beyond.html": ("#root > .h-screen.w-screen.overflow-hidden { position: relative; }",),
    "clearglass_x5f_rescue_x5f_draft_x5f_landing.html": ("overflow-wrap: anywhere",),
    "clearglass_x5f_shield_x5f_g01_x5f_verified.html": ("grid-template-columns: minmax(0, 1fr)", "min-width: 0"),
    "header-mockup-2040.html": (".brand, .wordmark { min-width: 0; }", "white-space: normal"),
    "shield_x5f_nexus_x5f_live_x5f_all.html": ("flex-wrap: wrap",),
}

ROBOTS = re.compile(r"<meta\b(?=[^>]*\bname=[\"']robots[\"'])[^>]*\bcontent=[\"']([^\"']*)[\"']", re.I)


def _block(html: str) -> str:
    match = re.search(r'<style id="cg-mobile-fit">(.*?)</style>', html, re.S)
    assert match, "cg-mobile-fit block missing"
    return match.group(1)


def test_each_prototype_carries_its_mobile_fit() -> None:
    for page, needles in FIXES.items():
        block = _block((ROOT / page).read_text(encoding="utf-8"))
        for needle in needles:
            assert needle in block, f"{page}: {needle}"


def test_fixes_do_not_hide_overflow() -> None:
    for page in FIXES:
        block = _block((ROOT / page).read_text(encoding="utf-8"))
        assert "overflow-x" not in block and "overflow: hidden" not in block, page
        assert not re.search(r"(^|[\s,}])(html|body)\s*[{,]", block), page


def test_prototypes_stay_noindex() -> None:
    for page in FIXES:
        match = ROBOTS.search((ROOT / page).read_text(encoding="utf-8"))
        assert match and "noindex" in match.group(1).lower(), page


def test_fit_block_sits_before_the_shared_layers() -> None:
    # Page CSS, then the fix, then the shared layers tools/shared_layers.py adds.
    for page in FIXES:
        html = (ROOT / page).read_text(encoding="utf-8")
        fit = html.index('id="cg-mobile-fit"')
        layer = html.find('href="/assets/css/future-buttons.css"')
        assert layer == -1 or fit < layer, page
        assert fit < html.index("</head>"), page
