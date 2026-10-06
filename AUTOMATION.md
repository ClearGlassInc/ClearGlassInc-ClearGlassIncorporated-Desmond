# ClearGlass CI/CD Automation

The CI/CD automation layer: lint auto-fix on PRs, per-PR staging checks,
staging-to-production promotion, CI diagnostics and weekly CI telemetry.

> **None of this runs yet.** Since 2026-09-06 GitHub Actions dispatches no runners
> for this repository (`runner_id: 0`, no steps). That is an organisation-level
> setting, not code: see CLAUDE.md, `PRODUCTION-RECOVERY.md` §1.4 and
> `docs/BASELINE.md` F1. Until it is fixed, run the gates yourself:
> `python3 scripts/ci_local.py`.

Everything here is additive. `ci.yml`, `commerce-deploy.yml`, `rollback.yml`,
`auto-heal.yml`, `pr-staging.yml` and `codex-autofix.yml` are unchanged and
keep their jobs. Anything that deploys or pushes stays off until its switch is set.

## 1. What is where

| File | Trigger | What it does | Default |
|---|---|---|---|
| `.github/workflows/auto-fix.yml` | CI fails on a PR | Applies ruff safe fixes to the PR's changed `.py` files, commits them as a Verified commit, posts one PR comment | **On** (off: `AUTOFIX_ENABLED=false`) |
| `.github/workflows/deploy-staging.yml` | PR opened or updated | Waits for the PR's host-built preview, smoke-tests it, posts the URL on the PR | Off until `PR_PREVIEW_URL_TEMPLATE` is set |
| `.github/workflows/deploy-promotion.yml` | Push to `main` (commerce paths), or manual | Gates, then staging, then production behind reviewers | Push: off until `PROMOTION_PIPELINE_ENABLED=true`. Manual: always runs |
| `.github/workflows/heal-pipeline.yml` | CI fails | After 3 failures in a row on a branch, keeps one `ci-diagnostic` issue for that branch, with a cause | On |
| `.github/workflows/ci-telemetry.yml` | Mondays 08:47 UTC, or manual | Failure rate, fast failures, slowest workflows over 7 days, in one `ci-telemetry` issue | On |
| `.github/workflows/reusable-ci.yml` | Called | The repo's real gates: ruff, root pytest, control-plane pytest, workflow safety; optional frontends and CodeQL | n/a |
| `.github/workflows/reusable-deploy.yml` | Called | Render deploy hook with a full SHA, waits for live, smoke-tests | n/a |
| `.github/actions/setup-node-python/` | Used by the above | Node 22, Python 3.11, ruff 0.15.8 (the versions `ci.yml` uses) | n/a |
| `.github/actions/run-smoke-tests/` | Used by the above | Read-only: polls `/health`, checks `/ready`, optionally proves the admin gate refuses anonymous reads | n/a |
| `.github/actions/post-pr-comment/` | Used by the above | Creates or edits one marker-tagged PR comment, so reruns do not stack comments | n/a |

## 2. Switches

Set in **Settings → Secrets and variables → Actions** (repository) or **Settings →
Environments → <name>** (environment).

| Name | Kind | Scope | Effect |
|---|---|---|---|
| `AUTOFIX_ENABLED` | variable | repository | `false` disables auto-fix everywhere |
| `PR_PREVIEW_URL_TEMPLATE` | variable | repository | e.g. `https://clearglass-commerce-api-pr-{pr}.onrender.com`; turns on per-PR staging checks |
| `PROMOTION_PIPELINE_ENABLED` | variable | repository | `true` lets a push to `main` start a promotion |
| `HEAL_PIPELINE_THRESHOLD` | variable | repository | Consecutive failures before a diagnostic issue (default 3, minimum 2) |
| `DEPLOY_BASE_URL` | variable | `staging`, `production` | https base URL of that environment's control plane |
| `RENDER_DEPLOY_HOOK` | secret | `staging`, `production` | That environment's Render deploy hook. `rollback.yml` already reads this name in `production` |
| `RENDER_API_KEY` | secret | `staging`, `production` | Lets the deploy wait until Render reports the new revision `live` |

## 3. Auto-fix

When `CI` fails on a pull request:

1. Skips unless the PR is open, from this repository (not a fork), not bot-authored,
   not labelled `no-autofix`, not on the default branch or `staging`, still at the
   failing commit, and has fewer than 2 `auto-fix:` commits.
