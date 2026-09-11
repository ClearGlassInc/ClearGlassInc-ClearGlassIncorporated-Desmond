import { after, before, beforeEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  TEST_TOKEN,
  callJson,
  jsonUpstream,
  makeEnv,
  resetRateLimiter,
  silenceLogs,
  stubUpstream,
} from './helpers.js';

describe('GET /v1/models', () => {
  let restoreLogs;
  before(() => {
    restoreLogs = silenceLogs();
  });
  after(() => restoreLogs());
  beforeEach(() => resetRateLimiter());

  it('requires authentication', async () => {
    const { status } = await callJson('/v1/models');
    assert.equal(status, 401);
  });

  it('returns the gateway allowlist in OpenAI list shape', async () => {
    const { status, json } = await callJson('/v1/models', { token: TEST_TOKEN });

    assert.equal(status, 200);
    assert.equal(json.object, 'list');
    assert.deepEqual(json.data.map((m) => m.id), ['gpt-5-mini', 'gpt-4o-mini']);
    assert.ok(json.data.every((m) => m.object === 'model'));
  });

  it('includes allowlisted embedding models when enabled', async () => {
    const env = makeEnv({ ALLOWED_EMBEDDING_MODELS: 'text-embedding-3-small' });
    const { json } = await callJson('/v1/models', { token: TEST_TOKEN, env });

    assert.ok(json.data.some((m) => m.id === 'text-embedding-3-small'));
  });

  it('answers from configuration without calling the provider', async () => {
    const upstream = stubUpstream(() => jsonUpstream({}));
    await callJson('/v1/models', { token: TEST_TOKEN });

    assert.equal(upstream.calls.length, 0, 'the provider catalogue must not be disclosed');
  });

  it('rejects a write method', async () => {
    const { status, response } = await callJson('/v1/models', { method: 'POST', token: TEST_TOKEN });

    assert.equal(status, 405);
    assert.equal(response.headers.get('Allow'), 'GET, HEAD');
  });
});

describe('POST /v1/embeddings', () => {
  let restoreLogs;
  let upstream;

  before(() => {
    restoreLogs = silenceLogs();
  });
  after(() => restoreLogs());

  beforeEach(() => {
    resetRateLimiter();
    upstream = stubUpstream(() =>
      jsonUpstream({
        object: 'list',
        data: [{ object: 'embedding', index: 0, embedding: [0.1, 0.2] }],
        model: 'text-embedding-3-small',
        usage: { prompt_tokens: 3, total_tokens: 3 },
      }),
    );
  });

  const enabledEnv = () => makeEnv({ ALLOWED_EMBEDDING_MODELS: 'text-embedding-3-small' });

  const post = (options = {}) =>
    callJson('/v1/embeddings', { method: 'POST', token: TEST_TOKEN, ...options });

  it('stays disabled until models are allowlisted', async () => {
    const { status, json } = await post({
      body: { model: 'text-embedding-3-small', input: 'hello' },
    });

    assert.equal(status, 404);
    assert.match(json.error.message, /not enabled/);
    assert.equal(upstream.calls.length, 0);
  });

  it('requires authentication even when enabled', async () => {
    const { status } = await callJson('/v1/embeddings', {
      method: 'POST',
      env: enabledEnv(),
      body: { model: 'text-embedding-3-small', input: 'hello' },
    });

    assert.equal(status, 401);
  });

  it('proxies a valid request once enabled', async () => {
    const { status, json } = await post({
      env: enabledEnv(),
      body: { model: 'text-embedding-3-small', input: 'hello' },
    });

    assert.equal(status, 200);
    assert.equal(json.object, 'list');
    assert.equal(upstream.calls[0].url, 'https://api.openai.com/v1/embeddings');
  });

  it('accepts an array of inputs', async () => {
    const { status } = await post({
      env: enabledEnv(),
      body: { model: 'text-embedding-3-small', input: ['a', 'b'] },
    });

    assert.equal(status, 200);
  });

  it('rejects a missing or malformed input', async () => {
    for (const input of [undefined, '', [], [''], [1, 2], {}, null]) {
      const body = { model: 'text-embedding-3-small' };
      if (input !== undefined) body.input = input;

      const { status } = await post({ env: enabledEnv(), body });
      assert.equal(status, 400, `expected 400 for input: ${JSON.stringify(input)}`);
    }
  });

  it('enforces its own model allowlist, separate from chat', async () => {
    const { status, json } = await post({
      env: enabledEnv(),
      body: { model: 'gpt-5-mini', input: 'hello' },
    });

    assert.equal(status, 403);
    assert.equal(json.error.type, 'permission_error');
    assert.equal(upstream.calls.length, 0);
  });

  it('strips parameters outside the embeddings allowlist', async () => {
    await post({
      env: enabledEnv(),
      body: {
        model: 'text-embedding-3-small',
        input: 'hello',
        messages: [{ role: 'user', content: 'ignored' }],
        base_url: 'https://attacker.example',
      },
    });

    const forwarded = upstream.calls[0].body;
    assert.equal(forwarded.messages, undefined);
    assert.equal(forwarded.base_url, undefined);
    assert.deepEqual(Object.keys(forwarded).sort(), ['input', 'model']);
  });
});
