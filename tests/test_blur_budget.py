"""products.html and side-store.html must not stack backdrop blurs inside blurred surfaces.

Measured in Chromium on main (80be3a9) as DOM elements whose computed
backdrop-filter is not `none`: products.html 596, side-store.html 464.
297 of products.html's 300 blurred buttons and 335 of side-store.html's 336 sat
inside an ancestor that already blurs its backdrop. An element with a
backdrop-filter is a backdrop root, so a nested control only re-blurs its
parent's own surface: the cost is paid for no visible change.

- products.html: glass.css blurs every [class*="-card"], and by substring each
  card's .pc-card-top and .pc-card-actions too; future-buttons.css blurs every
  control. Five stacked blurs per card, 94 cards, under a ~95% opaque surface.
- side-store.html: the 80 product cards keep their blur (their glass is
  translucent: it is the look); the 4 controls inside each card no longer
  repeat it.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _rule(css: str, selector_start: str) -> str:
    match = re.search(re.escape(selector_start) + r"[^{]*\{([^}]*)\}", css)
    assert match, selector_start
    return match.group(1)


def test_products_cards_and_their_controls_do_not_blur() -> None:
    css = (ROOT / "assets/css/product-command-center.css").read_text(encoding="utf-8")
    body = _rule(css, ".pc-card,.pc-card-top,.pc-card-actions,.pc-card .future-glass-control")
    # glass.css declares its card blur !important, so the reset must be too.
    assert "backdrop-filter:none!important" in body
    assert "-webkit-backdrop-filter:none!important" in body
    rule = re.search(r"\.pc-card,\.pc-card-top[^{]*\{", css).group(0)
    for part in (".pc-command .future-glass-control", ".pc-collections .future-glass-control"):
        assert part in rule


def test_side_store_keeps_card_glass_but_not_nested_control_blur() -> None:
    html = (ROOT / "side-store.html").read_text(encoding="utf-8")
    card = re.search(r"\.st-card\{background:var\(--st-glass\)[^}]*\}", html)
    assert card and "backdrop-filter:blur(" in card.group(0), "the cards' own glass must stay"
    body = _rule(html, ".st-card .future-glass-control,")
    assert "backdrop-filter:none" in body


def test_reset_rules_change_nothing_but_backdrop_filter() -> None:
    css = (ROOT / "assets/css/product-command-center.css").read_text(encoding="utf-8")
    html = (ROOT / "side-store.html").read_text(encoding="utf-8")
    for body in (_rule(css, ".pc-card,.pc-card-top,.pc-card-actions"), _rule(html, ".st-card .future-glass-control,")):
        props = {p.split(":")[0].strip() for p in body.split(";") if p.strip()}
        assert props == {"-webkit-backdrop-filter", "backdrop-filter"}, props
