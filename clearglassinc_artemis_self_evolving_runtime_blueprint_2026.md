# ClearGlassInc Artemis — Self-Evolving AI Intelligence Platform (Gotham + Foundry + AIP + Apollo)

## System Architecture

### 1) End-to-End Layered Architecture

```text
[Web Command Surface]
  └─ Next.js/React + TypeScript + WebSocket Mission Feed + Policy UX
        ↓
[API Gateway + BFF]
  └─ FastAPI gateway, request shaping, auth context propagation
        ↓
[Domain Services]
  ├─ Case Service (case lifecycle)
  ├─ Entity Service (ontology read/write)
  ├─ Alert Service (stream triage)
  ├─ Action Service (approval + execution)
  └─ Eval Service (self-improvement loop)
        ↓
[Event + Streaming Backbone]
  └─ Kafka / Foundry streaming datasets / mission event topics
        ↓
[Data + Ontology]
  ├─ Foundry pipelines + ontology objects + lineage
  ├─ Gotham operational graph and investigation views
  ├─ Lakehouse (Parquet/Iceberg) + Warehouse marts
  └─ Vector + lexical retrieval indexes
        ↓
[AI Orchestration (AIP)]
  ├─ Copilot runtime (analyst/commander)
  ├─ Multi-agent workflows
  ├─ Tool registry + policy wrappers
  ├─ Model router + prompt registry
  └─ Eval harness + improvement proposals
        ↓
[Policy + Governance]
  ├─ OPA/Rego policy-as-code
  ├─ ABAC/RBAC need-to-know
  ├─ coalition boundary controls
  └─ approval gates + immutable audit
        ↓
[Deployment + Runtime (Apollo)]
  ├─ ring deployments, canaries
  ├─ secure config and secrets
  ├─ rollback orchestration
  └─ runtime controls + kill switches
```

## Data and Ontology

### 2) Core Ontology Objects

- **Entity**: person, org, device, account, asset, indicator.
- **Event**: alert, telemetry point, case update, operator action.
- **Case**: mission container with status and priority.
- **Hypothesis**: analyst/AI claim with confidence and evidence.
- **ActionProposal**: recommended response requiring checks.
- **ApprovalDecision**: approve/reject with operator rationale.
- **Outcome**: post-action measured result.

### 3) Relationship Model

- `Entity --observed_in--> Event`
- `Event --contributes_to--> Case`
- `Hypothesis --supported_by--> Evidence`
- `ActionProposal --derived_from--> Hypothesis`
- `ApprovalDecision --applies_to--> ActionProposal`
- `Outcome --evaluates--> ActionProposal`

### 4) Required Metadata

- `confidence_score` (0..1)
- `lineage` (`source_system`, `pipeline_id`, `transform_id`, `model_version`)
- `temporal_state` (`valid_from`, `valid_to`, `observed_at`, `ingested_at`)
- `mission_context` (`operation_id`, `region`, `classification`)
- `policy_scope` (`coalition`, `compartment`, `need_to_know_tags`)

### 5) Ontology-Driven SQL View

```sql
CREATE VIEW mission_case_priority AS
SELECT
  c.case_id,
  c.operation_id,
  MAX(e.severity) AS max_severity,
  AVG(h.confidence_score) AS avg_hypothesis_conf,
  SUM(CASE WHEN a.status = 'pending_approval' THEN 1 ELSE 0 END) AS pending_actions,
  MAX(o.mission_impact_score) AS latest_impact,
  MAX(c.updated_at) AS last_updated
FROM case_fact c
LEFT JOIN event_fact e ON e.case_id = c.case_id
LEFT JOIN hypothesis_fact h ON h.case_id = c.case_id
LEFT JOIN action_fact a ON a.case_id = c.case_id
LEFT JOIN outcome_fact o ON o.case_id = c.case_id
GROUP BY c.case_id, c.operation_id;
```

## AI and Agent Design

### 6) Agent Roles (AIP)

- **Triage Agent**: classifies urgency, de-duplicates alerts.
- **Enrichment Agent**: pulls external/internal context.
- **Correlation Agent**: entity graph joins + hypothesis generation.
- **Recommendation Agent**: proposes ranked actions.
- **Summary Agent**: commander-ready briefs.
- **Execution Agent**: prepares action package but cannot execute without approval.

### 7) Tool-Use Contract

