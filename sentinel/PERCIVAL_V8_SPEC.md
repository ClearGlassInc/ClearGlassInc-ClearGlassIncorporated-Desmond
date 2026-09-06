# Percival v8 — Governed Control Plane Spec

Percival is a governed decision/execution substrate: **read-only analysis →
draft → human approval → execution**, deny-by-default, sponsor-owned,
audit-by-default. This document is the v8 control doctrine and the map from the
doctrine to the code that enforces it.

> **Honesty note.** The table below marks what is **implemented and tested**
> today vs. what is **planned**. The enforcing keystones (Policy Governor,
> capability tiers, scoped identity, hash-chained audit, mission memory) are
> real, stdlib-only modules with test coverage. The distributed-runtime pieces
> (isolated executor, vector/graph stores, microservice split) are roadmap, not
> claimed as running.

## 1. Policy Control Matrix

| Module | Execution Privilege | Default State | Escalation Trigger (fail-closed) | Status |
|---|---|---|---|---|
| **Policy Governor** | Sovereign enforcer | Deny-all | Undefined capability or conflicting rules | ✅ `sentinel/sentinel/governor.py` |
| **Task Router** | Read/route | Observational | Request spans unmapped domains | ◻ persona-level (lanes) → module planned |
| **Context Engine** | Read/infer | Stateless | Irresolvable contradiction in input | ◻ planned |
| **Retrieval Layer** | Read-only | Scoped search | Access outside approved token | ◻ planned |
| **Memory Vault** | Read/write (scoped) | Append-only | Overwrite of immutable decision history | ✅ `sentinel/sentinel/mission_memory.py` |
| **Execution Planner** | Propose-only | Draft mode | Missing deps / unapproved constraints | ◻ planned |
| **EvalOps Monitor** | Read/score | Active auditing | Output confidence below threshold | ✅ governor `confidence_threshold` downgrade |
| **Escalation Gate** | Blocking | Locked | High-risk system/data modification | ✅ governor escalates `execute_external` / `modify_system` |
| **Identity & Authority** | Scoped grant | Read-only | Unsponsored / out-of-scope / stopped | ✅ `sentinel/sentinel/identity.py` |
| **Capability Broker** | Grant/deny | Deny-by-default | Request above granted tier | ✅ `sentinel/sentinel/capability.py` |
| **Audit Ledger** | Append-only | Hash-chained | Tamper / broken chain | ✅ `sentinel/sentinel/audit.py` |

## 2. Capability Schema

Machine-readable contract at [`schemas/capabilities.json`](schemas/capabilities.json)
(JSON Schema draft-07). Every inbound request is validated against it by the
Policy Governor before routing. `action_scope` maps to capability tiers:

| `action_scope` | Capability tier | Behavior |
|---|---|---|
| `read_only` | `READ_ONLY` | allowed within scope |
| `draft_proposal` | `DRAFT` | allowed within scope |
| `execute_internal` | `CHANGE` | allowed only with an explicit CHANGE grant |
| `execute_external` | `DEPLOY` | **escalated** — blocked pending human approval |
| `modify_system` | `DEPLOY` | **escalated** — blocked pending human approval |

## 3. Enforcement Flow (implemented)

```
request ──▶ PolicyGovernor.evaluate()
             │
             ├─ validate_request()        # schema: required / enum / ranges  → DENY on violation
             ├─ identity.active?           # stopped instance                  → DENY (fail-closed)
             ├─ confidence ≥ threshold?    # EvalOps downgrade                 → DENY (verify mode)
             ├─ for each lane:
             │     identity.may_touch()    # deny-by-default, denial wins      → DENY
             │     broker.check(tier)      # object-capability, tier ceiling   → DENY
             ├─ scope ∈ {external, system}?                                    → ESCALATE (human)
             └─ else                                                           → ALLOW
             (every branch writes a hash-chained audit entry)
```

Deny rules override allow rules; anything undefined is denied; any ambiguity
fails closed.

## 4. Failure Modes & Handling

- **Conflicting policy directives** — e.g. a request needs `execute_internal`
  but a lane is scoped read-only. The Governor evaluates hierarchically: **deny
  overrides allow**, the request is denied, and the conflict is returned for the
  operator to resolve. (Implemented: lane-by-lane broker check.)
- **Silent hallucination of authority** — the planner tries to bypass the gate
  for a "low-risk" action that is actually out of bounds. Handling: high-power
  scopes are **hard-gated to escalation** in the Governor; a downstream runtime
  should additionally require a signature from the Escalation Gate before acting
  (roadmap: cryptographic signing between modules).
- **Context-window dilution** — over-broad retrieval drowns the objective.
  Handling: token budgeting + state summarization in the Context Engine
  (roadmap; mission memory already stores compact, sourced items rather than raw
  history).

## 5. Roadmap (not yet built — stated plainly)

Isolated executor runtime, recovery/safe-state fallback, RAG retrieval layer,
vector + graph memory stores, inter-module cryptographic signing, and the
microservice/`docker-compose` split. These are the target architecture; today's
implementation is a single, well-tested governance core the running agent can
adopt incrementally.
