# ClearGlass Edge Security

Provider-neutral perimeter policy with a Cloudflare Terraform reference implementation.

**This directory does not change DNS by itself.** Terraform manages supported edge resources only after an operator supplies the zone/account IDs and a least-privilege provider token. DNS cutover remains the manual procedure in `docs/dns-cutover-runbook.md`.

## Layout

- `policy.schema.json` - JSON Schema for neutral policies
- `policies/baseline.json` - baseline WAF/bot/reputation/rate/geo/header intent
- `observability.example.json` - provider-neutral dashboards, alerts, retention and privacy controls
- `main.tf` - provider and shared locals
- `variables.tf` - typed configuration and safe defaults
- `waf.tf` - custom WAF and managed-WAF entry points
- `rate_limits.tf` - route-specific rate limits
- `headers.tf` - edge response-header transforms
- `logging.tf` - optional privacy-minimized firewall-event Logpush
- `variables.example` - operator input template; never put secrets here
- `scripts/validate_policy.py` - schema/safety validation without external dependencies
- `scripts/smoke_test.py` - ordinary functional checks
- `scripts/negative_security_test.py` - dry-run by default; low-volume security probes only

## Critical state-ownership rule

Cloudflare ruleset phases are zone-level entry points. This repository already contains `clearglass-commerce/infra/cloudflare`, which can own `http_request_firewall_custom`, `http_request_firewall_managed`, and `http_ratelimit` for the same zone.

**Do not enable the corresponding resources in two Terraform states.** Before enabling this perimeter module for a phase that already exists, inspect the live zone and the existing Terraform state, then consolidate/import the rules into one authoritative state. The example configuration keeps every provider-mutating feature group disabled for this reason.

## Safe defaults

- every Terraform feature group is disabled in `variables.example` for the first plan
- geo/ASN enforcement disabled
- broad blocking prohibited by policy validation
- suspicious automation uses observe/challenge before block
- verified search crawlers are excluded from generic automation handling
- managed WAF is optional until account-plan support and state ownership are confirmed
- CSP is Report-Only when header transforms are enabled
- Logpush is optional and requires an operator-created destination
- full client-IP export is disabled by default
- all emergency controls must be short-lived and documented

## Requirements

- Terraform >= 1.6 (CI currently installs a checksum-verified Terraform 1.14.6 binary)
- Cloudflare provider ~> 4.40 to remain consistent with existing repository Cloudflare IaC
- Python >= 3.11 for validation/test scripts
- an edge-provider account/zone with the features required by the selected variables

## GitHub Actions environments

Create separate environments so planning never receives write credentials and production mutation can require reviewers:

- `edge-staging-plan` - read/plan token, no production approval gate
- `edge-staging` - apply token; protect as appropriate
- `edge-production-plan` - read/plan token, no production approval gate
- `edge-production` - **write/apply token and required reviewers**

The workflow never applies on ordinary pushes or pull requests. `apply`/`rollback` are manual dispatch operations; production apply is restricted to `main`. A rollback requires a full known-good 40-character commit SHA plus a change-ticket/incident reference.

## Required secret names

Never commit values.

Plan environments:

- `CLOUDFLARE_EDGE_PLAN_TOKEN` - read plus only the minimum permissions Terraform needs to refresh/plan the resources under review
- `EDGE_LOGPUSH_DESTINATION` - only if Logpush is enabled; treat as secret if the destination contains credentials

Apply environments:

- `CLOUDFLARE_EDGE_APPLY_TOKEN` - write permissions only for the edge resources intentionally managed by this module
- `EDGE_LOGPUSH_DESTINATION` - same reviewed destination when Logpush is enabled

Non-secret environment variables used by both plan/apply environments:

- `EDGE_CLOUDFLARE_ACCOUNT_ID`
- `EDGE_CLOUDFLARE_ZONE_ID`
- `EDGE_ZONE_NAME`
- `EDGE_PUBLIC_HOSTNAME`
- optional `EDGE_API_HOSTNAME`
- optional `EDGE_ADMIN_HOSTNAME`
- optional JSON arrays: `EDGE_TRUSTED_IPV4_CIDRS_JSON`, `EDGE_TRUSTED_IPV6_CIDRS_JSON`, `EDGE_TRUSTED_ASNS_JSON`, `EDGE_ALLOWED_COUNTRIES_JSON`, `EDGE_DENIED_COUNTRIES_JSON`, `EDGE_CHALLENGE_COUNTRIES_JSON`
- optional booleans: `EDGE_LOG_FULL_CLIENT_IP`, `EDGE_HSTS_INCLUDE_SUBDOMAINS`, `EDGE_HSTS_PRELOAD`

## Cloudflare token permissions

Scope tokens to the exact account and zone. Cloudflare's current API permission model exposes specific permissions such as Zone WAF Read/Write, Zone Transform Rules Read/Write, Logs Read/Write, and Zone Read. Grant only the permissions required by the feature groups you actually enable and by `terraform plan/apply`.

This module intentionally contains **no Cloudflare DNS resource**, so DNS write permission is not required for this implementation. DNS cutover is manual. Do not grant DNS write merely for convenience.

## Local validation

```bash
python3 infra/edge/scripts/validate_policy.py
python3 tests/test_edge_security_policy.py -v
terraform -chdir=infra/edge fmt -check -recursive
terraform -chdir=infra/edge init -backend=false
terraform -chdir=infra/edge validate
```

The CI validator also rejects committed `terraform.tfvars`, Terraform state, high-confidence secret patterns, unsafe broad allow/block policies, enabled baseline geo enforcement, and permanent reputation-only denies.

## Plan

```bash
cd infra/edge
cp variables.example terraform.tfvars
# Fill identifiers and reviewed, non-secret policy inputs.
# Keep feature groups false for the first state-ownership inspection plan.
export CLOUDFLARE_API_TOKEN='...'
terraform init
terraform plan -var-file=terraform.tfvars -out=edge.tfplan
terraform show -no-color edge.tfplan
```

Do not apply a plan you have not reviewed.

## Apply

Preferred path: manually dispatch `.github/workflows/edge-security.yml` with `operation=apply`. The workflow creates a reviewable plan artifact, records its SHA-256, waits at the protected apply environment, recomputes the plan with the protected token, and refuses the apply if the plan hash changes.

Local operator path, when explicitly authorized:

```bash
terraform apply edge.tfplan
```

Provider-side prerequisites, DNS and TLS configuration must already be correct. A successful Terraform apply does not prove DNS traffic is proxied through the edge.

## Rollback

Restore the last reviewed policy/configuration, plan and apply it. For an acute false positive, disable or return only the offending rule to observe/challenge rather than removing the entire perimeter. The workflow's `rollback` operation requires a full known-good commit SHA. See `docs/rollback-and-recovery.md`.

## GitHub Pages constraint

The current static origin cannot validate a secret edge header, require mTLS, or restrict source IPs. The proxy protects traffic sent to `www.clearglassinc.com`, but the GitHub Pages origin cannot be made truly private. For non-bypassable origin security, move the built static artifact to an origin supporting authenticated/private edge access.

## Provider mapping

The JSON policy is intentionally not Cloudflare expression syntax. For another provider, implement a renderer/adapter that preserves:

- rule IDs and descriptions
- scope/priority
- action and rollout mode
- exceptions
- owner/rationale
- expiry for temporary controls
- logging/privacy requirements

Do not port vendor-specific bot scores or managed-rule IDs as if they were portable semantics.
