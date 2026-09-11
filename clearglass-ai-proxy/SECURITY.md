# Security Policy — ClearGlass AI Gateway

## Reporting a vulnerability

Report suspected vulnerabilities privately to **Desmondotieno@icloud.com** with
subject `SECURITY: clearglass-ai-proxy`.

Please include the affected endpoint, reproduction steps, and what an attacker
gains. Do not open a public issue for an unpatched vulnerability, and do not
include live credentials in a report.

If you believe a credential has leaked, rotate first and report second:

```bash
printf '%s' "$NEW_TOKEN" | npx wrangler secret put PROXY_ACCESS_TOKEN
printf '%s' "$NEW_KEY"   | npx wrangler secret put OPENAI_API_KEY
```

Rotating `OPENAI_API_KEY` also requires revoking the old key in the provider's
dashboard — the Worker no longer using it does not invalidate it.

---

## What this service is

A **restricted** proxy to one preconfigured AI provider. It is deliberately not
a general-purpose proxy.

**In scope:**
- Authentication bypass — any route other than `/health` reachable without a valid token
- SSRF — inducing a request to any host other than the configured `OPENAI_BASE_URL`
- Secret disclosure — `OPENAI_API_KEY` or `PROXY_ACCESS_TOKEN` in any response, header or log
- Bypassing the model allowlist, request-size limit, or output-token ceiling
- Rate-limit bypass beyond the documented per-isolate limitation
- Injecting parameters past the forward allowlist

**Out of scope:**
- Behaviour of the upstream AI provider, including model outputs
- Volumetric DoS against Cloudflare's edge
- The per-isolate rate-limiter ceiling — documented in README, with the
  Cloudflare binding as the supported remedy
- Anything requiring a valid `PROXY_ACCESS_TOKEN` that the holder could do anyway

---

## Threat model

### 1. A client credential will leak

A token shipped in a browser or mobile app is readable by anyone who has it.
The design assumes this **will** happen.

Containment: the leaked credential is not the provider key. It is revocable on
its own, rate-limited per token, restricted to an allowlist of models, capped on
output tokens per request, and usable only against one preconfigured provider.
Rotation is a one-line change with no downtime (comma-separated list).

Residual risk: a leaked token can spend provider credit until revoked. Provider
spending limits are the backstop; the gateway caps per-request cost, not the
monthly bill.

### 2. The gateway becomes an open proxy

The failure mode with the worst consequences: an unauthenticated relay to a paid
API, which is found and abused quickly.

Controls:
- No credential configured → **503, never open**. `resolveAccessTokens()` raises
  rather than returning an empty allowlist.
- Tokens under 24 characters are refused at startup — a guessable token is an
  open proxy with extra steps.
- Routes declare `auth: true|false` explicitly in one reviewable table, so a new
  route cannot become public by omission. CI asserts every route declares it.
- Rate limiting runs *before* authentication, so guessing is throttled.

### 3. SSRF / arbitrary upstream

An attacker steering the upstream at cloud metadata (`169.254.169.254`), an
internal service, or a host they control.

Controls:
- The upstream base URL comes only from the environment, validated at startup:
  HTTPS required (http only for loopback), no embedded credentials, no query or
  fragment.
- Upstream paths are hard-coded constants (`/chat/completions`, `/embeddings`).
  No part of the URL is derived from a request.
- Requests are rebuilt from a **parameter allowlist**. A client-supplied
  `base_url`, `url` or `endpoint` is dropped, never forwarded.
- Exactly one module may call `fetch()`. CI fails the build if any other file
  does — verified against an injected violation, not just assumed.
- There is no route that accepts a URL, and no CONNECT or tunnelling path.

### 4. Secret leakage through responses or logs

Credentials escaping through an error body, a response header, or a log line.

Controls:
- Provider error bodies are **never forwarded**. Only `type` and `code` are
  extracted, and only when they match `^[a-z0-9_.-]{1,64}$` — a long or
  free-text value is dropped.
- A provider 401 maps to 502, so a bad provider key is never reported as a
  client credential problem.
- Unhandled exceptions collapse to a generic 500. Raw exception text can carry
  file paths and URLs and never reaches a client.
- Upstream response headers are dropped; only gateway-controlled headers are
  emitted. This removes provider organisation IDs, request IDs and `Set-Cookie`.
