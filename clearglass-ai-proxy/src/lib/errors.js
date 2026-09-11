/**
 * Structured, client-safe errors.
 *
 * Every error surfaced to a client is constructed here. The `message` on a
 * GatewayError is the text that reaches the caller, so it must never be built
 * from an upstream response body, an exception string, or anything derived from
 * a secret. Internal detail travels in `logDetail`, which is logged and dropped.
 */

export const ERROR_TYPES = Object.freeze({
  INVALID_REQUEST: 'invalid_request_error',
  AUTHENTICATION: 'authentication_error',
  PERMISSION: 'permission_error',
  NOT_FOUND: 'not_found_error',
  RATE_LIMIT: 'rate_limit_error',
  PAYLOAD_TOO_LARGE: 'payload_too_large_error',
  UPSTREAM: 'upstream_error',
  TIMEOUT: 'timeout_error',
  CONFIGURATION: 'configuration_error',
  INTERNAL: 'internal_error',
});

export class GatewayError extends Error {
  /**
   * @param {number} status HTTP status to return.
   * @param {string} type One of ERROR_TYPES.
   * @param {string} message Client-safe message. Never interpolate secrets.
   * @param {{ headers?: Record<string,string>, logDetail?: string, param?: string, code?: string }} [options]
   */
  constructor(status, type, message, options = {}) {
    super(message);
    this.name = 'GatewayError';
    this.status = status;
    this.type = type;
    this.headers = options.headers || {};
    // Never serialised into a response; for structured logs only.
    this.logDetail = options.logDetail || '';
    this.param = options.param;
    // Optional machine-readable hint (e.g. a sanitised upstream error code).
    this.code = options.code;
  }
}

export const badRequest = (message, param) =>
  new GatewayError(400, ERROR_TYPES.INVALID_REQUEST, message, { param });

export const unauthorized = (message = 'Missing or invalid credentials', logDetail = '') =>
  new GatewayError(401, ERROR_TYPES.AUTHENTICATION, message, {
    // Signals the scheme without hinting at token validity.
    headers: { 'WWW-Authenticate': 'Bearer realm="clearglass-ai-proxy"' },
    logDetail,
  });

export const forbidden = (message) =>
  new GatewayError(403, ERROR_TYPES.PERMISSION, message);

export const notFound = (message = 'Unknown endpoint') =>
  new GatewayError(404, ERROR_TYPES.NOT_FOUND, message);

export const methodNotAllowed = (allowed) =>
  new GatewayError(405, ERROR_TYPES.INVALID_REQUEST, 'Method not allowed', {
    headers: { Allow: allowed.join(', ') },
  });

export const payloadTooLarge = (maxBytes) =>
  new GatewayError(
    413,
    ERROR_TYPES.PAYLOAD_TOO_LARGE,
    `Request body exceeds the ${maxBytes} byte limit`,
  );

export const tooManyRequests = (retryAfterSeconds, limit) =>
  new GatewayError(429, ERROR_TYPES.RATE_LIMIT, 'Rate limit exceeded', {
    headers: {
      'Retry-After': String(retryAfterSeconds),
      'X-RateLimit-Limit': String(limit),
      'X-RateLimit-Remaining': '0',
    },
  });

export const misconfigured = (message, logDetail = '') =>
  new GatewayError(503, ERROR_TYPES.CONFIGURATION, message, { logDetail });

export const upstreamFailure = (status, logDetail = '', extra = {}) =>
  new GatewayError(status, ERROR_TYPES.UPSTREAM, 'AI provider request failed', {
    logDetail,
    ...extra,
  });

export const upstreamTimeout = () =>
  new GatewayError(504, ERROR_TYPES.TIMEOUT, 'AI provider request timed out');
