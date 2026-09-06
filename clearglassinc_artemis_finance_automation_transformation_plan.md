# ClearGlassInc Artemis — Finance Automation Platform Transformation Plan

## System Architecture

### Executive North Star
Build **ClearGlassInc Artemis** into a production-grade finance automation platform that continuously improves planning, forecasting, reporting, compliance confidence, and operating leverage.

### Layered Architecture (Palantir-native + full-stack)

```text
[Web UI: Analyst Console, CFO Console, Ops Console]
        |
[API Gateway + BFF]
        |
[Domain Services: Forecasting, Close, Variance, Controls, Treasury, Compliance]
        |
[Event Bus + Workflow Orchestrator + Agent Runtime]
        |
[Foundry Data Pipelines + Ontology + Feature Store + Document Store]
        |
[Model Router + AIP Agents + Evals + Prompt Registry]
        |
[Policy-as-Code + ABAC/RBAC + Audit + Immutable Logs]
        |
[Apollo Deploy + Runtime Policy + Rollback + Progressive Delivery]
```

### Component Responsibilities
- **Gotham**: case-centric investigation workflows for anomaly events, vendor risk, payment exceptions.
- **Foundry**: canonical finance ontology, lineage-aware ETL, KPI marts, temporal snapshots, reproducible transforms.
- **AIP**: copilots for FP&A, controllership, treasury; tool-using agents; evaluation harnesses.
- **Apollo**: release channels, canaries, policy-gated rollout, emergency rollback, runtime health guardrails.

### Deployment Topology
- **Frontend**: TypeScript/React, strict CSP, SSO, policy-aware UI components.
- **Backend**: Python FastAPI microservices with domain boundaries.
- **Data**: lakehouse + time-series aggregates + semantic retrieval index.
- **Streaming**: Kafka-compatible event backbone for transaction, alert, and outcome events.

---

## Data and Ontology

### Core Entity Model

```sql
-- canonical finance entities
CREATE TABLE entity_account (
  account_id STRING PRIMARY KEY,
  account_code STRING,
  account_name STRING,
  account_type STRING,
  legal_entity_id STRING,
  currency STRING,
  effective_from TIMESTAMP,
  effective_to TIMESTAMP,
  lineage_run_id STRING,
  confidence_score DOUBLE
);

CREATE TABLE entity_transaction (
  txn_id STRING PRIMARY KEY,
  account_id STRING,
  counterparty_id STRING,
  amount DECIMAL(18,2),
  currency STRING,
  txn_timestamp TIMESTAMP,
  source_system STRING,
  mission_context_id STRING,
  pii_classification STRING,
  confidence_score DOUBLE,
  lineage_run_id STRING
);

CREATE TABLE entity_forecast_version (
  forecast_version_id STRING PRIMARY KEY,
  model_name STRING,
  model_version STRING,
  prompt_version STRING,
  approval_status STRING,
  approved_by STRING,
  approved_at TIMESTAMP,
  rollback_version_id STRING,
  metrics_json STRING
);
```

### Ontology Relationships
- `ACCOUNT -> POSTED_IN -> LEDGER_PERIOD`
- `TRANSACTION -> BELONGS_TO -> ACCOUNT`
- `TRANSACTION -> INVOLVES -> COUNTERPARTY`
- `ALERT -> TRIGGERED_BY -> TRANSACTION_SET`
- `FORECAST -> GENERATED_FROM -> FEATURE_SNAPSHOT`
- `ACTION_PACKAGE -> APPROVED_BY -> OPERATOR`

### Finance-Critical Metadata
- **Confidence**: all enriched facts carry calibrated confidence and provenance.
- **Lineage**: every metric references source system, transformation version, and run ID.
- **Temporal state**: bi-temporal validity (`effective` + `recorded`) for audit reconstruction.
- **Permissions**: row/entity-level tags enforce coalition and legal-entity boundaries.

---

## AI and Agent Design

### Copilots
1. **FP&A Copilot**: scenario generation, variance decomposition, forecast risk commentary.
2. **Controller Copilot**: close checklist validation, reconciliations, materiality triage.
3. **Treasury Copilot**: cash positioning, liquidity stress signals, covenant watch.

