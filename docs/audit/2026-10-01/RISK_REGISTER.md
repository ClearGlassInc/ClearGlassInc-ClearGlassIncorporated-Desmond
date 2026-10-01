# Risk Register — 2026-10-01

One register for every open risk, carried forward from `docs/BASELINE.md` §6,
`docs/AUDIT-2026-09-23.md` and `docs/AUDIT-2026-09-24.md`, plus this audit's
new items (`N`). IDs from earlier documents are kept so history stays traceable.

## How items are ranked

Each factor is scored 1 to 5, with **effort** 1 (minutes) to 5 (weeks):

> **Priority = impact × likelihood × exposure ÷ effort**

The score orders the list; it is not a measurement. Severity (P0 to P4) is a
judgement about consequence, so a high-scoring cheap fix can still be P2. The
reasoning column says why.

## Open

Ordered by severity, then score.

| ID | Risk | Sev | I | L | E | Eff | Score | Reasoning | Status | Owner action |
|---|---|:-:|:-:|:-:|:-:|:-:|--:|---|---|---|
| R1 / F1 | GitHub Actions dispatches no runners; no CI signal on any change | **P0** | 5 | 5 | 5 | 1 | 125 | Certain and ongoing since 2026-09-06: 50 more PRs merged unverified this week. Owner fix takes minutes | VERIFIED today (job `110455407504`, `runner_id: 0`) | **Yes**: org billing, spending limit, allowed-actions policy, or Actions toggle |
| N2 / S-N2 | Third-party emails and personal documents published on a public repo and the company domain | **P1** | 4 | 5 | 5 | 1 | 100 | Already exposed; third parties did not consent; removing from the tree is quick, but history keeps them | VERIFIED | **Yes**: decide per file; deletion needs approval |
| R7 / S6 | `main` unprotected; CODEOWNERS unenforced | **P1** | 4 | 4 | 4 | 1 | 64 | With F1, review is the only gate left, and nothing requires it | VERIFIED today | **Yes**: require 1 review; add `ci_local.py` as a required pre-push habit until F1 clears |
| N1 / S-N1 | Node-dependent security tests pass by skipping; CI had no `setup-node` | **P1** | 4 | 3 | 3 | 1 | 36 | Would read as green the moment CI returns | **Fixed on this branch** | Review `ci.yml` change |
| R4 + N4 | 38 scheduled / 18 write-scoped workflows resume together when F1 clears; Auto Heal reacts to every failure | **P1** | 4 | 5 | 3 | 2 | 30 | Certain to happen on re-enable; PR flood plausible; reversible | VERIFIED counts and fan-out | **Yes**: staged re-enable; narrow Auto Heal first |
| 09-24 R3 | Commerce stack not deployed; live lead form records nothing | **P1** | 5 | 5 | 3 | 3 | 25 | Every real lead lost; needs Render + secrets | Carried (VERIFIED 09-24, not re-read) | **Yes**: deploy blueprint, set `cg-revenue-api` |
| R3 | Several public entry prices for the first offer | P2 | 3 | 4 | 4 | 1 | 48 | Owner decision, not code. 2026-10-01 revenue run (`5e54c62`) still counts four | INFERRED from `5e54c62` | **Yes**: choose one |
| N8 | Local compose stack could not record a lead; docs copied the wrong env file | P2 | 3 | 5 | 2 | 1 | 30 | Every developer following the docs hit it | **Fixed on this branch** (docs) | Review |
| N3 / S-N3 | `/ready` returns 200 on a database with no schema | P2 | 3 | 3 | 3 | 1 | 27 | Health check hides a 500 on every write | VERIFIED on PG 16 | Approve endpoint change |
| 09-24 R4 | Control-plane deps unpinned; image installs whatever is newest | P2 | 4 | 3 | 3 | 2 | 18 | Drift already observed: Stripe SDK 15 → 16 in one week. Tests pass today | VERIFIED drift | No: constraints file (backlog B5) |
| N5 / S-N5 | Live Stripe key is repository-scoped | P2 | 5 | 2 | 3 | 2 | 15 | Low likelihood, high impact; R7 raises likelihood | INFERRED from workflow | **Yes**: restricted key + environment secret |
| R11 | No Stripe read source, so cash reporting is incomplete | P2 | 3 | 5 | 1 | 2 | 7.5 | Reporting gap, not a defect | Carried | Yes: connect or export |
| R6 | No staging environment | P2 | 4 | 3 | 2 | 4 | 6 | Expensive; matters once the commerce stack is deployed | Carried | Yes: provision |
| S5 | `/revenue/health` public, exposes `last_stripe_event_at` | P3 | 2 | 3 | 4 | 1 | 24 | Small leak of activity timing | VERIFIED open | No |
| N9 | 100+ unprotected branches, many merged | P3 | 2 | 3 | 2 | 1 | 12 | Clutter; any can be pushed to | VERIFIED | Approve cleanup |
| N6 / S-N6 | 5 write-scoped workflows without concurrency | P3 | 2 | 2 | 2 | 1 | 8 | Races only when runners exist | VERIFIED | Approve (HIGH path) |
| N7 / S-N7 | `CG_ORG_PAT` scope unknown | P3 | 3 | 2 | 2 | 2 | 6 | Person-bound long-lived token | UNKNOWN scope | Yes: replace with App token |
| B5 | Two legacy Render services from another repo fail to build | P3 | 1 | 5 | 1 | 1 | 5 | Noise; one has a typo start command | Carried (`5e54c62` re-notes it) | Yes: fix or delete |
| R5 | Netlify, Fly and Cloudflare config coexist with Pages | P3 | 2 | 2 | 2 | 2 | 4 | Pages is verified as the server; the rest are inert but misleading | Narrowed | Decide which to keep |
| N10 | 144 dated reports, 235 other Markdown files and 45 uploads at the site root | P4 | 1 | 5 | 2 | 2 | 5 | Maintainability; overlaps N2 for the sensitive subset | VERIFIED | Decide archive policy |
| N12 | Copilot code review "dynamic" runs fail | P4 | 1 | 5 | 1 | 1 | 5 | INFERRED same entitlement cause as F1 | VERIFIED failing | Resolves with F1 |
| N11 | `proc-macro-error2 v2.0.1` will be rejected by a future Rust | P4 | 1 | 2 | 1 | 1 | 2 | Build warning today | VERIFIED (`cargo test`) | No |

## Closed or changed since the last register

| ID | Was | Now | Evidence |
|---|---|---|---|
| S4 | Master admin key typed into a public page | **Closed** | `f8a225a` removed the cockpit field; 2026-09-24 report carried it in error |
| R10 | `CLAUDE.md` deploy notice stale | Closed (2026-09-15); notice re-verified today | `CLAUDE.md` |
| R12 | `search-integrity` gate leaves a dirty tree when stale | **Accepted** | Documented as deliberate in `scripts/_ci_local_search_assets.py` |
| R8 | Canonical catalog lacks fields to validate checkout | Not re-verified | `docs/CATALOG_SCHEMA.md` and `tests/test_catalog_contract.py` now exist |
| R9b | Storefront vulnerabilities | Closed | `npm audit` 0 |
| F4–F8, B1–B4, S1–S3 | Various | Closed earlier; spot-checked green | `TEST_BASELINE.md` |
