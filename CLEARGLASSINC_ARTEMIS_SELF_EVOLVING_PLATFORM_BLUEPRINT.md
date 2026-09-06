# ClearGlassInc Artemis — Self-Evolving AI Intelligence Platform Blueprint

## Executive Intent
ClearGlassInc Artemis is a secure, coalition-aware, latency-sensitive intelligence platform built on **Palantir Gotham**, **Foundry**, **AIP**, and **Apollo**. The platform fuses live and historical data, reasons over a governed ontology, coordinates agentic workflows, and proposes evidence-backed improvements to prompts, workflows, heuristics, and model routing under explicit human-approved guardrails.

> **Target-state specification:** this document describes the intended production architecture and acceptance gates. It is not evidence that Palantir environments, integrations, security accreditations, data agreements, or operational capabilities have been provisioned. Every integration named below must be confirmed against the licensed platform version and the owning environment before implementation.

Palantir terms used precisely:
- **Gotham**: operational intelligence, investigations, entity tracking, link analysis, mission casework, and investigative timelines.
- **Foundry**: data integration, transformation pipelines, operational applications, Ontology, lineage, and governed data products.
- **Foundry Ontology**: the shared operational model of objects, links, actions, permissions, temporal state, and business logic used by humans and agents.
- **AIP**: AI copilots, agent orchestration, tool execution, evaluations, model governance, and workflow automation over governed data/actions.
- **Apollo**: secure deployment, canarying, runtime controls, rollback, policy distribution, and release telemetry across environments.

Non-negotiable operating constraints:
1. Artemis may recommend operational actions and self-upgrades, but cannot execute operationally significant actions or promote self-upgrades without explicit approval.
2. Every answer, tool call, recommendation, model route, and self-improvement proposal is permission-filtered, provenance-linked, auditable, and reversible.
3. The platform optimizes for precision, recall, latency, operator trust, mission impact, and policy compliance without autonomously changing mission objectives.

---

## System Architecture

### End-to-End Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Operator Surfaces                                                           │
│ React/TypeScript Analyst Workbench • Commander Console • Governance Console │
│ Gotham investigative views • Foundry apps • AIP copilot panels              │
└─────────────────────┬───────────────────────────────────────────────────────┘
                      │ OIDC/JWT, mission context, request provenance
┌─────────────────────▼───────────────────────────────────────────────────────┐
│ API Gateway / Backend-for-Frontend                                          │
│ FastAPI • GraphQL • WebSockets • schema validation • idempotency • OPA check │
└──────────────┬───────────────┬─────────────────┬────────────────────────────┘
               │               │                 │
┌──────────────▼───────┐ ┌─────▼──────────┐ ┌────▼────────────────────────────┐
│ Mission Services     │ │ Event Services │ │ AI Orchestration Services       │
│ cases, alerts,       │ │ Kafka/Pulsar,   │ │ AIP agents, tools, model router │
│ approvals, products  │ │ Flink/Ray, CQRS │ │ eval harness, prompt registry   │
└──────────────┬───────┘ └─────┬──────────┘ └────┬────────────────────────────┘
               │               │                 │
┌──────────────▼───────────────▼─────────────────▼────────────────────────────┐
│ Foundry + Gotham Operational Data Plane                                      │
│ Bronze/Silver/Gold datasets • Ontology • Actions • Functions • lineage       │
│ Gotham case graph • investigative timeline • link analysis • entity tracking │
└──────────────┬───────────────┬─────────────────┬────────────────────────────┘
               │               │                 │
┌──────────────▼───────┐ ┌─────▼──────────┐ ┌────▼────────────────────────────┐
│ Retrieval Layer      │ │ Policy Layer   │ │ Observability + Audit           │
│ hybrid search, graph │ │ ABAC/RBAC,     │ │ traces, metrics, evals,         │
│ expansion, vectors   │ │ OPA, policy    │ │ immutable append-only log        │
│ geotemporal indexes  │ │ as code        │ │                                 │
└──────────────┬───────┘ └─────┬──────────┘ └────┬────────────────────────────┘
               │               │                 │
┌──────────────▼───────────────▼─────────────────▼────────────────────────────┐
│ Apollo Runtime Control                                                       │
│ signed releases • policy bundles • deployment rings • canary gates • recall  │
│ rollback • runtime feature flags • environment-specific controls             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Production responsibility | Failure-safe behavior |
| --- | --- | --- |
| Frontend | Mission views, graph exploration, approvals, copilot interactions, eval dashboards | Hide unauthorized data, show uncertainty, require explicit approval for actions |
| API gateway | AuthN/AuthZ context, request validation, policy preflight, rate limits, idempotency | Reject malformed/unauthorized requests, preserve audit trail |
| Backend services | Deterministic mission logic, case lifecycle, alerts, feedback, recommendations | State-machine guarded transitions and replayable event handling |
| Data layer | Foundry pipelines, source lineage, normalized operational datasets | Quarantine malformed records and maintain raw payload references |
| Ontology layer | Mission entities, relationships, permissions, actions, temporal state | Enforce object/action permissions before read/write/tool use |
| AI orchestration | AIP copilots, agents, tool calls, model routing, eval capture | Tool allowlists, constrained JSON schemas, policy-gated execution |
| Policy layer | Need-to-know, coalition boundaries, prompt/tool/model governance | Default deny, immutable decision logs, break-glass with approval only |
| Observability | Metrics, traces, model telemetry, eval quality, drift, trust signals | Alert on SLO/policy/eval regressions; block promotion when thresholds fail |
| Deployment | Apollo releases, signed artifacts, progressive delivery, rollback | Auto-recall unsafe releases; pin known-good prompt/workflow/model versions |

### Frontend Applications

1. **Analyst Workbench**
   - Live alert stream with severity, uncertainty, lineage, deduplication status, and SLA.
   - Ontology graph explorer with bitemporal state playback and source drill-down.
   - Evidence tray for documents, events, images, logs, and human annotations.
   - AIP Copilot with mission-scoped tool permissions and transcript diff viewer.

2. **Commander Console**
   - Common operating picture, mission risk posture, pending approvals, and recommended action packages.
   - Latency, readiness, and confidence heatmaps.
   - “Why this recommendation?” panels showing evidence, assumptions, policy constraints, and alternatives.

