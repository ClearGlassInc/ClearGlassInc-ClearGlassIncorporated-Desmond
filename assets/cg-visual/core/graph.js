/* ClearGlass Visual Engine · intelligence graph physics.
 * Force-directed layout: repulsion (Coulomb-ish) + spring attraction along
 * edges + velocity damping + anchors + bounds constraints. Important nodes are
 * anchored so the topology stays stable and legible instead of drifting.
 * Coordinates normalised [0,1]. Deterministic given a seeded RNG. */

export class GraphPhysics {
  constructor(rng, opts = {}) {
    this.rng = rng;
    this.repulsion = opts.repulsion || 0.0012;
    this.spring = opts.spring || 2.2;
    this.damping = opts.damping || 0.86;
    this.restLength = opts.restLength || 0.22;
    this.nodes = [];
    this.edges = [];
  }

  addNode(id, opts = {}) {
    const n = {
      id,
      x: opts.x != null ? opts.x : (this.rng ? this.rng.range(0.2, 0.8) : 0.5),
      y: opts.y != null ? opts.y : (this.rng ? this.rng.range(0.2, 0.8) : 0.5),
      vx: 0, vy: 0,
      mass: opts.mass || 1,
      anchored: !!opts.anchored,     // important nodes stay put
      importance: opts.importance || 0.5,
      label: opts.label || id,
    };
    this.nodes.push(n);
    return n;
  }

  addEdge(a, b, weight = 1) { this.edges.push({ a, b, weight }); }

  step(dt) {
    const N = this.nodes.length;
    // Pairwise repulsion.
    for (let i = 0; i < N; i++) {
      const ni = this.nodes[i];
      if (ni.anchored) continue;
      let ax = 0, ay = 0;
      for (let j = 0; j < N; j++) {
        if (i === j) continue;
        const nj = this.nodes[j];
        let dx = ni.x - nj.x, dy = ni.y - nj.y;
        const d2 = dx * dx + dy * dy + 1e-4;
        const f = this.repulsion / d2;
        const inv = 1 / Math.sqrt(d2);
        ax += dx * inv * f; ay += dy * inv * f;
      }
      ni.vx += ax * dt; ni.vy += ay * dt;
    }
    // Spring attraction along edges.
    for (const e of this.edges) {
      const a = this._byId(e.a), b = this._byId(e.b);
      if (!a || !b) continue;
      let dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.sqrt(dx * dx + dy * dy) + 1e-4;
      const f = this.spring * (d - this.restLength) * e.weight;
      const ux = dx / d, uy = dy / d;
      if (!a.anchored) { a.vx += ux * f * dt / a.mass; a.vy += uy * f * dt / a.mass; }
      if (!b.anchored) { b.vx -= ux * f * dt / b.mass; b.vy -= uy * f * dt / b.mass; }
    }
    // Integrate + damp + clamp to [0,1] bounds.
    let activity = 0;
    for (const n of this.nodes) {
      if (n.anchored) { n.vx = n.vy = 0; continue; }
      n.vx *= this.damping; n.vy *= this.damping;
      n.x += n.vx * dt; n.y += n.vy * dt;
      if (n.x < 0.02) { n.x = 0.02; n.vx *= -0.5; }
      if (n.x > 0.98) { n.x = 0.98; n.vx *= -0.5; }
      if (n.y < 0.02) { n.y = 0.02; n.vy *= -0.5; }
      if (n.y > 0.98) { n.y = 0.98; n.vy *= -0.5; }
      activity += Math.abs(n.vx) + Math.abs(n.vy);
    }
    return activity;
  }

  _byId(id) { for (const n of this.nodes) if (n.id === id) return n; return null; }
}
