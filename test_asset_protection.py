from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "asset-protection.js").read_text(encoding="utf-8")


def test_protection_is_opt_in_and_does_not_disable_global_selection() -> None:
    assert "[data-cg-protected]" in SCRIPT
    assert "document.body.style.userSelect" not in SCRIPT
    assert 'closest("input,textarea,select,[contenteditable=true]")' in SCRIPT


def test_watermark_is_non_interactive_and_print_persistent() -> None:
    assert "[data-cg-watermark]::after" in SCRIPT
    assert "pointer-events:none" in SCRIPT
    assert "@media print" in SCRIPT


def test_asset_protection_remains_idempotent() -> None:
    assert "if (window.__cgAssetProtection) return" in SCRIPT
    assert 'getElementById("cg-asset-protection-styles")' in SCRIPT


def test_class_based_watermark_is_available_without_selection_blocking() -> None:
    assert ".protected,.protected *" not in SCRIPT
    assert ".protected-watermark::after" in SCRIPT
    assert "ClearGlassInc. • Confidential • © 2026" in SCRIPT
    assert ".blur-preview:hover,.blur-preview:focus-within" in SCRIPT
    assert "prefers-reduced-motion:reduce" in SCRIPT


def test_shortcuts_are_not_intercepted_and_session_token_is_random() -> None:
    assert '["c", "u", "s", "p"].indexOf(key)' not in SCRIPT
    assert 'document.addEventListener("keydown"' not in SCRIPT
    assert 'meta[name="session-watermark"]' in SCRIPT
    assert "window.crypto.getRandomValues" in SCRIPT


def test_page_specific_licence_and_provenance_metadata_are_published() -> None:
    assert 'link[rel="canonical"]' in SCRIPT
    assert 'license.href = "/legal/content-policy.html"' in SCRIPT
    assert 'provenance.href = "/provenance/release-manifest.json"' in SCRIPT


def test_sensitive_previews_blur_on_exit_and_inactivity() -> None:
    assert 'querySelectorAll("[data-cg-sensitive]")' in SCRIPT
    assert 'addEventListener("blur"' in SCRIPT
    assert "45000" in SCRIPT
    assert ".cg-sensitive-obscured" in SCRIPT


def test_copy_friction_is_limited_to_opt_in_regions() -> None:
    assert 'addEventListener("copy"' in SCRIPT
    assert 'addEventListener("cut"' in SCRIPT
    assert "closestProtected(e.target) && !isEditable(e.target)" in SCRIPT
