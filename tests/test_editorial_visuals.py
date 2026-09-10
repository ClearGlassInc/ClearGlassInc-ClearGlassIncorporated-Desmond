from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "cyber-defense-console.html": "municipal-cyber-tabletop-concept.webp",
    "advanced-features-tools-systems.html": "laptop-system-decomposition-concept.webp",
    "revenue-engine.html": "marketing-command-center-concept.webp",
    "button-lab.html": "verified-trust-layout-concept.webp",
}
BOOTSTRAPS = {
    "cyber-defense-console.html": "asset-protection.js",
    "advanced-features-tools-systems.html": "logo-badge.js",
    "revenue-engine.html": "logo-badge.js",
    "button-lab.html": "logo-badge.js",
}


def test_target_pages_load_the_governed_visual_module() -> None:
    badge = (ROOT / "logo-badge.js").read_text(encoding="utf-8")
    protection = (ROOT / "asset-protection.js").read_text(encoding="utf-8")
    module = (ROOT / "editorial-visuals.js").read_text(encoding="utf-8")

    assert 'script.src = "/editorial-visuals.js"' in badge
    assert 'script.src = "/editorial-visuals.js"' in protection
    assert 'last !== "cyber-defense-console.html"' in protection

    for page, bootstrap in BOOTSTRAPS.items():
        assert f'"{page}": {{' in module
        html = (ROOT / page).read_text(encoding="utf-8", errors="surrogateescape")
        assert bootstrap in html
        if bootstrap == "logo-badge.js":
            assert f'"{page}": true' in badge


def test_all_editorial_assets_exist_and_are_web_optimized() -> None:
    asset_root = ROOT / "assets" / "images" / "editorial"
    for filename in TARGETS.values():
        asset = asset_root / filename
        assert asset.is_file()
        assert asset.suffix == ".webp"
        assert asset.stat().st_size < 100_000


def test_unverified_claims_have_explicit_disclosures() -> None:
    module = (ROOT / "editorial-visuals.js").read_text(encoding="utf-8")

    required = (
        "not a report of an actual City of Burlington incident",
        "not repair, safety, or service documentation",
        "not certifications, affiliations, customers, or measured results",
        "not presented as a verified customer testimonial",
    )
    for disclosure in required:
        assert disclosure in module


def test_visuals_use_accessible_and_performance_safe_markup() -> None:
    module = (ROOT / "editorial-visuals.js").read_text(encoding="utf-8")

    assert 'section.setAttribute("aria-labelledby", "cgev-title")' in module
    assert 'links.setAttribute("aria-label", "Related ClearGlass resources")' in module
    assert 'image.loading = "lazy"' in module
    assert 'image.decoding = "async"' in module
    assert 'image.fetchPriority = "low"' in module
    assert "prefers-reduced-motion:reduce" in module


def test_module_activates_only_on_allowlisted_pages() -> None:
    badge = (ROOT / "logo-badge.js").read_text(encoding="utf-8")
    protection = (ROOT / "asset-protection.js").read_text(encoding="utf-8")
    module = (ROOT / "editorial-visuals.js").read_text(encoding="utf-8")

    assert "if (!EDITORIAL_TARGETS[last]" in badge
    assert 'last !== "cyber-defense-console.html"' in protection
    assert "var item = ITEMS[page];" in module
    assert "if (!item) return;" in module
