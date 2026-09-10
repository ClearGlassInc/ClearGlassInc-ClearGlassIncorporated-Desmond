"""Contract tests for the additive future-glass button enhancement."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "assets/css/future-buttons.css"
JS_PATH = ROOT / "assets/js/future-buttons.js"
EXCLUDED_PARTS = {".git", "node_modules", "vendor"}


def deployable_html_pages() -> list[Path]:
    pages = []
    for path in ROOT.rglob("*.html"):
        if EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts):
            continue
        markup = path.read_text(encoding="utf-8")
        if "</head>" in markup.lower() and "</body>" in markup.lower():
            pages.append(path)
    return pages


def test_every_deployable_page_loads_enhancement_once() -> None:
    pages = deployable_html_pages()
    assert pages
    for page in pages:
        markup = page.read_text(encoding="utf-8")
        assert markup.count('/assets/css/future-buttons.css') == 1, page
        assert markup.count('/assets/js/future-buttons.js') == 1, page


def test_service_worker_precaches_the_shared_layer() -> None:
    worker = (ROOT / "sw.js").read_text(encoding="utf-8")
    assert '"/assets/css/future-buttons.css"' in worker
    assert '"/assets/js/future-buttons.js"' in worker


def test_discovery_is_limited_to_control_semantics() -> None:
    script = JS_PATH.read_text(encoding="utf-8")
    expected_selectors = (
        '"button"', '".btn"', '".cta"', '"[role=\'button\']"',
        '"input[type=\'submit\']"', '"a.button"', '"a.btn"',
    )
    for selector in expected_selectors:
        assert selector in script
    assert '"a"' not in script.split("].join", 1)[0]
    assert "MutationObserver" in script
    assert "IntersectionObserver" in script
    assert "requestAnimationFrame" in script


def test_accessibility_and_motion_safety_contracts() -> None:
    stylesheet = CSS_PATH.read_text(encoding="utf-8")
    script = JS_PATH.read_text(encoding="utf-8")
    for contract in (
        ":focus-visible",
        "prefers-reduced-motion: reduce",
        "forced-colors: active",
        '[aria-busy="true"]',
        '[aria-disabled="true"]',
        "min-width: 44px",
        "min-height: 44px",
    ):
        assert contract in stylesheet
    assert "stopImmediatePropagation" in script
    assert "data-no-future-glass" in script


def test_visual_state_variants_are_available() -> None:
    stylesheet = CSS_PATH.read_text(encoding="utf-8")
    for selector in (
        ".btn--primary-future",
        ".btn--glass-secondary",
        ".btn--glass-ghost",
        ".btn--glass-danger",
        '[data-future-state="success"]',
        '[data-future-state="error"]',
    ):
        assert selector in stylesheet
