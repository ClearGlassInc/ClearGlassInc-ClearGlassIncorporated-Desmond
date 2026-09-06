# ClearGlassInc Artemis — Self-Evolving AI Intelligence Platform (Gotham + Foundry + AIP + Apollo)

## 1) System Architecture

### 1.1 Mission Goals
- Real-time intelligence fusion across cyber, HUMINT, OSINT, SIGINT-like telemetry abstractions.
- Human-accountable AI acceleration for triage, correlation, recommendation, and action preparation.
- Safe self-improvement under explicit policy guardrails and approval workflows.

### 1.2 Layered Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Web UI (React/TS) + Analyst Copilot + Commander Console            │
├─────────────────────────────────────────────────────────────────────┤
│ API Gateway (FastAPI/Envoy) + GraphQL + REST + WebSocket           │
├─────────────────────────────────────────────────────────────────────┤
│ Service Mesh: Case Service | Entity Service | Alert Service         │
│               Recommendation Service | Policy Service               │
├─────────────────────────────────────────────────────────────────────┤
│ Agent Orchestrator (AIP) + Workflow Runtime + Tool Registry         │
├─────────────────────────────────────────────────────────────────────┤
│ Foundry Ontology + Pipelines + Feature Store + Data Products       │
├─────────────────────────────────────────────────────────────────────┤
│ Gotham Operational Layer: investigations, link analysis, watchlists │
├─────────────────────────────────────────────────────────────────────┤
│ Stream Bus (Kafka/PubSub) + CDC + Batch Ingest                     │
├─────────────────────────────────────────────────────────────────────┤
│ Lakehouse + Search Index + Vector Store + Immutable Audit Ledger   │
├─────────────────────────────────────────────────────────────────────┤
│ Apollo Deployment Control Plane (promote/canary/rollback)          │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 Palantir Role Mapping
- **Gotham**: operational case graphs, entity tracking, investigative timelines, action history.
- **Foundry**: integration pipelines, ontology, transforms, permission-bound data products.
- **AIP**: copilots, multi-agent workflows, eval harnesses, model/tool routing.
- **Apollo**: mission-safe deployment, environment segmentation, staged rollout, rollback.

## 2) Data and Ontology

### 2.1 Core Ontology (Foundry)

#### Entities
- `Person`, `Organization`, `Device`, `Account`, `IP`, `Domain`, `Location`, `Asset`, `Event`, `Case`, `Mission`.

#### Relationship Examples
- `USES(Person -> Device)`
- `OWNS(Organization -> Asset)`
- `ASSOCIATED_WITH(Account -> Person)`
- `OBSERVED_AT(Device -> Location)`
- `MENTIONED_IN(Entity -> Report)`
- `PART_OF(Event -> Mission)`

#### Mandatory Metadata on Every Node/Edge
- `confidence_score` (0.0–1.0)
- `lineage_ref` (dataset + pipeline + transform hash)
- `first_seen_ts`, `last_seen_ts`, `valid_time_range`
- `classification` (UNCLASSIFIED/FOUO/SECRET/etc abstraction)
- `coalition_tags` (e.g., `US`, `FVEY`, `NATO-X`)
- `policy_labels` (need-to-know dimensions)

### 2.2 Example SQL-ish Ontology Table Definitions

```sql
create table ontology_entity (
  entity_id uuid primary key,
  entity_type text not null,
  canonical_name text,
  attributes jsonb not null default '{}',
  confidence_score numeric(4,3) not null,
  classification text not null,
  coalition_tags text[] not null,
  policy_labels text[] not null,
  first_seen_ts timestamptz not null,
  last_seen_ts timestamptz not null,
  lineage_ref text not null
);

create table ontology_relationship (
  relationship_id uuid primary key,
  src_entity_id uuid not null,
  dst_entity_id uuid not null,
  relationship_type text not null,
  confidence_score numeric(4,3) not null,
  valid_from timestamptz,
  valid_to timestamptz,
  attributes jsonb not null default '{}',
  lineage_ref text not null
);
```

### 2.3 Ontology-Driven Human + AI Workflows
- Human analysts navigate graph timelines and confidence overlays.
- Agents consume ontology abstractions (not raw tables) to reduce brittle prompt coupling.
- Recommendation engine weights graph centrality + mission context + policy constraints.

## 3) AI and Agent Design

