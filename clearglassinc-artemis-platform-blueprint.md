# ClearGlassInc Artemis — Self-Evolving AI Intelligence Platform Blueprint

**Organization:** ClearGlassInc Artemis  
**Platform stack:** Palantir Gotham, Foundry, AIP, and Apollo  
**Mission class:** secure, coalition-aware, multi-domain, latency-sensitive, audited intelligence operations  
**Design principle:** machine-speed intelligence with human-approved authority boundaries.

> ClearGlassInc Artemis is a self-evolving intelligence platform that fuses operational data, reasons over entity-centric context, orchestrates agentic workflows, and proposes safe upgrades to prompts, workflows, heuristics, model routing, and evaluation policy. It may recommend improvements, but it does not autonomously change mission objectives, access policy, operational rules of engagement, or deployment posture without explicit human approval.

---

## 1. System Architecture

### 1.1 Platform responsibilities

Palantir terminology is used precisely throughout this design:

- **Gotham** is the operational intelligence layer for investigations, entity tracking, link analysis, casework, mission timelines, and commander-facing operational views.
- **Foundry** is the data integration and application layer for pipelines, Ontology objects, transforms, governed data products, operational apps, and business logic.
- **AIP** is the AI operating layer for copilots, tool-using agents, model routing, prompt management, evaluations, and workflow automation against governed data.
- **Apollo** is the secure deployment and runtime control layer for progressive delivery, environment promotion, policy-aware updates, rollback, and operational health.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ClearGlassInc Artemis UI                           │
│  Commander cockpit · Analyst workbench · Case boards · Eval/admin consoles   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────────┐
│                         API Gateway / BFF Layer                              │
│  GraphQL + REST · WebSocket mission feed · auth context · policy decisions   │
└───────────────┬───────────────────────────────┬─────────────────────────────┘
                │                               │
┌───────────────▼───────────────┐   ┌───────────▼─────────────────────────────┐
│       Backend Services         │   │              AIP Orchestration           │
│ Case svc · Alert svc · Mission │   │ Copilots · Agents · Evals · Tool calls  │
│ Feedback svc · Approval svc    │   │ Prompt registry · Model router          │
└───────────────┬───────────────┘   └───────────┬─────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼─────────────────────────────┐
│                              Foundry Layer                                   │
│ Pipelines · Ontology · Code repositories · Functions · Lineage · Apps        │
└───────────────┬───────────────────────────────┬─────────────────────────────┘
                │                               │
┌───────────────▼───────────────┐   ┌───────────▼─────────────────────────────┐
│        Data / Retrieval        │   │                 Gotham                   │
│ Lakehouse · streams · search   │   │ Investigations · entity tracking · maps │
│ vector index · feature store   │   │ link analysis · operational casework    │
└───────────────┬───────────────┘   └───────────┬─────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼─────────────────────────────┐
│                         Policy, Security, Observability                      │
│ ABAC/ReBAC · coalition boundaries · immutable audit · metrics · traces       │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────────┐
│                                  Apollo                                      │
│ Deployment rings · environment promotion · runtime config · rollback         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Full-stack component map

| Layer | Components | Primary outputs |
|---|---|---|
| Frontend | React/Next.js cockpit, map canvas, graph explorer, case timeline, prompt/eval console | mission views, operator decisions, feedback events |
| API | FastAPI gateway, GraphQL federation, WebSocket feed, request signing | normalized secure access to Foundry, Gotham, and AIP |
| Backend | case, alert, feedback, approval, package, mission, policy, eval, and deployment services | operational state transitions and auditable decisions |
| Data | Foundry pipelines, streaming ingestion, lakehouse tables, feature store, vector/search indexes | trusted operational data products |
| Ontology | entity objects, relationships, temporal state, permissions, lineage, confidence | shared semantic model for humans and agents |
| AI | AIP copilots, multi-agent workflows, model router, tool registry, eval harness | grounded recommendations and action packages |
| Policy | OPA/Cedar-style policy, ABAC/ReBAC, classification, compartment checks | allow/deny/require-approval decisions |
| Observability | OpenTelemetry, eval dashboards, model traces, audit ledger, drift monitors | operational health, trust metrics, forensic replay |
| Deployment | Apollo release rings, signed artifacts, progressive rollout, rollback | controlled platform evolution |

---

## 2. Data and Ontology

### 2.1 Ontology design goals

