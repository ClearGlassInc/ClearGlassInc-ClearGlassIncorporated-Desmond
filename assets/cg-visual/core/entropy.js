/* ClearGlass Visual Engine · entropy model.
 * Entropy is a smoothed, weighted, normalised [0,1] scalar derived from four
 * observable activity inputs. It drives DENSITY / TURBULENCE / FREQUENCY /
 * COMPLEXITY of the visualization.
 *
 * IMPORTANT: this is a *visual* activity index only. It is explicitly NOT a
 * cyber-risk score and must never be presented as one (see directive §42).
 */

export const ENTROPY_WEIGHTS = Object.freeze({
  signalDensity: 0.30,
  graphActivity: 0.25,
  anomalyActivity: 0.25,
  eventRate: 0.20,
});

/** Squash an unbounded non-negative rate into [0,1] with a soft knee. */
function norm(x, knee) {
  const v = Math.max(0, Number.isFinite(x) ? x : 0);
  return v / (v + knee);
}

/**
 * Compute a smoothed entropy value.
 * @param {object} inputs {signalDensity, graphActivity, anomalyActivity, eventRate}
 * @param {number} prev previous smoothed entropy (for EWMA continuity)
 * @param {number} alpha smoothing factor in (0,1]
 * @returns {{value:number, raw:number, drivers:object}}
 */
export function computeEntropy(inputs = {}, prev = 0, alpha = 0.15) {
  const drivers = {
    signalDensity: norm(inputs.signalDensity, 24),
    graphActivity: norm(inputs.graphActivity, 12),
    anomalyActivity: norm(inputs.anomalyActivity, 4),
    eventRate: norm(inputs.eventRate, 8),
  };
  let raw = 0;
  for (const k in ENTROPY_WEIGHTS) raw += ENTROPY_WEIGHTS[k] * drivers[k];
  raw = Math.min(1, Math.max(0, raw));
  const a = Math.min(1, Math.max(1e-4, alpha));
  const value = prev + a * (raw - prev);
  return { value: Math.min(1, Math.max(0, value)), raw, drivers };
}

/** Map entropy [0,1] to the visual parameters scenes consume. */
export function entropyToVisual(entropy) {
  const e = Math.min(1, Math.max(0, entropy));
  return {
    density: 0.35 + 0.65 * e,        // fraction of particle budget in use
    turbulence: 0.15 + 0.85 * e,     // field noise amplitude
    frequency: 0.5 + 1.5 * e,        // temporal oscillation rate multiplier
    complexity: Math.round(1 + 4 * e), // number of active field octaves/effects
  };
}
