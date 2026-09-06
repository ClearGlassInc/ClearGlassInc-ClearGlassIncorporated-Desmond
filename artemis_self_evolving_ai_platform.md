# ClearGlassInc Artemis Self-Evolving AI Intelligence Platform Blueprint

## System Architecture

ClearGlassInc Artemis is a secure, coalition-aware, multi-domain intelligence platform that treats Palantir Gotham, Foundry, AIP, and Apollo as separate trust domains instead of one uncontrolled automation surface. Gotham is the operational-intelligence workspace for investigations, entity tracking, link analysis, and mission cases. Foundry is the integration, ontology, pipeline, and application-logic layer. AIP is the controlled AI copilot and agent layer for reasoning, evaluation, and workflow automation. Apollo is the deployment, runtime-control, versioning, rollback, and environment-promotion layer.

### End-to-end trust-domain map

```text
[Browser / Mission UI]
  -> [API Gateway + OIDC + mTLS + request signing]
  -> [Policy Enforcement Point]
  -> [Mission Backend Services]
  -> [Foundry Ontology + Pipelines + Object Sets]
  -> [Gotham Investigations + Entity Tracking]
  -> [AIP Agent Runtime + Model Router + Eval Harness]
  -> [Apollo Release Control + Runtime Guardrails]
  -> [Immutable Audit / Observability / Evidence Store]
```

### Major layers

| Layer | Responsibility | Primary controls |
|---|---|---|
| Web UI | Analyst cockpit, commander view, case workspace, eval dashboard, approval queue | OIDC, CSP, redaction, accessibility, no client-side authorization reliance |
| API gateway | Authentication, rate limits, request signing, tenant routing, schema validation | mTLS, JWT audience checks, WAF, replay protection |
| Backend services | Case orchestration, enrichment, workflow state, approvals, mission APIs | Server-side authorization, idempotency keys, typed events |
| Streaming layer | Live event ingestion and fanout | Partitioning by mission and compartment, bounded retries, dead-letter queues |
| Data/lakehouse | Raw, normalized, curated, and mission-specific datasets | Lineage, classification tags, retention, immutable raw zones |
| Foundry ontology | Canonical objects, relationships, actions, transforms, object sets | Row, column, entity, purpose, and compartment controls |
| Gotham layer | Entity tracking, investigations, operational workflows | Case-level provenance, source confidence, human annotations |
| AIP orchestration | Copilots, agents, tools, model routing, evals, prompt governance | Tool allowlists, approval gates, eval thresholds, red-team tests |
| Policy layer | Need-to-know decisions and action gates | Policy-as-code, deny by default, explainable decisions |
| Observability | Logs, metrics, traces, eval telemetry, audit evidence | Tamper-evident ledger, privacy-aware correlation IDs |
| Apollo deployment | Release promotion, canaries, rollback, environment control | Signed artifacts, progressive rollout, kill switches |

### Runtime architecture

```text
Live Sources -> Ingestion Adapters -> Event Bus -> Normalizers -> Foundry Object Sets
Historical Sources -> Batch Pipelines ----^                 -> Search/Retrieval Index
Foundry Ontology -> Mission APIs -> AIP Tools -> Agents -> Draft Recommendations
Gotham Cases <----- Human Review / Approval Queue <-------- Action Packages
Apollo Controls -> version pinning, canary rollout, rollback, policy bundles
Audit Plane <- every read, transform, inference, recommendation, approval, action
```

## Data and Ontology

The ontology is the contract between data, humans, AI agents, policy, and audit. It encodes what the system knows, how it knows it, who may see it, how confidence changes over time, and which actions are permitted.

### Core objects

| Entity | Purpose | Key fields |
|---|---|---|
| `Mission` | Operational context and authority boundary | `mission_id`, `objective`, `authority`, `classification`, `coalition_scope`, `status` |
| `Actor` | Person, organization, device, unit, account, or model actor | `actor_id`, `type`, `affiliation`, `confidence`, `last_seen_at` |
| `Asset` | Protected, observed, or operational resource | `asset_id`, `owner`, `criticality`, `location`, `compartments` |
| `Observation` | Atomic evidence from a source | `observation_id`, `source_id`, `payload_hash`, `observed_at`, `confidence` |
| `Event` | Normalized activity derived from observations | `event_id`, `event_type`, `entities`, `temporal_bounds`, `severity` |
| `Relationship` | Typed edge between ontology objects | `subject`, `predicate`, `object`, `valid_time`, `confidence` |
| `Case` | Gotham-style investigation container | `case_id`, `mission_id`, `lead_actor`, `status`, `assigned_team` |
| `IntelProduct` | Human-readable intelligence output | `product_id`, `sources`, `claims`, `confidence`, `release_markings` |
| `Recommendation` | AI-drafted, human-reviewable proposal | `recommendation_id`, `action_type`, `risk`, `evidence`, `approval_state` |
| `Approval` | Consequential-action authorization record | `approval_id`, `approver`, `decision`, `reason`, `expires_at` |
| `EvalRun` | Evaluation evidence for prompts, models, tools, and workflows | `eval_id`, `candidate_version`, `metrics`, `decision` |
| `PolicyDecision` | Immutable authorization and governance decision | `decision_id`, `subject`, `resource`, `action`, `allow`, `explanation` |

