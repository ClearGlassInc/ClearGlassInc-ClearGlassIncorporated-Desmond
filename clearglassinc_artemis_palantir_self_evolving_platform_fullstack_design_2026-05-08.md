# ClearGlassInc Artemis: Self-Evolving Intelligence Platform (Palantir Gotham + Foundry + AIP + Apollo)

## System Architecture

### 1) Mission Objectives
- Fuse live + historical intelligence into a coalition-aware operational picture.
- Support machine-speed triage with human-in-the-loop control for consequential actions.
- Continuously improve prompts, workflows, and model routing with explicit approval gates.
- Maintain immutable provenance, policy enforcement, and auditable operations.

### 2) Layered Architecture

```text
[Web UI + Analyst Workbench]
    |
[API Gateway + BFF]
    |
[Domain Services: Case, Alert, Entity, Mission, Report, Feedback]
    |
[Event Bus / Streaming + Workflow Engine]
    |
[Foundry Data Pipelines + Ontology + Feature Store]
    |
[AIP Agent Runtime + Model Router + Eval Harness]
    |
[Gotham Operational Views + Investigative Graphs]
    |
[Apollo Deployment, Policy Rollout, Runtime Controls]
```

### 3) Frontend
- **Stack:** React + TypeScript + GraphQL client + websocket live feed.
- **Primary screens:**
  - Mission Dashboard (timeline, live alerts, confidence trend)
  - Entity 360 (relationships, provenance, sensitivity tags)
  - Agent Recommendation Queue (approve/reject/defer with rationale)
  - Model/Eval Console (prompt version deltas, A/B outcomes)

### 4) API Gateway + Backend
- **API gateway:** routing, JWT introspection, rate limits, tenant/coalition headers.
- **BFF pattern:** mission-specific data shaping for low-latency UI.
- **Service mesh:** mTLS between services, OPA sidecars for policy decisions.
- **Core microservices (Python/FastAPI):**
  - `ingest-service`
  - `entity-resolution-service`
  - `case-service`
  - `recommendation-service`
  - `feedback-service`
  - `eval-service`
  - `reporting-service`

### 5) Data + Ontology + Search
- **Foundry pipelines:** batch + streaming transforms, enrichment, schema harmonization.
- **Ontology:** mission objects mapped to operational entities/relations.
- **Storage:** lakehouse + graph projection + vector index + time-series index.
- **Search/RAG:** hybrid retrieval (keyword + graph neighborhood + embeddings).

### 6) AI Orchestration (AIP)
- Multi-agent runtime with tool-using agents and workflow guardrails.
- Model router selects model per task: extraction, reasoning, summarization, forecasting.
- Evaluations as first-class artifacts: precision/recall, hallucination risk, operator trust.

### 7) Deployment + Runtime Control (Apollo)
- Progressive deploys per region/coalition cell.
- Signed artifact promotion from dev → staging → ops.
- Fast rollback of model routes, prompts, policies, and service versions.

---

## Data and Ontology

### 1) Entity Model
- **Core entities:** Person, Organization, Device, Location, Event, Signal, Case, Mission, Task.
- **Support entities:** SourceDocument, SensorFeed, Assessment, Recommendation, ActionPackage.

### 2) Relationship Model
- `ASSOCIATED_WITH`, `OWNS`, `LOCATED_AT`, `PARTICIPATED_IN`, `DERIVED_FROM`, `CONTRADICTS`, `SUPPORTS`.
- Relationships have confidence, temporal validity, and sensitivity label.

### 3) Mandatory Metadata Fields
- `confidence_score: float`
- `lineage: [{source_id, transform_id, timestamp}]`
- `valid_time: {start, end}`
- `transaction_time: {ingested_at, updated_at}`
- `mission_context: {mission_id, objective, priority}`
- `permissions: {classification, releasability, compartments}`

### 4) Example Ontology Schema (SQL)

```sql
create table ontology_entity (
  entity_id uuid primary key,
  entity_type text not null,
  canonical_name text not null,
  confidence_score numeric(5,4) not null,
  mission_id uuid,
  classification text not null,
  releasability text not null,
  compartments text[] not null,
  valid_start timestamptz,
  valid_end timestamptz,
  ingested_at timestamptz not null,
  updated_at timestamptz not null
);

create table ontology_relationship (
  rel_id uuid primary key,
  src_entity_id uuid not null,
  dst_entity_id uuid not null,
  rel_type text not null,
  confidence_score numeric(5,4) not null,
  source_ref text not null,
  valid_start timestamptz,
  valid_end timestamptz,
  classification text not null,
  compartments text[] not null
);
```

