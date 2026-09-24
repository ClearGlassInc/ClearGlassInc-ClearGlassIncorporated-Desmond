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
    # glass.css repaints [class*="-pill"], "-badge" and "-chip" (and their
    # prefix forms) on the homepage, so the Intel Desk's flags and topic links
    # must not wear those words either.
    nets = ("-panel", "panel-", "-card", "card-", "-tile", "tile-", "kicker", "eyebrow",
            "footer", "btn", "button", "status-dot", "signal-dot", "icon", "scanline", "scan-line",
            "-pill", "pill-", "-badge", "badge-", "-chip", "chip-")
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


def test_readouts_are_real_and_claim_no_monitoring() -> None:
    for text in (DOCK, SENTINEL, HOMEPAGE):
        assert not re.search(r"threat level", text, re.I)
        assert not re.search(r"ONLINE\s*·\s*ACTIVE\s*·\s*MONITORING", text)
        assert not re.search(r"systems:\s*\d+\s*online", text, re.I)
        assert not re.search(r"confidence:\s*9\d(\.\d)?%", text, re.I)
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
    assert "browser provider may process" in SENTINEL
    assert "Optional voice input uses your browser’s own speech service." in HOMEPAGE
    for hook in ('data-sentinel-mode="text"', 'data-sentinel-mode="voice"', 'data-sentinel-mode="query"',
                 "data-sentinel-voice ", "data-sentinel-voice-note", "data-sentinel-link"):
        assert hook in HOMEPAGE, hook


HUB = (ROOT / "blog" / "index.html").read_text(encoding="utf-8")
HUB_JS = (ROOT / "blog" / "insights.js").read_text(encoding="utf-8")
FEED = json.loads((ROOT / "blog" / "posts.json").read_text(encoding="utf-8"))


def _intel_paths() -> dict[str, str]:
    block = re.search(r"var INTEL = \{(.*?)\};", DOCK, re.S)
    assert block, "INTEL settings missing from station-chat.js"
    return dict(re.findall(r'(\w+): "([^"]+)"', block.group(1)))


def test_intel_desk_reads_the_generated_brief_index() -> None:
    paths = _intel_paths()
    assert paths["feed"] == "blog/posts.json"
    assert (ROOT / paths["feed"]).is_file()
    assert (ROOT / paths["hub"] / "index.html").is_file()
    assert (ROOT / paths["rss"]).is_file()
    # every field the desk reads is one tools/insights_index.py writes
    assert FEED["posts"], "brief index is empty"
    for field in ("slug", "url", "title", "category", "quote", "description", "readMinutes",
                  "deskRank", "featured", "publishedAt", "topics", "tags", "status"):
        assert f"p.{field}" in DOCK, field
        assert any(field in post for post in FEED["posts"]), field
    assert isinstance(FEED["topics"], dict) and FEED["updated"]


def test_intel_desk_topic_links_land_on_real_hub_filters() -> None:
    chips = set(re.findall(r'data-topic="([^"]+)"', HUB))
    feed_topics = {t for post in FEED["posts"] for t in post.get("topics", [])}
    assert feed_topics <= chips, f"topics with no hub filter: {sorted(feed_topics - chips)}"
    assert "saved" in chips                         # the /saved command's target
    # the hub reads exactly the parameters the desk writes, and #latest holds the grid
    assert "params.get('topic')" in HUB_JS and "get('q')" in HUB_JS
    assert 'id="latest"' in HUB and 'id="postGrid"' in HUB
    assert 'params.push("topic=" + encodeURIComponent(topic))' in DOCK
    assert 'params.push("q=" + encodeURIComponent(query))' in DOCK
    # the saved list the desk counts is the one the hub writes
    assert "var SAVED_KEY = 'ix-saved-posts';" in HUB_JS
    assert 'var SAVED_KEY = "ix-saved-posts";' in DOCK


