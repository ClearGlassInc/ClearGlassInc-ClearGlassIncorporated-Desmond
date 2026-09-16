# ClearGlass Auto-Heal

This directory contains the repository-local self-healing control plane for GitHub Actions.

## Purpose

The system detects recent failed, cancelled, and timed-out Actions runs; retrieves failed-job diagnostics; classifies failures; applies only deterministic low-risk remediations; re-runs transient failures; and escalates unsafe or ambiguous repairs through issues or pull requests.

## Failure handling

1. `.github/workflows/auto-heal.yml` runs after completed workflows, every 30 minutes, or by manual dispatch.
2. `auto_heal.py` inspects up to 50 recent completed workflow runs and processes a bounded number per cycle.
3. Job logs are matched against `error-patterns.json` and mapped to a category.
4. `healing-strategies.json` determines retry limits, review requirements, and automatic actions.
5. Infrastructure/transient failures can be re-run automatically within the configured retry budget.
6. Workflow/configuration failures can invoke the existing `scripts/workflow_doctor.py --fix` when present. Any resulting edits are committed to an `auto-heal/*` branch and proposed through a pull request.
7. Unsafe, security-sensitive, dependency-major, deployment, or unknown failures are escalated with diagnostic evidence instead of silently patched.
8. `run-history.json` records handled runs and outcomes. `flaky-tests.json` records recurring failure candidates.

## Review and merge

Auto-heal pull requests must be reviewed like any other production change. Confirm the failed-run link, classification, exact changed files, test evidence, and whether the repair is minimal. Merge only when required checks pass and the change respects repository policy.

## Safety boundaries

The system never force-pushes protected branches, edits repository secrets or tokens, auto-merges pull requests, weakens security scanning to make CI green, disables tests, deletes existing workflows, or changes security-critical infrastructure automatically. Security, deployment, permissions, identity, secret-management, and ambiguous dependency changes require human review.

The framework is intentionally additive. Existing CI, repository architecture, branch protection, required reviewers, and status checks remain authoritative.
