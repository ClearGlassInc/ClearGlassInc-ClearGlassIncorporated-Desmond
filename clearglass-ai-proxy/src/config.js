/**
 * Configuration resolution and validation.
 *
 * Every tunable is read from the Worker environment — never from a request.
 * This module is the only place an upstream URL is decided, which is what keeps
 * the gateway from becoming an SSRF primitive or an open forwarder.
 *
 * Validation is fail-closed: an invalid value raises rather than silently
 * falling back to a permissive default.
 */

import { misconfigured } from './lib/errors.js';

export const SERVICE_NAME = 'clearglass-ai-proxy';
export const SERVICE_VERSION = '1.0.0';

/** Non-secret defaults. Safe to ship; every one can be overridden by [vars]. */
export const DEFAULTS = Object.freeze({
  PROVIDER: 'openai',
  OPENAI_BASE_URL: 'https://api.openai.com/v1',
  DEFAULT_MODEL: 'gpt-5-mini',
  RATE_LIMIT_PER_MINUTE: 30,
  MAX_REQUEST_BYTES: 32_768,
  MAX_OUTPUT_TOKENS: 2_048,
  MAX_MESSAGES: 64,
  MAX_COMPLETIONS: 4,
  UPSTREAM_TIMEOUT_MS: 30_000,
  MAX_OUTPUT_TOKENS_FIELD: 'max_completion_tokens',
  ALLOWED_ORIGIN: '',
  ALLOW_STREAMING: 'true',
});

/**
 * Shortest credential the gateway will accept.
 *
 * A short PROXY_ACCESS_TOKEN is functionally an open proxy, so this is enforced
 * at startup rather than documented and hoped for.
 */
export const MIN_TOKEN_LENGTH = 24;

const BOUNDS = Object.freeze({
  RATE_LIMIT_PER_MINUTE: { min: 1, max: 100_000 },
  MAX_REQUEST_BYTES: { min: 256, max: 5_000_000 },
  MAX_OUTPUT_TOKENS: { min: 1, max: 200_000 },
  MAX_MESSAGES: { min: 1, max: 1_000 },
  MAX_COMPLETIONS: { min: 1, max: 128 },
  UPSTREAM_TIMEOUT_MS: { min: 1_000, max: 120_000 },
});

const TOKEN_FIELDS = new Set(['max_tokens', 'max_completion_tokens', 'none']);

function readString(env, key) {
  const value = env?.[key];
  if (value === undefined || value === null) return '';
  return String(value).trim();
}

function readInt(env, key) {
  const raw = readString(env, key);
  if (raw === '') return DEFAULTS[key];

  // Number() rather than parseInt: "30abc" must be rejected, not silently 30.
  const value = Number(raw);
  if (!Number.isInteger(value)) {
    throw misconfigured('Gateway is not configured correctly', `${key} must be an integer`);
  }

  const bound = BOUNDS[key];
  if (bound && (value < bound.min || value > bound.max)) {
    throw misconfigured(
      'Gateway is not configured correctly',
      `${key} must be between ${bound.min} and ${bound.max}`,
    );
  }
  return value;
}

function readBool(env, key) {
  const raw = readString(env, key).toLowerCase() || String(DEFAULTS[key] ?? 'false');
  if (['1', 'true', 'yes', 'on'].includes(raw)) return true;
  if (['0', 'false', 'no', 'off'].includes(raw)) return false;
  throw misconfigured('Gateway is not configured correctly', `${key} must be a boolean`);
}

function readList(env, key) {
  return readString(env, key)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

/**
 * Validates and pins the upstream base URL.
 *
 * Requires HTTPS (so provider credentials are never sent in the clear) and
 * rejects embedded credentials. Plain HTTP is permitted only against loopback,
 * which is what `wrangler dev` against a local mock needs.
 */
export function parseBaseUrl(raw, key = 'OPENAI_BASE_URL') {
  let url;
  try {
    url = new URL(raw);
  } catch {
    throw misconfigured('Gateway is not configured correctly', `${key} is not a valid URL`);
  }

  const isLoopback = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && isLoopback)) {
    throw misconfigured(
      'Gateway is not configured correctly',
      `${key} must use https (http is allowed only for loopback)`,
    );
  }
  if (url.username || url.password) {
    throw misconfigured(
      'Gateway is not configured correctly',
      `${key} must not embed credentials`,
    );
  }
  if (url.search || url.hash) {
    throw misconfigured(
      'Gateway is not configured correctly',
      `${key} must not contain a query string or fragment`,
    );
  }

  // Normalise to a no-trailing-slash origin+path so path joining is predictable.
  const pathname = url.pathname.replace(/\/+$/, '');
  return `${url.origin}${pathname}`;
}

