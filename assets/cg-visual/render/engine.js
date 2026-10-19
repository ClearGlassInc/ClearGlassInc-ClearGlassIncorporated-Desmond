/* ClearGlass Visual Engine · orchestrator.
 *
 * Wires the centralized Simulation (WorldState) to a feature-detected render
 * backend and a SceneManager, governed by the ResourceGovernor. Separates the
 * SIMULATION pipeline (fixed-timestep, governed frequency) from the RENDER
 * pipeline (one draw per rAF). Non-blocking, content-first: the canvas is a
 * decorative layer (pointer-events:none) that never alters layout.
 *
 * Resilience: pauses when hidden/offscreen; recovers from GPU context loss by
 * preserving WorldState and re-initialising the backend; honours reduced-motion
 * with a genuine static profile. */

import { Simulation } from '../core/simulation.js';
import { ResourceGovernor } from '../core/governor.js';
import { importanceToLod } from '../core/importance.js';
import { selectBackend, detectBackends } from './backend.js';
import { SceneManager } from './scenes.js';
import { Hud, hudEnabled } from './hud.js';
import { parseFaults, createFaultController } from './failure-injection.js';

export class VisualEngine {
  constructor(opts = {}) {
    this.opts = opts;
    this.host = opts.host || (typeof document !== 'undefined' ? document.body : null);
    this.seed = opts.seed || 20260912;
    this.sim = new Simulation(this.seed, { particleCapacity: opts.particleCapacity || 4000 });
    this.governor = new ResourceGovernor({ startTier: opts.startTier || 'BALANCED' });
    this.scenes = new SceneManager();
    (opts.scenes || ['FIELD', 'GRAPH']).forEach((id) => this.scenes.activate(id));

    this.backend = null;
    this.canvas = null;
    this.running = false;
    this.reduced = !!opts.reduced;
    this.visible = true;
    this._raf = 0;
    this._last = 0;
    this._simAcc = 0;
    this._frameTimes = [];
    this._faults = parseFaults();
    this._hud = null;
    this._simMs = 0;
    this._recovering = false;
    this._disposed = false;
    this._backendSelectionId = 0;
    this._pagehideHandler = null;
    this._pageshowHandler = null;
    this._contextLostHandler = null;
    this._contextRestoredHandler = null;
  }

  /** Async init: create the decorative canvas, pick a backend, start. */
  async init() {
    if (typeof document === 'undefined' || !this.host || this._disposed || this.canvas) return this;
    const canvas = document.createElement('canvas');
    canvas.className = 'cg-visual-canvas';
    canvas.setAttribute('aria-hidden', 'true');
    canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;display:block;';
    // Host must be a positioned decorative container; never affects flow.
    this.host.appendChild(canvas);
    this.canvas = canvas;

    // Context-loss handling (WebGL). Preserve WorldState, rebuild the backend.
    this._contextLostHandler = (event) => { event.preventDefault(); this._onContextLost(); };
    this._contextRestoredHandler = () => {
      this.reinitBackend().then(() => {
        if (this._disposed || !this.backend) return;
        if (this.reduced) this._renderStaticProfile();
        else if (this.visible) this.start();
      }).catch((error) => this._reportError('Backend restoration failed', error));
    };
    canvas.addEventListener('webglcontextlost', this._contextLostHandler, false);
    canvas.addEventListener('webglcontextrestored', this._contextRestoredHandler, false);

    // Attach lifecycle listeners before asynchronous backend selection. A fast
    // navigation must not strand a canvas while init() is still awaiting GPU setup.
    this._pagehideHandler = (event) => {
      if (event.persisted) this.setVisible(false);
      else this.dispose();
    };
    this._pageshowHandler = (event) => {
      if (event.persisted && !this._disposed) this.setVisible(!document.hidden);
    };
    this._visHandler = () => this.setVisible(!document.hidden);
    window.addEventListener('pagehide', this._pagehideHandler);
    window.addEventListener('pageshow', this._pageshowHandler);
    document.addEventListener('visibilitychange', this._visHandler);
    this.visible = !document.hidden;
    this.governor.setVisible(this.visible);

    if (this._faults.has('disableWebGPU')) this.opts.allowWebGPU = false;
    if (this._faults.has('disableWebGL') || this._faults.has('forceCanvas')) this.opts.forced = 'canvas2d';
    if (this._faults.has('reducedMotion')) this.reduced = true;

    await this.reinitBackend();
    if (this._disposed || !this.canvas) return this;

    // Offscreen pause.
    if (typeof IntersectionObserver !== 'undefined') {
      this._io = new IntersectionObserver((es) => { this.setVisible(es[0].isIntersecting); }, { threshold: 0.01 });
      this._io.observe(this.host);
    }
    if (hudEnabled()) { this._hud = new Hud(); }

    // Expose a dev handle (faults + engine) when debugging.
    if (hudEnabled() || this._faults.size) {
      window.__cgVisual = window.__cgVisual || {};
      window.__cgVisual.engine = this;
      window.__cgVisual.faults = createFaultController(this);
      window.__cgVisual.detected = detectBackends();
    }

    if (this.reduced) this._renderStaticProfile();
    else if (this.visible) this.start();
    return this;
  }

