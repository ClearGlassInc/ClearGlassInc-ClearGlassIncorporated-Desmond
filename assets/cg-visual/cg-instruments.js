/* ClearGlass Visual Engine · in-content instruments · boot.
 *
 * The background engine (cg-visual-boot.js) paints a decorative, aria-hidden
 * field behind the page. Instruments are its in-content counterpart: small,
 * labelled figures inside sections that explain one thing each — an evidence
 * chain, a sensor scope, the interface's own telemetry. Their markup is
 * readable static HTML; this module only adds motion on top.
 *
 *   <figure data-cg-instrument="chain|radar|telemetry"> … </figure>
 *
 * Loaded as <script type="module"> (deferred, never blocks parsing). Same kill
 * switch as the engine (?cgvisual=off, localStorage['cg-visual-off']==='1'),
 * same reduced-motion sources, and each instrument module is imported only if
 * the page has one. Any failure leaves the static markup exactly as written. */

import { InstrumentScheduler } from './instruments/scheduler.js';

const LOADERS = {
  chain: () => import('./instruments/chain.js'),
  radar: () => import('./instruments/radar.js'),
  telemetry: () => import('./instruments/telemetry.js'),
};

(function boot() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  if (window.__cgInstrumentsBooted) return;
  window.__cgInstrumentsBooted = true;

  function killed() {
    try {
      if (/[?&]cgvisual=off\b/.test(location.search)) return true;
      if (localStorage.getItem('cg-visual-off') === '1') return true;
    } catch (e) {}
    return false;
  }

  function run() {
    const hosts = Array.from(document.querySelectorAll('[data-cg-instrument]'));
    if (!hosts.length || killed()) return;
    const scheduler = new InstrumentScheduler();
    window.__cgVisual = Object.assign(window.__cgVisual || {}, { instruments: scheduler });
    for (const host of hosts) {
      const load = LOADERS[host.getAttribute('data-cg-instrument')];
      if (!load) continue;
      load()
        .then((m) => m.mount(host, scheduler))
        .catch(() => { /* static markup stays; never surface errors to the page */ });
    }
  }

  function schedule() {
    if ('requestIdleCallback' in window) requestIdleCallback(run, { timeout: 1500 });
    else setTimeout(run, 200);
  }
  if (document.readyState === 'complete' || document.readyState === 'interactive') schedule();
  else window.addEventListener('DOMContentLoaded', schedule, { once: true });
})();
