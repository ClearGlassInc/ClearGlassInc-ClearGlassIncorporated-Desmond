"""Decorative light layers sit behind the glass, never on top of it.

stealth-glass.js's #cg-neon-aura (a red edge glow with a 340px corner bloom,
pulsing on a 6s cycle) and ui.css's #cg-spotlight (a red glow that follows the
pointer) were both fixed at z-index 2147483000. That put them above every page
layer: the Sentinel command center's panels, map, topbar (1200), drawer (1300)
and toasts (1400), so the "neon light" tinted the interface instead of sitting
behind it, and the aura's bloom pulsed behind the Sentinel Core dock in the
bottom-right corner of every page. Both now share the ambient layer that
neon-pulse.css gives .cg-np-ambient (z-index -1, below all content).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _rule(text: str, selector: str) -> str:
    """Body of the first rule whose selector is exactly `selector`."""
    match = re.search(r"(?<![\w-])" + re.escape(selector) + r"\s*\{([^}]*)\}", text)
    assert match, f"no rule for {selector}"
    return match.group(1)


def _z_index(declarations: str) -> int:
    match = re.search(r"z-index\s*:\s*(-?\d+)", declarations)
    assert match, "rule sets no z-index"
    return int(match.group(1))


def test_neon_aura_paints_behind_content() -> None:
    js = (ROOT / "stealth-glass.js").read_text(encoding="utf-8")
    rule = _rule(js, "#cg-neon-aura")
    assert _z_index(rule) < 0, "the aura must sit below panels, controls and the Sentinel Core dock"
    assert "pointer-events:none" in rule
    # No permanent full-viewport compositor layer; the animation promotes it while it runs.
    assert "will-change" not in rule


def test_neon_aura_respects_opt_out_phones_and_forced_colors() -> None:
    js = (ROOT / "stealth-glass.js").read_text(encoding="utf-8")
    assert "[data-no-neon] #cg-neon-aura{display:none}" in js
    assert "@media(max-width:720px),(pointer:coarse){#cg-neon-aura{animation:none;opacity:.8}}" in js
    assert "@media (forced-colors:active),print{#cg-neon-aura{display:none}}" in js
    assert "@media (prefers-reduced-motion:reduce){#cg-neon-aura{animation:none;opacity:.8}" in js


def test_pointer_spotlight_paints_behind_content() -> None:
    css = (ROOT / "ui.css").read_text(encoding="utf-8")
    rule = _rule(css, "#cg-spotlight")
    assert _z_index(rule) < 0, "the pointer spotlight must not tint what is under the cursor"
    assert "pointer-events: none" in rule
