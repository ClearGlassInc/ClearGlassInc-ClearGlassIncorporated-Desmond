# ClearGlassInc Artemis 2040: Palantir-Native Self-Evolving AI Intelligence Platform

## Executive intent

ClearGlassInc Artemis is a secure, coalition-aware, multi-domain intelligence platform built on Palantir Gotham, Foundry, AIP, and Apollo. Its mission is to fuse live and historical data, reason over entities and missions at machine speed, support audited operator decisions, and safely improve its own prompts, workflows, heuristics, model routing, and evaluation suites under explicit human-approved guardrails.

The core principle is **governed autonomy**: agents may observe, recommend, simulate, and propose upgrades, but they cannot silently change operational objectives, bypass policy, or execute significant actions without approval.

## System Architecture

### Palantir role mapping

- **Gotham** provides operational intelligence, investigations, entity tracking, link analysis, watchlists, case workspaces, mission timelines, and commander-facing operational views.
- **Foundry** provides data integration, pipeline orchestration, ontology-backed objects, lineage, quality scoring, application logic, and governed data products.
- **AIP** provides copilots, agent orchestration, tool calling, secured model access, workflow automation, evaluations, prompt governance, and human-in-the-loop AI actions.
- **Apollo** provides deployment orchestration, runtime control, version promotion, staged rollouts, rollback, policy bundle distribution, and mission-environment update safety.

### End-to-end topology

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                           ClearGlassInc Artemis UI                         │
│  Next.js Command UI | Analyst Graph | Mission Feed | Eval Console | Admin  │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ OIDC + signed requests + WebSocket/SSE
┌───────────────────────────────▼────────────────────────────────────────────┐
│                             API Gateway / BFF                               │
│ FastAPI/TypeScript edge | schema validation | rate limits | request policy  │
└───────┬───────────────────────┬───────────────────────┬────────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐       ┌─────────────────┐      ┌───────────────────────────┐
│ Mission Svc   │       │ Ontology Svc    │      │ AI Orchestrator / AIP     │
│ cases/tasks   │       │ entity graph    │      │ copilots + agent runtime  │
└───────┬───────┘       └────────┬────────┘      └────────────┬──────────────┘
        │                        │                            │
        ▼                        ▼                            ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                       Event Bus / Streaming Fabric                          │
│ Kafka/Pulsar topics: raw.events, entity.updates, agent.actions, feedback    │
└───────────────┬───────────────────────────────────────────────┬────────────┘
                │                                               │
                ▼                                               ▼
┌───────────────────────────────┐               ┌────────────────────────────┐
│ Foundry Data + Ontology Layer │               │ Search / Retrieval Layer   │
│ pipelines, lineage, lakehouse │               │ graph, vector, BM25, OLAP  │
└───────────────┬───────────────┘               └──────────────┬─────────────┘
                │                                              │
                ▼                                              ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                 Policy, Governance, Observability, Apollo Ops               │
