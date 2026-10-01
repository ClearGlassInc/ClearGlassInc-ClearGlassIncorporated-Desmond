# Security Review — 2026-10-01

**Scope:** the repository at `b53bfd7`, its 85 workflows, its dependency
manifests, and GitHub-side state readable through the API. **Not in scope:**
live-host testing, authenticated DAST, the Render/Stripe/PayPal accounts. The
threat model itself stays in `security/HARDENING_AND_THREAT_MODEL.md`.

No secret value was printed, copied or transmitted at any point.

## Findings

Ordered by severity. "Fixed here" means fixed on this branch and awaiting review.

### S-N1 — Security tests can pass by skipping — P1 — Fixed here (needs review)

- **Evidence (VERIFIED):** with no `node` on `PATH`, `pytest tests/` reports
  1863 passed, 35 skipped, exit 0. 24 of those skips are Node-dependent tests,
  including `test_rfed_hash_parity.py` (an enforced gate per `CLAUDE.md`) and
  the admin login guard (open redirect, constant-time token compare, lockout).
  The admin suite also skips on Node < 22.6; a stub reporting v20.11.0
  reproduces that.
- **Root cause:** `ci.yml`'s `python-tests` job had no `actions/setup-node`
  step. It inherited the runner image's Node, which `test_admin_login_guard.py`
  records as 20 on `ubuntu-latest` (INFERRED).
- **Impact:** once Actions runs again, CI would report the admin auth tests as
  green while skipping them.
- **Fix:** `setup-node` (same SHA pin already used in `ci.yml`, Node 22) before
  `pytest`. `tests/test_node_toolchain_guard.py` fails if that step disappears,
  and fails on GitHub Actions if Node is absent or below 22.6.
- **Additive:** yes. **Approval:** `ci.yml` is HIGH in
  `scripts/automation_governance.py`, so a human must review it.
- **Rollback:** revert the commit.

### S-N2 — Third-party contact data and personal documents are published — P1 — REQUIRES APPROVAL

- **Evidence (VERIFIED):** the repository is public (`visibility: public`) and
  Pages publishes every tracked file (`.nojekyll`; the mechanism is documented
  in commit `612e47a`). At the root:
  - `remote_strike_pipeline.csv`: 11 rows of named companies and roles, with
    **3 third-party email addresses** in a "Verified direct email" column.
    Tracked since `49267a7` (2026-09-27).
  - 45 PDF, XLS/XLSX, CSV, TXT and ZIP files, including a personal cover letter,
    course certificates, a domain ownership letter, analytics exports named
    after the owner, and a site-visitor export (`cleaglassinc_visitors_*.xls`,
    contents not inspected).
- **Root cause:** files uploaded to the root, which is also the site root.
  `tests/test_no_prospect_files_published.py` guards only
  `offers/outreach/lead-list-*.csv`.
- **Impact:** third parties' contact details are downloadable from the company
  domain. Personal documents are public.
- **Safest fix:** the owner decides per file. For files that should not be
  public: remove from the tree, add to `.gitignore`, and extend the publication
  guard test. **Removal from the tree does not remove them from public git
  history**, the same limit `612e47a` recorded.
- **Not done here:** this audit's rules forbid deleting files without approval.

### S-N3 — `/ready` reports ready on a database with no schema — P2 — REQUIRES APPROVAL

- **Evidence (VERIFIED, Postgres 16.14):** booted as the compose stack was
  documented, `GET /ready` → **200** and `POST /revenue/leads` → **500**.
  `/ready` runs `SELECT 1` only. `GET /revenue/health`, which counts `leads`,
  would report `degraded` on the same database.
- **Impact:** an orchestrator health check passes while every write fails.
  Availability and observability, not confidentiality.
- **Proposed fix:** have `/ready` return 503 when
  `app.migrate.missing_columns()` reports gaps (cached once per process).
  Changes the endpoint's meaning, so it needs review: a Render health check
  could start failing on a drifted database, which is the point but a change.

### S-N4 — Auto Heal runs on every workflow completion with write scopes — P2 — REQUIRES APPROVAL

