# ClearGlassInc Artemis: Global NET-Aware Self-Evolving AI Intelligence Platform

> Production architecture and implementation blueprint for a secure, coalition-aware, audited, real-time intelligence system built on Palantir Gotham, Foundry, AIP, and Apollo. The platform can ingest live and historical sources, including ionospheric products such as Global NET F2-layer electron-density maps, reason over operational context, learn from operator feedback, and propose self-upgrades only inside explicit human-approved guardrails.

## System Architecture

### Mission intent

**ClearGlassInc Artemis** is a mission-critical intelligence platform for secure multi-domain operations. It combines:

- **Gotham** for operational intelligence, investigations, link analysis, cases, missions, watchlists, and entity tracking.
- **Foundry** for data integration, lakehouse pipelines, ontology-backed application logic, lineage, quality, permissions, and productized datasets.
- **AIP** for governed copilots, tool-using agents, evaluations, prompt governance, model routing, and workflow automation.
- **Apollo** for signed deployment, environment promotion, ring rollout, runtime controls, rollback, policy bundle delivery, and kill switches.

The design treats the **ontology as the operating system**: human workflows, AI tools, permissions, evidence lineage, mission state, and feedback loops all bind to ontology objects and relationships rather than loose tables or ad hoc prompts.

### End-to-end topology

```text
[Live Feeds / Historical Stores / GNSS RO / Global NET / OSINT / HUMINT / SIGINT]
          |
          v
[Secure Ingestion Edge] --> [Schema Registry] --> [Streaming Bus]
          |                                            |
          v                                            v
[Foundry Bronze Datasets] --> [Foundry Silver Pipelines] --> [Gold Data Products]
          |                         |                         |
          v                         v                         v
   [Raw Evidence]         [Entity Resolution]          [Ontology Objects]
                                                            |
                                                            v
[Gotham Mission Views] <--> [API Gateway + BFF] <--> [Backend Mission Services]
          ^                         |                         |
          |                         v                         v
          |                [Policy Decision Point]     [AIP Agent Runtime]
          |                         |                         |
          |                         v                         v
          +---------------- [Action Approval Gate] <-- [Model Router + Tools]
                                                            |
                                                            v
                                               [Eval, Feedback, Drift, Upgrade Lab]
                                                            |
                                                            v
                                             [Human Change Board + Apollo Rollout]
```

### Layered architecture

| Layer | Responsibility | Representative technologies |
|---|---|---|
| Frontend | Analyst console, commander board, copilot panel, graph/map/timeline views | Next.js, TypeScript, WebSockets, Cytoscape, deck.gl |
| API gateway | mTLS, JWT validation, request signing, rate shaping, audit envelope creation | Envoy, FastAPI BFF, OpenAPI, gRPC |
| Backend services | Cases, alerts, missions, evidence, feedback, agent orchestration, product generation | Python FastAPI, Temporal-style workflows, Postgres |
| Data layer | Batch/stream ingestion, feature store, lakehouse, retrieval indexes | Foundry datasets, object storage, vector DB, search |
| Ontology layer | Canonical entities, relationships, temporal facts, permissions, lineage | Foundry Ontology, Gotham object views |
| AI layer | Copilots, agents, model router, tool registry, eval harness | AIP, governed model endpoints, Python evaluators |
| Policy layer | Need-to-know, coalition boundaries, action approval, prompt/model governance | OPA/Rego-like policy-as-code, ABAC/PBAC |
| Observability | Logs, traces, metrics, eval dashboards, immutable audit | OpenTelemetry, SIEM, append-only ledger |
| Deployment | Signed artifacts, canaries, rollback, runtime config, kill switches | Apollo, GitOps, SLSA attestations |

## Data and Ontology

### Core ontology entities

