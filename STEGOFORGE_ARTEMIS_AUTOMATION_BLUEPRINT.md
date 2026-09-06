# ClearGlassInc Artemis — STEGOFORGE Autonomous Intelligence System Blueprint

## System Architecture

### Mission Objective
Build a secure, coalition-aware, low-latency system that reproduces and operationalizes the STEGOFORGE capabilities shown in the screenshot (encode/decode/detect/scan/encrypt/diff plus stealth forensic workflows), while embedding a governed self-improvement loop on Palantir Gotham, Foundry, AIP, and Apollo.

### End-to-End Full-Stack Topology

```text
[React Mission UI + Terminal Emulator + Command Palette]
      |
[API Gateway (mTLS, JWT, OPA PDP, request signing)]
      |
[Python Service Mesh]
  - command-service
  - pipeline-orchestrator
  - stego-forensics-service
  - crypto-service (AES-256-GCM, KMS envelope keys)
  - mission-case-service
  - feedback-service
      |
[Event Fabric: Kafka/Pulsar + Redis Streams]
      |
[Foundry]
  - Batch + streaming transforms
  - Ontology + object lineage
  - Feature views and mission data products
      |
[AIP]
  - Copilots (Analyst/Commander)
  - Agent runtime + tool contracts
  - Eval registry + prompt/workflow registry
  - Model router + guarded tool calling
      |
[Gotham]
  - Investigations, timelines, link analysis, case graph
      |
[Apollo]
  - Progressive deploy, policy bundles, rollback, drift gates
```

### Layer Responsibilities
- **Frontend layer**: real-time terminal panel and explainability panel (lineage, confidence, approvals).
- **Backend layer**: deterministic Python services for file analysis, cryptographic operations, and case workflow state.
- **Data layer**: lakehouse + graph + vector + OLTP split.
- **Ontology layer**: mission entities/relations with confidence, temporal validity, compartment tags.
- **AI orchestration**: model routing, tool-use agents, approval-gated operational actions.
- **Policy layer**: ABAC/RBAC + coalition boundaries + entity-level constraints.
- **Observability layer**: trace every tool call, policy decision, and recommendation outcome.
- **Deployment layer**: Apollo ring rollout with automatic rollback on precision/trust degradation.

---

## Data and Ontology

### Core Ontology Objects (Foundry Ontology)

```yaml
Entity:
  Signal:
    fields: [signal_id, source_type, ts_utc, confidence, classification, mission_id]
  MediaArtifact:
    fields: [artifact_id, mime_type, hash_sha256, size_bytes, source_uri]
  StegoAnalysis:
    fields: [analysis_id, artifact_id, detector_family, score, hidden_payload_estimate]
  CryptoEnvelope:
    fields: [envelope_id, alg, key_ref, nonce_ref, aad_ref, created_at]
  Recommendation:
    fields: [recommendation_id, mission_id, risk_level, rationale, status]
  ActionPackage:
    fields: [action_pkg_id, recommendation_id, required_approvers, status]
  OperatorFeedback:
    fields: [feedback_id, recommendation_id, disposition, correction, outcome]

Relationship:
  - SIGNAL_GENERATED_ARTIFACT (Signal -> MediaArtifact)
  - ARTIFACT_ANALYZED_AS (MediaArtifact -> StegoAnalysis)
  - RECOMMENDS_ACTION (Recommendation -> ActionPackage)
  - FEEDBACK_ON (OperatorFeedback -> Recommendation)
  - LINKED_TO_CASE (Signal|Recommendation|ActionPackage -> Case)
```

### Permissioned Attributes
- `classification`, `releasability`, `need_to_know_tags`, `compartment`, `coalition_scope`.
- AI agents receive scoped ontology views (no global unrestricted graph visibility).

### Temporal + Lineage Model
- All entities use bitemporal semantics:
  - `valid_from/valid_to` (when true in mission world)
  - `observed_at/ingested_at` (when system learned)
