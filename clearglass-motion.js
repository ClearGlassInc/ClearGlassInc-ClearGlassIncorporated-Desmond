/* ClearGlass Cinematic Motion System — behaviour layer.
 *
 * Progressive enhancement only. Every construct this file drives has a static
 * resting state in clearglass-motion.css, so with JS disabled the page renders
 * complete and readable; this file adds `cgm-js` to <html> and only then are the
 * pre-animation (hidden/scattered) states allowed to apply.
 *
 * Renderer ladder for the Layer-3 ambient field:
 *   WebGPU -> WebGL2 -> Canvas2D -> inline SVG -> CSS gradients only
 * Each rung is attempted in order and any failure falls through silently.
 *
 * Budget rules enforced here:
 *   - frame cap (default 30fps for ambient work)
 *   - device-pixel-ratio clamped to 2
 *   - rendering paused when the document is hidden or the host is offscreen
 *   - GPU/context resources released on teardown
 *   - pointer input coalesced into one rAF write per frame (no layout thrash)
 */
(function () {
  'use strict';

  /* ── configuration ─────────────────────────────────────────────────── */
  var CONFIG = {
    ENABLE_ADVANCED_VISUALS: true,   // master flag for the GPU/canvas ladder
    FPS_CAP: 30,
    DPR_CAP: 2,
    MAGNET_MAX: 5,                   // px, matches --cgm-magnet-max
    TILT_MAX: 2.5,                   // deg, matches --cgm-tilt-max
    PARTICLES: 46,
    STORAGE_KEY: 'cgm-motion-preference'
  };

  var html = document.documentElement;
  var reduceQuery = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : { matches: false, addEventListener: null };
  var finePointer = window.matchMedia
    ? window.matchMedia('(hover:hover) and (pointer:fine)')
    : { matches: false };
  var lowPower = window.matchMedia
    ? window.matchMedia('(max-width:900px)')
    : { matches: false };

  /* User opt-out is authoritative over the OS hint only when set to 'reduced'. */
  var stored = null;
  try { stored = window.localStorage.getItem(CONFIG.STORAGE_KEY); } catch (e) { /* private mode */ }

  function motionReduced() {
    if (stored === 'reduced') return true;
    if (stored === 'full') return false;
    return !!reduceQuery.matches;
  }

  function advancedAllowed() {
    return CONFIG.ENABLE_ADVANCED_VISUALS &&
           !motionReduced() &&
           !lowPower.matches &&
           document.body != null;
  }

  html.classList.add('cgm-js');
  if (finePointer.matches) html.classList.add('cgm-pointer-fine');
  html.setAttribute('data-cgm-motion', motionReduced() ? 'reduced' : 'full');

  /* ── shared rAF write queue: coalesce all style writes into one frame ── */
  var pendingWrites = [];
  var writeScheduled = false;
  function queueWrite(fn) {
    pendingWrites.push(fn);
    if (writeScheduled) return;
    writeScheduled = true;
    requestAnimationFrame(function () {
      writeScheduled = false;
      var jobs = pendingWrites;
      pendingWrites = [];
      for (var i = 0; i < jobs.length; i++) {
        try { jobs[i](); } catch (e) { /* never let one writer kill the frame */ }
      }
    });
  }

  /* ─────────────────────────────────────────────────────────────────────
     LAYER 2 — reveal on approach, once
     ───────────────────────────────────────────────────────────────────── */
  function initReveals() {
    var targets = document.querySelectorAll('[data-cgm-reveal]');
    if (!targets.length) return;

    if (!('IntersectionObserver' in window) || motionReduced()) {
      for (var i = 0; i < targets.length; i++) {
        targets[i].classList.add('cgm-in', 'cgm-settled');
      }
      return;
    }

    // Stagger is assigned per group so siblings cascade, capped so a long
    // list never waits seconds for its tail.
    // Stagger resets per section, so a block far down the page still starts
    // promptly instead of inheriting the whole document's running index.
    var groups = {};
    var sectionKeys = [];
    Array.prototype.forEach.call(targets, function (el) {
      var key = el.getAttribute('data-cgm-group');
      if (!key) {
        var section = el.closest ? el.closest('section,article,footer,main') : null;
        if (section) {
          var at = sectionKeys.indexOf(section);
          if (at === -1) { at = sectionKeys.push(section) - 1; }
          key = 's' + at;
        } else {
          key = '_';
        }
      }
      groups[key] = groups[key] || 0;
      var index = Math.min(groups[key]++, 6);
      el.style.setProperty('--cgm-delay', (index * 75) + 'ms');
    });

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        el.classList.add('cgm-in');
        observer.unobserve(el);              // animate once, by default
        // Release the compositor hint after the transition completes.
        window.setTimeout(function () { el.classList.add('cgm-settled'); }, 900);
      });
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.12 });

    Array.prototype.forEach.call(targets, function (el) { observer.observe(el); });
  }

  /* ─────────────────────────────────────────────────────────────────────
     Scene 1 scatter offsets — deterministic, seeded by index, never random
     per render (so the layout is stable across reloads and SSR/static HTML).
     ───────────────────────────────────────────────────────────────────── */
  function initScatter() {
    var scenes = document.querySelectorAll('.cgm-scene--scatter');
    Array.prototype.forEach.call(scenes, function (scene) {
      var frags = scene.querySelectorAll('.cgm-scene__frag');
      Array.prototype.forEach.call(frags, function (frag, i) {
        var a = Math.sin(i * 12.9898) * 43758.5453;
        var b = Math.sin(i * 78.233) * 12345.6789;
        var fx = ((a - Math.floor(a)) * 2 - 1) * 44;
        var fy = ((b - Math.floor(b)) * 2 - 1) * 30;
        var fr = ((a - Math.floor(a)) * 2 - 1) * 5;
        frag.style.setProperty('--cgm-fx', fx.toFixed(1) + 'px');
        frag.style.setProperty('--cgm-fy', fy.toFixed(1) + 'px');
        frag.style.setProperty('--cgm-fr', fr.toFixed(2) + 'deg');
      });
    });
  }

  /* ─────────────────────────────────────────────────────────────────────
     Pointer-aware glass highlight + magnetic buttons + bounded tilt
     ───────────────────────────────────────────────────────────────────── */
  function initPointerGlass() {
    if (!finePointer.matches || motionReduced()) return;

    var cards = document.querySelectorAll('.cgm-glass');
    Array.prototype.forEach.call(cards, function (card) {
      card.addEventListener('pointermove', function (ev) {
        var rect = card.getBoundingClientRect();          // read
        var x = ((ev.clientX - rect.left) / rect.width) * 100;
        var y = ((ev.clientY - rect.top) / rect.height) * 100;
        queueWrite(function () {                          // write, next frame
          card.style.setProperty('--cgm-mx', x.toFixed(2) + '%');
          card.style.setProperty('--cgm-my', y.toFixed(2) + '%');
        });
        if (card.classList.contains('cgm-tilt')) {
          var ry = (((ev.clientX - rect.left) / rect.width) * 2 - 1) * CONFIG.TILT_MAX;
          var rx = (((ev.clientY - rect.top) / rect.height) * 2 - 1) * -CONFIG.TILT_MAX;
          queueWrite(function () {
            card.style.setProperty('--cgm-ry', ry.toFixed(2) + 'deg');
            card.style.setProperty('--cgm-rx', rx.toFixed(2) + 'deg');
          });
        }
      }, { passive: true });

      card.addEventListener('pointerleave', function () {
        queueWrite(function () {
          card.style.setProperty('--cgm-rx', '0deg');
          card.style.setProperty('--cgm-ry', '0deg');
        });
      }, { passive: true });
    });

    // Magnetic CTA. Movement is hard-clamped so the target never runs away
    // from the cursor — an unclickable button is worse than a static one.
    var magnets = document.querySelectorAll('.cgm-btn[data-cgm-magnetic]');
    Array.prototype.forEach.call(magnets, function (btn) {
      btn.addEventListener('pointermove', function (ev) {
        var rect = btn.getBoundingClientRect();
        var dx = (ev.clientX - (rect.left + rect.width / 2)) / (rect.width / 2);
        var dy = (ev.clientY - (rect.top + rect.height / 2)) / (rect.height / 2);
        var mx = Math.max(-1, Math.min(1, dx)) * CONFIG.MAGNET_MAX;
        var my = Math.max(-1, Math.min(1, dy)) * CONFIG.MAGNET_MAX;
        queueWrite(function () {
          btn.style.setProperty('--cgm-btn-x', mx.toFixed(1) + 'px');
          btn.style.setProperty('--cgm-btn-y', my.toFixed(1) + 'px');
        });
      }, { passive: true });
      btn.addEventListener('pointerleave', function () {
        queueWrite(function () {
          btn.style.setProperty('--cgm-btn-x', '0px');
          btn.style.setProperty('--cgm-btn-y', '0px');
        });
      }, { passive: true });
    });
  }

  /* Global cursor light for the atmospheric layer. */
  function initCursorLight() {
    var atmos = document.querySelector('.cgm-atmos');
    if (!atmos || !finePointer.matches || motionReduced()) return;
    window.addEventListener('pointermove', function (ev) {
      var x = ev.clientX, y = ev.clientY;
      queueWrite(function () {
        atmos.style.setProperty('--cgm-mx', x + 'px');
        atmos.style.setProperty('--cgm-my', y + 'px');
      });
    }, { passive: true });
  }

  /* ─────────────────────────────────────────────────────────────────────
     Custom cursor — additive ring. The native cursor is never hidden.
     ───────────────────────────────────────────────────────────────────── */
  function initCustomCursor() {
    if (!finePointer.matches || motionReduced()) return;
    var ring = document.querySelector('.cgm-cursor');
    if (!ring) return;
    html.classList.add('cgm-cursor-on');

    window.addEventListener('pointermove', function (ev) {
      var x = ev.clientX, y = ev.clientY;
      queueWrite(function () {
        ring.style.setProperty('--cgm-cx', x + 'px');
        ring.style.setProperty('--cgm-cy', y + 'px');
      });
    }, { passive: true });

    // Grow over anything interactive, using a capability check not a tag list.
    document.addEventListener('pointerover', function (ev) {
      var t = ev.target;
      if (t && t.closest && t.closest('a,button,[role="button"],input,select,textarea,summary')) {
        ring.classList.add('cgm-cursor--hot');
      }
    }, { passive: true });
    document.addEventListener('pointerout', function (ev) {
      var t = ev.target;
      if (t && t.closest && t.closest('a,button,[role="button"],input,select,textarea,summary')) {
        ring.classList.remove('cgm-cursor--hot');
      }
    }, { passive: true });
  }

  /* ─────────────────────────────────────────────────────────────────────
     CAPABILITY CONSTELLATION
     Nodes are real <button>s laid out from deterministic coordinates, so
     keyboard order matches visual order and screen readers get the same
     content. The canvas only draws the connective tissue.
     ───────────────────────────────────────────────────────────────────── */
  var CAPABILITIES = [
    { id: 'strategy',        label: 'Strategy',        x: 50, y: 12, copy: 'Positioning, offer design and the sequencing decisions that determine what the rest of the system is even for.' },
    { id: 'experience',      label: 'Experience',      x: 79, y: 25, copy: 'Interface, narrative and information design — how quickly a visitor understands what you do and what to do next.' },
    { id: 'engineering',     label: 'Engineering',     x: 90, y: 52, copy: 'The build itself: performant, accessible, typed, and maintainable by someone who is not the original author.' },
    { id: 'automation',      label: 'Automation',      x: 79, y: 79, copy: 'Governed workflows that remove manual steps without removing the human approval that keeps them safe.' },
    { id: 'ai',              label: 'AI',              x: 50, y: 90, copy: 'Model-assisted work under the same rule as everything else here: read-only analysis, drafted change, human approval, logged execution.' },
    { id: 'security',        label: 'Security',        x: 21, y: 79, copy: 'Threat modelling, header and edge posture, dependency integrity, and evidence you can hand an auditor.' },
    { id: 'discoverability', label: 'Discoverability', x: 10, y: 52, copy: 'Technical SEO, structured data and internal link authority — being findable by the people already looking.' },
    { id: 'analytics',       label: 'Analytics',       x: 21, y: 25, copy: 'Measurement that answers a decision. Fewer dashboards, more resolved questions.' },
    { id: 'operations',      label: 'Operations',      x: 50, y: 51, copy: 'The connective layer: runbooks, ownership, escalation and the boring reliability work that compounds.' }
  ];

  function initConstellation() {
    var root = document.querySelector('[data-cgm-constellation]');
    if (!root) return;

    var stage = root.querySelector('.cgm-constellation__stage');
    var title = root.querySelector('[data-cgm-readout-title]');
    var body = root.querySelector('[data-cgm-readout-body]');
    var pathwayEl = root.querySelector('[data-cgm-pathway]');
    if (!stage || !title || !body) return;

    var selected = [];
    var nodes = [];
    // Shared, mutable view of interaction state. The renderer reads it each
    // frame instead of being re-created on every hover.
    var state = { focused: null, selected: selected };

    CAPABILITIES.forEach(function (cap, i) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'cgm-node';
      btn.style.left = cap.x + '%';
      btn.style.top = cap.y + '%';
      btn.setAttribute('aria-pressed', 'false');
      btn.setAttribute('data-cgm-node', cap.id);
      btn.innerHTML = '<span class="cgm-node__dot" aria-hidden="true"></span>';
      btn.appendChild(document.createTextNode(cap.label));

      btn.addEventListener('click', function () {
        var at = selected.indexOf(cap.id);
        if (at === -1) { selected.push(cap.id); } else { selected.splice(at, 1); }
        if (selected.length > 5) selected.shift();
        render();
      });
      btn.addEventListener('focus', function () { state.focused = cap.id; preview(cap); });
      btn.addEventListener('blur', function () { if (state.focused === cap.id) state.focused = null; });
      btn.addEventListener('pointerenter', function () { state.focused = cap.id; preview(cap); }, { passive: true });
      btn.addEventListener('pointerleave', function () { if (state.focused === cap.id) state.focused = null; }, { passive: true });

      stage.appendChild(btn);
      nodes.push({ cap: cap, el: btn, i: i });
    });

    function preview(cap) {
      title.textContent = cap.label;
      body.textContent = cap.copy;
    }

    function render() {
      nodes.forEach(function (n) {
        n.el.setAttribute('aria-pressed', selected.indexOf(n.cap.id) !== -1 ? 'true' : 'false');
      });
      if (!pathwayEl) return;
      if (selected.length < 2) {
        pathwayEl.hidden = true;
        pathwayEl.textContent = '';
        return;
      }
      var labels = selected.map(function (id) {
        for (var i = 0; i < CAPABILITIES.length; i++) {
          if (CAPABILITIES[i].id === id) return CAPABILITIES[i].label;
        }
        return id;
      });
      pathwayEl.hidden = false;
      pathwayEl.textContent = 'System pathway: ' + labels.join(' → ') +
        ' — a ' + labels.length + '-stage engagement. Start with a scoped review of the first stage.';
    }

    render();
    startAmbient(stage, nodes, state);
  }

  /* ─────────────────────────────────────────────────────────────────────
     RENDERER LADDER for the connective field behind the nodes
     ───────────────────────────────────────────────────────────────────── */
  function startAmbient(stage, nodes, state) {
    if (!advancedAllowed()) { drawStaticSvg(stage, nodes); return; }

    var dpr = Math.min(window.devicePixelRatio || 1, CONFIG.DPR_CAP);
    var canvas = document.createElement('canvas');
    canvas.className = 'cgm-atmos__canvas';
    canvas.setAttribute('aria-hidden', 'true');   // decorative; nodes carry meaning
    stage.insertBefore(canvas, stage.firstChild);

    // The graph's job is to explain relationships, so the connective tissue is
    // what gets drawn. That is a handful of lines and a travelling pulse —
    // Canvas2D expresses it directly and cheaply. The WebGL2 path is kept for
    // the full-viewport particle field, where many points actually pay for a
    // GPU context.
    var renderer = createConnectionRenderer(canvas, nodes, state)
                || createCanvas2dRenderer(canvas);
    if (!renderer) { canvas.remove(); drawStaticSvg(stage, nodes); return; }
    // Static lines sit underneath as the no-context fallback and as the
    // reduced-motion resting state.
    drawStaticSvg(stage, nodes);

    var running = false, rafId = 0, last = 0;
    var minFrame = 1000 / CONFIG.FPS_CAP;

    function resize() {
      var rect = stage.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      canvas.width = Math.round(rect.width * dpr);
      canvas.height = Math.round(rect.height * dpr);
      renderer.resize(canvas.width, canvas.height, dpr);
    }

    function frame(now) {
      if (!running) return;
      rafId = requestAnimationFrame(frame);
      if (now - last < minFrame) return;        // hold the cap
      last = now;
      renderer.draw(now);
    }

    function start() {
      if (running) return;
      running = true;
      last = 0;
      rafId = requestAnimationFrame(frame);
    }
    function stop() {
      running = false;
      if (rafId) cancelAnimationFrame(rafId);
      rafId = 0;
    }

    // Pause offscreen.
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        entries[0].isIntersecting ? start() : stop();
      }, { threshold: 0.01 }).observe(stage);
    } else { start(); }

    // Pause when the tab is hidden.
    document.addEventListener('visibilitychange', function () {
      document.hidden ? stop() : start();
    });

    var ro = ('ResizeObserver' in window) ? new ResizeObserver(resize) : null;
    if (ro) { ro.observe(stage); } else { window.addEventListener('resize', resize); }
    resize();

    // Release GPU/context resources on teardown.
    function dispose() {
      stop();
      if (ro) ro.disconnect();
      renderer.dispose();
      canvas.width = canvas.height = 0;   // frees the backing store
      canvas.remove();
    }
    window.addEventListener('pagehide', dispose);
    stage.cgDispose = dispose;            // exposed for tests / SPA unmount
  }

  /* Deterministic particle seed shared by every renderer. */
  function seedParticles(count) {
    var out = [];
    for (var i = 0; i < count; i++) {
      var a = Math.sin(i * 12.9898) * 43758.5453; a -= Math.floor(a);
      var b = Math.sin(i * 78.233) * 12345.6789;  b -= Math.floor(b);
      var c = Math.sin(i * 39.425) * 24634.6345;  c -= Math.floor(c);
      out.push({ x: a, y: b, phase: c * Math.PI * 2, speed: 0.12 + c * 0.22 });
    }
    return out;
  }

  /* Hub-and-spoke plus ring edges. An edge brightens when either endpoint is
     focused or selected, and carries a slow pulse so the graph reads as live
     without inventing any data. */
  function createConnectionRenderer(canvas, nodes, state) {
    var ctx = null;
    try { ctx = canvas.getContext('2d'); } catch (e) { ctx = null; }
    if (!ctx) return null;

    var byId = {};
    nodes.forEach(function (n) { byId[n.cap.id] = n.cap; });

    var edges = [];
    var ring = nodes.filter(function (n) { return n.cap.id !== 'operations'; });
    ring.forEach(function (n, i) {
      edges.push([n.cap.id, 'operations']);                       // spoke
      edges.push([n.cap.id, ring[(i + 1) % ring.length].cap.id]); // ring
    });

    var w = 1, h = 1, scale = 1;

    function isHot(id) {
      return state.focused === id || state.selected.indexOf(id) !== -1;
    }

    return {
      kind: 'canvas2d-connections',
      resize: function (cw, ch, dpr) { w = cw; h = ch; scale = dpr || 1; },
      draw: function (now) {
        ctx.clearRect(0, 0, w, h);
        ctx.lineCap = 'round';
        for (var i = 0; i < edges.length; i++) {
          var a = byId[edges[i][0]], bb = byId[edges[i][1]];
          if (!a || !bb) continue;
          var x1 = a.x / 100 * w, y1 = a.y / 100 * h;
          var x2 = bb.x / 100 * w, y2 = bb.y / 100 * h;
          var hot = isHot(edges[i][0]) || isHot(edges[i][1]);

          ctx.strokeStyle = hot ? 'rgba(238,99,122,0.55)' : 'rgba(234,70,72,0.16)';
          ctx.lineWidth = (hot ? 1.6 : 0.9) * scale;
          ctx.beginPath();
          ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();

          // Pulse position is derived from time and edge index, so it is
          // deterministic and evenly distributed rather than random.
          var speed = hot ? 0.00022 : 0.00009;
          var tt = ((now * speed) + i * 0.137) % 1;
          var px = x1 + (x2 - x1) * tt, py = y1 + (y2 - y1) * tt;
          ctx.globalAlpha = hot ? 0.85 : 0.32;
          ctx.fillStyle = hot ? '#ee637a' : '#ea4648';
          ctx.beginPath();
          ctx.arc(px, py, (hot ? 2.4 : 1.5) * scale, 0, Math.PI * 2);
          ctx.fill();
          ctx.globalAlpha = 1;
        }
      },
      dispose: function () { ctx.clearRect(0, 0, w, h); }
    };
  }

  function createWebgl2Renderer(canvas) {
    var gl = null;
    try {
      gl = canvas.getContext('webgl2', { alpha: true, antialias: false, powerPreference: 'low-power' });
    } catch (e) { gl = null; }
    if (!gl) return null;

    var vs = '#version 300 es\nin vec2 p;in float ph;uniform float t;uniform vec2 res;out float a;' +
      'void main(){float y=fract(p.y+t*0.004*(0.4+ph*0.2));vec2 q=vec2(p.x,y);' +
      'a=0.25+0.45*sin(t*0.001+ph*6.2831);' +
      'gl_Position=vec4(q*2.0-1.0,0.0,1.0);gl_PointSize=max(1.0,res.y*0.004);}';
    var fs = '#version 300 es\nprecision mediump float;in float a;uniform vec3 c;out vec4 o;' +
      'void main(){vec2 d=gl_PointCoord-0.5;float m=smoothstep(0.5,0.0,length(d));o=vec4(c,a*m);}';

    function compile(type, src) {
      var s = gl.createShader(type);
      gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { gl.deleteShader(s); return null; }
      return s;
    }
    var v = compile(gl.VERTEX_SHADER, vs), f = compile(gl.FRAGMENT_SHADER, fs);
    if (!v || !f) return null;
    var prog = gl.createProgram();
    gl.attachShader(prog, v); gl.attachShader(prog, f); gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return null;

    var parts = seedParticles(CONFIG.PARTICLES);
    var pos = new Float32Array(parts.length * 2), phase = new Float32Array(parts.length);
    parts.forEach(function (p, i) { pos[i * 2] = p.x; pos[i * 2 + 1] = p.y; phase[i] = p.phase; });

    var vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    var bufP = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, bufP); gl.bufferData(gl.ARRAY_BUFFER, pos, gl.STATIC_DRAW);
    var locP = gl.getAttribLocation(prog, 'p');
    gl.enableVertexAttribArray(locP); gl.vertexAttribPointer(locP, 2, gl.FLOAT, false, 0, 0);
    var bufH = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, bufH); gl.bufferData(gl.ARRAY_BUFFER, phase, gl.STATIC_DRAW);
    var locH = gl.getAttribLocation(prog, 'ph');
    gl.enableVertexAttribArray(locH); gl.vertexAttribPointer(locH, 1, gl.FLOAT, false, 0, 0);

    var uT = gl.getUniformLocation(prog, 't');
    var uRes = gl.getUniformLocation(prog, 'res');
    var uC = gl.getUniformLocation(prog, 'c');
    var w = 1, h = 1;

    return {
      kind: 'webgl2',
      resize: function (cw, ch) { w = cw; h = ch; gl.viewport(0, 0, cw, ch); },
      draw: function (now) {
        gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
        gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        gl.useProgram(prog); gl.bindVertexArray(vao);
        gl.uniform1f(uT, now); gl.uniform2f(uRes, w, h);
        gl.uniform3f(uC, 0.918, 0.275, 0.282);   // crimson --prism-1
        gl.drawArrays(gl.POINTS, 0, parts.length);
      },
      dispose: function () {
        gl.deleteBuffer(bufP); gl.deleteBuffer(bufH);
        gl.deleteVertexArray(vao);
        gl.deleteProgram(prog); gl.deleteShader(v); gl.deleteShader(f);
        var lose = gl.getExtension('WEBGL_lose_context');
        if (lose) lose.loseContext();
      }
    };
  }

  function createCanvas2dRenderer(canvas) {
    var ctx = null;
    try { ctx = canvas.getContext('2d'); } catch (e) { ctx = null; }
    if (!ctx) return null;
    var parts = seedParticles(CONFIG.PARTICLES);
    var w = 1, h = 1, scale = 1;
    return {
      kind: 'canvas2d',
      resize: function (cw, ch, dpr) { w = cw; h = ch; scale = dpr || 1; },
      draw: function (now) {
        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = 'rgba(234,70,72,0.5)';
        var r = Math.max(1, h * 0.002);
        for (var i = 0; i < parts.length; i++) {
          var p = parts[i];
          var y = (p.y + now * 0.000004 * (0.4 + p.speed)) % 1;
          var alpha = 0.25 + 0.45 * Math.sin(now * 0.001 + p.phase);
          ctx.globalAlpha = Math.max(0.05, alpha);
          ctx.beginPath();
          ctx.arc(p.x * w, y * h, r * scale, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.globalAlpha = 1;
      },
      dispose: function () { ctx.clearRect(0, 0, w, h); }
    };
  }

  /* Final visual rung: a static inline SVG. Used for reduced motion, low-power
     devices, and any environment where no drawing context could be acquired. */
  function drawStaticSvg(stage, nodes) {
    if (stage.querySelector('[data-cgm-static-links]')) return;   // idempotent
    var NS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('data-cgm-static-links', '');
    svg.setAttribute('viewBox', '0 0 100 100');
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    var hub = null;
    nodes.forEach(function (n) { if (n.cap.id === 'operations') hub = n.cap; });
    if (hub) {
      nodes.forEach(function (n) {
        if (n.cap.id === 'operations') return;
        var line = document.createElementNS(NS, 'line');
        line.setAttribute('x1', hub.x); line.setAttribute('y1', hub.y);
        line.setAttribute('x2', n.cap.x); line.setAttribute('y2', n.cap.y);
        line.setAttribute('stroke', 'rgba(234,70,72,0.22)');
        line.setAttribute('stroke-width', '0.25');
        svg.appendChild(line);
      });
    }
    stage.insertBefore(svg, stage.firstChild);
  }

  /* ─────────────────────────────────────────────────────────────────────
     MOTION PREFERENCE CONTROL
     ───────────────────────────────────────────────────────────────────── */
  function initMotionToggle() {
    var btn = document.querySelector('[data-cgm-motion-toggle]');
    if (!btn) return;

    function paint() {
      var reduced = motionReduced();
      html.setAttribute('data-cgm-motion', reduced ? 'reduced' : 'full');
      btn.setAttribute('aria-pressed', reduced ? 'true' : 'false');
      btn.textContent = reduced ? 'Visual effects: reduced' : 'Reduce visual effects';
    }
    paint();

    btn.addEventListener('click', function () {
      stored = motionReduced() ? 'full' : 'reduced';
      try { window.localStorage.setItem(CONFIG.STORAGE_KEY, stored); } catch (e) { /* ignore */ }
      paint();
      // Tear down live renderers immediately rather than waiting for a reload.
      if (motionReduced()) {
        Array.prototype.forEach.call(
          document.querySelectorAll('.cgm-constellation__stage'),
          function (stage) { if (typeof stage.cgDispose === 'function') stage.cgDispose(); }
        );
      }
    });

    if (reduceQuery.addEventListener) {
      reduceQuery.addEventListener('change', paint);
    }
  }

  /* ─────────────────────────────────────────────────────────────────────
     LIVE SIGNAL BADGE — pulses only when the state attribute actually changes.
     Nothing here invents a value; it reacts to a real mutation.
     ───────────────────────────────────────────────────────────────────── */
  function initSignalBadges() {
    if (!('MutationObserver' in window)) return;
    var badges = document.querySelectorAll('.cgm-signal-badge');
    if (!badges.length) return;
    var mo = new MutationObserver(function (records) {
      records.forEach(function (r) {
        if (r.attributeName !== 'data-state') return;
        var el = r.target;
        if (motionReduced()) return;         // state still readable as text
        el.classList.remove('cgm-pulse');
        void el.offsetWidth;                 // restart the animation
        el.classList.add('cgm-pulse');
      });
    });
    Array.prototype.forEach.call(badges, function (b) {
      mo.observe(b, { attributes: true, attributeFilter: ['data-state'] });
    });
  }

  /* ─────────────────────────────────────────────────────────────────────
     ATMOSPHERIC PARTICLE FIELD — the one place a GPU context earns its keep.
     WebGL2 first, Canvas2D as the fallback, nothing at all under reduced
     motion or on low-power devices (the CSS gradients carry the look there).
     ───────────────────────────────────────────────────────────────────── */
  function initAtmosphereField() {
    var atmos = document.querySelector('.cgm-atmos');
    if (!atmos || !advancedAllowed()) return;

    var dpr = Math.min(window.devicePixelRatio || 1, CONFIG.DPR_CAP);
    var canvas = document.createElement('canvas');
    canvas.className = 'cgm-atmos__canvas';
    canvas.setAttribute('aria-hidden', 'true');
    atmos.appendChild(canvas);

    var renderer = createWebgl2Renderer(canvas) || createCanvas2dRenderer(canvas);
    if (!renderer) { canvas.remove(); return; }
    atmos.setAttribute('data-cgm-renderer', renderer.kind);

    var running = false, rafId = 0, last = 0;
    var minFrame = 1000 / CONFIG.FPS_CAP;

    function resize() {
      canvas.width = Math.round(window.innerWidth * dpr);
      canvas.height = Math.round(window.innerHeight * dpr);
      renderer.resize(canvas.width, canvas.height, dpr);
    }
    function frame(now) {
      if (!running) return;
      rafId = requestAnimationFrame(frame);
      if (now - last < minFrame) return;
      last = now;
      renderer.draw(now);
    }
    function start() { if (running) return; running = true; last = 0; rafId = requestAnimationFrame(frame); }
    function stop() { running = false; if (rafId) cancelAnimationFrame(rafId); rafId = 0; }

    document.addEventListener('visibilitychange', function () {
      document.hidden ? stop() : start();
    });
    window.addEventListener('resize', resize);
    resize();
    start();

    function dispose() {
      stop();
      renderer.dispose();
      canvas.width = canvas.height = 0;
      canvas.remove();
      atmos.removeAttribute('data-cgm-renderer');
    }
    window.addEventListener('pagehide', dispose);
    atmos.cgmDispose = dispose;
  }

  /* ── boot ──────────────────────────────────────────────────────────── */
  function boot() {
    try { initScatter(); } catch (e) {}
    try { initReveals(); } catch (e) {}
    try { initPointerGlass(); } catch (e) {}
    try { initCursorLight(); } catch (e) {}
    try { initCustomCursor(); } catch (e) {}
    try { initConstellation(); } catch (e) {}
    try { initAtmosphereField(); } catch (e) {}
    try { initMotionToggle(); } catch (e) {}
    try { initSignalBadges(); } catch (e) {}

    // Report WebGPU availability without depending on it; the ladder's top
    // rung is advisory until a shipped WGSL path is verified on real hardware.
    if (!(navigator.gpu && typeof navigator.gpu.requestAdapter === 'function')) {
      html.classList.add('cgm-no-webgpu');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else { boot(); }

  window.ClearGlassMotion = { config: CONFIG, capabilities: CAPABILITIES };
})();
