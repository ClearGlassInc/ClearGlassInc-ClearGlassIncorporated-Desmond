/* ClearGlass · corner commerce dock — a fixed, self-contained brand mark and
   sales launcher for every page EXCEPT the homepage. Drop in with
   <script defer src="/logo-badge.js"></script>. No dependencies.

   The dock holds a BUY / BOOK control and the ClearGlass coin. The commerce
   panel links only to live Stripe-hosted Payment Links already configured in
   the ClearGlass account; no API keys or card data ever enter this website.
   Idempotent — a second include is a no-op. */
(function () {
  "use strict";
  if (window.__cgLogoBadge) return;
  window.__cgLogoBadge = true;

  // Homepage guard: skip the site root and root index.html.
  var path = location.pathname.replace(/\/+$/, "/");
  var last = (location.pathname.split("/").pop() || "").toLowerCase();
  var isHome = path === "/" || (last === "index.html" && location.pathname.toLowerCase() === "/index.html");
  if (isHome) return;

  var LOGO = "/assets/images/clearglass-logo.png";
  var HOME = "/index.html";
  var STORE = "/store.html";
  var CHECKOUT = "/checkout/";
  var OFFERS = [
    {
      group: "Start here",
      name: "Guardian Command Nexus Blueprint",
      price: "CAD $199 one-time",
      url: "https://buy.stripe.com/eVq4gAbbSglDfGk0LG4Ni07"
    },
    {
      group: "Start here",
      name: "Security Quick-Audit",
      price: "CAD $249 one-time",
      url: "https://buy.stripe.com/8x2eVe7ZG0mFam00LG4Ni03"
    },
    {
      group: "Start here",
      name: "90-Minute Cyber Risk Audit",
      price: "CAD $297 one-time",
      url: "https://buy.stripe.com/6oU9AUfs85GZ8dS0LG4Ni00"
    },
    {
      group: "Recurring protection",
      name: "Business Protection",
      price: "CAD $100 / month",
      url: "https://buy.stripe.com/6oU6oI2Fm7P7cu851W4Ni01"
    },
    {
      group: "Recurring protection",
      name: "Business Protection Annual",
      price: "CAD $1,000 / year",
      url: "https://buy.stripe.com/00waEY7ZGfhz51G9ic4Ni02"
    },
    {
      group: "Recurring protection",
      name: "Managed Monitoring",
      price: "from CAD $600 / month",
      url: "https://buy.stripe.com/dRm28sa7OglDbq41PK4Ni06"
    },
    {
      group: "Projects",
      name: "M365 + Windows Hardening Sprint",
      price: "from CAD $2,500",
      url: "https://buy.stripe.com/cNi7sMa7Ob1j2Ty8e84Ni04"
    },
    {
      group: "Projects",
      name: "PHIPA Readiness Assessment",
      price: "from CAD $3,000",
      url: "https://buy.stripe.com/fZu14o6VC4CV0Lq9ic4Ni05"
    }
  ];
  var EDITORIAL_TARGETS = {
    "cyber-defense-console.html": true,
    "advanced-features-tools-systems.html": true,
    "revenue-engine.html": true,
    "button-lab.html": true
  };

  function loadEditorialVisuals() {
    if (!EDITORIAL_TARGETS[last] || document.getElementById("cg-editorial-visuals-script")) return;
    var script = document.createElement("script");
    script.id = "cg-editorial-visuals-script";
    script.src = "/editorial-visuals.js";
    script.defer = true;
    document.head.appendChild(script);
  }

  function makeOfferLink(offer) {
    var a = document.createElement("a");
    a.className = "cg-sales-offer";
    a.href = offer.url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.setAttribute("data-cg-offer", offer.name);
    a.innerHTML =
      '<span class="cg-sales-copy"><strong>' + offer.name + '</strong><small>' + offer.price +
      '</small></span><span class="cg-sales-arrow" aria-hidden="true">→</span>';
    return a;
  }

  function buildSalesPanel(dock) {
    var shell = document.createElement("div");
    shell.id = "cg-sales-shell";

    var button = document.createElement("button");
    button.id = "cg-sales-button";
    button.type = "button";
    button.setAttribute("aria-haspopup", "dialog");
    button.setAttribute("aria-expanded", "false");
    button.innerHTML = '<span class="cg-sales-live" aria-hidden="true"></span><span>BUY / BOOK</span>';

    var panel = document.createElement("section");
    panel.id = "cg-sales-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "false");
    panel.setAttribute("aria-label", "ClearGlass secure checkout options");
    panel.hidden = true;

    var header = document.createElement("div");
    header.className = "cg-sales-head";
    header.innerHTML =
      '<div><strong>ClearGlass Secure Checkout</strong><small>Stripe-hosted · CAD pricing</small></div>' +
      '<button type="button" class="cg-sales-close" aria-label="Close checkout menu">×</button>';
    panel.appendChild(header);

    var currentGroup = "";
    OFFERS.forEach(function (offer) {
      if (offer.group !== currentGroup) {
        currentGroup = offer.group;
        var title = document.createElement("div");
        title.className = "cg-sales-group";
        title.textContent = currentGroup;
        panel.appendChild(title);
      }
      panel.appendChild(makeOfferLink(offer));
    });

    var footer = document.createElement("div");
    footer.className = "cg-sales-foot";
    footer.innerHTML =
      '<a href="' + STORE + '">Compare engagements</a>' +
      '<a href="' + CHECKOUT + '">Open checkout hub</a>';
    panel.appendChild(footer);

    function setOpen(open) {
      panel.hidden = !open;
      shell.classList.toggle("open", open);
      button.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) {
        var first = panel.querySelector(".cg-sales-offer");
        if (first) first.focus();
      } else {
        button.focus();
      }
    }

    button.addEventListener("click", function () {
      setOpen(panel.hidden);
    });
    header.querySelector(".cg-sales-close").addEventListener("click", function () {
      setOpen(false);
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !panel.hidden) setOpen(false);
    });
    document.addEventListener("click", function (event) {
      if (!panel.hidden && !shell.contains(event.target)) setOpen(false);
    });
    panel.addEventListener("click", function (event) {
      var offer = event.target.closest("[data-cg-offer]");
      if (!offer) return;
      try {
        window.dispatchEvent(new CustomEvent("cg:sales-click", {
          detail: { offer: offer.getAttribute("data-cg-offer"), page: location.pathname }
        }));
      } catch (_) { /* older browser — checkout still opens */ }
    });

    shell.appendChild(button);
    shell.appendChild(panel);
    dock.appendChild(shell);
  }

  function build() {
    if (document.getElementById("cg-dock")) {
      loadEditorialVisuals();
      return;
    }

    var css = [
      "#cg-dock{position:fixed;right:18px;bottom:18px;z-index:2147483000;display:inline-flex;align-items:center;gap:8px;pointer-events:none;font-family:Urbanist,Inter,system-ui,-apple-system,sans-serif}",
      "#cg-dock>*{pointer-events:auto}",
      "#cg-dock>#cgw-fab{margin-right:0!important}",
      "#cg-dock::before{content:'';position:absolute;inset:-16px -16px -16px -22px;border-radius:999px;pointer-events:none;z-index:-1;will-change:opacity;background:radial-gradient(120% 130% at 82% 50%,rgba(238, 99, 101,.42) 0%,rgba(238, 99, 122,.28) 42%,rgba(235, 77, 79,.12) 60%,transparent 74%);filter:blur(9px);opacity:.72;animation:cgDockGlow 3.6s ease-in-out infinite}",
      "@keyframes cgDockGlow{0%,100%{opacity:.5}50%{opacity:.96}}",
      "#cg-sales-shell{position:relative;display:flex;align-items:center}",
      "#cg-sales-button{min-height:48px;display:inline-flex;align-items:center;gap:9px;padding:0 17px;border-radius:999px;border:1px solid rgba(238, 99, 108,.58);background:linear-gradient(135deg,rgba(32, 22, 23,.96),rgba(88, 31, 41,.96));color:#f8fbff;font:800 12px/1 Urbanist,Inter,system-ui,sans-serif;letter-spacing:.12em;cursor:pointer;box-shadow:0 8px 28px rgba(0,0,0,.38),0 0 20px rgba(238, 99, 101,.3),inset 0 1px 0 rgba(255,255,255,.17);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease}",
      "#cg-sales-button:hover,#cg-sales-button[aria-expanded='true']{transform:translateY(-2px);border-color:rgba(238, 99, 122,.94);box-shadow:0 12px 34px rgba(0,0,0,.44),0 0 30px rgba(238, 99, 108,.46)}",
      "#cg-sales-button:focus-visible{outline:2px solid #ee637a;outline-offset:3px}",
      ".cg-sales-live{width:8px;height:8px;border-radius:50%;background:#55e6a5;box-shadow:0 0 12px rgba(85,230,165,.9)}",
      "#cg-sales-panel{position:absolute;right:0;bottom:66px;width:min(390px,calc(100vw - 28px));max-height:min(72vh,690px);overflow:auto;padding:14px;border:1px solid rgba(238, 99, 108,.34);border-radius:20px;background:linear-gradient(165deg,rgba(20, 14, 14,.98),rgba(30, 22, 23,.98));color:#f7f2f2;box-shadow:0 28px 90px rgba(0,0,0,.62),0 0 42px rgba(237, 91, 101,.22);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px)}",
      "#cg-sales-panel[hidden]{display:none!important}",
      ".cg-sales-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:4px 4px 13px;border-bottom:1px solid rgba(255,255,255,.1)}",
      ".cg-sales-head strong{display:block;font-size:15px;letter-spacing:.01em;color:#fff}",
      ".cg-sales-head small{display:block;margin-top:4px;font-size:11px;color:#c89397}",
      ".cg-sales-close{width:32px;height:32px;border-radius:10px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.05);color:#fff;font:400 22px/1 system-ui;cursor:pointer}",
      ".cg-sales-group{padding:14px 5px 6px;font-size:10px;font-weight:800;letter-spacing:.17em;text-transform:uppercase;color:#d89095}",
      ".cg-sales-offer{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-top:6px;padding:12px 13px;border:1px solid rgba(255,255,255,.09);border-radius:13px;background:rgba(255,255,255,.045);color:#eef3ff;text-decoration:none;transition:transform .16s ease,border-color .16s ease,background .16s ease}",
      ".cg-sales-offer:hover,.cg-sales-offer:focus-visible{transform:translateX(2px);border-color:rgba(238, 99, 101,.52);background:rgba(238, 99, 108,.13);outline:none}",
      ".cg-sales-copy{min-width:0;display:block}",
      ".cg-sales-copy strong{display:block;font-size:13px;line-height:1.25;color:#fff}",
      ".cg-sales-copy small{display:block;margin-top:4px;font-size:11px;color:#d09ea1}",
      ".cg-sales-arrow{flex:0 0 auto;color:#ee6365;font-size:17px}",
      ".cg-sales-foot{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:14px;padding-top:13px;border-top:1px solid rgba(255,255,255,.1)}",
      ".cg-sales-foot a{display:flex;align-items:center;justify-content:center;min-height:40px;padding:8px;border:1px solid rgba(255,255,255,.11);border-radius:11px;color:#e8d9da;text-decoration:none;font-size:11px;font-weight:750;text-align:center;background:rgba(255,255,255,.04)}",
      ".cg-sales-foot a:hover{color:#fff;border-color:rgba(238, 99, 122,.62)}",
      "#cg-logo-badge{position:relative;flex:0 0 auto;width:54px;height:54px;border-radius:50%;display:block;overflow:hidden;background:linear-gradient(180deg,rgba(34, 26, 26,.92),rgba(22, 17, 17,.92));border:1px solid rgba(247,250,255,.82);box-shadow:0 0 10px rgba(238, 99, 108,.55),0 0 22px rgba(237, 94, 118,.35),inset 0 4px 12px rgba(255,255,255,.72),inset 0 -10px 22px rgba(0,0,0,.42);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);transition:transform .18s cubic-bezier(.16,1,.3,1),box-shadow .18s ease;line-height:0}",
      "#cg-logo-badge:hover{transform:scale(1.06);border-color:rgba(238, 99, 108,.95);box-shadow:0 8px 26px rgba(0,0,0,.46),0 0 26px rgba(238, 99, 101,.6),0 0 44px rgba(238, 99, 122,.45)}",
      "#cg-logo-badge img{width:100%;height:100%;object-fit:cover;display:block}",
      "#cg-logo-badge:focus-visible{outline:2px solid #ee637a;outline-offset:3px}",
      "@media(max-width:640px){#cg-dock{right:12px;bottom:12px;gap:6px}#cg-logo-badge{width:46px;height:46px}#cg-sales-button{min-height:44px;padding:0 13px;font-size:10.5px}#cg-sales-panel{position:fixed;right:12px;bottom:68px;width:calc(100vw - 24px);max-height:72vh}.cg-sales-foot{grid-template-columns:1fr}}",
      "@media (prefers-reduced-motion:reduce){#cg-dock::before{animation:none;opacity:.7}#cg-sales-button,#cg-sales-offer,#cg-logo-badge{transition:none}}",
      /* The Stealth Glass stack (stealth-glass.js) is anchored to the same
         bottom-right corner, so the logo badge ended up half-hidden behind it.
         Stack it directly above this dock, on the same right edge, so the two
         read as one column. Nothing is hidden or resized. */
      "body.cg-dock-mounted.cg-security-dock-mounted #cg-security-stack{right:max(18px,env(safe-area-inset-right))!important;bottom:calc(max(18px,env(safe-area-inset-bottom)) + 64px)!important}",
      "body.cg-dock-mounted.cg-security-dock-mounted{padding-bottom:calc(140px + env(safe-area-inset-bottom))}",
      "@media(max-width:640px){body.cg-dock-mounted.cg-security-dock-mounted #cg-security-stack{right:max(12px,env(safe-area-inset-right))!important;bottom:calc(max(12px,env(safe-area-inset-bottom)) + 56px)!important}body.cg-dock-mounted.cg-security-dock-mounted{padding-bottom:calc(124px + env(safe-area-inset-bottom))}}",
      /* ── ClearGlass material: see-through, not frosted ──
         One material for the whole corner column (Stealth Glass frame, BUY /
         BOOK, coin). Light blur + saturation so the page reads through it,
         a refracted hairline edge, and a specular highlight driven by
         --cg-lx/--cg-ly: pointer-tracked on hover devices, a slow ambient
         sweep on touch. Registered with @property so the sweep interpolates. */
      "@property --cg-lx{syntax:'<percentage>';inherits:true;initial-value:28%}",
      "@property --cg-ly{syntax:'<percentage>';inherits:true;initial-value:0%}",
      "@keyframes cgGlassSweep{0%,100%{--cg-lx:12%;--cg-ly:0%}50%{--cg-lx:88%;--cg-ly:100%}}",
      "#cg-sales-button{background:radial-gradient(120% 160% at var(--cg-lx) var(--cg-ly),rgba(255,255,255,.20),transparent 46%),linear-gradient(135deg,rgba(88,31,41,.26),rgba(32,22,23,.16));-webkit-backdrop-filter:blur(9px) saturate(185%) brightness(1.06);backdrop-filter:blur(9px) saturate(185%) brightness(1.06);text-shadow:0 1px 2px rgba(0,0,0,.65);box-shadow:0 8px 26px rgba(0,0,0,.30),inset 0 1px 0 rgba(255,255,255,.30),inset 0 -1px 0 rgba(0,0,0,.18)}",
      "#cg-logo-badge::after{content:'';position:absolute;inset:0;border-radius:inherit;pointer-events:none;background:radial-gradient(70% 70% at var(--cg-lx) var(--cg-ly),rgba(255,255,255,.34),transparent 60%);mix-blend-mode:screen}",
      "body.cg-dock-mounted.cg-security-dock-mounted #cg-security-stack{border-color:rgba(255,255,255,.20)!important;background:radial-gradient(90% 140% at var(--cg-lx) var(--cg-ly),rgba(255,255,255,.16),transparent 52%),linear-gradient(145deg,rgba(58,24,26,.20),rgba(21,13,14,.12))!important;-webkit-backdrop-filter:blur(10px) saturate(190%) brightness(1.05)!important;backdrop-filter:blur(10px) saturate(190%) brightness(1.05)!important}",
      "body.cg-dock-mounted.cg-security-dock-mounted #cg-security-stack::before{background:linear-gradient(135deg,rgba(255,255,255,.55),rgba(255,255,255,.04) 38%,rgba(238,99,101,.10) 64%,rgba(120,224,200,.30));padding:1px;-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);mask-composite:exclude;opacity:.9;mix-blend-mode:normal}",
      "body.cg-dock-mounted.cg-security-dock-mounted #cg-security-stack #cg-stealth-btn:not(.is-on){background:radial-gradient(90% 180% at var(--cg-lx) var(--cg-ly),rgba(255,255,255,.18),transparent 50%),linear-gradient(155deg,rgba(88,42,45,.24),rgba(28,19,20,.14))!important;-webkit-backdrop-filter:blur(6px) saturate(175%)!important;backdrop-filter:blur(6px) saturate(175%)!important;text-shadow:0 1px 2px rgba(0,0,0,.7)}",
      "@media (hover:none) and (prefers-reduced-motion:no-preference){#cg-dock,body.cg-dock-mounted.cg-security-dock-mounted #cg-security-stack{animation:cgGlassSweep 9s ease-in-out infinite}}",
      /* Accessibility + capability fallbacks: opaque where transparency is unwanted or unsupported. */
      "@media (prefers-reduced-transparency:reduce){#cg-sales-button{background:linear-gradient(135deg,rgba(32,22,23,.96),rgba(88,31,41,.96))}body.cg-dock-mounted.cg-security-dock-mounted #cg-security-stack,body.cg-dock-mounted.cg-security-dock-mounted #cg-security-stack #cg-stealth-btn:not(.is-on){background:linear-gradient(145deg,rgba(43,24,26,.96),rgba(21,13,14,.96))!important}#cg-logo-badge::after{display:none}}",
      "@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){#cg-sales-button{background:linear-gradient(135deg,rgba(32,22,23,.96),rgba(88,31,41,.96))}body.cg-dock-mounted.cg-security-dock-mounted #cg-security-stack,body.cg-dock-mounted.cg-security-dock-mounted #cg-security-stack #cg-stealth-btn:not(.is-on){background:linear-gradient(145deg,rgba(43,24,26,.96),rgba(21,13,14,.96))!important}}"
    ].join("");

    var style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);

    var dock = document.createElement("div");
    dock.id = "cg-dock";
    document.body.appendChild(dock);
    document.body.classList.add("cg-dock-mounted");

    buildSalesPanel(dock);

    var a = document.createElement("a");
    a.id = "cg-logo-badge";
    a.href = HOME;
    a.setAttribute("aria-label", "ClearGlass — home");
    a.title = "ClearGlass — home";

    var img = document.createElement("img");
    img.src = LOGO;
    img.alt = "ClearGlass logo";
    img.decoding = "async";
    img.loading = "lazy";

    a.appendChild(img);
    dock.appendChild(a);
    trackGlassLight(dock);
    loadEditorialVisuals();
  }

  // Specular highlight follows the pointer across each glass surface.
  // Hover-capable pointers only; touch gets the CSS ambient sweep instead.
  function trackGlassLight(dock) {
    if (!window.matchMedia) return;
    if (!matchMedia("(hover:hover)").matches) return;
    if (matchMedia("(prefers-reduced-motion:reduce)").matches) return;
    var raf = 0, px = 0, py = 0;
    function place(el) {
      if (!el) return;
      var r = el.getBoundingClientRect();
      if (!r.width || !r.height) return;
      var x = Math.max(-50, Math.min(150, ((px - r.left) / r.width) * 100));
      var y = Math.max(-50, Math.min(150, ((py - r.top) / r.height) * 100));
      el.style.setProperty("--cg-lx", x.toFixed(1) + "%");
      el.style.setProperty("--cg-ly", y.toFixed(1) + "%");
    }
    function flush() {
      raf = 0;
      place(dock.querySelector("#cg-sales-button"));
      place(dock.querySelector("#cg-logo-badge"));
      place(document.getElementById("cg-security-stack"));
    }
    document.addEventListener("pointermove", function (event) {
      if (event.pointerType && event.pointerType !== "mouse") return;
      px = event.clientX;
      py = event.clientY;
      if (!raf) raf = requestAnimationFrame(flush);
    }, { passive: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", build);
  } else {
    build();
  }
})();