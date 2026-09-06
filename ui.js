/* ClearGlass · advanced interaction behaviors. Self-contained, dependency-free,
   non-breaking. Pairs with ui.css. Drop in with <script defer src="ui.js"></script>.

   Adds three real, tasteful micro-interactions:
     1) click ripple on buttons (Material-style, positioned at the pointer)
     2) subtle magnetic pull on buttons toward the cursor
     3) an ambient pointer spotlight (very low-opacity blue-violet glow)

   Everything is feature-gated: disabled under prefers-reduced-motion and on
   coarse/touch pointers (except the ripple, which stays for tap feedback).
   Uses event delegation so it costs nothing on elements you never touch, and it
   never restyles colors or clobbers existing pseudo-elements. */
(function () {
  "use strict";
  if (window.__cgUiLoaded) return;
  window.__cgUiLoaded = true;

  var SEL = 'button,.btn,.cta,.button,.cg-btn,[role="button"],a.btn,a.cta,a.button,a.cg-btn,input[type="submit"],input[type="button"]';
  var reduce = false, finePointer = true;
  try {
    reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  } catch (e) {}

  function isControl(node) {
    if (!node || !node.closest) return null;
    var el = node.closest(SEL);
    if (!el) return null;
    if (el.closest("#cg-nav")) return null;          // nav manages itself
    if (el.disabled || el.getAttribute("aria-disabled") === "true") return null;
    return el;
  }

  /* ── 1) ripple ──────────────────────────────────────────────────────────── */
  function ripple(e) {
    if (reduce) return;
    var el = isControl(e.target);
    if (!el) return;
    var cs = getComputedStyle(el);
    if (cs.position === "static") el.style.position = "relative";
    if (cs.overflow === "visible") el.style.overflow = "hidden";
    var r = el.getBoundingClientRect();
    var size = Math.max(r.width, r.height);
    var x = (e.clientX != null ? e.clientX : r.left + r.width / 2) - r.left;
    var y = (e.clientY != null ? e.clientY : r.top + r.height / 2) - r.top;
    var s = document.createElement("span");
    s.className = "cg-ripple";
    s.style.width = s.style.height = size + "px";
    s.style.left = (x - size / 2) + "px";
    s.style.top = (y - size / 2) + "px";
    el.appendChild(s);
    var done = function () { if (s.parentNode) s.parentNode.removeChild(s); };
    s.addEventListener("animationend", done);
    setTimeout(done, 800);                            // safety net
  }
  document.addEventListener("pointerdown", ripple, { passive: true });

  /* ── 2) magnetic pull ───────────────────────────────────────────────────── */
  var MAG = 5;                                        // max px displacement
  function bindMagnet(el) {
    if (el.__cgMag) return;
    el.__cgMag = true;
    el.classList.add("cg-magnetic");
    var raf = 0, tx = 0, ty = 0;
    function apply() { raf = 0; el.style.transform = "translate(" + tx + "px," + (ty - 2) + "px)"; }
    el.addEventListener("pointermove", function (e) {
      var r = el.getBoundingClientRect();
      var dx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
      var dy = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
      tx = Math.max(-1, Math.min(1, dx)) * MAG;
      ty = Math.max(-1, Math.min(1, dy)) * MAG;
      if (!raf) raf = requestAnimationFrame(apply);
    });
    el.addEventListener("pointerleave", function () {
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
      el.style.transform = "";
    });
  }
  if (finePointer && !reduce) {
    document.addEventListener("pointerover", function (e) {
      var el = isControl(e.target);
      if (el) bindMagnet(el);
    }, { passive: true });
  }

  /* ── 3) ambient pointer spotlight ───────────────────────────────────────── */
  if (finePointer && !reduce) {
    var build = function () {
      if (document.getElementById("cg-spotlight")) return;
      var spot = document.createElement("div");
      spot.id = "cg-spotlight";
      document.body.appendChild(spot);
      var raf = 0, x = -100, y = -100;
      var paint = function () { raf = 0; spot.style.setProperty("--cg-x", x + "px"); spot.style.setProperty("--cg-y", y + "px"); };
      window.addEventListener("pointermove", function (e) {
        x = e.clientX; y = e.clientY;
        spot.style.opacity = "1";
        if (!raf) raf = requestAnimationFrame(paint);
      }, { passive: true });
      window.addEventListener("pointerleave", function () { spot.style.opacity = "0"; });
    };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", build);
    } else { build(); }
  }

  /* ── 4) command atmosphere + additive neon classification ──────────────── */
  function buildCommandLayer() {
    if (document.getElementById("cg-command-atmosphere")) return;
    var layer = document.createElement("div");
    layer.id = "cg-command-atmosphere";
    layer.className = "cg-command-atmosphere";
    layer.setAttribute("aria-hidden", "true");
    document.body.insertBefore(layer, document.body.firstChild);

    var cards = document.querySelectorAll('.card,.panel,.tile,.tech-card,.product-card,.connect-card,.value-card,.founder-card,.credentials-card,.signup-card,.catalog-card,.dcard,.console,.stat,.stat-card,.metric,.kpi,.feature-card,.data-panel');
    cards.forEach(function (el) { el.classList.add("cg-neon-card"); });

    var focal = document.querySelectorAll('.btn-crystal,.nav-cta,.primary-btn,.btn-dark,.cta-primary,.primary,.hero-actions .btn:first-child');
    focal.forEach(function (el) { el.classList.add("cg-neon-action"); });

    var labels = document.querySelectorAll('.sh-tag,.eyebrow,.badge,.pill,.chip,.pc-era,.hero-year');
    labels.forEach(function (el) { el.classList.add("cg-holo-shimmer"); });

    var statusLabels = document.querySelectorAll('.is-active,.active,[aria-current="page"],.clive,.status-live,.live,.online');
    statusLabels.forEach(function (el) { el.classList.add("cg-signal-active"); });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildCommandLayer);
  } else { buildCommandLayer(); }

  if (finePointer && !reduce) {
    window.addEventListener("pointermove", function (e) {
      var layer = document.getElementById("cg-command-atmosphere");
      if (!layer) return;
      layer.style.setProperty("--cg-orbit-x", Math.round((e.clientX / Math.max(1, window.innerWidth)) * 100) + "%");
      layer.style.setProperty("--cg-orbit-y", Math.round((e.clientY / Math.max(1, window.innerHeight)) * 100) + "%");
    }, { passive: true });
  }

})();
