# Automation changelog

Every change made to this repository by automation, and every change to what
automation is allowed to do. Newest first.

Entries record what was changed, the evidence it was based on, how it was
validated, and how to reverse it. An entry without those is not a record, it is
a note.

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
