/* ClearGlass · content shield — provenance stamping and copy deterrence for
   high-value page regions. Companion to /asset-protection.js, which already
   shields images site-wide; this file covers text and composed layouts. Drop in
   with <script defer src="/cg-content-shield.js"></script>, after
   asset-protection.js. No dependencies. Idempotent — a second include is a
   no-op.

   What it does:
   - Stamps every [data-cg-protect] region with an ownership line and a
     per-session reference token, so a screenshot carries its own provenance.
   - Annotates copied text from protected regions with a source line and a link
     to the reuse terms.
   - Blocks drag-out of protected regions.
   - Veils [data-cg-veil] previews when the tab loses focus or the visitor goes
     idle, and restores them on any interaction.

   On the copy handler: this does not deny the copy. It rewrites the clipboard
   payload to carry the original selection *plus* attribution, which is the only
   reason it calls preventDefault() — that is the sole way to add data to the
   clipboard. The selected text still copies verbatim and in full, so screen
   readers, translation tools, and quote-with-credit workflows are unaffected.

   What it deliberately does NOT do: intercept print, save, view-source, or
   developer tools, or disable text selection. Those are trivially bypassed,
   break assistive technology, and cost more in goodwill than they return in
   protection. /asset-protection.js documents the same boundary. Client-side
   measures are deterrence and provenance, not access control — anything that
   must not be seen belongs behind server-side authentication. */
