# ClearGlassInc Artemis — Self-Evolving AI Intelligence Platform Blueprint

**Date:** 2026-07-18  
**Organization:** ClearGlassInc Artemis  
**Platform stack:** Palantir Gotham, Foundry, AIP, Apollo  
**Operating posture:** secure, coalition-aware, multi-domain, latency-sensitive, audited, human-approved self-improvement  
**Implementation bias:** Python-first precision, production full stack, policy-as-code, immutable provenance, safe rollback

> **Operational safety note:** ClearGlassInc Artemis is an intelligence-software design. It must not be used to automate physical-world intervention, safety-critical action, or operationally significant decision execution without explicit human authorization, jurisdiction-specific compliance review, and recorded approval.

---

## 1. System Architecture

### 1.1 Platform intent

ClearGlassInc Artemis is a self-evolving intelligence platform that fuses live and historical data, reasons over an operational ontology, assists analysts and commanders, and proposes improvements to prompts, workflows, heuristics, model routing, and evaluation suites. The system may recommend changes, generate pull requests, stage experiments, and prepare deployment artifacts, but production changes only move through explicit human-approved gates.

### 1.2 Palantir product roles

- **Gotham:** operational intelligence workspace for investigations, entity tracking, link analysis, watchlists, case management, mission threads, and commander views.
- **Foundry:** data integration, semantic ontology, pipelines, lineage, transformation logic, data quality controls, operational applications, and governed data products.
- **AIP:** AI copilot runtime, agent orchestration, tool execution, prompt/version governance, evaluations, model routing, approval workflows, and explainable recommendations.
- **Apollo:** secure continuous deployment, environment promotion, runtime policy, edge deployment, canary rollout, rollback, health checks, and version pinning across classified, coalition, cloud, and disconnected environments.

### 1.3 End-to-end logical architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ClearGlassInc Artemis Web UI                         │
│ Analyst Copilot │ Commander COP │ Case Workbench │ Eval Console │ Admin     │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ OIDC + signed requests + policy context
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ API Gateway / Backend-for-Frontend                                          │
│ GraphQL │ REST │ WebSocket │ SSE │ tenant routing │ request provenance       │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ Domain Services                                                             │
│ Case Service │ Entity Service │ Alert Service │ Tasking Service │ Feedback  │
│ Intel Product Service │ Policy Service │ Audit Service │ Eval Service       │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ events, ontology queries, tools, approvals
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ AIP AI Orchestration Layer                                                  │
│ Copilots │ Agents │ Model Router │ Prompt Registry │ Tool Registry │ Evals   │
│ Human Approval Gates │ Guardrail Runtime │ Self-Improvement Proposer         │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ ontology-grounded tool calls
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ Foundry Data + Ontology Layer                                               │
│ Ingestion │ Pipelines │ Ontology Objects │ Object Sets │ Lineage │ Apps      │
│ Data Quality │ Transformation DAGs │ Feature Tables │ Vector Indexes         │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ operational sync / investigations
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ Gotham Operational Intelligence Layer                                       │
│ Cases │ Investigations │ Link Analysis │ Entity Resolution │ Watchlists      │
│ Mission Views │ Alerts │ Commander Operating Picture                         │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ deploy, govern, rollback
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ Apollo Deployment + Runtime Control                                         │
│ Version Sets │ Release Channels │ Canary │ Rollback │ Edge Runtime │ SLOs     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Deployment tiers

| Tier | Purpose | Latency posture | Data posture | Release posture |
|---|---|---:|---|---|
| `dev-synthetic` | Synthetic data engineering | relaxed | no mission data | fast CI |
| `test-redteam` | adversarial evals and policy tests | moderate | sanitized | blocked on eval pass |
| `staging-secure` | human UAT and integration rehearsal | production-like | partitioned samples | approval required |
| `prod-coalition` | mission operations | low latency | compartmented | Apollo canary |
| `edge-disconnected` | denied/intermittent environments | local first | replicated subset | signed bundle |
| `breakglass-readonly` | emergency continuity | deterministic | immutable snapshots | no writes except audit |

### 1.5 Critical design principles

1. **Ontology is the control plane.** Every human view, agent tool, policy decision, and eval fixture references ontology objects rather than loose records.
2. **Human approval is mandatory for mission-significant actions.** Agents prepare and explain action packages; operators authorize.
3. **Self-improvement is proposal-driven.** The system can propose prompt/workflow/model-routing changes, but cannot silently alter production behavior.
4. **Everything is versioned.** Data schemas, ontology mappings, prompts, evals, policies, workflows, model routes, and deployment bundles have immutable versions.
5. **Every output has provenance.** An answer must be traceable to data, prompt, model, policy, tool call, operator, and deployment version.
6. **Least privilege is enforced at query time, tool time, and generation time.** Retrieval and final response rendering both filter on clearance, compartment, coalition caveat, purpose, and case assignment.

