/* ClearGlass · Sentinel Core (bottom-right command dock)
   ────────────────────────────────────────────────────────────────────────────
   The collapsible command console: a compact "SENTINEL CORE" pill that expands
   into a mission console — readiness strip, a command bar (Ask Sentinel, slash
   commands, brief search), the Intel Desk, six mission modules, eight
   controls, routes and TOP/BOTTOM jumps.

   The Intel Desk is the console's featured module: ClearGlass Insights, read
   from blog/posts.json (the static index tools/insights_index.py generates).
   It rotates the editors' desk picks, flags briefs published in the last 14
   days that have not been opened from this device, links each topic straight
   into the hub's own ?topic= filter, and badges the collapsed dock with the
   same count. With no feed (offline, file://) it falls back to a plain link
   to the hub, so the section is never empty.

   It is the single floating control surface on pages that load it, so it
   absorbs the widgets that used to pile up in the corners on phones:
     • the Sentinel launcher (sentinel.js)     → Ask Sentinel / missions here
     • the Stealth Glass pill (stealth-glass.js) → mirrored, never duplicated
     • "Reduce visual effects" (clearglass-motion.js) → the Tactical View chip
     • the ↑/↓ scroll arrows (fx.js)            → the TOP/BOTTOM jumps
   Each is hidden only while this dock is mounted, so a page without it keeps
   them all. The toggles drive the original buttons, which stay the source of
   truth for their own state.

   Every readout is a real, locally known value (network link, session id, UTC
   clock, stealth and motion state, the feed index's own date and counts).
   Nothing here claims to monitor anything: this public console has no
   sensors, and it says so.

   Site Intelligence makes the console the site's navigation layer, on every
   page tools/internal_links.py maps (the generator adds the script tag):
     • ask in plain language ("Where is the pricing page?", "Show all
       cybersecurity services", "Take me to OSINT workflows") and get ranked
       pages, a sector listing, or a straight jump
     • a global index readout, Mission Control (command center + twelve
       sectors), nine smart actions about the current page, and the
       Intelligence Graph: a zoomable map of every page and its links
     • answers written to Sentinel's house style
       (prompts/sentinel_core_system_prompt.md) in four modes: Executive,
       Technical, Pitch, Analytical
   It all runs on data/site-index.json, the same graph that builds every
   page's "Continue exploring" block. Matching is rule-guided (word prefixes
   plus a short synonym table), it happens in this browser, and every answer
   says what it assumed and how it was ranked. Missions and questions asked
   on a page without the Sentinel conversation carry over to the home page's
   Sentinel through sessionStorage, never the URL.

   No backend, no tracking, no external command execution. The only network
   requests are two same-origin GETs of static indexes (briefs, pages), made
   when the browser is idle. "Opened" briefs and the saved list stay in this
   browser. Drop in with <script defer src="station-chat.js"></script>; add
   data-fit="fixed" on full-viewport pages for the compact dock. No deps. */
