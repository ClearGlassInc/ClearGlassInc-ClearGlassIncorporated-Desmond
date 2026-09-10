from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_security_controls_share_a_fused_glass_dock() -> None:
    css = (ROOT / "security-stack-fusion.css").read_text(encoding="utf-8")
    aegis = (ROOT / "aegis-glass.js").read_text(encoding="utf-8")
    stealth = (ROOT / "stealth-glass.js").read_text(encoding="utf-8")

    assert "#cg-security-stack" in css
    assert "Aegis × Sentinel Fusion Dock" in css
    assert "display:flex" in css or "display: flex" in css
    assert "flex-direction:column" in css or "flex-direction: column" in css
    assert "justify-content:flex-end" in css or "justify-content: flex-end" in css
    assert "backdrop-filter:blur(34px)" in css or "backdrop-filter: blur(34px)" in css
    assert "securityStack.appendChild(status)" in aegis
    assert "securityStack.appendChild(stealthButton)" in aegis
    assert "stack.insertBefore(btn, stack.firstChild)" in stealth
    assert "cg-security-dock-mounted" in stealth


def test_security_pills_keep_standalone_fallbacks() -> None:
    css = (ROOT / "security-stack-fusion.css").read_text(encoding="utf-8")
    stealth = (ROOT / "stealth-glass.js").read_text(encoding="utf-8")

    assert "#cg-security-stack #cg-stealth-btn" in css
    assert "#cg-security-stack #aegis-glass-status" in css
    assert "--cg-security-bottom" in css
    assert "--cg-security-edge" in css
    assert "--cg-security-bottom,84px" in stealth
    assert "--cg-security-edge,18px" in stealth


def test_mobile_fusion_dock_reserves_control_lane_and_clears_content() -> None:
    css = (ROOT / "security-stack-fusion.css").read_text(encoding="utf-8")

    assert "--cg-mobile-fusion-right-lane:76px" in css or "--cg-mobile-fusion-right-lane: 76px" in css
    assert "--cg-mobile-fusion-clearance:92px" in css or "--cg-mobile-fusion-clearance: 92px" in css
    assert "body.cg-security-dock-mounted" in css
    assert "#cg-security-stack #aegis-glass-status{display:none!important}" in css
    assert "@media(max-width:720px)" in css
    assert "prefers-reduced-motion:reduce" in css


def test_scroll_controls_include_top_and_bottom_arrows() -> None:
    css = (ROOT / "fx.css").read_text(encoding="utf-8")
    js = (ROOT / "fx.js").read_text(encoding="utf-8")

    assert "#cg-top,#cg-bottom" in css
    assert "Scroll to bottom" in js
    assert "bottom.innerHTML = \"↓\"" in js
    assert "window.scrollTo({ top: max" in js