3. **Governance Console**
   - Prompt/workflow/model-router version registry.
   - Eval scorecards, A/B tests, drift reports, regression failures, and approval workflows.
   - Policy-as-code bundle viewer and Apollo release channel status.

---

## Data and Ontology

### Core Ontology

```yaml
ontology: ClearGlassIncArtemis
version: 1.0
classification_strategy: entity_and_attribute_level
objects:
  Mission:
    primary_key: mission_id
    fields:
      mission_id: string
      name: string
      priority: enum[P0,P1,P2,P3]
      status: enum[planning, active, paused, closed]
      coalition_scope: list[string]
      classification: string
      objectives_ref: string
      created_at: timestamp
  Actor:
    primary_key: actor_id
    fields:
      actor_id: string
      actor_type: enum[person, organization, device, service_account, unknown]
      aliases: list[string]
      confidence: float
      country: string
      watchlist_status: enum[none, candidate, confirmed, retired]
      pii_handling: enum[none, restricted, masked]
  Asset:
    primary_key: asset_id
    fields:
      asset_id: string
      asset_type: enum[facility, system, endpoint, dataset, application, network]
      owner_org: string
      location: geopoint
      criticality: enum[low, medium, high, mission_critical]
      lifecycle_state: enum[planned, active, degraded, decommissioned]
  Event:
    primary_key: event_id
    fields:
      event_id: string
      event_type: string
      ts_event: timestamp
      ts_ingest: timestamp
      source_system: string
      raw_payload_ref: string
      normalized_payload_hash: string
      confidence: float
      lineage_refs: list[string]
  Alert:
    primary_key: alert_id
    fields:
      alert_id: string
      event_id: string
      rule_id: string
      severity: enum[info, low, medium, high, critical]
      score: float
      rationale: string
      state: enum[new, triaged, escalated, suppressed, resolved]
      sla_due_at: timestamp
  Case:
    primary_key: case_id
    fields:
      case_id: string
      mission_id: string
      title: string
      status: enum[open, investigating, pending_approval, actioned, closed]
      owner_user_id: string
      opened_at: timestamp
      closed_at: timestamp?
  Recommendation:
    primary_key: rec_id
    fields:
      rec_id: string
      case_id: string
      action_type: string
      expected_impact: string
      risk_score: float
      confidence: float
      status: enum[draft, proposed, approved, rejected, executed, rolled_back]
      prompt_version: string
      workflow_version: string
      model_route: string
  ApprovalDecision:
    primary_key: decision_id
    fields:
      decision_id: string
      rec_id: string
      approver_user_id: string
      decision: enum[approve, reject, request_changes]
      reason: string
      decided_at: timestamp
      policy_version: string
  FeedbackSignal:
    primary_key: feedback_id
    fields:
      feedback_id: string
      source: enum[operator_correction, edited_summary, alert_outcome, mission_result, eval_failure]
      target_type: enum[prompt, workflow, model_route, entity, alert, recommendation]
      target_id: string
      label: string
      correction_json: json
      confidence_delta: float
      outcome: string
      captured_at: timestamp
```

### Relationships

```yaml
relationships:
  - name: EVENT_OBSERVED_ACTOR
    from: Event
    to: Actor
    fields: [confidence, extractor_version, observed_at]
  - name: EVENT_TARGETED_ASSET
    from: Event
    to: Asset
    fields: [confidence, impact_estimate]
  - name: EVENT_TRIGGERED_ALERT
    from: Event
    to: Alert
    fields: [rule_version, score_components]
  - name: ALERT_ESCALATED_TO_CASE
    from: Alert
    to: Case
    fields: [escalated_by, escalation_reason]
  - name: CASE_HAS_RECOMMENDATION
    from: Case
    to: Recommendation
    fields: [rank, rationale_hash]
  - name: RECOMMENDATION_REQUIRES_DECISION
    from: Recommendation
    to: ApprovalDecision
    fields: [approval_gate, min_authority]
  - name: FEEDBACK_ON_RECOMMENDATION
    from: FeedbackSignal
    to: Recommendation
    fields: [signal_weight, adjudication_status]
  - name: MISSION_CONTAINS_CASE
    from: Mission
    to: Case
    fields: [mission_relevance, tasking_ref]
```

### Temporal State, Confidence, and Lineage

Foundry stores raw, normalized, and curated records with immutable lineage. Artemis uses bitemporal facts so operators can ask both “what was true at event time?” and “what did we know at decision time?”

```sql
CREATE TABLE ontology_fact_history (
  fact_id TEXT PRIMARY KEY,
  subject_type TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  predicate TEXT NOT NULL,
  object_type TEXT,
  object_id TEXT,
  value_json JSONB,
  confidence DOUBLE PRECISION NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  source_refs TEXT[] NOT NULL,
  classification TEXT NOT NULL,
  coalition_scope TEXT[] NOT NULL,
  valid_from TIMESTAMPTZ NOT NULL,
  valid_to TIMESTAMPTZ,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  recorded_by TEXT NOT NULL,
  transform_version TEXT NOT NULL,
  policy_version TEXT NOT NULL
);

CREATE INDEX idx_fact_subject_time
  ON ontology_fact_history(subject_type, subject_id, valid_from, recorded_at);

CREATE INDEX idx_fact_policy_scope
  ON ontology_fact_history(classification, coalition_scope);
```

The ontology drives human and AI behavior by making actions object-aware. An agent cannot “open a case” generically; it must call an ontology action such as `Case.open_from_alert(alert_id, mission_id)` and pass policy checks tied to the mission, alert, actor, asset, and user context.

---

## AI and Agent Design

### Copilots

- **Analyst Copilot**: performs evidence summarization, entity expansion, timeline generation, anomaly explanation, case drafting, and uncertainty analysis.
- **Commander Copilot**: summarizes mission posture, compares courses of action, highlights approval queues, and explains tradeoffs.
- **Governance Copilot**: reviews proposed prompt/workflow/router updates, compares eval deltas, checks policy impacts, and prepares approval packets.

### Multi-Agent Workflows

