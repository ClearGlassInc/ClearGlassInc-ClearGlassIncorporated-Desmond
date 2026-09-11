/**
 * Transport-level protections: CORS, method guards and request-size limits.
 */

import { badRequest, methodNotAllowed, payloadTooLarge } from '../lib/errors.js';
import { SECURITY_HEADERS } from '../lib/response.js';

const ALLOWED_REQUEST_HEADERS = 'Authorization, Content-Type, X-Request-Id';
const PREFLIGHT_MAX_AGE = '600';

/**
 * Decides the CORS headers for a request.
 *
 * Credentialed CORS is never combined with a wildcard origin: the pairing is
 * rejected by browsers and, where it is honoured, lets any site ride along on a
 * user's cookies. This gateway authenticates with a bearer token rather than
 * cookies, so `Allow-Credentials` is never emitted at all.
 *
 * @returns {Record<string,string>}
 */
export function resolveCors(request, config) {
  const origin = request.headers.get('Origin');

  if (config.allowAnyOrigin) {
    return {
      'Access-Control-Allow-Origin': '*',
      Vary: 'Origin',
    };
  }

  // Echo only an origin that is explicitly listed; anything else gets no CORS
  // headers, so the browser blocks the response.
  if (origin && config.allowedOrigins.includes(origin)) {
    return {
      'Access-Control-Allow-Origin': origin,
      Vary: 'Origin',
    };
  }

  return { Vary: 'Origin' };
}

/** Builds the CORS preflight response. */
export function preflightResponse(request, config, requestId) {
  const cors = resolveCors(request, config);

  return new Response(null, {
    status: 204,
    headers: {
      ...SECURITY_HEADERS,
      'X-Request-Id': requestId,
      ...cors,
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': ALLOWED_REQUEST_HEADERS,
      'Access-Control-Max-Age': PREFLIGHT_MAX_AGE,
    },
  });
}

/** Rejects any method the route does not implement. */
export function assertMethod(request, allowed) {
  if (!allowed.includes(request.method)) {
    throw methodNotAllowed(allowed);
  }
}

/**
 * Reads a request body under a hard byte ceiling.
 *
 * The declared Content-Length is checked first so an oversized request is
 * rejected before it is read, but the stream is also metered while it drains —
 * a chunked request can lie about, or simply omit, its length.
 */
export async function readBodyLimited(request, maxBytes) {
  const declared = request.headers.get('Content-Length');
  if (declared !== null) {
    const length = Number(declared);
    if (!Number.isFinite(length) || length < 0) {
      throw badRequest('Invalid Content-Length header');
    }
    if (length > maxBytes) {
      throw payloadTooLarge(maxBytes);
    }
  }

  if (!request.body) return '';

  const reader = request.body.getReader();
  const chunks = [];
  let total = 0;

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) {
        // Stop pulling bytes we have already decided to refuse.
        await reader.cancel();
        throw payloadTooLarge(maxBytes);
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }

  const merged = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.byteLength;
  }

  return new TextDecoder('utf-8', { fatal: false }).decode(merged);
}

/**
 * Reads and parses a JSON body.
 *
 * The Content-Type check is a CSRF control as much as a correctness one:
 * requiring application/json keeps a form POST from a hostile page off the
 * endpoint, since forms cannot set that type.
 */
export async function readJsonBody(request, config) {
  const contentType = request.headers.get('Content-Type') || '';
  if (!contentType.toLowerCase().includes('application/json')) {
    throw badRequest('Content-Type must be application/json');
  }

  const raw = await readBodyLimited(request, config.maxRequestBytes);
  if (raw.trim() === '') {
    throw badRequest('Request body is empty');
  }

  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    // The parser message can echo body content; report the shape only.
    throw badRequest('Request body is not valid JSON');
  }

  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw badRequest('Request body must be a JSON object');
  }

  return parsed;
}
