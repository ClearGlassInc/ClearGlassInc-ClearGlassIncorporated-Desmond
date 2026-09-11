/**
 * OpenAI-compatible provider adapter.
 *
 * This is the only module that performs an outbound request. The upstream URL
 * is composed from the validated base URL in configuration plus a fixed,
 * hard-coded path constant — no part of it is derived from the client request,
 * which is what prevents the gateway from being used to reach arbitrary hosts.
 */

import { upstreamFailure, upstreamTimeout } from '../lib/errors.js';

/** Fixed upstream paths. Never assembled from user input. */
export const UPSTREAM_PATHS = Object.freeze({
  chat: '/chat/completions',
  embeddings: '/embeddings',
});

/**
 * Maps an upstream status onto the status the client should see.
 *
 * A provider 401 means *our* credential is bad, not the caller's; returning 401
 * would tell the caller to re-present their token and would confuse a bad
 * OPENAI_API_KEY with a bad PROXY_ACCESS_TOKEN. It surfaces as 502.
 */
export function mapUpstreamStatus(status) {
  if (status === 429) return 429;
  if (status === 400 || status === 404 || status === 422) return 400;
  if (status === 408 || status === 504) return 504;
  return 502;
}

/**
 * Extracts a machine-readable hint from an upstream error body.
 *
 * Only the `type` and `code` fields are read, and only when they are short,
 * simple strings. The upstream `message` is deliberately discarded: provider
 * error text has been known to echo request headers and URLs.
 */
export async function sanitizeUpstreamError(response) {
  try {
    const body = await response.json();
    const error = body?.error;
    if (!error || typeof error !== 'object') return {};

    const safe = {};
    for (const field of ['type', 'code']) {
      const value = error[field];
      if (typeof value === 'string' && value.length > 0 && value.length <= 64 &&
          /^[a-z0-9_.-]+$/i.test(value)) {
        safe[field] = value;
      }
    }
    return safe;
  } catch {
    // A non-JSON or truncated error body tells us nothing safe to forward.
    return {};
  }
}

/**
 * Builds an adapter bound to one provider configuration.
 *
 * @param {Readonly<object>} config
 * @param {string} apiKey Provider credential, from a Worker secret.
 */
export function createOpenAIAdapter(config, apiKey) {
  async function call(path, payload, { stream = false } = {}) {
    const url = `${config.baseUrl}${path}`;

    let response;
    try {
      response = await fetch(url, {
        method: 'POST',
        headers: {
          // The provider credential is attached here and nowhere else. It is
          // never copied from, or reflected back into, the client exchange.
          Authorization: `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
          Accept: stream ? 'text/event-stream' : 'application/json',
          'User-Agent': `${config.service}/${config.version}`,
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(config.upstreamTimeoutMs),
      });
    } catch (error) {
      // TimeoutError is what AbortSignal.timeout raises; AbortError covers
      // runtimes that surface the older name.
      if (error?.name === 'TimeoutError' || error?.name === 'AbortError') {
        throw upstreamTimeout();
      }
      // Network-level failure: the message can contain the upstream host, so it
      // is logged rather than returned.
      throw upstreamFailure(502, `upstream fetch failed: ${error?.name || 'unknown'}`);
    }

    if (!response.ok) {
      const hint = await sanitizeUpstreamError(response.clone());
      throw upstreamFailure(mapUpstreamStatus(response.status), `upstream status ${response.status}`, {
        code: hint.code || hint.type,
      });
    }

    return response;
  }

  return Object.freeze({
    id: 'openai',

    /** @returns {Promise<Response>} The raw upstream response. */
    chatCompletions(payload, options) {
      return call(UPSTREAM_PATHS.chat, payload, options);
    },

    /** @returns {Promise<Response>} The raw upstream response. */
    embeddings(payload) {
      return call(UPSTREAM_PATHS.embeddings, payload);
    },
  });
}
