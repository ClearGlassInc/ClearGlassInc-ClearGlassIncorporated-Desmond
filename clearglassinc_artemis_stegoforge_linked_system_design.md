# ClearGlassInc Artemis — STEGOFORGE Self-Evolving Intelligence Platform

## System Architecture

ClearGlassInc Artemis runs STEGOFORGE as a policy-constrained, continuously improving intelligence platform across Palantir Gotham, Foundry, AIP, and Apollo.

### 1) Frontend Layer (Operator UX)
- **Mission Console (Web UI)**: React + TypeScript + Tailwind + terminal-themed panel set.
- **Analyst Copilot Panel**: natural-language query + ontology-backed drill-down.
- **Commander Action Board**: approval gates for operationally significant actions.
- **Forensic Terminal View**: modules for Encode, Decode, Detect, Scan, Encrypt, Diff.

### 2) API + Application Layer
- **API Gateway**: request authentication, policy pre-checks, schema validation.
- **Domain Services (Python/FastAPI)**:
  - Incident triage service
  - Entity correlation service
  - Recommendation service
  - Action package generator
- **Workflow Engine**: state machines for triage → enrichment → recommendation → approval.

### 3) Data + Ontology Layer (Foundry)
- **Ingestion**: live telemetry, OSINT, HUMINT/SIGINT-derived metadata, case records.
- **Foundry Pipelines**: normalization, deduplication, confidence scoring, entity resolution.
- **Ontology**: entities, temporal relationships, mission context, lineage and provenance.
- **Data products**: mission-scoped datasets with row/column/entity ACLs.

### 4) Operational Intelligence Layer (Gotham)
- **Case Graphing**: graph views for actors, devices, campaigns, infrastructure.
- **Investigations**: linked evidence boards with confidence + source quality overlays.
- **Alert to Case Automation**: event correlation opens/updates cases with human review.

### 5) AI Orchestration Layer (AIP)
- **Model Router**: policy-constrained routing by task class (summarization, extraction, reasoning).
- **Agent Toolkit**: ontology query tool, case update tool, intel package drafting tool.
- **Evaluation Harness**: prompt variants, workflow variants, decision quality scoring.
- **Guardrailed self-improvement**: proposals are generated automatically; deployment is human-approved.

### 6) Deployment + Runtime Layer (Apollo)
- **Progressive delivery**: canary, blue/green, mission-segment rollout.
- **Rollback**: one-click or policy-triggered rollback on quality drift.
- **Runtime controls**: kill switches for tools, prompts, or model routes by mission boundary.
- **Cryptographic attestation**: versioned artifacts with immutable release manifests.

### 7) Observability + Governance Layer
- **Metrics**: precision/recall, false-positive rate, time-to-triage, operator trust score.
- **Tracing**: request-level and agent-step-level trace IDs across services.
- **Audit logs**: immutable logs for prompts, tool calls, approvals, and policy decisions.
- **Drift monitors**: concept drift, prompt decay, latency and reliability regression.

---

## Data and Ontology

## Core Entity Model

```sql
-- Foundry-backed logical schema (portable SQL style)
CREATE TABLE entity (
  entity_id            TEXT PRIMARY KEY,
  entity_type          TEXT NOT NULL,            -- Person, Device, Org, Malware, IOC, Case, Mission
  display_name         TEXT,
  confidence_score     DOUBLE PRECISION NOT NULL,
  risk_score           DOUBLE PRECISION,
  temporal_start_ts    TIMESTAMP,
  temporal_end_ts      TIMESTAMP,
  mission_id           TEXT,
  coalition_domain     TEXT NOT NULL,
  created_at           TIMESTAMP NOT NULL,
  updated_at           TIMESTAMP NOT NULL
);

CREATE TABLE relationship (
  relationship_id      TEXT PRIMARY KEY,
  src_entity_id        TEXT NOT NULL,
  dst_entity_id        TEXT NOT NULL,
  relationship_type    TEXT NOT NULL,
  confidence_score     DOUBLE PRECISION NOT NULL,
  provenance_ref       TEXT NOT NULL,
  first_seen_ts        TIMESTAMP,
  last_seen_ts         TIMESTAMP,
  mission_id           TEXT,
  FOREIGN KEY (src_entity_id) REFERENCES entity(entity_id),
  FOREIGN KEY (dst_entity_id) REFERENCES entity(entity_id)
);

CREATE TABLE evidence (
  evidence_id          TEXT PRIMARY KEY,
  source_system        TEXT NOT NULL,
  source_uri           TEXT,
  content_hash         TEXT NOT NULL,
  classification       TEXT NOT NULL,
  lineage_chain        TEXT NOT NULL,
  ingest_ts            TIMESTAMP NOT NULL,
  confidence_score     DOUBLE PRECISION NOT NULL
);
```

