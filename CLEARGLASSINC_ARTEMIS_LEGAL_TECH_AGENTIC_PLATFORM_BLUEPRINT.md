# ClearGlassInc Artemis — Self-Evolving Legal-Tech Intelligence Platform

## System Architecture

ClearGlassInc Artemis is a secure, coalition-aware, multi-domain intelligence platform for legal-tech automation and mission-critical investigations. It uses **Palantir Gotham** for operational intelligence, investigations, entity tracking, case timelines, and link analysis; **Palantir Foundry** for ingestion, pipelines, ontology, permissions, and application logic; **Palantir AIP** for governed copilots, tool-using agents, evaluations, and workflow automation; and **Palantir Apollo** for signed deployment, runtime control, canary promotion, rollback, and policy distribution.

The initial demo-ready MVP is a two-agent legal automation workflow: an **OSINT Intake Agent** gathers and normalizes public evidence, while a **Document Processing Agent** extracts clauses, facts, parties, obligations, risk signals, and citations. A deterministic **Case Orchestrator** reconciles their outputs, enforces policy, asks for human approval, and writes governed ontology updates only when confidence and permission thresholds are satisfied.

```mermaid
flowchart LR
  subgraph UI[Frontend Surfaces]
    analyst[Analyst Workbench]
    commander[Commander Console]
    legal[Legal Evidence Review]
    governance[AI Governance Console]
  end

  subgraph API[API and Backend]
    gateway[API Gateway / BFF]
    auth[OIDC + mTLS + Mission Context]
    policy[Policy Enforcement Point]
    cases[Case Service]
    docs[Document Service]
    workflow[Workflow Orchestrator]
    feedback[Feedback Service]
  end

  subgraph DATA[Foundry Data Plane]
    bronze[Bronze: Raw OSINT, filings, docs, logs]
    silver[Silver: Normalized entities and documents]
    gold[Gold: Mission-ready intelligence products]
    ontology[Foundry Ontology Objects, Links, Actions]
  end

  subgraph OPS[Gotham Operations]
    graph[Entity Graph]
    timelines[Case Timelines]
    watchlists[Watchlists]
    investigations[Investigations]
  end

  subgraph AIP[AIP Orchestration]
    osint[OSINT Intake Agent]
    docagent[Document Processing Agent]
    triage[Triage and Correlation Agent]
    summarizer[Intel Product Agent]
    router[Model Router]
    evals[Eval Harness]
    registry[Prompt / Workflow Registry]
  end

  subgraph GOV[Governance, Observability, Deployment]
    opa[OPA Policy-as-Code]
    audit[Immutable Audit Ledger]
    telemetry[OpenTelemetry + Eval Dashboards]
    apollo[Apollo Signed Releases / Rollback]
  end

  UI --> gateway --> auth --> policy
  policy --> cases --> ontology
  policy --> docs --> bronze
  policy --> workflow --> osint
  workflow --> docagent --> triage --> summarizer
  osint --> silver --> ontology --> graph
  ontology --> timelines
  ontology --> investigations
  registry --> apollo
  evals --> registry
  feedback --> evals
  opa --> policy
  gateway --> audit
  telemetry --> apollo
```

### Layer responsibilities

| Layer | Implementation detail |
|---|---|
| Frontend | React/TypeScript UI with alert queue, document viewer, extracted-clause comparison, entity graph, timeline, approval inbox, and eval dashboard. |
| Backend | Python FastAPI services for case intake, document processing, ontology queries, feedback capture, agent workflow state, and approval gates. |
| Data | Foundry bronze/silver/gold datasets with lineage, quality checks, temporal snapshots, dedupe, and mission-ready feature tables. |
| Ontology | Objects, links, actions, confidence, lineage, temporal validity, coalition markings, legal privileges, and entity-level permissions. |
| AI orchestration | AIP agents with strict tool schemas, model routing, retrieval controls, eval capture, prompt versioning, and deterministic workflow checkpoints. |
| Policy | OPA/Rego plus Foundry/Gotham object permissions for need-to-know, row, column, edge, action, prompt, model, and coalition controls. |
| Observability | OpenTelemetry traces, structured logs, agent spans, quality metrics, latency budgets, drift monitors, and immutable audit events. |
| Deployment | Apollo promotion rings, signed prompt/workflow/model-router bundles, canaries, kill switches, rollback, and runtime config locks. |

