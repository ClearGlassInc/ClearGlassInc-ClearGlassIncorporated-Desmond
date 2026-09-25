/** Neon pulse discovery: classes existing cards, panels, Sentinel modules and
 *  status dots for /assets/css/neon-pulse.css without touching their layout,
 *  page-owned pseudo-elements, stacking or events. Decorative only.
 *
 *  Every class this adds is in the cg-np- namespace. The layer only ever
 *  paints a pseudo-element it has claimed: cg-np-own-a (::after) or
 *  cg-np-own-b (::before), and only when that pseudo-element was free. */
(() => {
  "use strict";

  const root = document.documentElement;
  if (root.hasAttribute("data-no-neon") || !document.querySelectorAll) return;

  // Class tokens, matched whole or as a hyphenated suffix ("intel-card").
  const CARD = /(^|[-_])(card|tile)$/i;
  const PANEL = /(^|[-_])(panel|glass|glass-panel|pane)$/i;
  const MODULE = /(^|[-_])(module|console|sentinel)$/i;
  const HEADER = /(^|[-_])(t|title|head|header|hd|bar|top)$/i;
  const AUTHORED = /(^|\s)cg-np-(card|panel|module)(\s|$)/;
  // A status token on the dot, or a short status label beside it. A bare
  // "dot" class proves nothing: legends, orbits and window chrome use it too.
  const STATUS_TOKEN = /(^|[-_])(led|live|lv|beacon|status|signal|online|sync|indicator|heartbeat)([-_]|$)/i;
  const NOT_A_DOT = /(^|[-_])(port|handle|socket|knob|thumb|swatch|avatar|bullet|marker)([-_]|$)/i;
  const STATUS_TEXT = /\b(live|online|active|monitor(ing)?|status|alert|sync(ed|ing)?|secure|operational|ready|streaming|connected|armed|nominal|healthy)\b/i;
  const ALERT_TEXT = /(^|[-_\s])(alert|alarm|critical|danger|error|fail(ed|ure)?|offline|down|threat|breach|incident)([-_\s]|$)/i;
  const NOT_STATUS = "[role='tablist'],[role='tab'],[class*='pagination'],[class*='carousel'],[class*='slider'],[class*='swiper'],[class*='stepper'],[class*='progress'],[class*='rating'],[class*='avatar']";
  const SENTINEL_SCOPE = "[class*='sentinel'],[class*='command'],[data-sentinel]";
  const COMMAND_PAGE = /(sentinel|command|mission|guardian|aegis|percival|defender|console)/i.test(location.pathname);
  const SKIP_TAGS = /^(BUTTON|A|INPUT|SELECT|TEXTAREA|IMG|SVG|CANVAS|VIDEO|IFRAME|LABEL|OPTION)$/i;
  const MAX_FRAMES = 160;
  const MAX_BEACONS = 40;
  const MIN_SIZE = 72;

  const seen = new WeakSet();
  let frames = 0;
  let beacons = 0;
  let queued = false;
  let pending = [];
  let ambientChecked = false;

  const visibility = "IntersectionObserver" in window
    ? new IntersectionObserver((entries) => {
        for (const entry of entries) entry.target.classList.toggle("cg-np-live", entry.isIntersecting);
      }, { rootMargin: "80px 0px" })
    : null;

  function free(el, pseudo) {
    const content = getComputedStyle(el, pseudo).content;
    return !content || content === "none" || content === "normal";
  }

  // Marker classes added by enhancement layers (this one, ui.js's
  // cg-neon-card / cg-holo-shimmer, future-buttons) describe decoration, not
  // what an element is, so they never count as a card/panel signal.
  const LAYER_MARKER = /^(cg-np-|cg-neon-|cg-holo-|cg-signal-|future-glass)/;

  function tokens(el) {
    return (typeof el.className === "string" ? el.className : "").split(/\s+/).filter((t) => t && !LAYER_MARKER.test(t));
  }

  function clips(style) {
    return /(hidden|clip)/.test(style.overflowX) && /(hidden|clip)/.test(style.overflowY);
  }

  // Positioned already, or static where position:relative is provably inert:
  // no offsets start applying and no absolutely positioned descendant changes
  // containing block. No z-index is ever set, so no stacking context appears.
  function anchorable(el, style) {
    if (style.position !== "static") return true;
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

  function kindOf(el) {
    const match = typeof el.className === "string" && el.className.match(AUTHORED);
    if (match) return match[2];
    let kind = "";
    for (const token of tokens(el)) {
      if (MODULE.test(token) || el.hasAttribute("data-sentinel-module")) return "module";
      if (PANEL.test(token)) kind = kind || "panel";
      if (CARD.test(token)) kind = "card";
    }
    const scope = kind && el.closest(SENTINEL_SCOPE);
    if (kind === "card" && scope && scope !== el) return "module";
    if (kind === "panel" && COMMAND_PAGE) return "module";
    return kind;
  }

  function claimedBy(el, planned) {
    for (let node = el.parentElement; node; node = node.parentElement) {
      if (planned.has(node) || node.classList.contains("cg-np-frame")) return true;
    }
    return false;
  }

  // ---- read phase: decide everything before writing a single class --------

  function planFrame(el, planned, plan) {
    const kind = kindOf(el);
    if (!kind) return;
    seen.add(el);
    const authored = AUTHORED.test(el.className);
    const style = getComputedStyle(el);
    if (!authored) {
      if (el === document.body || el === root || SKIP_TAGS.test(el.tagName)) return;
      if (el.classList.contains("future-glass-control") || claimedBy(el, planned)) return;
      if (style.display === "contents" || style.display === "inline") return;
      const rect = el.getBoundingClientRect();
      if (rect.width < MIN_SIZE || rect.height < MIN_SIZE || rect.height > innerHeight * 2.5) return;
      if (!anchorable(el, style)) return;
    }
    const freeA = free(el, "::after");
    const freeB = free(el, "::before");
    const classes = ["cg-np-frame", "cg-np-" + kind, "cg-np-d" + (frames % 4)];
    if (style.position === "static") classes.push("cg-np-anchor");

    if (freeA) {
      classes.push("cg-np-rim-a", "cg-np-own-a");
      const clipped = clips(style);
      if (freeB) {
        if (kind === "card") classes.push("cg-np-corners", "cg-np-own-b");
        else if (kind === "panel" && clipped) classes.push("cg-np-reflect", "cg-np-own-b");
        else if (kind === "module" && clipped) classes.push("cg-np-scan", "cg-np-own-b");
      }
    } else if (freeB) {
      classes.push("cg-np-rim-b", "cg-np-own-b");
    } else {
      // The page already decorates both pseudo-elements (ui.css's neon card
      // does on the Sentinel console). A module can still carry a scanning
      // edge on its header bar; the sweep is horizontal, so the module has to
      // clip on the x axis.
      if (kind === "module" && /(hidden|clip)/.test(style.overflowX)) planScanbar(el, planned, plan);
      return;
    }
    planned.add(el);
    plan.push([el, classes]);
    frames += 1;
  }

  function planScanbar(module, planned, plan) {
    const header = Array.prototype.find.call(module.children, (child) =>
      /^(H[1-6]|HEADER)$/.test(child.tagName) || tokens(child).some((t) => HEADER.test(t)));
    if (!header || seen.has(header)) return;
    seen.add(header);
    const style = getComputedStyle(header);
    if (style.display === "contents" || style.display === "inline") return;
    if (header.getBoundingClientRect().width < 120 || !free(header, "::after") || !anchorable(header, style)) return;
    const classes = ["cg-np-frame", "cg-np-scanbar", "cg-np-own-a", "cg-np-d" + (frames % 4)];
    if (style.position === "static") classes.push("cg-np-anchor");
    planned.add(module);
    plan.push([header, classes]);
    frames += 1;
  }

  // A status dot: a small, round, filled, childless, text-free element whose
  // name or label says it reports state, that is not already animated and is
  // not a control, pager or carousel dot. Its halo inherits the dot's own
  // colour, so green stays green and red stays red.
  function planBeacon(el, plan) {
    if (el.childElementCount || SKIP_TAGS.test(el.tagName) || el.hasAttribute("tabindex")) return;
    if ((el.textContent || "").trim()) return;
    const names = tokens(el);
    if (names.some((t) => NOT_A_DOT.test(t))) return;
    const label = el.parentElement ? (el.parentElement.textContent || "").trim() : "";
    const labelled = label.length <= 80 && STATUS_TEXT.test(label);
    if (!names.some((t) => STATUS_TOKEN.test(t)) && !labelled) return;
    if (el.closest(NOT_STATUS)) return;
    seen.add(el);
    const rect = el.getBoundingClientRect();
    if (rect.width < 4 || rect.width > 18 || Math.abs(rect.width - rect.height) > 2) return;
    const style = getComputedStyle(el);
    if (style.animationName !== "none" || parseFloat(style.borderTopLeftRadius) < rect.width * .4) return;
    const rgb = (style.backgroundColor.match(/[\d.]+/g) || []).map(Number);
    if (rgb.length < 3 || rgb[3] === 0) return;
    if (!free(el, "::after") || !anchorable(el, style)) return;
    const classes = ["cg-np-beacon", "cg-np-own-a"];
    const pace = tone(rgb, names.join(" ") + " " + (label.length <= 80 ? label : ""));
    if (pace) classes.push("cg-np-beacon--" + pace);
    if (style.position === "static") classes.push("cg-np-anchor");
    plan.push([el, classes]);
    beacons += 1;
  }

  // Tempo only. Alert pace comes from words, never from hue: the brand accent
  // is red, so a red dot is usually decoration, not an alarm.
  function tone([r, g, b], words) {
    if (ALERT_TEXT.test(words)) return "alert";
    if (g > r + 30 && g >= b - 20) return "online";
    if (r > 150 && g > 90 && b < 90 && g < r) return "monitoring";
    if (b > r + 30 && b >= g - 40) return "intel";
    return "";
  }

  function plan(scope) {
    const out = [];
    const planned = new Set();
    const nodes = scope.querySelectorAll ? scope.querySelectorAll("[class],[data-sentinel-module]") : [];
    const list = scope.nodeType === 1 && scope.hasAttribute("class") ? [scope, ...nodes] : nodes;
    for (const el of list) {
      if (seen.has(el) || el.closest(".cg-np-ambient,[data-no-neon]")) continue;
      if (frames < MAX_FRAMES) planFrame(el, planned, out);
      if (beacons < MAX_BEACONS && !seen.has(el)) planBeacon(el, out);
    }
    return out;
  }

  // ---- write phase ----------------------------------------------------------

  function apply(decisions) {
    for (const [el, classes] of decisions) {
      el.classList.add(...classes);
      if (visibility) visibility.observe(el);
      else el.classList.add("cg-np-live");
    }
  }

  function ambient() {
    ambientChecked = true;
    // ui.js already paints a command atmosphere (grid + drift) on its pages;
    // a second grid would double up rather than add.
    if (document.querySelector(".cg-np-ambient,#cg-command-atmosphere")) return;
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

  function flush() {
    queued = false;
    if (!ambientChecked) ambient();
    const batch = pending;
    pending = [];
    const decisions = [];
    for (const node of batch) if (node.isConnected) decisions.push(...plan(node));
    apply(decisions);
  }

  function schedule(node) {
    pending.push(node);
    if (queued) return;
    queued = true;
    (window.requestIdleCallback || ((fn) => setTimeout(fn, 120)))(flush, { timeout: 800 });
  }

  function start() {
    if (!document.body || document.body.hasAttribute("data-no-neon")) return;
    schedule(document.body);
    if (!("MutationObserver" in window)) return;
    const mutations = new MutationObserver((records) => {
      if (frames >= MAX_FRAMES && beacons >= MAX_BEACONS) { mutations.disconnect(); return; }
      for (const record of records) {
        for (const node of record.addedNodes) {
          if (node.nodeType === 1 && !node.classList.contains("cg-np-ambient")) schedule(node);
        }
      }
    });
    mutations.observe(document.body, { childList: true, subtree: true });
    addEventListener("pagehide", (event) => {
      if (event.persisted) return;
      mutations.disconnect();
      if (visibility) visibility.disconnect();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
