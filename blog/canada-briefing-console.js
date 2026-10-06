/* ClearGlass Insights — Canada strategic briefing console.

   Progressive enhancement for blog/canada-strategic-briefing-october-2026.html.
   The article is complete without this file. With it, a reader gets:

   - the claim ledger, fetched same-origin and checked against its published
     SHA-256 manifest before a single record is shown as trustworthy;
   - status / domain / text filters, deep links (#CA-03), copyable citations,
     and CSV / JSON export generated on the reader's own device;
   - claim chips in the prose that open their ledger record;
   - the scenario cards as an accessible tab set;
   - an action matrix the reader can track locally and export as Markdown.

   Nothing leaves the browser: no analytics, no third-party requests, and
   localStorage only for the reader's own tracked actions. Every string that
   comes from the ledger is escaped before it reaches the DOM, and only
   https: source links are rendered. */
(function () {
  'use strict';

  var DATA_URL = 'data/canada-strategic-briefing-2026-10.json';
  var MANIFEST_URL = 'data/canada-strategic-briefing-2026-10.manifest.json';
  var TRACK_KEY = 'cg:ca-brief-2026-10:tracked:v1';
  var STATUSES = ['confirmed', 'corrected', 'updated', 'assessment', 'target'];
  var GLYPH = { confirmed: '✓', corrected: '≠', updated: '↻', assessment: '◇', target: '◎' };

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function safeUrl(url) {
    try { var u = new URL(url); return u.protocol === 'https:' ? u.href : ''; } catch (e) { return ''; }
  }
  function setText(id, text) { var n = document.getElementById(id); if (n) n.textContent = text; }
  function readStore(key, fallback) {
    try { var v = JSON.parse(localStorage.getItem(key)); return v == null ? fallback : v; } catch (e) { return fallback; }
  }
  function writeStore(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* private mode: tracking is session-only */ }
  }
  function toast(text) {
    var n = $('#toast');
    if (!n) return;
    n.textContent = text;
    n.classList.add('show');
    clearTimeout(toast.t);
    toast.t = setTimeout(function () { n.classList.remove('show'); }, 1800);
  }
  function download(name, type, text) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([text], { type: type }));
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 0);
  }

  /* ------------------------------------------------------------------ ledger */
  var ledger = null;
  var raw = '';
  var filter = { status: 'all', domain: 'all', query: '' };

  function sha256Hex(text) {
    if (!window.crypto || !crypto.subtle || !window.TextEncoder) return Promise.resolve(null);
    return crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)).then(function (buf) {
      return Array.prototype.map.call(new Uint8Array(buf), function (b) { return b.toString(16).padStart(2, '0'); }).join('');
    });
  }

  function loadLedger() {
    var integrity = $('#lgIntegrity');
    if (!integrity || !window.fetch) return;
    Promise.all([
      fetch(DATA_URL, { credentials: 'same-origin' }).then(function (r) { if (!r.ok) throw new Error('ledger HTTP ' + r.status); return r.text(); }),
      fetch(MANIFEST_URL, { credentials: 'same-origin' }).then(function (r) { if (!r.ok) throw new Error('manifest HTTP ' + r.status); return r.json(); })
    ]).then(function (res) {
      raw = res[0];
      var manifest = res[1];
      ledger = JSON.parse(raw);
      return sha256Hex(raw).then(function (hash) {
        var expected = String(manifest.sha256 || '').toLowerCase();
        var state = hash === null ? 'unchecked' : (hash === expected ? 'verified' : 'failed');
        integrity.dataset.state = state;
        integrity.textContent = { verified: 'VERIFIED', failed: 'HASH MISMATCH', unchecked: 'UNCHECKED (no Web Crypto)' }[state];
        var shown = hash || expected;
        setText('lgHash', shown ? shown.slice(0, 12) + '…' + shown.slice(-6) : '—');
        boot();
      });
    }).catch(function (err) {
      integrity.dataset.state = 'failed';
      integrity.textContent = 'LOAD FAILED';
      var rows = $('#lgRows');
      if (rows) rows.insertAdjacentHTML('afterbegin', '<p class="lg-empty">The ledger could not be loaded (' + esc(err.message) + '). The article above is unaffected.</p>');
    });
  }

  function boot() {
    setText('lgAsOf', ledger.asOf || '—');
    if (ledger.asOf) {
      var days = Math.max(0, Math.floor((Date.now() - Date.parse(ledger.asOf + 'T00:00:00Z')) / 86400000));
      setText('lgAge', days === 0 ? 'current' : days + ' day' + (days === 1 ? '' : 's'));
    }
    reconcileTally();
    decorateChips();
    var domains = {};
    ledger.records.forEach(function (r) { domains[r.domain] = true; });
    var select = $('#lgDomain');
    if (select) {
      select.insertAdjacentHTML('beforeend', Object.keys(domains).sort().map(function (d) {
        return '<option value="' + esc(d) + '">' + esc(d) + '</option>';
      }).join(''));
      select.addEventListener('change', function () { filter.domain = select.value; render(); });
    }
    $$('[data-lg-status]').forEach(function (btn) {
      btn.addEventListener('click', function () { setStatus(btn.dataset.lgStatus); });
    });
    var search = $('#lgSearch');
    if (search) search.addEventListener('input', function () { filter.query = search.value.trim(); render(); });
    var csv = $('#lgCSV'); if (csv) csv.addEventListener('click', exportCSV);
    var json = $('#lgJSON'); if (json) json.addEventListener('click', function () {
      download('canada-strategic-briefing-2026-10.json', 'application/json', raw);
    });
    var pr = $('#lgPrint'); if (pr) pr.addEventListener('click', function () { window.print(); });
    var controls = $('#lgControls'); if (controls) controls.hidden = false;
    render();
    var m = /^#(CA-\d{2})$/.exec(location.hash);
    if (m) focusRecord(m[1]);
  }

  /* The static tally is authored into the page so it reads without JS. If it
     ever disagrees with the ledger, the ledger wins and the page says so. */
  function reconcileTally() {
    var counts = { total: ledger.records.length };
    STATUSES.forEach(function (s) { counts[s] = 0; });
    ledger.records.forEach(function (r) { counts[r.status] = (counts[r.status] || 0) + 1; });
    $$('[data-count]').forEach(function (n) {
      var key = n.getAttribute('data-count');
      var want = String(counts[key] || 0);
      if (n.textContent !== want) { n.textContent = want; n.title = 'Updated from the ledger'; }
    });
  }

  function byId(id) {
    for (var i = 0; i < ledger.records.length; i++) if (ledger.records[i].id === id) return ledger.records[i];
    return null;
  }

  function decorateChips() {
    $$('a.claim[data-claim]').forEach(function (chip) {
      var rec = byId(chip.dataset.claim);
      if (!rec) return;
      chip.title = rec.status.toUpperCase() + ' · ' + rec.finding;
      chip.addEventListener('click', function (e) {
        e.preventDefault();
        focusRecord(rec.id);
      });
    });
  }

  function setStatus(status) {
    filter.status = status;
    $$('[data-lg-status]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.lgStatus === status)); });
    render();
  }

  function focusRecord(id) {
    filter = { status: 'all', domain: 'all', query: '' };
    var search = $('#lgSearch'); if (search) search.value = '';
    var select = $('#lgDomain'); if (select) select.value = 'all';
    setStatus('all');
    var row = document.getElementById(id);
    if (!row) return;
    if (history.replaceState) history.replaceState(null, '', '#' + id);
    row.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    row.classList.add('flash');
    row.setAttribute('tabindex', '-1');
    row.focus({ preventScroll: true });
    setTimeout(function () { row.classList.remove('flash'); }, 2200);
  }

  function matches(r) {
    if (filter.status !== 'all' && r.status !== filter.status) return false;
    if (filter.domain !== 'all' && r.domain !== filter.domain) return false;
    if (!filter.query) return true;
    var hay = [r.id, r.domain, r.status, r.draft, r.finding].concat((r.sources || []).map(function (s) { return s.publisher + ' ' + s.title; })).join(' ').toLowerCase();
    return hay.indexOf(filter.query.toLowerCase()) !== -1;
  }

  function render() {
    var root = $('#lgRows');
    if (!root || !ledger) return;
    var rows = ledger.records.filter(matches);
    setText('lgVisible', rows.length + ' of ' + ledger.records.length);
    if (!rows.length) { root.innerHTML = '<p class="lg-empty">No records match these filters.</p>'; return; }
    root.innerHTML = rows.map(function (r) {
      var status = STATUSES.indexOf(r.status) === -1 ? 'assessment' : r.status;
      var sources = (r.sources || []).map(function (s) {
        var href = safeUrl(s.url);
        var label = esc(s.publisher) + ' — ' + esc(s.title);
        return '<li>' + (href ? '<a href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">' + label + '</a>' : label) + '</li>';
      }).join('');
      return '<article class="lg-row s-' + status + '" id="' + esc(r.id) + '">' +
        '<header><span><code>' + esc(r.id) + '</code> <span class="lg-state">' + GLYPH[status] + ' ' + esc(status) + '</span></span>' +
        '<span class="lg-meta">' + esc(r.domain) + ' · §' + esc(r.section) + ' · confidence ' + esc(r.confidence) + ' · via ' + esc(r.checkedVia) + '</span></header>' +
        '<p class="lg-draft">Draft: ' + (status === 'corrected' ? '<s>' + esc(r.draft) + '</s>' : esc(r.draft)) + '</p>' +
        '<p class="lg-find">' + esc(r.finding) + '</p>' +
        (sources ? '<ul class="lg-src">' + sources + '</ul>' : '<p class="lg-meta">No external source: labelled, not verified.</p>') +
        '<div class="lg-actions"><button type="button" data-cite="' + esc(r.id) + '">Copy citation</button><button type="button" data-link="' + esc(r.id) + '">Copy link</button></div>' +
        '</article>';
    }).join('');
    $$('[data-cite]', root).forEach(function (b) { b.addEventListener('click', function () { cite(b.dataset.cite); }); });
    $$('[data-link]', root).forEach(function (b) { b.addEventListener('click', function () { copy(location.href.split('#')[0] + '#' + b.dataset.link, 'Link copied'); }); });
  }

  function copy(text, msg) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { toast(msg); }, function () { toast('Clipboard unavailable'); });
    } else { toast('Clipboard unavailable'); }
  }

  function cite(id) {
    var r = byId(id);
    if (!r) return;
    var first = (r.sources || [])[0];
    copy(r.id + ' [' + r.status + ', as of ' + ledger.asOf + '] ' + r.finding +
      (first ? ' Source: ' + first.publisher + ', ' + first.title + ' <' + first.url + '>.' : '') +
      ' ' + location.href.split('#')[0] + '#' + r.id, 'Citation copied');
  }

  // A cell that opens with = + - @ is a formula to a spreadsheet; neutralize it.
  function csvCell(v) {
    var s = String(v == null ? '' : v);
    if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
    return '"' + s.replace(/"/g, '""') + '"';
  }

  function exportCSV() {
    var head = ['id', 'status', 'domain', 'section', 'draft', 'finding', 'confidence', 'checkedVia', 'sources'];
    var lines = [head.join(',')].concat(ledger.records.map(function (r) {
      return [r.id, r.status, r.domain, r.section, r.draft, r.finding, r.confidence, r.checkedVia,
        (r.sources || []).map(function (s) { return s.url; }).join(' ')].map(csvCell).join(',');
    }));
    download('canada-strategic-briefing-2026-10.csv', 'text/csv;charset=utf-8', '﻿' + lines.join('\r\n'));
  }

  /* --------------------------------------------------------------- scenarios */
  function initScenarios() {
    var tabs = $$('[data-scn-tab]');
    var grid = $('#scnGrid');
    if (!tabs.length || !grid) return;
    var list = tabs[0].parentNode;
    function select(name, focus) {
      tabs.forEach(function (t) {
        var on = t.dataset.scnTab === name;
        t.setAttribute('aria-selected', String(on));
        t.tabIndex = on ? 0 : -1;
        if (on && focus) t.focus();
      });
      $$('.scn-card', grid).forEach(function (c) { c.hidden = c.dataset.scn !== name; });
    }
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { select(t.dataset.scnTab, false); });
      t.addEventListener('keydown', function (e) {
        var step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
        if (!step) return;
        e.preventDefault();
        select(tabs[(i + step + tabs.length) % tabs.length].dataset.scnTab, true);
      });
    });
    grid.classList.add('tabbed');
    list.hidden = false;
    select('base', false);
    window.addEventListener('beforeprint', function () { $$('.scn-card', grid).forEach(function (c) { c.hidden = false; }); });
    window.addEventListener('afterprint', function () {
      var on = tabs.filter(function (t) { return t.getAttribute('aria-selected') === 'true'; })[0];
      select(on ? on.dataset.scnTab : 'base', false);
    });
  }

  /* ----------------------------------------------------------- action matrix */
  function initActions() {
    var table = $('#actionMatrix');
    var controls = $('#amControls');
    if (!table || !controls) return;
    var tracked = readStore(TRACK_KEY, []);
    if (!Array.isArray(tracked)) tracked = [];
    var rows = $$('tbody tr[data-action]', table);
    rows.forEach(function (tr) {
      var id = tr.dataset.action;
      var cell = $('.am-track', tr);
      var label = tr.cells[2] ? tr.cells[2].textContent : id;
      cell.innerHTML = '<input type="checkbox" class="adopt" aria-label="Track action: ' + esc(label) + '">';
      var box = $('input', cell);
      box.checked = tracked.indexOf(id) !== -1;
      box.addEventListener('change', function () {
        tracked = tracked.filter(function (x) { return x !== id; });
        if (box.checked) tracked.push(id);
        writeStore(TRACK_KEY, tracked);
        toast(box.checked ? 'Action tracked in this browser' : 'Action untracked');
      });
    });
    $$('[data-horizon-filter]', controls).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var h = btn.dataset.horizonFilter;
        $$('[data-horizon-filter]', controls).forEach(function (b) { b.setAttribute('aria-pressed', String(b === btn)); });
        rows.forEach(function (tr) { tr.hidden = h !== 'all' && tr.dataset.horizon !== h; });
      });
    });
    var exp = $('#amExport');
    if (exp) exp.addEventListener('click', function () {
      var chosen = rows.filter(function (tr) { return tracked.indexOf(tr.dataset.action) !== -1; });
      if (!chosen.length) { toast('Track at least one action first'); return; }
      var md = ['# Tracked actions — Strategic Briefing: Canada (October 2026)', '',
        'Source: ' + location.href.split('#')[0], 'Exported: ' + new Date().toISOString().slice(0, 10), '',
        'Outcomes are the author\'s proposed measures, not government commitments.', ''];
      chosen.forEach(function (tr) {
        var c = tr.cells;
        md.push('## ' + c[1].textContent, '', '- [ ] ' + c[2].textContent, '- Reason: ' + c[3].textContent,
          '- Risk avoided: ' + c[4].textContent, '- Measurable outcome: ' + c[5].textContent, '');
      });
      download('canada-briefing-tracked-actions.md', 'text/markdown;charset=utf-8', md.join('\n'));
    });
    table.classList.add('live');
    controls.hidden = false;
  }

  /* ---------------------------------------------------------------- keyboard */
  document.addEventListener('keydown', function (e) {
    var tag = (document.activeElement && document.activeElement.tagName) || '';
    if (e.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(tag) && !e.metaKey && !e.ctrlKey) {
      var s = $('#lgSearch');
      if (s && !$('#lgControls').hidden) { e.preventDefault(); s.focus(); }
    }
  });
  window.addEventListener('hashchange', function () {
    var m = /^#(CA-\d{2})$/.exec(location.hash);
    if (m && ledger) focusRecord(m[1]);
  });

  initScenarios();
  initActions();
  loadLedger();
})();
