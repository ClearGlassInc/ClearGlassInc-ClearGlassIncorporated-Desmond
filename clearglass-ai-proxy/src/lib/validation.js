/**
 * Payload validation.
 *
 * The gateway forwards an allowlist of parameters, never the caller's object.
 * That is the control that stops a client from smuggling provider-specific or
 * future fields through the proxy, and it keeps request cost bounded.
 */

import { badRequest, forbidden } from './errors.js';

/** Roles accepted in a chat message. */
const ROLES = new Set(['system', 'developer', 'user', 'assistant', 'tool', 'function']);

/** Parameters copied through to the provider on /v1/chat/completions. */
export const CHAT_PARAM_ALLOWLIST = Object.freeze([
  'model',
  'messages',
  'temperature',
  'top_p',
  'n',
  'stream',
  'stream_options',
  'stop',
  'max_tokens',
  'max_completion_tokens',
  'presence_penalty',
  'frequency_penalty',
  'seed',
  'response_format',
  'tools',
  'tool_choice',
  'parallel_tool_calls',
  'reasoning_effort',
  'logprobs',
  'top_logprobs',
  'user',
]);

/** Parameters copied through on /v1/embeddings. */
export const EMBEDDING_PARAM_ALLOWLIST = Object.freeze([
  'model',
  'input',
  'encoding_format',
  'dimensions',
  'user',
]);

/** Numeric parameters and their accepted ranges. */
const NUMERIC_RANGES = Object.freeze({
  temperature: { min: 0, max: 2 },
  top_p: { min: 0, max: 1 },
  presence_penalty: { min: -2, max: 2 },
  frequency_penalty: { min: -2, max: 2 },
  top_logprobs: { min: 0, max: 20, integer: true },
  dimensions: { min: 1, max: 16_384, integer: true },
});

/** Validates the model against the allowlist for a route. */
export function assertModelAllowed(model, allowed, fallback) {
  const requested = model === undefined || model === null ? fallback : model;

  if (typeof requested !== 'string' || requested.trim() === '') {
    throw badRequest('"model" must be a non-empty string', 'model');
  }

  if (!allowed.includes(requested)) {
    // 403, not 404: the model may well exist upstream — this deployment simply
    // does not permit it. The allowlist itself is not disclosed here.
    throw forbidden(`Model "${requested}" is not permitted by this gateway`);
  }

  return requested;
}

function assertNumericRanges(payload) {
  for (const [field, range] of Object.entries(NUMERIC_RANGES)) {
    if (payload[field] === undefined) continue;

    const value = payload[field];
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      throw badRequest(`"${field}" must be a finite number`, field);
    }
    if (range.integer && !Number.isInteger(value)) {
      throw badRequest(`"${field}" must be an integer`, field);
    }
    if (value < range.min || value > range.max) {
      throw badRequest(`"${field}" must be between ${range.min} and ${range.max}`, field);
    }
  }
}

/** Validates the `messages` array. */
export function assertMessages(messages, config) {
  if (!Array.isArray(messages)) {
    throw badRequest('"messages" must be an array', 'messages');
  }
  if (messages.length === 0) {
    throw badRequest('"messages" must contain at least one message', 'messages');
  }
  if (messages.length > config.maxMessages) {
    throw badRequest(
      `"messages" must contain at most ${config.maxMessages} messages`,
      'messages',
    );
  }

  messages.forEach((message, index) => {
    if (message === null || typeof message !== 'object' || Array.isArray(message)) {
      throw badRequest(`messages[${index}] must be an object`, 'messages');
    }
    if (!ROLES.has(message.role)) {
      throw badRequest(
        `messages[${index}].role must be one of ${[...ROLES].join(', ')}`,
        'messages',
      );
    }

    const { content } = message;
    const hasToolCalls = Array.isArray(message.tool_calls) && message.tool_calls.length > 0;

    // An assistant turn that only issues tool calls legitimately carries no
    // content; every other message must say something.
    if (content === undefined || content === null) {
      if (message.role === 'assistant' && hasToolCalls) return;
      throw badRequest(`messages[${index}].content is required`, 'messages');
    }
    if (typeof content !== 'string' && !Array.isArray(content)) {
      throw badRequest(
        `messages[${index}].content must be a string or an array of content parts`,
        'messages',
      );
    }
    if (typeof content === 'string' && content.length === 0 && !hasToolCalls) {
      throw badRequest(`messages[${index}].content must not be empty`, 'messages');
    }
  });
}

