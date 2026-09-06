# ClearGlassInc Artemis — Mission-Grade, Self-Evolving C2 Architecture (Palantir Gotham + Foundry + AIP + Apollo)

## System Architecture

### 1) Layered Full-Stack Topology

```text
[Operator Web UI: SvelteKit + TypeScript + Deck.gl/Cesium]
        |
        v
[API Gateway + Policy Enforcement Point]
        |
        +--> [Realtime Channel Service: WebSocket/gRPC-Web]
        +--> [Command API Service: Python FastAPI]
        +--> [Search API Service: Python + PGVector/Qdrant]
        |
        v
[Event Bus: Redpanda/Kafka]
   |          |            |
   |          |            +--> [AIP Agent Orchestrator]
   |          +--> [Foundry Pipeline Workers]
   +--> [Ingestion Connectors: GDELT/NVD/ADS-B/USGS/OSINT]

[Data Plane]
  - PostgreSQL + PostGIS + TimescaleDB
  - Lakehouse (Foundry datasets, immutable bronze/silver/gold)
  - Vector DB (Qdrant/Milvus)
  - Object Store for raw artifacts (S3-compatible MinIO on-prem)

[Intelligence Plane]
  - Palantir Gotham (investigations, case management, entity graph)
  - Palantir Foundry (ontology, transforms, data lineage)
  - Palantir AIP (copilots, agents, eval harness)
  - Local LLM Runtime (vLLM/Ollama, no external API dependency)

[Control Plane]
  - Apollo release rings, canary, rollback, policy gating
  - OPA/Cedar policy-as-code
  - OpenTelemetry + SIEM + immutable audit ledger
```

### 2) Component Responsibilities

- **Gotham**: operational intelligence workspace, case timelines, link analysis, watchlists.
- **Foundry**: canonical data model, ontology objects/edges, pipeline DAGs, data quality checks.
- **AIP**: mission copilots, tool-using agents, evaluation pipelines, model/prompt routing.
- **Apollo**: secure packaging, staged deployments (dev/stage/prod/edge), kill-switch + rollback.

### 3) High-Performance Backend (Python-first implementation with polyglot gateways)

Even with Rust/Go edge services possible, this implementation centers Python for precision and velocity:
- **Python FastAPI microservices** with `uvloop`, `asyncio`, `pydantic`.
- Critical hot-path parsers can be moved to Rust extensions (`pyo3`) where needed.
- Streaming consumers use `aiokafka` and `confluent-kafka` bindings.

---

## Data and Ontology

### 1) Core Ontology Objects

```yaml
entities:
  Person:
    keys: [person_id, aliases, citizenship]
  Organization:
    keys: [org_id, legal_name, sector]
  ThreatActor:
    keys: [actor_id, actor_name, ttps, confidence]
  Asset:
    keys: [asset_id, asset_type, owner, criticality]
  Vulnerability:
    keys: [cve_id, cvss, epss, exploited_in_wild]
  Event:
    keys: [event_id, source, event_type, occurred_at, geo]
  Mission:
    keys: [mission_id, objective, priority, theater]
  Alert:
    keys: [alert_id, severity, status, created_at]
relationships:
  - ThreatActor TARGETS Asset
  - Vulnerability IMPACTS Asset
  - Event INDICATES ThreatActor
  - Alert DERIVED_FROM Event
  - Mission PRIORITIZES Alert
  - Analyst RESOLVES Alert
metadata:
  confidence: [0.0, 1.0]
  lineage: [source_system, transform_id, model_version]
  temporal: [valid_from, valid_to, observed_at]
  permissions: [classification, coalition_tags, need_to_know]
```

### 2) Postgres + Timescale + PostGIS schema

```sql
create extension if not exists postgis;
create extension if not exists timescaledb;

create table intel_event (
  event_id uuid primary key,
  source text not null,
  event_type text not null,
  payload jsonb not null,
  confidence numeric(4,3) not null check (confidence between 0 and 1),
  observed_at timestamptz not null,
  occurred_at timestamptz,
  geom geometry(Point, 4326),
  lineage jsonb not null,
  classification text not null,
  coalition_tags text[] not null default '{}'
);

select create_hypertable('intel_event', 'observed_at', if_not_exists => true);

create table threat_alert (
  alert_id uuid primary key,
  mission_id uuid,
  severity text not null,
  score numeric(5,2) not null,
  status text not null,
  recommendation jsonb,
  opened_by text,
  opened_at timestamptz not null,
  resolved_at timestamptz,
  feedback_label text,
  feedback_notes text
);

create index idx_intel_event_payload_gin on intel_event using gin(payload);
create index idx_intel_event_geom on intel_event using gist(geom);
create index idx_alert_status on threat_alert(status);
```

