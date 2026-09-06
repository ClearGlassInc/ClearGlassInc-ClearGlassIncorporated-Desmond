# ClearGlassInc Artemis — Next-Generation Self-Evolving Intelligence Platform

## 1) System Architecture

### 1.1 Reference stack (Palantir-native mapping)
- **Gotham**: mission operations, case management, investigations, entity timelines, targeting views.
- **Foundry**: ingestion, ontology, transforms, data products, policy-aware application logic.
- **AIP**: copilots, multi-agent workflows, evaluation harnesses, tool calling, model routing.
- **Apollo**: deployment orchestration, signed artifacts, progressive rollout, rollback, runtime controls.

### 1.2 Logical layers

```text
[Web UI (React/TS)]
    |
[API Gateway + OPA Policy Check]
    |
[Mission Services (Python/FastAPI)] ---- [AIP Agent Runtime]
    |                    |                      |
    |                    |                      +--> [Model Router + Guardrails]
    |                    |
    |                    +--> [Workflow Engine (Temporal)]
    |
[Event Bus (Kafka/Pulsar)]
    |
[Foundry Pipelines + Ontology + Feature Views] ---- [Search/RAG Index]
    |
[Lakehouse + Warehouse + Object Store]
    |
[Gotham Operational Surfaces]

Cross-cutting: Observability, Audit Ledger, KMS/HSM, Secrets, Apollo Runtime Controls
```

### 1.3 Physical deployment topology
- **Secure enclaves** by classification level (`UNCLAS`, `SECRET`, `TS`) with one-way transfer patterns.
- **Coalition partitions** per partner nation/org; no cross-partition query without explicit release policy.
- **Regional active-active** control plane + localized data plane for latency.
- **Zero trust mesh** (mTLS + SPIFFE identities + workload attestation).

## 2) Data and Ontology

### 2.1 Core ontology entities

```sql
-- Foundry ontology-backed tables (logical representation)
CREATE TABLE entity_person (
  person_id UUID PRIMARY KEY,
  canonical_name TEXT,
  aliases JSONB,
  nationality TEXT,
  risk_score DOUBLE PRECISION,
  confidence DOUBLE PRECISION,
  valid_from TIMESTAMPTZ,
  valid_to TIMESTAMPTZ,
  source_lineage JSONB,
  classification TEXT,
  coalition_tags TEXT[]
);

CREATE TABLE entity_device (
  device_id UUID PRIMARY KEY,
  imei TEXT,
  mac TEXT,
  owner_person_id UUID,
  confidence DOUBLE PRECISION,
  valid_from TIMESTAMPTZ,
  valid_to TIMESTAMPTZ,
  source_lineage JSONB,
  classification TEXT
);

CREATE TABLE relationship_contact (
  rel_id UUID PRIMARY KEY,
  src_person_id UUID,
  dst_person_id UUID,
  relation_type TEXT, -- "called", "met", "co-travel"
  count_30d INT,
  weight DOUBLE PRECISION,
  confidence DOUBLE PRECISION,
  observed_at TIMESTAMPTZ,
  mission_context_id UUID,
  source_lineage JSONB
);
```

### 2.2 Ontology principles
- **Temporal bitemporality**: event time vs ingest time for after-action correction.
- **Confidence envelope**: every object/relation carries confidence, model version, evidence references.
- **Provenance-first**: immutable lineage pointer to raw source, parser, transform, human overrides.
- **Mission context projection**: same entity appears differently by mission scope + need-to-know policy.

### 2.3 Permissions model
- ABAC + ReBAC hybrid:
  - Attributes: clearance, role, compartment, coalition, mission assignment.
  - Relationships: analyst assigned to case, commander owns operation.
- Enforced at:
  1. query planner (row/column/entity filtering),
  2. tool invocation (agent cannot call tools outside authorization),
  3. output redaction (final response sanitizer).

## 3) AI and Agent Design

### 3.1 Copilots
- **Analyst Copilot**: triage feed, summarize entity graphs, draft intel notes.
- **Commander Copilot**: mission impact estimate, COA (course of action) scoring, risk briefings.
- **Watchfloor Copilot**: anomaly clustering, alert fatigue reduction, escalation recommendations.

### 3.2 Multi-agent graph