The ClearGlassInc Artemis Ontology is the shared semantic contract between Gotham investigations, Foundry applications, AIP agents, and operator workflows. Every object has provenance, confidence, permissions, temporal validity, and mission context.

### 2.2 Core entity types

```yaml
ontology:
  entities:
    Person:
      keys: [person_id]
      properties: [names, aliases, biometrics_ref, citizenships, roles, risk_score]
    Organization:
      keys: [org_id]
      properties: [legal_name, aliases, jurisdictions, sectors, risk_score]
    Asset:
      keys: [asset_id]
      properties: [asset_type, owner_org_id, location, criticality, cyber_exposure]
    Device:
      keys: [device_id]
      properties: [hostnames, ips, macs, owner, posture, last_seen]
    Location:
      keys: [location_id]
      properties: [geo, address, jurisdiction, confidence]
    Event:
      keys: [event_id]
      properties: [event_type, observed_at, occurred_at, severity, summary]
    Alert:
      keys: [alert_id]
      properties: [source, severity, status, triage_state, false_positive_probability]
    Case:
      keys: [case_id]
      properties: [title, mission_id, owner, status, classification, priority]
    Mission:
      keys: [mission_id]
      properties: [objective, commander, coalition_scope, active_windows, constraints]
    IntelProduct:
      keys: [product_id]
      properties: [type, audience, classification, conclusions, confidence]
    ActionPackage:
      keys: [package_id]
      properties: [recommended_action, risk, authority_required, approval_state]
    FeedbackSignal:
      keys: [feedback_id]
      properties: [operator_id, target_id, signal_type, correction, outcome]
    EvalRun:
      keys: [eval_run_id]
      properties: [suite, candidate_version, baseline_version, metrics, decision]
```

### 2.3 Relationship types

```yaml
relationships:
  - type: AFFILIATED_WITH
    from: Person
    to: Organization
    temporal: true
    confidence_required: true
  - type: OWNS_OR_CONTROLS
    from: Organization
    to: Asset
    temporal: true
  - type: OBSERVED_AT
    from: Event
    to: Location
    temporal: true
  - type: INVOLVES_ENTITY
    from: Event
    to: [Person, Organization, Asset, Device]
  - type: GENERATED_ALERT
    from: Event
    to: Alert
  - type: PART_OF_CASE
    from: [Alert, Event, IntelProduct, ActionPackage]
    to: Case
  - type: SUPPORTS_CONCLUSION
    from: [Event, Document, Observation]
    to: IntelProduct
    properties: [rationale, confidence_delta]
  - type: REVIEWED_BY
    from: [IntelProduct, ActionPackage, PromptVersion, WorkflowVersion]
    to: Person
  - type: SUPERSEDES
    from: [PromptVersion, WorkflowVersion, PolicyVersion]
    to: [PromptVersion, WorkflowVersion, PolicyVersion]
```

### 2.4 Object envelope

Every ontology object uses a common metadata envelope:

```json
{
  "object_id": "alert_01J...",
  "object_type": "Alert",
  "classification": "SECRET//COALITION-A",
  "compartments": ["ARTEMIS-NORTH", "CYBER"],
  "coalition_visibility": ["US", "CAN"],
  "need_to_know_tags": ["mission:aurora-watch", "case:2026-118"],
  "confidence": {
    "score": 0.82,
    "method": "weighted_source_consensus_v3",
    "explanation": "three independent sensors and one HUMINT correction"
  },
  "lineage": {
    "sources": ["foundry.dataset.raw_sensor_events", "gotham.case.2026-118"],
    "transform_ids": ["normalize_events:v12", "entity_resolution:v7"],
    "model_ids": ["triage-router:v4.2"]
  },
  "temporal": {
    "observed_at": "2026-06-29T14:02:18Z",
    "valid_from": "2026-06-29T13:58:00Z",
    "valid_to": null
  },
  "audit": {
    "created_by": "pipeline:live_ingest",
    "created_at": "2026-06-29T14:02:20Z",
    "last_modified_by": "operator:analyst-17"
  }
}
```

### 2.5 Ontology-driven behavior

The ontology drives human and AI behavior in four ways:

1. **UI composition:** the cockpit renders cases, alerts, entities, maps, and timelines from ontology object types and relationship schemas.
2. **Agent grounding:** AIP tools query the ontology rather than ungoverned raw tables, so answers inherit lineage and permissions.
3. **Policy enforcement:** access decisions evaluate object classification, compartments, coalition scope, mission assignment, and relationship-derived need-to-know.
4. **Self-improvement:** feedback, outcome, prompt, workflow, and eval objects become first-class data that can be audited, evaluated, approved, and rolled back.

---

## 3. AI and Agent Design

### 3.1 Copilots

| Copilot | Users | Responsibilities | Default authority |
|---|---|---|---|
| Analyst Copilot | investigators, analysts | entity summaries, link analysis, hypotheses, collection gaps, draft intel products | read + draft |
| Commander Copilot | mission leads | operational picture, risk tradeoffs, decision briefs, action package summaries | read + recommend |
| Data Steward Copilot | data engineers | lineage debugging, schema quality, transform impact analysis | read + propose code |
| Red-Team Copilot | security reviewers | adversarial prompt tests, tool misuse detection, policy bypass probes | sandbox only |
| Eval Copilot | AI governance team | eval generation, score analysis, candidate comparison | propose only |

### 3.2 Multi-agent workflows

```text
Live Event → Triage Agent → Enrichment Agent → Correlation Agent
              │             │                  │
              ▼             ▼                  ▼
          Severity       Entity graph       Hypotheses
              └─────────────┬──────────────────┘
                            ▼
                    Summarization Agent
                            ▼
                  Recommendation Agent
                            ▼
                 Approval + Policy Gateway
                            ▼
              Case update / Intel product / Action package
```

### 3.3 Tool-using agents

Representative AIP tool registry:

```yaml
tools:
  query_ontology:
    risk: read_only
    approval: none
    scopes: [ontology:read]
  search_evidence:
    risk: read_only
    approval: none
    scopes: [search:read, evidence:read]
  create_case_note:
    risk: low_write
    approval: auto_if_case_member
    scopes: [case:write]
  generate_intel_product:
    risk: draft_write
    approval: human_review_before_publish
    scopes: [product:draft]
  open_case:
    risk: operational_write
    approval: supervisor_required
    scopes: [case:create]
  prepare_action_package:
    risk: operational_significant
    approval: commander_required
    scopes: [action:prepare]
  execute_external_action:
    risk: consequential
    approval: forbidden_by_default
    scopes: [external:execute]
```

### 3.4 Approval gates

Operationally significant actions require explicit human approval. Examples include opening a case outside the current mission scope, changing an alert severity that affects watch floor posture, publishing an intel product, tasking a collection source, exporting coalition-visible artifacts, or deploying any workflow/prompt/model route candidate.

---

## 4. Self-Improvement Loop

### 4.1 Signals captured

ClearGlassInc Artemis captures improvement signals as governed ontology objects:

- explicit feedback: thumbs up/down, rating, correction text, structured defect labels;
- implicit feedback: accepted recommendations, edited drafts, abandoned workflows, dwell time, repeated queries;
- operational outcomes: true positive, false positive, missed detection, lead time, escalation success, mission impact;
- query logs: redacted prompts, retrieved evidence IDs, model choices, latency, cost, policy decisions;
- alert outcomes: triage disposition, severity adjustments, resolution notes;
- eval outcomes: regression scores, adversarial failures, safety violations, drift alarms.

### 4.2 Closed-loop lifecycle

```text
Observe → Normalize → Mine Patterns → Generate Candidate → Offline Eval
   → Red-Team Eval → Human Review → Apollo Canary → Monitor → Promote/Rollback
```

### 4.3 Candidate types

| Candidate | Example | Promotion requirement |
|---|---|---|
| PromptVersion | clearer citation instruction for Analyst Copilot | eval win + no policy regressions + reviewer approval |
| WorkflowVersion | add enrichment step before recommendation | latency budget preserved + improved precision |
| RoutingPolicy | use smaller model for low-risk summaries | quality non-inferior + cost/latency improved |
| HeuristicRule | suppress duplicate alert cluster under exact conditions | recall impact bounded and approved |
| EvalCase | new regression case from operator correction | eval steward approval |

### 4.4 Safety constraints

The platform can propose self-upgrades, but it cannot autonomously:

- expand its own permissions;
- lower approval gates;
- change mission objectives;
- alter coalition visibility;
- deploy candidates to production;
- suppress audit logging;
- bypass eval or red-team requirements.

### 4.5 Rollback and versioning