### 3) Ontology-driven behavior

Agents do not call raw tables directly; they query ontology-resolved views with row/entity filters injected by policy engine:
- `view_mission_context_entities(user_ctx, mission_id)`
- `fn_resolve_actor_confidence(actor_id, as_of_ts)`

---

## AI and Agent Design

### 1) Copilots
- **Analyst Copilot**: triage suggestions, evidence packets, timeline generation.
- **Commander Copilot**: risk posture summary, decision branches, likely impact.

### 2) Multi-agent workflow (AIP)

```text
IngestAgent -> NormalizeAgent -> EnrichAgent -> CorrelateAgent -> RiskScoreAgent
     -> RecoAgent -> HumanApprovalGate -> ActionAgent (if approved)
```

### 3) Tool-using agent contract (Python)

```python
from pydantic import BaseModel, Field
from typing import Literal, Any

class ToolCall(BaseModel):
    tool: Literal["search_events", "open_case", "draft_action_pkg", "query_graph"]
    args: dict[str, Any]
    justification: str = Field(min_length=20)

class AgentDecision(BaseModel):
    decision: Literal["recommend", "defer", "escalate"]
    confidence: float
    rationale: str
    tool_calls: list[ToolCall]
    requires_human_approval: bool = True
```

### 4) Human approval gates
- Any action mutating case state, ticketing external response, or changing watchlists requires signed operator approval.
- Two-person integrity for high-severity operational actions.

---

## Self-Improvement Loop

### 1) Feedback capture
Signals captured:
- operator accepts/rejects recommendation
- analyst corrections to entities/links
- alert precision outcomes (true/false positive)
- downstream mission effect (time-to-containment, escalation avoided)

### 2) Continuous eval pipeline

```text
Raw Signals -> Feature Builder -> Eval Dataset Version N
     -> Prompt/Workflow Candidates
     -> Offline Evals (precision/recall/latency/trust)
     -> Shadow Deployment
     -> Human Review Board
     -> Apollo Ring Promotion
```

### 3) Safe mutation rules
- Agent may propose changes, never auto-merge to production.
- Changes are PR-based and policy-checked.
- Rollback target is always previous signed release bundle.

### 4) Drift detection
- Population drift on source fields (PSI/KL divergence).
- Concept drift on label agreement between operator feedback and model prediction.
- Auto-create “recalibration missions” when drift threshold breached.

---

## Full-Stack Implementation

### Frontend (SvelteKit + Deck.gl)
- live mission board, threat matrix, geospatial layer, event timeline.
- WebSocket delta updates (<300ms target intra-site).

### API Gateway
- Envoy/NGINX + OPA sidecar.
- mTLS, JWT, ABAC claims (`compartment`, `mission_scope`, `coalition`).

### Backend services (Python)
- `ingest-service` (connectors)
- `fusion-service` (correlation/scoring)
- `case-service` (Gotham case sync)
- `ai-orchestrator` (AIP tools + model routing)
- `eval-service` (self-improvement harness)

### Streaming layer
- Redpanda topics:
  - `intel.raw.*`
  - `intel.normalized.*`
  - `intel.alerts`
  - `intel.feedback`
  - `intel.eval.requests`

### Retrieval/search
- hybrid BM25 + vector retrieval over Foundry-curated corpus.

### Observability
- OpenTelemetry traces across ingest → agent → approval.
- Grafana dashboards for SLOs and eval metrics.

---

## Security and Governance

- Need-to-know via ABAC + ReBAC (entity relationship access).
- Row/column/entity filtering enforced at query gateway.
- Zero-trust workload identity (SPIFFE/SPIRE or mesh identity).
- Immutable logs (append-only, hashed chain, periodic notarization).
- Prompt governance: signed prompt registry with changelog and reviewer IDs.
- Model governance: approved model card catalog + mission suitability constraints.

Policy-as-code sketch:

```rego
package artemis.authz

default allow = false

allow {
  input.user.clearance >= input.resource.classification
  input.user.coalition[_] == input.resource.coalition_tag
  input.action == "read"
}

allow {
  input.action == "execute_operational"
  input.user.role == "commander"
  input.change.approval_count >= 2
}
```

---

## Code Examples

### 1) Real-time ingestion handler (Python/FastAPI + aiokafka)

