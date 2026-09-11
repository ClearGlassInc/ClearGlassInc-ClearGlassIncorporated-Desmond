/**
 * Bearer-token authentication for protected routes.
 */

import { resolveAccessTokens } from '../config.js';
import { unauthorized } from '../lib/errors.js';

const encoder = new TextEncoder();

async function sha256(value) {
  const digest = await crypto.subtle.digest('SHA-256', encoder.encode(value));
  return new Uint8Array(digest);
}

/**
 * Compares two secrets without leaking their contents through timing.
 *
 * Both sides are hashed first, so the loop always runs over 32 fixed-width
 * bytes. A naive `a === b` — or any length-sensitive compare — lets an attacker
 * recover a token byte by byte from response latency.
 */
export async function constantTimeEquals(a, b) {
  const [left, right] = await Promise.all([sha256(a), sha256(b)]);
  let difference = 0;
  for (let i = 0; i < left.length; i += 1) {
    difference |= left[i] ^ right[i];
  }
  return difference === 0;
}

/**
 * Derives a short, non-reversible identifier for logs and rate-limit keys.
 *
 * This is what makes per-credential accounting possible without ever writing a
 * token into a log line.
 */
export async function tokenFingerprint(token) {
  const digest = await sha256(token);
  return [...digest]
    .slice(0, 6)
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

/** Extracts the credential from an `Authorization: Bearer <token>` header. */
export function parseBearer(request) {
  const header = request.headers.get('Authorization');
  if (!header) return null;

  const match = /^Bearer[ ]+(.+)$/i.exec(header.trim());
  if (!match) return null;

  const token = match[1].trim();
  return token === '' ? null : token;
}

/**
 * Authenticates a request.
 *
 * Throws 401 for a missing or unrecognised credential and 503 when no token is
 * configured at all — an unconfigured gateway refuses traffic instead of
 * serving it anonymously.
 *
 * @returns {Promise<{ tokenId: string }>}
 */
export async function authenticate(request, env) {
  // Raises a configuration error if PROXY_ACCESS_TOKEN is unset or too weak.
  const accepted = resolveAccessTokens(env);

  const presented = parseBearer(request);
  if (!presented) {
    throw unauthorized('Missing or invalid credentials', 'no bearer token presented');
  }

  // Every candidate is compared, so the response time does not reveal which
  // token matched or how far down the list it sat.
  const results = await Promise.all(
    accepted.map((candidate) => constantTimeEquals(presented, candidate)),
  );

  if (!results.some(Boolean)) {
    throw unauthorized('Missing or invalid credentials', 'bearer token not recognised');
  }

  return { tokenId: await tokenFingerprint(presented) };
}
