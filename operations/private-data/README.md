# Private Data Operations

This directory defines safe handling rules for private data collection integrations.

## Non-negotiable controls

- Never commit credentials, API keys, access tokens, session cookies, personal identifiers, financial records, or raw private datasets.
- Store secrets only in GitHub Actions encrypted secrets or an approved external secret manager.
- Collect only data with a documented lawful purpose, explicit authorization, and minimum necessary scope.
- Record source, consent/authority, retention period, and deletion procedure for every collection job.
- Encrypt data in transit and at rest.
- Keep public website builds separated from private processing systems.
- Publish only aggregated or sanitized outputs reviewed for disclosure risk.

## Repository layout

- `schemas/` — metadata contracts and validation schemas.
- `policies/` — collection, retention, and access-control policies.
- `samples/` — synthetic examples only; never real personal data.
- `reports/` — generated audit summaries with sensitive values removed.

## Deployment boundary

GitHub Pages is a public static hosting surface. It must not receive private datasets or secrets. Any private collector must run in a separately secured service and expose only authorized, sanitized API responses.
