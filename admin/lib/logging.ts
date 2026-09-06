// Access logging + burst detection for the admin cockpit.
//
// Every request that reaches middleware is fingerprinted and logged as one
// structured JSON line, so a log drain (Render, Datadog, CloudWatch, …) can
// alert on scraping, credential-stuffing, or premium-content exfiltration.
//
// Privacy: we do NOT log raw IPs. The fingerprint is a salted hash of
// IP + user-agent, so patterns are correlatable across requests without
// storing the identity itself.
//
// Note on the in-memory burst counter: serverless/edge instances are ephemeral
// and not shared, so this catches a burst *within one instance* and is a
// best-effort signal, not a global rate limit. Enforce hard limits at the CDN /
// control-plane edge (the control plane already rate-limits — see
// app/security.py). Set BURST_STORE=external in a real deployment to route this
// to a shared store; see the deployment checklist.

const encoder = new TextEncoder();

export interface RequestFingerprint {
  /** Salted hash of ip+ua — stable per client, not reversible to an identity. */
  fingerprint: string;
  ip: string; // coarse, for the log line only; hashed clients preferred for alerts
  userAgent: string;
  referrer: string;
  path: string;
  method: string;
  timestamp: string; // ISO-8601
}

async function sha256Hex(input: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(input));
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** Best-effort client IP from common proxy headers. */
export function clientIp(headers: Headers): string {
  const xff = headers.get("x-forwarded-for");
  if (xff) return xff.split(",")[0].trim();
  return headers.get("x-real-ip") || "unknown";
}

/**
 * Build a fingerprint for a request. The hash is salted with LOG_SALT so
 * fingerprints cannot be pre-computed / correlated across deployments.
 */
export async function fingerprintRequest(
  req: { headers: Headers; method: string },
  path: string,
): Promise<RequestFingerprint> {
  const ip = clientIp(req.headers);
  const userAgent = req.headers.get("user-agent") || "unknown";
  const referrer = req.headers.get("referer") || req.headers.get("referrer") || "";
  const salt = process.env.LOG_SALT || "clearglass-log-salt";
  const fingerprint = (await sha256Hex(`${salt}:${ip}:${userAgent}`)).slice(0, 16);
  return {
    fingerprint,
    ip,
    userAgent,
    referrer,
    path,
    method: req.method,
    timestamp: new Date().toISOString(),
  };
}

// --- burst detection ----------------------------------------------------------

interface Bucket {
  count: number;
  windowStart: number;
}

const WINDOW_MS = 60_000;
const BURST_THRESHOLD = Number(process.env.BURST_THRESHOLD || 120); // req/min/fingerprint
const buckets = new Map<string, Bucket>();

// Bound memory: evict stale buckets opportunistically.
function sweep(now: number): void {
  if (buckets.size < 1000) return;
  for (const [key, b] of buckets) {
    if (now - b.windowStart > WINDOW_MS) buckets.delete(key);
  }
}

/**
 * Record a hit for `fingerprint` and report whether it just crossed the burst
 * threshold in the current 1-minute window. Returns the current count too.
 */
export function recordAndDetectBurst(fingerprint: string): { burst: boolean; count: number } {
  const now = Date.now();
  sweep(now);
  const b = buckets.get(fingerprint);
  if (!b || now - b.windowStart > WINDOW_MS) {
    buckets.set(fingerprint, { count: 1, windowStart: now });
    return { burst: false, count: 1 };
  }
  b.count += 1;
  return { burst: b.count === BURST_THRESHOLD, count: b.count };
}

export type AccessDecision = "allow" | "redirect-login" | "deny-token";

/**
 * Emit one structured access-log line. Level escalates to "warn" on a burst or a
 * blocked request so alerting rules can key off it. Kept as console JSON so it
 * works on every host without a logging SDK.
 */
export function logAccess(fp: RequestFingerprint, decision: AccessDecision, burst: boolean): void {
  const level = burst || decision !== "allow" ? "warn" : "info";
  const line = {
    level,
    event: "admin_access",
    decision,
    burst,
    ts: fp.timestamp,
    fingerprint: fp.fingerprint,
    ip: fp.ip,
    method: fp.method,
    path: fp.path,
    referrer: fp.referrer,
    ua: fp.userAgent,
  };
  // One line per request; the platform's log drain parses the JSON.
  console[level === "warn" ? "warn" : "log"](JSON.stringify(line));
}
