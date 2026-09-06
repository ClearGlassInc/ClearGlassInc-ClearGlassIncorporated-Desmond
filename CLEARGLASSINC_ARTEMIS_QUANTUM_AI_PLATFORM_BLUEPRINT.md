# ClearGlassInc Artemis — Quantum-Centric Self-Evolving AI Intelligence Platform

## Source Grounding

This blueprint is intentionally scoped to three 2026 evidence anchors:

1. **IBM March 12, 2026 quantum-centric supercomputing reference architecture**: a hybrid QPU/GPU/CPU/HPC architecture where quantum processors operate as accelerators inside coordinated classical workflows, with Qiskit-centered orchestration, scheduling, shared storage, and deployment paths across cloud, research centers, and on-prem environments.
2. **2026 practical quantum-advantage target posture**: treat quantum advantage for real-world combinatorial optimization as an evidence-gated, benchmarked capability, not a guaranteed production fact. Artemis must compare every QAOA candidate against strong classical baselines before promotion.
3. **Siemens-style AI digital-twin optimization pattern**: a continuously updated digital twin fuses physical/operational data with AI, simulation, and optimization; recommended changes remain governed by operator approval and closed-loop measurement.

The result is a production architecture for **ClearGlassInc Artemis**: a secure, coalition-aware, audited, latency-sensitive intelligence and optimization platform on **Palantir Gotham, Foundry, AIP, Apollo**, extended with a quantum-classical optimization lane for HVAC + SPD/PDLC Smart Glass control.

---

## System Architecture

### Platform Intent

ClearGlassInc Artemis is a full-stack intelligence operating system that:

- Ingests live and historical operational data.
- Builds a governed Foundry Ontology used by humans, services, and AIP agents.
- Supports Gotham investigation workflows for entity tracking, cases, alerts, timelines, and mission context.
- Uses AIP copilots and agents to triage, enrich, correlate, summarize, recommend, and generate governed action packages.
- Uses Apollo to deploy, monitor, canary, recall, and roll back services, prompts, policies, workflows, and model-router configurations.
- Safely improves its own prompts, workflows, routing policies, QUBO encodings, and QAOA parameter heuristics only through eval-backed, human-approved change control.

### End-to-End Topology

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Operator Surfaces                                                            │
│ React/Next.js Command Surface • Gotham Graph Views • Foundry Apps • AIP Chat │
└───────────────┬──────────────────────────────────────────────────────────────┘
                │ OIDC/JWT + mission context + purpose-of-use
┌───────────────▼──────────────────────────────────────────────────────────────┐
│ API Gateway / Backend-for-Frontend                                           │
│ FastAPI + GraphQL facade + WebSockets + idempotency + policy preflight       │
└───────┬───────────────┬─────────────────┬─────────────────┬────────────────┘
        │               │                 │                 │
┌───────▼──────┐ ┌──────▼───────┐ ┌───────▼──────┐ ┌────────▼───────────────┐
│ Mission Svcs │ │ Digital Twin │ │ Optimization │ │ Governance Services    │
│ cases/alerts │ │ telemetry    │ │ QUBO/QAOA    │ │ evals/prompts/policy   │
└───────┬──────┘ └──────┬───────┘ └───────┬──────┘ └────────┬───────────────┘
        │               │                 │                 │
┌───────▼───────────────▼─────────────────▼─────────────────▼────────────────┐
│ Foundry + Gotham Operational Data Layer                                      │
│ Bronze/Silver/Gold pipelines • Ontology • Actions • Search • Graph • Lineage │
└───────┬───────────────────────────────┬────────────────────────────────────┘
        │                               │
┌───────▼────────────────────┐ ┌────────▼────────────────────────────────────┐
│ AIP Agent Runtime           │ │ Quantum-Centric Compute Lane               │
│ copilots/agents/tools/evals │ │ QPU as accelerator + CPU/GPU simulator     │
└───────┬────────────────────┘ │ Qiskit/PennyLane • classical solvers        │
        │                      └────────┬────────────────────────────────────┘
