/* ClearGlass Visual Engine · ClearGlassGPUResourceGovernor.
 * Watches frame time / complexity / particle count / DPR / visibility and
 * controls the render budget (particle budget, sim frequency, resolution
 * scale, LOD, effect count) via discrete quality tiers.
 *
 * HYSTERESIS is the whole point: a tier change requires a sustained trend
 * (N consecutive breaches) plus a cooldown, so a single bad frame never causes
 * flapping. Frame health is judged on MEDIAN and P95, not the instantaneous FPS. */

export const TIERS = ['MINIMAL', 'LOW', 'BALANCED', 'HIGH', 'ULTRA'];

export const TIER_BUDGET = Object.freeze({
  ULTRA:    { particles: 4000, simHz: 60, resScale: 1.0,  lod: 3, effects: 5 },
  HIGH:     { particles: 2600, simHz: 60, resScale: 1.0,  lod: 3, effects: 4 },
  BALANCED: { particles: 1500, simHz: 45, resScale: 0.85, lod: 2, effects: 3 },
  LOW:      { particles: 700,  simHz: 30, resScale: 0.7,  lod: 1, effects: 2 },
  MINIMAL:  { particles: 250,  simHz: 20, resScale: 0.55, lod: 0, effects: 1 },
});

export class ResourceGovernor {
  constructor(opts = {}) {
    this.budgetMs = opts.budgetMs || 16.67;      // 60fps frame budget
    this.window = opts.window || 90;             // frames of history
    this.upThreshold = opts.upThreshold || 6;    // sustained good frames to raise
    this.downThreshold = opts.downThreshold || 8;// sustained bad frames to lower
    this.cooldownFrames = opts.cooldownFrames || 45;
    this.tierIndex = TIERS.indexOf(opts.startTier || 'BALANCED'); // default BALANCED
    this.frames = [];
    this._good = 0;
    this._bad = 0;
    this._cooldown = 0;
    this.dpr = 1;
    this.visible = true;
    this.changes = 0;
  }

  get tier() { return TIERS[this.tierIndex]; }
  get budget() {
    const b = TIER_BUDGET[this.tier];
    // Reduce work further when the tab is hidden.
    return this.visible ? b : { ...b, simHz: Math.min(b.simHz, 10), particles: Math.round(b.particles * 0.25) };
  }

  setDpr(dpr) { this.dpr = Math.max(0.5, Math.min(3, dpr || 1)); }
  setVisible(v) { this.visible = !!v; }

  /** Percentile of the frame-time window (0..1). */
  _percentile(p) {
    if (!this.frames.length) return 0;
    const s = [...this.frames].sort((a, b) => a - b);
    return s[Math.min(s.length - 1, Math.floor(p * s.length))];
  }
  get median() { return this._percentile(0.5); }
  get p95() { return this._percentile(0.95); }

  /** Record a frame time (ms) and possibly adjust the tier. */
  record(frameMs) {
    const ms = Number.isFinite(frameMs) && frameMs > 0 ? frameMs : this.budgetMs;
    this.frames.push(ms);
    if (this.frames.length > this.window) this.frames.shift();
    if (this._cooldown > 0) { this._cooldown--; return this.tier; }
    if (this.frames.length < 12) return this.tier; // need a sample first

    const med = this.median, p95 = this.p95;
    // Bad frame: median over budget, or P95 badly over (spikes).
    const bad = med > this.budgetMs * 1.1 || p95 > this.budgetMs * 1.6;
    // Good headroom: median comfortably under budget AND P95 tame.
    const good = med < this.budgetMs * 0.7 && p95 < this.budgetMs * 1.1;

    if (bad) { this._bad++; this._good = 0; }
    else if (good) { this._good++; this._bad = 0; }
    else { this._good = 0; this._bad = 0; }

    if (this._bad >= this.downThreshold && this.tierIndex > 0) {
      this.tierIndex--; this._bad = 0; this._cooldown = this.cooldownFrames; this.changes++;
    } else if (this._good >= this.upThreshold && this.tierIndex < TIERS.length - 1) {
      this.tierIndex++; this._good = 0; this._cooldown = this.cooldownFrames; this.changes++;
    }
    return this.tier;
  }

  snapshot() {
    return { tier: this.tier, budget: this.budget, median: this.median, p95: this.p95, dpr: this.dpr, visible: this.visible, changes: this.changes };
  }
}