### Multi-Agent Pipeline

```text
Signal Ingest Agent
 -> Data Quality Agent
 -> Enrichment Agent
 -> Correlation Agent
 -> Recommendation Agent
 -> Human Approval Gate
 -> Execution Agent (restricted)
```

### Tooling Contract
Agents can only use signed tools:
- `query_finance_ontology`
- `generate_board_pack_section`
- `open_investigation_case`
- `propose_journal_entry` (approval required)
- `simulate_cashflow_scenario`

Operationally significant actions require explicit human approval and policy checks.

---

## Self-Improvement Loop

### Closed-Loop Learning Flow
1. Capture signals: operator edits, overrides, acceptance/rejection, latency, downstream outcome.
2. Convert to eval records and attach mission/business labels (e.g., false positive, high-value save).
3. Train/update:
   - prompt variants
   - routing policies
   - threshold heuristics
   - workflow branch logic
4. Gate changes through offline replay + shadow testing + human approval board.
5. Progressive rollout with Apollo canary.
6. Auto-rollback on trust/safety/regression breach.

### Safety Controls
- No autonomous goal mutation.
- No direct production prompt overwrite.
- Mandatory signed change request with approver identity.
- Drift detectors (data drift, concept drift, outcome drift).

### Metrics
- Precision/recall of anomalies.
- Forecast MAPE / WAPE by entity.
- Median triage latency.
- Operator trust score (acceptance rate adjusted for rework).
- Mission impact ($ preserved, losses avoided, cycle time reduction).

---

## Full-Stack Implementation

### Backend (Python/FastAPI)

```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal

app = FastAPI(title="ClearGlassInc Artemis Finance API")

class ApprovalRequest(BaseModel):
    action_type: Literal["journal_entry", "payment_hold", "forecast_publish"]
    payload: dict
    risk_score: float


def policy_check(user, action_type: str, payload: dict) -> bool:
    # policy-as-code hook (OPA/Cedar style adapter)
    return user["role"] in {"controller", "finance_admin"} and payload.get("entity") in user["scopes"]


@app.post("/v1/actions/approve")
def approve_action(req: ApprovalRequest, user=Depends(lambda: {"role": "controller", "scopes": ["US_LE"]})):
    if not policy_check(user, req.action_type, req.payload):
        raise HTTPException(status_code=403, detail="Policy denied")
    if req.risk_score > 0.85:
        raise HTTPException(status_code=412, detail="Requires second approver")
    return {"status": "approved", "audit": "immutable-log-ref-123"}
```

### Event Handler (Python)

```python
from dataclasses import dataclass

@dataclass
class AlertEvent:
    alert_id: str
    entity: str
    severity: float
    feature_snapshot_id: str


def on_alert(event: AlertEvent, bus, agent_runtime):
    if event.severity < 0.4:
        return bus.publish("alerts.deferred", event.__dict__)

    recommendation = agent_runtime.run(
        workflow="finance_alert_triage_v3",
        context={"alert_id": event.alert_id, "entity": event.entity}
    )
    bus.publish("alerts.recommendation.created", recommendation)
```

### Prompt/Workflow Optimization Job (Python)

```python
def optimize_prompt_variant(eval_store, registry, min_samples=500):
    candidates = eval_store.fetch_candidates(task="variance_explanation", min_samples=min_samples)
    baseline = registry.get_active("variance_explanation")

    winner = baseline
    for c in candidates:
        if c.precision > winner.precision and c.latency_p95 <= winner.latency_p95 * 1.1:
            winner = c

    if winner.version != baseline.version:
        return {
            "proposed_change": {"from": baseline.version, "to": winner.version},
            "requires_approval": True,
            "rollback_to": baseline.version,
        }
    return {"proposed_change": None}
```

### Workflow State Machine (pseudo-Python)

```python
STATE_GRAPH = {
  "INGESTED": ["ENRICHED", "REJECTED"],
  "ENRICHED": ["CORRELATED", "REJECTED"],
  "CORRELATED": ["RECOMMENDED"],
  "RECOMMENDED": ["APPROVED", "REJECTED", "ESCALATED"],
  "APPROVED": ["EXECUTED", "ROLLED_BACK"],
}
```

