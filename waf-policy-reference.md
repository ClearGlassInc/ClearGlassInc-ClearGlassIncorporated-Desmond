# WAF Policy Reference

Source of truth: `infra/edge/policies/baseline.json` validated by `infra/edge/policy.schema.json`.

## Rollout semantics

- `observe`: record a match without terminating the request where provider capabilities permit.
- `challenge`: use managed challenge for uncertain malicious/automated traffic.
- `block`: terminate only high-confidence malicious traffic after review.
- `allow`: narrow trusted exception; never use as a broad bypass.
- `rate_limit`: apply route-specific request controls.

A rule may declare a different provider-native action while retaining the neutral rollout state.

## Baseline categories

| Category | Baseline behavior |
|---|---|
| SQL injection | managed WAF, observe then block high-confidence matches |
| XSS | managed WAF, observe then block high-confidence matches |
| local/remote file inclusion | managed WAF, observe then block |
| command injection | managed WAF, observe then block |
| path traversal | custom + managed detection, observe/challenge first |
| protocol anomalies | managed WAF, observe/challenge |
| malformed requests | challenge/block based on confidence |
| suspicious user agents | log or challenge; never blanket-deny automation |
| exploit signatures | managed rules, promote on evidence |
| scanner/probing behavior | challenge/rate-limit, then block repeat offenders |
| unexpected methods | allow GET/HEAD/OPTIONS on static host; route-specific methods elsewhere |
| oversized request metadata | conservative limits; provider/app body-size limits remain authoritative |

## Bot decision model

Order of precedence:

1. explicit narrow trusted exception
2. provider-verified search crawler
3. approved monitoring/internal automation identity
4. normal browser
5. headless/automation signal
6. suspicious automation
7. credential-stuffing or high-volume scraping pattern
8. repeated challenge failure

Actions are configurable: allow/skip, log, managed challenge, interactive challenge, rate-limit, block.

User-agent text alone is not trustworthy. Where available use provider-verified bot identity, bot score, JA3/JA4/fingerprint data, behavior and reputation signals.

## IP reputation

- Provider threat intelligence is a signal, not the sole basis for a permanent deny.
- Tor policy defaults to challenge, not permanent block.
- VPN/proxy/hosting-provider signals default to log/challenge depending on route sensitivity.
- Trusted IPs must be explicit CIDRs with owner and review date.
- Temporary quarantines require expiry timestamps.
- Permanent deny entries require confirmed abuse evidence and review.

## Route rate limits

Defaults are intentionally generous and should be tuned from observed legitimate p99 traffic.

| Route class | Example | Baseline per-IP policy |
|---|---|---:|
| static assets | `/assets/*`, common extensions | 600/min observe |
| HTML documents | `/`, `/*.html` | 120/min observe |
| login/auth | `/api/auth/*`, `/login*` | 20/min challenge/rate-limit |
| password reset | `/api/*reset*` | 8/10 min challenge/rate-limit |
| search | `/api/search*`, `/search*` | 60/min observe |
| contact/forms | `/api/contact*`, `/contact*` | 10/10 min challenge/rate-limit |
| APIs | `/api/*` | 120/min observe; route-specific overrides required |
| admin | `/admin*` | 60/min plus optional geo/ASN restriction |
| webhooks | `/api/webhook*`, `/webhooks*` | source-auth aware; do not challenge valid signed webhooks |

For authenticated dynamic origins, prefer identity/session/token counters over source IP when supported. Never replace application-side authentication or authorization with edge rate limiting.

## Rate-limit/provider failure behavior

- A CI/API control-plane failure must fail closed for configuration change: no new Terraform apply occurs and the last successfully deployed provider policy remains authoritative.
- Do not respond to a provider API failure by installing a broad `allow` rule or disabling the WAF.
- If a provider-managed rate-limit service or data plane is impaired, preserve application-side authentication, authorization, account lock/risk controls, and local route limits as defense in depth for dynamic origins.
- Static GitHub Pages delivery does not depend on an application rate-limit datastore; edge-rate-limit unavailability therefore must not trigger a repository-side denial policy.
- For future APIs, sensitive routes such as login, password reset, admin, forms, and webhooks must retain server-side abuse controls so provider rate limiting is supplemental rather than a single point of failure.
- During a provider-wide outage, follow `docs/incident-response-edge.md` and `docs/dns-cutover-runbook.md`; use the recorded DNS rollback only when the operational risk of bypassing the edge is explicitly accepted.

## Geo/ASN

All geographic deny/challenge controls are disabled by default. Administrative/API routes may enable narrow geo/ASN rules after operator approval. Emergency regional restrictions must expire automatically or have an explicit review timestamp.

## Headers and CSP

The initial CSP is Report-Only and derived from the existing repository header baseline:

```text
default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'self';
form-action 'self' https://formspree.io;
script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com;
font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:;
img-src 'self' data: blob: https:; media-src 'self' https:;
connect-src 'self' https://formspree.io https://api.github.com;
frame-src 'self' https://www.youtube-nocookie.com;
manifest-src 'self'; worker-src 'self' blob:; upgrade-insecure-requests
```

Do not promote to enforcing CSP until violations from all supported pages have been reviewed and inline script/style handling has been addressed.

## Change-control requirements

Every broad promotion to block must record:

- rule ID/version
- owner
- rationale/change ticket
- observed match volume
- false-positive review
- rollback command/procedure
- operator and timestamp

Emergency rules additionally require an expiry.
