# Automation changelog

Every change made to this repository by automation, and every change to what
automation is allowed to do. Newest first.

Entries record what was changed, the evidence it was based on, how it was
validated, and how to reverse it. An entry without those is not a record, it is
a note.

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
