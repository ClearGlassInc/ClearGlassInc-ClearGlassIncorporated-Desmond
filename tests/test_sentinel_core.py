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
    # two static indexes, one read each: the briefs here, the pages in the
    # Site Intelligence test below; both same-origin, neither sends anything
    assert DOCK.count("fetch(") == 2
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


# ── Site Intelligence ─────────────────────────────────────────────────────────
# The console reads data/site-index.json, which tools/internal_links.py writes
# from the same graph that builds every page's "Continue exploring" block. These
# tests run the console's own matcher on the real index, so a phrasing that
# stops resolving, or a sector that empties, fails here rather than on the site.

INDEX = json.loads((ROOT / "data" / "site-index.json").read_text(encoding="utf-8"))


def test_site_index_is_the_generated_graph() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("internal_links", ROOT / "tools" / "internal_links.py")
    assert spec and spec.loader
    links = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(links)
    assert (ROOT / "data" / "site-index.json").read_text(encoding="utf-8") == links.build_site_index()
    assert INDEX["counts"]["pages"] == len(INDEX["pages"]) == len(links.PAGES)
    assert INDEX["counts"]["clusters"] == len(INDEX["clusters"]) == len(links.CLUSTERS)
    for page in INDEX["pages"]:
        for field in ("path", "title", "summary", "cluster", "role", "related", "prev", "next"):
            assert field in page, (page["path"], field)
        assert (ROOT / page["path"]).is_file(), page["path"]
    # every field the console reads is one the generator writes
    for field in ("p.path", "p.title", "p.summary", "p.about", "p.cluster", "p.role", "p.related", "p.prev", "p.next",
                  "c.id", "c.name", "c.pillar", "c.members", "c.cta"):
        assert field in DOCK, field


def test_console_rides_on_every_mapped_page() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("internal_links", ROOT / "tools" / "internal_links.py")
    assert spec and spec.loader
    links = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(links)
    for page in links.PAGES:
        text = (ROOT / page).read_text(encoding="utf-8", errors="surrogateescape")
        assert len(re.findall(r'src="[^"]*station-chat\.js"', text)) == 1, page
        tag = re.search(r'<script defer src="[^"]*station-chat\.js"[^>]*>', text).group(0)
        assert ('data-fit="fixed"' in tag) == (page in links.FIXED_VIEWPORT and page not in links.CONSOLE_SELF_HOSTED), page


def test_site_index_is_one_same_origin_read_painted_as_text() -> None:
    assert 'fetch(BASE + SITE.index, { cache: "no-cache", credentials: "same-origin" })' in DOCK
    assert "function siteFallback()" in DOCK and ".catch(siteFallback)" in DOCK
    # index data and answers never reach the HTML parser: the only innerHTML
    # writes are the static build template and the pause/play icon constants
    writes = re.findall(r"[\w.]+\.innerHTML\s*=[^;\n]*", DOCK)
    assert writes == ["b.innerHTML = intel.hold ? IC_PLAY : IC_HOLD", "root.innerHTML ="], writes
    for name in ("ingestSite", "paintIndex", "paintAnswer", "listRows", "rich", "paintSide", "buildGraph", "showLinks"):
        assert re.search(r"\n  function " + name + r"\(", DOCK), name
    # page paths are the only URLs the index can hand the console
    assert "function siteUrl(raw)" in DOCK


def test_questions_reach_the_home_sentinel_without_touching_the_url() -> None:
    assert 'sessionStorage.setItem(SENTINEL_HANDOFF, String(prompt || "").slice(0, 800))' in DOCK
    assert 'go(BASE + "index.html#sentinel");' in DOCK
    assert 'if (location.hash !== "#sentinel") return;' in DOCK
    # the pickup never forwards a question onward (no bounce loop)
    assert "if (!hasSentinel()) return;                 // never bounce the question onward" in DOCK
    assert "sessionStorage.removeItem(SENTINEL_HANDOFF)" in DOCK


def test_site_readouts_count_what_the_index_holds() -> None:
    for claim in ("Pages Synced: Live", "Knowledge Nodes: Live", "Intelligence Graph: Active", "Site Indexed ✓"):
        assert claim not in DOCK, claim
    assert 'ready ? String(site.pages.length) : "--"' in DOCK
    assert 'ready ? String(site.links) : "--"' in DOCK
    # every answer says how it was resolved, measured on the device
    assert '"Resolved on this device in "' in DOCK
    assert "Assembled from the site index, not written by a language model." in DOCK
    assert (ROOT / "prompts" / "sentinel_core_system_prompt.md").is_file()


