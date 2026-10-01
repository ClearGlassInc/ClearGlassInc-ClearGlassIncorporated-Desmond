# Test Baseline — 2026-10-01

**Commit:** `b53bfd7` (`main`), full clone. **Toolchain:** Python 3.11.15, Node
22.22.0, npm 10.9.4, ruff 0.15.8 (CI pin), Postgres 16.14 (throwaway local
cluster), cargo 1.97.0. Every row is **VERIFIED** unless marked otherwise.

## Results on `main`, before any change from this audit

| Command | Scope | Result | Time |
|---|---|---|---|
| `python3 scripts/ci_local.py` | Every `ci.yml` gate | **10 passed, 0 failed, 1 skipped** (Lighthouse: network). `git status` clean afterwards | 51 s |
| `python3 -m pytest tests/ -q -rs` | Root suite, 143 modules | **1887 passed, 11 skipped** | 47.3 s |
| same, with no `node` on `PATH` | Root suite | **1863 passed, 35 skipped, exit 0** — see "Skips that pass" | 42.3 s |
| `python3 -m ruff check .` | Repo lint, ruff 0.15.8 | clean | 0.1 s |
| `ruff check .` | Repo lint, ruff 0.15.20 (on `PATH` here) | clean | — |
| `cd control-plane && ruff check .` | Control plane | clean | — |
| `cd control-plane && pytest tests/ -q` | Control plane, SQLite | **735 passed, 5 skipped** | 18.7 s |
| same with `CONTROL_PLANE_TEST_POSTGRES_URL` | Control plane, Postgres 16.14 | **739 passed, 1 skipped** (single-currency price book) | 19.5 s |
| `python -m app.daily_loop --json` | Governance self-check | `governance_failures: []`, exit 0 | — |
| `storefront`: `npm ci`, `tsc --noEmit`, `npm run build`, `npm audit` | Next.js app | exit 0 / 0 / 0, **0 vulnerabilities** | — |
| `admin`: same four | Next.js app | exit 0 / 0 / 0, **0 vulnerabilities** | — |
| root: `npm ci`, `npm run typecheck`, `npm audit` | Live-signal fabric | exit 0 / 0, **0 vulnerabilities** | — |
| `npm audit --package-lock-only` | `apps/artemis-engineering`, `clearglass-ai-proxy`, `clearglass-air-control` | **0 vulnerabilities** each | — |
| `pip-audit -r` | All 7 `requirements*.txt` | **No known vulnerabilities** in any | — |
| `node --experimental-strip-types --test admin/tests/login-guard.test.mjs` | Admin login guard | **7/7 pass** | — |
| `python3 scripts/secret_scan.py` | Tracked files | "No hardcoded secrets detected." | — |
| `python3 -m bots.rfed_audit_bot --self-check` | RFED invariants | "SELF-CHECK PASSED" | — |
| `python3 -m truth_forensics demo --check` | Truth Forensics demo corpus | "demo files current" | — |
| `python3 tools/growth_registry.py --check` | Growth registries | exit 0; 0 experiments, nothing claimed | — |
| `python3 scripts/workflow_doctor.py` | 87 workflow files | 0 errors | 0.9 s |
| `python3 scripts/audit_github_actions.py` | Workflow safety invariants | every file "valid and ready" | 0.5 s |
| `cargo test --locked` in `agent_army/secure_runtime` | Rust sidecar | **5 passed**, exit 0; 1 future-incompat warning (`proc-macro-error2 v2.0.1`) | 43 s |

## Movement since the last baseline

| Measure | 2026-09-23 | 2026-09-24 | 2026-10-01 |
|---|---|---|---|
| `ci_local.py` | 10 / 0 / 1 (after repair) | 10 / 0 / 1 | 10 / 0 / 1 |
| Root tests passing | 1568 | not recorded | **1887** |
| Control-plane tests (Postgres) | 402 | 426 | **739** |
| `npm audit` storefront / admin | 0 / 0 | 0 / 0 | 0 / 0 |

**What the green means.** Fifty PRs merged since 2026-09-24 with no CI signal
(F1), yet every gate holds. The local `ci_local.py` discipline is working.

## Skips that pass

The root suite skips 11 tests on a full toolchain. None is a gate passing by
accident: 1 needs Pillow, 4 are `@types/react` checks for apps that declare no
types, 6 are article checks that do not apply to tool pages.

The suite also has a quieter problem. **24 tests shell out to `node` and skip when it is missing**,
and the run still exits 0:

| Module | Skips without Node | What goes unchecked |
|---|---|---|
| `test_rfed_hash_parity.py` | 4 | Python↔n8n RFED hash parity — named in `CLAUDE.md` as an enforced gate |
| `test_truth_forensics_parity.py` | 6 | Python↔browser Truth Forensics parity |
| `test_sentinel_core.py` | 6 | Sentinel Core console helpers, matcher, voice |
| `test_homepage_subscribe_handler.py` | 5 | Homepage subscribe handler |
| `test_inline_script_syntax.py` | 1 | Every inline `<script>` on every page |
| `test_side_store_storefront.py` | 1 | Side Store pricing in the browser |
| `test_admin_login_guard.py` | 1 | Admin open-redirect, token comparison, lockout. **Also skips on Node < 22.6** |

CI's `python-tests` job installed Python only and inherited the runner image's
Node, which `test_admin_login_guard.py` records as 20 on `ubuntu-latest`
(**INFERRED**; this audit cannot read the image). On Node 20 the admin login
guard's behavioural suite skips. This audit pins Node 22 in that job and adds
`tests/test_node_toolchain_guard.py`. See `VALIDATION_REPORT.md` §2.

## Not run

| Check | Why | Status |
|---|---|---|
| Lighthouse budgets | Needs network to the live site | **BLOCKED** by scope (no live probing before inventory sign-off) |
| Docker image builds, `docker compose up` | No Docker daemon in this environment | **BLOCKED**. `docker compose config` was run; see `VALIDATION_REPORT.md` §3 |
| Any test in CI | F1: GitHub Actions dispatches no runners | **BLOCKED** (owner, organisation settings) |
| Live-site, Render, Stripe, PayPal state | Out of read-only scope for this pass | Not re-verified; carried from 2026-09-24 |
