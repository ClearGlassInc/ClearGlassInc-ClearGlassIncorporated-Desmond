# ClearGlassInc Artemis — Self-Evolving AI Intelligence Platform

## System Architecture

### 1) Control Plane vs Mission Plane

**Control Plane (change management + governance):**
- **Apollo** release channels (dev/staging/prod), canary rollouts, policy bundles, rollback orchestration.
- Prompt/workflow/model registry with immutable versions.
- Eval orchestrator that gates promotions.
- Governance service for human approvals and separation-of-duties.

**Mission Plane (real-time intelligence operations):**
- **Gotham** apps for investigations, case management, operational timelines, target/entity tracking.
- **Foundry** pipelines + ontology-backed data products.
- **AIP** copilots, agents, and tool-calling workflows.
- Event-driven backend services for triage, enrichment, alerting, and recommendation.

### 2) Full-Stack Layered View

```text
[Web UI (React/TS)]
   -> [API Gateway + BFF]
      -> [AuthN/AuthZ + Policy Engine]
      -> [Mission Services (Python FastAPI)]
         -> [Event Bus (Kafka/PubSub)]
         -> [Foundry Pipelines + Ontology]
         -> [Gotham Operational Apps]
         -> [AIP Agent Runtime + Model Router]
         -> [Search/RAG Index + Feature Store]
         -> [Observability + Evals + Audit Ledger]
            -> [Apollo Deployment Control + Rollback]
```

### 3) Frontend (Mission UI)
- Analyst workspace: timeline, entity graph, alert inbox, evidence panel, confidence ladder.
- Commander dashboard: mission KPIs, escalation queue, approval tasks, coalition posture.
- Copilot panel: explainable recommendations with provenance links.
- “Why this?” panel: model trace, prompt version, retrieval citations, policy checks, and confidence decomposition.

### 4) Backend Service Topology (Python-first)
- `ingest-service`: connectors for ISR feeds, SIGINT summaries, HUMINT reports, OSINT streams.
- `entity-resolution-service`: graph merge, dedupe, confidence propagation.
- `triage-service`: risk scoring, queue prioritization, mission-context routing.
- `agent-orchestrator`: multi-agent workflow runtime with state machine + tool contracts.
- `recommendation-service`: action package generation with decision rationale.
- `approval-service`: human gate enforcement and SLA timers.
- `learning-loop-service`: eval ingestion, regression detection, safe-upgrade proposals.
- `policy-decision-point`: centralized ABAC/ReBAC checks.

### 5) Deployment and Runtime
- Apollo deploys signed artifacts to isolated enclaves.
- Per-enclave model catalog and policy bundles.
- Runtime kill-switches for any autonomous subsystem.
- Blue/green + canary + automatic rollback on quality, latency, or policy violations.

---

## Data and Ontology

### 1) Canonical Ontology (Foundry Ontology + Gotham objects)

Core entities:
- `Person`, `Organization`, `Device`, `Vehicle`, `Location`, `Event`, `Case`, `Mission`, `Signal`, `Report`, `Indicator`, `ActionPackage`, `Decision`.

Core relationships:
- `ASSOCIATED_WITH`, `OBSERVED_AT`, `COMMUNICATED_WITH`, `TRIGGERED`, `MENTIONED_IN`, `PART_OF_CASE`, `SUPPORTS_HYPOTHESIS`, `CONTRADICTS`.

Enrichment attributes:
- `confidence_score` (0-1), `source_reliability`, `information_credibility`, `classification`, `compartment`, `coalition_tags`, `lineage_ref`, `temporal_validity` (`valid_from`, `valid_to`), `mission_phase`.

### 2) Temporal + Lineage Model
- Bi-temporal storage:
  - **Event time** (when it happened).
  - **System time** (when we learned/updated it).
- Lineage chain:
  - raw source -> transform -> entity resolution -> analytical product -> recommendation -> decision outcome.
- Every transform versioned and traceable to code commit + workflow version + model ID.

