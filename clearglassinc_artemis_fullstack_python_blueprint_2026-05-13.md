# ClearGlassInc Artemis — Self-Evolving AI Intelligence Platform

## System Architecture

### 1) Platform Topology (Gotham + Foundry + AIP + Apollo)

```mermaid
flowchart LR
  subgraph Edge[Coalition Edge / Mission Zone]
    UI[Artemis Command UI\n(React + TypeScript)]
    SDK[Secure SDK + WASM Policy Hints]
  end

  subgraph Control[Core Control Plane]
    APIGW[API Gateway\n(FastAPI + Envoy)]
    Auth[AuthN/AuthZ\nOIDC + ABAC + ReBAC]
    Policy[Policy Decision Point\nOPA + Cedar]
    Bus[Streaming Bus\nKafka/Redpanda]
    Orchestrator[Workflow Orchestrator\nTemporal + Python Workers]
  end

  subgraph Foundry[Foundry Data Plane]
    Ont[Ontology + Object Types]
    Pipelines[Batch/Streaming Pipelines]
    Lake[Lakehouse\nParquet/Iceberg]
    Search[Vector + Graph Retrieval]
  end

  subgraph Gotham[Gotham Ops Plane]
    Cases[Case Mgmt + Investigations]
    Link[Entity Link Analysis]
    Ops[Operational Timeline]
  end

  subgraph AIP[AIP AI Plane]
    Router[Model Router\nPolicy-Aware]
    Agents[Multi-Agent Runtime]
    Evals[Eval Harness + Prompt Registry]
  end

  subgraph Apollo[Apollo Runtime]
    Deploy[Progressive Deploy]
    Rollback[Instant Rollback]
    Attest[Signed Artifact + SBOM]
  end

  UI --> SDK --> APIGW
  APIGW --> Auth --> Policy
  APIGW --> Bus
  Bus --> Pipelines --> Lake --> Ont
  Ont --> Search
  APIGW --> Orchestrator --> Agents
  Agents --> Router --> Evals
  Agents --> Cases
  Agents --> Link
  Agents --> Ops
  Deploy --> APIGW
  Deploy --> Orchestrator
  Deploy --> Agents
  Deploy --> Pipelines
  Rollback --> Deploy
  Attest --> Deploy
```

### 2) Layered Full-Stack Design
- **Frontend layer**: React + TypeScript + WebSockets + MapLibre/Deck.gl mission map, with per-widget clearance tags.
- **API layer**: Envoy ingress + FastAPI services exposing mission APIs and AI action endpoints.
- **Domain services** (Python): ingestion, entity-resolution, alert scoring, case orchestration, action package generator.
- **Streaming layer**: Kafka topics for raw intel, normalized events, alerts, feedback, outcomes.
- **Data layer**: Foundry datasets + PostgreSQL/PostGIS + OpenSearch + Qdrant for mixed structured/unstructured retrieval.
- **Ontology layer**: Foundry Ontology objects and links as the shared contract between humans, apps, and agents.
- **AI layer (AIP)**: copilots + tool-using agents + eval gates + guarded model router.
- **Policy layer**: OPA/Cedar enforcing ABAC/ReBAC, coalition partitions, purpose-of-use checks.
- **Observability layer**: OpenTelemetry traces, Prometheus metrics, Loki logs, AIP eval dashboards.
- **Deployment layer (Apollo)**: canary deployments, signed bundles, rollback pins, runtime kill switches.

---

## Data and Ontology

### 1) Core Ontology Objects

```python
# ontology/types.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict

class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    method: str  # bayesian_fusion | model_vote | analyst_override
    rationale: str

class SourceLineage(BaseModel):
    source_system: str  # GDELT, NVD, ADS-B, SIGINT-X
    source_record_id: str
    ingestion_time: datetime
    transform_version: str
    checksum: str

class Entity(BaseModel):
    entity_id: str
    entity_type: str  # PERSON, ORG, DEVICE, LOCATION, VULN, INCIDENT
    canonical_name: str
    aliases: List[str] = []
    first_seen: datetime
    last_seen: datetime
    confidence: Confidence
    lineage: List[SourceLineage]
    labels: Dict[str, str] = {}  # coalition, compartment, mission

class Relationship(BaseModel):
    rel_id: str
    src_entity_id: str
    dst_entity_id: str
    rel_type: str  # OWNS, CONTACTED, EXPLOITS, LOCATED_AT
    valid_from: datetime
    valid_to: Optional[datetime]
    confidence: Confidence
    lineage: List[SourceLineage]
```

