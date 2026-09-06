# ClearGlassInc Artemis — Self-Evolving AI Intelligence Platform (Palantir Gotham + Foundry + AIP + Apollo)

## 1) System Architecture

### 1.1 Layered Reference Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                                Web Frontend                                │
│ React/Next.js + Map UI + Case Workbench + Copilot Panels + Evals Console  │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ mTLS + OIDC + ABAC claims
┌───────────────▼─────────────────────────────────────────────────────────────┐
│                              API Gateway Layer                              │
│ GraphQL Federation + REST + WebSocket + Rate-limit + Schema Validation     │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────────────────────┐
│                         Backend Domain Services                              │
│ CaseSvc │ EntitySvc │ MissionSvc │ AlertSvc │ FeedbackSvc │ PolicySvc       │
│ PromptRegistrySvc │ EvalSvc │ WorkflowOrchestrator │ FeatureStoreSvc        │
└───────┬───────────────┬─────────────────────────────┬───────────────────────┘
        │               │                             │
┌───────▼──────┐ ┌──────▼──────────────────┐ ┌───────▼───────────────────────┐
│ Event Bus    │ │ Search/Retrieval Layer  │ │ Model Router/Inference Layer   │
│ Kafka/Pulsar │ │ OpenSearch + Vector DB  │ │ AIP agents + policy-aware LLM  │
└───────┬──────┘ └──────────┬──────────────┘ └───────┬───────────────────────┘
        │                   │                        │
┌───────▼───────────────────▼────────────────────────▼────────────────────────┐
│ Data Layer (Foundry): Ontology, Data Pipelines, Lakehouse, Lineage, ACLs   │
└───────┬──────────────────────────────────────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────────────────────────────────────┐
│ Operations Layer (Apollo): deploy, canary, rollback, runtime policy control │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Platform Responsibilities by Palantir Product
- **Gotham**: mission operations UI, case management, link analysis, entity tracking, watchlists.
- **Foundry**: data ingestion, ontology, transforms, model feature pipelines, data governance.
- **AIP**: copilots, multi-agent orchestration, tool calling, eval harnesses, guardrailed automation.
- **Apollo**: secure rollout, staged promotion, rollback, runtime configuration and policy enforcement.

---

## 2) Data and Ontology

### 2.1 Core Ontology Objects

```sql
-- canonical entity table (logical schema representation)
CREATE TABLE ontology_entity (
  entity_id           UUID PRIMARY KEY,
  entity_type         TEXT NOT NULL,          -- Person, Org, Device, Asset, Event, Location
  canonical_name      TEXT,
  confidence_score    DOUBLE PRECISION,
  mission_context_id  UUID,
  classification      TEXT,                   -- UNCLASS/SECRET/etc
  coalition_tags      TEXT[],                 -- e.g., ["FVEY", "NATO"]
  valid_time_start    TIMESTAMP,
  valid_time_end      TIMESTAMP,
  ingest_time         TIMESTAMP NOT NULL,
  lineage_ref         TEXT NOT NULL,          -- pointer to Foundry lineage/provenance artifact
  version             BIGINT NOT NULL
);

CREATE TABLE ontology_relationship (
  rel_id              UUID PRIMARY KEY,
  src_entity_id       UUID NOT NULL,
  dst_entity_id       UUID NOT NULL,
  rel_type            TEXT NOT NULL,          -- COMMUNICATED_WITH, LOCATED_AT, FUNDED_BY
  confidence_score    DOUBLE PRECISION,
  evidence_refs       TEXT[],
  mission_context_id  UUID,
  valid_time_start    TIMESTAMP,
  valid_time_end      TIMESTAMP,
  ingest_time         TIMESTAMP NOT NULL,
  version             BIGINT NOT NULL
);
```

### 2.2 Confidence, Lineage, Temporal State
- **Confidence** is attached at both entity and relationship levels, derived from source reliability, corroboration count, and model certainty.
- **Lineage** references Foundry pipeline/artifact IDs for traceability and replay.
- **Temporal state** uses bi-temporal fields: valid-time (real world) + ingest-time (system).