/**
 * Validates and clamps output-token limits.
 *
 * A caller may request fewer tokens than the ceiling but never more, and a
 * request that names no limit has the ceiling applied — otherwise an unbounded
 * generation is billable to this deployment.
 */
export function applyOutputTokenLimit(source, target, config) {
  let declared = false;

  for (const field of ['max_tokens', 'max_completion_tokens']) {
    const value = source[field];
    if (value === undefined || value === null) continue;

    if (!Number.isInteger(value) || value < 1) {
      throw badRequest(`"${field}" must be a positive integer`, field);
    }
    if (value > config.maxOutputTokens) {
      throw badRequest(
        `"${field}" must not exceed ${config.maxOutputTokens}`,
        field,
      );
    }
    target[field] = value;
    declared = true;
  }

  if (!declared && config.maxOutputTokensField !== 'none') {
    target[config.maxOutputTokensField] = config.maxOutputTokens;
  }
}

/** Validates `stream` and `n`, both of which multiply cost or change framing. */
function assertStreamAndCompletions(payload, config) {
  if (payload.stream !== undefined) {
    if (typeof payload.stream !== 'boolean') {
      throw badRequest('"stream" must be a boolean', 'stream');
    }
    if (payload.stream && !config.allowStreaming) {
      throw forbidden('Streaming is disabled on this gateway');
    }
  }

  if (payload.n !== undefined) {
    if (!Number.isInteger(payload.n) || payload.n < 1) {
      throw badRequest('"n" must be a positive integer', 'n');
    }
    if (payload.n > config.maxCompletions) {
      throw badRequest(`"n" must not exceed ${config.maxCompletions}`, 'n');
    }
  }
}

/** Copies allowlisted fields from a validated payload. */
function pick(payload, allowlist) {
  const result = {};
  for (const key of allowlist) {
    if (payload[key] !== undefined) result[key] = payload[key];
  }
  return result;
}

/**
 * Validates a chat completion request and returns the payload to forward.
 *
 * @returns {{ payload: object, model: string, stream: boolean }}
 */
export function buildChatPayload(body, config) {
  assertMessages(body.messages, config);
  assertNumericRanges(body);
  assertStreamAndCompletions(body, config);

  const model = assertModelAllowed(body.model, config.chatModels, config.defaultModel);

  const payload = pick(body, CHAT_PARAM_ALLOWLIST);
  payload.model = model;

  // Rebuilt after pick() so a caller-supplied value can never exceed the cap.
  delete payload.max_tokens;
  delete payload.max_completion_tokens;
  applyOutputTokenLimit(body, payload, config);

  return { payload, model, stream: body.stream === true };
}

/**
 * Validates an embeddings request and returns the payload to forward.
 *
 * @returns {{ payload: object, model: string }}
 */
export function buildEmbeddingPayload(body, config) {
  assertNumericRanges(body);

  const { input } = body;
  if (input === undefined || input === null) {
    throw badRequest('"input" is required', 'input');
  }

  const isString = typeof input === 'string' && input.length > 0;
  const isStringArray =
    Array.isArray(input) &&
    input.length > 0 &&
    input.length <= config.maxMessages &&
    input.every((item) => typeof item === 'string' && item.length > 0);

  if (!isString && !isStringArray) {
    throw badRequest(
      `"input" must be a non-empty string or an array of at most ${config.maxMessages} non-empty strings`,
      'input',
    );
  }

  const model = assertModelAllowed(body.model, config.embeddingModels, config.embeddingModels[0]);

  const payload = pick(body, EMBEDDING_PARAM_ALLOWLIST);
  payload.model = model;

  return { payload, model };
}
