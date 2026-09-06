/* ClearGlass · site-wide privacy analytics loader.
   ───────────────────────────────────────────────────────────────────────────
   PURPOSE: one place to switch on website analytics so you can finally SEE
   visitors, traffic sources, and store clicks. Loaded on every page via
   /stealth-glass.js, so configuring it here turns analytics on site-wide.

   DEFAULT = OFF. Until you set CONFIG.provider below, this file does nothing:
   no third-party request, no cookies, no tracking. That is intentional — it
   should not phone home to anyone until you choose a provider.

   ── HOW TO TURN IT ON (2 minutes) ──────────────────────────────────────────
   GA4 (free):  create a property at analytics.google.com, copy the Measurement
     ID (looks like G-XXXXXXXXXX), then set:
       provider: "ga4",  measurementId: "G-XXXXXXXXXX"
   Plausible (paid, cookieless): add the domain at plausible.io, then set:
       provider: "plausible"   (domain below is already correct)
   Commit the change; CI stays green; analytics goes live on the next deploy.

   NOTE: GA4 sets cookies — update the privacy policy if you enable it.
   Plausible is cookieless and needs no consent banner. */
(function () {
  "use strict";
  if (window.__cgAnalytics) return;   // idempotent — load once even if injected twice
  window.__cgAnalytics = true;

  // ── CONFIG ── set ONE provider to switch analytics on site-wide ────────────
  var CONFIG = {
    provider: "",                          // "ga4" | "plausible" | "" (off)
    measurementId: "",                     // GA4 only, e.g. "G-XXXXXXXXXX"
    domain: "www.clearglassinc.com"      // Plausible only — already correct
  };

  var provider = (CONFIG.provider || "").toLowerCase().trim();
  if (!provider) return;   // disabled by default: no network, no tracking

  function injectScript(src, attrs) {
    var s = document.createElement("script");
    s.src = src;
    s.defer = true;
    if (attrs) {
      Object.keys(attrs).forEach(function (k) { s.setAttribute(k, attrs[k]); });
    }
    (document.head || document.documentElement).appendChild(s);
    return s;
  }

  if (provider === "ga4" && CONFIG.measurementId) {
    injectScript("https://www.googletagmanager.com/gtag/js?id=" +
      encodeURIComponent(CONFIG.measurementId));
    window.dataLayer = window.dataLayer || [];
    function gtag() { window.dataLayer.push(arguments); }
    gtag("js", new Date());
    gtag("config", CONFIG.measurementId);
  } else if (provider === "plausible" && CONFIG.domain) {
    injectScript("https://plausible.io/js/script.js", { "data-domain": CONFIG.domain });
  }
})();