┌───────▼───────────────────────────────▼────────────────────────────────────┐
│ Security, Observability, and Apollo Runtime Control                         │
│ OPA policy • audit ledger • OpenTelemetry • drift monitors • canary/rollback│
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Layer | Responsibility |
|---|---|
| Frontend | Mission dashboard, HVAC/glass digital-twin map, Gotham investigation launch points, AIP copilot panel, quantum recommendation panel, approvals, eval dashboards. |
| Backend | Mission APIs, command validation, workflow state machines, feedback ingestion, QUBO assembly, QAOA job scheduling, recommendation packaging. |
| Data layer | Live streams, batch history, bitemporal facts, source lineage, feature tables, optimization snapshots, outcome labels. |
| Ontology layer | Governed objects, relationships, actions, permissions, confidence, temporal validity, mission context, smart-building equipment state. |
| AI orchestration | AIP copilots, tool-using agents, model router, retrieval, eval harness, prompt registry, workflow optimizer. |
| Quantum lane | Classical QUBO generation, QAOA simulator, IBM Quantum backend adapter, classical solver baselines, benchmark adjudication. |
| Policy layer | Need-to-know access, entity/field/action permissions, coalition release controls, operational approval gates, prompt/tool constraints. |
| Observability | Service traces, model traces, optimizer metrics, quantum job metrics, eval scorecards, drift alarms, immutable logs. |
| Deployment | Apollo-managed service bundles, prompt packs, workflow packs, policy bundles, model-router configs, rollback and kill switches. |

---

## Data and Ontology

### Core Ontology Objects

Artemis uses Foundry Ontology as the operating contract. Gotham presents investigations over the same objects; AIP agents can only act through ontology actions and governed tools.

```sql
CREATE TABLE artemis_entity (
  entity_id UUID PRIMARY KEY,
  entity_type TEXT NOT NULL CHECK (entity_type IN (
    'Person','Organization','Device','Sensor','Facility','Zone','AirHandler',
    'Chiller','Vent','SmartGlassPanel','WeatherCell','CyberAsset','Observation',
    'Alert','Case','Mission','OptimizationRun','ActionRecommendation'
  )),
  display_name TEXT NOT NULL,
  canonical_attributes JSONB NOT NULL DEFAULT '{}',
  confidence NUMERIC(5,4) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  classification TEXT NOT NULL,
  compartments TEXT[] NOT NULL DEFAULT '{}',
  coalition_scope TEXT NOT NULL,
  mission_tags TEXT[] NOT NULL DEFAULT '{}',
  valid_from TIMESTAMPTZ NOT NULL,
  valid_to TIMESTAMPTZ,
  system_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  system_to TIMESTAMPTZ,
  lineage JSONB NOT NULL,
  provenance_hash TEXT NOT NULL
);

CREATE TABLE artemis_relationship (
  relationship_id UUID PRIMARY KEY,
  src_entity_id UUID NOT NULL REFERENCES artemis_entity(entity_id),
  dst_entity_id UUID NOT NULL REFERENCES artemis_entity(entity_id),
  relationship_type TEXT NOT NULL CHECK (relationship_type IN (
    'located_in','controls','observed_by','feeds','depends_on','derived_from',
    'supports','contradicts','approved_by','deployed_as','coupled_with'
  )),
  confidence NUMERIC(5,4) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  evidence_refs UUID[] NOT NULL DEFAULT '{}',
  classification TEXT NOT NULL,
  compartments TEXT[] NOT NULL DEFAULT '{}',
  coalition_scope TEXT NOT NULL,
  valid_from TIMESTAMPTZ NOT NULL,
  valid_to TIMESTAMPTZ,
  lineage JSONB NOT NULL
);
```

### HVAC + Smart Glass Optimization Objects

