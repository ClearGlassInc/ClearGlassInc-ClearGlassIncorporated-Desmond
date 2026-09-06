# ClearGlassInc Artemis — Skeleton Key Palantir Self-Evolving Intelligence Platform Blueprint

**Document date:** 2026-06-29  
**Organization:** ClearGlassInc Artemis  
**Reference stack:** Palantir Gotham, Foundry, AIP, Apollo  
**Operating posture:** secure, coalition-aware, multi-domain, latency-sensitive, fully audited, human-approved autonomy.

> ClearGlassInc Artemis is designed as a self-improving intelligence platform: it ingests live and historical data, reasons over a governed ontology, assists analysts and commanders through AIP agents, proposes workflow and prompt upgrades, and deploys approved changes through Apollo with rollback-ready controls.

## System Architecture

### Palantir product responsibilities

- **Gotham** provides operational intelligence, investigations, link analysis, entity tracking, watchlists, case timelines, and mission action history.
- **Foundry** provides data integration, transform pipelines, ontology objects, application logic, lineage, data products, and operational apps.
- **AIP** provides governed copilots, agent orchestration, tool calling, prompt/version governance, evaluations, model routing, and human-in-the-loop workflow automation.
- **Apollo** provides secure deployment, staged rollout, runtime policy, telemetry-aware promotion, rollback, and environment-specific configuration.

### End-to-end topology

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ ClearGlassInc Artemis Web UI                                                  │
│ Analyst Console | Commander Console | Case Graph | Intel Product Studio       │
│ Realtime Alert Wall | Eval Dashboard | Prompt/Workflow Review Board           │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │ OIDC/JWT + mTLS + WebSocket/SSE
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ API Gateway / Edge Control                                                     │
│ FastAPI/BFF | GraphQL | REST | WebSocket | Rate Limits | Request Signing       │
└───────────────┬───────────────────────┬───────────────────────┬───────────────┘
                │                       │                       │
┌───────────────▼────────────┐ ┌────────▼─────────┐ ┌───────────▼───────────────┐
│ Mission Services            │ │ AI Orchestration │ │ Policy + Audit Services   │
│ Case | Alert | Entity | Task │ │ AIP Agents       │ │ ABAC/RBAC/ReBAC | OPA     │
│ Intel Product | Feedback     │ │ Model Router     │ │ Immutable Ledger          │
└───────────────┬────────────┘ └────────┬─────────┘ └───────────┬───────────────┘
                │                       │                       │
┌───────────────▼───────────────────────▼───────────────────────▼───────────────┐
│ Foundry Operational Data + Ontology                                             │
│ Ontology Objects | Object Sets | Transforms | Data Products | Feature Store     │
└───────────────┬───────────────────────┬───────────────────────┬───────────────┘
                │                       │                       │
┌───────────────▼────────────┐ ┌────────▼─────────┐ ┌───────────▼───────────────┐
│ Streaming Layer             │ │ Search/Retrieval │ │ Gotham Operational Layer  │
│ Kafka/Pulsar | CDC | DLQ     │ │ OpenSearch/RAG   │ │ Investigation Graphs      │
└───────────────┬────────────┘ └────────┬─────────┘ └───────────┬───────────────┘
                │                       │                       │
┌───────────────▼───────────────────────▼───────────────────────▼───────────────┐
│ Lakehouse + Warehouse + Vector Store + Immutable Evidence Vault                 │
│ Raw | Bronze | Silver | Gold | Embeddings | Time Series | Audit WORM Storage    │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼───────────────────────────────────────┐
│ Apollo Deployment Control                                                     │
│ Dev | Staging | Coalition Cells | Mission Edge | Canary | Rollback | SBOM       │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Runtime services

| Layer | Services | Primary guarantees |
| --- | --- | --- |
| Frontend | Next.js/React mission console, graph explorer, approval board | Low-latency operator workflows and explicit approval gates |
| API | FastAPI backend-for-frontend, GraphQL object search, REST tools | Authenticated, traced, rate-limited access |
| Data | Foundry pipelines, lakehouse, warehouse, vector index | Lineage, quality checks, reproducibility |
| Ontology | Mission, Entity, Event, Relationship, Case, ActionPackage | Common semantic contract for humans and agents |
| AI | AIP copilots, multi-agent workflows, model router, eval harness | Tool-bounded reasoning with measurable quality |
| Policy | OPA-style policy-as-code, ABAC, coalition filters | Need-to-know and operational guardrails |
| Observability | OpenTelemetry, SIEM, eval dashboards, prompt telemetry | Mission, model, data, and deployment visibility |
| Deployment | Apollo releases, canaries, edge config, rollback | Controlled promotion across classified/coalition environments |

