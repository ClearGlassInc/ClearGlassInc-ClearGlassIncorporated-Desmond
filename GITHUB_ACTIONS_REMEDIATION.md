# GitHub Actions Remediation Report

**Scope:** all workflow files under `.github/workflows/`  
**Audit mode:** offline, non-executing, fail-closed source inspection  
**Rollback:** revert the remediation commit; no workflow was remotely dispatched and no deployment was performed.

## Executive decision

The repository contains 52 workflows. YAML parsing, local references, full-SHA action pinning, explicit permissions, job timeouts, deployment dependencies, secrets interpolation, artifact/cache declarations, environments, and recognizable deployment targets were inspected by `scripts/audit_github_actions.py`. The auditor also fails closed when a named artifact download has no same-workflow producer or when the official Pages deploy action lacks an upstream Pages artifact, job-local `pages: write` and `id-token: write`, or the `github-pages` environment. Its JSON evidence now records action references, artifact actions, cache configuration, and concurrency alongside the existing trigger, permission, secret-name, job, environment, error, and warning map. The inventory below is generated from the checked-in workflow source.

The immediate source-level governance defects were patched: every unattended repository writer now crosses the `automation-write` environment boundary, and production deploy, rollback, release, and image-publication jobs cross the `production` environment boundary. The offline auditor now evaluates write authority per job rather than incorrectly combining unrelated workflow-level signals.

No remote workflow was executed. All workflows are source-valid after remediation. Execution of environment-bound jobs remains blocked until a repository administrator confirms that `automation-write` and `production` exist, require reviewers, restrict deployment branches, and scope their secrets appropriately.

## Apply fixes in this order

1. **Merged in this change:** bind scheduled/chained repository writers to `automation-write` and bind production deployment, rollback, release, and GHCR publication to `production`.
2. **Repository-admin gate:** configure both environments with required reviewers, branch/tag restrictions, prevent self-review, and environment-scoped secrets. Until verified, do not approve or execute the bound jobs.
3. Open a pull request and run the read-only CI, security, policy, workflow-doctor, and offline audit gates.
4. Exercise `automation-write` with a no-change/manual run first; review the approval record and confirm no protected-branch write occurs without approval.
5. Exercise deployment only with an authorized release owner, validated artifacts, health monitoring, and the documented rollback anchor.

## Exact remediation applied

| Workflow | Failure risk | Patch |
|---|---|---|
| `artemis-deploy.yml` | Scheduled provenance writer could push without an approval boundary. | Bound `provenance` to `automation-write`. |
| `auto-store.yml` | Rollback hook was outside the production environment boundary. | Bound `rollback` to `production`. |
| `bot-orchestrator.yml` | Scheduled generated-output writer could push without approval. | Bound `orchestrate` to `automation-write`. |
| `clearglassinc-military-op.yml` | Release tag writer relied only on an upstream job's environment. | Bound `release` itself to `production`. |
| `content-pipeline.yml` | Chained `workflow_run` writer could push without approval. | Bound `validate-and-commit` to `automation-write`. |
| `control-surface-feeds.yml` | Scheduled feed writer could push without approval. | Bound `publish-feeds` to `automation-write`. |
| `dependency-updater.yml` | Scheduled dependency branch writer could push without approval. | Bound `update-python-deps` to `automation-write`. |
| `release-supply-chain.yml` | Reusable GHCR publisher had no environment boundary. | Bound `build-sign-attest` to `production`. |
| `workflow-doctor.yml` | Scheduled repair branch writer could force-push without approval. | Bound `repair` to `automation-write`; PR review remains required. |
| `scripts/audit_github_actions.py` | Workflow-wide write detection produced false positives, and its custom loader mutated PyYAML resolver state process-wide. | Made unattended-write analysis job-scoped/environment-aware and isolated the loader resolver table. |
| `scripts/audit_github_actions.py` | Artifact consumers and Pages deploy readiness were inventory-only, so a producer/name mismatch or an incomplete official Pages dependency chain could pass the offline gate. | Added fail-closed same-workflow artifact matching and explicit Pages producer, dependency, permission, and environment validation; expanded JSON audit evidence. |
| `tests/test_audit_github_actions.py` | The new artifact and Pages invariants had no regression coverage. | Added positive and negative Pages, artifact-name, and machine-readable inventory tests. |