### 3) Permissions in Ontology
- Entity-level ACL + attribute-level masking.
- ReBAC: user can access object if linked to authorized mission/case.
- Need-to-know tags with coalition segmentation.
- Dynamic policy constraints: geography, operation window, duty role.

### 4) Example Ontology Tables (SQL)

```sql
create table ontology_entity (
  entity_id uuid primary key,
  entity_type text not null,
  canonical_name text,
  confidence_score numeric(4,3) not null,
  classification text not null,
  compartment text not null,
  coalition_tags text[] not null,
  valid_from timestamptz,
  valid_to timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  lineage_ref text not null
);

create table ontology_relationship (
  rel_id uuid primary key,
  src_entity_id uuid not null,
  dst_entity_id uuid not null,
  rel_type text not null,
  confidence_score numeric(4,3) not null,
  evidence_refs text[] not null,
  valid_from timestamptz,
  valid_to timestamptz,
  lineage_ref text not null
);
```

---

## AI and Agent Design

### 1) AIP Copilots
- **Analyst Copilot**: hypothesis generation, evidence retrieval, contradiction checks.
- **Commander Copilot**: mission impact forecasts, escalation recommendations, resource options.
- **Watchfloor Copilot**: high-velocity triage, priority justification, suggested SOP playbooks.

### 2) Multi-Agent Workflow (AIP)
Agent roles:
1. `TriageAgent` – classify severity and urgency.
2. `EnrichmentAgent` – gather additional data/evidence.
3. `CorrelationAgent` – link event to active cases/entities.
4. `SummarizationAgent` – build concise intel brief.
5. `RecommendationAgent` – propose action package and expected outcomes.
6. `SafetyAgent` – policy and guardrail validation.

### 3) Tooling Contracts
Allowed tool calls:
- `query_ontology(entity_filters, mission_scope)`
- `open_case(case_payload)`
- `generate_brief(template_id, evidence_refs)`
- `submit_action_package(package, risk_assessment)`
- `request_human_approval(action_id, reason)`

Operationally significant calls (`open_case`, `submit_action_package`) require explicit approval token.

### 4) Model Router Strategy
- Route by data sensitivity, task type, latency SLA, and confidence requirements.
- Example tiers:
  - Tier 1 fast classifier model (triage, tagging).
  - Tier 2 reasoning model (correlation, recommendation draft).
  - Tier 3 high-assurance model (final narrative, justification).
- Router emits: model ID, latency, cost, confidence, and fallback decision.

---

## Self-Improvement Loop

### 1) Signals Captured
- Operator edits to recommendations.
- Accepted/rejected approvals with reasons.
- Query reformulations and abandoned sessions.
- Alert false-positive/false-negative outcomes.
- Mission outcomes (e.g., timeliness, correctness, downstream impact).

### 2) Evaluation Pipeline
1. Collect feedback events into `learning_events` stream.
2. Build eval datasets by scenario class.
3. Run offline eval harness (precision/recall, policy compliance, latency).
4. Propose updates: prompts, heuristics, routing, workflow branching.
5. Run shadow/canary tests.
6. Require human approval for promotion.
7. Apollo rollout with auto-rollback thresholds.

### 3) Safe Upgrade Controls
- No autonomous objective rewriting.
- Bounded change surface:
  - Prompt sections allowed to mutate (`examples`, `ordering`, `format_constraints`).
  - Disallowed sections (`mission_policy`, `legal`, `action_authority`).
- Dual sign-off for critical workflow changes.
- Policy-as-code checks before deployment.
- Drift monitors trigger quarantine mode + revert.

### 4) Versioning + Rollback
- Semantic versioning for prompts/workflows/models:
  - `prompt.triage.v1.12.0`
  - `workflow.alertflow.v2.4.1`
- Every recommendation carries version tuple in metadata.
- One-click rollback via Apollo to previous known-good bundle.

---

## Full-Stack Implementation

### 1) Web UI (TypeScript/React)
- Microfrontend modules:
  - `intel-feed`
  - `entity-graph`
  - `copilot-console`
  - `approval-center`
  - `eval-observatory`
- Real-time updates via WebSocket/SSE from event gateway.