## Data and Ontology

### Ontology design principles

1. **Agents only reason over governed objects.** Raw tables remain behind Foundry access controls.
2. **Every claim has lineage.** Each entity property and relationship carries source, transform, timestamp, and confidence.
3. **Temporal state is first-class.** The platform tracks valid time, observed time, supersession, and current operational state.
4. **Permissions travel with the object.** Classification, coalition tags, compartments, and need-to-know labels are enforced at query time and tool-call time.
5. **Confidence is composable.** Entity confidence, relationship confidence, model confidence, and operator confidence are stored separately.

### Core ontology objects

```sql
create table artemis_entity (
  entity_id uuid primary key,
  entity_type text not null check (entity_type in (
    'PERSON','ORGANIZATION','DEVICE','ACCOUNT','IP','DOMAIN','LOCATION',
    'ASSET','VEHICLE','FILE','MODEL','PROMPT','WORKFLOW','MISSION'
  )),
  canonical_name text,
  aliases text[] not null default '{}',
  attributes jsonb not null default '{}',
  confidence numeric(5,4) not null check (confidence between 0 and 1),
  classification text not null,
  compartments text[] not null default '{}',
  coalition_tags text[] not null default '{}',
  policy_labels text[] not null default '{}',
  valid_from timestamptz,
  valid_to timestamptz,
  first_observed_at timestamptz not null,
  last_observed_at timestamptz not null,
  lineage jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table artemis_relationship (
  relationship_id uuid primary key,
  source_entity_id uuid not null references artemis_entity(entity_id),
  target_entity_id uuid not null references artemis_entity(entity_id),
  relationship_type text not null,
  evidence_refs text[] not null default '{}',
  confidence numeric(5,4) not null check (confidence between 0 and 1),
  relationship_state text not null default 'ACTIVE',
  attributes jsonb not null default '{}',
  valid_from timestamptz,
  valid_to timestamptz,
  lineage jsonb not null,
  created_at timestamptz not null default now()
);

create table artemis_event (
  event_id uuid primary key,
  mission_id uuid,
  event_type text not null,
  severity int not null check (severity between 0 and 100),
  source_system text not null,
  payload jsonb not null,
  observed_at timestamptz not null,
  ingested_at timestamptz not null default now(),
  dedupe_key text,
  triage_status text not null default 'NEW',
  classification text not null,
  compartments text[] not null default '{}',
  coalition_tags text[] not null default '{}',
  lineage jsonb not null
);
```

### Mission and AI governance tables

```sql
create table artemis_case (
  case_id uuid primary key,
  mission_id uuid not null,
  title text not null,
  status text not null check (status in ('OPEN','WATCH','ESCALATED','CLOSED')),
  priority int not null check (priority between 0 and 100),
  assigned_team text,
  related_entities uuid[] not null default '{}',
  summary text,
  created_by text not null,
  created_at timestamptz not null default now(),
  closed_at timestamptz
);

create table artemis_operator_feedback (
  feedback_id uuid primary key,
  mission_id uuid not null,
  actor_id text not null,
  artifact_type text not null check (artifact_type in ('ALERT','SUMMARY','RECOMMENDATION','PROMPT','WORKFLOW','ROUTING')),
  artifact_id text not null,
  rating int check (rating between 1 and 5),
  correction jsonb,
  outcome jsonb,
  trust_signal text check (trust_signal in ('ACCEPTED','EDITED','REJECTED','ESCALATED','NO_ACTION')),
  created_at timestamptz not null default now()
);

create table artemis_change_proposal (
  proposal_id uuid primary key,
  proposal_type text not null check (proposal_type in ('PROMPT','WORKFLOW','MODEL_ROUTE','HEURISTIC','POLICY')),
  source_eval_run_id uuid,
  current_version text not null,
  proposed_version text not null,
  diff jsonb not null,
  expected_impact jsonb not null,
  risk_assessment jsonb not null,
  approval_status text not null default 'PENDING',
  approved_by text,
  created_at timestamptz not null default now(),
  approved_at timestamptz
);
```

