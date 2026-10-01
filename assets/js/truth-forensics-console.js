/* ClearGlass Truth Forensics — evidence integrity console (UI).
 *
 * Drives assets/js/truth-forensics-engine.js. Everything runs in this
 * browser tab: files are read into memory, hashed and analysed locally
 * (in a Web Worker where the browser allows it), and discarded when the
 * session is cleared or the tab closes. Nothing is uploaded, stored or sent
 * to an AI service.
 *
 * Security: every string that can come from evidence (filenames, metadata,
 * claims, notes) is written with textContent or as an SVG text node. This
 * file never parses a string as HTML; tests/test_truth_forensics_parity.py
 * fails if it tries.
 */
(function () {
  'use strict';
  var E = window.ClearGlassTruthForensics;
  var root = document.getElementById('tf-app');
  if (!E || !root) return;
  var V = E.vocab;
  var DEMO_BASE = '/data/truth-forensics/';
  var MAX_FILE = 256 * 1024 * 1024;
  var MAX_ANALYSIS = 64 * 1024 * 1024;
  var MAX_DECODE_PIXELS = 16000000;
  var MAX_AUDIO_SECONDS = 600;
  var reduceMotion = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  var objectUrls = [];
  var mediaViews = {};  // rendered waveform/spectrogram nodes, kept out of the analysis data

  // ------------------------------------------------------------------
  // DOM helpers — text only
  // ------------------------------------------------------------------
  function h(tag, attrs, kids) {
    var el = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'text') el.textContent = String(v);
      else if (k === 'on') Object.keys(v).forEach(function (evn) { el.addEventListener(evn, v[evn]); });
      else if (k === 'class') el.className = v;
      else el.setAttribute(k, v === true ? '' : String(v));
    });
    append(el, kids);
    return el;
  }
  function append(el, kids) {
    if (kids === null || kids === undefined || kids === false) return el;
    if (!Array.isArray(kids)) kids = [kids];
    kids.forEach(function (k) {
      if (k === null || k === undefined || k === false) return;
      el.appendChild(typeof k === 'string' || typeof k === 'number' ? document.createTextNode(String(k)) : k);
    });
    return el;
  }
  var SVGNS = 'http://www.w3.org/2000/svg';
  function s(tag, attrs, kids) {
    var el = document.createElementNS(SVGNS, tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') el.textContent = String(attrs[k]);
      else el.setAttribute(k, String(attrs[k]));
    });
    (kids || []).forEach(function (k) { if (k) el.appendChild(k); });
    return el;
  }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
  function chip(state, label) { return h('span', { class: 'tf-chip tf-s-' + String(state).replace(/[^A-Z_]/g, ''), text: label || state }); }
  function short(hash) { return hash ? hash.slice(0, 12) + '…' + hash.slice(-6) : ''; }
  function say(el, text, isError) { if (!el) return; el.textContent = text; el.classList.toggle('tf-error', !!isError); }
  function nowIso() { return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'); }
  function bytesLabel(n) { return n < 1024 ? n + ' B' : n < 1048576 ? (n / 1024).toFixed(1) + ' KiB' : (n / 1048576).toFixed(1) + ' MiB'; }
  function table(caption, head, rows) {
    return h('div', { class: 'tf-table-wrap' }, h('table', { class: 'tf-table' }, [
      caption ? h('caption', { text: caption }) : null,
      h('thead', {}, h('tr', {}, head.map(function (c) { return h('th', { scope: 'col', text: c }); }))),
      h('tbody', {}, rows.map(function (r) { return h('tr', r.attrs || {}, (r.cells || r).map(function (c) { return h('td', {}, c); })); }))
    ]));
  }
  function kv(pairs) {
    var dl = h('dl', { class: 'tf-kv' });
    pairs.forEach(function (p) { if (p[1] === undefined || p[1] === null || p[1] === '') return; dl.appendChild(h('dt', { text: p[0] })); dl.appendChild(h('dd', {}, p[1])); });
    return dl;
  }
  function download(name, text, type) {
    var url = URL.createObjectURL(new Blob([text], { type: type }));
    var a = h('a', { href: url, download: name });
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
  }

  // ------------------------------------------------------------------
  // Session model
  // ------------------------------------------------------------------
  // { kind, kase, analyzed:{records, analyses, telemetry}, reviews:[], claim, at, result, report }
  var sessions = { demo: null, local: null };

  async function assess(session) {
    var res = await E.assessCase(session.kase, session.analyzed, session.reviews, session.claim, session.at);
    res.telemetry = session.analyzed.telemetry;
    session.result = res;
    session.report = null;
    return res;
  }

  // ------------------------------------------------------------------
  // Workspace (tabbed) — one per session
  // ------------------------------------------------------------------
  var TABS = [['overview', 'Overview'], ['evidence', 'Evidence'], ['timeline', 'Timeline'], ['graph', 'Evidence graph'],
    ['claim', 'Claim'], ['corroboration', 'Corroboration'], ['findings', 'Findings'], ['review', 'Human review'],
    ['report', 'Report'], ['audit', 'Audit trail']];

  function workspace(host, session) {
    clear(host);
    var id = 'tf-' + session.kind;
    var list = h('div', { class: 'tf-tabs', role: 'tablist', 'aria-label': 'Case workspace' });
    var panels = {};
    TABS.forEach(function (t, i) {
      var btn = h('button', { type: 'button', class: 'tf-btn tf-btn-quiet', role: 'tab', id: id + '-tab-' + t[0],
        'aria-controls': id + '-panel-' + t[0], 'aria-selected': i === 0 ? 'true' : 'false', tabindex: i === 0 ? '0' : '-1', text: t[1] });
      btn.addEventListener('click', function () { select(t[0]); });
      btn.addEventListener('keydown', function (ev) {
        var k = ev.key, idx = TABS.findIndex(function (x) { return x[0] === t[0]; });
        if (k === 'ArrowRight' || k === 'ArrowLeft') {
          ev.preventDefault();
          var next = TABS[(idx + (k === 'ArrowRight' ? 1 : TABS.length - 1)) % TABS.length][0];
          select(next); document.getElementById(id + '-tab-' + next).focus();
        }
      });
      list.appendChild(btn);
      panels[t[0]] = h('div', { role: 'tabpanel', id: id + '-panel-' + t[0], 'aria-labelledby': id + '-tab-' + t[0], class: i === 0 ? '' : 'tf-hidden', tabindex: '0' });
    });
    function select(name) {
      TABS.forEach(function (t) {
        var on = t[0] === name;
        document.getElementById(id + '-tab-' + t[0]).setAttribute('aria-selected', on ? 'true' : 'false');
        document.getElementById(id + '-tab-' + t[0]).setAttribute('tabindex', on ? '0' : '-1');
        panels[t[0]].classList.toggle('tf-hidden', !on);
      });
    }
    host.appendChild(list);
    TABS.forEach(function (t) { host.appendChild(panels[t[0]]); });
    session.panels = panels;
    session.select = select;
    renderAll(session);
  }

  function renderAll(session) {
    var r = session.result, p = session.panels;
    renderOverview(session, clear(p.overview));
    renderEvidence(session, clear(p.evidence));
    renderTimeline(r, clear(p.timeline));
    renderGraph(r, clear(p.graph));
    renderClaim(session, clear(p.claim));
    renderCorroboration(r, clear(p.corroboration));
    renderFindings(session, clear(p.findings));
    renderReview(session, clear(p.review));
    renderReport(session, clear(p.report));
    renderAudit(session, clear(p.audit));
  }

  // ------------------------------------------------------------------
  // Overview: pipeline, tiles, analytical indicators, bifocal
  // ------------------------------------------------------------------
  function renderOverview(session, el) {
    var r = session.result;
    if (r.demonstration) el.appendChild(h('p', { class: 'tf-demo-banner', text: r.label }));
    var pipe = h('ol', { class: 'tf-pipeline', 'aria-label': 'Analysis pipeline' });
    r.pipeline.forEach(function (st) { pipe.appendChild(h('li', { 'data-state': st.status, text: st.stage.replace(/_/g, ' ') + (st.status === 'DONE' ? ' ✓' : ' …') })); });
    el.appendChild(h('h3', { text: 'Pipeline' }));
    el.appendChild(pipe);
    el.appendChild(h('p', { class: 'tf-job', text: 'Job: ' + r.job.history.join(' → ') }));
    var claimVerdict = r.claim ? r.claim.verdict : 'no claim';
    el.appendChild(h('div', { class: 'tf-grid tf-grid-5', style: 'margin-top:16px' }, [
      tile(r.evidence.length, 'evidence items'), tile(r.summary.independent_groups, 'independent groups'),
      tile(r.summary.open_findings, 'open findings'), tile(claimVerdict.replace(/_/g, ' '), 'claim assessment'),
      tile(r.bifocal.score === null ? '—' : r.bifocal.score, 'bifocal consistency')
    ]));
    el.appendChild(h('p', { class: 'tf-muted tf-small', text: r.summary.statement }));
    el.appendChild(h('h3', { text: 'Analytical indicators' }));
    el.appendChild(h('p', { class: 'tf-muted tf-small', text: r.integrity_indicators.note }));
    var g = h('div', { class: 'tf-grid tf-grid-5' });
    Object.keys(r.integrity_indicators.values).forEach(function (k) {
      var v = r.integrity_indicators.values[k];
      var bar = h('i', { style: 'width:' + (v === null ? 0 : v) + '%' });
      g.appendChild(h('div', { class: 'tf-meter', role: 'group', 'aria-label': k.replace(/_/g, ' ') + ': ' + (v === null ? 'not measurable' : v + ' percent') }, [
        h('div', { class: 'tf-meter-head' }, [h('span', { text: k.replace(/_/g, ' ') }), h('span', { text: v === null ? 'n/a' : v + '%' })]),
        h('div', { class: 'tf-meter-bar', 'aria-hidden': 'true' }, bar),
        h('p', { text: r.integrity_indicators.definitions[k] })
      ]));
    });
    el.appendChild(g);
    el.appendChild(h('h3', { text: 'ClearGlass Bifocal Verification' }));
    var b = r.bifocal;
    el.appendChild(h('p', { class: 'tf-small' }, [chip(b.status === 'INSUFFICIENT_CHANNELS' ? 'INCONCLUSIVE' : b.status, b.status.replace(/_/g, ' ')),
      ' Coverage ' + b.coverage + ' channels. Score: ' + (b.score === null ? 'not reported' : b.score + ' of 100 (' + b.scored_checks + ' independent checks)') + '. ', h('strong', { text: b.disclaimer })]));
    if (b.checks.length) {
      el.appendChild(table('Bifocal checks', ['Check', 'Channel', 'Result', 'Independent', 'Detail'], b.checks.map(function (c) {
        return [c.check, c.channel, chip(c.result), c.independent ? 'yes' : 'no — excluded', c.detail + (c.note ? ' ' + c.note : '')];
      })));
    }
    el.appendChild(h('details', {}, [h('summary', { text: 'Channel adapters (what is and is not implemented)' }),
      h('ul', {}, b.adapters.map(function (a) { return h('li', {}, [a.name + ': ', chip(a.implemented ? 'NORMAL' : 'UNVERIFIED', a.implemented ? 'implemented' : 'not implemented')]); }))]));
  }
  function tile(value, label) { return h('div', { class: 'tf-tile' }, [h('b', { text: String(value) }), h('span', { text: label })]); }

  // ------------------------------------------------------------------
  // Evidence inventory + detail
  // ------------------------------------------------------------------
  function renderEvidence(session, el) {
    var r = session.result, detail = h('div', { class: 'tf-panel', style: 'margin-top:14px', 'aria-live': 'polite' });
    var rows = r.evidence.map(function (e) {
      var btn = h('button', { type: 'button', class: 'tf-linkish', text: e.evidence_id, 'aria-label': 'Show details for ' + e.evidence_id });
      btn.addEventListener('click', function () { showDetail(r, e.evidence_id, detail); });
      return [btn, e.label, e.object_kind.toLowerCase() + ' ' + e.source_type, e.mime_sniffed,
        h('span', { class: 'tf-hash', title: e.content_sha256, text: short(e.content_sha256) }), chip(e.integrity_state), e.group,
        chip(e.proposed_status), chip(e.final_status), String(e.open_findings)];
    });
    el.appendChild(table('Evidence inventory. Final status combines analysis with human review; demonstration data is always SIMULATED.',
      ['ID', 'Label', 'Kind', 'Type (from bytes)', 'SHA-256', 'Integrity', 'Group', 'Proposed', 'Final', 'Open'], rows));
    el.appendChild(detail);
    if (r.evidence.length) showDetail(r, r.evidence[0].evidence_id, detail);
  }
  function showDetail(r, eid, el) {
    clear(el);
    var e = r.evidence.filter(function (x) { return x.evidence_id === eid; })[0], a = r.analyses[eid];
    if (!e) return;
    el.appendChild(h('h3', { text: eid + ' — ' + e.label }));
    el.appendChild(kv([['SHA-256', h('span', { class: 'tf-hash', text: e.content_sha256 })], ['Size', bytesLabel(e.size_bytes) + ' (' + e.size_bytes + ' bytes)'],
      ['Type from bytes', e.mime_sniffed], ['Declared type', e.mime_declared || '—'], ['File name (label only)', e.declared_name || '—'],
      ['Acquired', e.acquired_at + ' by ' + e.acquired_by + ' via ' + e.acquisition_method], ['Boundary', e.processing_boundary],
      ['Lineage', e.lineage.join(' → ')], ['Transformation', e.transformation || '—'], ['Upstream source', e.upstream_source || '—'],
      ['Status rule', e.status_rule], ['Analyzer', a.analyzer + (a.browser_analyzers ? ' + ' + a.browser_analyzers.join(', ') : '')]]));
    el.appendChild(h('h4', { text: 'Observations' }));
    el.appendChild(a.observations.length ? table('', ['Dimension', 'Value', 'Basis', 'Source'], a.observations.map(function (o) { return [o.dimension, o.value, o.basis, o.source]; }))
      : h('p', { class: 'tf-muted', text: 'No observations. Metadata-free files and unanalysed types carry none until an analyst adds them.' }));
    if (mediaViews[eid] && r.case_id.indexOf('LOCAL-') === 0) el.appendChild(mediaViews[eid]);
    el.appendChild(h('h4', { text: 'Metadata (as the file states it; unsigned)' }));
    el.appendChild(h('pre', { class: 'tf-pre', text: JSON.stringify(a.metadata, null, 2) }));
    if (a.not_performed && a.not_performed.length) {
      el.appendChild(h('h4', { text: 'Not performed' }));
      el.appendChild(h('ul', { class: 'tf-small tf-muted' }, a.not_performed.map(function (n) { return h('li', { text: n }); })));
    }
  }

  // ------------------------------------------------------------------
  // Timeline (SVG + table alternative)
  // ------------------------------------------------------------------
  var SEG_COLOURS = { NORMAL: '#3fbf86', SUPPORTED: '#56d8f5', REVIEW: '#f5c451', ANOMALY: '#ea4648' };
  function renderTimeline(r, el) {
    var keys = Object.keys(r.timelines).sort();
    if (!keys.length) { el.appendChild(h('p', { class: 'tf-muted', text: 'No frame-timed media in this case. Add an MP4 or MOV file to see a frame-timing timeline.' })); return; }
    keys.forEach(function (eid) {
      var tl = r.timelines[eid], segs = tl.segments;
      var total = segs.reduce(function (m, x) { return Math.max(m, x.end_ms); }, 1), W = 1000, H = 96;
      var svgEl = s('svg', { class: 'tf-viz', viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': 'Frame timeline for ' + eid + ': ' + segs.map(function (x) { return E.fmtMs(x.start_ms) + ' to ' + E.fmtMs(x.end_ms) + ' ' + x.label; }).join('; ') });
      segs.forEach(function (x) {
        var x0 = x.start_ms / total * W, w = Math.max(2, (x.end_ms - x.start_ms) / total * W);
        svgEl.appendChild(s('rect', { x: x0, y: 30, width: w, height: 26, rx: 3, fill: SEG_COLOURS[x.label] || '#888', opacity: 0.85 }, [s('title', { text: x.label + ' ' + E.fmtMs(x.start_ms) + '–' + E.fmtMs(x.end_ms) + ': ' + x.reason })]));
        if (w > 70) svgEl.appendChild(s('text', { x: x0 + 4, y: 24, text: x.label }));
      });
      var step = total > 120000 ? 30000 : total > 30000 ? 10000 : 5000;
      svgEl.appendChild(s('line', { class: 'tf-axis', x1: 0, x2: W, y1: 64, y2: 64 }));
      for (var t = 0; t <= total; t += step) {
        var x = t / total * W;
        svgEl.appendChild(s('line', { class: 'tf-axis', x1: x, x2: x, y1: 60, y2: 68 }));
        svgEl.appendChild(s('text', { x: Math.min(x + 2, W - 40), y: 84, text: E.fmtMs(t).slice(0, 5) }));
      }
      el.appendChild(h('h3', { text: eid + ' — nominal ' + Math.floor(tl.fps_x100 / 100) + '.' + String(tl.fps_x100 % 100).padStart(2, '0') + ' fps, ' + tl.intervals + ' frame intervals' + (tl.corroborated_by ? ', SUPPORTED spans covered by ' + tl.corroborated_by : '') }));
      el.appendChild(h('div', { class: 'tf-panel' }, svgEl));
      el.appendChild(table('Timeline segments (text alternative)', ['From', 'To', 'State', 'Reason'], segs.map(function (x) { return [E.fmtMs(x.start_ms), E.fmtMs(x.end_ms), chip(x.label), x.reason]; })));
    });
    el.appendChild(h('p', { class: 'tf-muted tf-small', text: 'A gap estimates missing frames from the container timing table. It cannot distinguish encoder drops from deletion; a SUPPORTED span is covered by an independent channel, not proven.' }));
  }

  // ------------------------------------------------------------------
  // Evidence graph (SVG + edge table)
  // ------------------------------------------------------------------
  var COLS = [['Source'], ['Evidence'], ['Transformation', 'Analysis'], ['Device', 'Location', 'Timestamp', 'Subject', 'Person', 'Organization', 'Event'], ['Claim']];
  var NODE_COLOURS = { Evidence: '#56d8f5', Source: '#9fb0c4', Transformation: '#b59cff', Analysis: '#6b7c93', Device: '#f5c451', Location: '#55f2a6',
    Timestamp: '#7fd3ff', Subject: '#ff9f7a', Person: '#ff9f7a', Organization: '#ff9f7a', Event: '#ffd27a', Claim: '#ea4648' };
  function renderGraph(r, el) {
    var showInf = true, showAnalysis = false, host = h('div', { class: 'tf-panel' });
    var ctrl = h('div', { class: 'tf-actions' });
    var inf = h('input', { type: 'checkbox', id: 'tf-g-inf-' + r.case_id, checked: true });
    var an = h('input', { type: 'checkbox', id: 'tf-g-an-' + r.case_id });
    inf.addEventListener('change', function () { showInf = inf.checked; draw(); });
    an.addEventListener('change', function () { showAnalysis = an.checked; draw(); });
    append(ctrl, [h('label', {}, [inf, ' Show inferences (dashed)']), h('label', {}, [an, ' Show analyzer nodes']),
      chip('FACTUAL', 'FACTUAL: recorded by the engine'), chip('INFERENCE', 'INFERENCE: read from metadata, an analyst or an analyzer')]);
    el.appendChild(h('p', { class: 'tf-muted tf-small', text: 'Solid edges are facts the engine recorded itself (acquisition, hashing, derivation, analysis). Dashed edges are inferences and are never shown as facts.' }));
    el.appendChild(ctrl); el.appendChild(host);
    function draw() {
      clear(host);
      var nodes = r.graph.nodes.filter(function (n) { return showAnalysis || n.type !== 'Analysis'; });
      var ids = new Set(nodes.map(function (n) { return n.id; }));
      var edges = r.graph.edges.filter(function (e) { return ids.has(e.source) && ids.has(e.target) && (showInf || e.basis === 'FACTUAL'); });
      var colOf = function (n) { for (var i = 0; i < COLS.length; i++) if (COLS[i].indexOf(n.type) >= 0) return i; return 3; };
      var cols = COLS.map(function () { return []; });
      nodes.forEach(function (n) { cols[colOf(n)].push(n); });
      var W = 1100, rowH = 26, H = Math.max(260, Math.max.apply(null, cols.map(function (c) { return c.length; })) * rowH + 60), pos = {};
      cols.forEach(function (c, ci) {
        c.forEach(function (n, k) { pos[n.id] = { x: 70 + ci * ((W - 200) / (COLS.length - 1)), y: 40 + (k + 0.5) * ((H - 60) / Math.max(1, c.length)) }; });
      });
      var svgEl = s('svg', { class: 'tf-viz', viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': 'Evidence graph with ' + nodes.length + ' nodes and ' + edges.length + ' edges; the table below lists every edge.' });
      COLS.forEach(function (c, ci) { svgEl.appendChild(s('text', { x: 70 + ci * ((W - 200) / (COLS.length - 1)) - 30, y: 18, text: c[0] + (c.length > 1 ? ' +' : '') })); });
      edges.forEach(function (e) {
        var a = pos[e.source], b = pos[e.target], mx = (a.x + b.x) / 2;
        var path = s('path', { d: 'M' + a.x + ',' + a.y + ' C' + mx + ',' + a.y + ' ' + mx + ',' + b.y + ' ' + b.x + ',' + b.y,
          class: 'tf-edge-' + e.basis + (e.basis === 'INFERENCE' && !reduceMotion ? ' tf-flow' : '') }, [s('title', { text: e.type + ' (' + e.basis + '): ' + e.why })]);
        svgEl.appendChild(path);
      });
      nodes.forEach(function (n) {
        var p = pos[n.id], label = String(n.label).length > 26 ? String(n.label).slice(0, 25) + '…' : String(n.label);
        svgEl.appendChild(s('g', {}, [s('circle', { class: 'tf-node', cx: p.x, cy: p.y, r: n.type === 'Claim' ? 9 : 6, fill: NODE_COLOURS[n.type] || '#ccc' }, [s('title', { text: n.type + ': ' + n.label })]),
          colOf(n) === COLS.length - 1 ? s('text', { x: p.x - 13, y: p.y + 4, 'text-anchor': 'end', text: label }) : s('text', { x: p.x + 11, y: p.y + 4, text: label })]));
      });
      host.appendChild(svgEl);
      host.appendChild(h('details', {}, [h('summary', { text: 'All ' + edges.length + ' edges as a table' }),
        table('', ['From', 'Relation', 'To', 'Basis', 'Why'], edges.map(function (e) { return [e.source, e.type, e.target, chip(e.basis), e.why]; }))]));
    }
    draw();
  }

  // ------------------------------------------------------------------
  // Claim analyzer + consistency matrix
  // ------------------------------------------------------------------
  function renderClaim(session, el) {
    var r = session.result;
    var input = h('textarea', { id: 'tf-claim-' + session.kind, 'aria-describedby': 'tf-claim-help-' + session.kind });
    input.value = session.claim !== null && session.claim !== undefined ? session.claim : (session.kase.claim || '');
    var status = h('p', { class: 'tf-status', role: 'status' });
    var btn = h('button', { type: 'button', class: 'tf-btn tf-btn-primary', text: 'Assess claim' });
    btn.addEventListener('click', async function () {
      btn.disabled = true; say(status, 'Assessing…');
      try { session.claim = input.value; await assess(session); renderAll(session); session.select('claim'); }
      catch (e) { say(status, 'Could not assess: ' + e.message, true); }
      finally { btn.disabled = false; }
    });
    el.appendChild(h('div', { class: 'tf-form' }, [h('label', { for: 'tf-claim-' + session.kind, text: 'Claim to test' }), input,
      h('p', { id: 'tf-claim-help-' + session.kind, class: 'tf-muted tf-small', text: 'Name the source, subject, time, date and place, e.g. “Video A shows Forklift FL-3 at Dock 2 at 21:43 on 14 March 2026”. Decomposition is rule-based; it is a starting point, not language understanding.' }),
      h('div', { class: 'tf-actions' }, [btn, status])]));
    if (!r.claim) { el.appendChild(h('p', { class: 'tf-muted', text: 'No claim assessed yet.' })); return; }
    var c = r.claim;
    el.appendChild(h('p', {}, ['Assessment: ', chip(c.verdict), ' state ', chip(c.state), ' final after human review: ', chip(c.final_verdict)]));
    el.appendChild(table('Propositions: each is tested against independent groups, not files.', ['#', 'Dimension', 'Value', 'Verdict', 'Confidence', 'Agreeing', 'Conflicting', 'Excluded', 'Rule'],
      c.propositions.map(function (p) {
        var ev = function (list) { return list.map(function (x) { return (x.evidence_id || x.group) + (x.evidence_id ? ' [' + x.group + ']' : ''); }).join(', ') || '—'; };
        return [p.id, p.dimension, Array.isArray(p.value) ? p.value.join(' → ') : (p.value || 'implicit'), chip(p.verdict), chip(p.confidence), ev(p.agreeing), ev(p.conflicting),
          p.excluded.map(function (x) { return x.evidence_id; }).join(', ') || '—', p.rule];
      })));
    el.appendChild(h('h3', { text: 'ClearGlass Consistency Engine' }));
    el.appendChild(table('WHO / WHAT / WHEN / WHERE / HOW / SOURCE / PROVENANCE. Confidence is derived from the rule shown, never from a model score.', ['Dimension', 'Evidence', 'Status', 'Confidence', 'Rationale'],
      r.consistency.map(function (row) { return [row.dimension, row.evidence.join(', ') || '—', chip(row.status), chip(row.confidence), row.rationale]; })));
  }

  // ------------------------------------------------------------------
  // Corroboration matrix
  // ------------------------------------------------------------------
  function renderCorroboration(r, el) {
    var c = r.correlation;
    el.appendChild(h('p', { class: 'tf-small' }, ['Independent pairs agreeing: ' + c.summary.agreeing + '; conflicting: ' + c.summary.conflicting + '; dependent pairs not counted: ' + c.summary.dependent + '.']));
    el.appendChild(h('h3', { text: 'Independence groups' }));
    el.appendChild(h('p', { class: 'tf-muted tf-small', text: 'Copies, derivatives, shared upstream sources and near-duplicate images are one source. Only groups count as corroboration.' }));
    el.appendChild(table('', ['Group', 'Members'], c.groups.map(function (g) { return [g.group, g.members.join(', ')]; })));
    if (c.relations.length) el.appendChild(table('Why items were grouped', ['A', 'B', 'Relation'], c.relations.map(function (x) { return [x.a, x.b, x.reason]; })));
    var dims = ['identity', 'event', 'time', 'location', 'device'];
    el.appendChild(h('h3', { text: 'Corroboration matrix (what each item says)' }));
    el.appendChild(table('', ['Item'].concat(dims), Object.keys(c.grid).sort().map(function (id) { return [id].concat(dims.map(function (d) { return c.grid[id][d].join('; ') || '—'; })); })));
    el.appendChild(h('h3', { text: 'Pairwise relations' }));
    el.appendChild(c.pairs.length ? table('', ['A', 'B', 'Dimension', 'Relation', 'Independent'], c.pairs.map(function (p) { return [p.a, p.b, p.dimension, chip(p.relation), p.independent ? 'yes' : 'no (same group)']; }))
      : h('p', { class: 'tf-muted', text: 'No comparable observations between items.' }));
    el.appendChild(h('h3', { text: 'Conflicts and gaps' }));
    el.appendChild(h('ul', { class: 'tf-small' }, [
      h('li', { text: 'Missing dimensions (no item addresses them): ' + (c.missing.join(', ') || 'none') }),
      h('li', { text: 'Independent time conflicts: ' + (c.temporal_conflicts.map(function (p) { return p.a + ' vs ' + p.b; }).join(', ') || 'none') }),
      h('li', { text: 'Provenance conflicts: ' + (c.provenance_conflicts.map(function (p) { return p.evidence_id + ' (' + p.issue + ')'; }).join('; ') || 'none') })]));
  }

  // ------------------------------------------------------------------
  // Findings (explainable indicators)
  // ------------------------------------------------------------------
  function renderFindings(session, el) {
    var r = session.result;
    if (!r.indicators.length) { el.appendChild(h('p', { text: V.NO_INDICATORS })); return; }
    el.appendChild(h('p', { class: 'tf-small tf-muted', text: 'Every finding answers: what was found, how, on what evidence, with what confidence, what else could explain it, and what the system cannot determine.' }));
    r.indicators.forEach(function (i) {
      var cls = 'tf-finding tf-s-' + i.state;
      el.appendChild(h('article', { class: cls }, [
        h('h4', {}, [i.title + ' ', chip(i.state), ' ', chip(i.confidence, 'confidence ' + i.confidence), ' ', chip(i.resolution, 'review ' + i.resolution)]),
        h('p', { class: 'tf-small tf-mono', text: i.finding_id + ' · ' + i.category + ' · ' + i.analyzer }),
        h('dl', {}, [h('dt', { text: 'Found' }), h('dd', { text: i.title }), h('dt', { text: 'Evidence' }), h('dd', { text: i.evidence }),
          h('dt', { text: 'Method' }), h('dd', { text: i.method }), h('dt', { text: 'Confidence' }), h('dd', { text: i.confidence }),
          h('dt', { text: 'Could also be' }), h('dd', { text: i.alternatives.join('; ') }), h('dt', { text: 'Cannot determine' }), h('dd', { text: i.limitation }),
          i.location ? h('dt', { text: 'Location' }) : null, i.location ? h('dd', { text: i.location }) : null])
      ]));
    });
  }

  // ------------------------------------------------------------------
  // Human review console
  // ------------------------------------------------------------------
  function renderReview(session, el) {
    var r = session.result, k = session.kind;
    el.appendChild(h('p', { class: 'tf-small tf-muted', text: 'Reviews are appended to a hash-chained log and never edit a finding. The analyst (' + r.analyst + ') cannot accept, reject or mark their own analysis inconclusive. A second-review request blocks the requester from deciding.' }));
    var who = h('input', { type: 'text', id: 'tf-rv-who-' + k, value: 'reviewer-1', autocomplete: 'off' });
    var target = h('select', { id: 'tf-rv-target-' + k });
    [['CLAIM', 'CLAIM — the claim assessment']].concat(r.evidence.map(function (e) { return [e.evidence_id, e.evidence_id + ' — ' + e.label]; }))
      .concat(r.indicators.map(function (i) { return [i.finding_id, i.finding_id]; }))
      .forEach(function (o) { target.appendChild(h('option', { value: o[0], text: o[1] })); });
    var action = h('select', { id: 'tf-rv-action-' + k });
    ['ACCEPT', 'REJECT', 'ESCALATE', 'MARK_INCONCLUSIVE', 'REQUEST_SECOND_REVIEW', 'ADD_EVIDENCE', 'ANNOTATE', 'COMMENT'].forEach(function (a) { action.appendChild(h('option', { value: a, text: a.replace(/_/g, ' ') })); });
    var note = h('textarea', { id: 'tf-rv-note-' + k, maxlength: '2000' });
    var status = h('p', { class: 'tf-status', role: 'status' });
    var submit = h('button', { type: 'button', class: 'tf-btn tf-btn-primary', text: 'Record review' });
    submit.addEventListener('click', function () {
      addReview(session, { action: action.value, target: target.value, reviewer: who.value, at: nowIso(), note: note.value }, status);
    });
    var controls = [submit, status];
    if (session.kase.suggested_reviews && session.kase.suggested_reviews.length) {
      var demoBtn = h('button', { type: 'button', class: 'tf-btn', text: 'Apply the demonstration reviews' });
      demoBtn.addEventListener('click', async function () {
        demoBtn.disabled = true;
        for (var i = 0; i < session.kase.suggested_reviews.length; i++) {
          var sr = session.kase.suggested_reviews[i];
          if (session.reviews.some(function (x) { return x.target === sr.target && x.reviewer === sr.reviewer && x.action === sr.action; })) continue;
          await addReview(session, sr, status, true);
        }
        await assess(session); renderAll(session); session.select('review');
        say(document.querySelector('#tf-' + session.kind + '-panel-review .tf-status'),
          'Applied ' + session.reviews.length + ' review(s). Claim final status: ' + (session.result.claim ? session.result.claim.final_verdict : 'n/a') + '.');
      });
      controls.unshift(demoBtn);
    }
    el.appendChild(h('div', { class: 'tf-grid tf-grid-2' }, [
      h('div', { class: 'tf-form' }, [h('label', { for: who.id, text: 'Reviewer' }), who, h('label', { for: target.id, text: 'Target' }), target,
        h('label', { for: action.id, text: 'Action' }), action]),
      h('div', { class: 'tf-form' }, [h('label', { for: note.id, text: 'Note (recorded verbatim)' }), note])]));
    el.appendChild(h('div', { class: 'tf-actions' }, controls));
    var rv = r.reviews;
    el.appendChild(h('p', { class: 'tf-small' }, ['Review chain: ', chip(rv.verified ? 'NORMAL' : 'ANOMALY_DETECTED', rv.verified ? 'verified' : 'broken at #' + rv.first_bad_seq), ' ' + rv.records.length + ' record(s).']));
    if (rv.records.length) {
      el.appendChild(table('Review log (append-only)', ['#', 'Action', 'Target', 'Reviewer', 'At', 'Note', 'Record hash'], rv.records.map(function (x) {
        return [String(x.seq), x.action, x.target, x.reviewer, x.at, x.note, h('span', { class: 'tf-hash', text: short(x.record_hash) })];
      })));
    }
    el.appendChild(h('h3', { text: 'AI analysis + human review = final status' }));
    el.appendChild(table('', ['Item', 'Analysis proposed', 'Review', 'Final'], r.evidence.map(function (e) {
      return [e.evidence_id, chip(e.proposed_status), e.review.state + (e.review.action ? ' (' + e.review.action + ' by ' + e.review.reviewer + ')' : ''), chip(e.final_status)];
    }).concat(r.claim ? [['CLAIM', chip(r.claim.verdict), r.claim.review.state + (r.claim.review.action ? ' (' + r.claim.review.action + ' by ' + r.claim.review.reviewer + ')' : ''), chip(r.claim.final_verdict)]] : [])));
  }
  async function addReview(session, rec, status, quiet) {
    try {
      await E.reviewLogFrom(session.result.analyst, session.reviews.concat([rec]));
    } catch (e) { say(status, 'Refused: ' + e.message, true); return false; }
    session.reviews.push(rec);
    if (!quiet) { await assess(session); renderAll(session); session.select('review'); }
    say(document.querySelector('#tf-' + session.kind + '-panel-review .tf-status') || status, 'Recorded ' + rec.action + ' on ' + rec.target + '.');
    return true;
  }

  // ------------------------------------------------------------------
  // Report
  // ------------------------------------------------------------------
  function renderReport(session, el) {
    var status = h('p', { class: 'tf-status', role: 'status' }), out = h('div');
    var gen = h('button', { type: 'button', class: 'tf-btn tf-btn-primary', text: 'Generate forensic report' });
    gen.addEventListener('click', async function () {
      gen.disabled = true; say(status, 'Generating…');
      try {
        session.report = await E.buildReport(session.result);
        showReport(session, out); say(status, 'Report SHA-256 ' + session.report.report_sha256);
      } catch (e) { say(status, 'Report failed: ' + e.message, true); }
      finally { gen.disabled = false; }
    });
    el.appendChild(h('p', { class: 'tf-small tf-muted', text: 'Fourteen sections; every line is typed OBSERVATION, INTERPRETATION or CONCLUSION. The report is generated in this browser and downloads to your device only.' }));
    el.appendChild(h('div', { class: 'tf-actions' }, [gen, status]));
    el.appendChild(out);
    if (session.report) showReport(session, out);
  }
  function showReport(session, out) {
    clear(out);
    var md = E.renderMarkdown(session.report), id = session.result.case_id || 'case';
    var dMd = h('button', { type: 'button', class: 'tf-btn', text: 'Download report (.md)' });
    var dJs = h('button', { type: 'button', class: 'tf-btn', text: 'Download report (.json)' });
    var dRes = h('button', { type: 'button', class: 'tf-btn', text: 'Download full result (.json)' });
    dMd.addEventListener('click', function () { download(id + '-report.md', md, 'text/markdown'); });
    dJs.addEventListener('click', function () { download(id + '-report.json', JSON.stringify(session.report, null, 2), 'application/json'); });
    dRes.addEventListener('click', function () { download(id + '-result.json', JSON.stringify(session.result, null, 2), 'application/json'); });
    out.appendChild(h('div', { class: 'tf-actions' }, [dMd, dJs, dRes]));
    session.report.sections.forEach(function (sec, n) {
      out.appendChild(h('h3', { text: (n + 1) + '. ' + sec.title }));
      out.appendChild(h('ul', { class: 'tf-small' }, sec.statements.map(function (st) { return h('li', {}, [chip(st.kind === 'CONCLUSION' ? 'SUPPORTED' : st.kind === 'INTERPRETATION' ? 'REVIEW' : 'PENDING', st.kind), ' ' + st.text]); })));
    });
  }

  // ------------------------------------------------------------------
  // Audit trail + telemetry
  // ------------------------------------------------------------------
  function renderAudit(session, el) {
    var r = session.result, p = r.provenance;
    el.appendChild(h('p', { class: 'tf-small' }, ['Provenance ledger: ', chip(p.verified ? 'NORMAL' : 'ANOMALY_DETECTED', p.verified ? 'chain verified' : 'broken at #' + p.first_bad_seq),
      ' ' + p.records.length + ' records; head ', h('span', { class: 'tf-hash', text: short(p.head) })]));
    el.appendChild(table('Append-only, SHA-256 hash-chained: changing any record breaks every hash after it.', ['#', 'Event', 'Subject', 'Actor', 'At', 'Detail', 'Record hash'],
      p.records.map(function (x) { return [String(x.seq), x.event, x.subject_id, x.actor, x.at, JSON.stringify(x.detail), h('span', { class: 'tf-hash', text: short(x.record_hash) })]; })));
    el.appendChild(h('h3', { text: 'AI governance record' }));
    el.appendChild(h('p', { class: 'tf-small', text: r.external_ai.note }));
    el.appendChild(table('', ['Run', 'Analyzer', 'Model', 'Input SHA-256', 'Output SHA-256', 'Confidence', 'Human review'], r.ai_audit.map(function (a) {
      return [a.run_id, a.analyzer, a.model, h('span', { class: 'tf-hash', text: short(a.input_sha256) }), h('span', { class: 'tf-hash', text: short(a.output_sha256) }), a.confidence, a.human_review_status];
    })));
    el.appendChild(h('h3', { text: 'Telemetry (ids and sizes only; never content)' }));
    el.appendChild(table('', ['Item', 'Stage', 'Analyzer', 'Size', 'Duration', 'Outcome'], (r.telemetry || []).map(function (t) {
      return [t.evidence_id, t.stage, t.analyzer, bytesLabel(t.size_bytes), t.duration_ms + ' ms', t.outcome];
    })));
  }

  // ------------------------------------------------------------------
  // Demonstration case
  // ------------------------------------------------------------------
  async function runDemo(btn, status, host) {
    btn.disabled = true;
    try {
      say(status, 'QUEUED — fetching the synthetic demonstration files…');
      var kase = await (await fetch(DEMO_BASE + 'demo-case.json', { credentials: 'same-origin' })).json();
      var files = {};
      for (var i = 0; i < kase.evidence.length; i++) {
        var it = kase.evidence[i];
        var resp = await fetch(DEMO_BASE + it.file, { credentials: 'same-origin' });
        if (!resp.ok) throw new Error('could not load ' + it.file);
        files[it.evidence_id] = new Uint8Array(await resp.arrayBuffer());
      }
      say(status, 'PROCESSING → ANALYZING ' + kase.evidence.length + ' items…');
      var analyzed = await E.analyzeEvidence(kase, files);
      var session = { kind: 'demo', kase: kase, analyzed: analyzed, reviews: [], claim: null, at: kase.analysis_at };
      await assess(session);
      sessions.demo = session;
      workspace(host, session);
      say(status, 'REVIEW_REQUIRED — ' + session.result.summary.open_findings + ' open findings across ' + session.result.evidence.length + ' synthetic items. Nothing here is real evidence.');
    } catch (e) {
      say(status, 'FAILED — ' + e.message, true);
    } finally { btn.disabled = false; }
  }

  // ------------------------------------------------------------------
  // Local evidence (your files; never uploaded)
  // ------------------------------------------------------------------
  var local = { items: [], counter: 0 };
  var worker = null, workerOk = true, pending = {};
  function getWorker() {
    if (!workerOk || typeof Worker === 'undefined') return null;
    if (worker) return worker;
    try {
      worker = new Worker('/assets/js/truth-forensics-worker.js');
      worker.onmessage = function (ev) { var p = pending[ev.data.id]; if (p) { delete pending[ev.data.id]; p(ev.data); } };
      worker.onerror = function () {
        // Fail every pending job so it falls back to the main thread instead of hanging.
        workerOk = false; worker = null;
        Object.keys(pending).forEach(function (k) { var p = pending[k]; delete pending[k]; p({ ok: false, error: 'worker unavailable' }); });
      };
    } catch (e) { workerOk = false; worker = null; }
    return worker;
  }
  function analyzeInWorker(id, buffer, options) {
    var w = getWorker();
    if (!w) return null;
    return new Promise(function (resolve) {
      pending[id] = resolve;
      w.postMessage({ id: id, buffer: buffer, options: options, maxAnalysis: MAX_ANALYSIS }, [buffer]);
    });
  }
  async function analyzeMainThread(bytes, options) {
    var t0 = performance.now();
    var record = await E.acquireBytes(bytes, options);
    var ok = bytes.length <= MAX_ANALYSIS;
    if (!ok) record.processing_boundary = 'HASH_ONLY';
    var analysis = await E.analyzeItem(record, ok ? bytes : null);
    return { ok: true, record: record, analysis: analysis, duration_ms: Math.round(performance.now() - t0) };
  }

  function queueRow(item) {
    return [item.id, item.label, item.kind, bytesLabel(item.size || 0), chip(item.state === 'FAILED' ? 'ANOMALY_DETECTED' : item.state === 'REVIEW_REQUIRED' ? 'REVIEW' : 'PENDING', item.state),
      item.record ? h('span', { class: 'tf-hash', text: short(item.record.content_sha256) }) : '—', item.message || ''];
  }
  function renderQueue() {
    var host = document.getElementById('tf-local-queue');
    clear(host);
    if (!local.items.length) { host.appendChild(h('p', { class: 'tf-muted tf-small', text: 'No evidence added in this session.' })); return; }
    host.appendChild(table('Intake queue: QUEUED → PROCESSING (hash) → ANALYZING → REVIEW_REQUIRED', ['ID', 'Label', 'Source', 'Size', 'State', 'SHA-256', 'Note'], local.items.map(queueRow)));
    var sel = document.getElementById('tf-obs-target');
    if (sel) {
      var cur = sel.value; clear(sel);
      local.items.filter(function (i) { return i.record; }).forEach(function (i) { sel.appendChild(h('option', { value: i.id, text: i.id + ' — ' + i.label })); });
      if (cur) sel.value = cur;
    }
    document.getElementById('tf-local-assess').disabled = !local.items.some(function (i) { return i.record; });
  }

  async function intakeBytes(bytes, label, kind, declaredMime, method, extra) {
    var id = 'EV-' + (++local.counter);
    var item = { id: id, label: label, kind: kind, size: bytes.length, state: 'QUEUED', observations: [] };
    local.items.push(item); renderQueue();
    var options = { label: label, acquired_at: nowIso(), acquired_by: document.getElementById('tf-analyst').value || 'local-analyst',
      declared_name: extra && extra.name || '', declared_mime: declaredMime || '', evidence_id: id, method: method, demonstration: false };
    item.state = 'PROCESSING'; renderQueue();
    var out;
    try {
      var copy = bytes.slice(0);
      out = await (analyzeInWorker(id, copy.buffer, options) || analyzeMainThread(bytes, options));
      if (!out.ok) throw new Error(out.error);
    } catch (e) {
      try { out = await analyzeMainThread(bytes, options); } catch (e2) { item.state = 'FAILED'; item.message = e2.message; renderQueue(); return null; }
    }
    item.state = 'ANALYZING'; renderQueue();
    item.record = out.record; item.analysis = out.analysis; item.duration_ms = out.duration_ms;
    if (extra && extra.url) {
      Object.assign(item.record, { source_type: 'url', mime_sniffed: 'text/uri-list', processing_boundary: 'REFERENCE_ONLY', provenance_state: V.PROVENANCE_GAP });
      item.analysis = await E.analyzeItem(item.record, bytes);
      item.message = extra.notes.join(' ');
    }
    try { await browserAugment(item, bytes); } catch (e) { item.analysis.not_performed.push('Browser media pass failed: ' + e.message); }
    item.state = 'REVIEW_REQUIRED';
    item.message = item.message || (item.analysis.indicators.length ? item.analysis.indicators.length + ' indicator(s)' : 'no indicators from available analyzers');
    renderQueue();
    return item;
  }

  // Browser-only passes: pixels for formats the reference engine cannot
  // decode, Web Audio for compressed audio, sampled frames for video.
  async function browserAugment(item, bytes) {
    var mime = item.record.mime_sniffed, a = item.analysis;
    if (item.record.processing_boundary !== 'PARSE') return;
    if (/^image\/(jpeg|webp|gif)$/.test(mime) && typeof createImageBitmap === 'function') {
      var bmp = await createImageBitmap(new Blob([bytes], { type: mime }));
      if (bmp.width * bmp.height > MAX_DECODE_PIXELS) { a.not_performed.push('Canvas pixel pass skipped: image exceeds the decode limit'); return; }
      var cv = document.createElement('canvas'); cv.width = bmp.width; cv.height = bmp.height;
      var ctx = cv.getContext('2d', { willReadFrequently: true }); ctx.drawImage(bmp, 0, 0);
      var px = E.analyzeCanvasPixels(bmp.width, bmp.height, ctx.getImageData(0, 0, bmp.width, bmp.height).data);
      px.pixels.decoded_by = 'browser canvas';
      a.pixels = px.pixels;
      a.browser_analyzers = (a.browser_analyzers || []).concat(['canvas-pixels@' + E.VERSION]);
      a.not_performed = a.not_performed.filter(function (n) { return n.indexOf('Copy-move pixel analysis of JPEG') !== 0; });
      a.not_performed.push('Pixels decoded by this browser; colour management and decoder differences can change exact values');
      var inds = px.indicators.map(function (x) { x.analyzer = 'canvas-pixels@' + E.VERSION; return x; });
      a.indicators = reassignIds(item.id, a.indicators.concat(inds));
    }
    if (mime.indexOf('audio/') === 0 || mime === 'application/ogg') {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      var actx = new AC();
      try {
        var buf = await actx.decodeAudioData(bytes.slice(0).buffer);
        if (buf.duration > MAX_AUDIO_SECONDS) { a.not_performed.push('Browser audio pass limited: recording exceeds 10 minutes'); return; }
        var chans = []; for (var c = 0; c < buf.numberOfChannels; c++) chans.push(buf.getChannelData(c));
        if (mime !== 'audio/wav') {
          var m = E.analyzePcm(E.floatChannelsToPcm(chans), buf.sampleRate); m.channels = buf.numberOfChannels;
          a.metrics = m;
          a.browser_analyzers = (a.browser_analyzers || []).concat(['webaudio-pcm@' + E.VERSION]);
          a.not_performed = a.not_performed.filter(function (n) { return n.indexOf('Sample analysis of') !== 0; });
          a.not_performed.push('Audio decoded by this browser; codec delay and padding can shift event times slightly');
          a.indicators = reassignIds(item.id, a.indicators.concat(E.audioIndicators(m).map(function (x) { x.analyzer = 'webaudio-pcm@' + E.VERSION; return x; })));
        }
        mediaViews[item.id] = audioViz(chans[0], buf.sampleRate, a.metrics);
      } finally { if (actx.close) actx.close(); }
    }
    if (mime.indexOf('video/') === 0) {
      var frames = await sampleVideo(bytes, mime);
      if (frames) {
        a.browser_video = frames.summary;
        a.browser_analyzers = (a.browser_analyzers || []).concat(['sampled-frames@' + E.VERSION]);
        mediaViews[item.id] = h('div', {}, [h('h4', { text: 'Sampled-frame pass (browser, indicative only)' }), h('p', { class: 'tf-small', text: frames.text })]);
        a.not_performed.push('Sampled-frame pass examines ' + frames.summary.samples + ' evenly spaced frames only; it cannot see frames between samples');
      }
    }
  }
  function reassignIds(eid, inds) {
    var seen = {};
    return inds.map(function (x) { seen[x.code] = (seen[x.code] || 0) + 1; x.finding_id = eid + '#' + x.code + (seen[x.code] === 1 ? '' : '~' + seen[x.code]); return x; });
  }

  // Waveform + spectrogram drawn from decoded audio (a small radix-2 FFT).
  function audioViz(samples, rate, metrics) {
    var W = 900, Hh = 120, wave = document.createElement('canvas'), spec = document.createElement('canvas');
    wave.width = W; wave.height = Hh; spec.width = W; spec.height = Hh;
    wave.setAttribute('role', 'img'); spec.setAttribute('role', 'img');
    wave.setAttribute('aria-label', 'Waveform envelope; flagged points are listed in the findings');
    spec.setAttribute('aria-label', 'Spectrogram, 0 Hz at the bottom to ' + Math.round(rate / 2) + ' Hz at the top');
    var g = wave.getContext('2d'), n = samples.length, per = Math.max(1, Math.floor(n / W));
    g.fillStyle = '#070d16'; g.fillRect(0, 0, W, Hh); g.strokeStyle = '#56d8f5';
    for (var x = 0; x < W; x++) {
      var lo = 1, hi = -1;
      for (var i = x * per; i < Math.min(n, (x + 1) * per); i++) { if (samples[i] < lo) lo = samples[i]; if (samples[i] > hi) hi = samples[i]; }
      g.beginPath(); g.moveTo(x + 0.5, (1 - hi) * Hh / 2); g.lineTo(x + 0.5, (1 - lo) * Hh / 2); g.stroke();
    }
    if (metrics) {
      g.fillStyle = 'rgba(234,70,72,.8)';
      (metrics.discontinuities || []).forEach(function (ms) { g.fillRect(ms / 1000 * rate / n * W, 0, 2, Hh); });
      g.fillStyle = 'rgba(245,196,81,.35)';
      (metrics.digital_silence || []).forEach(function (sp) { g.fillRect(sp[0] / 1000 * rate / n * W, 0, Math.max(2, (sp[1] - sp[0]) / 1000 * rate / n * W), Hh); });
    }
    var N = 256, cols = W, sg = spec.getContext('2d'), img = sg.createImageData(W, Hh), hop = Math.max(1, Math.floor((n - N) / cols));
    for (var cIdx = 0; cIdx < cols && cIdx * hop + N <= n; cIdx++) {
      var re = new Float64Array(N), im = new Float64Array(N);
      for (var k = 0; k < N; k++) re[k] = samples[cIdx * hop + k] * (0.5 - 0.5 * Math.cos(2 * Math.PI * k / (N - 1)));
      fft(re, im);
      for (var y = 0; y < Hh; y++) {
        var bin = Math.floor((1 - y / Hh) * (N / 2 - 1)), mag = Math.sqrt(re[bin] * re[bin] + im[bin] * im[bin]);
        var v = Math.max(0, Math.min(255, Math.round((Math.log10(mag + 1e-9) + 4) * 55))), p = (y * W + cIdx) * 4;
        img.data[p] = v * 0.35; img.data[p + 1] = v * 0.85; img.data[p + 2] = v; img.data[p + 3] = 255;
      }
    }
    sg.putImageData(img, 0, 0);
    return h('div', {}, [h('h4', { text: 'Waveform (red: discontinuities, amber: digital silence) and spectrogram' }), h('div', { class: 'tf-panel' }, [wave, spec])]);
  }
  function fft(re, im) {
    var n = re.length, j = 0, i, t;
    for (i = 1; i < n; i++) { var bit = n >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit; if (i < j) { t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; } }
    for (var len = 2; len <= n; len <<= 1) {
      var ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang);
      for (i = 0; i < n; i += len) {
        var cr = 1, ci = 0;
        for (j = 0; j < len / 2; j++) {
          var ar = re[i + j + len / 2] * cr - im[i + j + len / 2] * ci, ai = re[i + j + len / 2] * ci + im[i + j + len / 2] * cr;
          re[i + j + len / 2] = re[i + j] - ar; im[i + j + len / 2] = im[i + j] - ai; re[i + j] += ar; im[i + j] += ai;
          var ncr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = ncr;
        }
      }
    }
  }

  // Sampled-frame pass: evenly spaced frames, dHash each, report identical
  // neighbours (possible frozen or duplicated frames) and abrupt changes.
  function sampleVideo(bytes, mime) {
    return new Promise(function (resolve) {
      var v = document.createElement('video');
      if (!v.canPlayType(mime)) { resolve(null); return; }
      var url = URL.createObjectURL(new Blob([bytes], { type: mime })), done = false;
      var finish = function (val) { if (done) return; done = true; URL.revokeObjectURL(url); v.removeAttribute('src'); v.load(); resolve(val); };
      var timer = setTimeout(function () { finish(null); }, 20000);
      v.muted = true; v.preload = 'auto'; v.src = url;
      v.addEventListener('error', function () { clearTimeout(timer); finish(null); });
      v.addEventListener('loadedmetadata', async function () {
        var d = v.duration;
        if (!isFinite(d) || d <= 0 || !v.videoWidth) { clearTimeout(timer); finish(null); return; }
        var samples = Math.min(40, Math.max(4, Math.floor(d * 2))), cv = document.createElement('canvas');
        cv.width = 64; cv.height = 36;
        var ctx = cv.getContext('2d', { willReadFrequently: true }), hashes = [];
        for (var i = 0; i < samples; i++) {
          var t = (i + 0.5) * d / samples;
          await new Promise(function (res) { var on = function () { v.removeEventListener('seeked', on); res(); }; v.addEventListener('seeked', on); v.currentTime = t; });
          ctx.drawImage(v, 0, 0, 64, 36);
          var data = ctx.getImageData(0, 0, 64, 36).data, gray = new Uint8Array(64 * 36);
          for (var k = 0, p = 0; k < gray.length; k++, p += 4) gray[k] = Math.floor((299 * data[p] + 587 * data[p + 1] + 114 * data[p + 2]) / 1000);
          hashes.push({ t: t, hash: E.dhash(64, 36, gray) });
        }
        clearTimeout(timer);
        var frozen = [], cuts = [];
        for (var j = 1; j < hashes.length; j++) {
          var dist = E.hammingHex(hashes[j - 1].hash, hashes[j].hash);
          if (dist === 0) frozen.push(E.fmtMs(Math.round(hashes[j].t * 1000)));
          if (dist >= 24) cuts.push(E.fmtMs(Math.round(hashes[j].t * 1000)));
        }
        finish({ summary: { samples: samples, identical_neighbours: frozen, abrupt_changes: cuts },
          text: samples + ' frames sampled. Identical neighbouring samples (possible frozen or duplicated footage, or a static scene): ' + (frozen.join(', ') || 'none') +
            '. Abrupt visual changes (cuts or fast motion): ' + (cuts.join(', ') || 'none') + '. Indicative only; not a finding.' });
      });
    });
  }

  function localCase() {
    return { schema: V.CASE_SCHEMA, case_id: 'LOCAL-' + new Date().toISOString().slice(0, 10), title: 'Local session (evidence never left this browser)',
      demonstration: false, analyst: document.getElementById('tf-analyst').value || 'local-analyst', channels: [], claim: document.getElementById('tf-local-claim').value || '',
      evidence: local.items.filter(function (i) { return i.record; }).map(function (i) { return { evidence_id: i.id, label: i.label }; }) };
  }
  async function assessLocal(status, host) {
    var items = local.items.filter(function (i) { return i.record; });
    if (!items.length) { say(status, 'Add evidence first.', true); return; }
    var analyzed = { records: [], analyses: {}, telemetry: [] };
    items.forEach(function (i) {
      var a = JSON.parse(JSON.stringify(i.analysis));
      i.observations.forEach(function (o) { a.observations.push(o); });
      analyzed.records.push(i.record); analyzed.analyses[i.id] = a;
      analyzed.telemetry.push({ stage: 'CONTENT_ANALYSIS', evidence_id: i.id, size_bytes: i.record.size_bytes, analyzer: a.analyzer, duration_ms: i.duration_ms || 0, outcome: 'ok' });
    });
    var kase = localCase();
    var session = sessions.local && sessions.local.kind === 'local' ? sessions.local : { kind: 'local', reviews: [] };
    Object.assign(session, { kase: kase, analyzed: analyzed, claim: kase.claim, at: nowIso() });
    try {
      await assess(session);
      sessions.local = session;
      workspace(host, session);
      say(status, 'Assessed ' + items.length + ' item(s). ' + session.result.summary.statement);
    } catch (e) { say(status, 'Assessment failed: ' + e.message, true); }
  }

  function clearLocal(status) {
    local.items = []; local.counter = 0; sessions.local = null; mediaViews = {};
    clear(document.getElementById('tf-local-out'));
    objectUrls.forEach(function (u) { URL.revokeObjectURL(u); }); objectUrls = [];
    if (worker) { worker.terminate(); worker = null; }
    renderQueue();
    say(status, 'Session cleared. Evidence, hashes and reviews were held only in this tab and are now discarded.');
  }

  // ------------------------------------------------------------------
  // Wiring
  // ------------------------------------------------------------------
  function wire() {
    var demoBtn = document.getElementById('tf-run-demo');
    var demoStatus = document.getElementById('tf-demo-status');
    var demoOut = document.getElementById('tf-demo-out');
    demoBtn.disabled = false;
    demoBtn.addEventListener('click', function () { runDemo(demoBtn, demoStatus, demoOut); });

    var status = document.getElementById('tf-local-status');
    var fileInput = document.getElementById('tf-files');
    var drop = document.getElementById('tf-drop');
    async function takeFiles(fileList) {
      // Copy first: a FileList is live, and resetting the input empties it.
      var list = Array.prototype.slice.call(fileList || []);
      for (var i = 0; i < list.length; i++) {
        var f = list[i];
        if (f.size > MAX_FILE) { say(status, 'Refused ' + E.displayName(f.name) + ': larger than 256 MiB.', true); continue; }
        say(status, 'Reading ' + E.displayName(f.name) + ' into memory (not uploaded)…');
        var bytes = new Uint8Array(await f.arrayBuffer());
        await intakeBytes(bytes, E.displayName(f.name) || 'file', 'file', f.type, 'file', { name: f.name });
        say(status, 'Hashed and analysed ' + E.displayName(f.name) + ' in this browser.');
      }
    }
    fileInput.addEventListener('change', function () { takeFiles(fileInput.files); fileInput.value = ''; });
    ['dragenter', 'dragover'].forEach(function (n) { drop.addEventListener(n, function (ev) { ev.preventDefault(); drop.classList.add('tf-over'); }); });
    ['dragleave', 'drop'].forEach(function (n) { drop.addEventListener(n, function (ev) { ev.preventDefault(); drop.classList.remove('tf-over'); }); });
    drop.addEventListener('drop', function (ev) { if (ev.dataTransfer && ev.dataTransfer.files) takeFiles(ev.dataTransfer.files); });

    document.getElementById('tf-add-text').addEventListener('click', async function () {
      var t = document.getElementById('tf-text').value;
      if (!t.trim()) { say(status, 'Enter some text first.', true); return; }
      await intakeBytes(new TextEncoder().encode(t), document.getElementById('tf-text-label').value || 'Text entry', 'text', 'text/plain', 'text-entry');
      say(status, 'Text entry hashed and recorded.');
    });
    document.getElementById('tf-add-url').addEventListener('click', async function () {
      var u = document.getElementById('tf-url').value.trim();
      if (!u) { say(status, 'Enter a URL first.', true); return; }
      var v = E.validateUrl(u);
      var notes = ['URL recorded as a reference; its content was not fetched or acquired.'].concat(v[0] ? [] : v[1].map(function (x) { return 'not fetchable: ' + x; }));
      await intakeBytes(new TextEncoder().encode(u), 'URL reference', 'url', '', 'url-reference', { url: true, notes: notes });
      say(status, 'URL recorded as a reference only. This page makes no request to it.');
    });
    document.getElementById('tf-add-event').addEventListener('click', async function () {
      var raw = document.getElementById('tf-event').value, obj;
      try { obj = JSON.parse(raw); } catch (e) { say(status, 'Structured event must be valid JSON.', true); return; }
      if (!obj || typeof obj !== 'object' || Array.isArray(obj)) { say(status, 'Structured event must be a JSON object.', true); return; }
      await intakeBytes(new TextEncoder().encode(E.canonicalJson(obj)), document.getElementById('tf-event-label').value || 'Structured event', 'event', 'application/json', 'structured-event');
      say(status, 'Structured event hashed in canonical JSON form.');
    });
    document.getElementById('tf-add-obs').addEventListener('click', function () {
      var target = document.getElementById('tf-obs-target').value, item = local.items.filter(function (i) { return i.id === target; })[0];
      var value = document.getElementById('tf-obs-value').value.trim();
      if (!item || !value) { say(status, 'Choose an item and enter a value.', true); return; }
      var entity = document.getElementById('tf-obs-entity').value;
      var o = { dimension: document.getElementById('tf-obs-dim').value, value: value.slice(0, 300), basis: 'analyst: ' + (document.getElementById('tf-obs-basis').value || 'observation').slice(0, 200), source: 'analyst' };
      if (o.dimension === 'identity' && entity) o.entity = entity;
      item.observations.push(o);
      document.getElementById('tf-obs-value').value = '';
      say(status, 'Observation added to ' + item.id + ' as an analyst assertion (an inference, not a fact).');
    });
    document.getElementById('tf-local-assess').addEventListener('click', function () { assessLocal(status, document.getElementById('tf-local-out')); });
    document.getElementById('tf-local-clear').addEventListener('click', function () { clearLocal(status); });
    renderQueue();
    if (!(window.crypto && window.crypto.subtle)) {
      say(demoStatus, 'This browser does not expose WebCrypto here (it needs HTTPS). Hashing is unavailable, so the console is disabled.', true);
      demoBtn.disabled = true;
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire); else wire();
})();
