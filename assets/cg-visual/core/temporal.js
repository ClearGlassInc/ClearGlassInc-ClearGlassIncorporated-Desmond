/* ClearGlass Visual Engine · temporal model.
 * A rolling-history channel that derives value/velocity/accel/trend/variance/
 * mean/min/max/stability/recoveryRate from a stream of samples using EWMA.
 * Pure math, no DOM, no time source — the caller supplies dt so replays match. */

/** Exponentially-weighted temporal channel. */
export class TemporalChannel {
  /**
   * @param {number} alpha smoothing factor in (0,1]; higher = more responsive.
   * @param {number} historyLen ring-buffer length for min/max/variance windows.
   */
  constructor(alpha = 0.2, historyLen = 64) {
    this.alpha = Math.min(1, Math.max(1e-4, alpha));
    this.historyLen = Math.max(2, historyLen | 0);
    this.history = [];
    this.value = 0;
    this.prev = 0;
    this.mean = 0;       // EWMA mean
    this.variance = 0;   // EWMA variance
    this.velocity = 0;   // smoothed d(value)/dt
    this.accel = 0;      // smoothed d(velocity)/dt
    this.min = Infinity;
    this.max = -Infinity;
    this._peak = -Infinity;   // for recoveryRate
    this.recoveryRate = 0;    // how fast we fall back from a peak (>=0)
    this.samples = 0;
  }

  /**
   * Push one sample observed over dt seconds.
   * @returns {this}
   */
  push(raw, dt = 1 / 60) {
    const v = Number.isFinite(raw) ? raw : 0;
    const d = dt > 1e-6 ? dt : 1 / 60;
    const a = this.alpha;

    this.prev = this.value;
    this.value = v;

    // EWMA mean + variance (Welford-style EWMA).
    if (this.samples === 0) {
      this.mean = v;
      this.variance = 0;
    } else {
      const delta = v - this.mean;
      this.mean += a * delta;
      this.variance = (1 - a) * (this.variance + a * delta * delta);
    }

    // Velocity + acceleration, smoothed.
    const instVel = (this.value - this.prev) / d;
    const prevVel = this.velocity;
    this.velocity += a * (instVel - this.velocity);
    const instAcc = (this.velocity - prevVel) / d;
    this.accel += a * (instAcc - this.accel);

    // Windowed history for min/max + robust stats.
    this.history.push(v);
    if (this.history.length > this.historyLen) this.history.shift();
    this.min = Math.min(...this.history);
    this.max = Math.max(...this.history);

    // Recovery: track a decaying peak; recoveryRate is the downhill slope.
    if (v >= this._peak) {
      this._peak = v;
      this.recoveryRate = 0;
    } else {
      this.recoveryRate = Math.max(0, (this._peak - v) / d);
      this._peak += a * (v - this._peak); // peak decays toward current
    }

    this.samples++;
    return this;
  }

  /** Trend in [-1,1]: sign+magnitude of smoothed velocity, squashed. */
  get trend() {
    return Math.tanh(this.velocity);
  }

  /** Stability in [0,1]: 1 when variance is low relative to mean scale. */
  get stability() {
    const scale = Math.max(1e-3, Math.abs(this.mean));
    return 1 / (1 + Math.sqrt(Math.max(0, this.variance)) / scale);
  }

  snapshot() {
    return {
      value: this.value,
      mean: this.mean,
      variance: this.variance,
      velocity: this.velocity,
      accel: this.accel,
      trend: this.trend,
      stability: this.stability,
      recoveryRate: this.recoveryRate,
      min: this.history.length ? this.min : 0,
      max: this.history.length ? this.max : 0,
    };
  }
}