- The log record is an explicit **field allowlist**. Nothing reads request
  headers, prompts or response bodies. A prompt cannot reach the log stream
  without someone deliberately adding a field.
- IPs are logged as a truncated SHA-256 hash; tokens as a 12-hex fingerprint.

### 5. Timing attacks on the credential

A naive `===` on a secret leaks it byte by byte through response latency.

Control: both values are SHA-256 hashed and compared over fixed-width bytes, so
comparison time is independent of content *and* length. Every configured token
is checked, so timing does not reveal which matched or its position in the list.

### 6. Cost exhaustion

An authenticated but hostile client maximising spend.

Controls: per-request output-token ceiling (injected when unspecified, so an
unbounded generation is impossible); `n` capped; request body capped; per-token
and per-IP rate limits; model allowlist keeping traffic off expensive models.

Residual risk: the built-in limiter is per-isolate and is not a billing control.
Use the Cloudflare rate-limiting binding and provider-side spending limits.

### 7. Supply chain

Anything in the dependency tree would execute at the edge with access to the
provider key.

Controls: **zero runtime dependencies** — the Worker runs only first-party code.
Wrangler is build-time only. `npm ci` installs the locked tree exactly;
`npm audit --omit=dev --audit-level=low` is a hard CI failure; lockfile
integrity is asserted; the audit also runs weekly, because advisories are
published against code that has not changed.

### 8. Browser-originated abuse

A hostile page driving the gateway from a visitor's browser.

Controls: exact-origin CORS allowlist (no wildcard matching, no suffix
matching); `Access-Control-Allow-Credentials` never sent under any
configuration; `Content-Type: application/json` required, which a plain HTML
form cannot set, blocking simple-request CSRF; deny-all CSP,
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `no-referrer`,
`Cache-Control: no-store`.

CORS is a browser-enforced control, not an access control. Authentication is the
access control.

---

## Secret handling rules

1. Secrets live only in Cloudflare Worker secrets and GitHub Actions secrets.
2. `wrangler.toml` is committed and public. **No secret may appear in it.** CI
   fails the build if one does.
3. `.env` and `.dev.vars` are gitignored, and CI asserts both that they are
   untracked and that the ignore rules still hold.
4. In CI, secret values are passed on **stdin**, never as command-line
   arguments — an argument is visible in the process table.
5. `OPENAI_API_KEY` is never sent to a client, under any configuration.
6. No secret is ever logged, including at debug level.
7. `PROXY_ACCESS_TOKEN` must be at least 24 characters; generate with
   `openssl rand -hex 32`.

---

## Deployment security checklist

- [ ] `PROXY_ACCESS_TOKEN` is 32+ random bytes, not a memorable string
- [ ] `ALLOWED_ORIGIN` names real origins, not `*`
- [ ] `ALLOWED_MODELS` restricted to models you intend to pay for
- [ ] Cloudflare API token scoped to Workers on one account — not a Global API Key
- [ ] Cloudflare rate-limiting binding enabled
- [ ] Provider-side spending limits set
- [ ] `GATEWAY_URL` set, so post-deployment verification actually runs
- [ ] `/health` returns `ready: true`; an unauthenticated call returns 401
- [ ] Token rotation rehearsed using the comma-separated list
- [ ] Workers Logs reviewed; alerting on 401/429/502 rates

---

## Known limitations

These are design trade-offs, documented rather than hidden.

1. **Rate limiting is per-isolate by default.** Cloudflare runs many isolates,
   so the real global ceiling exceeds `RATE_LIMIT_PER_MINUTE`. It stops runaway
   clients and slows brute force; it is not a billing control. Use the
   Cloudflare binding for a globally enforced limit.

2. **A single shared token cannot identify users.** Per-user quotas or
   revocation require per-user tokens issued by your own backend.

3. **`X-Forwarded-For` is client-controlled.** `CF-Connecting-IP` is preferred
   and is what Cloudflare sets. Behind a different proxy, ensure it is set by
   trusted infrastructure or IP-based limiting can be evaded.

4. **The gateway does not inspect prompt or completion content.** No moderation,
   no PII filtering, no jailbreak detection. Add those separately if required.

5. **Model availability is not validated.** The gateway enforces the allowlist
   you configure; it cannot know which model IDs your provider account serves.
   An unavailable ID fails at the provider and surfaces as 502.

---

## Supported versions

| Version | Supported |
|---|---|
| 1.0.x | Yes |

Security fixes are released against the latest version.
