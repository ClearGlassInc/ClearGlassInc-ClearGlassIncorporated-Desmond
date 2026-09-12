/* ClearGlass Visual Engine · Simulation + centralized WorldState.
 *
 * ONE authoritative WorldState from which every scene derives. The causal
 * pipeline is:
 *   EVENT -> CLASSIFY -> STATE TRANSITION -> SIM UPDATE -> (SCENE UPDATE / RENDER)
 * A single event influences multiple layers (particles, graph, signals,
 * anomalies, entropy). Multi-scale synchronisation runs three cadences:
 *   MICRO  (every step)  particles, fields
 *   MESO   (~15 Hz)      graph, signals, provenance, ai
 *   MACRO  (~2 Hz)       systemState, stability classification
 *
 * DETERMINISTIC: no wall-clock or Math.random in this file. All time is the
 * `dt` argument; all randomness comes from the seeded Rng. Same seed + same
 * event sequence + same step count => bit-identical WorldState. */

import { Rng } from './rng.js';
import { EventQueue, PRIORITY } from './events.js';
import { computeEntropy, entropyToVisual } from './entropy.js';
import { TemporalChannel } from './temporal.js';
import { FieldStack } from './fields.js';
import { ParticlePool } from './particle-pool.js';
import { GraphPhysics } from './graph.js';
import { SignalSystem } from './signals.js';
import { ProvenancePipeline } from './provenance.js';
import { AnomalyField } from './anomaly.js';
import { AiPipeline } from './ai-pipeline.js';

const MESO_HZ = 15;
const MACRO_HZ = 2;

export class Simulation {
  constructor(seed = 1, opts = {}) {
    this.seed = seed;
    this.rng = new Rng(seed);
    this.opts = opts;

    this.queue = new EventQueue({ maxQueue: opts.maxQueue || 256 });
    this.fields = new FieldStack(this.rng);
    this.pool = new ParticlePool(opts.particleCapacity || 4000);
    this.graph = new GraphPhysics(this.rng);
    this.signals = new SignalSystem({ max: opts.maxSignals || 128 });
    this.provenance = new ProvenancePipeline();
    this.anomalies = new AnomalyField();
    this.ai = new AiPipeline();

    this.entropyChannel = new TemporalChannel(0.2, 90);
    this.activityChannel = new TemporalChannel(0.25, 90);

    this._mesoAcc = 0;
    this._macroAcc = 0;
    this._recentEvents = 0; // decays; feeds eventRate

    // Particle budget requested by the governor; defaults to a safe mid value.
    this.particleBudget = opts.particleBudget || 1500;

    this.world = {
      clock: 0, frame: 0,
      systemState: 'NOMINAL',
      stability: 1, entropy: 0, activity: 0,
      events: [], nodes: this.graph.nodes, edges: this.graph.edges,
      signals: this.signals.signals, provenance: this.provenance.items,
      anomalies: this.anomalies.items, aiJobs: this.ai.jobs,
      performance: { median: 0, p95: 0, tier: 'BALANCED' },
      renderBackend: 'unknown',
      visual: entropyToVisual(0),
      demo: true,
    };

    if (opts.seedTopology !== false) this._seedTopology();
  }

  /** Build a small deterministic graph with a few anchored (important) nodes. */
  _seedTopology() {
    const hubs = ['core', 'edge', 'intel'];
    hubs.forEach((id, i) => this.graph.addNode(id, {
      anchored: true, importance: 1,
      x: 0.5 + 0.25 * Math.cos((i / hubs.length) * Math.PI * 2),
      y: 0.5 + 0.25 * Math.sin((i / hubs.length) * Math.PI * 2),
    }));
    for (let i = 0; i < 9; i++) {
      const n = this.graph.addNode('n' + i, { importance: this.rng.range(0.2, 0.7) });
      this.graph.addEdge(n.id, hubs[i % hubs.length]);
    }
    this.graph.addEdge('core', 'edge');
    this.graph.addEdge('edge', 'intel');
    this.graph.addEdge('intel', 'core');
  }

  /** Public API: offer an (untrusted) event. Validated + queued. */
  emit(rawEvent) { return this.queue.offer(rawEvent); }

  /** Set the render particle budget (called by the governor). */
  setParticleBudget(n) { this.particleBudget = Math.max(50, n | 0); }
  setBackend(name) { this.world.renderBackend = name; }
  setPerformance(perf) { this.world.performance = perf; }

