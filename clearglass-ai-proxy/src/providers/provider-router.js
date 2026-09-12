/**
 * Provider selection.
 *
 * The gateway targets the OpenAI-compatible request/response shape, so most
 * providers are a configuration change rather than a code change: point
 * OPENAI_BASE_URL at the provider and supply its key. This registry is the seam
 * for the cases that genuinely need different wire behaviour — register a
 * factory returning the same `{ chatCompletions, embeddings }` interface and
 * select it with the PROVIDER variable, and no routing or middleware changes.
 */

import { misconfigured } from '../lib/errors.js';
import { createOpenAIAdapter } from './openai.js';

/** provider id -> factory(config, apiKey) => adapter */
const REGISTRY = new Map([
  ['openai', createOpenAIAdapter],
  // Same wire format, different host. Named separately so deployments can be
  // explicit about what they are pointed at.
  ['openai-compatible', createOpenAIAdapter],
]);

/** Provider ids this build can serve. */
export function supportedProviders() {
  return [...REGISTRY.keys()];
}

/**
 * Resolves the adapter for the configured provider.
 *
 * @param {Readonly<object>} config
 * @param {string} apiKey
 */
export function resolveProvider(config, apiKey) {
  const factory = REGISTRY.get(config.provider);
  if (!factory) {
    throw misconfigured(
      'AI provider is not configured',
      `unknown PROVIDER "${config.provider}"`,
    );
  }
  return factory(config, apiKey);
}
