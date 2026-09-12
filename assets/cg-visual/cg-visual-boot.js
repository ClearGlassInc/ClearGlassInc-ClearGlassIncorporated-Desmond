/* ClearGlass Visual Engine · boot.
 *
 * Progressive enhancement entry point. Loaded as <script type="module"> (so it
 * is deferred and never blocks parsing or navigation). It self-initialises AFTER
 * content is in the DOM, feature-detects, and degrades silently to nothing on
 * unsupported browsers — the static site is fully functional without it.
 *
 * Config (all optional, additive):
 *   <body data-cg-visual="FIELD,GRAPH">   scene list; "off" disables
 *   ?cgvisual=off  or  localStorage['cg-visual-off']==='1'   kill switch
 *   ?cgdebug=1  or  localStorage['cg-visual-debug']==='1'    dev HUD + faults
 * Reduced motion integrates with the site's existing toggle:
 *   prefers-reduced-motion, OR localStorage['cgm-motion-preference']==='reduced'
 *   ('full' explicitly opts back in). */

import { VisualEngine } from './render/engine.js';

(function boot() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  if (window.__cgVisualBooted) return;
  window.__cgVisualBooted = true;

  function killed() {
    try {
      if (/[?&]cgvisual=off\b/.test(location.search)) return true;
      if (localStorage.getItem('cg-visual-off') === '1') return true;
    } catch (e) {}
    return false;
  }

  function reducedMotion() {
    try {
      const pref = localStorage.getItem('cgm-motion-preference');
      if (pref === 'reduced') return true;
      if (pref === 'full') return false;
    } catch (e) {}
    try { return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); }
    catch (e) { return false; }
  }

  function supported() {
    try {
      const c = document.createElement('canvas');
      return !!(c.getContext('webgl2') || c.getContext('2d'));
    } catch (e) { return false; }
  }

  function sceneConfig() {
    const raw = (document.body && document.body.getAttribute('data-cg-visual')) || 'FIELD,GRAPH';
    if (raw.trim().toLowerCase() === 'off') return null;
    const allowed = ['FIELD', 'GRAPH', 'NETWORK', 'TELEMETRY', 'ANOMALY', 'RADAR', 'PROVENANCE', 'AI_PIPELINE'];
    const list = raw.split(',').map((s) => s.trim().toUpperCase()).filter((s) => allowed.indexOf(s) !== -1);
    return list.length ? list : ['FIELD', 'GRAPH'];
  }

  function run() {
    if (killed() || !supported()) return;
    const scenes = sceneConfig();
    if (!scenes) return;

    // Layout-neutral decorative host, strictly beneath content.
    const stage = document.createElement('div');
    stage.className = 'cg-visual-stage';
    stage.setAttribute('aria-hidden', 'true');
    const atmos = document.querySelector('.cgm-atmos');
    if (atmos && atmos.parentNode) atmos.parentNode.insertBefore(stage, atmos.nextSibling);
    else document.body.insertBefore(stage, document.body.firstChild);

    const engine = new VisualEngine({
      host: stage,
      scenes,
      reduced: reducedMotion(),
      seed: 20260912,
    });
    engine.init().catch(() => { /* never surface engine errors to the page */ });
    window.__cgVisual = Object.assign(window.__cgVisual || {}, { engine });

    // React to a later reduced-motion change (e.g. the site's toggle button).
    try {
      const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
      const onChange = () => engine.setReducedMotion(reducedMotion());
      if (mq.addEventListener) mq.addEventListener('change', onChange);
    } catch (e) {}
  }

  // Initialise after content paints; requestIdleCallback keeps it non-blocking.
  function schedule() {
    if ('requestIdleCallback' in window) requestIdleCallback(run, { timeout: 1500 });
    else setTimeout(run, 200);
  }
  if (document.readyState === 'complete' || document.readyState === 'interactive') schedule();
  else window.addEventListener('DOMContentLoaded', schedule, { once: true });
})();