```python
from pydantic import BaseModel, Field
from typing import Literal, List

class ToolRequest(BaseModel):
    tool_name: Literal[
        "query_ontology", "open_case", "create_action_proposal",
        "prepare_brief", "execute_playbook"
    ]
    justification: str = Field(min_length=15)
    case_id: str
    requires_approval: bool = True

class ToolResult(BaseModel):
    status: Literal["ok", "blocked", "error"]
    evidence_refs: List[str]
    policy_decision_id: str | None = None
```

### 8) Approval Gate Pattern

```python
from enum import Enum

class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

APPROVAL_REQUIRED = {RiskTier.MEDIUM, RiskTier.HIGH, RiskTier.CRITICAL}

def require_human_approval(risk_tier: RiskTier, action_type: str) -> bool:
    always_sensitive = {"network_isolation", "credential_revocation", "external_notification"}
    return risk_tier in APPROVAL_REQUIRED or action_type in always_sensitive
```

## Self-Improvement Loop

### 9) Closed-Loop Learning Pipeline

1. Capture telemetry: prompts, model choice, tool calls, operator edits, final outcomes.
2. Generate eval records per workflow run.
3. Compute regressions and drift signals.
4. Produce **improvement proposals** (prompt/workflow/router updates).
5. Route proposals through review board + policy checks.
6. Canaried deployment through Apollo rings.
7. Compare treatment/control; auto-rollback if thresholds fail.

### 10) Feedback Event Schema

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional

class FeedbackEvent(BaseModel):
    event_id: str
    timestamp: datetime
    operation_id: str
    case_id: str
    actor_type: Literal["operator", "agent", "system"]
    signal_type: Literal[
        "operator_correction", "approval_decision", "prompt_edit",
        "alert_outcome", "mission_result", "latency_observation"
    ]
    payload: dict
    model_version: Optional[str] = None
    workflow_version: Optional[str] = None
```

### 11) Eval Job Skeleton (Python)

```python
from dataclasses import dataclass
from statistics import mean

@dataclass
class EvalMetrics:
    precision: float
    recall: float
    p95_latency_ms: int
    operator_override_rate: float
    trust_score: float


def evaluate_batch(records: list[dict]) -> EvalMetrics:
    precision = mean(r["precision"] for r in records)
    recall = mean(r["recall"] for r in records)
    p95 = sorted(r["latency_ms"] for r in records)[int(len(records)*0.95)-1]
    overrides = mean(r["operator_overrode"] for r in records)
    trust = 1.0 - overrides
    return EvalMetrics(precision, recall, p95, overrides, trust)


def gate_for_promotion(m: EvalMetrics) -> bool:
    return (
        m.precision >= 0.92 and
        m.recall >= 0.86 and
        m.p95_latency_ms <= 1800 and
        m.operator_override_rate <= 0.12
    )
```

### 12) Prompt + Workflow Versioning

```yaml
proposal_id: imp-2026-04-26-0091
target:
  prompt_id: triage_prompt_v18
  workflow_id: mission_triage_flow_v11
changes:
  - type: prompt_patch
    summary: "tighten false positive suppression for low-confidence IOC bursts"
  - type: router_rule
    summary: "route high-ambiguity cases to high-reasoning model"
risk_assessment:
  blast_radius: "low"
  rollback_plan: "apollo rollback to ring-1 stable"
approvals:
  required_roles: ["mission_commander", "ai_governance_officer"]