```sql
CREATE TABLE hvac_zone_state (
  zone_id UUID PRIMARY KEY,
  facility_id UUID NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  occupancy_count INTEGER NOT NULL,
  indoor_temp_c NUMERIC(5,2) NOT NULL,
  target_temp_c NUMERIC(5,2) NOT NULL,
  co2_ppm NUMERIC(8,2),
  humidity_pct NUMERIC(5,2),
  solar_gain_w_m2 NUMERIC(8,2),
  thermal_load_kw NUMERIC(8,3),
  classification TEXT NOT NULL,
  lineage JSONB NOT NULL
);

CREATE TABLE smart_glass_state (
  panel_id UUID PRIMARY KEY,
  zone_id UUID NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  glass_type TEXT NOT NULL CHECK (glass_type IN ('SPD','PDLC','electrochromic')),
  tint_level INTEGER NOT NULL CHECK (tint_level BETWEEN 0 AND 5),
  switching_cost_kwh NUMERIC(8,5) NOT NULL,
  glare_index NUMERIC(5,2),
  visible_light_transmission NUMERIC(5,4),
  lineage JSONB NOT NULL
);

CREATE TABLE optimization_run (
  run_id UUID PRIMARY KEY,
  mission_id UUID NOT NULL,
  facility_id UUID NOT NULL,
  optimizer_type TEXT NOT NULL CHECK (optimizer_type IN ('classical_mip','or_tools','qaoa_sim','qaoa_qpu')),
  problem_hash TEXT NOT NULL,
  qubo_terms JSONB NOT NULL,
  constraints JSONB NOT NULL,
  solver_config JSONB NOT NULL,
  result JSONB,
  objective_value NUMERIC(12,4),
  baseline_objective_value NUMERIC(12,4),
  approximation_ratio NUMERIC(8,5),
  latency_ms INTEGER,
  eval_status TEXT NOT NULL DEFAULT 'pending',
  approval_state TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  lineage JSONB NOT NULL
);
```

### Ontology-Driven AI Behavior

The ontology drives agent behavior by determining:

- **What the agent can see**: entity, edge, row, field, mission, and coalition filters are resolved before retrieval.
- **What the agent can do**: only ontology actions with approved tool manifests may mutate state.
- **How confident the agent should be**: confidence, lineage, source reliability, recency, and contradictions become part of prompts and ranking features.
- **When approval is mandatory**: any recommendation affecting actuator setpoints, intelligence dissemination, mission tasking, or model/workflow promotion requires a human approval object.

---

## AI and Agent Design

### Copilots

- **Analyst Copilot**: searches Gotham/Foundry entities, builds timelines, summarizes evidence with citations, flags missing collection, drafts intelligence products.
- **Commander Copilot**: packages courses of action, operational risk, confidence, alternative hypotheses, and approval requests.
- **Facility Optimization Copilot**: explains HVAC + Smart Glass recommendations, energy/comfort tradeoffs, constraints, and why QAOA did or did not beat classical baselines.
- **Governance Copilot**: reviews proposed prompt, workflow, model-router, QUBO, or QAOA heuristic changes against eval evidence and policy.

### Multi-Agent Workflows

```text
Live Event → Triage Agent → Enrichment Agent → Correlation Agent
          → Risk/Impact Agent → Recommendation Agent → Policy Agent
          → Human Approval → Execution Agent → Outcome Monitor → Eval Builder
```

### Tool-Using Agents

AIP agents receive tools as explicit contracts:

```yaml
tools:
  - name: ontology.search_entities
    risk: low
    requires_approval: false
  - name: case.open_case
    risk: medium
    requires_approval: true
  - name: optimization.build_qubo
    risk: medium
    requires_approval: false
  - name: optimization.run_qaoa
    risk: medium
    requires_approval: false
  - name: actuator.apply_setpoints
    risk: high
    requires_approval: true
  - name: governance.promote_prompt
    risk: high
    requires_approval: true
```