  /** (Re)select the backend, preserving WorldState. Resizes to host box. */
  async reinitBackend() {
    const canvas = this.canvas;
    if (!canvas || this._disposed) return;
    const selectionId = ++this._backendSelectionId;
    const previous = this.backend;
    this.backend = null;
    if (previous) this._cleanup('Previous renderer backend disposal failed', () => previous.dispose());

    const backend = await selectBackend(canvas, { forced: this.opts.forced, allowWebGPU: this.opts.allowWebGPU });
    if (this._disposed || this.canvas !== canvas || selectionId !== this._backendSelectionId) {
      this._cleanup('Stale renderer backend disposal failed', () => backend.dispose());
      return;
    }
    this.backend = backend;
    this.sim.setBackend(backend.kind);
    this._resize();
    // In reduced-motion, repaint the static frame after a backend swap.
    if (this.reduced && !this.running) this._renderStaticProfile();
  }

  _resize() {
    if (!this.backend || !this.host) return;
    const dpr = Math.min(3, (typeof devicePixelRatio !== 'undefined' ? devicePixelRatio : 1) || 1);
    const r = this.host.getBoundingClientRect();
    const w = Math.max(1, Math.round(r.width)), h = Math.max(1, Math.round(r.height));
    if (w === this._w && h === this._h && dpr === this._dpr) return;  // resize only on change
    this._w = w; this._h = h; this._dpr = dpr;
    this.governor.setDpr(dpr);
    this.backend.resize(w, h, dpr * this.governor.budget.resScale);
  }

  _quality() {
    const b = this.governor.budget;
    const lod = importanceToLod(0.5) && b.lod; // baseline lod from budget
    return { tier: this.governor.tier, lod: b.lod, effects: b.effects, reduced: this.reduced, density: this.sim.world.visual.density };
  }

  start() {
    if (this.running || this.reduced || this._disposed || !this.visible || !this.backend) return;
    this.running = true; this._last = 0;
    const loop = (now) => {
      if (!this.running) return;
      this._raf = requestAnimationFrame(loop);
      if (!this._last) { this._last = now; return; }
      let frameMs = now - this._last; this._last = now;
      if (this._faults.has('forceLowFps')) frameMs = Math.max(frameMs, 45); // simulate a slow device
      this._tick(frameMs);
    };
    this._raf = requestAnimationFrame(loop);
    if (typeof ResizeObserver !== 'undefined' && !this._ro) { this._ro = new ResizeObserver(() => this._resize()); this._ro.observe(this.host); }
  }

  stop() { this.running = false; if (this._raf) cancelAnimationFrame(this._raf); this._raf = 0; }

  /** One rendered frame: governed fixed-timestep sim, then draw. */
  _tick(frameMs) {
    if (this._disposed || !this.backend) { this.stop(); return; }
    this._frameTimes.push(frameMs); if (this._frameTimes.length > 120) this._frameTimes.shift();
    this.governor.record(frameMs);
    const budget = this.governor.budget;
    this.sim.setParticleBudget(budget.particles);

    // Dev fault: flood the pipeline to prove backpressure holds.
    if (this._faults.has('floodEvents')) {
      for (let k = 0; k < 300; k++) this.sim.emit({ type: 'signal', source: 'flood' + (k % 40), magnitude: 3 });
    }

    // SIMULATION pipeline — fixed timestep at the governed frequency.
    const simDt = 1 / budget.simHz;
    this._simAcc += Math.min(0.1, frameMs / 1000);   // clamp huge gaps (tab wake)
    const t0 = now();
    let steps = 0;
    while (this._simAcc >= simDt && steps < 6) { this.sim.step(simDt); this._simAcc -= simDt; steps++; }
    this._simMs = now() - t0;

    // RENDER pipeline.
    this.sim.setPerformance({ median: this.governor.median, p95: this.governor.p95, tier: this.governor.tier });
    this._resize();
    try {
      this.backend.begin();
      this.scenes.render(this.backend, this.sim.world, this.sim, this._quality());
      this.backend.end();
    } catch (error) {
      // Stop the repeating loop on a persistent backend fault and expose evidence
      // in the console rather than retrying a broken renderer every frame.
      this.stop();
      this._reportError('Frame rendering failed; animation paused', error);
    }

    if (this._hud && this.backend) this._updateHud(frameMs);
  }

