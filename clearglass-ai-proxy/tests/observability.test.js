import { beforeEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  TEST_API_KEY,
  TEST_TOKEN,
  VALID_CHAT_REQUEST,
  callJson,
  captureLogs,
  chatCompletionBody,
  jsonUpstream,
  makeEnv,
  resetRateLimiter,
  stubUpstream,
} from './helpers.js';

const SENSITIVE_PROMPT = 'My password is hunter2 and my card is 4111111111111111';

describe('observability', () => {
  beforeEach(() => {
    resetRateLimiter();
    stubUpstream(() => jsonUpstream(chatCompletionBody()));
  });

  const post = (options = {}) =>
    callJson('/v1/chat/completions', {
      method: 'POST',
      token: TEST_TOKEN,
      body: VALID_CHAT_REQUEST,
      ...options,
    });

  it('emits one structured JSON record per request', async () => {
    const { lines } = await captureLogs(() => post());

    assert.equal(lines.length, 1);
    const record = JSON.parse(lines[0]);

    for (const field of ['request_id', 'timestamp', 'route', 'method', 'status', 'latency_ms']) {
      assert.ok(record[field] !== undefined, `record should carry ${field}`);
    }
    assert.equal(record.route, '/v1/chat/completions');
    assert.equal(record.method, 'POST');
    assert.equal(record.status, 200);
    assert.equal(typeof record.latency_ms, 'number');
    assert.match(record.timestamp, /^\d{4}-\d{2}-\d{2}T/);
  });

  it('records the model and provider actually used', async () => {
    const { lines } = await captureLogs(() => post());
    const record = JSON.parse(lines[0]);

    assert.equal(record.model, 'gpt-5-mini');
    assert.equal(record.provider, 'openai');
  });

  it('records the error type on a failed request', async () => {
    const { lines } = await captureLogs(() => post({ token: undefined }));
    const record = JSON.parse(lines[0]);

    assert.equal(record.status, 401);
    assert.equal(record.error_type, 'authentication_error');
    assert.equal(record.outcome, 'error');
  });

  it('never writes a credential to the log stream', async () => {
    const { lines } = await captureLogs(() =>
      post({
        headers: { 'X-Custom': 'noise' },
        body: { ...VALID_CHAT_REQUEST, messages: [{ role: 'user', content: SENSITIVE_PROMPT }] },
      }),
    );

    const output = lines.join('\n');
    assert.doesNotMatch(output, new RegExp(TEST_TOKEN));
    assert.doesNotMatch(output, new RegExp(TEST_API_KEY));
    assert.doesNotMatch(output, /Bearer /);
    assert.doesNotMatch(output, /Authorization/i);
  });

  it('never writes prompt or completion content to the log stream', async () => {
    const { lines } = await captureLogs(() =>
      post({ body: { ...VALID_CHAT_REQUEST, messages: [{ role: 'user', content: SENSITIVE_PROMPT }] } }),
    );

    const output = lines.join('\n');
    assert.doesNotMatch(output, /hunter2/);
    assert.doesNotMatch(output, /4111111111111111/);
    assert.doesNotMatch(output, /Hello from ClearGlass/);
  });

  it('logs a pseudonymous client identifier rather than the raw IP', async () => {
    const { lines } = await captureLogs(() => post({ ip: '198.51.100.77' }));
    const record = JSON.parse(lines[0]);

    assert.doesNotMatch(lines.join('\n'), /198\.51\.100\.77/);
    assert.match(record.client_ip_hash, /^[0-9a-f]{12}$/);
  });

  it('logs a token fingerprint rather than the token', async () => {
    const { lines } = await captureLogs(() => post());
    const record = JSON.parse(lines[0]);

    assert.match(record.token_id, /^[0-9a-f]{12}$/);
    assert.ok(!TEST_TOKEN.includes(record.token_id));
  });

  it('correlates the log record with the client response', async () => {
    const { lines, result } = await captureLogs(() => post());
    const record = JSON.parse(lines[0]);

    assert.equal(record.request_id, result.json.request_id ?? result.response.headers.get('X-Request-Id'));
  });

  it('issues a unique request ID per request', async () => {
    const first = await post();
    const second = await post();

    const a = first.response.headers.get('X-Request-Id');
    const b = second.response.headers.get('X-Request-Id');

    assert.notEqual(a, b);
    assert.match(a, /^req_[0-9a-f]{32}$/);
  });

  it('caps free-text detail so a log line cannot be flooded', async () => {
    const env = makeEnv({ OPENAI_BASE_URL: 'http://attacker.example/v1' });
    const { lines } = await captureLogs(() => post({ env }));

    for (const line of lines) {
      const record = JSON.parse(line);
      if (record.detail) assert.ok(record.detail.length <= 300);
    }
  });
});