## Ontology Concepts
- **Temporal state**: each entity/relationship has active windows; AI responses must respect time-slicing.
- **Mission context**: `mission_id` binds records, workflows, and permissions.
- **Lineage/provenance**: every analytic claim references source evidence IDs.
- **Confidence semantics**: confidence is attached to every inferred edge and narrative statement.
- **Permissions as first-class attributes**: coalition domain + compartment tags drive tool output filtering.

## Ontology-Driven Behavior
- Copilot prompts include mission context, classification rules, and evidence constraints.
- Agents cannot propose operational actions without confidence and provenance thresholds.
- Recommendation ranking is a function of risk score, confidence, timeliness, and mission intent.

---

## AI and Agent Design

## Agent Topology
- **Analyst Copilot Agent**: retrieval + synthesis + timeline generation.
- **Triage Agent**: event severity estimation and duplicate suppression.
- **Enrichment Agent**: IOC enrichment, entity resolution, external correlation.
- **Recommendation Agent**: ranked COAs (courses of action).
- **Compliance Agent**: validates policy and approval prerequisites.

## Multi-Agent Workflow
1. Event arrives from streaming layer.
2. Triage agent assigns severity and links known entities.
3. Enrichment agent expands graph + confidence scores.
4. Recommendation agent drafts response package.
5. Compliance agent checks policy gates.
6. Human operator approves/rejects.
7. Outcome captured for eval and future optimization.

## Tool-Using Agent Capabilities
- Query Foundry ontology datasets.
- Search Gotham case graph.
- Draft intel summaries and action packages.
- Open/update case records.
- Trigger controlled workflow transitions.

## Approval Gates
- Any external action (blocking infra, contacting partner, escalating mission posture) requires:
  - dual attestation (operator + commander for high-impact missions),
  - policy checks,
  - immutable decision log entries.

---

## Self-Improvement Loop

## Signal Capture
- Operator thumbs-up/down and free-text correction notes.
- Query logs and prompt/tool traces.
- Alert outcomes (true positive, false positive, missed detection).
- Mission success metrics (MTTR, prevented impact, analyst trust score).

## Optimization Pipeline
1. **Harvest**: periodic ETL composes training/eval slices.
2. **Generate candidates**:
   - prompt variants,
   - workflow branching variants,
   - router policy variants.
3. **Run eval harness** on historical and shadow-live datasets.
4. **Score** by precision, recall, latency, policy compliance, and trust delta.
5. **Create change proposal** with explainability report.
6. **Human approval** required for production promotion.
7. **Canary rollout** and drift watch.
8. **Auto rollback** if guardrail thresholds fail.

## Safety Constraints
- No autonomous objective changes.
- No bypass of mission policy, classification, or human approval gates.
- No direct deployment to production without approval ticket.

---

## Full-Stack Implementation

## Reference Runtime Stack
- **Frontend**: React + Vite + TypeScript + Tailwind + xterm.js.
- **Backend**: Python FastAPI + Pydantic + asyncio workers.
- **Stream/Event Bus**: Kafka-compatible topic mesh.
- **Storage**: Lakehouse + graph index + vector index + case store.
- **AI**: AIP model gateway with policy-constrained routing.
- **Identity**: OIDC/SAML + ABAC + mission-scoped claims.
- **Observability**: OpenTelemetry, metrics TSDB, eval dashboard service.

## API Surface (example)
- `POST /v1/events/intake`
- `POST /v1/cases/{id}/recommendations`
- `POST /v1/actions/{id}/approve`
- `POST /v1/self-improve/proposals`
- `GET /v1/evals/runs/{run_id}`

---

## Security and Governance

- **Need-to-know ABAC**: enforced at API, query, and tool execution layers.
- **Row/column/entity ACLs**: mission and coalition tags enforced in retrieval.
- **Compartmentalization**: domain boundaries enforced per tenant + mission + clearance.
- **Zero trust**: every request authenticated, authorized, and policy-evaluated.
- **Immutable logs**: append-only event store with hash-chain attestations.
- **Prompt governance**: versioned prompts with risk labels and approval metadata.
- **Model governance**: approved model registry, task-safe routing policies.
- **Policy-as-code**: deployable, testable rules for all high-impact operations.

---

## Code Examples

### Python backend service (FastAPI + workflow trigger)

```python
# services/intake_api.py
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from stegoforge.engine import WorkflowEngine
from stegoforge.policy import PolicyEngine

app = FastAPI(title="ClearGlassInc Artemis STEGOFORGE API")
workflow = WorkflowEngine()
policy = PolicyEngine()


class EventIn(BaseModel):
    event_id: str
    mission_id: str
    coalition_domain: str
    payload: dict


@app.post("/v1/events/intake")
async def intake_event(event: EventIn, principal=Depends(policy.principal_context)):
    policy.assert_can_ingest(principal=principal, mission_id=event.mission_id)
    run_id = await workflow.start_triage(event.model_dump(), principal)
    return {"status": "accepted", "run_id": run_id}
```