---

## 2. Data and Ontology

### 2.1 Data ingestion classes

| Class | Examples | Processing mode | Key controls |
|---|---|---|---|
| Live telemetry | sensor events, device pings, network events | streaming | schema validation, replay window, source trust |
| Historical records | reports, case notes, entity registries | batch/incremental | lineage, de-duplication, retention |
| Human intelligence products | field reports, analyst notes, commander guidance | document pipeline | caveats, source sensitivity, confidence |
| Open-source information | public web, filings, media, geospatial | scheduled crawl | terms, source reputation, misinformation checks |
| Feedback signals | corrections, approvals, dismissals, edits | event stream | operator identity, intent, audit hash |
| Model artifacts | prompts, evals, routing decisions, traces | append-only | version pinning, approval status |

### 2.2 Ontology core entities

```yaml
ontology:
  objects:
    Person:
      properties: [person_id, names, aliases, dob_range, nationality, confidence, caveats]
      temporal: true
      permissions: [compartment_ids, coalition_release, need_to_know_tags]
    Organization:
      properties: [org_id, legal_names, aliases, type, jurisdiction, confidence]
    Asset:
      properties: [asset_id, class, serial, owner, geofence, status, confidence]
    Location:
      properties: [location_id, geometry, geohash, address, uncertainty_meters]
    Event:
      properties: [event_id, event_type, occurred_at, observed_at, source_ids, severity]
    Signal:
      properties: [signal_id, stream, payload_hash, quality_score, latency_ms]
    Case:
      properties: [case_id, title, mission_id, state, priority, lead_org, assigned_users]
    Alert:
      properties: [alert_id, rule_id, entity_refs, severity, status, rationale]
    IntelProduct:
      properties: [product_id, classification, executive_summary, claims, citations]
    Mission:
      properties: [mission_id, objective, authority, constraints, success_metrics]
    Feedback:
      properties: [feedback_id, user_id, target_ref, label, correction, outcome]
    PromptVersion:
      properties: [prompt_id, semver, owner, status, eval_score, rollback_ref]
    WorkflowVersion:
      properties: [workflow_id, semver, graph_hash, approval_state]

  relationships:
    OBSERVED_AT: [Signal, Location]
    MENTIONS: [IntelProduct, Person|Organization|Asset|Location|Event]
    PARTICIPATED_IN: [Person|Organization|Asset, Event]
    LOCATED_NEAR: [Person|Asset|Event, Location]
    OWNS_OR_CONTROLS: [Person|Organization, Asset|Organization]
    GENERATED_ALERT: [Event|Signal, Alert]
    PART_OF_CASE: [Alert|Event|Entity, Case]
    SUPPORTED_BY: [Claim, Source|Signal|IntelProduct]
    CORRECTS: [Feedback, Alert|IntelProduct|AgentOutput]
    PROPOSES_CHANGE: [SelfImprovementProposal, PromptVersion|WorkflowVersion|PolicyVersion]
```

### 2.3 Entity confidence model

Each ontology object uses a confidence vector instead of a single score.

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

class ConfidenceDimension(str, Enum):
    SOURCE_RELIABILITY = "source_reliability"
    INFORMATION_CREDIBILITY = "information_credibility"
    ENTITY_RESOLUTION = "entity_resolution"
    TEMPORAL_FRESHNESS = "temporal_freshness"
    GEO_PRECISION = "geo_precision"
    MODEL_INFERENCE = "model_inference"
    HUMAN_VALIDATION = "human_validation"

@dataclass(frozen=True)
class ConfidenceVector:
    source_reliability: float
    information_credibility: float
    entity_resolution: float
    temporal_freshness: float
    geo_precision: float
    model_inference: float
    human_validation: float
    computed_at: datetime

    def mission_score(self, weights: dict[ConfidenceDimension, float]) -> float:
        numerator = sum(getattr(self, dim.value) * weight for dim, weight in weights.items())
        denominator = sum(weights.values()) or 1.0
        return round(numerator / denominator, 4)
