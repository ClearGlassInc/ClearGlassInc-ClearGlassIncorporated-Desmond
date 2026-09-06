# ClearGlass Enterprise Patch & Deploy

A single, reusable, event-driven control plane for patching and deploying every
ClearGlassInc repository under a **low** risk tolerance and **high**
auditability posture. It detects a change, classifies its risk and blast
radius, validates it in isolation, promotes it through staged gates with human
approval, deploys with automatic rollback, and writes an immutable audit trail.
**Production changes never proceed without explicit verification and confidence
thresholds.**

Core invariant (same spirit as the commerce OS safety model):
**read-only analysis → draft → human approval → execution — every material
action logged.**

## What ships in this repo

| Artifact | Path | Role |
|---|---|---|
| Reusable workflow | `.github/workflows/enterprise-patch-deploy.yml` | The 8-phase control plane, callable org-wide via `workflow_call` |
| Triage + gate engine | `scripts/patch_deploy/risk_score.py` | Stdlib-only risk score + confidence gate (unit-tested) |
| Engine tests | `tests/test_patch_deploy_risk.py` | Covers the confidence-threshold logic + stop-loss guardrails |
| Per-repo config schema | `.github/enterprise-patch-deploy/config.schema.json` | JSON Schema for each repo's `.github/patch-deploy.yml` |
| Per-repo config example | `.github/enterprise-patch-deploy/config.example.yml` | Copy → `.github/patch-deploy.yml`, trim to overrides |
| Repo criticality matrix | `.github/enterprise-patch-deploy/repo-inventory.example.json` | Blast-radius / exposure inputs for triage |
| Inventory schema | `.github/enterprise-patch-deploy/repo-inventory.schema.json` | JSON Schema for the criticality matrix |

## The 8 phases (mapped to workflow jobs)

1. **Intake + 2. Triage** → job `triage`. Runs `risk_score.py`:
   `risk = CVSS × exposure × data_sensitivity × blast_radius` (0–100), banded to
   **low / medium / high / critical**, then the confidence gate emits a verdict.
   Emits an idempotent `change_id = sha256(content + target)[:16]` and an
   `intake-<id>.json` audit artifact. A `hard_stop` verdict halts here.
3. **Validation** → job `validate` (env `validation`). Runs the repo's configured
   validation commands in isolation with flaky re-runs (up to 3 attempts).
4. **Staging** → job `staging` (env `staging`). Deploy candidate + smoke/synthetic.
5. **Deployment** → jobs `canary` (env `production-canary`, 1 approver) then
   `promote` (env `production`, 2nd approver for high/critical). Only runs for
   `target_env: production` and when `dry_run: false`.
6. **Verification** → job `verify`. Soak + recompute confidence.
7. **Rollback** → job `rollback`. Runs automatically on any phase failure
   (`if: contains(needs.*.result, 'failure')`); must verify health before
   marking success, else escalate.
8. **Post-Deploy Review** → job `audit` (`if: always()`). Assembles an immutable
   change record and uploads it with **≥ 1 year** retention.

## Control model (encoded in `risk_score.py`, unit-tested)

| Confidence | Verdict | Meaning |
|---|---|---|
| `≥ 0.92` **and** risk_class `low` | `autonomous` | Auto-execute + log |
| `0.75 – 0.91`, or risk_class ≥ `medium` | `approval` | Proceed only with human approval |
| `< 0.75`, or any critical gate failure / contradictory results | `hard_stop` | Halt immediately (stop-loss) |

Change types that are **never auto-executed** regardless of score:
`secret_rotation`, `privileged`, `inventory_change`, `risk_model_change`.
Change types that **always require approval**: the above plus `config_change`,
`policy_change`, `production_traffic_shift`.

CLI exit codes (consumed by the workflow): `0` autonomous, `1` approval,
`2` hard-stop, `3` input error.

## Safety guardrails

- **Dry-run default** (`dry_run: true`): triage + validation only, never deploys.
  New change types stay in dry-run until explicitly promoted.
- **Least-privilege**: top-level `permissions: contents: read`; jobs widen only
  what they need (`security-events: write` for SARIF, `id-token: write` for OIDC).
- **OIDC-only creds** for deploy phases — no long-lived secrets, never logged.
- **Concurrency group** per repo + environment prevents overlapping runs.
- **Missing inventory ⇒ worst-case**: a repo with no criticality row is scored as
  internet-facing, customer-data, max-criticality, full-fleet — it escalates
  rather than sneaking through as low risk.
- **Immutable audit**: intake record + final change record uploaded as artifacts
  with 400-day retention.

## Wiring a repo (thin caller)

Add `.github/workflows/patch-deploy.yml` to any ClearGlassInc repo:

```yaml
name: Patch & Deploy
on:
  pull_request:      # PR: triage + validate (dry-run)
  workflow_dispatch: # manual promotion with inputs
    inputs:
      change_type: { required: true, type: string }
      target_env:  { required: false, type: string, default: staging }
      dry_run:     { required: false, type: boolean, default: true }

jobs:
  patch-deploy:
    # Pin to a commit SHA, never a moving branch/tag.
    uses: ClearGlassInc/ClearGlassInc.github.io/.github/workflows/enterprise-patch-deploy.yml@<sha>
    with:
      change_type: ${{ inputs.change_type || 'dependency_bump' }}
      target_env:  ${{ inputs.target_env  || 'staging' }}
      dry_run:     ${{ inputs.dry_run != false }}
    secrets: inherit
```

Then:

1. Copy `.github/enterprise-patch-deploy/config.example.yml` →
   `.github/patch-deploy.yml` and trim it to what differs from the defaults.
2. Add this repo's row to a live `repo-inventory.json` (or accept worst-case).
3. Create the GitHub Environments (`validation`, `staging`, `production-canary`,
   `production`) and set **required reviewers** — 1 for canary, 2 for
   production on high/critical.

## Running the engine locally

```bash
# Triage one change (prints the risk card + decision; exit code = verdict).
python scripts/patch_deploy/risk_score.py \
  --repo clearglass-commerce --change-type security_hotfix --cvss 9.8 \
  --confidence 0.95 \
  --inventory .github/enterprise-patch-deploy/repo-inventory.example.json

# Unit tests (confidence thresholds + stop-loss + idempotency).
python -m pytest tests/test_patch_deploy_risk.py -q
ruff check scripts/patch_deploy/
```

## Production readiness checklist

- [x] Org reusable workflow published (`enterprise-patch-deploy.yml`)
- [x] Risk classification matrix + criticality inventory template
- [x] Confidence-threshold logic unit-tested
- [x] Dry-run default for new change types
- [x] Automatic rollback wired on any phase failure
- [x] Immutable audit artifacts retained ≥ 1 year
- [ ] Production Environments protected with required reviewers *(org setup)*
- [ ] Populate a live `repo-inventory.json` for every active repo *(org setup)*
- [ ] Stop-loss alerts wired to on-call webhook secret *(org setup)*
- [ ] Pin the reusable-workflow SHA in each caller repo *(org setup)*

Items marked *(org setup)* are GitHub org/settings actions that live outside
this repo and require an org admin.