### 2.3 Ontology-Driven Agent Behavior
- Agent tool selection is restricted by ontology class permissions.
- Entity graph neighborhoods seed retrieval context for copilots.
- Mission context scoping constrains which entities are visible and actionable.

---

## 3) AI and Agent Design

### 3.1 Copilots
- **Analyst Copilot**: explain evidence chains, draft intelligence summaries, recommend next queries.
- **Commander Copilot**: risk/impact deltas, COA (course of action) comparisons, approval-ready action packages.

### 3.2 Multi-Agent Workflow (AIP)
1. **Triage Agent**: classifies incoming event severity.
2. **Enrichment Agent**: gathers entity context from Foundry ontology + external feeds.
3. **Correlation Agent**: links event to prior cases and graph motifs.
4. **Summarization Agent**: builds concise intel product.
5. **Recommendation Agent**: proposes actions with confidence + policy citations.
6. **Approval Gate Agent**: blocks execution until authorized human approves.

### 3.3 Operational Gates
- Any action touching real-world ops must pass:
  - policy-as-code check,
  - mission role check,
  - two-person integrity for high-impact actions,
  - immutable audit write.

---

## 4) Self-Improvement Loop (Safe)

### 4.1 Signals Captured
- Operator feedback (thumbs up/down + freeform rationale).
- Corrections (entity merges/splits, relationship edits).
- Query logs and retrieval hits.
- Alert outcomes (true/false positive).
- Mission outcomes (success, delay, collateral risk, escalation).

### 4.2 Improvement Pipeline

```python
# python: self_improvement/pipeline.py
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class CandidateChange:
    change_id: str
    kind: str  # prompt|workflow|router|heuristic
    proposed_artifact_uri: str
    expected_gain: Dict[str, float]
    risk_score: float


def generate_candidates(signals: List[dict]) -> List[CandidateChange]:
    # 1) mine recurrent failures
    # 2) map failure mode -> change templates
    # 3) produce candidates with estimated benefit
    return []


def gate_candidate(c: CandidateChange, policy_client) -> bool:
    if c.risk_score > 0.35:
        return False
    return policy_client.is_change_type_allowed(c.kind)


def promote_if_passed(eval_result: dict, apollo_client, artifact_uri: str):
    if eval_result["precision_delta"] >= 0.03 and eval_result["latency_delta_ms"] <= 50:
        apollo_client.promote_canary(artifact_uri)
    else:
        apollo_client.rollback(artifact_uri)
```

### 4.3 Versioning + Rollback
- Prompt/workflow/model-router artifacts are semantically versioned (`x.y.z`).
- Every deployment canary-tested in Apollo environment rings.
- Auto rollback on threshold breach (precision drop, policy violations, latency regression).

### 4.4 Drift Detection
- Population drift: embedding centroid shifts.
- Concept drift: precision/recall degradation over labeled mission outcomes.
- Behavior drift: agent action distribution shifts outside approved envelope.

---

## 5) Full-Stack Implementation Blueprint

### 5.1 Frontend (TypeScript / Next.js)
```tsx
// app/cases/[id]/copilot-panel.tsx
export function CopilotPanel({ caseId }: { caseId: string }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);

  const ask = async () => {
    const res = await fetch(`/api/copilot/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ caseId, question })
    });
    const data = await res.json();
    setAnswer(data.answer);
  };

  return (<div>{/* secure case-scoped copilot UX */}</div>);
}
```

### 5.2 API Gateway Contract
```yaml
POST /copilot/query
request:
  caseId: string
  prompt: string
response:
  answer: string
  citations: [string]
  confidence: number
  requiresApproval: boolean
```

### 5.3 Backend Service (Python / FastAPI)
```python
from fastapi import FastAPI, Depends
from pydantic import BaseModel

app = FastAPI()

class CopilotQuery(BaseModel):
    case_id: str
    prompt: str

@app.post("/copilot/query")
def copilot_query(req: CopilotQuery, user=Depends(get_user_ctx)):
    assert_policy("READ_CASE", user, req.case_id)
    ctx = retrieve_case_context(req.case_id, user)
    plan = run_agent_workflow(prompt=req.prompt, context=ctx, user=user)
    return {
        "answer": plan.answer,
        "citations": plan.citations,
        "confidence": plan.confidence,
        "requiresApproval": plan.requires_approval,
    }