(function () {
  "use strict";
  if (window.__cgContentShield) return;
  window.__cgContentShield = true;

  var HOLDER = "ClearGlass Inc.";
  var TERMS_URL = "https://www.clearglassinc.com/legal/content-policy.html";
  var PROTECT_SELECTOR = "[data-cg-protect]";
  var VEIL_SELECTOR = "[data-cg-veil]";
  /* Short selections are usually an email address, a product name, or a phone
     number the visitor is copying to actually use. Appending four lines of
     legal boilerplate to those is user-hostile and teaches people to retype
     rather than copy. Only annotate selections long enough to be substantive
     prose. */
  var MIN_COPY_CHARS = 140;
  var IDLE_MS = 60000;

  var stampYear = String(new Date().getFullYear());
  var stampDate = new Date().toISOString().slice(0, 10);
  var reference = sessionReference();

  function sessionReference() {
    /* /asset-protection.js mints this token first when both files are present.
       Reuse it so the page reports one reference, not two. */
    var existing = document.documentElement.dataset.sessionWatermark;
    if (existing) return existing;
    var token;
    if (window.crypto && window.crypto.getRandomValues) {
      var bytes = new Uint8Array(4);
      window.crypto.getRandomValues(bytes);
      token = Array.prototype.map.call(bytes, function (byte) {
        return byte.toString(16).padStart(2, "0");
      }).join("").toUpperCase();
    } else {
      token = Math.random().toString(36).slice(2, 10).toUpperCase();
    }
    document.documentElement.dataset.sessionWatermark = token;
    return token;
  }

  function isEditable(el) {
    return !!(el && el.closest &&
      el.closest("input,textarea,select,[contenteditable=true]"));
  }

  function elementFor(node) {
    if (!node) return null;
    return node.nodeType === 1 ? node : node.parentElement;
  }

  function protectedAncestor(node) {
    var el = elementFor(node);
    return el && el.closest ? el.closest(PROTECT_SELECTOR) : null;
  }

  function sourceUrl() {
    var canonical = document.querySelector('link[rel="canonical"]');
    return canonical && canonical.href
      ? canonical.href
      : location.origin + location.pathname;
  }

  /* ── Visible provenance ────────────────────────────────────────────────
     Both layers are injected as their own absolutely positioned elements
     rather than as ::before/::after on the region. Several of the sections
     these attach to already spend both pseudo-elements on their background
     treatment, and an element can only have one of each. Being out of flow,
     neither layer can shift layout when it lands after first paint. */
  function stampRegions() {
    var regions = document.querySelectorAll(PROTECT_SELECTOR);
    for (var i = 0; i < regions.length; i++) {
      var region = regions[i];
      if (region.__cgStamped) continue;
      region.__cgStamped = true;

      /* Reuse the context-menu shielding asset-protection.js already applies to
         [data-cg-protected] rather than re-registering an equivalent handler.
         Its [data-cg-watermark] corner mark is deliberately left off these
         regions: the .cg-stamp below occupies the same corner and says the
         same thing. */
      if (!region.hasAttribute("data-cg-protected")) {
        region.setAttribute("data-cg-protected", "");
      }

      var mark = document.createElement("span");
      mark.className = "cg-mark";
      mark.setAttribute("aria-hidden", "true");
      region.appendChild(mark);

      /* A <span>, not a <p>: assets/css/glass.css sets `p{color:…!important}`
         site-wide, which would repaint the stamp dark on the dark sections. */
      var stamp = document.createElement("span");
      stamp.className = "cg-stamp";
      stamp.setAttribute("aria-hidden", "true");
      stamp.textContent = "© " + stampYear + " " + HOLDER +
        " · All rights reserved · REF " + reference + " · " + stampDate;
      region.appendChild(stamp);
    }
  }

  /* ── Copy carries its source ───────────────────────────────────────────── */
  function onCopy(e) {
    var selection = window.getSelection();
    if (!selection || selection.isCollapsed || !selection.rangeCount) return;

    var region = protectedAncestor(selection.anchorNode);
    if (!region || isEditable(elementFor(selection.anchorNode))) return;

    var text = selection.toString();
    if (!text || text.trim().length < MIN_COPY_CHARS) return;
    if (!e.clipboardData) return;

    var url = sourceUrl();
    var credit = "© " + stampYear + " " + HOLDER + " All rights reserved.\n" +
      "Source: " + url + " (REF " + reference + ", retrieved " + stampDate + ")\n" +
      "Reuse terms: " + TERMS_URL;

    var wrapper = document.createElement("div");
    try {
      wrapper.appendChild(selection.getRangeAt(0).cloneContents());
    } catch (err) {
      wrapper.textContent = text;
    }
    var cite = document.createElement("p");
    var link = document.createElement("a");
    link.href = url;
    link.textContent = url;
    cite.appendChild(document.createTextNode(
      "© " + stampYear + " " + HOLDER + " All rights reserved. Source: "
    ));
    cite.appendChild(link);
    cite.appendChild(document.createTextNode(
      " (REF " + reference + ", retrieved " + stampDate + "). Reuse terms: "
    ));
    var termsLink = document.createElement("a");
    termsLink.href = TERMS_URL;
    termsLink.textContent = TERMS_URL;
    cite.appendChild(termsLink);
    wrapper.appendChild(cite);

    e.clipboardData.setData("text/plain", text + "\n\n" + credit);
    e.clipboardData.setData("text/html", wrapper.innerHTML);
    /* Required to substitute the payload above. The copy itself still
       succeeds — see the note in the file header. */
    e.preventDefault();
  }

  /* ── Veiled previews ───────────────────────────────────────────────────
     Sensitive previews soften when the visitor's attention leaves the page, so
     a background tab left open on a shared screen is not a standing capture
     target. Any interaction restores them, and keyboard focus inside a preview
     holds it open. Blur is purely visual: nothing is removed from the DOM or
     the accessibility tree, so assistive technology is unaffected. */
  var veils = [];
  var idleTimer = null;

  function setVeiled(on) {
    for (var i = 0; i < veils.length; i++) {
      var veil = veils[i];
      if (on && veil.contains(document.activeElement)) continue;
      veil.classList.toggle("is-veiled", !!on);
    }
  }

  function resetIdle() {
    if (idleTimer) clearTimeout(idleTimer);
    setVeiled(false);
    idleTimer = setTimeout(function () { setVeiled(true); }, IDLE_MS);
  }

  function initVeils() {
    veils = Array.prototype.slice.call(document.querySelectorAll(VEIL_SELECTOR));
    if (!veils.length) return;

    for (var i = 0; i < veils.length; i++) {
      var veil = veils[i];
      if (!veil.hasAttribute("data-cg-veil-label")) {
        veil.setAttribute("data-cg-veil-label", "Preview paused — interact to resume");
      }
    }

    window.addEventListener("blur", function () { setVeiled(true); });
    window.addEventListener("focus", resetIdle);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") setVeiled(true);
      else resetIdle();
    });
    document.addEventListener("focusin", resetIdle);

    var activity = ["pointerdown", "pointermove", "keydown", "wheel", "touchstart"];
    for (var a = 0; a < activity.length; a++) {
      document.addEventListener(activity[a], resetIdle, { passive: true });
    }
    resetIdle();
  }

  function init() {
    stampRegions();

    /* Keep inline rights notices on the same year as the injected stamps. */
    var years = document.querySelectorAll(".cg-year");
    for (var y = 0; y < years.length; y++) years[y].textContent = stampYear;

    document.addEventListener("copy", onCopy);
    document.addEventListener("dragstart", function (e) {
      if (protectedAncestor(e.target)) e.preventDefault();
    });
    initVeils();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