```text
Incoming Event
  └─ Triage Agent
      ├─ Deduplication Tool
      ├─ Policy Filter Tool
      └─ Severity Scorer
          └─ Enrichment Agent
              ├─ Entity Resolver
              ├─ Graph Correlator
              ├─ Retrieval Tool
              └─ Source Reliability Estimator
                  └─ Synthesis Agent
                      ├─ Timeline Builder
                      ├─ Hypothesis Generator
                      └─ Intel Product Drafter
                          └─ Recommendation Agent
                              ├─ Risk/Impact Estimator
                              ├─ Approval Gate Classifier
                              └─ Action Package Builder
```

### Tool Contract Rules

1. Tools are registered with JSON schemas, ownership metadata, required scopes, side-effect level, and approval gate.
2. Read-only tools may execute after policy checks and audit logging.
3. Mutating tools require state-machine validation and may require human approval depending on action criticality.
4. Operationally significant actions always require approval and cannot be chained behind hidden autonomous decisions.
5. Every tool result is stored with input hash, output hash, policy version, model version, prompt version, and lineage references.

### Human Approval Gates

| Action | Side effect | Approval |
| --- | --- | --- |
| Summarize evidence | none | no approval, policy-filtered |
| Expand graph neighborhood | none | no approval, policy-filtered |
| Draft case | reversible write | analyst confirmation |
| Open case | workflow write | analyst confirmation; commander for high severity |
| Generate action package | recommendation only | no execution without approval |
| Execute operational action | external side effect | explicit authorized human approval |
| Promote prompt/workflow/router update | platform behavior change | governance approval + Apollo canary |

---

## Self-Improvement Loop

### Signal Capture

Artemis captures improvement signals without collecting unnecessary sensitive data:

```text
Operator edits summary  ─┐
Rejected recommendation ─┤
Accepted recommendation ─┤
Alert true/false outcome ├─► FeedbackSignal dataset
Case closure result      ┤       └─► eval examples
Latency/error telemetry  ┤       └─► prompt/workflow proposals
Drift detector alerts    ┘       └─► router threshold proposals
```

### Improvement Lifecycle

```text
1. Capture signal
2. Normalize and redact sensitive fields
3. Convert to eval example with lineage and permission constraints
4. Run offline evals against current and candidate prompt/workflow/model routes
5. Generate improvement proposal with diff, metrics, risks, rollback plan
6. Governance review approves/rejects/requests changes
7. Apollo deploys to shadow or canary channel
8. Monitor precision, recall, latency, trust, safety, and policy violations
9. Promote, hold, or rollback
10. Immutable audit entry links every decision and artifact version
```

### Drift Detection and Rollback

- **Data drift**: population stability index, embedding distribution distance, source mix changes, missing-field rates.
- **Concept drift**: precision/recall decay, label disagreement, operator correction spikes, false-positive clusters.
- **Policy drift**: new coalition-sharing rule, compartment change, new restricted attribute, tool manifest change.
- **Operational drift**: latency SLO breaches, tool timeouts, case backlog, alert storms.

Rollback is version-addressed:

```yaml
rollback_unit:
  prompt_version: artemis-triage-v18
  workflow_version: alert-triage-sm-v7
  model_route_version: router-2026-07-13.2
  policy_bundle_version: opa-bundle-44f3a
  deployment_channel: mission-canary
  rollback_to:
    prompt_version: artemis-triage-v17
    workflow_version: alert-triage-sm-v6
    model_route_version: router-2026-07-12.1
```

### Safe “Gets Better and Better” Mechanism

Artemis improves only within bounded, reviewable dimensions:

- Prompt text, retrieval templates, and structured output schemas.
- Workflow thresholds, ordering, retries, and escalation heuristics.
- Model routing based on task type, sensitivity, latency budget, and eval performance.
- Entity-resolution confidence calibration.
- Alert scoring calibration.

Artemis never self-modifies:

- Mission objectives.
- Legal/policy constraints.
- Approval requirements.
- User permissions or coalition boundaries.
- External side-effect permissions.

---

## Full-Stack Implementation

### Repository Blueprint

```text
artemis/
  apps/
    web-console/                 # React/TypeScript operator UI
    governance-console/          # prompt/eval/deployment review UI
  services/
    api-gateway/                 # FastAPI BFF and GraphQL facade
    alert-service/               # alert lifecycle and triage state
    case-service/                # case state machine and approvals
    ai-orchestrator/             # AIP agent runtime integration
    feedback-service/            # learning signal capture
    improvement-service/         # evals and self-upgrade proposals
  packages/
    ontology-client/             # typed Foundry/Gotham ontology access
    policy-client/               # OPA/ABAC helpers
    schemas/                     # JSON Schema, Protobuf, OpenAPI
  infra/
    apollo/                      # release channels and rollback config
    foundry/                     # pipeline specs, dataset contracts
    policies/                    # Rego policy-as-code
  evals/
    datasets/                    # permission-filtered eval examples
    suites/                      # prompt/workflow/model eval definitions
```

### Web UI Blueprint

```tsx
// apps/web-console/src/components/ApprovalInbox.tsx
import { useEffect, useState } from "react";

type Recommendation = {
  recId: string;
  caseId: string;
  actionType: string;
  expectedImpact: string;
  riskScore: number;
  confidence: number;
  rationale: string;
};

export function ApprovalInbox({ missionId }: { missionId: string }) {
  const [items, setItems] = useState<Recommendation[]>([]);

  useEffect(() => {
    const ws = new WebSocket(`/ws/missions/${missionId}/approvals`);
    ws.onmessage = event => setItems(JSON.parse(event.data));
    return () => ws.close();
  }, [missionId]);

  async function decide(recId: string, decision: "approve" | "reject", reason: string) {
    const response = await fetch(`/api/recommendations/${recId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, reason, idempotencyKey: crypto.randomUUID() })
    });
    if (!response.ok) throw new Error("Decision was not accepted");
  }

  return (
    <section aria-label="Approval inbox">
      {items.map(item => (
        <article key={item.recId} className="approval-card">
          <h3>{item.actionType}</h3>
          <p>{item.expectedImpact}</p>
          <p>Risk: {item.riskScore.toFixed(2)} • Confidence: {item.confidence.toFixed(2)}</p>
          <details><summary>Rationale</summary>{item.rationale}</details>
          <button onClick={() => decide(item.recId, "approve", "Meets mission intent")}>Approve</button>
          <button onClick={() => decide(item.recId, "reject", "Insufficient evidence")}>Reject</button>
        </article>
      ))}
    </section>
  );
}
```

### API Gateway Pattern

```python
# services/api_gateway/main.py
from pydantic import BaseModel, Field
from fastapi import FastAPI, Depends, HTTPException, Header
from uuid import UUID

