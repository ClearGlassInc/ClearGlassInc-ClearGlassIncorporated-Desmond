"""Contract tests for the Visual Engine's in-content instruments.

The instruments (assets/cg-visual/instruments/) put motion on top of static,
readable figures on the homepage: an evidence chain, a simulated sensor scope
and the interface's own telemetry. These tests pin what must stay true when
someone edits them later: they are honest about what they show, they cannot
make network calls or claim live intelligence, they never animate anything
but transform and opacity, and the evidence chain never shows execution
before human approval.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VISUAL = ROOT / "assets" / "cg-visual"
INDEX = ROOT / "index.html"
CSS = VISUAL / "cg-instruments.css"
BOOT = VISUAL / "cg-instruments.js"
MODULES = sorted((VISUAL / "instruments").glob("*.js")) + [BOOT, VISUAL / "core" / "cadence.js"]


def _instrument_markup(html: str) -> list[str]:
    """Every <figure data-cg-instrument=...> block on the page."""
    return re.findall(r"<figure[^>]*data-cg-instrument=\"[a-z]+\".*?</figure>", html, re.S)


def test_homepage_loads_the_layer_once_with_css_in_head() -> None:
    html = INDEX.read_text(encoding="utf-8")
    head = html.split("</head>", 1)[0]
    # In <head>: the figures sit mid-page, so a late stylesheet would reflow them (CLS).
    assert head.count('href="/assets/cg-visual/cg-instruments.css"') == 1
    assert html.count('href="/assets/cg-visual/cg-instruments.css"') == 1
    assert html.count('<script type="module" src="/assets/cg-visual/cg-instruments.js"></script>') == 1


def test_every_instrument_on_the_page_has_a_module() -> None:
    html = INDEX.read_text(encoding="utf-8")
    boot = BOOT.read_text(encoding="utf-8")
    kinds = set(re.findall(r'data-cg-instrument="([a-z]+)"', html))
    assert kinds == {"chain", "radar", "telemetry"}
    for kind in kinds:
        assert f"import('./instruments/{kind}.js')" in boot
        assert (VISUAL / "instruments" / f"{kind}.js").is_file()


def test_figures_label_what_they_are() -> None:
    figures = _instrument_markup(INDEX.read_text(encoding="utf-8"))
    assert len(figures) == 3
    by_kind = {re.search(r'data-cg-instrument="([a-z]+)"', f).group(1): f for f in figures}
    assert "not a live feed" in by_kind["chain"]
    assert "nothing on this page is connected to a live system" in by_kind["chain"]
    assert "Simulated" in by_kind["radar"] and "example signals" in by_kind["radar"]
    assert "No real system is being observed" in by_kind["radar"]
    assert "own state" in by_kind["telemetry"]
    assert "None of them measures anything outside the page" in by_kind["telemetry"]
    for figure in figures:
        labelled_by = re.search(r'aria-labelledby="([^"]+)"', figure).group(1)
        assert f'id="{labelled_by}"' in figure


def test_no_fabricated_intelligence_in_instruments() -> None:
    forbidden = re.compile(
        r"live threat|threat detected|active attack|government signal|real-time surveillance|"
        r"live security incident|breach detected",
        re.I,
    )
    for text in _instrument_markup(INDEX.read_text(encoding="utf-8")):
        assert not forbidden.search(text), text[:120]
    for path in MODULES:
        assert not forbidden.search(path.read_text(encoding="utf-8")), path
    scheduler = (VISUAL / "instruments" / "scheduler.js").read_text(encoding="utf-8")
    # Only benign event types reach the engine; alert/anomaly would read as threats.
    assert "new Set(['signal', 'provenance', 'telemetry'])" in scheduler
    for path in MODULES:
        source = path.read_text(encoding="utf-8")
        assert "type: 'alert'" not in source and "type: 'anomaly'" not in source, path


def test_instruments_make_no_network_calls_and_run_no_dynamic_code() -> None:
    banned = ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon",
              "eval(", "new Function", "innerHTML", "document.write")
    for path in MODULES:
        source = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in source, f"{path.name}: {token}"
        for url in re.findall(r"https?://[^\s'\"]+", source):
            assert url == "http://www.w3.org/2000/svg", f"{path.name}: {url}"


def test_keyframes_animate_only_transform_and_opacity() -> None:
    css = CSS.read_text(encoding="utf-8")
    keyframes = re.findall(r"@keyframes\s+[\w-]+\s*\{(.*?)\}\s*$", css, re.M)
    assert len(keyframes) >= 4
    for body in keyframes:
        for prop in re.findall(r"([a-z-]+)\s*:", body):
            assert prop in {"transform", "opacity"}, prop


def test_motion_safety_states_are_present() -> None:
    css = CSS.read_text(encoding="utf-8")
    for contract in (
        "@media (prefers-reduced-motion: reduce)",
        'html[data-cgm-motion="reduced"]',
        "@media (forced-colors: active)",
        "@media print",
        ".cg-instrument--static",
        "aspect-ratio",
    ):
        assert contract in css, contract
    scheduler = (VISUAL / "instruments" / "scheduler.js").read_text(encoding="utf-8")
    for contract in ("IntersectionObserver", "visibilitychange", "data-cgm-motion",
                     "cgm-motion-preference", "cancelAnimationFrame", "pagehide"):
        assert contract in scheduler, contract


def test_evidence_chain_never_shows_execution_before_approval() -> None:
    chain = next(f for f in _instrument_markup(INDEX.read_text(encoding="utf-8"))
                 if 'data-cg-instrument="chain"' in f)
    stages = re.findall(r"<li class=\"cg-chain__stage\"([^>]*)>.*?<b>([^<]+)</b>", chain, re.S)
    names = [name for _attrs, name in stages]
    assert names == ["Analysis", "Draft", "Risk score", "Human approval", "Execution", "Ledger"]
    gates = [name for attrs, name in stages if "data-gate" in attrs]
    assert gates == ["Human approval"]


def test_telemetry_cells_are_ones_the_module_fills() -> None:
    html = INDEX.read_text(encoding="utf-8")
    module = (VISUAL / "instruments" / "telemetry.js").read_text(encoding="utf-8")
    keys = set(re.findall(r'data-cg-tel="([a-z]+)"', html))
    assert keys == {"motion", "tier", "renderer", "signals"}
    for key in keys:
        assert f"write('{key}'" in module, key


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_cadence_node_suite_passes() -> None:
    result = subprocess.run(
        ["node", "--test", str(VISUAL / "tests" / "cadence.test.mjs")],
        capture_output=True, text=True, timeout=120, cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
