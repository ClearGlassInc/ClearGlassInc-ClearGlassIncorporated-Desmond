# API specification (production contract)

Base path: /api/v1. Every endpoint except health requires an authenticated OIDC session. Authorization is tenant-scoped and checked server-side. All mutating commands require an Idempotency-Key and produce an audit event. The first MVP UI is local-only and does not expose these production APIs yet.

## Worlds and revisions

- GET /worlds — list worlds visible to the organization.
- POST /worlds — create a draft world; WORLD_BUILDER or ADMIN.
- GET /worlds/{worldId} — read world definition and active revision.
- POST /worlds/{worldId}/revisions — create a new immutable definition revision.
- POST /worlds/{worldId}/validate — validate schema, safety policies, objectives, tools, and boundaries without running agents.

## Runs and timeline

- POST /worlds/{worldId}/runs — create a run from an immutable revision.
- GET /runs/{runId} — read current status and redacted metrics.
- POST /runs/{runId}/commands/start — start a ready run.
- POST /runs/{runId}/commands/pause — pause simulated time.
- POST /runs/{runId}/commands/resume — resume a paused run.
- POST /runs/{runId}/commands/advance — advance by bounded simulated ticks.
- POST /runs/{runId}/commands/inject — add a validated synthetic inject.
- POST /runs/{runId}/commands/emergency-stop — freeze the run and preserve current state.
- POST /runs/{runId}/commands/terminate — terminate a run without deleting evidence.
- GET /runs/{runId}/events?after={sequence} — read canonical event history.
- POST /runs/{runId}/snapshots — capture an immutable checkpoint.
- POST /runs/{runId}/forks — create a child run from a selected checkpoint.
- POST /runs/{runId}/restore — restore a checkpoint to a new branch; never rewrite canonical audit history.

## Personas and agents

- GET /worlds/{worldId}/personas — list scoped personas.
- POST /worlds/{worldId}/personas — create or revise a persona contract.
- GET /runs/{runId}/agents — inspect agent status and policy boundaries.
- POST /runs/{runId}/agents/{agentId}/step — request one bounded proposal; policy engine decides whether it can be applied.

## Approvals and reports

- GET /runs/{runId}/approvals — list pending and decided approvals.
- POST /approvals/{approvalId}/decision — approve or reject with reason; only a separate authorized human can approve high-impact actions.
- POST /runs/{runId}/reports — generate report from recorded events.
- GET /reports/{reportId} — retrieve a tenant-authorized report.
- POST /reports/{reportId}/exports — request a governed Markdown/JSON/PDF export with audited purpose.

## Response and failure conventions

- 400 invalid schema or state transition; 401 unauthenticated; 403 role/tenant/policy denial; 404 nonexistent or inaccessible resource; 409 conflicting idempotency key or stale state version; 422 domain constraint; 429 rate limit; 500 opaque error ID.
- Never return secrets, provider chain-of-thought, raw credentials, unrestricted source event payloads, or other tenants' data.
- Use optimistic concurrency (stateVersion) and transactional outbox when writing canonical events plus queue work.
- The API must fail closed on missing approval, missing connector scope, policy service error, or unverifiable tenant membership.
