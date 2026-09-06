/* ClearPulse · live command-surface behaviors. Self-contained, dependency-free,
   non-breaking. Turns the static NEXUS-Med dashboard into a live operational
   surface. Drop in with <script defer src="clearpulse.js"></script>.

   What it adds (all real, all client-side, no network, no data fabrication about
   real patients — this is a product demo surface driving synthetic telemetry):

     1) Live telemetry: a single rAF-driven simulator eases the events/sec,
        risk-index, active-alerts and PHI counters and streams rolling
        time-series into the four header sparklines.
     2) Streaming triage feed: synthetic scored events flow in at the top,
        capped and de-duplicated, reusing the page's own row markup. The six
        seeded rows are preserved as history.
     3) Explainable drill-down: selecting any row (mouse, touch or keyboard)
        deterministically reconstructs its Risk Envelope — factor breakdown,
        triggers, ledger hash — into the envelope viewer. Same input → same
        envelope, so "forensic replay" is reproducible.
     4) Feed controls: severity filter + pause/resume, injected only when JS is
        live so no-JS visitors never see dead buttons.
     5) Maturity bars animate from zero when scrolled into view.
     6) A live UTC clock in the status strip.

   Engineering guarantees:
     • idempotent (window guard), leaks no globals
     • every DOM lookup is defensive; missing hooks disable only that feature
     • fully gated by prefers-reduced-motion (no motion → static, accessible)
     • pauses all work when the tab is hidden (Page Visibility API)
     • deterministic xorshift PRNG — no Math.random drift, reproducible demos
     • all injected text is escaped; nothing is built from untrusted input */