│ OPA/Rego | entity ABAC | immutable logs | OpenTelemetry | eval dashboards   │
└────────────────────────────────────────────────────────────────────────────┘
```

### Full-stack component blueprint

| Layer | Production responsibility | Preferred implementation |
|---|---|---|
| Frontend | Mission command UI, graph investigation, operator correction, approvals, eval dashboard | Next.js, React Query, WebSocket/SSE, Cytoscape/Sigma, MapLibre, Tailwind |
| API gateway | Request normalization, policy pre-checks, tenant and mission context injection | FastAPI or NestJS, Pydantic/Zod schemas, Envoy, mTLS |
| Backend services | Cases, alerts, tasks, entity merge, feedback, evals, products, workflow execution | Python FastAPI, async workers, Temporal, gRPC internally |
| Streaming | Live events, feedback, model telemetry, audit append events | Kafka/Pulsar with schema registry |
| Data layer | Raw lake, curated products, features, warehouse marts | Foundry datasets, Iceberg/Delta, Postgres, object storage |
| Ontology | Operational objects, links, actions, lineage, security labels | Foundry Ontology + graph index + temporal relational tables |
| Retrieval | Mission RAG, entity search, document search, graph expansion | OpenSearch/Elasticsearch, pgvector/Milvus, graph DB, rerankers |
| AI orchestration | Copilots, tool registry, multi-agent planning, model routing, eval gates | Palantir AIP, Python agents, policy-wrapped tools |
| Policy | Need-to-know, coalition boundaries, row/column/entity controls | OPA/Rego, Cedar-style decisions, Foundry markings |
| Observability | Logs, metrics, traces, eval scores, drift alerts, audit replay | OpenTelemetry, Prometheus, Grafana, immutable ledger |
| Deployment | Ring rollout, rollback, policy/model/prompt promotion | Apollo deployment tracks and runtime controls |

## Data and Ontology

### Ontology philosophy

The ontology is the operational brain of ClearGlassInc Artemis. It gives humans and agents the same mission vocabulary: people, organizations, assets, devices, locations, events, signals, reports, cases, missions, hypotheses, recommendations, approvals, and outcomes. Every object carries confidence, provenance, temporal state, mission context, classification, coalition permissions, and lineage.

### Core entities

```yaml
Ontology:
  Person:
    keys: [person_id]
    attributes: [canonical_name, aliases, identifiers, role, risk_score]
    markings: [classification_level, coalition_tags, need_to_know_labels]
  Organization:
    attributes: [legal_name, aliases, jurisdiction, sector, registration_refs]
  Asset:
    attributes: [asset_type, owner_ref, value_band, location_ref, operational_status]
  Device:
    attributes: [device_type, hardware_ids, network_ids, last_seen_at]
  Location:
    attributes: [geo_point, geo_hash, jurisdiction, facility_type]
  Event:
    attributes: [event_type, observed_at, source, severity, payload_hash]
  Signal:
    attributes: [signal_type, source_system, raw_ref, extraction_confidence]
  Indicator:
    attributes: [indicator_type, pattern, first_seen, last_seen, confidence]
  Case:
    attributes: [case_type, status, priority, lead_operator, mission_context_id]
  Mission:
    attributes: [mission_type, objective, commander, rules_of_engagement_ref]
  Hypothesis:
    attributes: [claim, supporting_evidence, contradicting_evidence, posterior]
  ActionRecommendation:
    attributes: [action_type, rationale, risk, confidence, required_approvals]
  Approval:
    attributes: [decision, approver, rationale, decided_at, policy_snapshot]
  Outcome:
    attributes: [mission_result, alert_truth_label, impact_score, lessons]