```yaml
Person:
  keys: [person_id]
  properties: [name, aliases, nationality, role, risk_score, confidence]
  security: [classification, compartments, coalition_release]

Organization:
  keys: [org_id]
  properties: [name, type, jurisdiction, aliases, confidence]

Device:
  keys: [device_id]
  properties: [imei, imsi, serial, cyber_fingerprint, last_seen_at]

Asset:
  keys: [asset_id]
  properties: [asset_type, owner, operational_status, geofence]

Location:
  keys: [location_id]
  properties: [lat, lon, h3_cell, region, uncertainty_m]

Signal:
  keys: [signal_id]
  properties: [source_type, observed_at, payload_hash, confidence, feature_vector]

IonosphereObservation:
  keys: [iono_obs_id]
  properties:
    - model_name: Global NET
    - log_nf2
    - altitude_band_km
    - hemisphere
    - observed_at
    - geomagnetic_context
    - quality_score

Event:
  keys: [event_id]
  properties: [event_type, severity, start_time, end_time, location, confidence]

Case:
  keys: [case_id]
  properties: [title, mission_id, status, priority, owner, disposition]

Mission:
  keys: [mission_id]
  properties: [name, objective, commander, sop_version, coalition_scope]

IntelProduct:
  keys: [product_id]
  properties: [type, summary, citations, generated_by, approved_by]

FeedbackSignal:
  keys: [feedback_id]
  properties: [operator_id, target_ref, rating, correction, outcome, created_at]
```

### Relationships

```text
OBSERVED_AT(Signal -> Location, temporal_window)
MENTIONS(Signal -> Entity, confidence)
CORROBORATES(Signal -> Signal, confidence)
CONTRADICTS(Signal -> Signal, confidence)
ASSOCIATED_WITH(Person -> Organization, confidence, evidence_refs)
OWNS(Person|Organization -> Device|Asset, confidence)
PARTICIPATES_IN(Entity -> Event, role, confidence)
TRIGGERS(Event -> Alert, rule_version, model_version)
BELONGS_TO(Alert -> Case)
SUPPORTS(Evidence -> IntelProduct, citation_span)
AFFECTS(IonosphereObservation -> SignalPath, propagation_impact_score)
AUTHORIZED_FOR(User|Team -> Mission|Case|Entity, policy_ref)
```

### Confidence, lineage, and temporal state

Every object and edge carries:

```json
{
  "confidence_score": 0.84,
  "source_reliability": "B",
  "corroboration_count": 3,
  "lineage": {
    "dataset_rid": "foundry.dataset.raw.signal.v17",
    "transform_rid": "foundry.transform.entity-resolution.v42",
    "source_hash": "sha256:...",
    "ingested_at": "2026-06-29T00:00:00Z"
  },
  "temporal": {
    "observed_at": "2026-06-29T00:00:00Z",
    "valid_from": "2026-06-29T00:00:00Z",
    "valid_to": null,
    "asserted_at": "2026-06-29T00:02:11Z"
  },
  "security": {
    "classification": "SECRET",
    "compartments": ["ARTEMIS", "IONO", "COALITION-A"],
    "releasable_to": ["USA", "CAN", "GBR"]
  }
}
```

The same metadata drives AI behavior. An agent cannot summarize, correlate, or recommend action using evidence it is not authorized to see. Output classification is derived from the highest classified source plus policy transformations.

## AI and Agent Design

### Copilots

- **Analyst Copilot:** entity search, case summarization, timeline construction, hypothesis generation, evidence citation, contradiction detection.
- **Commander Copilot:** mission posture, top risks, recommended courses of action, confidence intervals, approval queues.
- **Data Steward Copilot:** schema quality, pipeline anomalies, ontology merge suggestions, lineage repair.
- **PromptOps Copilot:** proposes prompt variants, tool-routing changes, and evaluation additions; never deploys them without approval.

### Multi-agent workflows

```text
TriageAgent
  -> validates source, deduplicates event, estimates severity
EnrichmentAgent
  -> queries ontology, retrieves similar cases, adds geospatial and ionospheric context
CorrelationAgent
  -> links entities/events/signals and computes confidence
RedTeamAgent
  -> searches for contradictions, missing evidence, policy violations
RecommendationAgent
  -> drafts action package with options, risks, citations, and approval requirements
ProductAgent
  -> generates intel brief after operator approval
LearningAgent
  -> converts outcomes and feedback into eval cases and proposed upgrades
```

