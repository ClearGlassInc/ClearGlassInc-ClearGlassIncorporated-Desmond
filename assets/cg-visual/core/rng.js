/* ClearGlass Visual Engine · deterministic RNG.
 * Seeded, allocation-free per call, reproducible across runs and machines.
 * Used everywhere a "random" value is needed so replays are bit-identical.
 * No crypto material here — this is a visual PRNG only (labelled DEMO). */

/** mulberry32: fast 32-bit seeded PRNG. Returns a function -> float in [0,1). */
export function mulberry32(seed) {
  let a = seed >>> 0;
  return function next() {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Deterministic string -> uint32 seed (djb2). */
export function hashSeed(str) {
  let h = 5381;
  const s = String(str);
  for (let i = 0; i < s.length; i++) h = (Math.imul(h, 33) ^ s.charCodeAt(i)) >>> 0;
  return h >>> 0;
}

/** A small stateful RNG wrapper with the helpers the engine reaches for. */
export class Rng {
  constructor(seed) {
    this.seed = (typeof seed === 'string' ? hashSeed(seed) : (seed >>> 0)) || 1;
    this._n = mulberry32(this.seed);
  }
  float() { return this._n(); }
  range(lo, hi) { return lo + (hi - lo) * this._n(); }
  int(lo, hi) { return Math.floor(this.range(lo, hi + 1)); }
  /** Reset to the original seed — used by deterministic replay. */
  reset() { this._n = mulberry32(this.seed); }
}
