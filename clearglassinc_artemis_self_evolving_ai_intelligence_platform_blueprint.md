# ClearGlassInc Artemis Self-Evolving AI Intelligence Platform Blueprint

## System Architecture

ClearGlassInc Artemis is a secure, coalition-aware intelligence platform that combines Palantir Gotham for operational intelligence, Foundry for data integration and ontology-backed applications, AIP for governed AI copilots and agents, and Apollo for controlled deployment, rollback, and runtime policy. The design assumes human-approved self-improvement: the platform may propose better prompts, workflows, model routes, and heuristics, but cannot promote them without explicit review gates.

### Layered reference architecture

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Web UI: analyst cockpit, commander board, eval dashboard, approval console    │
├──────────────────────────────────────────────────────────────────────────────┤
│ API gateway: OIDC, mTLS, request signing, rate limits, tenant compartments    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Mission services: cases, alerts, tasks, action packages, feedback, products   │
├──────────────────────────────────────────────────────────────────────────────┤
│ AIP orchestration: copilots, agents, tools, evals, model router, prompt store │
├──────────────────────────────────────────────────────────────────────────────┤
│ Gotham: entity tracking, link analysis, investigations, operational context   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Foundry: ontology, pipelines, transforms, lineage, decisions, applications    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Data plane: streams, lakehouse, vector search, graph index, audit/event logs  │
├──────────────────────────────────────────────────────────────────────────────┤
│ Policy plane: need-to-know, coalition boundaries, ABAC, policy-as-code        │
├──────────────────────────────────────────────────────────────────────────────┤
│ Apollo: deployment rings, canaries, signed artifacts, rollback, runtime flags │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Core responsibilities

| Component | Role in ClearGlassInc Artemis |
|---|---|
| Gotham | Operational intelligence, entity tracking, investigations, watchlists, link analysis, and mission context. |
| Foundry | Data integration, ontology modeling, pipeline transforms, lineage, application logic, and governed data products. |
| AIP | AI copilots, tool-using agents, workflow automation, evaluations, prompt governance, and human approval gates. |
| Apollo | Secure deployment, runtime configuration, rollback, environment promotion, health checks, and fleet governance. |
| Python precision layer | Deterministic scoring, calibration, statistical drift detection, eval aggregation, routing optimization, and audit-safe numerics. |

## Data and Ontology

The Foundry ontology is the operational contract between humans, agents, and systems. Every entity includes lineage, confidence, temporal state, mission context, and permissions so an AI action can be traced to exactly what it knew, when it knew it, and whether the operator was allowed to see it.

### Entity model

```yaml
ontology:
  entities:
    Person:
      keys: [person_id]
      properties: [name, aliases, biometric_refs, affiliation, clearance_tags, confidence]
    Organization:
      keys: [org_id]
      properties: [name, type, country, risk_score, coalition_visibility]
    Asset:
      keys: [asset_id]
      properties: [asset_type, owner_org, location, readiness, telemetry_refs]
    Event:
      keys: [event_id]
      properties: [event_type, observed_at, source_ids, severity, confidence, status]
    Signal:
      keys: [signal_id]
      properties: [source, modality, raw_ref, normalized_payload, quality_score]
    Case:
      keys: [case_id]
      properties: [mission_id, owner_cell, priority, state, assigned_operator]
    Alert:
      keys: [alert_id]
      properties: [rule_id, severity, triage_state, explanation, recommended_actions]
    IntelProduct:
      keys: [product_id]
      properties: [classification, summary, citations, confidence, approval_state]
    AgentRun:
      keys: [run_id]
      properties: [agent_name, prompt_version, model_route, tool_calls, outcome]
    ImprovementProposal:
      keys: [proposal_id]
      properties: [target_type, target_version, eval_delta, risk_rating, approval_state]
  relationships:
    - Person AFFILIATED_WITH Organization
    - Person OBSERVED_AT Event
    - Signal SUPPORTS Event
    - Event TRIGGERS Alert
    - Alert OPENS Case
    - Case PRODUCES IntelProduct
    - AgentRun READS Entity
    - AgentRun PROPOSES ImprovementProposal
```

