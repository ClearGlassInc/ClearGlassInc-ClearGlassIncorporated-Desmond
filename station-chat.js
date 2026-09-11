/* ClearGlass · Station Chat (Control Station dock)
   ────────────────────────────────────────────────────────────────────────────
   The collapsible bottom-right command dock: "Control Station" bar → expands
   into the ClearGlass Station panel (Ask a question → Sentinel, Stealth Glass
   toggle, numbered destinations, TOP/BOTTOM scroll jumps).

   This layer is strictly additive. It owns no state that other scripts own:
     • the chat row re-uses the existing Sentinel concierge (sentinel.js)
     • the Stealth Glass row mirrors and drives the existing #cg-stealth-btn
       (stealth-glass.js) — it never duplicates the privacy mode itself
     • it offsets, never hides, the Sentinel launcher and the security stack so
       three bottom-right docks cannot land on top of one another

   No backend, no network request, no tracking, no external command execution.
   Drop in with <script defer src="station-chat.js"></script>. No deps. */
(function () {
  "use strict";
  if (window.__cgStationChat) return;
  window.__cgStationChat = true;

  var STORE_OPEN = "cg-station-open";
  var STEALTH_KEY = "cg-stealth";
  var DOCK_H = 64;          // dock bar height, kept in sync with the CSS below
  var reduce = false;
  try { reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}

  // ── destinations ─────────────────────────────────────────────────────────
  var LINKS = [
    { code: "01", title: "Web Design", sub: "Design &amp; Development", href: "web-design.html" },
    { code: "02", title: "Insights", sub: "ClearGlass Intelligence", href: "blog/" }
  ];

  // ── icons (inline, so nothing is fetched) ────────────────────────────────
  var IC_CHAT = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="M20 4H4a1.6 1.6 0 0 0-1.6 1.6v9.2A1.6 1.6 0 0 0 4 16.4h2.6V20l4-3.6H20a1.6 1.6 0 0 0 1.6-1.6V5.6A1.6 1.6 0 0 0 20 4Z" ' +
    'fill="currentColor" fill-opacity=".16" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>';
  var IC_CONTRAST = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<circle cx="12" cy="12" r="8.4" stroke="currentColor" stroke-width="1.6"/>' +
    '<path d="M12 3.6a8.4 8.4 0 0 1 0 16.8Z" fill="currentColor"/></svg>';
  var IC_CHEV = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="m6.5 9.5 5.5 5.5 5.5-5.5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  // ── styles ───────────────────────────────────────────────────────────────
  var CSS = [
    /* declared on the root so the co-existence rules below (which target other
       elements' subtrees) can read them too */
    ":root{--cgst-lift:" + (DOCK_H + 10) + "px;--cgst-stack-h:52px}",
    "#cg-station{--cgst-red:#ee6365;--cgst-red-soft:rgba(238,99,101,.28);--cgst-ink:#f7f1f1;--cgst-mute:#c08c8e;",
    "--cgst-mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;",
    "--cgst-sans:'Urbanist',Inter,system-ui,-apple-system,'Segoe UI',sans-serif;",
    "--cgst-edge:max(12px,env(safe-area-inset-right));--cgst-floor:max(12px,env(safe-area-inset-bottom));",
    /* tops out the stacking context: the panel must cover the security dock,
       which pins itself to the maximum z-index */
    "position:fixed;right:var(--cgst-edge);bottom:var(--cgst-floor);z-index:2147483647;",
    "display:flex;flex-direction:column;align-items:stretch;",
    "width:min(340px,calc(100vw - 24px));font-family:var(--cgst-sans);pointer-events:none}",
    "#cg-station *{box-sizing:border-box}",
    "#cg-station>*{pointer-events:auto}",

    /* ── panel (absolute, so a collapsed dock reserves no phantom box) ── */
    "#cg-station .cgst-panel{position:absolute;left:0;right:0;bottom:calc(100% + 8px);",
    "max-height:calc(100vh - var(--cgst-lift) - 56px);overflow-y:auto;overscroll-behavior:contain;",
    "display:flex;flex-direction:column;gap:9px;padding:14px 13px 13px;border-radius:20px;",
    "border:1px solid rgba(238,99,101,.42);color:var(--cgst-ink);",
    "background:radial-gradient(120% 90% at 82% 0,rgba(238,99,101,.16),transparent 60%),linear-gradient(168deg,rgba(44,24,26,.94),rgba(18,12,13,.96));",
    "-webkit-backdrop-filter:blur(18px) saturate(1.4);backdrop-filter:blur(18px) saturate(1.4);",
    "box-shadow:0 26px 60px -22px rgba(0,0,0,.9),0 0 0 .5px rgba(238,99,101,.22),0 0 34px -12px rgba(238,99,101,.45),inset 0 1px 0 rgba(255,255,255,.08);",
    "transform-origin:100% 100%;transition:opacity .26s cubic-bezier(.16,1,.3,1),transform .26s cubic-bezier(.16,1,.3,1)}",
    "#cg-station[data-open='false'] .cgst-panel{opacity:0;transform:translateY(10px) scale(.96);pointer-events:none;visibility:hidden}",
    "#cg-station[data-open='true'] .cgst-panel{opacity:1;transform:none;visibility:visible}",

    /* ── panel header ── */
    "#cg-station .cgst-head{display:flex;align-items:center;gap:9px;padding:0 2px 2px}",
    "#cg-station .cgst-live{flex:0 0 auto;width:9px;height:9px;border-radius:50%;background:var(--cgst-red);",
    "box-shadow:0 0 10px rgba(238,99,101,.85);animation:cgstPulse 2.4s ease-in-out infinite}",
    "@keyframes cgstPulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(.82)}}",
    "#cg-station .cgst-title{flex:1 1 auto;margin:0;font-size:16px;font-weight:800;letter-spacing:-.01em;color:#fff;white-space:nowrap}",
    "#cg-station .cgst-pill{flex:0 0 auto;display:inline-flex;align-items:center;gap:6px;height:26px;padding:0 10px;",
    "border:1px solid rgba(238,99,101,.5);border-radius:999px;background:rgba(238,99,101,.08);color:#e7c9ca;cursor:pointer;",
    "font-family:var(--cgst-mono);font-size:8.5px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;white-space:nowrap;",
    "transition:background .2s ease,border-color .2s ease,color .2s ease}",
    "#cg-station .cgst-pill:hover{background:rgba(238,99,101,.18);border-color:rgba(238,99,101,.8);color:#fff}",
    "#cg-station .cgst-pill-dot{width:7px;height:7px;border-radius:50%;background:rgba(238,99,101,.72);",
    "box-shadow:0 0 7px rgba(238,99,101,.45);transition:background .2s ease,box-shadow .2s ease}",
    "#cg-station .cgst-pill[aria-pressed='true']{border-color:rgba(120,224,200,.6);background:rgba(120,224,200,.1);color:#c9fbf2}",
    "#cg-station .cgst-pill[aria-pressed='true'] .cgst-pill-dot{background:#78e0c8;box-shadow:0 0 9px rgba(120,224,200,.8)}",

    /* ── rows ── */
    "#cg-station .cgst-row{display:flex;align-items:center;gap:11px;width:100%;padding:11px 12px;text-align:left;",
    "border:1px solid rgba(238,99,101,.22);border-radius:15px;background:rgba(26,17,18,.7);color:var(--cgst-ink);",
    "text-decoration:none;cursor:pointer;font-family:inherit;",
    "transition:transform .2s cubic-bezier(.16,1,.3,1),border-color .2s ease,background .2s ease,box-shadow .2s ease}",
    "#cg-station .cgst-row:hover{transform:translateY(-1px);border-color:rgba(238,99,101,.62);background:rgba(44,24,26,.85);",
    "box-shadow:0 10px 26px -16px rgba(0,0,0,.9),0 0 18px -8px rgba(238,99,101,.55)}",
    "#cg-station .cgst-row--primary{border-color:rgba(238,99,101,.55);",
    "background:linear-gradient(104deg,rgba(238,99,101,.22),rgba(238,99,122,.08) 62%,rgba(26,17,18,.72))}",
    "#cg-station .cgst-ic{flex:0 0 auto;display:grid;place-items:center;width:38px;height:38px;border-radius:12px;",
    "border:1px solid rgba(238,99,101,.4);background:rgba(238,99,101,.12);color:var(--cgst-red)}",
    "#cg-station .cgst-ic svg{width:19px;height:19px;display:block}",
    "#cg-station .cgst-num{flex:0 0 auto;display:grid;place-items:center;width:38px;height:38px;border-radius:12px;",
    "border:1px solid rgba(238,99,101,.34);background:rgba(238,99,101,.07);color:#eab2b3;",
    "font-family:var(--cgst-mono);font-size:12px;font-weight:700;letter-spacing:.04em}",
    "#cg-station .cgst-tx{flex:1 1 auto;min-width:0;display:block}",
    "#cg-station .cgst-tx strong{display:block;font-size:15px;font-weight:700;color:#fff;letter-spacing:-.01em;",
    "overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
    "#cg-station .cgst-tx small{display:block;margin-top:2px;font-family:var(--cgst-mono);font-size:9.5px;letter-spacing:.055em;",
    "color:var(--cgst-mute);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
    "#cg-station .cgst-go{flex:0 0 auto;color:var(--cgst-red);font-size:14px;line-height:1;transition:transform .2s cubic-bezier(.16,1,.3,1)}",
    "#cg-station .cgst-row:hover .cgst-go{transform:translate(2px,-2px)}",
    "#cg-station .cgst-badge{flex:0 0 auto;padding:5px 11px;border:1px solid rgba(238,99,101,.42);border-radius:999px;",
    "background:rgba(238,99,101,.07);color:#dfa9ab;font-family:var(--cgst-mono);font-size:9px;font-weight:700;letter-spacing:.14em}",
    "#cg-station .cgst-row[aria-pressed='true'] .cgst-badge{border-color:rgba(120,224,200,.6);background:rgba(120,224,200,.12);color:#c9fbf2}",
    "#cg-station .cgst-row[aria-pressed='true'] .cgst-ic{border-color:rgba(120,224,200,.5);background:rgba(120,224,200,.12);color:#78e0c8}",

    /* ── scroll jumps ── */
    "#cg-station .cgst-jumps{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:1px}",
    "#cg-station .cgst-jump{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:44px;padding:0 10px;",
    "border:1px solid rgba(238,99,101,.32);border-radius:14px;background:rgba(26,17,18,.66);color:#eedcdc;cursor:pointer;",
    "font-family:var(--cgst-mono);font-size:10px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;",
    "transition:border-color .2s ease,background .2s ease,color .2s ease,transform .2s cubic-bezier(.16,1,.3,1)}",
    "#cg-station .cgst-jump:hover:not([disabled]){transform:translateY(-1px);border-color:rgba(238,99,101,.7);background:rgba(238,99,101,.14);color:#fff}",
    "#cg-station .cgst-jump[disabled]{opacity:.34;cursor:default}",

    /* ── dock bar ── */
    "#cg-station .cgst-dock{--cgst-mx:0px;--cgst-my:0px;display:flex;align-items:center;gap:11px;width:100%;",
    "min-height:" + DOCK_H + "px;padding:0 14px;border:1px solid rgba(238,99,101,.5);border-radius:18px;cursor:pointer;text-align:left;",
    "color:var(--cgst-ink);font-family:inherit;overflow:hidden;isolation:isolate;-webkit-tap-highlight-color:transparent;",
    "background:radial-gradient(140% 130% at 88% 50%,rgba(238,99,101,.22),transparent 66%),linear-gradient(168deg,rgba(46,25,27,.95),rgba(19,13,14,.97));",
    "-webkit-backdrop-filter:blur(16px) saturate(1.45);backdrop-filter:blur(16px) saturate(1.45);",
    "box-shadow:0 18px 44px -18px rgba(0,0,0,.92),0 0 0 .5px rgba(238,99,101,.26),0 0 26px -10px rgba(238,99,101,.5),inset 0 1px 0 rgba(255,255,255,.1);",
    "transform:translate3d(var(--cgst-mx),var(--cgst-my),0);will-change:transform;",
    "transition:transform .22s cubic-bezier(.16,1,.3,1),border-color .22s ease,box-shadow .22s ease}",
    "#cg-station .cgst-dock:hover{border-color:rgba(238,99,101,.85);",
    "box-shadow:0 22px 50px -18px rgba(0,0,0,.95),0 0 0 .5px rgba(238,99,101,.5),0 0 32px -8px rgba(238,99,101,.7),inset 0 1px 0 rgba(255,255,255,.13)}",
    "#cg-station .cgst-dock:active{transform:translate3d(var(--cgst-mx),var(--cgst-my),0) scale(.985)}",
    "#cg-station .cgst-dock-ic{position:relative;flex:0 0 auto;display:grid;place-items:center;width:38px;height:38px;border-radius:12px;",
    "border:1px solid rgba(238,99,101,.45);color:var(--cgst-red);",
    /* the ring is the live read-through-the-page scroll progress */
    "background:conic-gradient(rgba(238,99,101,.55) calc(var(--cgst-progress,0) * 1%),rgba(238,99,101,.1) 0)}",
    "#cg-station .cgst-dock-ic::before{content:'';position:absolute;inset:3px;border-radius:9px;background:rgba(22,14,15,.94)}",
    "#cg-station .cgst-dock-ic svg{position:relative;width:19px;height:19px;display:block}",
    "#cg-station .cgst-ping{position:absolute;top:-3px;right:-3px;width:9px;height:9px;border-radius:50%;background:var(--cgst-red);",
    "border:1.5px solid #16100f;box-shadow:0 0 9px rgba(238,99,101,.9);animation:cgstPulse 2.4s ease-in-out infinite}",
    "#cg-station .cgst-dock-tx{flex:1 1 auto;min-width:0}",
    "#cg-station .cgst-dock-tx strong{display:block;font-size:15px;font-weight:800;color:#fff;letter-spacing:-.01em;",
    "overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
    "#cg-station .cgst-dock-tx small{display:block;margin-top:2px;font-family:var(--cgst-mono);font-size:9px;font-weight:600;",
    "letter-spacing:.2em;color:var(--cgst-mute)}",
    "#cg-station .cgst-chev{flex:0 0 auto;color:#e2b4b5;transition:transform .26s cubic-bezier(.16,1,.3,1)}",
    "#cg-station .cgst-chev svg{width:20px;height:20px;display:block}",
    "#cg-station[data-open='false'] .cgst-chev{transform:rotate(180deg)}",
    "#cg-station[data-open='false'] .cgst-ping{opacity:1}",
    "#cg-station[data-open='true'] .cgst-ping{opacity:0}",

    /* ── focus ── */
    "#cg-station button:focus-visible,#cg-station a:focus-visible{outline:2px solid #fff;outline-offset:3px}",

    /* ── yield entirely while the Sentinel conversation is open ── */
    "body.sentinel-open #cg-station{opacity:0;visibility:hidden;pointer-events:none}",

    /* ── keep the other bottom-right docks clear of this one ──
       Three fixed docks share the bottom-right corner. Nothing is hidden; the
       stack is simply ordered dock → security stack → Sentinel launcher.
       The security stack hard-codes its own bottom under 720px, so this has to
       out-specify it rather than ride on --cg-security-bottom. */
    "body.cg-station-mounted #cg-security-stack{",
    "bottom:calc(max(12px,env(safe-area-inset-bottom)) + var(--cgst-lift,74px))!important}",
    "body.cg-station-mounted .sentinel-launcher{",
    "bottom:calc(max(12px,env(safe-area-inset-bottom)) + var(--cgst-lift,74px) + var(--cgst-stack-h,52px) + 10px)!important}",
    /* reserve the corner so the docks never sit on top of page content */
    "body.cg-station-mounted{padding-bottom:calc(var(--cgst-lift,74px) + var(--cgst-stack-h,52px) + 34px + env(safe-area-inset-bottom))}",

    /* ── stealth skin ── */
    "[data-skin='stealth'] #cg-station .cgst-panel,[data-skin='stealth'] #cg-station .cgst-dock{",
    "border-color:rgba(120,224,200,.34);box-shadow:0 20px 48px -20px rgba(0,0,0,.94),0 0 0 .5px rgba(120,224,200,.22)}",

    /* ── narrow phones ── */
    "@media(max-width:420px){#cg-station{width:min(320px,calc(100vw - 20px))}",
    "#cg-station .cgst-title{font-size:15px}#cg-station .cgst-tx strong{font-size:14px}}",

    "@media(prefers-reduced-motion:reduce){#cg-station *,#cg-station *::before{transition:none!important;animation:none!important}",
    "#cg-station[data-open='false'] .cgst-panel{transform:none}}",
    "@media print{#cg-station{display:none!important}}",
    "@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){",
    "#cg-station .cgst-panel{background:linear-gradient(168deg,rgba(44,24,26,.99),rgba(18,12,13,.99))}",
    "#cg-station .cgst-dock{background:linear-gradient(168deg,rgba(46,25,27,.99),rgba(19,13,14,.99))}}"
  ].join("");

  function injectStyle() {
    if (document.getElementById("cg-station-style")) return;
    var style = document.createElement("style");
    style.id = "cg-station-style";
    style.textContent = CSS;
    (document.head || document.documentElement).appendChild(style);
  }

  // ── state ────────────────────────────────────────────────────────────────
  function readOpen() {
    try {
      var v = localStorage.getItem(STORE_OPEN);
      return v === null ? true : v === "1";
    } catch (e) { return true; }
  }
  function writeOpen(v) { try { localStorage.setItem(STORE_OPEN, v ? "1" : "0"); } catch (e) {} }

  var root, panel, dock, pill, stealthRow, stealthBadge, jumpTop, jumpBottom;
  var lastFocus = null;

  // ── Sentinel hand-off ────────────────────────────────────────────────────
  // sentinel.js binds openPanel() directly on [data-sentinel-open] and binds its
  // own Station grid on the launcher *container*. Dispatching a non-bubbling
  // click therefore opens the concierge itself and never the grid, without this
  // file having to reach into sentinel.js.
  function openSentinel() {
    var btn = document.querySelector("[data-sentinel-open]");
    if (btn) {
      try {
        btn.dispatchEvent(new MouseEvent("click", { bubbles: false, cancelable: true }));
        return true;
      } catch (e) {
        btn.click();
        return true;
      }
    }
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

  // Idempotent on purpose: this also runs from a MutationObserver, so writing
  // unchanged values back into the DOM would feed the observer its own output.
  function paintStealth() {
    var on = stealthActive();
    var label = on ? "ON" : "OFF";
    if (stealthBadge && stealthBadge.textContent !== label) stealthBadge.textContent = label;
    if (stealthRow) stealthRow.setAttribute("aria-pressed", String(on));
    if (pill) {
      pill.setAttribute("aria-pressed", String(on));
      pill.title = on ? "Stealth Glass is on — tap to restore signal" : "Stealth Glass — dim and desaturate";
    }
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

  // ── scroll jumps + progress ring ─────────────────────────────────────────
  function scrollTo(y) {
    try { window.scrollTo({ top: y, behavior: reduce ? "auto" : "smooth" }); }
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
      panel.querySelectorAll(".cgst-pill,.cgst-row,.cgst-jump"),
      function (el) { return !el.disabled; }
    );
  }

  function panelKeys(event) {
    var list = items();
    if (!list.length) return;
    var at = list.indexOf(document.activeElement);
    if (event.key === "ArrowDown") { event.preventDefault(); list[(at + 1 + list.length) % list.length].focus(); }
    else if (event.key === "ArrowUp") { event.preventDefault(); list[(at - 1 + list.length) % list.length].focus(); }
    else if (event.key === "Home") { event.preventDefault(); list[0].focus(); }
    else if (event.key === "End") { event.preventDefault(); list[list.length - 1].focus(); }
  }

  // ── open / close ─────────────────────────────────────────────────────────
  // The security stack's height depends on which controls mounted into it, so
  // the launcher offset is measured rather than assumed.
  function measureStack() {
    var stack = document.getElementById("cg-security-stack");
    var h = stack ? Math.round(stack.getBoundingClientRect().height) : 0;
    document.documentElement.style.setProperty("--cgst-stack-h", (h || 52) + "px");
    // documented hook honoured by stealth-glass.js when it runs standalone
    document.documentElement.style.setProperty("--cg-security-bottom", (DOCK_H + 22) + "px");
  }

  function setOpen(open, moveFocus) {
    root.setAttribute("data-open", String(open));
    dock.setAttribute("aria-expanded", String(open));
    dock.setAttribute("aria-label", open ? "Collapse the ClearGlass Control Station" : "Expand the ClearGlass Control Station");
    panel.setAttribute("aria-hidden", String(!open));
    writeOpen(open);
    if (!moveFocus) return;
    if (open) {
      lastFocus = document.activeElement;
      var list = items();
      if (list.length) list[0].focus();
    } else if (dock.focus) dock.focus();
  }

  // ── build ────────────────────────────────────────────────────────────────
  function build() {
    if (!document.body || document.getElementById("cg-station")) return;
    injectStyle();

    root = document.createElement("aside");
    root.id = "cg-station";
    root.setAttribute("aria-label", "ClearGlass Control Station");

    var linkHTML = LINKS.map(function (l) {
      return '<a class="cgst-row" href="' + l.href + '" data-cgst-item>' +
        '<span class="cgst-num" aria-hidden="true">' + l.code + '</span>' +
        '<span class="cgst-tx"><strong>' + l.title + '</strong><small>' + l.sub + '</small></span>' +
        '<span class="cgst-go" aria-hidden="true">&#8599;</span></a>';
    }).join("");

    root.innerHTML =
      '<div class="cgst-panel" id="cgStationPanel" role="group" aria-label="ClearGlass Station">' +
        '<div class="cgst-head">' +
          '<span class="cgst-live" aria-hidden="true"></span>' +
          '<h2 class="cgst-title">ClearGlass Station</h2>' +
          '<button type="button" class="cgst-pill" data-cgst="stealth" aria-pressed="false">' +
            '<span class="cgst-pill-dot" aria-hidden="true"></span>Stealth Glass</button>' +
        '</div>' +
        '<button type="button" class="cgst-row cgst-row--primary" data-cgst="sentinel" data-cgst-item>' +
          '<span class="cgst-ic" aria-hidden="true">' + IC_CHAT + '</span>' +
          '<span class="cgst-tx"><strong>Ask a question</strong><small>Open Sentinel</small></span>' +
          '<span class="cgst-go" aria-hidden="true">&#8599;</span></button>' +
        '<button type="button" class="cgst-row" data-cgst="stealth" data-cgst-item aria-pressed="false">' +
          '<span class="cgst-ic" aria-hidden="true">' + IC_CONTRAST + '</span>' +
          '<span class="cgst-tx"><strong>Stealth Glass</strong><small>Privacy visual mode</small></span>' +
          '<span class="cgst-badge" data-cgst-badge>OFF</span></button>' +
        linkHTML +
        '<div class="cgst-jumps">' +
          '<button type="button" class="cgst-jump" data-cgst="top">&#8593; Top</button>' +
          '<button type="button" class="cgst-jump" data-cgst="bottom">&#8595; Bottom</button>' +
        '</div>' +
      '</div>' +
      '<button type="button" class="cgst-dock" id="cgStationDock" aria-expanded="true" aria-controls="cgStationPanel">' +
        '<span class="cgst-dock-ic" aria-hidden="true">' + IC_CHAT + '<i class="cgst-ping"></i></span>' +
        '<span class="cgst-dock-tx"><strong>Control Station</strong><small>CLEARGLASS</small></span>' +
        '<span class="cgst-chev" aria-hidden="true">' + IC_CHEV + '</span>' +
      '</button>';

    document.body.appendChild(root);
    document.body.classList.add("cg-station-mounted");

    panel = root.querySelector(".cgst-panel");
    dock = root.querySelector(".cgst-dock");
    pill = root.querySelector(".cgst-pill");
    stealthRow = root.querySelector('.cgst-row[data-cgst="stealth"]');
    stealthBadge = root.querySelector("[data-cgst-badge]");
    jumpTop = root.querySelector('[data-cgst="top"]');
    jumpBottom = root.querySelector('[data-cgst="bottom"]');

    // wiring
    dock.addEventListener("click", function () { setOpen(root.getAttribute("data-open") !== "true", true); });
    magnetize(dock);

    root.addEventListener("click", function (event) {
      var target = event.target.closest ? event.target.closest("[data-cgst]") : null;
      if (!target || target === dock) return;
      var act = target.getAttribute("data-cgst");
      if (act === "sentinel") { openSentinel(); return; }
      if (act === "stealth") { toggleStealth(); return; }
      if (act === "top") { scrollTo(0); return; }
      if (act === "bottom") { scrollTo(docHeight()); return; }
    });

    panel.addEventListener("keydown", panelKeys);

    document.addEventListener("keydown", function (event) {
      if (event.altKey && event.shiftKey && (event.key === "S" || event.key === "s")) {
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
      if (lastFocus && lastFocus.focus) { try { lastFocus.focus(); } catch (e) {} }
    });

    window.addEventListener("scroll", queueScroll, { passive: true });
    window.addEventListener("resize", queueScroll, { passive: true });
    window.addEventListener("resize", measureStack, { passive: true });
    window.addEventListener("clearglass:stealth", paintStealth);

    // stealth-glass.js mounts on its own schedule; catch it the first time it
    // lands, then stop watching — this observer must never outlive its purpose.
    if (window.MutationObserver && document.body && !stealthButton()) {
      var observer = new MutationObserver(function () {
        if (!stealthButton()) return;
        observer.disconnect();
        paintStealth();
        measureStack();
      });
      observer.observe(document.body, { childList: true, subtree: true });
      setTimeout(function () { observer.disconnect(); }, 8000);
    }

    paintStealth();
    syncScroll();
    measureStack();
    setOpen(readOpen(), false);
    // geometry settles a frame later, once the other docks have mounted
    requestAnimationFrame(measureStack);
    setTimeout(measureStack, 800);
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
