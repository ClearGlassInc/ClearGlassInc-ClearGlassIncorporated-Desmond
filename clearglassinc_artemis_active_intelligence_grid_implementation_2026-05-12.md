# ClearGlassInc Artemis — Active Intelligence Grid

## System Architecture

### 1) Runtime Topology (Production)

```text
[Next.js 15 Edge UI]
   ├─ /dashboard /events /agents /policy /memory /topology /workflows /telemetry /logs /settings
   ├─ Zustand real-time state layer
   ├─ Shadcn/ui + Tailwind + Framer Motion
   └─ WebSocket client + command palette + approval actions

[API Gateway (FastAPI + Next Route Handlers)]
   ├─ AuthN (OIDC/SAML) + short-lived JWT
   ├─ AuthZ (RBAC + ABAC + policy-as-code)
   ├─ request signing + rate controls + tenant isolation
   └─ fan-out to internal services

[Orchestration Plane]
   ├─ LangGraph Orchestrator
   ├─ Model Router (OpenAI + fallback model pool)
   ├─ Agent Runtime (Triage/Enrichment/Correlation/Policy/Memory/Recovery/Sentinel)
   ├─ Human Approval Gate
   └─ Self-Improvement Controller

[Streaming Plane]
   ├─ Event bus (NATS/Kafka)
   ├─ WebSocket broker (Redis pub/sub + ws)
   └─ telemetry stream processors

[Data Plane]
   ├─ Supabase Postgres (OLTP + RLS)
   ├─ pgvector memory index
   ├─ object store for artifacts
   ├─ Timescale hypertables for telemetry
   └─ immutable audit ledger tables

[Observability + Governance]
   ├─ OpenTelemetry traces, logs, metrics
   ├─ eval dashboards (precision/recall/latency/trust)
   ├─ prompt + workflow registry (versioned)
   └─ Apollo-style controlled deployment + rollback
```

### 2) Page Architecture (exact routes)

- `/dashboard`: command center (global mission state, active incidents, approval queue).
- `/events`: active SOC/OSINT/infrastructure event stream with correlation ribbons.
- `/agents`: per-agent state machines, reasoning chain snapshots, latency and confidence.
- `/policy`: governance center (approval gate, policy simulation, risk score, chain-of-command).
- `/memory`: vector recall, incident lineage, decision history.
- `/topology`: interactive graph (agents, zones, trust boundaries, attack pathways).
- `/workflows`: LangGraph execution DAG + retries + fallback routes.
- `/telemetry`: infra + AI metrics (token usage, p95 latency, error budgets).
- `/logs`: live terminal stream (policy checks, tool calls, model routing, rollback traces).
- `/settings`: runtime flags, RBAC, model routing guardrails.

---

## Data and Ontology

### 1) Core ontology (Foundry-like semantics)

```sql
create table ontology_entity (
  id uuid primary key,
  tenant_id uuid not null,
  entity_type text not null, -- Person, Host, Account, Process, Alert, Policy, Mission, Agent
  canonical_name text not null,
  attributes jsonb not null default '{}'::jsonb,
  confidence numeric(5,4) not null check (confidence between 0 and 1),
  temporal_valid_from timestamptz not null,
  temporal_valid_to timestamptz,
  provenance jsonb not null, -- source systems, transforms, tool chain
  classification text not null, -- U, C, S, TS or coalition tags
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table ontology_relation (
  id uuid primary key,
  tenant_id uuid not null,
  src_entity_id uuid references ontology_entity(id),
  dst_entity_id uuid references ontology_entity(id),
  relation_type text not null, -- LOGGED_INTO, CONNECTED_TO, DERIVED_FROM, IMPACTS
  confidence numeric(5,4) not null,
  evidence jsonb not null,
  valid_from timestamptz not null,
  valid_to timestamptz
);
```

### 2) Event + execution schema

```sql
create table intel_event (
  id uuid primary key,
  tenant_id uuid not null,
  source text not null, -- soc, osint, policy, infra
  event_type text not null,
  payload jsonb not null,
  priority smallint not null check (priority between 1 and 100),
  geo_point point,
  received_at timestamptz not null default now(),
  correlated_incident_id uuid,
  status text not null default 'new'
);

create table agent_execution (
  id uuid primary key,
  event_id uuid references intel_event(id),
  agent_name text not null,
  state text not null,
  latency_ms int not null,
  confidence numeric(5,4) not null,
  reasoning_chain jsonb not null,
  tool_calls jsonb not null,
  memory_refs jsonb not null,
  started_at timestamptz not null,
  finished_at timestamptz,
  trace_id text not null
);
```

### 3) Memory layer