### How the ontology drives human and agent behavior

- Analysts see a single mission graph rather than disconnected records.
- Commanders receive mission-level risk and recommended action packages grounded in objects and lineage.
- AIP agents use ontology object sets as constrained tool inputs, preventing prompt-only assumptions.
- Policy checks evaluate entity labels, relationship labels, user attributes, mission context, and requested action.
- Self-improvement proposals are themselves ontology objects, so prompts, models, workflows, and evals have lineage and approval history.

## AI and Agent Design

### Copilots

- **Analyst Copilot:** explains alerts, builds entity dossiers, drafts hypotheses, generates collection questions, and prepares case notes.
- **Commander Copilot:** aggregates mission posture, highlights changing risk, summarizes tradeoffs, and prepares approval-ready action packages.
- **Governance Copilot:** reviews proposed prompt/workflow changes, compares eval results, highlights drift, and recommends approve/reject/rollback.

### Agent workflow graph

```text
Inbound Event
  └─ TriageAgent
       ├─ DeduplicationTool
       ├─ PolicyFilterTool
       └─ SeverityClassifier
            └─ EnrichmentAgent
                 ├─ OntologyQueryTool
                 ├─ SearchRetrievalTool
                 └─ LineageVerifier
                      └─ CorrelationAgent
                           ├─ GraphPatternTool
                           ├─ TemporalReasoner
                           └─ AnomalyDetector
                                └─ RecommendationAgent
                                     ├─ ActionPackageDraftTool
                                     ├─ RiskScoringTool
                                     └─ AlternativesGenerator
                                          └─ VerifierAgent
                                               ├─ PolicyCheckTool
                                               ├─ SourceCitationCheck
                                               └─ ApprovalGate
```

### Approval gates

| Action | Required gate |
| --- | --- |
| Read governed data | Runtime ABAC/ReBAC policy check |
| Generate summary | Citation and lineage check |
| Open or update case | Analyst approval or delegated low-risk rule |
| Notify external coalition partner | Commander approval plus coalition policy check |
| Change prompt/workflow/model route | Eval threshold plus review-board approval |
| Deploy runtime change | Apollo staged rollout with rollback plan |

## Self-Improvement Loop

### Signals captured

```text
operator feedback + edits
query logs + retrieval misses
alert outcomes + false positives/false negatives
case closure reasons + mission results
latency + cost + tool failure rates
model confidence + evaluator scores
policy denials + approval/rejection reasons
post-deployment telemetry + drift metrics
```

### Improvement pipeline

1. **Capture:** persist feedback, corrections, tool traces, prompt versions, model outputs, and decisions.
2. **Normalize:** convert raw traces into eval examples, counterexamples, rubrics, and regression tests.
3. **Evaluate:** run offline evals against current and candidate prompts/workflows/routes.
4. **Propose:** create a change proposal with expected impact, risk, rollback plan, and diff.
5. **Review:** human review board approves, rejects, edits, or requests more evidence.
6. **Deploy:** Apollo canary deploys the approved version to a small mission cell.
7. **Observe:** compare precision, recall, latency, operator trust, and mission impact.
8. **Promote or rollback:** promote on thresholds; rollback automatically on guardrail breach.

### Safe self-upgrade contract

```yaml
self_improvement_guardrails:
  allowed_to_propose:
    - prompt edits
    - workflow routing changes
    - retrieval query rewrites
    - model route thresholds
    - alert scoring heuristic changes
  never_autonomous:
    - operationally significant external actions
    - weakening policy controls
    - changing mission objectives
    - expanding data access
    - disabling audit or monitoring
  required_before_deploy:
    - offline_eval_passed
    - regression_suite_passed
    - risk_assessment_attached
    - human_approval_recorded
    - rollback_plan_attached
    - apollo_canary_configured
```

## Full-Stack Implementation

### Repository layout

