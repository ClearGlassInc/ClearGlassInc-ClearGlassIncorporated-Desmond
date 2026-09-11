/**
 * GET /v1/models — the models this gateway permits.
 *
 * Answered from the allowlist rather than by proxying the provider's catalogue.
 * Two reasons: a caller learns exactly what this deployment will accept (the
 * upstream list would advertise models that the gateway rejects with 403), and
 * the provider's account-scoped catalogue is not disclosed.
 */

import { assertMethod } from '../middleware/security.js';
import { json } from '../lib/response.js';

export function handleModels(request, env, config, ctx) {
  assertMethod(request, ['GET', 'HEAD']);

  const data = config.chatModels.map((id) => ({
    id,
    object: 'model',
    owned_by: config.provider,
  }));

  const embeddings = config.embeddingModels.map((id) => ({
    id,
    object: 'model',
    owned_by: config.provider,
  }));

  return json(
    { object: 'list', data: [...data, ...embeddings] },
    { status: 200, requestId: ctx.requestId, headers: ctx.headers },
  );
}
