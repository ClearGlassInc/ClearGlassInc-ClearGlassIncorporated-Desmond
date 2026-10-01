# Workflow Map — 2026-10-01

**Source:** every file in `.github/workflows/`, parsed with PyYAML on `b53bfd7`
plus this branch's one-step `ci.yml` change. Run history read from the GitHub
API. All counts **VERIFIED**.

## Summary

| Measure | 2026-09-24 | 2026-10-01 |
|---|---:|---:|
| Workflow files | 81 | **85** |
| Scheduled (`schedule:`) | 36 | **38** |
| Holding `contents: write` | 16 | **18** |
| Holding any write scope | — | 36 |
| Without a `concurrency` group | — | 40 (5 of them hold `contents: write`) |
| Jobs without `timeout-minutes` | — | **0** |
| Third-party `uses:` not pinned to a 40-char SHA | — | **0** |
| `pull_request_target` triggers | — | **0** |
| Untrusted `github.event.*` text interpolated into `run:` | — | **0** |
| Files that fail to parse | — | **0** |
| Lifetime runs (API `total_count`) | 2,050 (09-15) | **2,500+** (API cap; Auto Heal alone is at run #4,291) |

Added since 2026-09-24: `ieso-public-feed.yml`, `intelligence-graph.yml`,
`shield-billing-lock.yml`, `shield-g01-mvp.yml`. Modified:
`defensive-security-orchestrator.yml`, `release-supply-chain.yml`.

The supply-chain hygiene is strong. Every workflow declares top-level
`permissions`, every job has a timeout, every action is SHA-pinned, and nothing
runs untrusted PR code with secrets. The problems are **volume** and
**re-energisation**, not individual YAML defects.

## What one merge to `main` does today

Observed for `b53bfd7` (PR #162), 2026-10-01 15:53 UTC:

1. Every push-triggered workflow whose path filter matches starts (39 files
   have a `push` trigger). Every job fails in 4 to 9 s with `runner_id: 0`
   (F1). Example: CI run `36887733554`, 7 jobs, all failed in 5 to 9 s.
2. GitHub's own `pages build and deployment` (run #253) succeeds in 33 s. **This
   is the only reason the site ships.**
3. Each failed completion fires `auto-heal.yml` through
   `workflow_run: workflows: ["*"]`. Runs #4278 to #4291 (14 runs in 30 s) followed:
   8 were cancelled by the concurrency group, 4 failed, 1 skipped, and 1
   (triggered by the Copilot reviewer) stopped at `action_required`.
4. `sync-stripe-products.yml` fires after `Deploy Pages` (`workflow_run`) and fails
   on F1 too. Its automatic path is a dry run with a test-mode key only.

Plus the timers: 38 scheduled workflows, including Auto Heal every 30 minutes
(48 runs a day), two hourly feeds that can commit (`control-surface-feeds`,
`ieso-public-feed`) and `minerals-data-sync` every 6 h.

## The ten questions, answered for the workflows that matter

| Question | `ci.yml` | `pages.yml` | `auto-heal.yml` | `sync-stripe-products.yml` | `edge-security.yml` |
|---|---|---|---|---|---|
| What starts it? | push/PR to `main`, dispatch | push to `main`, dispatch | any workflow completing; cron `*/30`; dispatch | after `Deploy Pages`; dispatch | push, PR, dispatch |
| What does it modify? | nothing | Pages artifact (but Pages is on branch deploy) | opens branch + PR with diagnostics and workflow repairs | Stripe catalogue, only on dispatch with `apply` | Cloudflare edge config, only on dispatch `apply`/`rollback` |
| Permissions | `contents: read` | `contents: read`; build job `pages: write`; deploy job `pages`, `id-token: write` | `actions`, `contents`, `issues`, `pull-requests: write` | `contents: read` | `contents: read`; secrets via environments |
| Secrets | none | none | `GITHUB_TOKEN` | test key; **live key in `plan-live-mode` with no environment** | plan/apply tokens, environment-scoped |
| If it fails? | red check (today: always red, F1) | Pages keeps last deploy | its own run fails | dry run lost; no write | no provider change attempted |
| Safe to run twice? | yes | yes (concurrency) | yes (serialised, `cancel-in-progress: false`) | yes; live apply requires a matching plan hash | yes (environment-gated) |
| Untrusted influence? | PR code runs read-only, no secrets | no | reacts to run *conclusions*, not their content | no | PR runs validate only |
| Success verified by | job status | `verify_site.py` before upload | PR for a human | sync report artifact | plan + smoke jobs |
| Failure reported by | check run | check run | check run | step summary | step summary |
| How to stop it | disable workflow | Pages settings | disable workflow; it is noisy now and will open PRs when runners return | dispatch only; unset `ALLOW_STRIPE_LIVE_SYNC` | do not dispatch |

## Write-scoped workflows without concurrency

These five hold `contents: write` and declare no `concurrency` group. Two
overlapping runs can race on a push to the same branch. None can run today (F1).
Adding a group is a one-line change to a **HIGH**-classified path
(`scripts/automation_governance.py`), so it is in the backlog as REQUIRES APPROVAL.

`clearglassinc-military-op.yml` (weekly cron), `dependency-updater.yml` (weekly
cron), `workflow-doctor.yml` (push + weekly cron), `remove-homepage-crimson-loader.yml`
(dispatch), `workflow-repair-agent.yml` (dispatch).

## Cross-repository dependencies

- `repository-health.yml` calls `ClearGlasslabs/ClearCast/.github/workflows/repository-health.yml@90a3d54…`:
  pinned to a SHA (good), but it lives in a different organisation, so a
  change there needs that repo's owners.
- `multi-repo-audit.yml` uses `CG_ORG_PAT`, a personal access token with reach
  beyond this repository. Its scopes cannot be read from here: **UNKNOWN**.

## Full inventory

"Write scopes" lists every scope granted `write` at workflow or job level.
"Secrets" counts distinct `secrets.*` names other than `GITHUB_TOKEN`.

| Workflow | Starts on | Schedule (UTC) | Write scopes | Concurrency | Secrets |
|---|---|---|---|:-:|:-:|
| `advanced-seo-growth.yml` | PR, push, cron, dispatch | `15 7 1 * *` | read-only | yes | 0 |
| `agent-army-crypto.yml` | PR, push, dispatch | — | read-only | yes | 0 |
| `agent-army.yml` | PR, push, dispatch | — | read-only | yes | 0 |
| `agent-deployer.yml` | call, dispatch | — | read-only | **no** | 0 |
| `agent-os.yml` | PR, push, cron, dispatch | `30 13 * * *` | read-only | yes | 0 |
| `agent.yml` | dispatch | — | contents, pull-requests | yes | 3 |
| `ai-proxy-deploy.yml` | PR, push, dispatch | — | read-only | yes | 4 |
| `ai-proxy-security.yml` | PR, push, cron, dispatch | `30 6 * * 1` | read-only | yes | 0 |
| `api-security-audit.yml` | cron, dispatch | `0 3 * * 1` | issues | **no** | 3 |
| `artemis-browser.yml` | PR, push, dispatch | — | read-only | **no** | 0 |
| `artemis-deploy.yml` | push, cron, dispatch | `30 6 * * *` | contents | yes | 0 |
| `artemis-engineering.yml` | PR, push, dispatch | — | read-only | **no** | 0 |
| `artemis-fawl.yml` | PR, dispatch | — | read-only | **no** | 0 |
| `auto-heal.yml` | cron, dispatch, wf_run (after *) | `*/30 * * * *` | actions, contents, issues, pull-requests | yes | 0 |
| `auto-store.yml` | PR, push, cron, dispatch | `0 12 * * *` | issues | yes | 4 |
| `bot-orchestrator.yml` | cron, dispatch | `0 7 * * *` | contents, issues | yes | 1 |
| `burlington-military-op.yml` | cron, dispatch | `23 7 * * 1` | read-only | **no** | 0 |
| `burlington-release.yml` | cron, dispatch | `17 7 * * *` | read-only | **no** | 0 |
| `cert-bot.yml` | cron, dispatch | `17 6 * * *` | read-only | yes | 0 |
| `ci.yml` | PR, push, dispatch | — | read-only | **no** | 0 |
| `clearglassinc-military-op.yml` | cron, dispatch | `0 6 * * 1` | contents | **no** | 0 |
| `cloudflare-email-routing-diagnostic.yml` | push, dispatch | — | issues | yes | 1 |
| `cloudflare-email-routing.yml` | push, dispatch | — | read-only | yes | 1 |
| `codex-autofix.yml` | dispatch | — | contents, pull-requests | yes | 1 |
| `commerce-daily-loop.yml` | cron, dispatch | `0 13 * * *` | read-only | **no** | 0 |
| `commerce-deploy.yml` | push, dispatch | — | read-only | **no** | 1 |
| `commerce-frontend-ci.yml` | PR, push, dispatch | — | read-only | **no** | 0 |
| `compliance-evidence.yml` | cron, dispatch | `0 8 * * 1` | read-only | **no** | 0 |
| `content-pipeline.yml` | dispatch, wf_run (after Bot Orchestrator) | — | contents | yes | 0 |
| `control-surface-feeds.yml` | cron, dispatch | `17 * * * *` | actions, contents | yes | 1 |
| `copilot-setup-steps.yml` | PR, push, dispatch | — | read-only | **no** | 0 |
| `daily-marketing-content.yml` | cron, dispatch | `0 7 * * *` | issues | yes | 1 |
| `defender-watch.yml` | PR, push, cron, dispatch | `0 */6 * * *` | issues | yes | 3 |
| `defensive-security-orchestrator.yml` | PR, push, dispatch | — | id-token, security-events | yes | 1 |
| `dependency-updater.yml` | cron, dispatch | `0 8 * * 1` | contents, issues, pull-requests | **no** | 1 |
| `dispatch-all-workflows.yml` | dispatch | — | actions | **no** | 1 |
| `edge-security.yml` | PR, push, dispatch | — | read-only | yes | 3 |
| `enterprise-patch-deploy.yml` | call | — | id-token | yes | 0 |
| `function-agent-ci.yml` | PR, push, dispatch | — | read-only | yes | 0 |
| `health-monitor.yml` | cron, dispatch | `0 */6 * * *` | issues | yes | 1 |
| `ieso-public-feed.yml` | cron, dispatch | `41 * * * *` | contents | yes | 0 |
| `indexnow.yml` | dispatch | — | read-only | yes | 1 |
| `intelligence-graph.yml` | cron, dispatch | `17 5 * * *` | contents | yes | 0 |
| `internal-link-authority.yml` | PR, push, dispatch | — | read-only | yes | 0 |
| `ip-protection-scan.yml` | PR, push, cron, dispatch | `0 2 * * *` | issues, pull-requests | **no** | 1 |
| `maintenance-review.yml` | cron, dispatch | `0 12 * * 1` | issues | yes | 1 |
| `marketing-market-intelligence.yml` | cron, dispatch | `0 13 * * 1` | contents | yes | 0 |
| `master-orchestrator.yml` | cron, dispatch | `0 */6 * * *` | read-only | yes | 0 |
| `minerals-data-sync.yml` | cron, dispatch | `17 */6 * * *` | contents | yes | 0 |
| `minerals-link-authority-sync.yml` | PR, push | — | contents | yes | 0 |
| `multi-repo-audit.yml` | cron, dispatch | `17 4 * * *` | read-only | **no** | 1 |
| `organic-daily.yml` | cron, dispatch | `0 12 * * *` | issues | yes | 1 |
| `organic-weekly-review.yml` | cron, dispatch | `0 15 * * 1` | issues | **no** | 1 |
| `pages-check.yml` | push, dispatch | — | read-only | **no** | 0 |
| `pages.yml` | push, dispatch | — | id-token, pages | yes | 0 |
| `percival-policy-gate.yml` | PR, dispatch | — | read-only | **no** | 0 |
| `percival-policy-reusable.yml` | call | — | read-only | **no** | 0 |
| `phoenix-self-heal.yml` | PR, push, dispatch | — | read-only | **no** | 0 |
| `policy-gate.yml` | PR, push, dispatch | — | read-only | **no** | 0 |
| `pr-automation.yml` | PR | — | issues, pull-requests | **no** | 1 |
| `release-supply-chain.yml` | call | — | attestations, id-token, packages | **no** | 1 |
| `remove-homepage-crimson-loader.yml` | dispatch | — | contents, pull-requests | **no** | 0 |
| `repo-audit.yml` | cron, dispatch | `0 7 * * 1` | read-only | yes | 1 |
| `repository-health.yml` | PR, push, dispatch | — | read-only | **no** | 0 |
| `revenue-command.yml` | PR, push, dispatch | — | read-only | **no** | 0 |
| `revenue-pipeline-agent.yml` | cron, dispatch | `17 13 * * 1-5` | read-only | **no** | 0 |
| `rollback.yml` | dispatch | — | issues | yes | 2 |
| `runner-canary.yml` | push, dispatch | — | read-only | **no** | 0 |
| `sales-ops-briefing.yml` | cron, dispatch | `17 11 * * *` | read-only | **no** | 4 |
| `security.yml` | PR, push, cron, dispatch | `0 6 * * 1` | pull-requests | **no** | 0 |
| `semgrep-trial.yml` | cron, dispatch | `42 5 * * 1` | read-only | yes | 0 |
| `seo-continuous-audit.yml` | PR, push, cron, dispatch | `17 6 * * 1` | read-only | yes | 0 |
| `seo-dashboard.yml` | push, cron, dispatch | `40 6 * * *` | contents | yes | 7 |
| `seo-optimizer.yml` | call, dispatch | — | read-only | **no** | 0 |
| `shield-billing-lock.yml` | PR, push, dispatch | — | read-only | yes | 0 |
| `shield-g01-mvp.yml` | PR, dispatch | — | read-only | yes | 0 |
| `site-integrity-and-deploy.yml` | PR, push, dispatch | — | read-only | yes | 0 |
| `site-reliability.yml` | PR, push, cron, dispatch | `17 7 * * 1` | read-only | yes | 0 |
| `sync-stripe-products.yml` | dispatch, wf_run (after Deploy Pages) | — | read-only | yes | 2 |
| `thought-leadership.yml` | call, dispatch | — | read-only | **no** | 0 |
| `viral-content.yml` | call, dispatch | — | read-only | **no** | 0 |
| `visual-restoration.yml` | push, dispatch | — | read-only | **no** | 0 |
| `workflow-doctor.yml` | push, cron, dispatch | `0 3 * * 1` | contents, pull-requests | **no** | 1 |
| `workflow-repair-agent.yml` | dispatch | — | contents, pull-requests | **no** | 0 |
| `xenolith-gate.yml` | PR, push, dispatch | — | read-only | **no** | 0 |

Regenerate: parse each file with `yaml.safe_load`, read `on`/`True`, `permissions`, `concurrency`, `jobs.*.timeout-minutes`, `jobs.*.steps[*].uses`, and the `secrets.*` names in the raw text.
