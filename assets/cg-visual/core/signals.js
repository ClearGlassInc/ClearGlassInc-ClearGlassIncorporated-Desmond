/* ClearGlass Visual Engine · signal physics.
 * A signal is a governed packet travelling a path between nodes. State machine:
 *   SOURCE -> PROPAGATE -> TRANSIT -> RECEIVE -> COMPLETE
 * A failed signal short-circuits to QUARANTINED. Fields: source/dest/path/
 * velocity/intensity/latency/priority/state. Bounded population. Pure math. */

export const SIGNAL_STATE = Object.freeze({
  SOURCE: 'SOURCE', PROPAGATE: 'PROPAGATE', TRANSIT: 'TRANSIT',
  RECEIVE: 'RECEIVE', COMPLETE: 'COMPLETE', QUARANTINED: 'QUARANTINED',
});

export class SignalSystem {
  constructor(opts = {}) {
    this.max = opts.max || 128;         // hard limit
    this.signals = [];
    this.completed = 0;
    this.quarantined = 0;
  }

  /** Emit a signal along a path of {x,y} points. Returns it or null if full. */
  emit(spec) {
    if (this.signals.length >= this.max) return null;
    const s = {
      source: spec.source, dest: spec.dest,
      path: spec.path && spec.path.length >= 2 ? spec.path : [{ x: 0, y: 0 }, { x: 1, y: 1 }],
      t: 0,                                  // param along path [0,1]
      velocity: Math.max(0.05, Math.min(2, spec.velocity || 0.5)),
      intensity: Math.max(0, Math.min(1, spec.intensity != null ? spec.intensity : 0.7)),
      latency: 0,
      priority: spec.priority != null ? spec.priority : 2,
      state: SIGNAL_STATE.SOURCE,
      failProb: Math.max(0, Math.min(1, spec.failProb || 0)),
    };
    this.signals.push(s);
    return s;
  }

  /** Advance all signals. `rng` used only for the failure roll (deterministic). */
  step(dt, rng) {
    let active = 0;
    for (const s of this.signals) {
      if (s.state === SIGNAL_STATE.COMPLETE || s.state === SIGNAL_STATE.QUARANTINED) continue;
      active++;
      s.latency += dt;
      // Advance state machine by progress.
      if (s.state === SIGNAL_STATE.SOURCE) s.state = SIGNAL_STATE.PROPAGATE;
      else if (s.state === SIGNAL_STATE.PROPAGATE && s.t > 0.05) s.state = SIGNAL_STATE.TRANSIT;
      else if (s.state === SIGNAL_STATE.TRANSIT && s.t >= 0.95) s.state = SIGNAL_STATE.RECEIVE;
      s.t += s.velocity * dt;
      // Failure roll while in transit -> quarantine.
      if (s.state === SIGNAL_STATE.TRANSIT && s.failProb > 0 && rng && rng.float() < s.failProb * dt) {
        s.state = SIGNAL_STATE.QUARANTINED; this.quarantined++; continue;
      }
      if (s.t >= 1 || s.state === SIGNAL_STATE.RECEIVE) {
        s.t = 1; s.state = SIGNAL_STATE.COMPLETE; this.completed++;
      }
    }
    // Reap terminal signals to respect the population cap.
    if (this.signals.length > this.max * 0.75) {
      this.signals = this.signals.filter((s) =>
        s.state !== SIGNAL_STATE.COMPLETE && s.state !== SIGNAL_STATE.QUARANTINED);
    }
    return active;
  }

  /** Interpolated position of a signal along its path. */
  position(s) {
    const p = s.path, seg = (p.length - 1) * Math.min(1, Math.max(0, s.t));
    const i = Math.min(p.length - 2, Math.floor(seg));
    const f = seg - i;
    return { x: p[i].x + (p[i + 1].x - p[i].x) * f, y: p[i].y + (p[i + 1].y - p[i].y) * f };
  }
}
