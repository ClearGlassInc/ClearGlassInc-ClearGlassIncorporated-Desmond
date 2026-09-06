# Percival v9 — Governed Orchestration Architecture (Blueprint)

> **Status: design blueprint, not a provisioned system.** This document is the
> version-controlled reference for Percival v9. It does **not** stand up any
> cloud infrastructure. Provisioning AWS EKS / Temporal / Kafka is an external,
> irreversible, cost-incurring action and — consistent with Percival's own
> Policy Governor model and this repo's safety invariant
> (**read-only → draft → approval → execution**) — requires credentials and
> explicit human approval before any `terraform apply`.

Percival v9 is a strict, policy-bound agentic orchestration engine. Its defining
property is that **the Policy Governor is a physically separate service and
sidecar**, so no module can bypass authorization. Every request is evaluated and
every decision is appended to an immutable audit ledger.

---

## 1. Assumptions

| Concern | Choice |
|---|---|
| Orchestration | AWS EKS (Elastic Kubernetes Service) |
| Workflow state | LangGraph for agentic workflow definition, backed by Temporal for durable, deterministic execution |
| Observability | OpenTelemetry (OTel) → unified tracing backend (Jaeger or Datadog) |
| Identity | OAuth2 / OIDC via an external identity provider (IdP) |

---

## 2. Production Repository Layout

Physical separation of concerns; the Policy Governor runs independently and as a
sidecar so other modules cannot bypass authorization.

```text
/percival-v9
├── /cmd
│   ├── governor/            # Entry point: Policy enforcer service
│   ├── orchestrator/        # Entry point: LangGraph/Temporal worker
│   └── gateway/             # Entry point: API gateway & request interception
├── /internal
│   ├── policy/              # OPA (Open Policy Agent) rego rules & validator
│   ├── graph/               # LangGraph DAG definitions and state transitions
│   ├── agents/              # Router, Context, Execution, EvalOps logic
│   ├── memory/              # Vector (RAG) and Graph DB interfaces
│   └── tracing/             # OpenTelemetry spans, metrics, context propagation
├── /deploy
│   ├── terraform/           # EKS cluster, IAM roles, RDS, Temporal Cloud
│   ├── k8s/                 # manifests, Helm charts, sidecar definitions
│   └── policies/            # JSON/YAML capability schemas and RBAC maps
├── /prompts                 # Version-controlled system and operator packs
├── /tests
│   ├── e2e/                 # Temporal workflow execution tests
│   └── policy/              # Fail-closed and boundary violation tests
└── .github/workflows/       # CI/CD pipelines (audit-logged deployments)
```

---

## 3. Deployment Blueprint (Terraform & Kubernetes)

Sidecar pattern for the Policy Governor and Trace Collector ensures every request
in the cluster is evaluated and logged deterministically.

### Architecture Component Mapping

| Component | Technology | Responsibility |
|---|---|---|
| **API Gateway** | Envoy / Istio | JWT validation, rate limiting, ingress routing |
| **Workflow Engine** | Temporal | Durable execution, state persistence, recovery |
| **Graph Logic** | LangGraph (Python) | Agentic routing, planning, and evaluation |
| **Policy Governor** | OPA Sidecar | Synchronous capability evaluation per request |
| **Audit Ledger** | Kafka + S3 (WORM) | Immutable, append-only log of all decisions |

### Kubernetes Deployment Example (Orchestrator with Policy Sidecar)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: percival-orchestrator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: percival-orchestrator
  template:
    metadata:
      labels:
        app: percival-orchestrator
      annotations:
        instrumentation.opentelemetry.io/inject-python: "true"
    spec:
      containers:
      - name: orchestrator-worker
        image: clearglass/percival-orchestrator:v9.0.0
        env:
          - name: TEMPORAL_HOST_URL
            value: "temporal-frontend.temporal.svc.cluster.local:7233"
          - name: POLICY_ENDPOINT
            value: "http://localhost:8181/v1/data/percival/authz/allow"
      - name: policy-governor-sidecar
        image: openpolicyagent/opa:latest
        args:
          - "run"
          - "--server"
          - "/policies"
        volumeMounts:
          - name: opa-policies
            mountPath: /policies
            readOnly: true