```text
IngressAgent -> TriageAgent -> EnrichmentAgent -> CorrelationAgent ->
HypothesisAgent -> RecommendationAgent -> ApprovalGateAgent -> ActionPackAgent
```

### 3.3 Tool contracts
- `query_ontology(query_spec)`
- `open_case(case_payload)`
- `generate_brief(template_id, context)`
- `submit_action_proposal(proposal)`
- `request_human_approval(approval_packet)`

Any operationally significant action is blocked until `approval_status == APPROVED`.

## 4) Self-Improvement Loop (Human-Governed)

### 4.1 Signals captured
- Prompt inputs/outputs, tool traces, token/latency cost.
- Operator edits (diff of AI draft -> final accepted artifact).
- Alert outcomes (`true_positive`, `false_positive`, `missed`).
- Mission KPIs (time-to-decision, mission success proxy, operator trust score).

### 4.2 Pipeline
1. **Observe**: stream logs/events into Foundry datasets.
2. **Label**: derive weak/strong labels from operator corrections + outcomes.
3. **Evaluate**: run nightly eval suites per mission type.
4. **Propose**: generate candidate prompt/workflow/router changes.
5. **Simulate**: shadow tests + replay historical traces.
6. **Approve**: human review board + policy engine checks.
7. **Rollout**: Apollo canary deployment.
8. **Monitor**: auto rollback on degradation thresholds.

### 4.3 Drift and rollback
- Drift detectors:
  - embedding distribution shift,
  - false-positive trend break,
  - latency p95 regression,
  - trust-score decline.
- Rollback triggers expressed in policy-as-code and executed by Apollo.

## 5) Full-Stack Implementation Blueprint

### 5.1 Web UI (React/TypeScript)
- Mission console, graph explorer, live alert stream, approval queue, eval dashboard.
- Fine-grained policy-driven component visibility.

### 5.2 API gateway
- FastAPI gateway + Envoy external authz + OPA decisions.
- JWT/SPIFFE identity binding and request-level mission context injection.

### 5.3 Backend services (Python)
- `case-service`: case lifecycle + audit events.
- `entity-service`: ontology query and confidence fusion.
- `agent-orchestrator`: runs AIP workflows and tool mediation.
- `eval-service`: offline/online eval orchestration.
- `policy-service`: centralized decision point with cached policies.

### 5.4 Streaming + storage
- Kafka topics: `intel.raw`, `intel.enriched`, `alerts.scored`, `operator.feedback`, `agent.traces`.
- Lakehouse for raw/curated zones; vector index for semantic retrieval.

### 5.5 Model routing
- Router dimensions: classification level, latency budget, accuracy tier, cost ceiling.
- Always-on safety filters: prompt injection detector, PII leakage gate, policy redaction.

## 6) Security and Governance
- Need-to-know by default with deny-first policies.
- Entity-level ACLs and coalition boundary tags.
- Immutable audit chain (append-only hash-linked log).
- Signed prompts/workflows with semantic diff approval.
- Model registry with approved model cards, usage constraints, and expiration dates.

## 7) Code Examples

### 7.1 FastAPI gateway with policy check (Python)

```python
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel
import httpx

app = FastAPI(title="ClearGlassInc Artemis Gateway")

class QueryRequest(BaseModel):
    mission_id: str
    query: str

async def opa_authorize(token: str, action: str, mission_id: str) -> None:
    payload = {
        "input": {
            "token": token,
            "action": action,
            "mission_id": mission_id,
            "resource": "ontology"
        }
    }
    async with httpx.AsyncClient(timeout=2.0) as client:
        resp = await client.post("http://opa:8181/v1/data/artemis/authz/allow", json=payload)
        allowed = resp.json().get("result", False)
        if not allowed:
            raise HTTPException(status_code=403, detail="Access denied by policy")

@app.post("/v1/ontology/query")
async def ontology_query(req: QueryRequest, authorization: str = Header(...)):
    await opa_authorize(authorization, "ontology:query", req.mission_id)
    return {"status": "accepted", "trace_id": "trc_123", "result_ref": "job_456"}
```

### 7.2 Agent workflow state machine (Python)