- Every transform writes lineage:
  - `source_dataset_id`, `pipeline_id`, `transform_hash`, `operator_override_ref`.

### SQL DDL (Representative)

```sql
CREATE TABLE stego_analysis (
  analysis_id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  detector_family TEXT NOT NULL,
  detector_version TEXT NOT NULL,
  score NUMERIC NOT NULL,
  hidden_payload_estimate_bytes BIGINT,
  confidence NUMERIC NOT NULL,
  mission_id TEXT NOT NULL,
  classification TEXT NOT NULL,
  releasability JSONB NOT NULL,
  need_to_know_tags JSONB NOT NULL,
  lineage_ref TEXT NOT NULL,
  valid_from TIMESTAMPTZ,
  valid_to TIMESTAMPTZ,
  observed_at TIMESTAMPTZ NOT NULL,
  ingested_at TIMESTAMPTZ NOT NULL
);
```

---

## AI and Agent Design

### Copilots
1. **Analyst Copilot**: anomaly explanation, detector confidence decomposition, suggested next commands.
2. **Commander Copilot**: response options with mission impact/latency/collateral risk.
3. **Policy Copilot**: explains why an action is blocked/allowed.

### Agent Graph (AIP)

```text
IngestAgent -> TriageAgent -> EnrichmentAgent -> CorrelationAgent ->
StegoForensicsAgent -> RecommenderAgent -> ApprovalGateAgent -> ExecutionAgent
```

### Tool Contracts
Agents can only invoke registered, typed tools:
- `tool.scan_artifact`
- `tool.detect_stego_patterns`
- `tool.decode_candidate_payload`
- `tool.encrypt_payload_aes_gcm`
- `tool.diff_original_vs_stego`
- `tool.open_case`
- `tool.propose_action_package`
- `tool.request_human_approval`

### Tool-Use Policy
- Any `open_case`, `propose_action_package`, or mission impact action requires signed policy check + human approval state.
- Model output is non-authoritative; tool responses are authoritative.

---

## Self-Improvement Loop

### Signals Captured
- Command usage patterns (`encode`, `decode`, `detect`, `scan`, `encrypt`, `diff`)
- Operator edits/rejections
- Downstream mission outcomes (success/escalation/false alarm)
- Runtime telemetry (latency/cost/model-confidence drift)

### Controlled Optimization Pipeline

```text
feedback_events -> eval_dataset_builder -> offline_eval ->
candidate_prompt/workflow/router changes -> shadow run ->
review_board approval -> Apollo canary -> promotion/rollback
```

### Guardrails
- No autonomous policy mutation.
- No autonomous approval threshold changes.
- No deployment unless:
  - precision >= baseline - 1%
  - recall >= baseline - 2%
  - trust score non-decreasing
  - p95 latency within SLA envelope

### Drift + Rollback
- Drift monitors compare cohort metrics by mission type/classification zone.
- Apollo rollback trigger if 3 consecutive windows violate SLO.

---

## Full-Stack Implementation

### Web UI (TypeScript/React)
- Terminal-like command center inspired by screenshot.
- Panels:
  - `SystemInitLog`
  - `StegoForgeCommandMenu`
  - `LiveDataStreams`
  - `ApprovalQueue`
  - `CaseGraphViewer`

```tsx
// ui/src/components/CommandMenu.tsx
const COMMANDS = ["encode", "decode", "detect", "scan", "encrypt", "diff"] as const;

export function CommandMenu({ onRun }: { onRun: (cmd: string) => Promise<void> }) {
  return (
    <div className="font-mono text-cyan-300">
      {COMMANDS.map((cmd, i) => (
        <button key={cmd} onClick={() => onRun(cmd)} className="block hover:text-fuchsia-300">
          {i + 1}. {cmd.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
```

### API Gateway
- Endpoints:
  - `POST /v1/commands/{encode|decode|detect|scan|encrypt|diff}`
  - `POST /v1/recommendations/{id}/decision`
  - `GET /v1/cases/{case_id}/timeline`

