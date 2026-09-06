(() => {
  'use strict';

  const DATA_URL = 'data/ontario-influence-environment-2026-08-07.json';
  const MANIFEST_URL = 'data/ontario-influence-environment-2026-08-07.manifest.json';
  const NOTE_KEY = 'cg:on-intel:notes:v1';
  const WATCH_KEY = 'cg:on-intel:watch:v1';
  const FILTER_KEY = 'cg:on-intel:filter:v1';
  const sessionId = (crypto.randomUUID ? crypto.randomUUID() : `cg-${Date.now()}-${Math.random().toString(16).slice(2)}`);
  const sessionEvents = [];
  let dataset = null;
  let rawDataset = '';
  let manifest = null;
  let currentHash = '';
  let selectedStatus = 'all';
  let selectedDomain = 'all';
  let selectedConfidence = 'all';
  let query = '';
  let watch = new Set(readJSON(WATCH_KEY, []));

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function readJSON(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
  }

  function logEvent(type, detail = '') {
    const event = { at: new Date().toISOString(), type, detail };
    sessionEvents.push(event);
    const list = $('#custodyLog');
    if (list) {
      const row = document.createElement('li');
      row.innerHTML = `<time>${esc(event.at.slice(11, 19))}Z</time><span>${esc(type)}</span><small>${esc(detail)}</small>`;
      list.prepend(row);
      while (list.children.length > 12) list.lastElementChild.remove();
    }
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function tickClock() {
    const now = new Date();
    setText('utcClock', `${now.toISOString().slice(11, 19)} UTC`);
  }

  async function sha256Hex(text) {
    if (!crypto.subtle) throw new Error('Web Crypto unavailable');
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
  }

  async function loadEvidence() {
    const integrity = $('#integrityState');
    try {
      const [dataResponse, manifestResponse] = await Promise.all([
        fetch(DATA_URL, { cache: 'no-store', credentials: 'same-origin' }),
        fetch(MANIFEST_URL, { cache: 'no-store', credentials: 'same-origin' })
      ]);
      if (!dataResponse.ok || !manifestResponse.ok) throw new Error(`Evidence retrieval failed (${dataResponse.status}/${manifestResponse.status})`);
      rawDataset = await dataResponse.text();
      dataset = JSON.parse(rawDataset);
      manifest = await manifestResponse.json();
      currentHash = await sha256Hex(rawDataset);
      const match = currentHash.toLowerCase() === String(manifest.sha256 || '').toLowerCase();
      integrity.dataset.state = match ? 'verified' : 'failed';
      integrity.textContent = match ? 'INTEGRITY VERIFIED' : 'INTEGRITY FAILURE';
      setText('hashShort', `${currentHash.slice(0, 16)}…${currentHash.slice(-8)}`);
      setText('schemaVersion', dataset.schema || 'unknown');
      setText('recordCount', String(dataset.records?.length || 0));
      setText('sessionId', sessionId.slice(0, 18));
      calculateFreshness();
      buildDomainOptions();
      buildSourceMatrix();
      renderMetrics();
      renderLedger();
      logEvent(match ? 'evidence-integrity-verified' : 'evidence-integrity-failed', currentHash);
    } catch (error) {
      integrity.dataset.state = 'failed';
      integrity.textContent = 'EVIDENCE LOAD FAILURE';
      $('#ledgerRows').innerHTML = `<div class="failure">Workbench could not load the local evidence ledger. Static article content remains available.<br><code>${esc(error.message)}</code></div>`;
      logEvent('evidence-load-failed', error.message);
    }
  }

  function calculateFreshness() {
    if (!dataset?.asOf) return;
    const asOf = new Date(`${dataset.asOf}T00:00:00Z`);
    const days = Math.max(0, Math.floor((Date.now() - asOf.getTime()) / 86400000));
    setText('freshness', days === 0 ? 'CURRENT' : `${days}D OLD`);
    const chip = $('#freshnessState');
    if (chip) chip.dataset.state = days <= 7 ? 'verified' : days <= 30 ? 'warning' : 'failed';
  }

  function sourceURLs(record) {
    return [record.source, ...(record.sources || [])].filter(Boolean);
  }

  function buildSourceMatrix() {
    const records = dataset?.records || [];
    const urls = records.flatMap(sourceURLs);
    const hosts = urls.map(u => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return 'invalid'; } });
    const official = records.filter(r => /official|intelligence|election-administration/.test(r.sourceType || '')).length;
    const cross = records.filter(r => sourceURLs(r).length > 1 || (r.corroborationCount || 0) > 1).length;
    const uniqueHosts = new Set(hosts).size;
    setText('sourceCount', String(urls.length));
    setText('officialCount', String(official));
    setText('crossSourceCount', String(cross));
    setText('hostCount', String(uniqueHosts));

    const hostCounts = hosts.reduce((acc, host) => ((acc[host] = (acc[host] || 0) + 1), acc), {});
    const list = $('#sourceHosts');
    if (list) {
      list.innerHTML = Object.entries(hostCounts)
        .sort((a,b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .map(([host, count]) => `<li><span>${esc(host)}</span><b>${count}</b></li>`).join('');
    }
  }

  function renderMetrics() {
    const records = dataset?.records || [];
    const verified = records.filter(r => r.status === 'verified');
    const collection = records.filter(r => r.status === 'collection-target');
    const avg = verified.length ? Math.round(verified.reduce((n, r) => n + Number(r.confidenceScore || 0), 0) / verified.length) : 0;
    setText('verifiedCount', String(verified.length));
    setText('collectionCount', String(collection.length));
    setText('confidenceAverage', `${avg}/100`);
  }

  function buildDomainOptions() {
    const select = $('#domainFilter');
    if (!select) return;
    const domains = [...new Set((dataset.records || []).map(r => r.domain))].sort();
    select.innerHTML = '<option value="all">All domains</option>' + domains.map(d => `<option value="${esc(d)}">${esc(d)}</option>`).join('');
  }

  function matches(record) {
    const statusOk = selectedStatus === 'all' || record.status === selectedStatus;
    const domainOk = selectedDomain === 'all' || record.domain === selectedDomain;
    const confidenceOk = selectedConfidence === 'all' || record.confidence === selectedConfidence;
    const hay = `${record.id} ${record.domain} ${record.claim} ${record.sourceType || ''} ${(record.requiredEvidence || []).join(' ')}`.toLowerCase();
    const queryOk = !query || hay.includes(query.toLowerCase());
    return statusOk && domainOk && confidenceOk && queryOk;
  }

  function renderLedger() {
    const root = $('#ledgerRows');
    if (!root || !dataset) return;
    const rows = dataset.records.filter(matches);
    setText('visibleCount', String(rows.length));
    if (!rows.length) {
      root.innerHTML = '<div class="empty">No records match the current analytical filters.</div>';
      return;
    }
    root.innerHTML = rows.map(record => {
      const urls = sourceURLs(record);
      const score = Number(record.confidenceScore || 0);
      const watched = watch.has(record.id);
      const sourceLinks = urls.length
        ? `<div class="sources-mini">${urls.map((u, i) => `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">Source ${i + 1}</a>`).join('')}</div>`
        : `<div class="requirements">Required: ${(record.requiredEvidence || []).map(esc).join(' · ')}</div>`;
      return `<article class="intel-row" id="claim-${esc(record.id)}" data-status="${esc(record.status)}">
        <div class="intel-topline">
          <div><span class="state ${record.status === 'verified' ? 'ok' : 'collect'}">${esc(record.status)}</span><code>${esc(record.id)}</code></div>
          <button class="watch ${watched ? 'on' : ''}" type="button" data-watch="${esc(record.id)}" aria-pressed="${watched}">${watched ? 'WATCHING' : 'WATCH'}</button>
        </div>
        <h3>${esc(record.claim)}</h3>
        <div class="intel-meta"><span>${esc(record.domain)}</span><span>${esc(record.sourceType || 'collection requirement')}</span><span>${esc(record.confidence)}</span></div>
        ${record.status === 'verified' ? `<div class="scoreline"><span>Editorial confidence</span><meter min="0" max="100" value="${score}">${score}</meter><b>${score}/100</b></div>` : '<div class="scoreline unassessed">Confidence intentionally unassessed until evidence is collected.</div>'}
        ${sourceLinks}
        ${record.notes ? `<p class="record-note">${esc(record.notes)}</p>` : ''}
        <div class="row-actions"><button type="button" data-copy="${esc(record.id)}">Copy claim citation</button><a href="#claim-${esc(record.id)}">Permalink</a></div>
      </article>`;
    }).join('');

    $$('[data-watch]', root).forEach(btn => btn.addEventListener('click', () => toggleWatch(btn.dataset.watch)));
    $$('[data-copy]', root).forEach(btn => btn.addEventListener('click', () => copyClaim(btn.dataset.copy)));
  }

  function toggleWatch(id) {
    if (watch.has(id)) watch.delete(id); else watch.add(id);
    localStorage.setItem(WATCH_KEY, JSON.stringify([...watch]));
    logEvent('watchlist-updated', id);
    renderLedger();
    setText('watchCount', String(watch.size));
  }

  async function copyClaim(id) {
    const record = dataset?.records.find(r => r.id === id);
    if (!record) return;
    const citation = `${record.id} — ${record.claim} [${record.status}; confidence ${record.confidence}; as of ${dataset.asOf}] ${location.origin}${location.pathname}#claim-${record.id}`;
    try {
      await navigator.clipboard.writeText(citation);
      toast('Claim citation copied');
      logEvent('claim-citation-copied', id);
    } catch { toast('Clipboard unavailable'); }
  }

  function toast(text) {
    const el = $('#toast');
    if (!el) return;
    el.textContent = text;
    el.classList.add('show');
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => el.classList.remove('show'), 1800);
  }

  function download(name, type, text) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([text], { type }));
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
  }

  function exportCSV() {
    if (!dataset) return;
    const fields = ['id','status','domain','claim','confidence','confidenceScore','sourceType'];
    const csv = [fields.join(',')].concat(dataset.records.map(r => fields.map(f => `"${String(r[f] ?? '').replace(/"/g, '""')}"`).join(','))).join('\n');
    download('ontario-influence-evidence-2026-08-07.csv', 'text/csv;charset=utf-8', csv);
    logEvent('evidence-export', 'csv');
  }

  function exportJSON() {
    if (!rawDataset) return;
    download('ontario-influence-evidence-2026-08-07.json', 'application/json', rawDataset);
    logEvent('evidence-export', 'json');
  }

  function exportSession() {
    const payload = {
      schema: 'clearglass-analyst-session-v1',
      classification: 'PUBLIC // OSINT',
      article: location.href.split('#')[0],
      generatedAt: new Date().toISOString(),
      sessionId,
      evidenceSha256: currentHash || null,
      manifestExpectedSha256: manifest?.sha256 || null,
      watchlist: [...watch],
      notes: $('#analystNotes')?.value || '',
      events: sessionEvents
    };
    download(`clearglass-analyst-session-${new Date().toISOString().slice(0,10)}.json`, 'application/json', JSON.stringify(payload, null, 2));
    logEvent('analyst-session-export', `${sessionEvents.length} events`);
  }

  function saveNotes() {
    const notes = $('#analystNotes')?.value || '';
    localStorage.setItem(NOTE_KEY, notes);
    setText('noteState', `Saved locally ${new Date().toISOString().slice(11,16)}Z`);
    logEvent('local-note-saved', `${notes.length} chars`);
    toast('Analyst note saved locally');
  }

  function clearNotes() {
    localStorage.removeItem(NOTE_KEY);
    if ($('#analystNotes')) $('#analystNotes').value = '';
    setText('noteState', 'No saved note');
    logEvent('local-note-cleared');
  }

  function bindControls() {
    setInterval(tickClock, 1000);
    tickClock();
    setText('sessionId', sessionId.slice(0, 18));
    setText('watchCount', String(watch.size));

    const savedFilter = readJSON(FILTER_KEY, {});
    selectedStatus = savedFilter.status || 'all';
    selectedConfidence = savedFilter.confidence || 'all';

    $$('[data-status-filter]').forEach(btn => {
      if (btn.dataset.statusFilter === selectedStatus) btn.classList.add('on');
      else btn.classList.remove('on');
      btn.addEventListener('click', () => {
        selectedStatus = btn.dataset.statusFilter;
        $$('[data-status-filter]').forEach(b => b.classList.toggle('on', b === btn));
        persistFilters(); renderLedger(); logEvent('status-filter', selectedStatus);
      });
    });

    $('#domainFilter')?.addEventListener('change', e => { selectedDomain = e.target.value; persistFilters(); renderLedger(); logEvent('domain-filter', selectedDomain); });
    $('#confidenceFilter')?.addEventListener('change', e => { selectedConfidence = e.target.value; persistFilters(); renderLedger(); logEvent('confidence-filter', selectedConfidence); });
    $('#claimSearch')?.addEventListener('input', e => { query = e.target.value.trim(); renderLedger(); });
    $('#exportJSON')?.addEventListener('click', exportJSON);
    $('#exportCSV')?.addEventListener('click', exportCSV);
    $('#exportSession')?.addEventListener('click', exportSession);
    $('#printBrief')?.addEventListener('click', () => { logEvent('print-brief'); print(); });
    $('#saveNotes')?.addEventListener('click', saveNotes);
    $('#clearNotes')?.addEventListener('click', clearNotes);
    if ($('#analystNotes')) $('#analystNotes').value = localStorage.getItem(NOTE_KEY) || '';
    setText('noteState', localStorage.getItem(NOTE_KEY) ? 'Recovered from this browser' : 'No saved note');

    document.addEventListener('keydown', e => {
      const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName || '');
      if (e.key === '/' && !typing) { e.preventDefault(); $('#claimSearch')?.focus(); }
      if (!typing && e.key.toLowerCase() === 'v') activateStatus('verified');
      if (!typing && e.key.toLowerCase() === 'c') activateStatus('collection-target');
      if (!typing && e.key.toLowerCase() === 'a') activateStatus('all');
    });

    document.addEventListener('visibilitychange', () => logEvent(document.hidden ? 'session-hidden' : 'session-visible'));
    logEvent('workbench-initialized', sessionId);
  }

  function activateStatus(status) {
    const btn = $(`[data-status-filter="${status}"]`);
    btn?.click();
  }

  function persistFilters() {
    localStorage.setItem(FILTER_KEY, JSON.stringify({ status: selectedStatus, domain: selectedDomain, confidence: selectedConfidence }));
  }

  bindControls();
  loadEvidence();
})();
