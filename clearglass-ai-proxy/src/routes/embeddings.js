/**
 * POST /v1/embeddings — optional, disabled until models are allowlisted.
 *
 * The route stays absent rather than open: with no ALLOWED_EMBEDDING_MODELS set
 * it reports 404, so enabling embeddings is a deliberate act.
 */

import { resolveProviderKey } from '../config.js';
import { notFound } from '../lib/errors.js';
import { buildEmbeddingPayload } from '../lib/validation.js';
import { json } from '../lib/response.js';
import { assertMethod, readJsonBody } from '../middleware/security.js';
import { resolveProvider } from '../providers/provider-router.js';

export async function handleEmbeddings(request, env, config, ctx) {
  assertMethod(request, ['POST']);

  if (!config.embeddingsEnabled) {
    throw notFound('Embeddings are not enabled on this gateway');
  }

  const apiKey = resolveProviderKey(env);
  const provider = resolveProvider(config, apiKey);

  const body = await readJsonBody(request, config);
  const { payload, model } = buildEmbeddingPayload(body, config);

  ctx.model = model;
  ctx.provider = provider.id;

  const upstream = await provider.embeddings(payload);
  const result = await upstream.json();

  return json(result, { status: 200, requestId: ctx.requestId, headers: ctx.headers });
}
