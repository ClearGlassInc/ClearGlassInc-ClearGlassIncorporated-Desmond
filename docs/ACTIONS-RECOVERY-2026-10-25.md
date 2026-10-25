# GitHub Actions recovery and repair operations

Observed 2026-10-25 for `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond`.
Baseline: `main` at `dfdc3123970f227cac6152afd9d485b11c99699f`.
Repair branch: `repair/github-reliability-2026-10-25`.

## Verified blocker and rollout order

GitHub check annotations explicitly state:

> The job was not started because your account is locked due to a billing issue.

This is a platform/account blocker, not evidence that application tests failed.
The sampled jobs have `runner_id: 0`, no runner name and no steps; job logs are
unavailable. No repository edit or new runner configuration resolves this lock.

| Workflow | Run | Observed conclusion |
|---|---|---|
| CI | [40194965988](https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond/actions/runs/40194965988) | failure before steps |
| 4-D Dominance Pipeline | [40187167093](https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond/actions/runs/40187167093) | failure before steps |
| ARTEMIS Engineering CI | [38469599470](https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond/actions/runs/38469599470) | failure before steps |
| Advanced SEO Growth | [40094082020](https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond/actions/runs/40094082020) | failure before steps |
| Deploy Pages | [40194965795](https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond/actions/runs/40194965795) | build failure, deploy skipped |
| GitHub-managed Pages | [40194965970](https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond/actions/runs/40194965970) | success on baseline SHA |

An IESO Public Feed run [37655505283](https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond/actions/runs/37655505283)
remains queued since 2026-10-07. Its individual waiting reason is unverified.
Recent Auto Heal runs include failures, skips and cancellations; do not infer a
successful repair from a skipped/cancelled result.

1. **Account owner/billing manager:** open the owning account's GitHub
   **Settings → Billing and licensing**, resolve the displayed billing lock,
   and contact GitHub Support if the lock remains. Any payment or spending-limit
   change requires the owner's authorization; this patch performs neither.
2. **Repository administrator:** approve and configure protection for
   `automation-write` before permitting mutation workflows: required human
   reviewers, prevention of self-approval where supported, and trusted branch
   restrictions. The observed environment has `protection_rules: []` and no
   deployment branch policy. Merely referencing this environment is not an
   approval gate. `github-pages`, `staging`, and `copilot` also had no protection
   rules. Production/preview protection must be verified before deployment.
3. **Repository administrator:** separately approve branch protection/rulesets
   for `main`, including review and the existing `CI result` check. The branch
   API reports `protected: false`, status enforcement off, and rulesets empty.
   Do not rename required checks or bypass reviews to merge this repair.
4. **Operator:** obtain approval for the actual branch/PR-triggered effects
   described below, review this patch, then publish its repair branch and PR.
5. **Operator after the account unlock:** inspect and run **Runner Canary**
   (`runner-canary.yml`) on a reviewed ref. It has only shell diagnostics,
   read-only contents permission, no checkout/actions/secrets, and a five-minute
   timeout. Use its existing manual dispatch, or retry a known failed canary.
   Confirm a nonzero runner ID and successful steps, then run validation CI.
   Do not dispatch Workflow Doctor to test runner availability: manual dispatch
   also enables its repair job. Never use Dispatch All Workflows as recovery.
6. Monitor actual run IDs/jobs/annotations. On failure, fix the first actionable
   cause, rerun local checks, and retry at most three times per unresolved cause.
   A repeated billing-lock annotation is a reason to stop and escalate.

Pages is currently `build_type: legacy`, source `main:/`, with HTTPS enforced.
Preserve that configuration. A successful managed Pages run is independent of
CI and does not verify any backend deployment or current website behavior.

## Source repairs and review boundaries

- Workflow Doctor formerly force-reset `bot/workflow-doctor-repair`, overwriting
  previous review work. It now seeds an ordinary, unique
  `bot/workflow-doctor-repair-<run-id>-<attempt>` branch, used consistently by
  the signing action and PR creation. No auto-merge was added.
- `verified-commit` formerly serialized GraphQL `fileChanges` as a string with
  `gh -f`. It now sends a complete JSON request through `gh api graphql --input -`.
  Rename detection is disabled in the payload helper so a staged rename includes
  both the old-path deletion and the new-path addition. Existing bounded retry
  and ordinary git fallback remain; hosted signing has not been executed here.
- Existing root CI lint failures in legacy Python sources are repaired without
  adding exclusions, disabling checks, or introducing dependencies.

The existing workflow security audit is a **source-only** check: its label
`valid and ready` does not establish billing eligibility, environment protection,
secret availability, or remote action provenance. Inventory all workflows with:

```sh
python3 scripts/workflow_doctor.py
python3 scripts/audit_github_actions.py --markdown
python3 scripts/audit_github_actions.py --json
```

The baseline contains 98 workflows and five local actions; ten workflows expose
`workflow_call` and 39 are scheduled. Existing CI already validates PRs and main,
and `.github/dependabot.yml` already schedules reviewed dependency/action updates.
No extra scheduler, auto-merge mechanism, runner or GitHub App is needed.

### Publishing and workflow effects

A workflow-file push runs Workflow Doctor's audit, not its repair job. However,
its failure can invoke the default branch's wildcard Auto Heal controller, which
has issue, branch and PR write capabilities. This remains true when runners are
currently blocked, because account status can change between inspection and run.

Opening a main-targeting PR can run PR Automation (labels/comments), Defender
Watch (incident issues and configured Slack/Discord alerts), and configured
Cloud Run/Render preview automation. Failed CI can invoke Auto-Fix and Heal
Pipeline. Inspect current configuration and obtain authorization for these
effects before publishing; a draft PR still emits PR events. Do not bypass this
by disabling checks or assuming the billing lock will prevent side effects.