## Validation and rollout runbook

### Local/source gate

1. Run `python scripts/audit_github_actions.py`; any `ERROR` is a hard stop.
2. Run `python scripts/audit_github_actions.py --markdown` and review inventory drift.
3. Run `python -m pytest tests/test_audit_github_actions.py -q`.
4. Run `python scripts/workflow_doctor.py`; apply no automatic repair without reviewing its diff.
5. Run `git diff --check` and inspect every workflow diff.

### GitHub validation (authorized operator)

1. Open a pull request and require `CI`, `Security`, policy gates, and relevant commerce gates to pass.
2. Confirm repository Actions policy permits only the SHA-pinned actions in the inventory.
3. Confirm `production` and `github-pages` environments have intended reviewers and branch rules.
4. Dispatch only read-only/manual validation workflows first. Capture run URL, actor, source SHA, inputs, job logs, artifact names/digests, and conclusion.
5. For Pages, inspect the `github-pages` artifact from the build job, then approve deployment. Verify the deployed URL and retain the prior successful deployment as rollback anchor.
6. For Render, verify the release SHA, approve the environment, monitor readiness and functional checks, and roll back to the last green release on any invariant failure.

### Post-deployment monitoring

Monitor failed/skipped gates, environment approvals, unexpected token permission elevation, artifact digest/path changes, Pages deployment URL/HTTP status, Render readiness and checkout health, rollback invocation, bot-created commits/issues, and repeated retry/warning patterns. Alert on any direct protected-branch push by automation or deployment without a corresponding approved environment record.

### Weekly health check

Run the offline audit and workflow doctor; review action SHA drift and upstream security advisories; audit environment/branch protection and token permissions; inspect secret age/ownership without exposing values; sample artifacts and retention; review scheduled-run failure rate/duration; test a non-production rollback; and reconcile workflow inventory against CODEOWNERS and deployment ownership.

## Workflow inventory

The table maps triggers, permissions, referenced secret names (never values), jobs, artifact/cache use, environment bindings, deployment targets, status, and exact source-verifiable risk. “Valid and ready” means **source-valid**; it does not attest that remote secrets or GitHub settings exist.