### 5) Ontology-Driven Behavior
- Agents must query ontology policy filters before retrieving any object.
- Recommendation logic weighs graph centrality + temporal recency + source reliability.
- Human workflows use ontology-native views (Entity 360, Case impact map, mission dependencies).

---

## AI and Agent Design

### 1) Copilots
- **Analyst Copilot:** triage suggestions, query generation, evidence threading.
- **Commander Copilot:** mission-level prioritization, risk summaries, action package review.

### 2) Multi-Agent Workflow
1. **Triage Agent** classifies incoming signal and assigns urgency.
2. **Enrichment Agent** resolves entities and pulls contextual graph neighborhood.
3. **Correlation Agent** links to ongoing missions/cases and deduplicates patterns.
4. **Summarization Agent** drafts assessment with confidence and dissenting evidence.
5. **Recommendation Agent** proposes actions requiring explicit operator approval.

### 3) Tool-Using Actions (Gated)
- Query Foundry datasets.
- Traverse Gotham-style investigation graph.
- Draft intel report.
- Open/append case.
- Build action package (never dispatch autonomously).

### 4) Approval Gates
- Any high-impact action (`priority=high`, cross-compartment data access, external dissemination) requires:
  - dual authorization
  - policy pass
  - immutable approval log entry

---

## Self-Improvement Loop

### 1) Feedback Signal Capture
- Operator edits to summaries/recommendations.
- Approve/reject outcomes and reason codes.
- Alert disposition labels (true positive, false positive, inconclusive).
- Mission outcome metrics (latency to action, downstream mission impact).

### 2) Improvement Pipeline
```text
Raw Signals -> Labeling/Normalization -> Eval Dataset Build ->
Prompt/Workflow Candidates -> Offline Eval -> Shadow Deployment ->
Human Review Board -> Controlled Rollout -> Continuous Monitoring
```

### 3) Versioning + Change Control
- Version each artifact independently:
  - prompts (`prompt://recommendation/v23`)
  - workflows (`wf://triage/v11`)
  - routing policies (`route://intel-router/v7`)
- Apollo release bundles include artifact hashes + rollback pointers.

### 4) Drift and Safety
- Drift monitors detect distribution changes in event type, source reliability, and error rates.
- Auto-freeze self-update pipeline if:
  - precision drops below floor
  - false-positive rate exceeds threshold
  - operator trust score dips beyond SLA band

### 5) Human Governance Board
- Weekly review of proposed upgrades with signed decisions.
- Required evidence: eval diff, risk memo, blast-radius estimate, rollback plan.

---

## Full-Stack Implementation Blueprint

### 1) Suggested Repository Structure

```text
clearglassinc-artemis/
  apps/
    web-console/                 # React/TS analyst & commander UI
  services/
    api-gateway/                 # AuthN, routing, throttling
    case-service/                # Cases and mission workflows
    entity-service/              # Resolution and ontology sync
    recommendation-service/      # Agent orchestration + approvals
    feedback-service/            # Operator feedback capture
    eval-service/                # Offline/online eval harness
  agents/
    triage_agent/
    enrichment_agent/
    correlation_agent/
    summary_agent/
    recommendation_agent/
  data/
    schemas/
    foundry-pipelines/
    quality-rules/
  policy/
    opa/
    prompt-governance/
    model-governance/
  infra/
    terraform/
    apollo-release-manifests/
  observability/
    dashboards/
    alerts/
  docs/
    runbooks/
    architecture/
```

### 2) Event Bus Contracts (Python/Pydantic)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, List

class IntelEvent(BaseModel):
    event_id: str
    mission_id: str
    source_type: Literal["osint", "sigint", "humint", "partner_feed"]
    payload_ref: str
    confidence: float = Field(ge=0.0, le=1.0)
    classification: str
    compartments: List[str]
    observed_at: datetime

class AgentRecommendation(BaseModel):
    rec_id: str
    event_id: str
    action_type: Literal["open_case", "escalate", "monitor", "dismiss"]
    rationale: str
    confidence: float
    requires_approval: bool
