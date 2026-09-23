/* ClearGlass · Station Enhance (search, repositionable dock, keyboard access)
   ────────────────────────────────────────────────────────────────────────────
   Three additions layered on top of the existing Station surfaces. Strictly
   additive: it creates its own nodes, owns its own state, and never rewrites
   markup that sentinel.js or station-chat.js already manages.

     1. Directory search — the Station panel's destination grid gets a live
        filter: substring + initials matching, ranked, with the matched run
        highlighted, arrow-key navigation and an aria-live result count.
     2. Repositionable dock — the bottom-right Control Station bar can be
        dragged anywhere on screen and remembers where it was left. Dragging is
        also available from the keyboard, and a double-click resets it.
     3. Keyboard access — Ctrl/Cmd+K opens the Station, "/" focuses the search.

   Highlighting builds text nodes rather than assigning innerHTML, so a query is
   never interpreted as markup - the same rule sentinel.js follows with
   copy.textContent for chat messages.

   No backend, no network request, no tracking, no dependencies, no build step. */
(function () {
  "use strict";
  if (window.__cgStationEnhance) return;
  window.__cgStationEnhance = true;

  var POS_KEY = "cg-station-pos";
  var DRAG_THRESHOLD = 4;      // px of travel before a press becomes a drag
  var EDGE = 8;                // keep this much of a gap to the viewport edge
  var reduce = false;
  try { reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}

  // ── styles ───────────────────────────────────────────────────────────────
  var CSS = [
    ".cg-se-search{position:relative;margin:0 0 14px}",
    ".cg-se-field{display:flex;align-items:center;gap:10px;padding:11px 13px;border-radius:13px;",
    "border:1px solid rgba(238,99,101,.38);background:linear-gradient(168deg,rgba(44,24,26,.92),rgba(18,12,13,.95));",
    "box-shadow:inset 0 1px 0 rgba(255,255,255,.07);transition:border-color .2s ease,box-shadow .2s ease}",
    ".cg-se-field:focus-within{border-color:rgba(238,99,101,.85);box-shadow:0 0 0 3px rgba(238,99,101,.22)}",
    ".cg-se-field svg{width:17px;height:17px;flex:0 0 auto;color:#c08c8e}",
    ".cg-se-input{flex:1;min-width:0;background:none;border:0;outline:0;color:#f7f1f1;font:600 14px/1.4 Inter,system-ui,sans-serif}",
    ".cg-se-input::placeholder{color:#8d6467}",
    ".cg-se-clear{flex:0 0 auto;width:22px;height:22px;border-radius:7px;border:1px solid rgba(238,99,101,.34);",
    "background:rgba(238,99,101,.12);color:#f7f1f1;font:700 13px/1 Inter,system-ui,sans-serif;cursor:pointer;display:none}",
    ".cg-se-clear:hover{background:rgba(238,99,101,.26)}",
    ".cg-se-search[data-filled='1'] .cg-se-clear{display:block}",
    ".cg-se-count{margin:7px 2px 0;font:600 11px/1.3 'IBM Plex Mono',ui-monospace,monospace;letter-spacing:.08em;color:#c08c8e}",
    ".cg-se-hit{color:#ffd9da;background:rgba(238,99,101,.26);border-radius:3px;padding:0 1px}",
    ".cg-station-item[hidden]{display:none!important}",
    ".cg-station-item.cg-se-active{outline:2px solid rgba(238,99,101,.9);outline-offset:2px}",
    ".cg-se-empty{padding:16px 13px;border-radius:12px;border:1px dashed rgba(238,99,101,.32);",
    "color:#c08c8e;font:600 13px/1.5 Inter,system-ui,sans-serif}",
    /* dock drag affordances */
    "#cg-station[data-cg-moved='1']{right:auto;bottom:auto}",
    "#cg-station .cg-se-grip{cursor:grab;touch-action:none}",
    "#cg-station[data-cg-dragging='1'],#cg-station[data-cg-dragging='1'] .cg-se-grip{cursor:grabbing;user-select:none}",
    "#cg-station[data-cg-dragging='1']{opacity:.96" + (reduce ? "" : ";transition:none") + "}",
    ".cg-se-reset{position:absolute;top:-9px;left:-9px;width:22px;height:22px;border-radius:50%;z-index:5;",
    "border:1px solid rgba(238,99,101,.5);background:#2a1618;color:#f7f1f1;font:700 12px/1 Inter,sans-serif;",
    "cursor:pointer;display:none;align-items:center;justify-content:center;padding:0}",
    "#cg-station[data-cg-moved='1'] .cg-se-reset{display:flex}",
    /* station-chat.js hides the dock while the Sentinel modal is open, but
       #cg-station[data-open='true'] .cgst-panel re-asserts visibility:visible on
       the child, so the dock panel kept floating over the modal and swallowing
       clicks (visibility is overridable by descendants; opacity:0 alone still
       hit-tests). Re-hide the subtree explicitly. */
    "body.sentinel-open #cg-station,body.sentinel-open #cg-station .cgst-panel,"+
    "body.sentinel-open #cg-station .cgst-dock{visibility:hidden!important;pointer-events:none!important}",
    ".cg-se-sr{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}"
  ].join("");

  function injectCSS() {
    if (document.getElementById("cg-se-css")) return;
    var tag = document.createElement("style");
    tag.id = "cg-se-css";
    tag.textContent = CSS;
    (document.head || document.documentElement).appendChild(tag);
  }

  var IC_SEARCH = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<circle cx="11" cy="11" r="6.4" stroke="currentColor" stroke-width="1.8"/>' +
    '<path d="m15.8 15.8 4 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>';

  // ── matching ─────────────────────────────────────────────────────────────
  // Returns null for no match, else {score, field, start, end} describing the
  // best run to highlight. Lower score sorts first.
  function match(query, title, sub, code) {
    var q = query.toLowerCase();
    var t = title.toLowerCase();
    var s = sub.toLowerCase();

    if (code.toLowerCase() === q) return { score: 0, field: "title", start: -1, end: -1 };

    var i = t.indexOf(q);
    if (i === 0) return { score: 1, field: "title", start: i, end: i + q.length };
    if (i > 0) return { score: 2, field: "title", start: i, end: i + q.length };

    // initials: "cc" matches "Command Center"
    var initials = title.split(/\s+/).map(function (w) { return w.charAt(0); }).join("").toLowerCase();
    if (initials.indexOf(q) === 0) return { score: 3, field: "title", start: -1, end: -1 };

    var j = s.indexOf(q);
    if (j >= 0) return { score: 4, field: "sub", start: j, end: j + q.length };

    return null;
  }

  // Rebuilds an element's text with the matched run wrapped, using DOM nodes so
  // the query can never be parsed as markup.
  function paint(el, text, start, end) {
    el.replaceChildren();
    if (start < 0 || end <= start) { el.textContent = text; return; }
    el.appendChild(document.createTextNode(text.slice(0, start)));
    var mark = document.createElement("span");
    mark.className = "cg-se-hit";
    mark.textContent = text.slice(start, end);
    el.appendChild(mark);
    el.appendChild(document.createTextNode(text.slice(end)));
  }

  // ── directory search ─────────────────────────────────────────────────────
  function enhanceGrid(grid) {
    if (!grid || grid.__cgSE) return;
    grid.__cgSE = true;
    injectCSS();

    var items = Array.prototype.slice.call(grid.querySelectorAll(".cg-station-item"));
    if (!items.length) return;

    // Snapshot the original text once; filtering repaints from this, never from
    // the (possibly already highlighted) live DOM.
    var rows = items.map(function (el) {
      var strong = el.querySelector("strong");
      var small = el.querySelector("small");
      var code = el.querySelector(".cg-station-code");
      return {
        el: el, strong: strong, small: small,
        title: strong ? strong.textContent : "",
        sub: small ? small.textContent : "",
        code: code ? code.textContent : ""
      };
    });

    var wrap = document.createElement("div");
    wrap.className = "cg-se-search";
    wrap.innerHTML =
      '<div class="cg-se-field">' + IC_SEARCH +
      '<input class="cg-se-input" type="search" autocomplete="off" spellcheck="false" ' +
      'placeholder="Search destinations — try a name, a code, or initials" ' +
      'aria-label="Search ClearGlass Station destinations">' +
      '<button type="button" class="cg-se-clear" aria-label="Clear search">&times;</button></div>' +
      '<p class="cg-se-count" role="status" aria-live="polite"></p>';

    var empty = document.createElement("p");
    empty.className = "cg-se-empty";
    empty.hidden = true;

    grid.parentNode.insertBefore(wrap, grid);
    grid.parentNode.insertBefore(empty, grid.nextSibling);

    var input = wrap.querySelector(".cg-se-input");
    var clear = wrap.querySelector(".cg-se-clear");
    var count = wrap.querySelector(".cg-se-count");
    var active = -1;
    var visible = rows.slice();

    function setActive(next) {
      if (active >= 0 && visible[active]) visible[active].el.classList.remove("cg-se-active");
      active = next;
      if (active >= 0 && visible[active]) {
        visible[active].el.classList.add("cg-se-active");
        visible[active].el.scrollIntoView({ block: "nearest" });
      }
    }

    function apply() {
      var q = input.value.trim();
      wrap.dataset.filled = q ? "1" : "0";
      setActive(-1);

      if (!q) {
        rows.forEach(function (r) {
          r.el.hidden = false;
          if (r.strong) r.strong.textContent = r.title;
          if (r.small) r.small.textContent = r.sub;
          grid.appendChild(r.el);          // restore the authored order
        });
        visible = rows.slice();
        empty.hidden = true;
        count.textContent = rows.length + " DESTINATIONS";
        return;
      }

      var hits = [];
      rows.forEach(function (r) {
        var m = match(q, r.title, r.sub, r.code);
        if (!m) { r.el.hidden = true; return; }
        r.el.hidden = false;
        if (r.strong) paint(r.strong, r.title, m.field === "title" ? m.start : -1, m.field === "title" ? m.end : -1);
        if (r.small) paint(r.small, r.sub, m.field === "sub" ? m.start : -1, m.field === "sub" ? m.end : -1);
        hits.push({ row: r, score: m.score });
      });

      hits.sort(function (a, b) { return a.score - b.score; });
      hits.forEach(function (h) { grid.appendChild(h.row.el); });   // best match first
      visible = hits.map(function (h) { return h.row; });

      empty.hidden = hits.length > 0;
      if (!hits.length) empty.textContent = 'No destination matches "' + q + '". Try a shorter word.';
      count.textContent = hits.length
        ? hits.length + (hits.length === 1 ? " MATCH" : " MATCHES") + " · ↑↓ TO MOVE · ENTER TO OPEN"
        : "NO MATCHES";
      if (hits.length) setActive(0);
    }

    input.addEventListener("input", apply);
    clear.addEventListener("click", function () { input.value = ""; apply(); input.focus(); });

    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        if (!visible.length) return;
        e.preventDefault();
        var next = active + (e.key === "ArrowDown" ? 1 : -1);
        if (next < 0) next = visible.length - 1;
        if (next >= visible.length) next = 0;
        setActive(next);
      } else if (e.key === "Enter") {
        if (active >= 0 && visible[active]) { e.preventDefault(); visible[active].el.click(); }
      } else if (e.key === "Escape") {
        if (input.value) { e.stopPropagation(); input.value = ""; apply(); }
      }
    });

    apply();
    try { input.focus({ preventScroll: true }); } catch (err) { input.focus(); }
  }

  // ── repositionable dock ──────────────────────────────────────────────────
  function clamp(v, min, max) { return v < min ? min : v > max ? max : v; }

  function enhanceDock(dock) {
    if (!dock || dock.__cgSE) return;
    dock.__cgSE = true;
    injectCSS();

    // Grips are the panel header and the collapsed dock bar - never the whole
    // aside: making the root a grip would swallow every row inside it.
    var grips = [];
    ["#cgStationPanel .cgst-head", ".cgst-head", "#cgStationDock", ".cgst-dock"].forEach(function (sel) {
      var el = dock.querySelector(sel);
      if (el && grips.indexOf(el) < 0) grips.push(el);
    });
    if (!grips.length) return;                 // unknown markup: leave it alone
    grips.forEach(function (g) { g.classList.add("cg-se-grip"); });
    var grip = grips[0];                       // the one that takes keyboard focus

    function place(x, y) {
      var w = dock.offsetWidth, h = dock.offsetHeight;
      x = clamp(x, EDGE, Math.max(EDGE, window.innerWidth - w - EDGE));
      y = clamp(y, EDGE, Math.max(EDGE, window.innerHeight - h - EDGE));
      dock.dataset.cgMoved = "1";
      dock.style.left = x + "px";
      dock.style.top = y + "px";
      return { x: x, y: y };
    }

    function save(pos) { try { localStorage.setItem(POS_KEY, JSON.stringify(pos)); } catch (e) {} }

    function reset() {
      delete dock.dataset.cgMoved;
      dock.style.left = dock.style.top = "";
      try { localStorage.removeItem(POS_KEY); } catch (e) {}
      announce("Dock position reset");
    }

    var live = document.createElement("span");
    live.className = "cg-se-sr";
    live.setAttribute("role", "status");
    live.setAttribute("aria-live", "polite");
    dock.appendChild(live);
    function announce(msg) { live.textContent = msg; }

    var resetBtn = document.createElement("button");
    resetBtn.type = "button";
    resetBtn.className = "cg-se-reset";
    resetBtn.innerHTML = "&times;";
    resetBtn.title = "Reset dock position";
    resetBtn.setAttribute("aria-label", "Reset dock to its default position");
    resetBtn.addEventListener("click", function (e) { e.stopPropagation(); reset(); });
    dock.appendChild(resetBtn);

    // restore a saved position
    try {
      var saved = JSON.parse(localStorage.getItem(POS_KEY) || "null");
      if (saved && typeof saved.x === "number" && typeof saved.y === "number") place(saved.x, saved.y);
    } catch (e) {}

    var dragging = false, moved = false, sx = 0, sy = 0, ox = 0, oy = 0, pid = null;

    grips.forEach(function (g) { g.addEventListener("pointerdown", function (e) {
      if (e.button !== 0 && e.pointerType === "mouse") return;
      // never hijack a press that belongs to a control inside the bar
      if (e.target.closest("a,button,input,textarea,select") && e.target !== grip) return;
      var box = dock.getBoundingClientRect();
      dragging = true; moved = false; pid = e.pointerId;
      sx = e.clientX; sy = e.clientY; ox = box.left; oy = box.top;
    }); });

    window.addEventListener("pointermove", function (e) {
      if (!dragging || (pid !== null && e.pointerId !== pid)) return;
      var dx = e.clientX - sx, dy = e.clientY - sy;
      if (!moved && Math.abs(dx) + Math.abs(dy) < DRAG_THRESHOLD) return;
      if (!moved) { moved = true; dock.dataset.cgDragging = "1"; }
      e.preventDefault();
      place(ox + dx, oy + dy);
    }, { passive: false });

    function endDrag() {
      if (!dragging) return;
      dragging = false;
      delete dock.dataset.cgDragging;
      if (moved) {
        var box = dock.getBoundingClientRect();
        save({ x: box.left, y: box.top });
        announce("Dock moved. Press Escape on the handle to reset.");
      }
      moved = false; pid = null;
    }
    window.addEventListener("pointerup", endDrag);
    window.addEventListener("pointercancel", endDrag);

    // A click that followed a drag must not also activate the bar underneath.
    grips.forEach(function (g) { g.addEventListener("click", function (e) {
      if (dock.__cgSuppressClick) { e.stopPropagation(); e.preventDefault(); dock.__cgSuppressClick = false; }
    }, true); });
    window.addEventListener("pointerup", function () {
      if (moved) dock.__cgSuppressClick = true;
    }, true);

    grips.forEach(function (g) { g.addEventListener("dblclick", reset); });

    // keyboard: arrows nudge, shift+arrows jump, Escape resets
    grip.tabIndex = grip.tabIndex >= 0 ? grip.tabIndex : 0;
    grip.addEventListener("keydown", function (e) {
      var step = e.shiftKey ? 32 : 8, box = dock.getBoundingClientRect(), nx = null, ny = null;
      if (e.key === "ArrowLeft") { nx = box.left - step; ny = box.top; }
      else if (e.key === "ArrowRight") { nx = box.left + step; ny = box.top; }
      else if (e.key === "ArrowUp") { nx = box.left; ny = box.top - step; }
      else if (e.key === "ArrowDown") { nx = box.left; ny = box.top + step; }
      else if (e.key === "Escape" && dock.dataset.cgMoved === "1") { e.preventDefault(); reset(); return; }
      else return;
      e.preventDefault();
      save(place(nx, ny));
    });

    // keep it on screen when the viewport changes
    window.addEventListener("resize", function () {
      if (dock.dataset.cgMoved !== "1") return;
      var box = dock.getBoundingClientRect();
      save(place(box.left, box.top));
    });
  }

  // ── wiring ───────────────────────────────────────────────────────────────
  function scan() {
    var grid = document.querySelector(".cg-station-grid");
    if (grid) enhanceGrid(grid);
    var dock = document.getElementById("cg-station");
    if (dock) enhanceDock(dock);
  }

  function start() {
    scan();
    // Both surfaces are built by other scripts after load, and the Station panel
    // is rebuilt each time it opens, so watch for them rather than racing them.
    try {
      new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
    } catch (e) {}

    document.addEventListener("keydown", function (e) {
      var key = (e.key || "").toLowerCase();
      if ((e.metaKey || e.ctrlKey) && key === "k") {
        // the real opener is the button inside the launcher wrapper: clicking the
        // wrapper alone reaches the Station handler but never opens the shell.
        var opener = document.querySelector("[data-sentinel-open]") || document.getElementById("sentinelLauncher");
        if (opener) { e.preventDefault(); opener.click(); }
        return;
      }
      if (key === "/" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        var tag = (document.activeElement && document.activeElement.tagName || "").toLowerCase();
        if (tag === "input" || tag === "textarea" || tag === "select") return;
        if (document.activeElement && document.activeElement.isContentEditable) return;
        var box = document.querySelector(".cg-se-input");
        if (box) { e.preventDefault(); box.focus(); }
      }
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
}());
