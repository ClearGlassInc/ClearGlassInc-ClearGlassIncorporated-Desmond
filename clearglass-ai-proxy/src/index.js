/**
 * ClearGlass AI Gateway — Cloudflare Worker entry point.
 *
 * Pipeline, in order:
 *
 *   client -> CORS/preflight -> route match -> rate limit -> authentication
 *          -> request validation -> provider adapter -> upstream
 *          -> response -> client
 *
 * Rate limiting runs before authentication on purpose: an unauthenticated
 * caller must not get unlimited attempts at guessing the access token.
 */

import { resolveConfig } from './config.js';
import { GatewayError } from './lib/errors.js';
import { notFound } from './lib/errors.js';
import { hashIdentifier, logRequest } from './lib/log.js';
import { errorJson, newRequestId } from './lib/response.js';
import { authenticate } from './middleware/authentication.js';
import { clientIp, enforceRateLimit, rateLimitHeaders } from './middleware/rate-limit.js';
import { preflightResponse, resolveCors } from './middleware/security.js';
import { handleChat } from './routes/chat.js';
import { handleEmbeddings } from './routes/embeddings.js';
import { handleHealth } from './routes/health.js';
import { handleModels } from './routes/models.js';

/**
 * Route table.
 *
 * `auth: false` is an explicit, reviewable property rather than an omission, so
 * a new route cannot become public by forgetting to guard it.
 */
const ROUTES = [
  { path: '/health', auth: false, handler: handleHealth },
  { path: '/v1/chat/completions', auth: true, handler: handleChat },
  { path: '/v1/models', auth: true, handler: handleModels },
  { path: '/v1/embeddings', auth: true, handler: handleEmbeddings },
];

/** Normalises a path so `/health/` and `/health` resolve identically. */
function normalizePath(pathname) {
  if (pathname.length > 1 && pathname.endsWith('/')) {
    return pathname.replace(/\/+$/, '') || '/';
  }
  return pathname;
}

function matchRoute(pathname) {
  const path = normalizePath(pathname);
  return ROUTES.find((route) => route.path === path);
}

export default {
  /**
   * @param {Request} request
   * @param {Record<string, unknown>} env
   * @param {{ waitUntil?: Function }} _executionContext
   */
  async fetch(request, env, _executionContext) {
    const startedAt = Date.now();
    const requestId = newRequestId();
    const url = new URL(request.url);
    const route = normalizePath(url.pathname);

    // Per-request state shared with handlers: the response headers they must
    // carry, plus fields they fill in for the access log.
    const ctx = { requestId, headers: {}, model: '', provider: '', tokenId: '' };

    let config;
    try {
      config = resolveConfig(env);
    } catch (error) {
      // Invalid configuration: refuse traffic rather than serve with defaults.
      logRequest({
        request_id: requestId,
        route,
        method: request.method,
        status: 503,
        latency_ms: Date.now() - startedAt,
        error_type: 'configuration_error',
        outcome: 'rejected',
        detail: error?.logDetail || 'configuration invalid',
      });
      return errorJson(error, requestId);
    }

    const cors = resolveCors(request, config);
    ctx.headers = { ...cors };

    if (request.method === 'OPTIONS') {
      logRequest({
        request_id: requestId,
        route,
        method: 'OPTIONS',
        status: 204,
        latency_ms: Date.now() - startedAt,
        outcome: 'preflight',
      });
      return preflightResponse(request, config, requestId);
    }

    const ip = clientIp(request);
    let status = 500;
    let errorType = '';
    let detail = '';

    try {
      const matched = matchRoute(url.pathname);
      if (!matched) {
        throw notFound();
      }

      // Keyed on IP and enforced pre-auth, so token guessing is throttled.
      const ipLimit = await enforceRateLimit(`ip:${ip}:${route}`, env, config);
      ctx.headers = { ...ctx.headers, ...rateLimitHeaders(ipLimit, config) };

      if (matched.auth) {
        const { tokenId } = await authenticate(request, env);
        ctx.tokenId = tokenId;

        // A second bucket per credential: one token cannot spread its load
        // across many source addresses to exceed the intended ceiling.
        const tokenLimit = await enforceRateLimit(`tok:${tokenId}:${route}`, env, config);
        ctx.headers = { ...ctx.headers, ...rateLimitHeaders(tokenLimit, config) };
      }

      const response = await matched.handler(request, env, config, ctx);
      status = response.status;
      return response;
    } catch (error) {
      const gatewayError = error instanceof GatewayError ? error : null;
      status = gatewayError?.status ?? 500;
      errorType = gatewayError?.type ?? 'internal_error';

      // Unexpected exceptions are logged by name only. The message can carry a
      // URL or a credential fragment and must not be persisted or returned.
      detail = gatewayError?.logDetail || (gatewayError ? '' : `unhandled ${error?.name || 'Error'}`);

      return errorJson(error, requestId, ctx.headers);
    } finally {
      logRequest({
        request_id: requestId,
        route,
        method: request.method,
        status,
        latency_ms: Date.now() - startedAt,
        model: ctx.model,
        provider: ctx.provider,
        token_id: ctx.tokenId,
        client_ip_hash: await hashIdentifier(ip),
        error_type: errorType,
        outcome: status < 400 ? 'ok' : 'error',
        detail,
      });
    }
  },
};
