/* ClearGlass · Sentinel Core (bottom-right command dock)
   ────────────────────────────────────────────────────────────────────────────
   The collapsible command console: a compact "SENTINEL CORE" pill that expands
   into a mission console — readiness strip, Ask Sentinel, six mission modules,
   eight controls, routes and TOP/BOTTOM jumps.

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
   clock, stealth and motion state). Nothing here claims to monitor anything:
   this public console has no sensors, and it says so.

   No backend, no network request, no tracking, no external command execution.
   Drop in with <script defer src="station-chat.js"></script>. No deps. */
(function () {
  "use strict";
  if (window.__cgStationChat) return;
  window.__cgStationChat = true;

  var STORE_OPEN = "cg-station-open";
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
    { title: "Cyber Monitor", sub: "Defence console", href: "cyber-defense-console.html" },
    { title: "OSINT Fusion", sub: "Ontario deck", href: "Ontario-osint.html" },
    { title: "Sentinel Core", sub: "Geospatial", href: "sentinel.html" },
    { title: "Mission Feed", sub: "Intel briefs", href: "blog/" },
    { title: "Aegis Defence", sub: "Legal shield", href: "aegis.html" },
    { title: "Artemis Analytics", sub: "AI cyber intel", href: "artemis-ai-cyber-intelligence-platform.html" }
  ];

  var ROUTES = [
    { title: "Web Design", href: "web-design.html" },
    { title: "Project Board", href: "project-board.html" }
  ];

  // ── icons (inline, so nothing is fetched) ────────────────────────────────
  var IC_SEND = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="M7 17 17 7M9 7h8v8" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var IC_CHEV = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="m6.5 9.5 5.5 5.5 5.5-5.5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var TRACE = '<svg class="cgst-trace" viewBox="0 0 120 18" preserveAspectRatio="none" aria-hidden="true">' +
    '<polyline points="0,9 14,9 19,3 24,15 29,9 46,9 50,5 54,13 58,9 80,9 84,2 89,16 94,9 120,9"/></svg>';

  // ── styles ───────────────────────────────────────────────────────────────
  var CSS = [
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
    ".cgst-sr{position:absolute!important;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}",

    /* ── sheet (absolute, so a collapsed dock reserves no phantom box). Not
       named "*-panel": clearglass-crimson.css repaints every [class*="-panel"]
       with !important, which flattened this into a see-through card. ── */
    "#cg-station .cgst-sheet{position:absolute;left:0;right:0;bottom:calc(100% + 10px);",
    /* capped so an open console clears the site header on desktop and phones */
    "max-height:min(600px,calc(100vh - var(--cgst-lift) - 40px));max-height:min(600px,calc(100dvh - var(--cgst-lift) - 40px));",
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
    "#cg-station .cgst-ask input{flex:1 1 auto;min-width:0;height:38px;border:0;outline:0;background:none;color:#fff;font:600 16px/1.2 var(--cgst-sans)}",
    "#cg-station .cgst-ask input::placeholder{color:#9d7678}",
    "#cg-station .cgst-send{flex:0 0 auto;display:grid;place-items:center;width:40px;height:40px;border-radius:11px;cursor:pointer;",
    "border:1px solid rgba(238,99,101,.6);background:linear-gradient(135deg,rgba(238,99,101,.34),rgba(238,99,122,.16));color:#fff;",
    "transition:transform .2s cubic-bezier(.16,1,.3,1),box-shadow .2s ease}",
    "#cg-station .cgst-send:hover{transform:translateY(-1px);box-shadow:0 0 18px -4px rgba(238,99,101,.8)}",
    "#cg-station .cgst-send svg{width:18px;height:18px;display:block}",

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

    /* ── focus ── */
    "#cg-station button:focus-visible,#cg-station a:focus-visible,#cg-station .cgst-head:focus-visible{outline:2px solid #fff;outline-offset:3px}",

    /* ── yield entirely while the Sentinel conversation is open ── */
    /* descendants re-assert visibility and pointer-events, so hide the whole
       subtree or an invisible sheet keeps catching taps over the modal */
    "body.sentinel-open #cg-station,body.sentinel-open #cg-station *{opacity:0;visibility:hidden!important;pointer-events:none!important}",

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
    /* reserve the corner so the dock never sits on top of the last content */
    "body.cg-station-mounted{padding-bottom:calc(var(--cgst-lift,66px) + 22px + env(safe-area-inset-bottom))}",
    "body.cg-station-mounted:not(.cgst-absorb-stack){padding-bottom:calc(var(--cgst-lift,66px) + var(--cgst-stack-h,52px) + 30px + env(safe-area-inset-bottom))}",

    /* ── stealth skin ── */
    "[data-skin='stealth'] #cg-station .cgst-sheet,[data-skin='stealth'] #cg-station .cgst-dock{",
    "border-color:rgba(120,224,200,.36);box-shadow:0 20px 48px -20px rgba(0,0,0,.94),0 0 0 .5px rgba(120,224,200,.22)}",

    /* ── narrow phones ── */
    "@media(max-width:420px){#cg-station{width:calc(100vw - 20px)}",
    "#cg-station .cgst-sheet{padding:12px 11px 11px;gap:11px}",
    "#cg-station .cgst-title{font-size:14px;letter-spacing:.17em}",
    "#cg-station .cgst-mission strong{font-size:12.5px}}",
    "@media(max-width:340px){#cg-station .cgst-controls,#cg-station .cgst-missions{grid-template-columns:1fr}}",

    /* motion: the OS preference and the site's own Tactical View both quiet it */
    "@media(prefers-reduced-motion:reduce){#cg-station *,#cg-station *::before,#cg-station *::after{transition:none!important;animation:none!important}",
    "#cg-station[data-open='false'] .cgst-sheet{transform:none}}",
    "html[data-cgm-motion='reduced'] #cg-station *,html[data-cgm-motion='reduced'] #cg-station *::before,",
    "html[data-cgm-motion='reduced'] #cg-station *::after{animation:none!important}",
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
    try { return window.matchMedia("(max-width: 720px)").matches; } catch (e) { return false; }
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
    return false;
  }

  // ── Stealth Glass mirror ─────────────────────────────────────────────────
  function stealthButton() { return document.getElementById("cg-stealth-btn"); }

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

  // ── roving keyboard navigation inside the panel ──────────────────────────
  function items() {
    if (!panel) return [];
    return Array.prototype.filter.call(
      panel.querySelectorAll("[data-cgst-item]"),
      function (el) { return !el.disabled && !el.hidden; }
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
  function setOpen(open, moveFocus) {
    root.setAttribute("data-open", String(open));
    dock.setAttribute("aria-expanded", String(open));
    dock.setAttribute("aria-label", open ? "Collapse Sentinel Core" : "Expand Sentinel Core");
    panel.setAttribute("aria-hidden", String(!open));
    writeOpen(open);
    syncClock();
    if (open) typeStatus();
    if (!moveFocus) return;
    if (open) {
      lastFocus = document.activeElement;
      // focusing the field would raise the keyboard over the console on phones
      var first = narrow() ? items()[0] : askInput;
      if (first) { try { first.focus({ preventScroll: true }); } catch (e) { first.focus(); } }
    } else if (dock.focus) dock.focus();
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
      return '<a class="cgst-ctl" href="' + esc(c.href) + '" data-cgst-item>' + inner + '</a>';
    }).join("");

    var routeHTML = ROUTES.map(function (r) {
      return '<a class="cgst-route" href="' + esc(r.href) + '" data-cgst-item>' + esc(r.title) + ' &#8599;</a>';
    }).join("");

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
            'placeholder="Ask Sentinel anything…">' +
          '<button type="submit" class="cgst-send" aria-label="Send to Sentinel">' + IC_SEND + '</button>' +
        '</form>' +

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
          '<span class="cgst-keys"> · Alt+Shift+S toggles</span></p>' +
      '</div>' +

      '<button type="button" class="cgst-dock" id="cgStationDock" aria-expanded="false" aria-controls="cgStationPanel">' +
        '<span class="cgst-radar" aria-hidden="true"><i></i><b></b></span>' +
        '<span class="cgst-dock-tx"><strong>SENTINEL CORE</strong>' +
          '<small><span class="cgst-live" aria-hidden="true"></span><span data-cgst-dock-status>ONLINE · READY</span></small></span>' +
        '<span class="cgst-chev" aria-hidden="true">' + IC_CHEV + '</span>' +
      '</button>';

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

    // wiring
    dock.addEventListener("click", function () { setOpen(root.getAttribute("data-open") !== "true", true); });
    magnetize(dock);

    askForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var prompt = askInput.value.trim();
      askInput.value = "";
      askInput.blur();
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
    });

    panel.addEventListener("keydown", panelKeys);

    document.addEventListener("keydown", function (event) {
      if (event.altKey && event.shiftKey && (event.key === "S" || event.key === "s" || event.code === "KeyS")) {
        event.preventDefault();
        setOpen(root.getAttribute("data-open") !== "true", true);
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
      setOpen(false, true);
      if (lastFocus && lastFocus.focus && lastFocus !== document.body) { try { lastFocus.focus(); } catch (e) {} }
    });

    // On phones an open console covers most of the page, so a tap outside it
    // folds it away, as any popover would.
    document.addEventListener("pointerdown", function (event) {
      if (root.getAttribute("data-open") !== "true" || !narrow()) return;
      if (root.contains(event.target) || document.body.classList.contains("sentinel-open")) return;
      setOpen(false, false);
    }, true);

    window.addEventListener("scroll", queueScroll, { passive: true });
    window.addEventListener("resize", queueScroll, { passive: true });
    window.addEventListener("resize", syncStack, { passive: true });
    window.addEventListener("clearglass:stealth", paintToggles);
    window.addEventListener("online", paintLink);
    window.addEventListener("offline", paintLink);
    document.addEventListener("visibilitychange", syncClock);

    // Stealth (data-skin) and Tactical View (data-cgm-motion) both land on
    // <html>; one attribute-filtered observer keeps both chips honest.
    if (window.MutationObserver) {
      new MutationObserver(paintToggles).observe(document.documentElement, {
        attributes: true, attributeFilter: ["data-skin", "data-cgm-motion"]
      });
      // The Sentinel shell toggles body.sentinel-open; pause the clock under it.
      new MutationObserver(syncClock).observe(document.body, { attributes: true, attributeFilter: ["class"] });
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
    setOpen(readOpen(), false);
    // geometry settles a frame later, once the other docks have mounted
    requestAnimationFrame(syncStack);
    setTimeout(function () { syncStack(); paintToggles(); }, 800);
  }

  // public, read-only-ish control surface for other ClearGlass layers
  window.__cgStation = {
    open: function () { if (root) setOpen(true, true); },
    close: function () { if (root) setOpen(false, false); },
    toggle: function () { if (root) setOpen(root.getAttribute("data-open") !== "true", true); }
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build, { once: true });
  else build();
})();
