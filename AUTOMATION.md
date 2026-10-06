# ClearGlass CI/CD automation

The CI, self-healing, staging and promotion layer added on 2026-10-06, and how
it fits the workflows that were already here. What automation may *change* is
governed separately by [`docs/AUTOMATION_POLICY.md`](docs/AUTOMATION_POLICY.md);
nothing here overrides it.

> **None of this runs yet.** Since 2026-09-06 GitHub Actions dispatches no
> runner for user-authored jobs in this repository (`runner_id: 0`, no steps,
> no logs; `CLAUDE.md`, `PRODUCTION-RECOVERY.md` §1.1). That is fixed in
> organisation settings (billing hold, spending limit, allowed-actions policy,
> or the Actions toggle), not in code. Every workflow below needs a runner.
> Until then, run the gates yourself: `python3 scripts/ci_local.py`.

## What was added

| File | Purpose | State on merge |
|---|---|---|
| `.github/workflows/reusable-ci.yml` | Callable gates: `scripts/ci_local.py` (every offline `ci.yml` gate) + the commerce gates from `commerce-deploy.yml` | Runs only when called |
| `.github/workflows/reusable-deploy.yml` | Deploy, smoke-test and name-the-rollback primitive, provider chosen per environment | Runs only when called |
| `.github/workflows/deploy-staging.yml` | Deploys each same-repo PR to `staging` as `pr-<n>` and comments the URL | **Off** until `CG_PR_STAGING_DEPLOY=true` |
| `.github/workflows/deploy-promotion.yml` | Gates, then staging, then production, for one resolved commit | **Off** until `CG_PROMOTION_ENABLED=true` |
| `.github/workflows/auto-fix.yml` | On a failed PR CI run: ruff safe fixes + regenerated assets, pushed as an `auto-fix:` commit | On (kill switch `CG_AUTO_FIX_DISABLED`) |
| `.github/workflows/heal-pipeline.yml` | One issue per workflow+branch after N consecutive CI failures | On (kill switch `CG_HEAL_PIPELINE_DISABLED`) |
| `.github/workflows/ci-telemetry.yml` | Weekly CI health issue, Mondays 09:00 UTC | On |
| `.github/actions/setup-node-python/` | Node 22 + Python 3.11 + ci.yml's pinned gate tools | n/a |
| `.github/actions/run-smoke-tests/` | Polls `/health` and `/ready` until 2xx | n/a |
| `.github/actions/post-pr-comment/` | PR comment, upserted by marker so a bot leaves one comment, not one per run | n/a |

## How it coexists with what was already here

Nothing existing was removed, renamed or edited.

| Blueprint item | Already here | Decision |
|---|---|---|
| `ci.yml` calling `reusable-ci.yml` | `ci.yml` with 7 gates (pytest, ruff, site audit, search integrity, Lighthouse, workflow doctor, OSINT deck) | **Kept unchanged.** The blueprint's file would have replaced it and dropped those gates. Its job names are also the check names branch protection reads; routing them through a reusable workflow renames every check. `reusable-ci.yml` exists for promotion, which now gates on exactly what `ci.yml` gates on. |
| `auto-fix.yml` | `codex-autofix.yml` (LLM, manual dispatch only) | Both kept. The new one is deterministic, never an LLM. |
| `heal-pipeline.yml` | `auto-heal.yml` (one issue per failed run, any workflow) | Both kept. The new one reports patterns, not incidents. |
| `deploy-staging.yml` | `pr-staging.yml` (read-only build and test of each PR) | Both kept. The new one only adds the deploy, and is off by default. |
| Auto-rollback in production | `rollback.yml` + `docs/INCIDENT_RESPONSE.md`: rollback is manual dispatch only | **Repository policy wins.** A failed production deploy names the last recorded good revision and the exact `rollback.yml` command, then fails. It does not roll back on its own. |
| Production deploy on `main` push | `render.yaml` `autoDeploy: true`, and `commerce-deploy.yml` calling `RENDER_DEPLOY_HOOK_URL` | Promotion is off by default. Enabling it with `render` deploys the same commit up to three times: retire the other two first. That is your call. |
| `.github/CODEOWNERS` | Root `CODEOWNERS` | **Not created.** GitHub reads the first CODEOWNERS it finds, `.github/` before the root, so a new file there would silently replace every existing rule. `/.github/actions/` was added to the root file instead. |
| CodeQL in `reusable-ci.yml` | `defensive-security-orchestrator.yml` uploads SARIF | Not duplicated. A called workflow that asks for `security-events: write` fails to load in any caller that does not grant it. |

## Auto-fix

Triggered when the `CI` workflow fails on a same-repository pull request.