app = FastAPI(title="ClearGlassInc Artemis API Gateway")

class AuthContext(BaseModel):
    user_id: str
    roles: list[str]
    compartments: list[str]
    coalition: list[str]
    mission_ids: list[str]

class DecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approve|reject|request_changes)$")
    reason: str = Field(min_length=3, max_length=4000)
    idempotency_key: UUID

async def auth_context(authorization: str = Header()) -> AuthContext:
    # Production implementation validates OIDC/JWT, extracts claims, and rejects stale tokens.
    return AuthContext(
        user_id="operator-123",
        roles=["analyst"],
        compartments=["alpha"],
        coalition=["CLEARGLASSINC"],
        mission_ids=["mission-7"],
    )

async def policy_allow(ctx: AuthContext, action: str, resource: dict) -> bool:
    # Calls OPA/Foundry policy service with full request provenance.
    return action == "recommendation.decide" and "analyst" in ctx.roles

@app.post("/api/recommendations/{rec_id}/decision")
async def recommendation_decision(rec_id: str, body: DecisionRequest, ctx: AuthContext = Depends(auth_context)):
    resource = {"type": "Recommendation", "id": rec_id}
    if not await policy_allow(ctx, "recommendation.decide", resource):
        raise HTTPException(status_code=403, detail="Not authorized for this recommendation")

    # Idempotent command forwarded to approval service.
    return {
        "status": "accepted",
        "rec_id": rec_id,
        "decision": body.decision,
        "decision_by": ctx.user_id,
        "idempotency_key": str(body.idempotency_key),
    }
```

### Event Bus and Streaming

```python
# services/alert_service/triage_consumer.py
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json

@dataclass(frozen=True)
class RawEvent:
    event_id: str
    source_system: str
    payload: dict
    ts_event: datetime
    classification: str
    coalition_scope: list[str]

@dataclass(frozen=True)
class AlertCandidate:
    alert_id: str
    event_id: str
    severity: str
    score: float
    rationale: str

SUSPICIOUS_EVENT_TYPES = {"credential_anomaly", "unexpected_data_transfer", "watchlist_match"}

def stable_id(prefix: str, value: dict) -> str:
    digest = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]
    return f"{prefix}_{digest}"

def triage_event(event: RawEvent) -> AlertCandidate | None:
    event_type = event.payload.get("event_type")
    source_reliability = float(event.payload.get("source_reliability", 0.5))
    impact = float(event.payload.get("impact_estimate", 0.0))

    if event_type not in SUSPICIOUS_EVENT_TYPES:
        return None

    score = min(1.0, 0.55 * source_reliability + 0.45 * impact)
    severity = "critical" if score >= 0.9 else "high" if score >= 0.75 else "medium"
    return AlertCandidate(
        alert_id=stable_id("alert", {"event_id": event.event_id, "event_type": event_type}),
        event_id=event.event_id,
        severity=severity,
        score=score,
        rationale=f"{event_type} scored {score:.2f} from reliability and impact signals",
    )
```

### Ontology-Driven Query

```python
# packages/ontology_client/client.py
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class QueryContext:
    user_id: str
    mission_id: str
    compartments: list[str]
    coalition: list[str]
    as_of: datetime

class OntologyClient:
    def __init__(self, foundry_session):
        self.session = foundry_session

    async def alert_context(self, alert_id: str, ctx: QueryContext) -> dict:
        # The Foundry query/action layer enforces row, column, entity, and action permissions.
        return await self.session.query("""
            SELECT a.alert_id, a.severity, a.score, e.event_type, e.ts_event,
                   asset.asset_id, asset.criticality, actor.actor_id, actor.confidence
            FROM Alert a
            JOIN Event e ON a.event_id = e.event_id
            LEFT JOIN EVENT_TARGETED_ASSET eta ON eta.event_id = e.event_id
            LEFT JOIN Asset asset ON asset.asset_id = eta.asset_id
            LEFT JOIN EVENT_OBSERVED_ACTOR eoa ON eoa.event_id = e.event_id
            LEFT JOIN Actor actor ON actor.actor_id = eoa.actor_id
            WHERE a.alert_id = :alert_id
              AND :mission_id = ANY(a.allowed_missions)
              AND a.classification <= current_user_clearance()
              AND overlaps(a.coalition_scope, :coalition)
        """, {"alert_id": alert_id, "mission_id": ctx.mission_id, "coalition": ctx.coalition})
```

### Model Router

```python
# services/ai_orchestrator/model_router.py
from dataclasses import dataclass

@dataclass(frozen=True)
class InferenceRequest:
    task: str
    classification: str
    latency_budget_ms: int
    requires_reasoning: bool
    pii_present: bool
    mission_critical: bool

@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str
    max_tokens: int
    temperature: float
    route_reason: str

class ModelRouter:
    def route(self, request: InferenceRequest) -> ModelRoute:
        if request.pii_present or request.classification not in {"public", "internal"}:
            return ModelRoute("aip-private", "mission-secure-reasoner", 4096, 0.0, "sensitive_data_private_route")
        if request.latency_budget_ms < 800 and not request.requires_reasoning:
            return ModelRoute("aip-low-latency", "fast-summarizer", 1024, 0.0, "latency_budget")
        if request.mission_critical or request.requires_reasoning:
            return ModelRoute("aip-governed", "high-precision-reasoner", 8192, 0.0, "mission_critical_reasoning")
        return ModelRoute("aip-standard", "balanced-reasoner", 4096, 0.1, "default_balanced")
```

### Workflow State Machine

```python
# services/case_service/state_machine.py
from enum import StrEnum

