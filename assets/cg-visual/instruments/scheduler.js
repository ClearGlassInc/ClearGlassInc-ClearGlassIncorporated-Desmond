/* ClearGlass Visual Engine · instrument scheduler (browser).
 *
 * One requestAnimationFrame loop for every in-content instrument on the page.
 * It runs only while at least one instrument is on screen and the tab is
 * visible, and it is frame-capped by policy (core/cadence.js).
 *
 * It owns no second performance model and no second event bus:
 *   - quality follows the engine's ResourceGovernor tier when the background
 *     engine is running (window.__cgVisual.engine);
 *   - signals are handed to the engine's own zero-trust intake
 *     (engine.sim.emit -> core/events.js validate/classify/queue), so one
 *     in-content event also moves the background field.
 *
 * Reduced motion follows the same sources as the rest of the site: the OS
 * setting, and the site's own "Reduce visual effects" control, which writes
 * html[data-cgm-motion] and localStorage['cgm-motion-preference']. A change to
 * either takes effect immediately, without a reload. */

import { instrumentPolicy } from '../core/cadence.js';

const POLICY_REFRESH_MS = 2000; // MACRO cadence, same order as the engine's
const EMITTABLE = new Set(['signal', 'provenance', 'telemetry']); // never alert/anomaly

export class InstrumentScheduler {
  constructor() {
    this.instruments = [];
    this.onScreen = new Set();
    this.signalsTraced = 0;
    this._listeners = new Set();
    this._raf = 0;
    this._last = 0;
    this._policyAt = 0;
    this._docVisible = document.visibilityState !== 'hidden';
    this._disposed = false;

    const mm = (q) => (window.matchMedia ? window.matchMedia(q) : null);
    this._mqReduce = mm('(prefers-reduced-motion: reduce)');
    this._mqNarrow = mm('(max-width: 720px)');
    this.policy = this._computePolicy();

    this._io = 'IntersectionObserver' in window
      ? new IntersectionObserver((entries) => {
          for (const e of entries) {
            const inst = this.instruments.find((i) => i.host === e.target);
            if (!inst) continue;
            if (e.isIntersecting) this.onScreen.add(inst); else this.onScreen.delete(inst);
          }
          this._wake();
        }, { rootMargin: '120px 0px' })
      : null;

    this._onVisibility = () => { this._docVisible = document.visibilityState !== 'hidden'; this._wake(); };
    document.addEventListener('visibilitychange', this._onVisibility);

    const refresh = () => this._refreshPolicy(true);
    for (const q of [this._mqReduce, this._mqNarrow]) {
      if (q && q.addEventListener) q.addEventListener('change', refresh);
    }
    // The site's motion control flips html[data-cgm-motion]; follow it live.
    this._mo = 'MutationObserver' in window ? new MutationObserver(refresh) : null;
    if (this._mo) this._mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-cgm-motion'] });

    this._onPageHide = (ev) => { if (!ev.persisted) this.dispose(); };
    window.addEventListener('pagehide', this._onPageHide);
  }

  engine() {
    const v = window.__cgVisual;
    return v && v.engine && !v.engine._disposed ? v.engine : null;
  }

  tier() {
    const e = this.engine();
    return e && e.governor ? e.governor.tier : null;
  }

  reduced() {
    const attr = document.documentElement.getAttribute('data-cgm-motion');
    if (attr === 'reduced') return true;
    if (attr === 'full') return false;
    try {
      const pref = localStorage.getItem('cgm-motion-preference');
      if (pref === 'reduced') return true;
      if (pref === 'full') return false;
    } catch (e) { /* storage blocked: fall through to the OS setting */ }
    return !!(this._mqReduce && this._mqReduce.matches);
  }

  _computePolicy() {
    const conn = navigator.connection;
    return instrumentPolicy({
      reduced: this.reduced(),
      tier: this.tier(),
      saveData: !!(conn && conn.saveData),
      narrow: !!(this._mqNarrow && this._mqNarrow.matches),
    });
  }

  /* `fromFrame`: called inside _frame, which re-arms its own rAF. Waking from
     there would start a second loop, so only out-of-frame callers wake. */
  _refreshPolicy(force, fromFrame = false) {
    const next = this._computePolicy();
    const changed = next.mode !== this.policy.mode || next.fps !== this.policy.fps;
    this.policy = next;
    if (changed || force) {
      for (const inst of this.instruments) inst.setMode(next.mode, next);
      this._notify();
    }
    if (!fromFrame) this._wake();
  }

  /** Register a mounted instrument: { host, frame(now), setMode(mode, policy) }. */
  add(inst) {
    this.instruments.push(inst);
    inst.setMode(this.policy.mode, this.policy);
    if (this._io) this._io.observe(inst.host); else this.onScreen.add(inst);
    this._wake();
  }

  /** Hand a visual event to the background engine's validated intake. */
  emit(event) {
    if (!event || !EMITTABLE.has(event.type)) return;
    if (event.type === 'signal') this.signalsTraced += 1;
    const e = this.engine();
    if (e && e.sim && typeof e.sim.emit === 'function') {
      try { e.sim.emit({ type: event.type, label: String(event.label || event.type).slice(0, 64), magnitude: 1 }); }
      catch (err) { /* the engine validates and may refuse; never surface it */ }
    }
    this._notify();
  }

  subscribe(fn) { this._listeners.add(fn); return () => this._listeners.delete(fn); }
  _notify() { for (const fn of this._listeners) { try { fn(this); } catch (e) { /* isolate */ } } }

  _shouldRun() {
    return !this._disposed && this._docVisible && this.onScreen.size > 0 && this.policy.fps > 0;
  }

  _wake() {
    if (this._raf || !this._shouldRun()) return;
    this._last = 0;
    this._raf = requestAnimationFrame((t) => this._frame(t));
  }

  _frame(now) {
    this._raf = 0;
    if (!this._shouldRun()) return;
    // The governor tier can move while the page is open; re-read it on the
    // MACRO cadence instead of every frame.
    if (now - this._policyAt > POLICY_REFRESH_MS) {
      this._policyAt = now;
      this._refreshPolicy(false, true);
      if (!this._shouldRun()) return;
    }
    const minFrame = 1000 / this.policy.fps;
    if (!this._last || now - this._last >= minFrame - 1) {
      this._last = now;
      for (const inst of this.onScreen) {
        try { inst.frame(now); } catch (e) { /* one faulty instrument never stops the rest */ }
      }
    }
    this._raf = requestAnimationFrame((t) => this._frame(t));
  }

  dispose() {
    this._disposed = true;
    if (this._raf) cancelAnimationFrame(this._raf);
    this._raf = 0;
    if (this._io) this._io.disconnect();
    if (this._mo) this._mo.disconnect();
    document.removeEventListener('visibilitychange', this._onVisibility);
    window.removeEventListener('pagehide', this._onPageHide);
    for (const inst of this.instruments) { if (inst.dispose) inst.dispose(); }
    this._listeners.clear();
  }
}
