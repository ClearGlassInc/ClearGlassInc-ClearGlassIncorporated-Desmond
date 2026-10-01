/* ClearGlass · site-wide privacy analytics loader.
   ───────────────────────────────────────────────────────────────────────────
   PURPOSE: one place to switch on website analytics so you can finally SEE
   visitors, traffic sources, and store clicks. Loaded on every page via
   /stealth-glass.js (and on campaign landing pages via cg-attribution.js), so
   configuring it here turns analytics on site-wide.

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
   Plausible is cookieless and needs no consent banner.
   NOTE: _headers carries a Content-Security-Policy whose script-src and
   connect-src name neither provider. GitHub Pages ignores _headers; any host
   that honours it would block analytics until the provider is added there.

   Once on, it also reports the funnel events listed under "Funnel events"
   below (CTA, booking, checkout, contact and form steps), tagged with the
   tab's campaign code. Campaign landing pages that do not load
   /stealth-glass.js get this file from /assets/js/cg-attribution.js. */
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

  var emit = null;
  if (provider === "ga4" && CONFIG.measurementId) {
    injectScript("https://www.googletagmanager.com/gtag/js?id=" +
      encodeURIComponent(CONFIG.measurementId));
    window.dataLayer = window.dataLayer || [];
    var gtag = function () { window.dataLayer.push(arguments); };
    gtag("js", new Date());
    gtag("config", CONFIG.measurementId);
    emit = function (name, props) { gtag("event", name, props); };
  } else if (provider === "plausible" && CONFIG.domain) {
    injectScript("https://plausible.io/js/script.js", { "data-domain": CONFIG.domain });
    // Plausible's documented queue, so events fired before the script loads are kept.
    window.plausible = window.plausible ||
      function () { (window.plausible.q = window.plausible.q || []).push(arguments); };
    emit = function (name, props) { window.plausible(name, { props: props }); };
  }
  if (!emit) return;

  // ── Funnel events ──────────────────────────────────────────────────────────
  // The pre-payment stages of docs/GROWTH_REVENUE_OS.md, so a provider shows
  // where visitors move and stop. Properties are the page path, where a link
  // goes (host and path only: a mailto body or payment-link query can hold an
  // email address) and the tab's last campaign code, kept by
  // /assets/js/cg-attribution.js. Never a name, an email or form contents.
  // Payment itself is measured by the control plane's ledger, not here.
  var FUNNEL = {
    offer_view: 1, cta_click: 1, form_start: 1, form_submit: 1, booking_start: 1,
    checkout_start: 1, contact_request: 1, outbound_click: 1, download: 1, lead_recorded: 1
  };
  var CHECKOUT_HOSTS = { "buy.stripe.com": 1, "checkout.stripe.com": 1, "www.paypal.com": 1 };
  var BUYING_PATH = /^\/(offers\/[^/]+\.html|store\.html|pricing\.html|checkout\/|revenue-command\.html)/;

  function lastCampaign() {
    try {
      var touch = JSON.parse(window.sessionStorage.getItem("cg-utm-last") || "null");
      return touch && typeof touch.campaign === "string" ? touch.campaign : null;
    } catch (e) { return null; }
  }

  function send(name, props) {
    if (!FUNNEL[name]) return;
    props = props || {};
    props.page = location.pathname;
    var campaign = lastCampaign();
    if (campaign) props.campaign = campaign;
    try { emit(name, props); } catch (e) { /* measurement never breaks the page */ }
  }

  function classify(href) {
    var url;
    try { url = new URL(href, location.href); } catch (e) { return null; }
    if (url.protocol === "mailto:" || url.protocol === "tel:") return ["contact_request", {}];
    if (url.protocol !== "https:" && url.protocol !== "http:") return null;
    var host = url.hostname;
    if (host === "calendly.com" || /\.calendly\.com$/.test(host)) {
      return ["booking_start", { target: host + url.pathname }];
    }
    if (CHECKOUT_HOSTS[host]) return ["checkout_start", { target: host }];
    if (host !== location.hostname) return ["outbound_click", { target: host }];
    if (/\.(pdf|zip|csv|xlsx|docx|pptx)$/i.test(url.pathname)) return ["download", { target: url.pathname }];
    if (BUYING_PATH.test(url.pathname) && url.pathname !== location.pathname) {
      return ["cta_click", { target: url.pathname }];
    }
    return null;
  }

  function formLabel(form) {
    return form.id || (form.getAttribute && form.getAttribute("action") ? "relay" : "inline");
  }

  document.addEventListener("click", function (event) {
    var link = event.target && event.target.closest ? event.target.closest("a[href]") : null;
    var hit = link ? classify(link.getAttribute("href")) : null;
    if (hit) send(hit[0], hit[1]);
  }, true);

  var started = [];
  document.addEventListener("focusin", function (event) {
    var form = event.target && event.target.form;
    if (!form || started.indexOf(form) > -1) return;
    started.push(form);
    send("form_start", { form: formLabel(form) });
  }, true);

  document.addEventListener("submit", function (event) {
    if (event.target && event.target.tagName === "FORM") send("form_submit", { form: formLabel(event.target) });
  }, true);

  // A page reports a stage only it can see (a lead the API accepted) by
  // dispatching cg:funnel with a stage name. Only the name is read.
  document.addEventListener("cg:funnel", function (event) {
    var name = event.detail && event.detail.name;
    if (typeof name === "string") send(name, {});
  });

  if (/^\/offers\/[^/]+\.html$/.test(location.pathname) && !/thank-you\.html$/.test(location.pathname)) {
    send("offer_view", {});
  }
})();
