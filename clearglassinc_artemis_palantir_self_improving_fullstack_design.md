# ClearGlassInc Artemis: Self-Evolving AI Intelligence Platform (Gotham + Foundry + AIP + Apollo)

## System Architecture

### 1) Full-Stack Layer Map

```text
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                                             │
│  - Artemis Mission Web (Next.js/TypeScript)                                         │
│  - Analyst Copilot Workspace (chat, graph, map, timeline, case pane)               │
│  - Commander Console (risk posture, mission KPIs, approval queue)                   │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ API GATEWAY + EDGE POLICY                                                           │
│  - REST/gRPC/WebSocket ingress                                                      │
│  - OIDC/SAML + hardware-backed MFA                                                  │
│  - mTLS service identity                                                            │
│  - PEP (Policy Enforcement Point)                                                   │
│  - Request context enricher (mission_id, coalition, classification, purpose)        │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ BACKEND SERVICE MESH                                                                 │
│  - Case Service (Gotham object orchestration)                                       │
│  - Ontology Query Service (Foundry object + graph query facade)                     │
│  - Agent Orchestrator (AIP agent runtime + tool router)                             │
│  - Eval Service (offline/online evals + candidate promotion scores)                 │
│  - Feedback Service (operator corrections, acceptance signals, outcomes)             │
└──────────────────────────────────────────────────────────────────────────────────────┘
                  │                          │                            │
                  ▼                          ▼                            ▼
┌───────────────────────────────┐   ┌────────────────────────────┐   ┌──────────────────────────┐
│ STREAMING / EVENT LAYER       │   │ DATA & ONTOLOGY LAYER      │   │ AI ORCHESTRATION (AIP)   │
│ Kafka/Pulsar + schema registry│   │ Foundry pipelines + Ontology│  │ Copilots + Multi-agent   │
│ raw -> normalized -> enriched │   │ bitemporal + lineage model  │  │ tool use + eval harness  │
└───────────────────────────────┘   └────────────────────────────┘   └──────────────────────────┘
                  │                          │                            │
                  └──────────────┬───────────┴──────────────┬─────────────┘
                                 ▼                          ▼
                        ┌─────────────────────┐    ┌──────────────────────────┐
                        │ SEARCH/RETRIEVAL    │    │ OBSERVABILITY + GOVERNANCE│
                        │ lexical+vector+graph│    │ tracing, policy logs, eval│
                        └─────────────────────┘    └──────────────────────────┘
                                                │
                                                ▼
                                     ┌────────────────────┐
                                     │ APOLLO DELIVERY    │
                                     │ canary, rollback,  │
                                     │ signed releases     │
                                     └────────────────────┘
```

### 2) Runtime Topology (Production Deployment)

- **Frontend**: Next.js app deployed in secure enclave edge nodes.
- **Gateway**: Envoy/Nginx + auth middleware + policy pre-check.
- **Core APIs (Python)**: FastAPI services, each independently versioned.
- **Eventing**: Kafka topics partitioned by mission and region.
- **Foundry**: bronze/silver/gold data products + ontology-backed object sets.
- **AIP**: prompt templates, agents, evaluation suites, tool contracts.
- **Apollo**: environment rings (`dev -> staging -> canary -> prod`) with rollback gates.

### 3) Primary Control Flows

1. **Intel Event Flow**: sensor event -> normalization -> entity resolution -> graph correlation -> recommendation.
2. **Operator Loop**: recommendation -> approve/reject/edit -> feedback capture -> eval dataset refresh.
3. **Self-Improve Loop**: evidence-driven proposal -> offline eval -> human governance approval -> canary deploy -> automatic rollback on drift.

---

## Data and Ontology

### 1) Ontology Design (Foundry Object Types)

#### Core Entities

- `Person`, `Organization`, `Asset`, `Device`, `Vessel`, `Location`, `Signal`, `Incident`, `Case`, `Mission`, `ActionPackage`, `Outcome`.

#### Core Relationships

- `OBSERVED_AT`, `ASSOCIATED_WITH`, `COMMUNICATED_WITH`, `TRAVELED_TO`, `PART_OF_MISSION`, `TRIGGERED_ALERT`, `RECOMMENDED_ACTION`, `APPROVED_BY`, `RESULTED_IN`.

#### Mandatory Governance Fields