### Configuration

These source repairs need no new secret or variable. The existing built-in
`GITHUB_TOKEN` is used by the signing/repair jobs with `contents: write` and,
for PR creation, `pull-requests: write`. An administrator must verify Actions
policy allows those operations; API metadata permissions alone are insufficient.

No secret values were inspected. Deployment/provider variables and webhook
availability are unverified. Configure existing secrets only in GitHub's
repository/environment secret UI or the provider's secret store; never paste
values into chat. These repairs do not require enabling deployment integrations.

## Local verification and rollback

Use an isolated environment with the repository's existing development tools:
pytest, pytest-cov, PyYAML and `ruff==0.15.8`. No dependency declarations or versions change.
The validation host used Python 3.12 and Node 24; hosted CI requests Python 3.11
and Node 22, so hosted runtime compatibility remains unverified.

```sh
python -m pytest tests/test_workflow_doctor_review_branch.py tests/test_verified_commit.py tests/test_cicd_layer.py tests/test_workflow_doctor.py tests/test_audit_github_actions.py -q
python -m pytest tests/ --cov --cov-report=xml -q
python -m ruff check .
python scripts/workflow_doctor.py
python scripts/audit_github_actions.py
git diff --check
```

The new regressions execute real local git indexes and a local bare remote;
GitHub request boundaries are replaced offline. They verify branch preservation,
structured request data, literal metadata, rename deletion, no-change behavior
and fallback. They do not prove GitHub accepted a signing request.

### Recorded validation

| Check | Result |
|---|---|
| Root CI test command, `pytest tests/ --cov --cov-report=xml -q` | 2,342 passed, 13 skipped, exit 0; loopback/network permission enabled |
| Initial restricted-sandbox root run | 2,325 passed, 13 skipped, 2 failed and 15 errors; the 17 blocked cases all raised socket `PermissionError` |
| Socket-dependent modules rerun with permission | 29 passed |
| Legacy `test_clearglass.py` in disposable directories | Baseline 19 passed; repaired 19 passed, using the declared `ecdsa==0.18.0` |
| Root `ruff check .`, version 0.15.8 | Baseline 43 errors; repaired zero errors |
| Workflow Doctor | 103 workflow/action files, zero errors, zero version bumps |
| Workflow safety audit | No errors; 90 source-ready, seven improvement warnings, one unsafe workflow; runtime protections unverified except the environment observations above |
| Changed workflow/composite Bash blocks | Eight scripts passed `bash -n` |
| Changed legacy sources and payload helper | `py_compile` passed |
| 4-D pipeline, `--all`, local mock backend | Four domains, eight draft tasks, exit 0; no publication/deployment/provider call |
| SEO engine self-tests and independent unittest suite | Seven self-tests and five unittest cases passed |
| Site reliability audit / OSINT release dry-run | Zero errors and 20 site warnings / eight of eight checks passed |
| Diff whitespace and independent code review | Passed; no blocking review findings |

Coverage was written outside the checkout. No new hosted run was triggered.
`actionlint`, frontend builds/typechecks, Lighthouse, provider deployments and
live API signing were **not executed**. The thirteen skipped root tests remain
skipped; the pass count does not include them. Local checks do not establish a
passing GitHub required check.

### File-level scope record

| Files | Change and reason | Scope / risk | Verification |
|---|---|---|---|
| `.github/workflows/workflow-doctor.yml` | Unique repair branches preserve earlier review work | Authorized automation repair / low | Local bare-remote regression, YAML/contract checks, Bash syntax |
| `.github/actions/verified-commit/action.yml` | Structured GraphQL request restores the signing path | Authorized automation repair / moderate | Real Bash with offline API boundary; success, fallback, literal metadata and no-change tests |
| `.github/actions/verified-commit/build_file_changes.py` | Include rename deletion alongside addition | Authorized automation repair / low | Real staged-rename regression |
| `tests/test_verified_commit.py`, `tests/test_workflow_doctor_review_branch.py` | Prevent recurrence of the diagnosed defects | Scope A CI tests / low | Expected baseline failures, then full root suite passed |
| `clearglass_api.py`, `clearglass_blockchain.py`, `clearglass_cli.py`, `clearglass_network.py`, `clearglass_wallet.py`, `examples.py`, `setup.py`, `test_clearglass.py` | Clear existing lint errors; narrow exception catches without masking process cancellation | Scope A CI correction / low | Ruff, compilation, legacy baseline/repaired tests, root suite and independent review |
| `docs/ACTIONS-RECOVERY-2026-10-25.md` | Preserve evidence, recovery order, configuration and rollback | Operations documentation / low | Compared with source and public GitHub responses |

Files deleted: **NONE**. Production changes: **NONE**. Verification:
**PARTIALLY VERIFIED** overall (local checks verified; hosted execution blocked).

Before merge, reject the patch by closing its PR; no production rollback is
needed. After merge, revert its repair commit through a reviewed PR and rerun
validation. Do not force-push or automatically delete review branches. Reverting
will restore the diagnosed force-reset/payload defects, so prefer a narrow
follow-up repair when possible. The repository owner controls merge and rollback.

Weekly: review failed/cancelled/queued runs and first annotations, environment
protection, the workflow inventory and Dependabot PRs. Treat the Intelligence
Graph direct-to-main scheduled writer as unsafe pending governance remediation;
do not execute it as part of this recovery. Keep existing advisory audit warnings
visible rather than marking them as resolved by a successful YAML parse.
