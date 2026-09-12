/* ClearGlass Visual Engine · importance engine.
 * importance = priority * activity * proximity * sceneRelevance * recency,
 * each factor normalised to (0,1]. Drives LOD, opacity, label visibility,
 * render budget allocation and draw order. Pure math. */

/** Convert a P0..P3 priority to a (0,1] weight (P0 highest). */
function priorityWeight(p) { return [1.0, 0.75, 0.5, 0.3][Math.max(0, Math.min(3, p | 0))]; }

/**
 * @param {object} o {priority, activity(0..1), proximity(0..1), sceneRelevance(0..1), ageSeconds}
 * @param {object} ctx {recencyHalfLife}
 */
export function importance(o, ctx = {}) {
  const halfLife = ctx.recencyHalfLife || 6;
  const recency = Math.pow(0.5, Math.max(0, o.ageSeconds || 0) / halfLife);
  const clamp01 = (x) => Math.min(1, Math.max(1e-3, Number.isFinite(x) ? x : 1e-3));
  return priorityWeight(o.priority) *
    clamp01(o.activity != null ? o.activity : 1) *
    clamp01(o.proximity != null ? o.proximity : 1) *
    clamp01(o.sceneRelevance != null ? o.sceneRelevance : 1) *
    clamp01(recency);
}

/** Return items sorted by descending importance (stable), with score attached. */
export function rankByImportance(items, ctx) {
  return items
    .map((it, i) => ({ item: it, i, score: importance(it, ctx) }))
    .sort((a, b) => (b.score - a.score) || (a.i - b.i))
    .map((r) => ({ ...r.item, _importance: r.score }));
}

/** Map importance -> discrete LOD level {0:statistical,1:far,2:medium,3:near}. */
export function importanceToLod(score) {
  if (score >= 0.6) return 3;
  if (score >= 0.3) return 2;
  if (score >= 0.12) return 1;
  return 0;
}