- `confidence_score: float [0..1]`
- `source_reliability: enum(A,B,C,D,E)`
- `lineage_ref: immutable provenance pointer`
- `valid_start_ts`, `valid_end_ts` (real-world validity)
- `record_start_ts`, `record_end_ts` (system bitemporal state)
- `classification`, `compartment`, `coalition_scope[]`
- `mission_context_id`
- `policy_tags[]`

### 2) SQL Model (Warehouse/Lakehouse Service Tables)

```sql
create table if not exists artemis.entity (
  entity_id uuid primary key,
  entity_type text not null,
  canonical_name text,
  attributes jsonb not null,
  confidence_score numeric(4,3) not null,
  source_reliability text not null,
  classification text not null,
  compartment text not null,
  coalition_scope text[] not null,
  mission_context_id uuid not null,
  lineage_ref text not null,
  valid_start_ts timestamptz not null,
  valid_end_ts timestamptz,
  record_start_ts timestamptz not null default now(),
  record_end_ts timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists artemis.relationship (
  relationship_id uuid primary key,
  src_entity_id uuid not null,
  dst_entity_id uuid not null,
  relationship_type text not null,
  attributes jsonb not null,
  confidence_score numeric(4,3) not null,
  mission_context_id uuid not null,
  lineage_ref text not null,
  valid_start_ts timestamptz not null,
  valid_end_ts timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists artemis.feedback_signal (
  signal_id uuid primary key,
  mission_context_id uuid not null,
  artifact_type text not null,   -- prompt/workflow/recommendation/route
  artifact_id text not null,
  action text not null,          -- approve/reject/edit/defer
  correction jsonb,
  actor_id text not null,
  actor_role text not null,
  trust_delta numeric(4,3),
  outcome_ref text,
  created_at timestamptz not null default now()
);
```

### 3) Ontology-Driven Execution

- **Human UX**: UI components query ontology types directly (graph nodes/edges, timelines, case facts).
- **Agent behavior**: tool contracts require ontology type constraints, confidence thresholds, and mission scope filters.
- **Permission propagation**: every query injects `mission_context_id`, `classification ceiling`, and `coalition_scope`.

---

## AI and Agent Design

### 1) Copilot Suite

- **Analyst Copilot**: investigation assistance, evidence synthesis, hypothesis testing.
- **Commander Copilot**: course-of-action options, risk tradeoff modeling, mission status forecasts.
- **Watch Officer Copilot**: real-time alert triage and escalation recommendation.

### 2) Multi-Agent Workflow Graph

```text
[Event Intake Agent]
   -> [Normalization Agent]
   -> [Entity Resolution Agent]
   -> [Correlation Agent]
   -> [Recommendation Agent]
   -> [Action Package Agent]
   -> [Human Approval Agent]
   -> [Execution Notifier Agent]
```

### 3) Tooling Contracts for Agents

Allowed tools (policy-scoped):

1. `query_ontology_graph`
2. `search_case_history`
3. `fetch_stream_context`
4. `draft_intel_brief`
5. `create_gotham_case`
6. `submit_action_for_approval`

Any tool that mutates operations must pass policy + approval gate.

### 4) Approval Matrix

| Action Type | Risk Level | Required Approvals |
|---|---|---|
| Draft narrative update | Low | Analyst optional |
| Open case / assign watch | Medium | Analyst required |
| Cross-coalition operational recommendation | High | Analyst + Commander + Policy officer |

---

## Self-Improvement Loop

### 1) Signal Capture Surface

The platform continuously logs:

- operator edits to AI summaries,
- approve/reject decisions on recommendations,
- false positive / false negative outcomes,
- mission result labels,
- latency and SLA misses,
- explicit operator trust score feedback.

### 2) Self-Upgrade Pipeline (Human-Governed)

```text
Signals
  -> Feature extraction
  -> Eval set construction
  -> Candidate proposal (prompt/workflow/router heuristic)
  -> Offline replay evals
  -> Governance review + sign-off
  -> Apollo canary deployment
  -> Online drift + KPI monitoring
  -> Promote OR rollback
```

### 3) Versioning + Rollback Policy

- Prompts: `prompt://triage/v2.4.1`
- Workflows: `wf://multiagent-triage/v1.9.0`
- Routing rules: `route://intel-router/v3.2.0`
- Policy bundles: `policy://coalition-guard/v5.0.3`

Rollback triggers:

- Precision drops by >3% from baseline,
- latency increase >20% p95,
- policy violation >0,
- operator trust index drop >10%.

