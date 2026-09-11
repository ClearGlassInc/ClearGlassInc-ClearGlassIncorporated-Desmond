/**
 * Response construction: request IDs, security headers, JSON and error bodies.
 */

import { ERROR_TYPES, GatewayError } from './errors.js';

/**
 * Headers applied to every response the gateway emits. The gateway serves JSON
 * only, so the CSP is a deny-all: nothing should ever be rendered from it.
 */
export const SECURITY_HEADERS = Object.freeze({
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'no-referrer',
  'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
  'Cross-Origin-Resource-Policy': 'same-origin',
  'Permissions-Policy': 'geolocation=(), microphone=(), camera=(), browsing-topics=()',
  // Responses are per-credential; never let a shared cache hold them.
  'Cache-Control': 'no-store',
});

/** Generates a request ID used for correlation between logs and clients. */
export function newRequestId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `req_${crypto.randomUUID().replace(/-/g, '')}`;
  }
  // Deterministically-shaped fallback; Workers and Node 22 both provide randomUUID.
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return `req_${[...bytes].map((b) => b.toString(16).padStart(2, '0')).join('')}`;
}

function baseHeaders(requestId, extra = {}) {
  return {
    ...SECURITY_HEADERS,
    'X-Request-Id': requestId,
    ...extra,
  };
}

/** Builds a JSON response carrying security headers and the request ID. */
export function json(body, { status = 200, requestId, headers = {} } = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      ...baseHeaders(requestId, headers),
    },
  });
}

/**
 * Renders an error as an OpenAI-shaped error envelope.
 *
 * Anything that is not a GatewayError is treated as an unexpected exception and
 * collapsed to a generic 500 — raw exception text never reaches a client,
 * because it can carry file paths, URLs or credentials.
 */
export function errorJson(error, requestId, headers = {}) {
  const safe =
    error instanceof GatewayError
      ? error
      : new GatewayError(500, ERROR_TYPES.INTERNAL, 'Internal server error');

  const body = {
    error: {
      message: safe.message,
      type: safe.type,
      request_id: requestId,
    },
  };
  if (safe.param) body.error.param = safe.param;
  if (safe.code) body.error.code = safe.code;

  return json(body, {
    status: safe.status,
    requestId,
    headers: { ...safe.headers, ...headers },
  });
}
