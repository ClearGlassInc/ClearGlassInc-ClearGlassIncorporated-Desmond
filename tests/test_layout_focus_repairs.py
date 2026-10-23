"""Regression guards for layout and focus defects found by the 2026-10-23 CSS audit.

Each was reproduced in headless Chromium before it was fixed:

* threads.html grew to 968px wide at a 375px viewport: an implicit `auto`
  grid track sized itself to 125-134 character UTM URLs and file paths.
* project-board.html overflowed at 400px and below: the topbar is a nowrap
  flex row whose 44px actions no longer fit beside the title.
* clearglass-nexus.html and ClearGlass-NEXUS-v12-FINAL.html parked the closed
  ARIA panel off-screen with a transform only, so its 16 controls stayed in
  the keyboard tab order while invisible.
* The nav CTA inside .nav-links rendered muted grey on crimson (3.22:1):
  `html .nav-links a` out-specified `html .nav-cta` in clearglass-crimson.css.
* The Control Surface bar (control-surface.js), fixed top-right, covered the
  page's own header controls on 12 of the 35 pages that load it ("Contact →",
  "Kill switch", back links), so they could not be clicked.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _rule(css: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match, selector
    return match.group(1)


def test_threads_cards_cannot_widen_the_page() -> None:
    html = (ROOT / "threads.html").read_text(encoding="utf-8")
    assert "grid-template-columns: minmax(0, 1fr)" in _rule(html, ".grid")
    assert "overflow-wrap: anywhere" in _rule(html, ".card")


def test_project_board_topbar_wraps_only_where_it_overflowed() -> None:
    css = (ROOT / "project-board.css").read_text(encoding="utf-8")
    block = re.search(r"@media \(max-width: 409px\)\s*\{(.*?)\n\}", css, re.S)
    assert block, "narrow-screen topbar breakpoint missing"
    assert "flex-wrap: wrap" in block.group(1)
    # Wider layouts keep the original single-row topbar.
    assert "flex-wrap" not in _rule(css, ".pb-topbar")


def test_closed_aria_panel_is_out_of_the_tab_order() -> None:
    for page in ("clearglass-nexus.html", "ClearGlass-NEXUS-v12-FINAL.html"):
        html = (ROOT / page).read_text(encoding="utf-8")
        closed = _rule(html, "#aria")
        opened = _rule(html, "#aria.on")
        assert "visibility:hidden" in closed, page
        # Hidden only after the .38s slide-out, so closing still animates.
        assert "visibility 0s linear .38s" in closed, page
        assert "visibility:visible" in opened, page


def test_nav_cta_outranks_generic_nav_link_colour() -> None:
    css = (ROOT / "clearglass-crimson.css").read_text(encoding="utf-8")
    rest = re.search(r"html \.nav-links a\.nav-cta\s*\{([^}]*)\}", css)
    assert rest, "a.nav-cta selector inside .nav-links is required to beat `html .nav-links a`"
    assert "color: #fff !important" in rest.group(1)
    assert "html .nav-links a.nav-cta:hover" in css
    assert "html .nav-links a.nav-cta:focus-visible" in css


def test_control_surface_steps_clear_of_page_controls() -> None:
    js = (ROOT / "control-surface.js").read_text(encoding="utf-8")
    assert "function clearPageControls(bar)" in js
    assert "clearPageControls(bar);" in js
    # Re-fit on resize and once layout settles, never on scroll.
    assert 'addEventListener("resize"' in js and 'addEventListener("load"' in js
    # A placement only replaces the original when it covers strictly fewer controls.
    assert "c.count < best.count" in js
    # tabindex=-1 landmarks (e.g. main#main-content) must not count as controls.
    assert '[tabindex]:not([tabindex="-1"])' in js