```

### 2.4 Temporal state model

ClearGlassInc Artemis treats facts as time-bounded assertions rather than static truth.

```sql
CREATE TABLE ontology_assertion (
    assertion_id UUID PRIMARY KEY,
    subject_ref TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_ref TEXT NOT NULL,
    valid_time_start TIMESTAMPTZ,
    valid_time_end TIMESTAMPTZ,
    observed_time TIMESTAMPTZ NOT NULL,
    source_id TEXT NOT NULL,
    confidence JSONB NOT NULL,
    caveats TEXT[] NOT NULL DEFAULT '{}',
    compartments TEXT[] NOT NULL DEFAULT '{}',
    lineage_hash TEXT NOT NULL,
    supersedes_assertion_id UUID
);

CREATE INDEX idx_ontology_assertion_subject_time
ON ontology_assertion (subject_ref, valid_time_start, valid_time_end);

CREATE INDEX idx_ontology_assertion_policy
ON ontology_assertion USING GIN (compartments);
```

### 2.5 How the ontology drives workflows and agents

- **Human workflows:** case queues are object sets filtered by mission, severity, permissions, recency, and unresolved defects in evidence quality.
- **AI tools:** agents receive tool schemas bound to ontology object permissions; they cannot issue unconstrained SQL against raw sources.
- **Policy:** every object carries compartments, coalition release markers, source caveats, retention tags, and purpose-of-use constraints.
- **Evals:** gold sets are ontology snapshots with expected entity links, expected citations, expected abstentions, and expected policy denials.
- **Lineage:** generated intelligence products cite ontology assertions and original sources, not just retrieved text chunks.

---

## 3. AI and Agent Design

### 3.1 Copilot families

| Copilot | Users | Primary tasks | Approval posture |
|---|---|---|---|
| Analyst Copilot | investigators, analysts | query, summarize, correlate, draft products | can draft; cannot publish without review |
| Commander Copilot | mission leads | operational picture, options, risk tradeoffs | recommends; cannot task assets directly |
| Data Steward Copilot | data engineers | mapping, quality rules, lineage fixes | PR + approval |
| Policy Copilot | security/governance | explain denials, simulate access | no unilateral policy change |
| Eval Copilot | AI governance team | produce eval cases and score regressions | can propose; approval required |
| Deployment Copilot | platform operators | release readiness and rollback planning | Apollo operator approval required |

### 3.2 Multi-agent workflow graph

```text
Incoming Event
   │
   ▼
Ingest Agent ──► Schema + Policy Validator ──► Entity Resolution Agent
   │                                               │
   ▼                                               ▼
Quality Agent                               Correlation Agent
   │                                               │
   └──────────────► Triage Agent ◄─────────────────┘
                         │
                         ▼
               Recommendation Agent
                         │
                         ▼
                Human Approval Gate
                  │ approve/reject/edit
                  ▼
          Case Update / Product Draft / Watchlist
                         │
                         ▼
            Feedback + Outcome Capture
                         │
                         ▼
              Self-Improvement Proposer
```

### 3.3 Agent operating contract

Every AIP agent runs with an explicit contract:

```yaml
agent_contract:
  name: artemis_triage_agent
  objective: Prioritize incoming alerts for assigned missions.
  allowed_tools:
    - ontology.search_entities
    - ontology.get_object_context
    - case.create_draft_update
    - eval.record_agent_trace
  prohibited_actions:
    - external_tasking.execute
    - case.close_without_human
    - policy.modify
    - prompt.promote_to_production
  required_citations: true
  max_tool_calls: 12
  max_latency_ms: 2500
  approval_required_for:
    - changing case priority above HIGH
    - adding entity to watchlist
    - publishing intelligence product
    - notifying external coalition partner
  abstain_when:
    - policy denies required source
    - confidence below mission threshold
    - evidence conflict cannot be reconciled
```

### 3.4 Tool design pattern

Tools are narrow, typed, policy-aware, observable, and auditable.

```python
from pydantic import BaseModel, Field

class EntitySearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=256)
    entity_types: list[str]
    mission_id: str
    max_results: int = Field(default=10, le=50)

class EntitySearchResult(BaseModel):
    entity_ref: str
    display_name: str
    entity_type: str
    confidence: float
    permitted_fields: dict[str, object]
    redactions: list[str]
    citations: list[str]

async def ontology_search_entities(
    request: EntitySearchInput,
    user_context: "UserContext",
    ontology_client: "OntologyClient",
    policy: "PolicyEngine",
) -> list[EntitySearchResult]:
    policy.require_purpose(user_context, purpose="mission_intelligence")
    policy.require_mission_assignment(user_context, request.mission_id)

    raw_results = await ontology_client.search(
        query=request.query,
        object_types=request.entity_types,
        mission_id=request.mission_id,
        limit=request.max_results,
    )

    filtered: list[EntitySearchResult] = []
    for item in raw_results:
        decision = policy.filter_object(user_context, item)
        if decision.allowed:
            filtered.append(EntitySearchResult(
                entity_ref=item.ref,
                display_name=decision.fields.get("display_name", "REDACTED"),
                entity_type=item.type,
                confidence=item.confidence,
                permitted_fields=decision.fields,
                redactions=decision.redactions,
                citations=item.citations,
            ))
    return filtered