### Operational approval gates

| Action | Autonomous? | Approval gate |
|---|---:|---|
| Search authorized data | Yes | Policy check and audit |
| Summarize case | Yes | Citation and classification validation |
| Open low-priority case | Conditional | Mission SOP policy |
| Notify analyst | Yes | Rate limit and relevance threshold |
| Recommend response | Yes | Must be labeled recommendation only |
| Change watchlist | No | Human approval |
| Send external tasking | No | Commander approval |
| Deploy prompt/workflow/model routing update | No | Change board + Apollo rollout |

## Self-Improvement Loop

### Signals captured

```text
operator_feedback: ratings, comments, corrections, rejected recommendations
query_logs: search terms, successful paths, abandoned sessions
alert_outcomes: true positive, false positive, false negative, duplicate
mission_results: time-to-triage, action taken, post-mission assessment
agent_traces: prompt version, model route, tools called, latency, tokens, policy decisions
case_edits: human changes to generated summaries, labels, entity merges
```

### Upgrade pipeline

1. **Capture:** immutable event envelope records interaction, source versions, prompt versions, model versions, policy decisions, and final outcome.
2. **Label:** feedback service converts operator corrections into supervised examples and eval cases.
3. **Evaluate:** champion and challenger prompts/workflows run against historical holdout cases and synthetic edge cases.
4. **Propose:** LearningAgent produces a change proposal: prompt diff, routing rule diff, eval delta, risk assessment, rollback plan.
5. **Approve:** human review board approves, rejects, or asks for changes.
6. **Deploy:** Apollo ships approved changes through dev, staging, canary, and production rings.
7. **Monitor:** drift, latency, precision, recall, trust, and mission-impact metrics are watched continuously.
8. **Rollback:** automatic or manual rollback triggers on SLO breach, policy violation, regression, or operator trust drop.

### Guardrails

- The platform may optimize **how** it performs approved tasks, but may not invent new mission objectives.
- Prompt/workflow/model updates are proposed as signed change requests, not silently activated.
- All autonomous improvements are constrained to offline eval generation, dashboards, and recommendations.
- Production behavior changes require human approval and Apollo-controlled rollout.

## Full-Stack Implementation

### Repository shape

```text
artemis/
  apps/
    web-console/                 # Next.js analyst and commander UI
    api-gateway/                 # FastAPI BFF
  services/
    alert-service/
    case-service/
    feedback-service/
    agent-orchestrator/
    eval-service/
    policy-service/
  packages/
    ontology-client/
    aip-tools/
    schemas/
    telemetry/
  foundry/
    transforms/
    ontology/
    datasets/
  apollo/
    environments/
    rollout-policies/
  infra/
    terraform/
    helm/
  tests/
    evals/
    integration/
```

### Event contract

```json
{
  "event_id": "evt_01J...",
  "event_type": "signal.observed",
  "occurred_at": "2026-06-29T00:00:00Z",
  "producer": "secure-ingest-edge",
  "classification": "SECRET",
  "compartments": ["ARTEMIS", "IONO"],
  "payload_ref": "foundry://dataset/raw_signal/partition=...",
  "payload_hash": "sha256:...",
  "lineage": {"source": "global-net-feed", "schema_version": "1.0.0"}
}
```

### API surface

```http
POST /v1/events/ingest
POST /v1/cases
GET  /v1/cases/{case_id}
POST /v1/agents/run
POST /v1/feedback
POST /v1/evals/run
POST /v1/change-proposals
POST /v1/approvals/{proposal_id}/decision
```

## Security and Governance

### Access model

ClearGlassInc Artemis uses layered authorization:

- **AuthN:** hardware-backed identity, short-lived tokens, mTLS workload identity.
- **ABAC:** attributes such as clearance, citizenship, team, mission, shift, device posture.
- **PBAC:** purpose-bound access, e.g., “counter-space mission triage only.”
- **Entity-level controls:** sensitive objects and relationships enforce compartments independently.
- **Coalition release controls:** output cannot include unreleasable evidence or derived claims.
- **Just-in-time access:** break-glass requires reason, expiry, manager approval, and enhanced audit.

