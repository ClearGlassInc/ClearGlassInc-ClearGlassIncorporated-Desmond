/* ClearGlass Visual Engine · particle pool.
 * Fixed-capacity, allocation-free particle system. All storage is preallocated
 * in typed arrays at construction; spawn/decay/terminate never grow the backing
 * store, so the heap does not churn per frame. Lifecycle:
 *   spawn -> propagate -> interact -> (merge|split) -> decay -> terminate.
 * A free-list recycles slots. Pure math; time supplied via dt. */

const DEAD = 0;
const ALIVE = 1;

export class ParticlePool {
  constructor(capacity = 4000) {
    this.capacity = capacity | 0;
    const n = this.capacity;
    this.state = new Uint8Array(n);
    this.x = new Float32Array(n);
    this.y = new Float32Array(n);
    this.vx = new Float32Array(n);
    this.vy = new Float32Array(n);
    this.life = new Float32Array(n);   // remaining life, seconds
    this.age = new Float32Array(n);
    this.mass = new Float32Array(n);
    this.hot = new Float32Array(n);    // 0..1 importance/priority tint
    this._free = new Int32Array(n);
    for (let i = 0; i < n; i++) this._free[i] = n - 1 - i; // stack of free indices
    this._freeTop = n;
    this.activeCount = 0;
    this.spawnFailures = 0;            // spawns refused because pool was full
  }

  /** Spawn one particle. Returns its index, or -1 if the pool is saturated. */
  spawn(px, py, vx, vy, life, mass, hot) {
    if (this._freeTop === 0) { this.spawnFailures++; return -1; }
    const i = this._free[--this._freeTop];
    this.state[i] = ALIVE;
    this.x[i] = px; this.y[i] = py;
    this.vx[i] = vx || 0; this.vy[i] = vy || 0;
    this.life[i] = life || 1; this.age[i] = 0;
    this.mass[i] = mass || 1; this.hot[i] = hot || 0;
    this.activeCount++;
    return i;
  }

  /** Terminate a particle and return its slot to the free-list. */
  terminate(i) {
    if (this.state[i] !== ALIVE) return;
    this.state[i] = DEAD;
    this._free[this._freeTop++] = i;
    this.activeCount--;
  }

  /**
   * Advance every live particle. `accel(i, out)` fills out.ax/out.ay from a
   * field; omitted => inertial motion. Decays life; terminates on expiry.
   */
  step(dt, accel) {
    const a = { ax: 0, ay: 0 };
    for (let i = 0; i < this.capacity; i++) {
      if (this.state[i] !== ALIVE) continue;
      if (accel) { a.ax = 0; a.ay = 0; accel(i, a); this.vx[i] += a.ax * dt; this.vy[i] += a.ay * dt; }
      this.x[i] += this.vx[i] * dt;
      this.y[i] += this.vy[i] * dt;
      this.age[i] += dt;
      this.life[i] -= dt;                 // decay
      if (this.life[i] <= 0) this.terminate(i);
    }
  }

  /** Merge b into a (mass-weighted); terminates b. Used for particle coalescing. */
  merge(a, b) {
    if (this.state[a] !== ALIVE || this.state[b] !== ALIVE) return;
    const ma = this.mass[a], mb = this.mass[b], m = ma + mb;
    this.x[a] = (this.x[a] * ma + this.x[b] * mb) / m;
    this.y[a] = (this.y[a] * ma + this.y[b] * mb) / m;
    this.vx[a] = (this.vx[a] * ma + this.vx[b] * mb) / m;
    this.vy[a] = (this.vy[a] * ma + this.vy[b] * mb) / m;
    this.mass[a] = m;
    this.hot[a] = Math.max(this.hot[a], this.hot[b]);
    this.terminate(b);
  }

  /** Split particle i into two, if capacity allows. Returns the new index or -1. */
  split(i, spreadVx, spreadVy) {
    if (this.state[i] !== ALIVE) return -1;
    const half = this.mass[i] * 0.5;
    this.mass[i] = half;
    return this.spawn(this.x[i], this.y[i],
      this.vx[i] + (spreadVx || 0), this.vy[i] + (spreadVy || 0),
      this.life[i], half, this.hot[i]);
  }

  /** Fraction of the pool currently in use. */
  get load() { return this.activeCount / this.capacity; }
}