- **Evidence (VERIFIED):** `workflow_run: workflows: ["*"]` plus cron `*/30`;
  permissions `actions`, `contents`, `issues`, `pull-requests: write`. One merge
  produced runs #4278 to #4291 in 30 s. 4,291 runs to date.
- **Impact today:** noise only (F1). **When runners return:** every failed run
  of 84 other workflows can trigger a heal attempt that pushes a branch and
  opens a PR. The job is gated by the `automation-write` environment; whether
  that environment requires a reviewer is **UNKNOWN** (needs admin read).
- **Proposed fix:** list the workflows it should react to instead of `"*"`,
  and drop the cron to daily. HIGH path.

### S-N5 — The live Stripe key is readable outside its environment — P2 — REQUIRES APPROVAL

- **Evidence:** `sync-stripe-products.yml` job `plan-live-mode` reads
  `secrets.STRIPE_LIVE_SECRET_KEY` with **no** `environment:`; only
  `apply-live-mode` uses `environment: stripe-live`. For planning to work, the
  key must therefore be a repository-level secret (INFERRED). A
  repository-level secret is readable by any workflow file anyone with write
  access adds, on any branch, without branch protection to stop them (R7).
- **Proposed fix:** store a **restricted, read-only** live key (`rk_live_…`) for
  planning, and move the write-capable key into the `stripe-live` environment
  with required reviewers. Credential change: owner only.

### S-N6 — Five write-scoped workflows have no concurrency group — P3 — REQUIRES APPROVAL

`clearglassinc-military-op`, `dependency-updater`, `workflow-doctor`,
`remove-homepage-crimson-loader`, `workflow-repair-agent`. Overlapping runs can
race on the same push. One line each; HIGH path.

### S-N7 — `CG_ORG_PAT` reaches beyond this repository — P3 — UNKNOWN scope

Used by the daily `multi-repo-audit.yml`. A classic or fine-grained PAT is
tied to a person and outlives sessions. Its scopes cannot be read from here.
Recommend a GitHub App installation token or a fine-grained read-only PAT.

## Carried forward and re-checked

| ID | Finding | 2026-09-24 | 2026-10-01 |
|---|---|---|---|
| S4 | Master `ADMIN_API_KEY` typed into the public Revenue Command cockpit | Open | **Closed.** VERIFIED: `f8a225a` (2026-09-24 12:21 UTC) removed the cockpit and its `type="password"` field; no root page asks for an admin key |
| S5 | `/revenue/health` public, returns `last_stripe_event_at` | Open, LOW | **Still open**, VERIFIED in `routers/revenue.py:263` |
| S6 / R7 | `main` unprotected | Open, HIGH | **Still open.** VERIFIED: every branch on the first page of `list_branches` (100) reports `protected: false`. CODEOWNERS exists but enforces nothing without protection |
| S2 | `CRCS_AUDIT_HASH_KEY` | Fixed | Holds (`render.yaml` `generateValue`) |
| S1 | `events` ledger append-only | Fixed | Holds; Postgres migration tests pass (739/1) |

## Controls verified working

- **Secrets in the tree:** `scripts/secret_scan.py` clean; no tracked `.env`,
  key or certificate file.
- **Dependencies:** `npm audit` 0 in all 6 lockfiles; `pip-audit` 0 in all 7
  requirements files.
- **Workflow supply chain:** 85/85 declare `permissions`; 0 unpinned
  third-party actions; 0 `pull_request_target`; 0 untrusted event text in
  `run:`; 0 jobs without a timeout; `persist-credentials: false` on checkouts
  in `ci.yml`.
- **Money paths:** SKU-only checkout contract, webhook signature and
  idempotency, `ALWAYS_ESCALATE` for ad spend, live payments, contracts; all
  covered by the 739 control-plane tests.
- **Access control:** `test_route_auth_coverage.py` (23 tests) and
  `test_web_stack_guard.py` pass; governance self-check `[]`.
- **Live Stripe sync:** four independent gates before any live write.
- **Edge apply:** dispatch-only, environment-scoped.

## Not verified

GitHub environment protection rules (`automation-write`, `stripe-live`,
`production`, `edge-*`), secret presence, Actions policy, and organisation
billing. All need an admin read this session does not have.
