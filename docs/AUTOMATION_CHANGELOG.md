# Automation changelog

Every change made to this repository by automation, and every change to what
automation is allowed to do. Newest first.

Entries record what was changed, the evidence it was based on, how it was
validated, and how to reverse it. An entry without those is not a record, it is
a note.

---

## 2026-10-06 — Repair after three CI/CD layers merged: ci.yml validity, auto-fix trust boundary

**Changes what automation may do:** yes. `auto-fix.yml` now runs in the
`automation-write` environment, and can no longer run code a pull request supplies.

### What broke

Three implementations of the same CI/CD blueprint merged within an hour (#187,
#188, #190) and their conflicts were resolved by hand. The result on `main`
(`7e88a90`):

- `ci.yml` was invalid. Its `stack` job, from #190, called `reusable-ci.yml` with 8
  inputs that file does not declare, because the merge kept #187's version, and
  without a grant its `codeql` job requires. Its `release` job called
  `deploy-promotion.yml`, which declares no `workflow_call`. GitHub rejects such a
  file outright, so none of `ci.yml`'s seven original gates would have run.
- `auto-fix.yml` held `contents: write` and `pull-requests: write`, checked out the
  PR head, and then ran `./.github/actions/verified-commit` and `post-pr-comment`
  from that checkout. A same-repository PR could edit them to run its own code with
  the token. `deploy-staging.yml`'s comment job had the same pattern with
  `pull-requests: write`.
- `tests/test_cicd_layer.py`, from #188, asserted #188's workflow design, which the
  merge replaced: 14 failures on `main`.

The 2026-10-06 entry below describes #188 as written. Most of the files it lists
were superseded in that merge by #187's versions.

**Detected by:** local runs of `scripts/ci_local.py` and actionlint on `main`.
**Not** detected by `workflow_doctor.py` or `audit_github_actions.py`, which both
passed: neither reads reusable-workflow inputs or permissions, and the auditor
cannot see a `git push` made inside a composite action.

### Fixed

- `ci.yml`: `stack` now calls `reusable-component-ci.yml`, #190's component
  workflow restored verbatim from `e0301ef` with its toolchain action
  (`.github/actions/setup-component-toolchain`). The `release` job is removed:
  `deploy-promotion.yml` starts itself on a push to `main`, so a second caller
  would promote every commit twice.
- `auto-fix.yml`: restores `.github/actions` from the default branch and proves it
  with `git diff --quiet`, before `verified-commit` and again after it (it resets
  the worktree to the PR branch). The job is bound to `automation-write`.
- `deploy-staging.yml`: the comment job checks out its actions from the default branch.
- `tests/test_cicd_layer.py`: rewritten for the design on `main`. It checks every
  reusable-workflow call site for declared inputs and permissions, and every
  write-token job triggered by a pull request for PR-controlled local actions.

### Validation

- actionlint on `ci.yml` and its callees: 9 errors before, 0 after.
- `tests/test_cicd_layer.py`: 44 passed. Swapping back `main`'s unfixed `ci.yml`,
  `auto-fix.yml` or `deploy-staging.yml` fails it (5, 2 and 1 tests), as does
  removing the promotion gate's `security-events` grant or auto-fix's second restore.
- The restore step, run against a scratch clone: a PR-modified `post-pr-comment` is
  replaced byte-for-byte, a planted action is removed, nothing is staged, and a PR
  that makes `.github` a symlink fails the step.
- `scripts/ci_local.py`: 10 passed, 6 skipped (network). pytest 2099 passed; its 5
  failures are the `clearglass-legal-assistance/prototype/` pages, also failing on
  `main` and untouched here. Control-plane: 735 passed.

### Still open

- #190's OIDC deploy scripts (`scripts/ci/deploy_target.sh`, `scripts/ci/release.py`)
  are on `main` but no workflow calls them. Wiring them in, or retiring #187's
  Render promotion, is an owner decision.
- `.github/actions/store-setup` interpolates an input into a shell script. It
  predates this layer.

### Reversing

Revert the commit. Doing so makes `ci.yml` invalid again.

---

## 2026-10-06 — CI/CD layer: reusable CI/deploy, staging, promotion, auto-fix, heal, telemetry

**Changes what automation may do:** yes. Adds one workflow that pushes to
pull-request branches (`auto-fix.yml`) and two deploy paths, both off by default.
Full description: `AUTOMATION.md`.

### What was added

Seven workflows (`reusable-ci`, `reusable-deploy`, `deploy-staging`,
`deploy-promotion`, `auto-fix`, `heal-pipeline`, `ci-telemetry`), three composite
actions under `.github/actions/`, `AUTOMATION.md`, a CI/CD section in
`SECURITY.md`, `/.github/actions/` in the root `CODEOWNERS`, and
`tests/test_cicd_layer.py`. No existing workflow, action or script was edited
or removed.

### Evidence it was based on

An external blueprint, adapted where its literal form would have broken this
repository:

- its `ci.yml` would have replaced the existing one and dropped five of its gates;
- it called reusable workflows from steps, which GitHub rejects;
- it deployed per-PR through `pr-<n>` environments, which hold no secrets;
- `if: failure() && ${{ inputs.enable_rollback }}` is always true (actionlint
  `if-cond`), so it would have rolled back on every failure, and automatic
  rollback contradicts `docs/INCIDENT_RESPONSE.md`;
- its auto-fix ran PR code with a write token and ran black and prettier over a
  repository that configures neither;
- its `.github/CODEOWNERS` would have shadowed the root file;
- its actions were unpinned tags, which `scripts/workflow_doctor.py` fails.

### Validated

- `scripts/workflow_doctor.py`: 0 errors, 98 files. `scripts/audit_github_actions.py`:
  all seven new workflows "valid and ready", no warnings. Defender workflow scan:
  0 findings on the new files.
- actionlint 1.7.12 with shellcheck: clean on the seven new files.
- `tests/test_cicd_layer.py`: 26 passed, and each of four injected regressions
  (PR code in the write job, production without a real staging deploy, input
  interpolated into JavaScript, a per-PR environment) fails exactly one test.
- `scripts/ci_local.py`: same result as untouched `main` (163fb9b). The only
  failures are the five pre-existing ones in `clearglass-legal-assistance/prototype/`.
- Nothing ran in GitHub Actions: runners are still not dispatched.

### Reversing

Set `CG_AUTO_FIX_DISABLED` and `CG_HEAL_PIPELINE_DISABLED` to `true` to stop
the event-driven workflows without a code change; the deploy workflows are
already off unless enabled. To remove the layer, revert the commit; nothing
else depends on it.

---

## 2026-09-15 — INCIDENT: admin app could not install (react/react-dom split)

**Severity:** production-blocking for the `admin` app. Not customer-facing — the
storefront, the control plane and the static site were unaffected.
**Detected by:** manual verification of `main` after a batch of auto-merged
dependency PRs. **Not** detected by CI, which was not running.

### What broke

Dependabot PR #48 (`deps(admin): bump react and @types/react in /admin`) raised
`react` 18.3.1 → 19.3.0 and `@types/react` 18.3.31 → 19.3.0, and left
`react-dom` at 18.3.1. Dependabot bundles `react` with `@types/react` because
they are linked, but treats `react-dom` as a separate update, so the pair split.

`admin/package-lock.json` then pinned `react@19.3.0` against `react-dom@18.3.1`,
which `npm ci` refuses outright:

```
Conflicting peer dependency: react@18.3.1
  peer react@"^18.3.1" from react-dom@18.3.1
```

The app could not be installed, typechecked, built, or deployed.

### Why it reached `main`

Three controls that should each have caught it were all inert:

1. `Commerce Frontend CI` runs `npm ci` and would have failed in seconds — but
   GitHub Actions was not dispatching runners (`PRODUCTION-RECOVERY.md` §1.1),
   so it reported nothing.
2. `.github/dependabot.yml` labels these PRs `human-approval-required`, which is
   a label, not a gate. The PRs were merged.
3. `scripts/automation_governance.py` classifies lockfiles as protected and
   never auto-mergeable — but it governs *this repository's own* automation, not
   a human merging a Dependabot PR. It was never consulted.

The common cause is the first: **a merge policy that depends on CI is not a
policy while CI is down.** Twelve dependency PRs (#38–#48, #50) merged in that
window, including `typescript` → 7.0.2, `@types/node` → 26.5.1, and several
Actions majors. Only #48 broke anything; the others were verified after the fact
and are fine.

### Fixed

| Change | Why |
|---|---|
| `admin/package.json`: `react-dom` → `^19.3.0` | Completes the upgrade that #48 started, rather than reverting it. Next 16.3.5 accepts `react-dom@^19.0.0`, and React 19 typechecks and builds clean against this app's 29 source files |
| `admin/package-lock.json` regenerated | Via `npm install --package-lock-only` — the repo's tooling, never by hand |
| `.github/dependabot.yml`: new `react` group for both apps | Groups `react`, `react-dom`, `@types/react`, `@types/react-dom` across **all** update types including major, so the pair can never split again |
| `tests/test_frontend_dependency_integrity.py` (new) | Turns this class of defect into a red test that runs without a runner |

The new test is the durable part. It reads the committed manifests and lockfiles
in pure Python — no network, no `node_modules`, no Actions — so it holds while
CI is down, which is exactly when a broken manifest can reach `main`
unchallenged. It checks both the declared ranges and the resolved pins, because
`npm ci` installs the lockfile, not the manifest.

### Validation

Reproduced the failure first, then showed the same checks passing:

| Check | Before (main `79c493b`) | After |
|---|---|---|
| `tests/test_frontend_dependency_integrity.py` | 2 failed | 10 passed, 4 skipped |
| `admin`: `npm ci` | **ERESOLVE, exit 1** | exit 0 |
| `admin`: `npx tsc --noEmit` | not reachable | exit 0 |
| `admin`: `npm run build` | not reachable | exit 0, 16 routes |
| `storefront`: `npm ci` / `tsc` / `build` | exit 0 | exit 0 (unaffected) |
| root `pytest tests/` | 1253 passed | 1263 passed, 9 skipped |
| `scripts/ci_local.py` | 9 passed | 9 passed, 0 failed |

### Still open

**PR #49** (`deps(storefront): bump react and @types/react in /storefront`) is
the same split, aimed at the storefront. Merging it as-is reproduces this
incident there. It must be closed and superseded by a grouped update, or have
`react-dom` raised in the same PR. The `dependabot.yml` change above prevents
the *next* one; it cannot retroactively fix a PR already open.

### Reversing

Revert the merge commit. `admin/` returns to react 18 across the board, which
also resolves the conflict — the pairing is what matters, not the major.

---

## 2026-09-15 — Governed revenue and reliability layer

**Policy version:** `automation_governance` 1.0.0 (new)
**Merged by:** human review (this change touches protected paths throughout and
is not auto-mergeable under its own policy)

### Changed

| Area | Change |
|---|---|
| Payments | PayPal Orders v2 integration added (`control-plane/app/paypal.py`, `app/routers/paypal.py`). Server-priced, fail-closed webhook verification, catalogue reconciliation, capture behind the approval gate |
| Payments | Idempotent order booking extracted to `control-plane/app/order_ledger.py`; Stripe and PayPal now share one implementation |
| Automation | `scripts/automation_governance.py` — protected-path classification and circuit breakers, with a `--self-check` |
| Security | `scripts/secret_scan.py` extracted from `security.yml`'s inline heredoc; Stripe live-key patterns added |
| CI | `.github/workflows/maintenance-review.yml` (weekly, proposes only), `.github/workflows/rollback.yml` (manual dispatch), `.github/dependabot.yml` |
| Docs | `docs/AUTOMATION_POLICY.md`, `docs/REVENUE_OPERATIONS.md`, `docs/INCIDENT_RESPONSE.md`, `OPERATIONS_HANDOFF.md`, `control-plane/.env.example` |

### Defects found and fixed

1. **`test_route_auth_coverage` was red on the branch.** `/subscriptions/portal`
   and `/subscriptions/webhook` had shipped without exemption entries. Both
   verified safe-open and documented; `/subscriptions/portal` was additionally
   missing the per-IP throttle its twin has, which was added rather than
   asserted.
2. **`audit_github_actions` was red on the branch.**
   `revenue-pipeline-agent.yml` used an unpinned `actions/checkout@v4`. Pinned,
   with `persist-credentials: false` and a job timeout.
3. **The protected-path classifier ignored every dotfile.** `lstrip("./")`
   stripped leading dots, so `.github/workflows/**` and `.env*` fell out of the
   protected set while the policy reported itself as enforcing. Caught by its own
   tests before first use.
4. **The credential-scan test was gitignored.** `.gitignore`'s `*_secret*` rule
   excluded `tests/test_secret_scan.py`. Renamed to `test_credential_scan.py`; a
   test that is not in the repository is not a test.

### Validation

Run locally, because Actions is not dispatching runners
(`PRODUCTION-RECOVERY.md` §1.1) and a green check is currently the absence of
signal:

- `ruff check .` in `control-plane` — clean
- `python -m pytest tests/ -q` in `control-plane` — 378 passed, 1 skipped
- `pytest tests/test_automation_governance.py tests/test_credential_scan.py` — 79 passed
- `python3 scripts/automation_governance.py --self-check` — 16 invariants hold
- `python3 scripts/secret_scan.py` — clean
- `python3 scripts/audit_github_actions.py` — 0 errors
- `python3 scripts/workflow_doctor.py` — 82 files, 0 errors

### Not verified

PayPal has never been run against PayPal. No credentials are configured and the
API base defaults to the sandbox. It books nothing. The verification checklist is
in `docs/REVENUE_OPERATIONS.md` and must be completed and recorded here before
PayPal is described as live anywhere.

### Reversing

Revert the merge commit. The two behavioural edits to existing code — the
`/subscriptions/portal` throttle and the Stripe router's delegation to the shared
ledger — are covered by the existing suite, so a revert is detectable by test
rather than by inspection.
