/** Neon pulse discovery: classes existing cards, panels and Sentinel modules
 *  for /assets/css/neon-pulse.css without touching their layout, pseudo
 *  elements, stacking or events. Decorative only; safe to remove. */
(() => {
  "use strict";

  const root = document.documentElement;
  if (root.hasAttribute("data-no-neon") || !document.querySelectorAll) return;

  // Class tokens, matched whole or as a hyphenated suffix ("intel-card").
  const CARD = /(^|[-_])(card|tile)$/i;
  const PANEL = /(^|[-_])(panel|glass|glass-panel|pane)$/i;
  const MODULE = /(^|[-_])(module|console|sentinel)$/i;
  const SENTINEL_SCOPE = "[class*='sentinel'],[class*='command'],[data-sentinel]";
  const MAX_ENHANCED = 160;
  const MIN_SIZE = 72;

  const seen = new WeakSet();
  let enhanced = 0;
  let queued = false;
  let pending = [];

  function freePseudo(el, pseudo) {
    const content = getComputedStyle(el, pseudo).content;
    return !content || content === "none" || content === "normal";
  }

  function kindOf(el) {
    const tokens = (typeof el.className === "string" ? el.className : "").split(/\s+/);
    let kind = "";
    for (const token of tokens) {
      if (!token || token.startsWith("cg-np-")) continue;
      if (MODULE.test(token) || el.hasAttribute("data-sentinel-module")) return "module";
      if (PANEL.test(token)) kind = kind || "panel";
      if (CARD.test(token)) kind = "card";
    }
    if (kind === "card" && el.closest(SENTINEL_SCOPE) && el.closest(SENTINEL_SCOPE) !== el) {
      return "module";
    }
    return kind;
  }

  function eligible(el) {
    if (seen.has(el)) return false;
    seen.add(el);
    if (el === document.body || el === root || el.closest("[data-no-neon]")) return false;
    if (/^(BUTTON|A|INPUT|SELECT|TEXTAREA|IMG|SVG|CANVAS|VIDEO|IFRAME|LABEL)$/i.test(el.tagName)) return false;
    if (el.classList.contains("future-glass-control")) return false;
    // An enhanced ancestor already frames this region.
    const parent = el.parentElement && el.parentElement.closest(".cg-np-card,.cg-np-panel,.cg-np-module");
    if (parent) return false;
    const rect = el.getBoundingClientRect();
    if (rect.width < MIN_SIZE || rect.height < MIN_SIZE) return false;
    if (rect.height > innerHeight * 2.5) return false;
    const style = getComputedStyle(el);
    if (style.display === "contents" || style.display === "inline") return false;
    if (style.position === "static" && !canAnchor(el, style)) return false;
    return freePseudo(el, "::after");
  }

  // A static element may take position:relative only when that is inert: no
  // offsets would start applying and no absolutely positioned descendant
  // would change containing block. No z-index is set, so no stacking context.
  function canAnchor(el, style) {
    for (const side of ["top", "right", "bottom", "left"]) {
      if (style[side] !== "auto") return false;
    }
    const descendants = el.getElementsByTagName("*");
    if (descendants.length > 400) return false;
    for (const child of descendants) {
      if (getComputedStyle(child).position === "absolute") return false;
    }
    return true;
  }

  function enhance(el) {
    const kind = kindOf(el);
    if (!kind || !eligible(el)) return;
    const clipped = /(hidden|clip)/.test(getComputedStyle(el).overflow);
    const extras = ["cg-np-" + kind, "cg-np-d" + (enhanced % 4)];
    if (getComputedStyle(el).position === "static") extras.push("cg-np-anchor");
    if (freePseudo(el, "::before")) {
      if (kind === "card") extras.push("cg-np-corners");
      else if (kind === "panel" && clipped) extras.push("cg-np-reflect");
      else if (kind === "module" && clipped) extras.push("cg-np-scan");
    }
    el.classList.add(...extras);
    enhanced += 1;
    visibility && visibility.observe(el);
  }

  const visibility = "IntersectionObserver" in window
    ? new IntersectionObserver((entries) => {
        for (const entry of entries) entry.target.classList.toggle("cg-np-live", entry.isIntersecting);
      }, { rootMargin: "80px 0px" })
    : null;

  function scan(scope) {
    const nodes = scope.querySelectorAll ? scope.querySelectorAll("[class],[data-sentinel-module]") : [];
    const list = scope.nodeType === 1 && scope.hasAttribute("class") ? [scope, ...nodes] : nodes;
    for (const el of list) {
      if (enhanced >= MAX_ENHANCED) return;
      enhance(el);
    }
  }

  function flush() {
    queued = false;
    const batch = pending;
    pending = [];
    for (const node of batch) if (node.isConnected) scan(node);
  }

  function schedule(node) {
    pending.push(node);
    if (queued) return;
    queued = true;
    (window.requestIdleCallback || ((fn) => setTimeout(fn, 120)))(flush, { timeout: 800 });
  }

  function ambient() {
    if (document.querySelector(".cg-np-ambient")) return;
    const layer = document.createElement("div");
    layer.className = "cg-np-ambient";
    layer.setAttribute("aria-hidden", "true");
    for (const part of ["cg-np-grid", "cg-np-sweep", "cg-np-breath"]) {
      const span = document.createElement("span");
      span.className = part;
      layer.appendChild(span);
    }
    document.body.appendChild(layer);
  }

  function start() {
    if (!document.body || document.body.hasAttribute("data-no-neon")) return;
    ambient();
    schedule(document.body);
    if ("MutationObserver" in window) {
      const mutations = new MutationObserver((records) => {
        if (enhanced >= MAX_ENHANCED) { mutations.disconnect(); return; }
        for (const record of records) {
          for (const node of record.addedNodes) {
            if (node.nodeType === 1 && !node.classList.contains("cg-np-ambient")) schedule(node);
          }
        }
      });
      mutations.observe(document.body, { childList: true, subtree: true });
      addEventListener("pagehide", (event) => {
        if (!event.persisted) { mutations.disconnect(); visibility && visibility.disconnect(); }
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