### 2) Temporal + Mission Context
- Every entity and relation is bitemporal: **event time** and **system ingestion time**.
- Mission context envelope includes `mission_id`, `op_phase`, `roE_profile`, `coalition_tenant`.
- Permissions are stamped at object and edge level to enable coalition-safe graph traversals.

### 3) How Ontology Drives Behavior
- UI widgets query ontology object sets; no direct table coupling.
- Agents receive task + ontology schema + allowed tools, ensuring constrained reasoning.
- Gotham investigation views consume the same object graph, preserving analyst/AI consistency.

---

## AI and Agent Design

### 1) Copilots
- **Analyst Copilot**: triage, explain confidence, generate hypotheses, draft intel notes.
- **Commander Copilot**: summarize mission risk deltas, propose COAs, attach assumptions.
- **Compliance Copilot**: validate releaseability, policy violations, and provenance completeness.

### 2) Multi-Agent Workflow Graph

```python
# aip/agent_graph.py
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class AgentTask:
    task_id: str
    mission_id: str
    objective: str
    context: Dict[str, Any]

class Agent:
    def run(self, task: AgentTask) -> Dict[str, Any]:
        raise NotImplementedError

class TriageAgent(Agent): ...
class EnrichmentAgent(Agent): ...
class CorrelationAgent(Agent): ...
class RecommendationAgent(Agent): ...
class RedTeamCriticAgent(Agent): ...

WORKFLOW = [
    "triage",
    "enrichment",
    "correlation",
    "recommendation",
    "red_team_critic",
    "human_approval_gate",
]
```

### 3) Tool-Using Agent Contract

```python
# aip/tools/contracts.py
from typing import Literal, TypedDict, Any

class ToolCall(TypedDict):
    tool: Literal[
        "query_ontology",
        "open_case",
        "generate_brief",
        "prepare_action_package",
        "request_human_approval",
    ]
    args: dict

class ToolResult(TypedDict):
    ok: bool
    data: Any
    provenance: dict
    policy_tags: list[str]
```

Operationally significant actions (`open_case`, `prepare_action_package`, outbound notifications) require explicit approval token issued by policy service.

---

## Self-Improvement Loop

### 1) Signal Capture
Capture streams:
- Operator edits to AI drafts.
- Analyst accept/reject decisions.
- Alert true/false positive outcomes.
- Mission result labels (prevented, delayed, escalated).
- Latency, retrieval hit-rate, and confidence calibration drift.

```sql
-- foundry/sql/feedback_signal.sql
CREATE TABLE feedback_signal (
  signal_id UUID PRIMARY KEY,
  timestamp_utc TIMESTAMPTZ NOT NULL,
  mission_id TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  signal_type TEXT NOT NULL,
  target_version TEXT NOT NULL,
  payload JSONB NOT NULL,
  approval_required BOOLEAN NOT NULL DEFAULT TRUE
);
```

### 2) Improvement Compiler
- Nightly and continuous jobs convert signals into candidate improvements:
  1. Prompt delta proposals.
  2. Tool-routing rule updates.
  3. Retrieval weighting updates.
  4. Threshold tuning for alert severity.

```python
# learning/improvement_compiler.py
class ImprovementProposal(BaseModel):
    proposal_id: str
    category: str  # prompt|workflow|routing|threshold
    current_version: str
    candidate_patch: dict
    expected_gain: dict
    risk_score: float


def compile_proposals(signals: list[dict]) -> list[ImprovementProposal]:
    # rank by mission impact and safety risk
    ...
```

### 3) Safe Promotion Workflow
- Candidate -> sandbox eval -> shadow traffic -> limited canary -> approved rollout.
- Requires human approval for mission-impacting categories.
- Apollo keeps immutable release lineage and one-click rollback.