### Approval Gates

Agents may propose but not independently execute:

- Actuator changes to HVAC or glass systems.
- Intelligence dissemination or coalition release.
- New workflow/prompt/model-router promotion.
- Entity merge/split operations above confidence thresholds.
- Any action package with safety, legal, mission, or operational impact.

---

## Self-Improvement Loop

### Signal Capture

```sql
CREATE TABLE feedback_signal (
  signal_id UUID PRIMARY KEY,
  signal_type TEXT NOT NULL CHECK (signal_type IN (
    'operator_accept','operator_reject','operator_edit','false_positive',
    'false_negative','mission_outcome','comfort_complaint','energy_outcome',
    'latency_complaint','policy_denial','optimizer_underperformed'
  )),
  object_ref TEXT NOT NULL,
  workflow_run_id UUID,
  prompt_version TEXT,
  model_id TEXT,
  optimizer_type TEXT,
  operator_id TEXT NOT NULL,
  mission_id UUID NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  classification TEXT NOT NULL,
  compartments TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE improvement_candidate (
  candidate_id UUID PRIMARY KEY,
  candidate_type TEXT NOT NULL CHECK (candidate_type IN (
    'prompt','workflow','model_router','policy','qubo_encoder','qaoa_heuristic'
  )),
  base_version TEXT NOT NULL,
  proposed_version TEXT NOT NULL,
  diff JSONB NOT NULL,
  supporting_eval_set TEXT NOT NULL,
  offline_metrics JSONB NOT NULL,
  shadow_metrics JSONB,
  risk_assessment JSONB NOT NULL,
  approval_state TEXT NOT NULL DEFAULT 'pending_review',
  rollback_plan JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Safe Upgrade Pipeline

```text
Feedback/Event Logs
  → normalize labels
  → generate eval examples
  → propose candidate change
  → run offline evals
  → run red-team/policy evals
  → shadow deploy on live traffic without impact
  → compare baseline/candidate
  → human review board approval
  → Apollo canary release
  → drift/quality monitoring
  → promote, hold, or rollback
```

### Guardrails

- Artemis can optimize prompts, workflows, retrieval weights, model routing, QUBO coefficients, and QAOA initialization heuristics.
- Artemis cannot change mission goals, policy boundaries, coalition sharing rules, operational authority, or approval requirements.
- Every self-upgrade is versioned, reproducible, eval-backed, approved, monitored, and reversible.

### Metrics

| Area | Metrics |
|---|---|
| Intelligence quality | precision, recall, contradiction rate, citation coverage, entity-resolution accuracy |
| Operator trust | accept/reject ratio, edit distance, override frequency, explanation usefulness |
| Optimization | objective value, approximation ratio, energy savings, comfort violation minutes, actuator wear cost |
| Runtime | p50/p95/p99 latency, queue lag, QPU job wait time, simulator runtime, tool failure rate |
| Governance | policy-denial correctness, approval SLA, audit completeness, rollback frequency |

---

## Full-Stack Implementation

### Repository Shape

```text
artemis/
  apps/
    command-surface/          # Next.js operator UI
    governance-console/       # Prompt/workflow/eval approvals
  services/
    api-gateway/              # FastAPI gateway
    agent-runtime/            # AIP tool orchestration adapters
    optimization-service/     # QUBO/QAOA/classical baselines
    feedback-service/         # Feedback and outcome labels
    improvement-service/      # Candidate generation + eval pipeline
  packages/
    ontology-client/          # Foundry/Gotham typed client
    policy-client/            # OPA/ABAC helper
    telemetry/                # OpenTelemetry wrappers
  infra/
    apollo/                   # Product manifests and canary rules
    policy/                   # Rego bundles
    sql/                      # Ontology/lakehouse DDL
