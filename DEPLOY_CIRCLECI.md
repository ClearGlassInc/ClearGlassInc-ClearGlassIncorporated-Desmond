# CircleCI control-plane pipeline

> **NOT CONNECTED / INERT.** This repository is **not** connected to a CircleCI
> project on circleci.com and there is no CircleCI API token. Nothing in
> `.circleci/config.yml` runs until a human connects the project, defines the
> three contexts and their credentials, and replaces the deploy/rollback
> placeholders. No pipeline has been triggered. Treat this document as a setup
> plan, not a description of a running system.
>
> (This is a separate document from `DEPLOY.md`, which covers the ClearGlass
> Commerce control plane / storefront / admin Render deploy and is unchanged.)

## Purpose

A governed release-control pipeline for the control plane, mirroring the repo's
core safety model: **read-only validation → draft (release manifest) → human
approval (approval jobs) → execution.** No high-impact action (a deploy or a
rollback) runs without an explicit approval hold.

## Architecture

Config: `.circleci/config.yml` (CircleCI 2.1). Logic lives in small POSIX `sh`
scripts under `scripts/ci/` so each step is auditable and testable in isolation.

| Script | Role |
|--------|------|
| `preflight.sh` | Validate pipeline parameter combinations; fail closed |
| `verify-lockfiles.sh` | Require a dependency lockfile for reproducible installs |
| `validate-github-workflows.sh` | Parse workflows, flag `@main`/`@master` refs |
| `run-agent-contract-tests.sh` | Non-destructive agent contract checks (dry-run/sandbox) |
| `build-release-manifest.sh` | Immutable manifest + SHA-256 artifact digest |
| `deploy-staging.sh` / `deploy-production.sh` | Verify digest, capture current version, deploy |
| `post-deploy-verify.sh` | HTTPS reachability, HTTP status, release marker |
| `rollback-staging.sh` / `rollback-production.sh` | Restore last verified artifact |

## Contexts (restricted, referenced by name — none defined yet)

| Context | Used by | Holds |
|---------|---------|-------|
| `ci-readonly` | validation jobs | no deploy credentials |
| `staging-deploy` | staging deploy / verify / rollback | staging deploy + `STAGING_URL` |
| `production-deploy` | production deploy / verify / rollback | production deploy + `PRODUCTION_URL` |

A human must create these three contexts in the CircleCI org and populate their
env vars (deploy credentials, environment URLs, optional `RELEASE_MARKER`).

## Trigger / parameter matrix

| Parameter | Default | Effect |
|-----------|---------|--------|
| `run_validation` | `true` | Runs the `validate` workflow (preflight, lockfiles, workflow scan, agent contract, manifest) |
| `dry_run` | `true` | Keeps deploy steps in dry-run posture |
| `deploy_staging` | `false` | Runs the `staging` workflow (approval-gated) |
| `deploy_production` | `false` | Runs the `production` workflow (approval-gated) |

`preflight.sh` rejects `deploy_staging` **and** `deploy_production` together, and
requires `run_validation=true` before either deploy.

## Deploy flow

`preflight → build-release-manifest → hold-* (manual approval) → deploy-* →
verify-*`. The release manifest is persisted to the CircleCI workspace between
build and deploy; the deploy job re-verifies the artifact's SHA-256 digest
before shipping.

## Rollback flow

Each deploy captures the currently deployed version to
`artifacts/evidence/<target>-previous-version.txt`. A `hold-rollback-*` approval
gates the `rollback-*` job, which restores the last verified artifact via the
`REPLACE_ME_ROLLBACK_COMMAND` placeholder.

## Evidence locations (git-ignored)

- `artifacts/release/manifest.json` — release provenance + artifact digest
- `artifacts/evidence/workflow-integrity.json` — workflow scan findings
- `artifacts/evidence/agent-contract-tests.json` — agent contract results
- `artifacts/evidence/<target>-verify.json` — post-deploy verification
- `artifacts/evidence/<target>-previous-version.txt` — rollback anchor

`artifacts/` is in `.gitignore`; generated evidence is uploaded as CircleCI
artifacts, never committed.

## What a human must do to make this real

1. Connect the project on circleci.com and add a CircleCI API token if
   triggering via API.
2. Create contexts `ci-readonly`, `staging-deploy`, `production-deploy` and add
   deploy credentials + `STAGING_URL` / `PRODUCTION_URL` / `RELEASE_MARKER`.
3. Replace `REPLACE_ME_DEPLOY_COMMAND` / `REPLACE_ME_ROLLBACK_COMMAND` in the
   deploy/rollback scripts with the real commands.
4. Confirm `policy/release-policy.json` `allowed_refs` matches the intended
   release refs.