### Permission-aware temporal state

Each ontology object stores immutable observations and derived current state separately. Agents never overwrite ground truth; they append claims with lineage.

```sql
CREATE TABLE ontology_claims (
  claim_id UUID PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  predicate TEXT NOT NULL,
  value_json JSONB NOT NULL,
  valid_time TSRANGE NOT NULL,
  transaction_time TIMESTAMPTZ NOT NULL DEFAULT now(),
  confidence NUMERIC(5,4) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  source_ids TEXT[] NOT NULL,
  lineage_hash TEXT NOT NULL,
  compartments TEXT[] NOT NULL,
  releasability TEXT[] NOT NULL
);

CREATE INDEX ontology_claims_entity_time_idx
  ON ontology_claims (entity_type, entity_id, valid_time);
```

### Human and AI workflow coupling

- Humans see cases, alerts, and entity graphs filtered through policy.
- Agents receive the same ontology objects plus machine-readable permission envelopes.
- Tool calls must cite ontology claims and lineage hashes.
- Recommendations include confidence, counter-evidence, and required approval authority.

## AI and Agent Design

AIP hosts governed copilots and multi-agent workflows. Each agent has a mission-specific policy profile, tool allowlist, model route, prompt version, eval suite, and approval requirements.

### Copilots

| Copilot | Users | Capabilities | Hard gates |
|---|---|---|---|
| Analyst Copilot | Investigators and analysts | Entity summaries, link analysis, hypothesis generation, source citation, case notes. | Cannot create operational action packages without analyst confirmation. |
| Commander Copilot | Command staff | Mission rollups, risk deltas, courses of action, resource impact summaries. | Requires commander approval for tasking recommendations. |
| Data Steward Copilot | Data owners | Pipeline health, ontology mapping suggestions, quality remediation. | Cannot promote schema or transform changes without steward approval. |
| Governance Copilot | Auditors and policy leads | Access reviews, prompt diffs, eval deltas, provenance reports. | Read-only except creating review tickets. |

### Multi-agent workflow

```text
Live signal
  → Intake Agent: validate source, normalize schema, attach lineage
  → Triage Agent: classify severity, de-duplicate, estimate confidence
  → Enrichment Agent: query Gotham/Foundry ontology, retrieve related cases
  → Correlation Agent: build graph hypotheses and competing explanations
  → Product Agent: draft analyst brief with citations and uncertainty
  → Recommendation Agent: prepare action package with explicit approval gate
  → Governance Agent: evaluate policy, auditability, and release constraints
```

### Tool contract

```json
{
  "tool_name": "query_ontology",
  "input_schema": {
    "mission_id": "string",
    "entity_types": ["Person", "Organization", "Event", "Alert"],
    "filters": {"classification_max": "SECRET", "compartments": ["ARTEMIS"]},
    "purpose": "case_enrichment"
  },
  "output_schema": {
    "records": "array",
    "lineage": "array",
    "policy_decision": "allow|deny|redact",
    "redactions": "array"
  },
  "approval_required": false,
  "audit_required": true
}
```

## Self-Improvement Loop

The platform gets better by converting operational signals into evals and reviewed proposals. It does not autonomously change goals, policy, mission priorities, or operational thresholds outside approved guardrails.

### Signals captured

- Operator thumbs-up/down and structured correction reasons.
- Edits to generated summaries, citations, and action packages.
- Query logs, abandoned searches, and repeated refinement patterns.
- Alert outcomes: true positive, false positive, duplicate, stale, escalated.
- Mission results and post-action review findings.
- Latency, cost, retrieval quality, hallucination flags, and policy denials.

### Upgrade pipeline

```text
Telemetry capture
  → Feature extraction in Foundry
  → Eval case generation
  → Offline replay against candidate prompts/workflows/routes
  → Statistical comparison in Python
  → Risk scoring and policy validation
  → ImprovementProposal ontology object
  → Human review in AIP approval console
  → Apollo canary deployment
  → Online monitoring and automatic rollback on guardrail breach
```

### Versioned improvement object

