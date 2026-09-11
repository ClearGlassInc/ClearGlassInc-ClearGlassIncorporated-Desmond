# ClearGlass AI Gateway

An authenticated, rate-limited, validating proxy for OpenAI-compatible AI
providers, running on Cloudflare Workers.

It exists to solve one problem: **a browser or mobile client must never hold
your provider API key.** The gateway holds it, and clients present a separate
credential you can revoke without rotating the provider key.

It is **not** a general-purpose proxy. There is no path through it to an
arbitrary host: the upstream is fixed in configuration, and no request field,
header or path can change it.

```
CLIENT
  │  Authorization: Bearer <PROXY_ACCESS_TOKEN>
  ▼
CLEARGLASS AI GATEWAY  (Cloudflare Worker)
  ├─ CORS / preflight
  ├─ route match            unknown path → 404
  ├─ rate limiting          exceeded    → 429 + Retry-After
  ├─ authentication         bad token   → 401
  ├─ request validation     bad payload → 400 / 403 / 413
  ▼
AI PROVIDER ADAPTER        ← the only module that calls out
  │  Authorization: Bearer <OPENAI_API_KEY>
  ▼
AI API
  │
  ▼
RESPONSE HANDLING          upstream error → sanitised, never forwarded raw
  ▼
CLIENT
```

---

## Table of contents

