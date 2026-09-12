/* ClearGlass Visual Engine · deterministic replay.
 * Record a seed + the exact (frame, event, dt) sequence; replaying it rebuilds
 * a Simulation and reproduces bit-identical state. Also supports pause/step/
 * reset for debugging. Because Simulation uses only the seeded Rng and the dt
 * argument, replay is exact. */

import { Simulation } from './simulation.js';

export class Recorder {
  constructor(seed, opts = {}) {
    this.seed = seed;
    this.opts = opts;
    this.entries = []; // {frame, dt, events:[raw,...]}
    this.paused = false;
    this.sim = new Simulation(seed, opts);
  }

  /** Feed events for the *next* step, then step. Records both. */
  tick(dt, rawEvents = []) {
    if (this.paused) return this.sim.world;
    for (const e of rawEvents) this.sim.emit(e);
    this.entries.push({ frame: this.sim.world.frame + 1, dt, events: rawEvents.map(clone) });
    return this.sim.step(dt);
  }

  pause() { this.paused = true; }
  resume() { this.paused = false; }

  /** Step exactly once even while paused (debug stepping). */
  stepOnce(dt, rawEvents = []) {
    for (const e of rawEvents) this.sim.emit(e);
    this.entries.push({ frame: this.sim.world.frame + 1, dt, events: rawEvents.map(clone) });
    return this.sim.step(dt);
  }

  record() { return { seed: this.seed, opts: this.opts, entries: this.entries.map((e) => ({ ...e, events: e.events.map(clone) })) }; }

  reset() { this.sim = new Simulation(this.seed, this.opts); this.entries = []; }
}

/** Replay a recording from scratch; returns the final Simulation + snapshot. */
export function replay(record) {
  const sim = new Simulation(record.seed, record.opts || {});
  for (const entry of record.entries) {
    for (const e of entry.events) sim.emit(e);
    sim.step(entry.dt);
  }
  return { sim, snapshot: sim.snapshot() };
}

function clone(o) { return JSON.parse(JSON.stringify(o)); }
