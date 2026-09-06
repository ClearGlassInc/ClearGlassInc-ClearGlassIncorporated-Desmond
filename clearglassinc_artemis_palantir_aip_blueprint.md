# ClearGlassInc Artemis — Self-Evolving Intelligence Platform Blueprint

## System Architecture

### 1. Reference Stack
- **Gotham**: operational intelligence, case management, entity resolution, mission graphing.
- **Foundry**: ingestion pipelines, ontology, data products, transforms, policy-bound application logic.
- **AIP**: copilots, agents, prompt/workflow evaluations, human-in-the-loop orchestration.
- **Apollo**: deployment strategy, phased rollout, rollback orchestration, runtime controls.

### 2. End-to-End Layers
1. **Frontend layer** (TypeScript/React)
   - Analyst and commander workspaces.
   - Live intel map, timeline, entity graph, case queue, recommendation panel.
2. **API and orchestration layer** (Python/FastAPI)
   - Mission API gateway.
   - AuthN/AuthZ context injection.
   - Routing to Foundry data products + AIP agent service.
3. **Data layer**
   - Stream ingestion (Kafka/PubSub), batch ETL, lakehouse model.
   - Feature store and retrieval index for operational context.
4. **Ontology layer (Foundry Ontology)**
   - Entities: Person, Device, Location, Event, ThreatSignal, Mission, Case.
   - Relationships: observed_at, linked_to, owns, communicates_with, part_of_case.
5. **AI orchestration layer (AIP)**
   - Model router (task-aware, policy-aware).
   - Multi-agent mission workflow engine.
   - Evaluation harness and promotion gates.
6. **Policy layer**
   - OPA/Rego + Foundry policy actions.
   - Need-to-know checks, coalition partition controls, data minimization.
7. **Observability layer**
   - Telemetry, eval scores, latency budgets, mission outcomes, drift alarms.
8. **Deployment layer (Apollo)**
   - Environment promotion (dev → staging → mission-prod).
   - Canary rollout, auto rollback, signed artifact policy.

### 3. Runtime Topology
- Region-separated runtimes with cross-domain guards.
- Multi-tenant compartments with coalition-aware data boundaries.
- Command plane isolated from data plane and model-serving plane.

---

## Data and Ontology

### 1. Canonical Entity Model
```sql
CREATE TABLE ontology_entity (
  entity_id UUID PRIMARY KEY,
  entity_type VARCHAR(64) NOT NULL,
  canonical_name TEXT,
  confidence_score NUMERIC(5,4) NOT NULL,
  source_system VARCHAR(128) NOT NULL,
  mission_id UUID,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  valid_from TIMESTAMP,
  valid_to TIMESTAMP,
  classification VARCHAR(32) NOT NULL,
  lineage_hash TEXT NOT NULL
);

CREATE TABLE ontology_relation (
  relation_id UUID PRIMARY KEY,
  src_entity_id UUID NOT NULL,
  dst_entity_id UUID NOT NULL,
  relation_type VARCHAR(64) NOT NULL,
  confidence_score NUMERIC(5,4) NOT NULL,
  evidence_ref TEXT,
  created_at TIMESTAMP NOT NULL,
  valid_from TIMESTAMP,
  valid_to TIMESTAMP,
  mission_id UUID,
  policy_tag VARCHAR(64),
  FOREIGN KEY (src_entity_id) REFERENCES ontology_entity(entity_id),
  FOREIGN KEY (dst_entity_id) REFERENCES ontology_entity(entity_id)
);
```

### 2. Ontology Behavior Contracts
- **Confidence-aware reasoning**: agents must propagate uncertainty with every derived assertion.
- **Temporal state**: all assertions are bitemporal (`valid_*`, `observed_*`).
- **Lineage**: every derived object links to source evidence hash and transform version.
- **Mission context binding**: no cross-mission joins without explicit policy grant.

### 3. Permission Projection
Entity visibility = intersection of:
1. user clearance,
2. coalition membership,
3. mission assignment,
4. jurisdiction rule,
5. purpose-of-use declaration.

---

## AI and Agent Design

### 1. Copilot Roles
- **Analyst Copilot**: triage support, evidence summarization, query acceleration.
- **Commander Copilot**: mission posture snapshots, decision package generation.
- **Compliance Copilot**: policy explanation, audit trace assembly.

### 2. Multi-Agent Workflow
Agents in pipeline:
1. **Triage Agent** → classify event severity.
2. **Enrichment Agent** → pull entity context and prior incidents.
3. **Correlation Agent** → connect graph signals to mission threats.
4. **Recommendation Agent** → generate action options with risk tiers.
5. **Narrative Agent** → produce briefing output for command.