## Data and Ontology

The ontology is the contract between humans, agents, pipelines, and policy. AI agents do not operate on arbitrary database rows; they operate on governed ontology objects and actions with mission context and permission checks.

```yaml
ontology: ClearGlassIncArtemisLegalIntel
version: 1.0.0
objects:
  Mission:
    key: mission_id
    fields: [name, priority, objective, status, coalition_scope, classification, created_at]
  LegalCase:
    key: case_id
    fields: [mission_id, title, jurisdiction, matter_type, status, owner_user_id, privilege_level]
  Party:
    key: party_id
    fields: [party_type, legal_name, aliases, jurisdiction, risk_score, confidence]
  Document:
    key: document_id
    fields: [case_id, source_uri, sha256, doc_type, privilege_level, received_at, lineage_refs]
  Clause:
    key: clause_id
    fields: [document_id, clause_type, text_span_ref, normalized_obligation, risk_level, confidence]
  EvidenceItem:
    key: evidence_id
    fields: [source_system, source_uri, collected_at, reliability, admissibility_flag, raw_ref, hash]
  Event:
    key: event_id
    fields: [event_type, ts_event, ts_ingest, source_system, normalized_payload_hash, confidence]
  Recommendation:
    key: rec_id
    fields: [case_id, action_type, rationale, risk_score, confidence, status, prompt_version, workflow_version, model_route]
  ApprovalDecision:
    key: decision_id
    fields: [rec_id, approver_user_id, decision, reason, policy_version, decided_at]
  FeedbackSignal:
    key: feedback_id
    fields: [source, target_type, target_id, label, correction_json, confidence_delta, created_at]
links:
  PartyInCase: [Party, LegalCase]
  DocumentInCase: [Document, LegalCase]
  ClauseInDocument: [Clause, Document]
  EvidenceSupportsRecommendation: [EvidenceItem, Recommendation]
  EventMentionsParty: [Event, Party]
  RecommendationRequiresApproval: [Recommendation, ApprovalDecision]
actions:
  open_case:
    requires: [case:create, mission:write]
  add_evidence:
    requires: [case:write, evidence:create]
  propose_recommendation:
    requires: [aip:recommend, case:read]
  approve_action_package:
    requires: [action:approve, commander_or_counsel]
```

Ontology-driven behavior:

- **Human workflows** use `LegalCase`, `Document`, `Clause`, `EvidenceItem`, and `Recommendation` objects to review evidence, compare extracted facts, approve action packages, and trace every assertion back to source material.
- **AI agents** receive object-scoped capabilities. For example, an agent may read `Document` text spans and create draft `Clause` objects, but cannot approve `Recommendation` objects.
- **Temporal state** is bitemporal: each object tracks event time, ingest time, and correction time so analysts can replay what the system knew when a recommendation was made.
- **Confidence and lineage** are first-class fields. Every extracted obligation, OSINT fact, and action recommendation carries confidence, evidence references, model version, prompt version, and workflow version.
- **Permissions** are enforced at object, field, edge, action, and coalition level. Privileged legal documents can be visible to counsel only while nonprivileged metadata is visible to mission analysts.

## AI and Agent Design

### Copilots

- **Analyst Copilot**: answers mission-scoped questions, explains entity links, drafts summaries, compares documents, and identifies missing evidence.
- **Commander Copilot**: converts validated findings into risk posture, action options, operational constraints, and approval-ready decision briefs.
- **Counsel Copilot**: reviews extracted legal obligations, privilege markings, jurisdictional issues, citation quality, and escalation requirements.
- **Governance Copilot**: summarizes eval regressions, prompt diffs, workflow changes, release risk, and rollback recommendations.

### Multi-agent workflow