```

### 5.4 Event-Driven Processing
```python
# kafka consumer skeleton
def on_event(event: dict):
    normalized = normalize_event(event)
    entities = extract_entities(normalized)
    upsert_ontology(entities)
    score = triage_agent.score(normalized)
    publish("intel.triaged", {"event_id": event["id"], "score": score})
```

### 5.5 Workflow State Machine
```python
from enum import Enum

class IntelState(str, Enum):
    INGESTED="INGESTED"
    TRIAGED="TRIAGED"
    ENRICHED="ENRICHED"
    CORRELATED="CORRELATED"
    RECOMMENDED="RECOMMENDED"
    PENDING_APPROVAL="PENDING_APPROVAL"
    EXECUTED="EXECUTED"
    CLOSED="CLOSED"
```

---

## 6) Security and Governance

### 6.1 Access Model
- OIDC identity + short-lived workload identities.
- ABAC + RBAC hybrid: mission, clearance, coalition, need-to-know.
- Row/column/entity-level masking and denial-by-default.

### 6.2 Zero-Trust Runtime
- mTLS everywhere.
- Signed workloads and verified provenance.
- Isolated execution sandboxes for tool-using agents.

### 6.3 Governance Artifacts
- Prompt registry with approval metadata.
- Model cards + risk tiering.
- Policy-as-code for actions, routes, and data access.
- Immutable append-only audit ledger (hash-chained records).

---

## 7) Code Examples (Critical Paths)

### 7.1 Policy Check
```python
def assert_policy(action: str, user_ctx: dict, resource_id: str):
    decision = opa_client.evaluate(
        "artemis.authz.allow",
        {
            "action": action,
            "user": user_ctx,
            "resource": load_resource_attrs(resource_id),
        },
    )
    if not decision["allow"]:
        raise PermissionError(decision.get("reason", "denied"))
```

### 7.2 Model Router
```python
def route_model(task_type: str, sensitivity: str, latency_budget_ms: int):
    if sensitivity == "HIGH":
        return "onprem-validated-llm"
    if task_type == "summarization" and latency_budget_ms < 800:
        return "small-fast-llm"
    return "general-reasoning-llm"
```

### 7.3 Eval Pipeline SQL
```sql
INSERT INTO eval_runs(run_id, artifact_uri, metric_precision, metric_recall, latency_p95_ms)
SELECT
  gen_random_uuid(),
  :artifact_uri,
  AVG(CASE WHEN pred = label AND pred = 1 THEN 1 ELSE 0 END)::float AS precision,
  AVG(CASE WHEN pred = label AND label = 1 THEN 1 ELSE 0 END)::float AS recall,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS latency_p95
FROM eval_samples
WHERE eval_set = :eval_set;
```

---

## 8) Scenario Walkthrough (Cinematic + Technical)

1. **Live event arrives**: maritime AIS anomaly + SIGINT cue enters ingest topic.
2. **Triage agent** flags high severity (0.91) due to pattern overlap with prior smuggling topology.
3. **Enrichment agent** adds vessel ownership shell-org links, recent transponder gaps, and coalition watchlist matches.
4. **Correlation agent** maps event to an active Gotham case and links 3 known intermediaries.
5. **Recommendation agent** proposes: “Open priority case update + notify maritime task group + request ISR retask.”
6. **Approval gate** marks ISR retask as operationally significant; commander approval required.
7. **Operator rejects ISR retask** but approves case update and notification, citing weather constraints.
8. **Outcome capture** stores rejection rationale as structured feedback.
9. **Self-improvement job** detects recurring weather-related rejection pattern and proposes prompt change:
   - add environmental feasibility check before proposing ISR retask.
10. **Eval harness** runs A/B on 30-day replay; reduces rejected recommendations by 18% without precision loss.
11. **Human governance board** approves change.
12. **Apollo canary deploy** to one mission cell; post-canary metrics stable, then global promotion.

This is how ClearGlassInc Artemis continuously improves at machine speed while maintaining strict human control.