```sql
create extension if not exists vector;

create table memory_chunk (
  id uuid primary key,
  tenant_id uuid not null,
  incident_id uuid,
  text_chunk text not null,
  embedding vector(1536) not null,
  metadata jsonb not null,
  quality_score numeric(5,4) not null,
  created_at timestamptz not null default now()
);

create index on memory_chunk using ivfflat (embedding vector_cosine_ops) with (lists = 200);
```

---

## AI and Agent Design

### LangGraph state

```python
from typing import TypedDict, List, Dict, Any

class MissionState(TypedDict):
    event_id: str
    incident_id: str | None
    signals: List[Dict[str, Any]]
    triage: Dict[str, Any]
    enrichment: Dict[str, Any]
    correlation: Dict[str, Any]
    recommendation: Dict[str, Any]
    policy: Dict[str, Any]
    approval_required: bool
    approved: bool | None
    audit: List[Dict[str, Any]]
```

### Agent chain (deterministic + tool-using)

```python
# apps/orchestrator/graph.py
from langgraph.graph import StateGraph, END

def build_graph(nodes):
    g = StateGraph(MissionState)
    g.add_node("triage", nodes.triage)
    g.add_node("enrich", nodes.enrich)
    g.add_node("correlate", nodes.correlate)
    g.add_node("recommend", nodes.recommend)
    g.add_node("policy", nodes.policy_gate)
    g.add_node("approval", nodes.human_approval)
    g.add_node("execute", nodes.execute_action)
    g.add_node("recovery", nodes.recovery)

    g.set_entry_point("triage")
    g.add_edge("triage", "enrich")
    g.add_edge("enrich", "correlate")
    g.add_edge("correlate", "recommend")
    g.add_edge("recommend", "policy")

    g.add_conditional_edges(
        "policy",
        lambda s: "approval" if s["approval_required"] else "execute",
        {"approval": "approval", "execute": "execute"}
    )
    g.add_conditional_edges(
        "approval",
        lambda s: "execute" if s["approved"] else "recovery",
        {"execute": "execute", "recovery": "recovery"}
    )
    g.add_edge("execute", END)
    g.add_edge("recovery", END)
    return g.compile()
```

---

## Self-Improvement Loop

1. **Collect signals**: operator edits, rejected recommendations, false positives, mission outcomes, latency misses.
2. **Generate eval datasets** from `agent_execution`, `approval_decisions`, `incident_outcomes`.
3. **Run scheduled evals** by workflow version and model version.
4. **Propose change set** (prompt patch, tool ordering, threshold tuning, route updates).
5. **Safety checks**: drift, regression, policy violation simulation.
6. **Human approval board** (required for production promotion).
7. **Canary deploy** (5% traffic), then progressive rollout.
8. **Auto rollback** if trust/precision/SLA falls below thresholds.

```python
# apps/improvement/pipeline.py

def propose_improvement(metrics, baseline):
    proposal = []
    if metrics["precision"] < baseline["precision"] - 0.03:
        proposal.append({"type": "prompt_patch", "target": "RecommendationAgent"})
    if metrics["p95_latency_ms"] > baseline["p95_latency_ms"] * 1.2:
        proposal.append({"type": "router_change", "target": "model_router"})
    return proposal
```

---

## Full-Stack Implementation

### Next.js 15 folder structure

```text
apps/web/
  app/
    dashboard/page.tsx
    events/page.tsx
    agents/page.tsx
    policy/page.tsx
    memory/page.tsx
    topology/page.tsx
    workflows/page.tsx
    telemetry/page.tsx
    logs/page.tsx
    settings/page.tsx
    api/ws/route.ts
    api/events/route.ts
  components/
    command/ActiveEventStream.tsx
    command/ApprovalGate.tsx
    command/WorkflowStateGrid.tsx
    command/TelemetryPanel.tsx
    topology/RuntimeGraph.tsx
    memory/RecallPanel.tsx
    logs/LiveTerminal.tsx
  lib/
    store/mission-store.ts
    ws/client.ts
    policy/client.ts
    orchestration/client.ts
```

### Zustand live store

```ts
// lib/store/mission-store.ts
import { create } from "zustand";

type AgentState = { name: string; state: string; latencyMs: number; confidence: number };

type MissionStore = {
  connected: boolean;
  events: any[];
  agents: AgentState[];
  logs: string[];
  setConnected: (v: boolean) => void;
  pushEvent: (e: any) => void;
  upsertAgent: (a: AgentState) => void;
  pushLog: (l: string) => void;
};

export const useMissionStore = create<MissionStore>((set) => ({
  connected: false,
  events: [],
  agents: [],
  logs: [],
  setConnected: (connected) => set({ connected }),
  pushEvent: (e) => set((s) => ({ events: [e, ...s.events].slice(0, 500) })),
  upsertAgent: (a) => set((s) => ({ agents: [...s.agents.filter(x => x.name !== a.name), a] })),
  pushLog: (l) => set((s) => ({ logs: [l, ...s.logs].slice(0, 2000) })),
}));
```

