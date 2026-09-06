/* ClearGlass · platform layer — progressive enhancement with real, shipping
   browser technology. Drop in with <script defer src="platform.js"></script>.

     1) PWA: registers the service worker (offline shell + fast repeat visits)
        and injects the web-app manifest link where a page lacks it, making the
        site installable.
     2) Instant navigation: injects a Speculation Rules script so Chromium
        prefetches (and prerenders on hover) same-origin pages — typical
        click→render drops to near-zero. Other engines ignore it harmlessly.
     3) Cross-document View Transitions: opts the site into smooth page-to-page
        fades (Chromium 126+), disabled under prefers-reduced-motion.

   Everything is feature-detected; on unsupported browsers this file is inert. */
(function () {
  "use strict";
  if (window.__cgPlatform) return;
  window.__cgPlatform = true;

  /* ── 1) PWA: manifest link + service worker ─────────────────────────────── */
  if (!document.querySelector('link[rel="manifest"]')) {
    var mf = document.createElement("link");
    mf.rel = "manifest";
    mf.href = "manifest.webmanifest";
    document.head.appendChild(mf);
  }
  if (!document.querySelector('meta[name="theme-color"]')) {
    var tc = document.createElement("meta");
    tc.name = "theme-color";
    tc.content = "#0b0f1e";
    document.head.appendChild(tc);
  }
  function addLink(sel, attrs) {
    if (document.querySelector(sel)) return;
    var l = document.createElement("link");
    Object.keys(attrs).forEach(function (k) { l.setAttribute(k, attrs[k]); });
    document.head.appendChild(l);
  }
  addLink('link[rel="icon"][type="image/svg+xml"]', { rel: "icon", type: "image/svg+xml", href: "icon.svg" });
  addLink('link[rel="apple-touch-icon"]', { rel: "apple-touch-icon", href: "logo.png" });

  /* ── advanced motion layer (fx.css + fx.js) — progressive enhancement ───── */
  addLink('link[href="fx.css"]', { rel: "stylesheet", href: "fx.css" });
  if (!document.querySelector('script[src="fx.js"]')) {
    var fx = document.createElement("script");
    fx.src = "fx.js"; fx.defer = true;
    document.body.appendChild(fx);
  }
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("sw.js").catch(function () {});
    });
  }

  /* ── 2) instant navigation: Speculation Rules (Chromium) ────────────────── */
  try {
    if (HTMLScriptElement.supports && HTMLScriptElement.supports("speculationrules")) {
      var rules = document.createElement("script");
      rules.type = "speculationrules";
      rules.textContent = JSON.stringify({
        prefetch: [{ where: { href_matches: "/*" }, eagerness: "moderate" }],
        prerender: [{ where: { href_matches: "/*" }, eagerness: "moderate" }]
      });
      document.head.appendChild(rules);
    }
  } catch (e) {}

  /* ── 3) cross-document view transitions (motion-pref aware) ─────────────── */
  try {
    var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduce) {
      var st = document.createElement("style");
      st.textContent = "@view-transition{navigation:auto}" +
        "::view-transition-old(root),::view-transition-new(root){animation-duration:.22s}";
      document.head.appendChild(st);
    }
  } catch (e) {}

  /* ── 4) founder profile link ─────────────────────────────────────────────── */
  var founderActions = document.querySelector("#founder .founder-actions");
  if (founderActions && !founderActions.querySelector('a[data-founder-linkedin]')) {
    var linkedin = document.createElement("a");
    linkedin.href = "https://www.linkedin.com/in/desmondotieno?utm_source=share_via&utm_content=profile&utm_medium=member_ios";
    linkedin.className = "btn btn-glass";
    linkedin.target = "_blank";
    linkedin.rel = "noopener noreferrer me";
    linkedin.setAttribute("data-founder-linkedin", "true");
    linkedin.setAttribute("aria-label", "View Desmond Otieno Odhiambo on LinkedIn");
    linkedin.textContent = "LinkedIn Profile ↗";
    founderActions.appendChild(linkedin);
  }

  /* ── 5) pricing catalogue parity for newly published strategic offers ───── */
  var plans = document.querySelector("#plans.grid");
  if (plans && !plans.querySelector('[data-sku="critical-minerals-compliance"]')) {
    var critical = document.createElement("article");
    critical.className = "plan feat";
    critical.setAttribute("data-reveal", "");
    critical.setAttribute("data-tilt", "5");
    critical.setAttribute("data-sku", "critical-minerals-compliance");
    critical.innerHTML =
      '<span class="tag">Strategic operations · new</span>' +
      '<h3>Critical Minerals Compliance Strategy</h3>' +
      '<div class="blurb">Compliance-first civilian strategy for critical minerals, strategic materials and lawful dual-use supply chains.</div>' +
      '<div class="price">CAD&nbsp;$1,499<span class="u">one-time</span></div>' +
      '<ul class="feats">' +
        '<li><span class="ck">✓</span> Classification, sanctions and licensing triage</li>' +
        '<li><span class="ck">✓</span> Provenance and traceability architecture</li>' +
        '<li><span class="ck">✓</span> Risk register and mitigation ownership</li>' +
        '<li><span class="ck">✓</span> Ranked go/no-go opportunity matrix</li>' +
      '</ul>' +
      '<div class="cta"><a class="cg-btn cg-btn--primary cg-btn--block" href="https://book.stripe.com/fZu3cwcfWb1jgKoeCw4Ni08" rel="noopener">Secure checkout →</a>' +
      '<div class="paynote">🔒 Stripe · encrypted card payment</div></div>';
    plans.appendChild(critical);
  }

  /* Restore the explicit payment-safety promise if a compact storefront build
     omitted the older trust copy. This is customer-facing, not a hidden check. */
  if (/\/store(?:\.html)?$/.test(location.pathname) && !document.querySelector("[data-payment-safety]")) {
    var main = document.querySelector("main");
    if (main) {
      var safety = document.createElement("p");
      safety.setAttribute("data-payment-safety", "true");
      safety.className = "note";
      safety.textContent = "Nothing is auto-charged or auto-sent. Payments occur only when you explicitly choose and complete a checkout, e-Transfer, or approved invoice.";
      main.appendChild(safety);
    }
  }
})();