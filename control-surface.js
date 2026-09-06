/* ClearGlass · Control Surface 
   ────────────────────────────────────────────────────────────────────────────
   One integrated operating layer for the portfolio: a compact top cluster
   (status + command pill + menu), a command-palette-first interaction model
   (Cmd/Ctrl+K and /), and a right-side systems drawer.

   Engineering:
     • semantic + ARIA dialog, focus trap + restore, stable tab order
     • live GitHub Actions telemetry → NOMINAL / SYNCING / DEGRADED / FAILURE
     • context engine: surfaces page-relevant shortcuts only when relevant
     • spring-ish motion, fully gated by prefers-reduced-motion
     • programmable-glass aesthetic in the company blue-violet
   Drop in with <script defer src="control-surface.js"></script>. No deps. */
(function () {
  "use strict";
  if (window.__cgCS) return;
  window.__cgCS = true;
  window.__cgNavLoaded = true;            // supersede the legacy hover menu (nav.js)

  // Published hourly by .github/workflows/control-surface-feeds.yml from the
  // authenticated Actions API. Same-origin, so no rate limit and no third-party
  // request — the keyless api.github.com call below is only a fallback.
  var FEED = "/data/control-surface/";
  var REPO = "ClearGlassInc/ClearGlassIncorporated-Desmond";
  var EMAIL = "desmondotieno@icloud.com";

  // ── destinations (grouped) ──────────────────────────────────────────────
  var GROUPS = [
    ["Command", [
      ["Control Surface · v3.1", "control-surface.html", "◈"],
      ["Systems Control Surface", "systems.html", "▣"],
      ["Air Systems Control", "air-systems-control.html", "◍"],
      ["AVALON · ARTEMIS ⊕ PERCIVAL", "artemis-percival.html", "⬣"],
      ["PERCIVAL OS", "percival-os.html", "◐"],
      ["SENTINEL · Live", "sentinel.html", "◉"],
      ["AEGIS · Legal Shield", "aegis.html", "⚖"],
      ["Agent Mesh", "agentmesh.html", "⌗"],
      ["BLUEDESK · CISO Console", "bluedesk.html", "🛡"],
      ["AI Operator", "ai-operator.html", "🜂"],
      ["Command Console", "command-console.html", "▤"],
      ["Event Control Surface", "saas-platform.html", "◆"]
    ]],
    ["Platforms", [
      ["Artemis IV Core", "artemis-iv.html", "🧭"],
      ["Artemis VI", "artemis.html", "🛰"],
      ["Guardian", "guardian.html", "🌐"],
      ["ClearGlass NEXUS", "clearglass-nexus.html", "🛡"],
      ["Government", "government.html", "🏛"],
      ["ClearPulse", "clearpulse.html", "📡"],
      ["Satellite Map", "https://www.arcgis.com/apps/mapviewer/index.html?center=-79.799,43.3255&level=13", "🛰"]
    ]],
    ["Intelligence", [
      ["Intelligence", "intelligence.html", "🧠"],
      ["Command Surface", "intelligence-command-surface.html", "🗺"],
      ["Interface", "intelligence-interface.html", "🖥"],
      ["Ontario OSINT Deck", "Ontario-osint.html", "🛰"],
      ["Revenue Engine", "revenue-engine.html", "💹"]
    ]],
    ["Legal & Finance", [
      ["Corporate Legal", "corporate-legal-advisor.html", "§"],
      ["Banking Law", "banking-law-advisor.html", "🏦"],
      ["ClearTax", "tax.html", "🧾"]
    ]],
    ["Company", [
      ["Home", "index.html", "⌂"],
      ["Pricing & Engagements", "pricing.html", "◎"],
      ["Web Design & Dev", "web-design.html", "◳"],
      ["Button Lab", "button-lab.html", "◫"]
    ]]
  ];

  // ── actions (verbs, not just destinations) ──────────────────────────────
  var ACTIONS = [
    { label: "Open Systems Control Surface", sub: "Operations console", icon: "▣", href: "systems.html" },
    { label: "Open Air Systems Control", sub: "Atmospheric glass console", icon: "◍", href: "air-systems-control.html" },
    { label: "Pricing & engagements", sub: "Book a fixed-fee engagement", icon: "◎", href: "pricing.html" },
    { label: "Website design & development", sub: "Engagement", icon: "◳", href: "web-design.html" },
    { label: "Open latest project", sub: "Artemis VI", icon: "🛰", href: "artemis.html" },
    { label: "Deployment status", sub: "GitHub Actions", icon: "◇", act: "status" },
    { label: "Security research", sub: "SENTINEL", icon: "◉", href: "sentinel.html" },
    { label: "BLUEDESK · CISO risk console", sub: "Blue team", icon: "🛡", href: "bluedesk.html" },
    { label: "Contact", sub: EMAIL, icon: "✉", act: "contact" },
    { label: "Copy contact email", sub: EMAIL, icon: "⧉", act: "copyEmail" },
    { label: "View source on GitHub", sub: REPO, icon: "⌥", href: "https://github.com/" + REPO, ext: true }
  ];

  // ── context engine: page-type → relevant shortcuts ──────────────────────
  var CONTEXT = {
    research: { match: ["intelligence", "sentinel", "agentmesh", "stegoforge", "attack-prompt"], items: [
      ["Abstract", "#abstract", "¶"], ["Methods", "#methods", "⚙"], ["Results", "#results", "📊"], ["References", "#references", "🔖"]
    ]},
    platform: { match: ["artemis", "guardian", "clearglass-nexus", "clearpulse", "percival", "ai-operator", "command-console"], items: [
      ["Architecture", "#architecture", "🏗"], ["Live metrics", "#metrics", "📈"], ["Deployments", "#deploy", "🚀"], ["Docs", "#docs", "📚"]
    ]}
  };

  var here = (location.pathname.split("/").pop() || "index.html").toLowerCase();
  var flat = [];
  GROUPS.forEach(function (g) { g[1].forEach(function (it) { flat.push({ label: it[0], href: it[1], icon: it[2], group: g[0] }); }); });

  // ── recent destinations (localStorage) ──────────────────────────────────
  function recents() { try { return JSON.parse(localStorage.getItem("cg.recent") || "[]"); } catch (e) { return []; } }
  function pushRecent(href) {
    try {
      var r = recents().filter(function (x) { return x !== href; });
      r.unshift(href); localStorage.setItem("cg.recent", JSON.stringify(r.slice(0, 6)));
    } catch (e) {}
  }
  if (here && here !== "index.html") pushRecent(here);

  function ctxForPage() {
    for (var k in CONTEXT) {
      if (CONTEXT[k].match.some(function (m) { return here.indexOf(m) === 0 || here.indexOf(m) > -1; })) return CONTEXT[k];
    }
    return null;
  }

  // ── styles ───────────────────────────────────────────────────────────────
  var BLUE = "#60a5fa", VIOLET = "#a78bfa";
  var css = "" +
  "#cgcs,#cgcs *{box-sizing:border-box}" +
  "#cgcs{--b:var(--cg-blue," + BLUE + ");--v:var(--cg-violet," + VIOLET + ");--g1:var(--cg-surface,rgba(18,22,42,.72));" +
    "--ln:var(--cg-hairline,rgba(124,150,255,.28));--tx:var(--cg-on-surface,#e7ecff);" +
    "--cr:var(--cg-crystal,linear-gradient(135deg,#38bdf8,#a78bfa 35%,#f472b6 60%,#34d399));" +
    "font-family:var(--cg-sans,'Urbanist',system-ui,-apple-system,sans-serif)}" +
  // top cluster
  ".cgcs-bar{position:fixed;top:10px;right:12px;z-index:2147483600;display:flex;align-items:center;gap:8px;pointer-events:none}" +
  ".cgcs-bar>*{pointer-events:auto}" +
  ".cgcs-chip,.cgcs-cmd,.cgcs-menu{display:inline-flex;align-items:center;gap:8px;height:36px;padding:0 14px;border-radius:var(--cg-r-pill,999px);" +
    "border:1px solid var(--ln);background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,0) 50%),var(--g1);" +
    "backdrop-filter:blur(12px) saturate(1.1);-webkit-backdrop-filter:blur(12px) saturate(1.1);color:var(--tx);" +
    "font-size:12px;font-weight:600;cursor:pointer;box-shadow:0 1px 0 rgba(255,255,255,.08) inset,0 10px 24px -14px rgba(8,12,28,.9);" +
    "transition:transform var(--cg-dur-1,.18s) var(--cg-ease,cubic-bezier(.4,0,.2,1)),box-shadow .2s,border-color .2s,height .22s,opacity .22s}" +
  ".cgcs-cmd:hover,.cgcs-menu:hover,.cgcs-chip:hover{border-color:rgba(124,150,255,.6);transform:translateY(-1px)}" +
  ".cgcs-cmd kbd{font-family:'IBM Plex Mono',monospace;font-size:10px;background:rgba(124,150,255,.16);border:1px solid var(--ln);" +
    "border-radius:5px;padding:1px 6px;color:#cdd6f5}" +
  ".cgcs-menu{padding:0;width:36px;justify-content:center;font-size:15px}" +
  ".cgcs-chip{cursor:default}" +
  ".cgcs-dot{width:8px;height:8px;border-radius:50%;background:#7c889c;flex:0 0 auto;box-shadow:0 0 0 0 rgba(0,0,0,0)}" +
  ".cgcs-dot.ok{background:var(--cg-status-ok,#34d399);box-shadow:0 0 9px var(--cg-status-ok,#34d399)}" +
  ".cgcs-dot.sync{background:var(--cg-status-sync,#38bdf8);box-shadow:0 0 9px var(--cg-status-sync,#38bdf8);animation:cgcsPulse 1.1s infinite}" +
  ".cgcs-dot.warn{background:var(--cg-status-warn,#fbbf24);box-shadow:0 0 9px var(--cg-status-warn,#fbbf24)}" +
  ".cgcs-dot.fail{background:var(--cg-status-fail,#f472b6);box-shadow:0 0 9px var(--cg-status-fail,#f472b6);animation:cgcsPulse 1.1s infinite}" +
  "@keyframes cgcsPulse{0%,100%{opacity:1}50%{opacity:.35}}" +
  ".cgcs-chip .cgcs-st{white-space:nowrap;font-size:11px;letter-spacing:.02em}" +
  "#cgcs.scrolled .cgcs-chip .cgcs-st{display:none}#cgcs.scrolled .cgcs-chip{padding:0 9px}" +
  "#cgcs.scrolled .cgcs-cmd .cgcs-cmdlbl{display:none}#cgcs.scrolled .cgcs-cmd{padding:0 10px}" +
  // overlay shared
  ".cgcs-ov{position:fixed;inset:0;z-index:2147483640;display:none}" +
  ".cgcs-ov.open{display:block}" +
  ".cgcs-scrim{position:absolute;inset:0;background:radial-gradient(120% 120% at 50% 0,rgba(8,10,24,.55),rgba(6,8,18,.78));" +
    "backdrop-filter:blur(3px);opacity:0;transition:opacity .22s ease}" +
  ".cgcs-ov.open .cgcs-scrim{opacity:1}" +
  // palette
  ".cgcs-pal{position:absolute;top:14vh;left:50%;width:min(620px,92vw);transform:translate(-50%,-12px) scale(.98);opacity:0;" +
    "background:linear-gradient(180deg,rgba(20,24,44,.96),rgba(12,15,30,.97));border:1px solid var(--ln);border-radius:16px;" +
    "box-shadow:0 40px 120px -30px rgba(0,0,0,.8),0 0 0 1px rgba(124,150,255,.08);overflow:hidden;color:var(--tx);" +
    "transition:transform .26s cubic-bezier(.16,1,.3,1),opacity .2s ease}" +
  ".cgcs-ov.open .cgcs-pal{transform:translate(-50%,0) scale(1);opacity:1}" +
  ".cgcs-search{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid rgba(124,150,255,.16)}" +
  ".cgcs-search .ic{color:var(--b);font-size:15px}" +
  ".cgcs-search input{flex:1;background:none;border:0;outline:0;color:#fff;font-size:15px;font-family:inherit}" +
  ".cgcs-search input::placeholder{color:#8a93b8}" +
  ".cgcs-esc{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#9aa6c8;border:1px solid var(--ln);border-radius:5px;padding:2px 7px}" +
  ".cgcs-list{max-height:min(56vh,460px);overflow-y:auto;padding:8px;scrollbar-width:thin}" +
  ".cgcs-gl{font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:#7c85ad;padding:10px 10px 4px}" +
  ".cgcs-opt{display:flex;align-items:center;gap:12px;padding:9px 11px;border-radius:10px;cursor:pointer;border:1px solid transparent}" +
  ".cgcs-opt .ic{width:26px;height:26px;border-radius:7px;display:grid;place-items:center;font-size:14px;flex:0 0 auto;" +
    "background:rgba(124,150,255,.1);border:1px solid rgba(124,150,255,.2)}" +
  ".cgcs-opt .tl{font-size:13.5px;color:#e9eeff}.cgcs-opt .sb{font-size:11px;color:#8a93b8}" +
  ".cgcs-opt .meta{margin-left:auto;font-size:10px;color:#7c85ad;font-family:'IBM Plex Mono',monospace}" +
  ".cgcs-opt[aria-selected=true]{background:linear-gradient(100deg,rgba(96,165,250,.2),rgba(167,139,250,.07));border-color:rgba(124,150,255,.5)}" +
  ".cgcs-empty{padding:26px;text-align:center;color:#8a93b8;font-size:13px}" +
  // drawer
  ".cgcs-dr{position:absolute;top:0;right:0;height:100%;width:min(340px,88vw);transform:translateX(102%);" +
    "background:linear-gradient(180deg,rgba(16,19,38,.98),rgba(9,11,24,.99));border-left:1px solid var(--ln);" +
    "box-shadow:-30px 0 80px -30px rgba(0,0,0,.8);overflow-y:auto;padding:16px 14px 90px;" +
    "transition:transform .3s cubic-bezier(.16,1,.3,1)}" +
  ".cgcs-ov.open .cgcs-dr{transform:translateX(0)}" +
  ".cgcs-dh{display:flex;align-items:center;gap:10px;padding:2px 4px 12px;border-bottom:1px solid rgba(124,150,255,.16);margin-bottom:6px}" +
  ".cgcs-mk{width:28px;height:28px;border-radius:8px;box-shadow:0 0 14px rgba(124,150,255,.55);object-fit:cover}" +
  ".cgcs-dh b{background:var(--cr);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}" +
  ".cgcs-dx{margin-left:auto;background:none;border:0;color:#aab1d8;font-size:18px;cursor:pointer}" +
  ".cgcs-dr a{display:flex;align-items:center;gap:11px;padding:9px 10px;border-radius:9px;color:#dbe3f7;text-decoration:none;font-size:13px;border:1px solid transparent}" +
  ".cgcs-dr a:hover{background:rgba(124,150,255,.12);border-color:rgba(124,150,255,.26);color:#fff}" +
  ".cgcs-dr a.cur{background:linear-gradient(100deg,rgba(96,165,250,.18),rgba(167,139,250,.05));border-color:rgba(124,150,255,.45);color:#fff}" +
  ".cgcs-dr a .ic{width:24px;height:24px;border-radius:6px;display:grid;place-items:center;font-size:13px;background:rgba(124,150,255,.1);border:1px solid rgba(124,150,255,.2)}" +
  "@media(max-width:720px){.cgcs-bar .cgcs-chip .cgcs-st{display:none}.cgcs-bar{top:8px;right:max(8px,env(safe-area-inset-right))}}" +
  "@media(prefers-reduced-motion:reduce){#cgcs *{transition:none!important;animation:none!important}}";

  // ── helpers ───────────────────────────────────────────────────────────────
  function h(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function score(q, s) { s = s.toLowerCase(); q = q.toLowerCase(); if (!q) return 0; if (s.indexOf(q) === 0) return 3; if (s.indexOf(q) > -1) return 2; var i = 0, j = 0; while (i < s.length && j < q.length) { if (s[i] === q[j]) j++; i++; } return j === q.length ? 1 : -1; }

  var root, palOv, palInput, palList, drOv, lastFocus = null, opts = [], active = -1;

  function build() {
    // ensure the homepage font family is available wherever the nav renders
    if (!document.querySelector('link[href*="Urbanist"]')) {
      var fl = h("link"); fl.rel = "stylesheet";
      fl.href = "https://fonts.googleapis.com/css2?family=Urbanist:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap";
      document.head.appendChild(fl);
    }
    var style = h("style"); style.textContent = css; document.head.appendChild(style);
    root = h("div"); root.id = "cgcs";

    // top cluster
    var bar = h("div", "cgcs-bar");
    var chip = h("div", "cgcs-chip"); chip.setAttribute("role", "status"); chip.setAttribute("aria-live", "polite");
    chip.innerHTML = '<span class="cgcs-dot" id="cgcsDot"></span><span class="cgcs-st" id="cgcsSt">Checking status…</span>';
    var cmd = h("button", "cgcs-cmd"); cmd.setAttribute("aria-haspopup", "dialog"); cmd.setAttribute("aria-label", "Open command palette");
    cmd.innerHTML = '<span class="ic">⌘</span><span class="cgcs-cmdlbl">Command</span><kbd>' + (/Mac/i.test(navigator.platform) ? "⌘K" : "Ctrl K") + '</kbd>';
    var menu = h("button", "cgcs-menu"); menu.setAttribute("aria-haspopup", "dialog"); menu.setAttribute("aria-label", "Open systems drawer"); menu.textContent = "▦";
    bar.appendChild(chip); bar.appendChild(cmd); bar.appendChild(menu);

    // palette
    palOv = h("div", "cgcs-ov"); palOv.id = "cgcsPal";
    var pscrim = h("div", "cgcs-scrim");
    var pal = h("div", "cgcs-pal"); pal.setAttribute("role", "dialog"); pal.setAttribute("aria-modal", "true"); pal.setAttribute("aria-label", "Command palette");
    var search = h("div", "cgcs-search");
    search.innerHTML = '<span class="ic">⌕</span>';
    palInput = h("input"); palInput.type = "text"; palInput.setAttribute("role", "combobox"); palInput.setAttribute("aria-expanded", "true");
    palInput.setAttribute("aria-controls", "cgcsList"); palInput.setAttribute("aria-autocomplete", "list"); palInput.setAttribute("placeholder", "Search destinations, actions…");
    var esc = h("span", "cgcs-esc", "ESC");
    search.appendChild(palInput); search.appendChild(esc);
    palList = h("div", "cgcs-list"); palList.id = "cgcsList"; palList.setAttribute("role", "listbox"); palList.setAttribute("aria-label", "Results");
    pal.appendChild(search); pal.appendChild(palList);
    palOv.appendChild(pscrim); palOv.appendChild(pal);

    // drawer
    drOv = h("div", "cgcs-ov"); drOv.id = "cgcsDr";
    var dscrim = h("div", "cgcs-scrim");
    var dr = h("div", "cgcs-dr"); dr.setAttribute("role", "dialog"); dr.setAttribute("aria-modal", "true"); dr.setAttribute("aria-label", "Systems drawer");
    var dh = h("div", "cgcs-dh");
    dh.innerHTML = '<img class="cgcs-mk" src="icon.svg" alt="" width="28" height="28"><div><div style="font-weight:800;letter-spacing:.14em;font-size:13px">ClearGlass<b>·</b>OS</div>' +
      '<div style="font-size:8.5px;letter-spacing:.18em;color:#8a90c4;text-transform:uppercase">Systems · Control Surface v3.1</div></div>';
    var dx = h("button", "cgcs-dx"); dx.setAttribute("aria-label", "Close"); dx.textContent = "✕"; dh.appendChild(dx);
    dr.appendChild(dh);
    var ctx = ctxForPage();
    if (ctx) {
      dr.appendChild(h("div", "cgcs-gl", "On this page"));
      ctx.items.forEach(function (it) {
        var a = h("a"); a.href = it[1]; a.innerHTML = '<span class="ic">' + it[2] + '</span>' + it[0]; dr.appendChild(a);
      });
    }
    GROUPS.forEach(function (g) {
      dr.appendChild(h("div", "cgcs-gl", g[0]));
      g[1].forEach(function (it) {
        var a = h("a"); if (it[1].toLowerCase() === here) a.className = "cur";
        a.href = it[1]; if (/^https?:/i.test(it[1])) { a.target = "_blank"; a.rel = "noopener noreferrer"; }
        a.innerHTML = '<span class="ic">' + it[2] + '</span>' + it[0] + (it[1].toLowerCase() === here ? ' <span style="margin-left:auto;font:9px monospace;color:#8a90c4">● here</span>' : "");
        dr.appendChild(a);
      });
    });
    drOv.appendChild(dscrim); drOv.appendChild(dr);

    root.appendChild(bar); root.appendChild(palOv); root.appendChild(drOv);
    document.body.appendChild(root);

    // wiring
    cmd.addEventListener("click", openPalette);
    menu.addEventListener("click", openDrawer);
    dx.addEventListener("click", closeDrawer);
    pscrim.addEventListener("click", closePalette);
    dscrim.addEventListener("click", closeDrawer);
    palInput.addEventListener("input", function () { render(palInput.value); });
    palInput.addEventListener("keydown", paletteKeys);
    document.addEventListener("keydown", globalKeys, true);
    var lastY = 0;
    window.addEventListener("scroll", function () { var y = window.pageYOffset; root.classList.toggle("scrolled", y > 40); lastY = y; }, { passive: true });

    startStatus();
  }

  // ── palette data + render ───────────────────────────────────────────────
  function buildItems(q) {
    var items = [];
    flat.forEach(function (d) { items.push({ kind: "dest", label: d.label, sub: d.group, icon: d.icon, href: d.href }); });
    ACTIONS.forEach(function (a) { items.push({ kind: "act", label: a.label, sub: a.sub, icon: a.icon, href: a.href, act: a.act, ext: a.ext }); });
    if (!q) {
      var rec = recents().map(function (hf) { var d = flat.filter(function (x) { return x.href === hf; })[0]; return d ? { kind: "recent", label: d.label, sub: "Recent", icon: d.icon, href: d.href } : null; }).filter(Boolean);
      var out = [];
      var ctx = ctxForPage();
      if (ctx) ctx.items.forEach(function (it) { out.push({ kind: "ctx", label: it[0], sub: "On this page", icon: it[2], href: it[1] }); });
      return out.concat(rec).concat(items);
    }
    return items.map(function (it) { return { it: it, s: Math.max(score(q, it.label), score(q, it.sub || "") - 1) }; })
      .filter(function (x) { return x.s > 0; }).sort(function (a, b) { return b.s - a.s; }).map(function (x) { return x.it; });
  }

  function render(q) {
    palList.innerHTML = ""; opts = []; active = -1;
    var data = buildItems(q.trim());
    if (!data.length) { palList.appendChild(h("div", "cgcs-empty", "No matches for “" + q + "”")); return; }
    var lastGroup = null;
    data.forEach(function (it, i) {
      var grp = it.kind === "recent" ? "Recent" : it.kind === "ctx" ? "On this page" : it.kind === "act" ? "Actions" : "Destinations";
      if (grp !== lastGroup && !q.trim()) { palList.appendChild(h("div", "cgcs-gl", grp)); lastGroup = grp; }
      var o = h("div", "cgcs-opt"); o.id = "cgcsOpt" + i; o.setAttribute("role", "option"); o.setAttribute("aria-selected", "false");
      o.innerHTML = '<span class="ic">' + it.icon + '</span><div><div class="tl">' + it.label + '</div>' +
        (it.sub ? '<div class="sb">' + it.sub + '</div>' : "") + '</div>' +
        '<span class="meta">' + (it.kind === "act" ? "↵ run" : it.ext ? "↗" : "↵") + '</span>';
      o.addEventListener("click", function () { exec(it); });
      o.addEventListener("mousemove", function () { setActive(i); });
      palList.appendChild(o); opts.push({ el: o, it: it });
    });
    setActive(0);
  }

  function setActive(i) {
    if (!opts.length) return;
    if (active > -1 && opts[active]) opts[active].el.setAttribute("aria-selected", "false");
    active = (i + opts.length) % opts.length;
    var el = opts[active].el; el.setAttribute("aria-selected", "true");
    palInput.setAttribute("aria-activedescendant", el.id);
    var r = el.getBoundingClientRect(), pr = palList.getBoundingClientRect();
    if (r.bottom > pr.bottom) palList.scrollTop += r.bottom - pr.bottom;
    else if (r.top < pr.top) palList.scrollTop -= pr.top - r.top;
  }

  function exec(it) {
    closePalette();
    if (it.act === "copyEmail") { try { navigator.clipboard.writeText(EMAIL); } catch (e) {} toast("Email copied: " + EMAIL); return; }
    if (it.act === "contact") { location.href = "mailto:" + EMAIL; return; }
    if (it.act === "status") { window.open("https://github.com/" + REPO + "/actions", "_blank", "noopener"); return; }
    if (it.href) { if (it.ext || /^https?:/i.test(it.href)) window.open(it.href, "_blank", "noopener"); else location.href = it.href; }
  }

  // ── keyboard ──────────────────────────────────────────────────────────────
  function isOpen() { return palOv.classList.contains("open") || drOv.classList.contains("open"); }
  function typing(t) { return t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable); }

  function globalKeys(e) {
    if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) { e.preventDefault(); togglePalette(); return; }
    if (e.key === "/" && !typing(e.target) && !isOpen()) { e.preventDefault(); openPalette(); return; }
    if (e.key === "Escape" && isOpen()) { e.preventDefault(); closePalette(); closeDrawer(); }
  }

  function paletteKeys(e) {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive(active + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive(active - 1); }
    else if (e.key === "Enter") { e.preventDefault(); if (opts[active]) exec(opts[active].it); }
    else if (e.key === "Tab") { e.preventDefault(); setActive(active + (e.shiftKey ? -1 : 1)); }
  }

  // ── open/close with focus management ────────────────────────────────────
  function openPalette() { closeDrawer(); lastFocus = document.activeElement; palOv.classList.add("open"); palInput.value = ""; render(""); setTimeout(function () { palInput.focus(); }, 30); }
  function closePalette() { if (!palOv.classList.contains("open")) return; palOv.classList.remove("open"); restore(); }
  function togglePalette() { palOv.classList.contains("open") ? closePalette() : openPalette(); }
  function openDrawer() { closePalette(); lastFocus = document.activeElement; drOv.classList.add("open"); trapFocus(drOv); }
  function closeDrawer() { if (!drOv.classList.contains("open")) return; drOv.classList.remove("open"); restore(); }
  function restore() { if (lastFocus && lastFocus.focus) { try { lastFocus.focus(); } catch (e) {} } lastFocus = null; }

  function trapFocus(container) {
    var f = container.querySelectorAll('a[href],button,input,[tabindex]:not([tabindex="-1"])');
    if (f.length) setTimeout(function () { f[0].focus(); }, 30);
    container.addEventListener("keydown", function (e) {
      if (e.key !== "Tab") return;
      var list = container.querySelectorAll('a[href],button,input,[tabindex]:not([tabindex="-1"])');
      if (!list.length) return; var first = list[0], last = list[list.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
  }

  // ── live status (GitHub Actions) ────────────────────────────────────────
  function setStatus(state, text) {
    var dot = document.getElementById("cgcsDot"), st = document.getElementById("cgcsSt");
    if (!dot || !st) return;
    dot.className = "cgcs-dot " + ({ NOMINAL: "ok", SYNCING: "sync", DEGRADED: "warn", FAILURE: "fail" }[state] || "");
    st.textContent = text;
  }
  // A feed row is in flight when its conclusion has not landed yet; the
  // generator writes the raw state ("in_progress", "queued") ahead of the " · ".
  function inFlight(row) {
    var head = String(row && row.detail || "").split("·")[0].trim();
    return head === "in_progress" || head === "queued" || head === "pending" || head === "requested";
  }

  function applyRuns(runs) {
    if (!runs.length) { setStatus("DEGRADED", "No runs"); return; }
    if (runs.some(inFlight)) { setStatus("SYNCING", "Pipeline running"); return; }
    var s = runs[0].status;
    if (s === "ok") setStatus("NOMINAL", "Build healthy");
    else if (s === "bad") setStatus("FAILURE", "Pipeline failure");
    else setStatus("DEGRADED", "Degraded");
  }

  // Fallback only. Unauthenticated api.github.com allows 60 requests/hour/IP and
  // is blocked outright on plenty of corporate networks, which is why the chip
  // read "Status offline" for most visitors before the feed existed.
  function pollApi() {
    fetch("https://api.github.com/repos/" + REPO + "/actions/runs?per_page=10", { headers: { Accept: "application/vnd.github+json" } })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) {
        var runs = (d && d.workflow_runs) || [];
        if (!runs.length) { setStatus("DEGRADED", "No runs"); return; }
        if (runs.some(function (r) { return r.status !== "completed"; })) { setStatus("SYNCING", "Pipeline running"); return; }
        var c = runs[0].conclusion;
        if (c === "success") setStatus("NOMINAL", "Build healthy");
        else if (c === "failure" || c === "timed_out" || c === "startup_failure") setStatus("FAILURE", "Pipeline failure");
        else setStatus("DEGRADED", "Degraded");
      })
      .catch(function () { setStatus("", "Status offline"); });
  }

  function pollStatus() {
    fetch(FEED + "runs.json", { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (rows) {
        if (!Array.isArray(rows)) throw new Error("shape");
        applyRuns(rows);
      })
      .catch(pollApi);
  }
  // The feed is rewritten hourly, so polling faster than that only costs
  // requests. Two minutes kept the chip lively against the old live API call.
  function startStatus() { pollStatus(); setInterval(pollStatus, 300000); }

  // ── tiny toast ─────────────────────────────────────────────────────────
  function toast(msg) {
    var t = h("div", null, msg);
    t.style.cssText = "position:fixed;left:50%;bottom:80px;transform:translateX(-50%);z-index:2147483646;background:rgba(16,19,38,.96);" +
      "border:1px solid rgba(124,150,255,.4);color:#e7ecff;font:13px Inter,system-ui,sans-serif;padding:10px 16px;border-radius:11px;" +
      "box-shadow:0 20px 50px -20px rgba(0,0,0,.7)";
    document.body.appendChild(t); setTimeout(function () { t.style.transition = "opacity .3s"; t.style.opacity = "0"; setTimeout(function () { t.remove(); }, 320); }, 1800);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
  else build();
})();