- [Architecture](#architecture)
- [Installation](#installation)
- [Local development](#local-development)
- [Cloudflare setup](#cloudflare-setup)
- [Secret configuration](#secret-configuration)
- [Deployment](#deployment)
- [GitHub Actions](#github-actions)
- [API usage](#api-usage)
- [Authentication](#authentication)
- [CORS](#cors)
- [Rate limiting](#rate-limiting)
- [Configuration reference](#configuration-reference)
- [Provider configuration](#provider-configuration)
- [Security model](#security-model)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Production hardening](#production-hardening)
- [Using it from a ClearGlass application](#using-it-from-a-clearglass-application)

---

## Architecture

```
clearglass-ai-proxy/
├── src/
│   ├── index.js                   Worker entry point; routing and the pipeline
│   ├── config.js                  Env parsing and validation; fail-closed
│   ├── middleware/
│   │   ├── security.js            CORS, method guards, request-size limits
│   │   ├── authentication.js      Bearer auth, constant-time comparison
│   │   └── rate-limit.js          Fixed-window limiter + Cloudflare binding
│   ├── routes/
│   │   ├── health.js              GET  /health
│   │   ├── chat.js                POST /v1/chat/completions
│   │   ├── models.js              GET  /v1/models
│   │   └── embeddings.js          POST /v1/embeddings (opt-in)
│   ├── providers/
│   │   ├── openai.js              The only module that performs fetch()
│   │   └── provider-router.js     Adapter registry / provider selection
│   └── lib/
│       ├── errors.js              Client-safe error types
│       ├── response.js            JSON + security headers + request IDs
│       ├── validation.js          Payload validation and param allowlists
│       └── log.js                 Structured logging with field allowlist
├── tests/                         138 tests, no network, no dependencies
├── package.json
├── wrangler.toml                  Non-secret configuration only
├── .env.example                   Placeholders only
├── README.md
└── SECURITY.md
```

Workflows live at the repository root (`.github/workflows/ai-proxy-*.yml`),
because GitHub only runs workflows from the root of a repository. This project
is one tree inside a monorepo, so both are path-filtered and prefixed.

**Zero runtime dependencies.** Nothing but your own code executes at the edge
with access to the provider key. Wrangler is the only dependency, and it is
build-time only.

---

## Installation

```bash
cd clearglass-ai-proxy
npm install
```

Requires Node.js 20 or newer (CI uses 22).

---

## Local development

Local secrets go in `.dev.vars`, which is gitignored. It is **not** read in
production — deployed Workers read Cloudflare secrets.

```bash
cat > .dev.vars <<'EOF'
OPENAI_API_KEY=sk-your-real-key
PROXY_ACCESS_TOKEN=a-long-random-token-at-least-24-chars
EOF

npm run dev          # http://127.0.0.1:8787
```

Then:

```bash
curl http://127.0.0.1:8787/health
```

To develop without spending provider tokens, point the gateway at a local mock.
`http://` is accepted **only** for loopback addresses, exactly for this:

```bash
echo 'OPENAI_BASE_URL=http://127.0.0.1:8787/v1' >> .dev.vars
```

---

## Cloudflare setup

1. Create a Cloudflare account (the Workers free plan is sufficient to start).
2. Authenticate Wrangler:

   ```bash
   npx wrangler login
   ```

3. For CI, create an API token instead — at
   **My Profile → API Tokens → Create Token**, using the
   **Edit Cloudflare Workers** template. Scope it to the single account and zone
   you deploy to; do not use a Global API Key.
4. Note your **Account ID** from the Workers dashboard.

---

## Secret configuration

Generate a proxy access token (minimum 24 characters — the gateway refuses to
start below that, because a short token is functionally an open proxy):

```bash
openssl rand -hex 32
```

Set both secrets. Wrangler prompts for the value so it never lands in your
shell history:

```bash
npx wrangler secret put OPENAI_API_KEY
npx wrangler secret put PROXY_ACCESS_TOKEN
```

| Secret | Where it is set | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | Cloudflare Worker secret + GitHub Actions secret | Provider credential. Never leaves the Worker. |
| `PROXY_ACCESS_TOKEN` | Cloudflare Worker secret + GitHub Actions secret | What *your* clients present. Revocable independently. |

Non-secret settings belong in `[vars]` in `wrangler.toml`. **Never put a secret
there** — that file is committed, and CI fails the build if it finds one.

---

## Deployment

```bash
npm install
npx wrangler login
npx wrangler secret put OPENAI_API_KEY
npx wrangler secret put PROXY_ACCESS_TOKEN
npm run deploy
```

Then verify against the real deployment:

```bash
GATEWAY=https://clearglass-ai-proxy.<your-subdomain>.workers.dev

# 1. Health
curl -s $GATEWAY/health
# {"ok":true,...,"checks":{"auth_configured":true,"provider_configured":true,"ready":true}}

# 2. Unauthorized must be refused
curl -s -o /dev/null -w '%{http_code}\n' -X POST $GATEWAY/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"ping"}]}'
# 401

# 3. Authorized
curl -s -X POST $GATEWAY/v1/chat/completions \
  -H "Authorization: Bearer $PROXY_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-5-mini","messages":[{"role":"user","content":"Hello"}]}'
```

If `checks.ready` is `false`, the Worker is deployed but its secrets are not
set. It will refuse traffic with 503 rather than serve without authentication.

---

## GitHub Actions

Two workflows, both path-filtered to `clearglass-ai-proxy/**`.

### `ai-proxy-deploy.yml`

Runs on push to `main`, on pull requests, and on demand.

1. `npm ci` — installs the locked tree exactly; fails if the lockfile drifted.
2. `npm run check` — syntax check on every source file.
3. `npm test` — the full suite.
4. `npx wrangler deploy --dry-run` — proves the Worker bundles and the config is valid.
5. Committed-secret assertion.
6. **Deploy** (skipped on pull requests, including forks).
7. **Post-deployment verification** against the live URL: `/health` returns 200
   and `ready: true`; an unauthenticated request returns 401; an invalid token
   returns 401; a valid token passes authentication.

Step 7 is the gate that matters. A green deploy step only proves an upload
succeeded — it says nothing about whether the service answers or whether it is
open. The authenticated check deliberately sends an invalid payload so it
proves the credential works **without spending provider tokens**; set the
repository variable `RUN_LIVE_AI_CHECK=true` to make a real billable completion
instead.

### `ai-proxy-security.yml`

Runs on push, on pull requests, weekly on a schedule, and on demand.

- **Dependency audit** — `npm audit --omit=dev --audit-level=low` is a hard
  failure: runtime dependencies execute at the edge with access to the provider
  key. Build-time findings are reported but do not block.
- **Lockfile integrity** — detects a hand-edited lockfile or a `package.json`
  changed without one.
- **Secret scanning** — full history, tracked files only, with an assertion
  that `.env` and `.dev.vars` are both untracked and ignored.
- **Source validation** — the test suite plus four architectural invariants:
  only the provider adapter may call `fetch()`; the upstream URL is never
  derived from request input; no hard-coded credentials; every route declares an
  auth posture explicitly.

The schedule matters: a dependency that is clean today can have an advisory
published against it next week with no commit to trigger a re-check.

### Required GitHub secrets

Set under **Settings → Secrets and variables → Actions → Secrets**:

```text
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID
OPENAI_API_KEY
PROXY_ACCESS_TOKEN
```

### Repository variables (optional)

Under the **Variables** tab:

| Variable | Effect |
|---|---|
| `GATEWAY_URL` | Deployed Worker URL. **Without it, post-deployment verification is skipped with a warning.** Set it. |
| `RUN_LIVE_AI_CHECK` | `true` makes one real (billable) completion after each deploy. |

---

## API usage

### `GET /health`

Public. No credential required, so uptime monitors and deploy gates can use it.

```json
{
  "ok": true,
  "service": "clearglass-ai-proxy",
  "version": "1.0.0",
  "timestamp": "2026-01-01T00:00:00.000Z",
  "request_id": "req_...",
  "checks": { "auth_configured": true, "provider_configured": true, "ready": true }
}
```

Booleans only — no URL, model name, or value derived from a secret.

### `POST /v1/chat/completions`

The primary endpoint. Accepts an OpenAI-compatible request and returns the
provider's OpenAI-compatible response.

```bash
curl https://YOUR-WORKER.workers.dev/v1/chat/completions \
  -H "Authorization: Bearer YOUR_PROXY_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5-mini",
    "messages": [
      {
        "role": "user",
        "content": "Hello from ClearGlass"
      }
    ]
  }'
```

Streaming works by passing `"stream": true`; the SSE body is passed through
unbuffered.

Because the official OpenAI SDKs are OpenAI-compatible, they work by changing
the base URL:

```js
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'https://YOUR-WORKER.workers.dev/v1',
  apiKey: PROXY_ACCESS_TOKEN,   // the gateway token, NOT your provider key
});
```

### `GET /v1/models`

Authenticated. Returns the models **this gateway permits**, in OpenAI list
shape. It is answered from configuration, not by proxying the provider's
catalogue — so it reflects what will actually be accepted, and does not
disclose your account's full catalogue.

### `POST /v1/embeddings`

Authenticated, and **disabled by default**: it returns 404 until
`ALLOWED_EMBEDDING_MODELS` names at least one model.

### Errors

Every error is an OpenAI-shaped envelope carrying the request ID:

```json
{
  "error": {
    "message": "AI provider request failed",
    "type": "upstream_error",
    "request_id": "req_..."
  }
}
```

| Status | When |
|---|---|
| 400 | Malformed JSON, invalid messages, out-of-range parameter, over-limit token request |
| 401 | Missing or invalid `PROXY_ACCESS_TOKEN` |
| 403 | Model not on the allowlist; streaming disabled |
| 404 | Unknown endpoint; embeddings not enabled |
| 405 | Wrong method (carries `Allow`) |
| 413 | Body over `MAX_REQUEST_BYTES` |
| 429 | Rate limit exceeded (carries `Retry-After`) |
| 502 | Upstream failed — including a provider 401, which means *our* key is wrong |
| 503 | Gateway misconfigured (no token, no provider key, bad var) |
| 504 | Upstream timed out |

---

## Authentication

Every endpoint except `/health` requires:

```http
Authorization: Bearer <PROXY_ACCESS_TOKEN>
```

- Tokens are compared in **constant time**. Both values are hashed and compared
  over fixed-width bytes, so neither length nor content leaks through response
  latency.
- Missing and wrong tokens return **identical** responses — the gateway never
  reveals whether a token exists.
- Only a short, non-reversible fingerprint of the token is logged.
- **Rotation without downtime**: `PROXY_ACCESS_TOKEN` accepts a comma-separated
  list. Publish the new token alongside the old, migrate clients, then drop the
  old value.

```bash
printf 'old-token,new-token' | npx wrangler secret put PROXY_ACCESS_TOKEN
```

---

## CORS

CORS is enforced by browsers, not servers. It constrains what a *web page* can
do with the gateway; it is not an access control. Authentication is.

Set `ALLOWED_ORIGIN` to exact origins, comma-separated:

```toml
ALLOWED_ORIGIN = "https://clearglassinc.com,https://app.clearglassinc.com"
```

- Only an exact match is echoed back. `https://clearglassinc.com.attacker.example`
  does not match.
- Empty (the default) means no browser origin is allowed. Server-to-server
  callers are unaffected.
- `*` is accepted for local development. **Do not ship it**: it lets any site on
  the internet drive your gateway from a visitor's browser.
- `Access-Control-Allow-Credentials` is never sent, under any configuration.

---

## Rate limiting

Fixed one-minute window, applied twice per request:

- **per source IP**, enforced *before* authentication — so the access token
  cannot be brute-forced;
- **per access token**, enforced after — so one credential cannot spread its
  load across many addresses.

Exceeding either returns 429 with `Retry-After`, plus `X-RateLimit-Limit`,
`X-RateLimit-Remaining` and `X-RateLimit-Reset`.

> **Know this limitation.** The built-in limiter counts **per Worker isolate**.
> Cloudflare runs many isolates, so the effective global ceiling is higher than
> `RATE_LIMIT_PER_MINUTE`. It reliably stops a runaway client and slows
> brute-force attempts; it is **not** a billing control.

For a globally enforced limit, uncomment the rate-limiting binding in
`wrangler.toml`. The code detects it and uses it automatically — no code change:

```toml
[[unsafe.bindings]]
name = "RATE_LIMITER"
type = "ratelimit"
namespace_id = "1001"
simple = { limit = 30, period = 60 }
```

A Durable Object is the other option where you need exact counts and a shared
window across the edge.

---

## Configuration reference

Secrets — set with `wrangler secret put`, never in `wrangler.toml`:

| Name | Required | Notes |
|---|---|---|
| `OPENAI_API_KEY` | Yes | Provider credential. Missing → 503 on AI routes. |
| `PROXY_ACCESS_TOKEN` | Yes | Client credential, min 24 chars. Missing → 503. Comma-separated to rotate. |

Non-secret vars:

| Name | Default | Notes |
|---|---|---|
| `PROVIDER` | `openai` | `openai` or `openai-compatible`. |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | HTTPS required (http only for loopback). No credentials, query or fragment. |
| `DEFAULT_MODEL` | `gpt-5-mini` | Used when a request omits `model`. |
| `ALLOWED_MODELS` | *(unset)* | Comma-separated allowlist. **Unset → only `DEFAULT_MODEL` is reachable.** |
| `ALLOWED_EMBEDDING_MODELS` | *(unset)* | Unset keeps `/v1/embeddings` disabled. |
| `ALLOWED_ORIGIN` | *(empty)* | Exact origins, comma-separated. `*` for dev only. |
| `RATE_LIMIT_PER_MINUTE` | `30` | Per IP and per token. |
| `MAX_REQUEST_BYTES` | `32768` | Enforced on the declared length *and* while the body streams. |
| `MAX_OUTPUT_TOKENS` | `2048` | Hard ceiling. A request may ask for less, never more. |
| `MAX_OUTPUT_TOKENS_FIELD` | `max_completion_tokens` | Field used when injecting the ceiling. Use `max_tokens` for legacy-style providers, `none` to inject nothing. |
| `MAX_MESSAGES` | `64` | Also caps embedding input array length. |
| `MAX_COMPLETIONS` | `4` | Ceiling on `n`. |
| `UPSTREAM_TIMEOUT_MS` | `30000` | 1000–120000. |
| `ALLOW_STREAMING` | `true` | `false` refuses `stream: true` with 403. |

Every numeric var is range-checked at startup. An invalid value fails the
gateway closed with 503 rather than silently falling back to a permissive
default.

> **Verify `ALLOWED_MODELS` against your own provider account.** The gateway
> enforces the list you give it; it cannot know which model IDs your account can
> actually serve. An unavailable ID fails at the provider, surfacing as 502.

---

## Provider configuration

The gateway targets the OpenAI-compatible wire format, so most providers are a
configuration change, not a code change:

```toml
PROVIDER = "openai-compatible"
OPENAI_BASE_URL = "https://your-provider.example/v1"
ALLOWED_MODELS = "their-model-id"
MAX_OUTPUT_TOKENS_FIELD = "max_tokens"   # if they expect the legacy field
```

...plus `wrangler secret put OPENAI_API_KEY` with that provider's key.

For a provider that genuinely differs on the wire, add a factory to the registry
in `src/providers/provider-router.js` returning the same
`{ chatCompletions, embeddings }` interface. No routing or middleware changes.

---

## Security model

Defence in depth. Each control assumes the one in front of it may fail.

| # | Control | Implementation |
|---|---|---|
| 1 | Authentication | Constant-time bearer comparison; fails closed when unset |
| 2 | CORS | Exact-origin allowlist; never combined with credentials |
| 3 | Rate limiting | Per-IP (pre-auth) and per-token (post-auth) windows |
| 4 | Request validation | Strict message/role/parameter checks |
| 5 | Request-size limits | Declared length *and* metered stream read |
| 6 | Output-token limits | Hard ceiling, injected when unspecified |
| 7 | Model allowlisting | Fail-closed; refused before any upstream call |
| 8 | Timeout handling | `AbortSignal.timeout`, bounded 1–120s |
| 9 | Safe error responses | Upstream bodies never forwarded; only sanitised codes |
| 10 | No secret leakage | Secrets absent from responses, headers and logs |
| 11 | No arbitrary upstream URLs | Base URL from config only, validated at startup |
| 12 | No arbitrary HTTP forwarding | Fixed route table; fixed upstream path constants |
| 13 | No SSRF | `fetch()` confined to one module; CI-enforced |
| 14 | No CONNECT tunnelling | Not implemented; no tunnelling path exists |
| 15 | No anonymous proxy mode | No credential configured → 503, never open |

**Fail-closed, everywhere.** Missing token → 503. Missing provider key → 503.
Invalid config value → 503. No model allowlist → only the default model. No
embedding allowlist → route returns 404. There is no configuration in which the
gateway serves anonymous traffic.

**Error sanitisation.** Provider error bodies are never forwarded — they have
been known to echo request headers and URLs. Only `type` and `code` are
extracted, and only when they match `^[a-z0-9_.-]{1,64}$`. A provider 401 is
mapped to 502, because it means *our* key is wrong, not the caller's.

**Logging.** The log record is an explicit field allowlist. Nothing reads request
headers, prompts or response bodies, so a prompt cannot reach the log stream by
accident — a field must be added deliberately. IPs are stored as a truncated
hash; tokens as a 12-hex fingerprint.

Full detail, including the threat model and reporting process, is in
[SECURITY.md](./SECURITY.md).

---

## Testing

```bash
npm test      # 138 tests
npm run check # syntax check every source file
```

No network access and no test dependencies: `fetch` is stubbed, so a test can
never reach a real provider or spend tokens.

Coverage includes every area the build must not regress on: health; unauthorized
and authorized requests; malformed JSON; missing messages; invalid methods; rate
limiting (including both buckets and the Cloudflare binding); CORS (including
look-alike origins and preflight); provider failures (500/401/429/timeout/network);
oversized requests (declared *and* chunked); token limits; model restrictions;
secret absence; unexpected exceptions; SSRF resistance; streaming; and log
redaction.

---

## Troubleshooting

**503, `configuration_error`, "not configured for authenticated access"**
`PROXY_ACCESS_TOKEN` is unset or under 24 characters. This is deliberate — the
gateway refuses to run as an open proxy.

**503, "AI provider is not configured"**
`OPENAI_API_KEY` is not set on the deployed Worker. Secrets are per-Worker and
per-environment; setting one locally does not set it in production.
Check with `npx wrangler secret list`.

**503 right after changing `wrangler.toml`**
A var failed validation. `RATE_LIMIT_PER_MINUTE = "30 "` or `"thirty"` is
rejected rather than coerced. Run `npx wrangler tail` — the log record's
`detail` field names the offending variable.

**401 with a token you believe is correct**
The deployed secret differs from the one you are sending. Re-run
`npx wrangler secret put PROXY_ACCESS_TOKEN`. Watch for a trailing newline:
use `printf '%s' "$TOKEN" | npx wrangler secret put PROXY_ACCESS_TOKEN`.

**403, "Model ... is not permitted by this gateway"**
The model is not in `ALLOWED_MODELS`. Note that `ALLOWED_MODELS` unset means
*only* `DEFAULT_MODEL` is permitted.

**502 on every request**
The provider is rejecting the gateway's credential (a provider 401 maps to 502
by design). Verify `OPENAI_API_KEY` directly against the provider.

**CORS errors in a browser, but curl works**
That is CORS behaving correctly. Add the exact origin — scheme, host and port —
to `ALLOWED_ORIGIN`.

**429 sooner than expected**
Both buckets apply. Your IP and your token each have their own window.

**`npm ci` fails in CI**
`package.json` and `package-lock.json` disagree. Run `npm install` locally and
commit the updated lockfile.

**Post-deployment verification was skipped**
The repository variable `GATEWAY_URL` is not set. Set it to the deployed URL.

---

## Production hardening

Before going live:

- [ ] `ALLOWED_ORIGIN` set to real origins — **not `*`**
- [ ] `ALLOWED_MODELS` restricted to models you intend to pay for, and verified against your provider account
- [ ] `MAX_OUTPUT_TOKENS` and `MAX_REQUEST_BYTES` sized to your actual workload
- [ ] Cloudflare rate-limiting binding enabled (the built-in limiter is per-isolate)
- [ ] `GATEWAY_URL` set so post-deployment verification actually runs
- [ ] Provider-side spending limits configured — the gateway caps per-request cost, not your monthly bill
- [ ] Cloudflare WAF and bot management in front of the Worker
- [ ] A custom domain, so the token is not bound to a `*.workers.dev` hostname
- [ ] Token rotation scheduled, and rehearsed with the comma-separated list
- [ ] Workers Logs reviewed; alerting on 401/429/502 rates
- [ ] `npm audit` clean and the weekly security workflow green

**Per-user accounting.** A single shared `PROXY_ACCESS_TOKEN` cannot distinguish
your users. If you need per-user quotas or revocation, issue short-lived
per-user tokens from your own backend and have it call the gateway, or put an
authenticating service in front of it.

---

## Using it from a ClearGlass application

A ClearGlass application needs exactly two values:

```text
PROXY_ENDPOINT      https://YOUR-WORKER.workers.dev/v1/chat/completions
PROXY_ACCESS_TOKEN  the gateway token
```

`OPENAI_API_KEY` is never one of them. It stays in the Worker.

> **A token shipped to a browser is a public token.** Anyone can read it from
> devtools or a bundle. The gateway is what makes that survivable: the exposed
> credential is revocable on its own, rate-limited, restricted to an allowlist of
> models, and capped on output tokens — none of which is true of a leaked
> provider key. It is a containment boundary, not a secret store.
>
> For anything beyond a low-risk public feature, call the gateway from **your
> own server**, or mint short-lived per-user tokens. Serious deployments should
> not put a long-lived shared token in client-side JavaScript.