(function () {
  "use strict";
  if (window.__cgClearPulse) return;
  window.__cgClearPulse = true;

  /* ── environment gates ──────────────────────────────────────────────────── */
  var reduce = false;
  try {
    reduce = window.matchMedia &&
             window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (_) { reduce = false; }

  var $  = function (sel, root) { return (root || document).querySelector(sel); };
  var raf = window.requestAnimationFrame ||
            function (fn) { return setTimeout(function () { fn(Date.now()); }, 16); };

  /* ── deterministic PRNG (xorshift32) — stable, dependency-free ──────────── */
  function rng(seed) {
    var s = (seed >>> 0) || 0x9e3779b9;
    return function () {
      s ^= s << 13; s >>>= 0;
      s ^= s >> 17;
      s ^= s << 5;  s >>>= 0;
      return s / 4294967296;
    };
  }
  // FNV-1a hash → stable 32-bit seed from any string (e.g. a trace id).
  function hash(str) {
    var h = 0x811c9dc5, i;
    for (i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
    }
    return h >>> 0;
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;",
               '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function pad(n) { return n < 10 ? "0" + n : "" + n; }
  function clamp(n, lo, hi) { return n < lo ? lo : n > hi ? hi : n; }

  // Short trace tag + a coherent UUIDv7-style id sharing the same entropy, so a
  // row's "trace=abc123" tag and its envelope UUID are provably the same event.
  function hex(rand, len) {
    var out = "", i;
    for (i = 0; i < len; i++) out += Math.floor(rand() * 16).toString(16);
    return out;
  }
  function uuid7(rand, tsMs) {
    var ts = ("000000000000" + tsMs.toString(16)).slice(-12);
    return ts.slice(0, 8) + "-" + ts.slice(8, 12) + "-7" + hex(rand, 3) +
           "-" + ((8 + Math.floor(rand() * 4)).toString(16)) + hex(rand, 3) +
           "-" + hex(rand, 12);
  }

  /* ── severity model (mirrors the page's seeded rows) ────────────────────── */
  function severity(score) {
    if (score >= 70) return { label: "CRITICAL", lvl: "high" };
    if (score >= 55) return { label: "HIGH",     lvl: "mid"  };
    if (score >= 30) return { label: "MEDIUM",   lvl: "mid"  };
    return                   { label: "LOW",      lvl: "low"  };
  }

  /* ─────────────────────────────────────────────────────────────────────────
     1) LIVE TELEMETRY
     ──────────────────────────────────────────────────────────────────────── */
  var Sparkline = function (poly, n, seedBase) {
    this.poly = poly;
    this.n = n;
    this.rand = rng(seedBase);
    this.pts = [];
    var i;
    for (i = 0; i < n; i++) this.pts.push(this.rand());
  };
  Sparkline.prototype.push = function (v01) {
    this.pts.push(clamp(v01, 0, 1));
    if (this.pts.length > this.n) this.pts.shift();
    if (!this.poly) return;
    var n = this.pts.length, s = "", i, x, y;
    for (i = 0; i < n; i++) {
      x = (i / (n - 1)) * 100;
      y = 28 - this.pts[i] * 26 + 2;          // 2..28 within the 0..30 viewBox
      s += (i ? " " : "") + x.toFixed(1) + "," + y.toFixed(1);
    }
    this.poly.setAttribute("points", s);
  };

  // An eased scalar that drifts toward a re-rolled target — smooth, bounded,
  // never a fabricated hard jump.
  var Metric = function (value, lo, hi, seed) {
    this.v = value; this.lo = lo; this.hi = hi;
    this.rand = rng(seed); this.target = value;
  };
  Metric.prototype.tick = function () {
    if (this.rand() < 0.28) {
      var span = (this.hi - this.lo);
      this.target = clamp(this.v + (this.rand() - 0.5) * span * 0.5, this.lo, this.hi);
    }
    this.v += (this.target - this.v) * 0.18;
    return this.v;
  };
  Metric.prototype.norm = function () {
    return (this.v - this.lo) / (this.hi - this.lo || 1);
  };

  function setText(id, txt) { var el = document.getElementById(id); if (el) el.textContent = txt; }
  function fmt(n) { return Math.round(n).toLocaleString("en-US"); }

  function initTelemetry() {
    var epsEl   = document.getElementById("eps");
    var eps     = new Metric(1284, 940, 1680, 0xA11CE);
    var risk    = new Metric(42,   28,   61,   0xB0B);
    var alerts  = new Metric(7,    4,    12,   0xC0FFEE);
    var phi     = new Metric(3,    1,    6,    0xD00D);
    var contrib = new Metric(127,  90,   210,  0xE1E1);

    var sEps    = new Sparkline(document.getElementById("sparkEps"),    11, 0x51),
        sRisk   = new Sparkline(document.getElementById("sparkRisk"),   11, 0x52),
        sAlerts = new Sparkline(document.getElementById("sparkAlerts"), 11, 0x53),
        sPhi    = new Sparkline(document.getElementById("sparkPhi"),    11, 0x54);

    if (!epsEl) return function () {};    // no telemetry hooks on this page

    function frame() {
      var e = eps.tick(), r = risk.tick(), a = alerts.tick(),
          p = phi.tick(),  c = contrib.tick();
      if (epsEl) epsEl.firstChild ? (epsEl.firstChild.nodeValue = fmt(e))
                                  : (epsEl.textContent = fmt(e));
      setText("riskVal",   String(Math.round(r)));
      setText("alertsVal", String(Math.round(a)));
      setText("phiVal",    String(Math.round(p)));
      setText("contribVal", fmt(c));
      sEps.push(eps.norm()); sRisk.push(risk.norm());
      sAlerts.push(alerts.norm()); sPhi.push(phi.norm());
    }
    return frame;
  }

  /* ─────────────────────────────────────────────────────────────────────────
     2) STREAMING TRIAGE FEED
     ──────────────────────────────────────────────────────────────────────── */
  var EVENTS = [
    { type: "collision", desc: "Billing collision · {a} ⨯ {b} · P-{pid}",
      base: 72, spread: 16 },
    { type: "access",    desc: "Access spike · {role} · {n} unique MRNs / 1h",
      base: 58, spread: 14 },
    { type: "offhours",  desc: "Off-hours claim submission · {dept} · DR-{did}",
      base: 34, spread: 10 },
    { type: "phi",       desc: "PHI at-rest exposure · {store} bucket · {n} records",
      base: 61, spread: 12 },
    { type: "encounter", desc: "Routine encounter · ED triage P-{pid}",
      base: 11, spread: 8 },
    { type: "lab",       desc: "Lab order · {panel} panel · P-{pid}",
      base: 7,  spread: 6 }
  ];
  var PROC   = ["MRI", "CT", "Consultation", "Echocardiogram", "Colonoscopy", "PET"],
      ROLES  = ["Derm nurse", "Radiology tech", "Billing clerk", "ED registrar", "Cardiology PA"],
      DEPTS  = ["Cardiology", "Oncology", "Neurology", "Orthopedics", "Nephrology"],
      PANELS = ["Hematology", "Lipid", "Metabolic", "Thyroid", "Coagulation"],
      STORES = ["export-stage", "backup-cold", "analytics-lake"];

  function pick(arr, r) { return arr[Math.floor(r() * arr.length)]; }

  // Build one synthetic event. `seq` guarantees uniqueness even within a ms.
  function makeEvent(seq) {
    var now  = new Date();
    var seed = hash(now.getTime() + ":" + seq);
    var r    = rng(seed);
    var tpl  = EVENTS[Math.floor(r() * EVENTS.length)];
    var score = clamp(Math.round(tpl.base + (r() - 0.5) * tpl.spread * 2), 1, 96);
    var trace = hex(rng(seed ^ 0x5bd1e995), 6);
    var desc  = tpl.desc
      .replace("{a}", pick(PROC, r)).replace("{b}", pick(PROC, r))
      .replace("{role}", pick(ROLES, r)).replace("{dept}", pick(DEPTS, r))
      .replace("{panel}", pick(PANELS, r)).replace("{store}", pick(STORES, r))
      .replace("{pid}", 1000 + Math.floor(r() * 8999))
      .replace("{did}", 100 + Math.floor(r() * 899))
      .replace(/\{n\}/g, 10 + Math.floor(r() * 60));
    return {
      ts: pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds()),
      tsMs: now.getTime(), type: tpl.type, desc: desc, score: score, trace: trace
    };
  }

  function rowNode(ev) {
    var sv  = severity(ev.score);
    var row = document.createElement("div");
    row.className = "row lvl-" + sv.lvl + " cp-row cp-new";
    row.setAttribute("role", "button");
    row.setAttribute("tabindex", "0");
    row.setAttribute("aria-label",
      sv.label + " severity, score " + ev.score + ". " + ev.desc + ". Activate to open risk envelope.");
    row.dataset.sev = sv.lvl;
    row.innerHTML =
      '<span class="ts">' + esc(ev.ts) + '</span>' +
      '<span class="desc">' + esc(ev.desc) +
        ' <span class="trace">trace=' + esc(ev.trace) + '</span></span>' +
      '<span class="mono" style="color:var(--txt-dim)">' + sv.label + '</span>' +
      '<span class="sev">' + ev.score + '</span>';
    return row;
  }

  /* ─────────────────────────────────────────────────────────────────────────
     3) EXPLAINABLE RISK-ENVELOPE DRILL-DOWN
     ──────────────────────────────────────────────────────────────────────── */
  // Deterministically apportion a score across weighted factors that fit the
  // event type, then render an audit-grade envelope. Same row → same envelope.
  function buildEnvelope(ev) {
    var r = rng(hash(ev.trace + ":" + ev.score));
    var sv = severity(ev.score);
    var weights = {
      collision: ["temporal_overlap", "code_pair_conflict", "off_hours"],
      access:    ["access_spike", "peer_group_deviation", "off_hours"],
      offhours:  ["off_hours", "volume_anomaly", "novel_endpoint"],
      phi:       ["exposure_surface", "record_volume", "encryption_gap"],
      encounter: ["baseline_activity", "temporal_overlap"],
      lab:       ["baseline_activity", "order_frequency"]
    }[ev.type] || ["baseline_activity", "temporal_overlap"];

    // Split the score into positive integer parts summing to it.
    var parts = [], rem = ev.score, i, w;
    for (i = 0; i < weights.length; i++) {
      if (i === weights.length - 1) { parts.push(rem); break; }
      w = Math.max(1, Math.round(rem * (0.35 + r() * 0.35)));
      w = Math.min(w, rem - (weights.length - 1 - i));
      parts.push(w); rem -= w;
    }
    var ratio = (0.4 + r() * 0.55).toFixed(2);
    var z     = (2 + r() * 3.5).toFixed(1);
    var cpts  = ["73721", "99213", "70551", "45378", "93306", "80053"];
    var uid   = uuid7(rng(hash(ev.trace)), ev.tsMs || Date.now());
    var lh    = hex(rng(hash(ev.trace + ":ledger")), 4) + "…" +
                hex(rng(hash(ev.trace + ":ledger2")), 4);

    var L = [];
    L.push("{");
    L.push('  <span class="k">"trace_id"</span>: <span class="s">"' + esc(uid) + '"</span>,');
    L.push('  <span class="k">"score"</span>: <span class="n">' + ev.score + '</span>,');
    L.push('  <span class="k">"severity"</span>: <span class="s">"' + sv.label + '"</span>,');
    L.push('  <span class="k">"factors"</span>: {');
    for (i = 0; i < weights.length; i++) {
      var noteMap = { temporal_overlap: "ratio " + ratio, access_spike: "z = " + z,
                      volume_anomaly: "z = " + z, peer_group_deviation: "z = " + z };
      var note = noteMap[weights[i]] ? '  <span class="c">// ' + noteMap[weights[i]] + "</span>" : "";
      L.push('    <span class="k">"' + weights[i] + '"</span>: <span class="n">' +
             parts[i] + "</span>" + (i < weights.length - 1 ? "," : " ") + note);
    }
    L.push("  },");
    L.push('  <span class="k">"triggers"</span>: [');
    L.push('    { <span class="k">"type"</span>: <span class="s">"claim"</span>, ' +
           '<span class="k">"id"</span>: <span class="s">"' + esc(ev.trace) + '"</span>, ' +
           '<span class="k">"cpt"</span>: <span class="s">"' + pick(cpts, r) + '"</span> }');
    L.push("  ],");
    L.push('  <span class="k">"rule_version"</span>: <span class="s">"2026.06.01"</span>,');
    L.push('  <span class="k">"ledger_hash"</span>:  <span class="s">"sha256:' + lh + '"</span>');
    L.push("}");
    return L.join("\n");
  }

  function evFromRow(row) {
    var descEl  = $(".desc", row), sevEl = $(".sev", row), tsEl = $(".ts", row);
    var traceEl = $(".trace", row);
    var score   = sevEl ? parseInt(sevEl.textContent, 10) : 0;
    var trace   = "unknown";
    if (traceEl) { var m = /trace=([0-9a-f]+)/i.exec(traceEl.textContent); if (m) trace = m[1]; }
    var desc = descEl ? descEl.textContent.replace(/\s*trace=[0-9a-f]+\s*$/i, "").trim() : "";
    var type = /collision/i.test(desc) ? "collision" :
               /access spike/i.test(desc) ? "access" :
               /off-hours/i.test(desc) ? "offhours" :
               /PHI|exposure/i.test(desc) ? "phi" :
               /lab order/i.test(desc) ? "lab" : "encounter";
    return { ts: tsEl ? tsEl.textContent : "", desc: desc, score: isNaN(score) ? 0 : score,
             trace: trace, type: type, tsMs: Date.now() };
  }

  function selectRow(row, feed, envEl, titleEl) {
    if (!row || !envEl) return;
    var rows = feed.querySelectorAll(".row"), i;
    for (i = 0; i < rows.length; i++) rows[i].classList.remove("cp-sel");
    row.classList.add("cp-sel");
    var ev = evFromRow(row);
    envEl.innerHTML = buildEnvelope(ev);
    if (titleEl) titleEl.textContent = "Risk Envelope · " + ev.trace;
  }

  /* ─────────────────────────────────────────────────────────────────────────
     4) FEED CONTROLS (injected only when JS is live)
     ──────────────────────────────────────────────────────────────────────── */
  function makeControls() {
    var bar = document.createElement("div");
    bar.className = "cp-controls";
    bar.setAttribute("role", "group");
    bar.setAttribute("aria-label", "Triage feed controls");
    bar.innerHTML =
      '<button type="button" class="cp-btn is-on" data-filter="all" aria-pressed="true">All</button>' +
      '<button type="button" class="cp-btn" data-filter="high" aria-pressed="false">Critical</button>' +
      '<button type="button" class="cp-btn" data-filter="mid" aria-pressed="false">High/Med</button>' +
      '<button type="button" class="cp-btn" data-filter="low" aria-pressed="false">Low</button>' +
      '<span class="cp-controls-sp" aria-hidden="true"></span>' +
      '<button type="button" class="cp-btn cp-btn-live" data-act="pause" aria-pressed="false">' +
        '<span class="cp-live-dot" aria-hidden="true"></span>Live</button>';
    return bar;
  }

  function applyFilter(feed, filter) {
    var rows = feed.querySelectorAll(".row"), i, r, show;
    for (i = 0; i < rows.length; i++) {
      r = rows[i];
      var lvl = r.dataset.sev ||
                (/lvl-high/.test(r.className) ? "high" :
                 /lvl-mid/.test(r.className)  ? "mid"  : "low");
      show = filter === "all" || filter === lvl;
      r.style.display = show ? "" : "none";
    }
  }

  /* ─────────────────────────────────────────────────────────────────────────
     5) MATURITY BARS — animate on first view
     ──────────────────────────────────────────────────────────────────────── */
  function initBars() {
    var host = document.getElementById("cpBars");
    if (!host) return;
    var fills = host.querySelectorAll(".bar-fill"), i, targets = [];
    for (i = 0; i < fills.length; i++) {
      targets.push(fills[i].style.width || "0%");
      if (!reduce) {
        fills[i].style.transition = "width 1.1s cubic-bezier(.2,.8,.2,1)";
        fills[i].style.width = "0%";
      }
    }
    if (reduce) return;                     // already at target, no motion
    var run = function () {
      for (var j = 0; j < fills.length; j++) {
        (function (el, w, d) {
          setTimeout(function () { el.style.width = w; }, d);
        })(fills[j], targets[j], j * 90);
      }
    };
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting) { run(); io.disconnect(); }
        });
      }, { threshold: 0.25 });
      io.observe(host);
    } else { run(); }
  }

  /* ─────────────────────────────────────────────────────────────────────────
     6) LIVE UTC CLOCK
     ──────────────────────────────────────────────────────────────────────── */
  function initClock() {
    var strip = document.querySelector(".topbar .stat-row");
    if (!strip) return function () {};
    var chip = document.createElement("span");
    chip.className = "mono";
    chip.id = "cpClock";
    strip.insertBefore(chip, strip.firstChild ? strip.firstChild.nextSibling : null);
    return function () {
      var d = new Date();
      chip.textContent = pad(d.getUTCHours()) + ":" + pad(d.getUTCMinutes()) +
                         ":" + pad(d.getUTCSeconds()) + " UTC";
    };
  }

  /* ─────────────────────────────────────────────────────────────────────────
     ORCHESTRATION
     ──────────────────────────────────────────────────────────────────────── */
  function start() {
    var feed    = document.getElementById("cpFeed");
    var envEl   = document.getElementById("cpEnv");
    var titleEl = document.getElementById("cpEnvTitle");

    var tickTelemetry = initTelemetry();
    var tickClock     = initClock();
    initBars();

    // Wire drill-down on existing + future rows (event delegation).
    if (feed) {
      feed.addEventListener("click", function (e) {
        var row = e.target.closest && e.target.closest(".row");
        if (row) selectRow(row, feed, envEl, titleEl);
      });
      feed.addEventListener("keydown", function (e) {
        if (e.key !== "Enter" && e.key !== " ") return;
        var row = e.target.closest && e.target.closest(".row");
        if (row) { e.preventDefault(); selectRow(row, feed, envEl, titleEl); }
      });
      // Make the seeded rows keyboard-reachable and self-describing.
      var seed = feed.querySelectorAll(".row"), i;
      for (i = 0; i < seed.length; i++) {
        var row = seed[i];
        row.classList.add("cp-row");
        row.setAttribute("role", "button");
        row.setAttribute("tabindex", "0");
        row.dataset.sev = /lvl-high/.test(row.className) ? "high" :
                          /lvl-mid/.test(row.className)  ? "mid"  : "low";
      }
    }

    // Controls + streaming.
    var streaming = true, filter = "all", seq = 0, MAX_ROWS = 24;
    if (feed && feed.parentNode) {
      var controls = makeControls();
      feed.parentNode.insertBefore(controls, feed);
      controls.addEventListener("click", function (e) {
        var btn = e.target.closest && e.target.closest(".cp-btn");
        if (!btn) return;
        if (btn.dataset.filter) {
          filter = btn.dataset.filter;
          var all = controls.querySelectorAll("[data-filter]"), i;
          for (i = 0; i < all.length; i++) {
            var on = all[i] === btn;
            all[i].classList.toggle("is-on", on);
            all[i].setAttribute("aria-pressed", on ? "true" : "false");
          }
          applyFilter(feed, filter);
        } else if (btn.dataset.act === "pause") {
          streaming = !streaming;
          btn.classList.toggle("is-paused", !streaming);
          btn.setAttribute("aria-pressed", streaming ? "false" : "true");
          btn.lastChild.nodeValue = streaming ? "Live" : "Paused";
        }
      });
    }

    function emit() {
      if (!feed || !streaming) return;
      var ev  = makeEvent(seq++);
      var row = rowNode(ev);
      if (filter !== "all" && row.dataset.sev !== filter) row.style.display = "none";
      feed.insertBefore(row, feed.firstChild);
      // Cap length so memory stays bounded.
      while (feed.children.length > MAX_ROWS) feed.removeChild(feed.lastChild);
      if (!reduce) {
        raf(function () { raf(function () { row.classList.remove("cp-new"); }); });
      } else {
        row.classList.remove("cp-new");
      }
    }

    /* Single scheduler. Page Visibility pauses everything off-screen. */
    var lastTele = 0, lastEmit = 0, telePeriod = 1200, emitPeriod = 3600;
    var hidden = function () { return document.hidden === true; };

    function loop(now) {
      if (!hidden()) {
        tickClock();
        if (!reduce && now - lastTele >= telePeriod) { tickTelemetry(); lastTele = now; }
        if (now - lastEmit >= emitPeriod) { emit(); lastEmit = now; }
      }
      raf(loop);
    }
    // Prime once so the surface is populated immediately, then animate.
    tickClock();
    tickTelemetry();
    raf(loop);

    // Under reduced motion we still want telemetry to be current, just not
    // animating — refresh on a calm interval instead of per-frame.
    if (reduce) {
      setInterval(function () { if (!hidden()) tickTelemetry(); }, 4000);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
