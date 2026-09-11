import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  DEFAULTS,
  MIN_TOKEN_LENGTH,
  parseBaseUrl,
  resolveAccessTokens,
  resolveConfig,
  resolveProviderKey,
} from '../src/config.js';
import { makeEnv } from './helpers.js';

describe('configuration', () => {
  describe('base URL pinning', () => {
    it('accepts an https URL and normalises the trailing slash', () => {
      assert.equal(parseBaseUrl('https://api.openai.com/v1'), 'https://api.openai.com/v1');
      assert.equal(parseBaseUrl('https://api.openai.com/v1/'), 'https://api.openai.com/v1');
      assert.equal(parseBaseUrl('https://api.openai.com/v1///'), 'https://api.openai.com/v1');
      assert.equal(parseBaseUrl('https://api.openai.com'), 'https://api.openai.com');
    });

    it('rejects plain http against a remote host', () => {
      assert.throws(() => parseBaseUrl('http://api.openai.com/v1'), /not configured/);
    });

    it('permits http against loopback for local development', () => {
      assert.equal(parseBaseUrl('http://localhost:8787/v1'), 'http://localhost:8787/v1');
      assert.equal(parseBaseUrl('http://127.0.0.1:8787/v1'), 'http://127.0.0.1:8787/v1');
    });

    it('rejects a URL with embedded credentials', () => {
      assert.throws(() => parseBaseUrl('https://user:pass@api.openai.com/v1'), /not configured/);
    });

    it('rejects a query string or fragment', () => {
      assert.throws(() => parseBaseUrl('https://api.openai.com/v1?key=leak'), /not configured/);
      assert.throws(() => parseBaseUrl('https://api.openai.com/v1#x'), /not configured/);
    });

    it('rejects non-HTTP schemes outright', () => {
      for (const url of ['file:///etc/passwd', 'ftp://host/x', 'javascript:alert(1)', 'not a url']) {
        assert.throws(() => parseBaseUrl(url), /not configured/, `should reject ${url}`);
      }
    });
  });

  describe('model allowlist', () => {
    it('falls back to the default model alone when no allowlist is set', () => {
      const config = resolveConfig({ DEFAULT_MODEL: 'my-model' });
      assert.deepEqual(config.chatModels, ['my-model']);
    });

    it('parses and trims a comma-separated allowlist', () => {
      const config = resolveConfig({ ALLOWED_MODELS: ' a , b ,, c ' });
      assert.deepEqual(config.chatModels, ['a', 'b', 'c']);
    });

    it('keeps embeddings disabled until models are named', () => {
      assert.equal(resolveConfig({}).embeddingsEnabled, false);
      assert.equal(resolveConfig({ ALLOWED_EMBEDDING_MODELS: 'text-embedding-3-small' }).embeddingsEnabled, true);
    });
  });

  describe('numeric bounds', () => {
    it('applies documented defaults when unset', () => {
      const config = resolveConfig({});

      assert.equal(config.rateLimitPerMinute, DEFAULTS.RATE_LIMIT_PER_MINUTE);
      assert.equal(config.maxRequestBytes, DEFAULTS.MAX_REQUEST_BYTES);
      assert.equal(config.maxOutputTokens, DEFAULTS.MAX_OUTPUT_TOKENS);
      assert.equal(config.upstreamTimeoutMs, DEFAULTS.UPSTREAM_TIMEOUT_MS);
    });

    it('rejects a non-integer value rather than coercing it', () => {
      for (const value of ['30abc', 'abc', '3.5', '']) {
        if (value === '') continue;
        assert.throws(() => resolveConfig({ RATE_LIMIT_PER_MINUTE: value }), /not configured/);
      }
    });

    it('rejects values outside their safe range', () => {
      assert.throws(() => resolveConfig({ RATE_LIMIT_PER_MINUTE: '0' }), /not configured/);
      assert.throws(() => resolveConfig({ RATE_LIMIT_PER_MINUTE: '-5' }), /not configured/);
      assert.throws(() => resolveConfig({ MAX_REQUEST_BYTES: '99999999' }), /not configured/);
      assert.throws(() => resolveConfig({ UPSTREAM_TIMEOUT_MS: '10' }), /not configured/);
    });

    it('rejects an unrecognised token-limit field', () => {
      assert.throws(() => resolveConfig({ MAX_OUTPUT_TOKENS_FIELD: 'max_tokens_v2' }), /not configured/);
    });

    it('parses booleans strictly', () => {
      assert.equal(resolveConfig({ ALLOW_STREAMING: 'false' }).allowStreaming, false);
      assert.equal(resolveConfig({ ALLOW_STREAMING: 'TRUE' }).allowStreaming, true);
      assert.throws(() => resolveConfig({ ALLOW_STREAMING: 'maybe' }), /not configured/);
    });
  });

  describe('secrets', () => {
    it('refuses to run with no access token configured', () => {
      assert.throws(() => resolveAccessTokens({}), /not configured for authenticated access/);
      assert.throws(() => resolveAccessTokens({ PROXY_ACCESS_TOKEN: '   ' }), /not configured/);
    });

    it('refuses a token shorter than the minimum', () => {
      const short = 'a'.repeat(MIN_TOKEN_LENGTH - 1);
      assert.throws(() => resolveAccessTokens({ PROXY_ACCESS_TOKEN: short }), /not configured/);
    });

    it('accepts a token at the minimum length', () => {
      const exact = 'a'.repeat(MIN_TOKEN_LENGTH);
      assert.deepEqual(resolveAccessTokens({ PROXY_ACCESS_TOKEN: exact }), [exact]);
    });

    it('rejects a rotation list containing one weak entry', () => {
      const strong = 'a'.repeat(MIN_TOKEN_LENGTH);
      assert.throws(() => resolveAccessTokens({ PROXY_ACCESS_TOKEN: `${strong},short` }), /not configured/);
    });

    it('refuses to serve with no provider key', () => {
      assert.throws(() => resolveProviderKey({}), /AI provider is not configured/);
    });

    it('never places a secret on the resolved config object', () => {
      const config = resolveConfig(makeEnv());
      const serialised = JSON.stringify(config);

      assert.doesNotMatch(serialised, /sk-test-provider-key/);
      assert.doesNotMatch(serialised, /test-proxy-token/);
    });
  });

  it('returns a frozen configuration object', () => {
    const config = resolveConfig(makeEnv());

    assert.equal(Object.isFrozen(config), true);
    assert.throws(() => {
      'use strict';
      config.baseUrl = 'https://attacker.example';
    }, TypeError);
  });
});
