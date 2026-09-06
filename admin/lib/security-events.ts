export interface SecurityEvent {
  event: string;
  at: string;
  fingerprint: string;
  referrer: string;
  path: string;
  method: string;
  burstCount?: number;
  reason?: string;
}

const WINDOW_MS = 60_000;
const BURST_THRESHOLD = Number(process.env.ROUTE_BURST_THRESHOLD || 60);
const burstBuckets = new Map<string, number[]>();

function prune(now: number, hits: number[]): number[] {
  return hits.filter((hit) => now - hit <= WINDOW_MS);
}

export function recordSecurityEvent(event: Omit<SecurityEvent, "at" | "burstCount">): SecurityEvent {
  const now = Date.now();
  const hits = prune(now, burstBuckets.get(event.fingerprint) || []);
  hits.push(now);
  burstBuckets.set(event.fingerprint, hits);

  const securityEvent: SecurityEvent = {
    ...event,
    at: new Date(now).toISOString(),
    burstCount: hits.length,
  };

  // Structured stdout is intentionally sink-agnostic: production deployments can
  // route these records to a SIEM, OpenTelemetry collector, or append-only log.
  console.info(JSON.stringify({ severity: hits.length > BURST_THRESHOLD ? "warn" : "info", ...securityEvent }));
  return securityEvent;
}
