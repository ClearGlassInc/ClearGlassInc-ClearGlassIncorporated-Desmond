# Improvement Backlog — 2026-10-01

Path risk comes from the repository's own classifier,
`scripts/automation_governance.classify_change()`: **LOW** may auto-merge,
**MEDIUM** needs review, **HIGH** is a protected path that is never
auto-merged. Nothing in this backlog merges itself.

## Done on this branch (awaiting review)

### I-1 — CI runs the Node-dependent tests it claims to (N1 / S-N1)

| | |
|---|---|
| Problem | `python-tests` inherited the runner's Node; 24 tests skip without Node, and the admin login guard skips below 22.6, and pytest still exits 0 |
| Evidence | No-Node run: 1863 passed / 35 skipped / exit 0. Stub Node 20: guard suite skips |
| Change | `actions/setup-node` (existing SHA pin, Node 22) before `pytest` in `ci.yml`; new `tests/test_node_toolchain_guard.py` |
| Files | `.github/workflows/ci.yml` (HIGH, +6 lines), `tests/test_node_toolchain_guard.py` (LOW, new) |
| Benefit | The RFED parity gate and admin auth tests cannot pass by skipping in CI |
| Risk | Low. Adds ~5 s to the job. No new third-party code |
| Test plan | Guard red on `main`'s `ci.yml`, green after; under `GITHUB_ACTIONS=true` red with no Node and with Node 20, green with Node 22. Workflow doctor and safety invariants pass |
| Rollback | Revert the commit |
| Approval | **Yes**: `ci.yml` is a protected path |
| Before → after | `test_ci_python_tests_job_installs_node_before_pytest`: **fail → pass** |

### I-2 — Local stack instructions that work (N8)

| | |
|---|---|
| Problem | `docker compose up --build` exits 1 on a fresh clone; `DEPLOY.md` copied the wrong `.env.example`; neither path created the schema |
| Evidence | `docker compose config` exit 1; on PG 16.14 the documented path gives `/ready` 200 and `POST /revenue/leads` **500** |
| Change | Docs: copy `control-plane/.env.example`, append `RUN_MIGRATIONS=true` |
| Files | `DEPLOY.md`, `docs/RUNBOOK.md`, `README.md`, `CLAUDE.md` (all LOW) |
| Benefit | First local run records a lead |
| Risk | None to runtime |
| Test plan | `docker compose config` exit 0 with `RUN_MIGRATIONS=true` resolved; same env on PG 16.14: `POST /revenue/leads` **201** |
| Rollback | Revert the commit |
| Approval | No (LOW paths) |

### I-3 — Documentation drift

`CLAUDE.md` workflow counts (81/36/16 → 85/38/18), F1 re-verified with today's
job ID, `docs/ARCHITECTURE.md` §8 counts, `docs/CHANGELOG.md` entry. LOW.

## Proposed — needs approval

Ordered by the risk register's priority.

