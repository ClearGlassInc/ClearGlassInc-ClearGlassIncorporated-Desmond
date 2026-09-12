/**
 * GET /health — liveness and readiness.
 *
 * Unauthenticated by design: deploy pipelines and uptime monitors need it
 * without holding a credential. It therefore reports booleans only. No URL,
 * model name, version of a dependency, or any value derived from a secret
 * appears here — readiness is a yes/no, not a configuration dump.
 */

import { resolveAccessTokens, resolveProviderKey } from '../config.js';
import { assertMethod } from '../middleware/security.js';
import { json } from '../lib/response.js';

function configured(reader, env) {
  try {
    reader(env);
    return true;
  } catch {
    return false;
  }
}

export function handleHealth(request, env, config, ctx) {
  assertMethod(request, ['GET', 'HEAD']);

  const authConfigured = configured(resolveAccessTokens, env);
  const providerConfigured = configured(resolveProviderKey, env);

  const body = {
    ok: true,
    service: config.service,
    version: config.version,
    timestamp: new Date().toISOString(),
    request_id: ctx.requestId,
    checks: {
      auth_configured: authConfigured,
      provider_configured: providerConfigured,
      // Reflects whether the deployment can actually serve traffic, which is
      // what a readiness probe needs to gate a rollout on.
      ready: authConfigured && providerConfigured,
    },
  };

  return json(body, { status: 200, requestId: ctx.requestId, headers: ctx.headers });
}