```

### Relationship graph

```text
Person --ASSOCIATED_WITH--> Organization
Person --USES--> Device
Device --OBSERVED_AT--> Location
Event --MENTIONS--> Person | Organization | Asset | Device
Signal --EXTRACTED_INDICATOR--> Indicator
Indicator --SUPPORTS_HYPOTHESIS--> Hypothesis
Hypothesis --PART_OF_CASE--> Case
Case --SUPPORTS_MISSION--> Mission
ActionRecommendation --RESPONDS_TO--> Event | Case | Mission
Approval --AUTHORIZES--> ActionRecommendation
Outcome --EVALUATES--> ActionRecommendation | Mission | Alert
```

### SQL schema for temporal, permissioned ontology storage

```sql
CREATE TABLE artemis_entity (
  entity_id UUID PRIMARY KEY,
  entity_type TEXT NOT NULL,
  canonical_name TEXT,
  attributes JSONB NOT NULL DEFAULT '{}',
  confidence_score NUMERIC(5,4) NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
  confidence_method TEXT NOT NULL,
  classification_level TEXT NOT NULL CHECK (classification_level IN ('U','C','S','TS')),
  coalition_tags TEXT[] NOT NULL DEFAULT '{}',
  need_to_know_labels TEXT[] NOT NULL DEFAULT '{}',
  mission_context_id UUID,
  valid_from TIMESTAMPTZ NOT NULL,
  valid_to TIMESTAMPTZ,
  transaction_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  transaction_to TIMESTAMPTZ,
  lineage_ref TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  provenance_hash TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE artemis_relation (
  relation_id UUID PRIMARY KEY,
  src_entity_id UUID NOT NULL REFERENCES artemis_entity(entity_id),
  dst_entity_id UUID NOT NULL REFERENCES artemis_entity(entity_id),
  relation_type TEXT NOT NULL,
  relation_strength NUMERIC(5,4) NOT NULL CHECK (relation_strength BETWEEN 0 AND 1),
  evidence_refs TEXT[] NOT NULL,
  confidence_score NUMERIC(5,4) NOT NULL,
  classification_level TEXT NOT NULL,
  coalition_tags TEXT[] NOT NULL DEFAULT '{}',
  mission_context_id UUID,
  valid_from TIMESTAMPTZ NOT NULL,
  valid_to TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE artemis_feedback_signal (
  feedback_id UUID PRIMARY KEY,
  operator_id TEXT NOT NULL,
  mission_context_id UUID NOT NULL,
  target_type TEXT NOT NULL,
  target_id UUID NOT NULL,
  feedback_kind TEXT NOT NULL,
  correction JSONB,
  rating INTEGER CHECK (rating BETWEEN 1 AND 5),
  outcome_label TEXT,
  free_text TEXT,
  policy_snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### How ontology drives workflows and agents

- Human workflows use ontology objects as canonical units for cases, tasking, alerts, and intelligence products.
- Agent tools receive ontology object IDs rather than unbounded raw prompts, reducing hallucination and improving traceability.
- Confidence and lineage fields determine whether an agent may summarize, recommend, or escalate.
- Temporal fields prevent agents from treating stale signals as current intelligence.
- Permission markings are enforced before retrieval, after retrieval, and before generation.

## AI and Agent Design

### Copilot suite

1. **Analyst Copilot**: summarizes cases, proposes hypotheses, identifies missing evidence, asks clarifying questions, and drafts intelligence notes.
2. **Commander Copilot**: explains operational posture, escalations, risk bands, decision options, and likely second-order effects.
3. **Watchfloor Copilot**: clusters live alerts, suppresses likely duplicates, highlights novelty, and routes triage work.
4. **Governance Copilot**: shows why an answer was allowed or denied, cites policy, and prepares review packets.
5. **PromptOps Copilot**: analyzes eval failures and proposes prompt, tool, routing, or workflow changes for approval.

### Multi-agent workflow

```text
Live Event
  -> Triage Agent
  -> Enrichment Agent
  -> Correlation Agent
  -> Hypothesis Agent
  -> Recommendation Agent
  -> Compliance Agent
  -> Product Agent
  -> Human Approval Gate
  -> Outcome Capture
  -> Evaluation + Self-Improvement Proposal
```

### Agent constraints

- Agents can query only policy-filtered tools.
- Agents must cite object IDs, evidence references, and lineage hashes for material claims.
- Agents cannot alter mission objectives, security labels, approval thresholds, or coalition rules.
- Agents cannot execute operationally significant actions; they can prepare an action package for operator approval.
- Agents must run through eval gates for high-impact recommendations.

### AIP tool contract pattern

```python
from pydantic import BaseModel, Field
from typing import Literal, list
from uuid import UUID

class ToolContext(BaseModel):
    operator_id: str
    mission_context_id: UUID
    clearance: Literal['U', 'C', 'S', 'TS']
    coalition_tags: list[str]
    need_to_know_labels: list[str]
    request_id: str

class EntityQuery(BaseModel):
    entity_type: str | None = None
    text: str | None = None
    mission_context_id: UUID
    max_results: int = Field(default=25, le=100)

class EntityResult(BaseModel):
    entity_id: UUID
    entity_type: str
    display_name: str
    confidence_score: float
    lineage_ref: str
    redactions: list[str] = []
```

## Self-Improvement Loop

### Signals captured

ClearGlassInc Artemis continuously captures learning signals without allowing silent autonomous goal changes:

- Operator feedback: thumbs up/down, corrections, rejected rationales, edited summaries, approved action packets.
- Query logs: question type, retrieval path, latency, redactions, no-result events, follow-up behavior.
- Alert outcomes: true positive, false positive, duplicate, benign, escalated, missed detection.
- Mission outcomes: operational impact, time-to-decision, action success, downstream corrections.
- Model telemetry: model version, prompt version, route, token cost, latency, eval scores, refusal/denial reasons.
- Workflow telemetry: state transitions, bottlenecks, retries, approval delays, tool failures.

### Improvement pipeline

```text
1. Capture feedback and outcomes as immutable events.
2. Normalize signals into eval datasets and labeled examples.
3. Run nightly and on-demand eval suites by mission, model, prompt, and workflow version.
4. Detect regressions, drift, latency spikes, false-positive clusters, and trust degradation.
5. Generate candidate improvements: prompt patch, workflow edge change, heuristic threshold, router rule.
6. Simulate candidate against held-out evals and adversarial safety cases.
7. Open a governed ChangeProposal object with evidence, diff, expected effect, rollback plan.
8. Human reviewer approves, rejects, or requests changes.
9. Apollo deploys approved change to canary ring.
10. Compare champion vs challenger; promote, hold, or rollback.
11. Persist decision, metrics, and provenance to immutable audit ledger.
```

### Change proposal object

```json
{
  "proposal_id": "cp_2040_001",
  "change_type": "prompt_patch",
  "target": "triage_agent.system_prompt",
  "current_version": "triage-prompt@18",
  "candidate_version": "triage-prompt@19",
  "reason": "False-positive rate increased on duplicate financial indicators.",
  "expected_effect": {"precision_delta": 0.04, "latency_delta_ms": 0},
  "eval_summary": {"pass_rate": 0.982, "safety_cases_passed": 94, "regressions": 0},
  "required_approvers": ["mission_owner", "ai_governance_lead"],
  "rollback": {"apollo_release": "triage-prompt@18", "max_rollback_seconds": 90},
  "status": "pending_human_review"
}
```

### Safe versioning and rollback

- Every prompt, tool, policy bundle, router rule, eval set, and workflow definition is versioned.
- Apollo deploys approved changes through dev, staging, canary, and production mission rings.
- Rollback is automatic when critical metrics breach thresholds: safety failure, policy denial regression, latency SLO breach, precision cliff, or operator trust drop.
- Rollbacks preserve the failed version for audit and forensic review.

## Full-Stack Implementation

### Repository/service layout

```text
artemis/
  apps/
    command-ui/                 # Next.js mission UI
    eval-console/               # prompt/workflow/model governance UI
  services/
    api-gateway/                # FastAPI edge/BFF
    ontology-service/           # permission-aware entity graph API
    mission-service/            # cases, tasks, approvals, outcomes
    agent-orchestrator/         # AIP agents, tools, state machines
    feedback-service/           # feedback and correction capture
    eval-service/               # offline/online eval harness
    policy-service/             # OPA/Rego wrapper and policy decisions
  pipelines/
    foundry_transforms/         # ingestion, normalization, ontology writes
    eval_builders/              # labeled dataset generation
  infra/
    apollo/                     # release channels and runtime controls
    policy/                     # Rego bundles
    observability/              # dashboards and alerts
```

### Event topics

```yaml
topics:
  raw.intel.events: source-normalized events from sensors, partner feeds, OSINT, and enterprise systems
  ontology.entity.updates: entity upserts, merges, confidence changes, lineage changes
  mission.alerts: triaged alerts ready for watchfloor review
  agent.actions: tool calls, planned actions, recommendations, refusals
  operator.feedback: corrections, ratings, approvals, rejections, edited outputs
  mission.outcomes: truth labels, impact, final disposition
  eval.results: eval scores, drift alerts, regression findings
  governance.change_proposals: proposed self-upgrades awaiting human review
```

### Backend API sketch

```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID

app = FastAPI(title="ClearGlassInc Artemis API")

class Principal(BaseModel):
    sub: str
    clearance: str
    coalition_tags: list[str]
    need_to_know_labels: list[str]

class ApproveActionRequest(BaseModel):
    recommendation_id: UUID
    decision: str
    rationale: str

async def current_principal() -> Principal:
    # Production: validate OIDC token, mTLS identity, and mission session binding.
    return Principal(
        sub="operator.demo",
        clearance="S",
        coalition_tags=["USA", "FVEY"],
        need_to_know_labels=["ARTEMIS-OPS"]
    )

@app.post("/missions/{mission_id}/recommendations/{recommendation_id}/approval")
async def approve_recommendation(
    mission_id: UUID,
    recommendation_id: UUID,
    body: ApproveActionRequest,
    principal: Principal = Depends(current_principal),
):
    allowed = await policy_decide(
        principal=principal,
        action="approve_recommendation",
        resource={"mission_id": str(mission_id), "recommendation_id": str(recommendation_id)}
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Policy denied approval action")

    approval = await mission_service.record_approval(
        mission_id=mission_id,
        recommendation_id=recommendation_id,
        approver=principal.sub,
        decision=body.decision,
        rationale=body.rationale,
    )
    await audit_log("approval.recorded", principal.sub, approval.model_dump())
    return approval
```

### Workflow state machine

```python
from enum import Enum
from pydantic import BaseModel

class TriageState(str, Enum):
    RECEIVED = "received"
    POLICY_FILTERED = "policy_filtered"
    ENRICHED = "enriched"
    CORRELATED = "correlated"
    RECOMMENDED = "recommended"
    COMPLIANCE_REVIEWED = "compliance_reviewed"
    AWAITING_HUMAN = "awaiting_human"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"

class WorkflowTransition(BaseModel):
    from_state: TriageState
    to_state: TriageState
    actor: str
    reason: str
    evidence_refs: list[str]

ALLOWED_TRANSITIONS = {
    TriageState.RECEIVED: {TriageState.POLICY_FILTERED},
    TriageState.POLICY_FILTERED: {TriageState.ENRICHED},
    TriageState.ENRICHED: {TriageState.CORRELATED},
    TriageState.CORRELATED: {TriageState.RECOMMENDED},
    TriageState.RECOMMENDED: {TriageState.COMPLIANCE_REVIEWED},
    TriageState.COMPLIANCE_REVIEWED: {TriageState.AWAITING_HUMAN},
    TriageState.AWAITING_HUMAN: {TriageState.APPROVED, TriageState.REJECTED},
    TriageState.APPROVED: {TriageState.CLOSED},
    TriageState.REJECTED: {TriageState.CLOSED},
}

def transition(current: TriageState, target: TriageState) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"Illegal transition: {current} -> {target}")
```

## Security and Governance

### Access control model

Security is enforced as a layered decision, not a single middleware check:

1. **Authentication**: OIDC, mTLS service identity, device posture, session binding.
2. **Authorization**: clearance, coalition tags, need-to-know labels, mission role, action sensitivity.
3. **Entity filtering**: row, column, field, relationship, and object-level policy.
4. **Tool control**: agents call only registered tools with scoped permissions.
5. **Output control**: generated text is scanned for unauthorized leakage and unsupported claims.
6. **Audit**: every query, tool call, generation, decision, approval, and deployment is immutably logged.

### Rego policy example

```rego
package artemis.authz

default allow := false

clearance_rank := {"U": 0, "C": 1, "S": 2, "TS": 3}

allow if {
  input.action == "read_entity"
  clearance_rank[input.principal.clearance] >= clearance_rank[input.resource.classification_level]
  every tag in input.resource.coalition_tags { tag in input.principal.coalition_tags }
  every label in input.resource.need_to_know_labels { label in input.principal.need_to_know_labels }
}

allow if {
  input.action == "approve_recommendation"
  input.principal.role in {"mission_commander", "senior_operator"}
  input.resource.impact != "strategic" # strategic actions require dual approval policy
}
```

### Governance objects

- `ModelCard`: model purpose, training data boundary, approved missions, limitations, eval history.
- `PromptCard`: owner, allowed tools, safety constraints, version, eval baseline, rollback target.
- `WorkflowCard`: state graph, approval gates, allowed autonomous transitions, maximum impact level.
- `PolicyBundle`: Rego version, signing key, reviewer approvals, Apollo release ring.
- `ChangeProposal`: candidate self-upgrade, evidence, eval results, risk, approvers, rollback.

## Code Examples

### Permission-aware ontology query

```python
async def query_entities(query: EntityQuery, ctx: ToolContext) -> list[EntityResult]:
    rows = await db.fetch_all(
        """
        SELECT entity_id, entity_type, canonical_name, confidence_score,
               lineage_ref, classification_level, coalition_tags, need_to_know_labels
        FROM artemis_entity
        WHERE ($1::text IS NULL OR entity_type = $1)
          AND mission_context_id = $2
          AND transaction_to IS NULL
        ORDER BY confidence_score DESC
        LIMIT $3
        """,
        query.entity_type,
        query.mission_context_id,
        query.max_results,
    )

    results: list[EntityResult] = []
    for row in rows:
        allowed, redactions = await policy_filter_entity(row, ctx)
        if not allowed:
            await audit_log("ontology.entity.redacted", ctx.operator_id, {
                "entity_id": str(row["entity_id"]),
                "reason": redactions,
                "request_id": ctx.request_id,
            })
            continue
        results.append(EntityResult(
            entity_id=row["entity_id"],
            entity_type=row["entity_type"],
            display_name=row["canonical_name"],
            confidence_score=float(row["confidence_score"]),
            lineage_ref=row["lineage_ref"],
            redactions=redactions,
        ))
    return results
```

### Agent recommendation with approval gate

```python
class Recommendation(BaseModel):
    summary: str
    action_type: str
    rationale: str
    confidence: float
    risk: str
    evidence_refs: list[str]
    requires_human_approval: bool = True

async def recommend_response(event_id: UUID, ctx: ToolContext) -> Recommendation:
    event = await load_policy_filtered_event(event_id, ctx)
    related = await query_entities(EntityQuery(
        entity_type=None,
        mission_context_id=ctx.mission_context_id,
        max_results=50,
    ), ctx)

    prompt = build_recommendation_prompt(event=event, related=related)
    draft = await model_router.generate(
        task="mission_recommendation",
        prompt=prompt,
        policy_context=ctx.model_dump(),
        eval_gate="high_impact_recommendation_v7",
    )

    recommendation = Recommendation.model_validate_json(draft)
    if recommendation.risk in {"high", "strategic"}:
        recommendation.requires_human_approval = True

    await audit_log("agent.recommendation.created", ctx.operator_id, {
        "event_id": str(event_id),
        "recommendation": recommendation.model_dump(),
    })
    return recommendation
```

### Eval pipeline for prompt and workflow upgrades

```python
class EvalCase(BaseModel):
    case_id: str
    input_payload: dict
    expected_label: str
    safety_tags: list[str]
    mission_type: str

class EvalResult(BaseModel):
    case_id: str
    passed: bool
    precision_hit: bool
    latency_ms: int
    policy_violations: int
    notes: str

async def run_eval_suite(candidate_version: str, eval_cases: list[EvalCase]) -> dict:
    results: list[EvalResult] = []
    for case in eval_cases:
        started = monotonic_ms()
        output = await model_router.generate(
            task="triage",
            prompt_version=candidate_version,
            prompt=case.input_payload["prompt"],
            policy_context=case.input_payload["policy_context"],
            eval_mode=True,
        )
        latency = monotonic_ms() - started
        policy_violations = await scan_policy_violations(output, case.input_payload)
        predicted = parse_label(output)
        results.append(EvalResult(
            case_id=case.case_id,
            passed=(predicted == case.expected_label and policy_violations == 0),
            precision_hit=(predicted == case.expected_label),
            latency_ms=latency,
            policy_violations=policy_violations,
            notes="ok" if policy_violations == 0 else "policy violation detected",
        ))

    return {
        "candidate_version": candidate_version,
        "pass_rate": sum(r.passed for r in results) / len(results),
        "precision": sum(r.precision_hit for r in results) / len(results),
        "p95_latency_ms": percentile([r.latency_ms for r in results], 95),
        "policy_violations": sum(r.policy_violations for r in results),
        "results": [r.model_dump() for r in results],
    }
```

### Drift detector

```python
def detect_drift(baseline: dict, current: dict) -> list[str]:
    alerts: list[str] = []
    if current["precision"] < baseline["precision"] - 0.03:
        alerts.append("precision_regression")
    if current["false_positive_rate"] > baseline["false_positive_rate"] + 0.05:
        alerts.append("false_positive_spike")
    if current["p95_latency_ms"] > baseline["p95_latency_ms"] * 1.25:
        alerts.append("latency_regression")
    if current["operator_trust"] < baseline["operator_trust"] - 0.10:
        alerts.append("operator_trust_drop")
    return alerts
```

### Analytics dashboard JSON

```json
{
  "dashboard": "clearGlassInc_artemis_self_improvement_kpis",
  "period": "rolling_90_days",
  "metrics": [
    {"name": "triage_precision", "target": ">=0.92", "source": "eval.results"},
    {"name": "triage_recall", "target": ">=0.88", "source": "eval.results"},
    {"name": "p95_agent_latency_ms", "target": "<=2500", "source": "otel.traces"},
    {"name": "operator_trust_score", "target": ">=4.3/5", "source": "operator.feedback"},
    {"name": "policy_violation_rate", "target": "0", "source": "policy.decisions"},
    {"name": "approved_self_upgrades", "target": ">=2/month", "source": "governance.change_proposals"},
    {"name": "rollback_time_seconds", "target": "<=90", "source": "apollo.deployments"},
    {"name": "mission_time_to_decision", "target": "-30% quarter over quarter", "source": "mission.outcomes"}
  ]
}
```

## Scenario Walkthrough

### 1. Live event enters

At 02:14 UTC, a partner feed emits a high-volume anomaly involving a supplier organization, a newly observed device, and a financial transfer pattern. The raw event lands on `raw.intel.events` with source metadata, classification markings, and a payload hash.

### 2. Foundry normalizes and links

Foundry pipelines validate schema, attach lineage, deduplicate the supplier entity, create a new `Device`, and link the device to a location and a prior case through `OBSERVED_AT` and `SUPPORTS_HYPOTHESIS` relationships. Confidence starts at 0.71 because two independent sources agree but one field is stale.

### 3. AIP triages

The Triage Agent classifies the event as `financial_intrusion_possible`, severity `high`, novelty `medium`, and routes it to the Watchfloor Copilot. The agent cites entity IDs, relation IDs, confidence values, and lineage references.

### 4. Enrichment and correlation

The Enrichment Agent queries the ontology, vector index, and graph expansion tool. The Correlation Agent finds a temporal pattern: similar device identifiers appeared in two closed false-positive cases and one confirmed intrusion. The system lowers confidence on one weak relation and raises confidence on the supplier-device link.

### 5. Recommendation package

The Recommendation Agent proposes an action package: open a case, notify the mission commander, request partner corroboration, and place the supplier on a temporary enhanced-monitoring watchlist. The Compliance Agent blocks one proposed data-sharing clause because the target partner lacks a required need-to-know label.

### 6. Human approval

The operator sees the package in Gotham: evidence graph, timeline, source lineage, policy denial reason, and a generated brief. The operator approves case creation and monitoring, rejects the partner-sharing clause, and adds a correction: the supplier's jurisdiction was misclassified.

### 7. Outcome and learning

The feedback service writes the approval, rejection, correction, and final rationale to `operator.feedback`. Later, the case outcome is labeled true positive. The eval builder turns the event, agent output, operator correction, and outcome into a new eval case.

### 8. Self-improvement proposal

That night, the PromptOps Copilot notices repeated jurisdiction misclassification in similar supplier cases. It proposes a prompt patch and retrieval rule: require jurisdiction corroboration from the authoritative registry before generating recommendations that depend on jurisdiction. The proposal includes eval results, a diff, expected precision lift, and rollback plan.

### 9. Approval, canary, rollback safety

The AI governance lead approves the candidate. Apollo deploys it to the canary ring for one mission cell. Metrics improve: jurisdiction accuracy rises, latency stays inside SLO, and policy violations remain zero. The change is promoted. If precision had dropped or latency had breached the threshold, Apollo would have rolled back to the prior prompt and router bundle within 90 seconds.

## Operating Metrics

| Metric | Target | Why it matters |
|---|---:|---|
| Triage precision | >= 0.92 | Reduces operator fatigue and false escalations |
| Triage recall | >= 0.88 | Prevents missed mission-relevant events |
| P95 agent latency | <= 2.5s for triage, <= 10s for deep correlation | Keeps watchfloor operations real-time |
| Operator trust | >= 4.3/5 | Measures practical adoption and explainability |
| Policy violation rate | 0 | Non-negotiable for coalition operations |
| Evidence citation coverage | >= 98% | Ensures claims are traceable |
| Approved self-upgrades | >= 2/month | Demonstrates safe continuous improvement |
| Rollback time | <= 90s | Contains model, prompt, or workflow regressions |

## Build Sequence

1. Stand up identity, policy, audit, and Apollo release rings before agent autonomy.
2. Implement Foundry data products and ontology objects for `Event`, `Entity`, `Case`, `Mission`, and `Outcome`.
3. Launch the Analyst Copilot in read-only mode with strict citations and no operational actions.
4. Add triage and enrichment agents with human approval gates.
5. Capture feedback and outcomes into eval datasets.
6. Launch prompt/workflow governance with ChangeProposal objects.
7. Add champion/challenger routing and Apollo-controlled canaries.
8. Expand to commander workflows after policy, eval, and rollback metrics are stable.

ClearGlassInc Artemis becomes smarter by converting mission reality into governed evals, governed evals into approved improvements, and approved improvements into Apollo-controlled releases. The platform evolves continuously, but the mission owner remains in command.