/**
 * Builds the immutable runtime configuration.
 *
 * @param {Record<string, unknown>} env Worker environment bindings.
 * @returns {Readonly<object>}
 */
export function resolveConfig(env = {}) {
  const provider = (readString(env, 'PROVIDER') || DEFAULTS.PROVIDER).toLowerCase();
  const baseUrl = parseBaseUrl(readString(env, 'OPENAI_BASE_URL') || DEFAULTS.OPENAI_BASE_URL);
  const defaultModel = readString(env, 'DEFAULT_MODEL') || DEFAULTS.DEFAULT_MODEL;

  // Fail closed: with no explicit allowlist, only the default model is reachable.
  // The operator opts models in deliberately rather than inheriting the whole
  // provider catalogue.
  const allowedModels = readList(env, 'ALLOWED_MODELS');
  const chatModels = allowedModels.length > 0 ? allowedModels : [defaultModel];

  // Embeddings stay disabled until models are named for them.
  const embeddingModels = readList(env, 'ALLOWED_EMBEDDING_MODELS');

  const maxOutputTokensField =
    readString(env, 'MAX_OUTPUT_TOKENS_FIELD') || DEFAULTS.MAX_OUTPUT_TOKENS_FIELD;
  if (!TOKEN_FIELDS.has(maxOutputTokensField)) {
    throw misconfigured(
      'Gateway is not configured correctly',
      `MAX_OUTPUT_TOKENS_FIELD must be one of ${[...TOKEN_FIELDS].join(', ')}`,
    );
  }

  const allowedOrigins = readList(env, 'ALLOWED_ORIGIN');

  return Object.freeze({
    service: SERVICE_NAME,
    version: SERVICE_VERSION,
    provider,
    baseUrl,
    defaultModel,
    chatModels: Object.freeze(chatModels),
    embeddingModels: Object.freeze(embeddingModels),
    embeddingsEnabled: embeddingModels.length > 0,
    allowedOrigins: Object.freeze(allowedOrigins),
    allowAnyOrigin: allowedOrigins.includes('*'),
    rateLimitPerMinute: readInt(env, 'RATE_LIMIT_PER_MINUTE'),
    maxRequestBytes: readInt(env, 'MAX_REQUEST_BYTES'),
    maxOutputTokens: readInt(env, 'MAX_OUTPUT_TOKENS'),
    maxMessages: readInt(env, 'MAX_MESSAGES'),
    maxCompletions: readInt(env, 'MAX_COMPLETIONS'),
    upstreamTimeoutMs: readInt(env, 'UPSTREAM_TIMEOUT_MS'),
    maxOutputTokensField,
    allowStreaming: readBool(env, 'ALLOW_STREAMING'),
  });
}

/**
 * Reads the access tokens the gateway will accept.
 *
 * Comma-separated to allow zero-downtime rotation: publish the new token
 * alongside the old, move clients, then drop the old one.
 *
 * @returns {string[]}
 */
export function resolveAccessTokens(env = {}) {
  const tokens = readList(env, 'PROXY_ACCESS_TOKEN');
  if (tokens.length === 0) {
    // No credential means every caller is anonymous. Refuse to serve rather
    // than run as an open proxy.
    throw misconfigured(
      'Gateway is not configured for authenticated access',
      'PROXY_ACCESS_TOKEN is not set',
    );
  }
  const weak = tokens.filter((token) => token.length < MIN_TOKEN_LENGTH);
  if (weak.length > 0) {
    throw misconfigured(
      'Gateway is not configured for authenticated access',
      `PROXY_ACCESS_TOKEN entries must be at least ${MIN_TOKEN_LENGTH} characters`,
    );
  }
  return tokens;
}

/** Reads the provider credential. Absent means the route is unavailable, not open. */
export function resolveProviderKey(env = {}) {
  const key = readString(env, 'OPENAI_API_KEY');
  if (!key) {
    throw misconfigured(
      'AI provider is not configured',
      'OPENAI_API_KEY is not set',
    );
  }
  return key;
}
