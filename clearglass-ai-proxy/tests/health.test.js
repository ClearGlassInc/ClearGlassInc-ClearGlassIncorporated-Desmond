import { after, before, beforeEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { callJson, makeEnv, resetRateLimiter, silenceLogs } from './helpers.js';

describe('GET /health', () => {
  let restoreLogs;
  before(() => {
    restoreLogs = silenceLogs();
  });
  after(() => restoreLogs());
  beforeEach(() => resetRateLimiter());

  it('responds 200 without a credential', async () => {
    const { status, json } = await callJson('/health');

    assert.equal(status, 200);
    assert.equal(json.ok, true);
    assert.equal(json.service, 'clearglass-ai-proxy');
    assert.equal(json.version, '1.0.0');
    assert.match(json.request_id, /^req_[0-9a-f]{32}$/);
  });

  it('reports readiness as booleans when fully configured', async () => {
    const { json } = await callJson('/health');

    assert.deepEqual(json.checks, {
      auth_configured: true,
      provider_configured: true,
      ready: true,
    });
  });

  it('reports not-ready when secrets are absent, without failing the probe', async () => {
    const env = makeEnv({ OPENAI_API_KEY: '', PROXY_ACCESS_TOKEN: '' });
    const { status, json } = await callJson('/health', { env });

    assert.equal(status, 200);
    assert.equal(json.checks.auth_configured, false);
    assert.equal(json.checks.provider_configured, false);
    assert.equal(json.checks.ready, false);
  });

  it('never discloses credentials or the upstream URL', async () => {
    const { text } = await callJson('/health');

    assert.doesNotMatch(text, /sk-test-provider-key/);
    assert.doesNotMatch(text, /test-proxy-token/);
    assert.doesNotMatch(text, /api\.openai\.com/);
  });

  it('carries the standard security headers', async () => {
    const { response } = await callJson('/health');

    assert.equal(response.headers.get('X-Content-Type-Options'), 'nosniff');
    assert.equal(response.headers.get('X-Frame-Options'), 'DENY');
    assert.equal(response.headers.get('Referrer-Policy'), 'no-referrer');
    assert.equal(response.headers.get('Cache-Control'), 'no-store');
    assert.match(response.headers.get('X-Request-Id'), /^req_/);
  });

  it('rejects a method the route does not implement', async () => {
    const { status, json, response } = await callJson('/health', { method: 'DELETE' });

    assert.equal(status, 405);
    assert.equal(json.error.type, 'invalid_request_error');
    assert.equal(response.headers.get('Allow'), 'GET, HEAD');
  });

  it('treats a trailing slash as the same route', async () => {
    const { status } = await callJson('/health/');
    assert.equal(status, 200);
  });

  it('returns 404 for an unknown path', async () => {
    const { status, json } = await callJson('/not-a-route');

    assert.equal(status, 404);
    assert.equal(json.error.type, 'not_found_error');
    assert.match(json.error.request_id, /^req_/);
  });
});