1. **OSINT Intake Agent**
   - Searches allowlisted public and paid sources.
   - Normalizes entities, domains, corporate filings, adverse media, sanctions references, and source reliability.
   - Emits `EvidenceItem`, `Party`, and `Event` candidates.
2. **Document Processing Agent**
   - Parses PDFs, DOCX files, emails, exhibits, contracts, and filings.
   - Extracts parties, dates, obligations, indemnities, termination rights, governing law, risk clauses, and citations.
   - Emits `Document`, `Clause`, and fact candidates.
3. **Triage and Correlation Agent**
   - Joins OSINT facts with document facts through ontology links.
   - Deduplicates parties, scores contradictions, and creates draft alerts.
4. **Intel Product Agent**
   - Produces an evidence-backed brief with citations, uncertainty, assumptions, and recommended next actions.
5. **Human Approval Gate**
   - Required for case creation from sensitive data, external notifications, operational recommendations, workflow promotions, prompt changes, and model-route changes.

### Error-rate target

For the MVP, the orchestrator refuses automatic merge when confidence is low or agents disagree. A practical target is **<5% critical extraction error rate** on a seeded evaluation set of legal documents and OSINT tasks by enforcing:

- dual-agent agreement for named parties, dates, monetary values, and obligations;
- citation-required outputs;
- schema validation and ontology constraints;
- human review on critical fields;
- regression tests before prompt or workflow promotion.

## Self-Improvement Loop

ClearGlassInc Artemis gets better by converting operational signals into governed improvement proposals. It does not autonomously change mission goals, approval policy, or operational authority.

```text
Observe → Label → Evaluate → Propose → Review → Canary → Measure → Promote/Rollback
```

### Signals captured

- Operator corrections to extracted parties, dates, clauses, summaries, and recommendations.
- Query logs and failed searches.
- Alert outcomes: true positive, false positive, false negative, duplicate, stale, policy-blocked.
- Mission results: accepted brief, rejected recommendation, escalated case, closed-no-action.
- Tool telemetry: latency, retries, denied actions, schema failures, citation coverage.
- Eval results: precision, recall, extraction F1, hallucination rate, policy violations, human-edit distance.

### Improvement artifacts

| Signal | Artifact | Promotion gate |
|---|---|---|
| Repeated operator edits | New eval cases and prompt patch | Eval score improves without policy regression |
| False-positive alerts | Rule threshold proposal | Review by mission owner and canary validation |
| Slow model route | Router policy patch | Latency improves with equal or better quality |
| Citation failures | Workflow step requiring retrieval validation | Zero critical citation regressions |
| Drift in document format | Parser update proposal | Golden corpus passes and counsel approves |

### Versioning and rollback

- Prompts are immutable records: `prompt_id`, semantic version, owner, diff, eval report, approval decision, Apollo release channel.
- Workflows are signed DAG definitions with state-machine versions.
- Model routes are policy files with allowed models, data boundary constraints, fallback behavior, and eval thresholds.
- Apollo deploys to ring 0 sandbox, ring 1 limited analysts, and ring 2 production. Any eval regression, policy denial spike, or operator trust drop triggers automatic rollback to the last known-good bundle.

## Full-Stack Implementation

```text
apps/
  web/                       React + TypeScript UI
  api/                       FastAPI gateway and service APIs
  workers/                   Python event consumers and eval jobs
packages/
  ontology/                  Pydantic and SQL schemas
  policy/                    OPA/Rego bundles and tests
  agents/                    AIP tool definitions and workflow graphs
  evals/                     Golden datasets, graders, reports
infra/
  foundry/                   Dataset and ontology definitions
  apollo/                    Release manifests and rollout gates
  terraform/                 Cloud primitives when outside Palantir runtime
```

### Runtime path

1. UI uploads document or opens OSINT task.
2. API Gateway validates token, mission context, schema, and policy.
3. Event bus emits `case.document.received` or `osint.task.created`.
4. Foundry pipeline stores raw data, computes metadata, and materializes normalized objects.
5. AIP workflow launches OSINT and document agents with scoped tools.
6. Agents write candidate objects to staging tables, not production ontology.
7. Orchestrator reconciles candidates and runs eval/policy checks.
8. Human operator approves, rejects, or edits.
9. Approved updates become ontology actions and Gotham case graph updates.
10. Feedback becomes eval data and possible self-upgrade proposal.