```text
artemis-platform/
  apps/
    web-console/                 # Next.js operator UI
    eval-dashboard/              # Prompt/workflow/model quality dashboard
  services/
    api-gateway/                 # FastAPI edge/BFF
    event-ingest/                # streaming consumers and validators
    ontology-service/            # governed object queries
    agent-orchestrator/          # AIP workflow runtime facade
    policy-service/              # OPA/Cedar-style decisions
    feedback-service/            # learning signal capture
    eval-service/                # offline/online eval runner
    deployment-controller/       # Apollo release integration
  packages/
    schemas/                     # pydantic/jsonschema contracts
    policy/                      # policy-as-code bundles
    prompts/                     # versioned prompt registry
    workflows/                   # workflow DAG definitions
  infra/
    helm/
    terraform/
    apollo/
```

### Event contract

```json
{
  "event_id": "d0f612c5-7f56-48aa-a384-6f2ee64f0d1a",
  "mission_id": "mission-northstar-17",
  "event_type": "NETWORK_ANOMALY",
  "source_system": "edge-sensor-42",
  "observed_at": "2026-06-29T13:22:05Z",
  "severity_hint": 73,
  "payload": {
    "src_ip": "203.0.113.40",
    "dst_asset": "command-relay-a",
    "bytes_out": 98234412,
    "protocol": "tls",
    "indicator_refs": ["ioc-991", "ioc-1044"]
  },
  "security": {
    "classification": "SECRET",
    "compartments": ["ARTEMIS-CYBER"],
    "coalition_tags": ["US", "FVEY"]
  },
  "lineage": {
    "producer": "sensor-normalizer-v3",
    "transform_hash": "sha256:2b3c...",
    "raw_ref": "s3://evidence/2026/06/29/event.json"
  }
}
```

## Security and Governance

### Controls

- **Need-to-know access:** policy decisions combine user clearance, mission role, compartments, coalition caveats, entity labels, and action type.
- **Row/column/entity-level security:** Foundry object permissions and service-side policy checks filter objects before they reach agents or UI components.
- **Coalition boundaries:** cross-coalition data sharing requires explicit releasability tags and commander approval for external notifications.
- **Zero-trust execution:** every service uses mTLS, signed requests, short-lived workload identity, and explicit tool scopes.
- **Immutable provenance:** evidence, prompt outputs, operator decisions, eval results, and deployment events write to append-only WORM storage.
- **Model governance:** every model route has approved use cases, max data classification, latency/cost limits, eval thresholds, and rollback criteria.
- **Prompt governance:** prompts are versioned, tested, reviewed, signed, and deployed like software artifacts.

### Policy-as-code example

```rego
package artemis.authz

default allow := false

allow {
  input.action == "ontology.read"
  input.user.clearance_rank >= input.resource.classification_rank
  every c in input.resource.compartments { c in input.user.compartments }
  input.mission_id in input.user.missions
  releasable_to_user
}

releasable_to_user {
  count(input.resource.coalition_tags) == 0
}

releasable_to_user {
  every tag in input.resource.coalition_tags { tag in input.user.coalition_tags }
}

allow {
  input.action == "change.deploy"
  input.user.role == "release_commander"
  input.resource.approval_status == "APPROVED"
  input.resource.eval_status == "PASSED"
  input.resource.rollback_plan_attached == true
}
```

## Code Examples

### Python API gateway with policy enforcement

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

app = FastAPI(title="ClearGlassInc Artemis API", version="2040.1")


class UserContext(BaseModel):
    subject: str
    role: str
    clearance_rank: int
    missions: list[str]
    compartments: list[str]
    coalition_tags: list[str]


class OntologyEvent(BaseModel):
    event_id: UUID
    mission_id: str
    event_type: str
    severity_hint: int = Field(ge=0, le=100)
    payload: dict[str, Any]
    classification: str
    compartments: list[str] = []
    coalition_tags: list[str] = []
    lineage: dict[str, Any]


async def user_context(request: Request) -> UserContext:
    # Production implementation validates OIDC JWT and maps claims to mission roles.
    return UserContext(
        subject=request.headers.get("x-user", "unknown"),
        role=request.headers.get("x-role", "analyst"),
        clearance_rank=int(request.headers.get("x-clearance-rank", "1")),
        missions=request.headers.get("x-missions", "").split(","),
        compartments=request.headers.get("x-compartments", "").split(","),
        coalition_tags=request.headers.get("x-coalition-tags", "").split(","),
    )


