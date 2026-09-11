/**
 * Request rate limiting.
 *
 * Two backends are supported:
 *
 *  - Cloudflare's native rate-limiting binding (`env.RATE_LIMITER`), which is
 *    enforced across the edge. Use this in production.
 *  - An in-isolate fixed-window counter, used when no binding is present.
 *
 * The in-isolate limiter is deliberately conservative but is *per isolate*:
 * Cloudflare runs many isolates, so the effective global ceiling is higher than
 * the configured value. It stops runaway clients and brute-force attempts; it
 * is not a billing control. See README "Production hardening".
 */

import { tooManyRequests } from '../lib/errors.js';

const WINDOW_MS = 60_000;

/** Bounds isolate memory if a large number of distinct keys is seen. */
const MAX_TRACKED_KEYS = 10_000;

/** Module-scoped so the window survives across requests in the same isolate. */
const buckets = new Map();

/** Drops expired entries; called before insert so the map cannot grow forever. */
function prune(now) {
  for (const [key, bucket] of buckets) {
    if (bucket.resetAt <= now) buckets.delete(key);
  }
  if (buckets.size >= MAX_TRACKED_KEYS) {
    // Still saturated after pruning: shed the oldest entries rather than
    // letting the isolate accumulate unbounded state.
    const excess = buckets.size - Math.floor(MAX_TRACKED_KEYS / 2);
    let removed = 0;
    for (const key of buckets.keys()) {
      if (removed >= excess) break;
      buckets.delete(key);
      removed += 1;
    }
  }
}

/** Clears all counters. Exported for tests. */
export function resetRateLimiter() {
  buckets.clear();
}

/** Returns the caller's IP as reported by Cloudflare, with a safe fallback. */
export function clientIp(request) {
  return (
    request.headers.get('CF-Connecting-IP') ||
    request.headers.get('X-Real-IP') ||
    // X-Forwarded-For is client-controlled unless a trusted proxy rewrites it;
    // it is used only as a last resort and only the first hop is taken.
    (request.headers.get('X-Forwarded-For') || '').split(',')[0].trim() ||
    'unknown'
  );
}

function checkLocal(key, limit, now) {
  const existing = buckets.get(key);

  if (!existing || existing.resetAt <= now) {
    prune(now);
    buckets.set(key, { count: 1, resetAt: now + WINDOW_MS });
    return { allowed: true, remaining: limit - 1, resetAt: now + WINDOW_MS };
  }

  if (existing.count >= limit) {
    return { allowed: false, remaining: 0, resetAt: existing.resetAt };
  }

  existing.count += 1;
  return { allowed: true, remaining: limit - existing.count, resetAt: existing.resetAt };
}

/**
 * Applies the rate limit for a key.
 *
 * @returns {Promise<{ allowed: boolean, remaining: number, resetAt: number }>}
 */
export async function checkRateLimit(key, env, config, now = Date.now()) {
  const binding = env?.RATE_LIMITER;

  if (binding && typeof binding.limit === 'function') {
    const outcome = await binding.limit({ key });
    return {
      allowed: Boolean(outcome?.success),
      // The native binding does not report a remaining count or a reset time;
      // the window length is the honest upper bound to advertise.
      remaining: outcome?.success ? config.rateLimitPerMinute - 1 : 0,
      resetAt: now + WINDOW_MS,
    };
  }

  return checkLocal(key, config.rateLimitPerMinute, now);
}

/** Formats the advisory headers returned on allowed requests. */
export function rateLimitHeaders(result, config) {
  return {
    'X-RateLimit-Limit': String(config.rateLimitPerMinute),
    'X-RateLimit-Remaining': String(Math.max(0, result.remaining)),
    'X-RateLimit-Reset': String(Math.ceil(result.resetAt / 1000)),
  };
}

/**
 * Enforces the rate limit, raising 429 with `Retry-After` when exceeded.
 *
 * @param {string} key Bucket identifier, already namespaced by the caller.
 */
export async function enforceRateLimit(key, env, config, now = Date.now()) {
  const result = await checkRateLimit(key, env, config, now);

  if (!result.allowed) {
    const retryAfter = Math.max(1, Math.ceil((result.resetAt - now) / 1000));
    throw tooManyRequests(retryAfter, config.rateLimitPerMinute);
  }

  return result;
}
