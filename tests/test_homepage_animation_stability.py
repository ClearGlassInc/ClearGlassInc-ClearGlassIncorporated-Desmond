from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_homepage_reveal_observer_has_failsafe_and_zero_threshold() -> None:
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "threshold:0" in homepage
    assert "threshold:.1" not in homepage
    assert "classList.add('vis')" in homepage
    assert "prefers-reduced-motion: reduce" in homepage
    assert ".rv{opacity:1!important" in homepage or ".rv{opacity:1 !important" in homepage
    assert "rvSweep" in homepage
    assert "setTimeout(function(){rvEls.forEach(revealRv);},4000)" in homepage


def test_homepage_cursor_glow_uses_compositor_transform() -> None:
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "transition:left .5s ease,top .5s ease" not in homepage
    assert "will-change:transform" in homepage
    assert "translate3d(" in homepage
    assert "glow.style.left=e.clientX" not in homepage
    assert "paintGlow" in homepage


def test_design_system_does_not_double_hide_rv_nodes() -> None:
    core = (ROOT / "assets/js/cg-design-system-core.js").read_text(encoding="utf-8")
    assert "t.classList.contains('rv')" in core
    assert "classList.contains('rv')) continue" in core or "classList.contains('rv') ||" in core
    assert "glow.style.left = x + 'px'" not in core
    assert "translate3d(" in core


def test_service_worker_cache_bumped_for_motion_assets() -> None:
    sw = (ROOT / "sw.js").read_text(encoding="utf-8")
    assert 'VERSION = "cg-v52"' in sw
