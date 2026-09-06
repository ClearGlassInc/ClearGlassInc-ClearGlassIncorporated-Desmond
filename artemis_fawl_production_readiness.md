# ARTEMIS // FAWL production-readiness audit and control plan

ClearGlassInc Artemis // FAWL is a target-state autonomous resilience and recovery
platform founded by Desmond Otieno Odhiambo. This repository currently contains a
large GitHub Pages site, several agent/runtime prototypes, and governed commerce
subsystems. The safest high-value production step completed in this change is to
turn the incident recovery lifecycle into executable, tested policy code instead
of leaving it only as architecture prose.

## Executive assessment

Current maturity is **prototype-to-governed-runtime**: deterministic agent OS
modules already cover governance, planning, audit chains, intelligence confidence,
learning, and recovery classification, while several UI/docs surfaces remain
static demonstrations or target-state blueprints. Principal risks are unsafe
interpretation of target-state docs as deployed capability, incomplete production
source onboarding, and missing hard state-transition enforcement for autonomous
recovery workflows.

Strongest completed improvement: `agent_os.state_machine` now rejects invalid
recovery jumps, requires attribution and evidence for every accepted transition,
and appends every transition to the tamper-evident audit ledger.

## Architecture map

| Layer | Current repository evidence | Production boundary |
| --- | --- | --- |
| Operator interface | Static pages and FAWL UI under `artemis-fawl/` plus root marketing pages. | Must show live, stale, simulated, unavailable, and inferred states distinctly. |
| Agent runtime | `agent_os/` deterministic stdlib modules for governance, audit, planning, recovery, learning, and orchestration. | No external side effects; hands gated actions to approved executors only. |
| Policy decision point | `agent_os/governance.py` scores action risk and approval requirements. | Deny by default for unknown, low-confidence, evidence-free, money, production, data, access, secrets, and mass-outbound actions. |
| Incident lifecycle | `agent_os/state_machine.py`. | Signal → validate → correlate → classify → contain → plan → authorize → execute → verify → recover/rollback/escalate → close. |
| Audit plane | `agent_os/audit.py` hash-chain ledger. | Persist to append-only storage with access control and retention before production use. |
| Commerce runtime | `clearglass-commerce/` governed e-commerce OS. | Preserve read-only analysis → draft → human approval → execution. |
| Deployment | GitHub Pages plus independent app/workflow subtrees. | Release gates must validate docs do not imply undeployed capabilities are live. |

## Evidence-backed findings and disposition

| Priority | Finding | Impact / risk | Disposition |
| --- | --- | --- | --- |
| P0 | Incident recovery transitions were described in prompts/docs but not enforced in `agent_os` runtime. | Unsafe autonomous action paths can emerge if an executor assumes a plan may go directly from detection to execution. | Fixed with `IncidentStateMachine`, terminal states, allowed transition graph, required evidence, and audit append. |
| P1 | Recovery/audit code existed, but no lifecycle tests covered detect-to-close, rollback, invalid transitions, or missing attribution. | Regression could weaken authorization, verification, or rollback gates silently. | Added focused state-machine regression tests. |
| P1 | Production-readiness guidance is split across root docs, FAWL docs, commerce docs, and target-state architecture docs. | Operators or buyers may confuse static demos with deployed controls. | Added this control plan and updated runtime README. |
| P2 | Audit ledger is in-memory for `agent_os` demos. | Production evidence retention is not durable until backed by append-only storage. | Documented as a production boundary; not changed to avoid inventing infrastructure. |
| P3 | UI polish and commercial packaging remain broad. | Buyer-facing maturity is limited until real telemetry and deployment evidence exist. | Left as roadmap; no fake telemetry or claims added. |

## Recovery-control matrix

| Remediation action | Trigger | Required evidence | Confidence threshold | Authorization | Blast-radius limit | Timeout/retry | Rollback | Verification | Escalation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Validate signal | New incident signal | schema, source, timestamp, tenant/environment | Source-specific; missing confidence fails closed | Level 0 observation | Single incident/correlation ID | No retries for malformed input | Mark invalid/quarantine | Schema and provenance checks | ESCALATED or QUARANTINED |
| Correlate/classify | Validated signal | independent claims, topology, recent change, service health | Minimum evidence confidence only | Level 0/1 | Read-only data | Bounded query timeouts | None needed | Contradiction report | ESCALATED |
| Contain | Classified incident | affected asset, reversible control, owner | >= policy threshold | Level 1/2; human for high blast radius | Explicit service/feature/queue target | Bounded retries with backoff | Restore prior routing/flag state | Independent health probe | MANUAL_INTERVENTION_REQUIRED |
| Execute recovery | Approved recovery plan | policy decision, capability, idempotency key, rollback plan | >= policy threshold | Level 2/3 depending action | Explicit target and recovery budget | Worker timeout, cancellation, bounded retries | Compensating action | Technical and business checks | ROLLBACK_PENDING or ESCALATED |
| Roll back | Failed verification or operator override | failed postcondition, previous state | N/A | Same or higher than original action | Original affected target only | Bounded rollback retry | Manual restoration if rollback fails | Re-run independent probes | MANUAL_INTERVENTION_REQUIRED |
| Close | Monitoring confirms recovery | timeline, receipts, validation, operator note | N/A | Operator or policy-approved closure | Incident only | No retry loop | Reopen only as new incident | Audit chain verification | ESCALATED if evidence incomplete |

