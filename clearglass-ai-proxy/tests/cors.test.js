import { after, before, beforeEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  TEST_TOKEN,
  VALID_CHAT_REQUEST,
  call,
  callJson,
  chatCompletionBody,
  jsonUpstream,
  makeEnv,
  resetRateLimiter,
  silenceLogs,
  stubUpstream,
} from './helpers.js';

describe('CORS', () => {
  let restoreLogs;

  before(() => {
    restoreLogs = silenceLogs();
  });
  after(() => restoreLogs());

  beforeEach(() => {
    resetRateLimiter();
    stubUpstream(() => jsonUpstream(chatCompletionBody()));
  });

  it('echoes an allowlisted origin', async () => {
    const { response } = await callJson('/health', { origin: 'https://clearglassinc.com' });

    assert.equal(response.headers.get('Access-Control-Allow-Origin'), 'https://clearglassinc.com');
    assert.equal(response.headers.get('Vary'), 'Origin');
  });

  it('omits the CORS header for an origin that is not allowlisted', async () => {
    const { response, status } = await callJson('/health', { origin: 'https://attacker.example' });

    // The request still succeeds server-side; the browser is what blocks it,
    // because no Allow-Origin header comes back.
    assert.equal(status, 200);
    assert.equal(response.headers.get('Access-Control-Allow-Origin'), null);
  });

  it('does not treat a look-alike origin as a match', async () => {
    const lookalikes = [
      'https://clearglassinc.com.attacker.example',
      'http://clearglassinc.com',
      'https://evil.clearglassinc.com',
    ];

    for (const origin of lookalikes) {
      const { response } = await callJson('/health', { origin });
      assert.equal(
        response.headers.get('Access-Control-Allow-Origin'),
        null,
        `must not allow ${origin}`,
      );
    }
  });

  it('supports several allowlisted origins', async () => {
    const env = makeEnv({ ALLOWED_ORIGIN: 'https://a.example,https://b.example' });

    for (const origin of ['https://a.example', 'https://b.example']) {
      const { response } = await callJson('/health', { env, origin });
      assert.equal(response.headers.get('Access-Control-Allow-Origin'), origin);
    }

    const { response } = await callJson('/health', { env, origin: 'https://c.example' });
    assert.equal(response.headers.get('Access-Control-Allow-Origin'), null);
  });

  it('supports the development wildcard', async () => {
    const env = makeEnv({ ALLOWED_ORIGIN: '*' });
    const { response } = await callJson('/health', { env, origin: 'https://anywhere.example' });

    assert.equal(response.headers.get('Access-Control-Allow-Origin'), '*');
  });

  it('never sends Allow-Credentials, least of all with a wildcard', async () => {
    for (const allowed of ['*', 'https://clearglassinc.com']) {
      const env = makeEnv({ ALLOWED_ORIGIN: allowed });
      const { response } = await callJson('/health', { env, origin: 'https://clearglassinc.com' });

      assert.equal(response.headers.get('Access-Control-Allow-Credentials'), null);
    }
  });

  it('sends no CORS header when no origin is allowlisted', async () => {
    const env = makeEnv({ ALLOWED_ORIGIN: '' });
    const { response } = await callJson('/health', { env, origin: 'https://clearglassinc.com' });

    assert.equal(response.headers.get('Access-Control-Allow-Origin'), null);
  });

  describe('preflight', () => {
    it('answers OPTIONS with 204 and the permitted methods and headers', async () => {
      const response = await call('/v1/chat/completions', {
        method: 'OPTIONS',
        origin: 'https://clearglassinc.com',
      });

      assert.equal(response.status, 204);
      assert.equal(response.headers.get('Access-Control-Allow-Origin'), 'https://clearglassinc.com');
      assert.match(response.headers.get('Access-Control-Allow-Methods'), /POST/);
      assert.match(response.headers.get('Access-Control-Allow-Headers'), /Authorization/);
      assert.match(response.headers.get('Access-Control-Allow-Headers'), /Content-Type/);
      assert.ok(Number(response.headers.get('Access-Control-Max-Age')) > 0);
    });

    it('does not require authentication, as browsers send it unauthenticated', async () => {
      const response = await call('/v1/chat/completions', {
        method: 'OPTIONS',
        origin: 'https://clearglassinc.com',
      });

      assert.equal(response.status, 204);
    });

    it('refuses preflight for an origin that is not allowlisted', async () => {
      const response = await call('/v1/chat/completions', {
        method: 'OPTIONS',
        origin: 'https://attacker.example',
      });

      assert.equal(response.headers.get('Access-Control-Allow-Origin'), null);
    });
  });

  it('applies CORS headers to error responses too', async () => {
    const { response, status } = await callJson('/v1/chat/completions', {
      method: 'POST',
      body: VALID_CHAT_REQUEST,
      origin: 'https://clearglassinc.com',
    });

    assert.equal(status, 401);
    assert.equal(response.headers.get('Access-Control-Allow-Origin'), 'https://clearglassinc.com');
  });

  it('applies CORS headers to successful proxied responses', async () => {
    const { response, status } = await callJson('/v1/chat/completions', {
      method: 'POST',
      token: TEST_TOKEN,
      body: VALID_CHAT_REQUEST,
      origin: 'https://clearglassinc.com',
    });

    assert.equal(status, 200);
    assert.equal(response.headers.get('Access-Control-Allow-Origin'), 'https://clearglassinc.com');
  });
});