### Relationship model

```sql
CREATE TABLE ontology_relationships (
  relationship_id UUID PRIMARY KEY,
  subject_id TEXT NOT NULL,
  predicate TEXT NOT NULL,
  object_id TEXT NOT NULL,
  confidence NUMERIC(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  valid_from TIMESTAMPTZ NOT NULL,
  valid_to TIMESTAMPTZ,
  source_observation_ids UUID[] NOT NULL,
  lineage_hash TEXT NOT NULL,
  classification TEXT NOT NULL,
  compartments TEXT[] NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Confidence, lineage, temporal state, and permissions

- Confidence is not a single model score. It is a calibrated value derived from source reliability, corroboration, recency, transformation quality, and human adjudication.
- Lineage is preserved from raw observation through normalized event, ontology relationship, agent context, recommendation, approval, and final action.
- Temporal state uses valid time and transaction time so analysts can ask both “what was true then?” and “what did Artemis know then?”
- Permissions are attached to objects, edges, columns, derived products, search indexes, prompts, tool outputs, and logs.
- AI agents receive ontology-shaped context, not raw unrestricted data dumps. Every retrieved object carries policy metadata and provenance.

## AI and Agent Design

AIP hosts controlled copilots and multi-agent workflows. The system can propose improvements to prompts, workflow graphs, heuristics, and model routing, but never grants itself new objectives, tools, data access, deployment rights, or operational authority.

### Copilots

| Copilot | Users | Responsibilities |
|---|---|---|
| Analyst Copilot | Investigators and analysts | Query ontology, summarize evidence, draft hypotheses, compare timelines, prepare intel products |
| Commander Copilot | Mission leads | Summarize mission posture, surface tradeoffs, explain risk, draft decision briefs |
| Data Steward Copilot | Data owners | Review lineage gaps, schema drift, data quality, source reliability |
| Governance Copilot | Approvers and auditors | Explain policy decisions, verify approvals, inspect eval evidence |
| Deployment Copilot | Platform engineers | Review Apollo rollout health, canary metrics, rollback candidates |

### Multi-agent workflow topology

```text
Triage Agent
  -> Enrichment Agent
  -> Correlation Agent
  -> Confidence Calibration Agent
  -> Summarization Agent
  -> Recommendation Agent
  -> Policy Review Agent
  -> Human Approval Queue
  -> Action Package Draft or Rejection Learning Signal