### Python Backend (FastAPI + asyncio)

```python
# services/command_service/api.py
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from .policy import authorize
from .executor import dispatch_command

app = FastAPI(title="ClearGlassInc Artemis STEGOFORGE Command Service")

class CommandRequest(BaseModel):
    mission_id: str
    artifact_id: str
    params: dict

@app.post("/v1/commands/{command}")
async def run_command(command: str, req: CommandRequest, user=Depends(authorize)):
    allowed = {"encode", "decode", "detect", "scan", "encrypt", "diff"}
    if command not in allowed:
        raise HTTPException(400, "Unsupported command")
    result = await dispatch_command(command=command, req=req.model_dump(), user=user)
    return {"status": "ok", "command": command, "result": result}
```

### Command Execution + Event Emission

```python
# services/command_service/executor.py
from artemis.events import publish
from artemis.stego import detect, decode, encode, diff_heatmap
from artemis.crypto import encrypt_aes_256_gcm

async def dispatch_command(command: str, req: dict, user: dict) -> dict:
    artifact_id = req["artifact_id"]
    params = req.get("params", {})

    if command == "detect":
        out = await detect(artifact_id, detector_profile=params.get("profile", "default"))
    elif command == "decode":
        out = await decode(artifact_id, key_ref=params.get("key_ref"))
    elif command == "encode":
        out = await encode(artifact_id, payload_ref=params["payload_ref"], strategy=params.get("strategy", "adaptive"))
    elif command == "encrypt":
        out = await encrypt_aes_256_gcm(payload_ref=params["payload_ref"], aad=params.get("aad", ""))
    elif command == "diff":
        out = await diff_heatmap(artifact_id, params["candidate_artifact_id"])
    else:  # scan
        out = {"scan": "queued", "artifact_id": artifact_id}

    await publish("artemis.commands.executed", {
        "mission_id": req["mission_id"],
        "artifact_id": artifact_id,
        "command": command,
        "result": out,
        "operator_id": user["sub"],
    })
    return out
```

### Workflow State Machine

```python
# services/workflow/state_machine.py
from enum import Enum

class RecState(str, Enum):
    PROPOSED = "PROPOSED"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"

VALID = {
    RecState.PROPOSED: {RecState.REVIEW},
    RecState.REVIEW: {RecState.APPROVED, RecState.REJECTED},
    RecState.APPROVED: {RecState.EXECUTED},
    RecState.REJECTED: set(),
    RecState.EXECUTED: set(),
}

def transition(curr: RecState, nxt: RecState) -> RecState:
    if nxt not in VALID[curr]:
        raise ValueError(f"Invalid transition: {curr} -> {nxt}")
    return nxt
```

### Policy-as-Code (Rego)

```rego
package artemis.pdp

default allow = false

allow {
  input.user.clearance >= input.resource.classification
  input.user.mission_id == input.resource.mission_id
  input.user.coalition[_] == input.resource.releasability[_]
  not compartment_blocked
}

compartment_blocked {
  some tag
  input.resource.need_to_know_tags[tag]
  not input.user.entitlements[tag]
}
```

### Eval Pipeline (Python)

```python
# services/evals/pipeline.py
from dataclasses import dataclass

@dataclass
class Metrics:
    precision: float
    recall: float
    p95_latency_ms: int
    operator_trust: float


def can_promote(candidate: Metrics, baseline: Metrics) -> bool:
    return (
        candidate.precision >= baseline.precision - 0.01 and
        candidate.recall >= baseline.recall - 0.02 and
        candidate.p95_latency_ms <= int(baseline.p95_latency_ms * 1.10) and
        candidate.operator_trust >= baseline.operator_trust
    )
```

### Streaming + Feedback Schema

```sql
CREATE TABLE operator_feedback (
  feedback_id TEXT PRIMARY KEY,
  mission_id TEXT NOT NULL,
  recommendation_id TEXT NOT NULL,
  operator_id TEXT NOT NULL,
  disposition TEXT NOT NULL,      -- approve/reject/edit
  correction JSONB,
  outcome_label TEXT,             -- tp/fp/fn/tn/mission_success/mission_failure
  prompt_version TEXT NOT NULL,
  workflow_version TEXT NOT NULL,
  model_route_version TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);
```