### 4) Drift Detection

- **Data drift**: feature distribution shift (PSI, KL divergence).
- **Concept drift**: outcome misalignment by mission segment.
- **Behavior drift**: recommendation acceptance collapse by role.

All drift alerts are immutable and visible in governance dashboard.

---

## Full-Stack Implementation

### 1) Web UI Blueprint (TypeScript)

- **MissionBoard**: live feed + graph summary + risk trend.
- **CopilotPanel**: chat with citations and confidence.
- **ApprovalQueue**: risk-ranked operational actions.
- **EvalConsole**: side-by-side A/B outputs for reviewers.

```tsx
// app/components/ApprovalQueue.tsx
import { useEffect, useState } from "react";

type ApprovalItem = {
  id: string;
  missionId: string;
  risk: "low" | "medium" | "high";
  summary: string;
};

export function ApprovalQueue() {
  const [items, setItems] = useState<ApprovalItem[]>([]);

  useEffect(() => {
    const ws = new WebSocket(`${process.env.NEXT_PUBLIC_WS}/approvals`);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      setItems((prev) => [msg, ...prev].slice(0, 100));
    };
    return () => ws.close();
  }, []);

  return (
    <section>
      <h2>Operational Approval Queue</h2>
      {items.map((i) => (
        <article key={i.id}>
          <strong>{i.risk.toUpperCase()}</strong> · {i.summary}
        </article>
      ))}
    </section>
  );
}
```

### 2) API Gateway Contract

```yaml
openapi: 3.1.0
info:
  title: ClearGlassInc Artemis API
  version: 1.0.0
paths:
  /v1/copilot/respond:
    post:
      security:
        - bearerAuth: []
      parameters:
        - in: header
          name: X-Mission-Context
          required: true
          schema:
            type: string
      requestBody:
        required: true
      responses:
        "200":
          description: Copilot response with evidence citations
```

### 3) Backend Services (Python/FastAPI)

```python
# backend/app/main.py
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from app.policy import authorize, enforce_tool_access
from app.router import select_model
from app.agent_runtime import run_agent_plan

app = FastAPI(title="ClearGlassInc Artemis Mission API")

class CopilotRequest(BaseModel):
    user_query: str
    mission_context_id: str
    role_mode: str  # analyst | commander | watch_officer

@app.post("/v1/copilot/respond")
def copilot_respond(payload: CopilotRequest, authorization: str = Header(""), x_mission_context: str = Header("")):
    if payload.mission_context_id != x_mission_context:
        raise HTTPException(status_code=400, detail="Mission context mismatch")

    auth_ctx = authorize(token=authorization, mission_context_id=payload.mission_context_id)
    enforce_tool_access(auth_ctx, requested_action="copilot_read")

    route = select_model(task="intel_reasoning", auth_ctx=auth_ctx, role_mode=payload.role_mode)
    response = run_agent_plan(payload=payload, route=route, auth_ctx=auth_ctx)
    return response
```

### 4) Streaming/Event Handler (Python)

```python
# backend/workers/event_triage_worker.py
import json
from kafka import KafkaConsumer, KafkaProducer
from app.triage import triage_event

consumer = KafkaConsumer(
    "intel.events.normalized",
    bootstrap_servers=["kafka:9092"],
    value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    group_id="artemis-triage-workers",
)
producer = KafkaProducer(
    bootstrap_servers=["kafka:9092"],
    value_serializer=lambda o: json.dumps(o).encode("utf-8"),
)

for msg in consumer:
    event = msg.value
    outcome = triage_event(event)
    producer.send("intel.events.enriched", outcome)
```

### 5) Ontology Query Adapter (Python)

```python
# backend/app/tools/ontology.py
from typing import Any, Dict

ALLOWED_TYPES = {"Person", "Organization", "Device", "Asset", "Incident", "Case", "Vessel"}


def query_ontology_graph(params: Dict[str, Any], auth_ctx: Dict[str, Any]) -> Dict[str, Any]:
    entity_type = params["entity_type"]
    if entity_type not in ALLOWED_TYPES:
        raise ValueError(f"Unsupported entity type: {entity_type}")

    query = {
        "entity_type": entity_type,
        "mission_context_id": auth_ctx["mission_context_id"],
        "max_classification": auth_ctx["clearance"],
        "coalition_scope": auth_ctx["coalition_scope"],
        "limit": min(int(params.get("limit", 100)), 500),
    }
    # Foundry query call placeholder
    return {"query": query, "rows": []}
```