```python
# app/ingest/main.py
import asyncio
import json
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import BaseModel

class NormalizedEvent(BaseModel):
    event_id: str
    source: str
    event_type: str
    observed_at: str
    confidence: float
    payload: dict

async def run_ingest_loop() -> None:
    consumer = AIOKafkaConsumer(
        "intel.raw.gdelt", "intel.raw.nvd", "intel.raw.adsb",
        bootstrap_servers="redpanda:9092", group_id="ingest-service"
    )
    producer = AIOKafkaProducer(bootstrap_servers="redpanda:9092")
    await consumer.start(); await producer.start()
    try:
        async for msg in consumer:
            raw = json.loads(msg.value)
            norm = NormalizedEvent(
                event_id=raw["id"],
                source=raw["source"],
                event_type=raw["type"],
                observed_at=raw["ts"],
                confidence=min(max(raw.get("confidence", 0.5), 0.0), 1.0),
                payload=raw,
            )
            await producer.send_and_wait(
                "intel.normalized.events",
                norm.model_dump_json().encode("utf-8"),
            )
    finally:
        await consumer.stop(); await producer.stop()

if __name__ == "__main__":
    asyncio.run(run_ingest_loop())
```

### 2) Workflow state machine (Python)

```python
from enum import Enum
from dataclasses import dataclass

class AlertState(str, Enum):
    NEW = "NEW"
    TRIAGED = "TRIAGED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"

@dataclass
class AlertContext:
    alert_id: str
    state: AlertState
    risk_score: float
    requires_2pi: bool


def transition(ctx: AlertContext, event: str) -> AlertContext:
    table = {
        (AlertState.NEW, "triage_complete"): AlertState.TRIAGED,
        (AlertState.TRIAGED, "recommendation_ready"): AlertState.PENDING_APPROVAL,
        (AlertState.PENDING_APPROVAL, "approved"): AlertState.APPROVED,
        (AlertState.APPROVED, "action_executed"): AlertState.EXECUTED,
        (AlertState.PENDING_APPROVAL, "rejected"): AlertState.REJECTED,
    }
    ctx.state = table.get((ctx.state, event), ctx.state)
    return ctx
```

### 3) Self-improvement evaluator (Python)

```python
# eval_service/pipeline.py
from dataclasses import dataclass

@dataclass
class EvalResult:
    candidate_id: str
    precision: float
    recall: float
    p95_latency_ms: int
    trust_score: float


def passes_gate(r: EvalResult) -> bool:
    return (
        r.precision >= 0.92 and
        r.recall >= 0.88 and
        r.p95_latency_ms <= 1200 and
        r.trust_score >= 4.3
    )


def select_for_shadow(candidates: list[EvalResult]) -> list[str]:
    return [c.candidate_id for c in candidates if passes_gate(c)]
```

### 4) Ontology query abstraction (Python)

```python
async def query_actor_activity(db, actor_name: str, mission_id: str, user_ctx: dict):
    sql = """
    select e.event_id, e.observed_at, e.payload
    from intel_event e
    join mission_entity_access mea on mea.entity_id = (e.payload->>'actor_id')::uuid
    where e.payload->>'actor_name' = $1
      and mea.mission_id = $2
      and mea.principal_id = $3
    order by e.observed_at desc
    limit 200
    """
    return await db.fetch(sql, actor_name, mission_id, user_ctx["principal_id"])
```

---

## Scenario Walkthrough (Cinematic + Technical)

**T+00:00 (2026-05-13 15:45 UTC)**: GDELT stream emits sudden burst around critical infrastructure filing chatter in CA.
1. `ingest-service` normalizes event, writes `intel.normalized.events`.
2. `fusion-service` correlates with NVD exploit chatter + known FIN7 infrastructure.
3. `RiskScoreAgent` raises alert score from 61.2 → 84.9, marks `PENDING_APPROVAL`.
4. Commander Copilot drafts action package: “Increase monitoring on utility regulator portals, deploy additional detections, notify mission cell.”
5. Operator **rejects** recommendation step 3 because local context indicates scheduled benign filing cycle.
6. Feedback event (`intel.feedback`) stores rejection reason “seasonal false positive due to recurring compliance filing window.”
7. Eval pipeline clusters similar false positives, proposes prompt patch and a new feature: `regulatory_calendar_proximity`.
8. Human review board approves update for shadow ring.
9. Apollo promotes after 48h shadow success: false positives drop 27%, precision increases 8.4 points.

This is how ClearGlassInc Artemis gets better: bounded self-proposal, explicit human approval, measurable mission outcomes, and cryptographically auditable change control.
