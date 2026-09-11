/**
 * Shared test harness.
 *
 * The Worker is exercised through its real `fetch(request, env, ctx)` export,
 * so tests cover the actual routing, middleware and error paths rather than
 * re-implementing them.
 */

import worker from '../src/index.js';
import { resetRateLimiter } from '../src/middleware/rate-limit.js';

/** At least MIN_TOKEN_LENGTH (24) characters, as the gateway requires. */
export const TEST_TOKEN = 'test-proxy-token-0123456789abcdef';
// Deliberately not 'sk-'-shaped. The public-artifact credential scanner
// (tests/test_public_artifact_security.py) flags /sk-[A-Za-z0-9_-]{20,}/ in a
// public repo, and a fixture that looks like a real provider key trips it.
export const TEST_API_KEY = 'test-provider-key-DO-NOT-USE';

/**
 * Baseline environment. Rate limits are set high so unrelated tests are not
 * throttled; the rate-limit suite overrides this.
 */
export function makeEnv(overrides = {}) {
  return {
    OPENAI_API_KEY: TEST_API_KEY,
    PROXY_ACCESS_TOKEN: TEST_TOKEN,
    OPENAI_BASE_URL: 'https://api.openai.com/v1',
    DEFAULT_MODEL: 'gpt-5-mini',
    ALLOWED_MODELS: 'gpt-5-mini,gpt-4o-mini',
    ALLOWED_ORIGIN: 'https://clearglassinc.com',
    RATE_LIMIT_PER_MINUTE: '1000',
    ...overrides,
  };
}

/**
 * Drives one request through the Worker.
 *
 * `rawBody` bypasses JSON.stringify so malformed-payload cases can be tested.
 */
export async function call(path, options = {}) {
  const {
    method = 'GET',
    body,
    rawBody,
    headers = {},
    env = makeEnv(),
    token,
    origin,
    contentType = 'application/json',
    ip = '203.0.113.10',
  } = options;

  const requestHeaders = new Headers(headers);
  if (token) requestHeaders.set('Authorization', `Bearer ${token}`);
  if (origin) requestHeaders.set('Origin', origin);
  if (!requestHeaders.has('CF-Connecting-IP')) requestHeaders.set('CF-Connecting-IP', ip);

  const payload = rawBody !== undefined ? rawBody : body !== undefined ? JSON.stringify(body) : undefined;
  if (payload !== undefined && !requestHeaders.has('Content-Type') && contentType !== null) {
    requestHeaders.set('Content-Type', contentType);
  }

  const request = new Request(`https://gateway.example${path}`, {
    method,
    headers: requestHeaders,
    body: payload,
  });

  const response = await worker.fetch(request, env, { waitUntil() {} });
  return response;
}

/** Convenience: drives a request and parses the JSON response. */
export async function callJson(path, options = {}) {
  const response = await call(path, options);
  const text = await response.text();
  let json = null;
  try {
    json = JSON.parse(text);
  } catch {
    json = null;
  }
  return { response, status: response.status, json, text };
}

/**
 * Replaces global fetch so no test can reach the network.
 *
 * Returns a record of every outbound call, which lets tests assert on the
 * upstream URL and headers — the checks that prove the provider key is sent
 * only upstream and that the URL is never client-controlled.
 */
export function stubUpstream(handler) {
  const original = globalThis.fetch;
  const calls = [];

  globalThis.fetch = async (url, init = {}) => {
    const record = {
      url: String(url),
      method: init.method,
      headers: new Headers(init.headers || {}),
      body: init.body ? JSON.parse(init.body) : null,
    };
    calls.push(record);
    return handler(record, init);
  };

  return {
    calls,
    restore() {
      globalThis.fetch = original;
    },
  };
}

/** Builds a plausible OpenAI-shaped chat completion. */
export function chatCompletionBody(overrides = {}) {
  return {
    id: 'chatcmpl-test',
    object: 'chat.completion',
    created: 1_700_000_000,
    model: 'gpt-5-mini',
    choices: [
      { index: 0, message: { role: 'assistant', content: 'Hello from ClearGlass' }, finish_reason: 'stop' },
    ],
    usage: { prompt_tokens: 8, completion_tokens: 5, total_tokens: 13 },
    ...overrides,
  };
}

export function jsonUpstream(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * Captures console output for the duration of a block.
 *
 * Used both to keep test output readable and to assert that no secret ever
 * reaches the log stream.
 */
export async function captureLogs(fn) {
  const lines = [];
  const originalLog = console.log;
  const originalError = console.error;

  console.log = (...args) => lines.push(args.join(' '));
  console.error = (...args) => lines.push(args.join(' '));

  try {
    const result = await fn();
    return { result, lines };
  } finally {
    console.log = originalLog;
    console.error = originalError;
  }
}

/** Silences the access log for a whole suite. */
export function silenceLogs() {
  const originalLog = console.log;
  const originalError = console.error;
  console.log = () => {};
  console.error = () => {};
  return () => {
    console.log = originalLog;
    console.error = originalError;
  };
}

export { resetRateLimiter };

/** Minimal valid chat request body. */
export const VALID_CHAT_REQUEST = {
  model: 'gpt-5-mini',
  messages: [{ role: 'user', content: 'Hello from ClearGlass' }],
};
