# ClearGlassInc Artemis — MLOps Deploy Agent (ADA-7) Engineering Design

**Date:** 2026-05-09
**Branch:** `claude/prompt-compiler-orchestrator-nbnwE`
**Package:** `bots.mlops_deploy_agent`

## 1. Intent

Convert a high-level deploy intent into a deterministic, audited, rollback-safe
production deployment for ML models and prompt-controlled workflows. Targets
MLOps teams, AI startups, and enterprise engineering orgs that need
time-to-prod measured in minutes with a signed audit trail per release.

## 2. DSL Surface

The orchestrator accepts the following constructs (compiled into a
`DeployPlan`):

```
intent("deploy ranker v2.4.0 to prod-east with canary + SLO gates")
buyer("MLOps team")
artifact("agent")
dependency("model registry, CI/CD, container runtime, secrets manager, deployment target")
constraint("must be deterministic, strict, and monetizable immediately")
monetize("productized service + template + implementation sprint")
```

Concrete plans are JSON conforming to `bots/mlops_deploy_agent/schema.py`. See
`bots/mlops_deploy_agent/examples/example_plan.json`.

## 3. Architecture

```
        Supervisor
   ┌──────────────────┐
   │ intake → resolve │
   │ → policy → prov. │
   │ → deploy →verify │
   │ → promote → audit│──► AuditManifest (chain-hashed, signed)
   │ → monetize       │──► CI billing event
   └──────────────────┘
        │   │   │   │
   Registry Runtime Secrets CI
   (MLflow / SageMaker, KServe / SageMaker / ECS, Vault / ASM, GH Actions)
```

Adapters are protocols (`bots/mlops_deploy_agent/adapters.py`). In-memory
implementations ship for tests and dry-run. Real adapters are added per
engagement during the 7-day implementation sprint.

## 4. Stage Contract

| Stage      | Validator rule                                                  |
|------------|-----------------------------------------------------------------|
| intake     | `result.plan_id == plan.plan_id`                                |
| resolve    | registry digest matches plan; image digest pinned               |
| policy     | zero violations from `PolicyEngine`                             |
| provision  | drift = 0                                                       |
| deploy     | every canary step in `plan.target.canary_steps` executed        |
| verify     | p95, error rate, cost all within `Policy` thresholds            |
| promote    | alias = `prod`, weight = 100                                    |
| audit      | non-empty `chain_hash`, `signed = True`                         |
| monetize   | non-empty `event_id` from CI adapter                            |

A failed validator triggers exactly one deterministic repair attempt. Failure
of the repair triggers `runtime.rollback(plan)` and raises `StageFailure`.

## 5. Determinism Guarantees

- All artifact references are SHA256 digests. Tags are rejected at schema
  construction time.
- Plans are frozen dataclasses; mutation requires a new plan_id.
- The audit manifest hashes the previous chain hash plus the current plan
  identity, producing an append-only release ledger.
- The same plan + same registry state produces the same `chain_hash` (test:
  `test_chain_hash_is_deterministic_for_same_inputs`).

## 6. Operating Surface

- **Library:** `from bots.mlops_deploy_agent import Supervisor, DeployPlan, ...`
- **CLI:** `python -m bots.mlops_deploy_agent.cli --plan path/to/plan.json --dry-run`
- **Tests:** `pytest tests/test_mlops_deploy_agent.py`

## 7. Monetization

| Layer    | Offer                              | Price             |
|----------|------------------------------------|-------------------|
| Audit    | Deployment + PromptOps Risk Audit  | $4,500 fixed      |
| Sprint   | ADA-7 Implementation Sprint        | $35k–$85k         |
| Template | Deploy-Agent Template License      | $2.5k/repo, $9.9k/org |
| Retainer | Managed Deploy Pipeline            | $8k–$25k/mo       |
| Add-on   | Performance tier (cost savings)    | +10–15%           |

The `monetize` stage emits a billing event per successful release, enabling
usage-based pricing on the recurring tier.

## 8. Risk Controls

- Pinned digests, signed artifacts, OPA-style gates pre-deploy.
- Canary walk + SLO verification before promotion.
- Auto-rollback on any verifier failure when `rollback_on_fail` is true.
- Append-only signed audit manifest per deploy.
- Adapter abstraction prevents vendor lock-in.

## 9. Status

- Schema, supervisor, policy engine, validators, adapters, CLI, and tests
  shipped on this branch.
- 14/14 tests pass under `pytest`.
- Real adapter implementations (MLflow, SageMaker, KServe, Vault, GitHub
  Actions) are deferred to per-client implementation sprints.