class CaseState(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    PENDING_APPROVAL = "pending_approval"
    ACTIONED = "actioned"
    CLOSED = "closed"

ALLOWED_TRANSITIONS = {
    CaseState.OPEN: {CaseState.INVESTIGATING, CaseState.CLOSED},
    CaseState.INVESTIGATING: {CaseState.PENDING_APPROVAL, CaseState.CLOSED},
    CaseState.PENDING_APPROVAL: {CaseState.INVESTIGATING, CaseState.ACTIONED, CaseState.CLOSED},
    CaseState.ACTIONED: {CaseState.CLOSED},
    CaseState.CLOSED: set(),
}

def transition_case(current: CaseState, desired: CaseState, *, approval_present: bool) -> CaseState:
    if desired not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"Invalid transition from {current} to {desired}")
    if desired == CaseState.ACTIONED and not approval_present:
        raise PermissionError("Human approval is required before actioned state")
    return desired
```

### Policy-as-Code

```rego
package artemis.authz

default allow := false

allow if {
  input.action == "ontology.read"
  input.user.clearance >= input.resource.classification_rank
  some c
  c := input.resource.coalition_scope[_]
  c == input.user.coalition[_]
  input.resource.mission_id == input.request.mission_id
}

allow if {
  input.action == "recommendation.decide"
  "analyst" in input.user.roles
  input.resource.status == "proposed"
  input.resource.mission_id in input.user.mission_ids
  not input.resource.requires_commander_approval
}

allow if {
  input.action == "recommendation.decide"
  "commander" in input.user.roles
  input.resource.status == "proposed"
  input.resource.mission_id in input.user.mission_ids
}

deny_reason contains "operational actions require explicit approval" if {
  input.action == "external.execute"
  not input.request.human_approval_id
}
```

### Eval Pipeline

```python
# services/improvement_service/evals.py
from dataclasses import dataclass
from statistics import mean

@dataclass(frozen=True)
class EvalExample:
    example_id: str
    prompt_input: dict
    expected_label: str
    policy_context: dict
    lineage_refs: list[str]

@dataclass(frozen=True)
class EvalResult:
    candidate_version: str
    precision: float
    recall: float
    latency_p95_ms: int
    policy_violations: int
    passed: bool

class CandidateWorkflow:
    def __init__(self, version: str):
        self.version = version

    async def run(self, example: EvalExample) -> tuple[str, int, bool]:
        # Returns predicted label, latency, policy_violation.
        return "escalate", 420, False

async def run_eval_suite(candidate: CandidateWorkflow, examples: list[EvalExample]) -> EvalResult:
    tp = fp = fn = 0
    latencies: list[int] = []
    policy_violations = 0

    for example in examples:
        predicted, latency_ms, policy_violation = await candidate.run(example)
        latencies.append(latency_ms)
        policy_violations += int(policy_violation)
        if predicted == "escalate" and example.expected_label == "escalate":
            tp += 1
        elif predicted == "escalate":
            fp += 1
        elif example.expected_label == "escalate":
            fn += 1

    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    latency_p95 = sorted(latencies)[int(0.95 * (len(latencies) - 1))] if latencies else 0
    passed = precision >= 0.92 and recall >= 0.88 and latency_p95 <= 1500 and policy_violations == 0

    return EvalResult(candidate.version, precision, recall, latency_p95, policy_violations, passed)
```

### Improvement Proposal Object

```json
{
  "proposal_id": "upgrade_2026_07_13_triage_prompt_v19",
  "proposal_type": "prompt_update",
  "target": "alert_triage_agent",
  "current_version": "triage_prompt_v18",
  "candidate_version": "triage_prompt_v19",
  "evidence": {
    "eval_suite": "alert_triage_regression_2026_07_13",
    "precision_delta": 0.031,
    "recall_delta": 0.018,
    "latency_delta_ms": 42,
    "policy_violations": 0,
    "operator_rejection_rate_delta": -0.07
  },
  "risk_assessment": {
    "blast_radius": "mission-canary only",
    "rollback_seconds": 45,
    "known_risks": ["slightly longer rationale text"]
  },
  "approval_gate": "governance_review",
  "apollo_channel": "mission-canary"
}
```

### Delivery Plan and Operational Readiness

The safest implementation sequence establishes deterministic controls before enabling model-driven automation. Each milestone is independently deployable and reversible.

| Milestone | Deliverable | Exit gate | Accountable owner |
| --- | --- | --- | --- |
| M0 — authority and threat model | mission boundary, data classification, abuse cases, RACI, SLO/RTO/RPO, accreditation plan | security, privacy, legal, coalition, and operational owners approve the boundary | program executive |
| M1 — governed data plane | signed ingestion, quarantine, bronze/silver/gold datasets, lineage, initial Ontology | contract tests pass; replay is deterministic; unauthorized reads and cross-coalition joins fail | data platform owner |
| M2 — read-only operations | Gotham investigation views, workbench search, graph/timeline, evidence provenance | analyst acceptance tests; p95 objectives met; recovery exercise passes | mission application owner |
| M3 — advisory AI | AIP copilot, read-only typed tools, retrieval controls, eval harness, abstention | golden/adversarial eval gates pass; no consequential side effects exist | AI assurance owner |
| M4 — governed workflows | draft recommendations, approval service, action packages, append-only audit | forbidden-transition, replay, idempotency, and dual-control tests pass | operations owner |
| M5 — bounded improvement | feedback compiler, proposal registry, shadow and canary evaluation, Apollo rollback | signed human approval and tested rollback required for every promotion | change authority |
| M6 — production hardening | load/fault tests, backup restore, key rotation, incident drills, runbooks | operational review gates complete and observation window accepted | service owner |

Initial objectives must be baselined from representative workloads rather than treated as measured facts:

```yaml
service_objectives:
  alert_ingest:
    availability: "99.95% per mission month"
    p95_end_to_end_latency_ms: 1500
    maximum_event_loss: 0
  approval_plane:
    availability: "99.99% per mission month"
    rto_minutes: 15
    rpo: "zero committed approvals"
  analytical_plane:
    rto_minutes: 60
    rpo_minutes: 5
  audit_plane:
    maximum_event_loss: 0
    integrity_check: "continuous hash-chain verification plus independent WORM export"