status: pending_review
```

## Full-Stack Implementation

### 13) Web UI (TypeScript)

```ts
// app/api/cases/[caseId]/recommendation/route.ts
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest, { params }: { params: { caseId: string } }) {
  const body = await req.json();
  const res = await fetch(`${process.env.GATEWAY_URL}/v1/cases/${params.caseId}/recommend`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": req.headers.get("Authorization") || "",
      "x-mission-context": req.headers.get("x-mission-context") || "",
    },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
```

### 14) API Gateway (FastAPI)

```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ClearGlassInc Artemis Gateway")

class RecommendRequest(BaseModel):
    mission_id: str
    objective: str

@app.post("/v1/cases/{case_id}/recommend")
def recommend(case_id: str, req: RecommendRequest, user=Depends(...)):
    if not user.can_read_case(case_id):
        raise HTTPException(403, "need-to-know violation")

    # call AIP orchestration service
    recommendation = orchestrator.recommend(case_id=case_id, mission_id=req.mission_id, objective=req.objective, actor=user)
    return recommendation
```

### 15) Event Handler (Streaming)

```python
def handle_alert_event(event: dict):
    case_id = case_service.route_or_create_case(event)
    graph_service.upsert_entities(event)
    rec = orchestrator.triage(case_id=case_id, event=event)
    action_service.record_recommendation(case_id, rec)
    eval_service.log_inference(event=event, recommendation=rec)
```

### 16) Workflow State Machine

```python
from transitions import Machine

states = [
  "ingested", "triaged", "enriched", "recommended",
  "pending_approval", "approved", "executed", "closed", "rolled_back"
]

class CaseWorkflow:
    def __init__(self):
        self.machine = Machine(model=self, states=states, initial="ingested")
        self.machine.add_transition("triage", "ingested", "triaged")
        self.machine.add_transition("enrich", "triaged", "enriched")
        self.machine.add_transition("recommend", "enriched", "recommended")
        self.machine.add_transition("submit", "recommended", "pending_approval")
        self.machine.add_transition("approve", "pending_approval", "approved")
        self.machine.add_transition("execute", "approved", "executed")
        self.machine.add_transition("close", ["executed", "rolled_back"], "closed")
        self.machine.add_transition("rollback", "executed", "rolled_back")
```

## Security and Governance

### 17) Policy-as-Code (Rego)

```rego
package clearglass.authz

default allow = false

allow {
  input.user.clearance >= input.resource.classification
  input.user.coalition == input.resource.coalition
  input.action == "read"
}

allow {
  input.action == "execute"
  input.request.approval_token_valid == true
  input.request.risk_tier != "critical"
}
```

### 18) Mandatory Governance Controls

- Need-to-know ABAC + RBAC overlay.
- Row/column/entity-level controls in Foundry datasets.
- Coalition boundary tags enforced at query and tool layers.
- Zero-trust service identity (mTLS, workload identities).
- Immutable provenance logs (append-only, signed hashes).
- Model governance (allowed model list, eval thresholds, kill switch).
- Prompt governance (registry, owners, diff review, approval history).

## Code Examples

### 19) Safe Model Router

```python
class ModelRouter:
    def __init__(self, policy, registry):
        self.policy = policy
        self.registry = registry

    def choose(self, task_type: str, sensitivity: str, ambiguity: float) -> str:
        candidates = self.registry.allowed_models(task_type=task_type, sensitivity=sensitivity)
        ranked = sorted(candidates, key=lambda m: (m.cost_score, -m.quality_score))
        if ambiguity > 0.7:
            ranked = sorted(candidates, key=lambda m: (-m.reasoning_score, m.latency_ms))
        model_id = ranked[0].model_id
        self.policy.assert_model_allowed(model_id, sensitivity)
        return model_id
```

### 20) Drift Detection

```python
def detect_drift(current: dict, baseline: dict) -> dict:
    deltas = {k: current[k] - baseline[k] for k in baseline}
    drift = {
      "precision_drop": deltas.get("precision", 0) < -0.03,
      "latency_increase": deltas.get("p95_latency_ms", 0) > 300,
      "override_spike": deltas.get("operator_override_rate", 0) > 0.05,
    }
    drift["any"] = any(drift.values())
    return drift
```

## Scenario Walkthrough

### 21) Live Event to Learned Improvement

1. **Ingress**: A suspicious identity pivot enters Foundry streaming ingest and is linked to an active operation.
2. **Triage**: Triage Agent scores it high-risk due to identity + endpoint + geo anomaly correlation.
3. **Recommendation**: Recommendation Agent proposes temporary token revocation + segmented host isolation.
4. **Policy Check**: Rego policy marks action as high-impact; execution requires operator approval.
5. **Human Decision**: Commander approves revocation, rejects isolation, and edits rationale.
6. **Execution**: Approved action runs; outcome shows attack contained with no service outage.
7. **Learning Capture**: System stores approval split, rationale text, and mission outcome as eval signals.
8. **Improvement Proposal**: Eval pipeline suggests prompt patch: lower weight on isolation if business continuity risk is high.
9. **Governed Release**: Proposal reviewed and canaried via Apollo ring-1.
10. **Validation**: A/B shows equal containment with fewer operator overrides.
11. **Promotion**: Version promoted to stable; full audit retained.

This is how **ClearGlassInc Artemis** gets better continuously—through operator-guided optimization inside strict governance guardrails.
