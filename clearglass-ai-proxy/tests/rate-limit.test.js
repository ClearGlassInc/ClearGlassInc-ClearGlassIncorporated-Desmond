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
import { checkRateLimit, clientIp } from '../src/middleware/rate-limit.js';
import { resolveConfig } from '../src/config.js';

describe('rate limiting', () => {
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
    callJson('/v1/chat/completions', {
      method: 'POST',
      token: TEST_TOKEN,
      body: VALID_CHAT_REQUEST,
      ...options,
    });

  it('allows requests up to the limit, then returns 429', async () => {
    const env = makeEnv({ RATE_LIMIT_PER_MINUTE: '3' });

    for (let i = 0; i < 3; i += 1) {
      const { status } = await post({ env });
      assert.equal(status, 200, `request ${i + 1} should be allowed`);
    }

    const { status, json } = await post({ env });
    assert.equal(status, 429);
    assert.equal(json.error.type, 'rate_limit_error');
  });

  it('returns Retry-After and rate-limit headers on 429', async () => {
    const env = makeEnv({ RATE_LIMIT_PER_MINUTE: '1' });
    await post({ env });
    const { response } = await post({ env });

    const retryAfter = Number(response.headers.get('Retry-After'));
    assert.ok(Number.isInteger(retryAfter) && retryAfter >= 1 && retryAfter <= 60,
      `Retry-After should be a sane second count, got ${retryAfter}`);
    assert.equal(response.headers.get('X-RateLimit-Limit'), '1');
    assert.equal(response.headers.get('X-RateLimit-Remaining'), '0');
  });

  it('advertises the remaining budget on allowed requests', async () => {
    const env = makeEnv({ RATE_LIMIT_PER_MINUTE: '5' });
    const { response } = await post({ env });

    assert.equal(response.headers.get('X-RateLimit-Limit'), '5');
    assert.equal(response.headers.get('X-RateLimit-Remaining'), '4');
    assert.ok(Number(response.headers.get('X-RateLimit-Reset')) > 0);
  });

  it('throttles unauthenticated callers, so tokens cannot be brute-forced', async () => {
    const env = makeEnv({ RATE_LIMIT_PER_MINUTE: '2' });

    const first = await post({ env, token: 'wrong-token-but-long-enough-to-pass' });
    const second = await post({ env, token: 'wrong-token-but-long-enough-to-pass' });
    const third = await post({ env, token: 'wrong-token-but-long-enough-to-pass' });

    assert.equal(first.status, 401);
    assert.equal(second.status, 401);
    assert.equal(third.status, 429, 'guessing must be throttled, not merely rejected');
  });

  it('keeps separate buckets per source IP', async () => {
    // Distinct tokens, so this exercises the IP bucket in isolation from the
    // per-token bucket asserted in the next test.
    const tokenB = 'second-client-token-abcdef0123456789';
    const env = makeEnv({
      RATE_LIMIT_PER_MINUTE: '1',
      PROXY_ACCESS_TOKEN: `${TEST_TOKEN},${tokenB}`,
    });

    const a1 = await post({ env, ip: '198.51.100.1', token: TEST_TOKEN });
    const a2 = await post({ env, ip: '198.51.100.1', token: TEST_TOKEN });
    const b1 = await post({ env, ip: '198.51.100.2', token: tokenB });

    assert.equal(a1.status, 200);
    assert.equal(a2.status, 429);
    assert.equal(b1.status, 200, 'a different client must not inherit the throttle');
  });

  it('limits a single token even when it rotates source addresses', async () => {
    const env = makeEnv({ RATE_LIMIT_PER_MINUTE: '2' });

    const r1 = await post({ env, ip: '198.51.100.11' });
    const r2 = await post({ env, ip: '198.51.100.12' });
    const r3 = await post({ env, ip: '198.51.100.13' });

    assert.equal(r1.status, 200);
    assert.equal(r2.status, 200);
    assert.equal(r3.status, 429, 'the per-token bucket must still bind');
  });

  it('does not reach the provider once throttled', async () => {
    const env = makeEnv({ RATE_LIMIT_PER_MINUTE: '1' });
    await post({ env });
    await post({ env });

    assert.equal(upstream.calls.length, 1, 'the throttled request must cost nothing upstream');
  });

  it('starts a fresh window after the previous one expires', async () => {
    const config = resolveConfig(makeEnv({ RATE_LIMIT_PER_MINUTE: '1' }));
    const now = Date.now();

    const first = await checkRateLimit('window-test', {}, config, now);
    const blocked = await checkRateLimit('window-test', {}, config, now + 1_000);
    const afterWindow = await checkRateLimit('window-test', {}, config, now + 61_000);

    assert.equal(first.allowed, true);
    assert.equal(blocked.allowed, false);
    assert.equal(afterWindow.allowed, true);
  });

  it('uses the Cloudflare rate-limiting binding when one is bound', async () => {
    const seen = [];
    // Counts per key, because each request consults the binding twice: once for
    // the IP bucket and once for the token bucket.
    const perKey = new Map();
    const env = makeEnv({
      RATE_LIMIT_PER_MINUTE: '5',
      RATE_LIMITER: {
        limit: async ({ key }) => {
          seen.push(key);
          const used = (perKey.get(key) || 0) + 1;
          perKey.set(key, used);
          return { success: used <= 1 };
        },
      },
    });

    const first = await post({ env });
    const second = await post({ env });

    assert.equal(first.status, 200);
    assert.equal(second.status, 429);
    assert.ok(seen.length >= 2, 'the binding should have been consulted');
    assert.ok(seen.some((key) => key.startsWith('ip:')), 'expected an IP-scoped key');
    assert.ok(seen.some((key) => key.startsWith('tok:')), 'expected a token-scoped key');
  });

  it('reads the client IP from Cloudflare headers, preferring trusted ones', () => {
    const make = (headers) => new Request('https://x.example', { headers });

    assert.equal(clientIp(make({ 'CF-Connecting-IP': '1.1.1.1', 'X-Forwarded-For': '9.9.9.9' })), '1.1.1.1');
    assert.equal(clientIp(make({ 'X-Real-IP': '2.2.2.2' })), '2.2.2.2');
    assert.equal(clientIp(make({ 'X-Forwarded-For': '3.3.3.3, 4.4.4.4' })), '3.3.3.3');
    assert.equal(clientIp(make({})), 'unknown');
  });
});