### Governance primitives

```yaml
prompt_governance:
  required_fields: [owner, purpose, data_allowed, tools_allowed, eval_suite, rollback_plan]
  approval: [mission_owner, model_risk_officer, security_officer]

model_governance:
  routing_constraints:
    - no_external_model_for_secret_data
    - latency_sensitive_tasks_prefer_small_local_model
    - high_impact_recommendations_require_reasoning_model_plus_red_team_agent

policy_governance:
  bundle_signing: required
  dry_run: required
  canary: required
  rollback_on_violation: true
```

## Code Examples

### FastAPI gateway with policy and audit envelope

```python
from datetime import datetime, timezone
from typing import Any
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="ClearGlassInc Artemis API")

class Principal(BaseModel):
    user_id: str
    clearance: str
    compartments: set[str]
    releasable_to: set[str]
    purpose: str

class AgentRunRequest(BaseModel):
    mission_id: str
    case_id: str | None = None
    objective: str
    classification: str
    compartments: list[str] = Field(default_factory=list)

class AuditEnvelope(BaseModel):
    request_id: str
    actor: str
    action: str
    resource: str
    decision: str
    at: datetime
    metadata: dict[str, Any]

def current_principal() -> Principal:
    return Principal(
        user_id="operator-17",
        clearance="SECRET",
        compartments={"ARTEMIS", "IONO", "COALITION-A"},
        releasable_to={"USA", "CAN", "GBR"},
        purpose="mission-triage",
    )

def authorize(principal: Principal, action: str, classification: str, compartments: list[str]) -> None:
    if classification == "SECRET" and principal.clearance not in {"SECRET", "TOP_SECRET"}:
        raise HTTPException(status_code=403, detail="insufficient clearance")
    if not set(compartments).issubset(principal.compartments):
        raise HTTPException(status_code=403, detail="compartment denied")
    if principal.purpose not in {"mission-triage", "case-investigation", "command-review"}:
        raise HTTPException(status_code=403, detail="purpose denied")

async def write_audit(envelope: AuditEnvelope) -> None:
    # Production: append to immutable ledger and SIEM sink.
    print(envelope.model_dump_json())

@app.post("/v1/agents/run")
async def run_agent(req: AgentRunRequest, principal: Principal = Depends(current_principal)):
    authorize(principal, "agent.run", req.classification, req.compartments)
    await write_audit(AuditEnvelope(
        request_id="req_generated",
        actor=principal.user_id,
        action="agent.run",
        resource=req.mission_id,
        decision="allow",
        at=datetime.now(timezone.utc),
        metadata={"case_id": req.case_id, "objective": req.objective},
    ))
    return {"run_id": "agent_run_123", "status": "queued"}
```

### Ontology-driven query

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class OntologyQuery:
    mission_id: str
    h3_cell: str
    start: datetime
    end: datetime
    min_confidence: float = 0.65

class FoundryOntologyClient:
    def query_correlated_events(self, query: OntologyQuery) -> list[dict]:
        # Production: call Foundry Ontology APIs with object security inherited.
        return [
            {
                "event_id": "evt_8842",
                "event_type": "gnss_degradation_anomaly",
                "confidence": 0.82,
                "related_objects": ["iono_obs_55", "signal_992", "asset_14"],
                "lineage_refs": ["foundry://dataset/global_net_gold/rid/..."]
            }
        ]
```

### Tool-using AIP agent skeleton

```python
from enum import Enum
from pydantic import BaseModel

class Gate(str, Enum):
    AUTO = "auto"
    HUMAN_APPROVAL = "human_approval"

class ToolResult(BaseModel):
    name: str
    data: dict
    citations: list[str]
    confidence: float