```

### Agent boundaries

- Read tools can query authorized Foundry object sets, search indexes, case files, and audit summaries.
- Draft tools can create recommended case updates, intel products, tasking packages, and approval requests.
- Action tools are disabled unless policy permits the action and a valid human approval token exists.
- All tools require typed inputs, resource scopes, timeout budgets, idempotency keys, and audit metadata.
- Agents must return evidence references and uncertainty. Unsupported claims are rejected by deterministic validators.

## Self-Improvement Loop

The self-improvement loop converts operator behavior and mission outcomes into evaluated, reviewable, reversible change proposals.

### Signals captured

| Signal | Example | Use |
|---|---|---|
| Operator feedback | thumbs up/down, correction text, confidence override | Prompt and rubric improvements |
| Query logs | authorized query intent and result satisfaction | Retrieval tuning and ontology gaps |
| Alert outcomes | true positive, false positive, duplicate, stale | Triage threshold calibration |
| Case outcomes | resolved, escalated, rejected, reopened | Workflow and recommendation evaluation |
| Mission results | time to detect, time to brief, prevented loss | Outcome-weighted evals |
| Policy decisions | denied tool use, missing approval, compartment mismatch | Guardrail hardening |
| Drift telemetry | embedding drift, source distribution drift, latency drift | Model routing and pipeline quality checks |

### Safe self-improvement lifecycle

```text
1. Capture feedback and outcomes as immutable events.
2. Build evaluation datasets with lineage, labels, and classification controls.
3. Generate candidate changes: prompt, workflow, heuristic, router policy, or eval rubric.
4. Run offline regression, safety, security, bias, latency, and cost evals.
5. Compare candidate against pinned baseline with confidence intervals.
6. Produce a human-reviewable change package with diff, metrics, rollback plan, and residual risk.
7. Human approves or rejects the candidate.
8. Apollo deploys approved candidate to canary scope.
9. Runtime monitors guardrail violations, quality, latency, cost, and operator trust.
10. Promote, hold, or rollback based on predeclared gates.
```

### Versioned artifacts

| Artifact | Versioned fields | Promotion gate |
|---|---|---|
| Prompt | template, tools, citations rule, refusal policy, eval suite | No safety regression; better quality or lower latency/cost |
| Workflow | state graph, transitions, approvals, retries, SLAs | No forbidden-state reachability; canary success |
| Model route | model ID, fallback order, context limits, data boundary | Eval pass; compartment and export-control compliance |
| Heuristic | thresholds, weights, decay functions | Calibration and false-positive improvement |
| Policy bundle | Rego rules, data markings, action risk matrix | Security review and human authorization |

### Drift and rollback

- Drift detection runs on source distributions, ontology edge frequencies, embedding neighborhoods, model-output schemas, rejection rates, and operator override rates.
- Rollback is Apollo-controlled, version-pinned, and audited. A rollback never deletes evidence; it restores runtime configuration and preserves failed-candidate telemetry.
- Every self-upgrade candidate includes the baseline version, candidate version, eval run IDs, approval ID, rollout plan, kill switch, rollback target, and post-deployment observation window.

## Full-Stack Implementation

### Web UI

The UI uses a case-first mission cockpit:

- Mission timeline with live event stream and temporal filters.
- Entity graph with confidence, lineage, coalition markings, and relationship explanations.
- Recommendation panel with evidence, uncertainty, policy decision, and approval controls.
- Eval dashboard showing prompt/workflow candidates, baseline comparison, safety findings, and Apollo rollout state.
- Audit explorer with tamper-evident event chains and redacted views by clearance.

### API gateway

- OIDC identity from enterprise IdP.
- JWT `aud`, `iss`, `exp`, `sub`, `scp`, `mission`, and `compartment` validation.
- mTLS for service-to-service calls.
- JSON schema validation and max payload sizes.
- Request signing for consequential operations.
- Rate limits by user, mission, tenant, and tool.

### Backend services

```text
services/
  mission-api/          # cases, tasks, mission context
  ontology-api/         # object set queries and lineage views
  agent-orchestrator/   # AIP tool gateway and workflow state machines
  eval-service/         # datasets, offline evals, candidate scoring
  approval-service/     # human approval queue and action tokens
  audit-service/        # append-only ledger and evidence hashing
  policy-service/       # policy-as-code decisions and explanations
  deployment-service/   # Apollo release metadata and rollback controls
```

### Data and retrieval

- Raw landing zone stores immutable source payloads with hashes and classifications.
- Normalized zone stores typed, validated events.
- Curated ontology zone stores Foundry object sets and relationship edges.
- Retrieval layer indexes only authorized text chunks and graph neighborhoods; indexes inherit source markings.
- Search responses include source IDs, confidence, lineage, and policy decision IDs.

### Model router

The router selects an approved model by mission classification, data residency, latency budget, task type, eval score, cost ceiling, and failure mode. Fallbacks must not cross compartments or lower assurance boundaries.

## Security and Governance

### Need-to-know authorization

Authorization is evaluated at every service boundary and before every tool call. It considers user identity, role, clearance, mission membership, compartment, coalition markings, purpose of use, object classification, relationship sensitivity, and action risk.

### Governance invariants

- Consequential operational actions require explicit human approval.
- AI output is a draft until validated by policy and authorized by a person.
- Agents cannot expand their own tools, scope, privileges, persistence, objectives, or deployment targets.
- Every material read, inference, recommendation, approval, and action is audited.
- Policy denial fails closed and records an explainable `PolicyDecision`.
- Coalition views are derived from the same ontology but filtered through releasability rules and redaction transforms.

### Observability and audit

- Logs are structured and redact sensitive fields before emission.
- Metrics include precision, recall, false-positive rate, alert aging, human override rate, prompt regression rate, tool denial rate, p95 latency, cost per mission, and operator trust score.
- Traces carry correlation IDs, not secrets.
- Audit records are hash-chained and append-only.

## Code Examples

### Python policy-aware mission API

```python
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

class ActionRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]
    clearance: str
    mission_ids: frozenset[str]
    compartments: frozenset[str]

@dataclass(frozen=True)
class PolicyDecision:
    decision_id: UUID
    allow: bool
    reason: str
    evaluated_at: datetime

class PolicyEngine:
    def authorize(self, principal: Principal, action: str, resource: dict[str, Any]) -> PolicyDecision:
        compartments = set(resource.get("compartments", []))
        mission_id = resource.get("mission_id")
        if mission_id not in principal.mission_ids:
            return PolicyDecision(uuid4(), False, "principal_not_on_mission", datetime.now(UTC))
        if not compartments.issubset(principal.compartments):
            return PolicyDecision(uuid4(), False, "missing_compartment", datetime.now(UTC))
        if action.startswith("execute:") and "operator_approver" not in principal.roles:
            return PolicyDecision(uuid4(), False, "execution_requires_approver_role", datetime.now(UTC))
        return PolicyDecision(uuid4(), True, "allow", datetime.now(UTC))
```

### Python workflow state machine with approval gate

```python
from enum import StrEnum
from pydantic import BaseModel, Field

class RecState(StrEnum):
    DRAFTED = "drafted"
    POLICY_REVIEWED = "policy_reviewed"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    ROLLED_BACK = "rolled_back"

class Recommendation(BaseModel):
    recommendation_id: str
    mission_id: str
    action_type: str
    risk: ActionRisk
    state: RecState = RecState.DRAFTED
    evidence_ids: list[str] = Field(min_length=1)
    approval_id: str | None = None

ALLOWED_TRANSITIONS = {
    RecState.DRAFTED: {RecState.POLICY_REVIEWED},
    RecState.POLICY_REVIEWED: {RecState.PENDING_APPROVAL, RecState.REJECTED},
    RecState.PENDING_APPROVAL: {RecState.APPROVED, RecState.REJECTED},
    RecState.APPROVED: {RecState.EXECUTED},
    RecState.EXECUTED: {RecState.ROLLED_BACK},
}

def transition(rec: Recommendation, next_state: RecState) -> Recommendation:
    if next_state not in ALLOWED_TRANSITIONS.get(rec.state, set()):
        raise ValueError(f"forbidden transition: {rec.state} -> {next_state}")
    if next_state is RecState.EXECUTED and not rec.approval_id:
        raise ValueError("execution requires human approval_id")
    return rec.model_copy(update={"state": next_state})
```

### Python event handler for feedback-to-eval conversion

```python
from pydantic import BaseModel, Field

class OperatorFeedbackEvent(BaseModel):
    event_id: str
    mission_id: str
    case_id: str
    prompt_version: str
    workflow_version: str
    recommendation_id: str
    label: str = Field(pattern="^(accepted|rejected|corrected|unsafe|duplicate)$")
    correction: str | None = None
    source_claim_ids: list[str]

class EvalExample(BaseModel):
    input_ref: str
    expected_behavior: str
    negative_requirements: list[str]
    labels: dict[str, str]

async def feedback_to_eval_example(event: OperatorFeedbackEvent) -> EvalExample:
    negative = ["do_not_invent_sources", "respect_compartment_boundaries", "cite_evidence"]
    if event.label == "unsafe":
        negative.append("must_refuse_operational_action_without_approval")
    return EvalExample(
        input_ref=f"case://{event.case_id}/recommendation/{event.recommendation_id}",
        expected_behavior=event.correction or "match_operator_accepted_recommendation",
        negative_requirements=negative,
        labels={
            "mission_id": event.mission_id,
            "prompt_version": event.prompt_version,
            "workflow_version": event.workflow_version,
            "operator_label": event.label,
        },
    )
```

### Python model router

```python
@dataclass(frozen=True)
class ModelCandidate:
    model_id: str
    max_classification: str
    allowed_compartments: frozenset[str]
    p95_latency_ms: int
    eval_score: float
    cost_per_1k_tokens: float

@dataclass(frozen=True)
class InferenceRequest:
    task_type: str
    classification: str
    compartments: frozenset[str]
    latency_budget_ms: int
    min_eval_score: float

CLASSIFICATION_RANK = {"unclassified": 0, "controlled": 1, "secret": 2, "top_secret": 3}

