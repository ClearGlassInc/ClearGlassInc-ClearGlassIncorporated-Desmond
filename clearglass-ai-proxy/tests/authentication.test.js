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
import { constantTimeEquals, parseBearer, tokenFingerprint } from '../src/middleware/authentication.js';

describe('authentication', () => {
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

  const post = (options) =>
    callJson('/v1/chat/completions', { method: 'POST', body: VALID_CHAT_REQUEST, ...options });

  it('rejects a request with no Authorization header', async () => {
    const { status, json } = await post({});

    assert.equal(status, 401);
    assert.equal(json.error.type, 'authentication_error');
    assert.equal(json.error.message, 'Missing or invalid credentials');
    assert.equal(upstream.calls.length, 0, 'must not reach the provider');
  });

  it('rejects an incorrect token', async () => {
    const { status, json } = await post({ token: 'wrong-token-but-long-enough-to-pass-length' });

    assert.equal(status, 401);
    assert.equal(json.error.type, 'authentication_error');
    assert.equal(upstream.calls.length, 0);
  });

  it('rejects a malformed Authorization scheme', async () => {
    for (const header of ['Basic abc123', TEST_TOKEN, 'Bearer', 'Bearer   ']) {
      const { status } = await post({ headers: { Authorization: header } });
      assert.equal(status, 401, `expected 401 for header: ${header}`);
    }
    assert.equal(upstream.calls.length, 0);
  });

  it('advertises the Bearer scheme on 401 without hinting at validity', async () => {
    const missing = await post({});
    const wrong = await post({ token: 'wrong-token-but-long-enough-to-pass-length' });

    assert.equal(missing.response.headers.get('WWW-Authenticate'), 'Bearer realm="clearglass-ai-proxy"');
    // Identical bodies: the response must not reveal whether the token existed.
    assert.equal(missing.json.error.message, wrong.json.error.message);
  });

  it('accepts the configured token', async () => {
    const { status, json } = await post({ token: TEST_TOKEN });

    assert.equal(status, 200);
    assert.equal(json.object, 'chat.completion');
    assert.equal(upstream.calls.length, 1);
  });

  it('accepts any token in a comma-separated rotation list', async () => {
    const second = 'rotation-token-fedcba9876543210abcdef';
    const env = makeEnv({ PROXY_ACCESS_TOKEN: `${TEST_TOKEN},${second}` });

    for (const token of [TEST_TOKEN, second]) {
      const { status } = await post({ token, env });
      assert.equal(status, 200, `rotation token should be accepted: ${token}`);
    }
  });

  it('fails closed with 503 when no access token is configured', async () => {
    const env = makeEnv({ PROXY_ACCESS_TOKEN: '' });
    const { status, json } = await post({ token: TEST_TOKEN, env });

    assert.equal(status, 503, 'an unconfigured gateway must refuse, not run open');
    assert.equal(json.error.type, 'configuration_error');
    assert.equal(upstream.calls.length, 0);
  });

  it('fails closed when the configured token is too weak', async () => {
    const env = makeEnv({ PROXY_ACCESS_TOKEN: 'short' });
    const { status, json } = await post({ token: 'short', env });

    assert.equal(status, 503);
    assert.equal(json.error.type, 'configuration_error');
    assert.equal(upstream.calls.length, 0);
  });

  it('never echoes the presented or configured token in an error body', async () => {
    const { text } = await post({ token: 'wrong-token-but-long-enough-to-pass-length' });

    assert.doesNotMatch(text, /wrong-token/);
    assert.doesNotMatch(text, /test-proxy-token/);
  });

  describe('primitives', () => {
    it('parseBearer accepts case-insensitive schemes and rejects junk', () => {
      const make = (value) => new Request('https://x.example', { headers: { Authorization: value } });

      assert.equal(parseBearer(make('Bearer abc')), 'abc');
      assert.equal(parseBearer(make('bearer abc')), 'abc');
      assert.equal(parseBearer(make('BEARER  abc')), 'abc');
      assert.equal(parseBearer(make('Token abc')), null);
      assert.equal(parseBearer(new Request('https://x.example')), null);
    });

    it('constantTimeEquals matches only identical values, regardless of length', async () => {
      assert.equal(await constantTimeEquals('alpha', 'alpha'), true);
      assert.equal(await constantTimeEquals('alpha', 'alphb'), false);
      assert.equal(await constantTimeEquals('alpha', 'alphalonger'), false);
      assert.equal(await constantTimeEquals('', ''), true);
    });

    it('tokenFingerprint is stable, short and not the token', async () => {
      const fingerprint = await tokenFingerprint(TEST_TOKEN);

      assert.match(fingerprint, /^[0-9a-f]{12}$/);
      assert.equal(fingerprint, await tokenFingerprint(TEST_TOKEN));
      assert.notEqual(fingerprint, await tokenFingerprint(`${TEST_TOKEN}x`));
      assert.ok(!TEST_TOKEN.includes(fingerprint));
    });
  });
});