Each candidate is immutable and versioned. Apollo deploys candidates through rings: `dev → eval → shadow → canary → limited_ops → production`. Any degradation in precision, recall, latency, policy violations, operator trust, or mission-defined guardrail metrics triggers automatic rollback to the previous approved version.

---

## 5. Full-Stack Implementation

### 5.1 Reference repositories

```text
clearglassinc-artemis/
  apps/
    cockpit-web/                 # Next.js mission UI
    eval-console/                # prompt/model/workflow governance UI
  services/
    api-gateway/                 # FastAPI BFF and policy enforcement
    alert-service/               # alert lifecycle
    case-service/                # case state and notes
    feedback-service/            # feedback capture and normalization
    orchestration-service/       # workflow state machines
    eval-service/                # offline/online eval execution
    model-router/                # route inference requests
  foundry/
    pipelines/                   # transforms and ontology sync jobs
    ontology/                    # ontology schemas and actions
  aip/
    prompts/                     # prompt registry
    agents/                      # agent definitions
    evals/                       # eval suites
  policy/
    cedar/                       # policy-as-code
    opa/                         # rego policies
  infra/
    apollo/                      # deployment channels and rollback rules
    observability/               # dashboards and alerts
```

### 5.2 Runtime path for a live event

1. A live source emits an event to Kafka/Pulsar/Kinesis.
2. Foundry ingestion validates schema, attaches lineage, and writes raw/bronze records.
3. Foundry transforms normalize, resolve entities, enrich confidence, and publish ontology objects.
4. Alert Service consumes high-severity events and opens or updates an alert.
5. AIP triage workflow runs read-only tools against the ontology and search layer.
6. Recommendation Agent drafts an action package with cited evidence and confidence.
7. Policy Service determines whether the package is viewable and what approval is required.
8. Operator approves, rejects, or edits the recommendation.
9. Feedback Service records the decision and outcome as self-improvement signals.
10. Eval Service turns repeated patterns into eval cases and candidate improvements.
11. Apollo deploys approved candidates through controlled rings with rollback.

---

## 6. Security and Governance

### 6.1 Access model

ClearGlassInc Artemis uses layered access control:

- **Authentication:** hardware-backed SSO, mTLS service identity, short-lived tokens.
- **Authorization:** ABAC for attributes, ReBAC for mission/case relationships, RBAC for coarse roles.
- **Data controls:** row-, column-, object-, relationship-, and field-level enforcement.
- **Coalition controls:** visibility is constrained by nationality, coalition agreement, mission scope, compartment, and releasability marking.
- **Zero-trust execution:** every tool call is independently authorized; no agent receives blanket authority.

### 6.2 Governance objects

```yaml
governance:
  PromptVersion:
    required_reviews: [ai_governance, mission_owner]
    immutable_after_approval: true
  WorkflowVersion:
    required_reviews: [ops_owner, security, ai_governance]
    canary_required: true
  ModelRouteVersion:
    required_reviews: [ai_governance, cost_owner, security]
    rollback_metric: [quality_regression, latency_regression, policy_violation]
  PolicyVersion:
    required_reviews: [security_owner, legal_owner]
    emergency_change_process: break_glass_with_post_review
```

### 6.3 Audit and provenance

All material actions append immutable ledger entries:

```json
{
  "audit_id": "aud_01J...",
  "actor": "agent:recommendation-agent:v6",
  "human_supervisor": "operator:commander-02",
  "action": "prepare_action_package",
  "target": "case:2026-118",
  "policy_decision": "require_commander_approval",
  "evidence_ids": ["event:e1", "alert:a7", "entity:org9"],
  "model": "reasoning-model-prod-2026-06",
  "prompt_version": "commander_brief:v14",
  "workflow_version": "live_event_triage:v9",
  "timestamp": "2026-06-29T14:05:43Z"
}
```

---

## 7. Code Examples

### 7.1 Python domain models

```python
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class Classification(str, Enum):
    unclassified = "UNCLASSIFIED"
    confidential = "CONFIDENTIAL"
    secret = "SECRET"
    top_secret = "TOP_SECRET"


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    method: str
    explanation: str


class Lineage(BaseModel):
    sources: list[str]
    transform_ids: list[str] = []
    model_ids: list[str] = []


class SecurityEnvelope(BaseModel):
    classification: Classification
    compartments: list[str]
    coalition_visibility: list[str]
    need_to_know_tags: list[str]


class AlertObject(BaseModel):
    object_id: str
    object_type: Literal["Alert"] = "Alert"
    source: str
    severity: Literal["low", "medium", "high", "critical"]
    status: Literal["new", "triaged", "in_case", "closed"]
    summary: str
    occurred_at: datetime
    observed_at: datetime
    confidence: Confidence
    lineage: Lineage
    security: SecurityEnvelope
```