### 3.1 Copilot Roles
- **Analyst Copilot**: investigate alerts, summarize entities, propose hypotheses.
- **Commander Copilot**: mission-level risk state, recommended priority actions, what-if simulations.

### 3.2 Multi-Agent Topology (AIP)
- `TriageAgent`: classify, deduplicate, prioritize inbound events.
- `EnrichmentAgent`: attach contextual entities and intel references.
- `CorrelationAgent`: graph pattern matching + anomaly fusion.
- `RecommendationAgent`: generate action packages + confidence + risk.
- `VerifierAgent`: policy, provenance, and coalition compliance check.
- `NarrativeAgent`: produce briefings and SITREP artifacts.

### 3.3 Tooling Contract
- `query_ontology`
- `open_case`
- `draft_action_package`
- `run_policy_check`
- `submit_for_approval`
- `emit_audit_event`

Operationally significant actions (`block`, `contain`, `notify external`) require explicit human approval token.

## 4) Self-Improvement Loop

### 4.1 Learning Signals Captured
- Analyst feedback (thumbs up/down + rationale)
- Corrective edits to summaries and recommendations
- Alert outcome labels (true positive, false positive, escalated, dismissed)
- Mission KPIs (time-to-triage, disruption avoided, precision/recall)
- Query traces and tool invocation success/failure

### 4.2 Improvement Pipeline
1. Signal ingestion into `feedback_events` stream.
2. Nightly/continuous eval dataset synthesis.
3. Prompt candidate generation (small diffs only).
4. Workflow graph mutation proposals (bounded templates).
5. Offline eval + shadow mode replay.
6. Human review board approval.
7. Canary release through Apollo.
8. Drift monitors + auto-rollback conditions.

### 4.3 Guardrails
- No autonomous objective rewriting.
- No bypass of policy gate.
- No production promotion without signed approval artifact.
- Every change receives `change_id`, semantic version, rollback pointer.

## 5) Full-Stack Implementation Blueprint

### 5.1 Frontend (React + TypeScript)
- Mission dashboard, live alert stream, graph workspace, case timeline, action approval queue.
- WebSocket channels:
  - `/ws/alerts`
  - `/ws/case/{id}`
  - `/ws/agent-status`

### 5.2 API Gateway
- FastAPI for service aggregation + GraphQL endpoint for rich entity graph queries.
- OPA sidecar for request-time policy enforcement.

### 5.3 Backend Services (Python)
- `ingest-service`
- `entity-resolution-service`
- `intel-correlation-service`
- `recommendation-service`
- `approval-service`
- `eval-orchestrator-service`

### 5.4 Event and Data Plane
- Kafka topics: `raw_events`, `normalized_events`, `case_updates`, `feedback_events`, `eval_jobs`.
- Lakehouse for immutable history; OLAP marts for dashboard latency.
- Search stack: hybrid lexical + vector retrieval for intel notes and reports.

### 5.5 Model Router
- Route by task type + sensitivity + latency SLA.
- Fallback chains and abstain behavior when confidence < threshold.

## 6) Security and Governance

### 6.1 Zero-Trust Controls
- mTLS everywhere, short-lived workload identities, signed artifacts.
- Policy decision point per request + per tool invocation.

### 6.2 Need-to-Know Enforcement
- Row/column/entity-level filters via policy tags.
- Coalition-aware data partitions + dynamic redaction.

### 6.3 Provenance + Immutable Audit
- Append-only audit log with cryptographic hash chaining.
- Every AI output includes source refs, model id, prompt version, tool transcript digest.

### 6.4 Model + Prompt Governance
- Registries for model versions, prompt templates, eval baselines.
- Change control workflow with staged approvals.

## 7) Code Examples (Python-first)

### 7.1 Event Ingest Handler

```python
# services/ingest_service/consumer.py
from pydantic import BaseModel
from datetime import datetime

class RawEvent(BaseModel):
    event_id: str
    source: str
    ts: datetime
    payload: dict


def normalize_event(raw: RawEvent) -> dict:
    return {
        "event_id": raw.event_id,
        "source": raw.source,
        "timestamp": raw.ts.isoformat(),
        "indicators": raw.payload.get("indicators", []),
        "severity": raw.payload.get("severity", "unknown"),
        "lineage_ref": f"{raw.source}:{raw.event_id}"
    }
```

