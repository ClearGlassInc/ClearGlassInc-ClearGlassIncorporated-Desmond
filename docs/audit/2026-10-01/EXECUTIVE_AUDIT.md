# Executive Audit — 2026-10-01

**Verdict: NOT PRODUCTION-READY. The code is healthy. What stops it is the
same as a week ago: organisation settings and owner decisions.**

`main` at `b53bfd7` absorbed 50 PRs (#112 to #162, 217 commits, +41,596
lines) since the last audit, all with no CI because GitHub Actions still
dispatches no runners. Despite that, every local gate is green. The
discipline of running `scripts/ci_local.py` before pushing is holding.

## What was verified

| Area | Result |
|---|---|
| Every `ci.yml` gate (`ci_local.py`) | 10 passed, 0 failed, 1 skipped (Lighthouse, network) |
| Root test suite | 1887 passed, 11 skipped |
| Commerce control plane | ruff clean; 739 passed on Postgres 16; governance self-check clean |
| Storefront, admin, root Node app | install, typecheck and build all pass |
| Dependencies | 0 known vulnerabilities across 6 npm lockfiles and 7 Python requirement files |
| Secrets in the tree | none found |
| Workflow supply chain | all 85 workflows SHA-pinned, permission-scoped, time-limited; no untrusted-input injection |
| GitHub Actions (F1) | **still broken**: job `110455407504` today, `runner_id: 0`, 4 s |
| Site deployment | **working**: GitHub's own Pages build deployed `b53bfd7` in 33 s |

## What this audit found

| # | Finding | Sev | Action |
|---|---|:-:|---|
| 1 | Actions dispatches no runners: no CI on any change since 2026-09-06 | P0 | **Owner**: organisation settings |
| 2 | **Third-party email addresses and personal documents are published** at the root of a public repository, which is also the website root | P1 | **Owner decision**: which files to remove; history keeps them regardless |
| 3 | `main` is unprotected; CODEOWNERS enforces nothing | P1 | **Owner**: branch protection |
| 4 | CI would have reported the admin login security tests as **passing while skipping them**: it never installed the Node version they need | P1 | **Fixed** on this branch; needs review (protected file) |
| 5 | 38 scheduled workflows (18 can commit) resume at once when runners return. Auto Heal already fires 14 times per merge | P1 | Narrow Auto Heal, then staged re-enable |
| 6 | The commerce API is not deployed, so the live lead form records nothing | P1 | Carried; **owner** deploy |
| 7 | The documented local stack **could not record a lead** (500 on every lead) | P2 | **Fixed** (docs), verified on Postgres |
| 8 | `/ready` reports healthy on a database with no tables | P2 | Proposed; needs approval |
| 9 | The live Stripe key is readable by a job outside its protected environment | P2 | **Owner**: re-scope the key |
| 10 | Python dependencies unpinned: Stripe SDK moved a major version in one week | P2 | Proposed constraints file |

One correction to the record: the 2026-09-24 audit listed "admin key typed
into a public page" as open. It had been fixed that morning (`f8a225a`). Closed.

## What changed on this branch

- `.github/workflows/ci.yml`: install Node 22 before the root tests (6 lines;
  protected path, needs review).
- `tests/test_node_toolchain_guard.py`: fails if that step is removed, or if CI
  runs without a capable Node. Red before the fix, green after.
- `DEPLOY.md`, `docs/RUNBOOK.md`, `README.md`, `CLAUDE.md`: working local-stack
  steps. `CLAUDE.md` and `docs/ARCHITECTURE.md`: current workflow counts and
  today's F1 evidence. `docs/CHANGELOG.md`: this entry.
- `docs/audit/2026-10-01/`: this report set.

Nothing was deleted, renamed, deployed, merged, or changed in any external
system, secret or setting.

## The four owner actions that matter most

1. **Restore Actions** (P0): billing, spending limit, allowed-actions policy, or the Actions toggle.
2. **Decide on the published files** (P1): start with `remote_strike_pipeline.csv`.
3. **Protect `main`** (P1): one required review.
4. **Before re-enabling schedules**, approve backlog I-5 (narrow Auto Heal) and plan I-6.

Details: `RISK_REGISTER.md`, `SECURITY_REVIEW.md`, `IMPROVEMENT_BACKLOG.md`.
