# Edge Provider Setup

Reference provider: Cloudflare. DNS/provider actions in this document are manual; repository automation does not claim they have been performed.

## Operator-supplied values

- Cloudflare account ID
- Cloudflare zone ID for `clearglassinc.com`
- zone name: `clearglassinc.com`
- public hostname: `www.clearglassinc.com`
- current GitHub Pages target shown in GitHub Pages settings/DNS documentation
- optional API/admin hostnames and their real origins
- security-log destination details
- trusted IP/CIDR entries, if any
- monitoring service IPs, if any
- alerting destination

## Cloudflare zone and DNS

1. Add/select `clearglassinc.com` in the correct Cloudflare account.
2. Import/verify all existing DNS records before changing nameservers. Email records are especially critical: preserve MX, SPF, DKIM, DMARC and verification records exactly.
3. If Cloudflare is not authoritative DNS yet, change registrar nameservers only after the imported zone is verified.
4. Confirm DNSSEC state. If DNSSEC is enabled at the registrar, follow Cloudflare's migration procedure rather than leaving stale DS records.
5. Configure the `www` record for the current Pages target and set it to **Proxied** only during the controlled cutover window.
6. Keep mail and non-HTTP service records DNS-only unless their service explicitly supports proxying.

Do not create speculative origin records. Use the actual target shown by GitHub Pages for this repository.

## TLS

- Edge HTTPS: enabled.
- Minimum TLS version: 1.2 unless an operator-approved compatibility exception exists.
- TLS 1.3: enabled.
- Automatic HTTPS rewrites/redirect: enable after verifying there are no intentional HTTP-only dependencies.
- HSTS: introduce after HTTPS validation on all covered subdomains. Do not add `preload` until every subdomain is permanently HTTPS-ready.

For GitHub Pages, Cloudflare-to-origin TLS must remain compatible with GitHub's Pages certificate behavior. Validate the origin certificate before selecting a strict TLS mode. Do not disable origin certificate validation to hide a certificate mismatch.

## WAF and bot controls

1. Enable provider managed WAF capabilities available to the account plan.
2. Deploy repository custom rules in observation mode first where supported.
3. Keep verified crawlers and explicitly trusted monitoring services out of generic bot challenges.
4. Enable managed challenge before hard block for uncertain automation.
5. Do not turn on broad country/ASN blocking until explicitly approved.
6. If Bot Management/Super Bot Fight Mode is available, enable it only after reviewing the provider's interaction with custom bot rules.

## DDoS

Use the provider's managed network and application DDoS controls. Do not attempt a synthetic DDoS test. Validate only with ordinary functional traffic and provider analytics. During a real attack, use the emergency mode described in `docs/incident-response-edge.md`.

## Headers

Apply the transform rules produced by `infra/edge/`. Start CSP in report-only mode. Compare browser console violations against known repository integrations before enforcement.

## Logging

Enable security-event export if the plan supports it. Recommended baseline retention:

- high-cardinality raw security events: 14-30 days
- normalized security metrics: 90 days
- incident evidence: case-specific, access-controlled retention
- audit/configuration changes: at least 1 year where practical

Suppress or redact cookies, authorization headers, passwords, form bodies, and sensitive query values. Prefer sampled request logs over full raw HTTP logging for the static public site.

## Future dynamic API origin

For any non-Pages API/admin host:

- terminate public access at the edge
- use authenticated origin pulls, mTLS, signed origin headers, provider egress IP allow lists, private networking, or an equivalent origin control
- validate the origin-auth mechanism at the application/load-balancer layer
- disable direct public ingress if the hosting platform supports it
- rate-limit login, reset, search, contact, admin, API and webhook routes independently

## Alternative providers

- Fastly: map neutral rules to VCL/Next-Gen WAF, edge ACLs, rate counters and logging endpoints.
- AWS: Route 53 or external DNS -> CloudFront -> AWS WAF -> S3/ALB/API origin, with Origin Access Control for S3 and private/allow-listed dynamic origins.
- Azure: DNS -> Front Door Premium WAF -> Storage/App Service/APIM, using Private Link where supported.

Provider migration must preserve the neutral policy intent and rollout states rather than copying Cloudflare expressions verbatim.