```

---

## 4. Self-Improvement Loop

### 4.1 Signals captured

| Signal | Captured from | Used to improve |
|---|---|---|
| Explicit thumbs up/down | copilot UI | prompt quality and answer style |
| Operator correction | edited summaries, changed priority, merged entities | eval cases, heuristic rules, entity resolution |
| Query logs | search sessions, failed queries, refinements | retrieval ranking and UX affordances |
| Alert outcomes | true positive, false positive, ignored, escalated | triage thresholds and feature weights |
| Mission outcomes | operational success metrics | scenario eval weighting |
| Latency traces | AIP/model/tool spans | model routing and caching |
| Policy denials | access failures and appeal outcomes | policy explainability, training gaps |
| Red-team results | adversarial prompts, leakage tests | guardrails and abstention rules |

### 4.2 Improvement lifecycle

```text
Observe → Normalize → Label → Generate Eval → Candidate Change → Offline Test
→ Shadow Run → Human Review → Canary → Monitor → Promote or Roll Back
```

### 4.3 Self-improvement rules

1. **No autonomous goal mutation.** The system optimizes approved metrics only: precision, recall, latency, calibration, operator trust, policy compliance, and mission utility.
2. **No silent production changes.** Candidate prompts, workflows, policy rules, and model routes remain drafts until approved.
3. **Every candidate has an eval delta.** A proposed change must include before/after scores, failure examples, affected missions, and rollback plan.
4. **Policy changes are separate from prompt changes.** A prompt cannot override policy denial or change access scope.
5. **Canary blast radius is limited.** Apollo deploys candidate behavior to a small, named cohort or synthetic/shadow traffic first.

### 4.4 Versioned improvement artifact

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

@dataclass(frozen=True)
class ImprovementProposal:
    proposal_id: str
    target_type: Literal["prompt", "workflow", "model_route", "heuristic", "eval", "policy"]
    target_id: str
    base_version: str
    candidate_version: str
    rationale: str
    evidence_refs: list[str]
    offline_eval_report_ref: str
    risk_level: Literal["low", "medium", "high", "critical"]
    rollback_version: str
    requested_by: str
    created_at: datetime
    approval_state: Literal["draft", "review", "approved", "rejected", "canary", "promoted", "rolled_back"]
```

### 4.5 Drift detection

Drift monitors run across data, behavior, model quality, and policy outcomes.

```python
def population_stability_index(expected: list[float], actual: list[float], bins: int = 10) -> float:
    import numpy as np

    quantiles = np.quantile(expected, np.linspace(0, 1, bins + 1))
    quantiles[0] -= 1e-9
    quantiles[-1] += 1e-9
    expected_counts, _ = np.histogram(expected, bins=quantiles)
    actual_counts, _ = np.histogram(actual, bins=quantiles)
    expected_pct = np.maximum(expected_counts / max(expected_counts.sum(), 1), 1e-6)
    actual_pct = np.maximum(actual_counts / max(actual_counts.sum(), 1), 1e-6)
    return float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))


def should_freeze_route(psi: float, precision_delta: float, policy_denial_spike: float) -> bool:
    return psi > 0.25 or precision_delta < -0.05 or policy_denial_spike > 0.20
```

### 4.6 Evaluation harness

```python
from pydantic import BaseModel

class EvalCase(BaseModel):
    case_id: str
    prompt_input: dict
    expected_citations: list[str]
    expected_decision: str
    forbidden_claims: list[str]
    min_confidence: float
    policy_context: dict

class EvalResult(BaseModel):
    case_id: str
    passed: bool
    precision: float
    recall: float
    latency_ms: int
    policy_violations: int
    citation_coverage: float
    notes: str

async def run_eval_suite(candidate_prompt: str, cases: list[EvalCase], aip_client) -> list[EvalResult]:
    results: list[EvalResult] = []
    for case in cases:
        output = await aip_client.run_prompt(
            prompt=candidate_prompt,
            input=case.prompt_input,
            policy_context=case.policy_context,
            trace=True,
        )
        results.append(EvalResult(
            case_id=case.case_id,
            passed=(
                output.decision == case.expected_decision
                and not set(output.claims).intersection(case.forbidden_claims)
                and output.confidence >= case.min_confidence
                and set(case.expected_citations).issubset(set(output.citations))
                and output.policy_violations == 0
            ),
            precision=output.metrics.precision,
            recall=output.metrics.recall,
            latency_ms=output.metrics.latency_ms,
            policy_violations=output.policy_violations,
            citation_coverage=output.metrics.citation_coverage,
            notes=output.explanation,
        ))
    return results
```