def route_model(req: InferenceRequest, candidates: list[ModelCandidate]) -> ModelCandidate:
    eligible = [
        c for c in candidates
        if CLASSIFICATION_RANK[c.max_classification] >= CLASSIFICATION_RANK[req.classification]
        and req.compartments.issubset(c.allowed_compartments)
        and c.p95_latency_ms <= req.latency_budget_ms
        and c.eval_score >= req.min_eval_score
    ]
    if not eligible:
        raise RuntimeError("no approved model route satisfies mission constraints")
    return sorted(eligible, key=lambda c: (-c.eval_score, c.p95_latency_ms, c.cost_per_1k_tokens))[0]
```

### TypeScript API client shape

```ts
export type RecommendationRisk = "low" | "medium" | "high" | "critical";

export interface EvidenceRef {
  sourceId: string;
  claimId: string;
  confidence: number;
  lineageHash: string;
}

export interface RecommendationView {
  recommendationId: string;
  missionId: string;
  risk: RecommendationRisk;
  summary: string;
  evidence: EvidenceRef[];
  policyDecisionId: string;
  approvalState: "not_required" | "pending" | "approved" | "rejected";
}

export async function approveRecommendation(
  recommendationId: string,
  reason: string,
  idempotencyKey: string,
): Promise<{ approvalId: string }> {
  const response = await fetch(`/api/recommendations/${recommendationId}/approval`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "idempotency-key": idempotencyKey,
    },
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) throw new Error(`approval failed: ${response.status}`);
  return response.json();
}
```

### Rego-style policy-as-code sketch

```rego
package artemis.authz

default allow := false

allow if {
  input.subject.mission_ids[_] == input.resource.mission_id
  every c in input.resource.compartments { input.subject.compartments[_] == c }
  input.action == "read:ontology_object"
}

allow if {
  input.action == "draft:recommendation"
  input.subject.roles[_] == "analyst"
  input.subject.mission_ids[_] == input.resource.mission_id
}

allow if {
  input.action == "execute:operational_action"
  input.subject.roles[_] == "operator_approver"
  input.resource.approval.state == "approved"
  time.now_ns() < input.resource.approval.expires_at_ns
}
```

### SQL eval aggregation

```sql
SELECT
  candidate_version,
  baseline_version,
  AVG(precision_score) AS precision_score,
  AVG(recall_score) AS recall_score,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_latency_ms,
  SUM(CASE WHEN safety_violation THEN 1 ELSE 0 END) AS safety_violations,
  SUM(CASE WHEN policy_violation THEN 1 ELSE 0 END) AS policy_violations
FROM eval_runs
WHERE created_at >= now() - INTERVAL '14 days'
GROUP BY candidate_version, baseline_version
HAVING SUM(CASE WHEN safety_violation OR policy_violation THEN 1 ELSE 0 END) = 0;
```

## Scenario Walkthrough

1. A live event enters Artemis from a sensor, partner feed, or cyber telemetry stream. The ingestion adapter validates the payload, stamps source metadata, hashes the raw record, classifies it, and emits `ObservationCreated`.
2. Foundry pipelines normalize the observation into an `Event`, connect it to existing `Actor`, `Asset`, and `Mission` objects, and update relationship confidence with valid-time semantics.
3. Gotham surfaces the event inside an active investigation. Analysts see the entity graph, timeline, confidence rationale, and source lineage.
4. The AIP triage agent receives only policy-authorized context. It determines that the event is novel, mission-relevant, and above the triage threshold.
5. The enrichment and correlation agents retrieve related events, prior cases, entity relationships, geospatial context, and source reliability. Unsupported claims are removed by validators.
6. The recommendation agent drafts an action package: summary, evidence, uncertainty, alternatives, risks, and a proposed next step.
7. The policy agent scores the action as high risk. The system creates an approval request instead of executing anything.
8. A mission approver reviews the recommendation in the UI, inspects lineage, compares alternatives, and either approves, rejects, or edits the action package.
9. If approved, Apollo confirms the active workflow, tool, model, and policy versions are still valid. The backend executes through an idempotent action service and writes audit records.
10. If rejected or edited, the operator decision becomes feedback. Artemis adds a labeled eval example, runs offline comparisons against the active prompt/workflow, and may generate a candidate improvement.
11. The candidate improvement is not self-deployed. It is packaged with diffs, metrics, failure cases, policy decisions, and rollback plan for human review.
12. After approval, Apollo rolls the candidate to a canary mission scope. If precision, latency, operator trust, or guardrails degrade, Apollo rolls back automatically and preserves the failed-candidate evidence.

The platform gets better by learning which recommendations helped operators make faster, better-evidenced decisions, not by inventing new mission goals or bypassing authority. Its optimization target is bounded: improve precision, recall, latency, evidence quality, analyst workload, and mission impact while preserving policy, provenance, coalition boundaries, and human approval gates.