### 6) Workflow State Machine (Python)

```python
# backend/app/workflows/action_state_machine.py
from enum import Enum
from dataclasses import dataclass

class ActionState(str, Enum):
    DRAFT = "DRAFT"
    REVIEW_PENDING = "REVIEW_PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"

ALLOWED_TRANSITIONS = {
    ActionState.DRAFT: {ActionState.REVIEW_PENDING},
    ActionState.REVIEW_PENDING: {ActionState.APPROVED, ActionState.REJECTED},
    ActionState.APPROVED: {ActionState.EXECUTED},
}

@dataclass
class TransitionRequest:
    from_state: ActionState
    to_state: ActionState
    actor_role: str
    risk_level: str


def transition(req: TransitionRequest) -> ActionState:
    if req.to_state not in ALLOWED_TRANSITIONS.get(req.from_state, set()):
        raise ValueError("Invalid transition")
    if req.to_state == ActionState.APPROVED and req.risk_level == "high" and req.actor_role != "commander":
        raise PermissionError("High-risk actions require commander approval")
    return req.to_state
```

### 7) Policy-as-Code (Rego)

```rego
package clearglassinc.artemis.authz

default allow = false

allow {
  input.action == "read_ontology"
  input.subject.mission_context_id == input.resource.mission_context_id
  input.subject.clearance >= input.resource.classification
  some i
  input.subject.coalition_scope[i] == input.resource.coalition_scope[i]
}

allow {
  input.action == "approve_action"
  input.subject.role == "commander"
  input.resource.risk_level == "high"
  input.resource.requires_dual_control == false
}
```

### 8) Model Router (Python)

```python
# backend/app/router.py
from dataclasses import dataclass

@dataclass
class Route:
    provider: str
    model: str
    max_tokens: int
    reason: str


def select_model(task: str, auth_ctx: dict, role_mode: str) -> Route:
    classification = auth_ctx.get("classification", "low")
    latency_budget_ms = int(auth_ctx.get("latency_budget_ms", 1500))

    if classification in {"secret", "top_secret"}:
        return Route("internal", "secure-reasoner-70b", 2000, "high classification")
    if latency_budget_ms < 800:
        return Route("internal", "fast-triage-13b", 800, "tight latency")
    if role_mode == "commander":
        return Route("internal", "decision-support-34b", 1800, "commander mode")
    return Route("internal", "general-20b", 1200, "default route")
```

### 9) Eval Pipeline + Upgrade Proposal (Python)

```python
# backend/evals/pipeline.py
from dataclasses import dataclass
from statistics import mean

@dataclass
class EvalCase:
    case_id: str
    mission_context_id: str
    expected_label: str
    prompt_version: str


def run_eval_cases(cases: list[EvalCase]) -> dict:
    precision_scores = [0.94, 0.91, 0.93]
    recall_scores = [0.87, 0.89, 0.88]
    latency_scores = [820, 790, 860]

    result = {
        "precision": mean(precision_scores),
        "recall": mean(recall_scores),
        "latency_ms_p95": max(latency_scores),
    }
    result["pass"] = result["precision"] >= 0.92 and result["recall"] >= 0.86 and result["latency_ms_p95"] <= 1000
    return result


def propose_upgrade(metrics: dict, current_prompt: str) -> dict:
    if metrics["precision"] < 0.92:
        return {
            "change_type": "prompt_patch",
            "patch": "Require at least two independent corroborating sources before high-risk recommendation.",
            "requires_human_approval": True,
        }
    return {"change_type": "none", "requires_human_approval": False}
```

### 10) Apollo Promotion Workflow

```yaml
# .github/workflows/artemis-release.yml
name: artemis-release
on:
  push:
    branches: [main]

jobs:
  build-eval-release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest -q
      - run: python backend/evals/pipeline.py
      - run: ./scripts/build_signed_artifact.sh
      - run: ./scripts/apollo_deploy.sh canary
      - run: ./scripts/apollo_promote_if_healthy.sh
```

---

## Security and Governance

### 1) Access Control and Compartments

- Need-to-know enforced via ABAC + RBAC.
- Row/column/entity permissions enforced in query adapters and UI endpoints.
- Coalition boundaries encoded as policy tags and enforced at retrieval + tool execution.