### 2) API Gateway + BFF
- API gateway handles JWT/mTLS, rate limits, request signing.
- BFF composes data from ontology, case service, and copilot responses.

### 3) Streaming + Storage
- Kafka topics:
  - `raw.intel.events`
  - `intel.enriched`
  - `intel.alerts`
  - `ops.approvals`
  - `ml.feedback`
  - `ml.eval.results`
- Lakehouse for immutable storage + feature extraction.
- Vector index for semantic retrieval with attribute filters.

### 4) Observability Stack
- OpenTelemetry traces across agent workflow steps.
- Metrics: `p95_latency`, `precision`, `recall`, `trust_score`, `approval_overturn_rate`.
- Mission-aware SLO dashboards and anomaly alarms.

### 5) CI/CD/CD with Apollo
- GitOps repo for policy bundles and workflow specs.
- Build -> sign -> verify -> staged deploy -> canary -> promote.
- Runtime policy hot-reload under signed control.

---

## Security and Governance

### 1) Zero-Trust Architecture
- mTLS service-to-service.
- SPIFFE/SPIRE-style workload identity.
- Just-in-time credentials and short-lived tokens.

### 2) Access Control
- ABAC + ReBAC + mission compartment rules.
- Row/column/entity-level filtering in data access layer.
- Coalition boundary enforcement at query-time and render-time.

### 3) Immutable Provenance
- Append-only audit ledger for:
  - data accesses,
  - model/tool calls,
  - approvals,
  - deployments,
  - rollbacks.
- Cryptographic hash chain for tamper evidence.

### 4) Model & Prompt Governance
- Prompt registry with owner, rationale, test evidence, approval signatures.
- Model cards with known constraints and risk profile.
- Mandatory policy eval gates before production promotion.

---

## Code Examples

### A) Python FastAPI Mission Service

```python
# services/triage_service/main.py
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from .policy import check_access
from .router import route_model
from .agents import triage_event

app = FastAPI(title="ClearGlassInc Artemis Triage Service")

class IntelEvent(BaseModel):
    event_id: str
    mission_id: str
    payload: dict
    classification: str

@app.post("/triage")
def triage(event: IntelEvent, principal=Depends(check_access)):
    model = route_model(task="triage", classification=event.classification)
    result = triage_event(event.model_dump(), model=model)
    return {
        "event_id": event.event_id,
        "severity": result["severity"],
        "confidence": result["confidence"],
        "model": model,
        "prompt_version": result["prompt_version"],
    }
```

### B) Policy Check (Python, OPA-style)

```python
# services/common/policy.py
from dataclasses import dataclass

@dataclass
class Principal:
    user_id: str
    roles: list[str]
    compartments: list[str]
    coalition_tags: list[str]

def enforce_entity_access(principal: Principal, entity: dict) -> bool:
    if entity["classification"] not in principal.roles:
        return False
    if entity["compartment"] not in principal.compartments:
        return False
    if not set(entity["coalition_tags"]).issubset(set(principal.coalition_tags)):
        return False
    return True
```

### C) Event Handler (Python, Kafka)

```python
# services/learning_loop/consumer.py
import json
from confluent_kafka import Consumer
from .evals import enqueue_eval_candidate

consumer = Consumer({
    "bootstrap.servers": "kafka:9092",
    "group.id": "learning-loop",
    "auto.offset.reset": "earliest"
})
consumer.subscribe(["ml.feedback", "ops.approvals"])

while True:
    msg = consumer.poll(1.0)
    if msg is None or msg.error():
        continue
    event = json.loads(msg.value().decode("utf-8"))
    enqueue_eval_candidate(event)
```

### D) Ontology-Driven Query (SQL)

```sql
-- Find high-confidence entities connected to an active mission in last 24h
select e.entity_id, e.entity_type, e.canonical_name, e.confidence_score
from ontology_entity e
join mission_entity_link mel on mel.entity_id = e.entity_id
where mel.mission_id = :mission_id
  and e.confidence_score >= 0.80
  and e.updated_at >= now() - interval '24 hours'
order by e.confidence_score desc;
```

