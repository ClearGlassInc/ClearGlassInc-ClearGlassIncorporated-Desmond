"""Contract tests for the additive neon pulse command-centre layer."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "assets/css/neon-pulse.css"
JS_PATH = ROOT / "assets/js/neon-pulse.js"
EXCLUDED_PARTS = {".git", ".next", "node_modules", "vendor"}


def deployable_html_pages() -> list[Path]:
    """Same discovery as tests/test_future_buttons.py and tools/shared_layers.py."""
    pages = []
    for path in ROOT.rglob("*.html"):
        if EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts):
            continue
        markup = path.read_text(encoding="utf-8").lower()
        if "</head>" in markup and "</body>" in markup:
            pages.append(path)
    return pages


def test_every_deployable_page_loads_layer_once() -> None:
    pages = deployable_html_pages()
    assert pages
    for page in pages:
        markup = page.read_text(encoding="utf-8")
        assert markup.count("/assets/css/neon-pulse.css") == 1, page
        assert markup.count("/assets/js/neon-pulse.js") == 1, page


def test_service_worker_precaches_the_layer() -> None:
    worker = (ROOT / "sw.js").read_text(encoding="utf-8")
    assert '"/assets/css/neon-pulse.css"' in worker
    assert '"/assets/js/neon-pulse.js"' in worker


def test_keyframes_animate_only_transform_and_opacity() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    keyframes = re.findall(r"@keyframes\s+[\w-]+\s*\{(.*?)\}\s*$", css, re.M)
    assert keyframes
    for body in keyframes:
        for prop in re.findall(r"([a-z-]+)\s*:", body):
            assert prop in {"transform", "opacity"}, prop


def test_motion_and_accessibility_safety_contracts() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    script = JS_PATH.read_text(encoding="utf-8")
    for contract in (
        "prefers-reduced-motion: reduce",
        "forced-colors: active",
        "pointer-events: none",
        "@media print",
    ):
        assert contract in css
    assert 'setAttribute("aria-hidden", "true")' in script
    # Discovery never overrides page-owned pseudo-elements or positioning.
    assert 'free(el, "::after")' in script
    assert 'free(el, "::before")' in script
    assert 'style.position !== "static"' in script
    assert "data-no-neon" in script
    assert "IntersectionObserver" in script
    assert "MAX_FRAMES" in script and "MAX_BEACONS" in script
    # Status dots that already animate keep their own animation.
    assert 'style.animationName !== "none"' in script
    # Decoration only: no event handling that could swallow clicks.
    assert "preventDefault" not in script
    assert "stopPropagation" not in script


# Pseudo-elements this layer may style without discovery having claimed them:
# the future-glass ring (same shared-layer family) and the opt-in authored
# indicators, whose pseudo-element exists only because an author opted in.
UNCLAIMED_PSEUDO_ALLOWED = (
    ".future-glass-control.future-glass-layers",
    ".cg-np-status",
    ".cg-np-mission-ready",
)


def _selectors(css: str) -> list[str]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@keyframes[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)
    out = []
    for prelude in re.findall(r"([^{}]+)\{", css):
        prelude = prelude.strip()
        if prelude.startswith("@") or prelude.startswith(":root"):
            continue
        out.extend(part.strip() for part in prelude.split(","))
    return out


def test_pseudo_elements_are_only_styled_once_claimed() -> None:
    """A page's own ::before/::after (and their animations) are never touched."""
    for selector in _selectors(CSS_PATH.read_text(encoding="utf-8")):
        if selector.startswith(UNCLAIMED_PSEUDO_ALLOWED):
            continue
        if selector.endswith("::after"):
            assert ".cg-np-own-a" in selector, selector
        if selector.endswith("::before"):
            assert ".cg-np-own-b" in selector, selector


def test_classes_do_not_collide_with_existing_site_layers() -> None:
    """ui.css ships .cg-neon-card and clearglass-nexus.html ships .cg-status."""
    css = CSS_PATH.read_text(encoding="utf-8")
    script = JS_PATH.read_text(encoding="utf-8")
    classes = set(re.findall(r"\.(-?[_a-zA-Z][\w-]*)", re.sub(r"/\*.*?\*/", "", css, flags=re.S)))
    own = {c for c in classes if not c.startswith("future-glass")}
    assert own and all(c.startswith("cg-np-") for c in own), sorted(own)
    for foreign in ("cg-neon-card", "cg-status", "cg-sentinel-module", "cg-mission-ready"):
        assert f'"{foreign}"' not in script


def test_status_and_opt_in_classes_are_available() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    for selector in (
        ".cg-np-status--online",
        ".cg-np-status--monitoring",
        ".cg-np-status--alert",
        ".cg-np-status--intel",
        ".cg-np-beacon--online",
        ".cg-np-beacon--monitoring",
        ".cg-np-beacon--alert",
        ".cg-np-beacon--intel",
        ".cg-np-mission-ready",
        ".cg-np-scanbar",
    ):
        assert selector in css
