/* ClearGlass · Stealth Glass
   Single-source privacy visual mode and fused security dock control. */
(function () {
  "use strict";
  if (window.__cgStealthGlass) return;
  window.__cgStealthGlass = true;

  var KEY = "cg-stealth";
  var ON = "on";
  var OFF = "off";
  var reduce = false;
  try { reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}

  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function save(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }

  function loadOnce(selector, tagName, attrs) {
    if (document.querySelector(selector)) return;
    var el = document.createElement(tagName);
    Object.keys(attrs).forEach(function (key) { el.setAttribute(key, attrs[key]); });
    (tagName === "script" ? document.body : document.head).appendChild(el);
  }

  function ready(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn, { once: true });
    else fn();
  }

  loadOnce('link[href="/security-stack-fusion.css"],link[href="security-stack-fusion.css"]', "link", {
    rel: "stylesheet",
    href: "/security-stack-fusion.css",
    "data-security-stack-fusion": "true"
  });

  if (!window.__cgAnalytics && !document.querySelector("script[data-cg-analytics]")) {
    var analytics = document.createElement("script");
    analytics.src = "/analytics.js";
    analytics.defer = true;
    analytics.setAttribute("data-cg-analytics", "");
    (document.head || document.documentElement).appendChild(analytics);
  }

  var CSS = [
    "#cg-neon-aura{position:fixed;inset:0;z-index:2147483000;pointer-events:none;will-change:opacity;box-shadow:inset 0 0 130px rgba(96,165,250,.10),inset 0 0 46px rgba(167,139,250,.08);animation:cgNeonAura 6s ease-in-out infinite}",
    "#cg-neon-aura::after{content:'';position:absolute;right:-46px;bottom:-46px;width:340px;height:340px;border-radius:50%;background:radial-gradient(circle,rgba(96,165,250,.16),rgba(167,139,250,.09) 46%,transparent 72%);filter:blur(6px)}",
    "@keyframes cgNeonAura{0%,100%{opacity:.65}50%{opacity:1}}",
    "[data-skin='stealth'] #cg-neon-aura{box-shadow:inset 0 0 150px rgba(120,224,200,.12),inset 0 0 50px rgba(96,165,250,.08)}",
    "[data-skin='stealth'] #cg-neon-aura::after{background:radial-gradient(circle,rgba(120,224,200,.18),rgba(96,165,250,.08) 46%,transparent 72%)}",
    "#cg-stealth-veil{position:fixed;inset:0;z-index:2147483646;pointer-events:none;background:rgba(5,8,12,.26);will-change:opacity;-webkit-backdrop-filter:saturate(.6) brightness(.86);backdrop-filter:saturate(.6) brightness(.86);opacity:0;animation:cgSgVeil .4s cubic-bezier(.16,1,.3,1) forwards}",
    "@keyframes cgSgVeil{to{opacity:1}}",
    "#cg-stealth-btn{--cg-mx:0px;--cg-my:0px;position:fixed;right:var(--cg-security-edge,18px);bottom:var(--cg-security-bottom,84px);z-index:2147483647;display:inline-flex;align-items:center;gap:7px;height:30px;padding:0 13px 0 11px;margin:0;border:0;border-radius:999px;cursor:pointer;white-space:nowrap;line-height:1;overflow:hidden;isolation:isolate;-webkit-tap-highlight-color:transparent;font-family:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9.5px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#e7eeff;background:linear-gradient(165deg,rgba(30,34,58,.58),rgba(12,14,28,.66));-webkit-backdrop-filter:blur(14px) saturate(1.55);backdrop-filter:blur(14px) saturate(1.55);box-shadow:0 4px 18px rgba(0,0,0,.38),0 0 0 .5px rgba(150,170,255,.30),inset 0 1px 0 rgba(255,255,255,.16),inset 0 -1px 0 rgba(0,0,0,.25);transform:translate3d(var(--cg-mx),var(--cg-my),0);will-change:transform;transition:transform .22s cubic-bezier(.16,1,.3,1),box-shadow .22s ease,color .22s ease,background .22s ease}",
    "#cg-stealth-btn::after{content:'';position:absolute;inset:0;border-radius:inherit;padding:1px;pointer-events:none;background:linear-gradient(150deg,rgba(180,200,255,.55),rgba(150,170,255,.06) 42%,rgba(120,224,200,.14));-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);mask-composite:exclude;opacity:.76;z-index:3}",
    "#cg-stealth-btn::before{content:'';position:absolute;inset:0;border-radius:inherit;pointer-events:none;z-index:1;background:linear-gradient(115deg,transparent 30%,rgba(255,255,255,.18) 48%,rgba(255,255,255,.045) 54%,transparent 70%);transform:translateX(-130%);transition:transform .7s cubic-bezier(.16,1,.3,1)}",
    "#cg-stealth-btn:hover::before,#cg-stealth-btn:focus-visible::before{transform:translateX(130%)}",
    "#cg-stealth-btn:hover{color:#fff;transform:translate3d(var(--cg-mx),calc(var(--cg-my) - 1.5px),0) scale(1.035);box-shadow:0 8px 26px rgba(0,0,0,.46),0 0 0 .5px rgba(170,190,255,.5),0 0 22px -2px rgba(120,160,255,.5),inset 0 1px 0 rgba(255,255,255,.2),inset 0 -1px 0 rgba(0,0,0,.28)}",
    "#cg-stealth-btn:active{transform:translate3d(var(--cg-mx),var(--cg-my),0) scale(.975)}",
    "#cg-stealth-btn:focus-visible{outline:2px solid #a9b8ff;outline-offset:3px}",
    "#cg-stealth-btn .cg-sg-ic{width:13px;height:13px;display:block;flex:0 0 auto;position:relative;z-index:2;filter:drop-shadow(0 0 4px rgba(140,170,255,.45))}",
    "#cg-stealth-btn .cg-sg-ic svg{width:100%;height:100%;display:block}",
    "#cg-stealth-btn .cg-sg-tx{position:relative;z-index:2}",
    "#cg-stealth-btn .cg-sg-glow{position:absolute;inset:0;border-radius:inherit;z-index:0;pointer-events:none;background:radial-gradient(60% 120% at 18% 50%,rgba(130,160,255,.24),transparent 70%);opacity:.55;animation:cgSgPulse 4.2s ease-in-out infinite}",
    "@keyframes cgSgPulse{0%,100%{opacity:.4}50%{opacity:.86}}",
    "#cg-stealth-btn.is-on{color:#c9fbf2;background:linear-gradient(165deg,rgba(10,26,26,.62),rgba(4,14,14,.68));box-shadow:0 4px 18px rgba(0,0,0,.5),0 0 0 .5px rgba(120,224,200,.5),0 0 20px -3px rgba(120,224,200,.5),inset 0 1px 0 rgba(190,255,240,.16),inset 0 -1px 0 rgba(0,0,0,.3)}",
    "#cg-stealth-btn.is-on .cg-sg-ic{filter:drop-shadow(0 0 5px rgba(120,224,200,.7))}",
    "#cg-security-stack #cg-stealth-btn{position:relative;right:auto;bottom:auto;align-self:flex-end;pointer-events:auto}",
    "@media(max-width:640px){#cg-neon-aura::after{width:240px;height:240px;right:-40px;bottom:-40px}#cg-stealth-btn{right:var(--cg-security-edge,14px);bottom:var(--cg-security-bottom,72px);height:28px;font-size:8.5px;padding:0 10px 0 8px}}",
    "@media (prefers-reduced-motion:reduce){#cg-neon-aura{animation:none;opacity:.8}#cg-stealth-btn,#cg-stealth-btn:hover,#cg-stealth-btn:active{transition:none}#cg-stealth-btn::before{display:none}#cg-stealth-btn .cg-sg-glow{animation:none}#cg-stealth-veil{animation:none;opacity:1}}",
    "@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){#cg-stealth-btn{background:linear-gradient(165deg,rgba(26,30,52,.96),rgba(10,12,24,.97))}#cg-stealth-veil{background:rgba(6,9,13,.5)}}"
  ].join("");

  function injectStyle() {
    if (document.getElementById("cg-stealth-style")) return;
    var style = document.createElement("style");
    style.id = "cg-stealth-style";
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  function getStack() {
    var stack = document.getElementById("cg-security-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.id = "cg-security-stack";
      stack.setAttribute("role", "group");
      stack.setAttribute("aria-label", "ClearGlass security controls");
      document.body.appendChild(stack);
    }
    document.body.classList.add("cg-security-dock-mounted");
    return stack;
  }

  function veil(on) {
    var el = document.getElementById("cg-stealth-veil");
    if (on) {
      if (!el && document.body) {
        el = document.createElement("div");
        el.id = "cg-stealth-veil";
        el.setAttribute("aria-hidden", "true");
        document.body.appendChild(el);
      }
    } else if (el) {
      el.parentNode.removeChild(el);
    }
  }

  function apply(on, btn) {
    [document.documentElement, document.body].forEach(function (node) {
      if (!node) return;
      if (on) node.setAttribute("data-skin", "stealth");
      else if (node.getAttribute("data-skin") === "stealth") node.removeAttribute("data-skin");
    });
    veil(on);
    if (btn) {
      btn.setAttribute("aria-pressed", String(on));
      btn.classList.toggle("is-on", on);
      btn.title = on ? "Stealth Glass ON · tap to restore signal" : "Stealth Glass · dim and desaturate";
    }
  }

  function magnetize(btn) {
    if (reduce) return;
    var raf = 0, mx = 0, my = 0;
    function flush() {
      raf = 0;
      btn.style.setProperty("--cg-mx", mx.toFixed(2) + "px");
      btn.style.setProperty("--cg-my", my.toFixed(2) + "px");
    }
    btn.addEventListener("pointermove", function (event) {
      var rect = btn.getBoundingClientRect();
      var dx = (event.clientX - (rect.left + rect.width / 2)) / (rect.width / 2);
      var dy = (event.clientY - (rect.top + rect.height / 2)) / (rect.height / 2);
      mx = Math.max(-1, Math.min(1, dx)) * 2.5;
      my = Math.max(-1, Math.min(1, dy)) * 2.5;
      if (!raf) raf = requestAnimationFrame(flush);
    });
    btn.addEventListener("pointerleave", function () {
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
      mx = my = 0;
      btn.style.setProperty("--cg-mx", "0px");
      btn.style.setProperty("--cg-my", "0px");
    });
  }

  function alignWithAegis(btn) {
    var stack = getStack();
    if (btn.parentNode !== stack) stack.insertBefore(btn, stack.firstChild);
    btn.style.removeProperty("right");
    btn.style.removeProperty("bottom");
  }

  function build() {
    if (!document.body || document.getElementById("cg-stealth-btn")) return;
    injectStyle();

    if (!document.getElementById("cg-neon-aura")) {
      var aura = document.createElement("div");
      aura.id = "cg-neon-aura";
      aura.setAttribute("aria-hidden", "true");
      document.body.appendChild(aura);
    }

    var btn = document.createElement("button");
    btn.id = "cg-stealth-btn";
    btn.type = "button";
    btn.setAttribute("aria-label", "Toggle Stealth Glass visual mode");
    btn.setAttribute("aria-pressed", "false");
    btn.innerHTML = '<span class="cg-sg-glow" aria-hidden="true"></span>' +
      '<span class="cg-sg-ic" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M21 12.8A8.4 8.4 0 1 1 11.2 3a6.4 6.4 0 0 0 9.8 9.8Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span>' +
      '<span class="cg-sg-tx">Stealth Glass</span>';

    alignWithAegis(btn);
    magnetize(btn);

    var active = stored() === ON;
    apply(active, btn);

    btn.addEventListener("click", function () {
      active = !(btn.getAttribute("aria-pressed") === "true");
      save(active ? ON : OFF);
      apply(active, btn);
      window.dispatchEvent(new CustomEvent("clearglass:stealth", { detail: { active: active } }));
    });
  }

  window.__cgRefreshSecurityStack = function () {
    var btn = document.getElementById("cg-stealth-btn");
    if (btn) alignWithAegis(btn);
  };

  ready(build);
})();