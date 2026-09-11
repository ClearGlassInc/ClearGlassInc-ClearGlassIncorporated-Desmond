/**
 * Structured logging.
 *
 * The log record is an explicit allowlist of fields. Nothing here reads request
 * headers, prompt content, or response bodies, so a prompt or an Authorization
 * header cannot reach the log stream by accident — a new field has to be added
 * to FIELDS deliberately for it to be emitted at all.
 */

const FIELDS = Object.freeze([
  'request_id',
  'timestamp',
  'route',
  'method',
  'status',
  'latency_ms',
  'model',
  'error_type',
  'provider',
  'token_id',
  'client_ip_hash',
  'outcome',
  'detail',
]);

/** Fields that may contain free text and therefore get length-capped. */
const MAX_DETAIL_CHARS = 300;

/**
 * Emits one JSON line per request.
 *
 * @param {Record<string, unknown>} record
 */
export function logRequest(record) {
  const line = { timestamp: new Date().toISOString() };

  for (const field of FIELDS) {
    const value = record[field];
    if (value === undefined || value === null || value === '') continue;
    line[field] = field === 'detail' ? String(value).slice(0, MAX_DETAIL_CHARS) : value;
  }

  // Workers ships console output to the configured observability sink.
  const emit = line.status >= 500 || line.error_type ? console.error : console.log;
  emit(JSON.stringify(line));
}

/**
 * Hashes a client identifier for logs.
 *
 * Raw IPs are personal data; a truncated salted-free digest is enough to
 * correlate abuse across a window without storing the address itself.
 */
export async function hashIdentifier(value) {
  if (!value) return '';
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
  return [...new Uint8Array(digest)]
    .slice(0, 6)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}
