# Percival v9 — Deployment Blueprint (Target Architecture)

> **Status: reference design, NOT provisioned.** This repository is a GitHub
> Pages site plus stdlib-only Python governance modules. Nothing below (EKS,
> Temporal, OPA, Kafka, Terraform) is running today. This document is the
> *target* production shape for when the governed core graduates to a
> distributed service. The **enforcing logic already exists and is tested** in
> `sentinel/sentinel/` (governor, identity, capability, mission_memory, audit);
> v9 is how that core would be deployed, not a claim that it is deployed.

## Assumptions

- **Orchestration:** AWS EKS.
- **Workflow state:** LangGraph for agentic definition, Temporal for durable,
  deterministic execution.
- **Observability:** OpenTelemetry → a tracing backend (Jaeger / Datadog).
- **Identity:** OAuth2 / OIDC via an external IdP, mapped to the Policy Governor.

## Component Mapping

| Component | Technology | Responsibility | Today's stand-in |
|---|---|---|---|
| API Gateway | Envoy / Istio | JWT validation, rate limiting, ingress | — |
| Workflow Engine | Temporal | Durable execution, state, recovery | — |
| Graph Logic | LangGraph (Python) | Routing, planning, evaluation | persona lanes + `governor` |
| Policy Governor | OPA sidecar | Synchronous per-request capability eval | `sentinel/sentinel/governor.py` |
| Audit Ledger | Kafka + S3 (WORM) | Immutable append-only decision log | `sentinel/sentinel/audit.py` (hash-chained) |
| Identity | OIDC / IdP | Sponsor, scope, token | `sentinel/sentinel/identity.py` |

The Policy Governor runs as an **independent service and sidecar** so no module
can bypass authorization — the same invariant the in-repo `PolicyGovernor`
enforces as the single evaluation gate.

## Target Repository Layout (`/percival-v9`)

```
/cmd         governor/ · orchestrator/ · gateway/     # service entry points
/internal    policy/ (OPA rego) · graph/ (LangGraph) · agents/ · memory/ · tracing/
/deploy      terraform/ (EKS,IAM,RDS,Temporal) · k8s/ (Helm,sidecars) · policies/
/prompts     version-controlled system/developer/operator packs   # see prompts/percival/
/tests       e2e/ (Temporal) · policy/ (fail-closed, boundary)
.github/workflows/                                    # audit-logged CI/CD
```

## Kubernetes Sidecar Pattern (reference manifest — not applied)

Orchestrator worker with an OPA policy-governor sidecar; every request is
evaluated locally and synchronously before the worker acts:

```yaml
# reference only — no cluster is provisioned by this repo
apiVersion: apps/v1
kind: Deployment
metadata: { name: percival-orchestrator }
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: orchestrator-worker
          image: clearglass/percival-orchestrator:v9.0.0
          env:
            - { name: TEMPORAL_HOST_URL, value: "temporal-frontend.temporal.svc.cluster.local:7233" }
            - { name: POLICY_ENDPOINT,  value: "http://localhost:8181/v1/data/percival/authz/allow" }
        - name: policy-governor-sidecar
          image: openpolicyagent/opa:latest
          args: ["run", "--server", "/policies"]
          volumeMounts:
            - { name: opa-policies, mountPath: /policies, readOnly: true }
```

## Failure Modes, Edge Cases & Recovery

| Hazard | Handling |
|---|---|
| **Policy cache split-brain** (stale OPA allows a revoked capability) | Bind OPA cache invalidation to CI/CD completion for `deploy/policies/`; short TTLs. |
| **Temporal poison pill** (node exception → worker crash-loop) | Temporal **Reset** to rewind graph state to last-good node, bypassing the failed block. |
| **Audit ledger backpressure** (Kafka down → Escalation Gate hangs) | **Fail-closed audit sync:** Governor transitions to **deny-all** and raises an incident. *(Implemented today: `governor.degraded`.)* |
| **Post-retrieval PII/brand violation** (allowed fetch, disallowed content) | EvalOps scores output post-retrieval; below threshold → downgrade to verification. *(Implemented: `confidence_threshold`.)* |
| **Hanging external call** (API timeout leaves node unresolved) | Circuit breakers: strict timeouts (~5000ms) on Context/Retrieval external calls; fall back to safe state. |

## Validation Procedures

1. Inject simulated policy violations at the router → confirm the Governor
   intercepts and logs them. *(Covered in spirit by `tests/test_governor.py`.)*
2. Force a low EvalOps score on a draft → confirm downgrade, not flawed output.
   *(Covered: confidence-threshold tests.)*
3. Run a multi-lane request → confirm the router synthesizes one coherent
   output. *(Covered: multi-lane governor test.)*
4. Drop the audit ledger → confirm deny-all transition + incident.
   *(Covered: fail-closed audit-sync tests.)*