  /** Reduced-motion: build a settled state deterministically, paint once, stop. */
  _renderStaticProfile() {
    if (!this.backend || this._disposed) return;
    for (let i = 0; i < 90; i++) this.sim.step(1 / 60);
    this._resize();
    try {
      this.backend.begin();
      this.scenes.render(this.backend, this.sim.world, this.sim, { ...this._quality(), reduced: true });
      this.backend.end();
    } catch (error) {
      this._reportError('Static reduced-motion render failed', error);
    }
  }

  _onContextLost() {
    if (this._recovering || this._disposed) return;
    this._recovering = true;
    this.stop();
    // WorldState (this.sim) is preserved; only GPU resources are invalid.
    const previous = this.backend;
    this.backend = null;
    if (previous) this._cleanup('Context-lost renderer disposal failed', () => previous.dispose());
    // Re-init on the next microtask so the browser finishes the loss event.
    Promise.resolve().then(async () => {
      try {
        await this.reinitBackend();
      } catch (error) {
        this._reportError('GPU context recovery failed', error);
      } finally {
        this._recovering = false;
      }
      if (!this.reduced && !this._disposed && this.visible && this.backend) this.start();
    });
  }

  /** Dev/test hook: force a context-loss + recovery cycle. Returns a promise. */
  async simulateContextLoss() {
    if (this.backend && this.backend.gl) {
      const lose = this.backend.gl.getExtension('WEBGL_lose_context');
      if (lose) { lose.loseContext(); await new Promise((r) => setTimeout(r, 30)); }
    }
    this._onContextLost();
    return new Promise((resolve) => {
      const check = () => (this._recovering ? setTimeout(check, 20) : resolve(this.backend && this.backend.kind));
      setTimeout(check, 40);
    });
  }

  setReducedMotion(on) {
    if (this._disposed) return;
    this.reduced = !!on;
    if (this.reduced) { this.stop(); this._renderStaticProfile(); }
    else this.start();
  }

  setVisible(v) {
    if (this._disposed) return;
    this.visible = !!v;
    this.governor.setVisible(this.visible);
    if (this.reduced) return;
    if (this.visible) this.start(); else this.stop();
  }

  _updateHud(frameMs) {
    const w = this.sim.world, b = this.governor.budget;
    this._hud.update({
      backend: this.backend.kind, quality: this.governor.tier, dpr: (this._dpr || 1).toFixed(2),
      fps: frameMs > 0 ? 1000 / frameMs : 0, frameMs, p95: this.governor.p95,
      simMs: this._simMs, systemState: w.systemState, entropy: w.entropy,
      particles: this.sim.pool.activeCount, poolCap: this.sim.pool.capacity, load: this.sim.pool.load,
      spawnFailures: this.sim.pool.spawnFailures,
      nodes: this.sim.graph.nodes.length, edges: this.sim.graph.edges.length,
      signals: this.sim.signals.signals.length, queue: this.sim.queue.size,
      lod: b.lod, scenes: this.scenes.activeIds.join(','),
    });
  }

  dispose() {
    if (this._disposed) return;
    this._disposed = true;
    this._backendSelectionId++;
    this.stop();

    if (this._io) this._cleanup('IntersectionObserver cleanup failed', () => this._io.disconnect());
    if (this._ro) this._cleanup('ResizeObserver cleanup failed', () => this._ro.disconnect());
    if (this._visHandler && typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', this._visHandler);
    }
    if (this._pagehideHandler && typeof window !== 'undefined') {
      window.removeEventListener('pagehide', this._pagehideHandler);
    }
    if (this._pageshowHandler && typeof window !== 'undefined') {
      window.removeEventListener('pageshow', this._pageshowHandler);
    }

    const canvas = this.canvas;
    if (canvas && this._contextLostHandler) {
      canvas.removeEventListener('webglcontextlost', this._contextLostHandler);
    }
    if (canvas && this._contextRestoredHandler) {
      canvas.removeEventListener('webglcontextrestored', this._contextRestoredHandler);
    }

    const backend = this.backend;
    this.backend = null;
    if (backend) this._cleanup('Renderer backend disposal failed', () => backend.dispose());
    if (this._hud) this._cleanup('HUD disposal failed', () => this._hud.dispose());
    this._cleanup('Scene cleanup failed', () => this.scenes.destroyAll());

    this.canvas = null;
    if (canvas && typeof canvas.remove === 'function') {
      canvas.width = canvas.height = 0;
      canvas.remove();
    }
  }

  _reportError(phase, error) {
    if (typeof console !== 'undefined' && typeof console.error === 'function') {
      console.error('[ClearGlass Visual Engine] ' + phase, error);
    }
  }

  _cleanup(phase, action) {
    try {
      action();
    } catch (error) {
      this._reportError(phase, error);
    }
  }
}

function now() {
  return (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
}