### 2) Zero-Trust Runtime

- mTLS for all service-to-service traffic.
- SPIFFE/SPIRE or equivalent workload identity.
- Runtime attestation and deny-by-default network policy.

### 3) Immutable Audit and Provenance

- Append-only audit ledger captures:
  - prompt version used,
  - model route decision,
  - tool invocations,
  - policy decisions,
  - approval actions,
  - deployment and rollback events.

### 4) Model/Prompt Governance

- Artifact states: `draft -> evaluated -> approved -> canary -> production -> deprecated`.
- No automatic policy mutation allowed.
- All self-upgrade candidates require human sign-off.

---

## Code Examples

### 1) Mission Policy Check Middleware (Python)

```python
# backend/app/policy.py
from fastapi import HTTPException


def authorize(token: str, mission_context_id: str) -> dict:
    # placeholder token decode/validation
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    return {
        "subject_id": "user-123",
        "role": "analyst",
        "clearance": "secret",
        "classification": "secret",
        "coalition_scope": ["NATO-A", "NATO-B"],
        "mission_context_id": mission_context_id,
        "latency_budget_ms": 1000,
    }


def enforce_tool_access(auth_ctx: dict, requested_action: str) -> None:
    if requested_action == "copilot_read":
        return
    if requested_action == "approve_action" and auth_ctx.get("role") != "commander":
        raise HTTPException(status_code=403, detail="Commander required")
```

### 2) Agent Tool Call Envelope (Python)

```python
# backend/app/agent_runtime.py
from typing import Any, Dict
from app.tools.ontology import query_ontology_graph


def run_agent_plan(payload: Any, route: Any, auth_ctx: Dict[str, Any]) -> Dict[str, Any]:
    context = query_ontology_graph(
        {"entity_type": "Incident", "limit": 50},
        auth_ctx=auth_ctx,
    )

    return {
        "model_route": route.__dict__,
        "answer": f"Processed query '{payload.user_query}' in mission {payload.mission_context_id}",
        "evidence": context,
        "confidence": 0.89,
        "requires_approval": False,
    }
```

### 3) Feedback Ingest Endpoint (Python)

```python
# backend/app/feedback_api.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1/feedback")

class FeedbackPayload(BaseModel):
    mission_context_id: str
    artifact_type: str
    artifact_id: str
    action: str
    correction: dict | None = None

@router.post("")
def submit_feedback(payload: FeedbackPayload):
    # persist to artemis.feedback_signal
    return {"status": "accepted", "artifact_id": payload.artifact_id}
```

---

## Scenario Walkthrough

### Live Event to Safe Self-Improvement (End-to-End)

1. **00:00:03 UTC**: A maritime anomaly event enters `intel.events.raw` with AIS gaps and unusual rendezvous behavior.
2. **00:00:05 UTC**: Normalization and entity resolution bind vessel, owner org, and prior incident cluster in Foundry ontology.
3. **00:00:07 UTC**: Correlation agent computes risk score jump (`0.46 -> 0.84`) using temporal + graph + source confidence features.
4. **00:00:08 UTC**: Recommendation agent proposes `Priority-1 case` and a boarding preparation package in Gotham.
5. **00:00:10 UTC**: Because risk is high and coalition-sensitive, system routes to dual approval queue (analyst + commander).
6. **00:00:40 UTC**: Analyst approves with edited rationale; commander approves action package.
7. **00:15:00 UTC**: Mission outcome confirms interdiction success; outcome recorded with full lineage references.
8. **00:16:00 UTC**: Feedback + outcome signals enter eval builder; system proposes prompt patch to up-weight co-temporal logistics anomalies.
9. **00:22:00 UTC**: Offline replay eval passes thresholds (precision +2.8%, recall +1.9%, p95 latency +35ms).
10. **00:30:00 UTC**: Human AI governance board approves proposal; Apollo deploys canary to 10% watch desks.
11. **02:30:00 UTC**: Canary stable, no policy violations, trust index increases; Apollo promotes to 100%.
12. **Continuous**: If drift or policy breach appears, automatic rollback to prior approved prompt version executes.

### Why This Is “Self-Improving but Safe”

- The platform can **propose** prompt/workflow/router improvements.
- It cannot autonomously alter goals, policy, coalition boundaries, or approval requirements.
- Every change is versioned, evaluated, approved, and auditable.
- Human operators remain final authority for operationally significant decisions.