  /** Apply one classified event across multiple layers (causal fan-out). */
  _applyEvent(evt) {
    this._recentEvents += 1 + (evt.burst ? Math.min(evt.burst, 8) : 0);
    const r = this.rng;
    const amp = evt.amplitude;

    // Particles: a burst proportional to amplitude, capped by budget.
    const n = Math.round(amp * 40 * (evt.burst ? Math.min(evt.burst, 6) : 1));
    for (let i = 0; i < n && this.pool.activeCount < this.particleBudget; i++) {
      const ang = r.range(0, Math.PI * 2), spd = r.range(0.02, 0.2) * (0.5 + amp);
      this.pool.spawn(r.float(), r.float(), Math.cos(ang) * spd, Math.sin(ang) * spd,
        r.range(1, 3) * evt.duration, r.range(0.5, 2), amp);
    }

    switch (evt.type) {
      case 'signal':
      case 'telemetry':
        this.signals.emit({
          source: 'core', dest: 'edge',
          path: [{ x: r.range(0, 0.3), y: r.range(0, 1) }, { x: r.range(0.4, 0.6), y: r.range(0.3, 0.7) }, { x: r.range(0.7, 1), y: r.range(0, 1) }],
          velocity: 0.3 + amp, intensity: amp, priority: evt.priority,
          failProb: evt.priority <= PRIORITY.P1 ? 0.02 : 0.06,
        });
        break;
      case 'anomaly':
      case 'alert':
        this.anomalies.raise({ magnitude: Math.min(1, evt.magnitude / 100 + amp * 0.5), confidence: r.range(0.5, 0.95), x: r.float(), y: r.float(), priority: evt.priority, kind: (evt.magnitude | 0) });
        break;
      case 'provenance':
        this.provenance.admit({ label: evt.label, suspicious: evt.priority === PRIORITY.P0 });
        break;
      case 'pipeline':
        this.ai.submit({ label: evt.label });
        break;
      case 'node': {
        const id = 'ev' + (this.graph.nodes.length);
        if (this.graph.nodes.length < 40) {
          this.graph.addNode(id, { importance: amp });
          this.graph.addEdge(id, 'core');
        }
        break;
      }
      case 'edge':
        // Perturb the graph: nudge a random non-anchored node.
        for (const nd of this.graph.nodes) { if (!nd.anchored) { nd.vx += r.range(-0.2, 0.2); break; } }
        break;
    }
  }

  /** One deterministic simulation step over dt seconds. */
  step(dt = 1 / 60) {
    const d = dt > 0 ? dt : 1 / 60;
    this.world.clock += d;
    this.world.frame++;
    const t = this.world.clock;

    // ── EVENT stage ──────────────────────────────────────────────────────
    this.queue.beginTick();
    const drained = this.queue.drain(24); // bounded per-step drain
    this.world.events = drained;
    for (const evt of drained) this._applyEvent(evt);

    // Event-rate signal decays over time (per-second).
    this._recentEvents *= Math.pow(0.5, d / 1.5);

    // ── MICRO: fields + particles (every step) ───────────────────────────
    const vis = this.world.visual;
    this.fields.evolve(t, vis);
    this.pool.step(d, (i, out) => {
      const f = this.fields.sample(this.pool.x[i], this.pool.y[i], t);
      out.ax = f.fx * 0.4; out.ay = f.fy * 0.4;
      // wrap in unit square
      if (this.pool.x[i] < 0) this.pool.x[i] += 1; if (this.pool.x[i] > 1) this.pool.x[i] -= 1;
      if (this.pool.y[i] < 0) this.pool.y[i] += 1; if (this.pool.y[i] > 1) this.pool.y[i] -= 1;
    });

    // ── MESO: graph / signals / provenance / ai (~15 Hz) ─────────────────
    let graphActivity = this.world.activity;
    this._mesoAcc += d;
    const mesoDt = 1 / MESO_HZ;
    while (this._mesoAcc >= mesoDt) {
      this._mesoAcc -= mesoDt;
      graphActivity = this.graph.step(mesoDt);
      this.signals.step(mesoDt, this.rng);
      this.provenance.step(mesoDt);
      this.anomalies.step(mesoDt);
      this.ai.step(mesoDt, this.rng);
    }

    // ── activity + entropy ────────────────────────────────────────────────
    const signalDensity = this.signals.signals.length;
    const anomalyActivity = this.anomalies.items.reduce((s, a) => s + this.anomalies.response(a), 0);
    const eventRate = this._recentEvents;
    const activity = signalDensity * 0.5 + graphActivity * 8 + anomalyActivity * 4 + eventRate;
    this.activityChannel.push(activity, d);
    this.world.activity = this.activityChannel.value;

    const ent = computeEntropy({ signalDensity, graphActivity: graphActivity * 20, anomalyActivity, eventRate }, this.world.entropy, 0.12);
    this.world.entropy = ent.value;
    this.entropyChannel.push(ent.value, d);
    this.world.visual = entropyToVisual(ent.value);

    // ── MACRO: systemState + stability (~2 Hz) ───────────────────────────
    this._macroAcc += d;
    if (this._macroAcc >= 1 / MACRO_HZ) {
      this._macroAcc = 0;
      this.world.stability = this.entropyChannel.stability;
      const e = this.world.entropy, an = anomalyActivity;
      this.world.systemState = (e > 0.75 || an > 2.5) ? 'CRITICAL' : (e > 0.5 || an > 1) ? 'ELEVATED' : 'NOMINAL';
    }

    return this.world;
  }

  /** A cloneable snapshot of the salient scalar state (used by tests/replay). */
  snapshot() {
    return {
      clock: round(this.world.clock), frame: this.world.frame,
      systemState: this.world.systemState,
      entropy: round(this.world.entropy), activity: round(this.world.activity),
      stability: round(this.world.stability),
      particles: this.pool.activeCount, signals: this.signals.signals.length,
      provenance: this.provenance.items.length, anomalies: this.anomalies.items.length,
      aiJobs: this.ai.jobs.length, nodes: this.graph.nodes.length,
      visual: {
        density: round(this.world.visual.density), turbulence: round(this.world.visual.turbulence),
        frequency: round(this.world.visual.frequency), complexity: this.world.visual.complexity,
      },
    };
  }
}

function round(x) { return Math.round(x * 1e6) / 1e6; }