```

> **Hardening notes before this is production-real:** pin the OPA image to a
> digest (not `:latest`), pin `percival-orchestrator` to an immutable tag/digest,
> and define the `opa-policies` volume source (ConfigMap or projected read-only
> mount). Add resource requests/limits and liveness/readiness probes to both
> containers.

---

## 4. System / Developer / Operator Prompt Pack

Precise operating parameters for each human-in-the-loop interaction, preserving
the v9 capability scopes.

| Persona | Primary Prompt Directive | Execution Scope |
|---|---|---|
| **System (Base)** | "You are Percival v9, a strict, policy-bound orchestration engine. You must output the current graph state, validate OIDC tokens against the Policy Governor, and route intent. If authorization fails, output HTTP 403 and append to Audit Ledger. Do not evaluate user intent; evaluate policy state." | Sovereign Execution & Authorization |
| **Developer** | "Initialize Sandbox Mode. Assume `execute_internal` capability. Map the following user intent into a LangGraph DAG. Output the proposed nodes, edges, and required tools. Do not execute the graph. Flag all nodes requiring `external_system_write` for the Escalation Gate." | Graph Design & Testing |
| **Operator** | "Enter Escalation Gate Mode. Present the pending transaction trace. Display: 1. Requestor Identity, 2. Target System, 3. Proposed Payload, 4. Risk Score from EvalOps. Await explicit signed approval (cryptographic signature) before transitioning state to Execution." | Audit & Approval |

---

## 5. Edge Cases, Failure Modes & Validation

### Failure Modes
- **Split-Brain in Policy Caching** — the local OPA sidecar caches an outdated
  policy, allowing a revoked capability to execute.
- **Temporal Poison Pill** — an unhandled exception in a LangGraph node causes a
  deterministic worker crash loop in Temporal, blocking the queue.
- **Audit Ledger Backpressure** — the Kafka topic for the Audit Ledger goes down,
  causing the synchronous Escalation Gate to hang.

### Edge Cases
- A request perfectly matches an allow policy for data retrieval, but EvalOps
  scores the extracted PII as a violation of brand/security guidelines
  post-retrieval.
- A workflow requires an external API call that times out indefinitely, leaving
  the LangGraph state in an unresolved hanging node.

### Validation & Recovery Procedures
- **Cache Invalidation Hooks** — bind OPA cache refreshes to CI/CD pipeline
  completion for the `policies/` directory.
- **Circuit Breakers** — strict timeouts (e.g., 5000ms) on all Context Engine and
  Retrieval Layer external calls.
- **Fail-Closed Audit Sync** — if the Audit Ledger returns a timeout, the Policy
  Governor automatically transitions to **deny-all** and triggers an incident
  alert.
- **State Rewind** — for poisoned workflows, use Temporal's Reset to rewind the
  graph state to the last known good node, bypassing the failed logic block.

---

## 6. Relationship to this repo

Percival v9 generalizes the governance model already proven in
`clearglass-commerce/` (`control-plane/app/governance.py`): score every proposed
action, route low-risk to auto-execute, and **block high/critical actions behind
an approvals record** with an append-only audit trail. This blueprint restates
that invariant at cluster scale — OPA as the governor, Kafka+S3 WORM as the
ledger, and the Operator "Escalation Gate" as the approval step.

**Next real steps (each gated on approval + credentials):**
1. Scaffold the `/percival-v9` tree with stub services + `tests/policy` fail-closed cases.
2. Write the OPA rego + `deploy/policies` capability schemas; get the boundary tests green in CI first.
3. Only then wire `deploy/terraform` and run a plan (never a blind apply) against a non-prod account.
