/* ClearGlass Visual Engine · anomaly field (SIMULATION).
 * Anomaly objects carry magnitude/duration/confidence/classification/location/
 * priority/state. The visual response is PROPORTIONAL to magnitude*confidence,
 * and every anomaly is labelled SIMULATION — it never represents real telemetry
 * or a real threat. Bounded population. Pure math. */

export const ANOMALY_STATE = Object.freeze({
  DETECTED: 'DETECTED', ANALYZING: 'ANALYZING', CONTAINED: 'CONTAINED', CLEARED: 'CLEARED',
});

export class AnomalyField {
  constructor(opts = {}) {
    this.max = opts.max || 24;
    this.items = [];
    this.cleared = 0;
  }

  /** Raise a simulated anomaly. All values clamped to safe ranges. */
  raise(spec = {}) {
    if (this.items.length >= this.max) this.items.shift();
    const a = {
      label: 'SIMULATION',
      magnitude: Math.max(0, Math.min(1, spec.magnitude != null ? spec.magnitude : 0.5)),
      duration: Math.max(0.2, Math.min(20, spec.duration || 4)),
      elapsed: 0,
      confidence: Math.max(0, Math.min(1, spec.confidence != null ? spec.confidence : 0.6)),
      classification: ['drift', 'spike', 'outlier', 'pattern'][(spec.kind | 0) % 4] || 'drift',
      x: spec.x != null ? spec.x : 0.5,
      y: spec.y != null ? spec.y : 0.5,
      priority: spec.priority != null ? spec.priority : 1,
      state: ANOMALY_STATE.DETECTED,
      demo: true,
    };
    this.items.push(a);
    return a;
  }

  /** Response intensity is strictly proportional — no runaway amplification. */
  response(a) { return a.magnitude * a.confidence; }

  step(dt) {
    let activity = 0;
    for (const a of this.items) {
      if (a.state === ANOMALY_STATE.CLEARED) continue;
      a.elapsed += dt;
      const p = a.elapsed / a.duration;
      if (p > 0.2 && a.state === ANOMALY_STATE.DETECTED) a.state = ANOMALY_STATE.ANALYZING;
      if (p > 0.6 && a.state === ANOMALY_STATE.ANALYZING) a.state = ANOMALY_STATE.CONTAINED;
      if (p >= 1) { a.state = ANOMALY_STATE.CLEARED; this.cleared++; continue; }
      activity += this.response(a);
    }
    if (this.items.length > this.max * 0.75) {
      this.items = this.items.filter((a) => a.state !== ANOMALY_STATE.CLEARED);
    }
    return activity;
  }
}
