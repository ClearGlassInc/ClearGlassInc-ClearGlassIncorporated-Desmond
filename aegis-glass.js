(() => {
  'use strict';

  const VERSION = '1.0.0';
  const STORAGE_KEY = 'clearglass:aegis:trace:v1';
  const SIGNAL_LIMIT = 64;
  const WINDOW_MS = 60_000;
  const ROTATE_MS = 15_000;
  const CLASSIFICATIONS = ['PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED', 'CROWN-JEWEL'];
  const STATES = ['LOW', 'GUARDED', 'HIGH', 'CRITICAL'];

  const now = () => Date.now();
  const clampClassification = (value) => {
    const normalized = String(value || 'PUBLIC').trim().toUpperCase();
    return CLASSIFICATIONS.includes(normalized) ? normalized : 'PUBLIC';
  };

  const randomToken = () => {
    const bytes = new Uint8Array(18);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
  };

  const getTraceToken = () => {
    try {
      const existing = sessionStorage.getItem(STORAGE_KEY);
      if (existing && /^[a-f0-9]{36}$/i.test(existing)) return existing;
      const token = randomToken();
      sessionStorage.setItem(STORAGE_KEY, token);
      return token;
    } catch {
      return randomToken();
    }
  };

  const configuredClassification = () => {
    const meta = document.querySelector('meta[name="aegis-classification"]');
    return clampClassification(
      document.documentElement.dataset.aegisClassification ||
      document.body?.dataset.aegisClassification ||
      meta?.content ||
      'PUBLIC'
    );
  };

  const classification = configuredClassification();
  const classificationRank = CLASSIFICATIONS.indexOf(classification);
  const explicitlyProtected =
    document.documentElement.dataset.aegisProtected === 'true' ||
    document.body?.dataset.aegisProtected === 'true';
  const protectedMode = explicitlyProtected || classificationRank >= CLASSIFICATIONS.indexOf('CONFIDENTIAL');
  const traceToken = getTraceToken();
  const traceFragment = traceToken.slice(0, 10).toUpperCase();
  const signals = [];
  let state = 'LOW';

  const isEditable = (target) => {
    if (!(target instanceof Element)) return false;
    return Boolean(target.closest('input, textarea, select, [contenteditable="true"], [data-aegis-copy-allowed="true"]'));
  };

  const scoreState = () => {
    const cutoff = now() - WINDOW_MS;
    const recent = signals.filter((signal) => signal.at >= cutoff);
    const weighted = recent.reduce((sum, signal) => sum + signal.weight, 0);
    if (weighted >= 24) return 'CRITICAL';
    if (weighted >= 12) return 'HIGH';
    if (weighted >= 5) return 'GUARDED';
    return 'LOW';
  };

  const setState = (nextState) => {
    if (!STATES.includes(nextState) || nextState === state) return;
    const previous = state;
    state = nextState;
    const root = document.getElementById('aegis-glass-root');
    if (root) {
      for (const candidate of STATES) root.classList.remove(`aegis-state-${candidate.toLowerCase()}`);
      root.classList.add(`aegis-state-${state.toLowerCase()}`);
    }
    updateStatus();
    window.dispatchEvent(new CustomEvent('aegis:risk-change', {
      detail: Object.freeze({ previous, state, classification, trace: traceFragment })
    }));
  };

  const recordSignal = (type, weight = 1, detail = {}) => {
    const signal = Object.freeze({
      type,
      weight,
      at: now(),
      detail: { ...detail }
    });
    signals.push(signal);
    if (signals.length > SIGNAL_LIMIT) signals.splice(0, signals.length - SIGNAL_LIMIT);
    window.dispatchEvent(new CustomEvent('aegis:signal', { detail: signal }));
    setState(scoreState());
  };

  const watermarkText = () => {
    const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19) + 'Z';
    return `CLEARGLASS • ${classification} • ${traceFragment} • ${timestamp}`;
  };

  const rotateWatermarks = () => {
    const root = document.getElementById('aegis-glass-root');
    if (!root || !protectedMode) return;
    const x = Math.floor(Math.random() * 41) - 20;
    const y = Math.floor(Math.random() * 41) - 20;
    root.style.setProperty('--aegis-shift-x', `${x}px`);
    root.style.setProperty('--aegis-shift-y', `${y}px`);
    root.querySelectorAll('.aegis-watermark').forEach((node) => {
      node.textContent = watermarkText();
    });
  };

  function updateStatus() {
    const node = document.getElementById('aegis-glass-status');
    if (!node) return;
    const mode = protectedMode ? 'PROTECTED' : 'MONITOR';
    node.textContent = `AEGIS GLASS · ${mode} · ${classification} · ${state}`;
    node.setAttribute(
      'aria-label',
      `Aegis Glass security layer. Mode ${mode}. Classification ${classification}. Risk state ${state}.`
    );
  }

  const mount = () => {
    if (!document.body || document.getElementById('aegis-glass-root')) return;

    if (protectedMode) document.body.classList.add('aegis-protected');

    const root = document.createElement('div');
    root.id = 'aegis-glass-root';
    root.className = 'aegis-state-low';
    root.dataset.aegisVersion = VERSION;

    const mesh = document.createElement('div');
    mesh.id = 'aegis-glass-mesh';
    mesh.setAttribute('aria-hidden', 'true');

    const watermarks = document.createElement('div');
    watermarks.id = 'aegis-glass-watermarks';
    watermarks.setAttribute('aria-hidden', 'true');
    for (let index = 0; index < 12; index += 1) {
      const item = document.createElement('span');
      item.className = 'aegis-watermark';
      item.textContent = watermarkText();
      watermarks.appendChild(item);
    }

    const status = document.createElement('div');
    status.id = 'aegis-glass-status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');

    const printNotice = document.createElement('div');
    printNotice.id = 'aegis-print-notice';
    printNotice.textContent = `Protected ClearGlass content. Printing is disabled for this classified view. Trace ${traceFragment}.`;

    let securityStack = document.getElementById('cg-security-stack');
    if (!securityStack) {
      securityStack = document.createElement('div');
      securityStack.id = 'cg-security-stack';
      securityStack.setAttribute('role', 'group');
      securityStack.setAttribute('aria-label', 'ClearGlass security controls');
    }

    root.append(mesh, watermarks, printNotice);
    document.body.appendChild(root);
    document.body.appendChild(securityStack);
    const stealthButton = document.getElementById('cg-stealth-btn');
    if (stealthButton) securityStack.appendChild(stealthButton);
    securityStack.appendChild(status);
    updateStatus();
    rotateWatermarks();

    if (protectedMode) {
      setInterval(rotateWatermarks, ROTATE_MS);
    }
  };

  const denyProtectedAction = (event, type, weight) => {
    if (!protectedMode || isEditable(event.target)) return false;
    event.preventDefault();
    recordSignal(type, weight, { tag: event.target?.tagName || null });
    return true;
  };

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) recordSignal('visibility-hidden', protectedMode ? 2 : 1);
  }, { passive: true });

  window.addEventListener('blur', () => recordSignal('window-blur', protectedMode ? 2 : 1), { passive: true });
  window.addEventListener('focus', () => recordSignal('window-focus', 0), { passive: true });

  document.addEventListener('copy', (event) => {
    if (denyProtectedAction(event, 'copy-blocked', 3)) return;
    if (event.target instanceof Element && event.target.closest('[data-aegis-protected="true"]')) {
      event.preventDefault();
      recordSignal('protected-copy-blocked', 3);
    }
  });

  document.addEventListener('contextmenu', (event) => {
    if (protectedMode && !isEditable(event.target)) {
      event.preventDefault();
      recordSignal('context-menu-blocked', 2);
    }
  });

  document.addEventListener('dragstart', (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (protectedMode && target.closest('img, video, canvas, [data-aegis-protected="true"]')) {
      event.preventDefault();
      recordSignal('drag-blocked', 2);
    }
  });

  document.addEventListener('keydown', (event) => {
    if (!protectedMode) return;
    const key = event.key.toLowerCase();
    const modifier = event.ctrlKey || event.metaKey;
    if (modifier && (key === 'p' || key === 's')) {
      event.preventDefault();
      recordSignal(key === 'p' ? 'print-shortcut-blocked' : 'save-shortcut-blocked', 4);
    }
  });

  window.addEventListener('beforeprint', () => {
    if (protectedMode) recordSignal('print-attempt', 4);
  });

  Object.defineProperty(window, 'AegisGlass', {
    configurable: false,
    enumerable: false,
    writable: false,
    value: Object.freeze({
      version: VERSION,
      classification,
      protectedMode,
      trace: traceFragment,
      getState: () => state,
      getSignals: () => signals.map((signal) => ({ ...signal, detail: { ...signal.detail } })),
      recordSignal: (type, weight = 1, detail = {}) => recordSignal(type, weight, detail)
    })
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount, { once: true });
  } else {
    mount();
  }
})();

