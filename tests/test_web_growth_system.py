from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_growth_experience_is_additive_and_wired() -> None:
    page = (ROOT / "web-design.html").read_text(encoding="utf-8")
    assert 'id="growth-system"' in page
    assert 'href="web-growth-system.css"' in page
    assert 'src="web-growth-system.js"' in page
    assert 'id="showcase"' in page  # legacy content remains intact
    assert "cg-related:start" in page  # generated internal links remain intact


def test_requested_claim_safe_content_and_fallbacks_are_present() -> None:
    page = (ROOT / "web-design.html").read_text(encoding="utf-8")
    required = (
        "System Readiness Scan",
        "Growth Infrastructure Digital Twin",
        "ClearGlass Intelligence Layer",
        "Experience Laboratory",
        "Illustrative interface. Not live customer data.",
        "Demo — not live data",
        "Disable AI processing for this workspace",
        "educational starting point, not a guaranteed diagnosis",
        "<noscript>",
    )
    for text in required:
        assert text in page


def test_production_sensitive_features_default_to_disabled() -> None:
    script = (ROOT / "web-growth-system.js").read_text(encoding="utf-8")
    for flag in (
        "ENABLE_WEBGPU_VISUALS",
        "ENABLE_AI_DEMO",
        "ENABLE_EXPERIMENT_LAB",
        "ENABLE_ANALYTICS",
        "ENABLE_LEAD_CAPTURE",
    ):
        assert f"{flag}: false" in script
    assert "fetch(" not in script
    assert "localStorage" not in script


def test_accessibility_and_motion_controls_are_present() -> None:
    page = (ROOT / "web-design.html").read_text(encoding="utf-8")
    css = (ROOT / "web-growth-system.css").read_text(encoding="utf-8")
    assert 'aria-live="polite"' in page
    assert 'aria-pressed="true"' in page
    assert ":focus-visible" in css
    assert "prefers-reduced-motion:reduce" in css
    assert "forced-colors:active" in css
