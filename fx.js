/* ClearGlass · FX behaviors. Loaded by platform.js or the Pages hardening build.
   Progressive enhancement: inert under prefers-reduced-motion; never hides content
   if IntersectionObserver is unavailable. */
(function () {
  "use strict";
  if (window.__cgFx) return;
  window.__cgFx = true;

  var reduce = false;
  try { reduce = matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}
  // Only mark cg-fx when motion is allowed — the hiding rules in fx.css key off it,
  // so reduced-motion users (and no-JS) always see fully-visible content.
  if (!reduce) document.documentElement.classList.add("cg-fx");

  function ready(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
    else fn();
  }

  ready(function () {
    /* ── scroll progress bar ─────────────────────────────────────────────── */
    var bar = document.createElement("div");
    bar.id = "cg-progress";
    document.body.appendChild(bar);

    /* ── precision scroll controls: top + bottom ────────────────────────── */
    var top = document.createElement("button");
    top.id = "cg-top";
    top.type = "button";
    top.setAttribute("aria-label", "Back to top");
    top.innerHTML = "↑";
    top.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
    });
    document.body.appendChild(top);

    var bottom = document.createElement("button");
    bottom.id = "cg-bottom";
    bottom.type = "button";
    bottom.setAttribute("aria-label", "Scroll to bottom");
    bottom.innerHTML = "↓";
    bottom.addEventListener("click", function () {
      var h = document.documentElement;
      var max = Math.max(0, h.scrollHeight - h.clientHeight);
      window.scrollTo({ top: max, behavior: reduce ? "auto" : "smooth" });
    });
    document.body.appendChild(bottom);
    document.body.classList.add("cg-scroll-controls-mounted");

    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        var h = document.documentElement;
        var y = h.scrollTop || window.pageYOffset || 0;
        var max = (h.scrollHeight - h.clientHeight) || 1;
        var pct = Math.min(100, Math.max(0, y / max * 100));
        var nearBottom = (max - y) < 360;
        bar.style.width = pct + "%";
        top.classList.toggle("show", y > 480);
        bottom.classList.toggle("show", max > 900 && !nearBottom);
        ticking = false;
      });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    onScroll();

    if (reduce) return; // ambient bar/top/bottom stay; skip reveal + tilt

    /* ── scroll reveal (opt-in [data-reveal]) ────────────────────────────── */
    var reveals = [].slice.call(document.querySelectorAll("[data-reveal]"));
    if (reveals.length) {
      if ("IntersectionObserver" in window) {
        var io = new IntersectionObserver(function (entries) {
          entries.forEach(function (en) {
            if (en.isIntersecting) {
              var el = en.target, d = parseFloat(el.getAttribute("data-reveal-delay")) || 0;
              if (d) el.style.transitionDelay = d + "ms";
              el.classList.add("cg-in");
              io.unobserve(el);
            }
          });
        }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
        reveals.forEach(function (el) { io.observe(el); });
        // failsafe: if anything is still hidden after 1.6s, reveal it
        setTimeout(function () { reveals.forEach(function (el) { el.classList.add("cg-in"); }); }, 1600);
      } else {
        reveals.forEach(function (el) { el.classList.add("cg-in"); });
      }
    }

    /* ── pointer tilt (opt-in [data-tilt], fine pointers only) ───────────── */
    var fine = true;
    try { fine = matchMedia("(hover: hover) and (pointer: fine)").matches; } catch (e) {}
    if (fine) {
      [].slice.call(document.querySelectorAll("[data-tilt]")).forEach(function (el) {
        var raf = 0, rx = 0, ry = 0;
        var MAX = parseFloat(el.getAttribute("data-tilt")) || 6;
        function apply() { raf = 0; el.style.transform = "perspective(800px) rotateX(" + rx + "deg) rotateY(" + ry + "deg) translateY(-2px)"; }
        el.addEventListener("pointermove", function (e) {
          var r = el.getBoundingClientRect();
          ry = ((e.clientX - (r.left + r.width / 2)) / (r.width / 2)) * MAX;
          rx = -((e.clientY - (r.top + r.height / 2)) / (r.height / 2)) * MAX;
          if (!raf) raf = requestAnimationFrame(apply);
        });
        el.addEventListener("pointerleave", function () {
          if (raf) { cancelAnimationFrame(raf); raf = 0; }
          el.style.transform = "";
        });
      });
    }
  });
})();