### Python event handler (stream consumer)

```python
# workers/triage_consumer.py
from stegoforge.messaging import consume_topic
from stegoforge.agents import triage_agent, enrichment_agent


async def run():
    async for msg in consume_topic("intel.events.raw"):
        triage = await triage_agent.score(msg)
        if triage["duplicate"]:
            continue
        enriched = await enrichment_agent.expand_entities(msg, triage)
        await consume_topic.publish("intel.events.enriched", enriched)
```

### Ontology-driven query policy (Python)

```python
# stegoforge/policy.py
from dataclasses import dataclass


@dataclass
class Principal:
    user_id: str
    missions: set[str]
    clearance: str
    coalition_domain: str


class PolicyEngine:
    def assert_can_query(self, principal: Principal, mission_id: str, domain: str) -> None:
        if mission_id not in principal.missions:
            raise PermissionError("mission access denied")
        if principal.coalition_domain != domain:
            raise PermissionError("coalition boundary violation")
```

### Workflow state machine (Python)

```python
# stegoforge/workflow.py
from enum import Enum


class Stage(str, Enum):
    TRIAGE = "TRIAGE"
    ENRICH = "ENRICH"
    RECOMMEND = "RECOMMEND"
    WAIT_APPROVAL = "WAIT_APPROVAL"
    EXECUTE = "EXECUTE"
    CLOSED = "CLOSED"


TRANSITIONS = {
    Stage.TRIAGE: [Stage.ENRICH],
    Stage.ENRICH: [Stage.RECOMMEND],
    Stage.RECOMMEND: [Stage.WAIT_APPROVAL],
    Stage.WAIT_APPROVAL: [Stage.EXECUTE, Stage.CLOSED],
    Stage.EXECUTE: [Stage.CLOSED],
}
```

### Eval pipeline (Python)

```python
# stegoforge/evals.py
from statistics import mean


def evaluate(candidate_outputs: list[dict], truth: list[dict]) -> dict:
    precision = mean(x["precision"] for x in candidate_outputs)
    recall = mean(x["recall"] for x in candidate_outputs)
    latency_ms = mean(x["latency_ms"] for x in candidate_outputs)
    policy_violations = sum(x["policy_violations"] for x in candidate_outputs)
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "latency_ms": round(latency_ms, 2),
        "policy_violations": policy_violations,
        "pass": precision >= 0.9 and recall >= 0.85 and policy_violations == 0,
    }
```

### TypeScript UI-to-API hook

```ts
// ui/src/api/intake.ts
export async function sendEvent(event: {
  event_id: string;
  mission_id: string;
  coalition_domain: string;
  payload: Record<string, unknown>;
}) {
  const res = await fetch("/v1/events/intake", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(event),
  });
  if (!res.ok) throw new Error(`Intake failed: ${res.status}`);
  return res.json();
}
```

---

## Scenario Walkthrough (Cinematic + Operationally Credible)

1. **00:00:03 UTC**: A suspicious beaconing pattern enters `intel.events.raw` from coalition sensor grid.
2. **00:00:04**: Triage agent scores severity 0.91, links to prior malware cluster, opens case candidate.
3. **00:00:06**: Enrichment agent resolves C2 infrastructure and ties activity to known campaign entity.
4. **00:00:09**: Recommendation agent proposes three COAs: isolate segment, push YARA update, notify partner node.
5. **00:00:10**: Compliance agent flags COA-3 as cross-coalition, requiring commander approval.
6. **00:00:15**: Analyst approves COA-1 and COA-2; commander defers COA-3 pending legal review.
7. **00:00:17**: Actions execute through controlled runbook services; case state transitions to `EXECUTE`.
8. **+30 min**: Outcome confirms containment and no lateral movement.
9. **Nightly self-improvement cycle**:
   - logs decision traces,
   - compares recommended vs approved actions,
   - identifies that COA ranking overweighted noisy external feed,
   - proposes prompt + routing adjustment,
   - eval harness shows +4.3% precision, -8% false positives,
   - human reviewer approves,
   - Apollo canary rollout begins with automatic rollback thresholds.

---

## Screenshot Linkage (from provided references)

- Repository/mobile screenshot reference: [IMG_3402.jpeg](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/155441193/9f8ea619-7951-498c-956f-8f539fa3bea0/IMG_3402.jpeg)
- Suggested UI flow linking:
  1. Repo root → `docs/clearglassinc_artemis_stegoforge_linked_system_design.md`
  2. Website root → `artemis.html` “STEGOFORGE Console” button
  3. `artemis.html` deep links → mission console modules (Encode/Decode/Detect/Scan/Encrypt/Diff)

