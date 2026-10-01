# Validation Report — 2026-10-01

Covers the validation plan, what was run, what each change was checked
against, and what could not be checked. Raw numbers are in `TEST_BASELINE.md`.

## 1. Validation plan

| Stage | What | Needs | Run here |
|---|---|---|---|
| 0 | Snapshot: commit, branch, clean tree, tool versions, live Actions state | git, GitHub API (read) | Yes |
| 1 | Offline gates: `ci_local.py`, root pytest, ruff | Python | Yes |
| 2 | Control plane: ruff, pytest on SQLite and Postgres, governance self-check | Python, Postgres | Yes (local PG 16.14) |
| 3 | Node: `npm ci`, `tsc`, `next build`, `npm audit` for every lockfile | Node 22 | Yes |
| 4 | Dependencies: `pip-audit`, `npm audit` | Network to advisory DBs | Yes |
| 5 | Supply chain: workflow parse, permissions, pins, triggers, injection | PyYAML | Yes |
| 6 | Rust sidecar: `cargo test --locked` | cargo | Yes |
| 7 | Containers: `docker compose up`, image builds | Docker daemon | **No** (no daemon); `docker compose config` instead |
| 8 | CI on GitHub | Runners | **No** (F1) |
| 9 | Live site, Render, payment sandboxes | Network + owner credentials | **No** (out of scope) |

Re-run stages 1 to 3 after every logical change; record the tree state before and after.

## 2. Change I-1: CI pins Node for the root suite

**Reproduce the original failure.**

| Condition | Command | Result |
|---|---|---|
| No `node` on `PATH` | `pytest tests/ -q -rs` | 1863 passed, **35 skipped**, exit 0. 24 Node-dependent skips |
| `main`'s `ci.yml` | `pytest tests/test_node_toolchain_guard.py` | **FAIL**: "ci.yml python-tests never runs actions/setup-node…" |
| `GITHUB_ACTIONS=true`, no Node | same, Actions test | **FAIL**: "node is not on PATH: 24 Node-dependent tests are skipping" |
| `GITHUB_ACTIONS=true`, stub Node v20.11.0 | same | **FAIL**: "node 20.11 cannot strip TypeScript types…" |

**Show the fix.**

| Condition | Result |
|---|---|
| This branch's `ci.yml` | contract test **PASS** |
| `GITHUB_ACTIONS=true`, Node 22.22.0 | Actions test **PASS** |
| `scripts/workflow_doctor.py` | 87 files, 0 errors |
| `scripts/audit_github_actions.py` | every file valid |
| `test_workflow_doctor.py`, `test_pages_deployment_workflows.py`, `test_dispatch_all_workflows.py`, `test_automation_governance.py` | 79 passed |

**Adversarial re-read.** The new step reuses the SHA `ci.yml` already pins for
its Lighthouse job (`820762786…`, also used five times in
`sync-stripe-products.yml`), so no new third-party code. It sits before `pip
install` and `pytest`; the contract test asserts that order. It does not
enable npm caching, so it needs no lockfile. The Actions-only test skips
locally, so a developer without Node is not blocked; the contract test runs
everywhere.

## 3. Change I-2: local stack instructions

Reproduced in-process with the real app factory (`app.main.create_app`) and
FastAPI's `TestClient` against Postgres 16.14. That is the same Postgres major
as compose's `postgres:16-alpine`. Env matched what compose passes to the
container.

| Scenario | Schema flags | Manual SQL | `GET /ready` | `POST /revenue/leads` |
|---|---|---|---|---|
| A: `DEPLOY.md` §B as it was | both `false` | `001_init.sql` | 200 | **500** |
| B: same, no manual step | both `false` | none | 200 | **500** |
| C: corrected docs | `RUN_MIGRATIONS=true` | none | 200 | **201** |

Compose itself:

| Check | Result |
|---|---|
| `docker compose config` with no `.env` (fresh clone) | **exit 1**: "env file … .env not found" |
| After `cp control-plane/.env.example .env` and appending `RUN_MIGRATIONS=true` | exit 0; resolved `control-plane` env has `RUN_MIGRATIONS=true`, `AUTO_CREATE_TABLES=false`, `APP_ENV=development`, `DATABASE_URL` → `db:5432` |

**Not verified:** the containers themselves. With no Docker daemon, the
image build and `docker compose up` were not run. The behaviour above is the
app under the same env, not the container.

## 4. Full re-run after all changes

| Gate | Before | After |
|---|---|---|
| `scripts/ci_local.py` | 10 / 0 / 1 | **10 / 0 / 1** |
| Root pytest | 1887 passed, 11 skipped | **1888 passed, 12 skipped** (+1 pass, +1 skip: the new guard file) |
| Control plane, Postgres | 739 passed, 1 skipped | **739 passed, 1 skipped** |
| `git status` across the gate run | clean | unchanged (gates wrote nothing) |
| Rust sidecar | — | 5 passed (`cargo test --locked`, 43 s) |

One interruption, recorded so the record stays honest: the first
control-plane re-run returned **4 errors**. They were `Connection refused` from
the throwaway Postgres, whose process had been stopped externally (its log
ends without a shutdown entry). Restarted, re-run: 739 passed, 1 skipped. No
control-plane file is changed by this branch.

## 5. Change set and its risk class

16 files, +940 / −7. The 7 removed lines are stale text replaced in place.
Path risk from `scripts/automation_governance.classify_change`:

| Risk | Files |
|---|---|
| **HIGH** | `.github/workflows/ci.yml` (6 added lines) |
| LOW | `tests/test_node_toolchain_guard.py`, `CLAUDE.md`, `DEPLOY.md`, `README.md`, `docs/ARCHITECTURE.md`, `docs/CHANGELOG.md`, `docs/RUNBOOK.md`, 8 files in `docs/audit/2026-10-01/` |

No file deleted, renamed or moved. No secret, credential, permission, branch
setting, deployment or external system changed.

## 6. Final success criteria (from the brief)

| Criterion | State |
|---|---|
| Installation succeeds | **VERIFIED** for Python, 6 npm projects, Rust |
| Build succeeds | **VERIFIED** for storefront, admin, root, Rust. Docker: **BLOCKED** |
| Tests pass | **VERIFIED** locally; **BLOCKED** in CI (F1) |
| Main workflows execute | **No.** F1. Only GitHub-managed Pages and Dependabot run |
| Required integrations reachable | **No.** Commerce stack not deployed (carried) |
| Configuration documented | **Yes**, with the compose correction |
| Secrets safely referenced | **Yes** in code; S-N5 open for the live Stripe key |
| Security scans complete | **Yes** for secrets and dependencies; no DAST |
| Dependencies reviewed | **Yes**; drift recorded (09-24 R4) |
| Artifacts generated correctly | **Yes**: generated-asset gates pass |
| Health checks work | **Partly**: `/ready` passes on a schemaless DB (S-N3) |
| Failures visible | **No** in CI (F1); yes locally |
| Rollback documented | **Yes**: `docs/RUNBOOK.md` §5, per change here |
| Changes reviewable | **Yes**: draft PR; one HIGH path flagged |
| No destructive action without approval | **Yes** |

**The repository is not production-ready, and this audit does not say otherwise.**