```

Production admission requires a named service owner, change authority, incident commander rotation, data steward, security approver, and coalition release authority. Missing ownership is a release blocker, not an item that an agent may infer or self-assign.

### Deployment, Recovery, and Rollback Contract

1. Build immutable, signed application, prompt, workflow, model-route, and policy artifacts; record source commit, builder identity, SBOM, and eval evidence.
2. Deploy through Apollo rings: development → isolated integration → shadow → mission canary → production. No ring may inherit broader data or action permissions implicitly.
3. Keep database changes expand/contract compatible across the active and rollback versions. Destructive schema cleanup is a later, separately approved release.
4. Automatically halt or recall a canary on any policy violation, unauthorized disclosure, audit gap, approval bypass, statistically significant quality regression, or exhausted latency/error budget.
5. Restore the last known-good artifact bundle by content digest, disable affected tools with a server-side kill switch, replay idempotent events from the durable log, and reconcile side effects against the audit plane.
6. Validate recovery with synthetic mission data, permission-negative probes, audit-chain verification, queue-lag convergence, and operator sign-off before reopening consequential actions.

Rollback does not erase decisions or feedback. Audit records remain append-only; a compensating event records the rollback, its authority, reason, affected artifact digests, and reconciliation status.

---

## Security and Governance

### Access Control

- **AuthN**: OIDC, phishing-resistant MFA, hardware-backed workload identities, short-lived tokens.
- **AuthZ**: RBAC for broad duties, ABAC for mission/clearance/compartment/coalition/context, relationship-based checks for object ownership and case assignment.
- **Entity-level permissions**: each object has classification, compartments, allowed missions, coalition scope, and restricted attributes.
- **Row/column controls**: Foundry datasets expose only permitted rows and mask restricted columns such as PII, sources, or partner caveats.
- **Action controls**: ontology actions are policy-checked before execution and classified by side-effect level.

### Coalition Boundaries

- Coalition cells are represented as policy attributes on users, data, prompts, tools, and generated products.
- Agents receive only retrieval results permitted for the active coalition context.
- Generated products carry derivative classification and dissemination constraints computed from source lineage.
- Cross-coalition sharing requires explicit downgrade/release workflow and human review.

### Zero-Trust Execution

- Every service authenticates every call with workload identity.
- Tool execution runs in constrained sandboxes with egress controls, timeouts, resource quotas, and signed tool manifests.
- Prompts and model calls are treated as untrusted transformations: inputs are minimized, outputs are validated, and side effects are mediated by deterministic services.
- Secrets are never embedded in prompts, logs, eval examples, or generated products.

### Immutable Audit

Audit entries include:

```json
{
  "audit_id": "audit_01JZZ...",
  "ts": "2026-07-13T12:00:00Z",
  "actor_type": "agent",
  "actor_id": "triage-agent-v7",
  "human_supervisor": "operator-123",
  "action": "tool.call",
  "resource": { "type": "Alert", "id": "alert_abc" },
  "input_hash": "sha256:...",
  "output_hash": "sha256:...",
  "policy_version": "opa-bundle-44f3a",
  "prompt_version": "triage_prompt_v18",
  "workflow_version": "alert-triage-sm-v7",
  "model_route_version": "router-2026-07-13.2",
  "decision": "allow",
  "lineage_refs": ["dataset:events_silver@2026-07-13"]
}
```

### Governance Boards and SLOs

- **Prompt governance**: prompt diffs, eval results, red-team notes, injection tests, rollback plans.
- **Model governance**: model cards, sensitivity routes, latency/cost/SLO profiles, retirement plans.
- **Workflow governance**: state-machine diffs, action-gate impacts, concurrency/race analysis.
- **Policy governance**: Rego tests, change impact analysis, signed bundle rollout.

Target SLOs:

| Metric | Target |
| --- | --- |
| Hot-path alert triage p95 | < 1.5 seconds |
| Critical approval notification p95 | < 3 seconds |
| Unauthorized data exposure | 0 tolerated |
| Policy violation in eval/canary | 0 tolerated |
| Prompt rollback time | < 60 seconds |
| Operator trust score | > 4.3 / 5 |
| Recommendation precision | > 0.92 for high-impact recommendations |

---

## Code Examples

### AI Tool Registration

```python
# services/ai_orchestrator/tools.py
from pydantic import BaseModel, Field
from typing import Literal

class ToolManifest(BaseModel):
    name: str
    version: str
    side_effect: Literal["none", "reversible_write", "external_effect"]
    required_action: str
    approval_required: bool
    input_schema: dict

OPEN_CASE_TOOL = ToolManifest(
    name="case.open_from_alert",
    version="1.0.0",
    side_effect="reversible_write",
    required_action="case.open",
    approval_required=True,
    input_schema={
        "type": "object",
        "required": ["alert_id", "mission_id", "title"],
        "properties": {
            "alert_id": {"type": "string"},
            "mission_id": {"type": "string"},
            "title": {"type": "string", "minLength": 5, "maxLength": 160},
            "rationale": {"type": "string", "maxLength": 4000}
        },
        "additionalProperties": False
    }
)
```

### Tool Execution Guard

```python
# services/ai_orchestrator/executor.py
import jsonschema

class ToolExecutionDenied(Exception):
    pass

async def execute_tool(manifest, payload, ctx, policy_client, audit_writer, tool_impl):
    jsonschema.validate(payload, manifest.input_schema)

    allowed = await policy_client.allow(
        user=ctx.user,
        action=manifest.required_action,
        resource=payload,
        request={"mission_id": payload.get("mission_id"), "approval_id": ctx.approval_id},
    )
    if not allowed:
        await audit_writer.write_denied(manifest.name, payload, ctx)
        raise ToolExecutionDenied(f"Policy denied tool {manifest.name}")

    if manifest.approval_required and not ctx.approval_id:
        raise ToolExecutionDenied(f"Tool {manifest.name} requires approval")

    result = await tool_impl(payload, ctx)
    await audit_writer.write_allowed(manifest.name, payload, result, ctx)
    return result
```

### Feedback Capture

```python
# services/feedback_service/capture.py
from pydantic import BaseModel, Field
from typing import Literal

class FeedbackRequest(BaseModel):
    source: Literal["operator_correction", "edited_summary", "alert_outcome", "mission_result"]
    target_type: Literal["prompt", "workflow", "model_route", "entity", "alert", "recommendation"]
    target_id: str
    label: str = Field(max_length=200)
    correction_json: dict = Field(default_factory=dict)
    outcome: str = Field(max_length=2000)