async def require_policy(user: UserContext, action: str, resource: dict[str, Any]) -> None:
    async with httpx.AsyncClient(timeout=2.0) as client:
        decision = await client.post(
            "http://policy-service/v1/decide",
            json={"user": user.model_dump(), "action": action, "resource": resource},
        )
    if decision.status_code != 200 or not decision.json().get("allow"):
        raise HTTPException(status_code=403, detail="policy_denied")


@app.post("/v1/events")
async def ingest_event(event: OntologyEvent, user: UserContext = Depends(user_context)) -> dict[str, str]:
    await require_policy(
        user,
        "event.ingest",
        {
            "mission_id": event.mission_id,
            "classification": event.classification,
            "compartments": event.compartments,
            "coalition_tags": event.coalition_tags,
        },
    )
    # Publish to Kafka/Pulsar; persist raw payload; return trace identifier.
    return {"status": "accepted", "event_id": str(event.event_id)}
```

### Streaming triage worker

```python
import asyncio
from typing import Any

from pydantic import BaseModel


class TriageDecision(BaseModel):
    severity: int
    dedupe_key: str
    rationale: str
    requires_human_review: bool
    recommended_workflow: str


async def classify_event(event: dict[str, Any]) -> TriageDecision:
    payload = event["payload"]
    score = int(event.get("severity_hint", 0))
    if payload.get("indicator_refs"):
        score += 12
    if payload.get("bytes_out", 0) > 50_000_000:
        score += 10
    score = min(score, 100)
    return TriageDecision(
        severity=score,
        dedupe_key=f"{event['event_type']}:{payload.get('src_ip')}:{payload.get('dst_asset')}",
        rationale="High-volume anomaly with linked indicators and mission asset target.",
        requires_human_review=score >= 70,
        recommended_workflow="cyber_anomaly_enrichment_v7" if score >= 70 else "watchlist_update_v2",
    )


async def handle_event(event: dict[str, Any]) -> None:
    decision = await classify_event(event)
    await write_foundry_object("artemis_event_triage", event["event_id"], decision.model_dump())
    await emit_audit("triage.completed", event["event_id"], decision.model_dump())
    if decision.requires_human_review:
        await start_aip_workflow(decision.recommended_workflow, event)


async def write_foundry_object(object_type: str, object_id: str, body: dict[str, Any]) -> None:
    # Adapter writes to Foundry object/action endpoint in production.
    print(object_type, object_id, body)


async def emit_audit(action: str, subject: str, details: dict[str, Any]) -> None:
    print({"action": action, "subject": subject, "details": details})


async def start_aip_workflow(workflow_name: str, event: dict[str, Any]) -> None:
    print({"workflow": workflow_name, "event_id": event["event_id"]})
```

### Ontology-driven query tool

```python
from typing import Any


class OntologyTool:
    def __init__(self, foundry_client: Any, policy_client: Any):
        self.foundry = foundry_client
        self.policy = policy_client

    async def query_related_entities(self, *, user: dict[str, Any], mission_id: str, entity_id: str) -> list[dict[str, Any]]:
        allowed = await self.policy.decide(user=user, action="ontology.read", resource={"mission_id": mission_id})
        if not allowed:
            raise PermissionError("policy_denied")

        object_set = await self.foundry.object_sets.create(
            type="Entity",
            filters={"mission_id": mission_id, "related_to": entity_id},
            include_relationships=True,
        )
        return [
            {
                "entity_id": obj.id,
                "type": obj.type,
                "name": obj.properties.get("canonical_name"),
                "confidence": obj.properties.get("confidence"),
                "lineage": obj.properties.get("lineage"),
            }
            for obj in object_set.objects
        ]
```

### AIP agent tool manifest

```yaml
tools:
  query_ontology:
    description: Query governed Foundry ontology objects within mission scope.
    required_policy_action: ontology.read
    max_results: 50
  draft_action_package:
    description: Draft an operational recommendation for human approval.
    required_policy_action: action_package.draft
    requires_approval_before_execution: true
  open_case:
    description: Create a Gotham-linked case with cited evidence.
    required_policy_action: case.create
    requires_approval_before_execution: true
  submit_change_proposal:
    description: Submit prompt/workflow/model-route improvements for review.
    required_policy_action: change.propose
    requires_approval_before_execution: true
