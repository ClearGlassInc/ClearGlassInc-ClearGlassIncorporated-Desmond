"""Contract tests for the site-wide lighting and motion system.

The layers below load on every deployable page (neon-pulse, future-buttons,
buttons) or on most of them (cg-design-system on 133, ui.css on 39). A
keyframe that animates layout or paint there costs every visitor on every
frame, and a pulse that blinks or races reads as a fault, not a signal.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED_LAYERS = [
    ROOT / "assets/css/neon-pulse.css",
    ROOT / "assets/css/future-buttons.css",
    ROOT / "assets/css/cg-design-system.css",
    ROOT / "ui.css",
]
NEON = ROOT / "assets/css/neon-pulse.css"
DESIGN = ROOT / "assets/css/cg-design-system.css"
CORE_JS = ROOT / "assets/js/cg-design-system-core.js"
NEON_JS = ROOT / "assets/js/neon-pulse.js"

LAYOUT_PROPS = re.compile(
    r"^(top|right|bottom|left|width|height|inset|margin(-\w+)?|padding(-\w+)?|"
    r"font-size|line-height|border(-\w+)*-width)$"
)
PAINT_PROPS = {"box-shadow", "filter", "text-shadow", "background-position", "background-size"}


def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _keyframes(css: str) -> dict[str, str]:
    css = _strip_comments(css)
    out = {}
    for match in re.finditer(r"@keyframes\s+([\w-]+)\s*\{", css):
        depth, i = 1, match.end()
        while depth and i < len(css):
            depth += {"{": 1, "}": -1}.get(css[i], 0)
            i += 1
        out[match.group(1)] = css[match.end():i - 1]
    return out


def _props(body: str) -> set[str]:
    return set(re.findall(r"([a-z-]+)\s*:", re.sub(r"var\([^)]*\)", "", body)))


def test_shared_layers_never_animate_layout() -> None:
    for path in SHARED_LAYERS:
        for name, body in _keyframes(path.read_text(encoding="utf-8")).items():
            bad = {p for p in _props(body) if LAYOUT_PROPS.match(p)}
            assert not bad, f"{path.name} @keyframes {name} animates layout: {sorted(bad)}"


def test_design_system_keyframes_are_composited() -> None:
    """The 133-page layer animates only transform/translate/scale/rotate/opacity,
    except the opt-in crystal CTA gradient, which is one small element."""
    allowed_paint = {"cgCrystalShift"}
    for name, body in _keyframes(DESIGN.read_text(encoding="utf-8")).items():
        if name in allowed_paint:
            continue
        bad = _props(body) & PAINT_PROPS
        assert not bad, f"@keyframes {name} repaints every frame: {sorted(bad)}"


def _opacities(body: str) -> list[float]:
    return [float(v) for v in re.findall(r"opacity\s*:\s*([\d.]+)", body)]


def test_pulses_breathe_instead_of_blinking() -> None:
    """A pulse dips to at least 55% of its own peak (target 60%)."""
    pulses = {
        NEON: ("cg-np-glow-pulse", "cg-np-status-pulse", "cg-np-bg-pulse"),
        DESIGN: ("cgPulse", "cgNeonEdge", "cgTbEdge"),
        ROOT / "ui.css": ("cg-neon-breathe", "cg-neon-shimmer", "cg-signal-pulse", "smb-status-pulse"),
        ROOT / "clearglass-motion.css": ("cgm-breathe",),
    }
    for path, names in pulses.items():
        frames = _keyframes(path.read_text(encoding="utf-8"))
        for name in names:
            values = _opacities(frames[name])
            assert len(values) >= 2, (path.name, name)
            assert min(values) / max(values) >= 0.55, (path.name, name, values)


def test_pulse_tempo_tokens_stay_calm() -> None:
    css = NEON.read_text(encoding="utf-8")
    for token, low, high in (
        ("--cg-np-pulse", 2.0, 4.0),
        ("--cg-np-pulse-status", 2.0, 4.0),
        ("--cg-np-pulse-alert", 2.0, 4.0),
        ("--cg-np-breath", 6.0, 12.0),
    ):
        value = float(re.search(rf"{token}:\s*([\d.]+)s;", css).group(1))
        assert low <= value <= high, (token, value)
    # The fast stepped "process" flicker and the 1.1s hover pulse are gone.
    frames = _keyframes(css)
    assert "cg-np-process" not in frames and "cg-np-ring-hot" not in frames


def test_shared_keyframes_and_tokens_exist() -> None:
    css = NEON.read_text(encoding="utf-8")
    frames = _keyframes(css)
    for name in ("cg-np-glow-pulse", "cg-np-status-pulse", "cg-np-reveal-up", "cg-np-bg-pulse"):
        assert name in frames, name
    for token in (
        "--cg-np-glow-near", "--cg-np-glow-far", "--cg-np-glow-blur-near", "--cg-np-glow-blur-far",
        "--cg-np-reveal-dur", "--cg-np-reveal-shift", "--cg-np-stagger",
    ):
        assert token + ":" in css, token
    # The entrance settles on the element's own resting state: no end frame.
    assert "to" not in re.findall(r"\b(from|to)\b", frames["cg-np-reveal-up"])


def test_button_rings_pulse_on_primary_actions_only() -> None:
    css = _strip_comments(NEON.read_text(encoding="utf-8"))
    for prelude, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if "future-glass" in prelude and "animation:" in body and "none" not in body:
            assert "future-glass-primary" in prelude, prelude.strip()


def test_hover_never_retimes_an_infinite_animation() -> None:
    """Changing animation-duration mid-cycle jumps the animation to a new point."""
    for path in (ROOT / "buttons.css", NEON):
        css = _strip_comments(path.read_text(encoding="utf-8"))
        for prelude, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            if ":hover" in prelude:
                assert "animation-duration" not in body, (path.name, prelude.strip())


def test_reveal_is_one_animation_that_cannot_strand_content() -> None:
    css = _strip_comments(DESIGN.read_text(encoding="utf-8"))
    hidden = re.search(r"\.cg-rv:not\(\.cg-vis\)\s*\{([^}]*)\}", css).group(1)
    assert "opacity: 0" in hidden and "translate3d" in hidden
    shown = re.search(r"\.cg-rv\.cg-vis\s*\{([^}]*)\}", css).group(1)
    assert "cgRevealUp" in shown and "backwards" in shown and "--cg-rv-i" in shown
    # It must not fight the element's own hover transitions.
    assert not re.search(r"\.cg-rv[^{]*\{[^}]*transition\s*:", css.split("@media")[0])
    script = CORE_JS.read_text(encoding="utf-8")
    assert "FOREIGN_REVEAL" in script and "[data-cgm-reveal]" in script
    assert "animationName !== 'none'" in script
    assert "--cg-rv-i" in script and "STAGGER_MAX" in script
    assert "addEventListener('change'" in script
    # Reduced motion and print always resolve to visible content.
    for block in re.findall(r"@media[^{]*(?:reduce|print)[^{]*\{(.*?)\n\}", css, re.DOTALL):
        if ".cg-rv" in block:
            assert "opacity: 1 !important" in block or "opacity:1!important" in block


def test_one_atmosphere_and_one_rim_per_element() -> None:
    script = NEON_JS.read_text(encoding="utf-8")
    assert "function rimmed(el)" in script and "if (rimmed(el))" in script
    assert "atmosphereOwned()" in script
    for owner in ("#cg-command-atmosphere", ".cgm-atmos", ".cg-fx-neon-grid", "cg-design-system"):
        assert owner in script, owner
    assert "body:has(> .cg-fx-neon-grid) > .cg-np-ambient" in DESIGN.read_text(encoding="utf-8")


def test_cursor_glow_moves_by_transform() -> None:
    script = CORE_JS.read_text(encoding="utf-8")
    assert "glow.style.left" not in script and "glow.style.top" not in script
    assert "--cg-cx" in script
    css = _strip_comments(DESIGN.read_text(encoding="utf-8"))
    cursor = re.search(r"\.cg-fx-cursor\s*\{([^}]*)\}", css).group(1)
    assert "transition: transform" in cursor and "left .45s" not in cursor
