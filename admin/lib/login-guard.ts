// Login defences shared by /api/login and /api/auth/login.
//
// Kept free of Next.js imports so `node --test` can load it directly
// (tests/test_admin_login_guard.py). Erasable TypeScript only: no enums, no
// parameter properties, so Node's type stripping can run it unmodified.
import { createHash, timingSafeEqual } from "node:crypto";

const PROBE_ORIGIN = "https://login-guard.invalid";

// Tab, newline and other C0 controls are stripped by the WHATWG URL parser, and
// a backslash is read as "/" for http(s). So "/\evil.example" and
// "/\t/evil.example" both pass a startsWith("/") check and still resolve to
// //evil.example. Reject them outright instead of trying to normalise.
const UNSAFE_CHARS = /[\\\u0000-\u001f\u007f]/;

// Return a same-origin path to redirect to after login, or "/".
export function safeNextPath(value: unknown): string {
  if (typeof value !== "string" || !value.startsWith("/") || UNSAFE_CHARS.test(value)) return "/";
  let resolved: URL;
  try {
    resolved = new URL(value, PROBE_ORIGIN);
  } catch {
    return "/";
  }
  if (resolved.origin !== PROBE_ORIGIN) return "/";
  return `${resolved.pathname}${resolved.search}${resolved.hash}`;
}

// Compare a supplied credential with the expected one in constant time.
// Hashing both sides first makes the buffers equal length, so the comparison
// time does not reveal the expected length either.
export function constantTimeEqual(supplied: string, expected: string): boolean {
  const a = createHash("sha256").update(supplied, "utf8").digest();
  const b = createHash("sha256").update(expected, "utf8").digest();
  return timingSafeEqual(a, b);
}

export const MAX_FAILURES = 5;
export const GLOBAL_MAX_FAILURES = 50;
export const LOCKOUT_WINDOW_MS = 15 * 60_000;
const MAX_TRACKED_CLIENTS = 10_000;

// Failed-login lockout: MAX_FAILURES per client key, and GLOBAL_MAX_FAILURES
// across all keys, within a sliding LOCKOUT_WINDOW_MS.
//
// The client key is the middleware's request fingerprint (IP + user agent),
// which a caller can vary, so the global ceiling is what actually bounds
// guessing. The accepted cost: 50 bad attempts from anyone lock the login for
// everyone for up to 15 minutes. The control-plane API is unaffected.
//
// State is in memory: per instance, lost on restart. The durable per-user
// lockout (users.failed_logins, users.locked_until) arrives with RBAC in CRCS
// Phase 1 item 1.6.
export class LoginThrottle {
  readonly maxFailures: number;
  readonly globalMaxFailures: number;
  readonly windowMs: number;
  private readonly failures = new Map<string, number[]>();
  private globalFailures: number[] = [];

  constructor(
    maxFailures: number = MAX_FAILURES,
    globalMaxFailures: number = GLOBAL_MAX_FAILURES,
    windowMs: number = LOCKOUT_WINDOW_MS,
  ) {
    this.maxFailures = maxFailures;
    this.globalMaxFailures = globalMaxFailures;
    this.windowMs = windowMs;
  }

  private recent(hits: number[], now: number): number[] {
    return hits.filter((at) => now - at < this.windowMs);
  }

  private clientHits(key: string, now: number): number[] {
    const hits = this.recent(this.failures.get(key) || [], now);
    if (hits.length) this.failures.set(key, hits);
    else this.failures.delete(key);
    return hits;
  }

  isLocked(key: string, now: number = Date.now()): boolean {
    this.globalFailures = this.recent(this.globalFailures, now);
    return (
      this.globalFailures.length >= this.globalMaxFailures ||
      this.clientHits(key, now).length >= this.maxFailures
    );
  }

  // Seconds until the oldest counted failure leaves the window.
  retryAfterSeconds(key: string, now: number = Date.now()): number {
    const hits = this.clientHits(key, now);
    const blocking =
      hits.length >= this.maxFailures ? hits : this.recent(this.globalFailures, now);
    if (!blocking.length) return 0;
    return Math.max(1, Math.ceil((blocking[0] + this.windowMs - now) / 1000));
  }

  recordFailure(key: string, now: number = Date.now()): void {
    const hits = this.clientHits(key, now);
    hits.push(now);
    this.failures.set(key, hits);
    this.globalFailures.push(now);
    // Spoofed keys must not grow memory without bound: drop the oldest client.
    if (this.failures.size > MAX_TRACKED_CLIENTS) {
      const oldest = this.failures.keys().next().value;
      if (oldest !== undefined) this.failures.delete(oldest);
    }
  }

  // A successful login clears that client's count, not the global one.
  reset(key: string): void {
    this.failures.delete(key);
  }
}

// One throttle per server instance, shared by both login routes.
export const loginThrottle = new LoginThrottle(
  MAX_FAILURES,
  Number(process.env.ADMIN_LOGIN_GLOBAL_MAX_FAILURES || GLOBAL_MAX_FAILURES),
);
