/**
 * POST /v1/chat/completions — the primary endpoint.
 *
 * Accepts an OpenAI-compatible request and returns the provider's
 * OpenAI-compatible response, including SSE when streaming is requested.
 */

import { resolveProviderKey } from '../config.js';
import { buildChatPayload } from '../lib/validation.js';
import { json } from '../lib/response.js';
import { SECURITY_HEADERS } from '../lib/response.js';
import { assertMethod, readJsonBody } from '../middleware/security.js';
import { resolveProvider } from '../providers/provider-router.js';

/**
 * Streams the upstream SSE body straight through.
 *
 * The body is passed by reference rather than buffered, so the first token
 * reaches the client as soon as the provider emits it. Only the headers the
 * gateway controls are set; upstream headers are dropped, since they can carry
 * provider request IDs, rate-limit counters and organisation identifiers.
 */
function streamResponse(upstream, ctx) {
  return new Response(upstream.body, {
    status: 200,
    headers: {
      ...SECURITY_HEADERS,
      'Content-Type': 'text/event-stream; charset=utf-8',
      'X-Request-Id': ctx.requestId,
      // Defeats buffering by any intermediary that would otherwise hold the
      // stream until it completes.
      'X-Accel-Buffering': 'no',
      Connection: 'keep-alive',
      ...ctx.headers,
    },
  });
}

export async function handleChat(request, env, config, ctx) {
  assertMethod(request, ['POST']);

  // Raises 503 when the provider credential is absent, before any body is read.
  const apiKey = resolveProviderKey(env);
  const provider = resolveProvider(config, apiKey);

  const body = await readJsonBody(request, config);
  const { payload, model, stream } = buildChatPayload(body, config);

  // Recorded for the access log regardless of how the request resolves.
  ctx.model = model;
  ctx.provider = provider.id;

  const upstream = await provider.chatCompletions(payload, { stream });

  if (stream) {
    return streamResponse(upstream, ctx);
  }

  const completion = await upstream.json();
  return json(completion, { status: 200, requestId: ctx.requestId, headers: ctx.headers });
}