---

## 5. Full-Stack Implementation

### 5.1 Frontend blueprint

**Stack:** TypeScript, React, Next.js, TanStack Query, WebSocket/SSE stream client, OpenTelemetry browser instrumentation, OIDC, policy-aware component rendering.

```tsx
// app/cases/[caseId]/AnalystCopilotPanel.tsx
'use client';

import { useMutation, useQuery } from '@tanstack/react-query';

type CopilotRequest = {
  caseId: string;
  missionId: string;
  question: string;
};

export function AnalystCopilotPanel({ caseId, missionId }: { caseId: string; missionId: string }) {
  const context = useQuery({
    queryKey: ['case-context', caseId],
    queryFn: async () => fetch(`/api/cases/${caseId}/context`).then(r => r.json()),
  });

  const ask = useMutation({
    mutationFn: async (body: CopilotRequest) => {
      const response = await fetch('/api/aip/analyst-copilot', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error(await response.text());
      return response.json();
    },
  });

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-950 p-4">
      <h2 className="text-lg font-semibold text-white">Artemis Analyst Copilot</h2>
      <p className="text-sm text-slate-300">Ontology-grounded answers with citations and policy redactions.</p>
      <textarea
        className="mt-3 min-h-32 w-full rounded bg-slate-900 p-3 text-white"
        placeholder="Ask for correlations, anomalies, source-backed summaries, or draft case updates."
        onKeyDown={(event) => {
          if (event.key === 'Enter' && event.metaKey) {
            ask.mutate({ caseId, missionId, question: event.currentTarget.value });
          }
        }}
      />
      {ask.data && (
        <article className="mt-4 space-y-3 text-slate-100">
          <pre className="whitespace-pre-wrap">{ask.data.answer}</pre>
          <div className="text-xs text-slate-400">Trace: {ask.data.traceId}</div>
        </article>
      )}
      {context.data?.redactions?.length > 0 && (
        <div className="mt-2 text-xs text-amber-300">Some fields are redacted by policy.</div>
      )}
    </section>
  );
}
```

### 5.2 API gateway

```python
# services/api_gateway/main.py
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="ClearGlassInc Artemis API Gateway")

class AnalystCopilotBody(BaseModel):
    case_id: str
    mission_id: str
    question: str

async def get_user_context(request: Request) -> "UserContext":
    token = request.headers.get("authorization", "")
    return await UserContext.from_oidc_token(token)

@app.post("/aip/analyst-copilot")
async def analyst_copilot(
    body: AnalystCopilotBody,
    user: "UserContext" = Depends(get_user_context),
):
    if not await policy_engine.can_access_case(user, body.case_id, body.mission_id):
        raise HTTPException(status_code=403, detail="Access denied for case or mission")

    result = await aip_orchestrator.run_agent(
        agent_name="artemis_analyst_copilot",
        input={"case_id": body.case_id, "mission_id": body.mission_id, "question": body.question},
        user_context=user.model_dump(),
        require_citations=True,
    )
    await audit_log.write(
        actor=user.user_id,
        action="aip.analyst_copilot.run",
        target=body.case_id,
        trace_id=result.trace_id,
        policy_version=policy_engine.version,
    )
    return result.public_view()
```

### 5.3 Event streaming contracts

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ArtemisOperationalEvent",
  "type": "object",
  "required": ["event_id", "source_id", "observed_at", "event_type", "payload", "classification"],
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "source_id": { "type": "string" },
    "observed_at": { "type": "string", "format": "date-time" },
    "event_type": { "type": "string" },
    "mission_refs": { "type": "array", "items": { "type": "string" } },
    "payload": { "type": "object" },
    "classification": { "type": "string" },
    "compartments": { "type": "array", "items": { "type": "string" } },
    "lineage": {
      "type": "object",
      "required": ["ingest_hash", "producer", "schema_version"]
    }
  }
}
```

### 5.4 Backend event handler

```python
# services/streaming/event_handlers.py
from opentelemetry import trace

tracer = trace.get_tracer("artemis.streaming")

