# ClearGlassInc Artemis — Governed Intelligence Series Blueprint

> **Truth-in-architecture notice:** This is a target-state educational design for **ClearGlassInc Artemis**, not evidence of a provisioned Palantir environment, partnership, accreditation, operational deployment, or integration. Implementation depends on licensed platform access, approved data, coalition agreements, security review, and named operational authority.

This companion makes episodes LF05, LF09, LF14–LF16, LF18–LF19, LF21–LF22 technically credible without turning the channel into a claim of deployed capability.

## System Architecture

```text
[Analyst/Commander Web UI]
       │ OIDC + device/workload posture
[API/BFF + policy enforcement point] ─────────────── [Append-only audit plane]
       │ typed commands / read models                         │
[Mission workflow service] ── [Event bus] ── [Ingest/normalization]
       │                         │                    │
[AIP orchestration/model router]│              [Foundry pipelines]
       │ tool contracts          │                    │ lineage
[Gotham operational views] ─────┴──────────── [Foundry Ontology]
       │ investigations/cases              object/action types
       └──────── versioned release artifacts ──────── [Apollo]
                                      staged deploy, health gate, rollback
```

- **Gotham:** operational intelligence, investigations, entities, cases, and time-sensitive operator workflows.
- **Foundry:** governed integration, transforms, lineage, Ontology object/action types, and application logic.
- **AIP:** model-assisted copilots, constrained tools, evaluations, and workflow orchestration. Model output is untrusted.
- **Apollo:** controlled delivery across approved environments with versioning, policy, health checks, and rollback.

Planes stay distinct: data plane stores governed mission information; control plane versions workflows/models/policies; management plane deploys; audit plane independently records material transitions. The browser never becomes an authorization boundary.

## Data and Ontology

Core object types:

| Object | Required properties | Security behavior |
|---|---|---|
| `Observation` | source, observed_at, received_at, payload_digest, classification, confidence | immutable raw reference; correction appends |
| `Entity` | canonical_id, aliases, type, valid_time, confidence | entity-level and compartment policy |
| `Relationship` | subject, predicate, object, valid/transaction time, evidence IDs | access is intersection of supporting evidence policies |
| `Claim` | statement, evidence set, method, confidence, model/human provenance | no unsupported confidence; retract rather than overwrite |
| `Alert` | rule/model version, severity, status, mission context | acknowledged/closed only through typed action |
| `Case` | purpose, owner, members, compartment, retention | purpose-bound membership |
| `Recommendation` | options, assumptions, evidence, uncertainty, impact | proposal only; never equals authority |
| `Approval` | approver, scope, payload digest, expiry, decision, rationale | cannot approve own proposal where separation required |
| `ActionPackage` | exact target/scope, reversible plan, preconditions | execution blocked until valid approval |
| `Outcome` | action, observed result, attribution confidence | learning signal, not automatic reward truth |
| `EvalCase` | redacted input, expected properties, rubric, origin | privacy reviewed before reuse |
| `ArtifactVersion` | prompt/workflow/router/model/policy digest, parent, status | immutable versions; signed promotion |

Every record carries tenant/coalition, compartment, classification, releasability, source lineage, event time, transaction time, retention, legal/policy basis, and quality/confidence. Retrieval filters permissions **before** candidate generation. Derived objects inherit the most restrictive applicable policy unless an authorized release process creates a separately auditable derivative.

## AI and Agent Design

Copilots help analysts search, correlate, summarize with citations, draft intelligence products, and propose case actions. Commander views compress uncertainty, alternatives, and constraints but cannot manufacture authorization.

A multi-agent workflow is an orchestration pattern, not a society of independent authorities:

1. **Triage:** validate schema, deduplicate, classify, and route; no operational action.
2. **Enrichment:** use allowlisted sources with timeouts and provenance.
3. **Correlation:** propose entity/relationship candidates with confidence and conflicts.
4. **Synthesis:** draft a cited assessment and explicit unknowns.
5. **Recommendation:** enumerate options, assumptions, reversibility, and required authority.
6. **Policy:** deterministic service calculates allowed tools/data/actions.
7. **Approval:** accountable human signs exact digest/scope/expiry.
8. **Execution:** narrow service verifies approval again, acts idempotently, and appends audit events.

## Self-Improvement Loop