### E) Workflow State Machine (Python)

```python
# services/agent_orchestrator/state_machine.py
from enum import Enum

class State(str, Enum):
    INGESTED = "INGESTED"
    TRIAGED = "TRIAGED"
    ENRICHED = "ENRICHED"
    CORRELATED = "CORRELATED"
    RECOMMENDED = "RECOMMENDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"

ALLOWED = {
    State.INGESTED: [State.TRIAGED],
    State.TRIAGED: [State.ENRICHED],
    State.ENRICHED: [State.CORRELATED],
    State.CORRELATED: [State.RECOMMENDED],
    State.RECOMMENDED: [State.PENDING_APPROVAL],
    State.PENDING_APPROVAL: [State.EXECUTED, State.REJECTED],
}
```

### F) Prompt Evaluation Harness (Python)

```python
# services/evals/run_prompt_eval.py
from dataclasses import dataclass
from typing import Callable

@dataclass
class EvalCase:
    name: str
    input_payload: dict
    expected_label: str


def run_eval(cases: list[EvalCase], infer: Callable[[dict], dict]) -> dict:
    correct = 0
    for case in cases:
        out = infer(case.input_payload)
        if out.get("label") == case.expected_label:
            correct += 1
    precision = correct / max(len(cases), 1)
    return {
        "precision": precision,
        "cases": len(cases),
        "pass": precision >= 0.92,
    }
```

### G) TypeScript Approval Gate Client

```ts
// web/src/api/approval.ts
export async function requestApproval(actionId: string, rationale: string) {
  const res = await fetch(`/api/approvals`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actionId, rationale }),
  });

  if (!res.ok) throw new Error(`Approval request failed: ${res.status}`);
  return res.json();
}
```

---

## Scenario Walkthrough (Cinematic + Technical)

1. **Live Event Ingested**  
   A maritime sensor burst + intercepted comms enters `raw.intel.events`. Ingest service normalizes and tags mission context (`Mission-Red-Sea-07`).

2. **Machine-Speed Triage**  
   `TriageAgent` classifies severity as `HIGH`, confidence `0.87`, and escalates to enrichment due to anomaly signature similarity.

3. **Enrichment + Correlation**  
   `EnrichmentAgent` pulls vessel history, sanctions links, recent geofenced movement.  
   `CorrelationAgent` links to existing `Case-4421` and a known organization cluster with confidence propagation.

4. **Recommendation Drafted**  
   `RecommendationAgent` creates Action Package AP-99: “Open coordinated interdiction prep + alert partner cell.”  
   `SafetyAgent` flags operational significance -> mandatory human approval gate.

5. **Human Decision**  
   Commander reviews rationale, evidence graph, and policy trace. Approves with modification: narrow geofence to reduce collateral alerts.

6. **Execution + Auditing**  
   System executes only approved actions. Audit ledger stores: actor, timestamp, model/prompt/workflow versions, evidence refs.

7. **Learning Loop Update**  
   The commander’s modification is ingested as corrective feedback.  
   Eval pipeline creates a candidate prompt update improving geofence recommendation heuristics.

8. **Safe Self-Upgrade**  
   New prompt version passes offline eval + shadow test, then canary in one enclave via Apollo.  
   Drift monitor stays within guardrails for 48 hours -> promotion to production.

9. **Future Behavior Improvement**  
   Similar future events receive more precise geofence suggestions, with lower override rate and faster approval latency.

---

## Implementation Roadmap (90 Days)

- **Phase 1 (Days 1-30):** Ontology foundation, ingest pipelines, basic copilot, policy engine, audit logging.
- **Phase 2 (Days 31-60):** Multi-agent orchestration, approval center, eval harness, model router, dashboards.
- **Phase 3 (Days 61-90):** Self-improvement pipeline, canary rollouts, automated rollback, coalition hardening, mission SLOs.

This blueprint gives ClearGlassInc Artemis a production-grade, self-improving intelligence platform that remains human-governed, policy-bounded, and operationally decisive.
