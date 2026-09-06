# DNS / Edge Cutover Runbook

No DNS change is performed by repository automation. Execute this runbook manually with authorized access to the DNS/edge provider.

## Pre-cutover

- [ ] Confirm GitHub Pages currently serves the intended site and the root `CNAME` remains `www.clearglassinc.com`.
- [ ] Record current DNS records, TTLs, nameservers, DNSSEC state, certificate state and Pages custom-domain settings.
- [ ] Export or screenshot the full DNS zone before edits.
- [ ] Confirm MX/SPF/DKIM/DMARC records are preserved.
- [ ] Confirm Cloudflare zone/account IDs and least-privilege API token are available for Terraform planning.
- [ ] Apply/validate edge policies in observation mode only.
- [ ] Configure security analytics/log destination before enforcement.
- [ ] Confirm verified crawler handling and trusted-monitoring exceptions.
- [ ] Run `python3 infra/edge/scripts/validate_policy.py`.
- [ ] Run smoke tests against the existing public site and, if available, a staging/proxy hostname.
- [ ] Lower the public web-record TTL ahead of the window if operationally appropriate; do not lower unrelated records.
- [ ] Establish a rollback decision owner and communication channel.

## Cutover

1. In the edge provider, confirm the zone is active and certificate issuance is healthy.
2. Verify the `www` record points to the actual GitHub Pages target currently required by GitHub.
3. Change only the web record to proxied/edge-enabled status.
4. Do not change the repository `CNAME` unless the public hostname itself is changing.
5. Keep WAF custom rules in log/observe or conservative managed-challenge mode.
6. Confirm HTTPS redirect behavior.
7. Confirm the browser certificate covers `www.clearglassinc.com` and chains correctly.
8. Confirm ordinary HTML, CSS, JS, images, fonts, forms and client-side API calls still function.
9. Confirm response headers are being added by the edge.
10. Confirm edge analytics register requests.

## Post-cutover validation

```bash
curl -fsSIL https://www.clearglassinc.com/
curl -fsS https://www.clearglassinc.com/ -o /dev/null
python3 infra/edge/scripts/smoke_test.py --base-url https://www.clearglassinc.com
python3 infra/edge/scripts/negative_security_test.py --base-url https://www.clearglassinc.com --dry-run
```

Verify manually:

- [ ] homepage and representative internal pages load
- [ ] static assets return expected content types
- [ ] cache status changes appropriately on repeated cacheable requests
- [ ] Formspree submission path is not broken
- [ ] public GitHub API-backed UI components are not broken
- [ ] YouTube privacy-enhanced embeds still render
- [ ] verified search crawlers are not generically challenged
- [ ] no unexpected 403/429 spike appears for normal users
- [ ] CSP report-only violations are reviewed
- [ ] edge logs do not retain cookies/authorization secrets
- [ ] no certificate/DNS errors occur from multiple external resolvers

## DNS propagation checks

Use at least two independent resolvers or networks. Example local commands:

```bash
nslookup www.clearglassinc.com
dig +short www.clearglassinc.com A
dig +short www.clearglassinc.com AAAA
dig +trace www.clearglassinc.com
```

Do not treat one cached resolver as proof of global propagation.

## Rollback triggers

Rollback the proxy/DNS cutover if any of the following persists after a narrowly scoped rule disable:

- certificate validation failure
- broad legitimate-user 403/429 responses
- broken primary navigation/assets
- severe form/API integration breakage
- provider routing outage
- origin errors materially above baseline

## DNS rollback

1. Set the web record back to DNS-only or restore the exact previously recorded DNS state.
2. Disable custom edge enforcement rules before making multiple simultaneous changes.
3. Re-check the GitHub Pages custom-domain status and HTTPS certificate.
4. Validate direct public-site behavior.
5. Preserve edge logs and the policy version for incident review.
6. Restore normal TTL only after stability is confirmed.

Do not delete the zone or nameserver configuration as an emergency first response; that creates a larger recovery problem than disabling proxy/enforcement.