```python
from enum import Enum
from dataclasses import dataclass

class State(str, Enum):
    INGESTED = "INGESTED"
    TRIAGED = "TRIAGED"
    ENRICHED = "ENRICHED"
    CORRELATED = "CORRELATED"
    RECOMMENDED = "RECOMMENDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"

@dataclass
class WorkflowContext:
    alert_id: str
    mission_id: str
    state: State
    recommendation: dict | None = None

class ArtemisWorkflow:
    def run(self, ctx: WorkflowContext) -> WorkflowContext:
        ctx.state = State.TRIAGED
        ctx = self.enrich(ctx)
        ctx = self.correlate(ctx)
        ctx = self.recommend(ctx)
        ctx.state = State.PENDING_APPROVAL
        return ctx

    def enrich(self, ctx):
        ctx.state = State.ENRICHED
        return ctx

    def correlate(self, ctx):
        ctx.state = State.CORRELATED
        return ctx

    def recommend(self, ctx):
        ctx.state = State.RECOMMENDED
        ctx.recommendation = {"action": "Open surveillance case", "confidence": 0.82}
        return ctx
```

### 7.3 Operator feedback -> eval dataset builder (Python)

```python
import pandas as pd

def build_eval_rows(agent_traces: pd.DataFrame, corrections: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    merged = agent_traces.merge(corrections, on="trace_id", how="left").merge(outcomes, on="case_id", how="left")
    merged["quality_label"] = merged.apply(
        lambda r: "good" if r["accepted"] and r["outcome"] == "true_positive" else "bad", axis=1
    )
    merged["latency_ok"] = merged["latency_ms"] < 2500
    return merged[["trace_id", "prompt_version", "workflow_version", "quality_label", "latency_ok"]]
```

### 7.4 Prompt/version governance policy (Rego)

```rego
package artemis.changecontrol

default allow = false

allow if {
  input.change.type == "prompt_update"
  input.change.risk_score < 0.35
  input.change.eval.precision_delta >= 0
  input.change.eval.recall_delta >= 0
  input.change.approvals.security == true
  input.change.approvals.ops == true
}
```

### 7.5 A/B prompt experiment orchestrator (Python)

```python
from random import random

def route_prompt_variant(entity_risk: float) -> str:
    if entity_risk > 0.8:
        return "prompt_v_stable"  # no experiments for high-risk ops
    return "prompt_v_candidate" if random() < 0.2 else "prompt_v_stable"
```

## 8) Scenario Walkthrough (Cinematic + Technical)

1. **00:00:03 UTC**: SIGINT event enters `intel.raw` with device and geolocation markers.
2. **00:00:05**: TriageAgent scores severity 0.87 and maps to Mission `M-447`.
3. **00:00:07**: EnrichmentAgent joins Foundry ontology; identifies device linked to Person `P-1029` via prior co-travel relation.
4. **00:00:09**: CorrelationAgent detects pattern match to prior smuggling route; confidence rises to 0.81.
5. **00:00:11**: RecommendationAgent proposes: "Open priority case + task drone recon in sector Q9".
6. **00:00:12**: ApprovalGateAgent packages evidence, policy references, confidence bands, and sends to commander queue.
7. **00:00:20**: Commander rejects drone recon, approves case opening only, adds note: "weather low visibility".
8. **00:00:25**: System executes approved action, logs rejected action rationale.
9. **+24h**: Outcome marked true-positive; operator note indicates weather context was decisive.
10. **Nightly self-improvement loop**:
    - Builds eval row with rejection rationale feature (`weather_visibility_low`).
    - Candidate workflow update proposes weather-gated recommendation rule.
    - Replay improves precision +2.1%, latency +0.0%, no recall loss.
    - Human review board approves.
    - Apollo canary at 10% missions; no regressions after 48h.
    - Promote to stable; provenance + policy decisions recorded immutably.

## 9) “Gets Better” Metrics and Guardrails
- **Quality**: precision@k, recall, false-alarm rate, missed-event rate.
- **Speed**: p50/p95 end-to-end decision latency.
- **Human trust**: acceptance rate, override rate, confidence calibration error.
- **Mission impact**: time-to-action, action effectiveness score.

Guardrails:
- No autonomous objective rewriting.
- No direct operational execution without human approval token.
- Any self-upgrade requires passing eval gates + signed approvals + rollback plan.