```

### Workflow state machine

```python
from enum import StrEnum
from pydantic import BaseModel


class State(StrEnum):
    RECEIVED = "RECEIVED"
    TRIAGED = "TRIAGED"
    ENRICHED = "ENRICHED"
    CORRELATED = "CORRELATED"
    RECOMMENDED = "RECOMMENDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class WorkflowContext(BaseModel):
    event_id: str
    mission_id: str
    state: State = State.RECEIVED
    evidence_refs: list[str] = []
    recommendation_id: str | None = None
    approval_id: str | None = None


TRANSITIONS = {
    State.RECEIVED: {State.TRIAGED},
    State.TRIAGED: {State.ENRICHED},
    State.ENRICHED: {State.CORRELATED},
    State.CORRELATED: {State.RECOMMENDED},
    State.RECOMMENDED: {State.PENDING_APPROVAL},
    State.PENDING_APPROVAL: {State.APPROVED, State.REJECTED},
    State.APPROVED: {State.CLOSED},
    State.REJECTED: {State.CLOSED},
}


def transition(ctx: WorkflowContext, next_state: State) -> WorkflowContext:
    if next_state not in TRANSITIONS.get(ctx.state, set()):
        raise ValueError(f"illegal transition {ctx.state} -> {next_state}")
    return ctx.model_copy(update={"state": next_state})
```

### Eval pipeline for prompt/workflow upgrades

```python
from dataclasses import dataclass
from statistics import mean
from typing import Callable


@dataclass(frozen=True)
class EvalExample:
    example_id: str
    input_payload: dict
    expected: dict
    mission_tags: list[str]


@dataclass(frozen=True)
class EvalResult:
    candidate_version: str
    precision: float
    recall: float
    citation_coverage: float
    policy_violations: int
    p95_latency_ms: int


def score_candidate(candidate: Callable[[dict], dict], examples: list[EvalExample]) -> EvalResult:
    precisions: list[float] = []
    recalls: list[float] = []
    citation_scores: list[float] = []
    latencies: list[int] = []
    policy_violations = 0

    for ex in examples:
        output = candidate(ex.input_payload)
        precisions.append(output["metrics"]["precision"])
        recalls.append(output["metrics"]["recall"])
        citation_scores.append(1.0 if output.get("citations") else 0.0)
        latencies.append(output["metrics"]["latency_ms"])
        policy_violations += int(output["metrics"].get("policy_violation", False))

    return EvalResult(
        candidate_version=candidate.__name__,
        precision=mean(precisions),
        recall=mean(recalls),
        citation_coverage=mean(citation_scores),
        policy_violations=policy_violations,
        p95_latency_ms=sorted(latencies)[int(0.95 * (len(latencies) - 1))],
    )


def should_create_proposal(result: EvalResult, baseline: EvalResult) -> bool:
    return (
        result.policy_violations == 0
        and result.precision >= baseline.precision + 0.03
        and result.recall >= baseline.recall
        and result.citation_coverage >= 0.98
        and result.p95_latency_ms <= baseline.p95_latency_ms * 1.10
    )
```

### TypeScript frontend approval gate

```tsx
type ActionPackage = {
  id: string;
  missionId: string;
  title: string;
  confidence: number;
  risk: "LOW" | "MEDIUM" | "HIGH";
  citations: Array<{ label: string; href: string }>;
  proposedAction: string;
};