### 3. Tool-Using Agent Interface (Python)
```python
from pydantic import BaseModel
from typing import Literal, Any

class ToolCall(BaseModel):
    tool: Literal["query_ontology", "open_case", "build_action_package", "notify_watchfloor"]
    args: dict[str, Any]

class AgentDecision(BaseModel):
    rationale: str
    confidence: float
    recommended_action: str
    requires_human_approval: bool
    tool_calls: list[ToolCall]
```

### 4. Operational Approval Gates
- Any action with mission impact (`open_case`, `notify`, `task_force_dispatch`) requires human confirmation.
- Autonomy is limited to non-destructive actions (enrichment, drafts, tagging).

---

## Self-Improvement Loop

### 1. Signal Collection
Inputs captured continuously:
- operator edits and overrides,
- acceptance/rejection decisions,
- alert precision outcomes,
- mission result quality,
- latency + cost telemetry,
- post-incident review labels.

### 2. Improvement Pipeline
```python
class ImprovementCandidate(BaseModel):
    candidate_id: str
    change_type: str  # prompt|workflow|router|heuristic
    baseline_version: str
    proposed_version: str
    expected_gain: float
    risk_score: float


def generate_candidates(feedback_events):
    # 1) Cluster failure patterns
    # 2) Synthesize proposals
    # 3) Build eval packs
    return []
```

### 3. Evaluation and Promotion
1. Build offline replay dataset from immutable logs.
2. Run benchmark evals (precision, recall, false positive rate, latency p95).
3. Run policy evals (access violation count must be zero).
4. Launch A/B in shadow mode.
5. Request human review and approval.
6. Promote via Apollo canary rollout.

### 4. Safe Rollback Controls
- Versioned prompts/workflows/models (`semver + signed manifest`).
- One-click rollback in Apollo to last trusted release.
- Automatic rollback on metric breach (precision drop, latency breach, policy breach).

### 5. Drift Detection
- Data drift: PSI/KL divergence by mission segment.
- Concept drift: degradation in alert quality labels.
- Behavior drift: increase in operator overrides.

---

## Full-Stack Implementation

### 1. Frontend (TypeScript React)
```typescript
export type MissionEvent = {
  id: string;
  severity: "low" | "medium" | "high" | "critical";
  confidence: number;
  missionId: string;
  timestamp: string;
};

export async function fetchMissionQueue(token: string): Promise<MissionEvent[]> {
  const res = await fetch("/api/v1/missions/queue", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("queue_fetch_failed");
  return res.json();
}
```

### 2. API Gateway (FastAPI)
```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ClearGlassInc Artemis Gateway")

class DecisionRequest(BaseModel):
    event_id: str
    mission_id: str

@app.post("/api/v1/decision")
def generate_decision(req: DecisionRequest, user=Depends(auth_context)):
    if not policy_engine.can_access(user, req.mission_id):
        raise HTTPException(status_code=403, detail="mission_access_denied")
    return agent_orchestrator.run(req.event_id, req.mission_id, user)
```

### 3. Event Handler
```python
def on_intel_event(event: dict) -> None:
    normalized = normalizer.normalize(event)
    ontology_writer.upsert_entities(normalized.entities)
    workflow_bus.publish("intel.triage.requested", {
        "event_id": normalized.event_id,
        "mission_id": normalized.mission_id,
        "classification": normalized.classification
    })
```

### 4. Ontology-Driven Query
```python
def get_related_entities(entity_id: str, mission_id: str) -> list[dict]:
    query = """
    SELECT e2.entity_id, e2.entity_type, r.relation_type, r.confidence_score
    FROM ontology_relation r
    JOIN ontology_entity e2 ON r.dst_entity_id = e2.entity_id
    WHERE r.src_entity_id = :entity_id
      AND r.mission_id = :mission_id
      AND e2.classification <= :user_classification
    ORDER BY r.confidence_score DESC
    LIMIT 200
    """
    return db.fetch_all(query, {
        "entity_id": entity_id,
        "mission_id": mission_id,
        "user_classification": auth_context.current().classification_level,
    })
```

### 5. Workflow State Machine
```python
from enum import Enum

class CaseState(str, Enum):
    NEW = "new"
    TRIAGED = "triaged"
    ENRICHED = "enriched"
    RECOMMENDED = "recommended"
    PENDING_APPROVAL = "pending_approval"
    EXECUTED = "executed"
    CLOSED = "closed"

ALLOWED = {
    CaseState.NEW: {CaseState.TRIAGED},
    CaseState.TRIAGED: {CaseState.ENRICHED},
    CaseState.ENRICHED: {CaseState.RECOMMENDED},
    CaseState.RECOMMENDED: {CaseState.PENDING_APPROVAL},
    CaseState.PENDING_APPROVAL: {CaseState.EXECUTED, CaseState.CLOSED},
}
```