```yaml
ImprovementProposal:
  proposal_id: imp-2026-0630-001
  target_type: prompt
  target_name: triage_agent_v7
  current_version: 7.3.1
  candidate_version: 7.4.0
  eval_delta:
    precision: +0.037
    recall: +0.012
    p95_latency_ms: -140
    policy_violations: 0
  blast_radius: ring_0_shadow_then_ring_1_analyst
  rollback_condition: false_positive_rate_delta > 0.02 OR policy_denials > baseline + 3sigma
  approval_state: pending_human_review
```

## Full-Stack Implementation

### Web UI

- React/TypeScript mission cockpit.
- Entity graph, case timeline, alert queue, source viewer, and approval console.
- Eval dashboard showing prompt/workflow/model versions and metric deltas.
- Commander view optimized for latency, confidence, and action packages.

### API and services

- API gateway with OIDC, mTLS, request signing, WAF, and per-compartment rate limits.
- Python FastAPI mission services for deterministic workflows and policy calls.
- Event bus using Kafka-compatible topics for signals, alerts, feedback, eval results, and deployments.
- Search stack with lexical retrieval, vector retrieval, and graph expansion.
- Model router that chooses model/provider/region based on mission, classification, latency, cost, and eval score.

### Deployment

Apollo manages signed releases through rings:

1. `shadow`: replay only, no operator impact.
2. `ring_0_lab`: synthetic and historical eval traffic.
3. `ring_1_analyst`: limited analyst cohort.
4. `ring_2_mission`: production mission cells.
5. `ring_3_coalition`: coalition-approved release with releasability checks.

## Security and Governance

### Need-to-know controls

- Attribute-based access control with clearance, compartment, mission assignment, role, location, and purpose.
- Row, column, entity, edge, and claim-level permissions.
- Coalition boundaries enforced before retrieval, prompt construction, and tool output.
- Redaction is applied before model context assembly, not after model generation.

### Zero-trust execution

- Every service uses workload identity, mTLS, signed artifacts, and short-lived credentials.
- Tools run in constrained sandboxes with allowlisted network and data access.
- Prompt, workflow, policy, and model versions are immutable and hash-addressed.
- Audit logs are append-only and replicated to a write-once evidence store.

### Governance artifacts

```yaml
policy_as_code:
  prompt_change_requires:
    - eval_suite_passed
    - no_new_policy_violations
    - reviewer_role: AI_GOVERNANCE_LEAD
  operational_action_requires:
    - human_approval
    - source_citations
    - confidence_threshold_met
    - commander_or_delegate_signature
  coalition_release_requires:
    - releasability_tags
    - data_owner_approval
    - redaction_test_passed
```

## Code Examples

### Python policy check

```python
from dataclasses import dataclass
from enum import Enum

class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REDACT = "redact"

@dataclass(frozen=True)
class Principal:
    user_id: str
    role: str
    clearance: str
    compartments: set[str]
    coalition: str | None
    mission_ids: set[str]

@dataclass(frozen=True)
class Resource:
    entity_id: str
    classification: str
    compartments: set[str]
    releasability: set[str]
    mission_id: str

CLEARANCE_ORDER = {"UNCLASSIFIED": 0, "CONFIDENTIAL": 1, "SECRET": 2, "TOP_SECRET": 3}

def authorize(principal: Principal, resource: Resource, purpose: str) -> Decision:
    if CLEARANCE_ORDER[principal.clearance] < CLEARANCE_ORDER[resource.classification]:
        return Decision.DENY
    if not resource.compartments.issubset(principal.compartments):
        return Decision.REDACT
    if resource.mission_id not in principal.mission_ids:
        return Decision.DENY
    if principal.coalition and principal.coalition not in resource.releasability:
        return Decision.REDACT
    if purpose not in {"case_enrichment", "alert_triage", "approved_briefing"}:
        return Decision.DENY
    return Decision.ALLOW
```

### FastAPI event ingestion service

