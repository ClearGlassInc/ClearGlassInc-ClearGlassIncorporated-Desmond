/* ClearGlass · Command-Center atmosphere layer (behaviour)
   Self-contained, dependency-free. Injects command-center.css and a fixed
   background stack, animates a capped neural/particle field on a single canvas,
   drives a cursor-reactive glow, runs opt-in count-ups, and shows page-provided
   ambient toasts.

   Honesty + performance guarantees:
     * No fabricated data. Count-ups animate numbers already in the DOM; toast
       messages come only from a page-provided <script id="cc-messages"> block,
       so each page owns (and vouches for) its own copy.
     * Fully disabled under prefers-reduced-motion (static styling only).
     * requestAnimationFrame loop, capped node count, paused when the tab is
       hidden or the page is scrolled past the hero — GPU-friendly, no layout
       thrash (transforms/opacity only). */
(function () {
  "use strict";
  if (window.__ccBooted) return;
  window.__ccBooted = true;

  var reduce = false;
  try { reduce = matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}

  // inject stylesheet once
  if (!document.querySelector('link[data-cc]')) {
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "/command-center.css";
    link.setAttribute("data-cc", "1");
    document.head.appendChild(link);
  }

  function boot() {
    // ---- background stack -------------------------------------------------
    var bg = document.createElement("div");
    bg.id = "cc-bg";
    bg.setAttribute("aria-hidden", "true");
    bg.innerHTML =
      '<div class="cc-layer cc-grid"></div>' +
      '<div class="cc-layer cc-volume"></div>' +
      '<canvas class="cc-field"></canvas>' +
      '<div class="cc-layer cc-cursor"></div>' +
      '<div class="cc-layer cc-beam"></div>';
    document.body.insertBefore(bg, document.body.firstChild);

    if (!reduce) {
      initField(bg.querySelector(".cc-field"));
      initCursor();
    }
    initCountUp();
    if (!reduce) initToasts();
  }

  // ---- cursor-reactive glow (rAF-throttled) -------------------------------
  function initCursor() {
    var tx = 50, ty = 30, pending = false;
    window.addEventListener("pointermove", function (e) {
      tx = (e.clientX / window.innerWidth) * 100;
      ty = (e.clientY / window.innerHeight) * 100;
      if (!pending) {
        pending = true;
        requestAnimationFrame(function () {
          document.documentElement.style.setProperty("--cc-mx", tx.toFixed(1) + "%");
          document.documentElement.style.setProperty("--cc-my", ty.toFixed(1) + "%");
          pending = false;
        });
      }
    }, { passive: true });
  }

  // ---- neural / particle field on one canvas ------------------------------
  function initField(canvas) {
    var ctx = canvas.getContext("2d");
    if (!ctx) return;
    var dpr = Math.min(window.devicePixelRatio || 1, 1.75);
    var nodes = [], W = 0, H = 0, raf = 0, running = false;

    function resize() {
      W = canvas.clientWidth; H = canvas.clientHeight;
      canvas.width = Math.floor(W * dpr); canvas.height = Math.floor(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // node count scales with area but is hard-capped for 60fps on mid-tier GPUs
      var target = Math.max(28, Math.min(64, Math.round((W * H) / 26000)));
      nodes = [];
      for (var i = 0; i < target; i++) {
        nodes.push({
          x: Math.random() * W, y: Math.random() * H,
          vx: (Math.random() - 0.5) * 0.22, vy: (Math.random() - 0.5) * 0.22
        });
      }
    }

    function frame() {
      if (!running) return;
      ctx.clearRect(0, 0, W, H);
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        n.x += n.vx; n.y += n.vy;
        if (n.x < 0 || n.x > W) n.vx *= -1;
        if (n.y < 0 || n.y > H) n.vy *= -1;
      }
      // links between nearby nodes (secure network pathways)
      for (var a = 0; a < nodes.length; a++) {
        for (var b = a + 1; b < nodes.length; b++) {
          var dx = nodes[a].x - nodes[b].x, dy = nodes[a].y - nodes[b].y;
          var d2 = dx * dx + dy * dy;
          if (d2 < 15000) {
            var o = (1 - d2 / 15000) * 0.5;
            ctx.strokeStyle = "rgba(56,217,255," + o.toFixed(3) + ")";
            ctx.beginPath();
            ctx.moveTo(nodes[a].x, nodes[a].y);
            ctx.lineTo(nodes[b].x, nodes[b].y);
            ctx.stroke();
          }
        }
      }
      // nodes (moving data packets)
      for (var k = 0; k < nodes.length; k++) {
        ctx.fillStyle = "rgba(157,124,255,.85)";
        ctx.beginPath();
        ctx.arc(nodes[k].x, nodes[k].y, 1.6, 0, 6.2832);
        ctx.fill();
      }
      raf = requestAnimationFrame(frame);
    }

    function start() { if (!running) { running = true; raf = requestAnimationFrame(frame); } }
    function stop() { running = false; if (raf) cancelAnimationFrame(raf); }

    resize();
    window.addEventListener("resize", function () { resize(); }, { passive: true });
    // pause when tab hidden, or when the field is scrolled out of view
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) stop(); else start();
    });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (ents) {
        if (ents[0].isIntersecting && !document.hidden) start(); else stop();
      }, { threshold: 0 }).observe(canvas);
    } else { start(); }
    start();
  }

  // ---- count-up for opt-in [data-countup] elements ------------------------
  function initCountUp() {
    var els = [].slice.call(document.querySelectorAll("[data-countup]"));
    if (!els.length) return;
    function run(el) {
      var target = parseFloat(el.getAttribute("data-countup"));
      if (isNaN(target)) return;
      var dur = 1400, suffix = el.getAttribute("data-suffix") || "";
      var dec = (el.getAttribute("data-countup").split(".")[1] || "").length;
      if (reduce) { el.textContent = target.toFixed(dec) + suffix; return; }
      var t0 = null;
      function step(ts) {
        if (!t0) t0 = ts;
        var p = Math.min(1, (ts - t0) / dur);
        var e = 1 - Math.pow(1 - p, 3); // easeOutCubic
        el.textContent = (target * e).toFixed(dec) + suffix;
        if (p < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (ents) {
        ents.forEach(function (en) {
          if (en.isIntersecting) { run(en.target); io.unobserve(en.target); }
        });
      }, { threshold: 0.4 });
      els.forEach(function (el) { io.observe(el); });
    } else { els.forEach(run); }
  }

  // ---- ambient toasts (page-provided messages only) -----------------------
  function initToasts() {
    var src = document.getElementById("cc-messages");
    if (!src) return;                 // no page-authored messages -> nothing to show
    var msgs;
    try { msgs = JSON.parse(src.textContent); } catch (e) { return; }
    if (!Array.isArray(msgs) || !msgs.length) return;

    var stack = document.createElement("div");
    stack.id = "cc-toasts";
    stack.setAttribute("aria-hidden", "true");
    document.body.appendChild(stack);

    var i = 0;
    function show() {
      if (document.hidden) { schedule(); return; }
      var msg = msgs[i % msgs.length]; i++;
      var t = document.createElement("div");
      t.className = "cc-toast";
      t.innerHTML = '<span class="cc-status"></span>' + String(msg);
      stack.appendChild(t);
      requestAnimationFrame(function () { t.classList.add("cc-in"); });
      setTimeout(function () {
        t.classList.remove("cc-in");
        setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 450);
      }, 4200);
      schedule();
    }
    function schedule() { setTimeout(show, 5200 + Math.random() * 3200); }
    setTimeout(show, 2600);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else { boot(); }
})();