---

## Security and Governance

### Controls
- Zero-trust service identity (mTLS + short-lived workload credentials).
- Need-to-know ABAC with legal-entity and coalition constraints.
- Column/row/entity policies for sensitive financial and personal data.
- Immutable audit log for prompts, model routing decisions, and operator actions.
- Signed artifact promotion for models/prompts/workflows.

### Governance Boards
- **Model Risk Board**: approves model routing changes.
- **Prompt Governance Board**: approves prompt set revisions.
- **Operations Control Board**: approves high-impact workflow automations.

---

## Code Examples (Additional)

### Ontology-Driven Query

```python
def fetch_counterparty_exposure(foundry_client, counterparty_id: str):
    return foundry_client.query(
        """
        SELECT cp.counterparty_id,
               SUM(tx.amount_usd) AS exposure_usd,
               COUNT(DISTINCT tx.txn_id) AS txn_count,
               MAX(tx.txn_timestamp) AS latest_activity
        FROM entity_transaction tx
        JOIN entity_counterparty cp ON tx.counterparty_id = cp.counterparty_id
        WHERE cp.counterparty_id = :counterparty_id
        GROUP BY cp.counterparty_id
        """,
        params={"counterparty_id": counterparty_id}
    )
```

### Evaluation Pipeline Skeleton

```python
def run_eval_pipeline(predictions, labels):
    tp = sum(1 for p, y in zip(predictions, labels) if p == 1 and y == 1)
    fp = sum(1 for p, y in zip(predictions, labels) if p == 1 and y == 0)
    fn = sum(1 for p, y in zip(predictions, labels) if p == 0 and y == 1)

    precision = tp / (tp + fp + 1e-9)
    recall = tp / (tp + fn + 1e-9)
    return {"precision": precision, "recall": recall}
```

---

## Scenario Walkthrough (End-to-End)

1. A high-value payment anomaly arrives via streaming ingest (`alerts.raw`).
2. Enrichment agent links transaction to historical vendor behavior and active investigation graph.
3. Correlation agent identifies pattern similarity to prior confirmed fraud cases.
4. Recommendation agent proposes `payment_hold` + `case_open` with confidence 0.91.
5. Controller sees rationale, supporting evidence, and projected downside if ignored.
6. Controller approves `payment_hold`, rejects `case_open` pending more evidence.
7. Execution service performs hold; immutable audit record written.
8. Outcome later confirms anomaly was valid; label captured as true positive.
9. Self-improvement engine increments weight for features used, updates eval set, proposes improved triage prompt.
10. Change request routed to Prompt Governance Board; approved variant canaried via Apollo.
11. Post-canary metrics show better precision and stable latency; variant promoted globally.

---

## Current Repository Assessment

- The repository has strong ideation density but needs tighter production framing and explicit finance-operational controls.
- Documentation breadth is high; implementation traceability, governance patterns, and measurable acceptance criteria should be standardized into a canonical architecture playbook.

## Top Risks and Opportunities

### Risks
- Strategy fragmentation across many architecture documents.
- Inconsistent operational guardrails for self-improving AI behavior.
- Potential drift between aspirational design and implementable service contracts.

### Opportunities
- Consolidate around a single finance-first reference architecture.
- Standardize policy-as-code approval gates for all high-impact actions.
- Establish eval-driven CI/CD gates for prompts, workflows, and routing logic.

## Prioritized Recommendations

1. Adopt this document as the **canonical finance automation architecture baseline**.
2. Implement policy enforcement and approval gates first (highest risk reduction).
3. Stand up eval pipeline + canary rollout loop before expanding agent autonomy.
4. Create quarterly architecture scorecard (precision, latency, trust, impact).

## Verification Status

- Document added successfully.
- Python snippets are intentionally production-oriented skeletons and require integration with Foundry/AIP SDKs in environment-specific repos.

## Next-Step Plan

- Week 1: approve ontology baseline + policy contracts.
- Week 2: implement event bus workflows and approval APIs.
- Week 3: ship eval harness + drift monitors + dashboard KPIs.
- Week 4: Apollo canary rollout of first self-improving finance triage workflow.