```

### Event Topics

```yaml
topics:
  artemis.telemetry.raw:
    partitions: [facility_id, classification]
  artemis.alert.created:
    partitions: [mission_id, severity]
  artemis.workflow.completed:
    partitions: [workflow_name, mission_id]
  artemis.feedback.signal:
    partitions: [mission_id, signal_type]
  artemis.optimization.requested:
    partitions: [facility_id, optimizer_type]
  artemis.optimization.completed:
    partitions: [facility_id, run_id]
  artemis.improvement.candidate:
    partitions: [candidate_type, risk_level]
```

---

## Security and Governance

### Controls

- **Need-to-know ABAC/ReBAC**: subject attributes, entity relationships, mission membership, purpose-of-use, clearance, compartments, and coalition caveats.
- **Row/column/entity permissions**: enforced before display, retrieval, prompts, embeddings, tools, and exports.
- **Coalition boundaries**: releasability tags flow from source records into derived entities, summaries, vectors, and recommendations.
- **Zero-trust execution**: every service authenticates every call; tool invocations include signed user/agent context.
- **Immutable provenance**: source hash, transform version, prompt version, model ID, policy version, and approval record are logged.
- **Prompt governance**: prompt packs are signed artifacts with owners, eval scorecards, red-team results, and Apollo rollback plans.
- **Policy-as-code**: Rego bundles are reviewed, tested, signed, and deployed through Apollo.

### Policy Example

```rego
package artemis.authz

default allow := false

allow if {
  input.subject.clearance_level >= input.object.classification_level
  every c in input.object.compartments { c in input.subject.compartments }
  input.request.mission_id in input.subject.missions
  input.request.purpose in {"investigation", "optimization", "approved_operations"}
  not blocked_by_coalition_boundary
}

blocked_by_coalition_boundary if {
  input.object.coalition_scope == "NOFORN"
  input.subject.coalition != "US_ONLY"
}

requires_human_approval if {
  input.action in {"actuator.apply_setpoints", "case.release_product", "governance.promote_prompt"}
}
```

---

## Code Examples

### FastAPI Gateway With Policy Preflight

```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Any

app = FastAPI(title="ClearGlassInc Artemis API")

class UserContext(BaseModel):
    user_id: str
    clearance_level: int
    compartments: list[str]
    missions: list[UUID]
    coalition: str

class QuantumOptimizeRequest(BaseModel):
    mission_id: UUID
    facility_id: UUID
    horizon_minutes: int = Field(ge=5, le=240)
    optimizer: str = Field(pattern="^(classical_mip|or_tools|qaoa_sim|qaoa_qpu)$")
    max_latency_ms: int = Field(default=30000, ge=1000, le=300000)

async def current_user() -> UserContext:
    return UserContext(
        user_id="operator-123",
        clearance_level=3,
        compartments=["ARTEMIS", "FACILITY_OPT"],
        missions=[],
        coalition="US_ONLY",
    )

async def authorize(user: UserContext, action: str, resource: dict[str, Any]) -> None:
    allowed = await opa_check({"subject": user.model_dump(), "action": action, "object": resource})
    if not allowed:
        raise HTTPException(status_code=403, detail="Policy denied")

async def opa_check(payload: dict[str, Any]) -> bool:
    return "ARTEMIS" in payload["subject"]["compartments"]

@app.post("/v1/optimization/quantum")
async def request_quantum_optimization(req: QuantumOptimizeRequest, user: UserContext = Depends(current_user)):
    await authorize(user, "optimization.run_qaoa", {
        "facility_id": str(req.facility_id),
        "mission_id": str(req.mission_id),
        "classification_level": 3,
        "compartments": ["ARTEMIS", "FACILITY_OPT"],
        "coalition_scope": "US_ONLY",
    })
    run_id = await enqueue_optimization(req, requested_by=user.user_id)
    return {"run_id": str(run_id), "state": "queued", "approval_required_for_actuation": True}
```

### QUBO Builder for HVAC + SPD/PDLC Glass

```python
from dataclasses import dataclass
from itertools import combinations
from typing import Dict, Tuple

