/* ClearGlass Visual Engine · spatial force fields.
 * A weighted combination of curl, radial, attractor, repulsor, vortex and
 * directional fields. Parameters evolve slowly via several summed low-frequency
 * oscillators (NOT a single looping sinusoid) so the motion never reads as a
 * short GIF loop. Coordinates are normalised [0,1]. Pure math. */

function pseudoCurl(x, y, t) {
  // Divergence-free-ish curl of a scalar noise made from layered sinusoids.
  const n1 = Math.sin(x * 6.28 + t * 0.7) * Math.cos(y * 6.28 - t * 0.5);
  const n2 = Math.sin(x * 12.9 - t * 0.3) * Math.cos(y * 9.7 + t * 0.4);
  const s = n1 * 0.7 + n2 * 0.3;
  // gradient approximation rotated 90° => curl
  return { fx: Math.cos(y * 6.28 + s), fy: -Math.sin(x * 6.28 + s) };
}

export class FieldStack {
  constructor(rng) {
    this.rng = rng;
    // Weights per field type (combined each sample).
    this.weights = { curl: 0.4, radial: 0.15, attractor: 0.15, repulsor: 0.1, vortex: 0.1, directional: 0.1 };
    this.turbulence = 0.5;
    // Slowly-drifting anchor points and directional bias.
    this.attractor = { x: 0.5, y: 0.5 };
    this.repulsor = { x: 0.3, y: 0.7 };
    this.vortex = { x: 0.5, y: 0.5, spin: 1 };
    this.dir = { x: 0.2, y: -0.1 };
    this._phase = [rng ? rng.float() * 6.28 : 0, rng ? rng.float() * 6.28 : 1.7, rng ? rng.float() * 6.28 : 3.1];
  }

  /** Evolve field parameters. Multiple periods => quasi-non-repeating drift. */
  evolve(t, entropyVisual) {
    const p = this._phase;
    this.attractor.x = 0.5 + 0.28 * Math.sin(t * 0.11 + p[0]) + 0.06 * Math.sin(t * 0.37 + p[1]);
    this.attractor.y = 0.5 + 0.24 * Math.cos(t * 0.09 + p[1]) + 0.05 * Math.sin(t * 0.29 + p[2]);
    this.repulsor.x = 0.5 + 0.30 * Math.sin(t * 0.07 + p[2]);
    this.repulsor.y = 0.5 + 0.30 * Math.cos(t * 0.05 + p[0]);
    this.vortex.x = 0.5 + 0.18 * Math.sin(t * 0.043 + p[1]);
    this.vortex.y = 0.5 + 0.18 * Math.cos(t * 0.061 + p[2]);
    this.vortex.spin = 0.6 + 0.4 * Math.sin(t * 0.023 + p[0]);
    if (entropyVisual) this.turbulence = entropyVisual.turbulence;
  }

  /** Sample the combined acceleration at (x,y) at time t. */
  sample(x, y, t) {
    const w = this.weights;
    let fx = 0, fy = 0;

    const c = pseudoCurl(x, y, t);
    fx += c.fx * w.curl * this.turbulence;
    fy += c.fy * w.curl * this.turbulence;

    // radial (toward centre), attractor, repulsor, vortex, directional
    const add = (tx, ty, weight, sign, swirl) => {
      let dx = tx - x, dy = ty - y;
      const d2 = dx * dx + dy * dy + 1e-3;
      const inv = 1 / Math.sqrt(d2);
      dx *= inv; dy *= inv;
      const mag = weight * sign / (d2 * 12 + 0.2);
      fx += dx * mag; fy += dy * mag;
      if (swirl) { fx += -dy * mag * swirl; fy += dx * mag * swirl; }
    };
    add(0.5, 0.5, w.radial, 1, 0);
    add(this.attractor.x, this.attractor.y, w.attractor, 1, 0);
    add(this.repulsor.x, this.repulsor.y, w.repulsor, -1, 0);
    add(this.vortex.x, this.vortex.y, w.vortex, 0.4, this.vortex.spin);

    fx += this.dir.x * w.directional;
    fy += this.dir.y * w.directional;

    return { fx, fy };
  }
}