```text
operator correction + alert outcome + mission result + query telemetry
 → privacy/filtering + lineage
 → failure taxonomy
 → versioned eval case proposal
 → human-curated eval suite
 → sandbox candidate (prompt/workflow/router only)
 → offline quality/security/cost/latency gates
 → independent approval
 → canary on non-consequential traffic
 → monitored promotion or automatic rollback
 → immutable decision record
```

The optimizer may propose a candidate. It cannot alter objectives, permissions, tools, network destinations, policy, approval thresholds, deployment targets, or its own evaluator. Promotion requires a named owner. Feedback is weighted by provenance and task outcome, not copied blindly from operator clicks. Drift monitors input distribution, abstention, calibration, precision/recall, citation validity, latency, cost, overrides, and subgroup/coalition performance.

**Candidate gate:** no critical safety regression; no authorization-policy regression; citation and privacy tests pass; task metric improves by the predefined meaningful margin; latency/cost stay within budget; rollback artifact is present. A/B tests are confined to low-consequence advisory outputs and never split authorization or safety policy.

## Full-Stack Implementation

- **Frontend:** TypeScript/React mission workspace; typed API client; provenance drawer; temporal graph; uncertainty display; accessible keyboard workflows; approval page displays immutable payload digest.
- **Gateway/BFF:** short-lived OIDC tokens, audience binding, request size/schema validation, rate limits, correlation IDs, and policy obligations.
- **Python services:** FastAPI command/query APIs, Pydantic contracts, transactional outbox, idempotency keys, bounded workers, OpenTelemetry.
- **Streaming:** partition by tenant/mission; schema registry; dead-letter quarantine; replay protection; backpressure; event-time windows.
- **Storage/search:** governed lakehouse for history, Ontology for operational objects/actions, permission-aware full-text/vector retrieval; vector similarity never bypasses ACLs.
- **Inference:** approved model registry and router; data-class/region/task constraints; timeout, token/cost budgets, abstention, structured output validation.
- **Observability:** privacy-aware logs/traces/metrics; separate audit store; dashboards for service SLOs, evals, policy denials, drift, and operator overrides.
- **Deployment:** Apollo release rings, signed version bundle, config/policy separation, readiness and functional canaries, one-click/automatic rollback under approved rules.

## Security and Governance

Default deny. Authenticate user and workload; authorize tenant, mission, purpose, object/entity, property/column, action, and current context. Use short-lived audience-restricted identity, mTLS between services, restricted egress, secrets manager, encryption in transit/at rest, and compartment-specific keys where warranted. Record read access to high-sensitivity objects and every material proposal/approval/execution.

Threat controls include cross-coalition retrieval tests, indirect prompt-injection quarantine, tool parameter allowlists, output DLP, provenance validation, confused-deputy prevention, cache/index partitioning, approval replay rejection, dual control, immutable/tamper-evident audit export, backup restore exercises, and incident kill switches. Coalition release is an explicit action; it is never inferred from model output.

## Code Examples

### Typed, digest-bound state machine (Python)

```python
from dataclasses import dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json

class State(StrEnum):
    PROPOSED="proposed"; APPROVED="approved"; REJECTED="rejected"; EXECUTED="executed"

@dataclass(frozen=True)
class ActionPackage:
    action_id: str
    tenant: str
    action_type: str
    target_id: str
    parameters: dict[str, object]
    state: State = State.PROPOSED
    approval_digest: str | None = None

    def digest(self) -> str:
        canonical=json.dumps({"id":self.action_id,"tenant":self.tenant,
          "type":self.action_type,"target":self.target_id,"params":self.parameters},
          sort_keys=True,separators=(",",":"))
        return sha256(canonical.encode()).hexdigest()

def approve(pkg: ActionPackage, *, policy_allowed: bool) -> ActionPackage:
    if pkg.state is not State.PROPOSED or not policy_allowed:
        raise PermissionError("approval transition denied")
    return replace(pkg, state=State.APPROVED, approval_digest=pkg.digest())

def mark_executed(pkg: ActionPackage) -> ActionPackage:
    if pkg.state is not State.APPROVED or pkg.approval_digest != pkg.digest():
        raise PermissionError("valid digest-bound approval required")
    return replace(pkg, state=State.EXECUTED)
```

The executor additionally verifies approver identity/role, separation of duties, expiry, mission/tenant, idempotency key, and current policy adjacent to the action.

### Policy decision and ontology query (Python-style pseudocode)