Binary = str
Qubo = Dict[Tuple[Binary, Binary], float]

@dataclass(frozen=True)
class ZoneInput:
    zone_id: str
    thermal_load_kw: float
    current_temp_c: float
    target_temp_c: float
    occupancy: int
    solar_gain_w_m2: float

@dataclass(frozen=True)
class DeviceCost:
    airflow_energy: float
    glass_switch_cost: float
    comfort_penalty: float
    wear_penalty: float

def add(Q: Qubo, a: Binary, b: Binary, w: float) -> None:
    key = tuple(sorted((a, b)))
    Q[key] = Q.get(key, 0.0) + w

def build_hvac_glass_qubo(zones: list[ZoneInput], costs: DeviceCost) -> Qubo:
    """Builds a compact QUBO where each zone has binary airflow boost and binary glass darken decisions."""
    Q: Qubo = {}

    for z in zones:
        air = f"air_boost[{z.zone_id}]"
        tint = f"glass_darken[{z.zone_id}]"
        temp_error = abs(z.current_temp_c - z.target_temp_c)
        occupied_weight = 1.0 + min(z.occupancy, 20) / 20.0

        add(Q, air, air, costs.airflow_energy + costs.wear_penalty)
        add(Q, tint, tint, costs.glass_switch_cost)

        # Rewards encoded as negative costs.
        add(Q, air, air, -costs.comfort_penalty * temp_error * occupied_weight)
        add(Q, tint, tint, -0.002 * z.solar_gain_w_m2 * occupied_weight)

        # Coupling: tinting can reduce cooling load, so simultaneous air boost and tint may be redundant.
        add(Q, air, tint, 0.35 * costs.airflow_energy)

    # Building-level peak-load coupling discourages all zones boosting simultaneously.
    for za, zb in combinations(zones, 2):
        add(Q, f"air_boost[{za.zone_id}]", f"air_boost[{zb.zone_id}]", 0.12)

    return Q
```

### QAOA Runner Skeleton

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

@dataclass
class QaoaResult:
    bitstring: str
    objective_value: float
    samples: dict[str, int]
    backend: str
    depth_p: int
    approximation_ratio: float | None

class QaoaOptimizer:
    def __init__(self, backend_name: str = "simulator", depth_p: int = 2, shots: int = 2048):
        self.backend_name = backend_name
        self.depth_p = depth_p
        self.shots = shots

    def solve(self, qubo: Mapping[tuple[str, str], float], classical_baseline: float | None = None) -> QaoaResult:
        # Production implementation maps QUBO → Ising Hamiltonian → QAOA ansatz.
        # Simulator path uses local CPU/GPU. QPU path submits through IBM Quantum adapter.
        variables = sorted({v for pair in qubo for v in pair})
        best_bits = "0" * len(variables)
        best_value = self._score(best_bits, variables, qubo)

        # Placeholder deterministic local search seed; replace with Qiskit QAOA/Sampler in runtime.
        for i in range(1 << min(len(variables), 16)):
            bits = format(i, f"0{len(variables)}b")
            value = self._score(bits, variables, qubo)
            if value < best_value:
                best_bits, best_value = bits, value

        ratio = None if classical_baseline in (None, 0) else best_value / classical_baseline
        return QaoaResult(best_bits, best_value, {best_bits: self.shots}, self.backend_name, self.depth_p, ratio)

    @staticmethod
    def _score(bits: str, variables: list[str], qubo: Mapping[tuple[str, str], float]) -> float:
        x = dict(zip(variables, [int(b) for b in bits], strict=True))
        return sum(weight * x[a] * x[b] for (a, b), weight in qubo.items())
```

### Workflow State Machine