SITE_PROBE = r"""
const fs = require("fs"), vm = require("vm");
const src = fs.readFileSync(process.argv[1], "utf8");
function fn(name) {
  const head = "\\n  function " + name + "\\([^)]*\\) \\{";
  const m = src.match(new RegExp(head + "[^\\n]*\\}\\n")) || src.match(new RegExp(head + "\\n[\\s\\S]*?\\n  \\}\\n"));
  if (!m) throw new Error("missing " + name);
  return m[0];
}
function block(start, end) {
  const i = src.indexOf(start), j = src.indexOf(end, i);
  if (i < 0 || j < 0) throw new Error("missing " + start);
  return src.slice(i, j + end.length);
}
const BASE = "https://www.clearglassinc.com/";
const ctx = { BASE, location: { href: BASE + "cyber-defense-console.html" }, MISSIONS: [1, 2, 3, 4, 5, 6] };
vm.createContext(ctx);
vm.runInContext(block("  var SECTORS = [", "\n  ];"), ctx);
vm.runInContext(block("  var SECTOR_ALIAS = [", "\n  ];"), ctx);
vm.runInContext(block("  var ALIKE = {", "\n  };"), ctx);
vm.runInContext(block("  var STOPS = {};", "STOPS[w] = 1; });"), ctx);
vm.runInContext(block("  var site = {", "};"), ctx);
vm.runInContext("function paintIndex() {} function flushSite() {} function siteFallback() { site.state = 'static'; }", ctx);
["siteUrl", "strList", "herePath", "ingestSite", "norm", "stem", "words", "hit", "queryTerms", "rank", "unknownTerms",
 "inSector", "sectorKey", "orderSector", "sectorById", "sectorsIn", "sectorPages", "intentOf", "modeFor"].forEach(n => vm.runInContext(fn(n), ctx));
const input = JSON.parse(fs.readFileSync(0, "utf8"));
vm.runInContext("ingestSite(" + JSON.stringify(input.index) + ")", ctx);
const out = { state: ctx.site.state, here: ctx.site.here && ctx.site.here.path, intents: {}, top: {}, sectors: {}, urls: {} };
for (const q of input.intents) out.intents[q] = ctx.intentOf(q);
for (const q of input.top) { const r = ctx.rank(q); out.top[q] = r.length ? r[0].e.path : null; }
for (const s of ctx.SECTORS) out.sectors[s.id] = s.missions ? -1 : s.pages.length;
const sel = ctx.sectorsIn("cybersecurity services");
out.cyberServices = { ids: sel.ids, pages: ctx.sectorPages(sel).pages.map(e => e.path) };
for (const u of input.urls) out.urls[u] = ctx.siteUrl(u);
out.modes = input.modes.map(q => ctx.modeFor(q));
process.stdout.write(JSON.stringify(out));
"""

INTENTS = {
    "Where is the pricing page?": {"kind": "locate", "arg": "pricing"},
    "Show all cybersecurity services": {"kind": "sector", "arg": "cybersecurity services"},
    "What AI governance capabilities exist?": {"kind": "sector", "arg": "ai governance"},
    "Show every ClearGlass solution": {"kind": "sector", "arg": "solution"},
    "What are the Artemis features?": {"kind": "sector", "arg": "artemis"},
    "What pages discuss autonomous agents?": {"kind": "search", "arg": "autonomous agents"},
    "Take me to OSINT workflows": {"kind": "go", "arg": "osint workflows"},
    "Map the entire platform.": {"kind": "map"},
    "What pages exist?": {"kind": "pages"},
    "What's related to Artemis?": {"kind": "related", "arg": "artemis"},
    "Explain this page": {"kind": "explain"},
    "Summarize this section": {"kind": "summarize"},
    "Generate executive brief": {"kind": "brief"},
}
# Sentinel's own prompts keep going to the Sentinel conversation.
UNCLAIMED = list(EXPECTED) + UNMATCHED + ["Talk to a human", "Start a project brief"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required to run station-chat.js's matcher")
def test_site_intelligence_resolves_on_the_real_index() -> None:
    probe = {
        "index": INDEX,
        "intents": list(INTENTS) + UNCLAIMED,
        "top": ["pricing", "osint workflows", "the store", "zero trust", "phipa"],
        "urls": ["pricing.html", "blog/", "offers/security-quick-audit.html", "javascript:alert(1)", "//evil.example/x.html",
                 "https://evil.example/x.html", "../etc/passwd.html", "blog/../../x.html", "x.html\"onload=\"1"],
        "modes": ["Analyze the architecture", "compare cyber pages", "why choose ClearGlass", "Where is the pricing page?"],
    }
    result = subprocess.run(["node", "-e", SITE_PROBE, str(ROOT / "station-chat.js")], input=json.dumps(probe),
                            capture_output=True, text=True, check=True, timeout=60)
    out = json.loads(result.stdout)
    assert out["state"] == "ready"
    assert out["here"] == "cyber-defense-console.html"
    for query, want in INTENTS.items():
        assert out["intents"][query] == want, (query, out["intents"][query])
    claimed = {q: out["intents"][q] for q in UNCLAIMED if out["intents"][q] is not None}
    assert not claimed, f"Sentinel prompts captured by a site intent: {claimed}"
    assert out["top"]["pricing"] == "pricing.html"
    assert out["top"]["osint workflows"] == "blog/osint-workflow-that-survives-contact-with-reality.html"
    assert out["top"]["phipa"] in {"offers/phipa-readiness.html", "offers/phipa-readiness-checklist.html"}
    # every Mission Control sector holds pages; the counts are memberships
    empty = [sid for sid, n in out["sectors"].items() if n == 0]
    assert not empty, f"empty sectors: {empty}"
    # "cybersecurity services" is the overlap of two sectors, in the order named
    assert out["cyberServices"]["ids"] == ["cybersecurity", "services"]
    assert "offers/security-quick-audit.html" in out["cyberServices"]["pages"]
    assert "offers/hardening-sprint.html" in out["cyberServices"]["pages"]
    # only same-site page paths become links
    base = "https://www.clearglassinc.com/"
    assert out["urls"]["pricing.html"] == base + "pricing.html"
    assert out["urls"]["blog/"] == base + "blog/"
    assert out["urls"]["offers/security-quick-audit.html"] == base + "offers/security-quick-audit.html"
    for bad in probe["urls"][3:]:
        assert out["urls"][bad] == "", bad
    assert out["modes"] == ["technical", "analytical", "pitch", "executive"]