export function ApprovalCard({ pkg }: { pkg: ActionPackage }) {
  const canApprove = pkg.citations.length > 0 && pkg.confidence >= 0.72;

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-950 p-5 text-slate-100">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{pkg.title}</h2>
        <span className="rounded bg-cyan-900 px-2 py-1 text-xs">{pkg.risk}</span>
      </div>
      <p className="mt-3 text-sm text-slate-300">{pkg.proposedAction}</p>
      <p className="mt-2 text-xs text-slate-400">Confidence: {(pkg.confidence * 100).toFixed(1)}%</p>
      <ul className="mt-3 list-disc pl-5 text-xs">
        {pkg.citations.map((c) => (
          <li key={c.href}><a href={c.href}>{c.label}</a></li>
        ))}
      </ul>
      <div className="mt-4 flex gap-2">
        <button disabled={!canApprove} className="rounded bg-emerald-600 px-3 py-2 disabled:opacity-40">
          Approve
        </button>
        <button className="rounded bg-rose-600 px-3 py-2">Reject</button>
        <button className="rounded bg-slate-700 px-3 py-2">Request More Evidence</button>
      </div>
    </section>
  );
}
```

## Scenario Walkthrough

### 1. Live event enters

At 13:22:05 UTC on 2026-06-29, an edge sensor emits a high-volume outbound transfer from `command-relay-a` to an IP associated with two active indicators. The event enters the streaming layer, is validated against the event schema, stored in raw evidence storage, and normalized into the Foundry ontology.

### 2. Platform triages

`TriageAgent` computes severity `95`, creates a dedupe key, and marks the event as requiring human review. It starts `cyber_anomaly_enrichment_v7` and writes an immutable audit event.

### 3. Agents enrich and correlate

`EnrichmentAgent` queries the ontology for related assets, recent events, and indicator lineage. `CorrelationAgent` detects that the same destination was seen in a prior failed authentication sequence and links both events to an open mission case.

### 4. Recommendation is drafted

`RecommendationAgent` drafts an action package:

- isolate `command-relay-a` behind an approved containment policy;
- open a Gotham-linked investigation case;
- notify the cyber mission cell;
- defer coalition notification until releasability is confirmed.

`VerifierAgent` checks citations, lineage, and coalition tags. Because containment is operationally significant, it routes the package to a commander approval gate.

### 5. Operator approves or rejects

The commander sees evidence, confidence, risk, alternatives, and policy status in the web console. The commander approves isolation but rejects external notification due to insufficient releasability evidence. The decision is captured as structured feedback.

### 6. System learns safely

The feedback service records that the recommendation was partially accepted. The eval service converts the rejection reason into a regression example: future recommendations must verify releasability before suggesting coalition notification. AIP proposes a workflow update that moves `CoalitionReleasabilityCheck` before notification drafting. Offline evals show improved precision with no recall loss and zero policy violations.

### 7. Human-approved improvement deploys

A review board approves the workflow proposal. Apollo deploys `cyber_anomaly_enrichment_v8` as a canary to one mission cell. Observability compares false-positive notification recommendations, p95 latency, citation coverage, and operator trust against `v7`. If thresholds hold, Apollo promotes the workflow; if policy violations or latency regressions appear, Apollo rolls back to `v7` automatically.

## Production Metrics

| Metric | Target |
| --- | --- |
| Triage p95 latency | < 2 seconds |
| Enrichment p95 latency | < 10 seconds |
| Recommendation citation coverage | >= 98% |
| High-severity alert precision | +15% over baseline in 90 days |
| False-positive operational recommendations | -30% in 90 days |
| Policy violations in approved changes | 0 |
| Operator trust rating | >= 4.3 / 5 |
| Rollback time | < 5 minutes |
| Audit completeness | 100% of tool calls and approval decisions |

## Execution Roadmap

1. **Week 1-2:** establish ontology schemas, event contracts, policy service, and audit ledger.
2. **Week 3-4:** ship analyst console, case workflows, event ingestion, and baseline triage agent.
3. **Week 5-6:** add enrichment/correlation agents, vector retrieval, and citation verification.
4. **Week 7-8:** enable feedback capture, eval harness, prompt registry, and change proposals.
5. **Week 9-10:** integrate Apollo canary/rollback, observability dashboards, and governance board workflows.
6. **Week 11-12:** run mission simulation, calibrate metrics, and promote production release.

## Final Operating Doctrine

ClearGlassInc Artemis may accelerate analysis, draft recommendations, and propose self-upgrades, but it does not expand its own authority. Every meaningful improvement is tested, reviewed, versioned, audited, and deployed through controlled rollout. The platform gets better because human judgment, mission outcomes, and machine telemetry are converted into governed evals and approved changes—not because the system silently rewrites its own goals.
