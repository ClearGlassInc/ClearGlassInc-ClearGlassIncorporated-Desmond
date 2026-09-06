# ClearGlassInc Artemis Skeleton Key Execution Blueprint

## System Architecture

ClearGlassInc Artemis is a Palantir-native intelligence platform that pairs Gotham investigations, Foundry data products, AIP agent orchestration, and Apollo-controlled delivery into one governed operating system. Gotham owns mission workspaces, entity timelines, and investigative link analysis. Foundry owns data integration, ontology objects, lineage, and pipeline application logic. AIP owns copilots, tool-using agents, evals, and prompt/workflow governance. Apollo owns deployment rings, rollback, runtime policy bundles, and production change control.

```text
Operator UI -> API Gateway -> Policy Decision Point -> Mission Services
      |              |                    |                  |
      v              v                    v                  v
Gotham Views   Foundry Ontology     AIP Agent Runtime   Audit Ledger
      |              |                    |                  |
      v              v                    v                  v
Live Streams -> Lakehouse/Graph -> Model Router/Evals -> Apollo Rollout
```

The frontend is a Next.js command surface with a live mission feed, graph canvas, map overlays, evidence sidebars, approval queue, eval dashboard, and prompt/workflow change-review console. The backend is Python-first: FastAPI gateway, ontology service, mission service, feedback service, eval service, policy service, and AIP orchestration workers. Streaming uses Kafka-compatible topics for `raw.intel.events`, `ontology.entity.updates`, `agent.action.requests`, `operator.feedback`, `mission.outcomes`, and `governance.change.proposals`.

## Data and Ontology

The ontology defines mission reality as governed objects rather than loose documents. Core objects are `Person`, `Organization`, `Asset`, `Device`, `Account`, `Location`, `Signal`, `Indicator`, `Event`, `Case`, `Mission`, `ActionRecommendation`, `IntelProduct`, `Feedback`, `Outcome`, and `ChangeProposal`. Relationships include `OBSERVED_AT`, `ASSOCIATED_WITH`, `OWNS`, `USES`, `COMMUNICATED_WITH`, `MENTIONS`, `DERIVED_FROM`, `SUPPORTS`, `CONTRADICTS`, `RECOMMENDS`, and `APPROVED_BY`.

Every object carries confidence, temporal validity, lineage, compartment, coalition visibility, source reliability, handling caveats, and policy labels. This lets humans filter mission views by evidence and lets agents inherit the same permissions and ontology semantics as the operator they support.

```sql
CREATE TABLE artemis_event (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  valid_from TIMESTAMPTZ NOT NULL,
  valid_to TIMESTAMPTZ,
  confidence NUMERIC(4,3) CHECK (confidence BETWEEN 0 AND 1),
  source_ids TEXT[] NOT NULL,
  lineage_hash TEXT NOT NULL,
  mission_id TEXT NOT NULL,
  compartment TEXT NOT NULL,
  coalition_release TEXT[] DEFAULT '{}',
  payload JSONB NOT NULL
);
```

## AI and Agent Design

AIP hosts governed copilots and specialist agents. The Analyst Copilot explains entities, summarizes evidence, drafts intel products, and asks for missing context. The Commander Copilot compresses mission state into decision briefs and risk tradeoffs. Specialist agents handle triage, enrichment, correlation, summarization, recommendation, and change-proposal generation.

Agents may query data, build evidence graphs, prepare action packages, open draft cases, and generate reports, but operationally significant actions require explicit approval. A policy gate evaluates user authority, mission context, entity sensitivity, tool risk, coalition boundaries, and current Apollo runtime controls before every tool call.

## Self-Improvement Loop

The platform improves by converting operator behavior into governed evals, not by silently changing objectives. It captures query logs, accepted recommendations, rejected recommendations, operator corrections, case outcomes, alert dispositions, latency, citation quality, and policy denials. A nightly eval builder turns those signals into regression tests for prompts, model routing, retrieval policies, heuristics, and workflow transitions.

```text
Feedback + outcomes -> Eval cases -> Candidate prompt/workflow/router patch
      -> Offline eval -> Red-team policy eval -> Human approval
      -> Apollo canary -> Online metrics -> Promote or rollback
```

Self-upgrades are represented as versioned `ChangeProposal` objects with diffs, eval scores, blast radius, rollback target, owner, approval status, and immutable audit hash. Apollo deploys approved changes through dev, staging, canary, and mission rings. Drift monitors compare live distributions against training/eval baselines for source mix, entity types, language, geography, latency, false-positive rate, and operator trust.

## Full-Stack Implementation

The implementation is organized around production services:

- `gateway`: request validation, OIDC, rate limits, request signing, and policy pre-checks.
- `ontology-service`: Foundry object access, entity merge logic, lineage, and temporal queries.
- `mission-service`: cases, tasks, alerts, approvals, and action packages.
- `aip-orchestrator`: agent planning, tool calls, model routing, eval gates, and trace capture.
- `feedback-service`: corrections, ratings, dispositions, and outcome ingestion.
- `eval-service`: dataset generation, prompt tests, router tests, regression reports, and candidate scoring.
- `policy-service`: OPA/Rego policy-as-code plus entity-level authorization.
- `observability`: OpenTelemetry traces, Prometheus metrics, SIEM forwarding, and immutable audit logs.

## Security and Governance

ClearGlassInc Artemis uses zero-trust execution. Every request is authenticated, authorized, policy-checked, traced, and logged. Access control is need-to-know at row, column, entity, relationship, and tool levels. Coalition boundaries are enforced through labels such as `REL_US_ONLY`, `REL_COALITION_ALPHA`, `LEGAL_PRIVILEGED`, `SOURCE_PROTECTED`, and `NO_AI_SUMMARY`.

Prompt governance treats prompts as deployable artifacts. Model governance records model version, routing reason, input labels, output confidence, eval status, and rollback target. Policy-as-code prevents agents from exfiltrating restricted data, producing uncited claims, or executing operational actions without approval.

## Code Examples

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any

class Risk(str, Enum):
    READ_ONLY = "read_only"
    DRAFT_ACTION = "draft_action"
    OPERATIONAL = "operational"

@dataclass(frozen=True)
class ToolRequest:
    operator_id: str
    mission_id: str
    tool_name: str
    risk: Risk
    entity_ids: list[str]
    input_labels: set[str]
    payload: dict[str, Any]

class PolicyDecision(Exception):
    pass

async def enforce_policy(req: ToolRequest, pdp, ontology) -> None:
    entities = await ontology.fetch_entities(req.entity_ids)
    decision = await pdp.evaluate({
        "operator_id": req.operator_id,
        "mission_id": req.mission_id,
        "tool_name": req.tool_name,
        "risk": req.risk.value,
        "labels": sorted(req.input_labels | {e.compartment for e in entities}),
    })
    if not decision["allow"]:
        raise PolicyDecision(decision["reason"])
    if req.risk == Risk.OPERATIONAL and not decision.get("requires_approval_satisfied"):
        raise PolicyDecision("Operational action requires explicit human approval")
```

```python
async def build_eval_case(feedback, outcome, trace_store):
    trace = await trace_store.get(feedback.agent_trace_id)
    return {
        "eval_id": f"eval-{feedback.feedback_id}",
        "mission_id": feedback.mission_id,
        "input_event": trace.input_event,
        "agent_plan": trace.plan,
        "tool_calls": trace.tool_calls,
        "operator_correction": feedback.correction,
        "final_outcome": outcome.label,
        "expected_behavior": feedback.expected_behavior,
        "must_cite_sources": True,
        "must_obey_policy": True,
    }
```

```python
class WorkflowState(str, Enum):
    TRIAGE = "triage"
    ENRICH = "enrich"
    CORRELATE = "correlate"
    RECOMMEND = "recommend"
    APPROVAL = "approval"
    EXECUTE = "execute"
    LEARN = "learn"

TRANSITIONS = {
    WorkflowState.TRIAGE: WorkflowState.ENRICH,
    WorkflowState.ENRICH: WorkflowState.CORRELATE,
    WorkflowState.CORRELATE: WorkflowState.RECOMMEND,
    WorkflowState.RECOMMEND: WorkflowState.APPROVAL,
    WorkflowState.APPROVAL: WorkflowState.EXECUTE,
    WorkflowState.EXECUTE: WorkflowState.LEARN,
}
```

## Scenario Walkthrough

At 08:10 UTC, a live supplier-risk signal enters `raw.intel.events`. Foundry validates schema, attaches lineage, resolves two organizations and one device, and updates the ontology. Gotham surfaces a watchfloor alert with a timeline, map pin, graph edges, and source citations.

The triage agent scores relevance, the enrichment agent pulls authoritative registry records, the correlation agent links the event to a prior fraud pattern, and the recommendation agent drafts a response package. Policy blocks coalition sharing because one evidence item is `SOURCE_PROTECTED`. The operator approves case creation, rejects external release, and corrects a jurisdiction field.

That correction becomes feedback. When the case is later confirmed true positive, the eval service creates a regression case. The PromptOps agent proposes a retrieval rule requiring authoritative jurisdiction corroboration before jurisdiction-sensitive recommendations. Humans approve the change after offline evals improve precision without raising latency. Apollo canaries the update to one mission cell, metrics remain healthy, and the change is promoted. If trust, precision, policy, or latency had degraded, Apollo would roll back to the prior prompt and routing bundle.