class ArtemisToolRegistry:
    def __init__(self, ontology: FoundryOntologyClient):
        self.ontology = ontology

    def query_ontology(self, args: dict) -> ToolResult:
        rows = self.ontology.query_correlated_events(OntologyQuery(**args))
        return ToolResult(
            name="query_ontology",
            data={"events": rows},
            citations=[row["lineage_refs"][0] for row in rows],
            confidence=max((row["confidence"] for row in rows), default=0.0),
        )

    def open_case(self, args: dict) -> ToolResult:
        if args.get("severity") in {"high", "critical"}:
            return ToolResult(
                name="open_case",
                data={"gate": Gate.HUMAN_APPROVAL, "reason": "high-impact case creation"},
                citations=[],
                confidence=1.0,
            )
        return ToolResult(name="open_case", data={"case_id": "case_123"}, citations=[], confidence=0.9)
```

### Workflow state machine

```python
from transitions import Machine

class IntelWorkflow:
    states = ["received", "triaged", "enriched", "correlated", "review_required", "approved", "rejected", "closed"]

    transitions = [
        {"trigger": "triage", "source": "received", "dest": "triaged"},
        {"trigger": "enrich", "source": "triaged", "dest": "enriched"},
        {"trigger": "correlate", "source": "enriched", "dest": "correlated"},
        {"trigger": "requires_review", "source": "correlated", "dest": "review_required"},
        {"trigger": "approve", "source": "review_required", "dest": "approved"},
        {"trigger": "reject", "source": "review_required", "dest": "rejected"},
        {"trigger": "close", "source": ["approved", "rejected"], "dest": "closed"},
    ]

    def __init__(self, case_id: str):
        self.case_id = case_id
        self.machine = Machine(model=self, states=self.states, transitions=self.transitions, initial="received")
```

### Eval pipeline for prompt and routing upgrades

```python
from statistics import mean
from pydantic import BaseModel

class EvalCase(BaseModel):
    case_id: str
    input_payload: dict
    expected_labels: set[str]
    required_citations: int

class EvalResult(BaseModel):
    precision: float
    recall: float
    citation_pass_rate: float
    p95_latency_ms: float
    policy_violations: int

class PromptCandidate(BaseModel):
    prompt_id: str
    version: str
    text: str

async def run_eval_suite(candidate: PromptCandidate, cases: list[EvalCase]) -> EvalResult:
    scores = []
    citation_passes = []
    latencies = []
    violations = 0
    for case in cases:
        output = await simulate_agent(candidate, case.input_payload)
        predicted = set(output["labels"])
        tp = len(predicted & case.expected_labels)
        precision = tp / max(len(predicted), 1)
        recall = tp / max(len(case.expected_labels), 1)
        scores.append((precision, recall))
        citation_passes.append(len(output.get("citations", [])) >= case.required_citations)
        latencies.append(output["latency_ms"])
        violations += int(output.get("policy_violation", False))
    return EvalResult(
        precision=mean(p for p, _ in scores),
        recall=mean(r for _, r in scores),
        citation_pass_rate=mean(1.0 if ok else 0.0 for ok in citation_passes),
        p95_latency_ms=sorted(latencies)[int(0.95 * (len(latencies) - 1))],
        policy_violations=violations,
    )

async def simulate_agent(candidate: PromptCandidate, payload: dict) -> dict:
    # Production: execute candidate in isolated AIP eval environment.
    return {"labels": ["gnss_degradation_anomaly"], "citations": ["foundry://..."], "latency_ms": 740, "policy_violation": False}