2. Runs `ruff check --fix --force-exclude` (safe fixes only, pinned ruff 0.15.8,
   the repo's `pyproject.toml` config) on the Python files the PR changed.
3. If anything changed and the branch has not moved, commits it through
   `.github/actions/verified-commit` as `auto-fix: ruff safe fixes for PR #N`.
4. Edits one PR comment: what was fixed, or that the failure needs a person.

It never runs eslint, prettier or black. The repo uses none of them, and running
them repo-wide would rewrite thousands of files nobody touched. It is not an LLM:
`codex-autofix.yml` stays manual-only for the reasons in its header.

## 4. Per-PR staging

The host builds the preview; this workflow verifies it. On Render that means a
preview environment (`previews:` in `render.yaml`), which names each service
`<service>-pr-<N>`. Previews are billed instances, so enabling them is an owner
decision this change does not make. With `PR_PREVIEW_URL_TEMPLATE` set, each PR
gets a smoke test (up to 15 minutes for the build) and one comment with the URL.

## 5. Promotion to production

1. **Resolve.** Takes the pushed commit (or the dispatched `ref`), refuses anything
   not on `main`, and looks up the last successful `production` deployment.
2. **Gate.** `reusable-ci.yml` re-runs the Python, control-plane and workflow-safety
   gates on that exact commit.
3. **Staging.** Deploy hook with `?ref=<SHA>`, wait for `live`, smoke-test.
4. **Production.** The same SHA. The `production` environment's required reviewers
   approve before the job starts. Smoke tests here also require
   `admin_auth=enabled` and a 401/403 from `/events` and `/metrics/overview`.
5. **Incident.** If production fails, an `incident` issue names the last known-good
   SHA and the exact Rollback inputs.

**Switching from `commerce-deploy.yml`.** That workflow already deploys production on
every push to `main` that touches the commerce tree. Turning on
`PROMOTION_PIPELINE_ENABLED` while its `RENDER_DEPLOY_HOOK_URL` secret is still set
means two production deploys per push. To switch: delete `RENDER_DEPLOY_HOOK_URL`
(commerce-deploy keeps its gates and skips its deploy cleanly), then set the variable.

**Staging needs its own service.** `render.yaml` defines one set of services. Until a
separate staging service and database exist, there is nothing for the `staging`
environment's hook to point at. Pointing it at production is not staging.

## 6. Rollback

Manual, on purpose. `docs/INCIDENT_RESPONSE.md`: an automatic rollback can flap
between two broken states, and an automatic rollback of a data migration is worse
than the outage. A failed deploy writes the rollback target to the run summary and
the incident issue; a person runs **Actions → Rollback** with it.

## 7. Diagnostics and telemetry

- **heal-pipeline** classifies a red streak. If every failed job reports
  `runner_id: 0` and no steps, it says so and points at settings, not code.
  Otherwise it lists failing jobs and steps, and whether CI on `main` is red too.
  One issue per branch, edited in place.
- **ci-telemetry** counts runs per workflow over 7 days. A "fast failure" is a
  failed run under 20 seconds, the shape of the runner-dispatch problem. It is a
  duration heuristic: confirm on one job before acting on it.

## 8. Overriding automation

- `no-autofix` label on a PR: auto-fix leaves it alone.
- `AUTOFIX_ENABLED=false`: auto-fix off everywhere.
- `[skip ci]` in a commit message: GitHub skips push and pull_request workflows for it.
- **Actions → Deploy Promotion → Run workflow**: promote a specific SHA by hand.

## 9. Known limits

- **Commits made with the workflow token do not trigger CI.** After an auto-fix
  commit the PR head has no checks until the author pushes again.
- **Without `RENDER_API_KEY` the deploy cannot tell when the new revision is live.**
  It waits 180 seconds, and the smoke test may be answered by the previous
  revision. The same applies to PR previews.
- **`/health` reports the package version, not the commit.** No job can prove which
  SHA is serving. Fix: return `RENDER_GIT_COMMIT` from `/health`. That is a
  control-plane change and is not part of this layer.
- **CodeQL** in `reusable-ci.yml` is off by default. If GitHub's CodeQL default setup
  is on, an advanced-configuration upload is rejected.

## 10. Checking a change to this layer

```bash
pip install pyyaml "ruff==0.15.8"
python3 scripts/workflow_doctor.py        # SHA pins, trigger schemas
python3 scripts/audit_github_actions.py   # permissions, secrets, deploy gating
python3 scripts/ci_local.py               # every ci.yml gate
```
