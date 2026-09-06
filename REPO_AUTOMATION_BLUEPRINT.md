# ClearGlassInc Artemis — Repository Automation + Self-Evolving Intelligence Platform Blueprint

## Executive Summary
This document provides an implementation-ready automation architecture for GitHub repository operations and a full-stack, self-improving AI platform architecture aligned to Palantir Gotham, Foundry, AIP, and Apollo. It is designed for secure, auditable, low-risk autonomy with human approval gates for mission-significant changes.

## Assumptions to Replace Placeholders
- Repository type: Monorepo (services + web UI + data/ML components)
- Primary languages: Python, TypeScript, SQL
- Deployment target: Kubernetes + Palantir-managed runtime via Apollo
- Risk tolerance: Medium
- Human approval required: production deploys, schema/ontology changes, policy changes, autonomous workflow upgrades
- Autonomous actions allowed: labeling, triage comments, docs PR drafts, dependency PRs, CI retries, reporting

## A) Repository Automation Architecture

### Architecture split
1. Deterministic GitHub Actions (build/test/release gates).
2. Reusable workflows + composite actions (DRY standardization).
3. Agentic workflows (bounded low-risk automation in Markdown-defined runbooks).
4. Policy-as-code (OPA/Conftest + CODEOWNERS + branch protections).

### Workflow domains
- CI: lint, unit/integration tests, security scan, build reproducibility.
- Triage: issue/PR labeling, duplicate/stale detection, routing.
- Docs sync: detect API/interface diffs, open docs update PR.
- Dependencies: Renovate/Dependabot + license/CVE policies.
- Release prep: changelog draft, semantic version proposal, release checklist.
- Reporting: daily/weekly health report with SLO/SLA and flake metrics.
- Maintenance: workflow drift detection, action pinning updates.
- Quality checks: static analysis, mutation/coverage deltas.

### Guardrails by class
- All workflows use `permissions: {}` default and explicit per job scopes.
- Actions pinned to commit SHA.
- `pull_request_target` prohibited except vetted metadata-only jobs.
- Mandatory concurrency groups; cancel stale runs.
- Environment protection for staging/prod with required reviewers.

## B) Bot Capabilities
- Label/route issues using ML + rule fallback (component, severity, owner).
- Summarize new issues/PRs (impact, risk, missing artifacts).
- Detect stale/duplicate via embedding + title/body similarity.
- Open docs PR when code/API signatures change.
- Suggest tests based on changed code paths and coverage map.
- Monitor failed workflows and classify: infra flake vs deterministic fail.
- Draft release notes/changelog grouped by type + breaking changes.
- Sync repo settings/policies via org-level policy repo.
- Publish daily/weekly health report in Discussion + artifact.

## C) Workflow Map

| Workflow | Trigger | Purpose | Autonomy Level | Permissions | Human Review Required | Failure Handling |
|---|---|---|---|---|---|---|
| ci.yml | pull_request, push(main) | Lint/test/build/security | Deterministic | contents:read, checks:write | No (except failing gate) | annotate + block merge |
| triage.yml | issues, pull_request_target(metadata only) | Label, route, summarize | Low-risk autonomous | issues:write, pull-requests:write | No | fallback to `needs-human` label |
| docs-sync.yml | pull_request, workflow_dispatch | Detect API drift and open docs PR | Draft autonomous | contents:write (bot branch only) | Yes (PR review) | close PR + alert |
| deps.yml | schedule, workflow_dispatch | Dependency updates | Draft autonomous | contents:write, pull-requests:write | Yes | auto-close on policy violation |
| release-prep.yml | push(main), workflow_dispatch | Release notes/changelog draft | Advisory | contents:write | Yes | keep as draft release |
| ci-reliability.yml | workflow_run(failure) | Classify and retry flakes | Guarded autonomous | actions:write, contents:read | No for retries; yes for suppressions | cap retries + incident ticket |
| reporting.yml | schedule(daily/weekly) | Repo health metrics/report | Autonomous read-mostly | actions:read, checks:read, issues:write | No | post degraded-data notice |
| policy-sync.yml | workflow_dispatch, schedule | Sync labels/rules/templates | Controlled autonomous | administration:write (app-scoped) | Yes for org-wide | rollback from baseline snapshot |

## D) File Structure

```text
.github/
  workflows/
    ci.yml
    triage.yml
    docs-sync.yml
    deps.yml
    release-prep.yml
    ci-reliability.yml
    reporting.yml
    policy-sync.yml
    reusable/
      _ci-core.yml
      _python-quality.yml
      _ts-quality.yml
      _release-notes.yml
  actions/
    setup-toolchain/
      action.yml
    changed-paths/
      action.yml
    policy-check/
      action.yml
  agentic/
    triage-agent.md
    docs-alignment-agent.md
    flaky-ci-agent.md
    release-notes-agent.md
  config/
    labels.yml
    routing.yml
    stale.yml
    duplicate-detection.yml
    policy.yml
  scripts/
    report_health.py
    classify_failure.py
    suggest_tests.py
    docs_drift_detector.py
  CODEOWNERS
  dependabot.yml
  renovate.json
  pull_request_template.md
  ISSUE_TEMPLATE/

docs/
  automation/
    architecture.md
    runbooks.md
    rollback-playbook.md
    security-model.md
```

