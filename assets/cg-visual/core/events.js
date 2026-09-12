/* ClearGlass Visual Engine · event pipeline.
 * EVENT -> VALIDATE (zero-trust) -> CLASSIFY -> QUEUE (bounded, burst-compressed).
 * Every event is untrusted input: type/size/schema/range/frequency are checked
 * before anything downstream sees it. Queues have HARD LIMITS — never unbounded.
 * No DOM, no network, no eval. */

/** Priority bands. P0 = most critical (never dropped, never compressed away). */
export const PRIORITY = Object.freeze({ P0: 0, P1: 1, P2: 2, P3: 3 });

const KNOWN_TYPES = Object.freeze({
  signal: PRIORITY.P2,
  anomaly: PRIORITY.P1,
  provenance: PRIORITY.P2,
  node: PRIORITY.P3,
  edge: PRIORITY.P3,
  pipeline: PRIORITY.P2,
  alert: PRIORITY.P0,
  telemetry: PRIORITY.P3,
});

const MAX_PAYLOAD_BYTES = 4096;
const MAX_STRING = 512;

/** Rough byte size of a JSON-serialisable value without throwing on cycles. */
function roughSize(v) {
  try { return JSON.stringify(v).length; } catch (e) { return Infinity; }
}

/**
 * Zero-trust validation. Returns {ok:true, value} or {ok:false, reason}.
 * Rejects: non-objects, unknown types, oversized payloads, out-of-range
 * numbers, non-finite magnitudes, over-long strings.
 */
export function validateEvent(raw) {
  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) {
    return { ok: false, reason: 'not-an-object' };
  }
  const type = raw.type;
  if (typeof type !== 'string' || !(type in KNOWN_TYPES)) {
    return { ok: false, reason: 'unknown-type' };
  }
  if ('magnitude' in raw) {
    const m = raw.magnitude;
    if (typeof m !== 'number' || !Number.isFinite(m) || m < 0 || m > 1e6) {
      return { ok: false, reason: 'magnitude-out-of-range' };
    }
  }
  if ('label' in raw && (typeof raw.label !== 'string' || raw.label.length > MAX_STRING)) {
    return { ok: false, reason: 'bad-label' };
  }
  if (roughSize(raw) > MAX_PAYLOAD_BYTES) {
    return { ok: false, reason: 'payload-too-large' };
  }
  // Normalise into a trusted, minimal shape (drops unexpected keys).
  const clean = {
    type,
    magnitude: typeof raw.magnitude === 'number' ? Math.max(0, Math.min(1e6, raw.magnitude)) : 1,
    label: typeof raw.label === 'string' ? raw.label.slice(0, MAX_STRING) : type,
    source: typeof raw.source === 'string' ? raw.source.slice(0, MAX_STRING) : 'unknown',
    priorityHint: (raw.priority in PRIORITY_REVERSE) ? raw.priority : null,
  };
  return { ok: true, value: clean };
}

const PRIORITY_REVERSE = Object.freeze({ 0: 'P0', 1: 'P1', 2: 'P2', 3: 'P3' });

/** Assign category + priority + a bounded visual weight. */
export function classify(clean) {
  const priority = clean.priorityHint != null ? clean.priorityHint : KNOWN_TYPES[clean.type];
  // Higher priority (lower number) => more amplitude, longer duration.
  const amp = [1.0, 0.7, 0.45, 0.25][priority];
  return {
    type: clean.type,
    label: clean.label,
    source: clean.source,
    magnitude: clean.magnitude,
    priority,
    amplitude: amp,
    duration: [3.0, 2.0, 1.2, 0.7][priority],
    telemetry: priority <= PRIORITY.P1, // only high-priority events are logged verbosely
  };
}

/**
 * Bounded event queue with per-source frequency limiting, backpressure
 * (drop-lowest-priority), and burst compression (collapse consecutive
 * same-type events into one EVENT BURST × N, preserving P0).
 */
export class EventQueue {
  constructor(opts = {}) {
    this.maxQueue = opts.maxQueue || 256;
    this.maxPerSourcePerTick = opts.maxPerSourcePerTick || 32;
    this.items = [];
    this.dropped = 0;
    this.rejected = 0;
    this.compressed = 0;
    this._sourceCounts = new Map();
  }

  /** Reset per-tick frequency counters. Call once per simulation step. */
  beginTick() { this._sourceCounts.clear(); }

  /**
   * Offer a raw (untrusted) event. Returns the accepted classified event,
   * or null if it was rejected / dropped / rate-limited / compressed.
   */
  offer(raw) {
    const v = validateEvent(raw);
    if (!v.ok) { this.rejected++; return null; }

    // Frequency limit per source (flood protection).
    const c = (this._sourceCounts.get(v.value.source) || 0) + 1;
    this._sourceCounts.set(v.value.source, c);
    if (c > this.maxPerSourcePerTick) { this.dropped++; return null; }

    const evt = classify(v.value);

    // Burst compression: if the tail is a non-critical event of the same type
    // and source, aggregate instead of appending a new entry.
    const tail = this.items[this.items.length - 1];
    if (tail && evt.priority > PRIORITY.P0 &&
        tail.type === evt.type && tail.source === evt.source) {
      tail.burst = (tail.burst || 1) + 1;
      tail.magnitude = Math.max(tail.magnitude, evt.magnitude);
      tail.label = 'EVENT BURST × ' + tail.burst + ' · ' + evt.type;
      this.compressed++;
      return tail;
    }

    // Backpressure: hard cap. When full, evict the lowest-priority (highest
    // priority-number) item; refuse if the newcomer is itself the lowest.
    if (this.items.length >= this.maxQueue) {
      let worstIdx = -1, worstPri = evt.priority;
      for (let i = 0; i < this.items.length; i++) {
        if (this.items[i].priority > worstPri) { worstPri = this.items[i].priority; worstIdx = i; }
      }
      if (worstIdx === -1) { this.dropped++; return null; }
      this.items.splice(worstIdx, 1);
      this.dropped++;
    }
    this.items.push(evt);
    return evt;
  }

  /** Drain up to `n` items in priority order (P0 first). */
  drain(n = Infinity) {
    this.items.sort((a, b) => a.priority - b.priority);
    const out = this.items.splice(0, Math.min(n, this.items.length));
    return out;
  }

  get size() { return this.items.length; }
}