```python
from enum import Enum
from pydantic import BaseModel

class WorkflowState(str, Enum):
    RECEIVED = "received"
    TRIAGED = "triaged"
    ENRICHED = "enriched"
    RECOMMENDED = "recommended"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EXECUTED = "executed"
    REJECTED = "rejected"
    LEARNED = "learned"

class WorkflowRun(BaseModel):
    run_id: str
    state: WorkflowState
    mission_id: str
    risk_level: str
    recommendation: dict | None = None

APPROVAL_STATES = {WorkflowState.PENDING_APPROVAL}

async def advance(run: WorkflowRun, event: str, actor: str) -> WorkflowRun:
    if run.state == WorkflowState.RECEIVED and event == "triage_completed":
        run.state = WorkflowState.TRIAGED
    elif run.state == WorkflowState.TRIAGED and event == "enrichment_completed":
        run.state = WorkflowState.ENRICHED
    elif run.state == WorkflowState.ENRICHED and event == "recommendation_ready":
        run.state = WorkflowState.PENDING_APPROVAL if run.risk_level in {"medium", "high"} else WorkflowState.RECOMMENDED
    elif run.state == WorkflowState.PENDING_APPROVAL and event == "operator_approved":
        run.state = WorkflowState.APPROVED
    elif run.state == WorkflowState.PENDING_APPROVAL and event == "operator_rejected":
        run.state = WorkflowState.REJECTED
    elif run.state == WorkflowState.APPROVED and event == "execution_completed":
        run.state = WorkflowState.EXECUTED
    elif run.state in {WorkflowState.EXECUTED, WorkflowState.REJECTED} and event == "feedback_captured":
        run.state = WorkflowState.LEARNED
    else:
        raise ValueError(f"invalid transition from {run.state} on {event}")

    await append_audit_log(run.run_id, actor, event, run.state.value)
    return run
```

### Eval Pipeline for Prompt, Workflow, and Optimizer Candidates

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class EvalCase:
    case_id: str
    input_payload: dict
    expected: dict
    policy_context: dict

@dataclass(frozen=True)
class EvalScore:
    precision: float
    recall: float
    latency_ms: int
    policy_violations: int
    operator_edit_distance: float

async def run_candidate_eval(candidate_version: str, eval_cases: list[EvalCase]) -> EvalScore:
    tp = fp = fn = violations = 0
    total_latency = 0
    total_edit_distance = 0.0

    for case in eval_cases:
        result = await execute_shadow_candidate(candidate_version, case.input_payload)
        total_latency += result["latency_ms"]
        violations += int(not await opa_check({"subject": case.policy_context, "object": result, "action": "shadow_eval"}))
        tp += result["metrics"]["tp"]
        fp += result["metrics"]["fp"]
        fn += result["metrics"]["fn"]
        total_edit_distance += result["metrics"].get("operator_edit_distance", 0.0)

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return EvalScore(
        precision=precision,
        recall=recall,
        latency_ms=total_latency // max(len(eval_cases), 1),
        policy_violations=violations,
        operator_edit_distance=total_edit_distance / max(len(eval_cases), 1),
    )

def promotion_allowed(score: EvalScore, baseline: EvalScore) -> bool:
    return (
        score.policy_violations == 0
        and score.precision >= baseline.precision + 0.02
        and score.recall >= baseline.recall - 0.01
        and score.latency_ms <= int(baseline.latency_ms * 1.15)
        and score.operator_edit_distance <= baseline.operator_edit_distance
    )
```

### TypeScript Quantum Recommendation Panel

```tsx
type QuantumRecommendation = {
  runId: string;
  optimizer: "classical_mip" | "or_tools" | "qaoa_sim" | "qaoa_qpu";
  projectedEnergySavingsPct: number;
  comfortViolationMinutes: number;
  approvalState: "draft" | "pending_review" | "approved" | "rejected";
  setpoints: Array<{ zoneId: string; airflow: "normal" | "boost"; tintLevel: number }>;
};

