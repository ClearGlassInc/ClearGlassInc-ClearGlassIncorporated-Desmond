from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "blog" / "clearglassinc-artemis-palantir-self-evolving-ai-intelligence-platform.html"


def test_artemis_blueprint_loads_neon_progressive_enhancement() -> None:
    html = PAGE.read_text(encoding="utf-8")

    assert 'href="artemis-neon.css"' in html
    assert 'src="artemis-neon.js"' in html
    assert 'data-power-state="active"' in html
    assert 'aria-label="Preview interface energy state"' in html
    assert html.count('data-power-select=') == 5


def test_neon_motion_and_interaction_remain_accessible() -> None:
    css = (ROOT / "blog" / "artemis-neon.css").read_text(encoding="utf-8")
    javascript = (ROOT / "blog" / "artemis-neon.js").read_text(encoding="utf-8")

    assert "@media(prefers-reduced-motion:reduce)" in css
    assert ".power-state:focus-visible" in css
    assert 'setAttribute("aria-pressed"' in javascript
    assert "Object.hasOwn(descriptions, state)" in javascript
