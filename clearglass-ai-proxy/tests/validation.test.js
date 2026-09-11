import { after, before, beforeEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  TEST_TOKEN,
  VALID_CHAT_REQUEST,
  callJson,
  chatCompletionBody,
  jsonUpstream,
  makeEnv,
  resetRateLimiter,
  silenceLogs,
  stubUpstream,
} from './helpers.js';

describe('request validation', () => {
  let restoreLogs;
  let upstream;

  before(() => {
    restoreLogs = silenceLogs();
  });
  after(() => restoreLogs());

  beforeEach(() => {
    resetRateLimiter();
    upstream = stubUpstream(() => jsonUpstream(chatCompletionBody()));
  });

  const post = (options = {}) =>
    callJson('/v1/chat/completions', { method: 'POST', token: TEST_TOKEN, ...options });

  it('rejects a non-POST method with an Allow header', async () => {
    const { status, response } = await post({ method: 'GET', body: undefined });

    assert.equal(status, 405);
    assert.equal(response.headers.get('Allow'), 'POST');
    assert.equal(upstream.calls.length, 0);
  });

  it('rejects malformed JSON without echoing the body', async () => {
    const { status, json, text } = await post({ rawBody: '{"messages": [' });

    assert.equal(status, 400);
    assert.equal(json.error.type, 'invalid_request_error');
    assert.equal(json.error.message, 'Request body is not valid JSON');
    assert.doesNotMatch(text, /messages": \[/);
    assert.equal(upstream.calls.length, 0);
  });

  it('rejects a non-JSON Content-Type', async () => {
    const { status, json } = await post({
      rawBody: JSON.stringify(VALID_CHAT_REQUEST),
      contentType: 'text/plain',
      headers: { 'Content-Type': 'text/plain' },
    });

    assert.equal(status, 400);
    assert.match(json.error.message, /Content-Type must be application\/json/);
  });

  it('rejects an empty body', async () => {
    const { status, json } = await post({ rawBody: '' });

    assert.equal(status, 400);
    assert.match(json.error.message, /empty/i);
  });

  it('rejects a JSON array or scalar at the top level', async () => {
    for (const raw of ['[]', '"hello"', '42', 'null']) {
      const { status } = await post({ rawBody: raw });
      assert.equal(status, 400, `expected 400 for body: ${raw}`);
    }
  });

  it('rejects a missing messages field', async () => {
    const { status, json } = await post({ body: { model: 'gpt-5-mini' } });

    assert.equal(status, 400);
    assert.equal(json.error.param, 'messages');
    assert.equal(upstream.calls.length, 0);
  });

  it('rejects an empty or non-array messages field', async () => {
    for (const messages of [[], 'hello', {}, 42]) {
      const { status } = await post({ body: { model: 'gpt-5-mini', messages } });
      assert.equal(status, 400, `expected 400 for messages: ${JSON.stringify(messages)}`);
    }
  });

  it('rejects malformed message entries', async () => {
    const cases = [
      [{ role: 'wizard', content: 'hi' }],
      [{ content: 'no role' }],
      [{ role: 'user' }],
      [{ role: 'user', content: 42 }],
      [{ role: 'user', content: '' }],
      ['just a string'],
      [null],
    ];

    for (const messages of cases) {
      const { status, json } = await post({ body: { model: 'gpt-5-mini', messages } });
      assert.equal(status, 400, `expected 400 for: ${JSON.stringify(messages)}`);
      assert.equal(json.error.param, 'messages');
    }
    assert.equal(upstream.calls.length, 0);
  });

  it('accepts an assistant message that carries only tool calls', async () => {
    const { status } = await post({
      body: {
        model: 'gpt-5-mini',
        messages: [
          { role: 'user', content: 'What is the weather?' },
          {
            role: 'assistant',
            content: null,
            tool_calls: [{ id: 'call_1', type: 'function', function: { name: 'get_weather', arguments: '{}' } }],
          },
          { role: 'tool', content: '{"temp":21}' },
        ],
      },
    });

    assert.equal(status, 200);
  });

  it('rejects more messages than the configured maximum', async () => {
    const env = makeEnv({ MAX_MESSAGES: '2' });
    const messages = Array.from({ length: 3 }, () => ({ role: 'user', content: 'hi' }));
    const { status, json } = await post({ body: { model: 'gpt-5-mini', messages }, env });

    assert.equal(status, 400);
    assert.match(json.error.message, /at most 2 messages/);
  });

  it('rejects an oversized body by declared Content-Length', async () => {
    const env = makeEnv({ MAX_REQUEST_BYTES: '512' });
    const big = { model: 'gpt-5-mini', messages: [{ role: 'user', content: 'x'.repeat(2000) }] };
    const { status, json } = await post({ body: big, env });

    assert.equal(status, 413);
    assert.equal(json.error.type, 'payload_too_large_error');
    assert.match(json.error.message, /512 byte limit/);
    assert.equal(upstream.calls.length, 0);
  });

  it('rejects an oversized chunked body that declares no Content-Length', async () => {
    const env = makeEnv({ MAX_REQUEST_BYTES: '512' });
    const payload = JSON.stringify({
      model: 'gpt-5-mini',
      messages: [{ role: 'user', content: 'x'.repeat(2000) }],
    });

    // A ReadableStream body sends no Content-Length, so only the metered read
    // can catch this.
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(payload));
        controller.close();
      },
    });

    const request = new Request('https://gateway.example/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${TEST_TOKEN}`,
        'Content-Type': 'application/json',
        'CF-Connecting-IP': '203.0.113.99',
      },
      body: stream,
      duplex: 'half',
    });

    assert.equal(request.headers.get('Content-Length'), null);

    const { default: worker } = await import('../src/index.js');
    const response = await worker.fetch(request, env, { waitUntil() {} });

    assert.equal(response.status, 413);
    assert.equal(upstream.calls.length, 0);
  });

  it('rejects a model outside the allowlist before calling the provider', async () => {
    const { status, json } = await post({
      body: { model: 'gpt-4-turbo', messages: VALID_CHAT_REQUEST.messages },
    });

    assert.equal(status, 403);
    assert.equal(json.error.type, 'permission_error');
    assert.match(json.error.message, /not permitted by this gateway/);
    assert.equal(upstream.calls.length, 0, 'a refused model must cost nothing upstream');
  });

  it('does not disclose the allowlist when refusing a model', async () => {
    const { text } = await post({
      body: { model: 'gpt-4-turbo', messages: VALID_CHAT_REQUEST.messages },
    });

    assert.doesNotMatch(text, /gpt-4o-mini/);
  });

  it('falls back to the default model when none is supplied', async () => {
    const { status } = await post({ body: { messages: VALID_CHAT_REQUEST.messages } });

    assert.equal(status, 200);
    assert.equal(upstream.calls[0].body.model, 'gpt-5-mini');
  });

  it('rejects an output-token request above the ceiling', async () => {
    const env = makeEnv({ MAX_OUTPUT_TOKENS: '100' });

    for (const field of ['max_tokens', 'max_completion_tokens']) {
      const { status, json } = await post({
        body: { ...VALID_CHAT_REQUEST, [field]: 5000 },
        env,
      });
      assert.equal(status, 400, `expected 400 for ${field}`);
      assert.match(json.error.message, /must not exceed 100/);
    }
    assert.equal(upstream.calls.length, 0);
  });

  it('rejects a non-positive or fractional token limit', async () => {
    for (const value of [0, -5, 1.5]) {
      const { status } = await post({ body: { ...VALID_CHAT_REQUEST, max_tokens: value } });
      assert.equal(status, 400, `expected 400 for max_tokens=${value}`);
    }
  });

  it('injects the ceiling when the request names no token limit', async () => {
    const env = makeEnv({ MAX_OUTPUT_TOKENS: '256' });
    await post({ body: VALID_CHAT_REQUEST, env });

    assert.equal(upstream.calls[0].body.max_completion_tokens, 256);
  });

  it('honours MAX_OUTPUT_TOKENS_FIELD for legacy-style providers', async () => {
    const env = makeEnv({ MAX_OUTPUT_TOKENS: '256', MAX_OUTPUT_TOKENS_FIELD: 'max_tokens' });
    await post({ body: VALID_CHAT_REQUEST, env });

    assert.equal(upstream.calls[0].body.max_tokens, 256);
    assert.equal(upstream.calls[0].body.max_completion_tokens, undefined);
  });

  it('injects nothing when MAX_OUTPUT_TOKENS_FIELD is "none"', async () => {
    const env = makeEnv({ MAX_OUTPUT_TOKENS_FIELD: 'none' });
    await post({ body: VALID_CHAT_REQUEST, env });

    assert.equal(upstream.calls[0].body.max_tokens, undefined);
    assert.equal(upstream.calls[0].body.max_completion_tokens, undefined);
  });

  it('preserves a caller limit that sits under the ceiling', async () => {
    await post({ body: { ...VALID_CHAT_REQUEST, max_tokens: 64 } });
    assert.equal(upstream.calls[0].body.max_tokens, 64);
  });

  it('rejects numeric parameters outside their documented ranges', async () => {
    const cases = [
      ['temperature', 3],
      ['temperature', -1],
      ['top_p', 1.5],
      ['presence_penalty', 5],
      ['frequency_penalty', -9],
      ['top_logprobs', 50],
      ['temperature', 'hot'],
    ];

    for (const [field, value] of cases) {
      const { status, json } = await post({ body: { ...VALID_CHAT_REQUEST, [field]: value } });
      assert.equal(status, 400, `expected 400 for ${field}=${value}`);
      assert.equal(json.error.param, field);
    }
  });

  it('caps the number of completions requested', async () => {
    const env = makeEnv({ MAX_COMPLETIONS: '2' });
    const over = await post({ body: { ...VALID_CHAT_REQUEST, n: 5 }, env });
    const under = await post({ body: { ...VALID_CHAT_REQUEST, n: 2 }, env });

    assert.equal(over.status, 400);
    assert.match(over.json.error.message, /must not exceed 2/);
    assert.equal(under.status, 200);
  });

  it('rejects a non-boolean stream flag', async () => {
    const { status } = await post({ body: { ...VALID_CHAT_REQUEST, stream: 'yes' } });
    assert.equal(status, 400);
  });

  it('strips parameters outside the forward allowlist', async () => {
    await post({
      body: {
        ...VALID_CHAT_REQUEST,
        base_url: 'https://attacker.example/v1',
        api_key: 'sk-injected',
        __proto__prop: 'x',
        unknown_field: 'should not be forwarded',
      },
    });

    const forwarded = upstream.calls[0].body;
    assert.equal(forwarded.base_url, undefined);
    assert.equal(forwarded.api_key, undefined);
    assert.equal(forwarded.unknown_field, undefined);
    assert.deepEqual(
      Object.keys(forwarded).sort(),
      ['max_completion_tokens', 'messages', 'model'],
    );
  });

  it('forwards allowlisted tuning parameters unchanged', async () => {
    await post({
      body: {
        ...VALID_CHAT_REQUEST,
        temperature: 0.4,
        top_p: 0.9,
        seed: 7,
        stop: ['\n'],
        response_format: { type: 'json_object' },
        user: 'account-42',
      },
    });

    const forwarded = upstream.calls[0].body;
    assert.equal(forwarded.temperature, 0.4);
    assert.equal(forwarded.top_p, 0.9);
    assert.equal(forwarded.seed, 7);
    assert.deepEqual(forwarded.stop, ['\n']);
    assert.deepEqual(forwarded.response_format, { type: 'json_object' });
    assert.equal(forwarded.user, 'account-42');
  });
});