async def handle_operational_event(event: dict) -> None:
    with tracer.start_as_current_span("handle_operational_event") as span:
        span.set_attribute("event.id", event["event_id"])
        span.set_attribute("event.type", event["event_type"])

        validated = ArtemisOperationalEvent.model_validate(event)
        await immutable_event_store.append(validated)

        quality = await data_quality.score(validated)
        if quality.blocking_defects:
            await alert_service.create_data_quality_alert(validated, quality)
            return

        ontology_refs = await foundry_mapper.upsert_event_to_ontology(validated)
        triage_result = await aip_orchestrator.run_agent(
            agent_name="artemis_triage_agent",
            input={"event_ref": ontology_refs.event_ref, "quality": quality.model_dump()},
            user_context=system_context.for_service("streaming-triage"),
        )
        await alert_service.materialize_triage(validated, triage_result)
```

### 5.5 Workflow state machine

```python
from transitions import Machine

class CaseWorkflow:
    states = [
        "new",
        "triaged",
        "assigned",
        "investigating",
        "recommendation_drafted",
        "awaiting_approval",
        "approved",
        "rejected",
        "closed",
    ]

    transitions = [
        {"trigger": "triage", "source": "new", "dest": "triaged"},
        {"trigger": "assign", "source": "triaged", "dest": "assigned"},
        {"trigger": "open_investigation", "source": "assigned", "dest": "investigating"},
        {"trigger": "draft_recommendation", "source": "investigating", "dest": "recommendation_drafted"},
        {"trigger": "request_approval", "source": "recommendation_drafted", "dest": "awaiting_approval"},
        {"trigger": "approve", "source": "awaiting_approval", "dest": "approved"},
        {"trigger": "reject", "source": "awaiting_approval", "dest": "rejected"},
        {"trigger": "close", "source": ["approved", "rejected"], "dest": "closed"},
    ]

    def __init__(self, case_id: str):
        self.case_id = case_id
        self.machine = Machine(model=self, states=self.states, transitions=self.transitions, initial="new")
```

### 5.6 Retrieval and search layer

```python
class RetrievalPlan(BaseModel):
    lexical_query: str
    vector_query: str
    object_types: list[str]
    time_window_hours: int
    mission_id: str
    required_caveats: list[str] = []

async def retrieve_grounding_context(plan: RetrievalPlan, user: UserContext) -> list[GroundingDocument]:
    policy.require_mission_assignment(user, plan.mission_id)
    object_set = await foundry_ontology.query_objects(
        object_types=plan.object_types,
        mission_id=plan.mission_id,
        since_hours=plan.time_window_hours,
    )
    lexical = await search.lexical(plan.lexical_query, object_set.refs)
    semantic = await vector_store.search(plan.vector_query, object_set.refs)
    merged = reciprocal_rank_fusion(lexical, semantic)
    return [policy.redact_document(user, doc) for doc in merged[:20]]
```

### 5.7 Model router

```python
class ModelRouteRequest(BaseModel):
    task_type: str
    sensitivity: str
    max_latency_ms: int
    requires_tool_use: bool
    requires_long_context: bool
    mission_criticality: str

class ModelRouteDecision(BaseModel):
    model_id: str
    prompt_version: str
    reason: str
    fallback_model_id: str
    max_tokens: int

async def route_model(req: ModelRouteRequest) -> ModelRouteDecision:
    if req.sensitivity in {"restricted", "coalition-limited"}:
        return ModelRouteDecision(
            model_id="approved-secure-llm-local",
            prompt_version="analyst-v4.7.2",
            reason="Sensitive context requires approved local runtime",
            fallback_model_id="approved-secure-llm-small",
            max_tokens=4096,
        )
    if req.max_latency_ms < 1000:
        return ModelRouteDecision(
            model_id="low-latency-router-model",
            prompt_version="fast-triage-v2.3.1",
            reason="Latency target under one second",
            fallback_model_id="approved-secure-llm-small",
            max_tokens=1024,
        )
    return ModelRouteDecision(
        model_id="frontier-reasoning-model-approved",
        prompt_version="deep-analysis-v5.1.0",
        reason="Default high-accuracy route",
        fallback_model_id="approved-secure-llm-local",
        max_tokens=8192,
    )
```

---

## 6. Security and Governance

### 6.1 Need-to-know policy model

```rego
package artemis.authz

default allow := false

allow if {
  input.user.authenticated == true
  input.action in input.user.allowed_actions
  input.resource.mission_id in input.user.assigned_missions
  every c in input.resource.compartments { c in input.user.compartments }
  input.resource.classification_rank <= input.user.clearance_rank
  input.purpose in input.user.approved_purposes
}

