# Edge Security Architecture

## Target state

```text
Internet
  |
  v
Managed DNS / CDN / WAF
  |-- DDoS mitigation
  |-- managed WAF
  |-- bot classification / challenge
  |-- IP reputation / allow / deny / quarantine
  |-- rate limiting
  |-- geo / ASN policy
  |-- response-header transforms
  |-- cache / origin shielding
  |-- security analytics / logs / alerts
  |
  +--> static origin: GitHub Pages (current, bypassable origin limitation)
  |
  +--> API/admin origin(s): future/private-capable origin with authenticated origin access
```

Cloudflare is the reference implementation. The policy model in `infra/edge/policies/baseline.json` is provider-neutral and is intended to map to Fastly, CloudFront + AWS WAF, Azure Front Door, or another enterprise edge.

## Control ownership

| Control | Edge provider | GitHub Actions | Application | Manual operator |
|---|---:|---:|---:|---:|
| L3/L4/L7 DDoS | yes | no | no | enable/plan selection |
| managed WAF | yes | validate/plan/apply | input validation remains | credentials/approval |
| custom WAF | yes | validate/plan/apply | no | promotion approval |
| bot challenges | yes | validate/plan/apply | optional app telemetry | feature/plan enablement |
| IP reputation | yes | validate policy | no | list stewardship |
| route rate limits | yes | validate/plan/apply | app rate limits remain defense-in-depth | threshold approval |
| geo/ASN rules | yes | validate/plan/apply | no | disabled by default; explicit enablement |
| response headers | yes | validate config | app owns route-specific exceptions | rollout approval |
| origin authentication | provider/origin dependent | deploy templates | API origin must validate token/mTLS if used | origin configuration |
| DNS cutover | provider | no | no | yes, always manual here |
| logging/export | yes | config validation | origin logs | destination/retention setup |
| emergency bypass | yes | rollback workflow/plan | app fallback | operator decision |

## Policy order

1. explicit trusted allow/skip exceptions with narrow scope
2. verified crawler handling
3. emergency rules with mandatory expiry
4. malformed/protocol/method checks
5. IP reputation and quarantine signals
6. geo/ASN policy if explicitly enabled
7. bot classification/challenge
8. route-specific rate limiting
9. managed WAF
10. cache/header transforms

A provider's actual evaluation phases may differ; mappings must preserve the security intent rather than blindly preserve numeric order.

## Safe rollout

- Phase 0: baseline logging and analytics only.
- Phase 1: custom detections in `log` where supported; otherwise narrow managed challenges.
- Phase 2: managed challenge for suspicious automation and high-confidence anomalies.
- Phase 3: block only confirmed malicious signatures/sources after review.
- Phase 4: tighten thresholds based on measured legitimate p99 traffic.

Broad geo blocking, broad ASN blocking, blanket non-browser blocking, and blanket automation denial are prohibited by default.

## DDoS and caching

Use provider-managed DDoS protection. Cache static immutable assets aggressively when filenames are versioned; cache HTML conservatively so deployments propagate quickly. Never cache authentication, personalized, checkout, webhook, admin, or other sensitive dynamic responses unless the application explicitly marks them safe.

For GitHub Pages the provider acts as a caching proxy, not a private origin shield. For future API origins, use authenticated origin pulls, mTLS, signed origin headers, provider egress allow lists, private links, or equivalent controls.

## Header strategy

Initial edge policy:

- HSTS: `max-age=31536000; includeSubDomains` after confirming every subdomain supports HTTPS. Add `preload` only after operator review.
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`
- `Cross-Origin-Opener-Policy: same-origin-allow-popups`
- `Cross-Origin-Resource-Policy: same-site`
- `Content-Security-Policy-Report-Only` first, derived from the repository's existing `_headers` baseline.
- Frame protection through CSP `frame-ancestors`; retain `X-Frame-Options: SAMEORIGIN` as legacy defense-in-depth until compatibility testing permits removal.
- remove/minimize provider/origin-identifying headers where the provider supports it.

## Observability

Minimum metrics:

- request count by action: allow, log, challenge, block, rate-limit
- rule matches by rule ID
- challenge solve/fail rates
- country, ASN, reputation category and user-agent class
- origin 4xx/5xx, latency and availability
- cache hit ratio
- authentication/form/API abuse signals
- configuration version, drift, certificate state and DNS health

Do not export authorization headers, cookies, passwords, full sensitive query strings, or request bodies by default. Prefer field-level suppression. Where analytics do not require full IP addresses, pseudonymize or truncate them downstream.

## Emergency mode

Emergency high-security mode is opt-in and time-bounded. It may increase challenge sensitivity, reduce route-specific limits, temporarily restrict admin/API geography/ASNs, and block confirmed abusive indicators. Every temporary rule requires an owner, rationale and expiry. The emergency switch must not become a permanent default-deny perimeter.

## Provider portability

The neutral policy schema captures identifier, description, scope, priority, action, rollout mode, logging level, exceptions, expiry, owner and rationale/change ticket. Provider adapters may use native expression languages, managed rule IDs, bot scores and rate-limit primitives, but the source-of-truth security intent remains reviewable in the neutral policy document.
