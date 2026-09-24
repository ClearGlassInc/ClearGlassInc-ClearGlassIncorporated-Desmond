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
    assert 'freePseudo(el, "::after")' in script
    assert 'style.position === "static"' in script
    assert "data-no-neon" in script
    assert "IntersectionObserver" in script
    assert "MAX_ENHANCED" in script
    # Decoration only: no event handling that could swallow clicks.
    assert "preventDefault" not in script
    assert "stopPropagation" not in script


def test_status_and_opt_in_classes_are_available() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    for selector in (
        ".cg-status--online",
        ".cg-status--monitoring",
        ".cg-status--alert",
        ".cg-status--intel",
        ".cg-neon-card",
        ".cg-neon-panel",
        ".cg-sentinel-module",
        ".cg-mission-ready",
    ):
        assert selector in css
