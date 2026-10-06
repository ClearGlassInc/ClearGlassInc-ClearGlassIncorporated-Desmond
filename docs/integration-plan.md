# ClearGlass Operations Platform — Integration Plan

## Phase 1 — Repository discovery and threat model
**Status: IMPLEMENTED**
- Discovery recorded.
- Threat boundaries documented.
- New functionality isolated under `lib/operations`, `app/operations`, `app/api/operations`.
- Sensitive modules are feature-flagged and default off.
- Mock/live separation is explicit.

## Phase 2 — Incident → assignment → evidence → audit
**Status: IMPLEMENTED / MOCKED**
- Synthetic tenant/principal.
- Incident creation.
- Human-controlled assignment.
- Evidence ingestion with SHA-256.
- Evidence version and custody event.
- Incident status transition.
- Audit history.
- Reviewer readback of the complete timeline.

### Runtime mode
- Development/test default: `mock`.
- Production default: `blocked` unless `CLEARGLASS_OPERATIONS_APPROVED=true` and a future live persistence/auth adapter is configured.
- Mock data is synthetic and explicitly labelled.

## Phase 3 — Background processing / authorized artifact analysis
**Status: NOT STARTED**
Planned adapter boundary:
- isolated worker
- resource limits
- restricted network
- read-only source input
- job timeout/cancellation
- tool version capture
- structured findings and provenance

No forensic tool is assumed to be installed.

## Phase 4 — Voice intake
**Status: NOT STARTED**
Provider-neutral interfaces are present in `lib/operations/providers.ts`. Candidate vendors require current availability, licensing, pricing, retention, regional processing, and security verification before activation.

## Phase 5 — Operational assignment / real-time
**Status: NOT STARTED**
The core domain model already treats assignment and status changes as audited events. Real-time transport should reuse the repository's existing transport only if it meets the authorization boundary.

## Phase 6 — Recognition modules
**Status: BLOCKED BY DESIGN**
LPR and biometric verification remain disabled by default and are not connected to external sources in this phase.

## Phase 7 — Hardening / recovery
**Status: NOT STARTED**
Requires a durable persistence provider, backup/restore procedure, failure injection tests, and production identity integration.

## Rollback
The branch is additive. Rollback is a branch/commit revert with no production migration applied. The draft SQL migration is documentation-only until an approved database exists.