---

## Security and Governance

### Zero-Trust + Need-to-Know
- mTLS for all service hops.
- SPIFFE/SPIRE identities for workloads.
- OPA sidecar enforcement at ingress + service boundary.
- Data access filtered by entity-level ACL and coalition tags.

### Immutable Provenance
- Hash-chained audit log entries:
  - request hash
  - tool invocation hash
  - policy decision hash
  - recommendation hash
  - approval decision hash

### Model/Prompt Governance
- Versioned registries:
  - `prompt_registry`
  - `workflow_registry`
  - `model_router_registry`
- Change workflow:
  1. Proposed by eval pipeline.
  2. Reviewed by Ops + Security + Mission Lead.
  3. Signed and released via Apollo canary.

---

## Code Examples (Additional Critical Paths)

```python
# services/agents/recommender.py
async def build_recommendation(context: dict, tools, policy) -> dict:
    candidates = await tools.correlate(context)
    ranked = sorted(candidates, key=lambda x: x["risk_delta"], reverse=True)
    top = ranked[0]

    rec = {
        "mission_id": context["mission_id"],
        "rationale": top["explanation"],
        "recommended_action": top["action"],
        "evidence": top["evidence_ids"],
    }

    decision = policy.precheck(rec)
    rec["policy_precheck"] = decision
    return rec
```

```python
# services/approval/api.py
@app.post("/v1/recommendations/{rec_id}/decision")
async def decision(rec_id: str, payload: DecisionIn, user=Depends(authorize)):
    if payload.decision == "APPROVE" and "mission_commander" not in user["roles"]:
        raise HTTPException(403, "Commander role required")
    updated = await set_decision(rec_id, payload.decision, user["sub"], payload.reason)
    await publish("artemis.approvals.decisions", updated)
    return updated
```

```python
# services/improvement/proposer.py
async def propose_upgrade(eval_metrics, baseline_metrics, versions):
    if not can_promote(eval_metrics, baseline_metrics):
        return {"status": "rejected", "reason": "metrics_gate_failed"}

    return {
        "status": "pending_human_review",
        "candidate": {
            "prompt_version": versions["prompt_candidate"],
            "workflow_version": versions["workflow_candidate"],
            "router_version": versions["router_candidate"],
        }
    }
```

---

## Scenario Walkthrough (Cinematic + Operationally Precise)

1. **Event intake (T+00s)**: A maritime image artifact enters `signals.raw` with compartmented coalition tags.
2. **Triage (T+03s)**: TriageAgent scores anomaly 0.81 and opens `Case C-1129` in Gotham.
3. **Stego detect (T+06s)**: StegoForensicsAgent runs `detect` + `scan`; hidden payload likelihood 0.74.
4. **Decode/encrypt workflow (T+09s)**: Candidate payload is decoded in restricted enclave, then re-encrypted with AES-256-GCM envelope key for controlled sharing.
5. **Recommendation (T+12s)**: RecommenderAgent drafts ActionPackage `AP-778` (surveillance redirect + partner notification).
6. **Approval gate (T+20s)**: Commander approves surveillance redirect, rejects partner notification due to releasability constraints.
7. **Execution (T+30s)**: Approved action executes; all events appended to immutable audit chain.
8. **Outcome (T+8h)**: Mission result marked successful; rejected notification validated as correct non-escalation.
9. **Learning loop (T+24h)**:
   - Feedback joins eval corpus.
   - Candidate prompt reduces partner-notification bias when confidence < 0.80 and corroboration depth < 2.
   - Human board approves change.
   - Apollo deploys canary (10% missions), then promotes after trust + precision pass.

Result: **ClearGlassInc Artemis gets better over time through governed optimization, never uncontrolled autonomy**.