async def capture_feedback(body: FeedbackRequest, ctx, redactor, dataset_writer):
    safe_correction = redactor.minimize_and_mask(body.correction_json, ctx.policy_context)
    record = {
        "source": body.source,
        "target_type": body.target_type,
        "target_id": body.target_id,
        "label": body.label,
        "correction_json": safe_correction,
        "outcome": body.outcome,
        "captured_by": ctx.user.user_id,
        "policy_version": ctx.policy_version,
        "lineage_refs": ctx.lineage_refs,
    }
    await dataset_writer.append("feedback_signals_bronze", record)
    return {"status": "captured"}
```

### Drift Detector

```python
# services/improvement_service/drift.py
from dataclasses import dataclass

@dataclass(frozen=True)
class DriftReport:
    metric: str
    value: float
    threshold: float
    status: str

class DriftDetector:
    def missing_field_rate(self, records: list[dict], field: str) -> DriftReport:
        if not records:
            return DriftReport(f"missing_{field}", 1.0, 0.05, "alert")
        rate = sum(1 for record in records if record.get(field) in (None, "")) / len(records)
        return DriftReport(f"missing_{field}", rate, 0.05, "alert" if rate > 0.05 else "ok")

    def correction_spike(self, current_rate: float, baseline_rate: float) -> DriftReport:
        ratio = current_rate / max(0.001, baseline_rate)
        return DriftReport("operator_correction_ratio", ratio, 1.5, "alert" if ratio > 1.5 else "ok")
```

---

### Python Precision Runtime Contract

ClearGlassInc Artemis uses Python for precision-critical backend paths where determinism, typed validation, and reproducible evaluation matter more than UI ergonomics. The production services should keep AI behavior behind typed contracts: inputs are validated with Pydantic, tool outputs are normalized into ontology objects, and every probabilistic recommendation is paired with deterministic policy and state-machine checks.

```text
services/
  artemis_api/
    main.py                 # FastAPI gateway and request provenance
    auth.py                 # OIDC claims, mission context, coalition scopes
    policy.py               # OPA client and fail-closed policy checks
  artemis_ontology/
    objects.py              # Pydantic ontology objects and relationships
    permissions.py          # entity/row/column authorization helpers
    lineage.py              # provenance and temporal validity utilities
  artemis_agents/
    router.py               # model and tool routing under policy constraints
    tools.py                # read/write tools with approval gates
    workflows.py            # deterministic workflow state machines
  artemis_improvement/
    feedback.py             # operator correction capture and minimization
    evals.py                # regression eval generation and scoring
    proposals.py            # prompt/workflow/router upgrade proposals
    drift.py                # distribution and outcome drift detectors
```

Precision-critical rules:

1. **No untyped tool I/O**: every AIP tool request and response must have a schema, policy context, lineage reference, and audit identifier.
2. **No direct autonomous writes for consequential actions**: agents may create proposed actions, but state changes that affect operations require approval objects and policy checks.
3. **No hidden self-upgrades**: prompt, workflow, heuristic, and model-router changes are versioned artifacts promoted only through eval gates and Apollo release channels.
4. **No lossy evidence chains**: summaries must retain source references, confidence, temporal validity, and derivative classification metadata.

```python
# services/artemis_ontology/objects.py
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator

class ConfidenceBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class LineageRef(BaseModel):
    source_system: str
    dataset_rid: str
    record_id: str
    observed_at: datetime
    transform_version: str

