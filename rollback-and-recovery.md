# Edge Rollback and Recovery

## Principles

- Roll back the smallest changed layer first.
- Prefer moving a rule from block/challenge to observe over destroying the whole perimeter.
- Never make DNS, TLS and WAF changes simultaneously during incident recovery unless the failure clearly spans all three.
- Preserve logs, plan output, commit SHA and operator notes.

## WAF rollback

Terraform-managed edge controls:

```bash
cd infra/edge
terraform plan -var-file=terraform.tfvars -out=edge-rollback.tfplan
terraform apply edge-rollback.tfplan
```

For a bad enforcement promotion, restore the previous action values in version control or `terraform.tfvars`, return custom rules to `log`/disabled state as supported, and apply a reviewed plan.

If provider features do not support log-only mode on the current plan, disable the narrow rule or move it to managed challenge rather than creating a broad allow.

## Configuration version rollback

```bash
git log --oneline -- infra/edge docs/edge-security-*.md
git revert <bad-edge-commit>
```

Open the revert through the protected PR process where required. A repository revert changes IaC only; provider state changes only after an authorized apply.

## Emergency provider-side rollback

If GitHub Actions/provider API deployment is unavailable, an authorized operator may use the provider dashboard to:

1. disable the specific custom rule/rate limit/transform
2. disable emergency mode
3. restore the previous known-good rule version if available
4. record every manual mutation
5. reconcile Terraform state/configuration before the next apply

Manual provider changes create drift. Run `terraform plan` immediately after recovery and either codify or revert the drift.

## DNS rollback

Use the exact pre-cutover DNS snapshot and `docs/dns-cutover-runbook.md`. For the current GitHub Pages architecture the simplest edge bypass rollback is usually changing the web record from proxied to DNS-only while preserving its correct Pages target. Do not alter mail records.

## TLS recovery

- Visitor-to-edge failure: inspect edge certificate/hostname/issuance and DNS validation.
- Edge-to-origin failure: inspect GitHub Pages certificate state, SNI, hostname and selected TLS mode.
- Never use insecure origin TLS as a permanent fix.

## Static-origin recovery

Current Pages recovery remains Git-based:

```bash
git revert <site-merge-commit>
git push origin main
```

Respect branch protection/PR requirements. The edge layer must not cache broken HTML indefinitely; purge affected URLs after a legitimate rollback if needed.

## Dynamic-origin recovery

For future API/admin origins:

- isolate compromised or unhealthy origin
- fail over only to a preconfigured trusted origin
- rotate origin-auth credentials after compromise
- verify health/authentication before restoring edge traffic
- purge sensitive cached responses if a cache-control mistake occurred

## Recovery verification

```bash
python3 infra/edge/scripts/validate_policy.py
python3 infra/edge/scripts/smoke_test.py --base-url https://www.clearglassinc.com
python3 infra/edge/scripts/negative_security_test.py --base-url https://www.clearglassinc.com --dry-run
```

Then verify edge security-event ingestion, certificate state, DNS resolution, cache behavior and representative user flows.