redact[field] if {
  field := input.resource.fields[_]
  field.caveat != ""
  not field.caveat in input.user.caveats
}
```

### 6.2 Governance controls

- **Identity:** OIDC/SAML federation, hardware-backed MFA, workload identities, signed service tokens.
- **Authorization:** row, column, object, entity, relationship, and tool-level controls.
- **Compartmentalization:** mission partitions, coalition release markings, caveat inheritance, source sensitivity propagation.
- **Zero trust:** every tool call carries actor, purpose, mission, request hash, policy version, and environment ID.
- **Immutable logs:** append-only event store with hash chaining and retention policy.
- **Prompt governance:** semantic versioning, owner, eval thresholds, red-team status, approval record, rollback prompt.
- **Model governance:** approved model catalog, data residency rules, sensitivity routing, latency SLOs, regression history.
- **Policy-as-code:** peer-reviewed Rego or equivalent rules with simulation tests before promotion.
- **Provenance:** generated products cite ontology assertions, source documents, prompt version, model route, and tool traces.

### 6.3 Immutable audit hash chain

```python
import hashlib
import json
from datetime import datetime, timezone

async def write_audit_event(event: dict) -> str:
    previous_hash = await audit_store.latest_hash()
    envelope = {
        "event": event,
        "previous_hash": previous_hash,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
    event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    await audit_store.append({**envelope, "event_hash": event_hash})
    return event_hash
```

---

## 7. Code Examples

### 7.1 Ontology-driven query

```python
async def get_case_operational_picture(case_id: str, user: UserContext) -> dict:
    case = await foundry_ontology.get_object("Case", case_id)
    policy.require_object_access(user, case, action="read")

    object_set = await foundry_ontology.expand_object_set(
        root_ref=case.ref,
        relationships=["PART_OF_CASE", "PARTICIPATED_IN", "LOCATED_NEAR", "SUPPORTED_BY"],
        max_depth=3,
    )

    permitted = [policy.filter_object(user, obj) for obj in object_set]
    return {
        "case": policy.redact_object(user, case),
        "entities": [p.fields for p in permitted if p.allowed],
        "redaction_count": sum(len(p.redactions) for p in permitted),
        "lineage_refs": sorted({ref for obj in object_set for ref in obj.lineage_refs}),
    }
```

### 7.2 Approval gate

```python
class ApprovalRequest(BaseModel):
    request_id: str
    case_id: str
    action_type: str
    action_payload: dict
    agent_rationale: str
    citations: list[str]
    risk_level: str

async def request_human_approval(req: ApprovalRequest, user: UserContext) -> dict:
    if req.risk_level in {"high", "critical"}:
        policy.require_role(user, "mission_approver")
    await approval_queue.enqueue(req.model_dump())
    await audit_log.write(
        actor=user.user_id,
        action="approval.requested",
        target=req.request_id,
        details={"case_id": req.case_id, "action_type": req.action_type},
    )
    return {"status": "awaiting_approval", "request_id": req.request_id}
```

### 7.3 Feedback ingestion

```python
class FeedbackEvent(BaseModel):
    feedback_id: str
    user_id: str
    mission_id: str
    target_type: str
    target_id: str
    label: str
    correction: str | None = None
    outcome: str | None = None

async def ingest_feedback(event: FeedbackEvent) -> None:
    await feedback_store.append(event.model_dump())
    await eval_case_builder.consider(event)
    await improvement_signal_topic.publish({
        "signal_type": "operator_feedback",
        "mission_id": event.mission_id,
        "target": f"{event.target_type}:{event.target_id}",
        "label": event.label,
        "has_correction": event.correction is not None,
    })
```

### 7.4 Candidate prompt generation

```python
async def propose_prompt_update(prompt_id: str, recent_failures: list[EvalResult]) -> ImprovementProposal:
    base = await prompt_registry.get_production(prompt_id)
    failure_digest = summarize_failures(recent_failures)

    candidate = await aip_orchestrator.run_agent(
        agent_name="prompt_improvement_proposer",
        input={
            "base_prompt": base.text,
            "failure_digest": failure_digest,
            "constraints": [
                "do not weaken citation requirements",
                "do not broaden tool access",
                "preserve policy-denial behavior",
                "prefer abstention when evidence is insufficient",
            ],
        },
        user_context=system_context.for_service("eval-governance"),
    )

    candidate_version = await prompt_registry.create_candidate(
        prompt_id=prompt_id,
        base_version=base.version,
        text=candidate.text,
        rationale=candidate.rationale,
    )
    eval_report = await eval_service.run(prompt_id, candidate_version)
    return ImprovementProposal(
        proposal_id=new_id("imp"),
        target_type="prompt",
        target_id=prompt_id,
        base_version=base.version,
        candidate_version=candidate_version,
        rationale=candidate.rationale,
        evidence_refs=[r.case_id for r in recent_failures],
        offline_eval_report_ref=eval_report.ref,
        risk_level="medium",
        rollback_version=base.version,
        requested_by="system:self-improvement-proposer",
        created_at=datetime.now(timezone.utc),
        approval_state="review",
    )
```

### 7.5 Apollo release plan skeleton

```yaml
release:
  application: artemis-aip-agent-pack
  candidate_version: 2026.07.18-triage-prompt-v4.8.0
  environments:
    - name: dev-synthetic
      strategy: immediate
      required_checks: [unit, policy_simulation, synthetic_eval]
    - name: test-redteam
      strategy: immediate
      required_checks: [adversarial_eval, leakage_eval, rollback_test]
    - name: staging-secure
      strategy: manual_approval
      approvers: [ai-governance-lead, mission-product-owner]
    - name: prod-coalition
      strategy: canary
      canary_percent: 5
      max_error_budget_burn: 1.5
      auto_rollback_on:
        - policy_violation_count > 0
        - precision_delta < -0.03
        - p95_latency_ms > 2500
```

---

## 8. Scenario Walkthrough

### 8.1 Live event enters

At 03:17 UTC, a live signal arrives from a coalition-approved sensor feed. Foundry validates the schema, stamps lineage, computes quality, and maps it into the ontology as `Signal:S-94821` and `Event:E-77419`. The event inherits coalition caveats and mission compartments.

### 8.2 Platform triages

The AIP triage agent receives only policy-permitted ontology context. It correlates the event with two historical events, one watchlisted asset, and one geospatial anomaly. It assigns `severity=HIGH`, but confidence is only `0.71` because one source is stale.

### 8.3 Agent recommends a response

The recommendation agent drafts an action package:

```json
{
  "recommendation": "Open a priority investigation thread and request analyst validation of the asset correlation.",
  "confidence": 0.71,
  "required_approval": true,
  "why": [
    "Event pattern matches two prior mission-relevant anomalies.",
    "Asset proximity is significant but requires human validation.",
    "One source is stale; recommendation avoids direct operational action."
  ],
  "citations": ["Signal:S-94821", "Event:E-77419", "Asset:A-22014", "Assertion:AS-18872"]
}
```

The agent cannot notify external partners, add the entity to a watchlist, or task any operational asset. It can only create a draft case update and request approval.

### 8.4 Operator approves, edits, or rejects

The analyst edits the recommendation, downgrading the severity from `HIGH` to `MEDIUM` because a recent field report explains the anomaly. The operator submits feedback: `triage_overestimated_due_to_stale_source`.

### 8.5 System learns safely

1. Feedback is written to the immutable event log.
2. The feedback builder creates a new eval case covering stale-source conflict handling.
3. The self-improvement proposer identifies that the triage prompt underweights temporal freshness.
4. It proposes a prompt and heuristic change: increase abstention when source staleness conflicts with a newer field report.
5. Offline evals show precision improves from `0.82` to `0.87`, recall decreases from `0.79` to `0.78`, policy violations remain `0`, and p95 latency is unchanged.
6. Human reviewers approve a 5% Apollo canary.
7. Canary monitoring shows fewer high-severity false positives and no policy regression.
8. The change is promoted; rollback remains pinned to the previous prompt version.

### 8.6 Final operational state

The case remains active, the intelligence product is marked draft until supervisor review, the stale-source issue is documented, the eval suite is stronger, and future triage behavior improves without granting the AI any new authority.

---

## 9. Metrics and Definition of Done

### 9.1 Production metrics

| Metric | Target | Owner |
|---|---:|---|
| Alert precision | mission-defined, trending upward | AI governance |
| Alert recall | mission-defined, no unapproved degradation | mission owner |
| Citation coverage | 100% for factual claims | product owner |
| Policy violations | 0 | security |
| p95 triage latency | ≤ 2.5s for live triage | platform SRE |
| Operator trust | quarterly improvement | mission leadership |
| Rollback time | minutes, not hours | Apollo operators |
| Eval freshness | new cases from feedback weekly | eval lead |

### 9.2 Implementation completion criteria

- Ontology objects and relationships are versioned, policy-tagged, and lineage-backed.
- AIP agents use typed, policy-aware tools with trace capture.
- Human approval gates are enforced for mission-significant actions.
- Feedback signals generate evals and improvement proposals.
- Prompts, workflows, model routes, and policies have immutable versions and rollback references.
- Apollo deploys canaries with automatic rollback triggers.
- Dashboards expose model quality, drift, policy denials, latency, and operator feedback.
- Every generated intelligence product includes citations, confidence, caveats, and provenance.