(function () {
  "use strict";
  if (window.__cgStationChat) return;
  window.__cgStationChat = true;

  // New key on purpose: the previous dock auto-saved "1" on every load, so the
  // old value records no one's choice and would keep phones expanded.
  var STORE_OPEN = "cg-core-open";
  var STEALTH_KEY = "cg-stealth";
  var DOCK_H = 56;          // dock pill height, kept in sync with the CSS below
  var reduce = false;
  try { reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}

  // ── console content ──────────────────────────────────────────────────────
  // Mission prompts match the mission pathways in sentinel.js word for word.
  var MISSIONS = [
    { code: "M1", title: "Mission Briefing", sub: "What ClearGlass does", prompt: "Mission briefing" },
    { code: "M2", title: "Risk Assessment", sub: "Where you are exposed", prompt: "Risk assessment" },
    { code: "M3", title: "Threat Analysis", sub: "Threat-led priorities", prompt: "Threat analysis" },
    { code: "M4", title: "Infrastructure Monitoring", sub: "Visibility and alerting", prompt: "Infrastructure monitoring" },
    { code: "M5", title: "AI Governance", sub: "Approval-gated AI", prompt: "AI governance" },
    { code: "M6", title: "Executive Intelligence", sub: "Leadership briefs", prompt: "Executive intelligence" }
  ];

  var CONTROLS = [
    { act: "stealth", title: "Stealth Glass", sub: "Privacy dim" },
    { act: "tactical", title: "Tactical View", sub: "Reduce effects" },
    { title: "Cyber Monitor", sub: "Demo console", href: "cyber-defense-console.html" },
    { title: "OSINT Fusion", sub: "Demo deck", href: "Ontario-osint.html" },
    { title: "Sentinel Core", sub: "Geospatial", href: "sentinel.html" },
    { title: "Mission Feed", sub: "Intel briefs", href: "blog/", feed: true },
    { title: "Aegis Defence", sub: "Legal shield", href: "aegis.html" },
    { title: "Artemis Analytics", sub: "AI cyber intel", href: "artemis-ai-cyber-intelligence-platform.html" }
  ];

  var ROUTES = [
    { title: "Web Design", href: "web-design.html" },
    { title: "Project Board", href: "project-board.html" }
  ];

  // ── Site Intelligence content ────────────────────────────────────────────
  var SITE = {
    index: "data/site-index.json",   // generated by tools/internal_links.py
    show: 6,                         // rows in an answer before "Show all"
    graph: "authority-network.html"  // the static page map, when the index is unreachable
  };
  var SENTINEL_HANDOFF = "cg-sentinel-handoff";  // sessionStorage: a question carried to the home page
  var MODE_KEY = "cg-core-mode";
  var MC_KEY = "cg-core-mc";

  // Mission Control sectors. A page is in a sector when it sits in one of its
  // clusters, under one of its paths, or its title or summary uses one of its
  // words. The counts shown are those memberships and nothing else.
  var SECTORS = [
    { id: "missions", title: "Missions", sub: "Sentinel briefs", missions: true },
    { id: "services", title: "Services", sub: "Engagements", clusters: ["services"], paths: ["offers/"],
      words: ["engagement", "pricing"] },
    { id: "research", title: "Research", sub: "Insights", clusters: ["blog"] },
    { id: "documents", title: "Documents", sub: "Specs & policy", clusters: ["legal"], paths: ["docs/", "operations/"],
      words: ["spec", "specification", "runbook", "whitepaper", "checklist", "framework", "blueprint"] },
    { id: "intelligence", title: "Intelligence", sub: "Platforms", clusters: ["intelligence"], words: ["intelligence"] },
    // "product " (trailing space) is the whole word, so "productivity" stays out
    { id: "products", title: "Products", sub: "Platforms & assets", clusters: ["opal"], paths: ["products"],
      words: ["product ", "products", "platform", "suite"] },
    { id: "artemis", title: "Artemis", sub: "Intel OS", clusters: ["artemis"], words: ["artemis"] },
    { id: "aegis", title: "Aegis", sub: "Legal shield", words: ["aegis", "legal", "counsel"] },
    { id: "osint", title: "OSINT", sub: "Open source", words: ["osint", "open source intelligence", "investigation", "investigator"] },
    { id: "automation", title: "Automation", sub: "Agents & flows", clusters: ["command"],
      words: ["automation", "workflow", "agent", "orchestration"] },
    { id: "governance", title: "Governance", sub: "Approval-gated", words: ["governance", "governed", "approval",
      "audit trail", "liability", "compliance", "accountability", "oversight"] },
    { id: "cybersecurity", title: "Cybersecurity", sub: "Defence & risk", clusters: ["security"],
      words: ["cyber", "security", "threat", "defense", "defence", "zero trust", "phishing", "hardening", "blue team"] }
  ];

  // What a visitor may call each sector. "any" joins sectors instead of
  // narrowing to their overlap: "solutions" means products or services.
  var SECTOR_ALIAS = [
    { say: ["mission"], ids: ["missions"] },
    { say: ["service", "engagement", "offer"], ids: ["services"] },
    { say: ["research", "insight", "brief", "blog", "article"], ids: ["research"] },
    { say: ["document", "docs", "spec", "runbook", "policies", "policy"], ids: ["documents"] },
    { say: ["intelligence"], ids: ["intelligence"] },
    { say: ["product", "platform"], ids: ["products"] },
    { say: ["artemis"], ids: ["artemis"] },
    { say: ["aegis"], ids: ["aegis"] },
    { say: ["osint", "open source intelligence"], ids: ["osint"] },
    { say: ["automation", "automations", "workflow", "agents", "agentic"], ids: ["automation"] },
    { say: ["governance", "governed"], ids: ["governance"] },
    { say: ["cyber", "security", "defence", "defense"], ids: ["cybersecurity"] },
    { say: ["solution", "offerings"], ids: ["products", "services"], any: true }
  ];

  // Mission Control's command center.
  var COMMAND_CENTER = [
    { id: "search", title: "Search Site", sub: "Every page, in plain words" },
    { id: "mission", title: "Open Mission", sub: "Six Sentinel missions" },
    { id: "briefing", title: "Launch Briefing", sub: "M1 · Mission briefing" },
    { id: "products", title: "Explore Products", sub: "Platforms & assets" },
    { id: "report", title: "Generate Report", sub: "Executive brief, this page" },
    { id: "architecture", title: "Analyze Architecture", sub: "This page on the graph" },
    { id: "intel", title: "Browse Intelligence", sub: "Sector + Intel Desk" }
  ];

  // Smart actions about the current page, with the writing mode each one
  // defaults to while the mode is on Auto.
  var SMART = [
    { id: "explain", title: "Explain this page", mode: "executive" },
    { id: "summarize", title: "Summarize section", mode: "executive" },
    { id: "related", title: "Related pages", mode: "executive" },
    { id: "services", title: "Related services", mode: "pitch" },
    { id: "brief", title: "Executive brief", mode: "executive" },
    { id: "plan", title: "Action plan", mode: "executive" },
    { id: "next", title: "Next step", mode: "pitch" },
    { id: "similar", title: "Similar content", mode: "analytical" },
    { id: "docs", title: "Documentation", mode: "technical" }
  ];

  // Writing modes (prompts/sentinel_core_system_prompt.md §2). Each mode
  // changes which structure leads an answer, never which facts it contains.
  var MODES = [
    { id: "executive", label: "Exec", name: "Executive" },
    { id: "technical", label: "Tech", name: "Technical" },
    { id: "pitch", label: "Pitch", name: "Pitch" },
    { id: "analytical", label: "Analysis", name: "Analytical" }
  ];

  // Queries typed here are ranked with these widened meanings (weight 0.45).
  var ALIKE = {
    cyber: ["security", "defense", "defence", "threat"],
    cybersecurity: ["cyber", "security", "defense", "threat"],
    security: ["cyber", "defense", "threat"],
    defence: ["defense", "security"],
    defense: ["defence", "security"],
    ai: ["agent", "automation", "model", "intelligence"],
    governance: ["governed", "approval", "audit", "policy", "compliance"],
    governed: ["governance", "approval"],
    automation: ["automate", "workflow", "agent", "orchestration"],
    agent: ["agentic", "autonomous", "automation"],
    autonomous: ["autonomy", "agent", "self"],
    osint: ["open source intelligence", "investigation", "flowsint"],
    pricing: ["price", "plans", "cost"],
    price: ["pricing", "plans"],
    cost: ["pricing", "price"],
    plan: ["pricing"],
    docs: ["documentation", "spec", "runbook", "policy"],
    documentation: ["spec", "runbook", "whitepaper", "policy"],
    legal: ["law", "counsel", "aegis"],
    law: ["legal", "counsel"],
    health: ["healthcare", "phipa", "clinical"],
    healthcare: ["health", "phipa"],
    government: ["public sector", "procurement", "federal"],
    blog: ["insights", "brief"],
    insight: ["blog", "brief"],
    research: ["insights", "brief", "analysis"],
    product: ["platform"],
    service: ["engagement", "offer"],
    contact: ["onboarding", "engagement", "book"],
    threat: ["risk", "attack", "security"],
    risk: ["threat", "exposure"]
  };
  var STOPS = {};
  ("a an the and or of to for in on at by with from into me my i we you your our is are was be it its this that these those " +
   "what which where who how why do does can could would should will show list find give tell see all every any some " +
   "page pages site website clearglass clearglassinc there here exist exists about discuss discusses cover covers mention " +
   "mentions take go open please want need looking look learn know more info information detail details thing things stuff " +
   "everything anything capability capabilities feature features option options available have has get us").split(" ")
    .forEach(function (w) { STOPS[w] = 1; });

  // ── Intel Desk ───────────────────────────────────────────────────────────
  // Paths resolve against this script's own URL, not the page's, so the desk
  // links correctly from any page depth that loads the console.
  var BASE = (function () {
    try {
      var s = document.currentScript;
      return new URL(".", s && s.src ? s.src : location.href).href;
    } catch (e) { return ""; }
  })();
  // data-fit="fixed" (written by tools/internal_links.py on full-viewport HUD
  // pages) folds the dock to its radar and reserves no page space.
  var FIT = (function () {
    try { var s = document.currentScript; return (s && s.getAttribute("data-fit")) || ""; } catch (e) { return ""; }
  })();
  var INTEL = {
    feed: "blog/posts.json",   // generated by tools/insights_index.py
    hub: "blog/",
    rss: "blog/feed.xml",
    freshDays: 14,             // "new" = published inside this window and not yet opened here
    picks: 5,                  // briefs in the rotation
    topics: 6,                 // topic links shown
    rotateMs: 7000
  };
  var SEEN_KEY = "cg-intel-seen";      // slugs opened from this console, this browser only
  var SAVED_KEY = "ix-saved-posts";    // blog/insights.js's saved list (same origin, read only)

  // ── icons (inline, so nothing is fetched) ────────────────────────────────
  var IC_SEND = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="M7 17 17 7M9 7h8v8" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var IC_CHEV = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="m6.5 9.5 5.5 5.5 5.5-5.5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var TRACE = '<svg class="cgst-trace" viewBox="0 0 120 18" preserveAspectRatio="none" aria-hidden="true">' +
    '<polyline points="0,9 14,9 19,3 24,15 29,9 46,9 50,5 54,13 58,9 80,9 84,2 89,16 94,9 120,9"/></svg>';
  var IC_PREV = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="m14.5 6.5-5.5 5.5 5.5 5.5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var IC_NEXT = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="m9.5 6.5 5.5 5.5-5.5 5.5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var IC_HOLD = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="M9 7v10M15 7v10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  var IC_PLAY = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="M9 6.8v10.4l8-5.2z" fill="currentColor"/></svg>';
  var IC_GRAPH = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<circle cx="12" cy="12" r="2.6" fill="currentColor"/><circle cx="5" cy="6" r="1.8" stroke="currentColor" stroke-width="1.4"/>' +
    '<circle cx="19" cy="6.5" r="1.8" stroke="currentColor" stroke-width="1.4"/><circle cx="18" cy="18.5" r="1.8" stroke="currentColor" stroke-width="1.4"/>' +
    '<circle cx="5.5" cy="18" r="1.8" stroke="currentColor" stroke-width="1.4"/>' +
    '<path d="M6.5 7.2 10 10.4M17.4 7.6 14 10.4M16.6 17.3 14 13.8M7 16.8 10 13.8" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>';
  var IC_X = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="m7 7 10 10M17 7 7 17" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>';

  // ── styles ───────────────────────────────────────────────────────────────
  var CSS = [
    /* Isolation first. The console now runs on every mapped page, and a page's
       own element rules (nav{position:fixed}, section{min-height:100vh},
       button{…}) would otherwise land on its markup. Reverting to the browser
       defaults leaves only the rules below; :where() keeps this at the id's
       weight so every class rule after it still wins. SVG is left alone
       (its presentation attributes would be reverted too), and so are the
       nodes station-enhance.js adds. */
    "#cg-station{margin:0;padding:0;border:0;background:none;box-shadow:none;float:none;min-height:0;max-height:none;filter:none}",
    "#cg-station :where(div,section,nav,header,aside,p,ol,ul,li,h2,h3,h4,dl,dt,dd,form,label,a,button,input,span,strong,small,em,i,b,",
    "blockquote,table,thead,tbody,tr,th,td):where(:not([class*='cg-se-']):not(svg *)){all:revert}",
    /* the metrics the console was drawn with on the home page, now its own */
    "#cg-station :where(p){line-height:1.7}#cg-station :where(h2){line-height:1.1}#cg-station :where(input){padding:0}",
    /* declared on the root so the co-existence rules below (which target other
       elements' subtrees) can read them too */
    ":root{--cgst-lift:" + (DOCK_H + 10) + "px;--cgst-stack-h:52px}",
    "#cg-station{--cgst-red:#ee6365;--cgst-blue:#4cc3ff;--cgst-teal:#78e0c8;--cgst-ink:#f7f1f1;--cgst-mute:#c3999b;",
    "--cgst-line:rgba(238,99,101,.26);--cgst-cell:rgba(20,12,14,.78);",
    "--cgst-mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;",
    "--cgst-sans:'Urbanist',Inter,system-ui,-apple-system,'Segoe UI',sans-serif;",
    "--cgst-edge:max(12px,env(safe-area-inset-right));--cgst-floor:max(12px,env(safe-area-inset-bottom));",
    /* tops out the stacking context: the panel must cover the security dock,
       which pins itself to the maximum z-index */
    "position:fixed;right:var(--cgst-edge);bottom:var(--cgst-floor);z-index:2147483647;",
    "display:flex;flex-direction:column;align-items:flex-end;",
    "width:min(384px,calc(100vw - 20px));font-family:var(--cgst-sans);pointer-events:none}",
    "#cg-station *{box-sizing:border-box}",
    "#cg-station>*{pointer-events:auto}",
    /* id-scoped so the isolation reset above cannot un-hide it */
    "#cg-station .cgst-sr,.cgst-sr{position:absolute!important;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}",

    /* ── sheet (absolute, so a collapsed dock reserves no phantom box). Not
       named "*-panel": clearglass-crimson.css repaints every [class*="-panel"]
       with !important, which flattened this into a see-through card. ── */
    "#cg-station .cgst-sheet{position:absolute;left:0;right:0;bottom:calc(100% + 10px);",
    /* capped so an open console stops below the site header (--cgst-top-clear
       is measured from #navbar in syncTopClear) */
    "max-height:min(600px,calc(100vh - var(--cgst-lift) - var(--cgst-top-clear,40px)));",
    "max-height:min(600px,calc(100dvh - var(--cgst-lift) - var(--cgst-top-clear,40px)));",
    "overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:rgba(238,99,101,.4) transparent;",
    "display:flex;flex-direction:column;gap:12px;padding:14px 13px 12px;border-radius:20px;",
    "border:1px solid rgba(238,99,101,.42);color:var(--cgst-ink);isolation:isolate;",
    "background:",
    "linear-gradient(var(--cgst-blue),var(--cgst-blue)) left 8px top 8px/12px 1px no-repeat,",
    "linear-gradient(var(--cgst-blue),var(--cgst-blue)) left 8px top 8px/1px 12px no-repeat,",
    "linear-gradient(var(--cgst-blue),var(--cgst-blue)) right 8px top 8px/12px 1px no-repeat,",
    "linear-gradient(var(--cgst-blue),var(--cgst-blue)) right 8px top 8px/1px 12px no-repeat,",
    "linear-gradient(rgba(76,195,255,.035) 1px,transparent 1px) 0 0/100% 22px,",
    "radial-gradient(120% 70% at 88% 0,rgba(238,99,101,.2),transparent 62%),",
    "radial-gradient(90% 60% at 0 100%,rgba(76,195,255,.08),transparent 70%),",
    /* opaque: phones get no backdrop blur (cg-design-system.css touch budget),
       and any show-through lets the page's bright banner text ghost in */
    "linear-gradient(170deg,#180c0f,#060508);",
    "-webkit-backdrop-filter:blur(20px) saturate(1.4);backdrop-filter:blur(20px) saturate(1.4);",
    "box-shadow:0 30px 70px -24px rgba(0,0,0,.92),0 0 0 .5px rgba(238,99,101,.24),0 0 44px -14px rgba(238,99,101,.5),inset 0 1px 0 rgba(255,255,255,.08);",
    "transform-origin:100% 100%;transition:opacity .28s cubic-bezier(.16,1,.3,1),transform .28s cubic-bezier(.16,1,.3,1),visibility 0s linear .28s}",
    /* children keep their height; the sheet scrolls instead of squashing them */
    "#cg-station .cgst-sheet>*{flex-shrink:0}",
    "#cg-station[data-open='false'] .cgst-sheet{opacity:0;transform:translateY(12px) scale(.965);pointer-events:none;visibility:hidden}",
    "#cg-station[data-open='true'] .cgst-sheet{opacity:1;transform:none;visibility:visible;transition-delay:0s}",

    /* ── panel header: radar, identity, live status, scan sweep ── */
    "#cg-station .cgst-head{position:relative;display:flex;align-items:center;gap:11px;padding:2px 2px 12px;",
    "border-bottom:1px solid var(--cgst-line);overflow:hidden}",
    "#cg-station .cgst-head::after{content:'';position:absolute;left:0;bottom:-1px;width:38%;height:1px;",
    "background:linear-gradient(90deg,transparent,var(--cgst-blue),transparent);animation:cgstScan 3.6s cubic-bezier(.45,0,.55,1) infinite}",
    "@keyframes cgstScan{0%{transform:translateX(-110%)}100%{transform:translateX(290%)}}",
    "#cg-station .cgst-id{flex:1 1 auto;min-width:0}",
    "#cg-station .cgst-org{display:block;margin:0 0 2px;font-family:var(--cgst-mono);font-size:8.5px;font-weight:600;letter-spacing:.24em;color:var(--cgst-mute)}",
    "#cg-station .cgst-title{margin:0;font-family:var(--cgst-mono);font-size:15px;font-weight:700;letter-spacing:.2em;color:#fff;white-space:nowrap}",
    "#cg-station .cgst-status{display:flex;align-items:center;gap:7px;margin:5px 0 0;font-family:var(--cgst-mono);font-size:9px;",
    "font-weight:600;letter-spacing:.16em;color:#bfe9ff;min-height:12px}",
    "#cg-station .cgst-status [data-cgst-type]::after{content:'_';margin-left:1px;color:var(--cgst-blue);animation:cgstCaret 1s steps(1) infinite}",
    "@keyframes cgstCaret{50%{opacity:0}}",
    "#cg-station .cgst-live{flex:0 0 auto;width:7px;height:7px;border-radius:50%;background:#5ef0a8;box-shadow:0 0 0 0 rgba(94,240,168,.6);animation:cgstLive 2.2s ease-out infinite}",
    "#cg-station[data-link='offline'] .cgst-live{background:#f2b04b;animation:none}",
    "@keyframes cgstLive{0%{box-shadow:0 0 0 0 rgba(94,240,168,.55)}70%,100%{box-shadow:0 0 0 7px rgba(94,240,168,0)}}",
    "#cg-station .cgst-trace{position:absolute;right:0;top:4px;width:92px;height:16px;opacity:.55;pointer-events:none}",
    "#cg-station .cgst-trace polyline{fill:none;stroke:var(--cgst-blue);stroke-width:1;stroke-dasharray:160;stroke-dashoffset:160;animation:cgstTrace 3.2s linear infinite}",
    "@keyframes cgstTrace{to{stroke-dashoffset:-160}}",

    /* ── radar mark (header + dock); the outer ring is live scroll progress ── */
    "#cg-station .cgst-radar{position:relative;flex:0 0 auto;display:grid;place-items:center;width:40px;height:40px;border-radius:50%;",
    "background:conic-gradient(var(--cgst-red) calc(var(--cgst-progress,0) * 1%),rgba(238,99,101,.16) 0);overflow:hidden}",
    "#cg-station .cgst-radar::before{content:'';position:absolute;inset:2.5px;border-radius:50%;",
    "background:repeating-radial-gradient(circle,transparent 0 6px,rgba(76,195,255,.22) 6px 7px),",
    "linear-gradient(rgba(76,195,255,.18),rgba(76,195,255,.18)) center/1px 100% no-repeat,",
    "linear-gradient(rgba(76,195,255,.18),rgba(76,195,255,.18)) center/100% 1px no-repeat,#0b080b}",
    "#cg-station .cgst-radar::after{content:'';position:absolute;inset:2.5px;border-radius:50%;",
    "background:conic-gradient(from 0deg,rgba(76,195,255,.55),rgba(76,195,255,0) 70deg,transparent 360deg);animation:cgstSweep 3.4s linear infinite}",
    "@keyframes cgstSweep{to{transform:rotate(360deg)}}",
    "#cg-station .cgst-radar i{position:relative;z-index:1;width:6px;height:6px;border-radius:50%;background:var(--cgst-red);box-shadow:0 0 10px var(--cgst-red)}",
    "#cg-station .cgst-radar b{position:absolute;z-index:1;top:9px;left:25px;width:3px;height:3px;border-radius:50%;background:var(--cgst-blue);",
    "box-shadow:0 0 6px var(--cgst-blue);animation:cgstBlip 3.4s linear infinite}",
    "@keyframes cgstBlip{0%,8%{opacity:1}40%,100%{opacity:.15}}",

    /* ── section labels ── */
    "#cg-station .cgst-label{display:flex;align-items:center;gap:8px;margin:0 0 7px;font-family:var(--cgst-mono);font-size:8.5px;",
    "font-weight:700;letter-spacing:.24em;text-transform:uppercase;color:var(--cgst-mute)}",
    "#cg-station .cgst-label::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,var(--cgst-line),transparent)}",

    /* ── readiness strip ── */
    "#cg-station .cgst-telemetry{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;margin:0;padding:0;",
    "border:1px solid var(--cgst-line);border-radius:12px;overflow:hidden;background:var(--cgst-line)}",
    "#cg-station .cgst-cell{margin:0;padding:7px 9px;background:var(--cgst-cell);min-width:0}",
    "#cg-station .cgst-cell dt{font-family:var(--cgst-mono);font-size:7.5px;font-weight:600;letter-spacing:.2em;color:#a98486}",
    "#cg-station .cgst-cell dd{margin:2px 0 0;font-family:var(--cgst-mono);font-size:10.5px;font-weight:700;letter-spacing:.06em;color:#e9f6ff;",
    "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-variant-numeric:tabular-nums}",
    "#cg-station[data-link='offline'] [data-cgst-link]{color:#f2b04b}",

    /* ── ask ── */
    "#cg-station .cgst-ask{display:flex;align-items:center;gap:8px;padding:5px 5px 5px 13px;border-radius:14px;",
    "border:1px solid rgba(238,99,101,.5);background:linear-gradient(100deg,rgba(238,99,101,.14),rgba(76,195,255,.05) 70%),rgba(14,9,11,.9);",
    "box-shadow:inset 0 1px 0 rgba(255,255,255,.06);transition:border-color .2s ease,box-shadow .2s ease}",
    "#cg-station .cgst-ask:focus-within{border-color:rgba(238,99,101,.95);box-shadow:0 0 0 3px rgba(238,99,101,.2),0 0 22px -6px rgba(238,99,101,.6)}",
    "#cg-station .cgst-ask-mark{flex:0 0 auto;font-family:var(--cgst-mono);font-size:11px;font-weight:700;color:var(--cgst-red)}",
    /* 16px stops iOS Safari zooming the page when the field takes focus */
    "#cg-station .cgst-ask input{flex:1 1 auto;min-width:0;height:38px;border:0;outline:0;color:#fff;font:600 16px/1.2 var(--cgst-sans);",
    /* clearglass-crimson.css and glass.css set html input backgrounds and focus
       rings with !important; the id selector plus !important outranks them */
    "background:transparent!important;border-radius:0;box-shadow:none!important}",
    "#cg-station .cgst-ask input::placeholder{color:#9d7678!important;opacity:1}",
    "#cg-station .cgst-ask input::placeholder{color:#9d7678}",
    "#cg-station .cgst-send{flex:0 0 auto;display:grid;place-items:center;width:40px;height:40px;border-radius:11px;cursor:pointer;",
    "border:1px solid rgba(238,99,101,.6);background:linear-gradient(135deg,rgba(238,99,101,.34),rgba(238,99,122,.16));color:#fff;",
    "transition:transform .2s cubic-bezier(.16,1,.3,1),box-shadow .2s ease}",
    "#cg-station .cgst-send:hover{transform:translateY(-1px);box-shadow:0 0 18px -4px rgba(238,99,101,.8)}",
    "#cg-station .cgst-send svg{width:18px;height:18px;display:block}",
    "#cg-station [hidden]{display:none!important}",

    /* ── command bar: slash commands + brief matches under the Ask field ── */
    "#cg-station .cgst-hint{margin:-6px 3px 0;font-family:var(--cgst-mono);font-size:7.5px;font-weight:600;letter-spacing:.16em;",
    "text-transform:uppercase;color:#8e6c6e}",
    "#cg-station .cgst-hint b{color:#e7b9ba;font-weight:700}",
    "#cg-station .cgst-suggest{margin:-6px 0 0;padding:5px;list-style:none;border-radius:13px;border:1px solid rgba(238,99,101,.36);",
    "background:linear-gradient(170deg,rgba(26,13,16,.98),rgba(9,7,9,.98));box-shadow:0 16px 34px -18px rgba(0,0,0,.95),inset 0 1px 0 rgba(255,255,255,.05)}",
    "#cg-station .cgst-opt{display:flex;align-items:baseline;gap:9px;min-width:0;padding:8px 9px;border-radius:9px;cursor:pointer;color:var(--cgst-ink)}",
    "#cg-station .cgst-opt+.cgst-opt{margin-top:2px}",
    "#cg-station .cgst-opt[aria-selected='true']{background:rgba(238,99,101,.15);box-shadow:inset 2px 0 0 var(--cgst-red)}",
    /* hover only where it is real hover; a tap would leave it stuck on phones */
    "@media(hover:hover) and (pointer:fine){#cg-station .cgst-opt:hover{background:rgba(238,99,101,.1)}}",
    "#cg-station .cgst-opt-k{flex:0 0 auto;min-width:54px;font-family:var(--cgst-mono);font-size:9.5px;font-weight:700;letter-spacing:.08em;color:var(--cgst-blue)}",
    "#cg-station .cgst-opt-h{flex:1 1 auto;min-width:0;font-size:12.5px;font-weight:600;color:#eadada;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",

    /* ── Intel Desk: the featured module. A conic light orbits its edge — the
       ::before square is 2.5x the width, so it covers every corner at any
       angle, and ::after repaints the interior 1px in. ── */
    "#cg-station .cgst-intel{position:relative;display:flex;flex-direction:column;gap:9px;padding:12px 11px 10px;border-radius:16px;",
    "overflow:hidden;isolation:isolate;box-shadow:0 20px 44px -26px rgba(76,195,255,.75),0 0 0 .5px rgba(76,195,255,.2)}",
    "#cg-station .cgst-intel::before{content:'';position:absolute;z-index:-2;left:50%;top:50%;width:250%;height:0;padding-bottom:250%;",
    "background:conic-gradient(from 0deg,rgba(76,195,255,.95),rgba(238,99,101,.85) 22%,rgba(120,224,200,.8) 48%,rgba(76,195,255,.18) 74%,rgba(76,195,255,.95));",
    "transform:translate(-50%,-50%);animation:cgstOrbit 9s linear infinite}",
    "@keyframes cgstOrbit{to{transform:translate(-50%,-50%) rotate(360deg)}}",
    "#cg-station .cgst-intel::after{content:'';position:absolute;z-index:-1;inset:1px;border-radius:15px;",
    "background:linear-gradient(rgba(76,195,255,.035) 1px,transparent 1px) 0 0/100% 18px,",
    "radial-gradient(110% 80% at 100% 0,rgba(76,195,255,.17),transparent 60%),",
    "radial-gradient(80% 60% at 0 100%,rgba(120,224,200,.09),transparent 70%),linear-gradient(165deg,#10121a,#07070b)}",
    "#cg-station .cgst-intel-top{display:flex;align-items:center;gap:8px}",
    "#cg-station .cgst-intel-id{flex:1 1 auto;min-width:0}",
    "#cg-station .cgst-intel-title{display:flex;align-items:center;gap:8px;margin:0;font-family:var(--cgst-mono);font-size:11px;font-weight:700;",
    "line-height:1.2;letter-spacing:.26em;text-transform:uppercase;color:#fff}",
    "#cg-station .cgst-intel-title::before{content:'';flex:0 0 auto;width:7px;height:7px;border-radius:1px;background:var(--cgst-blue);",
    "box-shadow:0 0 10px var(--cgst-blue);transform:rotate(45deg);animation:cgstBeacon 2.4s ease-in-out infinite}",
    "@keyframes cgstBeacon{50%{box-shadow:0 0 2px var(--cgst-blue);opacity:.55}}",
    "#cg-station .cgst-intel-sub{display:block;margin-top:4px;font-family:var(--cgst-mono);font-size:8px;font-weight:600;letter-spacing:.16em;",
    "text-transform:uppercase;color:#8fb7cc;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    "#cg-station .cgst-flag{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;gap:5px;padding:3px 8px;border-radius:999px;",
    "font-family:var(--cgst-mono);font-size:8.5px;font-weight:700;line-height:1.2;letter-spacing:.14em;color:#fff;white-space:nowrap;",
    "background:linear-gradient(135deg,#ee6365,#b8324a);box-shadow:0 0 14px -2px rgba(238,99,101,.85)}",
    "#cg-station .cgst-flag[data-quiet]{background:rgba(76,195,255,.1);color:#bfe9ff;box-shadow:inset 0 0 0 1px rgba(76,195,255,.4)}",

    /* featured brief */
    "#cg-station .cgst-brief{position:relative;display:flex;flex-direction:column;gap:7px;min-height:150px;padding:11px 12px 14px;border-radius:13px;",
    "border:1px solid rgba(76,195,255,.3);background:linear-gradient(160deg,rgba(24,31,46,.86),rgba(11,10,16,.92));color:var(--cgst-ink);",
    "text-decoration:none;overflow:hidden;touch-action:pan-y;-webkit-tap-highlight-color:transparent;",
    "transition:border-color .2s ease,box-shadow .2s ease,transform .2s cubic-bezier(.16,1,.3,1)}",
    "#cg-station .cgst-brief:hover{border-color:rgba(76,195,255,.75);transform:translateY(-1px);",
    "box-shadow:0 14px 30px -18px rgba(0,0,0,.9),0 0 24px -10px rgba(76,195,255,.85)}",
    "#cg-station .cgst-brief.cgst-in{animation:cgstIn .42s cubic-bezier(.16,1,.3,1)}",
    "@keyframes cgstIn{from{opacity:0;transform:translateX(var(--cgst-dir,12px))}to{opacity:1;transform:none}}",
    "#cg-station .cgst-brief-meta{display:flex;align-items:center;gap:6px;min-width:0;padding-right:46px;font-family:var(--cgst-mono);",
    "font-size:8.5px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;white-space:nowrap}",
    "#cg-station .cgst-rank{flex:0 0 auto;color:var(--cgst-teal)}",
    "#cg-station .cgst-cat{min-width:0;overflow:hidden;text-overflow:ellipsis;color:#8fc4de}",
    "#cg-station .cgst-rank:not(:empty)+.cgst-cat::before{content:'· ';color:#5d7c8c}",
    "#cg-station .cgst-brief-title{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden;",
    "font-size:15.5px;font-weight:750;line-height:1.25;letter-spacing:-.01em;color:#fff}",
    "#cg-station .cgst-brief-quote{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;padding-left:9px;",
    "border-left:2px solid rgba(238,99,101,.65);font-family:'Cormorant Garamond',Georgia,serif;font-size:14.5px;font-style:italic;line-height:1.28;color:#dccbcc}",
    "#cg-station .cgst-brief-foot{display:flex;align-items:center;gap:8px;margin-top:auto;min-width:0;font-family:var(--cgst-mono);font-size:8.5px;",
    "font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:#b89293}",
    "#cg-station .cgst-brief-foot>span:first-child{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
    "#cg-station .cgst-open{flex:0 0 auto;margin-left:auto;color:#fff;font-weight:700}",
    "#cg-station .cgst-brief .cgst-flag{position:absolute;top:9px;right:9px;padding:2px 7px;font-size:7.5px}",
    /* rotation timer: the bar's own animationend advances the slide, so a
       paused animation is a paused timer and reduced motion stops rotation */
    "#cg-station .cgst-timer{position:absolute;left:0;bottom:0;width:100%;height:2px;transform-origin:0 50%;transform:scaleX(0);",
    "background:linear-gradient(90deg,var(--cgst-blue),var(--cgst-teal));",
    "animation:cgstFill " + INTEL.rotateMs + "ms linear forwards;animation-play-state:paused}",
    "#cg-station .cgst-intel[data-run='1'] .cgst-timer{animation-play-state:running}",
    "@keyframes cgstFill{to{transform:scaleX(1)}}",
    "#cg-station .cgst-intel[data-state='loading'] .cgst-cat{animation:cgstBeacon 1.2s ease-in-out infinite}",

    /* rotation controls */
    "#cg-station .cgst-intel-nav{display:flex;align-items:center;gap:6px}",
    "#cg-station .cgst-step{flex:0 0 auto;display:grid;place-items:center;width:34px;height:32px;padding:0;border-radius:9px;cursor:pointer;",
    "border:1px solid rgba(76,195,255,.3);background:rgba(10,14,22,.82);color:#d8f1ff;font-family:inherit;",
    "transition:border-color .2s ease,background .2s ease,box-shadow .2s ease}",
    "#cg-station .cgst-step:hover{border-color:rgba(76,195,255,.85);background:rgba(76,195,255,.14);box-shadow:0 0 14px -6px rgba(76,195,255,.9)}",
    "#cg-station .cgst-step[aria-pressed='true']{border-color:rgba(120,224,200,.6);color:#c9fbf2;background:rgba(120,224,200,.1)}",
    "#cg-station .cgst-step svg{width:15px;height:15px;display:block}",
    "#cg-station .cgst-dots{flex:1 1 auto;display:flex;align-items:center;justify-content:center;gap:1px;min-width:0}",
    "#cg-station .cgst-pip{box-sizing:content-box;width:7px;height:7px;padding:8px 3px;border:0;border-radius:6px;cursor:pointer;",
    "background:rgba(76,195,255,.28);background-clip:content-box;transition:width .25s cubic-bezier(.16,1,.3,1),background-color .2s ease}",
    "#cg-station .cgst-pip[aria-current='true']{width:20px;background:var(--cgst-teal);background-clip:content-box}",
    "#cg-station .cgst-pos{flex:0 0 auto;min-width:30px;font-family:var(--cgst-mono);font-size:8.5px;font-weight:700;letter-spacing:.1em;",
    "color:#8fb7cc;text-align:center;font-variant-numeric:tabular-nums}",

    /* topics + links */
    "#cg-station .cgst-topics{display:flex;flex-wrap:wrap;gap:5px}",
    "#cg-station .cgst-topic{display:inline-flex;align-items:center;gap:6px;min-height:27px;padding:3px 8px;border-radius:8px;",
    "border:1px solid rgba(120,224,200,.24);background:rgba(8,20,20,.55);color:#cfeee7;text-decoration:none;font-family:var(--cgst-mono);",
    "font-size:8.5px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;transition:border-color .2s ease,background .2s ease,color .2s ease}",
    "#cg-station .cgst-topic i{font-style:normal;font-weight:700;color:var(--cgst-teal)}",
    "#cg-station .cgst-topic:hover{border-color:rgba(120,224,200,.75);background:rgba(120,224,200,.1);color:#fff}",
    "#cg-station .cgst-intel-links{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px}",
    "#cg-station .cgst-go{flex:1 1 100%;display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:38px;padding:0 12px;",
    "border-radius:11px;border:1px solid rgba(76,195,255,.6);background:linear-gradient(100deg,rgba(76,195,255,.24),rgba(120,224,200,.12));",
    "color:#fff;text-decoration:none;font-family:var(--cgst-mono);font-size:9.5px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;",
    "box-shadow:inset 0 1px 0 rgba(255,255,255,.09);transition:box-shadow .2s ease,border-color .2s ease}",
    "#cg-station .cgst-go:hover{border-color:rgba(76,195,255,.95);box-shadow:0 0 22px -6px rgba(76,195,255,.95),inset 0 1px 0 rgba(255,255,255,.12)}",
    "#cg-station .cgst-aux{padding:4px 0;border:0;border-bottom:1px solid transparent;background:none;cursor:pointer;font-family:var(--cgst-mono);",
    "font-size:8.5px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#a9cfe0;text-decoration:none}",
    "#cg-station .cgst-aux:hover{color:#fff;border-bottom-color:var(--cgst-blue)}",
    "#cg-station .cgst-sync{margin:0;font-family:var(--cgst-mono);font-size:7.5px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:#7c95a3}",

    /* Mission Feed: the Controls entry for the same desk, marked as featured */
    "#cg-station .cgst-ctl[data-cgst-feed]{border-color:rgba(76,195,255,.45);background:linear-gradient(100deg,rgba(76,195,255,.12),rgba(16,10,12,.74) 70%)}",
    "#cg-station .cgst-ctl[data-cgst-feed] .cgst-ctl-dot{background:var(--cgst-blue);box-shadow:0 0 8px rgba(76,195,255,.9)}",
    "#cg-station .cgst-state[data-hot]{border-color:rgba(238,99,101,.85);background:rgba(238,99,101,.2);color:#fff}",

    /* ── mission modules ── */
    "#cg-station .cgst-missions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}",
    "#cg-station .cgst-mission{position:relative;display:flex;flex-direction:column;align-items:flex-start;gap:3px;min-height:62px;",
    "padding:9px 10px 9px;border-radius:13px;border:1px solid var(--cgst-line);background:var(--cgst-cell);color:var(--cgst-ink);",
    "text-align:left;cursor:pointer;font-family:inherit;overflow:hidden;",
    "transition:transform .2s cubic-bezier(.16,1,.3,1),border-color .2s ease,background .2s ease,box-shadow .2s ease}",
    "#cg-station .cgst-mission::after{content:'';position:absolute;inset:0;pointer-events:none;opacity:0;",
    "background:linear-gradient(105deg,transparent 30%,rgba(76,195,255,.16) 50%,transparent 70%);transform:translateX(-100%)}",
    "#cg-station .cgst-mission:hover{transform:translateY(-1px);border-color:rgba(238,99,101,.7);background:rgba(44,20,24,.88);",
    "box-shadow:0 12px 26px -18px rgba(0,0,0,.9),0 0 20px -10px rgba(238,99,101,.7)}",
    "#cg-station .cgst-mission:hover::after{opacity:1;transform:translateX(100%);transition:transform .7s cubic-bezier(.16,1,.3,1)}",
    "#cg-station .cgst-mission .cgst-code{font-family:var(--cgst-mono);font-size:8.5px;font-weight:700;letter-spacing:.18em;color:var(--cgst-blue)}",
    "#cg-station .cgst-mission strong{display:block;font-size:13px;font-weight:750;line-height:1.2;letter-spacing:-.005em;color:#fff}",
    "#cg-station .cgst-mission small{display:block;font-family:var(--cgst-mono);font-size:8.5px;letter-spacing:.05em;color:var(--cgst-mute)}",

    /* ── controls ── */
    "#cg-station .cgst-controls{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}",
    "#cg-station .cgst-ctl{display:flex;align-items:center;gap:8px;min-height:40px;padding:6px 9px;border-radius:11px;",
    "border:1px solid rgba(238,99,101,.2);background:rgba(16,10,12,.74);color:var(--cgst-ink);text-decoration:none;text-align:left;",
    "cursor:pointer;font-family:inherit;min-width:0;transition:border-color .2s ease,background .2s ease,box-shadow .2s ease}",
    "#cg-station .cgst-ctl[hidden]{display:none}",
    "#cg-station .cgst-ctl:hover{border-color:rgba(76,195,255,.55);background:rgba(20,22,32,.8);box-shadow:0 0 16px -8px rgba(76,195,255,.8)}",
    "#cg-station .cgst-ctl-dot{flex:0 0 auto;width:6px;height:6px;border-radius:1px;background:var(--cgst-red);box-shadow:0 0 7px rgba(238,99,101,.8);transform:rotate(45deg)}",
    "#cg-station .cgst-ctl-tx{flex:1 1 auto;min-width:0}",
    "#cg-station .cgst-ctl-tx strong{display:block;font-family:var(--cgst-mono);font-size:9px;font-weight:700;letter-spacing:.14em;",
    "text-transform:uppercase;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    "#cg-station .cgst-ctl-tx small{display:block;margin-top:1px;font-size:10px;color:var(--cgst-mute);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    "#cg-station .cgst-state{flex:0 0 auto;padding:3px 6px;border-radius:6px;border:1px solid rgba(238,99,101,.4);",
    "font-family:var(--cgst-mono);font-size:8px;font-weight:700;letter-spacing:.14em;color:#e0a9ab}",
    "#cg-station .cgst-ctl[aria-pressed='true']{border-color:rgba(120,224,200,.55);background:rgba(10,24,22,.78)}",
    "#cg-station .cgst-ctl[aria-pressed='true'] .cgst-state{border-color:rgba(120,224,200,.6);background:rgba(120,224,200,.12);color:#c9fbf2}",
    "#cg-station .cgst-ctl[aria-pressed='true'] .cgst-ctl-dot{background:var(--cgst-teal);box-shadow:0 0 8px rgba(120,224,200,.9)}",

    /* ── routes, jumps, footer ── */
    "#cg-station .cgst-routes{display:flex;flex-wrap:wrap;gap:6px 14px;margin:0}",
    "#cg-station .cgst-route{font-family:var(--cgst-mono);font-size:9.5px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;",
    "color:#eab2b3;text-decoration:none;padding:4px 0;border-bottom:1px solid transparent}",
    "#cg-station .cgst-route:hover{color:#fff;border-bottom-color:var(--cgst-red)}",
    "#cg-station .cgst-jumps{display:grid;grid-template-columns:1fr 1fr;gap:7px}",
    "#cg-station .cgst-jump{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:40px;padding:0 10px;",
    "border:1px solid rgba(238,99,101,.3);border-radius:12px;background:rgba(16,10,12,.7);color:#eedcdc;cursor:pointer;",
    "font-family:var(--cgst-mono);font-size:9.5px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;",
    "transition:border-color .2s ease,background .2s ease,color .2s ease}",
    "#cg-station .cgst-jump:hover:not([disabled]){border-color:rgba(238,99,101,.75);background:rgba(238,99,101,.14);color:#fff}",
    "#cg-station .cgst-jump[disabled]{opacity:.34;cursor:default}",
    "#cg-station .cgst-foot{margin:0;padding-top:9px;border-top:1px solid rgba(255,255,255,.06);font-family:var(--cgst-mono);",
    "font-size:8px;line-height:1.5;letter-spacing:.12em;text-transform:uppercase;color:#96706f}",
    "#cg-station .cgst-keys{display:none}",
    "@media(hover:hover) and (pointer:fine){#cg-station .cgst-keys{display:inline}}",

    /* ── dock pill ── */
    "#cg-station .cgst-dock{--cgst-mx:0px;--cgst-my:0px;position:relative;display:flex;align-items:center;gap:11px;",
    "min-height:" + DOCK_H + "px;max-width:100%;padding:0 14px 0 8px;border:1px solid rgba(238,99,101,.55);border-radius:999px;",
    "cursor:pointer;text-align:left;color:var(--cgst-ink);font-family:inherit;overflow:hidden;isolation:isolate;-webkit-tap-highlight-color:transparent;",
    "background:radial-gradient(120% 160% at 12% 50%,rgba(76,195,255,.14),transparent 55%),",
    "radial-gradient(140% 130% at 92% 50%,rgba(238,99,101,.24),transparent 62%),linear-gradient(168deg,rgba(30,15,18,.96),rgba(8,6,8,.97));",
    "-webkit-backdrop-filter:blur(16px) saturate(1.45);backdrop-filter:blur(16px) saturate(1.45);",
    "box-shadow:0 18px 44px -18px rgba(0,0,0,.92),0 0 0 .5px rgba(238,99,101,.3),0 0 28px -10px rgba(238,99,101,.55),inset 0 1px 0 rgba(255,255,255,.1);",
    "transform:translate3d(var(--cgst-mx),var(--cgst-my),0);will-change:transform;",
    "transition:transform .22s cubic-bezier(.16,1,.3,1),border-color .22s ease,box-shadow .22s ease}",
    "#cg-station .cgst-dock::before{content:'';position:absolute;inset:0;z-index:-1;pointer-events:none;",
    "background:linear-gradient(105deg,transparent 35%,rgba(255,255,255,.1) 50%,transparent 65%);transform:translateX(-120%);animation:cgstSheen 6s ease-in-out infinite}",
    "@keyframes cgstSheen{0%,70%{transform:translateX(-120%)}100%{transform:translateX(120%)}}",
    "#cg-station .cgst-dock:hover{border-color:rgba(238,99,101,.9);",
    "box-shadow:0 22px 50px -18px rgba(0,0,0,.95),0 0 0 .5px rgba(238,99,101,.55),0 0 34px -8px rgba(238,99,101,.75),inset 0 1px 0 rgba(255,255,255,.13)}",
    "#cg-station .cgst-dock:active{transform:translate3d(var(--cgst-mx),var(--cgst-my),0) scale(.985)}",
    "#cg-station .cgst-dock-tx{flex:0 1 auto;min-width:0}",
    "#cg-station .cgst-dock-tx strong{display:block;font-family:var(--cgst-mono);font-size:12.5px;font-weight:700;letter-spacing:.2em;color:#fff;white-space:nowrap}",
    "#cg-station .cgst-dock-tx small{display:flex;align-items:center;gap:6px;margin-top:3px;font-family:var(--cgst-mono);font-size:8.5px;",
    "font-weight:600;letter-spacing:.18em;color:#bfe9ff;white-space:nowrap}",
    "#cg-station .cgst-chev{flex:0 0 auto;margin-left:2px;color:#e2b4b5;transition:transform .26s cubic-bezier(.16,1,.3,1)}",
    "#cg-station .cgst-chev svg{width:18px;height:18px;display:block}",
    "#cg-station[data-open='false'] .cgst-chev{transform:rotate(180deg)}",
    /* unread-brief count riding on the radar, so the desk shows while collapsed */
    "#cg-station .cgst-dock .cgst-flag{position:absolute;left:33px;top:5px;z-index:2;min-width:18px;padding:2px 5px;font-size:8px;",
    "letter-spacing:.02em;box-shadow:0 0 0 1.5px #14090c,0 0 12px -1px rgba(238,99,101,.9)}",

    /* ── Site Intelligence module ── */
    "#cg-station .cgst-nexus{position:relative;display:flex;flex-direction:column;gap:9px;padding:12px 11px 11px;border-radius:16px;overflow:hidden;isolation:isolate;",
    "border:1px solid rgba(120,224,200,.3);box-shadow:0 18px 40px -26px rgba(120,224,200,.65),inset 0 1px 0 rgba(255,255,255,.05);",
    "background:linear-gradient(rgba(120,224,200,.03) 1px,transparent 1px) 0 0/100% 16px,",
    "radial-gradient(100% 70% at 0 0,rgba(120,224,200,.15),transparent 60%),radial-gradient(90% 70% at 100% 100%,rgba(76,195,255,.12),transparent 65%),",
    "linear-gradient(165deg,#0b1314,#060708)}",
    /* a slow light pass across the module: the "ambient intelligence" cue */
    "#cg-station .cgst-nexus::before{content:'';position:absolute;inset:0;z-index:-1;pointer-events:none;",
    "background:linear-gradient(100deg,transparent 30%,rgba(120,224,200,.1) 50%,transparent 70%);transform:translateX(-110%);animation:cgstSheen 9s ease-in-out infinite}",
    "#cg-station .cgst-nexus-top{display:flex;align-items:center;gap:9px}",
    "#cg-station .cgst-nexus-title{display:flex;align-items:center;gap:8px;margin:0;font-family:var(--cgst-mono);font-size:11px;font-weight:700;",
    "line-height:1.2;letter-spacing:.26em;text-transform:uppercase;color:#fff}",
    "#cg-station .cgst-nexus-title::before{content:'';flex:0 0 auto;width:7px;height:7px;border-radius:50%;background:var(--cgst-teal);",
    "box-shadow:0 0 0 0 rgba(120,224,200,.6);animation:cgstBeat 1.6s ease-out infinite}",
    /* heartbeat: a double pulse, then rest */
    "@keyframes cgstBeat{0%{box-shadow:0 0 0 0 rgba(120,224,200,.65)}18%{box-shadow:0 0 0 5px rgba(120,224,200,0)}",
    "30%{box-shadow:0 0 0 0 rgba(120,224,200,.55)}48%,100%{box-shadow:0 0 0 6px rgba(120,224,200,0)}}",
    /* neural pulse: three nodes firing in turn along a line */
    "#cg-station .cgst-pulse{position:relative;flex:0 0 auto;display:flex;align-items:center;gap:9px;padding:0 2px}",
    "#cg-station .cgst-pulse::before{content:'';position:absolute;left:4px;right:4px;top:50%;height:1px;background:linear-gradient(90deg,rgba(120,224,200,.2),rgba(76,195,255,.5),rgba(120,224,200,.2))}",
    "#cg-station .cgst-pulse i{position:relative;width:5px;height:5px;border-radius:50%;background:var(--cgst-teal);opacity:.35;animation:cgstFire 1.8s ease-in-out infinite}",
    "#cg-station .cgst-pulse i:nth-child(2){animation-delay:.3s;background:var(--cgst-blue)}",
    "#cg-station .cgst-pulse i:nth-child(3){animation-delay:.6s}",
    "@keyframes cgstFire{0%,60%,100%{opacity:.3;transform:scale(1)}20%{opacity:1;transform:scale(1.6)}}",
    "#cg-station .cgst-idx{grid-template-columns:repeat(4,minmax(0,1fr));border-color:rgba(120,224,200,.24);background:rgba(120,224,200,.2)}",
    "#cg-station .cgst-idx .cgst-cell{background:rgba(7,16,16,.88)}",
    "#cg-station .cgst-nexus[data-state='ready'] [data-cgst-idx-state]{color:#5ef0a8}",
    "#cg-station .cgst-nexus[data-state='static'] [data-cgst-idx-state]{color:#f2b04b}",
    "#cg-station .cgst-nexus[data-state='loading'] [data-cgst-idx-state]{animation:cgstBeacon 1.2s ease-in-out infinite}",
    "#cg-station .cgst-where{margin:0;font-family:var(--cgst-mono);font-size:8px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;",
    "color:#8fb7b0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    "#cg-station .cgst-where b{color:#e6fffa;font-weight:700}",
    "#cg-station .cgst-launch{display:grid;grid-template-columns:1fr 1fr;gap:6px}",
    "#cg-station button.cgst-go{width:100%;cursor:pointer}",
    "#cg-station .cgst-launch .cgst-go{padding:0 8px;font-size:9px;letter-spacing:.12em;white-space:nowrap}",
    "#cg-station .cgst-go svg{width:15px;height:15px;display:block;flex:0 0 auto}",
    "#cg-station .cgst-mc-toggle{border-color:rgba(120,224,200,.55);background:linear-gradient(100deg,rgba(120,224,200,.2),rgba(76,195,255,.08))}",
    "#cg-station .cgst-mc-toggle svg{transition:transform .26s cubic-bezier(.16,1,.3,1)}",
    "#cg-station .cgst-mc-toggle[aria-expanded='true'] svg{transform:rotate(180deg)}",
    "#cg-station .cgst-mc{display:flex;flex-direction:column;gap:9px;padding:9px;border-radius:12px;border:1px solid rgba(120,224,200,.2);",
    "background:rgba(4,10,10,.6);animation:cgstHolo .34s cubic-bezier(.16,1,.3,1)}",
    "#cg-station .cgst-cmds{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px}",
    "#cg-station .cgst-cmd{display:flex;align-items:center;gap:7px;min-width:0;min-height:38px;padding:5px 8px;border-radius:10px;cursor:pointer;",
    "border:1px solid rgba(120,224,200,.22);background:rgba(8,18,18,.66);color:var(--cgst-ink);text-align:left;font-family:inherit;",
    "transition:border-color .2s ease,background .2s ease,box-shadow .2s ease}",
    "#cg-station .cgst-cmd::before{content:'›';flex:0 0 auto;font-family:var(--cgst-mono);font-size:13px;font-weight:700;color:var(--cgst-teal)}",
    "#cg-station .cgst-cmd:hover,#cg-station .cgst-sector:hover,#cg-station .cgst-act:hover{border-color:rgba(120,224,200,.7);background:rgba(120,224,200,.1);",
    "box-shadow:0 0 16px -8px rgba(120,224,200,.9)}",
    "#cg-station .cgst-cmd span{min-width:0}",
    "#cg-station .cgst-cmd strong{display:block;font-family:var(--cgst-mono);font-size:8.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;",
    "color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    "#cg-station .cgst-cmd small{display:block;margin-top:1px;font-size:9.5px;color:#9fbab4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    "#cg-station .cgst-sectors{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}",
    "#cg-station .cgst-sector{position:relative;display:flex;flex-direction:column;align-items:flex-start;gap:1px;min-width:0;min-height:54px;padding:6px 8px;",
    "border-radius:10px;border:1px solid rgba(76,195,255,.22);background:rgba(10,14,22,.72);color:var(--cgst-ink);text-align:left;cursor:pointer;",
    "font-family:inherit;overflow:hidden;transition:border-color .2s ease,background .2s ease,box-shadow .2s ease}",
    "#cg-station .cgst-sector .cgst-code{font-family:var(--cgst-mono);font-size:7.5px;font-weight:700;letter-spacing:.16em;color:var(--cgst-blue)}",
    "#cg-station .cgst-sector strong{display:block;max-width:100%;font-size:10.5px;font-weight:750;line-height:1.2;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    "#cg-station .cgst-sector small{display:block;max-width:100%;font-family:var(--cgst-mono);font-size:7.5px;letter-spacing:.04em;color:#8fa9b8;",
    "white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    "#cg-station .cgst-count{position:absolute;top:5px;right:7px;font-family:var(--cgst-mono);font-size:9px;font-weight:700;color:var(--cgst-teal);font-variant-numeric:tabular-nums}",
    "#cg-station .cgst-smart{display:flex;flex-wrap:wrap;gap:5px}",
    "#cg-station .cgst-act{display:inline-flex;align-items:center;min-height:28px;padding:4px 9px;border-radius:8px;cursor:pointer;",
    "border:1px solid rgba(76,195,255,.28);background:rgba(8,14,22,.72);color:#d8f1ff;font-family:var(--cgst-mono);font-size:8.5px;",
    "font-weight:700;letter-spacing:.1em;text-transform:uppercase;text-align:left;transition:border-color .2s ease,background .2s ease,box-shadow .2s ease}",

    /* ── answer card: one card, four writing modes ── */
    "#cg-station .cgst-answer{position:relative;display:flex;flex-direction:column;gap:8px;padding:11px 11px 10px;border-radius:15px;overflow:hidden;isolation:isolate;",
    "border:1px solid rgba(120,224,200,.42);box-shadow:0 18px 40px -26px rgba(120,224,200,.75),inset 0 1px 0 rgba(255,255,255,.05);",
    "background:linear-gradient(rgba(120,224,200,.035) 1px,transparent 1px) 0 0/100% 18px,",
    "radial-gradient(110% 70% at 100% 0,rgba(120,224,200,.14),transparent 60%),linear-gradient(165deg,#0c1515,#070709)}",
    /* holographic arrival: the card settles in while a scan band crosses it */
    "#cg-station .cgst-answer::after{content:'';position:absolute;left:0;right:0;top:0;height:45%;z-index:-1;pointer-events:none;opacity:0;",
    "background:linear-gradient(180deg,transparent,rgba(120,224,200,.18),transparent);transform:translateY(-100%)}",
    "#cg-station .cgst-answer.cgst-routing{animation:cgstHolo .38s cubic-bezier(.16,1,.3,1)}",
    "#cg-station .cgst-answer.cgst-routing::after{animation:cgstRoute .8s cubic-bezier(.16,1,.3,1)}",
    "@keyframes cgstHolo{from{opacity:0;transform:translateY(6px) scale(.985)}to{opacity:1;transform:none}}",
    "@keyframes cgstRoute{0%{opacity:1;transform:translateY(-100%)}100%{opacity:0;transform:translateY(240%)}}",
    "#cg-station .cgst-ans-top{display:flex;align-items:center;gap:8px;min-width:0}",
    "#cg-station .cgst-ans-kind{flex:1 1 auto;min-width:0;font-family:var(--cgst-mono);font-size:8px;font-weight:700;letter-spacing:.18em;",
    "text-transform:uppercase;color:var(--cgst-teal);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    "#cg-station .cgst-x{flex:0 0 auto;display:grid;place-items:center;width:26px;height:26px;padding:0;border-radius:8px;cursor:pointer;",
    "border:1px solid rgba(120,224,200,.3);background:rgba(8,16,16,.7);color:#cfeee7}",
    "#cg-station .cgst-x svg{width:14px;height:14px;display:block}",
    "#cg-station .cgst-modes{display:flex;flex-wrap:wrap;gap:3px}",
    "#cg-station .cgst-mode{padding:3px 7px;border-radius:7px;cursor:pointer;border:1px solid rgba(120,224,200,.2);background:transparent;",
    "color:#9fc9c1;font-family:var(--cgst-mono);font-size:7.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase}",
    "#cg-station .cgst-mode[aria-pressed='true']{border-color:rgba(120,224,200,.75);background:rgba(120,224,200,.16);color:#fff}",
    "#cg-station .cgst-ans-title{margin:0;font-size:15px;font-weight:750;line-height:1.25;letter-spacing:-.01em;color:#fff;outline:none}",
    "#cg-station .cgst-ans-lede{margin:0;font-size:12.5px;line-height:1.45;color:#d3e2df}",
    "#cg-station .cgst-ans-lede strong,#cg-station .cgst-steps strong,#cg-station .cgst-bullets strong{color:#fff;font-weight:750}",
    "#cg-station .cgst-ans-body{display:flex;flex-direction:column;gap:9px;min-width:0}",
    "#cg-station .cgst-ans-h{margin:0 0 5px;font-family:var(--cgst-mono);font-size:7.5px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#8fc4bb}",
    "#cg-station .cgst-ans-list{display:flex;flex-direction:column;gap:4px;margin:0;padding:0;list-style:none}",
    "#cg-station .cgst-ans-row{display:flex;flex-direction:column;gap:2px;width:100%;min-width:0;padding:7px 9px;border-radius:10px;cursor:pointer;",
    "border:1px solid rgba(120,224,200,.18);background:rgba(8,16,16,.58);color:var(--cgst-ink);text-decoration:none;text-align:left;font-family:inherit;",
    "transition:border-color .2s ease,background .2s ease}",
    "#cg-station .cgst-ans-row:hover{border-color:rgba(120,224,200,.65);background:rgba(120,224,200,.09)}",
    "#cg-station .cgst-ans-row strong{font-size:12.5px;font-weight:700;line-height:1.25;color:#fff}",
    "#cg-station .cgst-ans-row small{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;font-size:10.5px;line-height:1.35;color:#aec5c0}",
    "#cg-station .cgst-ans-meta{font-family:var(--cgst-mono);font-size:7.5px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#7fd3c1}",
    "#cg-station .cgst-ans-row[data-here] {border-color:rgba(120,224,200,.7);box-shadow:inset 2px 0 0 var(--cgst-teal)}",
    "#cg-station .cgst-table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:10.5px;line-height:1.3;color:#d9e6e3}",
    "#cg-station .cgst-table th{padding:0 5px 5px 0;font-family:var(--cgst-mono);font-size:7px;font-weight:700;letter-spacing:.16em;",
    "text-transform:uppercase;text-align:left;color:#7fa9a1;border-bottom:1px solid rgba(120,224,200,.22)}",
    "#cg-station .cgst-table td{padding:5px 5px 5px 0;vertical-align:top;border-bottom:1px solid rgba(255,255,255,.05);overflow:hidden;text-overflow:ellipsis;word-break:break-word}",
    "#cg-station .cgst-table a{color:#fff;font-weight:700;text-decoration:none;border-bottom:1px solid rgba(120,224,200,.35)}",
    "#cg-station .cgst-table code{font-family:var(--cgst-mono);font-size:9px;color:#9fd8cc}",
    "#cg-station .cgst-table .cgst-num{text-align:right;font-family:var(--cgst-mono);font-variant-numeric:tabular-nums}",
    "#cg-station .cgst-table[data-cols='pages'] th:nth-child(1){width:40%}#cg-station .cgst-table[data-cols='pages'] th:nth-child(2){width:32%}",
    "#cg-station .cgst-table[data-cols='spread'] th:nth-child(1){width:62%}",
    "#cg-station .cgst-tree{display:flex;flex-direction:column;margin:0;padding:0;list-style:none;font-family:var(--cgst-mono);font-size:10px;line-height:1.55;color:#cfe5e0}",
    "#cg-station .cgst-tree li{display:flex;align-items:baseline;gap:5px;min-width:0}",
    "#cg-station .cgst-glyph{flex:0 0 auto;color:#5f8f86;white-space:pre}",
    "#cg-station .cgst-tree a,#cg-station .cgst-tree button{min-width:0;padding:0;border:0;background:none;cursor:pointer;font:inherit;color:#e8fff9;",
    "text-align:left;text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    "#cg-station .cgst-tree a:hover,#cg-station .cgst-tree button:hover{color:#fff;text-decoration:underline}",
    "#cg-station .cgst-tree i{flex:0 0 auto;font-style:normal;color:var(--cgst-teal)}",
    "#cg-station .cgst-tree [data-here]{color:#fff;font-weight:700}",
    "#cg-station .cgst-tree [data-here]::after{content:' ◉ here';color:var(--cgst-teal)}",
    "#cg-station .cgst-facts{display:grid;grid-template-columns:auto minmax(0,1fr);gap:6px 10px;margin:0}",
    "#cg-station .cgst-facts dt{font-family:var(--cgst-mono);font-size:7.5px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#7fa9a1;padding-top:2px}",
    "#cg-station .cgst-facts dd{margin:0;font-size:11.5px;line-height:1.4;color:#e6eeec}",
    "#cg-station .cgst-facts a,#cg-station .cgst-steps a,#cg-station .cgst-bullets a,#cg-station .cgst-nextline a{color:#fff;font-weight:700;text-decoration:none;",
    "border-bottom:1px solid rgba(120,224,200,.45)}",
    "#cg-station .cgst-steps{display:flex;flex-direction:column;gap:6px;margin:0;padding:0;list-style:none;counter-reset:cgstep}",
    "#cg-station .cgst-steps li{position:relative;padding-left:26px;font-size:11.5px;line-height:1.4;color:#dce8e5;counter-increment:cgstep}",
    "#cg-station .cgst-steps li::before{content:counter(cgstep);position:absolute;left:0;top:0;display:grid;place-items:center;width:18px;height:18px;",
    "border-radius:50%;border:1px solid rgba(120,224,200,.55);font-family:var(--cgst-mono);font-size:9px;font-weight:700;color:var(--cgst-teal)}",
    "#cg-station .cgst-bullets{display:flex;flex-direction:column;gap:5px;margin:0;padding:0;list-style:none}",
    "#cg-station .cgst-bullets li{position:relative;padding-left:14px;font-size:11.5px;line-height:1.4;color:#dce8e5}",
    "#cg-station .cgst-bullets li::before{content:'';position:absolute;left:1px;top:6px;width:5px;height:5px;background:var(--cgst-teal);transform:rotate(45deg)}",
    "#cg-station .cgst-lines{margin:0;padding:1px 0 1px 10px;border-left:2px solid rgba(120,224,200,.6);font-family:'Cormorant Garamond',Georgia,serif;",
    "font-size:14px;font-style:italic;line-height:1.35;color:#dfe9e6}",
    "#cg-station .cgst-lines p{margin:0 0 5px;line-height:1.35}#cg-station .cgst-lines p:last-child{margin:0}",
    "#cg-station .cgst-note{display:flex;flex-direction:column;gap:3px;margin:0;padding:0;list-style:none;font-size:10.5px;line-height:1.4;color:#e1c890}",
    "#cg-station .cgst-note li::before{content:'Assumed · ';font-family:var(--cgst-mono);font-size:7.5px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#f2b04b}",
    "#cg-station .cgst-nextline{margin:0;font-size:11.5px;line-height:1.4;color:#dce8e5}",
    "#cg-station .cgst-nextline b{font-family:var(--cgst-mono);font-size:7.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--cgst-teal);margin-right:6px}",
    "#cg-station .cgst-ans-acts{display:flex;flex-wrap:wrap;gap:5px}",
    "#cg-station .cgst-ans-acts .cgst-act:first-child{border-color:rgba(120,224,200,.6);background:rgba(120,224,200,.13);color:#fff}",
    "#cg-station .cgst-basis{margin:0;padding-top:7px;border-top:1px solid rgba(255,255,255,.06);font-family:var(--cgst-mono);font-size:7.5px;",
    "font-weight:600;line-height:1.5;letter-spacing:.12em;text-transform:uppercase;color:#6f8c86}",

    /* ── dock rail: Intelligence Graph orb beside the pill ── */
    "#cg-station>.cgst-rail{display:flex;align-items:center;gap:8px;max-width:100%;pointer-events:none}",
    "#cg-station .cgst-rail>*{pointer-events:auto}",
    "#cg-station .cgst-orb{position:relative;flex:0 0 auto;display:grid;place-items:center;width:46px;height:46px;padding:0;border-radius:50%;cursor:pointer;",
    "border:1px solid rgba(76,195,255,.55);color:#d8f1ff;overflow:hidden;isolation:isolate;-webkit-tap-highlight-color:transparent;",
    "background:radial-gradient(circle at 50% 42%,rgba(76,195,255,.22),transparent 66%),linear-gradient(168deg,rgba(14,20,30,.97),rgba(6,7,10,.98));",
    "box-shadow:0 14px 34px -16px rgba(0,0,0,.92),0 0 22px -8px rgba(76,195,255,.65),inset 0 1px 0 rgba(255,255,255,.1);",
    "transition:transform .2s cubic-bezier(.16,1,.3,1),box-shadow .2s ease,border-color .2s ease}",
    "#cg-station .cgst-orb::before{content:'';position:absolute;inset:0;z-index:-1;border-radius:50%;",
    "background:conic-gradient(from 0deg,transparent 0 68%,rgba(76,195,255,.5) 86%,transparent);animation:cgstSweep 5s linear infinite}",
    "#cg-station .cgst-orb svg{width:21px;height:21px;display:block}",
    "#cg-station .cgst-orb:hover{transform:translateY(-1px);border-color:rgba(76,195,255,.95);box-shadow:0 18px 38px -16px rgba(0,0,0,.95),0 0 28px -6px rgba(76,195,255,.85)}",
    "#cg-station[data-fit='compact'] .cgst-dock{padding:0 7px}",
    "#cg-station[data-fit='compact'] .cgst-dock-tx,#cg-station[data-fit='compact'] .cgst-chev{display:none}",

    /* ── Intelligence Graph: a full-screen dialog over the page ── */
    "#cg-station .cgst-graph{position:fixed;inset:0;z-index:5;display:flex;align-items:center;justify-content:center;",
    "padding:max(12px,env(safe-area-inset-top)) max(12px,env(safe-area-inset-right)) max(12px,env(safe-area-inset-bottom)) max(12px,env(safe-area-inset-left));",
    "background:radial-gradient(80% 60% at 50% 40%,rgba(76,195,255,.12),transparent 70%),rgba(3,4,8,.9);color:var(--cgst-ink);font-family:var(--cgst-sans);",
    "-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px)}",
    "#cg-station .cgst-gframe{position:relative;display:grid;grid-template-rows:auto minmax(0,1fr) auto;gap:10px;width:min(1180px,100%);height:min(820px,100%);",
    "padding:14px;border-radius:20px;border:1px solid rgba(76,195,255,.4);overflow:hidden;isolation:isolate;",
    "background:linear-gradient(170deg,#0a0e17,#050508);box-shadow:0 40px 90px -30px rgba(0,0,0,.95),0 0 0 .5px rgba(76,195,255,.3),0 0 60px -22px rgba(76,195,255,.55);",
    "animation:cgstHolo .36s cubic-bezier(.16,1,.3,1)}",
    "#cg-station .cgst-ghead{display:flex;align-items:flex-start;gap:12px;min-width:0}",
    "#cg-station .cgst-ghead>div:first-child{flex:1 1 auto;min-width:0}",
    "#cg-station .cgst-gtitle{margin:0;font-family:var(--cgst-mono);font-size:16px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#fff;outline:none}",
    "#cg-station .cgst-gsub{margin:4px 0 0;font-family:var(--cgst-mono);font-size:8.5px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#8fb7cc}",
    "#cg-station .cgst-gtools{flex:0 0 auto;display:flex;gap:5px}",
    "#cg-station .cgst-gtool{display:grid;place-items:center;min-width:34px;height:34px;padding:0 9px;border-radius:10px;cursor:pointer;",
    "border:1px solid rgba(76,195,255,.35);background:rgba(10,14,22,.85);color:#d8f1ff;font-family:var(--cgst-mono);font-size:13px;font-weight:700}",
    "#cg-station .cgst-gtool:hover{border-color:rgba(76,195,255,.9);background:rgba(76,195,255,.14)}",
    "#cg-station .cgst-gtool svg{width:16px;height:16px;display:block}",
    "#cg-station .cgst-gbody{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:12px;min-height:0}",
    "#cg-station .cgst-gview{position:relative;min-height:0;border-radius:16px;border:1px solid rgba(76,195,255,.22);overflow:hidden;isolation:isolate;",
    "touch-action:none;cursor:grab;outline:none;",
    "background:radial-gradient(circle at 50% 50%,rgba(238,99,101,.1),transparent 34%),radial-gradient(circle at 50% 50%,rgba(76,195,255,.1),transparent 62%),#05070c}",
    "#cg-station .cgst-gview:focus-visible{box-shadow:0 0 0 2px #fff}",
    "#cg-station .cgst-gview[data-drag='1']{cursor:grabbing}",
    /* quantum grid: a receding lattice drifting toward the viewer */
    "#cg-station .cgst-gview::before{content:'';position:absolute;left:-40%;right:-40%;top:42%;bottom:-70%;z-index:-1;pointer-events:none;opacity:.75;",
    "background:linear-gradient(rgba(76,195,255,.09) 1px,transparent 1px) 0 0/46px 46px,linear-gradient(90deg,rgba(76,195,255,.09) 1px,transparent 1px) 0 0/46px 46px;",
    "transform:perspective(520px) rotateX(62deg);transform-origin:50% 0;animation:cgstGrid 14s linear infinite}",
    "@keyframes cgstGrid{from{transform:perspective(520px) rotateX(62deg) translateY(0)}to{transform:perspective(520px) rotateX(62deg) translateY(46px)}}",
    "#cg-station .cgst-gview::after{content:'';position:absolute;inset:0;z-index:-1;pointer-events:none;",
    "background:linear-gradient(rgba(76,195,255,.04) 1px,transparent 1px) 0 0/100% 4px}",
    "#cg-station .cgst-gsvg{position:relative;display:block;width:100%;height:100%;user-select:none;-webkit-user-select:none}",
    "#cg-station .cgst-gsvg text{font-family:var(--cgst-mono);fill:#dbe9f5;pointer-events:none}",
    "#cg-station .cgst-gorbit{fill:none;stroke:rgba(76,195,255,.16);stroke-width:1;stroke-dasharray:2 7;vector-effect:non-scaling-stroke}",
    "#cg-station .cgst-gspoke{stroke:rgba(238,99,101,.32);stroke-width:1.1;vector-effect:non-scaling-stroke}",
    "#cg-station .cgst-gspoke.cgst-gon{stroke:var(--h);stroke-width:1.8;stroke-dasharray:7 9;animation:cgstFlow 1s linear infinite}",
    "#cg-station .cgst-gedge{stroke:rgba(76,195,255,.15);stroke-width:.8;vector-effect:non-scaling-stroke}",
    "#cg-station .cgst-gedge.cgst-gon{stroke:var(--h);stroke-opacity:.55}",
    "#cg-station .cgst-glink{fill:none;stroke:var(--cgst-teal);stroke-width:1.4;stroke-dasharray:6 8;vector-effect:non-scaling-stroke;animation:cgstFlow 1.2s linear infinite}",
    "@keyframes cgstFlow{to{stroke-dashoffset:-32}}",
    "#cg-station .cgst-gcluster{cursor:pointer;outline:none}",
    "#cg-station .cgst-gcluster .cgst-gdisc{fill:#0b0e16;stroke:var(--h);stroke-width:1.6;vector-effect:non-scaling-stroke}",
    "#cg-station .cgst-gcluster .cgst-ghalo{fill:var(--h);opacity:0;transform-box:fill-box;transform-origin:center;transition:opacity .2s ease}",
    "#cg-station .cgst-gcluster:hover .cgst-ghalo,#cg-station .cgst-gcluster:focus-visible .cgst-ghalo{opacity:.2}",
    "#cg-station .cgst-gcluster:focus-visible .cgst-gdisc{stroke:#fff;stroke-width:2.6}",
    "#cg-station .cgst-gcluster.cgst-gon .cgst-ghalo{opacity:.28;animation:cgstNode 2.4s ease-in-out infinite}",
    "@keyframes cgstNode{50%{transform:scale(1.35);opacity:.1}}",
    "#cg-station .cgst-gcl{font-size:calc(9.5px * var(--gs,1));font-weight:700;letter-spacing:.1em;fill:#fff}",
    "#cg-station .cgst-gcn{font-size:calc(8px * var(--gs,1));font-weight:700;fill:var(--h)}",
    "#cg-station .cgst-gnode{cursor:pointer;outline:none;transition:opacity .2s ease}",
    "#cg-station .cgst-gnode circle{fill:var(--h);opacity:.85}",
    "#cg-station .cgst-gnode[data-hub] circle{stroke:#fff;stroke-width:1;vector-effect:non-scaling-stroke}",
    "#cg-station .cgst-gnode:focus-visible circle{stroke:#fff;stroke-width:2.4;opacity:1}",
    "#cg-station .cgst-glabel{font-size:calc(9px * var(--gs,1));opacity:0;transition:opacity .18s ease}",
    "#cg-station .cgst-gnode:hover .cgst-glabel,#cg-station .cgst-gnode:focus .cgst-glabel,#cg-station .cgst-gnode.cgst-gon .cgst-glabel,",
    "#cg-station .cgst-gnode.cgst-ghit .cgst-glabel,#cg-station .cgst-gnode.cgst-ghere .cgst-glabel{opacity:1}",
    "#cg-station .cgst-gnode.cgst-gon[data-dense]:not(:hover):not(:focus):not(.cgst-ghit) .cgst-glabel{opacity:0}",
    "#cg-station .cgst-gsvg[data-dim='1'] .cgst-gnode:not(.cgst-gon):not(.cgst-ghit):not(.cgst-ghere){opacity:.16}",
    "#cg-station .cgst-gsvg[data-dim='1'] .cgst-gedge:not(.cgst-gon){opacity:.25}",
    "#cg-station .cgst-gnode.cgst-ghit circle{fill:#fff}",
    "#cg-station .cgst-gping{fill:none;stroke:#fff;stroke-width:1.2;vector-effect:non-scaling-stroke;transform-box:fill-box;transform-origin:center;",
    "animation:cgstPing 2.2s ease-out infinite}",
    "@keyframes cgstPing{0%{transform:scale(.6);opacity:.95}100%{transform:scale(2.8);opacity:0}}",
    "#cg-station .cgst-gcore{cursor:pointer;outline:none}",
    "#cg-station .cgst-gcore .cgst-gpulse{fill:none;stroke:rgba(76,195,255,.55);stroke-width:1.2;vector-effect:non-scaling-stroke;",
    "transform-box:fill-box;transform-origin:center;animation:cgstPing 3.2s ease-out infinite}",
    "#cg-station .cgst-gcore .cgst-gpulse+.cgst-gpulse{animation-delay:1.6s}",
    "#cg-station .cgst-gsweep{transform-box:view-box;transform-origin:500px 500px;animation:cgstSweep 4.5s linear infinite}",
    "#cg-station .cgst-gcore:focus-visible .cgst-gdisc{stroke:#fff;stroke-width:2.6}",
    "#cg-station .cgst-gside{display:flex;flex-direction:column;gap:9px;min-height:0;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;",
    "scrollbar-color:rgba(76,195,255,.4) transparent;padding:1px 3px 2px 1px}",
    "#cg-station .cgst-gfind{display:flex;align-items:center;gap:8px;padding:4px 5px 4px 11px;border-radius:12px;border:1px solid rgba(76,195,255,.4);",
    "background:rgba(8,12,20,.9)}",
    "#cg-station .cgst-gfind:focus-within{border-color:rgba(76,195,255,.95);box-shadow:0 0 0 3px rgba(76,195,255,.18)}",
    "#cg-station .cgst-gfind input{flex:1 1 auto;min-width:0;height:34px;border:0;outline:0;color:#fff;font:600 16px/1.2 var(--cgst-sans);",
    "background:transparent!important;box-shadow:none!important;-webkit-appearance:none;appearance:none}",
    "#cg-station .cgst-gfind input::placeholder{color:#6f8fa3;opacity:1}",
    "#cg-station .cgst-gpath{margin:0;font-family:var(--cgst-mono);font-size:8.5px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#8fb7cc}",
    "#cg-station .cgst-gpath b{color:#fff}",
    "#cg-station .cgst-gfoot{margin:0;font-family:var(--cgst-mono);font-size:8px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:#6d8797}",
    "@media(max-width:760px){#cg-station .cgst-gframe{height:100%;padding:11px;border-radius:16px}",
    "#cg-station .cgst-gbody{grid-template-columns:1fr;grid-template-rows:minmax(0,1.2fr) minmax(0,1fr)}",
    "#cg-station .cgst-gtitle{font-size:13px;letter-spacing:.16em}#cg-station .cgst-gtool{min-width:32px;height:32px;padding:0 7px}",
    "#cg-station .cgst-ghead .cgst-org,#cg-station .cgst-gfoot{display:none}#cg-station .cgst-gsub{font-size:7.5px;letter-spacing:.1em}}",
    "html.cgst-graph-open{overflow:hidden}",
    "@media(max-width:372px){#cg-station .cgst-sectors{grid-template-columns:repeat(2,minmax(0,1fr))}#cg-station .cgst-cmds{grid-template-columns:1fr}}",

    /* ── focus ── */
    "#cg-station button:focus-visible,#cg-station a:focus-visible,#cg-station .cgst-head:focus-visible{outline:2px solid #fff;outline-offset:3px}",
    "#cg-station .cgst-gsvg a:focus-visible,#cg-station .cgst-gsvg [tabindex]:focus-visible{outline:none}",

    /* ── yield entirely while the Sentinel conversation is open ── */
    /* descendants re-assert visibility and pointer-events, so hide the whole
       subtree or an invisible sheet keeps catching taps over the modal */
    "body.sentinel-open #cg-station,body.sentinel-open #cg-station *,",
    "body.mobile-nav-open #cg-station,body.mobile-nav-open #cg-station *{opacity:0;visibility:hidden!important;pointer-events:none!important}",

    /* ── one control surface: absorb the widgets this dock replaces ──
       Hidden, never removed: each original stays the source of truth for its
       own state and is driven from here. The security stack is only absorbed
       when Stealth Glass is all it holds (see syncStack); otherwise it sits
       clear of the dock. */
    "body.cg-station-mounted .sentinel-launcher,",
    "body.cg-station-mounted #cg-top,body.cg-station-mounted #cg-bottom,",
    "body.cgst-has-tactical .cgm-motion-toggle,",
    "body.cgst-absorb-stack #cg-security-stack{display:none!important}",
    "body.cg-station-mounted #cg-security-stack{",
    "bottom:calc(max(12px,env(safe-area-inset-bottom)) + var(--cgst-lift,66px))!important}",
    /* reserve the corner so the dock never sits on top of the last content;
       a full-viewport page (data-fit="fixed") has no last content to clear */
    "body.cg-station-mounted:not(.cgst-fixed){padding-bottom:calc(var(--cgst-lift,66px) + 22px + env(safe-area-inset-bottom))}",
    "body.cg-station-mounted:not(.cgst-absorb-stack):not(.cgst-fixed){padding-bottom:calc(var(--cgst-lift,66px) + var(--cgst-stack-h,52px) + 30px + env(safe-area-inset-bottom))}",
    /* the commerce dock (logo-badge.js, every page but home) pins itself to the
       same corner; it rides one row above the console, the security stack one
       row above that, and the phone sales panel opens above both */
    "body.cg-station-mounted #cg-dock{right:max(12px,env(safe-area-inset-right))!important;bottom:calc(max(12px,env(safe-area-inset-bottom)) + var(--cgst-lift,66px))!important}",
    "body.cg-station-mounted.cg-dock-mounted.cg-security-dock-mounted #cg-security-stack{bottom:calc(max(12px,env(safe-area-inset-bottom)) + var(--cgst-lift,66px) + 64px)!important}",
    "body.cg-station-mounted.cg-dock-mounted:not(.cgst-fixed){padding-bottom:calc(var(--cgst-lift,66px) + 64px + var(--cgst-stack-h,52px) + 30px + env(safe-area-inset-bottom))}",
    "@media(max-width:640px){body.cg-station-mounted #cg-sales-panel{bottom:calc(68px + var(--cgst-lift,66px))!important}}",
    /* command-center.js toasts float above the docks; the Insights hub's
       reading controls take the free corner on narrow screens */
    "body.cg-station-mounted #cc-toasts{bottom:calc(max(12px,env(safe-area-inset-bottom)) + var(--cgst-lift,66px) + 64px)}",
    "@media(max-width:980px){body.cg-station-mounted .future-controls{right:auto;left:14px}}",

    /* ── stealth skin ── */
    "[data-skin='stealth'] #cg-station .cgst-sheet,[data-skin='stealth'] #cg-station .cgst-dock{",
    "border-color:rgba(120,224,200,.36);box-shadow:0 20px 48px -20px rgba(0,0,0,.94),0 0 0 .5px rgba(120,224,200,.22)}",

    /* ── narrow phones ── */
    "@media(max-width:420px){#cg-station{width:calc(100vw - 20px)}",
    "#cg-station .cgst-sheet{padding:12px 11px 11px;gap:11px}",
    "#cg-station .cgst-title{font-size:14px;letter-spacing:.17em}",
    "#cg-station .cgst-mission strong{font-size:12.5px}}",
    "@media(max-width:372px){#cg-station .cgst-controls{grid-template-columns:1fr}}",
    "@media(max-width:340px){#cg-station .cgst-missions{grid-template-columns:1fr}",
    "#cg-station .cgst-cell{padding:7px 6px}#cg-station .cgst-cell dd{letter-spacing:0}}",

    /* motion: the OS preference and the site's own Tactical View both quiet it */
    "@media(prefers-reduced-motion:reduce){#cg-station *,#cg-station *::before,#cg-station *::after{transition:none!important;animation:none!important}",
    "#cg-station[data-open='false'] .cgst-sheet{transform:none}}",
    "html[data-cgm-motion='reduced'] #cg-station *,html[data-cgm-motion='reduced'] #cg-station *::before,",
    "html[data-cgm-motion='reduced'] #cg-station *::after{animation:none!important;transition:none!important}",
    "html[data-cgm-motion='reduced'] #cg-station[data-open='false'] .cgst-sheet{transform:none}",
    "@media print{#cg-station{display:none!important}}",
    "@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){",
    "#cg-station .cgst-sheet{background-color:#0c080a}",
    "#cg-station .cgst-dock{background:linear-gradient(168deg,rgba(30,15,18,.99),rgba(8,6,8,.99))}}"
  ].join("");

  function injectStyle() {
    if (document.getElementById("cg-station-style")) return;
    var style = document.createElement("style");
    style.id = "cg-station-style";
    style.textContent = CSS;
    (document.head || document.documentElement).appendChild(style);
  }

  // ── state ────────────────────────────────────────────────────────────────
  // First visit: open on wide screens, collapsed on phones, where an open
  // console would cover the page the visitor came to read.
  function narrow() {
    try {
      return window.matchMedia("(max-width: 720px), (max-height: 500px), (hover: none) and (pointer: coarse)").matches;
    } catch (e) { return false; }
  }
  function readOpen() {
    try {
      var v = localStorage.getItem(STORE_OPEN);
      if (v !== null) return v === "1";
    } catch (e) {}
    return !narrow();
  }
  function writeOpen(v) { try { localStorage.setItem(STORE_OPEN, v ? "1" : "0"); } catch (e) {} }

  var root, panel, dock, askForm, askInput, statusType, statusSr, dockStatus;
  var stealthCtl, tacticalCtl, jumpTop, jumpBottom, linkCell, clockCell;
  var lastFocus = null, clockTimer = 0, typeTimer = 0;

  function sessionId() {
    var api = window.__cgSentinel;
    if (api && api.session) return api.session;
    var bytes = new Uint8Array(2);
    try { window.crypto.getRandomValues(bytes); }
    catch (e) { bytes[0] = Math.floor(Math.random() * 256); bytes[1] = Math.floor(Math.random() * 256); }
    return "CG-SNT-" + Array.prototype.map.call(bytes, function (b) { return ("0" + b.toString(16)).slice(-2); }).join("").toUpperCase();
  }

  // ── Sentinel hand-off ────────────────────────────────────────────────────
  // sentinel.js exposes __cgSentinel, which opens the conversation itself.
  // Clicking [data-sentinel-open] would route through the site directory
  // first, so that is only the fallback for an older sentinel.js.
  function openSentinel(prompt) {
    var api = window.__cgSentinel;
    if (api && typeof api.open === "function") {
      if (prompt && typeof api.ask === "function") api.ask(prompt);
      else api.open();
      return true;
    }
    var btn = document.querySelector("[data-sentinel-open]");
    if (btn) { btn.click(); return true; }
    var shell = document.getElementById("sentinelShell");
    if (shell) {                                  // last resort: reveal the shell
      shell.hidden = false;
      document.body.classList.add("sentinel-open");
      var close = shell.querySelector("[data-sentinel-close]");
      if (close && close.focus) close.focus();
      return true;
    }
    // No conversation on this page: carry the question to the home page's.
    handoff(prompt);
    return true;
  }

  // ── Stealth Glass mirror ─────────────────────────────────────────────────
  function stealthButton() { return document.getElementById("cg-stealth-btn"); }
  // Only offered where stealth-glass.js runs; elsewhere the chip would do nothing.
  function stealthAvailable() { return !!(stealthButton() || document.querySelector('script[src*="stealth-glass"]')); }

  function stealthActive() {
    var btn = stealthButton();
    if (btn) return btn.getAttribute("aria-pressed") === "true";
    try { return localStorage.getItem(STEALTH_KEY) === "on"; } catch (e) { return false; }
  }

  function toggleStealth() {
    var btn = stealthButton();
    if (btn) { btn.click(); return; }
    // stealth-glass.js has not mounted yet; nudge it once it does.
    var tries = 0;
    var timer = setInterval(function () {
      var late = stealthButton();
      if (late) { clearInterval(timer); late.click(); }
      else if (++tries > 20) clearInterval(timer);
    }, 100);
  }

  // ── Tactical View mirror (clearglass-motion.js "Reduce visual effects") ──
  function motionToggle() { return document.querySelector("[data-cgm-motion-toggle]"); }
  function tacticalActive() { return document.documentElement.getAttribute("data-cgm-motion") === "reduced"; }
  function toggleTactical() { var btn = motionToggle(); if (btn) btn.click(); }

  // Idempotent on purpose: this runs from a MutationObserver, so writing
  // unchanged values back into the DOM would feed the observer its own output.
  function setState(ctl, on) {
    if (!ctl) return;
    var label = on ? "ON" : "OFF";
    var badge = ctl.querySelector(".cgst-state");
    if (badge && badge.textContent !== label) badge.textContent = label;
    if (ctl.getAttribute("aria-pressed") !== String(on)) ctl.setAttribute("aria-pressed", String(on));
  }
  function paintToggles() {
    if (stealthCtl) {
      var hasStealth = stealthAvailable();
      if (stealthCtl.hidden === hasStealth) stealthCtl.hidden = !hasStealth;
    }
    setState(stealthCtl, stealthActive());
    if (tacticalCtl) {
      var available = !!motionToggle();
      if (tacticalCtl.hidden === available) tacticalCtl.hidden = !available;
      document.body.classList.toggle("cgst-has-tactical", available);
      setState(tacticalCtl, tacticalActive());
    }
  }

  // ── security stack: absorb it only when Stealth Glass is all it holds ────
  function syncStack() {
    var stack = document.getElementById("cg-security-stack");
    var h = 0, absorb = false;
    if (stack) {
      absorb = !Array.prototype.some.call(stack.children, function (el) { return el.id !== "cg-stealth-btn"; });
      if (!absorb) h = Math.round(stack.getBoundingClientRect().height);
    }
    document.body.classList.toggle("cgst-absorb-stack", absorb);
    document.documentElement.style.setProperty("--cgst-stack-h", (h || 52) + "px");
    // documented hook honoured by stealth-glass.js when it runs standalone
    document.documentElement.style.setProperty("--cg-security-bottom", (DOCK_H + 22) + "px");
  }

  // ── readiness: every value here is known locally and true ────────────────
  function online() { return navigator.onLine !== false; }
  function statusText() { return (online() ? "ONLINE" : "OFFLINE") + " · ACTIVE · READY"; }

  function paintLink() {
    var state = online() ? "online" : "offline";
    if (root.getAttribute("data-link") !== state) root.setAttribute("data-link", state);
    if (linkCell) linkCell.textContent = state.toUpperCase();
    var text = statusText();
    if (statusSr) statusSr.textContent = "Status: " + text.toLowerCase().replace(/ · /g, ", ");
    if (dockStatus) dockStatus.textContent = (online() ? "ONLINE" : "OFFLINE") + " · READY";
    if (statusType && !typeTimer) statusType.textContent = text;
  }

  function quiet() { return reduce || tacticalActive(); }

  function typeStatus() {
    if (!statusType) return;
    var full = statusText();
    clearInterval(typeTimer); typeTimer = 0;
    if (quiet()) { statusType.textContent = full; return; }
    var i = 0;
    statusType.textContent = "";
    typeTimer = setInterval(function () {
      i += 2;
      statusType.textContent = full.slice(0, i);
      if (i >= full.length) { clearInterval(typeTimer); typeTimer = 0; }
    }, 34);
  }

  function tick() {
    if (clockCell) clockCell.textContent = new Date().toISOString().slice(11, 19) + "Z";
  }
  // The clock only runs while someone can see it.
  function syncClock() {
    var run = root && root.getAttribute("data-open") === "true" && !document.hidden &&
      !document.body.classList.contains("sentinel-open");
    if (run && !clockTimer) { tick(); clockTimer = setInterval(tick, 1000); }
    else if (!run && clockTimer) { clearInterval(clockTimer); clockTimer = 0; }
  }

  // ── scroll jumps + progress ring ─────────────────────────────────────────
  function scrollTo(y) {
    try { window.scrollTo({ top: y, behavior: quiet() ? "auto" : "smooth" }); }
    catch (e) { window.scrollTo(0, y); }
  }
  function docHeight() {
    var d = document.documentElement, b = document.body;
    return Math.max(d.scrollHeight, b ? b.scrollHeight : 0, d.offsetHeight, b ? b.offsetHeight : 0);
  }

  var scrollFrame = 0;
  function syncScroll() {
    scrollFrame = 0;
    var y = window.pageYOffset || document.documentElement.scrollTop || 0;
    var max = Math.max(1, docHeight() - window.innerHeight);
    var pct = Math.max(0, Math.min(100, (y / max) * 100));
    if (root) root.style.setProperty("--cgst-progress", pct.toFixed(1));
    if (jumpTop) jumpTop.disabled = y < 24;
    if (jumpBottom) jumpBottom.disabled = y > max - 24;
  }
  function queueScroll() { if (!scrollFrame) scrollFrame = requestAnimationFrame(syncScroll); }

  // ── magnetize (matches the Stealth Glass pill's feel) ────────────────────
  function magnetize(el) {
    if (reduce) return;
    var raf = 0, mx = 0, my = 0;
    function flush() {
      raf = 0;
      el.style.setProperty("--cgst-mx", mx.toFixed(2) + "px");
      el.style.setProperty("--cgst-my", my.toFixed(2) + "px");
    }
    el.addEventListener("pointermove", function (event) {
      if (event.pointerType !== "mouse") return;
      var rect = el.getBoundingClientRect();
      mx = Math.max(-1, Math.min(1, (event.clientX - (rect.left + rect.width / 2)) / (rect.width / 2))) * 2.5;
      my = Math.max(-1, Math.min(1, (event.clientY - (rect.top + rect.height / 2)) / (rect.height / 2))) * 2.5;
      if (!raf) raf = requestAnimationFrame(flush);
    });
    el.addEventListener("pointerleave", function () {
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
      mx = my = 0;
      el.style.setProperty("--cgst-mx", "0px");
      el.style.setProperty("--cgst-my", "0px");
    });
  }

  // ── Intel Desk: feed ─────────────────────────────────────────────────────
  var intel = { state: "idle", all: [], picks: [], topics: [], latest: null, updated: "", at: 0,
    hold: false, hover: false, focus: false };
  var intelEl, briefEl, timerEl, intelLive, dockFlag;

  function q(sel) { return root ? root.querySelector(sel) : null; }
  function setText(el, text) { if (el && el.textContent !== text) el.textContent = text; }

  // posts.json carries HTML entities in some fields ("&amp;"). Everything the
  // desk shows is painted with textContent, so decode them here instead of
  // ever handing feed data to the HTML parser.
  function decode(value) {
    return String(value == null ? "" : value).replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi, function (m, e) {
      var k = e.toLowerCase();
      if (k.charAt(0) === "#") {
        var n = k.charAt(1) === "x" ? parseInt(k.slice(2), 16) : parseInt(k.slice(1), 10);
        try { return n > 0 ? String.fromCodePoint(n) : m; } catch (err) { return m; }
      }
      return { amp: "&", lt: "<", gt: ">", quot: "\"", apos: "'", nbsp: " " }[k] || m;
    });
  }

  // Only same-site brief paths are followed, so a feed row can never hand the
  // console a javascript: or off-site URL.
  function briefUrl(raw) {
    var u = String(raw || "");
    if (!/^\/?blog\/[A-Za-z0-9][A-Za-z0-9._\/-]*$/.test(u) || u.indexOf("..") > -1) return "";
    return BASE + u.replace(/^\//, "");
  }

  // The hub (blog/insights.js) reads ?topic= and ?q= on load; #latest is the
  // section holding the filtered grid.
  function hubUrl(topic, query) {
    var params = [];
    if (query) params.push("q=" + encodeURIComponent(query));
    if (topic) params.push("topic=" + encodeURIComponent(topic));
    return BASE + INTEL.hub + (params.length ? "?" + params.join("&") + "#latest" : "");
  }

  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function parseDay(value) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ""));
    if (!m) return null;
    var d = new Date(+m[1], +m[2] - 1, +m[3]);
    return isNaN(d.getTime()) ? null : d;
  }
  function today() { var n = new Date(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); }
  function fmtDay(d) { return d.getDate() + " " + MONTHS[d.getMonth()] + " " + d.getFullYear(); }

  function readList(key) {
    try { var v = JSON.parse(localStorage.getItem(key) || "[]"); return Array.isArray(v) ? v : []; }
    catch (e) { return []; }
  }
  function markSeen(slugs) {
    var list = readList(SEEN_KEY);
    slugs.forEach(function (s) { if (s && list.indexOf(s) < 0) list.push(s); });
    try { localStorage.setItem(SEEN_KEY, JSON.stringify(list.slice(-200))); } catch (e) {}
  }
  function isFresh(p) { return p.age >= 0 && p.age < INTEL.freshDays; }
  function unread() {
    var done = readList(SEEN_KEY);
    return intel.all.filter(function (p) { return isFresh(p) && done.indexOf(p.slug) < 0; });
  }
  function isUnread(p) { return isFresh(p) && readList(SEEN_KEY).indexOf(p.slug) < 0; }

  function whenText(p) {
    var when = !p.day ? "" : p.age === 0 ? "Today" : p.age === 1 ? "Yesterday" :
      isFresh(p) ? p.age + " days ago" : fmtDay(p.day);
    return [when, p.mins ? p.mins + " min read" : ""].filter(Boolean).join(" · ") || "ClearGlass Insights";
  }

  function loadFeed() {
    if (intel.state !== "idle") return;
    intel.state = "loading";
    if (!window.fetch) { intelFallback(); return; }
    fetch(BASE + INTEL.feed, { cache: "no-cache", credentials: "same-origin" })
      .then(function (res) { if (!res.ok) throw new Error("HTTP " + res.status); return res.json(); })
      .then(ingest)
      .catch(intelFallback);
  }

  function ingest(data) {
    var rows = data && Array.isArray(data.posts) ? data.posts : [];
    var labels = data && data.topics && typeof data.topics === "object" ? data.topics : {};
    var now = today();
    var all = [];
    rows.forEach(function (p) {
      if (!p || typeof p !== "object" || (p.status && p.status !== "published")) return;
      var url = briefUrl(p.url);
      var title = decode(p.title).trim();
      if (!url || !title) return;
      var day = parseDay(p.publishedAt);
      all.push({
        slug: String(p.slug || url), url: url, title: title,
        category: decode(p.category), pull: decode(p.quote), desc: decode(p.description),
        mins: Math.max(0, parseInt(p.readMinutes, 10) || 0),
        rank: Math.max(0, parseInt(p.deskRank, 10) || 0), featured: p.featured === true,
        day: day, age: day ? Math.round((now - day) / 864e5) : -1,
        topics: Array.isArray(p.topics) ? p.topics.map(String) : [],
        tags: Array.isArray(p.tags) ? p.tags.map(decode) : []
      });
    });
    if (!all.length) { intelFallback(); return; }

    // Rotation: the newest brief, the rest of the fresh ones, the desk's
    // ranked picks, then featured, then newest.
    var dated = all.filter(function (p) { return p.day; }).sort(function (a, b) {
      return (b.day - a.day) || ((a.rank || 99) - (b.rank || 99));
    });
    var latest = dated[0] || all[0];
    var ranked = dated.filter(function (p) { return p.rank; })
      .sort(function (a, b) { return (a.rank - b.rank) || (b.day - a.day); });
    var pool = [latest].concat(dated.filter(isFresh), ranked, dated.filter(function (p) { return p.featured; }), dated, all);
    var picks = [];
    pool.forEach(function (p) { if (p && picks.length < INTEL.picks && picks.indexOf(p) < 0) picks.push(p); });
    picks.forEach(function (p) {
      var parts = [];
      if (p === latest) parts.push("Latest");
      if (p.rank) parts.push("Desk pick #" + p.rank);
      else if (p.featured) parts.push("Featured");
      p.label = parts.join(" · ");
    });

    // Topics by how many briefs carry them — only ones the hub names.
    var counts = {};
    all.forEach(function (p) {
      p.topics.forEach(function (t) {
        if (Object.prototype.hasOwnProperty.call(labels, t)) counts[t] = (counts[t] || 0) + 1;
      });
    });
    intel.topics = Object.keys(counts)
      .sort(function (a, b) { return (counts[b] - counts[a]) || (a < b ? -1 : 1); })
      .map(function (k) { return { key: k, label: decode(labels[k]), count: counts[k] }; });

    intel.all = all;
    intel.picks = picks;
    intel.latest = latest;
    intel.updated = /^\d{4}-\d{2}-\d{2}$/.test(String(data.updated || "")) ? data.updated : "";
    intel.state = "ready";
    renderIntel();
  }

  // No feed (offline, file://, a failed read): the desk stays a plain link to
  // the hub rather than an empty box.
  function intelFallback() {
    intel.state = "static";
    if (!intelEl) return;
    intelEl.setAttribute("data-state", "static");
    setText(q("[data-cgst-b-cat]"), "Open the hub");
    setText(q("[data-cgst-sync]"), "Brief index unavailable here · the hub has every brief");
    paintCounts();
  }

  // ── Intel Desk: paint ────────────────────────────────────────────────────
  function renderIntel() {
    if (!intelEl || intel.state !== "ready") return;
    intelEl.setAttribute("data-state", "ready");
    var n = intel.picks.length;

    var dots = q("[data-cgst-dots]");
    dots.textContent = "";
    intel.picks.forEach(function (p, i) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "cgst-pip";
      b.tabIndex = -1;                      // keyboard users have prev/next
      b.setAttribute("data-cgst", "intel-go");
      b.setAttribute("data-index", String(i));
      b.setAttribute("aria-label", "Brief " + (i + 1) + " of " + n);
      dots.appendChild(b);
    });
    q("[data-cgst-intel-nav]").hidden = n < 2;

    var box = q("[data-cgst-topics]");
    box.textContent = "";
    intel.topics.slice(0, INTEL.topics).forEach(function (t) {
      var a = document.createElement("a");
      a.className = "cgst-topic";
      a.href = hubUrl(t.key);
      a.setAttribute("data-cgst-item", "");
      a.setAttribute("aria-label", t.label + ", " + t.count + (t.count === 1 ? " brief" : " briefs"));
      a.appendChild(document.createTextNode(t.label));
      var count = document.createElement("i");
      count.setAttribute("aria-hidden", "true");
      count.textContent = String(t.count);
      a.appendChild(count);
      box.appendChild(a);
    });
    box.hidden = !intel.topics.length;

    setText(q("[data-cgst-sync]"), [intel.updated ? "Index " + intel.updated : "Index",
      intel.all.length + " briefs", intel.topics.length + " topics"].join(" · "));

    showBrief(intel.at, 0, false);
    paintCounts();
    syncRun();
  }

  function showBrief(i, dir, announce) {
    var n = intel.picks.length;
    if (!n || !briefEl) return;
    intel.at = ((i % n) + n) % n;
    var p = intel.picks[intel.at];
    var fresh = isUnread(p);
    briefEl.href = p.url;
    briefEl.setAttribute("data-slug", p.slug);
    setText(q("[data-cgst-b-rank]"), p.label || "");
    setText(q("[data-cgst-b-cat]"), p.category || "ClearGlass Insights");
    setText(q("[data-cgst-b-title]"), p.title);
    var quote = q("[data-cgst-b-quote]");
    setText(quote, p.pull ? "“" + p.pull + "”" : p.desc);
    quote.hidden = !(p.pull || p.desc);
    setText(q("[data-cgst-b-when]"), whenText(p));
    q("[data-cgst-b-new]").hidden = !fresh;
    briefEl.setAttribute("aria-label", p.title + (p.label ? ". " + p.label : "") + ". " + whenText(p) + (fresh ? ". New" : ""));
    Array.prototype.forEach.call(root.querySelectorAll(".cgst-pip"), function (b, k) {
      b.setAttribute("aria-current", String(k === intel.at));
    });
    setText(q("[data-cgst-pos]"), (intel.at + 1) + " / " + n);

    // a fresh timer bar restarts the countdown for this slide
    var t = timerEl.cloneNode(false);
    timerEl.parentNode.replaceChild(t, timerEl);
    timerEl = t;
    if (dir && !quiet()) {
      briefEl.style.setProperty("--cgst-dir", (dir > 0 ? 14 : -14) + "px");
      briefEl.classList.remove("cgst-in");
      void briefEl.offsetWidth;             // restart the entrance animation
      briefEl.classList.add("cgst-in");
    }
    if (announce && intelLive) intelLive.textContent = "Brief " + (intel.at + 1) + " of " + n + ": " + p.title;
  }

  // Every count here is derived from the feed and this browser's own lists.
  function paintCounts() {
    if (!root) return;
    var ready = intel.state === "ready";
    var n = ready ? unread().length : 0;
    var total = intel.all.length;

    var flag = q("[data-cgst-intel-flag]");
    if (flag && ready) {
      flag.hidden = false;
      if (n) { flag.removeAttribute("data-quiet"); setText(flag, n + " NEW"); }
      else { flag.setAttribute("data-quiet", ""); setText(flag, total + " BRIEFS"); }
      setText(q("[data-cgst-intel-sub]"), n
        ? n + " unread · last " + INTEL.freshDays + " days"
        : "ClearGlass Insights · no unread");
    }
    var seenBtn = q('[data-cgst="intel-seen"]');
    if (seenBtn) seenBtn.hidden = !n;

    if (dockFlag) { dockFlag.hidden = !n; setText(dockFlag, String(n)); }
    var st = q("[data-cgst-feed-state]");
    if (st) {
      st.hidden = !ready;
      if (n) { st.setAttribute("data-hot", ""); setText(st, n + " NEW"); }
      else { st.removeAttribute("data-hot"); setText(st, String(total)); }
    }

    var saved = readList(SAVED_KEY).filter(function (s) { return typeof s === "string"; }).length;
    var link = q("[data-cgst-saved]");
    if (link) { link.hidden = !saved; setText(link, "Saved · " + saved); }

    var p = ready ? intel.picks[intel.at] : null;
    var bNew = q("[data-cgst-b-new]");
    if (bNew) bNew.hidden = !(p && isUnread(p));
    labelDock();
  }

  function labelDock() {
    if (!dock) return;
    var open = root.getAttribute("data-open") === "true";
    var n = dockFlag && !dockFlag.hidden ? parseInt(dockFlag.textContent, 10) || 0 : 0;
    dock.setAttribute("aria-label", (open ? "Collapse Sentinel Core" : "Expand Sentinel Core") +
      (n ? ", " + n + " new intel " + (n === 1 ? "brief" : "briefs") : ""));
  }

  // Rotation runs only while someone can watch it, and stops for hover,
  // keyboard focus, the pause control, reduced motion and Tactical View.
  function syncRun() {
    if (!intelEl) return;
    var run = intel.state === "ready" && intel.picks.length > 1 && !intel.hold && !intel.hover && !intel.focus &&
      root.getAttribute("data-open") === "true" && !document.hidden && !graph.open &&
      !document.body.classList.contains("sentinel-open");
    var v = run ? "1" : "0";
    if (intelEl.getAttribute("data-run") !== v) intelEl.setAttribute("data-run", v);
  }

  function toggleHold() {
    intel.hold = !intel.hold;
    var b = q('[data-cgst="intel-hold"]');
    if (b) { b.setAttribute("aria-pressed", String(intel.hold)); b.innerHTML = intel.hold ? IC_PLAY : IC_HOLD; }
    syncRun();
  }

  function focusVisible(el) { try { return el.matches(":focus-visible"); } catch (e) { return true; } }

  function go(url) { window.location.href = url; }
  function openBrief(p) { markSeen([p.slug]); go(p.url); }

  function focusIntel() {
    if (!root || !intelEl) return;
    if (root.getAttribute("data-open") !== "true") { lastFocus = document.activeElement; setOpen(true, false); }
    try { intelEl.scrollIntoView({ block: "nearest" }); } catch (e) {}
    try { briefEl.focus({ preventScroll: true }); } catch (e) { briefEl.focus(); }
  }

  function wireIntel() {
    intelEl = q(".cgst-intel");
    briefEl = q("[data-cgst-brief]");
    timerEl = q(".cgst-timer");
    intelLive = q("[data-cgst-intel-live]");
    dockFlag = q("[data-cgst-dock-flag]");
    if (!intelEl || !briefEl || !timerEl) return;

    intelEl.addEventListener("animationend", function (event) {
      if (event.animationName === "cgstFill" && event.target === timerEl) showBrief(intel.at + 1, 1, false);
    });
    intelEl.addEventListener("pointerenter", function (event) {
      if (event.pointerType === "mouse") { intel.hover = true; syncRun(); }
    });
    intelEl.addEventListener("pointerleave", function () { intel.hover = false; syncRun(); });
    // a tap that focuses a link is not keyboard focus; only :focus-visible pauses
    intelEl.addEventListener("focusin", function (event) { intel.focus = focusVisible(event.target); syncRun(); });
    intelEl.addEventListener("focusout", function (event) {
      if (!intelEl.contains(event.relatedTarget)) { intel.focus = false; syncRun(); }
    });

    // horizontal swipe on the featured brief pages through the rotation
    var sx = 0, sy = 0, tracking = false, swiped = false;
    briefEl.addEventListener("pointerdown", function (event) {
      tracking = true; swiped = false; sx = event.clientX; sy = event.clientY;
    });
    briefEl.addEventListener("pointerup", function (event) {
      if (!tracking) return;
      tracking = false;
      var dx = event.clientX - sx, dy = event.clientY - sy;
      if (intel.picks.length > 1 && Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.4) {
        swiped = true;
        showBrief(intel.at + (dx < 0 ? 1 : -1), dx < 0 ? 1 : -1, true);
      }
    });
    briefEl.addEventListener("pointercancel", function () { tracking = false; });
    briefEl.addEventListener("click", function (event) {
      if (swiped) { event.preventDefault(); swiped = false; return; }
      var slug = briefEl.getAttribute("data-slug");
      if (slug) markSeen([slug]);
    });
  }

  // ── command bar: slash commands and brief matches on the Ask field ───────
  // Plain text still goes to Sentinel exactly as before: when matches show,
  // "Ask Sentinel" is the first, pre-selected option.
  var bar = { open: false, opts: [], active: -1 };
  var suggestEl;

  function commands() {
    var list = [
      { cmd: "/intel", hint: "Open the Intel Desk hub", run: function () { go(hubUrl()); } },
      { cmd: "/latest", hint: "Open the newest brief", run: function () { if (intel.latest) openBrief(intel.latest); else go(hubUrl()); } },
      { cmd: "/map", hint: "Intelligence Graph · every page", run: function () { openGraph({}); } },
      { cmd: "/pages", hint: "Search every page · /pages osint", run: function (arg) {
        runIntent(arg ? { kind: "search", arg: arg } : { kind: "pages" }, arg || "");
      } },
      { cmd: "/sector", hint: "Browse a sector · /sector artemis", run: function (arg) {
        if (arg && sectorsIn(arg)) runIntent({ kind: "sector", arg: arg }, arg); else setMc(true, true);
      } },
      { cmd: "/mc", hint: "Mission Control", run: function () { setMc(true, true); } },
      { cmd: "/explain", hint: "Explain this page", run: function () { smart("explain"); } },
      { cmd: "/summary", hint: "Summarize this section", run: function () { smart("summarize"); } },
      { cmd: "/related", hint: "Related pages", run: function () { smart("related"); } },
      { cmd: "/services", hint: "Related services", run: function () { smart("services"); } },
      { cmd: "/brief", hint: "Executive brief of this page", run: function () { smart("brief"); } },
      { cmd: "/plan", hint: "Action plan from this page", run: function () { smart("plan"); } },
      { cmd: "/next", hint: "Recommended next step", run: function () { smart("next"); } },
      { cmd: "/similar", hint: "Similar content", run: function () { smart("similar"); } },
      { cmd: "/docs", hint: "Documentation · /docs aegis", run: function (arg) { runIntent({ kind: "docs", arg: arg || "" }, arg || "", "technical"); } },
      { cmd: "/topic", hint: "Filter the hub by topic · /topic cyber", run: function (arg) {
        var t = topicFor(arg);
        go(t ? hubUrl(t.key) : hubUrl(null, arg));
      } },
      { cmd: "/search", hint: "Search every brief · /search botnet", run: function (arg) { go(hubUrl(null, arg)); } },
      { cmd: "/saved", hint: "Briefs saved on this device", run: function () { go(hubUrl("saved")); } },
      { cmd: "/rss", hint: "The brief feed (RSS)", run: function () { go(BASE + INTEL.rss); } }
    ];
    MISSIONS.forEach(function (m) {
      list.push({ cmd: "/" + m.code.toLowerCase(), hint: m.title, run: function () { openSentinel(m.prompt); } });
    });
    if (stealthAvailable()) list.push({ cmd: "/stealth", hint: "Toggle Stealth Glass", run: toggleStealth });
    if (motionToggle()) list.push({ cmd: "/tactical", hint: "Toggle Tactical View", run: toggleTactical });
    list.push(
      { cmd: "/top", hint: "Jump to the top of the page", run: function () { scrollTo(0); } },
      { cmd: "/bottom", hint: "Jump to the bottom of the page", run: function () { scrollTo(docHeight()); } }
    );
    return list;
  }

  function topicFor(arg) {
    var a = String(arg || "").trim().toLowerCase();
    if (!a) return null;
    var exact = intel.topics.filter(function (t) { return t.key === a || t.label.toLowerCase() === a; })[0];
    return exact || intel.topics.filter(function (t) {
      return t.key.indexOf(a) > -1 || t.label.toLowerCase().indexOf(a) > -1;
    })[0] || null;
  }

  function findBriefs(query) {
    var ql = query.toLowerCase();
    var words = ql.split(/\s+/).filter(Boolean);
    return intel.all.map(function (p) {
      var t = p.title.toLowerCase();
      var hay = t + " " + p.category.toLowerCase() + " " + p.tags.join(" ").toLowerCase() + " " + p.topics.join(" ");
      if (!words.every(function (w) { return hay.indexOf(w) > -1; })) return null;
      var at = t.indexOf(ql);
      return { p: p, s: at === 0 ? 0 : at > 0 ? 1 : words.every(function (w) { return t.indexOf(w) > -1; }) ? 2 : 3 };
    }).filter(Boolean).sort(function (a, b) {
      return (a.s - b.s) || ((b.p.day || 0) - (a.p.day || 0));
    }).slice(0, 4).map(function (h) { return h.p; });
  }

  function optionsFor(text) {
    var raw = String(text || "").replace(/^\s+/, "");
    if (raw.charAt(0) === "/") {
      var sp = raw.indexOf(" ");
      var name = (sp < 0 ? raw : raw.slice(0, sp)).toLowerCase();
      var arg = sp < 0 ? "" : raw.slice(sp + 1).trim();
      if (sp > -1 && name === "/topic" && intel.topics.length) {
        var a = arg.toLowerCase();
        return intel.topics.filter(function (t) {
          return !a || t.key.indexOf(a) > -1 || t.label.toLowerCase().indexOf(a) > -1;
        }).slice(0, 6).map(function (t) {
          return { key: "Topic", text: t.label + " · " + t.count + (t.count === 1 ? " brief" : " briefs"),
            run: function () { go(hubUrl(t.key)); } };
        });
      }
      if (sp > -1) {                         // a command with an argument
        var exact = commands().filter(function (c) { return c.cmd === name; })[0];
        return exact ? [{ key: exact.cmd, text: exact.hint, run: function () { exact.run(arg); } }] : [];
      }
      return commands().filter(function (c) { return c.cmd.indexOf(name) === 0; }).slice(0, name === "/" ? 10 : 8)
        .map(function (c) { return { key: c.cmd, text: c.hint, run: function () { c.run(""); } }; });
    }
    var query = raw.trim();
    if (query.length < 3 || (intel.state !== "ready" && site.state !== "ready")) return [];
    // A phrasing with a site meaning leads; anything else keeps "Ask Sentinel"
    // first and pre-selected, exactly as before.
    var intent = intentOf(query);
    var pages = site.state === "ready" ? rank(query).slice(0, 3) : [];
    var hits = intel.state === "ready" ? findBriefs(query).slice(0, pages.length ? 3 : 4) : [];
    if (!intent && !pages.length && !hits.length) return [];
    var opts = [];
    if (intent) opts.push(intentOption(intent, query));
    opts.push({ key: "Ask", text: (hasSentinel() ? "Ask Sentinel: “" : "Search the site: “") + query + "”",
      run: function () { if (hasSentinel()) openSentinel(query); else runIntent({ kind: "search", arg: query }, query); } });
    pages.forEach(function (h) { opts.push({ key: "Page", text: h.e.title + " · " + h.e.group, run: function () { go(h.e.url); } }); });
    hits.forEach(function (p) { opts.push({ key: "Brief", text: p.title, run: function () { openBrief(p); } }); });
    opts.push({ key: "Hub", text: "Search every brief for “" + query + "”", run: function () { go(hubUrl(null, query)); } });
    return opts;
  }

  function intentOption(it, query) {
    var run = function () { runIntent(it, query); };
    var label = {
      map: ["Map", "Open the Intelligence Graph"], pages: ["Map", "Every public page, by cluster"],
      explain: ["Page", "Explain this page"], summarize: ["Page", "Summarize this section"],
      brief: ["Page", "Executive brief of this page"], plan: ["Page", "Action plan from this page"],
      next: ["Page", "Recommended next step"], similar: ["Page", "Similar content"], services: ["Page", "Related services"],
      docs: ["Docs", it.arg ? "Documentation for “" + it.arg + "”" : "Documentation near this page"],
      related: ["Links", it.arg ? "Pages related to “" + it.arg + "”" : "Pages related to this one"],
      sector: ["Sector", "Show " + it.arg], search: ["Site", "Pages about “" + it.arg + "”"],
      locate: ["Find", "Locate “" + it.arg + "”"], go: ["Go", "Take me to “" + it.arg + "”"]
    }[it.kind] || ["Site", query];
    if (site.state === "ready" && (it.kind === "go" || it.kind === "locate")) {
      var top = rank(it.arg)[0];
      if (top) label = [it.kind === "go" ? "Go" : "Find", top.e.title + " · " + top.e.group];
    }
    if (site.state === "ready" && it.kind === "sector") {
      var sel = sectorsIn(it.arg);
      if (sel) {
        var names = sel.ids.map(function (id) { return sectorById(id).title; });
        var n = sel.ids[0] === "missions" ? MISSIONS.length : sectorPages(sel).pages.length;
        label = ["Sector", names.join(sel.any ? " + " : " ∩ ") + " · " + plural(n, sel.ids[0] === "missions" ? "mission" : "page")];
      }
    }
    return { key: label[0], text: label[1], run: run };
  }

  function setActiveOpt(i) {
    bar.active = i;
    Array.prototype.forEach.call(suggestEl.children, function (li, k) { li.setAttribute("aria-selected", String(k === i)); });
    if (i >= 0) askInput.setAttribute("aria-activedescendant", "cgstOpt" + i);
    else askInput.removeAttribute("aria-activedescendant");
  }

  function closeSuggest() {
    bar.open = false; bar.opts = []; bar.active = -1;
    if (suggestEl) { suggestEl.hidden = true; suggestEl.textContent = ""; }
    if (askInput) { askInput.setAttribute("aria-expanded", "false"); askInput.removeAttribute("aria-activedescendant"); }
  }

  function paintSuggest() {
    var opts = optionsFor(askInput.value);
    if (!opts.length) { closeSuggest(); return; }
    bar.opts = opts;
    suggestEl.textContent = "";
    opts.forEach(function (o, i) {
      var li = document.createElement("li");
      li.className = "cgst-opt";
      li.id = "cgstOpt" + i;
      li.setAttribute("role", "option");
      var k = document.createElement("span");
      k.className = "cgst-opt-k";
      k.textContent = o.key;
      var h = document.createElement("span");
      h.className = "cgst-opt-h";
      h.textContent = o.text;
      li.appendChild(k);
      li.appendChild(h);
      suggestEl.appendChild(li);
    });
    suggestEl.hidden = false;
    bar.open = true;
    askInput.setAttribute("aria-expanded", "true");
    setActiveOpt(0);
  }

  function runOption(o) {
    askInput.value = "";
    closeSuggest();
    askInput.blur();
    o.run();
  }

  function wireBar() {
    suggestEl = q("#cgstSuggest");
    if (!suggestEl || !askInput) return;
    askInput.addEventListener("input", paintSuggest);
    askInput.addEventListener("focus", function () {
      loadFeed();
      loadSite(function () { if (document.activeElement === askInput && askInput.value) paintSuggest(); });
      if (askInput.value) paintSuggest();
    });
    askInput.addEventListener("blur", function () {
      setTimeout(function () { if (document.activeElement !== askInput) closeSuggest(); }, 180);
    });
    askInput.addEventListener("keydown", function (event) {
      if (!bar.open) return;
      var n = bar.opts.length;
      if (event.key === "ArrowDown") { event.preventDefault(); setActiveOpt((bar.active + 1) % n); }
      else if (event.key === "ArrowUp") { event.preventDefault(); setActiveOpt((bar.active - 1 + n) % n); }
      else if (event.key === "Escape") {
        // close the list only; the console stays open
        event.preventDefault();
        event.stopPropagation();
        closeSuggest();
      }
    });
    // keep focus in the field while an option is pressed
    suggestEl.addEventListener("mousedown", function (event) { event.preventDefault(); });
    suggestEl.addEventListener("click", function (event) {
      var li = event.target.closest ? event.target.closest(".cgst-opt") : null;
      if (!li) return;
      var o = bar.opts[parseInt(li.id.replace("cgstOpt", ""), 10)];
      if (o) runOption(o);
    });
  }

  // ── Site Intelligence: the index ─────────────────────────────────────────
  var site = { state: "idle", pages: [], byPath: {}, clusters: [], byId: {}, links: 0, here: null, waiters: [] };
  var nexusEl;

  // Only same-site page paths are followed: letters, digits and ._/- ending in
  // .html or a folder. Never "..", "//" or a scheme.
  function siteUrl(raw) {
    var u = String(raw || "");
    if (!/^[A-Za-z0-9][A-Za-z0-9._\/-]*(\.html|\/)$/.test(u) || u.indexOf("..") > -1 || u.indexOf("//") > -1) return "";
    return BASE + u;
  }

  function strList(v) { return Array.isArray(v) ? v.filter(function (x) { return typeof x === "string"; }) : []; }

  // This page's path inside the site, the key it has in the index.
  function herePath() {
    var here = String(location.href).split("#")[0].split("?")[0];
    if (!BASE || here.indexOf(BASE) !== 0) return "";
    var rel = here.slice(BASE.length);
    try { rel = decodeURIComponent(rel); } catch (e) {}
    if (!rel || rel.slice(-1) === "/") rel += "index.html";
    return rel;
  }

  function loadSite(then) {
    if (typeof then === "function") site.waiters.push(then);
    if (site.state === "ready" || site.state === "static") { flushSite(); return; }
    if (site.state === "loading") return;
    site.state = "loading";
    paintIndex();
    if (!window.fetch) { siteFallback(); return; }
    fetch(BASE + SITE.index, { cache: "no-cache", credentials: "same-origin" })
      .then(function (res) { if (!res.ok) throw new Error("HTTP " + res.status); return res.json(); })
      .then(ingestSite)
      .catch(siteFallback);
  }

  function flushSite() {
    var list = site.waiters;
    site.waiters = [];
    list.forEach(function (fn) { try { fn(); } catch (e) {} });
  }

  function siteFallback() {
    site.state = "static";
    paintIndex();
    flushSite();
  }

  function ingestSite(data) {
    var rows = data && Array.isArray(data.pages) ? data.pages : [];
    var groups = data && Array.isArray(data.clusters) ? data.clusters : [];
    var byPath = {}, pages = [];
    rows.forEach(function (p) {
      if (!p || typeof p !== "object") return;
      var path = String(p.path || ""), url = siteUrl(path), title = String(p.title || "").trim();
      if (!url || !title || byPath[path]) return;
      var e = { path: path, url: url, title: title, summary: String(p.summary || ""), about: String(p.about || ""),
        cluster: String(p.cluster || ""), hub: p.role === "hub", related: strList(p.related),
        prev: String(p.prev || ""), next: String(p.next || "") };
      byPath[path] = e;
      pages.push(e);
    });
    var clusters = [], byId = {};
    groups.forEach(function (c) {
      if (!c || typeof c !== "object" || typeof c.id !== "string" || byId[c.id] || !byPath[c.pillar]) return;
      var g = { id: c.id, name: String(c.name || c.id), pillar: String(c.pillar),
        members: strList(c.members).filter(function (m) { return byPath[m] && m !== c.pillar; }),
        cta: (Array.isArray(c.cta) ? c.cta : []).filter(function (x) { return x && byPath[x.path]; })
          .map(function (x) { return { path: String(x.path), label: String(x.label || byPath[x.path].title) }; }) };
      byId[g.id] = g;
      clusters.push(g);
    });
    if (!pages.length || !clusters.length) { siteFallback(); return; }
    pages.forEach(function (e) {
      e.related = e.related.filter(function (r) { return byPath[r] && r !== e.path; });
      e.group = byId[e.cluster] ? byId[e.cluster].name : "";
      e.hay = { t: norm(e.title), s: norm(e.summary), a: norm(e.about), p: norm(e.path.replace(/\.html$/, "")), c: norm(e.group) };
    });
    site.pages = pages;
    site.byPath = byPath;
    site.clusters = clusters;
    site.byId = byId;
    site.links = pages.reduce(function (n, e) { return n + e.related.length; }, 0);
    var hp = herePath();
    site.here = byPath[hp] || byPath[hp + ".html"] || null;
    SECTORS.forEach(function (s) { s.pages = s.missions ? [] : orderSector(pages.filter(function (e) { return inSector(e, s); }), s); });
    site.state = "ready";
    paintIndex();
    flushSite();
  }

  function paintIndex() {
    if (!nexusEl) return;
    var st = site.state, ready = st === "ready";
    nexusEl.setAttribute("data-state", st);
    setText(q("[data-cgst-idx-state]"), ready ? "READY ✓" : st === "static" ? "OFFLINE" : st === "loading" ? "SYNCING" : "STANDBY");
    setText(q("[data-cgst-idx-pages]"), ready ? String(site.pages.length) : "--");
    setText(q("[data-cgst-idx-nodes]"), ready ? String(site.pages.length + site.clusters.length) : "--");
    setText(q("[data-cgst-idx-links]"), ready ? String(site.links) : "--");
    var where = q("[data-cgst-where]");
    if (where) {
      where.textContent = "";
      if (ready && site.here) {
        where.appendChild(document.createTextNode("You are here · " + site.here.group + " › "));
        var b = document.createElement("b");
        b.textContent = site.here.title;
        where.appendChild(b);
      } else if (ready) where.textContent = "This page is outside the public site graph";
      else if (st === "static") where.textContent = "Site index unavailable here · the Authority Network page maps it";
      else where.textContent = "Reading the site index…";
    }
    SECTORS.forEach(function (s) {
      var n = s.missions ? MISSIONS.length : ready ? s.pages.length : 0;
      var el = q('[data-cgst-sector-count="' + s.id + '"]');
      setText(el, s.missions || ready ? String(n) : "--");
      var btn = q('.cgst-sector[data-sector="' + s.id + '"]');
      if (btn && (s.missions || ready)) btn.setAttribute("aria-label", s.title + ", " + n + (s.missions ? " missions" : n === 1 ? " page" : " pages"));
    });
  }

  // ── Site Intelligence: matching ──────────────────────────────────────────
  // Rule-guided: word-prefix matches over each page's title (×6), summary
  // (×3.5), path (×2.5), description (×1.5) and cluster (×1), widened by the
  // ALIKE table at 0.45. It runs on the index, in this browser.
  function norm(s) {
    return " " + String(s || "").toLowerCase().replace(/&/g, " and ").replace(/[^a-z0-9]+/g, " ").trim() + " ";
  }
  // Truncating stem: every match is a word-prefix match, so "policies" →
  // "polic" finds "policy" too, and "workflows" → "workflow".
  function stem(w) {
    if (w.length >= 5 && /ies$/.test(w)) return w.slice(0, -3);
    if (w.length >= 5 && /[^s]s$/.test(w)) return w.slice(0, -1);
    return w;
  }
  function words(text) { return norm(text).trim().split(" ").filter(function (w) { return w && !STOPS[w]; }); }
  // Short words (ai, os, iot) match whole; longer ones at the start of a word.
  function hit(hay, w) {
    if (w.indexOf(" ") > -1 || w.length > 3) return hay.indexOf(" " + w) > -1;
    return hay.indexOf(" " + w + " ") > -1 || hay.indexOf(" " + w + "s ") > -1;
  }

  function queryTerms(text) {
    var out = [], seen = {};
    words(text).forEach(function (w) {
      var root = stem(w);
      if (seen[root]) return;
      seen[root] = 1;
      out.push({ w: root, k: 1, root: root });
      (ALIKE[w] || ALIKE[root] || []).forEach(function (s) {
        var t = s.indexOf(" ") > -1 ? s : stem(s);
        if (!seen[t]) { seen[t] = 1; out.push({ w: t, k: 0.45, root: root }); }
      });
    });
    return out;
  }

  function rank(text, pool) {
    var qs = queryTerms(text);
    if (!qs.length || site.state !== "ready") return [];
    var roots = {};
    qs.forEach(function (t) { roots[t.root] = 1; });
    var need = Object.keys(roots).length;
    var own = qs.filter(function (t) { return t.k === 1; });
    var phrase = " " + own.map(function (t) { return t.w; }).join(" ");
    return (pool || site.pages).map(function (e) {
      // each idea in the query scores once, by its best field; a synonym only
      // counts where the word itself does not appear
      var best = {};
      qs.forEach(function (t) {
        var v = hit(e.hay.t, t.w) ? 6 : hit(e.hay.s, t.w) ? 3.5 : hit(e.hay.p, t.w) ? 2.5 : hit(e.hay.a, t.w) ? 1.5 : hit(e.hay.c, t.w) ? 1 : 0;
        v *= t.k;
        if (v && (!best[t.root] || v > best[t.root])) best[t.root] = v;
      });
      var roots2 = Object.keys(best);
      if (!roots2.length) return null;
      var s = roots2.reduce(function (n, r) { return n + best[r]; }, 0);
      s *= 0.4 + 0.6 * roots2.length / need;     // reward covering every idea asked about
      if (need > 1 && e.hay.t.indexOf(phrase) > -1) s += 8;
      if (own.length && e.hay.t.indexOf(" " + own[0].w) === 0) s += 1.5;   // the title leads with it
      if (e.hub) s += 0.5;
      return s >= 1.2 ? { e: e, s: s } : null;
    }).filter(Boolean).sort(function (a, b) { return (b.s - a.s) || (a.e.title < b.e.title ? -1 : 1); });
  }

  // Query words no indexed page uses at all: reported, never guessed at.
  function unknownTerms(text) {
    return queryTerms(text).filter(function (t) {
      return t.k === 1 && !site.pages.some(function (e) { return hit(e.hay.t + e.hay.s + e.hay.a + e.hay.p + e.hay.c, t.w); });
    }).map(function (t) { return t.w; });
  }

  function inSector(e, sec) {
    if (sec.clusters && sec.clusters.indexOf(e.cluster) > -1) return true;
    if (sec.paths && sec.paths.some(function (x) { return e.path.indexOf(x) === 0; })) return true;
    var hay = e.hay.t + e.hay.s;
    return !!(sec.words && sec.words.some(function (w) { return hit(hay, w); }));
  }
  // Pages whose title names the sector first, hubs before members, then the
  // graph's own order.
  function sectorKey(e, secs) {
    var titled = secs.some(function (sec) { return hit(e.hay.t, sec.title.toLowerCase()); });
    var named = titled || secs.some(function (sec) { return (sec.words || []).some(function (w) { return hit(e.hay.t, w); }); });
    return (titled ? 0 : named ? 2 : 4) + (e.hub ? 0 : 1);
  }
  function orderSector(list, secs) {
    secs = [].concat(secs);
    return list.map(function (e, i) { return { e: e, k: sectorKey(e, secs), i: i }; })
      .sort(function (a, b) { return (a.k - b.k) || (a.i - b.i); }).map(function (x) { return x.e; });
  }
  function sectorById(id) { return SECTORS.filter(function (s) { return s.id === id; })[0] || null; }

  // Sectors named in a phrase, in the order the phrase names them.
  function sectorsIn(text) {
    var hay = norm(text), found = [], any = false;
    SECTOR_ALIAS.forEach(function (a) {
      var at = -1;
      a.say.forEach(function (w) { if (hit(hay, w)) { var i = hay.indexOf(" " + w); if (at < 0 || i < at) at = i; } });
      if (at < 0) return;
      a.ids.forEach(function (id, k) { found.push({ id: id, at: at + k / 10 }); });
      if (a.any) any = true;
    });
    found.sort(function (x, y) { return x.at - y.at; });
    var ids = [];
    found.forEach(function (f) { if (ids.indexOf(f.id) < 0) ids.push(f.id); });
    return ids.length ? { ids: ids, any: any } : null;
  }

  function sectorPages(sel) {
    var secs = sel.ids.map(sectorById).filter(Boolean);
    var sets = secs.map(function (s) { return s.pages || []; });
    var union = [];
    sets.forEach(function (set) { set.forEach(function (e) { if (union.indexOf(e) < 0) union.push(e); }); });
    if (sets.length > 1) union = orderSector(union, secs);
    if (sel.any || sets.length < 2) return { pages: union, joined: sets.length > 1 };
    var both = sets[0].filter(function (e) { return sets.every(function (set) { return set.indexOf(e) > -1; }); });
    return both.length ? { pages: both, joined: false } : { pages: union, joined: true, empty: true };
  }

  // ── Site Intelligence: intent ────────────────────────────────────────────
  // Only phrasings with a clear site meaning are claimed. Everything else goes
  // where it always went: to the Sentinel conversation, or, on a page without
  // one, to a site search in this console.
  function intentOf(raw) {
    var t = String(raw || "").toLowerCase().replace(/[’']/g, "'").replace(/[?!.]+\s*$/, "").replace(/\s+/g, " ").trim();
    if (t.length < 3 || t.charAt(0) === "/") return null;
    var m;
    if (/^(site ?map|map|graph)$/.test(t) || /\b(site ?map|knowledge graph|intelligence graph)\b/.test(t) ||
        /^(show|open)( me)? the (map|graph)$/.test(t) ||
        (/\b(map|graph)\b/.test(t) && /\b(platform|site|ecosystem|everything|entire|whole|network|clearglass|all)\b/.test(t)))
      return { kind: "map" };
    if (/^(what|which) (pages|content) (exist|are there|do you have)|^(show|list)( me)? (all|every)( the)? pages$|^(all|every) pages$/.test(t))
      return { kind: "pages" };
    if (/\b(explain|describe)\b.*\b(this|current) page\b|^what is this page|^where am i\b/.test(t)) return { kind: "explain" };
    if (/\bsummar(y|i[sz]e)\b/.test(t) || /^tl ?;? ?dr\b/.test(t)) return { kind: "summarize" };
    if (/\bexecutive brief/.test(t) || /\bgenerate (a |an )?(report|brief)/.test(t)) return { kind: "brief" };
    if (/\baction plan\b|\bbuild (a |an )?plan\b/.test(t)) return { kind: "plan" };
    if (/\bnext step\b|what should i do next|^recommend (a |the )?next/.test(t)) return { kind: "next" };
    if (/\bsimilar (content|pages|briefs)\b|^find similar\b/.test(t)) return { kind: "similar" };
    if ((m = /\b(?:documentation|docs)\b(?: (?:for|on|about) (.+))?/.exec(t))) return { kind: "docs", arg: m[1] || "" };
    if (/^(show |find )?related services\b/.test(t)) return { kind: "services" };
    if (/^(show |find )?related (pages|content)$/.test(t)) return { kind: "related", arg: "" };
    if ((m = /\brelated to (.+)$/.exec(t))) return { kind: "related", arg: m[1] };
    if ((m = /^(?:show|list|browse|explore|see)(?: me)?(?: all| every)?(?: of)?(?: the)?(?: clearglass)? (.+)$/.exec(t)) && sectorsIn(m[1]))
      return { kind: "sector", arg: m[1] };
    if ((m = /\beverything (?:under|in|about|for) (.+)$/.exec(t)) || (m = /^what(?:'s| is) (?:under|in) (.+)$/.exec(t)))
      return sectorsIn(m[1]) ? { kind: "sector", arg: m[1] } : { kind: "search", arg: m[1] };
    if ((m = /^what (.+?) (?:capabilities|features|services|solutions|products|options|pages) (?:exist|are there|do you (?:have|offer)|are available|does clearglass (?:have|offer))/.exec(t)) ||
        (m = /^what (?:are|is) (?:the )?(.+?) (?:features|capabilities)$/.exec(t)))
      return sectorsIn(m[1]) ? { kind: "sector", arg: m[1] } : { kind: "search", arg: m[1] };
    if ((m = /^(?:take me to|go to|goto|navigate to|bring me to|jump to|visit|open)(?: the)? (.+?)(?: page)?$/.exec(t))) return { kind: "go", arg: m[1] };
    if ((m = /^where(?:'s| is| are| can i find| do i find| would i find)(?: the| your)? (.+?)(?: page)?$/.exec(t))) return { kind: "locate", arg: m[1] };
    if ((m = /^(?:what|which) (?:pages |content |briefs |articles |posts )?(?:discuss|discusses|cover|covers|mention|mentions|talk about|are about|deal with)(?: the)? (.+)$/.exec(t)) ||
        (m = /^(?:pages|content|briefs|articles) (?:about|on|covering) (.+)$/.exec(t)) ||
        (m = /^(?:find|search(?: for)?|look for|looking for)(?: the)? (.+?)(?: pages?)?$/.exec(t)))
      return { kind: "search", arg: m[1] };
    return null;
  }

  // Writing mode from the words of the request (§2 of the house style).
  function modeFor(text) {
    var t = String(text || "").toLowerCase();
    if (/\b(architecture|architect|spec|specification|technical|implement|implementation|integration|api|stack|engineer|engineering|schema|runbook|how (?:does|do|is))\b/.test(t)) return "technical";
    if (/\b(compare|comparison|versus|vs|trade ?-?offs?|analy[sz]e|analysis|gaps?|coverage|evaluate|assess)\b/.test(t)) return "analytical";
    if (/\b(why (?:choose|clearglass|should|use)|pitch|sell|value|benefits?|convince|worth|roi)\b/.test(t)) return "pitch";
    return "executive";
  }

  // ── Answers: one card, four writing modes ────────────────────────────────
  // House style (prompts/sentinel_core_system_prompt.md): the answer is the
  // first sentence, key terms are bold, comparisons are tables, sequences are
  // numbered, and every card says what it assumed and how it was resolved.
  // A mode only reorders those structures; the facts are the same in all four.
  var ans = { spec: null, pick: "auto", all: false, ms: 0, acts: [], runs: [] };
  var ansEl, ansKind, ansTitle, ansLede, ansBody, ansActs, ansBasis, ansLive;

  function readMode() {
    try { var v = localStorage.getItem(MODE_KEY); if (v === "auto" || modeById(v)) return v; } catch (e) {}
    return "auto";
  }
  function modeById(id) { return MODES.filter(function (m) { return m.id === id; })[0] || null; }
  function curMode() {
    return ans.pick !== "auto" && modeById(ans.pick) ? ans.pick : (ans.spec && ans.spec.mode) || "executive";
  }
  function now() { try { return performance.now(); } catch (e) { return Date.now(); } }
  function cap(s) { s = String(s || ""); return s.charAt(0).toUpperCase() + s.slice(1); }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many || one + "s"); }

  // "**bold**" in an answer's own sentences becomes <strong>; text nodes only.
  function rich(el, text) {
    el.textContent = "";
    String(text || "").split("**").forEach(function (part, i) {
      if (!part) return;
      if (i % 2) { var b = document.createElement("strong"); b.textContent = part; el.appendChild(b); }
      else el.appendChild(document.createTextNode(part));
    });
  }
  function make(tag, cls, text) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text != null) el.textContent = text;
    return el;
  }
  function heading(text) { return make("h4", "cgst-ans-h", text); }

  function rowOf(e, extra) {
    return { title: e.title, sub: cap(e.summary), meta: extra || (e.hub ? "Hub · " : "") + e.group, href: e.url, e: e,
      here: !!site.here && e === site.here };
  }

  // A link, or a button for an action row; both roam with the arrow keys.
  function actionable(row, cls) {
    var el;
    if (row.href) { el = make("a", cls); el.href = row.href; }
    else { el = make("button", cls); el.type = "button"; el.setAttribute("data-cgst", "ans-run"); el.setAttribute("data-index", String(ans.runs.push(row.run) - 1)); }
    el.setAttribute("data-cgst-item", "");
    return el;
  }

  function show(spec, t0) {
    ans.spec = spec;
    ans.all = false;
    ans.ms = Math.max(0, now() - (t0 || now()));
    paintAnswer(true);
  }

  function paintAnswer(arrive) {
    var s = ans.spec;
    if (!s || !ansEl) return;
    var mode = curMode();
    ans.runs = [];
    ans.acts = [];
    ansEl.hidden = false;
    setText(ansKind, s.kind + " · " + modeById(mode).name + (ans.pick === "auto" ? " (auto)" : ""));
    Array.prototype.forEach.call(ansEl.querySelectorAll(".cgst-mode"), function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-mode") === ans.pick));
    });
    setText(ansTitle, s.title);
    rich(ansLede, (s.thesis && (s.thesis[mode] || s.thesis.executive)) || "");
    ansBody.textContent = "";
    var order = {
      executive: ["lines", "facts", "steps", "rows", "tree", "next"],
      technical: ["facts", "steps", "table", "tree", "lines", "next"],
      pitch: ["bullets", "lines", "steps", "facts", "next", "rows"],
      analytical: ["spread", "gaps", "rows", "facts", "steps", "tree"]
    }[mode];
    order.forEach(function (part) { var el = PARTS[part](s, mode); if (el) ansBody.appendChild(el); });
    if (s.assumptions && s.assumptions.length) {
      var note = make("ul", "cgst-note");
      s.assumptions.forEach(function (a) { note.appendChild(make("li", "", a)); });
      ansBody.appendChild(note);
    }
    ansActs.textContent = "";
    (s.acts || []).filter(Boolean).forEach(function (a) {
      var b = make("button", "cgst-act", a.label);
      b.type = "button";
      b.setAttribute("data-cgst", "ans-act");
      b.setAttribute("data-index", String(ans.acts.push(a.run) - 1));
      b.setAttribute("data-cgst-item", "");
      ansActs.appendChild(b);
    });
    ansActs.hidden = !ansActs.children.length;
    var ms = ans.ms < 1 ? "<1 ms" : Math.round(ans.ms) + " ms";
    setText(ansBasis, "Resolved on this device in " + ms + (s.basis ? " · " + s.basis : ""));
    if (ansLive) ansLive.textContent = s.title + ". " + (s.rows ? plural(s.rows.length, "result") : "");
    if (arrive && !quiet()) {
      ansEl.classList.remove("cgst-routing");
      void ansEl.offsetWidth;                 // restart the arrival animation
      ansEl.classList.add("cgst-routing");
    }
  }

  function listRows(rows, limit) {
    var box = make("ol", "cgst-ans-list");
    rows.slice(0, limit).forEach(function (r) {
      var li = make("li");
      var el = actionable(r, "cgst-ans-row");
      if (r.here) el.setAttribute("data-here", "");
      if (r.meta) el.appendChild(make("span", "cgst-ans-meta", r.here ? "You are here · " + r.meta : r.meta));
      el.appendChild(make("strong", "", r.title));
      if (r.sub) el.appendChild(make("small", "", r.sub));
      li.appendChild(el);
      box.appendChild(li);
    });
    return box;
  }
  function moreButton(n) {
    var b = make("button", "cgst-act", "Show all " + n);
    b.type = "button";
    b.setAttribute("data-cgst", "ans-more");
    b.setAttribute("data-cgst-item", "");
    return b;
  }

  // Each part renders one structure, or nothing when the answer has no data for it.
  var PARTS = {
    // pitch mode leads with three bullets, so its list starts after them
    rows: function (s, mode) {
      var list = (s.rows || []).slice(mode === "pitch" ? 3 : 0);
      if (!list.length) return null;
      var limit = ans.all ? list.length : SITE.show, wrap = make("div");
      if (mode === "pitch") wrap.appendChild(heading("Also worth opening"));
      wrap.appendChild(listRows(list, limit));
      if (list.length > limit) { var m = moreButton(list.length); m.style.marginTop = "5px"; wrap.appendChild(m); }
      return wrap;
    },
    table: function (s) {
      if (!s.rows || !s.rows.length) return null;
      var limit = ans.all ? s.rows.length : 8;
      var wrap = make("div"), t = make("table", "cgst-table"), head = make("tr");
      t.setAttribute("data-cols", "pages");
      ["Page", "Path", "Cluster"].forEach(function (h) { var th = make("th", "", h); th.scope = "col"; head.appendChild(th); });
      var thead = make("thead"); thead.appendChild(head); t.appendChild(thead);
      var body = make("tbody");
      s.rows.slice(0, limit).forEach(function (r) {
        var tr = make("tr"), a = actionable(r, "");
        a.textContent = r.title;
        var c1 = make("td"); c1.appendChild(a);
        var c2 = make("td"); c2.appendChild(make("code", "", r.e ? r.e.path : r.meta || ""));
        tr.appendChild(c1); tr.appendChild(c2); tr.appendChild(make("td", "", r.e ? r.e.group : ""));
        body.appendChild(tr);
      });
      t.appendChild(body);
      wrap.appendChild(t);
      if (s.rows.length > limit) { var m = moreButton(s.rows.length); m.style.marginTop = "5px"; wrap.appendChild(m); }
      return wrap;
    },
    // Where the results sit across clusters: the analytical view of any list.
    spread: function (s) {
      var rows = (s.rows || []).filter(function (r) { return r.e; });
      if (rows.length < 2) return null;
      var counts = {}, names = [];
      rows.forEach(function (r) { if (!counts[r.e.group]) { counts[r.e.group] = 0; names.push(r.e.group); } counts[r.e.group]++; });
      names.sort(function (a, b) { return counts[b] - counts[a]; });
      var wrap = make("div"), t = make("table", "cgst-table"), head = make("tr");
      t.setAttribute("data-cols", "spread");
      ["Cluster", "Pages", "Share"].forEach(function (h, i) { var th = make("th", i ? "cgst-num" : "", h); th.scope = "col"; head.appendChild(th); });
      var thead = make("thead"); thead.appendChild(head); t.appendChild(thead);
      var body = make("tbody");
      names.slice(0, 6).forEach(function (n) {
        var tr = make("tr");
        tr.appendChild(make("td", "", n));
        tr.appendChild(make("td", "cgst-num", String(counts[n])));
        tr.appendChild(make("td", "cgst-num", Math.round(100 * counts[n] / rows.length) + "%"));
        body.appendChild(tr);
      });
      t.appendChild(body);
      wrap.appendChild(heading("Distribution"));
      wrap.appendChild(t);
      return wrap;
    },
    // Sectors with nothing in the result: the gaps an analyst would ask about.
    gaps: function (s) {
      if (!s.gaps || !s.rows || !s.rows.length || site.state !== "ready") return null;
      var have = s.rows.map(function (r) { return r.e; }).filter(Boolean);
      var none = SECTORS.filter(function (sec) {
        return !sec.missions && sec.pages && sec.pages.length && !have.some(function (e) { return sec.pages.indexOf(e) > -1; });
      }).map(function (sec) { return sec.title; });
      if (!none.length) return null;
      var p = make("p", "cgst-nextline");
      p.appendChild(make("b", "", "Gaps"));
      p.appendChild(document.createTextNode("Nothing here from " + none.join(", ") + "."));
      return p;
    },
    bullets: function (s) {
      if (!s.rows || !s.rows.length) return null;
      var ul = make("ul", "cgst-bullets");
      s.rows.slice(0, 3).forEach(function (r) {
        var li = make("li"), a = actionable(r, "");
        a.textContent = r.title;
        li.appendChild(a);
        if (r.sub) li.appendChild(document.createTextNode(" — " + r.sub));
        ul.appendChild(li);
      });
      return ul;
    },
    tree: function (s) {
      if (!s.tree || !s.tree.length) return null;
      var ul = make("ul", "cgst-tree");
      s.tree.forEach(function (n, i) {
        var li = make("li");
        if (n.depth) {
          var last = !s.tree[i + 1] || s.tree[i + 1].depth < n.depth;
          li.appendChild(make("span", "cgst-glyph", (n.depth > 1 ? "│  " : " ") + (last ? "└─" : "├─")));
        }
        var label = n.href || n.run ? actionable(n, "") : make("span");
        label.textContent = n.text;
        if (n.here) label.setAttribute("data-here", "");
        li.appendChild(label);
        if (n.count != null) li.appendChild(make("i", "", String(n.count)));
        ul.appendChild(li);
      });
      return ul;
    },
    facts: function (s) {
      if (!s.facts || !s.facts.length) return null;
      var dl = make("dl", "cgst-facts");
      s.facts.forEach(function (f) {
        if (!f || !f[1]) return;
        dl.appendChild(make("dt", "", f[0]));
        var dd = make("dd");
        if (f[2]) { var a = actionable({ href: f[2] }, ""); a.textContent = f[1]; dd.appendChild(a); }
        else dd.textContent = f[1];
        dl.appendChild(dd);
      });
      return dl;
    },
    steps: function (s) {
      if (!s.steps || !s.steps.length) return null;
      var ol = make("ol", "cgst-steps");
      s.steps.forEach(function (st) {
        var li = make("li");
        li.appendChild(make("strong", "", st.title + " · "));
        if (st.href || st.run) { var a = actionable(st, ""); a.textContent = st.text; li.appendChild(a); }
        else li.appendChild(document.createTextNode(st.text));
        if (st.why) li.appendChild(document.createTextNode(" — " + st.why));
        ol.appendChild(li);
      });
      return ol;
    },
    lines: function (s) {
      if (!s.lines || !s.lines.length) return null;
      var q2 = make("blockquote", "cgst-lines");
      s.lines.forEach(function (l) { q2.appendChild(make("p", "", l)); });
      return q2;
    },
    next: function (s) {
      if (!s.next) return null;
      var p = make("p", "cgst-nextline");
      p.appendChild(make("b", "", "Next step"));
      var a = actionable(s.next, "");
      a.textContent = s.next.label;
      p.appendChild(a);
      return p;
    }
  };

  function hideAnswer() {
    if (!ansEl) return;
    ansEl.hidden = true;
    ans.spec = null;
  }

  // Keyboard and screen-reader users land on the answer; the phone keyboard drops.
  function presentAnswer() {
    if (!ansEl || ansEl.hidden) return;
    try { ansTitle.focus({ preventScroll: true }); } catch (e) { ansTitle.focus(); }
    if (panel && ansEl.offsetParent === panel) panel.scrollTop = Math.max(0, ansEl.offsetTop - 8);
  }

  // ── Site Intelligence: answer builders ───────────────────────────────────
  function hasSentinel() { return !!(window.__cgSentinel || document.getElementById("sentinelShell")); }

  // Sentinel's conversation lives on the home page. A question asked anywhere
  // else rides there in sessionStorage (this tab only); the URL carries only
  // "#sentinel", so a link can never put words in the visitor's mouth.
  function handoff(prompt) {
    try { sessionStorage.setItem(SENTINEL_HANDOFF, String(prompt || "").slice(0, 800)); } catch (e) {}
    go(BASE + "index.html#sentinel");
  }
  function pickupHandoff() {
    if (location.hash !== "#sentinel") return;
    var prompt = "";
    try { prompt = sessionStorage.getItem(SENTINEL_HANDOFF) || ""; sessionStorage.removeItem(SENTINEL_HANDOFF); } catch (e) {}
    try { history.replaceState(null, "", location.pathname + location.search); } catch (e) {}
    if (!hasSentinel()) return;                 // never bounce the question onward
    setTimeout(function () { openSentinel(prompt.trim() || null); }, 60);
  }
  function sentinelAct(query) {
    return hasSentinel()
      ? { label: "Ask Sentinel", run: function () { openSentinel(query); } }
      : { label: "Continue with Sentinel", run: function () { handoff(query); } };
  }
  function graphAct(opts) { return { label: "Show on graph", run: function () { openGraph(opts); } }; }

  function pageRows(paths) {
    var out = [];
    paths.forEach(function (p) { var e = site.byPath[p]; if (e && out.indexOf(e) < 0) out.push(e); });
    return out.map(function (e) { return rowOf(e); });
  }
  function quoteList(list) { return list.map(function (w) { return "“" + w + "”"; }).join(", "); }
  function densest(rows) {
    var c = {}, best = "", n = 0;
    rows.forEach(function (r) { if (r.e) { c[r.e.group] = (c[r.e.group] || 0) + 1; if (c[r.e.group] > n) { n = c[r.e.group]; best = r.e.group; } } });
    return { name: best, n: n, groups: Object.keys(c).length };
  }
  // The words this page is about, for "similar", "services" and "docs".
  function pageText(e) {
    if (e) return e.title + " " + e.summary + " " + e.about;
    var meta = document.querySelector('meta[name="description"]');
    return document.title + " " + (meta ? meta.getAttribute("content") || "" : "");
  }
  function clusterOf(e) { return e ? site.byId[e.cluster] : null; }
  function ctaOf(e) {
    var c = clusterOf(e);
    var x = c && c.cta[0];
    return x ? { label: x.label, href: siteUrl(x.path) } : null;
  }
  // The memory layer: a page inside its cluster, as a tree.
  function memoryTree(e, max) {
    var c = clusterOf(e);
    if (!c) return [];
    var list = [c.pillar].concat(c.members), at = Math.max(0, list.indexOf(e.path)), lim = max || 6;
    var start = Math.max(0, Math.min(at - 2, list.length - lim));
    var tree = [{ depth: 0, text: c.name, count: list.length, run: function () { runIntent({ kind: "cluster", id: c.id }, ""); } }];
    list.slice(start, start + lim).forEach(function (p) {
      var x = site.byPath[p];
      tree.push({ depth: 1, text: (x.hub ? "Hub · " : "") + x.title, href: x.url, here: x === site.here });
    });
    if (list.length > lim) tree.push({ depth: 1, text: "+" + (list.length - lim) + " more in this cluster", run: tree[0].run });
    return tree;
  }

  function buildSearch(arg) {
    var hits = rank(arg), unknown = unknownTerms(arg), rows = hits.map(function (h) { return rowOf(h.e); });
    var d = densest(rows), top = hits[0] && hits[0].e;
    return {
      kind: "Site search", title: rows.length ? "Pages about “" + arg + "”" : "Nothing indexed matches “" + arg + "”",
      thesis: top ? {
        executive: "**" + plural(rows.length, "page") + "** match. Start with **" + top.title + "**: " + top.summary + ".",
        technical: "Ranked **" + rows.length + " of " + site.pages.length + "** indexed pages by word-prefix match: title ×6, summary ×3.5, path ×2.5, description ×1.5, cluster ×1; synonyms at 0.45.",
        pitch: "**" + top.title + "** — " + cap(top.summary) + ". " + (rows.length > 1 ? plural(rows.length - 1, "more page") + " go deeper." : ""),
        analytical: "**" + plural(rows.length, "match", "matches") + "** across **" + plural(d.groups, "cluster") + "**. Densest: **" + d.name + "** (" + d.n + ")."
      } : { executive: "No indexed page uses those words. Try a broader term, or search the Insights hub." },
      rows: rows, gaps: true,
      assumptions: unknown.length ? ["Ignored " + quoteList(unknown) + ": no indexed page uses " + (unknown.length === 1 ? "it." : "them.")] : [],
      basis: "keyword + synonym ranking over data/site-index.json",
      acts: [rows.length ? graphAct({ paths: hits.slice(0, 24).map(function (h) { return h.e.path; }), label: "“" + arg + "”" }) : null,
        { label: "Search Insights", run: function () { go(hubUrl(null, arg)); } }, sentinelAct(arg)]
    };
  }

  // "Take me to …": jump when one page clearly wins, otherwise show the field.
  function buildGo(arg, jump) {
    var hits = rank(arg), top = hits[0] && hits[0].e;
    if (jump && top && hits[0].s >= 6 && (!hits[1] || hits[0].s >= hits[1].s * 1.3)) { go(top.url); return null; }
    if (!top) return buildSearch(arg);
    var c = clusterOf(top), hub = c && site.byPath[c.pillar];
    return {
      kind: jump ? "Navigate" : "Locate", title: "Found: " + top.title,
      thesis: {
        executive: "**" + top.title + "** — " + top.summary + ". It sits in **" + top.group + "**" + (top.hub ? " as the topic hub." : "."),
        technical: "Path **" + top.path + "** · cluster **" + top.cluster + "** · " + plural(top.related.length, "related link") + " · score " + hits[0].s.toFixed(1) + (hits[1] ? " vs " + hits[1].s.toFixed(1) + " next" : "") + ".",
        pitch: "**" + top.title + "**: " + cap(top.summary) + ".",
        analytical: plural(hits.length, "candidate") + "; **" + top.title + "** leads" + (hits[1] ? " " + hits[0].s.toFixed(1) + " to " + hits[1].s.toFixed(1) + " over " + hits[1].e.title : "") + "."
      },
      rows: hits.slice(0, 5).map(function (h) { return rowOf(h.e); }),
      tree: [{ depth: 0, text: "ClearGlass Inc.", href: siteUrl("index.html") },
        hub && hub !== top ? { depth: 1, text: c.name, href: hub.url } : null,
        { depth: hub && hub !== top ? 2 : 1, text: top.title, href: top.url, here: top === site.here }].filter(Boolean),
      next: { label: "Open " + top.title, href: top.url },
      assumptions: jump && hits[1] ? ["Two pages score close, so Sentinel shows them rather than guessing."] : [],
      basis: "keyword + synonym ranking over data/site-index.json",
      acts: [{ label: "Open page", run: function () { go(top.url); } }, graphAct({ paths: [top.path], cluster: top.cluster })]
    };
  }

  function buildSector(arg) {
    var sel = typeof arg === "string" ? sectorsIn(arg) : arg;
    if (!sel) return buildSearch(String(arg || ""));
    if (sel.ids.length === 1 && sel.ids[0] === "missions") return buildMissions();
    sel = { ids: sel.ids.filter(function (id) { return id !== "missions"; }), any: sel.any };
    var names = sel.ids.map(function (id) { return sectorById(id).title; });
    var res = sectorPages(sel), rows = res.pages.map(function (e) { return rowOf(e); }), d = densest(rows);
    var title = names.join(res.joined ? " + " : " ∩ "), first = res.pages[0];
    var assumptions = [];
    if (sel.any && typeof arg === "string") assumptions.push("Read “" + arg + "” as " + names.join(" or ") + ".");
    if (res.empty) assumptions.push("No page is in both " + names.join(" and ") + ", so this lists pages in either.");
    return {
      kind: "Sector", title: title,
      thesis: first ? {
        executive: "**" + plural(rows.length, "page") + "** in " + title + ". Start at **" + first.title + "** — " + first.summary + ".",
        technical: "Sector membership: a page's cluster, its path, or its title and summary words. " + plural(rows.length, "page") + " qualify across " + plural(d.groups, "cluster") + ".",
        pitch: "**" + first.title + "**: " + cap(first.summary) + ". " + (rows.length > 1 ? "Then " + plural(rows.length - 1, "more page") + " in " + title + "." : ""),
        analytical: "**" + plural(rows.length, "page") + "** across **" + plural(d.groups, "cluster") + "**; " + Math.round(100 * rows.length / site.pages.length) + "% of the site. Densest: **" + d.name + "** (" + d.n + ")."
      } : { executive: "No indexed page is in " + title + " yet." },
      rows: rows, gaps: true, assumptions: assumptions,
      basis: "Mission Control sector definitions · data/site-index.json",
      acts: [graphAct({ paths: res.pages.map(function (e) { return e.path; }), label: title }),
        { label: "Mission Control", run: function () { setMc(true, true); } }]
    };
  }

  function buildMissions() {
    return {
      kind: "Sector", title: "Missions",
      thesis: {
        executive: "**Six missions** open Sentinel's rule-guided briefs" + (hasSentinel() ? "." : " on the home page, where the conversation lives."),
        technical: "Each mission sends its prompt to sentinel.js, which answers from a fixed pathway table; nothing here reaches a model or a system."
      },
      rows: MISSIONS.map(function (m) {
        return { title: m.title, sub: m.sub, meta: m.code, run: function () { openSentinel(m.prompt); } };
      }),
      basis: "the six Sentinel missions"
    };
  }

  function buildCluster(id) {
    var c = site.byId[id];
    if (!c) return buildPages();
    var list = [c.pillar].concat(c.members), rows = pageRows(list), hub = site.byPath[c.pillar];
    return {
      kind: "Cluster", title: c.name,
      thesis: {
        executive: "**" + plural(list.length, "page") + "** in " + c.name + ", led by the **" + hub.title + "** hub: " + hub.summary + ".",
        technical: "Hub **" + c.pillar + "** plus " + plural(c.members.length, "member") + " in journey order; each carries a previous–hub–next rail.",
        analytical: plural(list.length, "page") + " = " + Math.round(100 * list.length / site.pages.length) + "% of the site."
      },
      rows: rows,
      tree: [{ depth: 0, text: c.name, count: list.length }].concat(list.slice(0, 8).map(function (p) {
        var x = site.byPath[p];
        return { depth: 1, text: (x.hub ? "Hub · " : "") + x.title, href: x.url, here: x === site.here };
      })),
      next: c.cta[0] ? { label: c.cta[0].label, href: siteUrl(c.cta[0].path) } : null,
      basis: "cluster from tools/internal_links.py",
      acts: [graphAct({ cluster: c.id }), { label: "Every page", run: function () { runIntent({ kind: "pages" }, ""); } }]
    };
  }

  function buildPages() {
    var big = site.clusters.slice().sort(function (a, b) { return b.members.length - a.members.length; })[0];
    return {
      kind: "Site map", title: "Every public page · " + site.pages.length,
      thesis: {
        executive: "**" + plural(site.pages.length, "page") + "** in **" + plural(site.clusters.length, "cluster") + "**, joined by **" + plural(site.links, "related link") + "**. Largest: **" + big.name + "** (" + (big.members.length + 1) + ").",
        technical: "The graph from tools/internal_links.py: pillar-and-cluster, rotated sibling links and curated bridges, exported to data/site-index.json.",
        pitch: "One map of ClearGlass: every service, platform, brief and policy, " + site.pages.length + " pages deep.",
        analytical: "Average " + (site.links / site.pages.length).toFixed(1) + " related links per page; " + site.clusters.length + " clusters from " + (Math.min.apply(null, site.clusters.map(function (c) { return c.members.length + 1; }))) + " to " + (big.members.length + 1) + " pages."
      },
      rows: site.pages.map(function (e) { return rowOf(e); }),
      tree: [{ depth: 0, text: "ClearGlass Inc.", count: site.pages.length }].concat(site.clusters.map(function (c) {
        return { depth: 1, text: c.name, count: c.members.length + 1, run: function () { runIntent({ kind: "cluster", id: c.id }, ""); } };
      })),
      basis: "data/site-index.json",
      acts: [graphAct({}), { label: "Mission Control", run: function () { setMc(true, true); } }]
    };
  }

  // Outside the graph, a page is explained by what it says about itself.
  function unmapped(kind) {
    var meta = document.querySelector('meta[name="description"]'), about = meta ? meta.getAttribute("content") || "" : "";
    var h1 = document.querySelector("h1");
    return {
      kind: kind, title: document.title || "This page",
      thesis: { executive: about ? about : "This page does not describe itself in its metadata." },
      facts: [["Heading", h1 ? h1.textContent.replace(/\s+/g, " ").trim() : ""], ["Address", location.pathname]],
      assumptions: [site.state === "ready"
        ? "This page is outside the public site graph (a utility, prototype or private surface), so Sentinel has only what the page says about itself."
        : "The site index is unavailable here, so Sentinel has only what the page says about itself."],
      acts: [graphAct({}), { label: "Every page", run: function () { runIntent({ kind: "pages" }, ""); } }]
    };
  }

  function buildExplain() {
    var e = site.here;
    if (!e) return unmapped("Explain · this page");
    var c = clusterOf(e), hub = site.byPath[c.pillar], cta = ctaOf(e), size = c.members.length + 1;
    var reach = {};
    e.related.forEach(function (p) { reach[site.byPath[p].cluster] = 1; });
    return {
      kind: "Explain · this page", title: e.title, mode: "executive",
      thesis: {
        executive: "**" + e.title + "** — " + e.summary + ". " + (e.about || ""),
        technical: "**" + e.path + "** · " + (e.hub ? "hub of" : "page in") + " **" + c.name + "** · " + plural(e.related.length, "related link") + " · journey " +
          (site.byPath[e.prev] ? site.byPath[e.prev].title : "—") + " → " + (site.byPath[e.next] ? site.byPath[e.next].title : "—") + ".",
        pitch: cap(e.summary) + "." + (cta ? " Next: **" + cta.label + "**." : ""),
        analytical: "One of **" + size + " pages** in " + c.name + " (" + Math.round(100 * size / site.pages.length) + "% of the site); it links out to **" + plural(e.related.length, "page") + "** in **" + plural(Object.keys(reach).length, "cluster") + "**."
      },
      facts: [["What it is", cap(e.summary)], ["Cluster", c.name, hub.url], ["Role", e.hub ? "Topic hub" : "Page in the " + hub.title + " hub"],
        ["Description", e.about]],
      tree: memoryTree(e, 6), rows: pageRows(e.related), next: cta,
      basis: "this page's row in data/site-index.json",
      acts: [{ label: "Related pages", run: function () { smart("related"); } }, { label: "Executive brief", run: function () { smart("brief"); } },
        graphAct({ cluster: e.cluster })]
    };
  }

  // Extractive, never generated: the reading section's own opening sentences.
  function currentSection() {
    var hs = Array.prototype.filter.call(document.querySelectorAll("h1,h2,h3"), function (h) {
      return !root.contains(h) && !(h.closest && h.closest("#cg-related,nav,footer,[aria-hidden='true'],[hidden]")) &&
        h.getClientRects().length && h.textContent.trim();
    });
    if (!hs.length) return null;
    var line = window.innerHeight * 0.4, pick = hs[0];
    hs.forEach(function (h) { if (h.getBoundingClientRect().top <= line) pick = h; });
    return pick;
  }
  function sectionText(h) {
    var level = +h.tagName.charAt(1), out = [], chars = 0;
    var walker = document.createTreeWalker(document.body, 1, {
      acceptNode: function (el) {
        if (el === root || el.id === "cg-related" || /^(SCRIPT|STYLE|NAV|FOOTER|NOSCRIPT|svg|TEMPLATE)$/.test(el.tagName) ||
            el.getAttribute("aria-hidden") === "true" || el.hidden) return 2;   // FILTER_REJECT: skip the subtree
        return 1;
      }
    });
    walker.currentNode = h;
    var el;
    while ((el = walker.nextNode()) && chars < 1800) {
      if (/^H[1-6]$/.test(el.tagName) && +el.tagName.charAt(1) <= level) break;
      if (!/^(P|LI|BLOCKQUOTE|DD|FIGCAPTION)$/.test(el.tagName) || el.querySelector("p,li")) continue;
      var t = el.textContent.replace(/\s+/g, " ").trim();
      if (t.length > 24) { out.push(t); chars += t.length; }
    }
    return out;
  }
  function buildSummary() {
    var h = currentSection();
    if (!h) return { kind: "Summary · extractive", title: "No sections to read", mode: "executive",
      thesis: { executive: "This page has no headings Sentinel can find, so there is no section to summarize." } };
    var paras = sectionText(h), text = paras.join(" ");
    var sentences = (text.match(/[^.!?]+[.!?]+(?=\s|$)/g) || (text ? [text] : [])).map(function (s) { return s.trim(); });
    var key = sentences.slice(0, 3).map(function (s) { return s.length > 240 ? s.slice(0, 237) + "…" : s; });
    var wordsN = text ? text.split(" ").length : 0, title = h.textContent.replace(/\s+/g, " ").trim();
    return {
      kind: "Summary · extractive", title: title, mode: "executive",
      thesis: key.length ? {
        executive: "The section's own opening lines, **quoted, not rewritten**: about **" + plural(wordsN, "word") + "**, " + Math.max(1, Math.round(wordsN / 230)) + " min to read in full.",
        technical: "Extracted from the " + h.tagName.toLowerCase() + " nearest the top of the view: " + plural(paras.length, "block") + ", first " + plural(key.length, "sentence") + " shown.",
        analytical: plural(paras.length, "paragraph") + ", " + plural(wordsN, "word") + "; the lines below are its first " + plural(key.length, "sentence") + "."
      } : { executive: "This section has no body text under its heading." },
      lines: key,
      assumptions: ["“This section” is the heading nearest the top of the screen."],
      basis: "extractive · this page's text",
      acts: [{ label: "Jump to section", run: function () {
        if (!h.hasAttribute("tabindex")) h.setAttribute("tabindex", "-1");
        try { h.scrollIntoView({ block: "start", behavior: quiet() ? "auto" : "smooth" }); } catch (e) { h.scrollIntoView(); }
        try { h.focus({ preventScroll: true }); } catch (e) {}
      } }, { label: "Explain this page", run: function () { smart("explain"); } }]
    };
  }

  function buildRelated(arg) {
    var e = arg ? (rank(arg)[0] || {}).e : site.here;
    if (!e) return arg ? buildSearch(arg) : unmapped("Related pages");
    var rows = pageRows(e.related.concat([e.prev, e.next]));
    var sel = arg ? sectorsIn(arg) : null;
    if (sel && !sel.any && sel.ids.length === 1 && sectorById(sel.ids[0]).pages) {
      sectorById(sel.ids[0]).pages.forEach(function (x) {
        if (x !== e && !rows.some(function (r) { return r.e === x; })) rows.push(rowOf(x));
      });
    }
    return {
      kind: "Related", title: "Related to " + e.title,
      thesis: {
        executive: "**" + plural(rows.length, "page") + "** connect to **" + e.title + "**: its journey neighbours, cluster siblings and curated bridges.",
        technical: plural(e.related.length, "outbound link") + " from **" + e.path + "** (tools/internal_links.py related_targets) plus its previous and next pages.",
        analytical: "Links reach **" + plural(densest(rows).groups, "cluster") + "**; densest: **" + densest(rows).name + "**."
      },
      rows: rows, tree: memoryTree(e, 5), gaps: true,
      assumptions: arg ? ["Read “" + arg + "” as " + e.title + ", the best-ranked page."] : [],
      basis: "related_targets + journey rail · data/site-index.json",
      acts: [graphAct({ paths: [e.path].concat(e.related), cluster: e.cluster }), { label: "Similar content", run: function () { smart("similar"); } }]
    };
  }

  function buildServices() {
    var e = site.here, svc = sectorById("services").pages || [];
    var c = clusterOf(e), rows = [];
    if (c) c.cta.forEach(function (x) { var p = site.byPath[x.path]; if (p) rows.push(rowOf(p, "Recommended · " + x.label)); });
    rank(pageText(e), svc).forEach(function (h) {
      if (h.e !== e && !rows.some(function (r) { return r.e === h.e; })) rows.push(rowOf(h.e));
    });
    rows = rows.slice(0, 8);
    var top = rows[0];
    return {
      kind: "Related services", title: "Services for " + (e ? e.title : document.title || "this page"), mode: "pitch",
      thesis: top ? {
        executive: "**" + plural(rows.length, "service") + "** fit this page. Lead with **" + top.title + "**: " + top.sub + ".",
        pitch: "Turn this into an engagement: **" + top.title + "** — " + top.sub + ".",
        technical: "The cluster's two conversion paths first, then services ranked by overlap with this page's title, summary and description.",
        analytical: plural(rows.length, "service") + " matched out of " + svc.length + " in the Services sector."
      } : { executive: "No service matches this page yet; the Services hub lists every engagement." },
      rows: rows, next: top ? { label: top.title, href: top.href } : { label: "Services & engagements", href: siteUrl("offers/index.html") },
      basis: "cluster conversion paths + Services sector ranking",
      acts: [{ label: "All services", run: function () { runIntent({ kind: "sector", arg: "services" }, ""); } }]
    };
  }

  function buildBrief() {
    var e = site.here;
    if (!e) return unmapped("Executive brief");
    var c = clusterOf(e), hub = site.byPath[c.pillar], cta = ctaOf(e);
    var adj = pageRows(e.related).filter(function (r) { return r.e.cluster !== "blog"; }).slice(0, 3);
    var evidence = rank(pageText(e), sectorById("research").pages || []).filter(function (h) { return h.e !== e; })[0];
    var facts = [
      ["Subject", e.title, e.url],
      ["What it is", cap(e.summary)],
      ["Where it sits", c.name + (e.hub ? " (topic hub)" : " · hub: " + hub.title), hub.url],
      ["Adjacent", adj.map(function (r) { return r.title; }).join(" · ")],
      ["Evidence", evidence ? evidence.e.title : "", evidence ? evidence.e.url : ""],
      ["Next step", cta ? cta.label : "", cta ? cta.href : ""]
    ];
    var copy = ["EXECUTIVE BRIEF · " + e.title].concat(facts.filter(function (f) { return f[1]; }).map(function (f) { return f[0] + ": " + f[1]; }),
      ["Source: ClearGlass site index, assembled on this device."]).join("\n");
    return {
      kind: "Executive brief", title: e.title, mode: "executive",
      thesis: {
        executive: "**Bottom line:** " + cap(e.summary) + ". " + (cta ? "Recommended next step: **" + cta.label + "**." : ""),
        technical: "Brief fields come from this page's index row, its cluster, its related links and the best-matching Insights brief.",
        pitch: "**" + e.title + "** — " + cap(e.summary) + ". " + (cta ? "**" + cta.label + "**." : ""),
        analytical: "Position: " + (e.hub ? "hub" : "member") + " of " + c.name + "; " + plural(e.related.length, "related link") + "; evidence " + (evidence ? "found" : "not found") + " in Insights."
      },
      facts: facts,
      assumptions: ["Assembled from the site index, not written by a language model."],
      basis: "site index + Insights ranking",
      acts: [{ label: "Copy brief", run: function () { copyText(copy); } }, { label: "Action plan", run: function () { smart("plan"); } },
        graphAct({ cluster: e.cluster })]
    };
  }

  function copyText(text) {
    function done(ok) { if (ansLive) ansLive.textContent = ok ? "Brief copied to the clipboard" : "Copy is not available in this browser"; }
    try { navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); }); }
    catch (e) { done(false); }
  }

  function buildPlan() {
    var e = site.here;
    if (!e) return unmapped("Action plan");
    var c = clusterOf(e), hub = site.byPath[c.pillar], cta = ctaOf(e);
    var adj = pageRows(e.related).filter(function (r) { return r.e.cluster !== "blog" && r.e !== hub; })[0];
    var brief = rank(pageText(e), sectorById("research").pages || []).filter(function (h) { return h.e !== e; })[0];
    var steps = [
      { title: "Orient", text: e.hub ? "You are on the " + c.name + " hub" : hub.title, href: e.hub ? "" : hub.url, why: "the topic hub frames the cluster" },
      adj ? { title: "Explore", text: adj.title, href: adj.href, why: adj.sub } : null,
      brief ? { title: "Deepen", text: brief.e.title, href: brief.e.url, why: "the closest Insights brief" } : null,
      cta ? { title: "Engage", text: cta.label, href: cta.href, why: "the cluster's conversion path" } : null
    ].filter(Boolean);
    return {
      kind: "Action plan", title: "Plan from " + e.title, mode: "executive",
      thesis: {
        executive: "**" + plural(steps.length, "step") + "** from here to an engagement: orient, explore, deepen, engage.",
        technical: "Steps follow the site's journey model: hub → adjacent capability → evidence → governed engagement.",
        pitch: "From interest to a scoped engagement in **" + plural(steps.length, "move") + "**."
      },
      steps: steps, basis: "journey model · tools/internal_links.py",
      acts: [{ label: "Next step", run: function () { smart("next"); } }]
    };
  }

  function buildNext() {
    var e = site.here;
    if (!e) return unmapped("Next step");
    var nxt = site.byPath[e.next], c = clusterOf(e), cta = ctaOf(e);
    var rows = [nxt ? rowOf(nxt, "Next in this journey") : null, site.byPath[c.pillar] !== e ? rowOf(site.byPath[c.pillar], "Topic hub") : null]
      .filter(Boolean);
    return {
      kind: "Next step", title: nxt ? nxt.title : "Next step", mode: "pitch",
      thesis: {
        executive: nxt ? "Next in this journey: **" + nxt.title + "** — " + nxt.summary + "." : "This page ends its journey.",
        pitch: cta ? "Ready to act? **" + cta.label + "**." + (nxt ? " Still exploring? **" + nxt.title + "**." : "") : "",
        technical: "Next = the following page in the cluster's journey rail (" + (nxt ? nxt.path : "none") + ")."
      },
      rows: rows, next: cta, basis: "journey rail · data/site-index.json"
    };
  }

  function buildSimilar() {
    var e = site.here;
    var hits = rank(pageText(e)).filter(function (h) { return h.e !== e; }).slice(0, 10);
    var rows = hits.map(function (h) { return rowOf(h.e); });
    return {
      kind: "Similar content", title: "Like " + (e ? e.title : document.title || "this page"), mode: "analytical",
      thesis: rows.length ? {
        executive: "**" + rows[0].title + "** is closest: " + rows[0].sub + ".",
        analytical: "**" + plural(rows.length, "page") + "** share this page's vocabulary, across **" + plural(densest(rows).groups, "cluster") + "**.",
        technical: "Ranked by word overlap with this page's title, summary and description, the same ranking as site search."
      } : { executive: "No other page shares enough of this page's words." },
      rows: rows, gaps: true, basis: "vocabulary overlap · data/site-index.json",
      acts: [graphAct({ paths: rows.map(function (r) { return r.e.path; }), label: "similar pages" })]
    };
  }

  function buildDocs(arg) {
    var docs = sectorById("documents").pages || [];
    var hits = rank(arg || pageText(site.here), docs).map(function (h) { return h.e; });
    var rows = (hits.length ? hits : docs).slice(0, 10).map(function (e) { return rowOf(e); });
    return {
      kind: "Documentation", title: arg ? "Documentation for “" + arg + "”" : "Documentation near this page", mode: "technical",
      thesis: {
        executive: hits.length ? "**" + plural(hits.length, "document") + "** match. Start with **" + rows[0].title + "**." : "Nothing matches this page directly; these are the site's core documents.",
        technical: "Documents sector: the legal cluster, docs/ and operations/ runbooks, and pages titled spec, runbook, whitepaper, checklist, framework or blueprint.",
        analytical: (hits.length ? hits.length : 0) + " of " + docs.length + " documents match."
      },
      rows: rows,
      assumptions: hits.length ? [] : ["No document shares this page's words, so the list falls back to the Documents sector."],
      basis: "Documents sector · data/site-index.json",
      acts: [{ label: "All documents", run: function () { runIntent({ kind: "sector", arg: "documents" }, ""); } }]
    };
  }

  function answerOffline() {
    show({
      kind: "Site intelligence", title: "Site index unavailable here",
      thesis: { executive: "Sentinel reads the site graph from **data/site-index.json**, and this page could not load it (offline, or opened from a file). The Authority Network page maps every page." },
      rows: [{ title: "Authority Network", sub: "The ClearGlass pillar-and-cluster site graph", meta: "Static map", href: BASE + SITE.graph },
        { title: "Insights hub", sub: "Every brief", meta: "Intel Desk", href: hubUrl() }]
    }, now());
    presentAnswer();
  }

  var BUILDERS = {
    pages: buildPages, explain: buildExplain, summarize: buildSummary, related: function (it) { return buildRelated(it.arg); },
    services: buildServices, brief: buildBrief, plan: buildPlan, next: buildNext, similar: buildSimilar,
    docs: function (it) { return buildDocs(it.arg); }, sector: function (it) { return buildSector(it.arg); },
    cluster: function (it) { return buildCluster(it.id); }, go: function (it) { return buildGo(it.arg, true); },
    locate: function (it) { return buildGo(it.arg, false); }, search: function (it) { return buildSearch(it.arg); }
  };
  // The page's own text is enough for these when the index cannot load.
  var OFFLINE_OK = { summarize: 1, explain: 1 };

  function runIntent(it, query, mode) {
    if (!it) return;
    if (it.kind === "map") { openGraph({}); return; }
    function build() {
      var t0 = now(), spec = BUILDERS[it.kind] ? BUILDERS[it.kind](it) : null;
      if (!spec) return;                       // navigated away
      spec.mode = mode || (query ? modeFor(query) : spec.mode) || "executive";
      show(spec, t0);
      presentAnswer();
    }
    if (site.state === "ready" || (site.state === "static" && OFFLINE_OK[it.kind])) { build(); return; }
    if (site.state === "static") { answerOffline(); return; }
    loadSite(function () {
      if (site.state === "ready" || OFFLINE_OK[it.kind]) build();
      else answerOffline();
    });
  }

  function smart(id) {
    var s = SMART.filter(function (x) { return x.id === id; })[0];
    if (s) runIntent({ kind: s.id, arg: "" }, "", s.mode);
  }

  // Free text with no site meaning: Sentinel where it lives, a search elsewhere.
  function runQuery(text) {
    var query = String(text || "").trim().slice(0, 800);
    if (!query) return;
    var it = intentOf(query);
    if (it) { runIntent(it, query); return; }
    if (hasSentinel()) { openSentinel(query); return; }
    runIntent({ kind: "search", arg: query }, query);
  }

  // ── Mission Control ──────────────────────────────────────────────────────
  var mcToggle, mcEl;
  function setMc(open, reveal) {
    if (!mcEl || !mcToggle) return;
    mcEl.hidden = !open;
    mcToggle.setAttribute("aria-expanded", String(open));
    try { localStorage.setItem(MC_KEY, open ? "1" : "0"); } catch (e) {}
    if (open && reveal) {
      try { mcEl.scrollIntoView({ block: "nearest" }); } catch (e) {}
      var first = mcEl.querySelector("button");
      if (first) { try { first.focus({ preventScroll: true }); } catch (e) { first.focus(); } }
    }
  }
  function runCommand(id) {
    if (id === "search") {
      show({
        kind: "Search", title: "Ask about any page", mode: "executive",
        thesis: { executive: "Type a question or a page name. Sentinel ranks **every public page** on this device, and jumps when one clearly wins." },
        acts: ["Where is the pricing page?", "Show all cybersecurity services", "Take me to OSINT workflows",
          "What pages discuss autonomous agents?", "Map the platform"].map(function (x) {
          return { label: x, run: function () { runQuery(x); } };
        })
      }, now());
      try { askInput.focus({ preventScroll: true }); } catch (e) { askInput.focus(); }
      return;
    }
    if (id === "mission") {
      var m = q(".cgst-mission");
      if (m) { try { m.scrollIntoView({ block: "nearest" }); } catch (e) {} try { m.focus({ preventScroll: true }); } catch (e) { m.focus(); } }
      return;
    }
    if (id === "briefing") { openSentinel(MISSIONS[0].prompt); return; }
    if (id === "products") { runIntent({ kind: "sector", arg: "products" }, "", "executive"); return; }
    if (id === "report") { smart("brief"); return; }
    if (id === "architecture") {
      runIntent({ kind: "explain" }, "", "technical");
      openGraph({ cluster: site.here ? site.here.cluster : "" });
      return;
    }
    if (id === "intel") {
      runIntent({ kind: "sector", arg: "intelligence" }, "", "executive");
    }
  }

  // ── Intelligence Graph ───────────────────────────────────────────────────
  // Every page as a node around its cluster, every cluster around Sentinel
  // Core. Zoom with the wheel, pinch, +/− or the keyboard; drag to pan. The
  // list beside it holds the same graph as a tree, for any input.
  var SVGNS = "http://www.w3.org/2000/svg";
  var HUES = ["#4cc3ff", "#ee6365", "#78e0c8", "#f2b04b", "#a99bff", "#ff8fb1", "#5ef0a8", "#7fb2ff", "#e7b9ba", "#64d2ff", "#ffd166", "#b5f5e0"];
  var graph = { built: false, open: false, vb: { x: 0, y: 0, w: 1000 }, focus: "", hits: [], hitLabel: "", lastFocus: null, anim: 0,
    node: {}, pts: {}, drag: null, pinch: null, suppress: false };
  var graphEl, gSvg, gView, gSide, gTree, gPath, gFind, gSub, gLinks;

  function sv(tag, attrs, parent) {
    var el = document.createElementNS(SVGNS, tag);
    Object.keys(attrs || {}).forEach(function (k) { el.setAttribute(k, String(attrs[k])); });
    if (parent) parent.appendChild(el);
    return el;
  }
  function svText(parent, x, y, text, cls, anchor) {
    var t = sv("text", { x: x.toFixed(1), y: y.toFixed(1), "class": cls, "text-anchor": anchor || "middle" }, parent);
    t.textContent = text;
    return t;
  }

  function buildGraph() {
    if (graph.built || site.state !== "ready" || !gSvg) return;
    graph.built = true;
    var C = 500, R = 215, n = site.clusters.length;
    var orbit = sv("g", {}, gSvg), spokes = sv("g", {}, gSvg), edges = sv("g", {}, gSvg);
    gLinks = sv("g", {}, gSvg);
    var nodes = sv("g", {}, gSvg), hubs = sv("g", {}, gSvg);
    [R, 330, 430].forEach(function (r) { sv("circle", { cx: C, cy: C, r: r, "class": "cgst-gorbit" }, orbit); });

    site.clusters.forEach(function (c, i) {
      var a = -Math.PI / 2 + (i / n) * Math.PI * 2, hue = HUES[i % HUES.length];
      var cx = C + R * Math.cos(a), cy = C + R * Math.sin(a);
      c.gx = cx; c.gy = cy; c.hue = hue;
      sv("line", { x1: C, y1: C, x2: cx.toFixed(1), y2: cy.toFixed(1), "class": "cgst-gspoke", "data-cluster": c.id, style: "--h:" + hue }, spokes);
      var list = [c.pillar].concat(c.members), per = 14, span = (Math.PI * 2 / n) * 0.82, dense = list.length > 14;
      c.box = { x0: cx, y0: cy, x1: cx, y1: cy };
      list.forEach(function (path, j) {
        var e = site.byPath[path], row = Math.floor(j / per), inRow = Math.min(per, list.length - row * per), k = j - row * per;
        var ang = a + span * ((k + 0.5) / inRow - 0.5), r = 318 + row * 44;
        var x = C + r * Math.cos(ang), y = C + r * Math.sin(ang);
        sv("line", { x1: cx.toFixed(1), y1: cy.toFixed(1), x2: x.toFixed(1), y2: y.toFixed(1), "class": "cgst-gedge", "data-cluster": c.id, style: "--h:" + hue }, edges);
        var link = sv("a", { href: e.url, "class": "cgst-gnode", "data-cluster": c.id, "data-path": path, tabindex: "-1",
          "aria-label": e.title + " — " + e.summary, style: "--h:" + hue }, nodes);
        if (e.hub) link.setAttribute("data-hub", "");
        if (e === site.here) {
          link.classList.add("cgst-ghere");
          sv("circle", { cx: x.toFixed(1), cy: y.toFixed(1), r: 9, "class": "cgst-gping" }, link);
        }
        sv("circle", { cx: x.toFixed(1), cy: y.toFixed(1), r: e.hub ? 7 : 4.6 }, link);
        // labels run outward along the node's own ray, so neighbours never collide
        var right = Math.cos(ang) >= 0, lx = x + Math.cos(ang) * 9, ly = y + Math.sin(ang) * 9;
        var deg = ang * 180 / Math.PI + (right ? 0 : 180);
        var lab = svText(link, lx, ly, e.title.length > 30 ? e.title.slice(0, 29) + "…" : e.title, "cgst-glabel", right ? "start" : "end");
        lab.setAttribute("dominant-baseline", "central");
        lab.setAttribute("transform", "rotate(" + deg.toFixed(1) + " " + lx.toFixed(1) + " " + ly.toFixed(1) + ")");
        if (dense) link.setAttribute("data-dense", "");
        graph.node[path] = { el: link, x: x, y: y };
        // the fit keeps room for the label's reach, not just the node
        var reach = dense ? 12 : 120, ex = x + Math.cos(ang) * reach, ey = y + Math.sin(ang) * reach;
        c.box.x0 = Math.min(c.box.x0, x, ex); c.box.x1 = Math.max(c.box.x1, x, ex);
        c.box.y0 = Math.min(c.box.y0, y, ey); c.box.y1 = Math.max(c.box.y1, y, ey);
      });
      var size = 13 + Math.sqrt(list.length) * 2.6;
      var g = sv("g", { "class": "cgst-gcluster", tabindex: "0", role: "button", "data-cluster": c.id, style: "--h:" + hue,
        "aria-label": c.name + ": " + plural(list.length, "page") + ". Focus the graph on it" }, hubs);
      sv("circle", { cx: cx.toFixed(1), cy: cy.toFixed(1), r: (size + 9).toFixed(1), "class": "cgst-ghalo" }, g);
      sv("circle", { cx: cx.toFixed(1), cy: cy.toFixed(1), r: size.toFixed(1), "class": "cgst-gdisc" }, g);
      svText(g, cx, cy + 3, String(list.length), "cgst-gcn");
      var label = c.name.split(/ [&·] /)[0].toUpperCase();
      svText(g, cx, cy + size + 13, label.length > 22 ? label.slice(0, 21) + "…" : label, "cgst-gcl");
    });

    var core = sv("g", { "class": "cgst-gcore", tabindex: "0", role: "button", "aria-label": "Sentinel Core: show the whole graph" }, gSvg);
    sv("circle", { cx: C, cy: C, r: 60, "class": "cgst-gpulse" }, core);
    sv("circle", { cx: C, cy: C, r: 60, "class": "cgst-gpulse" }, core);
    var grad = sv("radialGradient", { id: "cgstCoreGrad" }, sv("defs", {}, gSvg));
    sv("stop", { offset: "0%", "stop-color": "#ee6365", "stop-opacity": ".55" }, grad);
    sv("stop", { offset: "100%", "stop-color": "#0b080b", "stop-opacity": "1" }, grad);
    sv("circle", { cx: C, cy: C, r: 46, fill: "url(#cgstCoreGrad)", stroke: "#ee6365", "stroke-width": "1.6", "class": "cgst-gdisc" }, core);
    sv("path", { d: "M500 500 L500 456 A44 44 0 0 1 538 478 Z", fill: "rgba(76,195,255,.35)", "class": "cgst-gsweep" }, core);
    sv("circle", { cx: C, cy: C, r: 5, fill: "#ee6365" }, core);
    svText(core, C, C + 64, "SENTINEL CORE", "cgst-gcl");
  }

  // The label scale keeps text the same size on screen at any zoom.
  function paintVB() {
    var v = graph.vb;
    gSvg.setAttribute("viewBox", v.x.toFixed(1) + " " + v.y.toFixed(1) + " " + v.w.toFixed(1) + " " + v.w.toFixed(1));
    var r = gView.getBoundingClientRect(), px = Math.max(160, Math.min(r.width, r.height) || 600);
    gSvg.style.setProperty("--gs", (v.w / px * 1.12).toFixed(3));
  }
  function clampVB(v) {
    var w = Math.max(150, Math.min(1500, v.w));
    var cx = v.x + v.w / 2, cy = v.y + v.w / 2;
    cx = Math.max(-100, Math.min(1100, cx)); cy = Math.max(-100, Math.min(1100, cy));
    return { x: cx - w / 2, y: cy - w / 2, w: w };
  }
  function setVB(v, animate) {
    var to = clampVB(v);
    cancelAnimationFrame(graph.anim);
    if (!animate || quiet()) { graph.vb = to; paintVB(); return; }
    var from = graph.vb, t0 = now();
    (function step() {
      var k = Math.min(1, (now() - t0) / 420), e = 1 - Math.pow(1 - k, 3);
      graph.vb = { x: from.x + (to.x - from.x) * e, y: from.y + (to.y - from.y) * e, w: from.w + (to.w - from.w) * e };
      paintVB();
      if (k < 1) graph.anim = requestAnimationFrame(step);
    })();
  }
  function toSvg(clientX, clientY) {
    var r = gSvg.getBoundingClientRect(), v = graph.vb, side = Math.min(r.width, r.height) || 1;
    var ox = r.left + (r.width - side) / 2, oy = r.top + (r.height - side) / 2;     // xMidYMid meet
    return { x: v.x + (clientX - ox) / side * v.w, y: v.y + (clientY - oy) / side * v.w };
  }
  function zoomAt(f, pt, animate) {
    var v = graph.vb, p = pt || { x: v.x + v.w / 2, y: v.y + v.w / 2 }, w = Math.max(150, Math.min(1500, v.w * f)), s = w / v.w;
    setVB({ x: p.x - (p.x - v.x) * s, y: p.y - (p.y - v.y) * s, w: w }, animate);
  }
  function fitCluster(c) {
    if (!c) { setVB({ x: 0, y: 0, w: 1000 }, true); return; }
    var b = c.box, x0 = Math.min(b.x0, c.gx) - 40, x1 = Math.max(b.x1, c.gx) + 40, y0 = Math.min(b.y0, c.gy) - 50, y1 = Math.max(b.y1, c.gy) + 50;
    var w = Math.max(x1 - x0, y1 - y0, 260);
    setVB({ x: (x0 + x1) / 2 - w / 2, y: (y0 + y1) / 2 - w / 2, w: w }, true);
  }

  function focusCluster(id) {
    graph.focus = site.byId[id] ? id : "";
    Array.prototype.forEach.call(gSvg.querySelectorAll("[data-cluster]"), function (el) {
      var on = !!graph.focus && el.getAttribute("data-cluster") === graph.focus;
      el.classList.toggle("cgst-gon", on);
      if (el.classList.contains("cgst-gnode")) el.setAttribute("tabindex", on ? "0" : "-1");
    });
    paintDim();
    fitCluster(site.byId[graph.focus]);
    paintSide();
  }
  function paintDim() { gSvg.setAttribute("data-dim", graph.focus || graph.hits.length ? "1" : "0"); }

  function setHits(paths, label) {
    graph.hits = (paths || []).filter(function (p) { return graph.node[p]; });
    graph.hitLabel = label || "";
    Object.keys(graph.node).forEach(function (p) {
      var on = graph.hits.indexOf(p) > -1;
      graph.node[p].el.classList.toggle("cgst-ghit", on);
      if (on) graph.node[p].el.setAttribute("tabindex", "0");
      else if (!graph.focus || graph.node[p].el.getAttribute("data-cluster") !== graph.focus) graph.node[p].el.setAttribute("tabindex", "-1");
    });
    paintDim();
    paintSide();
  }

  // Data routing: a page's related links light up as flowing curves.
  function showLinks(path) {
    if (!gLinks) return;
    gLinks.textContent = "";
    var e = site.byPath[path], from = graph.node[path];
    if (!e || !from) return;
    e.related.forEach(function (p) {
      var to = graph.node[p];
      if (!to) return;
      var mx = (from.x + to.x) / 2, my = (from.y + to.y) / 2, cx = mx + (500 - mx) * 0.55, cy = my + (500 - my) * 0.55;
      sv("path", { d: "M" + from.x.toFixed(1) + " " + from.y.toFixed(1) + " Q" + cx.toFixed(1) + " " + cy.toFixed(1) + " " + to.x.toFixed(1) + " " + to.y.toFixed(1),
        "class": "cgst-glink" }, gLinks);
    });
    gPath.textContent = "";
    gPath.appendChild(document.createTextNode("Sentinel Core › " + e.group + " › "));
    gPath.appendChild(make("b", "", e.title));
    gPath.appendChild(document.createTextNode(" · " + plural(e.related.length, "link")));
  }
  function clearLinks() { if (gLinks) gLinks.textContent = ""; paintPath(); }
  function paintPath() {
    if (!gPath) return;
    gPath.textContent = "";
    var c = site.byId[graph.focus];
    gPath.appendChild(document.createTextNode("Sentinel Core"));
    if (c) { gPath.appendChild(document.createTextNode(" › ")); gPath.appendChild(make("b", "", c.name)); }
    else if (graph.hits.length) { gPath.appendChild(document.createTextNode(" › ")); gPath.appendChild(make("b", "", plural(graph.hits.length, "match", "matches") + (graph.hitLabel ? " · " + graph.hitLabel : ""))); }
  }

  // The same graph as a tree: the memory layer, and the keyboard's way in.
  function paintSide() {
    if (!gTree) return;
    paintPath();
    gTree.textContent = "";
    var tree = [], c = site.byId[graph.focus];
    if (graph.hits.length) {
      tree.push({ depth: 0, text: plural(graph.hits.length, "match", "matches") + (graph.hitLabel ? " · " + graph.hitLabel : ""), run: function () { gFind.value = ""; setHits([], ""); } });
      graph.hits.slice(0, 40).forEach(function (p) { var e = site.byPath[p]; tree.push({ depth: 1, text: e.title, href: e.url, path: p, here: e === site.here }); });
    } else if (c) {
      tree.push({ depth: 0, text: "← All sectors", run: function () { focusCluster(""); } });
      tree.push({ depth: 0, text: c.name, count: c.members.length + 1 });
      [c.pillar].concat(c.members).forEach(function (p) {
        var e = site.byPath[p];
        tree.push({ depth: 1, text: (e.hub ? "Hub · " : "") + e.title, href: e.url, path: p, here: e === site.here });
      });
    } else {
      tree.push({ depth: 0, text: "Sentinel Core", count: site.pages.length });
      site.clusters.forEach(function (x) {
        tree.push({ depth: 1, text: x.name, count: x.members.length + 1, here: !!site.here && site.here.cluster === x.id,
          run: function () { focusCluster(x.id); } });
      });
    }
    var ul = make("ul", "cgst-tree");
    tree.forEach(function (n, i) {
      var li = make("li");
      if (n.depth) {
        var last = !tree[i + 1] || tree[i + 1].depth < n.depth;
        li.appendChild(make("span", "cgst-glyph", " " + (last ? "└─" : "├─")));
      }
      var el;
      if (n.href) { el = make("a"); el.href = n.href; el.setAttribute("data-path", n.path || ""); }
      else if (n.run) { el = make("button"); el.type = "button"; el.addEventListener("click", n.run); }
      else el = make("span");
      el.textContent = n.text;
      if (n.here) el.setAttribute("data-here", "");
      li.appendChild(el);
      if (n.count != null) li.appendChild(make("i", "", String(n.count)));
      ul.appendChild(li);
    });
    gTree.appendChild(ul);
  }

  function openGraph(opts) {
    if (!graphEl) return;
    opts = opts || {};
    if (!graph.open) graph.lastFocus = document.activeElement;
    graphEl.hidden = false;
    graph.open = true;
    document.documentElement.classList.add("cgst-graph-open");
    syncRun();
    var title = graphEl.querySelector(".cgst-gtitle");
    try { title.focus({ preventScroll: true }); } catch (e) { title.focus(); }
    loadSite(function () {
      if (!graph.open) return;
      if (site.state !== "ready") {
        setText(gSub, "Site index unavailable here");
        gTree.textContent = "";
        var p = make("p", "cgst-gpath", "The graph is drawn from data/site-index.json, which this page could not load. ");
        var a = make("a", "", "Open the Authority Network map");
        a.href = BASE + SITE.graph;
        p.appendChild(a);
        gTree.appendChild(p);
        return;
      }
      buildGraph();
      setText(gSub, plural(site.pages.length, "page") + " · " + plural(site.clusters.length, "cluster") + " · " + plural(site.links, "link") + " · built from the site index");
      graph.hits = [];
      Object.keys(graph.node).forEach(function (p) { graph.node[p].el.classList.remove("cgst-ghit"); });
      if (gFind) gFind.value = "";
      paintVB();
      focusCluster(opts.cluster || "");
      if (opts.paths && opts.paths.length) setHits(opts.paths, opts.label || "");
    });
  }

  function closeGraph() {
    if (!graphEl || !graph.open) return;
    graphEl.hidden = true;
    graph.open = false;
    cancelAnimationFrame(graph.anim);
    document.documentElement.classList.remove("cgst-graph-open");
    syncRun();
    var back = graph.lastFocus;
    if (back && back.focus && back !== document.body && document.contains(back)) { try { back.focus({ preventScroll: true }); } catch (e) { back.focus(); } }
  }

  function wireGraph() {
    graphEl = q("[data-cgst-graph]");
    if (!graphEl) return;
    gSvg = graphEl.querySelector(".cgst-gsvg");
    gView = graphEl.querySelector("[data-cgst-gview]");
    gTree = graphEl.querySelector("[data-cgst-gtree]");
    gPath = graphEl.querySelector("[data-cgst-gpath]");
    gFind = graphEl.querySelector("#cgstGFind");
    gSub = graphEl.querySelector("[data-cgst-gsub]");
    gSide = graphEl.querySelector(".cgst-gside");

    graphEl.addEventListener("keydown", function (event) {
      if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); closeGraph(); return; }
      if (event.key === "Tab") {                      // keep focus inside the dialog
        var list = Array.prototype.filter.call(graphEl.querySelectorAll("button,input,a[href],[tabindex='0']"), function (el) {
          return el.getAttribute("tabindex") !== "-1" && el.getClientRects().length;
        });
        if (!list.length) return;
        var first = list[0], last = list[list.length - 1];
        if (event.shiftKey && (document.activeElement === first || !graphEl.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });
    graphEl.addEventListener("click", function (event) {
      if (event.target === graphEl) { closeGraph(); return; }
      var cl = event.target.closest ? event.target.closest(".cgst-gcluster") : null;
      if (cl) { focusCluster(cl.getAttribute("data-cluster") === graph.focus ? "" : cl.getAttribute("data-cluster")); return; }
      if (event.target.closest && event.target.closest(".cgst-gcore")) { setHits([], ""); if (gFind) gFind.value = ""; focusCluster(""); }
    });
    graphEl.addEventListener("keydown", function (event) {
      var t = event.target;
      if ((event.key === "Enter" || event.key === " ") && t.classList && (t.classList.contains("cgst-gcluster") || t.classList.contains("cgst-gcore"))) {
        event.preventDefault();
        t.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      }
    });
    // hover or focus on a page, in the graph or the list: route its links
    function pathOf(el) { var n = el && el.closest ? el.closest("[data-path]") : null; return n ? n.getAttribute("data-path") : ""; }
    graphEl.addEventListener("pointerover", function (event) { var p = pathOf(event.target); if (p) showLinks(p); });
    graphEl.addEventListener("focusin", function (event) { var p = pathOf(event.target); if (p) showLinks(p); });
    graphEl.addEventListener("pointerout", function (event) { if (pathOf(event.target) && !pathOf(event.relatedTarget)) clearLinks(); });

    gView.addEventListener("wheel", function (event) {
      if (!graph.built) return;
      event.preventDefault();
      zoomAt(event.deltaY > 0 ? 1.14 : 1 / 1.14, toSvg(event.clientX, event.clientY), false);
    }, { passive: false });
    gView.addEventListener("keydown", function (event) {
      if (event.target !== gView) return;
      var v = graph.vb, step = v.w * 0.08, k = event.key;
      if (k === "+" || k === "=") zoomAt(1 / 1.25, null, true);
      else if (k === "-" || k === "_") zoomAt(1.25, null, true);
      else if (k === "0") focusCluster("");
      else if (k === "ArrowLeft") setVB({ x: v.x - step, y: v.y, w: v.w });
      else if (k === "ArrowRight") setVB({ x: v.x + step, y: v.y, w: v.w });
      else if (k === "ArrowUp") setVB({ x: v.x, y: v.y - step, w: v.w });
      else if (k === "ArrowDown") setVB({ x: v.x, y: v.y + step, w: v.w });
      else return;
      event.preventDefault();
    });
    // drag to pan, two fingers to pinch; a drag never also clicks a node
    function dist() {
      var ids = Object.keys(graph.pts);
      if (ids.length < 2) return 0;
      var a = graph.pts[ids[0]], b = graph.pts[ids[1]];
      return Math.hypot(a.x - b.x, a.y - b.y);
    }
    gView.addEventListener("pointerdown", function (event) {
      if (!graph.built || (event.pointerType === "mouse" && event.button !== 0)) return;
      graph.pts[event.pointerId] = { x: event.clientX, y: event.clientY };
      var ids = Object.keys(graph.pts);
      if (ids.length === 1) graph.drag = { x: event.clientX, y: event.clientY, vb: graph.vb, moved: false, id: event.pointerId };
      else if (ids.length === 2) {
        var a = graph.pts[ids[0]], b = graph.pts[ids[1]];
        graph.pinch = { d: dist() || 1, vb: graph.vb, mid: toSvg((a.x + b.x) / 2, (a.y + b.y) / 2) };
        graph.drag = null;
      }
    });
    gView.addEventListener("pointermove", function (event) {
      if (!graph.pts[event.pointerId]) return;
      graph.pts[event.pointerId] = { x: event.clientX, y: event.clientY };
      if (graph.pinch) {
        var d = dist();
        if (!d) return;
        var v = graph.pinch.vb, w = Math.max(150, Math.min(1500, v.w * graph.pinch.d / d)), s = w / v.w, p = graph.pinch.mid;
        setVB({ x: p.x - (p.x - v.x) * s, y: p.y - (p.y - v.y) * s, w: w });
        graph.suppress = true;
        return;
      }
      var g = graph.drag;
      if (!g) return;
      var dx = event.clientX - g.x, dy = event.clientY - g.y;
      if (!g.moved && Math.abs(dx) + Math.abs(dy) < 5) return;
      if (!g.moved) { g.moved = true; gView.setAttribute("data-drag", "1"); try { gView.setPointerCapture(event.pointerId); } catch (e) {} }
      var r = gSvg.getBoundingClientRect(), side = Math.min(r.width, r.height) || 1, k = g.vb.w / side;
      setVB({ x: g.vb.x - dx * k, y: g.vb.y - dy * k, w: g.vb.w });
    });
    function lift(event) {
      delete graph.pts[event.pointerId];
      if (graph.drag && graph.drag.moved) graph.suppress = true;
      if (Object.keys(graph.pts).length < 2) graph.pinch = null;
      if (!Object.keys(graph.pts).length) { graph.drag = null; gView.removeAttribute("data-drag"); }
    }
    gView.addEventListener("pointerup", lift);
    gView.addEventListener("pointercancel", lift);
    gView.addEventListener("click", function (event) {
      if (graph.suppress) { event.preventDefault(); event.stopPropagation(); graph.suppress = false; }
    }, true);

    var findTimer = 0;
    if (gFind) gFind.addEventListener("input", function () {
      clearTimeout(findTimer);
      findTimer = setTimeout(function () {
        var v = gFind.value.trim();
        if (v.length < 2) { setHits([], ""); return; }
        setHits(rank(v).slice(0, 40).map(function (h) { return h.e.path; }), "“" + v + "”");
      }, 120);
    });
    graphEl.querySelector(".cgst-gfind").addEventListener("submit", function (event) { event.preventDefault(); });
    window.addEventListener("resize", function () { if (graph.open && graph.built) paintVB(); }, { passive: true });
  }

  // ── roving keyboard navigation inside the panel ──────────────────────────
  function items() {
    if (!panel) return [];
    // an item inside a hidden group (Intel Desk before its feed lands) is not
    // on screen, so arrow keys must not land on it
    return Array.prototype.filter.call(
      panel.querySelectorAll("[data-cgst-item]"),
      function (el) { return !el.disabled && !el.hidden && !(el.closest && el.closest("[hidden]")); }
    );
  }

  function panelKeys(event) {
    // the ask field keeps its own caret keys, and the header is a drag handle
    // whose arrow keys move the console (station-enhance.js)
    var t = event.target;
    if (t && (t.tagName === "INPUT" || (t.classList && t.classList.contains("cgst-head")))) return;
    var list = items();
    if (!list.length) return;
    var at = list.indexOf(document.activeElement);
    if (event.key === "ArrowDown" || event.key === "ArrowRight") { event.preventDefault(); list[(at + 1 + list.length) % list.length].focus(); }
    else if (event.key === "ArrowUp" || event.key === "ArrowLeft") { event.preventDefault(); list[(at - 1 + list.length) % list.length].focus(); }
    else if (event.key === "Home") { event.preventDefault(); list[0].focus(); }
    else if (event.key === "End") { event.preventDefault(); list[list.length - 1].focus(); }
  }

  // ── open / close ─────────────────────────────────────────────────────────
  function setOpen(open, moveFocus, persist) {
    root.setAttribute("data-open", String(open));
    dock.setAttribute("aria-expanded", String(open));
    labelDock();
    panel.setAttribute("aria-hidden", String(!open));
    if (persist) writeOpen(open);
    try { window.dispatchEvent(new CustomEvent("cg-station:toggle", { detail: { open: open } })); } catch (e) {}
    syncClock();
    syncRun();
    if (!open) closeSuggest();
    if (open) { typeStatus(); loadFeed(); loadSite(); }
    if (!moveFocus) return;
    if (open) {
      lastFocus = document.activeElement;
      // focusing the field would raise the keyboard over the console on phones
      var first = narrow() ? items()[0] : askInput;
      if (first) { try { first.focus({ preventScroll: true }); } catch (e) { first.focus(); } }
    } else if (dock.focus) dock.focus();
  }

  function syncTopClear() {
    var header = document.getElementById("navbar");
    var bottom = header ? header.getBoundingClientRect().bottom : 0;
    var clear = Math.max(40, Math.min(240, Math.round(bottom + 12)));
    document.documentElement.style.setProperty("--cgst-top-clear", clear + "px");
  }

  // ── build ────────────────────────────────────────────────────────────────
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"); }

  function build() {
    if (!document.body || document.getElementById("cg-station")) return;
    injectStyle();

    root = document.createElement("aside");
    root.id = "cg-station";
    // The console styles its own controls; future-buttons.js would otherwise
    // re-skin every button in it.
    root.setAttribute("data-no-future-glass", "");
    root.setAttribute("aria-label", "Sentinel Core command console");

    var sid = sessionId();

    var missionHTML = MISSIONS.map(function (m) {
      return '<button type="button" class="cgst-mission" data-cgst="mission" data-prompt="' + esc(m.prompt) + '" data-cgst-item>' +
        '<span class="cgst-code" aria-hidden="true">' + m.code + '</span>' +
        '<strong>' + esc(m.title) + '</strong><small>' + esc(m.sub) + '</small></button>';
    }).join("");

    var controlHTML = CONTROLS.map(function (c) {
      var inner = '<span class="cgst-ctl-dot" aria-hidden="true"></span>' +
        '<span class="cgst-ctl-tx"><strong>' + esc(c.title) + '</strong><small>' + esc(c.sub) + '</small></span>';
      if (c.act) {
        return '<button type="button" class="cgst-ctl" data-cgst="' + c.act + '" data-cgst-item aria-pressed="false">' +
          inner + '<span class="cgst-state" aria-hidden="true">OFF</span></button>';
      }
      // hrefs resolve against the site root, so they work from any page depth
      if (c.feed) {
        return '<a class="cgst-ctl" href="' + esc(BASE + c.href) + '" data-cgst-item data-cgst-feed>' + inner +
          '<span class="cgst-state" data-cgst-feed-state hidden></span></a>';
      }
      return '<a class="cgst-ctl" href="' + esc(BASE + c.href) + '" data-cgst-item>' + inner + '</a>';
    }).join("");

    var routeHTML = ROUTES.map(function (r) {
      return '<a class="cgst-route" href="' + esc(BASE + r.href) + '" data-cgst-item>' + esc(r.title) + ' &#8599;</a>';
    }).join("");

    // Site Intelligence: index readout, launchers, Mission Control, smart actions
    var cmdHTML = COMMAND_CENTER.map(function (c) {
      return '<button type="button" class="cgst-cmd" data-cgst="cmd" data-cmd="' + c.id + '" data-cgst-item>' +
        '<span><strong>' + esc(c.title) + '</strong><small>' + esc(c.sub) + '</small></span></button>';
    }).join("");
    var sectorHTML = SECTORS.map(function (s, i) {
      return '<button type="button" class="cgst-sector" data-cgst="sector" data-sector="' + s.id + '" data-cgst-item>' +
        '<span class="cgst-code" aria-hidden="true">' + ("0" + (i + 1)).slice(-2) + '</span>' +
        '<strong>' + esc(s.title) + '</strong><small>' + esc(s.sub) + '</small>' +
        '<span class="cgst-count" data-cgst-sector-count="' + s.id + '" aria-hidden="true">--</span></button>';
    }).join("");
    var smartHTML = SMART.map(function (s) {
      return '<button type="button" class="cgst-act" data-cgst="smart" data-smart="' + s.id + '" data-cgst-item>' + esc(s.title) + '</button>';
    }).join("");
    var modeHTML = [{ id: "auto", label: "Auto" }].concat(MODES).map(function (m) {
      return '<button type="button" class="cgst-mode" data-cgst="ans-mode" data-mode="' + m.id + '" aria-pressed="false"' +
        (m.name ? ' title="' + esc(m.name) + ' mode"' : ' title="Pick the mode from the question"') + '>' + esc(m.label) + '</button>';
    }).join("");

    var answerHTML =
      '<section class="cgst-answer" data-cgst-answer aria-labelledby="cgstAnsTitle" hidden>' +
        '<div class="cgst-ans-top">' +
          '<span class="cgst-ans-kind" data-cgst-ans-kind>Site intelligence</span>' +
          '<button type="button" class="cgst-x" data-cgst="ans-close" aria-label="Dismiss the answer">' + IC_X + '</button>' +
        '</div>' +
        '<div class="cgst-modes" role="group" aria-label="Writing mode">' + modeHTML + '</div>' +
        '<h3 class="cgst-ans-title" id="cgstAnsTitle" tabindex="-1" data-cgst-ans-title></h3>' +
        '<p class="cgst-ans-lede" data-cgst-ans-lede></p>' +
        '<div class="cgst-ans-body" data-cgst-ans-body></div>' +
        '<div class="cgst-ans-acts" data-cgst-ans-acts></div>' +
        '<p class="cgst-basis" data-cgst-ans-basis></p>' +
        '<span class="cgst-sr" role="status" aria-live="polite" data-cgst-ans-live></span>' +
      '</section>';

    var nexusHTML =
      '<section class="cgst-nexus" data-state="idle" aria-labelledby="cgstNexus">' +
        '<div class="cgst-nexus-top">' +
          '<div class="cgst-intel-id">' +
            '<p class="cgst-nexus-title" id="cgstNexus">Site Intelligence</p>' +
            '<span class="cgst-intel-sub">Every public page · searchable on this device</span>' +
          '</div>' +
          '<span class="cgst-pulse" aria-hidden="true"><i></i><i></i><i></i></span>' +
        '</div>' +
        '<div>' +
          '<p class="cgst-label" id="cgstIndex">Global index status</p>' +
          '<dl class="cgst-telemetry cgst-idx" aria-labelledby="cgstIndex" ' +
            'title="Generated from the site graph by tools/internal_links.py and read once from data/site-index.json">' +
            '<div class="cgst-cell"><dt>INDEX</dt><dd data-cgst-idx-state>STANDBY</dd></div>' +
            '<div class="cgst-cell"><dt>PAGES</dt><dd data-cgst-idx-pages>--</dd></div>' +
            '<div class="cgst-cell"><dt>NODES</dt><dd data-cgst-idx-nodes title="Pages plus the clusters that group them">--</dd></div>' +
            '<div class="cgst-cell"><dt>LINKS</dt><dd data-cgst-idx-links title="Related-page links between them">--</dd></div>' +
          '</dl>' +
        '</div>' +
        '<p class="cgst-where" data-cgst-where>Reading the site index…</p>' +
        '<div class="cgst-launch">' +
          '<button type="button" class="cgst-go" data-cgst="graph" data-cgst-item>' + IC_GRAPH + 'Intelligence Graph</button>' +
          '<button type="button" class="cgst-go cgst-mc-toggle" data-cgst="mc" aria-expanded="false" aria-controls="cgstMc" data-cgst-item>' +
            'Mission Control' + IC_CHEV + '</button>' +
        '</div>' +
        '<div class="cgst-mc" id="cgstMc" hidden>' +
          '<div role="group" aria-labelledby="cgstCmdL"><p class="cgst-label" id="cgstCmdL">Command center</p>' +
            '<div class="cgst-cmds">' + cmdHTML + '</div></div>' +
          '<div role="group" aria-labelledby="cgstSecL"><p class="cgst-label" id="cgstSecL">Sectors</p>' +
            '<div class="cgst-sectors">' + sectorHTML + '</div></div>' +
        '</div>' +
        '<div role="group" aria-labelledby="cgstSmart"><p class="cgst-label" id="cgstSmart">Smart actions · this page</p>' +
          '<div class="cgst-smart">' + smartHTML + '</div></div>' +
      '</section>';

    var graphHTML =
      '<div class="cgst-graph" data-cgst-graph role="dialog" aria-modal="true" aria-labelledby="cgstGraphTitle" hidden>' +
        '<div class="cgst-gframe">' +
          '<div class="cgst-ghead">' +
            '<div><span class="cgst-org" aria-hidden="true">CLEARGLASS KNOWLEDGE GRAPH</span>' +
              '<h2 class="cgst-gtitle" id="cgstGraphTitle" tabindex="-1">Intelligence Graph</h2>' +
              '<p class="cgst-gsub" data-cgst-gsub>Reading the site index…</p></div>' +
            '<div class="cgst-gtools">' +
              '<button type="button" class="cgst-gtool" data-cgst="g-in" aria-label="Zoom in">+</button>' +
              '<button type="button" class="cgst-gtool" data-cgst="g-out" aria-label="Zoom out">&minus;</button>' +
              '<button type="button" class="cgst-gtool" data-cgst="g-fit" aria-label="Show the whole graph">FIT</button>' +
              '<button type="button" class="cgst-gtool" data-cgst="g-close" aria-label="Close the Intelligence Graph">' + IC_X + '</button>' +
            '</div>' +
          '</div>' +
          '<div class="cgst-gbody">' +
            '<div class="cgst-gview" data-cgst-gview tabindex="0" role="group" ' +
              'aria-label="Graph canvas. Arrow keys pan, plus and minus zoom, 0 resets. The list beside it holds the same pages.">' +
              '<svg class="cgst-gsvg" viewBox="0 0 1000 1000" aria-hidden="false"></svg>' +
            '</div>' +
            '<div class="cgst-gside">' +
              '<form class="cgst-gfind" role="search"><label class="cgst-sr" for="cgstGFind">Filter the graph</label>' +
                '<input id="cgstGFind" type="search" autocomplete="off" spellcheck="false" maxlength="120" placeholder="Filter nodes: osint, pricing…"></form>' +
              '<p class="cgst-gpath" data-cgst-gpath>Sentinel Core</p>' +
              '<div data-cgst-gtree></div>' +
            '</div>' +
          '</div>' +
          '<p class="cgst-gfoot">Memory layer: clusters around Sentinel Core, pages around their cluster · ' +
            'drag to pan · wheel, pinch or +/− to zoom · hover a page to trace its links · Esc closes</p>' +
        '</div>' +
      '</div>';

    // The desk ships with a working static state (a link to the hub); the
    // feed only upgrades it.
    var hub = hubUrl();
    var intelHTML =
      '<section class="cgst-intel" data-state="loading" data-run="0" aria-labelledby="cgstIntel" aria-roledescription="carousel">' +
        '<div class="cgst-intel-top">' +
          '<div class="cgst-intel-id">' +
            '<p class="cgst-intel-title" id="cgstIntel">Intel Desk</p>' +
            '<span class="cgst-intel-sub" data-cgst-intel-sub>ClearGlass Insights · field briefs</span>' +
          '</div>' +
          '<span class="cgst-flag" data-cgst-intel-flag hidden></span>' +
        '</div>' +
        '<a class="cgst-brief" href="' + esc(hub) + '" data-cgst-item data-cgst-brief>' +
          '<span class="cgst-brief-meta"><span class="cgst-rank" data-cgst-b-rank></span>' +
            '<span class="cgst-cat" data-cgst-b-cat>Syncing brief index</span></span>' +
          '<span class="cgst-brief-title" data-cgst-b-title>ClearGlass Insights</span>' +
          '<span class="cgst-brief-quote" data-cgst-b-quote>Research-led briefs on governed AI, cyber architecture, OSINT and Canadian resilience.</span>' +
          '<span class="cgst-brief-foot"><span data-cgst-b-when>Intel briefs</span><span class="cgst-open" aria-hidden="true">Open brief &#8599;</span></span>' +
          '<span class="cgst-flag" data-cgst-b-new aria-hidden="true" hidden>NEW</span>' +
          '<span class="cgst-timer" aria-hidden="true"></span>' +
        '</a>' +
        '<div class="cgst-intel-nav" data-cgst-intel-nav hidden>' +
          '<button type="button" class="cgst-step" data-cgst="intel-prev" data-cgst-item aria-label="Previous brief">' + IC_PREV + '</button>' +
          '<div class="cgst-dots" data-cgst-dots></div>' +
          '<span class="cgst-pos" data-cgst-pos aria-hidden="true"></span>' +
          '<button type="button" class="cgst-step" data-cgst="intel-hold" data-cgst-item aria-pressed="false" aria-label="Pause rotation">' + IC_HOLD + '</button>' +
          '<button type="button" class="cgst-step" data-cgst="intel-next" data-cgst-item aria-label="Next brief">' + IC_NEXT + '</button>' +
        '</div>' +
        '<span class="cgst-sr" role="status" aria-live="polite" data-cgst-intel-live></span>' +
        '<div class="cgst-topics" data-cgst-topics hidden></div>' +
        '<div class="cgst-intel-links">' +
          '<a class="cgst-go" href="' + esc(hub) + '" data-cgst-item>Open Insights Desk &#8599;</a>' +
          '<a class="cgst-aux" href="' + esc(hubUrl("saved")) + '" data-cgst-item data-cgst-saved hidden>Saved</a>' +
          '<a class="cgst-aux" href="' + esc(BASE + INTEL.rss) + '" data-cgst-item>RSS feed</a>' +
          '<button type="button" class="cgst-aux" data-cgst="intel-seen" data-cgst-item hidden>Mark all seen</button>' +
        '</div>' +
        '<p class="cgst-sync" data-cgst-sync>Index · syncing</p>' +
      '</section>';

    root.innerHTML =
      '<div class="cgst-sheet" id="cgStationPanel" role="group" aria-labelledby="cgstTitle">' +
        '<div class="cgst-head" title="Drag, or focus and use the arrow keys, to move the console">' +
          '<span class="cgst-radar" aria-hidden="true"><i></i><b></b></span>' +
          '<div class="cgst-id">' +
            '<span class="cgst-org" aria-hidden="true">CLEARGLASS INC.</span>' +
            '<h2 class="cgst-title" id="cgstTitle">SENTINEL CORE</h2>' +
            '<p class="cgst-status"><span class="cgst-live" aria-hidden="true"></span>' +
              '<span class="cgst-sr" data-cgst-status-sr></span><span aria-hidden="true" data-cgst-type></span></p>' +
          '</div>' + TRACE +
        '</div>' +

        '<div>' +
          '<p class="cgst-label" id="cgstReadiness">Readiness</p>' +
          '<dl class="cgst-telemetry" aria-labelledby="cgstReadiness">' +
            '<div class="cgst-cell"><dt>LINK</dt><dd data-cgst-link>ONLINE</dd></div>' +
            '<div class="cgst-cell"><dt>MODE</dt><dd>PUBLIC</dd></div>' +
            '<div class="cgst-cell"><dt>ENGINE</dt><dd title="Deterministic, rule-guided answers — not a live language model">RULE-GUIDED</dd></div>' +
            '<div class="cgst-cell"><dt>CHAT DATA</dt><dd title="Sentinel conversations stay in this browser tab. Nothing is sent to ClearGlass.">ON DEVICE</dd></div>' +
            '<div class="cgst-cell"><dt>SESSION</dt><dd>' + esc(sid.replace(/^CG-SNT-/, "SNT-")) + '</dd></div>' +
            '<div class="cgst-cell"><dt>UTC</dt><dd data-cgst-clock>--:--:--Z</dd></div>' +
          '</dl>' +
        '</div>' +

        '<form class="cgst-ask" data-cgst-ask>' +
          '<span class="cgst-ask-mark" aria-hidden="true">&gt;_</span>' +
          '<label class="cgst-sr" for="cgstAskInput">Ask Sentinel</label>' +
          '<input id="cgstAskInput" type="text" maxlength="800" autocomplete="off" spellcheck="false" enterkeyhint="send" ' +
            'role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="cgstSuggest" aria-describedby="cgstAskHint" ' +
            'placeholder="Ask Sentinel anything…">' +
          '<button type="submit" class="cgst-send" aria-label="Send to Sentinel">' + IC_SEND + '</button>' +
        '</form>' +
        '<ul class="cgst-suggest" id="cgstSuggest" role="listbox" aria-label="Commands, pages and brief matches" hidden></ul>' +
        '<p class="cgst-hint" id="cgstAskHint"><b>/</b> commands · 3+ letters search the site' +
          '<span class="cgst-keys"> · Alt+Shift+I intel</span></p>' +

        answerHTML +

        intelHTML +

        nexusHTML +

        '<div role="group" aria-labelledby="cgstMissions">' +
          '<p class="cgst-label" id="cgstMissions">Missions</p>' +
          '<div class="cgst-missions">' + missionHTML + '</div>' +
        '</div>' +

        '<div role="group" aria-labelledby="cgstControls">' +
          '<p class="cgst-label" id="cgstControls">Controls</p>' +
          '<div class="cgst-controls">' + controlHTML + '</div>' +
        '</div>' +

        '<nav aria-labelledby="cgstRoutes">' +
          '<p class="cgst-label" id="cgstRoutes">Routes</p>' +
          '<div class="cgst-routes">' + routeHTML + '</div>' +
        '</nav>' +

        '<div class="cgst-jumps">' +
          '<button type="button" class="cgst-jump" data-cgst="top" data-cgst-item>&#8593; Top</button>' +
          '<button type="button" class="cgst-jump" data-cgst="bottom" data-cgst-item>&#8595; Bottom</button>' +
        '</div>' +

        '<p class="cgst-foot">Public console · rule-guided · no system access' +
          '<span class="cgst-keys"> · Alt+Shift+S toggles · Alt+Shift+I intel · Alt+Shift+G graph</span></p>' +
      '</div>' +

      graphHTML +

      '<div class="cgst-rail">' +
        '<button type="button" class="cgst-orb" data-cgst="graph" aria-label="Open the Intelligence Graph" title="Intelligence Graph">' + IC_GRAPH + '</button>' +
        '<button type="button" class="cgst-dock" id="cgStationDock" aria-expanded="false" aria-controls="cgStationPanel">' +
          '<span class="cgst-radar" aria-hidden="true"><i></i><b></b></span>' +
          '<span class="cgst-flag" data-cgst-dock-flag aria-hidden="true" hidden></span>' +
          '<span class="cgst-dock-tx"><strong>SENTINEL CORE</strong>' +
            '<small><span class="cgst-live" aria-hidden="true"></span><span data-cgst-dock-status>ONLINE · READY</span></small></span>' +
          '<span class="cgst-chev" aria-hidden="true">' + IC_CHEV + '</span>' +
        '</button>' +
      '</div>';

    document.body.appendChild(root);
    document.body.classList.add("cg-station-mounted");

    panel = root.querySelector(".cgst-sheet");
    dock = root.querySelector(".cgst-dock");
    askForm = root.querySelector("[data-cgst-ask]");
    askInput = root.querySelector("#cgstAskInput");
    statusType = root.querySelector("[data-cgst-type]");
    statusSr = root.querySelector("[data-cgst-status-sr]");
    dockStatus = root.querySelector("[data-cgst-dock-status]");
    stealthCtl = root.querySelector('.cgst-ctl[data-cgst="stealth"]');
    tacticalCtl = root.querySelector('.cgst-ctl[data-cgst="tactical"]');
    linkCell = root.querySelector("[data-cgst-link]");
    clockCell = root.querySelector("[data-cgst-clock]");
    jumpTop = root.querySelector('[data-cgst="top"]');
    jumpBottom = root.querySelector('[data-cgst="bottom"]');

    nexusEl = q(".cgst-nexus");
    ansEl = q("[data-cgst-answer]");
    ansKind = q("[data-cgst-ans-kind]");
    ansTitle = q("[data-cgst-ans-title]");
    ansLede = q("[data-cgst-ans-lede]");
    ansBody = q("[data-cgst-ans-body]");
    ansActs = q("[data-cgst-ans-acts]");
    ansBasis = q("[data-cgst-ans-basis]");
    ansLive = q("[data-cgst-ans-live]");
    mcToggle = q('[data-cgst="mc"]');
    mcEl = q("#cgstMc");
    ans.pick = readMode();

    // A full-viewport page gets the compact dock and keeps its own layout.
    if (FIT === "fixed") {
      root.setAttribute("data-fit", "compact");
      document.body.classList.add("cgst-fixed");
    }
    // Missions answer in the Sentinel conversation, which lives on the home page.
    if (!hasSentinel()) {
      Array.prototype.forEach.call(root.querySelectorAll(".cgst-mission"), function (m) {
        m.title = "Opens the Sentinel conversation on the home page";
      });
    }

    // wiring
    dock.addEventListener("click", function () { setOpen(root.getAttribute("data-open") !== "true", true, true); });
    magnetize(dock);
    wireIntel();
    wireBar();
    wireGraph();
    try { if (localStorage.getItem(MC_KEY) === "1") setMc(true, false); } catch (e) {}

    askForm.addEventListener("submit", function (event) {
      event.preventDefault();
      // a highlighted option (or a slash command) runs; anything else is a
      // question for Sentinel, as it always was
      var pick = bar.open && bar.active >= 0 ? bar.opts[bar.active] : null;
      if (!pick && askInput.value.trim().charAt(0) === "/") pick = optionsFor(askInput.value)[0] || null;
      if (pick) { runOption(pick); return; }
      var prompt = askInput.value.trim();
      // a phrasing with a site meaning is answered here, on any page; a page
      // without the Sentinel conversation answers everything here
      if (!prompt && !hasSentinel()) { runCommand("search"); return; }
      var intent = intentOf(prompt);
      if (intent || !hasSentinel()) {
        askInput.value = "";
        closeSuggest();
        if (intent) runIntent(intent, prompt); else runIntent({ kind: "search", arg: prompt }, prompt);
        return;
      }
      // Moving focus to the send button still drops the phone keyboard, and the
      // chat restores focus here when it closes (blur() left it on <body>).
      var send = askForm.querySelector(".cgst-send");
      if (send) { try { send.focus({ preventScroll: true }); } catch (e) { send.focus(); } }
      // An older cached sentinel.js cannot take the question, so keep it.
      if (window.__cgSentinel) askInput.value = "";
      openSentinel(prompt);
    });

    root.addEventListener("click", function (event) {
      var target = event.target.closest ? event.target.closest("[data-cgst]") : null;
      if (!target || target === dock) return;
      var act = target.getAttribute("data-cgst");
      if (act === "mission") { openSentinel(target.getAttribute("data-prompt")); return; }
      if (act === "stealth") { toggleStealth(); return; }
      if (act === "tactical") { toggleTactical(); return; }
      if (act === "top") { scrollTo(0); return; }
      if (act === "bottom") { scrollTo(docHeight()); return; }
      if (act === "intel-prev") { showBrief(intel.at - 1, -1, true); return; }
      if (act === "intel-next") { showBrief(intel.at + 1, 1, true); return; }
      if (act === "intel-hold") { toggleHold(); return; }
      if (act === "intel-go") {
        var to = parseInt(target.getAttribute("data-index"), 10) || 0;
        if (to !== intel.at) showBrief(to, to > intel.at ? 1 : -1, true);
        return;
      }
      if (act === "intel-seen") {
        var marked = unread();
        markSeen(marked.map(function (p) { return p.slug; }));
        paintCounts();
        if (intelLive) intelLive.textContent = marked.length + (marked.length === 1 ? " brief" : " briefs") + " marked as seen";
        return;
      }
      // Site Intelligence
      if (act === "graph") { openGraph({ cluster: site.here ? site.here.cluster : "" }); return; }
      if (act === "mc") { setMc(mcEl.hidden, false); return; }
      if (act === "cmd") { runCommand(target.getAttribute("data-cmd")); return; }
      if (act === "sector") {
        var sid = target.getAttribute("data-sector");
        runIntent({ kind: "sector", arg: sid === "missions" ? "missions" : sectorById(sid).title }, "", "executive");
        return;
      }
      if (act === "smart") { smart(target.getAttribute("data-smart")); return; }
      if (act === "ans-close") { hideAnswer(); try { askInput.focus({ preventScroll: true }); } catch (e) {} return; }
      if (act === "ans-more") { ans.all = true; paintAnswer(false); return; }
      if (act === "ans-mode") {
        ans.pick = target.getAttribute("data-mode");
        try { localStorage.setItem(MODE_KEY, ans.pick); } catch (e) {}
        paintAnswer(true);
        var again = q('.cgst-mode[data-mode="' + ans.pick + '"]');
        if (again) { try { again.focus({ preventScroll: true }); } catch (e) {} }
        return;
      }
      if (act === "ans-act" || act === "ans-run") {
        var list = act === "ans-act" ? ans.acts : ans.runs, fn = list[parseInt(target.getAttribute("data-index"), 10)];
        if (typeof fn === "function") fn();
        return;
      }
      if (act === "g-in") { zoomAt(1 / 1.3, null, true); return; }
      if (act === "g-out") { zoomAt(1.3, null, true); return; }
      if (act === "g-fit") { setHits([], ""); if (gFind) gFind.value = ""; focusCluster(""); return; }
      if (act === "g-close") { closeGraph(); return; }
    });

    panel.addEventListener("keydown", panelKeys);

    document.addEventListener("keydown", function (event) {
      var t = event.target;
      var editable = t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName || ""));
      if (event.altKey && event.shiftKey && !event.ctrlKey && !event.metaKey &&
          (event.key === "S" || event.key === "s" || (!editable && event.code === "KeyS"))) {
        event.preventDefault();
        setOpen(root.getAttribute("data-open") !== "true", true, true);
        return;
      }
      if (event.altKey && event.shiftKey && (event.key === "I" || event.key === "i" || event.code === "KeyI")) {
        event.preventDefault();
        focusIntel();
        return;
      }
      if (event.altKey && event.shiftKey && !event.ctrlKey && !event.metaKey &&
          (event.key === "G" || event.key === "g" || (!editable && event.code === "KeyG"))) {
        event.preventDefault();
        if (graph.open) closeGraph(); else openGraph({ cluster: site.here ? site.here.cluster : "" });
        return;
      }
      if (event.key !== "Escape") return;
      if (root.getAttribute("data-open") !== "true") return;
      // Scope to the event's own target. Checking activeElement instead would
      // swallow the Escape that closes the Sentinel shell, because sentinel.js
      // restores focus into this dock before the event finishes bubbling.
      if (!root.contains(event.target)) return;
      if (document.body.classList.contains("sentinel-open")) return;
      event.preventDefault();
      setOpen(false, true, true);
      if (lastFocus && lastFocus.focus && lastFocus !== document.body) { try { lastFocus.focus(); } catch (e) {} }
    });

    // On phones an open console covers most of the page, so a tap outside it
    // folds it away, as any popover would.
    document.addEventListener("pointerdown", function (event) {
      if (root.getAttribute("data-open") !== "true" || !narrow()) return;
      if (root.contains(event.target) || document.body.classList.contains("sentinel-open")) return;
      setOpen(false, false, true);
    }, true);

    // Keyboard focus moving into the page folds the console away, so it never
    // hides the element that has focus (WCAG 2.4.11). Not persisted: it is not
    // the visitor's choice to close it.
    document.addEventListener("focusin", function (event) {
      if (root.getAttribute("data-open") !== "true") return;
      if (root.contains(event.target) || document.body.classList.contains("sentinel-open")) return;
      var shell = document.getElementById("sentinelShell");
      if (shell && shell.contains(event.target)) return;
      setOpen(false, false, false);
    });

    window.addEventListener("scroll", queueScroll, { passive: true });
    window.addEventListener("resize", queueScroll, { passive: true });
    window.addEventListener("resize", syncStack, { passive: true });
    window.addEventListener("resize", syncTopClear, { passive: true });
    window.addEventListener("clearglass:stealth", paintToggles);
    window.addEventListener("online", paintLink);
    window.addEventListener("offline", paintLink);
    document.addEventListener("visibilitychange", syncClock);
    document.addEventListener("visibilitychange", syncRun);
    // counts follow the hub: a brief saved in another tab, or opened and then
    // navigated back from (bfcache), repaints the badges
    window.addEventListener("storage", function (event) {
      if (event.key === SEEN_KEY || event.key === SAVED_KEY) paintCounts();
    });
    window.addEventListener("pageshow", function () { paintCounts(); if (intel.state === "ready") showBrief(intel.at, 0, false); });

    // Stealth (data-skin) and Tactical View (data-cgm-motion) both land on
    // <html>; one attribute-filtered observer keeps both chips honest.
    if (window.MutationObserver) {
      new MutationObserver(paintToggles).observe(document.documentElement, {
        attributes: true, attributeFilter: ["data-skin", "data-cgm-motion"]
      });
      // The Sentinel shell toggles body.sentinel-open; pause the clock and the
      // Intel Desk rotation under it.
      new MutationObserver(function () { syncClock(); syncRun(); })
        .observe(document.body, { attributes: true, attributeFilter: ["class"] });
    }

    // stealth-glass.js mounts on its own schedule; catch it the first time it
    // lands, then stop watching — this observer must never outlive its purpose.
    // Once the stack exists, a childList-only observer on it (cheap: no
    // subtree) keeps the absorb decision right if anything else docks there.
    if (window.MutationObserver) {
      var watchStack = function () {
        var stack = document.getElementById("cg-security-stack");
        if (!stack || stack.__cgstWatched) return !!stack;
        stack.__cgstWatched = true;
        new MutationObserver(function () { syncStack(); paintToggles(); }).observe(stack, { childList: true });
        return true;
      };
      if (!watchStack() || !stealthButton()) {
        var observer = new MutationObserver(function () {
          watchStack();
          if (!stealthButton()) return;
          observer.disconnect();
          paintToggles();
          syncStack();
        });
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(function () { observer.disconnect(); }, 8000);
      }
    }

    paintLink();
    paintToggles();
    syncScroll();
    syncStack();
    syncTopClear();
    setOpen(readOpen(), false, false);
    // geometry settles a frame later, once the other docks have mounted
    requestAnimationFrame(syncStack);
    setTimeout(function () { syncStack(); paintToggles(); }, 800);
    // The collapsed dock badges unread briefs, so the index is read once the
    // page has settled rather than waiting for the console to open. The site
    // index follows it, so the readout and sector counts are ready on open.
    var settle = function () { loadFeed(); loadSite(); };
    if (window.requestIdleCallback) window.requestIdleCallback(settle, { timeout: 4000 });
    else setTimeout(settle, 1500);
    pickupHandoff();
  }

  // public, read-only-ish control surface for other ClearGlass layers
  window.__cgStation = {
    open: function () { if (root) setOpen(true, true, false); },
    close: function () { if (root) setOpen(false, false, false); },
    toggle: function () { if (root) setOpen(root.getAttribute("data-open") !== "true", true); },
    graph: function () { if (root) openGraph({}); },
    ask: function (text) {
      if (!root) return;
      if (root.getAttribute("data-open") !== "true") setOpen(true, false, false);
      runQuery(text);
    }
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build, { once: true });
  else build();
})();
