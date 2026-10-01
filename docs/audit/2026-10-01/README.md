# Repository Audit — 2026-10-01

**Base:** `main` at `b53bfd7` (PR #162), branch `percival/brave-goodall-miy7er`
**Measured against:** `docs/AUDIT-2026-09-24.md` (base `4725787`), `docs/AUDIT-2026-09-23.md`, `docs/BASELINE.md`
**Window covered:** 217 commits, 50 merged PRs (#112 to #162), 494 files changed, +41,596 / −1,821 lines

This folder is the audit's report set. Where the repository already had an
equivalent document, the audit updated that document instead of writing a
second one. Nothing here supersedes `docs/BASELINE.md`; it re-measures it.

## Status vocabulary

| Label | Meaning |
|---|---|
| **VERIFIED** | Observed with the command, API call or test named next to it |
| **INFERRED** | Follows from verified facts, not observed directly |
| **MISSING** | Required and not found |
| **BLOCKED** | Could not be checked or changed: permissions, tooling, or ambiguity |
| **RISK** | A concern that may cause a reliability, security, cost or maintenance problem |
| **IMPROVEMENT** | A safe recommended change |
| **REQUIRES APPROVAL** | Cannot proceed without the owner |

Severity: **P0** critical security / data-loss / production risk, **P1** major,
**P2** significant, **P3** minor, **P4** optional.

## The twelve deliverables

| # | Requested | Where it lives | New or existing |
|---|---|---|---|
| 1 | EXECUTIVE_AUDIT | [`EXECUTIVE_AUDIT.md`](EXECUTIVE_AUDIT.md) | New |
| 2 | REPOSITORY_INVENTORY | [`REPOSITORY_INVENTORY.md`](REPOSITORY_INVENTORY.md) | New |
| 3 | SYSTEM_ARCHITECTURE | `docs/ARCHITECTURE.md` | Existing, still accurate; workflow counts in §8 updated |
| 4 | WORKFLOW_MAP | [`WORKFLOW_MAP.md`](WORKFLOW_MAP.md) | New |
| 5 | INTEGRATION_MAP | [`INTEGRATION_MAP.md`](INTEGRATION_MAP.md) | New |
| 6 | TEST_BASELINE | [`TEST_BASELINE.md`](TEST_BASELINE.md) | New (re-measures `docs/BASELINE.md` §2) |
| 7 | SECURITY_REVIEW | [`SECURITY_REVIEW.md`](SECURITY_REVIEW.md) | New (threat model stays in `security/HARDENING_AND_THREAT_MODEL.md`) |
| 8 | RISK_REGISTER | [`RISK_REGISTER.md`](RISK_REGISTER.md) | New, consolidated: carries forward every open item from BASELINE §6 and both September audits |
| 9 | IMPROVEMENT_BACKLOG | [`IMPROVEMENT_BACKLOG.md`](IMPROVEMENT_BACKLOG.md) | New |
| 10 | CHANGELOG | `docs/CHANGELOG.md` | Existing; 2026-10-01 entry added |
| 11 | OPERATIONS_RUNBOOK | `docs/RUNBOOK.md` | Existing; §3 local stack corrected |
| 12 | VALIDATION_REPORT | [`VALIDATION_REPORT.md`](VALIDATION_REPORT.md) | New; includes the validation plan |

## How to reproduce

Every number in this folder came from one of these, run on `b53bfd7` with a
full (unshallowed) clone, Python 3.11.15, Node 22.22.0, npm 10.9.4:

```bash
pip install pytest pytest-cov pyyaml "ruff==0.15.8" -r control-plane/requirements.txt
python3 scripts/ci_local.py
python3 -m pytest tests/ -q -rs
(cd control-plane && python3 -m ruff check . && python3 -m pytest tests/ -q)
(cd control-plane && CONTROL_PLANE_TEST_POSTGRES_URL=<throwaway db> python3 -m pytest tests/ -q)
(cd control-plane && python -m app.daily_loop --json)
for d in storefront admin; do (cd $d && npm ci && npx tsc --noEmit && npm run build && npm audit); done
npm ci && npm run typecheck && npm audit
python3 scripts/secret_scan.py
python3 -m bots.rfed_audit_bot --self-check
python3 -m truth_forensics demo --check
pip-audit -r <each requirements file>
```

GitHub state (workflow runs, jobs, branches, visibility) was read through the
GitHub API, read-only.
