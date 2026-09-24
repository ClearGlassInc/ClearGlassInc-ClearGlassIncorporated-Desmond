"""Sentinel Core: the homepage's single floating command console.

`station-chat.js` builds the dock, `sentinel.js` answers. These tests pin the
contract between them and the three ways the redesign could quietly regress:

* the floating widgets it absorbed pile back up in the corners on phones;
* a site-wide substring selector (`[class*="-panel"]` and friends, repainted
  with !important in clearglass-crimson.css and glass.css) catches one of the
  console's class names and turns it into a see-through card;
* a readout starts claiming telemetry this public console does not have.

Routing is checked by running sentinel.js's own matcher and pathway table in
Node, so a mission button can never land on the wrong answer unnoticed.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DOCK = (ROOT / "station-chat.js").read_text(encoding="utf-8")
SENTINEL = (ROOT / "sentinel.js").read_text(encoding="utf-8")
HOMEPAGE = (ROOT / "index.html").read_text(encoding="utf-8")


def test_dock_is_the_single_floating_control_surface() -> None:
    # Hidden, never removed: each original stays the source of truth.
    for selector in (
        "body.cg-station-mounted .sentinel-launcher",
        "body.cg-station-mounted #cg-top",
        "body.cg-station-mounted #cg-bottom",
        "body.cgst-has-tactical .cgm-motion-toggle",
        "body.cgst-absorb-stack #cg-security-stack",
    ):
        assert selector in DOCK, selector
    # Stealth Glass and Tactical View drive the original buttons.
    assert 'document.getElementById("cg-stealth-btn")' in DOCK
    assert 'document.querySelector("[data-cgm-motion-toggle]")' in DOCK
    # The stack is only absorbed when Stealth Glass is all it holds.
    assert 'el.id !== "cg-stealth-btn"' in DOCK


def test_console_class_names_escape_site_wide_substring_selectors() -> None:
    nets = ("-panel", "panel-", "-card", "card-", "-tile", "tile-", "kicker", "eyebrow",
            "footer", "btn", "button", "status-dot", "signal-dot", "icon", "scanline", "scan-line")
    names = set(re.findall(r"\bcgst-[a-z0-9-]+", DOCK))
    assert names, "no cgst- classes found"
    caught = sorted(n for n in names if any(net in n for net in nets))
    assert not caught, f"class names caught by a site-wide [class*=] net: {caught}"
    # future-buttons.js re-skins every <button> outside [data-no-future-glass].
    assert 'root.setAttribute("data-no-future-glass", "")' in DOCK


def test_every_console_destination_exists() -> None:
    hrefs = re.findall(r'href: "([^"]+)"', DOCK)
    assert len(hrefs) >= 8
    for href in hrefs:
        target = ROOT / href
        if href.endswith("/"):
            target = target / "index.html"
        assert target.is_file(), href


def test_dock_missions_are_sentinel_missions() -> None:
    dock_prompts = re.findall(r'prompt: "([^"]+)"', DOCK)
    match = re.search(r"var missions=(\[[^\]]*\]);", SENTINEL)
    assert match, "missions list missing from sentinel.js"
    assert dock_prompts == json.loads(match.group(1))
    assert len(dock_prompts) == 6


def test_dock_opens_the_conversation_not_the_directory() -> None:
    assert "window.__cgSentinel={open:" in SENTINEL
    assert "if(showChat)showChat();" in SENTINEL
    assert "api.ask(prompt)" in DOCK and "api.open()" in DOCK


def test_console_state_and_shortcuts_respect_the_visitor() -> None:
    # Only a visitor's own toggle is saved, under a key the old dock never auto-wrote.
    assert 'var STORE_OPEN = "cg-core-open";' in DOCK
    assert "if (persist) writeOpen(open);" in DOCK
    assert "setOpen(readOpen(), false, false);" in DOCK
    # Touch devices of any size start collapsed; the site menu is never covered.
    assert "(hover: none) and (pointer: coarse)" in DOCK
    assert "body.mobile-nav-open #cg-station" in DOCK
    # Alt+Shift+S never swallows Option/AltGr characters typed into a field.
    assert '(!editable && event.code === "KeyS")' in DOCK
    # The mode group ships hidden and is revealed only by the sentinel.js that wires it.
    assert 'aria-label="Input mode" hidden>' in HOMEPAGE
    assert 'var modes=scope.querySelector(".sentinel-modes");if(modes)modes.hidden=false;' in SENTINEL
    # A moved console is clamped with its sheet, and the collapsed pill is draggable.
    enhance = (ROOT / "station-enhance.js").read_text(encoding="utf-8")
    assert "function sheetAbove()" in enhance and 'addEventListener("cg-station:toggle", reclamp)' in enhance
    assert "grips.indexOf(control) < 0" in enhance


def test_readouts_are_real_and_claim_no_monitoring() -> None:
    for text in (DOCK, SENTINEL, HOMEPAGE):
        assert not re.search(r"threat level", text, re.I)
        assert not re.search(r"ONLINE\s*·\s*ACTIVE\s*·\s*MONITORING", text)
        assert not re.search(r"systems:\s*\d+\s*online", text, re.I)
        assert not re.search(r"confidence:\s*9\d(\.\d)?%", text, re.I)
    # a keyword match is labelled as what it is, not as a confidence level
    assert '"Confidence: "' not in SENTINEL and "Pre-written answer" in SENTINEL
    # every readiness value is derived locally
    assert "navigator.onLine" in DOCK
    assert "new Date().toISOString()" in DOCK
    assert "RULE-GUIDED" in DOCK and "ON DEVICE" in DOCK
    assert "no system access" in DOCK


def test_voice_is_dictation_that_the_visitor_sends() -> None:
    body = re.search(r"function toggleVoice\(\)\{(.*?)\}\nfunction setMode", SENTINEL, re.S)
    assert body, "toggleVoice not found"
    assert "handleMessage" not in body.group(1)
    assert "requestSubmit" not in body.group(1)
    # say where the audio goes; the typed chat is what stays on the device
    assert "In Chrome and Edge the audio is sent to Google or Microsoft" in SENTINEL
    assert "does not send or store typed conversation content" in HOMEPAGE
    assert "ClearGlass has not received or stored this conversation" in SENTINEL
    for hook in ('data-sentinel-mode="text"', 'data-sentinel-mode="voice"', 'data-sentinel-mode="query"',
                 "data-sentinel-voice ", "data-sentinel-voice-note", "data-sentinel-link"):
        assert hook in HOMEPAGE, hook


ROUTER = r"""
const fs = require("fs"), vm = require("vm");
const src = fs.readFileSync(process.argv[1], "utf8");
function grab(re) { const m = src.match(re); if (!m) throw new Error("missing " + re); return m[0]; }
const ctx = {};
vm.createContext(ctx);
vm.runInContext(grab(/function hasTerm\(text,term\)\{[^\n]*\}\n/), ctx);
vm.runInContext(grab(/var missions=\[[^\]]*\];/), ctx);
vm.runInContext(grab(/var pathways=\[[\s\S]*?\n\];/), ctx);
const probes = JSON.parse(fs.readFileSync(0, "utf8"));
const out = {};
for (const probe of probes) {
  const text = probe.toLowerCase();
  const hit = ctx.pathways.find(p => p.terms.some(t => ctx.hasTerm(text, t)));
  out[probe] = hit ? hit.answer.slice(0, 40) : null;
}
out.__missions = ctx.missions;
process.stdout.write(JSON.stringify(out));
"""

EXPECTED = {
    # the six missions
    "Mission briefing": "ClearGlass Inc. is an Ontario advisory",
    "Risk assessment": "A ClearGlass risk assessment starts",
    "Threat analysis": "Sentinel has no access to your logs",
    "Infrastructure monitoring": "Sentinel is not connected to your infras",
    "AI governance": "ClearGlass designs AI with governance in",
    "Executive intelligence": "ClearGlass Insights publishes intelligen",
    # a reply chip that used to land on the portal answer via "app" in "approval"
    "How do approval gates work?": "ClearGlass designs AI with governance in",
    # "ai" inside "email" used to route security questions to AI automation
    "I need email security help": "ClearGlass provides blue-team-aligned cy",
    # the hero's quick objectives keep their pathways
    "I need a high-performance website.": "A high-performance website pathway usual",
    "I want more qualified leads.": "For qualified growth, ClearGlass can con",
    "I need AI automation.": "The AI automation pathway maps the workf",
    "I need a secure customer portal.": "A secure portal engagement begins with u",
    "I need cybersecurity guidance.": "ClearGlass provides blue-team-aligned cy",
    "I need cloud deployment help.": "A cloud deployment pathway covers worklo",
    "I want a full digital growth system.": "For qualified growth, ClearGlass can con",
    # mission terms are the mission phrases, not bare words that catch other questions
    "What does the quick audit cost?": "I will not invent pricing or availabilit",
}

# prompts that must NOT land on a mission answer
UNMATCHED = ["Is my business at risk right now?", "Tell me about your governance", "Any insights?"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run sentinel.js's matcher")
def test_sentinel_routes_each_prompt_to_its_pathway() -> None:
    result = subprocess.run(
        ["node", "-e", ROUTER, str(ROOT / "sentinel.js")],
        input=json.dumps(list(EXPECTED) + UNMATCHED), capture_output=True, text=True, check=True, timeout=60,
    )
    routed = json.loads(result.stdout)
    for missions_probe in routed.pop("__missions"):
        assert missions_probe in EXPECTED
    wrong = {probe: routed[probe] for probe, want in EXPECTED.items()
             if not (routed[probe] or "").startswith(want)}
    assert not wrong, f"misrouted prompts: {wrong}"
    captured = {probe: routed[probe] for probe in UNMATCHED if routed[probe] is not None}
    assert not captured, f"prompts captured by a mission answer: {captured}"