## Security and Governance

- **Need-to-know**: every query carries subject, mission, coalition, role, compartment, purpose, and case context.
- **Row/column/entity permissions**: document body, extracted clauses, legal privilege, PII, and source identities can be independently masked.
- **Coalition boundaries**: object and edge markings define which coalition partners can see facts, evidence, and derived intelligence.
- **Zero-trust execution**: agents use short-lived tokens, tool allowlists, schema-constrained calls, network egress controls, and no ambient authority.
- **Immutable logs**: every prompt, input hash, retrieval result, model route, output, approval, denial, and ontology write is append-only.
- **Model governance**: model eligibility depends on classification, jurisdiction, privacy level, latency SLO, eval score, and approved use case.
- **Prompt governance**: prompt changes require diff review, eval report, policy check, human approval, Apollo canary, and rollback plan.
- **Policy-as-code**: OPA/Rego bundles enforce access, action, release, and model-routing constraints.

## Code Examples

### Python domain models

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl

class Classification(str, Enum):
    public = "PUBLIC"
    confidential = "CONFIDENTIAL"
    privileged = "PRIVILEGED"
    restricted = "RESTRICTED"

class MissionContext(BaseModel):
    mission_id: str
    user_id: str
    roles: set[str]
    coalition: set[str]
    compartments: set[str]
    purpose: str

class EvidenceItem(BaseModel):
    evidence_id: str
    case_id: str
    source_uri: HttpUrl | None = None
    source_system: str
    sha256: str
    reliability: float = Field(ge=0, le=1)
    classification: Classification
    collected_at: datetime
    lineage_refs: list[str]

class ClauseCandidate(BaseModel):
    document_id: str
    clause_type: str
    text_span: tuple[int, int]
    normalized_obligation: str
    confidence: float = Field(ge=0, le=1)
    citations: list[str]
    model_route: str
    prompt_version: str
```

### FastAPI gateway with policy preflight

```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ClearGlassInc Artemis API")

class DocumentUploadRequest(BaseModel):
    case_id: str
    filename: str
    sha256: str
    classification: str
    storage_ref: str

async def current_context() -> MissionContext:
    # Production: derive from OIDC token, mTLS identity, mission header, and session policy.
    return MissionContext(
        mission_id="mission-alpha",
        user_id="analyst-7",
        roles={"analyst"},
        coalition={"CLEARGLASSINC"},
        compartments={"LEGAL_TECH"},
        purpose="legal_intelligence_review",
    )

async def opa_allow(ctx: MissionContext, action: str, resource: dict) -> bool:
    # Production: call OPA sidecar or Foundry/Gotham policy decision point.
    return action != "approve_action_package" or "commander" in ctx.roles or "counsel" in ctx.roles

@app.post("/v1/documents")
async def upload_document(req: DocumentUploadRequest, ctx: MissionContext = Depends(current_context)):
    allowed = await opa_allow(ctx, "document:ingest", req.model_dump())
    if not allowed:
        raise HTTPException(status_code=403, detail="policy_denied")

    event = {
        "type": "case.document.received",
        "mission_id": ctx.mission_id,
        "case_id": req.case_id,
        "storage_ref": req.storage_ref,
        "sha256": req.sha256,
        "classification": req.classification,
        "actor": ctx.user_id,
    }
    await publish_event("case.document.received", event)
    await append_audit("document_ingest_requested", ctx, event)
    return {"status": "accepted", "event_type": event["type"]}
```

### Agent tool contract

```python
from typing import Literal

class ToolResult(BaseModel):
    status: Literal["ok", "denied", "error"]
    data: dict
    audit_id: str