### 7.2 FastAPI gateway with policy checks

```python
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="ClearGlassInc Artemis API Gateway")


class Principal(BaseModel):
    subject: str
    roles: list[str]
    compartments: list[str]
    coalition: str
    missions: list[str]


async def get_principal(request: Request) -> Principal:
    token_claims = request.state.token_claims
    return Principal(**token_claims)


async def authorize(principal: Principal, action: str, resource: dict) -> str:
    decision = await policy_client.decide(
        principal=principal.model_dump(),
        action=action,
        resource=resource,
    )
    if decision.effect == "deny":
        raise HTTPException(status_code=403, detail=decision.reason)
    return decision.effect


@app.post("/cases/{case_id}/action-packages")
async def prepare_action_package(
    case_id: str,
    request: dict,
    principal: Principal = Depends(get_principal),
):
    case = await foundry_client.get_ontology_object("Case", case_id)
    effect = await authorize(principal, "action_package:prepare", case)
    package = await aip_client.run_workflow(
        workflow="prepare_action_package:v9",
        inputs={"case_id": case_id, "request": request},
        principal=principal.model_dump(),
        approval_mode=effect,
    )
    await audit_client.append(
        actor=principal.subject,
        action="action_package:prepare",
        target=case_id,
        policy_decision=effect,
        evidence_ids=package["evidence_ids"],
    )
    return package
```

### 7.3 Policy-as-code example

```rego
package artemis.authz

default allow := false
default require_approval := false

allow if {
  input.action == "ontology:read"
  input.principal.coalition in input.resource.coalition_visibility
  every c in input.resource.compartments { c in input.principal.compartments }
  some tag in input.resource.need_to_know_tags
  startswith(tag, "mission:")
  trim_prefix(tag, "mission:") in input.principal.missions
}

require_approval if {
  input.action == "action_package:prepare"
  allow
  input.resource.classification in {"SECRET", "TOP_SECRET"}
}
```

### 7.4 Ontology-driven query

```python
async def fetch_alert_context(alert_id: str, principal: Principal) -> dict:
    query = """
    MATCH (a:Alert {object_id: $alert_id})-[:INVOLVES_ENTITY]->(e)
    OPTIONAL MATCH (e)<-[:INVOLVES_ENTITY]-(prior:Event)
    OPTIONAL MATCH (prior)-[:PART_OF_CASE]->(c:Case)
    RETURN a, collect(distinct e) as entities,
           collect(distinct prior) as related_events,
           collect(distinct c) as related_cases
    LIMIT 1
    """
    result = await foundry_ontology.query(
        query=query,
        params={"alert_id": alert_id},
        security_context=principal.model_dump(),
    )
    return result[0]
```

### 7.5 Agent tool implementation

```python
from typing import Annotated


class OntologySearchTool:
    name = "query_ontology"
    risk = "read_only"

    async def __call__(
        self,
        query: Annotated[str, "Ontology graph query or semantic search string"],
        mission_id: str,
        principal: Principal,
    ) -> dict:
        await authorize(
            principal,
            "ontology:read",
            {"need_to_know_tags": [f"mission:{mission_id}"]},
        )
        rows = await foundry_ontology.semantic_search(
            text=query,
            filters={"mission_id": mission_id},
            security_context=principal.model_dump(),
            include_lineage=True,
            include_confidence=True,
        )
        return {"rows": rows, "count": len(rows)}
```

### 7.6 Workflow state machine