(() => {
  'use strict';

  const COMMANDS = [
    { key: 'guardian', title: 'GUARDIAN', subtitle: 'FINANCIAL INTELLIGENCE', href: '/guardian.html', badge: 'ENCRYPTED', action: 'OPEN CONSOLE', accent: '#35d7ff', spark: [88, 91, 90, 94, 93, 96, 97] },
    { key: 'bluedesk', title: 'BLUEDESK', subtitle: 'CISO RISK & BLUE TEAM', href: '/bluedesk.html', badge: 'WATCH', action: 'INSPECT SYSTEM', accent: '#60a5fa', spark: [82, 84, 87, 86, 90, 92, 91] },
    { key: 'nexus', title: 'CLEARGLASS NEXUS V12', subtitle: 'COMMAND PLATFORM', href: '/ClearGlass-NEXUS-v12-FINAL.html', badge: 'SYNCED', action: 'OPEN CONSOLE', accent: '#a78bfa', spark: [90, 92, 93, 92, 95, 96, 98] },
    { key: 'clearpulse', title: 'CLEARPULSE', subtitle: 'SIGNAL INTELLIGENCE', href: '/intelligence.html', badge: 'NOMINAL', action: 'VIEW SIGNALS', accent: '#38bdf8', spark: [78, 83, 80, 88, 85, 91, 90] },
    { key: 'flowsint', title: 'FLOWSINT', subtitle: 'OSINT INVESTIGATION GRAPH', href: '/flowsint.html', badge: 'SYNCED', action: 'VIEW GRAPH', accent: '#22c55e', spark: [79, 84, 86, 89, 88, 93, 95] },
    { key: 'command', title: 'COMMAND CENTER', subtitle: 'LIVE OPERATIONS CONSOLE', href: '/systems.html', badge: 'ONLINE', action: 'OPEN CONSOLE', accent: '#69e7ff', spark: [86, 88, 92, 90, 94, 97, 96] },
    { key: 'conduit', title: 'CONDUIT', subtitle: 'WORKFLOW AUTOMATION', href: '/conduit.html', badge: 'SYNCED', action: 'INSPECT FLOWS', accent: '#34d399', spark: [80, 86, 84, 89, 92, 90, 94] },
    { key: 'air', title: 'AIR SYSTEMS CONTROL', subtitle: 'GLASS CONTROL SURFACE', href: '/control-surface.html', badge: 'NOMINAL', action: 'CALIBRATE SURFACE', accent: '#93c5fd', spark: [83, 85, 88, 87, 91, 92, 94] },
    { key: 'sats', title: 'SATS DIGITAL TWIN', subtitle: 'STORM-ADAPTIVE SIMULATION', href: '/sats-digital-twin.html', badge: 'WATCH', action: 'INSPECT MODEL', accent: '#8b5cf6', spark: [76, 80, 83, 82, 86, 88, 91] },
    { key: 'counter', title: 'COUNTER', subtitle: 'COMMERCIALIZATION SYSTEM', href: '/revenue-engine.html', badge: 'NOMINAL', action: 'OPEN SYSTEM', accent: '#f0abfc', spark: [81, 83, 87, 90, 89, 94, 95] }
  ];

  const TICKS = [
    '[ONLINE] SECURE_SOCKET_VERIFIED',
    '[SYNC] AGENT_MESH_HEALTHY',
    '[MONITOR] ZERO_CRITICAL_ALERTS',
    '[ROUTE] ENCRYPTED_CHANNEL_ESTABLISHED',
    '[POLICY] DEFENSIVE_RULESET_VALIDATED'
  ];

  const EVENTS = [
    '06:01:14 — HEARTBEAT ACKNOWLEDGED',
    '06:01:16 — POLICY MATRIX VALIDATED',
    '06:01:18 — SECURE RELAY SYNCHRONIZED'
  ];

  const norm = (value) => String(value || '').toUpperCase().replace(/[^A-Z0-9&]+/g, ' ').replace(/\s+/g, ' ').trim();
  const isReduced = () => window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const canHover = () => window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  const seedFor = (value) => {
    let seed = 2166136261;
    for (const char of String(value)) {
      seed ^= char.charCodeAt(0);
      seed = Math.imul(seed, 16777619);
    }
    return seed >>> 0;
  };

  const hex = (seed) => (seed >>> 0).toString(16).toUpperCase().padStart(8, '0').slice(0, 8);
  const telemetryFor = (command, offset = 0) => {
    const seed = seedFor(command.key);
    const latency = 14 + ((seed + offset) % 23);
    const integrity = (98.2 + (((seed >> 4) + offset) % 17) / 10).toFixed(1);
    const node = 96 + (((seed >> 8) + offset) % 4);
    return { latency, integrity, node, hash: hex(seed + offset * 9973) };
  };

  const sparkPath = (values) => values.map((value, index) => {
    const x = 4 + index * 15;
    const y = 30 - ((value - 70) / 30) * 24;
    return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${Math.max(4, Math.min(30, y)).toFixed(1)}`;
  }).join(' ');

  const escapeAttr = (value) => String(value).replace(/[&<>"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char]));

  let visibleCards = new WeakSet();
  let openCard = null;
  let pointerBound = false;

  const setDrawerState = (card, open) => {
    if (openCard && openCard !== card) setDrawerState(openCard, false);
    card.classList.toggle('is-cg-open', open);
    card.setAttribute('aria-expanded', open ? 'true' : 'false');
    const drawer = card.querySelector('.cg-command-drawer');
    if (drawer) drawer.setAttribute('aria-hidden', open ? 'false' : 'true');
    openCard = open ? card : null;
  };

  const actionTarget = (card, command) => {
    const linked = card.matches('a[href]') ? card.getAttribute('href') : card.querySelector('a[href]')?.getAttribute('href');
    return linked || command.href;
  };

  const bindPointerAmbient = () => {
    if (pointerBound || !canHover()) return;
    pointerBound = true;
    window.addEventListener('pointermove', (event) => {
      document.body.style.setProperty('--cg-command-pointer-x', `${event.clientX}px`);
      document.body.style.setProperty('--cg-command-pointer-y', `${event.clientY}px`);
    }, { passive: true });
  };

  const observeCard = (card) => {
    if (!('IntersectionObserver' in window)) {
      visibleCards.add(card);
      return;
    }
    if (!window.__cgCommandDirectoryObserver) {
      window.__cgCommandDirectoryObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) visibleCards.add(entry.target);
          else visibleCards.delete(entry.target);
        });
      }, { rootMargin: '80px 0px 120px' });
    }
    window.__cgCommandDirectoryObserver.observe(card);
  };

  const findIconWell = (card) => {
    const children = Array.from(card.children || []);
    return children.find((child) => {
      const rect = child.getBoundingClientRect();
      const text = norm(child.textContent);
      return rect.width >= 36 && rect.width <= 92 && rect.height >= 36 && rect.height <= 92 && text.length <= 12;
    });
  };

  const cardCandidates = (command) => {
    const title = norm(command.title);
    const subtitle = norm(command.subtitle);
    return Array.from(document.querySelectorAll('a, button, article, li, section, div'))
      .filter((node) => {
        if (!(node instanceof HTMLElement)) return false;
        if (node.closest('#aegis-glass-root, #cg-security-stack')) return false;
        if (node.dataset.cgCommandEnhanced === 'true') return false;
        const text = norm(node.textContent);
        return text.includes(title) && text.includes(subtitle) && text.length < 900;
      })
      .sort((a, b) => norm(a.textContent).length - norm(b.textContent).length);
  };

  const promoteRoot = (node) => {
    let root = node;
    while (root.parentElement && root.parentElement !== document.body) {
      const rect = root.getBoundingClientRect();
      const parentText = norm(root.parentElement.textContent);
      if (rect.width >= Math.min(280, window.innerWidth * 0.72) && rect.height >= 56 && rect.height <= 260) break;
      if (parentText.length > 1000) break;
      root = root.parentElement;
    }
    return root;
  };

  const findCommandCard = (command) => {
    for (const candidate of cardCandidates(command)) {
      const root = promoteRoot(candidate);
      if (!(root instanceof HTMLElement)) continue;
      if (root.closest('#aegis-glass-root, #cg-security-stack')) continue;
      if (root.dataset.cgCommandEnhanced === 'true') continue;
      return root;
    }
    return null;
  };

  const buildDrawer = (command, metrics) => {
    const drawer = document.createElement('div');
    drawer.className = 'cg-command-drawer';
    drawer.setAttribute('aria-hidden', 'true');
    drawer.innerHTML = `
      <div>
        <div class="cg-drawer-inner">
          <div class="cg-metric-grid" aria-label="${escapeAttr(command.title)} tactical metrics">
            <span class="cg-metric"><span>Latency</span><b data-cg-latency>${metrics.latency}ms</b></span>
            <span class="cg-metric"><span>Integrity</span><b data-cg-integrity>${metrics.integrity}%</b></span>
            <span class="cg-metric"><span>Node security</span><b data-cg-node>${metrics.node}%</b></span>
          </div>
          <svg class="cg-sparkline" viewBox="0 0 100 36" aria-hidden="true" focusable="false"><path d="${sparkPath(command.spark)}" /></svg>
          <ul class="cg-event-feed" aria-label="Defensive event feed">
            ${EVENTS.map((event) => `<li>${escapeAttr(event)}</li>`).join('')}
          </ul>
          <span class="cg-drawer-action" role="button" tabindex="0" data-cg-command-action="${escapeAttr(command.href)}">${escapeAttr(command.action)}</span>
        </div>
      </div>`;
    return drawer;
  };

  const paintTelemetry = (card, command) => {
    const tick = Math.floor(Date.now() / 5200);
    const metrics = telemetryFor(command, tick);
    const message = TICKS[(seedFor(command.key) + tick) % TICKS.length];
    const ticker = card.querySelector('[data-cg-ticker]');
    const metricLine = card.querySelector('[data-cg-metric-line]');
    const hashLine = card.querySelector('[data-cg-hash-line]');
    const latency = card.querySelector('[data-cg-latency]');
    const integrity = card.querySelector('[data-cg-integrity]');
    const node = card.querySelector('[data-cg-node]');
    if (ticker) ticker.textContent = message;
    if (metricLine) metricLine.textContent = `${metrics.latency}ms · ${metrics.integrity}%`;
    if (hashLine) hashLine.textContent = `#${metrics.hash.slice(0, 6)}`;
    if (latency) latency.textContent = `${metrics.latency}ms`;
    if (integrity) integrity.textContent = `${metrics.integrity}%`;
    if (node) node.textContent = `${metrics.node}%`;
  };

  const enhanceCard = (card, command) => {
    card.dataset.cgCommandEnhanced = 'true';
    card.dataset.cgCommandKey = command.key;
    card.classList.add('cg-command-card');
    card.style.setProperty('--cg-command-accent', command.accent);
    card.setAttribute('aria-expanded', 'false');
    if (!card.matches('a, button, [tabindex]')) {
      card.setAttribute('role', 'button');
      card.tabIndex = 0;
    }

    const iconWell = findIconWell(card);
    if (iconWell) iconWell.classList.add('cg-existing-icon-well');

    const metrics = telemetryFor(command);
    const cluster = document.createElement('span');
    cluster.className = 'cg-card-status-cluster';
    cluster.setAttribute('aria-hidden', 'true');
    cluster.innerHTML = `
      <span class="cg-status-topline"><span class="cg-live-dot"></span><span class="cg-status-badge">${escapeAttr(command.badge)}</span></span>
      <span class="cg-metric-line" data-cg-metric-line>${metrics.latency}ms · ${metrics.integrity}%</span>
      <span class="cg-hash-line" data-cg-hash-line>#${metrics.hash.slice(0, 6)}</span>`;

    const ticker = document.createElement('div');
    ticker.className = 'cg-telemetry-ticker';
    ticker.setAttribute('aria-label', `${command.title} telemetry status`);
    ticker.innerHTML = '<span data-cg-ticker>[ONLINE] SECURE_SOCKET_VERIFIED</span>';

    card.append(cluster, ticker, buildDrawer(command, metrics));
    paintTelemetry(card, command);
    observeCard(card);

    const toggle = (event) => {
      const action = event.target instanceof Element ? event.target.closest('[data-cg-command-action]') : null;
      if (action) {
        event.preventDefault();
        const href = action.getAttribute('data-cg-command-action') || actionTarget(card, command);
        if (href) window.location.href = href;
        return;
      }
      event.preventDefault();
      card.classList.add('cg-perimeter-flash');
      window.setTimeout(() => card.classList.remove('cg-perimeter-flash'), 460);
      setDrawerState(card, !card.classList.contains('is-cg-open'));
    };

    card.addEventListener('click', toggle);
    card.addEventListener('keydown', (event) => {
      const key = event.key;
      if (key !== 'Enter' && key !== ' ') return;
      toggle(event);
    });

    card.querySelectorAll('[data-cg-command-action]').forEach((action) => {
      action.addEventListener('keydown', (event) => {
        const key = event.key;
        if (key !== 'Enter' && key !== ' ') return;
        event.preventDefault();
        const href = action.getAttribute('data-cg-command-action') || actionTarget(card, command);
        if (href) window.location.href = href;
      });
    });

    if (!isReduced()) {
      const timer = window.setInterval(() => {
        if (visibleCards.has(card)) paintTelemetry(card, command);
      }, 5200);
      card.dataset.cgTelemetryTimer = String(timer);
    }
  };

  const enhanceDirectory = () => {
    if (!document.body) return;
    let count = 0;
    COMMANDS.forEach((command) => {
      const card = findCommandCard(command);
      if (!card) return;
      enhanceCard(card, command);
      count += 1;
    });
    if (count > 0) {
      document.body.classList.add('cg-command-directory-active');
      bindPointerAmbient();
    }
  };

  const ready = () => {
    enhanceDirectory();
    let scheduled = false;
    const observer = new MutationObserver(() => {
      if (scheduled) return;
      scheduled = true;
      window.setTimeout(() => {
        scheduled = false;
        enhanceDirectory();
      }, 160);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready, { once: true });
  else ready();
})();