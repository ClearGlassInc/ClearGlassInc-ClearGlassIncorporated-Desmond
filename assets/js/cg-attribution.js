/* ClearGlass · campaign attribution, first party and session scoped.
   ───────────────────────────────────────────────────────────────────────────
   A campaign link carries utm_source / utm_medium / utm_campaign
   (tools/campaign_registry.py builds them). The lead form on
   /revenue-command.html sends those tags to POST /revenue/leads, and the
   control plane carries them through checkout onto the paid order
   (control-plane/app/attribution.py). Before this file, only the lead page
   itself read the tags, so a visitor who arrived on an offer page from an ad
   and then clicked through to the form was recorded as "direct".

   This runs on every campaign landing page and remembers two touches for the
   life of the tab:
     cg-utm-first  the first page this tab opened on the site (tagged or not)
     cg-utm-last   the most recent arrival that carried campaign tags

   What it keeps: the three tags, the landing path (no query string), and the
   external referrer's host name. Nothing else, and no cookies. It sends
   nothing anywhere; it only makes sure /analytics.js is loaded, which stays
   off until the owner sets a provider. sessionStorage ends with the tab,
   which is what the privacy notice discloses (legal/privacy.html section 10).
   Values that are not campaign tags are dropped, using the same rule as
   attribution.py, so free text or personal data cannot ride along into the
   lead or Stripe metadata. */
(function () {
  "use strict";
  if (window.CGAttribution) return;

  var FIRST = "cg-utm-first";
  var LAST = "cg-utm-last";
  // Mirrors control-plane/app/attribution.py _VALUE.
  var TAG = /^[A-Za-z0-9._\-]{1,120}$/;

  function storage() {
    try { return window.sessionStorage || null; } catch (e) { return null; }
  }

  function read(key) {
    var s = storage();
    if (!s) return null;
    try {
      var value = JSON.parse(s.getItem(key) || "null");
      return value && typeof value === "object" ? value : null;
    } catch (e) { return null; }
  }

  function write(key, value) {
    var s = storage();
    if (!s) return;
    try { s.setItem(key, JSON.stringify(value)); } catch (e) { /* full or blocked: stay unattributed */ }
  }

  function tag(params, key) {
    var value = params ? String(params.get(key) || "").trim() : "";
    return TAG.test(value) ? value : null;
  }

  function site(host) { return String(host || "").replace(/^www\./, ""); }

  function externalHost(referrer) {
    try {
      var url = new URL(referrer);
      if (url.protocol !== "https:" && url.protocol !== "http:") return null;
      // clearglassinc.com and www.clearglassinc.com are one site, not a referral.
      return site(url.hostname) === site(location.hostname) ? null : url.hostname;
    } catch (e) { return null; }
  }

  var params = null;
  try { params = new URLSearchParams(location.search); } catch (e) { /* very old browser */ }

  var touch = {
    source: tag(params, "utm_source"),
    medium: tag(params, "utm_medium"),
    campaign: tag(params, "utm_campaign"),
    landing_page: location.pathname,
    referrer: externalHost(document.referrer || "")
  };

  if (!read(FIRST)) write(FIRST, touch);
  if (touch.source || touch.medium || touch.campaign) write(LAST, touch);

  /** The attribution fields of a POST /revenue/leads body. */
  function leadFields() {
    var first = read(FIRST) || {};
    var last = read(LAST) || {};
    var landing = typeof first.landing_page === "string" && first.landing_page.charAt(0) === "/"
      ? first.landing_page : location.pathname;
    return {
      source: last.source || first.source || (first.referrer ? "referral" : "direct"),
      landing_page: location.origin + landing,
      referrer: first.referrer || null,
      utm_first_source: first.source || null,
      utm_first_medium: first.medium || null,
      utm_first_campaign: first.campaign || null,
      utm_last_source: last.source || null,
      utm_last_medium: last.medium || null,
      utm_last_campaign: last.campaign || null
    };
  }

  window.CGAttribution = {
    first: function () { return read(FIRST); },
    last: function () { return read(LAST); },
    leadFields: leadFields
  };

  // A landing page must also be measurable. /analytics.js stays off until the
  // owner sets a provider; this only makes sure the pages that do not load
  // /stealth-glass.js (which injects it everywhere else) load it too.
  try {
    if (!window.__cgAnalytics && !document.querySelector("script[data-cg-analytics]")) {
      var loader = document.createElement("script");
      loader.src = "/analytics.js";
      loader.defer = true;
      loader.setAttribute("data-cg-analytics", "");
      (document.head || document.documentElement).appendChild(loader);
    }
  } catch (e) { /* no DOM to attach to */ }
})();