```python
from transitions import Machine


class LiveEventWorkflow:
    states = [
        "received", "triaged", "enriched", "correlated", "summarized",
        "recommended", "awaiting_approval", "approved", "rejected", "closed"
    ]

    transitions = [
        {"trigger": "triage", "source": "received", "dest": "triaged"},
        {"trigger": "enrich", "source": "triaged", "dest": "enriched"},
        {"trigger": "correlate", "source": "enriched", "dest": "correlated"},
        {"trigger": "summarize", "source": "correlated", "dest": "summarized"},
        {"trigger": "recommend", "source": "summarized", "dest": "recommended"},
        {"trigger": "request_approval", "source": "recommended", "dest": "awaiting_approval"},
        {"trigger": "approve", "source": "awaiting_approval", "dest": "approved"},
        {"trigger": "reject", "source": "awaiting_approval", "dest": "rejected"},
        {"trigger": "close", "source": ["approved", "rejected"], "dest": "closed"},
    ]

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.machine = Machine(model=self, states=self.states, transitions=self.transitions, initial="received")
```

### 7.7 Feedback event handler

```python
async def handle_operator_feedback(event: dict) -> None:
    feedback = {
        "object_type": "FeedbackSignal",
        "target_id": event["target_id"],
        "operator_id": event["operator_id"],
        "signal_type": event["signal_type"],
        "correction": event.get("correction"),
        "outcome": event.get("outcome"),
        "prompt_version": event.get("prompt_version"),
        "workflow_version": event.get("workflow_version"),
        "model_route_version": event.get("model_route_version"),
    }
    await foundry_client.write_ontology_object("FeedbackSignal", feedback)

    if event["signal_type"] in {"false_positive", "missed_detection", "unsafe_recommendation"}:
        await eval_service.create_regression_case(
            source_feedback=feedback,
            required_review="eval_steward",
        )
```

### 7.8 Evaluation pipeline

```python
class EvalResult(BaseModel):
    suite: str
    candidate_version: str
    baseline_version: str
    precision: float
    recall: float
    p95_latency_ms: int
    policy_violations: int
    operator_trust_delta: float


def promotion_decision(result: EvalResult) -> str:
    if result.policy_violations > 0:
        return "reject"
    if result.precision < 0.92 or result.recall < 0.88:
        return "reject"
    if result.p95_latency_ms > 1800:
        return "reject"
    if result.operator_trust_delta < -0.01:
        return "reject"
    return "human_review_required"


async def run_candidate_eval(candidate_version: str, baseline_version: str) -> EvalResult:
    cases = await foundry_client.read_dataset("eval.live_event_triage_regression")
    metrics = await aip_eval_runner.compare(
        candidate=candidate_version,
        baseline=baseline_version,
        cases=cases,
        judges=["exact_match", "evidence_grounding", "policy_safety", "latency"],
    )
    result = EvalResult(**metrics)
    await foundry_client.write_ontology_object("EvalRun", result.model_dump())
    return result
```

### 7.9 Model router

```python
async def route_model(task: dict, principal: Principal) -> str:
    sensitivity = task["classification"]
    latency_budget_ms = task.get("latency_budget_ms", 1500)
    risk = task.get("risk", "read_only")

    if sensitivity in {"SECRET", "TOP_SECRET"}:
        return "approved-secure-reasoning-model"
    if risk == "operational_significant":
        return "high-reliability-reasoning-model"
    if latency_budget_ms < 700:
        return "low-latency-summary-model"
    return "balanced-reasoning-model"
```

### 7.10 SQL metrics for eval dashboard

```sql
SELECT
  candidate_version,
  baseline_version,
  AVG(precision) AS avg_precision,
  AVG(recall) AS avg_recall,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY p95_latency_ms) AS p95_latency_ms,
  SUM(policy_violations) AS policy_violations,
  AVG(operator_trust_delta) AS trust_delta
FROM artemis_eval_runs
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY candidate_version, baseline_version
ORDER BY created_at DESC;
```

### 7.11 TypeScript cockpit event feed

