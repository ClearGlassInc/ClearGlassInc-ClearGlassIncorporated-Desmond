/* ClearGlass Visual Engine · scenes + SceneManager.
 *
 * Every scene derives ONLY from the shared WorldState + Simulation — no scene
 * owns independent state, so scenes can never contradict each other. Scenes are
 * backend-agnostic: they call the common backend primitives (points/lines).
 *
 * Scene ids: FIELD, GRAPH, PROVENANCE, RADAR, NETWORK, TELEMETRY, ANOMALY,
 * AI_PIPELINE. FIELD and GRAPH are the fully-developed visuals; the others read
 * their WorldState slice and draw with the same primitives.
 *
 * A scene respects the `quality` budget (LOD, density) and `reduced` (no rapid
 * pulses / rotation when prefers-reduced-motion is active). */

const CRIMSON = { r: 0.918, g: 0.275, b: 0.282 };
const AMBER = { r: 1.0, g: 0.72, b: 0.28 };

/* Scratch buffers reused across frames (no per-frame allocation). */
const SCRATCH = { px: new Float32Array(6000), py: new Float32Array(6000), hot: new Float32Array(6000), seg: new Float32Array(12000) };

function scene(id, draw) {
  return {
    id, active: false, paused: false,
    activate() { this.active = true; this.paused = false; },
    deactivate() { this.active = false; },
    pause() { this.paused = true; },
    resume() { this.paused = false; },
    destroy() { this.active = false; },
    draw,
  };
}

/* FIELD — the particle field, density scaled by the entropy-derived budget. */
export const FieldScene = () => scene('FIELD', (backend, world, sim, q) => {
  const pool = sim.pool;
  const cap = pool.capacity;
  let n = 0;
  const stride = q.reduced ? 2 : 1;             // reduced-motion => sparser, calmer
  for (let i = 0; i < cap && n < SCRATCH.px.length; i += stride) {
    if (pool.state[i] !== 1) continue;
    SCRATCH.px[n] = pool.x[i]; SCRATCH.py[n] = pool.y[i]; SCRATCH.hot[n] = pool.hot[i];
    n++;
  }
  backend.points(SCRATCH.px, SCRATCH.py, SCRATCH.hot, n, { size: 1.4 + world.visual.density, r: CRIMSON.r, g: CRIMSON.g, b: CRIMSON.b });
});

/* GRAPH — intelligence graph: edges then nodes. Anchored (important) nodes hot. */
export const GraphScene = () => scene('GRAPH', (backend, world, sim, q) => {
  const g = sim.graph;
  let s = 0;
  for (const e of g.edges) {
    const a = g._byId(e.a), b = g._byId(e.b);
    if (!a || !b || s + 5 > SCRATCH.seg.length) continue;
    const hot = (a.anchored || b.anchored) ? 0.8 : 0.2;
    SCRATCH.seg[s++] = a.x; SCRATCH.seg[s++] = a.y; SCRATCH.seg[s++] = b.x; SCRATCH.seg[s++] = b.y; SCRATCH.seg[s++] = hot;
  }
  backend.lines(SCRATCH.seg.subarray(0, s), { a: 0.22, r: CRIMSON.r, g: CRIMSON.g, b: CRIMSON.b });
  let n = 0;
  for (const nd of g.nodes) { SCRATCH.px[n] = nd.x; SCRATCH.py[n] = nd.y; SCRATCH.hot[n] = nd.anchored ? 1 : 0.4; n++; }
  backend.points(SCRATCH.px, SCRATCH.py, SCRATCH.hot, n, { size: q.reduced ? 3 : 4, r: CRIMSON.r, g: CRIMSON.g, b: CRIMSON.b });
});