class OntologyToolset:
    def __init__(self, ctx: MissionContext):
        self.ctx = ctx

    async def query_case_graph(self, case_id: str, depth: int = 2) -> ToolResult:
        if not await opa_allow(self.ctx, "case:read_graph", {"case_id": case_id, "depth": depth}):
            return ToolResult(status="denied", data={}, audit_id=await append_audit("tool_denied", self.ctx, {}))
        rows = await foundry_ontology_query("CaseGraph", {"case_id": case_id, "depth": depth})
        return ToolResult(status="ok", data={"nodes": rows.nodes, "edges": rows.edges}, audit_id=rows.audit_id)

    async def stage_clause_candidates(self, candidates: list[ClauseCandidate]) -> ToolResult:
        if any(c.confidence < 0.75 or not c.citations for c in candidates):
            return ToolResult(status="denied", data={"reason": "low_confidence_or_missing_citation"}, audit_id="local")
        if not await opa_allow(self.ctx, "clause:stage", {"count": len(candidates)}):
            return ToolResult(status="denied", data={}, audit_id="policy")
        write_id = await foundry_stage_objects("ClauseCandidate", [c.model_dump() for c in candidates])
        return ToolResult(status="ok", data={"write_id": write_id}, audit_id=write_id)
```

### Multi-agent state machine

```python
from enum import Enum
from pydantic import BaseModel

class WorkflowState(str, Enum):
    received = "received"
    osint_running = "osint_running"
    document_running = "document_running"
    correlating = "correlating"
    awaiting_approval = "awaiting_approval"
    committed = "committed"
    rejected = "rejected"
    rollback = "rollback"

class WorkflowContext(BaseModel):
    case_id: str
    document_id: str | None = None
    osint_task_id: str | None = None
    state: WorkflowState = WorkflowState.received
    errors: list[str] = []

async def run_legal_intel_workflow(ctx: WorkflowContext, mission: MissionContext) -> WorkflowContext:
    tools = OntologyToolset(mission)

    ctx.state = WorkflowState.osint_running
    osint_result = await run_agent("osint_intake_agent", ctx.model_dump(), tools=tools)

    ctx.state = WorkflowState.document_running
    doc_result = await run_agent("document_processing_agent", ctx.model_dump(), tools=tools)

    ctx.state = WorkflowState.correlating
    reconciliation = await reconcile_candidates(osint_result, doc_result)
    eval_report = await run_eval_suite("legal_mvp_regression", reconciliation)

    if eval_report.critical_error_rate >= 0.05 or reconciliation.requires_human_review:
        ctx.state = WorkflowState.awaiting_approval
        await create_approval_task(ctx.case_id, reconciliation.summary, eval_report.model_dump())
        return ctx

    # Even when metrics pass, operationally significant actions remain human-gated.
    ctx.state = WorkflowState.awaiting_approval
    await create_approval_task(ctx.case_id, reconciliation.summary, eval_report.model_dump())
    return ctx
```

### SQL-style ontology query

```sql
SELECT
  c.case_id,
  p.legal_name AS party,
  d.document_id,
  cl.clause_type,
  cl.normalized_obligation,
  cl.confidence,
  e.source_uri
FROM LegalCase c
JOIN PartyInCase pc ON pc.case_id = c.case_id
JOIN Party p ON p.party_id = pc.party_id
JOIN DocumentInCase dc ON dc.case_id = c.case_id
JOIN Document d ON d.document_id = dc.document_id
JOIN Clause cl ON cl.document_id = d.document_id
LEFT JOIN EvidenceSupportsRecommendation er ON er.case_id = c.case_id
LEFT JOIN EvidenceItem e ON e.evidence_id = er.evidence_id
WHERE c.case_id = :case_id
  AND c.mission_id = :mission_id
  AND cl.confidence >= 0.80
  AND has_entity_access(:user_id, cl.clause_id, 'read') = true;
```

### OPA/Rego policy

```rego
package artemis.authz

default allow := false

allow if {
  input.action == "case:read_graph"
  input.subject.mission_id == input.resource.mission_id
  input.subject.roles[_] == "analyst"
  input.resource.classification != "PRIVILEGED"
}