```

### 3) Backend Service Skeleton (FastAPI)

```python
from fastapi import FastAPI, Depends, HTTPException
from .auth import enforce_policy
from .models import IntelEvent, AgentRecommendation
from .orchestrator import run_agent_workflow

app = FastAPI(title="ClearGlassInc Artemis Recommendation Service")

@app.post("/v1/events/triage", response_model=AgentRecommendation)
async def triage_event(event: IntelEvent, user=Depends(enforce_policy("triage:write"))):
    result = await run_agent_workflow(event=event, actor=user)
    if result.requires_approval and not user.can("approve:high_impact"):
        raise HTTPException(status_code=403, detail="Approval authority required")
    return result
```

### 4) Workflow State Machine (Python)

```python
from enum import Enum

class State(str, Enum):
    INGESTED = "ingested"
    TRIAGED = "triaged"
    ENRICHED = "enriched"
    CORRELATED = "correlated"
    RECOMMENDED = "recommended"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"

ALLOWED = {
    State.INGESTED: {State.TRIAGED},
    State.TRIAGED: {State.ENRICHED, State.REJECTED},
    State.ENRICHED: {State.CORRELATED},
    State.CORRELATED: {State.RECOMMENDED},
    State.RECOMMENDED: {State.APPROVED, State.REJECTED},
    State.APPROVED: {State.EXECUTED},
}

def transition(current: State, target: State) -> State:
    if target not in ALLOWED.get(current, set()):
        raise ValueError(f"Invalid transition {current} -> {target}")
    return target
```

### 5) Policy Check Example (OPA/Rego)

```rego
package artemis.authz

default allow = false

allow {
  input.user.clearance >= input.resource.classification
  input.user.compartments[_] == input.resource.compartments[_]
  input.action == "read"
}

allow {
  input.action == "approve"
  input.user.roles[_] == "mission_commander"
  input.resource.impact == "high"
}
```

### 6) Eval Pipeline Skeleton (Python)

```python
from dataclasses import dataclass
from typing import List

@dataclass
class EvalCase:
    prompt_version: str
    workflow_version: str
    input_event: dict
    expected_action: str


def evaluate(cases: List[EvalCase], runner):
    correct = 0
    latency_ms = []
    for c in cases:
        out = runner.run(c.input_event, c.prompt_version, c.workflow_version)
        correct += int(out.action_type == c.expected_action)
        latency_ms.append(out.latency_ms)
    precision = correct / max(1, len(cases))
    return {
        "precision": precision,
        "p95_latency_ms": sorted(latency_ms)[int(0.95 * (len(latency_ms)-1))]
    }
```

---

## Security and Governance

### 1) Need-to-Know Enforcement
- Entity-level ACL + attribute-based controls (classification, caveats, compartment).
- Coalition boundary policies for releasability tagging and cross-domain transfer controls.

### 2) Zero-Trust Execution
- Workload identity per service.
- No implicit trust by network segment.
- Runtime attestation for model-serving nodes.

### 3) Immutable Provenance
- Append-only audit ledger for:
  - data ingest
  - transformation lineage
  - model/prompt/workflow version used
  - operator approvals/rejections

### 4) Model/Prompt Governance
- Prompt changes require:
  - unit eval pass
  - safety eval pass
  - reviewer sign-off
- Routing policy change is blocked if mission-critical latency SLO degrades in shadow tests.

---

## Scenario Walkthrough (Cinematic + Technical)

1. A partner feed emits an anomalous maritime signal at **14:02:11Z** into the streaming bus.
2. `triage_agent` scores urgency at **0.87** and tags mission context `M-ATL-009`.
3. `enrichment_agent` resolves vessel, ownership shell entity, and prior route anomalies from Foundry ontology.
4. `correlation_agent` links two historical events and one ongoing case, raising confidence to **0.91**.
5. `recommendation_agent` drafts: “Escalate + open case + notify commander” with rationale and evidence chain.
6. Commander receives action package in UI, reviews source lineage and dissenting evidence, then **approves** escalation.
7. Case is opened and all decisions are written to immutable audit ledger.
8. 36 hours later, outcome label confirms true positive. Feedback pipeline generates a new eval datum.
9. Candidate prompt v24 shows +4.2% precision in shadow eval without latency regression.
10. Governance board approves rollout via Apollo canary to 10% missions, then 100% after stability window.

This produces a controlled self-improving system: continuously better recommendations, strict human authority, and complete operational accountability.