### 6. Policy-as-Code (Rego)
```rego
package artemis.authz

default allow = false

allow {
  input.user.clearance >= input.resource.classification
  input.user.mission_ids[_] == input.resource.mission_id
  input.user.coalition == input.resource.coalition
  input.action != "execute_operational_action"
}

allow {
  input.action == "execute_operational_action"
  input.approval.ticket_status == "approved"
  input.user.role == "commander"
}
```

### 7. Eval Pipeline
```python
def run_eval_suite(candidate_version: str, baseline_version: str) -> dict:
    replay = eval_store.load_replay_dataset("mission_last_30_days")
    baseline = evaluator.run(version=baseline_version, dataset=replay)
    candidate = evaluator.run(version=candidate_version, dataset=replay)

    return {
        "precision_delta": candidate.precision - baseline.precision,
        "recall_delta": candidate.recall - baseline.recall,
        "latency_p95_delta": candidate.latency_p95 - baseline.latency_p95,
        "policy_violations": candidate.policy_violations,
        "operator_acceptance_delta": candidate.acceptance_rate - baseline.acceptance_rate,
    }
```

---

## Security and Governance

### 1. Access and Compartment Controls
- Need-to-know enforced at row/column/entity level.
- Coalition boundary policy gates prevent cross-compartment leakage.
- Purpose binding required for high-sensitivity query execution.

### 2. Zero-Trust Execution
- Mutual TLS, workload identity, short-lived credentials.
- Runtime attestation for agent services.
- No implicit trust between services or environments.

### 3. Immutable Provenance
- Append-only audit ledger for:
  - prompt versions,
  - model routes,
  - agent actions,
  - approvals,
  - data access traces.

### 4. Model and Prompt Governance
- Prompt registry with ownership and review status.
- Model registry with risk class and allowed task scope.
- No promotion to mission production without eval and human signoff.

---

## Code Examples (Additional)

### A. Human Approval Endpoint
```python
@app.post("/api/v1/actions/{action_id}/approve")
def approve_action(action_id: str, user=Depends(auth_context)):
    action = action_repo.get(action_id)
    if user.role not in {"commander", "incident_commander"}:
        raise HTTPException(403, "insufficient_role")
    if action.status != "pending_approval":
        raise HTTPException(409, "invalid_state")

    action_repo.approve(action_id, approver=user.user_id)
    workflow_bus.publish("action.approved", {"action_id": action_id, "approver": user.user_id})
    return {"status": "approved"}
```

### B. Auto-Improvement Proposal Generator
```python
def propose_prompt_refinement(misfires: list[dict]) -> str:
    patterns = failure_miner.extract_patterns(misfires)
    draft = prompt_optimizer.suggest(
        current_prompt=prompt_registry.get("triage_v4"),
        failure_patterns=patterns,
        constraints={"no_scope_expansion": True, "must_preserve_policy_clauses": True},
    )
    return draft
```

---

## Scenario Walkthrough (Live Event)

1. **Live event ingestion**  
   A suspicious beaconing pattern enters via streaming telemetry for Mission M-421.

2. **Automated triage**  
   Triage Agent assigns `high` severity, confidence `0.84`, and opens a draft case.

3. **Enrichment and correlation**  
   Agents pull related entities: device cluster, operator account, prior command-and-control indicator.

4. **Recommendation generated**  
   Recommendation Agent proposes: isolate endpoint segment + rotate privileged tokens.

5. **Human approval gate**  
   Commander reviews evidence graph and approves token rotation, defers segmentation pending additional confirmation.

6. **Execution**  
   Approved action is executed via controlled playbook. Unapproved action remains blocked.

7. **Outcome feedback**  
   Incident closes with confirmed containment and no lateral movement.

8. **Self-improvement cycle**  
   System records that segmented isolation was frequently deferred in similar contexts.  
   Improvement service generates a candidate update to recommendation ranking logic.

9. **Eval and rollout**  
   Candidate runs in shadow mode for 7 days, improves operator acceptance by 11%, keeps precision above threshold, and has zero policy violations.

10. **Promotion**  
    Human reviewer approves. Apollo performs canary rollout to 10% of missions, then full promotion after SLO stability.

This loop enables ClearGlassInc Artemis to get better continuously while preserving strict human authority, policy compliance, and auditable control.