## E) Security and Governance
- Least privilege per workflow/job; no inherited broad `GITHUB_TOKEN`.
- OIDC for cloud access; no long-lived cloud keys.
- Secrets only in environment scopes; deny secrets on fork PR workflows.
- Threats: poisoned PRs, action supply chain, prompt injection, malicious docs changes.
- Mitigations: SHA pinning, artifact attestations, sandboxed agent tools, allowlisted commands, content classifiers.
- Branch protection: required checks, linear history, signed commits optional, CODEOWNERS required.
- Approval gates: environment reviewers, manual dispatch for policy/ontology/runtime upgrades.
- Immutable audit: append-only event log, signed release metadata.

## F) Phased Rollout
1. Phase 1 (triage/reporting)
   - Deliver: triage bot, stale/duplicate checks, daily report.
   - Metrics: triage latency <10 min, 80% label precision.
   - Rollback: disable triage write perms; keep read-only report.
2. Phase 2 (docs/quality/deps)
   - Deliver: docs drift PRs, quality gates, dependency PR automation.
   - Metrics: 30% PR cycle-time reduction; vulnerability MTTR down 40%.
   - Rollback: switch bots to draft-only.
3. Phase 3 (release/failure remediation)
   - Deliver: release prep drafts, flaky test classifier + bounded retries.
   - Metrics: CI success stability +20%; release prep time -50%.
   - Rollback: disable auto-retry; keep classification only.
4. Phase 4 (selective autonomous improvements)
   - Deliver: agent proposes prompt/workflow/routing updates with eval evidence.
   - Metrics: precision/recall gains with no increase in policy violations.
   - Rollback: hard-stop autonomous change application; human-only mode.

## G) Example Configurations

### 1) GitHub Actions workflow YAML (`.github/workflows/triage.yml`)
```yaml
name: triage
on:
  issues:
    types: [opened, edited, reopened]
permissions:
  contents: read
  issues: write
jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
      - name: Run triage
        run: python .github/scripts/triage.py --issue "$ISSUE_JSON"
        env:
          ISSUE_JSON: ${{ toJson(github.event.issue) }}
```

### 2) Reusable workflow (`.github/workflows/reusable/_ci-core.yml`)
```yaml
name: _ci-core
on:
  workflow_call:
    inputs:
      python-version:
        required: true
        type: string
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      checks: write
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
      - uses: actions/setup-python@42375524e23c412d93fb67b49958b491fce71c38
        with:
          python-version: ${{ inputs.python-version }}
      - run: pip install -r requirements.txt
      - run: pytest -q
```

### 3) Composite action (`.github/actions/policy-check/action.yml`)
```yaml
name: policy-check
runs:
  using: composite
  steps:
    - shell: bash
      run: |
        pip install conftest
        conftest test .github/config/policy.yml -p policy/
```

### 4) Agentic workflow markdown (`.github/agentic/docs-alignment-agent.md`)
```md
# Docs Alignment Agent
Goal: Detect code/API changes lacking docs updates and open a draft PR.

## Inputs
- Changed files list
- API signature diff
- Existing docs index

## Rules
1. Never modify runtime code.
2. Only edit docs paths allowlisted in `.github/config/policy.yml`.
3. Open draft PR with "needs-human-review" label.
4. Include diff rationale + confidence score.
```

### 5) Labels/config (`.github/config/labels.yml`)
```yaml
labels:
  - name: kind/bug
    color: d73a4a
    description: Something is not working
  - name: kind/feature
    color: a2eeef
    description: New capability request
  - name: area/ai-agent
    color: 5319e7
    description: Agentic workflow or model routing
  - name: needs-human-review
    color: fbca04
    description: Automation produced output requiring approval
```

## H) Operating Rules
- Never auto-merge PRs.
- Never change production behavior without human review.
- Never request broad secrets when fine-grained/OIDC can satisfy.
- Never execute ambiguous autonomous actions; escalate to human.
- Always record what changed and why in PR body + audit log.
- Always prefer low-risk outputs first (labels, drafts, suggestions).

## ClearGlassInc Artemis Full-Stack (Palantir) Implementation Blueprint

### System Architecture
- Gotham: mission ops UI for investigations/entity timelines.
- Foundry: ingestion, ontology, transforms, lakehouse, pipeline scheduling.
- AIP: copilots/agents, tool use, evals, guardrailed autonomy.
- Apollo: deployment, canary, rollback, policy-constrained updates.

### Self-Improvement Loop
- Collect signals: corrections, overrides, accepted/rejected recommendations, mission outcomes.
- Build eval datasets nightly (stratified by mission/context).
- Run prompt/workflow/model-router candidates in shadow/A-B.
- Promote only if metrics + policy checks pass and human approves.
- Version everything: prompts, tools, policies, workflows, models.

### Python Precision Snippet (workflow state machine)
```python
from dataclasses import dataclass
from enum import Enum

class State(str, Enum):
    INGESTED="ingested"; TRIAGED="triaged"; RECOMMENDED="recommended"; APPROVED="approved"; EXECUTED="executed"; REVIEWED="reviewed"

@dataclass
class Case:
    id: str
    state: State
    confidence: float
    requires_human: bool = True


def transition(case: Case, event: str) -> Case:
    table = {
        (State.INGESTED, "triage_complete"): State.TRIAGED,
        (State.TRIAGED, "recommendation_ready"): State.RECOMMENDED,
        (State.RECOMMENDED, "human_approved"): State.APPROVED,
        (State.APPROVED, "action_executed"): State.EXECUTED,
        (State.EXECUTED, "outcome_logged"): State.REVIEWED,
    }
    nxt = table.get((case.state, event))
    if not nxt:
        raise ValueError(f"invalid transition: {case.state} -> {event}")
    return Case(id=case.id, state=nxt, confidence=case.confidence, requires_human=case.requires_human)
```
