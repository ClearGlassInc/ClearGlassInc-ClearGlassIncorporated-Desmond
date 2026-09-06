from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_homepage_loads_sentinel_assets_and_three_presentation_modes() -> None:
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'href="sentinel.css"' in homepage
    assert 'src="sentinel.js"' in homepage
    assert 'class="sentinel-hero"' in homepage
    assert 'id="sentinelLauncher"' in homepage
    assert 'id="sentinelShell"' in homepage
    assert 'role="dialog"' in homepage and 'aria-modal="true"' in homepage


def test_sentinel_discloses_limits_and_protects_sensitive_information() -> None:
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "sentinel.js").read_text(encoding="utf-8")
    assert "Sentinel is an automated, rule-guided website concierge—not a human" in homepage
    assert "require authenticated, explicitly authorized workspaces" in homepage
    assert "Do not share passwords, API keys" in homepage
    assert "cannot access systems" in script
    assert "Nothing has been submitted" in script
    assert "copy.textContent=text" in script


def test_sentinel_exposes_required_project_pathways() -> None:
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    for prompt in ("I need a high-performance website.", "I want more qualified leads.", "I need AI automation.", "I need a secure customer portal.", "I need cybersecurity guidance.", "I need cloud deployment help.", "I want a full digital growth system."):
        assert prompt in homepage