export function QuantumRecommendationPanel({ rec }: { rec: QuantumRecommendation }) {
  return (
    <section className="rounded-2xl border border-cyan-300/30 bg-slate-950/80 p-5 shadow-2xl">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-cyan-300">ClearGlassInc Artemis</p>
          <h2 className="text-xl font-semibold text-white">Quantum Recommendation</h2>
        </div>
        <span className="rounded-full bg-cyan-400/10 px-3 py-1 text-sm text-cyan-200">{rec.optimizer}</span>
      </header>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <Metric label="Energy savings" value={`${rec.projectedEnergySavingsPct.toFixed(1)}%`} />
        <Metric label="Comfort violations" value={`${rec.comfortViolationMinutes} min`} />
      </dl>
      <ul className="mt-4 space-y-2">
        {rec.setpoints.map((s) => (
          <li key={s.zoneId} className="flex justify-between rounded-lg bg-white/5 px-3 py-2 text-slate-200">
            <span>{s.zoneId}</span>
            <span>airflow: {s.airflow} · tint: {s.tintLevel}</span>
          </li>
        ))}
      </ul>
      <button className="mt-5 w-full rounded-xl bg-cyan-300 px-4 py-2 font-semibold text-slate-950">
        Submit for Human Approval
      </button>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white/5 p-3">
      <dt className="text-slate-400">{label}</dt>
      <dd className="text-lg font-semibold text-white">{value}</dd>
    </div>
  );
}
```

---

## Scenario Walkthrough

1. **Live event enters**: a weather spike, occupancy surge, and solar-gain anomaly arrive from building telemetry. Foundry pipelines normalize the events into `hvac_zone_state` and `smart_glass_state` records with lineage.
2. **Triage**: an AIP triage agent detects projected thermal discomfort and energy spike risk in three zones. It opens a low-risk optimization workflow, not an actuator command.
3. **Ontology enrichment**: the enrichment agent pulls zone history, glass panel state, chiller constraints, tariff windows, maintenance limits, and mission occupancy priority.
4. **QUBO formation**: the optimization service converts airflow and tint choices into binary variables, adds energy, comfort, glare, equipment-wear, and peak-load coupling terms, and stores the problem hash.
5. **Hybrid solve**: Artemis runs OR-Tools/classical baseline and QAOA simulator immediately. If policy, latency, and queue conditions permit, it also submits a QAOA QPU job through the quantum-centric compute adapter.
6. **Recommendation**: the recommendation agent compares QAOA against classical baselines. It only labels the result quantum-advantaged if the benchmark evidence beats the accepted classical baseline under the same constraints.
7. **Approval**: the operator sees the recommendation panel with projected energy savings, comfort impact, confidence, baseline comparison, and lineage. The operator approves, edits, or rejects.
8. **Execution**: if approved, Apollo-managed runtime calls the actuator gateway with signed policy context; setpoints are applied gradually with safety bounds.
9. **Outcome monitoring**: energy use, comfort complaints, thermal response, and actuator wear are measured against the prediction.
10. **Learning**: feedback signals generate eval examples. If QAOA underperformed, the improvement service may propose QUBO coefficient changes or different QAOA initialization. The governance board sees the diff, eval results, risk assessment, and rollback plan before any promotion.
11. **Safe evolution**: approved improvements deploy through Apollo canary channels; drift monitors compare live behavior to baselines and trigger automatic rollback on policy violation, quality regression, or latency breach.

---

## Recommended Roadmap Choice

For the immediate ClearGlassInc roadmap, the strongest sequence is:

1. **Option B first — QUBO formulation**: lock the mathematical contract for HVAC + SPD/PDLC optimization and define measurable baselines.
2. **Option A second — runnable QAOA code**: implement simulator and IBM Quantum adapters against the stable QUBO schema.
3. **Option C third — Next.js recommendation panel**: integrate only after recommendations have stable fields, metrics, confidence, and approval semantics.

This sequence keeps the UI honest: the command surface displays validated optimization outputs rather than speculative quantum theater.