### 7.2 Ontology Query Tool

```python
# services/agent_tools/ontology.py
from typing import Any


def query_ontology(client: Any, entity_id: str, mission_id: str) -> dict:
    # Foundry/Gotham query abstraction
    graph = client.get_entity_subgraph(
        entity_id=entity_id,
        hops=2,
        mission_context=mission_id,
        include_confidence=True,
        include_temporal=True,
    )
    return {
        "entity": graph["root"],
        "neighbors": graph["neighbors"],
        "risk_signals": graph.get("risk_signals", []),
    }
```

### 7.3 Policy Gate for Actions

```python
# services/policy_service/checks.py
from dataclasses import dataclass

@dataclass
class ActionRequest:
    actor_id: str
    mission_id: str
    action_type: str
    target_entity: str
    coalition_tag: str


def authorize_action(pdp, req: ActionRequest) -> tuple[bool, str]:
    decision = pdp.evaluate(
        subject=req.actor_id,
        action=req.action_type,
        resource=req.target_entity,
        context={"mission": req.mission_id, "coalition": req.coalition_tag},
    )
    return decision.allowed, decision.reason
```

### 7.4 Agent Workflow State Machine

```python
# services/aip_orchestrator/workflow.py
from enum import Enum

class State(str, Enum):
    TRIAGE = "TRIAGE"
    ENRICH = "ENRICH"
    CORRELATE = "CORRELATE"
    RECOMMEND = "RECOMMEND"
    VERIFY = "VERIFY"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    EXECUTE = "EXECUTE"
    CLOSE = "CLOSE"


def next_state(current: State, approved: bool = False) -> State:
    transitions = {
        State.TRIAGE: State.ENRICH,
        State.ENRICH: State.CORRELATE,
        State.CORRELATE: State.RECOMMEND,
        State.RECOMMEND: State.VERIFY,
        State.VERIFY: State.HUMAN_APPROVAL,
        State.HUMAN_APPROVAL: State.EXECUTE if approved else State.CLOSE,
        State.EXECUTE: State.CLOSE,
    }
    return transitions[current]
```

### 7.5 Eval + Self-Upgrade Candidate Generation

```python
# services/eval_orchestrator/prompt_upgrade.py
from statistics import mean


def propose_prompt_upgrade(baseline_scores: list[float], candidate_scores: list[float]) -> dict:
    base = mean(baseline_scores)
    cand = mean(candidate_scores)
    delta = cand - base
    return {
        "approved_for_review": delta >= 0.03,
        "delta": round(delta, 4),
        "guardrails": [
            "no-policy-bypass",
            "no-autonomous-goal-change",
            "human-approval-required",
        ],
    }
```

## 8) Scenario Walkthrough (Cinematic + Credible)

1. **Live Event Arrival (00:00)**: endpoint telemetry reports suspicious credential replay from a privileged account.
2. **Machine-Speed Triage (00:01)**: TriageAgent marks priority `P1` due to identity + asset criticality.
3. **Context Enrichment (00:03)**: EnrichmentAgent links account, device, and geolocation anomalies in ontology timeline.
4. **Correlation (00:05)**: CorrelationAgent identifies similar pattern from prior campaign with 0.82 confidence.
5. **Recommendation (00:07)**: RecommendationAgent proposes `temporary token revocation + session isolation + targeted hunt`.
6. **Policy Verification (00:08)**: VerifierAgent confirms coalition and mission policy constraints are satisfied.
7. **Human Approval (00:10)**: operator reviews action package, approves with one modification (`exclude partner subnet`).
8. **Execution (00:12)**: action runs via approved tooling; audit record appended with signed provenance.
9. **Outcome Feedback (T+2h)**: mission marked successful, false-positive risk low, operator trust score +1.
10. **Self-Improvement (Nightly)**: eval pipeline learns from operator edit (`exclude partner subnet`) and proposes routing rule update for similar missions; human board approves; Apollo canary deploys change to 10% traffic with rollback guard.

## 9) Success Metrics
- Precision@TopAction
- Recall on mission-relevant detections
- Median time-to-triage
- Time-to-human-decision
- Policy violation rate (target: 0)
- Operator trust index
- Mission outcome impact score

---

This design gives **ClearGlassInc Artemis** a production-grade, self-evolving intelligence platform where AI continuously improves within explicit human and policy boundaries.