```typescript
type MissionEvent = {
  id: string;
  type: "alert" | "case_update" | "agent_step" | "approval_request";
  severity?: "low" | "medium" | "high" | "critical";
  title: string;
  summary: string;
  evidenceIds: string[];
  confidence: number;
  occurredAt: string;
};

export function subscribeMissionFeed(missionId: string, onEvent: (event: MissionEvent) => void) {
  const ws = new WebSocket(`wss://artemis.clearglassinc.example/ws/missions/${missionId}`);
  ws.onmessage = (message) => onEvent(JSON.parse(message.data));
  ws.onerror = () => console.error("mission feed disconnected");
  return () => ws.close();
}
```

---

## 8. Scenario Walkthrough

### 8.1 Event enters the system

At `2026-06-29T14:02:18Z`, a coalition cyber sensor emits a high-confidence anomaly: a critical infrastructure vendor account authenticated from an unexpected region and immediately queried a sensitive asset inventory.

Foundry receives the event, validates the schema, resolves the account to a `Person`, links the person to an `Organization`, links the query to an `Asset`, and creates an `Alert` object with lineage, confidence, classification, compartments, and coalition visibility.

### 8.2 Platform triages it

The AIP Triage Agent reads only authorized ontology context. It finds three prior events involving the same vendor account, one unresolved case, and a recent phishing campaign targeting the same organization. The agent assigns severity `high`, confidence `0.81`, and rationale: source confidence is high, behavior is unusual, but there is no confirmed credential compromise.

### 8.3 Agent recommends a response

The Recommendation Agent prepares an action package:

1. preserve all session logs;
2. notify the mission watch officer;
3. request human approval to open a linked investigation case;
4. draft a coalition-safe summary for authorized partners;
5. recommend temporary step-up authentication for the vendor account.

The Policy Service marks this as `operational_significant`, so it requires commander approval before any case escalation or external notification.

### 8.4 Operator approves or rejects

The commander approves steps 1, 2, and 5, edits the partner summary, and rejects immediate external notification because the coalition disclosure threshold is not yet met. The platform records the decision, the edits, the rejection reason, and the final operational outcome.

### 8.5 System learns safely

The next day, the case is confirmed as a true positive. Feedback Service writes a `FeedbackSignal` showing that the triage was correct, the notification recommendation was premature, and the edited partner summary reduced sensitive detail. Eval Service converts this into:

- a new regression case for coalition disclosure thresholds;
- a candidate prompt update for the Commander Copilot;
- a workflow candidate that delays partner notification recommendations until disclosure criteria are met;
- a routing rule to use a higher-reliability model for cross-coalition summaries.

The candidates run offline evals, red-team checks, and policy tests. Human reviewers approve the workflow update but reject the routing change because latency increased beyond mission budget. Apollo deploys the workflow update to shadow mode, then canary, then production. If false negatives or operator rejection rates rise, Apollo rolls back automatically.

---

## 9. Performance and Trust Metrics

| Metric | Target | Use |
|---|---:|---|
| Triage precision | >= 0.92 | avoid alert fatigue |
| Triage recall | >= 0.88 | avoid missed operational events |
| P95 agent latency | <= 1.8s for summaries, <= 8s for action packages | protect mission tempo |
| Evidence grounding | >= 0.97 cited claims | increase trust and auditability |
| Policy violation rate | 0 | hard gate |
| Operator acceptance | +10% quarter-over-quarter | measure practical usefulness |
| Edit distance on drafts | -15% quarter-over-quarter | measure output quality |
| Rollback mean time | < 5 minutes | reduce deployment risk |
| Provenance completeness | 100% for intel products | support audit and disclosure |

---

## 10. Implementation Roadmap

### Phase 0 — Control plane foundation

- Define ontology envelope, security labels, audit ledger, and approval taxonomy.
- Build API Gateway, policy service, and immutable audit writer.
- Stand up Foundry ingestion for live/historical feeds.

### Phase 1 — Analyst-grade MVP

- Implement Analyst Copilot with read-only ontology tools.
- Build alert triage workflow and case note drafting.
- Add cockpit event feed and evidence-linked summaries.

### Phase 2 — Self-improvement governance

- Capture feedback and outcomes as ontology objects.
- Build eval suite generation from corrections.
- Add prompt/workflow/model route registries with human review.

### Phase 3 — Mission operations hardening

- Add commander action packages and approval queues.
- Enforce coalition boundaries in UI, API, tools, and exports.
- Integrate Apollo progressive rollout and rollback metrics.

### Phase 4 — Continuous optimization

- Run A/B prompt and workflow tests in shadow/canary mode.
- Expand red-team evals and adversarial policy tests.
- Tune precision, recall, latency, trust, and mission impact metrics.

---

## 11. Executive Summary

ClearGlassInc Artemis is designed as a production-grade intelligence platform where Gotham provides operational investigation depth, Foundry provides governed data and ontology logic, AIP provides controlled agentic intelligence, and Apollo provides secure runtime evolution. The system gets better by converting operator behavior and mission outcomes into evals and candidate improvements, but every consequential change remains versioned, reviewed, policy-checked, deployed progressively, observable, and reversible.
