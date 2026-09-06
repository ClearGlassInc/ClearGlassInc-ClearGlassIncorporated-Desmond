# Edge Incident Response Runbooks

These runbooks cover the managed edge/CDN/WAF layer. Preserve evidence and make one reversible change at a time.

## 1. Suspected DDoS

Detection: abrupt request/connection surge, provider DDoS alert, cache/origin saturation, rising 5xx/latency.

Containment: confirm managed DDoS is active; increase caching for safe static objects; activate time-bounded high-security/challenge mode; tighten only the attacked route class; protect API/admin origins independently.

Verification: origin load falls, cache hit ratio recovers, legitimate success rate remains acceptable, challenge solve rate is sane.

Recovery: unwind temporary rules in reverse order; restore normal thresholds; retain attack metrics.

Review: identify attack vectors, provider mitigations, origin bottlenecks and threshold changes.

## 2. Credential stuffing

Detection: login failure surge, distributed login attempts, repeated usernames/accounts, bot/reputation signals.

Containment: route-specific login rate limit; managed challenge on suspicious automation; application lockout/risk checks; preserve verified monitoring/webhook traffic.

Verification: successful legitimate logins continue; abusive attempts decline; no broad customer lockout.

Recovery: remove emergency blocks; keep sustainable login controls; force credential resets only when account compromise evidence exists.

Review: affected accounts, breached-credential controls, MFA, device/risk signals.

## 3. Malicious scraping

Detection: high-volume sequential crawling, low cache diversity, datacenter ASN concentration, headless fingerprints, repeated challenge failures.

Containment: challenge/rate-limit suspicious automation; quarantine confirmed sources with expiry; protect expensive routes/assets; never block verified search crawlers by user-agent string alone.

Verification: scraper throughput falls without SEO/monitoring regression.

Recovery: expire temporary lists; retain tuned rate limits.

Review: content exposure, crawl patterns, API/data minimization.

## 4. WAF false positive

Detection: support report, sudden legitimate 403/challenge spike, known-good request matches a rule.

Containment: move the specific rule to log/observe or add the narrowest route/source exception; do not disable the entire WAF unless necessary.

Verification: reproduce the previously blocked legitimate request and confirm unrelated protections remain active.

Recovery: tune expression/managed-rule override, re-stage as observe/challenge, document exception owner.

Review: test case must be added before re-enforcement.

## 5. Legitimate users accidentally blocked

Detection: geographic/ASN/customer cluster complaints or elevated challenge failures.

Containment: disable the narrow offending geo/ASN/IP rule first; remove emergency rules past expiry; keep managed WAF active.

Verification: representative users regain access.

Recovery: use challenge rather than deny for uncertain signals.

Review: confirm source of false classification.

## 6. Origin compromise

Detection: unexpected content, unauthorized deployment, origin logs/config changes, integrity alerts.

Containment: do not rely on WAF as remediation. Freeze deployments, revoke compromised credentials, isolate dynamic origin, enable maintenance/static fail-safe at edge if available, preserve evidence.

Verification: trusted artifact/hash/deployment restored; secrets rotated; origin access path audited.

Recovery: redeploy from trusted commit/build; rotate origin-auth credentials; re-enable traffic gradually.

Review: root cause, credential path, CI integrity, provenance and origin-lockdown gaps.

## 7. Edge provider outage

Detection: provider status/telemetry plus multi-network failures while origin remains healthy.

Containment: if outage is prolonged and risk-approved, execute DNS-only rollback to the recorded origin path. Do not improvise DNS targets.

Verification: external resolvers and HTTPS checks succeed.

Recovery: return to proxy only after provider stability and certificate readiness are confirmed.

Review: secondary provider/traffic-manager requirements.

## 8. Emergency lockdown

Detection: active exploit/abuse where normal challenge/rate limits are insufficient.

Containment: enable emergency policy with explicit owner, reason and expiry; restrict only affected routes/geographies/ASNs; challenge uncertain traffic; block confirmed malicious indicators.

Verification: malicious traffic drops and critical legitimate paths remain usable.

Recovery: automatically/manual-expire temporary policy; restore staged baseline.

Review: no emergency rule may remain indefinitely.

## 9. DNS rollback

Follow `docs/dns-cutover-runbook.md`. Restore the exact prior DNS/proxy state; verify Pages custom domain and TLS.

## 10. Certificate/TLS failure

Detection: browser/curl certificate errors, edge/origin handshake failures, certificate expiration alert.

Containment: identify whether failure is visitor->edge or edge->origin. Do not disable certificate verification as a shortcut. Roll back recent TLS/DNS changes if needed.

Verification: chain, hostname, validity period, TLS versions and origin SNI all pass.

Recovery: renew/reissue through provider/GitHub process; return strict validation.

## 11. Revert bad WAF policy

Containment: set the offending rule/action back to observe or disable only that rule; apply the previous reviewed plan/version.

Verification: smoke tests pass; security-event flow continues.

Recovery: open a correction PR and add a regression test.

## 12. Rotate credentials and allow lists

Detection/trigger: suspected token exposure, staff/provider change, periodic access review.

Containment: revoke old provider token; issue least-privilege replacement; rotate any origin shared secret; remove stale CIDRs immediately when ownership is no longer trusted.

Verification: CI plan succeeds with new credential; old credential is rejected; trusted integrations still function.

Recovery: update secret metadata/owner/review date; never commit values.

## Post-incident minimum record

- UTC timeline
- policy/config versions and commit SHA
- operator(s)
- impacted host/routes
- edge actions and match IDs
- origin impact
- evidence retention location
- customer/security impact
- root cause
- corrective actions and owners