```python
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="ClearGlassInc Artemis Mission API")

class SignalIn(BaseModel):
    source: str
    modality: str
    observed_at: datetime
    payload: dict
    compartments: list[str] = Field(default_factory=list)
    releasability: list[str] = Field(default_factory=list)

class SignalOut(BaseModel):
    signal_id: str
    lineage_hash: str
    accepted_at: datetime

def hash_lineage(signal: SignalIn) -> str:
    import hashlib, json
    canonical = json.dumps(signal.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()

@app.post("/v1/signals", response_model=SignalOut)
async def ingest_signal(signal: SignalIn, principal=Depends(...)) -> SignalOut:
    if not set(signal.compartments).issubset(principal.compartments):
        raise HTTPException(status_code=403, detail="compartment denied")

    signal_id = f"sig-{uuid4()}"
    lineage_hash = hash_lineage(signal)
    event = {
        "signal_id": signal_id,
        "source": signal.source,
        "modality": signal.modality,
        "observed_at": signal.observed_at.isoformat(),
        "payload": signal.payload,
        "lineage_hash": lineage_hash,
        "accepted_at": datetime.now(timezone.utc).isoformat(),
    }
    await publish("artemis.signal.accepted", event)
    return SignalOut(signal_id=signal_id, lineage_hash=lineage_hash, accepted_at=datetime.now(timezone.utc))
```

### Ontology-driven query

```python
async def query_related_events(foundry_client, principal: Principal, person_id: str, mission_id: str):
    query = {
        "root": {"type": "Person", "id": person_id},
        "traverse": [
            {"edge": "OBSERVED_AT", "to": "Event"},
            {"edge": "TRIGGERS", "to": "Alert", "optional": True},
        ],
        "filters": {"mission_id": mission_id, "valid_time": "last_30_days"},
        "policy_context": {
            "user_id": principal.user_id,
            "clearance": principal.clearance,
            "compartments": sorted(principal.compartments),
            "purpose": "case_enrichment",
        },
    }
    result = await foundry_client.ontology.graph_query(query)
    return [record for record in result.records if record.policy_decision != "deny"]
```

### Tool-using AIP agent skeleton

```python
class ArtemisAgent:
    def __init__(self, model_router, tool_registry, audit_log):
        self.model_router = model_router
        self.tool_registry = tool_registry
        self.audit_log = audit_log

    async def triage_alert(self, alert_id: str, mission_id: str, principal: Principal) -> dict:
        tools = ["query_ontology", "retrieve_cases", "create_draft_intel_product"]
        model = await self.model_router.route(
            task="alert_triage",
            classification=principal.clearance,
            latency_budget_ms=1500,
            required_evals=["citation_grounding", "policy_compliance", "triage_precision"],
        )
        context = await self.tool_registry.call(
            "query_ontology",
            {"mission_id": mission_id, "alert_id": alert_id, "purpose": "alert_triage"},
            principal=principal,
        )
        response = await model.generate(
            prompt_version="triage_agent_v7.3.1",
            messages=[{"role": "system", "content": "Cite claims. Preserve uncertainty. Do not recommend action without approval gate."},
                      {"role": "user", "content": str(context)}],
            tools=tools,
        )
        await self.audit_log.write({"alert_id": alert_id, "model": model.name, "prompt": "triage_agent_v7.3.1", "response": response})
        return response
```

### Workflow state machine

```python
from transitions import Machine

class ActionPackageWorkflow:
    states = [
        "drafted",
        "policy_checked",
        "analyst_review",
        "commander_review",
        "approved",
        "rejected",
        "deployed",
        "rolled_back",
    ]

    def __init__(self):
        self.machine = Machine(model=self, states=self.states, initial="drafted")
        self.machine.add_transition("check_policy", "drafted", "policy_checked", conditions=["policy_passed"])
        self.machine.add_transition("send_to_analyst", "policy_checked", "analyst_review")
        self.machine.add_transition("analyst_approve", "analyst_review", "commander_review")
        self.machine.add_transition("commander_approve", "commander_review", "approved")
        self.machine.add_transition("reject", "*", "rejected")
        self.machine.add_transition("deploy", "approved", "deployed")
        self.machine.add_transition("rollback", "deployed", "rolled_back")

    def policy_passed(self) -> bool:
        return self.policy_decision == "allow" and self.has_citations and self.confidence >= 0.72
```

### Python eval pipeline for precision