```python
@dataclass(frozen=True)
class Decision:
    allowed: bool
    obligations: tuple[str, ...]
    policy_version: str

async def retrieve_claims(ctx, entity_ids: list[str]) -> list[dict]:
    decision = await policy.evaluate(
        subject=ctx.workload_and_user,
        action="claim.read",
        resources=entity_ids,
        purpose=ctx.mission_purpose,
        environment=ctx.device_and_network_posture,
    )
    if not decision.allowed:
        await audit.append("read.denied", ctx.correlation_id, decision.policy_version)
        raise PermissionError("denied")
    # Permission predicates are applied in the governed query, before ranking/vector search.
    return await ontology.query("Claim").where(
        entity_id__in=entity_ids,
        tenant=ctx.tenant,
        compartment__in=ctx.compartments,
        valid_at=ctx.as_of,
    ).select("statement", "evidence_ids", "confidence", "valid_time").execute()
```

### Constrained AIP tool adapter

```python
class OpenCaseInput(BaseModel):
    mission_id: UUID
    title: str = Field(min_length=5, max_length=120)
    evidence_ids: list[UUID] = Field(min_length=1, max_length=50)

async def prepare_case_draft(raw: dict, ctx: Context) -> dict:
    args = OpenCaseInput.model_validate(raw)  # model output is untrusted
    decision = await policy.evaluate(ctx, "case.draft", args.model_dump())
    if not decision.allowed:
        raise ToolDenied(decision.policy_version)
    # Draft only. A separate human-approved action creates the operational case.
    draft = await cases.create_draft(args, actor=ctx.actor, policy=decision.policy_version)
    await audit.append("case.draft.created", draft.digest, ctx.actor)
    return {"draft_id": str(draft.id), "status": "awaiting_human_approval"}
```

### Evaluation and promotion gate

```python
@dataclass(frozen=True)
class EvalResult:
    citation_precision: float
    task_recall: float
    unsafe_tool_calls: int
    cross_compartment_leaks: int
    p95_latency_ms: int
    cost_per_case: float


def promotable(base: EvalResult, candidate: EvalResult) -> bool:
    return all((
        candidate.unsafe_tool_calls == 0,
        candidate.cross_compartment_leaks == 0,
        candidate.citation_precision >= base.citation_precision,
        candidate.task_recall >= base.task_recall + 0.02,
        candidate.p95_latency_ms <= 2_000,
        candidate.cost_per_case <= 1.10 * base.cost_per_case,
    ))
```

Passing this function creates a **promotion proposal**, not a deployment. Human review, signed artifact identity, canary plan, and rollback reference remain mandatory.

## Scenario Walkthrough

A coalition-approved sensor feed emits a signed observation about a fictional logistics anomaly. Ingest validates schema/signature, assigns event and transaction time, hashes the payload, tags coalition/compartment policy, and writes a transactional outbox event. A triage worker deduplicates it, then Foundry transforms and Ontology actions create an `Observation` and candidate relationship with complete lineage.

Gotham presents the alert only to operators whose mission purpose and compartments intersect. AIP orchestration retrieves authorized history, treats retrieved text as untrusted, and asks correlation/synthesis steps for a cited assessment. One source conflicts, so the system displays the conflict and lowers confidence rather than hiding it. The recommendation agent drafts two response options and an abstention option. It cannot execute any of them.

The policy service denies one tool because the requested destination is outside the coalition allowlist. The remaining `ActionPackage` shows target, scope, assumptions, evidence, payload digest, expiry, rollback, and expected effect. The operator corrects an entity match, rejects the broad option, narrows the target, and approves the exact revised digest. The executor rechecks identity, policy, separation, expiry, and digest, executes idempotently through an allowlisted adapter, and appends outcome/audit events.

Later, the measured outcome and correction become a privacy-reviewed candidate eval case. Failure analysis identifies an alias-resolution weakness. AIP proposes a routing/heuristic candidate in a sandbox. It cannot change permission policy. Offline tests show higher recall but one cross-compartment leak, so the deterministic gate rejects it. Engineers fix pre-retrieval partitioning; the next candidate passes. A named reviewer approves a 5% advisory-only canary. Drift and leak monitors remain clean, the owner promotes the signed bundle through Apollo, and rollback stays pinned. The audit chain links observation → model/workflow versions → recommendation → correction → approval → action → outcome → eval → candidate → review → deployment. That is “getting better” without self-granted authority.