/* NETWORK / TELEMETRY — signals travelling their governed paths. */
export const NetworkScene = () => scene('NETWORK', (backend, world, sim) => {
  const sys = sim.signals; let n = 0, s = 0;
  for (const sig of sys.signals) {
    // faint path
    for (let k = 0; k < sig.path.length - 1 && s + 5 <= SCRATCH.seg.length; k++) {
      SCRATCH.seg[s++] = sig.path[k].x; SCRATCH.seg[s++] = sig.path[k].y;
      SCRATCH.seg[s++] = sig.path[k + 1].x; SCRATCH.seg[s++] = sig.path[k + 1].y; SCRATCH.seg[s++] = 0.1;
    }
    const p = sys.position(sig);
    SCRATCH.px[n] = p.x; SCRATCH.py[n] = p.y; SCRATCH.hot[n] = sig.state === 'QUARANTINED' ? 1 : sig.intensity; n++;
  }
  backend.lines(SCRATCH.seg.subarray(0, s), { a: 0.12, r: CRIMSON.r, g: CRIMSON.g, b: CRIMSON.b });
  backend.points(SCRATCH.px, SCRATCH.py, SCRATCH.hot, n, { size: 3, r: AMBER.r, g: AMBER.g, b: AMBER.b });
});

/* ANOMALY / RADAR — simulated anomalies as discs sized by proportional response.
   No radar sweep rotation under reduced motion. */
export const AnomalyScene = () => scene('ANOMALY', (backend, world, sim) => {
  const af = sim.anomalies; let n = 0;
  for (const a of af.items) {
    if (a.state === 'CLEARED') continue;
    SCRATCH.px[n] = a.x; SCRATCH.py[n] = a.y; SCRATCH.hot[n] = af.response(a); n++;
  }
  backend.points(SCRATCH.px, SCRATCH.py, SCRATCH.hot, n, { size: 6, r: AMBER.r, g: AMBER.g, b: AMBER.b });
});

/* PROVENANCE / AI_PIPELINE — staged progress columns (symbolic/DEMO). */
function columnScene(id, listFn, stageCountFn) {
  return scene(id, (backend, world, sim) => {
    const list = listFn(sim); let n = 0;
    list.forEach((it, row) => {
      const total = stageCountFn(it);
      const x = 0.1 + (it.stageIndex + it.progress) / total * 0.8;
      const y = 0.15 + (row % 8) * 0.1;
      SCRATCH.px[n] = Math.min(0.95, x); SCRATCH.py[n] = y;
      SCRATCH.hot[n] = it.state && (it.state === 'QUARANTINED') ? 1 : 0.6; n++;
    });
    backend.points(SCRATCH.px, SCRATCH.py, SCRATCH.hot, n, { size: 4, r: CRIMSON.r, g: CRIMSON.g, b: CRIMSON.b });
  });
}
export const ProvenanceScene = () => columnScene('PROVENANCE', (sim) => sim.provenance.items, () => 7);
export const RadarScene = () => scene('RADAR', AnomalyScene().draw);      // radar reads the anomaly field
export const TelemetryScene = () => scene('TELEMETRY', NetworkScene().draw);
export const AiPipelineScene = () => columnScene('AI_PIPELINE', (sim) => sim.ai.jobs, () => 8);

const REGISTRY = {
  FIELD: FieldScene, GRAPH: GraphScene, NETWORK: NetworkScene, TELEMETRY: TelemetryScene,
  ANOMALY: AnomalyScene, RADAR: RadarScene, PROVENANCE: ProvenanceScene, AI_PIPELINE: AiPipelineScene,
};

export class SceneManager {
  constructor() { this.scenes = new Map(); this.order = []; }
  register(id) {
    if (this.scenes.has(id)) return this.scenes.get(id);
    const factory = REGISTRY[id];
    if (!factory) return null;
    const sc = factory(); this.scenes.set(id, sc); this.order.push(id); return sc;
  }
  activate(id) { const s = this.scenes.get(id) || this.register(id); if (s) s.activate(); return s; }
  deactivate(id) { const s = this.scenes.get(id); if (s) s.deactivate(); }
  pauseAll() { this.scenes.forEach((s) => s.pause()); }
  resumeAll() { this.scenes.forEach((s) => s.resume()); }
  destroyAll() { this.scenes.forEach((s) => s.destroy()); this.scenes.clear(); this.order = []; }
  /** Draw every active, unpaused scene in registration order. */
  render(backend, world, sim, quality) {
    for (const id of this.order) {
      const s = this.scenes.get(id);
      if (s && s.active && !s.paused) { try { s.draw(backend, world, sim, quality); } catch (e) { /* one scene never kills the frame */ } }
    }
  }
  get activeIds() { return this.order.filter((id) => { const s = this.scenes.get(id); return s && s.active; }); }
}

export const SCENE_IDS = Object.keys(REGISTRY);