```python
from decimal import Decimal
from statistics import mean

@dataclass(frozen=True)
class EvalResult:
    prompt_version: str
    true_positive: int
    false_positive: int
    false_negative: int
    latency_ms: int
    policy_violations: int

    @property
    def precision(self) -> Decimal:
        denominator = self.true_positive + self.false_positive
        return Decimal(self.true_positive) / Decimal(denominator or 1)

    @property
    def recall(self) -> Decimal:
        denominator = self.true_positive + self.false_negative
        return Decimal(self.true_positive) / Decimal(denominator or 1)

def compare_candidate(baseline: list[EvalResult], candidate: list[EvalResult]) -> dict:
    base_precision = mean(float(x.precision) for x in baseline)
    cand_precision = mean(float(x.precision) for x in candidate)
    base_recall = mean(float(x.recall) for x in baseline)
    cand_recall = mean(float(x.recall) for x in candidate)
    policy_violations = sum(x.policy_violations for x in candidate)
    return {
        "precision_delta": cand_precision - base_precision,
        "recall_delta": cand_recall - base_recall,
        "candidate_p95_latency_ms": percentile([x.latency_ms for x in candidate], 95),
        "policy_violations": policy_violations,
        "promotable": cand_precision >= base_precision and policy_violations == 0,
    }
```

### TypeScript approval console client

```tsx
type ImprovementProposal = {
  proposalId: string;
  targetType: "prompt" | "workflow" | "model_route" | "heuristic";
  currentVersion: string;
  candidateVersion: string;
  precisionDelta: number;
  recallDelta: number;
  p95LatencyDeltaMs: number;
  policyViolations: number;
  approvalState: "pending" | "approved" | "rejected" | "canary";
};

export function ProposalCard({ proposal }: { proposal: ImprovementProposal }) {
  const safe = proposal.policyViolations === 0 && proposal.precisionDelta >= 0;
  return (
    <section className="rounded-xl border p-4 shadow-sm">
      <h3>{proposal.targetType}: {proposal.candidateVersion}</h3>
      <p>Current: {proposal.currentVersion}</p>
      <p>Precision Δ: {proposal.precisionDelta.toFixed(3)}</p>
      <p>Recall Δ: {proposal.recallDelta.toFixed(3)}</p>
      <p>p95 latency Δ: {proposal.p95LatencyDeltaMs}ms</p>
      <p>Policy violations: {proposal.policyViolations}</p>
      <button disabled={!safe} data-action="approve-canary">Approve canary</button>
      <button data-action="reject">Reject</button>
    </section>
  );
}
```

## Scenario Walkthrough

1. A live signal enters from an approved sensor stream. The ingestion service validates source identity, hashes the payload, writes an immutable signal object, and publishes `artemis.signal.accepted`.
2. The triage agent normalizes the signal, checks Foundry ontology relationships, and compares it with Gotham cases. It finds two related events and one unresolved case.
3. The correlation agent builds a hypothesis graph and identifies that the signal may be a duplicate of a known pattern, but the timing and asset proximity raise the severity.
4. The product agent drafts a short intelligence product with source citations, confidence bands, and counter-evidence.
5. The recommendation agent prepares an action package but marks it `approval_required=true` because it could change operational posture.
6. The analyst rejects one suggested rationale, edits the summary, and marks the alert as true positive with low confidence.
7. The feedback service captures the rejection reason, the edited text, and the final case outcome.
8. Foundry transforms convert the outcome into eval cases. AIP replays the triage prompt against similar historical examples.
9. The Python eval harness finds that a candidate prompt reduces duplicate escalation while preserving recall.
10. A new `ImprovementProposal` is created with metric deltas, lineage, rollback conditions, and a canary plan.
11. A governance reviewer approves ring-0 shadow deployment. Apollo deploys the candidate prompt to shadow traffic.
12. If precision improves and no policy violations appear, the candidate can move to limited analyst canary. If false positives exceed threshold, Apollo automatically rolls back and records the failed proposal.

The result is a platform that learns from operator behavior and mission outcomes while preserving human authority, auditability, policy boundaries, and deterministic rollback.
