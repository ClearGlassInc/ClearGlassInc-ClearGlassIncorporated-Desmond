/** Progressive future-glass control discovery and pointer physics. */
(() => {
  "use strict";

  const SELECTOR = [
    "button", ".btn", ".cg-btn", ".cta", "[role='button']",
    "input[type='submit']", "input[type='button']", "input[type='reset']",
    "a.button", "a.btn", "a.cta"
  ].join(",");
  const PRIMARY_HINT = /(^|[\s\-_])(primary|purchase|checkout|buy|order|subscribe|deploy|submit|cta)([\s\-_]|$)/i;
  const DANGER_HINT = /(^|[\s\-_])(danger|delete|remove|revoke|destructive)([\s\-_]|$)/i;
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = matchMedia("(hover: hover) and (pointer: fine)");
  const observed = new WeakSet();
  const states = new WeakMap();

  function hasOwnedPseudo(control, pseudo) {
    const content = getComputedStyle(control, pseudo).content;
    return content && content !== "none" && content !== "normal" && content !== '""';
  }

  function isPrimary(control) {
    const identity = `${control.className || ""} ${control.id || ""} ${control.getAttribute("name") || ""}`;
    return PRIMARY_HINT.test(identity);
  }

  function render(control) {
    const state = states.get(control);
    if (!state) return;
    if (!control.classList.contains("is-future-active")) { state.frame = 0; return; }
    const ease = .16;
    state.x += (state.targetX - state.x) * ease;
    state.y += (state.targetY - state.y) * ease;
    control.style.setProperty("--glass-btn-magnet-x", `${state.x.toFixed(2)}px`);
    control.style.setProperty("--glass-btn-magnet-y", `${state.y.toFixed(2)}px`);
    if (Math.abs(state.targetX - state.x) + Math.abs(state.targetY - state.y) > .08) {
      state.frame = requestAnimationFrame(() => render(control));
    } else state.frame = 0;
  }

  function onPointerMove(event) {
    if (reduceMotion.matches || !finePointer.matches) return;
    const control = event.currentTarget;
    const rect = control.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const x = Math.max(0, Math.min(rect.width, event.clientX - rect.left));
    const y = Math.max(0, Math.min(rect.height, event.clientY - rect.top));
    const nx = x / rect.width, ny = y / rect.height;
    const distance = Math.min(1, Math.hypot(nx - .5, ny - .5) * 1.42);
    control.style.setProperty("--pointer-x", `${(nx * 100).toFixed(1)}%`);
    control.style.setProperty("--pointer-y", `${(ny * 100).toFixed(1)}%`);
    control.style.setProperty("--pointer-distance", (1 - distance).toFixed(3));
    if (control.classList.contains("future-glass-primary")) {
      const state = states.get(control);
      const limit = Math.min(5, Math.max(2, rect.width / 70));
      state.targetX = (nx - .5) * limit * 2;
      state.targetY = (ny - .5) * limit * 1.35;
      if (!state.frame) state.frame = requestAnimationFrame(() => render(control));
    }
  }

  function resetPointer(event) {
    const control = event.currentTarget, state = states.get(control);
    if (state) state.targetX = state.targetY = 0;
    control.style.setProperty("--pointer-x", "50%");
    control.style.setProperty("--pointer-y", "50%");
    control.style.setProperty("--pointer-distance", "0");
    if (!reduceMotion.matches && state && !state.frame) state.frame = requestAnimationFrame(() => render(control));
  }

  function activate(control) {
    if (control.classList.contains("is-future-active")) return;
    control.classList.add("is-future-active");
    if (!reduceMotion.matches && finePointer.matches) {
      control.addEventListener("pointermove", onPointerMove, { passive: true });
      control.addEventListener("pointerleave", resetPointer, { passive: true });
    }
  }

  const viewportObserver = "IntersectionObserver" in window
    ? new IntersectionObserver(entries => {
        for (const entry of entries) if (entry.isIntersecting) {
          activate(entry.target);
          viewportObserver.unobserve(entry.target);
        }
      }, { rootMargin: "180px" })
    : null;

  function enhance(control) {
    if (!(control instanceof HTMLElement) || observed.has(control) || control.closest("[data-no-future-glass]")) return;
    observed.add(control);
    const baseBackground = getComputedStyle(control).backgroundImage;
    if (baseBackground && baseBackground !== "none") control.style.setProperty("--future-base-background-image", baseBackground);
    control.classList.add("future-glass-control");
    if (!(control instanceof HTMLInputElement) && !hasOwnedPseudo(control, "::before") && !hasOwnedPseudo(control, "::after")) control.classList.add("future-glass-layers");
    if (isPrimary(control)) control.classList.add("future-glass-primary");
    if (DANGER_HINT.test(`${control.className} ${control.id}`)) control.classList.add("future-glass-danger");
    states.set(control, { x: 0, y: 0, targetX: 0, targetY: 0, frame: 0 });
    if (viewportObserver) viewportObserver.observe(control); else activate(control);
  }

  function discover(root = document) {
    if (root instanceof Element && root.matches(SELECTOR)) enhance(root);
    root.querySelectorAll?.(SELECTOR).forEach(enhance);
  }

  /*
   * CLEARGLASS SHIELD // MISSION INTERFACE
   * This is a local, deterministic presentation layer. It does not connect to
   * VPN gateways, Stripe, GitHub, Slack, Etsy, external intelligence feeds,
   * packet captures, or remote agents. The UI deliberately labels simulation
   * data as simulation so the page never turns visual effects into false proof.
   */
  function initShieldInterface() {
    if (!/\/shield\.html?$/i.test(location.pathname) || document.getElementById("cg-shield-nexus")) return;

    const style = document.createElement("style");
    style.id = "cg-shield-nexus-style";
    style.textContent = `
      #cg-shield-nexus{position:relative;margin:0 auto 12px;width:min(1180px,92vw);border:1px solid rgba(103,232,249,.24);border-radius:22px;overflow:hidden;background:linear-gradient(145deg,rgba(7,14,24,.94),rgba(13,9,27,.96));box-shadow:0 24px 80px rgba(0,0,0,.34),inset 0 1px 0 rgba(255,255,255,.06)}
      #cg-shield-nexus:before{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(103,232,249,.08),transparent);transform:translateX(-120%);animation:cgShieldScan 9s ease-in-out infinite;pointer-events:none}
      @keyframes cgShieldScan{0%,58%{transform:translateX(-120%)}72%{transform:translateX(120%)}100%{transform:translateX(120%)}}
      .cgsn-top{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px 18px;border-bottom:1px solid rgba(255,255,255,.08);font:700 10px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.14em;text-transform:uppercase}
      .cgsn-top b{color:#67e8f9}.cgsn-status{color:#9aa8bd}.cgsn-status i{display:inline-block;width:7px;height:7px;margin-right:7px;border-radius:50%;background:#fbbf24;box-shadow:0 0 12px #fbbf24}
      .cgsn-grid{position:relative;display:grid;grid-template-columns:1.2fr .8fr;gap:0}
      .cgsn-main{padding:22px}.cgsn-side{padding:22px;border-left:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.018)}
      .cgsn-kicker{margin:0 0 7px;color:#a78bfa;font:800 10px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.16em;text-transform:uppercase}
      .cgsn-title{margin:0;color:#edf3ff;font:800 clamp(1.35rem,3vw,2rem)/1.05 system-ui,sans-serif;letter-spacing:-.035em}
      .cgsn-copy{max-width:690px;margin:9px 0 18px;color:#9aa8bd;font-size:13px}
      .cgsn-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
      .cgsn-metric{padding:12px;border:1px solid rgba(255,255,255,.08);border-radius:12px;background:rgba(255,255,255,.025)}
      .cgsn-metric span{display:block;color:#7f8ca3;font:700 9px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.12em;text-transform:uppercase}.cgsn-metric strong{display:block;margin-top:7px;color:#f2f7ff;font:800 18px/1 system-ui}.cgsn-metric small{display:block;margin-top:5px;color:#67e8f9;font-size:10px}
      .cgsn-console{margin-top:12px;border:1px solid rgba(103,232,249,.16);border-radius:14px;background:#05090f;overflow:hidden}
      .cgsn-console-head{display:flex;justify-content:space-between;padding:9px 12px;border-bottom:1px solid rgba(255,255,255,.07);color:#8fa0ba;font:700 9px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.12em;text-transform:uppercase}.cgsn-console-head b{color:#34d399}
      .cgsn-console-body{min-height:88px;padding:12px;color:#9fd9e7;font:11px/1.7 ui-monospace,SFMono-Regular,Menlo,monospace}
      .cgsn-line{display:block}.cgsn-line:before{content:"> ";color:#a78bfa}.cgsn-line[data-ok="1"]:after{content:"  [VERIFIED LOCALLY]";color:#34d399}
      .cgsn-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.cgsn-btn{border:1px solid rgba(103,232,249,.24);border-radius:10px;padding:9px 12px;background:rgba(103,232,249,.06);color:#dffbff;font:750 10px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.06em;cursor:pointer}.cgsn-btn:hover{border-color:#67e8f9;box-shadow:0 0 20px rgba(103,232,249,.12)}
      .cgsn-side h3{margin:0 0 11px;color:#edf3ff;font-size:12px;letter-spacing:.08em;text-transform:uppercase}.cgsn-node{display:grid;grid-template-columns:28px 1fr;gap:10px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.06)}.cgsn-node:last-child{border-bottom:0}.cgsn-node b{display:grid;place-items:center;width:28px;height:28px;border-radius:8px;background:rgba(167,139,250,.1);color:#a78bfa;font:800 10px ui-monospace}.cgsn-node strong{display:block;font-size:11px}.cgsn-node span{display:block;color:#7f8ca3;font-size:10px;margin-top:2px}
      .cgsn-gate{margin-top:14px;padding:10px;border:1px solid rgba(52,211,153,.16);border-radius:11px;background:rgba(52,211,153,.045);color:#a9d9c5;font-size:10px}.cgsn-gate b{color:#34d399}
      @media(max-width:800px){.cgsn-grid{grid-template-columns:1fr}.cgsn-side{border-left:0;border-top:1px solid rgba(255,255,255,.08)}.cgsn-metrics{grid-template-columns:repeat(2,1fr)}}
      @media(max-width:480px){.cgsn-main,.cgsn-side{padding:16px}.cgsn-top{align-items:flex-start;flex-direction:column}.cgsn-metrics{grid-template-columns:1fr 1fr}}
      @media(prefers-reduced-motion:reduce){#cg-shield-nexus:before{animation:none}}
    `;
    document.head.appendChild(style);

    const nexus = document.createElement("section");
    nexus.id = "cg-shield-nexus";
    nexus.setAttribute("aria-label", "ClearGlass Shield local verification console");
    nexus.innerHTML = `
      <div class="cgsn-top"><span><b>CG / SHIELD NEXUS</b> · LOCAL PRESENTATION PLANE</span><span class="cgsn-status"><i></i>CONCEPT / SIMULATION</span></div>
      <div class="cgsn-grid">
        <div class="cgsn-main">
          <p class="cgsn-kicker">Mission interface · evidence gated</p>
          <h2 class="cgsn-title">Observe. Verify. Authorize. Never confuse telemetry with proof.</h2>
          <p class="cgsn-copy">A futuristic command surface for the proposed Shield architecture. Every value below is deterministic demonstration data until real infrastructure, tests, audits and signed evidence exist.</p>
          <div class="cgsn-metrics">
            <div class="cgsn-metric"><span>Proof objects</span><strong id="cgsn-proof">06/06</strong><small>planned surfaces</small></div>
            <div class="cgsn-metric"><span>Unverified claims</span><strong id="cgsn-claims">00</strong><small>UI gate active</small></div>
            <div class="cgsn-metric"><span>Data paths</span><strong>00</strong><small>runtime not connected</small></div>
            <div class="cgsn-metric"><span>Execution</span><strong>LOCKED</strong><small>human authorization</small></div>
          </div>
          <div class="cgsn-console" aria-live="polite">
            <div class="cgsn-console-head"><span>Evidence console</span><b>LOCAL ONLY</b></div>
            <div class="cgsn-console-body" id="cgsn-log"><span class="cgsn-line" data-ok="1">boot / deterministic proof surface initialized</span><span class="cgsn-line">policy / external execution disabled</span><span class="cgsn-line">claims / waiting for implementation evidence</span></div>
          </div>
          <div class="cgsn-actions"><button class="cgsn-btn" type="button" id="cgsn-verify">RUN LOCAL VERIFICATION</button><button class="cgsn-btn" type="button" id="cgsn-threat">VIEW THREAT MODEL</button></div>
        </div>
        <aside class="cgsn-side">
          <h3>Architecture chain</h3>
          <div class="cgsn-node"><b>01</b><div><strong>Client</strong><span>WireGuard-first transport</span></div></div>
          <div class="cgsn-node"><b>02</b><div><strong>Trust Gateway</strong><span>signed image · runtime controls</span></div></div>
          <div class="cgsn-node"><b>03</b><div><strong>Veil Layer</strong><span>defined threat-model tradeoffs</span></div></div>
          <div class="cgsn-node"><b>04</b><div><strong>Proof Layer</strong><span>inventory · builds · audits</span></div></div>
          <div class="cgsn-gate"><b>CLAIM GATE:</b> no production assertion is unlocked by animation alone.</div>
        </aside>
      </div>
    `;

    const hero = document.querySelector("header.hero");
    if (hero) hero.insertAdjacentElement("afterend", nexus);
    else document.body.insertBefore(nexus, document.body.firstChild);

    const log = nexus.querySelector("#cgsn-log");
    const verify = nexus.querySelector("#cgsn-verify");
    const threat = nexus.querySelector("#cgsn-threat");
    let run = 0;

    verify.addEventListener("click", () => {
      run += 1;
      const lines = [
        "integrity / deterministic UI assets reachable",
        "claim-gate / production assertions remain locked",
        "execution / no external action capability present",
        "evidence / implementation + independent verification still required"
      ];
      log.innerHTML = lines.map((line, i) => `<span class="cgsn-line" data-ok="${i < 2 ? "1" : "0"}">${line}</span>`).join("");
      nexus.querySelector("#cgsn-claims").textContent = String(Math.max(0, 4 - run)).padStart(2, "0");
    });

    threat.addEventListener("click", () => {
      const section = document.querySelector("#architecture");
      if (section) section.scrollIntoView({ behavior: reduceMotion.matches ? "auto" : "smooth", block: "start" });
      const first = section?.querySelector(".node");
      if (first) {
        first.animate?.([{boxShadow:"0 0 0 rgba(103,232,249,0)"},{boxShadow:"0 0 28px rgba(103,232,249,.38)"},{boxShadow:"0 0 0 rgba(103,232,249,0)"}], {duration:900});
      }
    });
  }

  function init() {
    document.documentElement.classList.add("future-glass-ready");
    discover();
    initShieldInterface();
    new MutationObserver(records => {
      for (const record of records) for (const node of record.addedNodes) if (node.nodeType === Node.ELEMENT_NODE) discover(node);
    }).observe(document.body, { childList: true, subtree: true });
    document.addEventListener("click", event => {
      const busyControl = event.target.closest?.("[aria-busy='true']");
      if (busyControl?.matches(SELECTOR)) { event.preventDefault(); event.stopImmediatePropagation(); }
    }, true);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
