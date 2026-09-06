# ClearGlass Website CI Runbook

## Source of truth

- Repository: `ClearGlassInc/ClearGlassInc.github.io`
- CI workflow: `.github/workflows/ci.yml` (name: **CI**) — runs on every push and
  pull request to `main`.
- Deploy: `.github/workflows/pages.yml` publishes the static site to GitHub Pages
  on push to `main`. Full architecture + incident runbook:
  [`DEPLOYMENT.md`](DEPLOYMENT.md).

## CI jobs (gate every change into `main`)

| Job | What it gates |
|---|---|
| `Python Tests` | `pytest tests/` — bot / automation correctness |
| `Lint (ruff)` | `ruff check .` — repo-wide Python lint |
| `Site Reliability Audit` | `scripts/site_reliability_audit.py` — site invariants |
| `Workflow Doctor (dry-run)` | `scripts/workflow_doctor.py` — workflow YAML health |
| `OSINT Deck Validator` | `scripts/osint_deck_release.py --strict` |

Sibling workflows add further gates: Secret Pattern Scan, Policy Gate,
Dependency Review, IP Risk Assessment, and CodeQL Analyze (python + js/ts).

## Required status checks & branch protection

`main` is the production branch (it auto-deploys via Pages). To honour
"never merge code that fails tests or weakens security", configure branch
protection on `main`:

- **Require status checks to pass before merging**, and mark at least
  `Lint (ruff)`, `Python Tests`, and `Site Reliability Audit` as **required**.
- **Require branches to be up to date before merging**, so checks run against
  the post-merge tree rather than a stale base.
- **Do not allow bypassing the above** (restrict any admin override to
  break-glass use only).

> Why this section exists: a PR was once merged while `Lint (ruff)` was red,
> briefly leaving `main` failing CI until a follow-up PR remediated it.
> Required + blocking checks prevent a red `main`.

## Re-running / triggering

- Manual: **Actions → CI → Run workflow → Branch: `main`**.
- Always run against current `main`; do not re-run historical failed attempts
  from older commits.

## Rollback

The site is static, so rollback is a content revert:

1. `git revert <bad-sha>` on `main` (or revert the merge commit).
2. Let `pages.yml` redeploy the reverted tree, or re-run the last known-good
   Pages deployment from the Actions tab.

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for the full incident runbook.
