import { after, before, beforeEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  TEST_API_KEY,
  TEST_TOKEN,
  VALID_CHAT_REQUEST,
  call,
  callJson,
  captureLogs,
  chatCompletionBody,
  jsonUpstream,
  makeEnv,
  resetRateLimiter,
  silenceLogs,
  stubUpstream,
} from './helpers.js';
import { mapUpstreamStatus } from '../src/providers/openai.js';
import { supportedProviders } from '../src/providers/provider-router.js';

describe('provider integration', () => {
  let restoreLogs;
  before(() => {
    restoreLogs = silenceLogs();
  });
  after(() => restoreLogs());
  beforeEach(() => resetRateLimiter());

  const post = (options = {}) =>
    callJson('/v1/chat/completions', {
      method: 'POST',
      token: TEST_TOKEN,
      body: VALID_CHAT_REQUEST,
      ...options,
    });

  describe('successful proxying', () => {
    it('returns the provider response body unchanged', async () => {
      const body = chatCompletionBody();
      stubUpstream(() => jsonUpstream(body));

      const { status, json } = await post();

      assert.equal(status, 200);
      assert.deepEqual(json, body);
    });

    it('sends the provider credential upstream and only upstream', async () => {
      const upstream = stubUpstream(() => jsonUpstream(chatCompletionBody()));
      const { response, text } = await post();

      assert.equal(upstream.calls[0].headers.get('Authorization'), `Bearer ${TEST_API_KEY}`);
      assert.doesNotMatch(text, /sk-test-provider-key/);
      for (const [, value] of response.headers) {
        assert.doesNotMatch(value, /sk-test-provider-key/);
      }
    });

    it('does not forward the caller credential to the provider', async () => {
      const upstream = stubUpstream(() => jsonUpstream(chatCompletionBody()));
      await post();

      const sent = upstream.calls[0].headers.get('Authorization');
      assert.ok(!sent.includes(TEST_TOKEN), 'the proxy token must not reach the provider');
    });

    it('calls the configured path on the configured host', async () => {
      const upstream = stubUpstream(() => jsonUpstream(chatCompletionBody()));
      await post();

      assert.equal(upstream.calls[0].url, 'https://api.openai.com/v1/chat/completions');
      assert.equal(upstream.calls[0].method, 'POST');
    });

    it('honours a self-hosted OpenAI-compatible base URL', async () => {
      const upstream = stubUpstream(() => jsonUpstream(chatCompletionBody()));
      const env = makeEnv({
        OPENAI_BASE_URL: 'https://llm.internal.example/openai/v1/',
        PROVIDER: 'openai-compatible',
      });

      await post({ env });
      assert.equal(upstream.calls[0].url, 'https://llm.internal.example/openai/v1/chat/completions');
    });

    it('drops upstream response headers that could leak provider metadata', async () => {
      stubUpstream(() =>
        new Response(JSON.stringify(chatCompletionBody()), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
            'openai-organization': 'org-secret-clearglass',
            'x-request-id': 'upstream-req-123',
            'set-cookie': 'session=abc',
          },
        }),
      );

      const { response } = await post();

      assert.equal(response.headers.get('openai-organization'), null);
      assert.equal(response.headers.get('set-cookie'), null);
      assert.match(response.headers.get('X-Request-Id'), /^req_/, 'must be the gateway request id');
    });
  });

  describe('SSRF resistance', () => {
    it('ignores any attempt to steer the upstream from the request body', async () => {
      const upstream = stubUpstream(() => jsonUpstream(chatCompletionBody()));

      await post({
        body: {
          ...VALID_CHAT_REQUEST,
          base_url: 'http://169.254.169.254/latest/meta-data/',
          url: 'http://localhost:8080/admin',
          endpoint: 'https://attacker.example',
        },
      });

      assert.equal(upstream.calls.length, 1);
      assert.equal(upstream.calls[0].url, 'https://api.openai.com/v1/chat/completions');
    });

    it('ignores upstream-steering headers', async () => {
      const upstream = stubUpstream(() => jsonUpstream(chatCompletionBody()));

      await post({
        headers: {
          'X-Upstream-Url': 'https://attacker.example',
          Host: 'attacker.example',
          'X-Forwarded-Host': 'attacker.example',
        },
      });

      assert.equal(upstream.calls[0].url, 'https://api.openai.com/v1/chat/completions');
    });

    it('exposes no path that forwards an arbitrary request', async () => {
      stubUpstream(() => jsonUpstream(chatCompletionBody()));

      for (const path of ['/proxy', '/fetch', '/http://attacker.example', '/v1/', '/']) {
        const { status } = await callJson(path, { token: TEST_TOKEN });
        assert.equal(status, 404, `no forwarder should exist at ${path}`);
      }
    });

    it('refuses to start against a non-HTTPS upstream', async () => {
      const env = makeEnv({ OPENAI_BASE_URL: 'http://attacker.example/v1' });
      const { status, json } = await post({ env });

      assert.equal(status, 503);
      assert.equal(json.error.type, 'configuration_error');
    });
  });

  describe('upstream failures', () => {
    it('maps a provider 500 to 502 without forwarding its body', async () => {
      stubUpstream(() =>
        jsonUpstream(
          { error: { message: 'Internal error: key sk-live-SECRET at /srv/app.py:42', type: 'server_error' } },
          500,
        ),
      );

      const { status, json, text } = await post();

      assert.equal(status, 502);
      assert.equal(json.error.type, 'upstream_error');
      assert.equal(json.error.message, 'AI provider request failed');
      assert.doesNotMatch(text, /sk-live-SECRET/);
      assert.doesNotMatch(text, /srv\/app\.py/);
    });

    it('maps a provider 401 to 502, not 401', async () => {
      stubUpstream(() => jsonUpstream({ error: { message: 'Incorrect API key', type: 'invalid_request_error' } }, 401));

      const { status, json } = await post();

      // A bad OPENAI_API_KEY is our problem, not the caller's; 401 would tell
      // them to re-present a token that is in fact valid.
      assert.equal(status, 502);
      assert.equal(json.error.type, 'upstream_error');
    });

    it('passes a provider rate limit through as 429', async () => {
      stubUpstream(() => jsonUpstream({ error: { message: 'Rate limit reached', type: 'rate_limit_error' } }, 429));

      const { status, json } = await post();

      assert.equal(status, 429);
      assert.equal(json.error.type, 'upstream_error');
    });

    it('forwards only a sanitised machine-readable code', async () => {
      stubUpstream(() =>
        jsonUpstream({ error: { message: 'do not forward me', type: 'invalid_request_error', code: 'model_not_found' } }, 400),
      );

      const { status, json, text } = await post();

      assert.equal(status, 400);
      assert.equal(json.error.code, 'model_not_found');
      assert.doesNotMatch(text, /do not forward me/);
    });

    it('ignores an upstream code that is not a simple token', async () => {
      stubUpstream(() =>
        jsonUpstream({ error: { type: 'x'.repeat(200), code: 'key sk-live-SECRET leaked' } }, 400),
      );

      const { json, text } = await post();

      assert.equal(json.error.code, undefined);
      assert.doesNotMatch(text, /sk-live-SECRET/);
    });

    it('returns 504 when the provider times out', async () => {
      stubUpstream(() => {
        const error = new Error('The operation was aborted due to timeout');
        error.name = 'TimeoutError';
        throw error;
      });

      const { status, json } = await post();

      assert.equal(status, 504);
      assert.equal(json.error.type, 'timeout_error');
      assert.equal(json.error.message, 'AI provider request timed out');
    });

    it('returns 502 on a network-level failure, without the upstream host', async () => {
      stubUpstream(() => {
        throw new TypeError('fetch failed: getaddrinfo ENOTFOUND api.openai.com');
      });

      const { status, json, text } = await post();

      assert.equal(status, 502);
      assert.equal(json.error.type, 'upstream_error');
      assert.doesNotMatch(text, /ENOTFOUND/);
      assert.doesNotMatch(text, /api\.openai\.com/);
    });

    it('applies the configured upstream timeout to the request', async () => {
      const upstream = stubUpstream((record, init) => {
        assert.ok(init.signal, 'an abort signal must be attached');
        return jsonUpstream(chatCompletionBody());
      });

      const { status } = await post({ env: makeEnv({ UPSTREAM_TIMEOUT_MS: '5000' }) });

      assert.equal(status, 200);
      assert.equal(upstream.calls.length, 1);
    });

    it('fails closed with 503 when the provider key is absent', async () => {
      const upstream = stubUpstream(() => jsonUpstream(chatCompletionBody()));
      const env = makeEnv({ OPENAI_API_KEY: '' });

      const { status, json } = await post({ env });

      assert.equal(status, 503);
      assert.equal(json.error.type, 'configuration_error');
      assert.equal(json.error.message, 'AI provider is not configured');
      assert.equal(upstream.calls.length, 0);
    });

    it('fails closed for an unknown PROVIDER', async () => {
      stubUpstream(() => jsonUpstream(chatCompletionBody()));
      const { status, json } = await post({ env: makeEnv({ PROVIDER: 'not-a-provider' }) });

      assert.equal(status, 503);
      assert.equal(json.error.type, 'configuration_error');
    });
  });

  describe('unexpected exceptions', () => {
    it('collapses an unhandled error to a generic 500', async () => {
      // An upstream 200 whose body is not JSON makes response.json() throw
      // inside the route — an exception the gateway never anticipated.
      stubUpstream(() =>
        new Response('<html>gateway timeout at /internal/path</html>', {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );

      const { status, json, text } = await post();

      assert.equal(status, 500);
      assert.equal(json.error.type, 'internal_error');
      assert.equal(json.error.message, 'Internal server error');
      assert.match(json.error.request_id, /^req_/);
      assert.doesNotMatch(text, /internal\/path/);
      assert.doesNotMatch(text, /SyntaxError/);
    });

    it('still logs the request when a handler throws', async () => {
      stubUpstream(() => {
        throw new Error('boom');
      });

      const { lines } = await captureLogs(() => post());
      const record = JSON.parse(lines.at(-1));

      assert.equal(record.status, 502);
      assert.equal(record.route, '/v1/chat/completions');
      assert.ok(record.request_id);
    });
  });

  describe('streaming', () => {
    it('passes an SSE stream through with the right content type', async () => {
      const chunks = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
        'data: {"choices":[{"delta":{"content":" ClearGlass"}}]}\n\n',
        'data: [DONE]\n\n',
      ];

      stubUpstream(() => {
        const stream = new ReadableStream({
          start(controller) {
            const encoder = new TextEncoder();
            for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
            controller.close();
          },
        });
        return new Response(stream, {
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
        });
      });

      const response = await call('/v1/chat/completions', {
        method: 'POST',
        token: TEST_TOKEN,
        body: { ...VALID_CHAT_REQUEST, stream: true },
      });

      assert.equal(response.status, 200);
      assert.match(response.headers.get('Content-Type'), /text\/event-stream/);
      assert.equal(response.headers.get('X-Accel-Buffering'), 'no');

      const body = await response.text();
      assert.match(body, /Hello/);
      assert.match(body, /\[DONE\]/);
    });

    it('asks the provider for a stream only when the caller did', async () => {
      const upstream = stubUpstream(() => jsonUpstream(chatCompletionBody()));

      await post({ body: VALID_CHAT_REQUEST });
      assert.equal(upstream.calls[0].headers.get('Accept'), 'application/json');
      assert.equal(upstream.calls[0].body.stream, undefined);
    });

    it('refuses streaming when ALLOW_STREAMING is off', async () => {
      const upstream = stubUpstream(() => jsonUpstream(chatCompletionBody()));
      const env = makeEnv({ ALLOW_STREAMING: 'false' });

      const { status, json } = await post({ body: { ...VALID_CHAT_REQUEST, stream: true }, env });

      assert.equal(status, 403);
      assert.match(json.error.message, /Streaming is disabled/);
      assert.equal(upstream.calls.length, 0);
    });
  });

  describe('adapter units', () => {
    it('maps upstream statuses onto client-facing ones', () => {
      assert.equal(mapUpstreamStatus(429), 429);
      assert.equal(mapUpstreamStatus(400), 400);
      assert.equal(mapUpstreamStatus(404), 400);
      assert.equal(mapUpstreamStatus(422), 400);
      assert.equal(mapUpstreamStatus(408), 504);
      assert.equal(mapUpstreamStatus(504), 504);
      assert.equal(mapUpstreamStatus(401), 502);
      assert.equal(mapUpstreamStatus(403), 502);
      assert.equal(mapUpstreamStatus(500), 502);
      assert.equal(mapUpstreamStatus(503), 502);
    });

    it('registers the OpenAI-compatible adapters', () => {
      assert.deepEqual(supportedProviders().sort(), ['openai', 'openai-compatible']);
    });
  });
});