```

### SQL metrics for continuous improvement

```sql
CREATE TABLE agent_outcomes (
  run_id TEXT PRIMARY KEY,
  mission_id TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  workflow_version TEXT NOT NULL,
  model_route TEXT NOT NULL,
  operator_rating INTEGER CHECK (operator_rating BETWEEN 1 AND 5),
  alert_outcome TEXT CHECK (alert_outcome IN ('tp','fp','fn','duplicate','unknown')),
  latency_ms INTEGER NOT NULL,
  policy_violations INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

SELECT
  prompt_version,
  AVG(CASE WHEN alert_outcome = 'tp' THEN 1.0 ELSE 0.0 END) AS true_positive_rate,
  AVG(operator_rating) AS avg_operator_rating,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_latency_ms,
  SUM(policy_violations) AS policy_violations
FROM agent_outcomes
WHERE created_at > now() - interval '14 days'
GROUP BY prompt_version
ORDER BY true_positive_rate DESC, avg_operator_rating DESC;
```

### TypeScript UI component for approval queue

```tsx
import React from "react";

type ApprovalItem = {
  id: string;
  title: string;
  severity: "low" | "medium" | "high" | "critical";
  confidence: number;
  citations: string[];
  recommendation: string;
};

export function ApprovalQueue({ items, decide }: {
  items: ApprovalItem[];
  decide: (id: string, decision: "approve" | "reject") => Promise<void>;
}) {
  return (
    <section className="approval-queue">
      <h2>Commander Approval Queue</h2>
      {items.map(item => (
        <article key={item.id} className={`approval-card severity-${item.severity}`}>
          <header>
            <h3>{item.title}</h3>
            <span>{Math.round(item.confidence * 100)}% confidence</span>
          </header>
          <p>{item.recommendation}</p>
          <ul>{item.citations.map(c => <li key={c}>{c}</li>)}</ul>
          <footer>
            <button onClick={() => decide(item.id, "reject")}>Reject</button>
            <button onClick={() => decide(item.id, "approve")}>Approve</button>
          </footer>
        </article>
      ))}
    </section>
  );
}
```

## Scenario Walkthrough

### 00:00 UTC: live event enters

A Global NET-derived ionospheric anomaly and a GNSS signal degradation event arrive within the same H3 geocell. Foundry ingests both into bronze datasets, validates schemas, computes payload hashes, and promotes quality-controlled records into gold data products. The ontology creates an `IonosphereObservation`, a `Signal`, and an `Event` with temporal links and lineage.

### 00:02 UTC: platform triages

The TriageAgent sees elevated `log_nf2` variation, a coincident GNSS degradation alert, and two corroborating telemetry sources. It assigns severity `medium-high`, cites the Foundry data products, and sends a low-latency notification to the analyst console. No operational action is taken.

### 00:04 UTC: enrichment and correlation

The EnrichmentAgent queries Gotham case history and Foundry ontology objects. It finds a similar propagation-impact pattern from a previous solar-storm period and retrieves the associated mitigation playbook. The CorrelationAgent links the current event to affected assets, active missions, and communication paths.

### 00:06 UTC: recommendation

The RecommendationAgent proposes:

1. Increase monitoring cadence for affected GNSS-dependent assets.
2. Switch designated communications planning to alternate HF frequencies.
3. Open a case if degradation persists for 15 minutes or spreads to adjacent cells.

Because recommendations affect operational posture, they enter the commander approval queue with citations, confidence, alternatives, and risks.

### 00:08 UTC: operator decision

The commander approves increased monitoring but rejects automatic case creation. The rejection reason is captured: “case threshold too aggressive for transient ionospheric conditions.” The system records the decision, actor, policy bundle, prompt version, model route, evidence list, and final disposition in immutable audit logs.

### Post-event: safe learning

The LearningAgent converts the rejected threshold into an eval case. The Eval Service tests a challenger workflow that waits for persistence across three time windows before recommending case creation. The challenger improves false-positive rate without reducing recall on historical high-impact incidents. A change proposal is generated with metrics, diff, risk, and rollback plan.

### Human-approved upgrade

The mission review board approves the workflow update for canary only. Apollo deploys it to one mission cell, monitors false positives, latency, and operator trust, then either promotes it through rings or rolls it back automatically if SLOs degrade.

## How Artemis Gets Better Safely

The platform improves through measurable, governed iteration:

- **Precision:** percentage of recommendations that operators accept or that match verified outcomes.
- **Recall:** percentage of known incidents surfaced by the platform.
- **Latency:** p50/p95 time from event ingestion to triage and recommendation.
- **Trust:** operator ratings, edit distance between AI drafts and final products, rejection reasons.
- **Mission impact:** time saved, prevented duplicate work, reduced false positives, improved response time.
- **Safety:** zero unauthorized access, zero unreleasable disclosures, zero unapproved operational actions.

ClearGlassInc Artemis therefore becomes faster, more precise, and more trusted over time while remaining bounded by human intent, policy-as-code, immutable audit, and Apollo-controlled deployment.