| ID | Change | Files (path risk) | Benefit | Risk | Test plan | Rollback | Approval |
|---|---|---|---|---|---|---|---|
| I-4 | Remove or relocate published personal and third-party files; extend `test_no_prospect_files_published.py` to cover root `*.csv/*.xls*/*.pdf` with an allow-list | root uploads, `.gitignore`, test (LOW/MEDIUM) | Stops publishing third-party emails | History still holds them | Guard test red on current tree, green after | Restore from git | **Owner: per-file decision; deletion** |
| I-5 | Auto Heal: list the workflows it watches instead of `"*"`; cron `*/30` → daily | `auto-heal.yml` (HIGH) | Runs only for watched failures instead of every completion of 84 workflows; 47 fewer cron runs a day | A failure in an unlisted workflow goes unhealed | `workflow_doctor`, `audit_github_actions`, `test_workflow_doctor.py` | Revert | **Yes** |
| I-6 | Staged re-enable after F1: disable the 38 scheduled workflows, re-enable in batches of 5 read-only first, write-scoped last | Actions settings (no file change) | Controlled blast radius | Missed runs during staging | Each batch: one green run before the next | Re-enable all | **Owner** |
| I-7 | `/ready` returns 503 when `missing_columns()` reports gaps (computed once at startup) | `control-plane/app/main.py` (MEDIUM), new test | Health check stops hiding a schemaless DB | A Render health check fails on a drifted DB (intended) | New test: schemaless PG → 503; migrated PG → 200; existing `/ready` tests | Revert | **Yes**: endpoint semantics |
| I-8 | Constraints file pinned to the tested set; Dockerfile installs with `-c` | `control-plane/constraints.txt` (new), `Dockerfile` (MEDIUM), `requirements.txt` (HIGH) | Image matches what was tested | Manual bumps needed (Dependabot can do them) | Suite on the pinned set; image build once F1 clears | Remove `-c` | **Yes** |
| I-9 | Restricted read-only live key for `plan-live-mode`; write key only in `stripe-live` with required reviewers | GitHub secrets + environments; `sync-stripe-products.yml` (HIGH) | Live write key unreachable from arbitrary workflows | Misconfiguration blocks planning | Dispatch plan in test mode; confirm `rk_live` cannot write | Restore secret | **Owner: credentials** |
| I-10 | `concurrency` group on the 5 write-scoped workflows without one | 5 workflow files (HIGH) | No push races | None meaningful | Workflow gates | Revert | **Yes** |
| I-11 | Set `RUN_MIGRATIONS: "true"` in compose's `environment:` so the docs step is unnecessary | `docker-compose.yml` (HIGH) | One fewer manual step | None (local only) | `docker compose config`; PG reproduction | Revert | **Yes** |
| I-12 | `ci_local.py` prints a warning when Node is missing or < 22.6 | `scripts/ci_local.py` (MEDIUM) | Local runs say which gates skipped | None | Run with stub Node 20 | Revert | Review |
| I-13 | Postgres service in `commerce-deploy.yml` so the 4 migration tests run in CI | workflow (HIGH) | Migration tests in CI | Slower job | Job green with 739/1 | Revert | **Yes**, after F1 |
| I-14 | Replace `CG_ORG_PAT` with a GitHub App token | secrets, `multi-repo-audit.yml` | No person-bound token | Setup work | Dispatch once | Restore PAT | **Owner** |
| I-15 | Delete merged branches (keep `backup/*`) | GitHub | Less clutter | Losing an unmerged branch | List merged-only first | Recreate from SHA | **Owner** |

## Owner-only, no code

1. **F1:** fix Actions entitlement in organisation settings (billing hold,
   spending limit, allowed-actions policy, Actions toggle). Exit condition: a
   `ci.yml` job with `runner_id != 0` and a non-empty `steps` array.
2. **R7:** protect `main` (1 approving review; dismiss stale approvals; restrict
   force-push and deletion).
3. **09-24 R3:** deploy the Render blueprint and set `cg-revenue-api`.
4. **R3:** choose one first-offer price.

## The self-improvement loop, as it can run today

Section 6 of the brief asks for a continuous-improvement loop. Most of its
machinery already exists: `scripts/ci_local.py`, `workflow_doctor.py`,
`audit_github_actions.py`, `auto-heal.yml`, `maintenance-review.yml`, and dated
audits. None of the Actions half can run until F1 clears, and the baseline
already argued against adding YAML that cannot be verified. This audit adds no
workflow. The loop today is:

1. Every session runs `python3 scripts/ci_local.py` before pushing (the only
   signal while F1 holds).
2. Each audit re-measures the previous one's numbers and register, as this
   one did for 2026-09-24.
3. A finding that "passes by skipping" gets a guard test that fails in CI
   (`test_web_stack_guard.py`, `test_node_toolchain_guard.py`).
4. After F1: run I-5 and I-6 before letting the scheduled loop resume.