class MissionEntity(BaseModel):
    entity_id: str = Field(pattern=r"^[A-Z0-9:_-]{8,128}$")
    entity_type: str
    mission_id: str
    coalition_scope: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_band: ConfidenceBand
    valid_from: datetime
    valid_to: datetime | None = None
    lineage: list[LineageRef]

    @field_validator("coalition_scope")
    @classmethod
    def non_empty_scope(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("coalition_scope is required for every mission entity")
        return sorted(set(value))
```

```python
# services/artemis_agents/risk.py
from dataclasses import dataclass

@dataclass(frozen=True)
class TriageInputs:
    source_reliability: float
    asset_criticality: float
    actor_confidence: float
    corroboration_count: int
    policy_sensitivity: float

def deterministic_triage_score(inputs: TriageInputs) -> float:
    corroboration = min(inputs.corroboration_count, 5) / 5
    raw = (
        0.30 * inputs.source_reliability
        + 0.25 * inputs.asset_criticality
        + 0.20 * inputs.actor_confidence
        + 0.15 * corroboration
        - 0.10 * inputs.policy_sensitivity
    )
    return max(0.0, min(1.0, round(raw, 4)))

def escalation_band(score: float) -> str:
    if score >= 0.80:
        return "commander_review"
    if score >= 0.55:
        return "analyst_review"
    return "monitor"
```


---

## Defensive Algorithm Operating Prompt

Artemis includes a reusable defensive-algorithm prompt for AIP copilots, triage agents, policy agents, and runtime guardians. It is designed to protect systems, data, identities, and workflows while keeping operational disruption proportional to verified risk.

### Standard Guardian Prompt

```text
You are a defensive algorithm designed to protect systems, data, identities, and workflows.

Mission:
Detect risk early, prevent harm, reduce exposure, and respond safely to threats without causing unnecessary disruption.

Operating principles:
- Prioritize safety, containment, and verification.
- Prefer prevention over reaction.
- Minimize false positives, but never ignore credible threats.
- Use least privilege and only the minimum access needed.
- Preserve logs, audit trails, and evidence of suspicious activity.
- If uncertainty is high, escalate rather than assume safety.
- Never take destructive action without a clear confidence threshold and approval path.

Core responsibilities:
1. Monitor inputs, events, and system changes for anomalies.
2. Classify risk by severity, confidence, and blast radius.
3. Block or quarantine suspicious actions when thresholds are met.
4. Recommend the safest next step instead of over-automating.
5. Require explicit confirmation for high-impact changes.
6. Continuously learn from outcomes, misses, and false alarms.

Decision framework:
- Low risk: observe and log.
- Medium risk: warn, constrain, and request verification.
- High risk: isolate, halt, and escalate.
- Critical risk: contain immediately, preserve evidence, and notify operators.

Output format:
For every event, return:
- Risk level
- Why it was flagged
- Recommended action
- Confidence level
- Expected impact
- Whether human approval is required

Safety rules:
- Never widen access automatically.
- Never merge identities without confirmation.
- Never deploy unverified changes to production.
- Never overwrite evidence.
- Never suppress alerts without justification.
- Never optimize for convenience over security.

Final instruction:
Act as a calm, strict guardian system. Protect first, verify second, and only then allow execution.
```

### High-Reliability Version

```text
You are a high-reliability defensive algorithm for security, privacy, and operational integrity.

Your job is to detect threats, score risk, prevent unsafe actions, and guide the system toward the least harmful response. Treat every uncertain signal as a potential warning until verified. Use conservative thresholds for access changes, identity linking, workflow deployment, and data movement. Preserve evidence, minimize privilege, and always prefer reversible actions.

For each event, produce:
- classification
- severity
- confidence
- affected assets
- recommended containment
- recommended verification step
- approval requirement
- audit note

Decision rules:
- If confidence is low and impact is low, monitor.
- If confidence is moderate or impact is medium, restrict and verify.
- If confidence is high or impact is high, contain and escalate.
- If identity, credentials, or production systems are involved, require explicit human approval.

What this algorithm should optimize for:
- trust
- containment
- resilience
- explainability
- reversibility
- auditability
```

### Artemis Integration Pattern

- **Cybersecurity monitoring:** bind the prompt to read-only enrichment tools, containment proposal tools, and an approval-gated quarantine action.
- **Account-link protection:** require evidence-backed identity resolution, dual-control review, and a merge preview before any identity-link action.
- **AI prompt-injection defense:** classify retrieved content as data unless it is system-authorized instruction, then quarantine suspicious context and preserve the source snippet for review.
- **CI/CD workflow defense:** require signed artifacts, eval pass rates, policy checks, and Apollo rollback plans before any production deployment.

---

## Scenario Walkthrough

### 1. Live Event Enters
At 12:00:00Z, a partner telemetry feed sends an `unexpected_data_transfer` event involving a mission-critical dataset. The ingestion gateway validates schema, verifies source signature, assigns lineage references, and publishes to `events.raw.mission-7.alpha`.

### 2. Hot-Path Triage
The alert service consumes the event, normalizes it into the Foundry silver dataset, and runs deterministic scoring. The event score is high because source reliability is strong and impacted asset criticality is mission-critical. AIP triage receives only policy-filtered context and calls read-only tools for deduplication, related actor lookup, and graph expansion.

### 3. Agent Recommendation
The enrichment agent finds two prior related events and a weak actor association. The synthesis agent drafts a concise timeline with confidence labels. The recommendation agent proposes: open an investigation case, notify the mission cell, and request additional collection. It cannot execute those actions directly. It creates a `Recommendation` object in `proposed` state with risk, confidence, evidence, policy constraints, and required approval gate.

### 4. Operator Approval or Rejection
The Analyst Workbench shows the recommendation in the approval inbox. The operator inspects lineage, graph links, and uncertainty. If approved, the case service transitions the case to `pending_approval` or `actioned` only when state-machine and policy checks pass. If rejected, the operator must provide a reason such as “actor association too weak” or “duplicate of known benign transfer.”

### 5. Learning Signal
The feedback service captures the approval/rejection, edited rationale, final alert outcome, and case closure label. Sensitive content is minimized, masked, and stored as a `FeedbackSignal` with lineage and policy metadata.

### 6. Eval Generation
The improvement service converts the signal into an eval example: given similar source reliability, asset criticality, and actor-confidence conditions, should the triage workflow escalate, suppress, or ask for more evidence? The eval example is permission-scoped and cannot expose restricted raw data to unauthorized reviewers.

### 7. Self-Upgrade Proposal
After enough examples accumulate, Artemis generates a prompt/workflow proposal: increase the requirement for actor-confidence before recommending commander notification, but preserve case-opening behavior for mission-critical assets. Offline evals show improved precision with no recall regression and zero policy violations.

### 8. Human Review and Apollo Canary
The Governance Console shows a diff, eval metrics, sample failures, risk assessment, and rollback plan. A human governance reviewer approves canary deployment. Apollo releases the candidate to a mission-canary channel with feature flags and live telemetry.

### 9. Promote or Rollback
If canary precision, latency, operator trust, and policy metrics meet thresholds, Apollo promotes the update to production. If rejection rate spikes or policy tests fail, Apollo rolls back to the prior prompt/workflow/router bundle in under 60 seconds. The audit log records every artifact version, approval, deployment event, and rollback decision.

---

## Executable Verification Harness

The blueprint is paired with Python regression tests for the precision-critical control points in the reference implementation:

- **Self-improvement eval gates** must block candidate prompt/workflow/router versions when human approval is missing or quality thresholds regress.
- **Apollo canary promotion review** must deny unsafe rollback manifests and append a tamper-evident audit decision.
- **Human approval gates** must still enforce deterministic policy constraints; an analyst approval request cannot authorize a high-risk action that requires commander authority.
- **Feedback-to-eval compilation** must preserve stable artifact IDs, workflow versions, and operator correction labels without embedding unnecessary source payloads.

These tests keep the architecture honest: Artemis can propose better prompts, workflows, heuristics, and routing decisions, but promotion remains gated by eval evidence, policy, rollback safety, and explicit human approval.

---

## Remaining Engineering Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Prompt injection through retrieved documents | content isolation, instruction hierarchy, retrieval sanitization, tool-call schemas, policy mediation |
| Overfitting to operator behavior | holdout evals, cross-mission validation, governance review, drift monitoring |
| Coalition data leakage through generated summaries | derivative classification, source-aware output filtering, redaction and release workflow |
| Alert storms causing latency spikes | backpressure, priority queues, bounded retries, autoscaling, circuit breakers |
| Silent model regression | continuous evals, shadow mode, canary, rollback, model cards |
| Unsafe autonomy creep | hard-coded approval gates, policy-as-code, immutable audit, no autonomous mission-goal changes |

ClearGlassInc Artemis therefore becomes more capable over time by converting real operational evidence into governed, tested, human-approved upgrades while preserving accountability, coalition boundaries, and operator command authority.
