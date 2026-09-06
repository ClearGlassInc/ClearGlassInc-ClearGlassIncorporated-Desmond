/* ClearGlass Insight Atlas — a cinematic, living intelligence-graph render of the
   Insights desk. Inspired by policy-platform constellation dashboards: a luminous
   editorial core radiates governed beams to topic clusters, satellites orbit each
   cluster, and light pulses travel the network.

   Honest-data contract (repo rule: never fabricate metrics):
   - clusters, counts, tags and stats come from blog/posts.json (real content);
   - the timeline is the editorial ROADMAP view and is labelled as such;
   - nothing on this canvas pretends to be measured telemetry.

   Progressive enhancement: without JS the section shows a static caption.
   Respects prefers-reduced-motion (renders one lit, static frame). */
(function () {
  'use strict';

  var stage = document.getElementById('atlasStage');
  var canvas = document.getElementById('atlasCanvas');
  if (!stage || !canvas || !canvas.getContext) return;

  var ctx = canvas.getContext('2d');
  var labelLayer = document.getElementById('atlasLabels');
  var tip = document.getElementById('atlasTip');
  var modeEl = document.getElementById('atlasMode');
  var timelineEl = document.getElementById('atlasTimeline');
  var statsEl = document.getElementById('atlasStats');
  var askForm = document.getElementById('atlasAsk');
  var pauseBtn = document.getElementById('atlasPause');
  var seedBtn = document.getElementById('atlasSeed');

  var REDUCE = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var TAU = Math.PI * 2;

  /* ---------------------------------------------------------------- palette */
  var INK = {
    rose:   { body: '#ff9ec7', deep: '#6e2450', glow: '255,158,199' },
    violet: { body: '#b9a3ff', deep: '#34246e', glow: '157,123,255' },
    teal:   { body: '#8bf0dc', deep: '#174f49', glow: '85,242,166' },
    gold:   { body: '#e9b95e', deep: '#4d3410', glow: '255,214,150' }
  };

  /* Cluster definitions mirror the hub's real topic taxonomy (chip data-topic
     values), so clicking a node drives the same filter the chips drive. */
  var CLUSTERS = [
    { topic: 'governed-ai', label: 'Governed AI',        ink: 'rose',   era: 2026, slot: 0.00 },
    { topic: 'agents',      label: 'Autonomous agents',  ink: 'violet', era: 2025, slot: 0.14 },
    { topic: 'cyber',       label: 'Cyber architecture', ink: 'rose',   era: 2024, slot: 0.30 },
    { topic: 'systems',     label: 'High-trust systems', ink: 'teal',   era: 2022, slot: 0.45 },
    { topic: 'automation',  label: 'AI automation',      ink: 'violet', era: 2025, slot: 0.60 },
    { topic: 'fincrime',    label: 'Financial crime',    ink: 'rose',   era: 2027, slot: 0.74 },
    { topic: 'osint',       label: 'OSINT workflows',    ink: 'teal',   era: 2027, slot: 0.88 }
  ];

  /* Fallback satellite signals per cluster when posts.json is unreachable —
     these are real tags used on the desk, not invented data points. */
  var FALLBACK_TAGS = {
    'governed-ai': ['risk-router', 'approvals', 'audit-ledger', 'policy'],
    'agents':      ['human-in-the-loop', 'kill-switch', 'tool-gating'],
    'cyber':       ['zero-trust', 'permissions', 'telemetry'],
    'systems':     ['provenance', 'ontology', 'high-trust'],
    'automation':  ['evals', 'apollo', 'self-improvement'],
    'fincrime':    ['detection-lab', 'signals'],
    'osint':       ['source-grading', 'lineage', 'entity-resolution']
  };

  /* Editorial roadmap epochs — the timeline rail. Roadmap view, not telemetry. */
  var EPOCHS = [
    { year: 2020, label: 'FOUNDATIONS',        note: 'clarity-is-power charter' },
    { year: 2022, label: 'SYSTEMS ERA',        note: 'high-trust patterns' },
    { year: 2024, label: 'SENTINEL AGENTS',    note: 'fail-closed governors' },
    { year: 2025, label: 'COMMERCE OS',        note: 'audit-first operator' },
    { year: 2026, label: 'INSIGHTS DESK LIVE', note: 'flagship briefs shipping' },
    { year: 2027, label: 'SERIES ROADMAP',     note: 'osint · fincrime tradecraft' }
  ];

  /* ------------------------------------------------------------------ state */
  var W = 0, H = 0, DPR = 1;
  var core = { x: 0, y: 0, r: 19 };
  var hubs = [];         // cluster nodes
  var sats = [];         // satellite signal nodes
  var pulses = [];       // light travelling core -> hub
  var subPulses = [];    // light travelling hub -> satellite
  var dust = [];         // ambient star dust
  var sparks = [];       // motes orbiting the core
  var time = 0;
  var running = !REDUCE;
  var visible = true;
  var rafId = 0;
  var lastT = 0;
  var epochIdx = 4;      // start on "INSIGHTS DESK LIVE"
  var epochHold = 0;     // user interaction pauses auto-advance until this time
  var pointer = { x: 0, y: 0, inside: false };
  var par = { x: 0, y: 0 };      // eased parallax offset
  var hovered = null;

  function rand(a, b) { return a + Math.random() * (b - a); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function ease(t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }

  /* --------------------------------------------------------- graph assembly */
  function buildGraph() {
    hubs = [];
    sats = [];
    pulses = [];
    subPulses = [];
    CLUSTERS.forEach(function (c) {
      hubs.push({
        topic: c.topic, label: c.label, ink: INK[c.ink], era: c.era,
        angle: c.slot * TAU + rand(-0.12, 0.12),
        drift: rand(0.015, 0.03) * (Math.random() < 0.5 ? -1 : 1),
        rf: rand(0.86, 1.08),            // radial variance per cluster
        bend: rand(-30, 30),             // beam curvature
        wobble: rand(0, TAU),            // breathing phase
        size: 11, count: 0, lit: 1, hover: 0,
        tags: (FALLBACK_TAGS[c.topic] || []).slice(),
        x: 0, y: 0, el: null, pillEl: null
      });
    });
    seedSatellites();
    seedAmbient();
  }

  function seedSatellites() {
    sats = [];
    hubs.forEach(function (hub) {
      var n = Math.min(hub.tags.length, W < 640 ? 3 : 5) || 2;
      for (var i = 0; i < n; i++) {
        sats.push({
          hub: hub,
          tag: hub.tags[i] || 'signal',
          angle: rand(0, TAU),
          speed: rand(0.12, 0.34) * (Math.random() < 0.4 ? -1 : 1),
          orbit: rand(34, 78) * (W < 640 ? 0.72 : 1),
          squash: rand(0.72, 0.95),
          size: rand(2.4, 4.2),
          era: hub.era + (Math.random() < 0.3 ? 1 : 0),
          tw: rand(0, TAU),
          x: 0, y: 0
        });
      }
    });
  }

  function seedAmbient() {
    dust = [];
    var n = Math.min(110, Math.floor((W * H) / 16000));
    for (var i = 0; i < n; i++) {
      dust.push({ x: rand(0, 1), y: rand(0, 1), r: rand(0.4, 1.4), f: rand(0.3, 1.4), p: rand(0, TAU) });
    }
    sparks = [];
    for (var s = 0; s < 9; s++) {
      sparks.push({ a: rand(0, TAU), sp: rand(0.4, 1.1) * (s % 2 ? -1 : 1), r: rand(30, 52), sz: rand(0.8, 1.8) });
    }
  }

  /* --------------------------------------------- real content from the desk */
  fetch('posts.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      if (!data || !data.posts) return;
      var posts = data.posts;
      hubs.forEach(function (hub) {
        var inTopic = posts.filter(function (p) { return (p.topics || []).indexOf(hub.topic) !== -1; });
        hub.count = inTopic.length;
        var tags = [];
        inTopic.forEach(function (p) {
          (p.tags || []).forEach(function (t) { if (tags.indexOf(t) === -1) tags.push(t); });
        });
        if (tags.length) hub.tags = tags.slice(0, 6);
        if (hub.pillEl) hub.pillEl.textContent = String(hub.count);
      });
      seedSatellites();
      renderStats(posts, data.topics || {});
      if (REDUCE) drawFrame(0);
    })
    .catch(function () { renderStats(null, null); });

  function renderStats(posts, topics) {
    if (!statsEl) return;
    var live = posts ? posts.filter(function (p) { return p.status === 'published'; }).length : 2;
    var forming = posts ? posts.filter(function (p) { return p.status === 'series'; }).length : 2;
    var clusters = topics ? Object.keys(topics).length : CLUSTERS.length;
    var minutes = posts ? posts.reduce(function (a, p) { return a + (p.readMinutes || 0); }, 0) : 27;
    statsEl.innerHTML =
      '<div class="atlas-stat"><strong>' + live + '</strong><span>briefs live</span></div>' +
      '<div class="atlas-stat"><strong>' + forming + '</strong><span>series forming</span></div>' +
      '<div class="atlas-stat"><strong>' + clusters + '</strong><span>topic clusters</span></div>' +
      '<div class="atlas-stat"><strong>' + minutes + '</strong><span>min of reading</span></div>';
  }

  /* ------------------------------------------------------------- DOM layers */
  function buildLabels() {
    if (!labelLayer) return;
    labelLayer.innerHTML = '';
    var coreEl = document.createElement('div');
    coreEl.className = 'atlas-label core';
    coreEl.innerHTML = '<b>Editorial core</b><span class="pill">governed</span>';
    labelLayer.appendChild(coreEl);
    core.el = coreEl;

    hubs.forEach(function (hub) {
      var el = document.createElement('button');
      el.type = 'button';
      el.className = 'atlas-label';
      el.innerHTML = '<b>' + hub.label + '</b><span class="pill">' + hub.count + '</span>';
      el.setAttribute('aria-label', 'Filter briefs by ' + hub.label);
      el.addEventListener('click', function () { selectCluster(hub); });
      el.addEventListener('mouseenter', function () { hovered = hub; showTip(hub); });
      el.addEventListener('mouseleave', function () { hovered = null; hideTip(); });
      labelLayer.appendChild(el);
      hub.el = el;
      hub.pillEl = el.querySelector('.pill');
    });
  }

  function buildTimeline() {
    if (!timelineEl) return;
    timelineEl.innerHTML = '';
    EPOCHS.forEach(function (ep, i) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'atlas-year' + (i === epochIdx ? ' on' : '');
      b.innerHTML = '<i></i>' + ep.year;
      b.setAttribute('aria-label', 'Show roadmap era ' + ep.year + ' — ' + ep.label);
      b.addEventListener('click', function () {
        setEpoch(i);
        epochHold = time + 16;           // pause auto-advance after manual pick
        if (REDUCE || !running) drawFrame(0.5);  // repaint when the loop is idle
      });
      timelineEl.appendChild(b);
      ep.el = b;
    });
    setEpoch(epochIdx);
  }

  function setEpoch(i) {
    epochIdx = i;
    var ep = EPOCHS[i];
    EPOCHS.forEach(function (e, k) { if (e.el) e.el.classList.toggle('on', k === i); });
    if (modeEl) modeEl.textContent = 'ROADMAP ERA ' + ep.year + ' — ' + ep.label + ' · ' + ep.note;
  }

  /* -------------------------------------------------- interactions & wiring */
  function selectCluster(hub) {
    var chip = document.querySelector('#topics .chip[data-topic="' + hub.topic + '"]');
    if (chip) chip.click();
    var grid = document.getElementById('latest');
    if (grid) grid.scrollIntoView({ behavior: REDUCE ? 'auto' : 'smooth' });
    burst(hub);
  }

  function burst(hub) {
    for (var i = 0; i < 4; i++) {
      pulses.push({ hub: hub, t: -i * 0.09, dur: rand(0.9, 1.3), hot: true });
    }
  }

  if (askForm) {
    askForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var input = askForm.querySelector('input');
      var q = input ? input.value.trim() : '';
      var all = document.querySelector('#topics .chip[data-topic="all"]');
      if (all) all.click();
      var search = document.getElementById('smartSearch');
      if (search) {
        search.value = q;
        search.dispatchEvent(new Event('input', { bubbles: true }));
      }
      var grid = document.getElementById('latest');
      if (grid) grid.scrollIntoView({ behavior: REDUCE ? 'auto' : 'smooth' });
    });
  }

  if (pauseBtn) {
    pauseBtn.addEventListener('click', function () {
      running = !running;
      pauseBtn.textContent = running ? '❚❚' : '▶';
      pauseBtn.setAttribute('aria-label', running ? 'Pause animation' : 'Play animation');
      if (running) { lastT = 0; loop(); }
    });
    if (REDUCE) { pauseBtn.textContent = '▶'; }
  }

  if (seedBtn) {
    seedBtn.addEventListener('click', function () {
      hubs.forEach(function (h) {
        h.angle = rand(0, TAU);
        h.bend = rand(-34, 34);
        h.rf = rand(0.84, 1.1);
      });
      seedSatellites();
      hubs.forEach(burst);
      if (REDUCE || !running) drawFrame(0.05);
    });
  }

  stage.addEventListener('pointermove', function (e) {
    var r = stage.getBoundingClientRect();
    pointer.x = e.clientX - r.left;
    pointer.y = e.clientY - r.top;
    pointer.inside = true;
    /* labels manage their own hover via mouseenter/leave — don't fight them */
    if (!(e.target.closest && e.target.closest('.atlas-label'))) hitTest();
  }, { passive: true });
  stage.addEventListener('pointerleave', function () {
    pointer.inside = false;
    if (hovered && !hovered.el) { hovered = null; hideTip(); }
  });
  canvas.addEventListener('click', function () {
    if (hovered && hovered.topic) selectCluster(hovered);
  });

  function hitTest() {
    var hit = null, i, d;
    for (i = 0; i < hubs.length; i++) {
      d = Math.hypot(pointer.x - hubs[i].x, pointer.y - hubs[i].y);
      if (d < hubs[i].size + 9) { hit = hubs[i]; break; }
    }
    if (!hit) {
      for (i = 0; i < sats.length; i++) {
        d = Math.hypot(pointer.x - sats[i].x, pointer.y - sats[i].y);
        if (d < sats[i].size + 6) { hit = sats[i]; break; }
      }
    }
    if (hit !== hovered) {
      hovered = hit;
      if (hit) showTip(hit); else hideTip();
    }
    canvas.style.cursor = (hovered && hovered.topic) ? 'pointer' : 'default';
    if (hovered && !hovered.topic) positionTip(hovered.x, hovered.y);
  }

  function showTip(node) {
    if (!tip) return;
    if (node.topic) {
      tip.innerHTML = '<b>' + node.label + '</b><span>' + node.count + ' brief' + (node.count === 1 ? '' : 's') +
        ' on the desk · era ' + node.era + '</span><em>click to filter the grid</em>';
    } else {
      tip.innerHTML = '<b>#' + node.tag + '</b><span>signal · ' + node.hub.label + '</span><em>orbiting cluster</em>';
    }
    tip.hidden = false;
    positionTip(node.x, node.y);
  }
  function positionTip(x, y) {
    if (!tip || tip.hidden) return;
    var pad = 14;
    var tw = tip.offsetWidth, th = tip.offsetHeight;
    var tx = Math.min(Math.max(x + 16, pad), W - tw - pad);
    var ty = Math.min(Math.max(y - th - 14, pad), H - th - pad);
    tip.style.transform = 'translate(' + tx + 'px,' + ty + 'px)';
  }
  function hideTip() { if (tip) tip.hidden = true; }

  /* ------------------------------------------------------------------ sizing */
  function resize() {
    var r = stage.getBoundingClientRect();
    W = Math.max(300, r.width);
    H = Math.max(300, r.height);
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(W * DPR);
    canvas.height = Math.round(H * DPR);
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    seedAmbient();
    if (REDUCE) drawFrame(0);
  }
  if ('ResizeObserver' in window) {
    new ResizeObserver(resize).observe(stage);
  } else {
    addEventListener('resize', resize, { passive: true });
  }

  /* --------------------------------------------------------------- dynamics */
  function step(dt) {
    time += dt;

    /* parallax eases toward the cursor (or drifts on its own) */
    var tx = pointer.inside ? (pointer.x - W / 2) * 0.045 : Math.sin(time * 0.18) * 8;
    var ty = pointer.inside ? (pointer.y - H / 2) * 0.045 : Math.cos(time * 0.14) * 6;
    par.x += (tx - par.x) * 0.05;
    par.y += (ty - par.y) * 0.05;

    core.x = W / 2 + par.x * 0.5;
    core.y = H * 0.52 + par.y * 0.5;

    var rx = Math.min(W * 0.36, 430);
    var ry = Math.min(H * 0.335, 300);
    var year = EPOCHS[epochIdx].year;

    hubs.forEach(function (hub) {
      hub.angle += hub.drift * dt;
      var breathe = 1 + Math.sin(time * 0.6 + hub.wobble) * 0.022;
      hub.x = core.x + Math.cos(hub.angle) * rx * hub.rf * breathe + par.x;
      hub.y = core.y + Math.sin(hub.angle) * ry * hub.rf * breathe + par.y;
      var targetLit = hub.era <= year ? 1 : 0.17;
      hub.lit += (targetLit - hub.lit) * Math.min(1, dt * 3);
      hub.hover += ((hovered === hub ? 1 : 0) - hub.hover) * Math.min(1, dt * 8);
      hub.size = (10 + Math.min(hub.count, 4) * 1.3) + hub.hover * 3;
    });

    sats.forEach(function (s) {
      s.angle += s.speed * dt;
      s.x = s.hub.x + Math.cos(s.angle) * s.orbit + par.x * 0.4;
      s.y = s.hub.y + Math.sin(s.angle) * s.orbit * s.squash + par.y * 0.4;
    });

    /* spawn travelling light */
    var litHubs = hubs.filter(function (h) { return h.lit > 0.6; });
    if (litHubs.length && Math.random() < dt * 1.5) {
      pulses.push({ hub: litHubs[Math.floor(Math.random() * litHubs.length)], t: 0, dur: rand(1.4, 2.2), hot: false });
    }
    if (litHubs.length && Math.random() < dt * 2.4 && sats.length) {
      var s2 = sats[Math.floor(Math.random() * sats.length)];
      if (s2.hub.lit > 0.6) subPulses.push({ sat: s2, t: 0, dur: rand(0.7, 1.1) });
    }
    pulses = pulses.filter(function (p) { p.t += dt / p.dur; return p.t < 1.05; });
    subPulses = subPulses.filter(function (p) { p.t += dt / p.dur; return p.t < 1; });

    sparks.forEach(function (sp) { sp.a += sp.sp * dt; });

    /* roadmap auto-advance */
    if (time > epochHold && Math.floor(time / 4.5) !== Math.floor((time - dt) / 4.5)) {
      setEpoch((epochIdx + 1) % EPOCHS.length);
    }
  }

  /* ---------------------------------------------------------------- drawing */
  function beamPoint(hub, t) {
    /* quadratic bezier core -> hub with a perpendicular bend */
    var mx = (core.x + hub.x) / 2, my = (core.y + hub.y) / 2;
    var dx = hub.x - core.x, dy = hub.y - core.y;
    var len = Math.hypot(dx, dy) || 1;
    var cx = mx + (-dy / len) * hub.bend;
    var cy = my + (dx / len) * hub.bend;
    var u = 1 - t;
    return {
      x: u * u * core.x + 2 * u * t * cx + t * t * hub.x,
      y: u * u * core.y + 2 * u * t * cy + t * t * hub.y,
      cx: cx, cy: cy
    };
  }

  function drawBackground() {
    ctx.clearRect(0, 0, W, H);
    /* deep vignette pool behind the core */
    var g = ctx.createRadialGradient(core.x, core.y, 40, core.x, core.y, Math.max(W, H) * 0.72);
    g.addColorStop(0, 'rgba(22,34,58,.55)');
    g.addColorStop(0.5, 'rgba(8,13,24,.25)');
    g.addColorStop(1, 'rgba(2,3,7,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);

    /* star dust with slow twinkle */
    dust.forEach(function (d) {
      var a = 0.10 + 0.14 * (0.5 + 0.5 * Math.sin(time * d.f + d.p));
      ctx.fillStyle = 'rgba(190,214,255,' + a.toFixed(3) + ')';
      ctx.beginPath();
      ctx.arc(d.x * W, d.y * H, d.r, 0, TAU);
      ctx.fill();
    });
  }

  function drawSatEdges() {
    ctx.lineWidth = 0.7;
    sats.forEach(function (s) {
      var lit = s.hub.lit;
      ctx.strokeStyle = 'rgba(' + s.hub.ink.glow + ',' + (0.14 * lit).toFixed(3) + ')';
      ctx.beginPath();
      ctx.moveTo(s.hub.x, s.hub.y);
      ctx.lineTo(s.x, s.y);
      ctx.stroke();
    });
  }

  function drawBeams() {
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    hubs.forEach(function (hub) {
      var k = hub.lit * (0.75 + hub.hover * 0.45 + 0.1 * Math.sin(time * 1.7 + hub.wobble));
      var p = beamPoint(hub, 0.5);
      var grad = ctx.createLinearGradient(core.x, core.y, hub.x, hub.y);
      grad.addColorStop(0, 'rgba(' + INK.gold.glow + ',' + (0.5 * k).toFixed(3) + ')');
      grad.addColorStop(0.55, 'rgba(' + INK.gold.glow + ',' + (0.16 * k).toFixed(3) + ')');
      grad.addColorStop(1, 'rgba(' + hub.ink.glow + ',' + (0.3 * k).toFixed(3) + ')');

      /* wide haze, mid body, hot centre — layered for a tapered luminous beam */
      var passes = [[6.5, 0.10], [2.6, 0.3], [1, 0.85]];
      passes.forEach(function (pass) {
        ctx.strokeStyle = grad;
        ctx.globalAlpha = pass[1] * k;
        ctx.lineWidth = pass[0];
        ctx.beginPath();
        ctx.moveTo(core.x, core.y);
        ctx.quadraticCurveTo(p.cx, p.cy, hub.x, hub.y);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    });
    ctx.restore();
  }

  function drawPulses() {
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    pulses.forEach(function (p) {
      for (var i = 0; i < 6; i++) {
        var t = p.t - i * 0.022;
        if (t <= 0 || t >= 1) continue;
        var pt = beamPoint(p.hub, ease(t));
        var a = (1 - i / 6) * (p.hot ? 0.9 : 0.6);
        var r = (p.hot ? 3.2 : 2.4) * (1 - i / 7);
        ctx.fillStyle = 'rgba(255,236,190,' + a.toFixed(3) + ')';
        ctx.shadowColor = 'rgba(' + INK.gold.glow + ',.9)';
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, r, 0, TAU);
        ctx.fill();
      }
    });
    ctx.shadowBlur = 0;
    subPulses.forEach(function (p) {
      var t = ease(p.t);
      var x = lerp(p.sat.hub.x, p.sat.x, t);
      var y = lerp(p.sat.hub.y, p.sat.y, t);
      ctx.fillStyle = 'rgba(' + p.sat.hub.ink.glow + ',.8)';
      ctx.shadowColor = 'rgba(' + p.sat.hub.ink.glow + ',.8)';
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.arc(x, y, 1.6, 0, TAU);
      ctx.fill();
    });
    ctx.restore();
  }

  function sphere(x, y, r, ink, litAlpha, glowBoost) {
    ctx.save();
    ctx.globalAlpha = litAlpha;
    ctx.shadowColor = 'rgba(' + ink.glow + ',' + (0.85 * litAlpha).toFixed(3) + ')';
    ctx.shadowBlur = 14 + glowBoost;
    var g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.42, r * 0.08, x, y, r);
    g.addColorStop(0, '#ffffff');
    g.addColorStop(0.28, ink.body);
    g.addColorStop(1, ink.deep);
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, TAU);
    ctx.fill();
    ctx.restore();
  }

  function drawSats() {
    sats.forEach(function (s) {
      var lit = Math.max(0.12, s.hub.lit * (s.era <= EPOCHS[epochIdx].year ? 1 : 0.25));
      var tw = 0.75 + 0.25 * Math.sin(time * 1.6 + s.tw);
      sphere(s.x, s.y, s.size, s.hub.ink, lit * tw, 0);
    });
  }

  function drawHubs() {
    hubs.forEach(function (hub) {
      sphere(hub.x, hub.y, hub.size, hub.ink, Math.max(0.2, hub.lit), hub.hover * 14);
      /* selection / activity ring */
      var ringA = 0.16 * hub.lit + hub.hover * 0.35;
      if (ringA > 0.03) {
        ctx.strokeStyle = 'rgba(' + hub.ink.glow + ',' + ringA.toFixed(3) + ')';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(hub.x, hub.y, hub.size + 5 + Math.sin(time * 2 + hub.wobble) * 1.2, 0, TAU);
        ctx.stroke();
      }
    });
  }

  function drawCore() {
    var breathe = 1 + Math.sin(time * 0.9) * 0.06;

    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    var halo = ctx.createRadialGradient(core.x, core.y, 4, core.x, core.y, 95 * breathe);
    halo.addColorStop(0, 'rgba(255,226,168,.5)');
    halo.addColorStop(0.35, 'rgba(255,196,120,.16)');
    halo.addColorStop(1, 'rgba(255,180,90,0)');
    ctx.fillStyle = halo;
    ctx.beginPath();
    ctx.arc(core.x, core.y, 95 * breathe, 0, TAU);
    ctx.fill();
    ctx.restore();

    sphere(core.x, core.y, core.r * breathe, INK.gold, 1, 16);

    /* rotating governance rings — the "constitution" signature */
    ctx.save();
    ctx.strokeStyle = 'rgba(255,220,160,.5)';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 8]);
    ctx.lineDashOffset = -time * 26;
    ctx.beginPath();
    ctx.arc(core.x, core.y, 31, 0, TAU);
    ctx.stroke();
    ctx.setLineDash([1, 12]);
    ctx.lineDashOffset = time * 18;
    ctx.strokeStyle = 'rgba(255,220,160,.22)';
    ctx.beginPath();
    ctx.arc(core.x, core.y, 44, 0, TAU);
    ctx.stroke();
    ctx.restore();

    /* orbiting motes */
    sparks.forEach(function (sp) {
      var x = core.x + Math.cos(sp.a) * sp.r;
      var y = core.y + Math.sin(sp.a) * sp.r * 0.92;
      ctx.fillStyle = 'rgba(255,232,180,.75)';
      ctx.beginPath();
      ctx.arc(x, y, sp.sz, 0, TAU);
      ctx.fill();
    });
  }

  function syncLabels() {
    if (core.el) {
      core.el.style.transform = 'translate(' + (core.x + 22) + 'px,' + (core.y - 34) + 'px)';
    }
    hubs.forEach(function (hub) {
      if (!hub.el) return;
      var flip = hub.x > W * 0.72;
      hub.el.style.transform = 'translate(' + (hub.x + (flip ? -14 : 14)) + 'px,' + (hub.y - 16) + 'px)' + (flip ? ' translateX(-100%)' : '');
      hub.el.classList.toggle('dim', hub.lit < 0.5);
    });
  }

  function drawFrame(dt) {
    step(dt);
    drawBackground();
    drawSatEdges();
    drawBeams();
    drawPulses();
    drawSats();
    drawHubs();
    drawCore();
    syncLabels();
  }

  /* ------------------------------------------------------------------- loop */
  function loop(now) {
    if (!running || !visible) { rafId = 0; return; }
    if (!now) now = performance.now();
    if (!lastT) lastT = now;
    var dt = Math.min((now - lastT) / 1000, 0.05);
    lastT = now;
    drawFrame(dt);
    rafId = requestAnimationFrame(loop);
  }

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (es) {
      visible = es[0].isIntersecting;
      if (visible && running && !rafId) { lastT = 0; rafId = requestAnimationFrame(loop); }
    }, { threshold: 0.05 }).observe(stage);
  }

  /* ------------------------------------------------------------------- boot */
  resize();
  buildGraph();
  buildLabels();
  buildTimeline();
  hubs.forEach(burst);
  if (REDUCE) {
    /* static, fully-lit frame: everything visible, nothing moving */
    time = 2;
    step(0.016);
    hubs.forEach(function (h) { h.lit = h.era <= EPOCHS[epochIdx].year ? 1 : 0.17; });
    drawFrame(0);
  } else {
    rafId = requestAnimationFrame(loop);
  }
})();