## Security model

- **Identity boundary:** automation actors, human operators, source connectors, and executors are distinct actors in transition records.
- **Policy boundary:** governance scoring and state transitions are deterministic code; model output can propose but cannot authorize or execute.
- **Secrets strategy:** no secrets are stored in source; production connectors must use runtime secret managers and short-lived capabilities.
- **Audit protection:** each accepted transition is appended to a SHA-256 hash chain. Production must persist this chain to append-only storage.
- **AI safety constraints:** AI output remains untrusted input. It may summarize, rank, and draft but may not grant capability, bypass policy, suppress alerts, declare recovery, or rewrite production policy without human review.
- **Residual risks:** repository docs still contain target-state architecture that is not deployed infrastructure; production source onboarding and durable audit storage remain backlog items.

## Verification report

Executed in this change:

```bash
python -m pytest tests/test_agent_os.py tests/test_agent_os_advanced.py -q
python -m pytest tests/test_agent_os.py tests/test_agent_os_advanced.py tests/test_agent_os_state_machine.py -q
```

Verified behavior:

- Happy-path incident lifecycle reaches `CLOSED` with a verified audit chain.
- Invalid `DETECTED -> EXECUTING` transition raises and does not mutate state or audit head.
- Missing actor/evidence/policy/correlation/reason is rejected.
- Rollback failure path reaches `ROLLED_BACK` with verified audit chain.

Not verified in this change:

- Full monorepo test suite, frontend builds, dependency audits, container starts,
  accessibility scans, and deployment workflows. These are broad, independently
  deployed surfaces and remain required before production release.

## Deployment and rollback guide

1. Deploy as a Python runtime/library change with no migrations.
2. Import `IncidentStateMachine` wherever a recovery controller needs lifecycle enforcement.
3. Start each incident with `IncidentStateMachine.start(...)` using source evidence and correlation ID.
4. Move through allowed transitions only after policy and evidence checks complete.
5. Persist `ledger.to_json()` to the production audit backend once one is available.
6. Rollback is code-only: revert the commit if integration causes unexpected behavior. No data migration is introduced.

Release health criteria:

- State-machine tests pass.
- Governance tests pass.
- Existing orchestrator tests pass.
- Any production executor proves it cannot execute before `AUTHORIZATION_PENDING -> EXECUTING` with an approved policy decision.

## Commercial roadmap

Shortest credible path to a paid pilot:

1. **Buyer:** small regulated operations team with incident-response pain and limited SRE/security automation staff.
2. **Problem:** slow triage, weak incident evidence, unsafe manual remediation, poor post-incident learning.
3. **Offer:** Community pilot: local signal intake, deterministic state machine, manual playbooks, audit timeline, and read-only dashboard.
4. **Required proof:** ingest two real authorized signal sources, detect one synthetic incident, generate a gated recovery plan, record immutable evidence, and close or roll back with operator approval.
5. **Estimated effort:** 2-4 focused engineering weeks for a narrow pilot if source access and owner approvals are available.
6. **Explicit exclusions:** no autonomous production deploys, payment operations, mass outbound, unrestricted shell/cloud access, coalition/military claims, or compliance certifications until independently implemented and verified.

## Remaining backlog

| Priority | Backlog item | Dependency |
| --- | --- | --- |
| P0 | Wire every future recovery executor through `IncidentStateMachine` and governance checks. | Executor implementation. |
| P1 | Add durable append-only audit persistence and replay verification. | Storage selection and retention policy. |
| P1 | Define versioned signal/source registry schema with owner, approver, legal basis, retention, freshness SLA, and allowed actions. | Product/security decision. |
| P1 | Add CI gate for FAWL/source registry semantics and target-state disclaimer checks. | Workflow update. |
| P2 | Build read-only API gateway for real authorized health/signal feeds. | Source credentials and tenant model. |
| P2 | Add operator dashboard states for live/stale/simulated/unavailable/inferred. | UI scope. |
| P3 | Add prompt/workflow A/B eval harness after deterministic controls are in place. | Evals dataset and review process. |