1. **`context`** resolves the PR and stops if: the head is a fork, the author is a bot, the PR is labelled `no-autofix`, it already has two `auto-fix:` commits, the PR moved on since that CI run, or `CG_AUTO_FIX_DISABLED=true`.
2. **`fix`** (read-only token) checks out the PR head and runs only:
   - `ruff check --fix` (pinned 0.15.8, the repository's config) on the Python files the PR changed;
   - `tools/generate_search_assets.py`, `tools/internal_links.py`, `tools/insights_index.py`, the generators whose drift `ci.yml` fails on.
   It uploads the result as a patch. No black, prettier or eslint: none is configured here, and they would reformat the whole static site.
3. **`push`** (write token, `automation-write` environment) runs no PR code. It applies the patch, refuses it if any path is protected by `scripts/automation_governance.py` (loaded from the default branch) or sits under `.github/`, and pushes without force only if the branch has not moved.
4. **`report`** keeps one PR comment current with the outcome.

GitHub does not start workflow runs for a commit pushed with the workflow token, so CI runs again on the author's next push.

## Staging and promotion

The provider is chosen **per GitHub Environment** by the variable `DEPLOY_PROVIDER`:

| Value | Behaviour |
|---|---|
| unset / `none` | Nothing deployed. The run says so and reports `deployed=false`, which stops a promotion. |
| `render` | Calls the environment's `RENDER_DEPLOY_HOOK` secret with `?ref=<sha>`, the same call `rollback.yml` makes. One hook is one service, so `pr-<n>` deploys take turns on a single staging service. |
| anything else | Fails. Cloud Run, ECS and Kubernetes are not wired: no registry, cluster or credentials for them exist here. Add a case to `reusable-deploy.yml` when one does, with OIDC. |

Per-PR deploys run through the single `staging` environment. A `pr-<n>` environment would receive none of staging's secrets (environment secrets are not inherited) and would leave one orphan environment per PR.

Promotion order: resolve the tag or SHA to one commit on `main` → `reusable-ci` → `staging` → `production`. Production runs only if staging really deployed. Its manual approval is the `production` environment's required reviewers and wait timer, which are settings, below.

Smoke tests prove `/health` and `/ready` answer 2xx. Neither reports a commit, so a pass shows the service is healthy, not that the new revision is the one answering.

## Settings you make (cannot be done from code)

**Environments** (Settings → Environments):

| Environment | Protection | Variables | Secrets |
|---|---|---|---|
| `staging` | Optional reviewer; branches `main`, `staging` and PR heads | `DEPLOY_PROVIDER`, `DEPLOY_BASE_URL` (https) | `RENDER_DEPLOY_HOOK` if `render` |
| `production` | 1-2 required reviewers, 5-15 min wait timer, branch `main` only | `DEPLOY_PROVIDER`, `DEPLOY_BASE_URL`; `PRODUCTION_HEALTH_URL` is already read by `rollback.yml` | `RENDER_DEPLOY_HOOK` (already read by `rollback.yml`) |
| `automation-write` | Already exists (auto-heal, workflow doctor). Reviewers here also gate auto-fix pushes. | none | none |

Secrets are scoped to their environment, so the same name in each is correct; `STAGING_`/`PROD_` prefixes are unnecessary and nothing reads them.

**Repository variables** (Settings → Secrets and variables → Actions → Variables):

| Variable | Effect |
|---|---|
| `CG_PR_STAGING_DEPLOY=true` | Turns on per-PR staging deploys |
| `CG_PROMOTION_ENABLED=true` | Turns on staging → production promotion |
| `CG_AUTO_FIX_DISABLED=true` | Turns auto-fix off |
| `CG_HEAL_PIPELINE_DISABLED=true` | Turns heal-pipeline off |
| `CG_HEAL_FAILURE_THRESHOLD` | Consecutive CI failures before an issue (default 3, minimum 2) |

**Optional repository secret:** `CI_TELEMETRY_WEBHOOK_URL`, which receives the weekly summary as `{"text": ...}`.

## OIDC, when a cloud provider is added

Use OIDC; never store a long-lived cloud key. Scope the trust to the **environment**, not the repository. The blueprint's `repo:ORG/REPO:*` lets any branch or pull request job in the repository assume the production role:

```json
"Condition": {
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
    "token.actions.githubusercontent.com:sub": "repo:ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond:environment:production"
  }
}
```

One role per environment, least-privilege policies, and `id-token: write` granted only on the deploy job, never at the top level. An Azure equivalent is staged in `scripts/azure_oidc_activation.sh`.

## Overriding automation

- Label a PR `no-autofix` to keep auto-fix off it.
- Repository variables above switch each workflow on or off without a code change.
- `[skip ci]` in a commit message skips push and pull_request workflows for that commit (GitHub built-in).
- `deploy-promotion.yml` can be run by hand with `release_tag` (a tag or full SHA on `main`).
- Rollback is always `rollback.yml`, dispatched by a person: [`docs/INCIDENT_RESPONSE.md`](docs/INCIDENT_RESPONSE.md).

## Validating a change to this layer

```bash
pip install pytest pyyaml "ruff==0.15.8" actionlint-py shellcheck-py
python3 scripts/workflow_doctor.py           # SHA pins, trigger schema
python3 scripts/audit_github_actions.py      # permissions, credentials, environments
actionlint .github/workflows/{reusable-ci,reusable-deploy,deploy-staging,deploy-promotion,auto-fix,heal-pipeline,ci-telemetry}.yml
python3 -m pytest tests/test_cicd_layer.py -q
```

`actionlint` is not a repository gate: on 2026-10-06 it reported findings in 12
older workflows, which this layer did not touch. The seven files above lint
clean, including shellcheck.

```bash
python3 scripts/ci_local.py                  # everything ci.yml gates on
```
