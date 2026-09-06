# Percival v10 — Policy Boundary and Recovery Semantics

> **Status: deployment-grade design blueprint plus executable scaffold.** Percival v10 tightens the v9 governed orchestration model for ClearGlassInc Artemis by making policy freshness, signed approvals, audit durability, retry budgets, trace propagation, and workflow rewind explicit release-blocking contracts.

Percival is the ClearGlass governed intelligence substrate for controlled execution, policy enforcement, and decision support. It is not a generic assistant and it is not an unconstrained agent. It is a multi-service control plane that routes intent, validates authority, plans work, executes bounded tasks, and records every meaningful decision.

## System Architecture

Percival v10 is layered so no component can bypass policy or audit:

| Layer | Narrow contract | Fail-closed rule |
|---|---|---|
| Gateway | Ingress, identity validation, request normalization, correlation ID creation | Missing identity, malformed request, or replay risk returns deny before planning. |
| Governor | Synchronous OPA-style policy evaluation, deny/allow decision, policy version freshness | Missing, stale, contradictory, or timed-out policy returns deny and enters recovery. |
| Router | Lane assignment and conflict detection | Ambiguous lane or denied capability cannot reach Planner. |
| Planner | Graph construction with nodes, edges, dependencies, stop conditions, retry budgets | Node missing capability, timeout, fallback, or approval state is invalid. |
| Executor | Controlled task execution only after policy and dependency checks | Executor cannot self-authorize and cannot run unapproved sensitive actions. |
| EvalOps | Confidence, quality, drift, and safety scoring | Low confidence or denied eval result halts the node. |
| Audit Ledger | Immutable allow, deny, retry, approval, rewind, and final-disposition events | Audit sink outage fails closed; no silent buffering. |
| Recovery Controller | Halt, downgrade, rewind, or resume after clean policy and state checks | Poisoned workflow resets to the last safe checkpoint only. |

## Policy Semantics

Policy is evaluated synchronously at the boundary, before execution. The executable scaffold models these invariants in `PolicyGovernor`:

- **Deny by default:** no explicit grant means no execution.
- **Deny overrides allow:** explicit deny rules win even when a grant exists.
- **Stale policy cannot execute:** if the required policy bundle version is newer than the active sidecar version, the request is denied with `refresh_policy_cache` recovery guidance.
- **Signed approvals for sensitive actions:** high and critical risk capabilities require a single-use signed approval envelope before execution.
- **Audit durability is mandatory:** if the ledger cannot write the policy decision, Percival enters deny-all recovery.

```python
from percival_v9 import AuditLedger, Capability, PolicyGovernor, SignedApproval
from percival_v9.internal.policy.engine import Risk

governor = PolicyGovernor(ledger=AuditLedger())
governor.deploy_policy_bundle("bundle-v10.0")
governor.grant("agent-1", Capability("execute_external", Risk.HIGH))

decision = governor.evaluate("agent-1", "execute_external")
assert not decision.allow  # signed approval required

governor.approve_signed(SignedApproval(
    identity="agent-1",
    capability="execute_external",
    signer="operator:commander-7",
    signature="sig:detached-ed25519-placeholder",
    policy_version="bundle-v10.0",
))
assert governor.evaluate("agent-1", "execute_external").allow
```

## Execution Semantics

The Planner emits an explicit graph. Every node must declare input, output, required capability, timeout, retry policy, approval state, dependencies, and failure fallback. A node may not run until prerequisites are complete and policy has already allowed the capability.

```python
from percival_v9 import AuditLedger, ExecutionGraph, PlanNode, RetryPolicy

graph = ExecutionGraph(
    graph_id="mission-graph-001",
    ledger=AuditLedger(),
    nodes={
        "triage": PlanNode(
            node_id="triage",
            input_ref="event.raw",
            output_ref="event.triaged",
            required_capability="read_metrics",
            timeout_ms=1000,
            retry_policy=RetryPolicy(max_attempts=1, timeout_ms=1000),
        ),
        "external": PlanNode(
            node_id="external",
            input_ref="event.triaged",
            output_ref="action.package",
            required_capability="execute_external",
            timeout_ms=2000,
            retry_policy=RetryPolicy(max_attempts=2, timeout_ms=2000),
            approval_state="signed_required",
            failure_fallback="rewind_last_safe_checkpoint",
            dependencies=("triage",),
        ),
    },
)
```

## Recovery Semantics

Recovery Mode is a first-class state, not a cosmetic fallback. Percival halts or rewinds under these conditions:

- policy bundle is stale or contradictory;
- audit ledger cannot durably append;
- a node starts before dependencies are satisfied;
- a Temporal/LangGraph workflow is poisoned, stalled, or inconsistent;
- EvalOps returns deny or confidence below threshold;
- telemetry is unavailable for anything beyond approved low-risk read-only tasks.

The scaffold implements deterministic checkpoint rewind with `ExecutionGraph.rewind_last_safe_checkpoint()`. In production this maps to Temporal reset/rewind commands and an immutable recovery event in the ledger.

## Observability and Traceability

Percival v10 emits trace spans for request ingress, policy decision, lane classification, plan generation, approval gating, execution node start/stop, retry, rewind, and final disposition. `TraceContext` preserves correlation IDs across gateway, policy, orchestration, and execution services so every action can be reconstructed.

## Validation and Safety

The v10 regression suite proves:

- deny rules override allow rules;
- stale policy cannot execute until cache refresh;
- unauthorized external actions are blocked without signed approval;
- signed approvals are single-use;
- audit sink outage causes fail-closed behavior;
- graph dependencies are enforced;
- poisoned workflows can be rewound safely to the last checkpoint;
- graph audit outage halts execution.

## Full-Stack Implementation Notes

- **Gotham:** receives only governed case updates and operational intelligence products after signed approval gates.
- **Foundry:** stores policy bundle metadata, ontology-backed execution plans, lineage, and immutable eval slices.
- **AIP:** invokes Percival tools only through Governor-checked capability envelopes and produces self-improvement proposals as drafts, never self-deployments.
- **Apollo:** deploys policy bundles atomically, invalidates sidecar caches, canaries runtime changes, and rolls back to the previous approved bundle on drift or failed eval gates.

Percival v10 exists to function as ClearGlassInc Artemis's governed intelligence substrate: modular, observable, least-privilege, signed, audit-ready, and recoverable.