### Realistic synthetic stream engine (Python)

```python
# apps/sim/stream_engine.py
import asyncio, random, uuid, time, json
from websockets.server import serve

AGENTS = ["TriageAgent","EnrichmentAgent","CorrelationAgent","RecommendationAgent","PolicyAgent","MemoryAgent","RecoveryAgent","SentinelAgent"]

async def stream(websocket):
    while True:
        now = time.time()
        event = {
            "type": "intel.event",
            "id": str(uuid.uuid4()),
            "source": random.choice(["soc","osint","infra","policy"]),
            "priority": random.randint(42, 97),
            "summary": random.choice([
                "Privileged login anomaly from segmented enclave with geo mismatch",
                "C2 beacon-like burst observed across east-west microsegment",
                "Policy drift detected in production service account scope"
            ]),
            "ts": now,
        }
        await websocket.send(json.dumps(event))

        for name in AGENTS:
            agent_state = {
                "type": "agent.state",
                "name": name,
                "state": random.choice(["triaging","enriching","correlating","recommending","verifying","recalling","recovering","monitoring"]),
                "latencyMs": int(random.gauss(220, 70)),
                "confidence": round(min(0.99, max(0.51, random.gauss(0.79, 0.1))), 3),
                "trace": f"trace-{uuid.uuid4()}"
            }
            await websocket.send(json.dumps(agent_state))

        await websocket.send(json.dumps({
            "type": "log",
            "message": f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] Policy check completed; risk=0.{random.randint(10,89)}"
        }))
        await asyncio.sleep(random.uniform(0.4, 1.4))

async def main():
    async with serve(stream, "0.0.0.0", 8787):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Security and Governance

- **Need-to-know enforcement**: Postgres RLS per mission, coalition tag, compartment.
- **Entity-level ACL**: deny-by-default policy on ontology entities and relations.
- **Policy-as-code**: OPA/Rego checks for every operational action.
- **Zero-trust tools**: signed tool invocation envelopes with purpose binding.
- **Immutable audit**: append-only approval + execution + rollback events.
- **Model governance**: approved model registry, prompt hash pinning, eval gate required.

```rego
package artemis.policy.execution

default allow = false

allow if {
  input.user.role == "mission_commander"
  input.action.type == "quarantine_host"
  input.action.risk_score <= 0.72
  input.context.coalition in input.user.coalitions
}
```

---

## Code Examples

### Approval gate endpoint

```python
# apps/api/routes/policy.py
@router.post('/policy/approve')
async def approve(req: ApprovalRequest, user=Depends(require_role(["mission_commander", "security_lead"]))):
    decision = await policy_engine.validate(req, user)
    await audit_log.write("approval.decision", {
        "request_id": req.request_id,
        "decision": decision.verdict,
        "actor": user.sub,
        "reason": req.reason,
    })
    if decision.verdict != "ALLOW":
        return {"status": "blocked", "decision": decision.verdict}
    await orchestrator.resume(req.request_id)
    return {"status": "approved"}
```

### Vector recall query

```sql
select id, incident_id, text_chunk, quality_score
from memory_chunk
where tenant_id = $1
order by embedding <=> $2::vector
limit 8;
```

---

## Scenario Walkthrough (Live)

1. `2026-05-12T20:28:11Z`: SOC event enters stream (`privileged login anomaly`, priority 91).
2. `TriageAgent` classifies as potential lateral movement with confidence 0.74.
3. `EnrichmentAgent` pulls IAM change history, endpoint telemetry, geo-IP reputation.
4. `CorrelationAgent` links event to prior incident pattern cluster (`INC-2026-0442`).
5. `RecommendationAgent` proposes host quarantine + credential reset + scoped network block.
6. `PolicyAgent` marks action as **approval required** due to blast radius score 0.67.
7. Human operator on `/policy` approves with reason code `C2-CONTAINMENT`.
8. Execution engine triggers runbook; `SentinelAgent` monitors for regression.
9. `RecoveryAgent` validates service health, auto-rolls back one over-broad ACL change.
10. Outcome labeled `true_positive`; loop records improved threshold recommendation.
11. Improvement controller proposes reducing triage escalation threshold from 0.70 to 0.66 for this mission profile.
12. Change is sandbox-evaluated, then queued for human approval and canary deployment.

This architecture yields a real-time, policy-guarded, self-improving intelligence grid that remains human-governed for operationally significant actions.
