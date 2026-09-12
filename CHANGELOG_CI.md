# CI/CD Changelog

## 2026-09-12 — Add CircleCI control-plane pipeline (scaffolding)

Added a governed CircleCI 2.1 release-control pipeline (`.circleci/config.yml`)
plus supporting POSIX `sh` scripts under `scripts/ci/`, policy templates under
`policy/`, and `DEPLOY_CIRCLECI.md`.

- **Pipeline parameters:** `run_validation` (default `true`), `dry_run`
  (default `true`), `deploy_staging` (default `false`), `deploy_production`
  (default `false`).
- **Workflows:** `validate` (read-only gates), `staging`, and `production`.
  Deploys sit behind `type: approval` holds; verify jobs run post-deploy;
  rollback jobs are available behind their own approval holds.
- **Restricted contexts:** `ci-readonly` (validation), `staging-deploy`,
  `production-deploy`. These are referenced by name only — none are defined yet.
- **Safety:** preflight fails closed on invalid parameter combinations;
  immutable release manifest with a SHA-256 artifact digest verified before
  each deploy; evidence written to `artifacts/evidence/`.

**Status: INERT.** CircleCI is not yet connected (no project on circleci.com,
no API token). No pipeline has been triggered. Deploy and rollback commands are
literal `REPLACE_ME_DEPLOY_COMMAND` / `REPLACE_ME_ROLLBACK_COMMAND`
placeholders. The pipeline does nothing until a human connects the project,
defines the three contexts and their credentials, and replaces the deploy
placeholders.