| Workflow | Status | Triggers | Permissions | Secrets | Jobs | Artifacts / caches | Environments | Targets | Exact risk |
|---|---|---|---|---|---|---|---|---|---|
| `agent-army-crypto.yml` | valid and ready | pull_request, push, workflow_dispatch | contents | none | secure-runtime | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `agent-army.yml` | valid and ready | pull_request, push, workflow_dispatch | contents | none | validate | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `agent-deployer.yml` | valid and ready | workflow_call, workflow_dispatch | contents | none | run | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `agent-os.yml` | valid and ready | schedule, pull_request, workflow_dispatch | contents | none | self-check | 0 artifact step(s); cache: self-check:pip | none | none | No source-verifiable failure risk found. |
| `agent.yml` | valid and ready | workflow_dispatch | contents | ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN, GITHUB_TOKEN | repair | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `api-security-audit.yml` | valid and ready | schedule, workflow_dispatch | contents, security-events, issues | AUDIT_LOW_PRIV_TOKEN, AUDIT_OTHER_USER_ID, AUDIT_VALID_TOKEN | api-security-audit | 2 artifact step(s); cache: none | staging | none | No source-verifiable failure risk found. |
| `artemis-browser.yml` | valid and ready | push, pull_request, workflow_dispatch | contents | none | browser-assistant | 0 artifact step(s); cache: browser-assistant:pip, browser-assistant:npm | none | none | No source-verifiable failure risk found. |
| `artemis-deploy.yml` | valid and ready | push, schedule, workflow_dispatch | contents | none | validate, ip-guardian-gate, provenance | 1 artifact step(s); cache: none | automation-write | none | No source-verifiable failure risk found. |
| `artemis-fawl.yml` | valid and ready | pull_request, workflow_dispatch | contents | none | validate | 0 artifact step(s); cache: validate:pip | none | none | No source-verifiable failure risk found. |
| `auto-store.yml` | valid and ready | pull_request, push, schedule, workflow_dispatch | contents | CONTROL_PLANE_URL, GITHUB_TOKEN, RENDER_DEPLOY_HOOK_URL, RENDER_ROLLBACK_HOOK_URL | validate, test, checkout-health, deploy, verify, rollback, alert | 2 artifact step(s); cache: none | production, production | Render | No source-verifiable failure risk found. |
| `bot-orchestrator.yml` | valid and ready | schedule, workflow_dispatch | contents | GITHUB_TOKEN | orchestrate | 1 artifact step(s); cache: orchestrate:pip | automation-write | none | No source-verifiable failure risk found. |
| `burlington-military-op.yml` | valid and ready | workflow_dispatch, schedule | contents | none | military-op | 1 artifact step(s); cache: none | ${{ github.event_name == 'workflow_dispatch' && inputs.environment || 'staging' }} | none | No source-verifiable failure risk found. |
| `burlington-release.yml` | valid and ready | workflow_dispatch, schedule | contents | none | release-gate | 1 artifact step(s); cache: none | ${{ github.event_name == 'workflow_dispatch' && inputs.environment || 'staging' }} | none | No source-verifiable failure risk found. |
| `cert-bot.yml` | valid and ready | schedule, workflow_dispatch | contents | none | track | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `ci.yml` | valid and ready | push, pull_request, workflow_dispatch | contents | none | python-tests, lint, site-audit, workflow-doctor, osint-deck | 0 artifact step(s); cache: python-tests:pip, lint:pip, workflow-doctor:pip | none | none | No source-verifiable failure risk found. |
| `clearglassinc-military-op.yml` | valid and ready | workflow_dispatch, schedule | contents, id-token, actions, security-events | none | inspect, build-test, security, staging, production, release, audit | 3 artifact step(s); cache: none | {'name': 'production', 'url': 'https://www.clearglassinc.com'}, production | none | No source-verifiable failure risk found. |
| `codex-autofix.yml` | valid and ready | workflow_dispatch | contents | OPENAI_API_KEY | autofix | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `commerce-daily-loop.yml` | valid and ready | schedule, workflow_dispatch | contents | none | daily-loop | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `commerce-deploy.yml` | valid and ready | push, workflow_dispatch | contents | RENDER_DEPLOY_HOOK_URL | gate, frontend-build, deploy | 0 artifact step(s); cache: frontend-build:npm | production | Render | No source-verifiable failure risk found. |
| `commerce-frontend-ci.yml` | valid and ready | push, pull_request | contents | none | build | 0 artifact step(s); cache: build:npm | none | none | No source-verifiable failure risk found. |
| `compliance-evidence.yml` | valid and ready | schedule, workflow_dispatch | contents | none | harvest | 1 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `content-pipeline.yml` | valid and ready | workflow_run, workflow_dispatch | contents | none | validate-and-commit | 0 artifact step(s); cache: none | automation-write | none | No source-verifiable failure risk found. |
| `control-surface-feeds.yml` | valid and ready | schedule, workflow_dispatch | contents | GITHUB_TOKEN | publish-feeds, dispatch-pages-deploy | 0 artifact step(s); cache: publish-feeds:pip | automation-write | none | No source-verifiable failure risk found. |
| `copilot-setup-steps.yml` | valid and ready | push, workflow_dispatch | contents | none | validate-site | 1 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `daily-marketing-content.yml` | valid and ready | schedule, workflow_dispatch | contents, issues | GITHUB_TOKEN | create-daily-page | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `defender-watch.yml` | valid and ready | push, pull_request, schedule, workflow_dispatch | contents | DEFENDER_DISCORD_WEBHOOK_URL, DEFENDER_SLACK_WEBHOOK_URL, GITHUB_TOKEN | defend | 1 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `dependency-updater.yml` | valid and ready | schedule, workflow_dispatch | contents | GITHUB_TOKEN | update-python-deps | 0 artifact step(s); cache: update-python-deps:pip | automation-write | none | No source-verifiable failure risk found. |
| `dispatch-all-workflows.yml` | valid and ready | workflow_dispatch | contents, actions | GITHUB_TOKEN | dispatch | 0 artifact step(s); cache: dispatch:pip | none | none | No source-verifiable failure risk found. |
| `health-monitor.yml` | valid and ready | schedule, workflow_dispatch | contents | GITHUB_TOKEN | site-health | 1 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `internal-link-authority.yml` | valid and ready | pull_request, push, workflow_dispatch | contents | none | validate-authority-network | 3 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `ip-protection-scan.yml` | valid and ready | push, pull_request, schedule | contents, issues, pull-requests | GITHUB_TOKEN | scan | 1 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `master-orchestrator.yml` | valid and ready | workflow_dispatch, schedule | contents | none | web-seo, ai-agents, corporate-content, brand-viral | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `multi-repo-audit.yml` | valid and ready | schedule, workflow_dispatch | contents | CG_ORG_PAT | audit | 1 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `organic-daily.yml` | valid and ready | schedule, workflow_dispatch | contents, issues | GITHUB_TOKEN | generate | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `organic-weekly-review.yml` | valid and ready | schedule, workflow_dispatch | contents, issues | GITHUB_TOKEN | review | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `pages.yml` | valid and ready | push, workflow_dispatch | contents, pages, id-token | none | build, deploy | 1 artifact step(s); cache: none | {'name': 'github-pages', 'url': '${{ steps.deployment.outputs.page_url }}'} | GitHub Pages | No source-verifiable failure risk found. |
| `percival-policy-gate.yml` | valid and ready | pull_request, workflow_dispatch | contents | none | call-policy-gate | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `percival-policy-reusable.yml` | valid and ready | workflow_call | contents | none | policy-tests | 0 artifact step(s); cache: policy-tests:pip | none | none | No source-verifiable failure risk found. |
| `phoenix-self-heal.yml` | valid and ready | push, pull_request, workflow_dispatch | contents | none | self-heal-gate | 0 artifact step(s); cache: self-heal-gate:pip | none | none | No source-verifiable failure risk found. |
| `policy-gate.yml` | valid and ready | pull_request, push, workflow_dispatch | contents | none | opa | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `pr-automation.yml` | valid and ready | pull_request | contents | GITHUB_TOKEN | triage | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `release-supply-chain.yml` | valid and ready | workflow_call | contents | GITHUB_TOKEN | build-sign-attest | 0 artifact step(s); cache: none | production | GHCR | No source-verifiable failure risk found. |
| `remove-homepage-crimson-loader.yml` | valid and ready | push, workflow_dispatch | contents | none | patch | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `repo-audit.yml` | valid and ready | schedule, workflow_dispatch | contents | GITHUB_TOKEN | audit | 1 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `sales-ops-briefing.yml` | valid and ready | schedule, workflow_dispatch | contents | BRIEFING_TO, DATABASE_URL, GMAIL_APP_PASSWORD, GMAIL_USER | briefing | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `security.yml` | valid and ready | pull_request, push, schedule | contents | none | dependency-review, secret-scan, workflow-lint | 0 artifact step(s); cache: workflow-lint:pip | none | none | No source-verifiable failure risk found. |
| `seo-optimizer.yml` | valid and ready | workflow_call, workflow_dispatch | contents | none | run | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `thought-leadership.yml` | valid and ready | workflow_call, workflow_dispatch | contents | none | run | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `viral-content.yml` | valid and ready | workflow_call, workflow_dispatch | contents | none | run | 0 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
| `workflow-doctor.yml` | valid and ready | schedule, push, workflow_dispatch | contents | GITHUB_TOKEN | audit, repair | 0 artifact step(s); cache: audit:pip, repair:pip | automation-write | none | No source-verifiable failure risk found. |
| `workflow-repair-agent.yml` | valid and ready | workflow_dispatch | contents, pull-requests, actions, id-token | none | inspect-and-fix | 1 artifact step(s); cache: none | none | none | No source-verifiable failure risk found. |