```yaml
# apollo/promotion_policy.yaml
gates:
  - name: eval_pass
    min_precision: 0.92
    min_recall: 0.88
    max_p95_latency_ms: 1800
  - name: safety
    max_policy_violations: 0
    max_hallucination_rate: 0.01
  - name: human_review
    required_roles: ["LeadAnalyst", "MissionCommander"]
rollback:
  auto_on:
    - drift_score_gt: 0.15
    - policy_violation_count_gt: 0
```

### 4) Drift Detection + Audit
- Data drift: embedding centroid shift + feature PSI.
- Behavior drift: precision/recall decay over rolling windows.
- Full audit: who approved what, why, with before/after metrics and dataset hashes.

---

## Full-Stack Implementation

### 1) API Gateway + Mission Service (Python/FastAPI)

```python
# services/mission_api/main.py
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ClearGlassInc Artemis Mission API")

class ActionRequest(BaseModel):
    mission_id: str
    action_type: str
    payload: dict

@app.post("/v1/actions/propose")
def propose_action(req: ActionRequest, user=Depends(...)):
    # 1) policy pre-check
    # 2) route to agent orchestrator
    # 3) return proposal with confidence + provenance
    return {"proposal_id": "p-123", "status": "PENDING_APPROVAL"}

@app.post("/v1/actions/approve/{proposal_id}")
def approve_action(proposal_id: str, user=Depends(...)):
    # enforce role + mission clearance + two-person rule
    return {"proposal_id": proposal_id, "status": "APPROVED"}
```

### 2) Streaming Ingestion

```python
# ingestion/stream_worker.py
from confluent_kafka import Consumer, Producer
import json

consumer = Consumer({"bootstrap.servers": "kafka:9092", "group.id": "intel-norm"})
producer = Producer({"bootstrap.servers": "kafka:9092"})
consumer.subscribe(["raw.intel.events"])

while True:
    msg = consumer.poll(0.5)
    if not msg:
        continue
    event = json.loads(msg.value())
    normalized = {
        "event_id": event["id"],
        "event_time": event.get("event_time"),
        "source": event["source"],
        "payload": event,
    }
    producer.produce("intel.events.normalized", json.dumps(normalized).encode())
```

### 3) Workflow State Machine (Temporal)

```python
# workflows/triage_workflow.py
from temporalio import workflow

@workflow.defn
class TriageWorkflow:
    @workflow.run
    async def run(self, mission_id: str, alert_id: str) -> dict:
        triage = await workflow.execute_activity("triage_agent", alert_id, start_to_close_timeout=60)
        enrich = await workflow.execute_activity("enrichment_agent", triage, start_to_close_timeout=120)
        corr = await workflow.execute_activity("correlation_agent", enrich, start_to_close_timeout=120)
        reco = await workflow.execute_activity("recommendation_agent", corr, start_to_close_timeout=60)
        critique = await workflow.execute_activity("redteam_critic_agent", reco, start_to_close_timeout=45)
        return {"recommendation": reco, "critique": critique, "requires_approval": True}
```

### 4) Policy-as-Code Check

```rego
# policy/action_approval.rego
package artemis.authz

default allow = false

allow {
  input.user.clearance >= input.action.required_clearance
  input.user.mission_ids[_] == input.action.mission_id
  not input.action.cross_coalition
  input.user.roles[_] == "MissionCommander"
}
```

### 5) Eval Pipeline

```python
# evals/run_eval.py
from dataclasses import dataclass

@dataclass
class EvalResult:
    version: str
    precision: float
    recall: float
    p95_latency_ms: int
    policy_violations: int


def gate(result: EvalResult) -> bool:
    return (
        result.precision >= 0.92
        and result.recall >= 0.88
        and result.p95_latency_ms <= 1800
        and result.policy_violations == 0
    )
```

---

## Security and Governance

