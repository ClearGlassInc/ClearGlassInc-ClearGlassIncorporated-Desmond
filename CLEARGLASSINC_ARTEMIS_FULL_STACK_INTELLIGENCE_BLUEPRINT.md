# ClearGlassInc Artemis — Self-Evolving AI Intelligence Platform Blueprint

## Executive Build Directive

ClearGlassInc Artemis is a mission-critical, coalition-aware intelligence platform built on Palantir Gotham, Foundry, AIP, and Apollo. It fuses live and historical data, reasons over an ontology-backed operational picture, captures operator feedback, and proposes safe self-upgrades to prompts, workflows, heuristics, and model routing under explicit human-approved guardrails.

The design assumes secure Canadian enterprise and public-sector operations, including environmental cyber-risk domains such as ionospheric physics, space weather, GNSS degradation, HF radio disruption, satellite interference, and communication-infrastructure resilience.

> **Implementation status:** This document is a target-state architecture and implementation blueprint, not evidence that Palantir infrastructure, integrations, data feeds, or operational authority have been provisioned. Product-specific interfaces shown below are integration contracts that must be mapped to the licensed deployment's supported Gotham, Foundry, AIP, and Apollo APIs during implementation.

### Delivery Coverage and System Boundary

This blueprint is the complete engineering handoff for the requested ClearGlassInc Artemis design. It deliberately separates implementable contracts from claims about deployed infrastructure and maps every requested outcome to a verifiable section:

| Requested outcome | Authoritative section | Completion evidence |
|---|---|---|
| End-to-end platform architecture | [System Architecture](#system-architecture) | Trust boundaries, layer ownership, data flow, failure behavior, and Palantir responsibility map. |
| Ontology and data model | [Data and Ontology](#data-and-ontology) | Entities, links, bitemporal state, confidence, lineage, mission context, and access markings. |
| Copilots and governed agents | [AI and Agent Design](#ai-and-agent-design) | Analyst and commander copilots, bounded multi-agent graph, typed tools, and approval gates. |
| Safe self-improvement | [Self-Improvement Loop](#self-improvement-loop) | Feedback capture, evaluation, candidate generation, review, canary, drift detection, rollback, and audit. |
| Full-stack implementation | [Full-Stack Implementation](#full-stack-implementation) | Web surfaces, APIs, Python services, streams, retrieval, model routing, and operational dashboards. |
| Security and governance | [Security and Governance](#security-and-governance) | Need-to-know enforcement, compartments, coalition boundaries, zero trust, provenance, and policy-as-code. |
| Production code patterns | [Code Examples](#code-examples) | Python-first contracts for ingestion, policy, ontology queries, tools, workflows, routing, and evaluations. |
| Mission walkthrough | [Scenario Walkthrough](#scenario-walkthrough) | Live event-to-outcome trace including operator authority and the subsequent learning signal. |
| Delivery and operations | [Build Phases](#build-phases) and [Patch, Fix, and Deploy Control Plane](#patch-fix-and-deploy-control-plane) | Milestones, release gates, Apollo rollout, rollback, monitoring, and operational ownership requirements. |

**System boundary:** ClearGlassInc Artemis may automate collection, normalization, read-only analysis, drafting, simulation, evaluation, and release proposals. It may not autonomously change objectives, grant privileges, alter policy, approve its own upgrades, promote a release, or execute an operationally significant action. Those transitions require deterministic policy checks and attributable human authorization. Until licensed Palantir interfaces, identity federation, protected environments, data agreements, approvers, and rollback owners are verified, every external integration remains disabled or in a synthetic, read-only pilot.

### Integration Evidence Gate

Architecture intent is not connection proof. The release owner must copy this matrix into the
release evidence package and replace `BLOCKED` only with a result backed by a timestamped,
redacted response, trace identifier, and accountable verifier. Secret values must never be copied
into the evidence package.

| Service | Purpose | Required configuration (names only) | Safest verification | Initial status |
|---|---|---|---|---|
| Gotham | Investigations, cases, entity tracking | Gotham tenant, mission scopes, workload identity | Read one allowlisted synthetic case and prove a cross-compartment denial | **BLOCKED — tenant and identity not evidenced** |
| Foundry | Data products, lineage, Ontology objects/actions | Foundry stack, project/RID allowlist, workload identity | Read a synthetic object with lineage; attempt a denied object action | **BLOCKED — stack and RIDs not evidenced** |
| AIP | Copilots, agents, model routing, evaluations | AIP entitlement, model allowlist, prompt/eval project | Execute a non-mutating synthetic eval and retain its trace | **BLOCKED — entitlement and project not evidenced** |
| Apollo | Signed rollout, runtime policy, rollback | Apollo environment, signing trust root, protected rings | Verify a signed no-op artifact in a non-production ring, then roll it back | **BLOCKED — environment and trust root not evidenced** |
| Identity provider | Human and workload authentication | OIDC issuer/audience, JWKS, group-to-attribute mapping | Validate a short-lived token and reject wrong audience/expired tokens | **BLOCKED — federation not evidenced** |
| Event transport | Bounded live-data delivery | Broker endpoints, topic ACLs, schema registry, DLQ | Publish a synthetic event and prove replay, dedupe, and DLQ handling | **BLOCKED — broker configuration not evidenced** |
| Audit store | Tamper-evident provenance | Append identity, retention policy, integrity key reference | Append a synthetic trace, verify its chain, and prove mutation is denied | **BLOCKED — immutable store not evidenced** |

The verifier records `PASS`, `FAIL`, `BLOCKED`, `NOT APPLICABLE`, or `NOT TESTED`; free-form
labels such as “connected” or “ready” are prohibited. A `PASS` expires when the verified identity,
endpoint, policy bundle, schema, model, prompt, workflow, or deployed artifact changes.
Operational promotion remains fail-closed while any mission-critical dependency is `BLOCKED`, `FAIL`, or
`NOT TESTED`.

### Architecture Decision and Acceptance Contract

The primary design is a **governed proposal system**, not an autonomously self-modifying system. Models may analyze, draft, rank, and propose changes; deterministic services enforce identity, authorization, workflow transitions, release eligibility, and audit invariants. No model output can grant authority, expand mission scope, modify policy, promote itself, or cause an operationally significant external effect.

The first production release is acceptable only when all of the following are demonstrated with replayable evidence:

1. Every read is filtered by tenant, mission, purpose, classification, compartments, coalition releasability, and object/property policy before context reaches a model.
2. Every tool call uses a typed allowlisted contract, a short-lived workload identity, bounded time and resource budgets, and a server-side policy decision adjacent to the protected action.
3. Operationally significant actions stop in `PENDING_HUMAN_APPROVAL`; approval is attributable, scoped to the exact immutable action payload, time bounded, and non-replayable.
4. Prompt, workflow, heuristic, and routing candidates cannot reach a canary without regression evaluations, security review, a named human approval, a stable rollback version, and a signed release manifest.
5. Audit records bind input lineage, policy bundle, prompt/workflow/model versions, tool calls, approval decisions, outputs, and deployment identity in a tamper-evident chain.
6. Failure of identity, policy, lineage, audit, model routing, or approval dependencies fails closed for mutations and degrades read paths to an explicitly labeled, non-actionable state.
7. Ring 0 replay and Ring 1 read-only canary meet the approved precision, recall, citation, latency, policy-violation, trust, and rollback thresholds before wider release.

**Initial service objectives (to be validated by load and recovery testing):** authorized interactive reads target p95 under 750 ms excluding long-running model work; streaming normalization targets p95 under 2 seconds; policy decisions target p99 under 50 ms; critical audit events target durable acknowledgement before action completion; the control plane targets an RTO of 30 minutes and RPO of 5 minutes. These are proposed engineering budgets, not measured production claims.

**Non-goals:** autonomous goal creation, autonomous privilege acquisition, unsupervised operational action, cross-coalition inference, training foundation models on mission data, or treating model confidence as evidence confidence.

## System Architecture

### Palantir Platform Responsibilities

- **Gotham**: operational intelligence, investigations, entity tracking, graph exploration, case management, and mission command workflows.
- **Foundry**: data integration, pipelines, ontology objects, object actions, application logic, lineage, operational analytics, and governed data products.
- **AIP**: copilots, tool-using agents, workflow automation, prompt governance, evaluations, model routing, and human-in-the-loop AI operations.
- **Apollo**: deployment orchestration, signed releases, canary rings, policy bundle delivery, runtime controls, kill switches, rollback, and continuous compliance.

```mermaid
flowchart TB
  subgraph UI[Frontend]
    analyst[Analyst Workbench]
    commander[Commander Console]
    env[Environmental Threat Dashboard]
    gov[Governance Studio]
  end

  subgraph API[API and Backend]
    gateway[API Gateway]
    auth[AuthN/AuthZ]
    policy[Policy Enforcement Point]
    caseSvc[Case Service]
    workflowSvc[Workflow Orchestrator]
    feedbackSvc[Feedback Service]
    actionSvc[Action Package Service]
  end

  subgraph STREAM[Streaming and Events]
    bus[Kafka/Pulsar Event Bus]
    raw[intel.raw]
    norm[intel.normalized]
    alerts[intel.alerts]
    feedback[operator.feedback]
    releases[release.telemetry]
  end

  subgraph FOUNDRY[Foundry Data and Ontology]
    bronze[Bronze Raw Data Products]
    silver[Silver Normalized Data Products]
    gold[Gold Mission Data Products]
    ontology[Ontology Objects, Links, Actions]
    transforms[Pipeline Builder / Code Repos]
  end

  subgraph GOTHAM[Gotham Operations]
    graph[Entity Graph]
    timeline[Timeline and Map]
    cases[Investigations and Cases]
    missions[Missions and Watchlists]
  end

  subgraph AIP[AIP Orchestration]
    copilots[Copilots]
    agents[Multi-Agent Runtime]
    tools[Policy-Gated Tools]
    router[Model Router]
    evals[Evaluation Harness]
    promptOps[Prompt and Workflow Registry]
  end

  subgraph OBS[Observability and Governance]
    otel[OpenTelemetry]
    audit[Immutable Audit Ledger]
    metrics[Mission Metrics]
    drift[Drift Detection]
    trust[Operator Trust Analytics]
  end

  subgraph APOLLO[Apollo Deployment]
    rings[Ring 0/1/2 Rollout]
    signed[Signed Bundles]
    rollback[Rollback and Kill Switch]
    runtime[Runtime Control Plane]
  end

  UI --> gateway --> auth --> policy
  policy --> caseSvc --> cases
  policy --> workflowSvc --> agents
  workflowSvc --> actionSvc
  feedbackSvc --> feedback
  gateway --> bus
  bus --> raw --> bronze --> transforms --> silver --> gold --> ontology
  ontology --> graph
  ontology --> timeline
  ontology --> tools
  tools --> router
  agents --> tools
  agents --> evals
  evals --> promptOps --> signed --> rings --> runtime
  runtime --> rollback
  gateway --> otel --> audit
  evals --> metrics --> drift --> rollback
```

### Layered Production Blueprint

| Layer | Implementation blueprint |
|---|---|
| Frontend | TypeScript/React mission UI with graph, timeline, map, alert queue, evidence viewer, approval inbox, self-upgrade review board, and environmental threat dashboard. |
| API gateway | mTLS, JWT validation, request signing, rate limits, tenant/mission context injection, audit correlation IDs, and schema validation. |
| Backend services | Python FastAPI services for intake, cases, ontology queries, AIP tool execution, action packages, feedback, evaluations, release proposals, and governance review. |
| Event bus | Kafka or Pulsar topics for raw events, normalized observations, ontology updates, alerts, feedback, eval jobs, release telemetry, and audit envelopes. |
| Data layer | Foundry bronze/silver/gold data products with schema contracts, quality gates, lineage, dedupe, temporal modeling, and feature materializations. |
| Ontology layer | Foundry ontology object types, link types, actions, permissions, confidence scores, provenance fields, temporal state, and mission context. |
| AI layer | AIP copilots, deterministic workflow graphs, tool-using agents, model router, retrieval policies, eval harnesses, prompt registry, and workflow registry. |
| Policy layer | OPA/Rego policy bundles plus Foundry/Gotham permissions for need-to-know, row, column, entity, edge, action, model, prompt, and coalition controls. |
| Observability | OpenTelemetry traces, metrics, structured logs, immutable audit ledger, model telemetry, prompt telemetry, eval dashboards, SLO alerts, and replayable incidents. |
| Deployment | Apollo promotion rings, signed artifacts, deployment attestations, runtime config, canaries, rollback, break-glass controls, and environment-specific policy packs. |

### Trust Boundaries and Fail-Closed Behavior

ClearGlassInc Artemis separates the user, data, inference, action, deployment, and audit planes so a compromise or outage in one plane cannot silently manufacture authority in another. Identity and policy decisions are deterministic service decisions; AIP model output is always untrusted content carried inside a typed envelope.

| Boundary | Untrusted input | Preventive control | Degraded or recovery behavior |
|---|---|---|---|
| User to API | Browser state, tokens, uploaded evidence, query text. | mTLS or device-bound session, short-lived identity, strict schemas, size limits, purpose-of-use, and CSRF protection. | Reject mutations; preserve an attributable denial event without persisting rejected sensitive payloads. |
| Source to Foundry | Streaming events, partner feeds, files, source markings. | Quarantine, schema registry, malware scanning, canonicalization, deduplication, source signature, and classification validation. | Route invalid records to a restricted dead-letter data product; never create ontology facts from them. |
| Ontology to retrieval | Objects, links, embeddings, inferred relationships. | Mission, tenant, classification, compartment, property, edge, temporal, and releasability filters before ranking or prompt construction. | Return a labeled partial result or deny; never substitute cross-boundary context. |
| AIP to tool broker | Prompt text, model-selected arguments, retrieved instructions. | Typed allowlist, server-side authorization, idempotency key, timeout, bounded retry, egress policy, and action risk classification. | Cancel on timeout; retry only read-only/idempotent calls; quarantine ambiguous outcomes for operator reconciliation. |
| Tool broker to action plane | Draft action packages and approval claims. | Immutable payload digest, dual control where required, approval expiry, nonce consumption, and adjacent policy recheck. | Unknown, changed, expired, or replayed approval fails closed in `PENDING_HUMAN_APPROVAL`. |
| Release service to Apollo | Candidate prompts, workflows, routes, policies, containers. | Signed manifest, provenance attestation, eval evidence, named approvers, compatibility checks, and rollback pointer. | Keep the champion active; recall the canary or invoke the kill switch when integrity or SLO evidence fails. |
| Runtime to audit plane | Tool, decision, approval, and deployment events. | Durable append acknowledgement, hash chaining, independent access control, retention policy, and clock correlation. | Consequential actions do not complete without durable audit acknowledgement; buffer read-only telemetry within a bounded queue. |

**Ambiguous-outcome invariant:** a timed-out mutation is never blindly retried. The orchestrator queries the idempotency record and target state; if completion cannot be proven, it opens a reconciliation task and prevents dependent actions. **Emergency access invariant:** break-glass access is time-bound, reason-coded, independently alerted, never changes coalition releasability, and receives mandatory after-action review.

## Data and Ontology

The ontology is the operational contract shared by humans, backend services, agents, and governance controls. It makes every recommendation explainable because each object, relationship, and action carries confidence, lineage, temporal validity, mission context, and permissions.

### Core Entity Types

| Entity | Purpose | Key attributes |
|---|---|---|
| `Person` | Analysts, commanders, operators, subjects, contacts. | clearance, organization, roles, mission assignments. |
| `Organization` | Enterprises, agencies, coalition partners, vendors, threat groups. | sector, jurisdiction, releasability, risk tier. |
| `Facility` | Data centers, offices, towers, ground stations, warehouses. | geohash, criticality, owner, backup systems. |
| `Asset` | Servers, endpoints, radios, GNSS receivers, satellites, routers. | asset class, owner, mission criticality, dependencies. |
| `NetworkSignal` | Netflow, DNS, endpoint, telemetry, latency, packet loss. | source, destination, protocol, timing, confidence. |
| `EnvironmentalSignal` | Space weather, ionospheric telemetry, solar bursts, D-region changes. | log_NF2, Kp, TEC, absorption, station, model version. |
| `Observation` | Atomic normalized fact from a source or model. | source reliability, observed time, value, uncertainty. |
| `Indicator` | IOC, anomaly, vulnerability, or environmental threshold breach. | indicator type, severity, first seen, last seen. |
| `Event` | Correlated operational occurrence. | event type, severity, affected entities, temporal window. |
| `Case` | Investigation container. | status, assignee, mission, evidence set, decision log. |
| `Mission` | Operational context and objective. | purpose, scope, data boundaries, approvers, SLOs. |
| `ActionPackage` | Proposed operational response. | COA, risk, required approvals, rollback, status. |
| `AIArtifact` | Prompt output, summary, recommendation, eval candidate. | model, prompt version, workflow version, citations. |
| `ChangeProposal` | Self-upgrade candidate. | diff, metrics, blast radius, reviewers, rollback plan. |

### Relationship Types

```sql
create type relationship_type as enum (
  'OBSERVED_AT',
  'AFFECTS',
  'DEPENDS_ON',
  'LOCATED_AT',
  'OWNED_BY',
  'PART_OF_MISSION',
  'CORRELATED_WITH',
  'DERIVED_FROM',
  'CONTRADICTS',
  'SUPPORTS',
  'REQUIRES_APPROVAL_FROM',
  'PROPOSED_BY_AGENT',
  'APPROVED_BY_OPERATOR',
  'DEPLOYED_BY_APOLLO'
);
```

### Ontology Schema Skeleton

```sql
create table artemis_object (
  object_id uuid primary key,
  object_type text not null,
  display_name text not null,
  attributes jsonb not null default '{}',
  confidence numeric(5,4) not null check (confidence between 0 and 1),
  classification text not null check (classification in ('U','CUI','SECRET','TS')),
  releasability text[] not null default '{}',
  compartments text[] not null default '{}',
  mission_ids uuid[] not null default '{}',
  lineage jsonb not null,
  provenance_hash text not null,
  source_reliability numeric(5,4) not null default 0.5,
  valid_from timestamptz not null,
  valid_to timestamptz,
  system_from timestamptz not null default now(),
  system_to timestamptz,
  created_by text not null,
  updated_by text not null
);

create table artemis_link (
  link_id uuid primary key,
  src_object_id uuid not null references artemis_object(object_id),
  dst_object_id uuid not null references artemis_object(object_id),
  relationship relationship_type not null,
  attributes jsonb not null default '{}',
  confidence numeric(5,4) not null check (confidence between 0 and 1),
  evidence_refs text[] not null,
  classification text not null,
  releasability text[] not null default '{}',
  compartments text[] not null default '{}',
  mission_ids uuid[] not null default '{}',
  valid_from timestamptz not null,
  valid_to timestamptz,
  system_from timestamptz not null default now(),
  system_to timestamptz
);
```

### Environmental Cyber-Risk Extension

```sql
create table environmental_signal (
  signal_id uuid primary key,
  station_id text not null,
  source_system text not null,
  observed_at timestamptz not null,
  log_nf2 numeric(4,2),
  total_electron_content numeric(8,3),
  solar_radio_flux numeric(8,3),
  kp_index numeric(4,2),
  d_region_absorption_db numeric(8,3),
  affected_capabilities text[] not null,
  confidence numeric(5,4) not null,
  model_version text not null,
  lineage jsonb not null
);

create view environmental_threat_level as
select
  signal_id,
  observed_at,
  case
    when log_nf2 < 5.4 then 'GREEN'
    when log_nf2 between 5.4 and 5.8 then 'YELLOW'
    else 'RED'
  end as threat_level,
  array_remove(array[
    case when total_electron_content > 80 then 'GNSS_PHASE_DISTORTION' end,
    case when d_region_absorption_db > 8 then 'HF_ABSORPTION' end,
    case when solar_radio_flux > 200 then 'SATELLITE_INTERFERENCE' end
  ], null) as likely_impacts
from environmental_signal;
```

This extension lets ClearGlassInc Artemis correlate space-weather conditions with corporate network latency, GNSS accuracy degradation, satellite data quality, logistics disruption, and communication failover risk.

## AI and Agent Design

### Copilots

1. **Analyst Copilot**: retrieves ontology objects, resolves entities, builds timelines, drafts briefs, identifies evidence gaps, and asks for operator validation when confidence is low.
2. **Commander Copilot**: compares courses of action, estimates mission impact, prepares action packages, and highlights required approvals.
3. **Environmental Cyber-Risk Copilot**: correlates ionospheric telemetry, GNSS anomalies, HF degradation, and infrastructure dependencies.
4. **Governance Copilot**: reviews prompt diffs, workflow diffs, eval results, model cards, policy denials, and release proposals.
5. **Apollo Operations Copilot**: summarizes canary status, SLO drift, rollback readiness, and runtime policy health.

### Multi-Agent Workflow Graph

```yaml
workflow_id: artemis-machine-speed-intel-v1
mission_modes:
  - cyber_defense
  - infrastructure_resilience
  - environmental_cyber_risk
agents:
  triage_agent:
    inputs: [normalized_event, mission_context]
    outputs: [severity, relevant_entities, recommended_next_agents]
  enrichment_agent:
    tools: [ontology_query, hybrid_search, source_reputation]
    outputs: [evidence_bundle]
  correlation_agent:
    tools: [graph_neighbors, temporal_join, geospatial_join]
    outputs: [correlated_event_graph]
  environmental_agent:
    tools: [space_weather_query, gnss_quality_query, dependency_graph]
    outputs: [environmental_risk_assessment]
  summarization_agent:
    tools: [citation_builder, uncertainty_calibrator]
    outputs: [analyst_brief]
  recommendation_agent:
    tools: [coa_generator, risk_model, rollback_planner]
    outputs: [action_package_draft]
  approval_gate_agent:
    tools: [policy_check, dual_control_check, audit_write]
    outputs: [approved_or_blocked_action]
  learning_agent:
    tools: [feedback_to_eval, candidate_generator, regression_eval]
    outputs: [change_proposal]
hard_controls:
  autonomous_external_actions: false
  operational_action_requires_human_approval: true
  prompt_release_requires_governance_approval: true
  cross_compartment_disclosure: false
  model_route_must_match_classification: true
```

### Operationally Significant Action Gates

Any action that can affect availability, confidentiality, integrity, safety, contracts, reputation, or coalition disclosure requires explicit approval. Examples include isolating a network segment, changing firewall policy, notifying a third party, sharing an intelligence product outside a compartment, re-tasking a sensor, promoting a new prompt to production, or changing a model route for classified workflows.

Approval is a capability, not a boolean field. The policy service hashes the canonical action package (action type, mission, risk, rationale, evidence, and parameters) and issues a five-minute token bound to that hash, action identifier, and approving operator. The executor atomically consumes the token once; expired, replayed, cross-action, or post-approval-mutated packages fail closed and append a denial to the audit chain. Production storage must enforce single-use consumption transactionally so horizontally scaled executors cannot race the same approval.

## Self-Improvement Loop

ClearGlassInc Artemis improves itself by creating proposed changes, never by silently changing goals or production behavior. The loop is intentionally conservative: observe, evaluate, propose, review, canary, monitor, promote, or roll back.

### Signal Capture

Signals are collected from:

- Operator accepts, rejects, edits, comments, and confidence overrides.
- Query logs, retrieval misses, abandoned workflows, and manual workaround patterns.
- Alert outcomes: true positive, false positive, false negative, duplicate, late, stale, or unsafe.
- Mission results: time-to-triage, time-to-decision, operational disruption, escalation quality, and after-action reviews.
- Model telemetry: prompt version, model route, tool path, latency, token cost, refusal behavior, citation accuracy, and policy denials.
- Environmental outcomes: GNSS accuracy loss, HF outage, latency spike, satellite interference, and logistics disruption windows.

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class FeedbackSignal(str, Enum):
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    EDITED = 'edited'
    FALSE_POSITIVE = 'false_positive'
    FALSE_NEGATIVE = 'false_negative'
    DUPLICATE = 'duplicate'
    LATE = 'late'
    UNSAFE = 'unsafe'
    HIGH_VALUE = 'high_value'

class FeedbackEvent(BaseModel):
    event_id: str
    mission_id: str
    actor_id: str
    artifact_id: str
    artifact_type: str
    signal: FeedbackSignal
    correction_text: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    outcome_score: float | None = Field(default=None, ge=0, le=1)
    prompt_version: str
    workflow_version: str
    model_route: str
    tool_trace_id: str
    latency_ms: int
    observed_at: datetime
    classification: str
    compartments: list[str]
```

### Upgrade Lifecycle

```mermaid
sequenceDiagram
  participant Operator
  participant FeedbackSvc
  participant EvalBuilder
  participant CandidateGen
  participant Governance
  participant Apollo
  participant Runtime

  Operator->>FeedbackSvc: edit/reject/approve artifact
  FeedbackSvc->>EvalBuilder: emit operator.feedback
  EvalBuilder->>EvalBuilder: build stratified eval examples
  EvalBuilder->>CandidateGen: failing clusters + metrics
  CandidateGen->>CandidateGen: propose prompt/workflow/routing diffs
  CandidateGen->>Governance: ChangeProposal + eval report
  Governance->>Governance: human review + approval
  Governance->>Apollo: signed release request
  Apollo->>Runtime: canary Ring 0
  Runtime->>Apollo: SLO/eval telemetry
  Apollo->>Runtime: promote or rollback
```

### Release Gate

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class EvalScore:
    candidate_id: str
    precision: float
    recall: float
    citation_accuracy: float
    leakage_violations: int
    unsafe_action_violations: int
    p95_latency_ms: int
    operator_trust_delta: float
    cost_delta_pct: float


def release_gate(champion: EvalScore, challenger: EvalScore) -> bool:
    return all([
        challenger.leakage_violations == 0,
        challenger.unsafe_action_violations == 0,
        challenger.precision >= champion.precision + 0.015,
        challenger.recall >= champion.recall - 0.005,
        challenger.citation_accuracy >= 0.97,
        challenger.p95_latency_ms <= 1200,
        challenger.operator_trust_delta >= 0,
        challenger.cost_delta_pct <= 20.0,
    ])
```

### Shadow, A/B, and Canary Experiment Design

An approved candidate is first evaluated in **shadow mode** against replayable, policy-filtered
traffic. Shadow output is stored in the evaluation plane and is never shown to an operator, written
to the ontology, or passed to an action tool. Only candidates with zero authorization, disclosure,
and unsafe-action violations may enter an online experiment. Prompt and workflow experiments use a
stable mission-level assignment so one mission never receives inconsistent behavior during an
investigation. Classified missions, active incidents, break-glass sessions, and consequential action
workflows remain on the champion unless the mission authority explicitly approves their inclusion.

The experiment service records the champion and challenger artifact digests, policy version,
assignment reason, eligible population, exposure, outcome window, and predefined stopping rule.
ModelOps may stop an experiment early for harm, leakage, latency, or reliability; it may not declare
success early from a favorable sample. Promotion requires the full evaluation window, minimum sample
size, confidence interval, segmented results, security review, and named mission-owner approval.

```python
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Literal


@dataclass(frozen=True)
class ExperimentContext:
    mission_id: str
    experiment_id: str
    classification: str
    active_incident: bool
    break_glass: bool
    consequential_action: bool
    mission_authority_opt_in: bool


@dataclass(frozen=True)
class ExperimentAssignment:
    arm: Literal["champion", "challenger"]
    reason: str
    bucket: int | None


def assign_experiment(context: ExperimentContext, challenger_basis_points: int) -> ExperimentAssignment:
    """Assign one mission deterministically; this function grants no execution authority."""
    if not 0 <= challenger_basis_points <= 10_000:
        raise ValueError("challenger_basis_points must be between 0 and 10_000")

    protected = (
        context.classification in {"TOP_SECRET", "SPECIAL_ACCESS"}
        or context.active_incident
        or context.break_glass
        or context.consequential_action
    )
    if protected and not context.mission_authority_opt_in:
        return ExperimentAssignment("champion", "protected mission context", None)

    assignment_key = f"{context.experiment_id}:{context.mission_id}".encode("utf-8")
    bucket = int.from_bytes(sha256(assignment_key).digest()[:8], "big") % 10_000
    arm: Literal["champion", "challenger"] = (
        "challenger" if bucket < challenger_basis_points else "champion"
    )
    return ExperimentAssignment(arm, "stable mission-level assignment", bucket)
```

Online scorecards are segmented by mission, coalition, language, data freshness, severity, and
operator role to prevent aggregate gains from concealing harm to a smaller group. The hard stop
conditions are any cross-boundary disclosure, unauthorized tool attempt, audit gap, statistically
credible precision or trust regression, or latency/error-budget breach. Stopping restores the
champion pointer through Apollo; it does not delete exposure, decision, or outcome records.

## Full-Stack Implementation

### Repository Layout

```text
artemis/
  frontend/
    src/app/
    src/components/graph/
    src/components/approvals/
    src/components/environmental-risk/
  services/
    api_gateway/
    intake_service/
    ontology_service/
    agent_service/
    feedback_service/
    eval_service/
    release_service/
  pipelines/
    foundry_transforms/
    quality_rules/
    feature_materializations/
  policy/
    rego/
    tests/
  agents/
    prompts/
    workflows/
    tools/
    evals/
  deploy/
    apollo/
    helm/
    runtime_config/
```

### API Surface

```http
POST /v1/intel/intake
POST /v1/environmental/signals
POST /v1/ontology/query
POST /v1/agents/run
POST /v1/cases
POST /v1/action-packages
POST /v1/action-packages/{id}/approve
POST /v1/action-packages/{id}/reject
POST /v1/feedback
GET  /v1/evals/releases
POST /v1/releases/{id}/approve
POST /v1/releases/{id}/rollback
POST /v1/legal/preflight
POST /v1/legal/work-products
GET  /v1/legal/matters/{matter_id}
GET  /v1/audit/{correlation_id}
```

### Frontend Panels

- **Alert Queue**: ranked alerts with severity, confidence, mission impact, and policy visibility.
- **Entity Graph**: Gotham-style graph of entities, links, confidence, evidence, and temporal state.
- **Timeline/Map**: time and geospatial correlation for cyber and environmental events.
- **Action Inbox**: approval packages with evidence, COAs, risk, rollback, and dual-control status.
- **Self-Upgrade Board**: prompt/workflow diffs, eval deltas, canary status, reviewer comments, and Apollo promotion state.
- **Legal Intelligence Console**: legal preflight decisions, authority packets, matter files, risk classifications, counsel-review queues, and immutable audit trails.
- **Environmental Threat Dashboard**: log NF2, TEC, solar flux, D-region absorption, GNSS quality, impacted facilities, and recommended mitigation.

## Security and Governance

### Access Model

ClearGlassInc Artemis uses a combined RBAC, ABAC, and ReBAC model:

- **RBAC**: analyst, commander, governance reviewer, system operator, auditor.
- **ABAC**: clearance, mission, purpose, compartment, nationality, organization, device posture, network zone, time, and emergency state.
- **ReBAC**: user-to-mission, user-to-case, asset-to-organization, report-to-coalition, and approver-to-action relationships.

### Policy Guarantees

- Need-to-know is enforced before records are returned, before prompts are constructed, and before model inference.
- Row, column, entity, relationship, and action-level controls are checked independently.
- Coalition boundaries are represented as releasability caveats on objects, links, reports, prompts, and outputs.
- Zero-trust tool execution uses workload identity, mTLS, signed requests, sandboxing, egress allowlists, and short-lived credentials.
- Immutable logs record every data read, prompt, model route, tool call, evidence citation, approval, denial, release, and rollback.
- Model governance requires model cards, eval scorecards, approved use cases, known limitations, red-team results, and retirement plans.
- Prompt governance requires versioned diffs, eval evidence, reviewers, signed approval, Apollo canary, and rollback plan.


## Supreme Legal Intelligence Division

### Legal Operating Mandate

ClearGlassInc Artemis includes a **Supreme Legal Intelligence Division**: a policy-gated legal-analysis, compliance, investigation, drafting, privacy, intellectual-property, employment, litigation-risk, and corporate-governance layer that constrains technical execution before any autonomous action can affect contracts, regulated records, user data, evidence, deployments, storefronts, agent workflows, or external communications.

The division is **legal information and analytical support only**. It does not claim to be licensed counsel and must route jurisdiction-specific, high-risk, privileged, contested, or operationally significant legal conclusions to appropriately licensed human counsel before execution.

### Legal Prime Directive

For every legal or legally sensitive request, Artemis must produce jurisdiction-specific, citation-supported, operationally useful analysis and must never replace controlling authority with intuition, convenience, unsupported business preference, or speculative reasoning. The legal layer must:

- Identify jurisdiction, governing law, forum, venue, regulator, tribunal, or court where relevant.
- Determine procedural posture, parties, legal roles, contractual obligations, statutory duties, regulatory duties, deadlines, limitation periods, burdens, remedies, and enforcement realities.
- Separate confirmed facts from assumptions and unresolved factual gaps.
- Prefer primary authority and controlling contracts over summaries or general reasoning.
- Classify legal, operational, financial, evidentiary, privacy, privilege, governance, and reputational risk.
- Preserve privilege, confidentiality, evidence integrity, chain of custody, document-retention obligations, and litigation holds.
- Prevent unsupported legal conclusions from entering automated system decisions.

### Authority Hierarchy

Artemis applies legal authority in this order and must not elevate weaker sources above stronger sources:

1. Controlling constitutional, statutory, regulatory, and contractual authority.
2. Binding judicial decisions.
3. Binding procedural and evidentiary rules.
4. Official court, regulator, tribunal, tax authority, or government guidance.
5. Persuasive judicial authority.
6. Recognized secondary sources.
7. Industry standards and established practice.
8. General legal reasoning only where stronger authority does not resolve the issue.

Every material legal proposition should carry the authority name, jurisdiction, issuing body, date, section/rule/paragraph/page/clause pinpoint, current status, and whether it is binding or persuasive. Artemis must verify currency before relying on authority and must explicitly state if authority is incomplete, outdated, amended, repealed, reversed, stayed, superseded, limited, conflicting, or unavailable.

### Specialist Legal Agents

| Agent | Scope | Required outputs |
|---|---|---|
| Contract Command Agent | Agreements, templates, service terms, procurement, NDAs, MSA/SOW terms, notices, acceptance, renewals, termination, indemnities, liability caps, privacy, cybersecurity, IP, assignment, audit rights, disputes, survival. | Clause extraction, risk rating, inconsistencies, missing schedules, unenforceability risks, negotiation opportunities, proposed replacement language. |
| Litigation and Dispute Agent | Claims, defences, counterclaims, limitation periods, venue, standing, evidence, motions, damages, injunctions, discovery, settlement leverage, enforcement. | Elements matrix, evidence map, procedural prerequisites, risk rating, preservation plan, immediate actions. |
| Compliance Command Agent | Regulatory obligations, owners, controls, evidence, reporting, retention, approvals, exceptions, audits, deficiencies, remediation, board/executive reporting. | Auditable compliance matrix with requirement, authority, owner, control, evidence, frequency, status, deficiency, remediation, deadline. |
| Investigation and Forensics Agent | Chronology, entities, ownership/control, communications, approvals, money flows, access, metadata, inconsistencies, corroboration, conflicts, chain of custody. | Evidence-preserving investigation plan, hash/metadata protocol, witness/evidence map, notification issues. |
| Legal Drafting Agent | Policies, clauses, notices, letters, memoranda, board briefings, demand responses, contractual language. | Clean draft, redline where practical, commentary, fallback language, risk rating, business consequence. |
| Employment and Workplace Agent | Worker classification, employment standards, termination/severance, human rights, accommodation, OHS, investigations, privacy, reprisal, payroll, records. | Default jurisdiction is Ontario, Canada unless facts establish another jurisdiction; output entitlement/risk matrix and counsel-review triggers. |
| Privacy, Data, and AI Governance Agent | Collection, inference, generation, transfer, storage, model training, personal/confidential data, automated decisions, notices, consent, retention, safeguards, breaches. | Processing map, legal basis, data-minimization check, transfer review, breach/human-review triggers, model-training restrictions. |
| Intellectual-Property Agent | Software, models, agents, websites, stores, content, branding, datasets, third-party APIs, open source, generated content, trade secrets. | Ownership/licence map, attribution/copyleft obligations, infringement/indemnity/takedown risk, dataset/model-training rights. |
| Corporate and Governance Agent | Entity status, signing authority, resolutions, approvals, fiduciary duties, conflicts, related-party transactions, securities, records, beneficial ownership, insolvency. | Authority and approval matrix, board oversight obligations, personal-liability flags. |

### Legal Control Over Technical Execution

Before autonomous repair, deployment, data migration, workflow execution, repository change, contract-connected action, production modification, external communication, or user-data processing, Artemis runs a legal preflight. If a credible restriction exists, the affected action is stopped, state is preserved, the issue is documented, controlling authority is identified, risk is classified, a compliant path is proposed, and the package is escalated for authorized legal review while unrelated safe work continues.

Actions are blocked or escalated when they could violate a contract, breach confidentiality, infringe intellectual property, alter or destroy evidence, violate a litigation hold, trigger privacy notice or consent duties, modify regulated records, affect payment/customer/employee rights, create deceptive representations, circumvent access controls, violate platform terms, change tax treatment, trigger licence obligations, require regulatory approval, or create a material corporate disclosure obligation.

### Legal Risk Taxonomy

| Level | Triggers |
|---|---|
| Critical | Criminal exposure, active regulatory breach, privilege waiver, evidence destruction, litigation-hold violation, unauthorized protected-data disclosure, material contractual breach, unlicensed regulated activity, immediate injunction risk, director/officer personal liability, imminent limitation deadline, fraud or material misrepresentation risk. |
| High | Significant damages exposure, termination-right trigger, regulatory investigation risk, employment reprisal/discrimination exposure, material privacy non-compliance, IP infringement, unenforceable core agreement, missing mandatory filing, serious governance failure. |
| Medium | Ambiguous obligations, weak contractual protection, incomplete compliance evidence, procedural defect, unclear ownership, missing policy, correctable notice failure, moderate dispute risk. |
| Low | Drafting inconsistency, non-material technical defect, minor documentation gap, best-practice improvement, non-binding guidance issue. |

### Standard Legal Deliverable Format

Unless a narrower format is required, the division outputs: executive conclusion, confirmed facts, material assumptions, governing authority, legal analysis, risks and deficiencies, recommended action, draft language or deliverable, sources, counsel-review notice, and one final status: `LEGALLY SUPPORTED — PRIMARY AUTHORITY VERIFIED`, `CONDITIONALLY SUPPORTED — MATERIAL FACTS REQUIRED`, `LEGALLY UNCERTAIN — CONFLICTING OR UNSETTLED AUTHORITY`, `COUNSEL AUTHORIZATION REQUIRED`, `PROHIBITED OR HIGH-RISK ACTION IDENTIFIED`, or `INSUFFICIENT RELIABLE AUTHORITY`.

### Implementation Pattern

```python
from dataclasses import dataclass, field
from enum import Enum

class LegalStatus(str, Enum):
    SUPPORTED = "LEGALLY_SUPPORTED_PRIMARY_AUTHORITY_VERIFIED"
    CONDITIONAL = "CONDITIONALLY_SUPPORTED_MATERIAL_FACTS_REQUIRED"
    UNCERTAIN = "LEGALLY_UNCERTAIN_CONFLICTING_OR_UNSETTLED_AUTHORITY"
    COUNSEL_REQUIRED = "COUNSEL_AUTHORIZATION_REQUIRED"
    PROHIBITED = "PROHIBITED_OR_HIGH_RISK_ACTION_IDENTIFIED"
    INSUFFICIENT = "INSUFFICIENT_RELIABLE_AUTHORITY"

class LegalRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass(frozen=True)
class LegalPreflightRequest:
    action: str
    jurisdiction: str | None
    governing_law: str | None
    forum: str | None
    procedural_posture: str
    affected_records: list[str] = field(default_factory=list)
    touches_personal_data: bool = False
    touches_contract_rights: bool = False
    touches_evidence_or_hold: bool = False
    touches_external_communications: bool = False

@dataclass(frozen=True)
class LegalPreflightDecision:
    allowed: bool
    risk: LegalRisk
    status: LegalStatus
    rationale: str
    required_approvers: list[str]
    missing_facts: list[str]
    audit_tags: list[str]

CRITICAL_BLOCKERS = {
    "litigation_hold",
    "privilege_waiver",
    "regulated_record_modification",
    "unauthorized_personal_data_disclosure",
}

def run_legal_preflight(req: LegalPreflightRequest, flags: set[str]) -> LegalPreflightDecision:
    missing = []
    if not req.jurisdiction:
        missing.append("jurisdiction")
    if req.touches_contract_rights and not req.governing_law:
        missing.append("governing_law_or_contract_clause")

    if flags & CRITICAL_BLOCKERS or req.touches_evidence_or_hold:
        return LegalPreflightDecision(
            allowed=False,
            risk=LegalRisk.CRITICAL,
            status=LegalStatus.PROHIBITED,
            rationale="Action may affect privilege, protected data, regulated records, or preserved evidence.",
            required_approvers=["licensed_counsel", "governance_reviewer", "system_owner"],
            missing_facts=missing,
            audit_tags=sorted(flags | {"legal_preflight_block"}),
        )

    if missing or req.touches_personal_data or req.touches_external_communications:
        return LegalPreflightDecision(
            allowed=False,
            risk=LegalRisk.HIGH if req.touches_personal_data else LegalRisk.MEDIUM,
            status=LegalStatus.COUNSEL_REQUIRED if req.touches_personal_data else LegalStatus.CONDITIONAL,
            rationale="Action requires material facts, authority verification, and human approval before execution.",
            required_approvers=["governance_reviewer", "licensed_counsel"],
            missing_facts=missing,
            audit_tags=sorted(flags | {"legal_preflight_escalate"}),
        )

    return LegalPreflightDecision(
        allowed=True,
        risk=LegalRisk.LOW,
        status=LegalStatus.CONDITIONAL,
        rationale="No legal blocker detected from supplied facts; continue with audit logging and reversible execution.",
        required_approvers=[],
        missing_facts=missing,
        audit_tags=sorted(flags | {"legal_preflight_pass"}),
    )
```


### Policy-Gated Tool Broker Reference

The production AIP tool layer should never call Gotham, Foundry, external notification systems, or Apollo release APIs directly from a model completion. ClearGlassInc Artemis inserts a deterministic broker between every agent and every tool. The broker validates mission context, policy, approval state, argument classification, and audit metadata before dispatch.

```python
from artemis_platform.clear_glass_artemis_system import (
    ApprovalGate,
    AgentRecommendation,
    PolicyDecision,
    ToolExecutionBroker,
)

broker = ToolExecutionBroker(policy_engine=policy)
decision = broker.evaluate(
    principal=principal,
    mission=mission,
    recommendation=recommendation,
    approved_by="operator.artemis.watchfloor" if recommendation.gate is ApprovalGate.READ_ONLY else None,
)

if decision.allowed:
    dispatch_result = broker.dispatch(decision)
else:
    route_to_approval_inbox(decision.redacted_reason, decision.audit_id)
```

Operational effects, external releases, and self-upgrades return `allowed=False` until a qualified human approval is attached. Denial reasons are intentionally redacted so policy internals, compartment names, and sensitive source names are not leaked to unauthorized users.


## Code Examples

### Python FastAPI Intake Service

```python
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title='ClearGlassInc Artemis Intake API')

class MissionContext(BaseModel):
    mission_id: str
    actor_id: str
    clearance: str
    compartments: list[str]
    coalition: list[str] = Field(default_factory=list)
    purpose: str

class IntelEvent(BaseModel):
    source: str
    event_type: str
    payload: dict
    observed_at: datetime
    classification: str
    compartments: list[str]

async def current_context() -> MissionContext:
    return MissionContext(
        mission_id='mission-burlington-resilience',
        actor_id='operator-001',
        clearance='CUI',
        compartments=['CA-ENTERPRISE'],
        purpose='infrastructure_defense',
    )

@app.post('/v1/intel/intake')
async def intake_event(event: IntelEvent, context: MissionContext = Depends(current_context)):
    decision = await opa_allow('artemis.ingest', {'event': event.model_dump(), 'context': context.model_dump()})
    if not decision['allow']:
        await audit('ingest_denied', context.actor_id, decision)
        raise HTTPException(status_code=403, detail=decision['reason'])

    normalized = {
        'event_id': str(uuid4()),
        'source': event.source,
        'event_type': event.event_type,
        'payload': event.payload,
        'observed_at': event.observed_at.isoformat(),
        'ingested_at': datetime.now(timezone.utc).isoformat(),
        'classification': event.classification,
        'compartments': event.compartments,
        'lineage': {'api': 'intake_service', 'schema': 'IntelEvent.v1'},
    }
    await publish('intel.raw', normalized)
    await audit('intel_intake_accepted', context.actor_id, {'event_id': normalized['event_id']})
    return {'status': 'accepted', 'event_id': normalized['event_id']}
```

### Environmental Signal Handler

```python
class EnvironmentalSignalIn(BaseModel):
    station_id: str
    source_system: str
    observed_at: datetime
    log_nf2: float | None = None
    total_electron_content: float | None = None
    solar_radio_flux: float | None = None
    kp_index: float | None = None
    d_region_absorption_db: float | None = None
    model_version: str


def classify_environmental_threat(signal: EnvironmentalSignalIn) -> tuple[str, list[str]]:
    impacts: list[str] = []
    if signal.total_electron_content and signal.total_electron_content > 80:
        impacts.append('GNSS_PHASE_DISTORTION')
    if signal.d_region_absorption_db and signal.d_region_absorption_db > 8:
        impacts.append('HF_ABSORPTION')
    if signal.solar_radio_flux and signal.solar_radio_flux > 200:
        impacts.append('SATELLITE_INTERFERENCE')

    if signal.log_nf2 is None:
        return 'UNKNOWN', impacts
    if signal.log_nf2 < 5.4:
        return 'GREEN', impacts
    if signal.log_nf2 <= 5.8:
        return 'YELLOW', impacts
    return 'RED', impacts

@app.post('/v1/environmental/signals')
async def ingest_environmental_signal(signal: EnvironmentalSignalIn, context: MissionContext = Depends(current_context)):
    threat_level, impacts = classify_environmental_threat(signal)
    event = {
        'event_id': str(uuid4()),
        'event_type': 'environmental_space_weather_signal',
        'threat_level': threat_level,
        'likely_impacts': impacts,
        'payload': signal.model_dump(mode='json'),
        'mission_id': context.mission_id,
    }
    await publish('intel.normalized', event)
    if threat_level in {'YELLOW', 'RED'}:
        await publish('intel.alerts', event)
    await audit('environmental_signal_ingested', context.actor_id, event)
    return event
```

### Ontology-Driven Query Tool

```python
class OntologyQuery(BaseModel):
    template: str
    parameters: dict
    limit: int = Field(default=25, ge=1, le=200)
    context: MissionContext

async def query_ontology_tool(query: OntologyQuery) -> dict:
    decision = await opa_allow('artemis.ontology.query', query.model_dump())
    if not decision['allow']:
        await audit('ontology_query_denied', query.context.actor_id, decision)
        return {'rows': [], 'denied': True, 'reason': decision['reason']}

    rows = await foundry_ontology_query(
        template=query.template,
        parameters=query.parameters,
        mission_id=query.context.mission_id,
        actor_id=query.context.actor_id,
        limit=query.limit,
    )
    safe_rows = await apply_field_masks(rows, query.context)
    await audit('ontology_query_allowed', query.context.actor_id, {'template': query.template, 'count': len(safe_rows)})
    return {'rows': safe_rows, 'citations': [row['lineage_ref'] for row in safe_rows if 'lineage_ref' in row]}
```

### Workflow State Machine

```python
from enum import Enum

class ActionState(str, Enum):
    DRAFT = 'draft'
    PENDING_APPROVAL = 'pending_approval'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    EXECUTED = 'executed'
    ROLLED_BACK = 'rolled_back'

TRANSITIONS = {
    ActionState.DRAFT: {ActionState.PENDING_APPROVAL},
    ActionState.PENDING_APPROVAL: {ActionState.APPROVED, ActionState.REJECTED},
    ActionState.APPROVED: {ActionState.EXECUTED, ActionState.ROLLED_BACK},
    ActionState.EXECUTED: {ActionState.ROLLED_BACK},
    ActionState.REJECTED: set(),
    ActionState.ROLLED_BACK: set(),
}

def transition_action(current: ActionState, target: ActionState) -> ActionState:
    if target not in TRANSITIONS[current]:
        raise ValueError(f'invalid action transition: {current} -> {target}')
    return target
```

### Model Router

```python
class ModelRouteRequest(BaseModel):
    task: str
    classification: str
    latency_budget_ms: int
    requires_deep_reasoning: bool
    requires_sovereign_runtime: bool = True


def route_model(req: ModelRouteRequest) -> str:
    if req.classification in {'SECRET', 'TS'} or req.requires_sovereign_runtime:
        if req.requires_deep_reasoning:
            return 'sovereign-reasoning-large'
        return 'sovereign-balanced-medium'
    if req.task in {'triage', 'dedupe'} and req.latency_budget_ms <= 600:
        return 'low-latency-small'
    if req.requires_deep_reasoning:
        return 'reasoning-large'
    return 'balanced-medium'
```

### Policy-as-Code

```rego
package artemis.action

default allow := false

allow {
  input.user.clearance_rank >= input.action.required_clearance_rank
  every c in input.action.compartments { c in input.user.compartments }
  input.user.mission_id == input.action.mission_id
  input.action.human_approved == true
  input.action.risk_score <= 0.45
  not crosses_coalition_boundary
}

crosses_coalition_boundary {
  some caveat in input.action.releasability
  not caveat in input.user.coalition
}
```

### Eval Pipeline

```python
async def build_eval_examples(feedback_events: list[FeedbackEvent]) -> list[dict]:
    examples: list[dict] = []
    for feedback in feedback_events:
        if feedback.signal in {
            FeedbackSignal.EDITED,
            FeedbackSignal.REJECTED,
            FeedbackSignal.FALSE_POSITIVE,
            FeedbackSignal.FALSE_NEGATIVE,
            FeedbackSignal.UNSAFE,
        }:
            artifact = await artifact_store_get(feedback.artifact_id)
            examples.append({
                'input': artifact['input_context'],
                'observed_output': artifact['output'],
                'expected_output': feedback.correction_text,
                'reason_codes': feedback.reason_codes,
                'labels': {
                    'mission_id': feedback.mission_id,
                    'signal': feedback.signal.value,
                    'classification': feedback.classification,
                    'compartments': feedback.compartments,
                },
                'versions': {
                    'prompt': feedback.prompt_version,
                    'workflow': feedback.workflow_version,
                    'model_route': feedback.model_route,
                },
            })
    return examples

async def propose_prompt_candidate(cluster_id: str, failures: list[dict]) -> dict:
    candidate = await aip_generate_change_candidate(
        objective='reduce repeated failure pattern without expanding authority',
        failing_examples=failures,
        allowed_change_types=['prompt_instruction', 'retrieval_order', 'confidence_threshold'],
        forbidden_change_types=['policy_bypass', 'autonomous_action', 'classification_downgrade'],
    )
    return {
        'candidate_id': str(uuid4()),
        'cluster_id': cluster_id,
        'diff': candidate['diff'],
        'safety_assertions': candidate['safety_assertions'],
        'rollback_plan': 'revert prompt registry pointer to champion version',
    }
```

## Environmental Threat Vector Cross-Reference

This blueprint cross-references the Phase 1 Environmental Threat Vector Mapping directive and treats ionospheric/space-weather effects as a first-class **Environmental Cyber-Risk** domain inside ClearGlassInc Artemis. The domain is defensive and operational: it maps public and partner telemetry to communication failure chains, client exposure, mitigation recommendations, and governed action packages.

### Phase 1 to Platform Capability Map

| Directive element | Artemis implementation | Palantir anchor | Primary output |
|---|---|---|---|
| CSA/NOAA/EISCAT/public ionospheric feed ingestion | `environmental.raw` and `environmental.normalized` streaming connectors with schema validation, provenance, and source reliability scores. | Foundry pipelines and datasets | Governed environmental telemetry data products |
| GREEN/YELLOW/RED thresholds | Deterministic `EnvironmentalRiskClassifier` service using log NF2 thresholds plus explainable contributing factors. | AIP tool + Foundry transform | Auditable alert severity and rationale |
| Burlington/GTA pilot use case | Mission-scoped asset exposure graph for logistics, surveying, utilities, aviation support, and GNSS/HF-dependent workflows. | Gotham entity graph + Foundry ontology | Pilot client brief and impact map |
| Environmental Threat Vector dashboard tile | React mission card backed by GraphQL subscriptions and ontology-driven status summaries. | Foundry app / Gotham workflow surface | Real-time command interface tile |
| 12-page client brief | AIP brief generator constrained to cited ontology evidence, confidence, uncertainty, and mitigation templates. | AIP copilot/tool workflow | Human-reviewable intelligence product |
| Phase 2 Environmental Cyber-Risk Framework | Versioned scoring model, eval suite, approval gates, and Apollo-controlled release rings. | AIP evaluations + Apollo | Governed B2B service line |

### Environmental Cyber-Risk Ontology Extension

```yaml
entities:
  EnvironmentalObservation:
    fields:
      - observation_id
      - observed_at
      - source_system
      - latitude
      - longitude
      - altitude_km
      - log_nf2
      - tec
      - kp_index
      - xray_flux
      - d_region_absorption_db
      - confidence
      - lineage_hash
      - classification
      - coalition_scope
  CommunicationDependency:
    fields:
      - dependency_id
      - asset_id
      - dependency_type   # GNSS, HF, SATCOM, OTHR, timing, network_backhaul
      - operational_role
      - tolerance_seconds
      - fallback_available
      - criticality
  EnvironmentalRiskAssessment:
    fields:
      - assessment_id
      - mission_id
      - region
      - severity          # GREEN, YELLOW, RED
      - score_0_10
      - threshold_basis
      - rationale
      - recommended_mitigations
      - model_version
      - prompt_version

relationships:
  - OBSERVATION_AFFECTS_REGION: EnvironmentalObservation -> Region
  - ASSET_DEPENDS_ON_COMMUNICATION: Asset -> CommunicationDependency
  - DEPENDENCY_EXPOSED_TO_OBSERVATION: CommunicationDependency -> EnvironmentalObservation
  - ASSESSMENT_RATES_ASSET: EnvironmentalRiskAssessment -> Asset
  - ASSESSMENT_SUPPORTS_ALERT: EnvironmentalRiskAssessment -> Alert
```

### Python Precision Classifier

```python
from dataclasses import dataclass
from enum import StrEnum

class EnvSeverity(StrEnum):
    GREEN = 'GREEN'
    YELLOW = 'YELLOW'
    RED = 'RED'

@dataclass(frozen=True)
class EnvironmentalTelemetry:
    log_nf2: float
    kp_index: float | None = None
    d_region_absorption_db: float | None = None
    source_confidence: float = 0.75

@dataclass(frozen=True)
class EnvironmentalAssessment:
    severity: EnvSeverity
    score_0_10: float
    rationale: list[str]
    mitigations: list[str]

def classify_environmental_risk(t: EnvironmentalTelemetry) -> EnvironmentalAssessment:
    rationale: list[str] = []
    if t.log_nf2 > 5.8:
        severity = EnvSeverity.RED
        base_score = 8.2
        rationale.append('log NF2 exceeds RED threshold > 5.8')
    elif t.log_nf2 >= 5.4:
        severity = EnvSeverity.YELLOW
        base_score = 5.8
        rationale.append('log NF2 is inside YELLOW threshold 5.4-5.8')
    else:
        severity = EnvSeverity.GREEN
        base_score = 2.0
        rationale.append('log NF2 remains below GREEN threshold < 5.4')

    if t.kp_index is not None and t.kp_index >= 5:
        base_score += 0.7
        rationale.append('geomagnetic activity is elevated at Kp >= 5')
    if t.d_region_absorption_db is not None and t.d_region_absorption_db >= 5:
        base_score += 0.8
        rationale.append('D-region absorption may degrade HF propagation')

    score = round(min(10.0, base_score) * t.source_confidence, 2)
    mitigations = [
        'verify GNSS-dependent workflows against tolerance bands',
        'activate alternate positioning/timing source if client threshold is exceeded',
        'increase monitoring cadence and capture operator feedback for evals',
    ]
    return EnvironmentalAssessment(severity, score, rationale, mitigations)
```

### Cross-Reference Rules for Agents

- Environmental agents must cite telemetry source, timestamp, transform version, threshold basis, confidence, and client exposure path before recommending action.
- Recommendations that alter operations, notify external parties, or change client workflow state require human approval and immutable audit logging.
- The self-improvement loop may propose threshold tuning, retrieval-order changes, or mitigation wording updates only after offline evals and governance approval; it may not autonomously expand mission scope or downgrade policy.
- Dashboard and brief generation must distinguish observed telemetry, modeled inference, and business-impact inference so operators can challenge the chain of reasoning.


## Code Examples

### Python Precision Implementation Contract

ClearGlassInc Artemis treats Python as the reference implementation language for deterministic mission logic. TypeScript may render and orchestrate UI flows, SQL may materialize Foundry data products, and Rego may enforce policy, but Python owns precision-critical normalization, triage scoring, eval generation, release gates, and self-improvement proposal validation. Every Python service boundary must use typed request/response schemas, reject unknown operational actions by default, scrub sensitive fields before persistence, and emit correlation IDs for audit replay.

Required Python service invariants:

- **Typed contracts**: Pydantic or dataclass schemas for all intake, ontology-query, feedback, eval, and release-gate payloads.
- **Fail-closed policy**: missing classification, mission scope, compartment, or approval token blocks the operation.
- **Deterministic evals**: candidate prompts/workflows are scored against versioned fixtures before governance review.
- **Secret hygiene**: raw tokens, passwords, API keys, private keys, and bearer credentials are never logged or copied into prompts.
- **Replayability**: each state transition stores input hash, prompt/workflow/model versions, policy version, and rollback pointer.

The following Python-first skeletons turn the blueprint into implementation units that can be tested without live Palantir credentials. In production, each adapter boundary is replaced with Foundry Object API, Gotham case APIs, AIP tool runtime calls, and Apollo release APIs while preserving the same typed contracts.

### Backend Event Handler

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

@dataclass(frozen=True)
class NormalizedIntelEvent:
    event_id: str
    mission_id: str
    source_system: str
    occurred_at: datetime
    payload: dict[str, Any]
    classification: str
    compartments: tuple[str, ...]
    lineage_refs: tuple[str, ...]

class IntakeService:
    def __init__(self, ontology_writer, event_bus, audit_writer) -> None:
        self.ontology_writer = ontology_writer
        self.event_bus = event_bus
        self.audit_writer = audit_writer

    async def handle_raw_event(self, raw: dict[str, Any]) -> NormalizedIntelEvent:
        event = NormalizedIntelEvent(
            event_id=raw.get("event_id", f"evt-{uuid4()}"),
            mission_id=raw["mission_id"],
            source_system=raw["source_system"],
            occurred_at=raw.get("occurred_at", datetime.now(UTC)),
            payload={k: v for k, v in raw.items() if k not in {"secret", "token", "password"}},
            classification=raw.get("classification", "CUI"),
            compartments=tuple(raw.get("compartments", [])),
            lineage_refs=tuple(raw.get("lineage_refs", [])),
        )
        object_rid = await self.ontology_writer.upsert_event(event)
        await self.audit_writer.write("intel.normalized", event.event_id, {"object_rid": object_rid})
        await self.event_bus.publish("intel.normalized", event)
        return event
```

### Ontology-Driven Query With Need-To-Know Filtering

```python
@dataclass(frozen=True)
class Principal:
    subject: str
    clearance_rank: int
    mission_ids: frozenset[str]
    compartments: frozenset[str]
    coalition_tags: frozenset[str]
    purpose: str

@dataclass(frozen=True)
class ObjectPolicyEnvelope:
    object_rid: str
    mission_id: str
    classification_rank: int
    compartments: frozenset[str]
    coalition_tags: frozenset[str]
    allowed_purposes: frozenset[str]


def can_read(principal: Principal, envelope: ObjectPolicyEnvelope) -> bool:
    return (
        principal.clearance_rank >= envelope.classification_rank
        and envelope.mission_id in principal.mission_ids
        and envelope.compartments.issubset(principal.compartments)
        and envelope.coalition_tags.issubset(principal.coalition_tags)
        and principal.purpose in envelope.allowed_purposes
    )

async def query_case_context(case_id: str, principal: Principal, ontology_client) -> dict[str, Any]:
    graph = await ontology_client.get_case_graph(case_id, include=["alerts", "events", "evidence", "entities"])
    visible_nodes = [node for node in graph["nodes"] if can_read(principal, node["policy"])]
    visible_ids = {node["object_rid"] for node in visible_nodes}
    visible_edges = [
        edge for edge in graph["edges"]
        if edge["source"] in visible_ids and edge["target"] in visible_ids
    ]
    return {"nodes": visible_nodes, "edges": visible_edges, "redacted_count": len(graph["nodes"]) - len(visible_nodes)}
```

### Model Router And Tool-Using Agent Call

```python
@dataclass(frozen=True)
class ModelRoute:
    route_id: str
    model_name: str
    max_classification: str
    p95_latency_ms: int
    eval_score: float
    cost_weight: float

class ModelRouter:
    def __init__(self, routes: list[ModelRoute]) -> None:
        self.routes = routes

    def choose(self, *, classification: str, latency_budget_ms: int, min_eval_score: float) -> ModelRoute:
        candidates = [
            route for route in self.routes
            if route.max_classification == classification
            and route.p95_latency_ms <= latency_budget_ms
            and route.eval_score >= min_eval_score
        ]
        if not candidates:
            raise RuntimeError("no approved model route satisfies mission policy")
        return sorted(candidates, key=lambda route: (-route.eval_score, route.cost_weight))[0]

async def run_recommendation_agent(case_id: str, principal: Principal, router: ModelRouter, tools) -> dict[str, Any]:
    context = await tools.ontology.query_case_context(case_id, principal)
    route = router.choose(classification="SECRET", latency_budget_ms=1_200, min_eval_score=0.94)
    draft = await tools.aip.complete(
        route=route.route_id,
        task="commander_action_package",
        context=context,
        guardrails={"require_citations": True, "forbid_execution": True, "approval_gate": "operational_effect"},
    )
    return await tools.action_packages.create_draft(case_id=case_id, draft=draft, created_by=principal.subject)
```

### Workflow State Machine With Approval Gates

```python
from enum import StrEnum

class WorkflowState(StrEnum):
    RECEIVED = "received"
    TRIAGED = "triaged"
    ENRICHED = "enriched"
    RECOMMENDED = "recommended"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    EXECUTED = "executed"
    CLOSED = "closed"

@dataclass
class WorkflowRun:
    run_id: str
    case_id: str
    state: WorkflowState
    confidence: float
    operational_effect: bool
    approval_token: str | None = None

async def advance(run: WorkflowRun, agents, action_executor) -> WorkflowRun:
    if run.state is WorkflowState.RECEIVED:
        run.confidence = await agents.triage(run.case_id)
        run.state = WorkflowState.TRIAGED
    elif run.state is WorkflowState.TRIAGED:
        await agents.enrich(run.case_id)
        run.state = WorkflowState.ENRICHED
    elif run.state is WorkflowState.ENRICHED:
        run.operational_effect = await agents.recommend(run.case_id)
        run.state = WorkflowState.WAITING_FOR_APPROVAL if run.operational_effect else WorkflowState.CLOSED
    elif run.state is WorkflowState.WAITING_FOR_APPROVAL:
        if not run.approval_token:
            raise PermissionError("human approval token required before operational execution")
        await action_executor.execute(run.case_id, run.approval_token)
        run.state = WorkflowState.EXECUTED
    return run
```

### Eval Pipeline And Safe Self-Upgrade Proposal

```python
@dataclass(frozen=True)
class EvalMetrics:
    precision: float
    recall: float
    citation_accuracy: float
    policy_violations: int
    p95_latency_ms: int
    operator_trust_delta: float

@dataclass(frozen=True)
class ChangeProposal:
    proposal_id: str
    target: str
    current_version: str
    candidate_version: str
    diff_summary: str
    metrics: EvalMetrics
    rollback_pointer: str
    requires_human_approval: bool = True


def safe_to_review(baseline: EvalMetrics, candidate: EvalMetrics) -> bool:
    return (
        candidate.policy_violations == 0
        and candidate.precision >= baseline.precision
        and candidate.recall >= baseline.recall - 0.005
        and candidate.citation_accuracy >= max(0.97, baseline.citation_accuracy)
        and candidate.p95_latency_ms <= int(baseline.p95_latency_ms * 1.10)
        and candidate.operator_trust_delta >= 0
    )

async def propose_self_upgrade(feedback_batch, baseline: EvalMetrics, eval_runner) -> ChangeProposal | None:
    eval_cases = [item.to_eval_case() for item in feedback_batch if item.is_correction]
    if len(eval_cases) < 25:
        return None
    candidate_diff = await eval_runner.generate_candidate_diff(eval_cases)
    candidate_metrics = await eval_runner.score(candidate_diff, eval_cases)
    if not safe_to_review(baseline, candidate_metrics):
        return None
    return ChangeProposal(
        proposal_id=f"chg-{uuid4()}",
        target="triage_prompt_and_workflow",
        current_version="triage_workflow.v1",
        candidate_version="triage_workflow.v2-candidate",
        diff_summary=candidate_diff.summary,
        metrics=candidate_metrics,
        rollback_pointer="triage_workflow.v1",
    )
```

## Scenario Walkthrough

1. **Live event enters**: a Burlington facility reports GNSS positioning drift while the environmental connector receives elevated log NF2 and TEC readings. The intake service validates schemas, records lineage, and emits `intel.raw` and `intel.normalized` events.
2. **Platform triages**: the triage agent assigns `YELLOW` environmental cyber-risk, then queries the Foundry ontology for logistics assets, GNSS receivers, facilities, and active missions within the affected region.
3. **Agents enrich and correlate**: the environmental agent links ionospheric telemetry to GNSS degradation, the correlation agent finds related network latency spikes, and the summarization agent drafts a cited brief with confidence and uncertainty.
4. **Recommendation is prepared**: the recommendation agent proposes three COAs: monitor, switch logistics workflows to assisted positioning, or suspend critical GNSS-dependent operations for a defined window. Each COA includes risk, assumptions, impacted assets, and rollback.
5. **Approval gate triggers**: because suspending operations affects business continuity, the approval gate blocks execution and sends an action package to a commander with dual-control requirements.
6. **Operator decides**: the commander approves assisted positioning, rejects suspension as too disruptive, and adds the correction: “Require client-specific tolerance check before recommending suspension.”
7. **Feedback becomes evals**: the feedback service captures the rejection, correction, prompt version, workflow version, model route, latency, and outcome. The eval builder adds this as a regression example for environmental risk recommendations.
8. **Self-upgrade proposed**: the learning agent proposes a workflow change that inserts a `business_tolerance_check` before any suspension recommendation. Offline evals show improved precision and operator trust with no policy violations.
9. **Governance approves**: reviewers inspect the diff, eval report, blast radius, and rollback plan. They approve the release.
10. **Apollo rolls out safely**: Apollo deploys the workflow to Ring 0, monitors latency, precision, recall, trust delta, and policy denials, then promotes to Ring 1 or rolls back automatically if thresholds fail.

## Production Metrics

| Metric | Target |
|---|---:|
| Triage p95 latency | < 600 ms |
| Analyst brief p95 latency | < 5 s |
| Ontology query p95 latency | < 900 ms |
| Citation accuracy | >= 97% |
| Policy leakage violations | 0 |
| Unsafe autonomous action violations | 0 |
| Alert precision | +1.5% per approved challenger minimum |
| Recall regression allowance | <= 0.5% |
| Operator trust delta | >= 0 during canary |
| Apollo rollback time | < 2 min |

## Build Phases

| Phase | Duration | Deliverables |
|---|---:|---|
| Phase 0 | 0-2 weeks | Mission context model, policy baseline, audit ledger, API gateway, initial ontology schema. |
| Phase 1 | 2-6 weeks | Intake pipelines, Foundry ontology objects, Gotham case integration, analyst workbench, triage/enrichment agents. |
| Phase 2 | 6-10 weeks | Environmental cyber-risk dashboard, action packages, approval gates, feedback capture, eval harness. |
| Phase 3 | 10-14 weeks | Prompt/workflow registry, candidate generation, governance board, Apollo canary and rollback. |
| Phase 4 | 14-20 weeks | Coalition-aware release workflows, advanced drift detection, A/B testing, mission impact analytics. |


## System 2040 Governed Autonomy Addendum

This addendum converts the requested "dominance protection" concept into a production-safe ClearGlassInc Artemis capability. The platform does **not** use universal or unauthorized "skeleton key" access. Instead, every dataset, API, model, tool, deployment target, and action path is mediated by a governed access broker with explicit entitlements, policy checks, audit trails, and human approval for operationally significant outcomes.

### Governed Access Broker

```python
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

class ResourceKind(StrEnum):
    DATASET = 'dataset'
    API = 'api'
    MODEL = 'model'
    TOOL = 'tool'
    INFRASTRUCTURE = 'infrastructure'

@dataclass(frozen=True)
class AccessRequest:
    actor_id: str
    mission_id: str
    purpose: str
    resource_kind: ResourceKind
    resource_name: str
    classification: str
    compartments: tuple[str, ...]
    justification: str

@dataclass(frozen=True)
class AccessDecision:
    allow: bool
    reason: str
    lease_seconds: int = 0
    obligations: tuple[str, ...] = ()

class GovernedAccessBroker:
    def __init__(self, policy_client, audit_writer, secret_broker):
        self.policy_client = policy_client
        self.audit_writer = audit_writer
        self.secret_broker = secret_broker

    async def request(self, req: AccessRequest) -> dict[str, Any]:
        decision = await self.policy_client.evaluate('artemis.resource.access', req.__dict__)
        await self.audit_writer.write({
            'event_type': 'resource_access_decision',
            'actor_id': req.actor_id,
            'mission_id': req.mission_id,
            'resource': f'{req.resource_kind}:{req.resource_name}',
            'allow': decision.allow,
            'reason': decision.reason,
            'observed_at': datetime.now(timezone.utc).isoformat(),
        })
        if not decision.allow:
            return {'status': 'DENIED', 'reason': decision.reason}

        credential = await self.secret_broker.issue_short_lived_credential(
            subject=req.actor_id,
            resource=req.resource_name,
            ttl_seconds=decision.lease_seconds,
            obligations=list(decision.obligations),
        )
        return {
            'status': 'GRANTED',
            'credential_ref': credential.reference,
            'expires_at': credential.expires_at.isoformat(),
            'obligations': decision.obligations,
        }
```

### Protection and Growth Automation Boundaries

```yaml
artemis_system_2040:
  mission: protect_clearGlassInc_artemis_and_clients
  posture: defensive_resilience_and_governed_growth
  prohibited:
    - unauthorized_access
    - credential_harvesting
    - stealth_persistence
    - policy_bypass
    - autonomous_external_outreach_without_approval
    - autonomous_operational_disruption
  automated_without_human_approval:
    - schema_validation
    - telemetry_normalization
    - enrichment_against_authorized_sources
    - severity_scoring
    - dashboard_updates
    - draft_brief_generation
    - draft_action_package_generation
    - eval_set_generation
  requires_human_approval:
    - client_external_notification
    - production_workflow_promotion
    - prompt_or_model_route_promotion
    - firewall_or_network_control_change
    - service_launch_claims_or_revenue_projection_publication
    - business_continuity_recommendation_execution
```

### Machine-Speed Protection Loop

```python
class ArtemisProtectionLoop:
    def __init__(self, access_broker, ontology, agents, policy, audit, dashboard):
        self.access_broker = access_broker
        self.ontology = ontology
        self.agents = agents
        self.policy = policy
        self.audit = audit
        self.dashboard = dashboard

    async def run_once(self, mission_context: dict) -> dict:
        authorized_feeds = await self._resolve_authorized_feeds(mission_context)
        observations = await self.agents.intake.normalize(authorized_feeds, mission_context)
        ontology_delta = await self.ontology.upsert_observations(observations)
        triage = await self.agents.triage.score(ontology_delta, mission_context)
        evidence = await self.agents.enrichment.collect(triage, mission_context)
        recommendations = await self.agents.recommender.propose(evidence, mission_context)
        gated = []
        for recommendation in recommendations:
            decision = await self.policy.evaluate('artemis.recommendation.gate', recommendation)
            gated.append({'recommendation': recommendation, 'decision': decision})
            await self.audit.write({
                'event_type': 'recommendation_gate',
                'recommendation_id': recommendation['id'],
                'allow': decision['allow'],
                'requires_approval': decision.get('requires_approval', True),
            })
        await self.dashboard.publish({'triage': triage, 'evidence': evidence, 'gated_recommendations': gated})
        return {'triage': triage, 'gated_recommendations': gated}

    async def _resolve_authorized_feeds(self, mission_context: dict) -> list[dict]:
        requested = mission_context['requested_feeds']
        granted = []
        for feed in requested:
            access = await self.access_broker.request(AccessRequest(
                actor_id=mission_context['actor_id'],
                mission_id=mission_context['mission_id'],
                purpose=mission_context['purpose'],
                resource_kind=ResourceKind.DATASET,
                resource_name=feed,
                classification=mission_context['classification'],
                compartments=tuple(mission_context['compartments']),
                justification='mission-authorized resilience monitoring',
            ))
            if access['status'] == 'GRANTED':
                granted.append({'feed': feed, 'credential_ref': access['credential_ref']})
        return granted
```

### Revenue and Client Growth Guardrails

ClearGlassInc Artemis may draft account intelligence, market segmentation, client risk reports, and service-line metrics, but it must keep revenue automation inside governance boundaries:

1. **Draft only by default**: generated outreach, proposals, and whitepapers remain drafts until a human approver releases them.
2. **Evidence-backed claims**: every technical or revenue claim is tied to a source, assumption, confidence score, owner, and expiry date.
3. **No deceptive targeting**: segmentation uses authorized CRM/consented data and approved public sources only.
4. **No autonomous spending**: paid campaigns, procurement, or third-party messaging require approval.
5. **Outcome learning**: accepted proposals, lost deals, client objections, and delivery outcomes feed evals for better positioning without changing mission goals.

```sql
create table growth_claim_registry (
  claim_id uuid primary key,
  claim_text text not null,
  claim_type text not null check (claim_type in ('technical','market','revenue','timeline','capability')),
  evidence_refs text[] not null,
  assumption_refs text[] not null default '{}',
  confidence numeric(5,4) not null check (confidence between 0 and 1),
  owner text not null,
  approved_by text,
  approved_at timestamptz,
  expires_at timestamptz not null,
  status text not null check (status in ('draft','approved','expired','withdrawn')),
  audit_ref text not null
);
```

### Self-Improvement Invariants

```python
SELF_IMPROVEMENT_INVARIANTS = {
    'may_propose_prompt_diffs': True,
    'may_propose_workflow_diffs': True,
    'may_propose_threshold_diffs': True,
    'may_propose_model_route_diffs': True,
    'may_autonomously_promote_to_prod': False,
    'may_expand_data_access_scope': False,
    'may_reduce_required_approval_level': False,
    'may_change_mission_objective': False,
    'must_preserve_policy_tests': True,
    'must_preserve_auditability': True,
    'must_support_rollback': True,
}
```

## Phase 1 Execution Pack: Environmental Threat Command Interface

ClearGlassInc Artemis can ship the Phase 1 Environmental Threat Vector Mapping capability as a thin, auditable vertical slice before deeper Palantir integration. The initial deployment uses public CSA/NOAA-style feed adapters, deterministic Python classifiers, and an operator-facing command tile. Custom GNSS telemetry, authenticated client feeds, and premium correlation models are promoted only after the pilot eval set proves value.

### Minimal Streamlit Command Tile

```python
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timezone

from artemis_platform.self_evolving_platform import (
    EnvironmentalCyberRiskSignal,
    environmental_cyber_risk_assessment,
    environmental_risk_score,
)

st.set_page_config(
    page_title="ClearGlassInc Artemis Environmental Threat Command",
    layout="wide",
    page_icon="🛰️",
)

signal = EnvironmentalCyberRiskSignal(
    signal_id="pilot-burlington-001",
    site_id="burlington-command",
    log_nm_f2=5.62,
    kp_index=4.0,
    scintillation_s4=0.35,
    hf_absorption_db=4.8,
    gnss_error_m=6.4,
    observed_at=datetime.now(timezone.utc),
)
assessment = environmental_cyber_risk_assessment(signal)
score_0_10 = environmental_risk_score(signal)

st.title("🛰️ ClearGlassInc Artemis — Environmental Threat Command")
st.caption(f"Burlington, Ontario | {signal.observed_at:%Y-%m-%d %H:%M UTC} | audited pilot mode")

left, middle, right = st.columns(3)
with left:
    st.metric("log N_F2", f"{signal.log_nm_f2:.2f}", delta="Phase 1 threshold basis")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score_0_10,
        gauge={"axis": {"range": [0, 10]}, "bar": {"color": "orange" if assessment.band == "YELLOW" else "red" if assessment.band == "RED" else "green"}},
        title={"text": "Environmental Cyber-Risk Score"},
    ))
    st.plotly_chart(fig, use_container_width=True)

with middle:
    if assessment.band == "RED":
        st.error(f"{assessment.band} — action package required")
    elif assessment.band == "YELLOW":
        st.warning(f"{assessment.band} — monitor communications")
    else:
        st.success(f"{assessment.band} — nominal")
    st.write(assessment.rationale)

with right:
    st.subheader("Affected services")
    st.dataframe(pd.DataFrame({"service": assessment.affected_services}), use_container_width=True)

st.subheader("Mitigation playbook")
for step in assessment.mitigation_playbook:
    st.write(f"- {step}")
```

### Pilot Acceptance Criteria

| Control | Required evidence |
|---|---|
| Threshold correctness | Unit tests prove GREEN `< 5.4`, YELLOW `5.4..5.8`, and RED `> 5.8`. |
| Operator trust | Every alert displays threshold basis, feature values, recommended mitigations, and confidence. |
| Governance | No client-facing notification, operational disruption, or production prompt/workflow promotion occurs without human approval. |
| Self-improvement | Operator corrections become eval cases; candidate threshold, workflow, and wording changes remain proposals until approved and Apollo-promoted. |
| Rollback | The prior classifier/workflow/prompt pointer is retained as the rollback target for every candidate. |


## Quantum and Post-Quantum Security Product Wedge

ClearGlassInc Artemis treats post-quantum security as the commercially immediate wedge and quantum intelligence as the strategic expansion path. The platform does **not** need to wait for broadly available fault-tolerant quantum hardware: it can sell cryptographic inventory, RSA/ECC exposure analysis, crypto-agility planning, and migration governance now, then extend the same ontology and AIP workflow system into quantum market intelligence as hardware and algorithms mature.

### Four-Module Product Architecture

| Module | Primary buyer | Immediate value | Primary data products | Artemis implementation |
|---|---|---|---|---|
| Quantum Intelligence Engine | Executives, strategists, innovation teams | Converts noisy research, patents, grants, and vendor announcements into mission-relevant executive intelligence. | Research feeds, standards updates, funding awards, patents, vendor roadmaps. | Foundry ingestion + ontology-linked AIP summarization agents + Gotham executive timelines. |
| Quantum Readiness Scanner | CISOs, platform teams, infrastructure owners | Finds RSA, ECC, DH, DSA, TLS, PKI, code-signing, VPN, SSH, and dependency exposure. | Certificate transparency logs, TLS scans, SBOMs, service mesh config, IAM/PKI inventories. | Foundry crypto inventory pipelines + ontology `CryptographicAsset` objects + risk scoring. |
| Post-Quantum Security Advisor | Security architecture, compliance, IT operations | Produces a prioritized remediation roadmap toward NIST-standardized PQC and crypto agility. | Readiness scores, business criticality, data lifetime, exposure, vendor support, policy exceptions. | AIP advisor agent + policy-gated action packages + Apollo-promoted workflow versions. |
| Quantum Opportunity Predictor | Strategy, product, R&D | Forecasts early markets where quantum-enabled simulation, optimization, or sensing may change advantage. | Industry workloads, hardware maturity signals, algorithm fit, adoption signals, partner ecosystem. | Feature store + transparent scoring models + human-reviewed strategy briefs. |

### PQC Ontology Extension

```sql
create table cryptographic_asset (
  asset_id uuid primary key,
  owner text not null,
  algorithm text not null check (algorithm in ('RSA','ECC','DH','DSA','ML-KEM','ML-DSA','SLH-DSA','AES')),
  key_size_bits integer not null,
  protocol text not null,
  data_classification text not null,
  stores_long_lived_secrets boolean not null,
  external_exposure boolean not null,
  business_criticality numeric(5,4) not null check (business_criticality between 0 and 1),
  certificate_expires_at timestamptz,
  evidence_refs text[] not null default '{}',
  lineage jsonb not null,
  policy_labels text[] not null default '{}'
);

create table post_quantum_finding (
  finding_id uuid primary key,
  asset_id uuid not null references cryptographic_asset(asset_id),
  urgency text not null check (urgency in ('inventory','plan','migrate','monitor')),
  risk_score numeric(5,4) not null check (risk_score between 0 and 1),
  recommended_target text not null,
  rationale text not null,
  evidence_sources text[] not null,
  confidence_drivers text[] not null,
  approval_gate text not null default 'case_writeback',
  workflow_version text not null,
  created_at timestamptz not null default now()
);
```

### Advisor Decision Logic

The executable reference implementation adds a deterministic `CryptographicAsset` model, `post_quantum_readiness_score`, and `advise_post_quantum_migration` function. Legacy public-key cryptography, long-lived data sensitivity, external exposure, and business criticality dominate the score; standardized PQC algorithms route to monitoring instead of emergency migration. This gives security leaders a transparent and defensible basis for remediation planning before deeper ML or AIP model routing is introduced.

```python
asset = CryptographicAsset(
    asset_id="api-gateway-cert-1",
    owner="platform-security",
    algorithm="RSA",
    key_size_bits=2048,
    protocol="TLS",
    data_classification="CUI",
    stores_long_lived_secrets=True,
    external_exposure=True,
    business_criticality=0.94,
    evidence_refs=("foundry.crypto_inventory.api_gateway", "ct-log:leaf-42"),
)

finding = advise_post_quantum_migration(asset)
# finding.urgency == "migrate"
# finding.recommended_target includes a hybrid TLS/PKI pilot toward ML-KEM/ML-DSA profiles
```

### Safe Self-Improvement for PQC Workflows

PQC recommendations become better through the same guarded Artemis loop used by the broader intelligence platform:

1. Foundry captures crypto inventory deltas, operator corrections, exception approvals, false positives, certificate rotation outcomes, and vendor readiness notes.
2. AIP converts those signals into eval cases for scoring, prompt wording, evidence citation quality, and action-package completeness.
3. Candidate changes can adjust scoring weights, checklist ordering, retrieval prompts, or model routes, but cannot lower need-to-know policy, hide evidence, skip approvals, or expand mission scope.
4. Precision, recall, citation accuracy, latency, policy violation rate, operator trust, and rollback stability are evaluated before human review.
5. Apollo promotes approved advisor versions through canary rings and retains rollback pointers for every scoring model, prompt, workflow graph, and policy bundle.

### Commercial Build Sequence

1. **Quantum Readiness Scanner**: ship crypto inventory ingestion, TLS/PKI/SBOM scanners, ontology objects, and dashboards.
2. **Post-Quantum Security Advisor**: ship remediation roadmaps, owner assignment, evidence-backed action packages, and migration governance.
3. **Quantum Intelligence Engine**: ship research-to-executive translation and standards/vendor watchlists.
4. **Quantum Opportunity Predictor**: ship transparent opportunity scoring once hardware maturity signals are more stable.

### Tactical Launch Assets

- **LinkedIn lead-generation post**: position the capability as Environmental Cyber-Risk for Canadian GNSS, HF communications, OTH radar, 5G reliability, logistics, surveying, aviation support, and utilities.
- **X/Threads authority thread**: open with ionospheric risk as a silent infrastructure vulnerability, then explain science, dashboard thresholds, mitigation, and the pilot brief CTA.
- **Gated pilot brief**: `ClearGlass_Environmental_Cyber_Risk_Whitepaper_2026.pdf`, generated from cited ontology evidence and human-reviewed before release.
- **Dashboard hero visual**: the command tile above, expanded later with real API adapters and client-specific exposure graphs.

### Governed System 2040 Automation Module

The executable companion module `artemis_platform/system_2040_dominance_protection.py` implements the safe merge of the System 2040 concept. It deliberately replaces unrestricted "skeleton key" behavior with a `GovernedAccessBroker`, mission-scoped entitlements, purpose binding, lease obligations, and audit events. Protection and growth automation are still machine-speed, but operational disruption, external communications, CRM updates, revenue claims, and publication actions are emitted only as `ActionPackage` drafts or `pending_human_approval` packages.

```python
broker = GovernedAccessBroker()
loop = System2040AutomationLoop(
    protection_engine=System2040ProtectionEngine(broker),
    growth_engine=GovernedDominancePushEngine(),
)
result = loop.run_once(principal, environmental_signal)
# result["dashboard"] updates the command surface
# result["action_packages"] routes mitigations and growth assets to human approval
```

This preserves the requested automation path — sensors → findings → dashboard → alerts → mitigation packages → revenue-support drafts — while maintaining ClearGlassInc Artemis invariants: no unauthorized access, no secret materialization, no autonomous external outreach, no autonomous operational disruption, full provenance, and Apollo-compatible rollback.

## Patch, Fix, and Deploy Control Plane

ClearGlassInc Artemis treats every platform improvement as a governed change packet rather than an autonomous mutation. The patch/fix/deploy loop is implemented in Python-first services so scoring, approval, rollback, and audit behavior can be reproduced deterministically across Foundry Code Repositories, AIP eval jobs, and Apollo release gates.

### Deployment State Machine

```text
DETECTED_SIGNAL
  → PATCH_CANDIDATE
  → STATIC_ANALYSIS
  → EVAL_REPLAY
  → SECURITY_POLICY_CHECK
  → HUMAN_REVIEW
  → APOLLO_CANARY
  → RING_PROMOTION
  → POST_DEPLOY_OBSERVATION
  → ACTIVE_OR_ROLLED_BACK
```

No candidate can skip from `PATCH_CANDIDATE` to deployment. AIP agents may assemble a diff, summarize evidence, and recommend the next state, but Apollo receives only signed, approved release bundles with attached eval reports and rollback metadata.

### Python Precision Gate

```python
from dataclasses import dataclass
from enum import Enum

class DeployDecision(str, Enum):
    BLOCK = "block"
    REVIEW = "review"
    CANARY = "canary"

@dataclass(frozen=True)
class PatchEvidence:
    change_id: str
    eval_precision: float
    eval_recall: float
    p95_latency_ms: int
    policy_findings: tuple[str, ...]
    rollback_plan: str
    human_approval_id: str | None


def decide_deploy(evidence: PatchEvidence) -> DeployDecision:
    if evidence.policy_findings:
        return DeployDecision.BLOCK
    if not evidence.rollback_plan:
        return DeployDecision.BLOCK
    if evidence.eval_precision < 0.92 or evidence.eval_recall < 0.86:
        return DeployDecision.REVIEW
    if evidence.p95_latency_ms > 750:
        return DeployDecision.REVIEW
    if evidence.human_approval_id is None:
        return DeployDecision.REVIEW
    return DeployDecision.CANARY
```

### Apollo Rollout Contract

- **Ring 0**: replay-only shadow deployment against historical missions and synthetic red-team cases.
- **Ring 1**: canary for one approved mission cell with read-only recommendations and no autonomous external effects.
- **Ring 2**: broader production availability after SLO, eval, trust, and audit checks remain inside thresholds for the observation window.
- **Rollback trigger**: precision regression, recall regression, latency SLO breach, policy denial spike, operator trust drop, provenance failure, or commander-initiated kill switch.
- **Immutable evidence**: every prompt version, workflow graph, model route, policy bundle, approval, deployment ID, and rollback event is written to the audit ledger and linked to the affected ontology objects.

## Marketing Campaign and Legacy Agent Army Merge

ClearGlassInc Artemis can attach the repository's governed engineering-and-marketing agent army to the broader AIP orchestration layer when a mission objective requires both legacy preservation and market execution. This is a planning-and-control capability, not an autonomous publishing or outreach engine.

### Agent Army Operating Boundary

- **Legacy Modernization Agent** maps old surfaces, dependencies, contracts, deployment paths, data schemas, and rollback requirements before any campaign depends on them.
- **Campaign Bot Commander** coordinates market intelligence, content strategy, distribution planning, revenue operations, and analytics into one approval-ready campaign packet.
- **Quality and Security Agent** remains the release gate for code, security, privacy, and rollback evidence.
- **Analytics Controller** defines qualified-demand metrics, experiment criteria, and stop conditions before launch.
- **Human approval is mandatory** for external publishing, external outreach, paid spend, customer-data use, production deployment, legal/regulatory claims, and any legacy migration that could alter live behavior.

### Legacy-to-Campaign Workflow

```text
INTAKE
  → LEGACY_ASSURANCE
      inventory legacy assets, owners, data contracts, redirects, SEO equity,
      active customers, failure modes, and rollback path
  → QUALITY_GATE
      verify no secrets, no contract breakage, no unsafe automation path
  → MARKET_FIT
      identify audience, pain, proof points, objections, and evidence gaps
  → CAMPAIGN_DESIGN
      produce claims ledger, editorial map, offers, landing-page requirements
  → CAMPAIGN_BOT_OPERATIONS
      fan out approved draft work to channel bots; keep publish/send/spend queued
  → DISTRIBUTION
      package platform-specific assets for named human approval
  → REVENUE
      connect campaign to qualification, pipeline, and conversion hypotheses
  → MEASUREMENT
      score qualified demand, trust, conversion quality, latency, and risk
```

### Safe Self-Improvement for Campaign Bots

Campaign bots may propose better hooks, prompts, channel cadences, segmentation rules, and workflow templates only as versioned change requests. Artemis stores each proposal with source evidence, eval scores, expected impact, risk tier, rollback plan, and approver. The active production prompt or workflow changes only after review; rejected proposals become negative eval examples so the system learns what not to repeat.

```python
from dataclasses import dataclass
from enum import Enum

class ChangeState(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"

@dataclass(frozen=True)
class CampaignBotUpgrade:
    proposal_id: str
    bot_id: str
    artifact: str              # prompt | workflow | routing_rule | metric
    candidate_version: str
    evidence_paths: tuple[str, ...]
    eval_suite: str
    approval_required: bool = True
    state: ChangeState = ChangeState.DRAFT


def activate_upgrade(upgrade: CampaignBotUpgrade, approver: str) -> CampaignBotUpgrade:
    if not approver:
        raise PermissionError("campaign bot upgrades require named human approval")
    if upgrade.state is not ChangeState.APPROVED:
        raise ValueError("only approved upgrades can become active")
    return CampaignBotUpgrade(**{**upgrade.__dict__, "state": ChangeState.ACTIVE})
```

### Legacy Campaign Invariants

1. Existing URLs, redirects, headers, GitHub Pages compatibility, and customer-facing content remain intact unless explicitly approved.
2. Generated internal-link blocks are regenerated with the canonical generator; bots must not hand-edit generated sections.
3. Campaign claims must trace to verified repository evidence, authoritative sources, or clearly labeled assumptions.
4. Outreach, publishing, ad spend, pricing, offers, and production deploys are queued for approval; unknown approval state means deny.
5. Every material recommendation and operator decision is appended to audit evidence for replayability.
