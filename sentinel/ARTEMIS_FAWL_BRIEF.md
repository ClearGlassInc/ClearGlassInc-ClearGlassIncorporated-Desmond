# ARTEMIS // FAWL — Governed Self-Healing Lifecycle Control Plane

> **A**utonomous **R**esilience **T**riage, **E**xecution, **M**onitoring &
> **I**ncident **S**afety // **F**ail-closed **A**uthorized **W**orkflow **L**ifecycle.
> The governance spine the PHOENIX recovery engines plug into: PHOENIX decides
> *what* to remediate; ARTEMIS // FAWL decides *whether an action may run at
> all*, drives the incident through an **enforced** state machine, and mints a
> single-use, short-lived, narrowly-scoped capability for each approved action.

- **Executable:** `sentinel/sentinel/artemis_fawl.py` (pure stdlib, fail-closed)
- **Tests:** `sentinel/tests/test_artemis_fawl.py` (27 property tests)
- **CI gate:** `.github/workflows/phoenix-self-heal.yml` (Phoenix Self-Heal)
- **Private surface:** `sentinel/ARTEMIS_FAWL_COMMAND_SURFACE.html` (noindex; not in `sitemap.xml`)
- **Run it:** `python -m sentinel.artemis_fawl` · `--json`

## What it adds (that the recovery engines assume but don't enforce)

### 1. Enforced lifecycle state machine
The full lifecycle with an explicit allowed-transition table. Illegal
transitions raise `InvalidTransition`; every accepted transition is persisted to
the hash-chained audit log with actor, timestamp, evidence, correlation id, and
reason.

```
DETECTED → VALIDATING → CORRELATED → CLASSIFIED → CONTAINMENT_PENDING →
CONTAINED → PLAN_GENERATED → AUTHORIZATION_PENDING → EXECUTING → VERIFYING →
RECOVERED → MONITORING → CLOSED
```
Failure / safety paths: `ESCALATED`, `ROLLBACK_PENDING → ROLLING_BACK →
ROLLED_BACK`, `QUARANTINED`, `MANUAL_INTERVENTION_REQUIRED`. The emergency kill
switch (`StateMachine.quarantine`) is the only way off the happy path from an
arbitrary active state — and it is audited too.

### 2. Automation safety levels 0–4 + fail-closed Policy Decision Point

| Level | Meaning | Default disposition |
|---|---|---|
| 0 | Observe (read-only) | PERMIT — even under the kill switch |
| 1 | Low / reversible | PERMIT when confidence ≥ tau |
| 2 | Bounded production | REQUIRE_APPROVAL (approval + high confidence to permit) |
| 3 | Human authorized | Explicit human authorization only |
| 4 | Prohibited | DENY — always, for everyone |

The `PolicyDecisionPoint` evaluates actor, confidence, blast radius, recovery
budget, the kill switch, and the AI-safety boundary. **Any unverifiable term
denies.** An AI-originated action can never self-authorize at level ≥ 2.

### 3. Short-lived capability tokens
`CapabilityBroker.issue()` mints a token bound to exactly one action against one
target, with a TTL and an idempotency key, redeemable exactly once. No token ⇒
no execution. Scope mismatch, expiry, or reuse all raise `CapabilityError`.

## Recovery-control matrix (per action)

| Control | Where |
|---|---|
| Trigger / classification | PHOENIX (`phoenix.py` / `selfheal.py`) |
| Required evidence + confidence threshold | `PolicyContext.confidence` / `tau`, `tau_high` |
| Authorization level | `Action.safety_level()` → `PolicyDecisionPoint` |
| Blast-radius ceiling | `PolicyContext.blast_radius` / `blast_ceiling` |
| Recovery budget / loop guard | `PolicyContext.recovery_budget_remaining` |
| Idempotency key + least-privilege scope | `CapabilityToken` |
| Independent verification | injected `verifier`; failure ⇒ rollback |
| Rollback + escalation | `FawlOrchestrator._rollback` → `ESCALATED` |
| Kill switch | `PolicyContext.kill_switch` / `StateMachine.quarantine` |
| Immutable attribution | hash-chained `audit.AuditLog` |

## AI-safety boundary (enforced)

Model output is treated as untrusted input. AI may summarize, rank causes, and
propose plans, but the code prevents it from self-authorizing: any action with
`ai_originated=True` at safety level ≥ 2 is forced to `REQUIRE_APPROVAL` unless a
human actor supplies an approval token. AI never grants capabilities, never
bypasses the PDP, and never declares recovery — verification is independent.

## Wiring it to real systems

The orchestrator is adapter-driven. To operate for real:
1. Feed PHOENIX-classified incidents in as `IncidentInput` with a candidate `Action`.
2. Provide `executor(action, token)` that performs the real remediation only
   after validating the capability token, and a `verifier(action)` that
   independently re-probes health.
3. Persist the `AuditLog` transitions and decision receipts to durable storage.
4. Regenerate the command-surface snapshot with `python -m sentinel.artemis_fawl --json`.

Nothing here executes an irreversible or high-impact action without explicit
human authorization, and nothing moves money or changes pricing — by
construction and by test.