- **Need-to-know**: ABAC + ReBAC with mission, compartment, coalition, and purpose-of-use attributes.
- **Fine-grained controls**: row/column/entity/edge-level policy filters across Foundry datasets and ontology objects.
- **Compartmentalization**: per-coalition encryption domains and scoped key material.
- **Zero-trust runtime**: workload identity (SPIFFE/SPIRE), mTLS east-west, ephemeral credentials.
- **Immutable provenance**: append-only audit ledger for source lineage, prompt version, model version, and operator approvals.
- **Model governance**: model registry with risk tiering, approved tasks, blocked tasks, and sunset policies.
- **Prompt governance**: signed prompt bundles, semantic diffing, and mandatory reviewer attestation.

---

## Code Examples (Additional)

### Model Router with Guardrails

```python
# aip/router.py
from typing import Dict

MODEL_POOL = {
    "high_precision": "llama-3.1-70b-instruct",
    "fast_path": "mistral-8x7b",
    "critical_reasoning": "mixtral-governed",
}

def route(task: Dict) -> str:
    if task["risk_level"] == "HIGH":
        return MODEL_POOL["critical_reasoning"]
    if task["latency_budget_ms"] < 800:
        return MODEL_POOL["fast_path"]
    return MODEL_POOL["high_precision"]
```

### Operator Feedback Capture API

```python
# services/feedback_api.py
@app.post("/v1/feedback")
def capture_feedback(payload: dict, user=Depends(...)):
    # validate schema, attach mission/user context, push to feedback topic
    kafka_produce("intel.feedback.signals", payload)
    return {"status": "RECORDED"}
```

### Ontology-Driven Retrieval Query (Pseudo SQL/Graph)

```sql
SELECT e.entity_id, e.canonical_name, r.rel_type, e2.canonical_name AS related
FROM ontology_entity e
JOIN ontology_relationship r ON r.src_entity_id = e.entity_id
JOIN ontology_entity e2 ON e2.entity_id = r.dst_entity_id
WHERE e.labels->>'mission_id' = :mission_id
  AND e.entity_type = 'INCIDENT'
  AND r.confidence_score > 0.7
ORDER BY e.last_seen DESC
LIMIT 200;
```

---

## Scenario Walkthrough (Cinematic + Technical)

1. **Live Event Arrival (T+0s)**
   - ADS-B anomaly + CVE exploit chatter enter `raw.intel.events`.
   - Ingestion service normalizes and emits to `intel.events.normalized`.

2. **Triage + Enrichment (T+2s)**
   - Triage agent scores severity 0.84 (critical band).
   - Enrichment agent pulls correlated entities from ontology + recent mission graph.

3. **Correlation + Recommendation (T+6s)**
   - Correlation agent identifies shared infrastructure pattern tied to prior campaign.
   - Recommendation agent proposes COA: isolate segment X, elevate watch on corridor Y.

4. **Approval Gate (T+9s)**
   - Mission Commander receives action package with provenance, confidence, and counterfactual risks.
   - Commander approves isolation, rejects automated notification.

5. **Execution + Audit (T+12s)**
   - Approved action executed via orchestrator; all artifacts signed and logged.
   - Gotham case auto-created with timeline and linked entities.

6. **Learning Loop (Post-Event)**
   - System records that notification recommendation was rejected.
   - Improvement compiler flags over-aggressive notification heuristic.
   - Candidate workflow update enters eval harness, passes shadow tests, awaits human approval.
   - After approval, Apollo rolls out canary to 10% missions with rollback guard.

7. **Safer, Better Future Behavior**
   - Next similar event: fewer false notification recommendations, higher analyst trust score, lower response latency.

---

## Implementation Roadmap (90 Days)
- **Phase 1 (Weeks 1–3)**: ontology contract, streaming ingestion, baseline copilot, policy foundation.
- **Phase 2 (Weeks 4–7)**: multi-agent orchestration, approval gates, eval harness, mission UI.
- **Phase 3 (Weeks 8–10)**: self-improvement compiler, shadow traffic, drift monitors.
- **Phase 4 (Weeks 11–13)**: Apollo progressive delivery, rollback drills, coalition hardening, readiness certification.

This design gives **ClearGlassInc Artemis** a mission-grade, human-governed, self-improving intelligence platform with Python-centric implementation depth, strict safety constraints, and production deployment discipline.