allow if {
  input.action == "clause:stage"
  input.subject.roles[_] == "analyst"
  input.subject.compartments[_] == "LEGAL_TECH"
  input.resource.max_confidence >= 0.75
}

allow if {
  input.action == "approve_action_package"
  input.subject.roles[_] == "counsel"
  input.resource.risk_score < 0.70
  input.resource.has_citations == true
}
```

### Evaluation pipeline

```python
class EvalResult(BaseModel):
    suite: str
    prompt_version: str
    workflow_version: str
    precision: float
    recall: float
    extraction_f1: float
    critical_error_rate: float
    hallucination_rate: float
    policy_violations: int
    latency_p95_ms: int

async def evaluate_candidate_release(candidate: dict) -> EvalResult:
    corpus = await load_golden_corpus("legal_osint_doc_mvp")
    judgments = []
    for example in corpus:
        output = await run_workflow_candidate(candidate, example.input)
        judgments.append(await grade_output(example.expected, output))

    result = aggregate_judgments(judgments)
    if result.critical_error_rate >= 0.05:
        await block_release(candidate, reason="critical_error_rate_threshold")
    if result.policy_violations > 0:
        await block_release(candidate, reason="policy_violation")
    await append_audit("candidate_release_evaluated", None, result.model_dump())
    return result
```

### Prompt improvement proposal

```python
async def propose_prompt_patch(feedback_batch_id: str) -> dict:
    feedback = await load_feedback_batch(feedback_batch_id)
    clusters = cluster_operator_corrections(feedback)
    proposal = await run_agent(
        "governance_copilot",
        {
            "task": "propose_minimal_prompt_patch",
            "constraints": [
                "do_not_change_operational_authority",
                "preserve_citation_requirement",
                "preserve_human_approval_gates",
            ],
            "feedback_clusters": clusters,
        },
    )
    eval_result = await evaluate_candidate_release(proposal)
    return {
        "proposal": proposal,
        "eval_result": eval_result.model_dump(),
        "requires_approval_from": ["ai_governance_lead", "mission_owner"],
    }
```

## Scenario Walkthrough

At 08:00 UTC, ClearGlassInc Artemis receives a new legal-intelligence event: a public corporate filing, a related contract exhibit, and an adverse-media OSINT hit appear in the intake queue for an active matter.

1. **Live event enters**: the API Gateway validates the analyst session, signs the request, emits `case.document.received`, and writes an immutable audit envelope.
2. **Platform triages**: Foundry stores raw files in bronze datasets, normalizes document metadata into silver, and links the case to relevant `Party`, `Document`, and `EvidenceItem` objects.
3. **Agents collaborate**: the OSINT Intake Agent identifies related public records and source reliability, while the Document Processing Agent extracts parties, dates, obligations, indemnities, governing law, and unusual termination clauses.
4. **Correlation**: the Triage Agent detects that an OSINT adverse-media event mentions the same party that appears in a high-risk indemnity clause. It stages a draft `Recommendation` with citations, confidence, risk score, and alternative explanations.
5. **Approval gate**: the Commander or Counsel Copilot shows the recommendation, provenance, uncertainty, and policy constraints. Counsel rejects one extracted obligation, edits the clause type, and approves a narrower action package: open a follow-up diligence task, not an external notification.
6. **Learning signal**: the correction becomes a `FeedbackSignal` linked to the document span, prompt version, model route, workflow version, operator, and approval decision.
7. **Self-improvement**: nightly eval jobs cluster similar corrections and propose a prompt patch for indemnity-clause extraction. The patch is tested on the golden corpus. If precision improves, critical error rate remains below 5%, citations remain intact, and policy tests pass, the Governance Console asks humans to approve canary release.
8. **Apollo rollout**: Apollo deploys the signed prompt/workflow bundle to ring 0. Telemetry shows lower edit distance and no policy regression, so it promotes to ring 1. If hallucination rate, latency, or denied-action spikes cross thresholds, Apollo rolls back automatically.

The result is a system that gets better every day from operator behavior, but only through explicit review, measurable eval improvement, immutable provenance, and reversible deployment.