def test_intel_desk_is_one_same_origin_read_painted_as_text() -> None:
    assert DOCK.count("fetch(") == 1
    assert 'fetch(BASE + INTEL.feed, { cache: "no-cache", credentials: "same-origin" })' in DOCK
    # feed data never reaches the HTML parser
    for name in ("renderIntel", "showBrief", "paintCounts", "paintSuggest", "ingest"):
        body = re.search(r"\n  function " + name + r"\([^)]*\) \{\n(.*?)\n  \}\n", DOCK, re.S)
        assert body, name
        assert "innerHTML" not in body.group(1), name
    # it always has somewhere to go, feed or no feed
    assert "function intelFallback()" in DOCK and ".catch(intelFallback)" in DOCK
    # counts claim nothing the page cannot know
    assert "localStorage.setItem(SEEN_KEY" in DOCK


INTEL_PROBE = r"""
const fs = require("fs"), vm = require("vm");
const src = fs.readFileSync(process.argv[1], "utf8");
function grab(name) {
  const m = src.match(new RegExp("\\n  function " + name + "\\([^)]*\\) \\{\\n[\\s\\S]*?\\n  \\}\\n"));
  if (!m) throw new Error("missing " + name);
  return m[0];
}
const ctx = { BASE: "https://www.clearglassinc.com/", INTEL: { hub: "blog/" } };
vm.createContext(ctx);
["decode", "briefUrl", "hubUrl"].forEach(n => vm.runInContext(grab(n), ctx));
const input = JSON.parse(fs.readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify({
  decoded: input.decode.map(s => ctx.decode(s)),
  urls: input.urls.map(u => ctx.briefUrl(u)),
  feed: input.feed.map(u => ctx.briefUrl(u)),
  hub: [ctx.hubUrl(), ctx.hubUrl("cyber"), ctx.hubUrl(null, "botnet & iot")]
}));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run station-chat.js's helpers")
def test_intel_desk_only_follows_same_site_brief_links() -> None:
    probes = {
        "decode": ["Cyber Intelligence &amp; Critical Infrastructure", "&lt;img src=x&gt;", "Canada&#x2013;US"],
        "urls": ["/blog/x.html", "blog/y.html", "javascript:alert(1)", "https://evil.example/blog/x.html",
                 "//evil.example/blog/x.html", "/blog/../admin.html", "/blog/x.html\"onmouseover=\"1"],
        "feed": [post["url"] for post in FEED["posts"]],
    }
    result = subprocess.run(
        ["node", "-e", INTEL_PROBE, str(ROOT / "station-chat.js")],
        input=json.dumps(probes), capture_output=True, text=True, check=True, timeout=60,
    )
    out = json.loads(result.stdout)
    base = "https://www.clearglassinc.com/"
    assert out["decoded"] == ["Cyber Intelligence & Critical Infrastructure", "<img src=x>", "Canada–US"]
    assert out["urls"] == [base + "blog/x.html", base + "blog/y.html", "", "", "", "", ""]
    # no published brief is silently dropped from the desk
    assert all(out["feed"]), [u for u, r in zip(probes["feed"], out["feed"]) if not r]
    assert out["hub"] == [base + "blog/", base + "blog/?topic=cyber#latest",
                          base + "blog/?q=botnet%20%26%20iot#latest"]


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
    "Mission briefing": "ClearGlass Inc. is an Ontario practice",
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
}


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run sentinel.js's matcher")
def test_sentinel_routes_each_prompt_to_its_pathway() -> None:
    result = subprocess.run(
        ["node", "-e", ROUTER, str(ROOT / "sentinel.js")],
        input=json.dumps(list(EXPECTED)), capture_output=True, text=True, check=True, timeout=60,
    )
    routed = json.loads(result.stdout)
    for missions_probe in routed.pop("__missions"):
        assert missions_probe in EXPECTED
    wrong = {probe: routed[probe] for probe, want in EXPECTED.items()
             if not (routed[probe] or "").startswith(want)}
    assert not wrong, f"misrouted prompts: {wrong}"
