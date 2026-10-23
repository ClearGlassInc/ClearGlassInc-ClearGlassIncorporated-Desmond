/* ClearGlass Visual Engine · instrument cadence.
 * Pure, DOM-free timing and policy for the in-content instruments
 * (assets/cg-visual/instruments/). Node-testable like the rest of core/.
 *
 * "Stochastic within deterministic limits": every interval is drawn from a
 * seeded Rng and clamped to a [min, max] window, so motion never bunches up or
 * stalls, and a run with the same seed is identical. */

/** A delay in [minMs, maxMs], drawn from a seeded Rng (core/rng.js). */
export function boundedDelay(rng, minMs, maxMs) {
  const lo = Math.min(minMs, maxMs);
  const hi = Math.max(minMs, maxMs);
  return lo + (hi - lo) * rng.float();
}

/**
 * Rendering policy for the instruments. The engine's ResourceGovernor already
 * measures frame health and picks a tier; instruments follow it rather than
 * keeping a second, competing performance model.
 *   full   — continuous motion at 30fps
 *   lite   — motion on, 20fps, one signal at a time (small screens, Save-Data,
 *            a struggling device)
 *   static — no continuous motion; every instrument shows its resting state
 */
export function instrumentPolicy({ reduced = false, tier = null, saveData = false, narrow = false } = {}) {
  if (reduced || tier === 'MINIMAL') return { mode: 'static', fps: 0, signals: 0 };
  if (saveData || narrow || tier === 'LOW') return { mode: 'lite', fps: 20, signals: 1 };
  return { mode: 'full', fps: 30, signals: 2 };
}

function dwellAt(plan, i) {
  const d = plan.dwellMs && plan.dwellMs[i];
  return typeof d === 'number' && d >= 0 ? d : plan.defaultDwellMs;
}

/** Total length of one evidence-chain run, in ms. */
export function chainDuration(plan) {
  let total = 0;
  for (let i = 0; i < plan.stages; i++) total += dwellAt(plan, i);
  return total + Math.max(0, plan.stages - 1) * plan.travelMs + plan.sealMs;
}

/**
 * Where an evidence-chain run is at `t` ms after it started. A packet dwells at
 * each stage, travels to the next, and the run ends sealed at the last stage.
 * Gate stages (human approval) get a longer dwell so the motion shows the wait.
 *   { phase: 'dwell'|'travel'|'sealed'|'done', stage, to?, progress 0..1 }
 */
export function chainState(t, plan) {
  let at = Math.max(0, t);
  for (let i = 0; i < plan.stages; i++) {
    const dwell = dwellAt(plan, i);
    if (at < dwell) return { phase: 'dwell', stage: i, progress: dwell ? at / dwell : 1 };
    at -= dwell;
    if (i < plan.stages - 1) {
      if (at < plan.travelMs) return { phase: 'travel', stage: i, to: i + 1, progress: at / plan.travelMs };
      at -= plan.travelMs;
    }
  }
  const last = plan.stages - 1;
  if (at < plan.sealMs) return { phase: 'sealed', stage: last, progress: at / plan.sealMs };
  return { phase: 'done', stage: last, progress: 1 };
}

/**
 * Example targets for the radar, spread so no two share a bearing window.
 * Bearings in degrees [0, 360), range as a fraction of the scope radius.
 * Ids are EX-nn: they are example signals and are labelled as such.
 */
export function seedTargets(rng, count, minSeparationDeg = 40) {
  const targets = [];
  let guard = 0;
  while (targets.length < count && guard++ < count * 50) {
    const bearing = rng.float() * 360;
    const clear = targets.every((t) => angularGap(t.bearing, bearing) >= minSeparationDeg);
    if (!clear) continue;
    targets.push({
      id: 'EX-' + String(targets.length + 1).padStart(2, '0'),
      bearing,
      range: 0.28 + rng.float() * 0.58,
    });
  }
  return targets;
}

export function angularGap(a, b) {
  const d = Math.abs(((a - b) % 360 + 360) % 360);
  return Math.min(d, 360 - d);
}

/**
 * Targets the sweep passed over between two frames: bearing in (prev, next].
 * Angles are UNWRAPPED (they only grow), so the wrap through 0deg is handled
 * here and a sweep that advanced a full turn or more (a long-hidden tab)
 * reports nothing rather than firing every target at once.
 */
export function sweepHits(prevDeg, nextDeg, targets) {
  const advance = nextDeg - prevDeg;
  if (!(advance > 0) || advance >= 360) return [];
  const start = ((prevDeg % 360) + 360) % 360;
  return targets.filter((t) => {
    const fromStart = ((t.bearing - start) % 360 + 360) % 360;
    return fromStart > 0 && fromStart <= advance;
  });
}
