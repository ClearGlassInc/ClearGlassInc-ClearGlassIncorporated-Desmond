# ClearGlass Project Board — Defense-in-Depth Security Audit

**Scope:** `project-board.html`, `project-board.js`, `project-board.css`, and `data/project-board/board.json`.

**Assessment date:** 2026-09-18.

## Executive finding

The Project Board is currently a **static, browser-only console**. Its data source is a same-origin committed JSON feed and its editable state is stored in browser `localStorage`. There is no Project Board server API, database, identity provider, session service, or mutation endpoint in this surface.

That architecture creates an important trust-boundary limitation:

- UI controls are not an authorization boundary.
- `localStorage` is attacker-controlled client state and must not be treated as authoritative.
- The committed JSON feed is public/static data, not a protected business-data API.
- RBAC, ownership checks, server-side schema validation, durable audit logging, idempotency, optimistic concurrency, encrypted PII storage, refresh-token rotation, and server-side rate limiting cannot be truthfully certified or implemented inside the existing static console without introducing a backend and changing the data architecture.
- This hardening pass therefore adds **fail-closed client-side validation at the local-state trust boundary** and documents the server-side controls as explicit pre-production blockers rather than simulating them.

## 1. Threat model

### Attack surface

1. Same-origin JSON feed: `/data/project-board/board.json`.
2. Browser DOM/event handlers in `project-board.js`.
3. Native task dialog inputs: title, column, board, dates, priority, assignees, subtasks.
4. Drag/drop and keyboard task movement.
5. Browser `localStorage` key `cg.projectboard.v1`.
6. JSON export/download functionality.
7. Static activity, timesheet, calendar, velocity and member data rendered into the DOM.
8. Any future API or external integration added to the board.

### Trust boundaries

**Untrusted → renderer:** committed feed and localStorage are parsed into JavaScript objects.

**Untrusted → mutation model:** task dialog values and DOM-selected IDs become task objects.

**Renderer → browser storage:** edited task state is serialized to localStorage.

There is currently **no server-side trust boundary** for task/sprint/timesheet mutations.

### Primary threats

| Threat | Current exposure | Control |
|---|---|---|
| Stored XSS through task text | Reduced: renderer uses DOM nodes/textContent | Preserve and regression-test |
| Malformed localStorage causing renderer faults/resource abuse | Previously permissive | **Hardened: strict shape, length, ID, enum and referential validation** |
| Forged assignee/board/column/sprint IDs | Client-controlled | **Hardened client-side; server-side authorization still absent** |
| Oversized task/subtask payload | Client-controlled | **Hardened with bounded counts/lengths** |
| ID collision on rapid task creation | Timestamp-based | **Hardened with crypto.randomUUID when available** |
| RBAC/IDOR/BOLA | No server API | **Not implemented; backend required** |
| Authentication/session theft | No Project Board auth/session | **Not applicable to current static surface; backend required for protected deployment** |
| Tamper-evident audit trail | No durable server log | **Not implemented; backend required** |
| Duplicate mutation/retry | No server mutation | **Not implemented; backend required** |
| Race-condition/concurrent writes | Browser-local only | **Not implemented; backend/versioning required** |
| Field-level encryption | No server-side PII store | **Not implemented; backend/KMS required** |
| TLS 1.3 enforcement | Hosting-layer concern | **Deployment control, not browser JS** |

## 2. Authentication and authorization

**Required before treating this as a multi-user internal system:**

- OIDC/OAuth2 or equivalent identity provider.
- Short-lived access/session tokens.
- Refresh-token rotation where refresh tokens are used.
- HttpOnly, Secure, SameSite cookies for browser sessions; no bearer credentials in localStorage.
- API-layer RBAC.
- Object-level authorization for every task, sprint, timesheet and subtask mutation.
- Explicit tenant/workspace ownership checks.
- Rate limiting and brute-force controls on login/session endpoints.
- Server-side authorization independent of UI visibility.

No client-side check is considered an authorization control.

## 3. Input validation and injection defense

The browser now rejects malformed local state and mutation input before it is rendered or persisted:

- bounded task and subtask counts;
- bounded title/subtask lengths;
- strict task ID format;
- strict ISO calendar dates;
- start/end ordering;
- enumerated priorities;
- referential checks for columns, boards, sprints and assignees;
- duplicate task-ID rejection;
- rejection of malformed localStorage snapshots.

The renderer continues to use text nodes rather than assigning task/user content through `innerHTML`.

For a real multi-user system, repeat the same validation at the API boundary using a strict server schema library (for example Pydantic or Zod) and parameterized database access.

## 4. Data protection

The current static board does not persist a server-side timesheet/PII database. Therefore AES-256-GCM field encryption cannot be meaningfully added to this surface without inventing a storage service.

For a backend implementation:

- TLS 1.3 at the ingress/load-balancer boundary where supported.
- AES-256-GCM or an equivalent approved authenticated-encryption scheme for sensitive fields.
- KMS/vault-managed data-encryption keys.
- Secrets only from environment/secret-manager injection.
- No credentials, access tokens, or database secrets in browser storage.

## 5. Audit and observability

A production backend must emit structured audit events for task/sprint/timesheet create/update/delete containing actor, action, object ID, timestamp, authorization context, request/correlation ID, and redacted before/after state.

Audit records should be append-only/tamper-evident and protected separately from application writers.

Alert candidates:

- burst/mass deletes;
- repeated authorization failures;
- privilege changes;
- off-hours privileged operations;
- repeated invalid mutation payloads;
- unusual cross-workspace/object access.

The static board cannot provide a trustworthy durable audit trail.

## 6. Resilience and integrity

A future API mutation contract should require:

- Idempotency-Key on create/import/bulk mutation requests.
- Server-side version/ETag or integer revision on update/delete.
- Conflict response on stale versions rather than last-write-wins.
- Timeouts, bounded retries and circuit breakers for external dependencies.
- Durable transaction boundaries for task + timesheet updates.

The current browser-only implementation has no external mutation dependency to wrap with a circuit breaker.

## 7. Supply chain

The repository contains multiple independent Node/Python applications. Supply-chain verification must be scoped per application rather than assuming the Project Board's static JavaScript has an npm dependency graph.

Required CI gates for the protected application/backend lane:

- ESLint security configuration where ESLint is used.
- Bandit for Python services.
- Semgrep with a reviewed ruleset.
- npm audit/Snyk for Node applications.
- lockfile verification.
- lockfile-based SBOM generation (CycloneDX or SPDX).
- secret scanning with gitleaks or equivalent.
- pinned GitHub Actions by reviewed full commit SHA.

## 8. Testing standard

The existing Project Board tests already cover feed referential integrity, UI wiring, accessibility-related invariants and the no-`innerHTML` rendering invariant.

This hardening adds a dedicated security-contract test layer for:

- valid state acceptance;
- wrong schema;
- oversized title;
- oversized subtask;
- malformed dates;
- reversed date range;
- unknown IDs;
- duplicate IDs;
- malformed assignee lists;
- invalid priority;
- excessive task/subtask counts;
- XSS payloads remaining inert because rendering uses text nodes.

For a future API, each externally supplied field must additionally receive at least three adversarial cases: injection, oversized input, and malformed type.

## Verification language

A control is **VERIFIED** only when executable evidence exists for it.

Controls marked **backend required** above are intentionally **NOT VERIFIED** in this static console. No claim of RBAC, authenticated sessions, server-side authorization, encryption-at-rest, durable audit logging, idempotency, concurrency control, or server-side rate limiting should be inferred from the client-side hardening.

## Change-scope guarantee

This pass is additive/minimal. Existing valid task data and UI behavior remain supported. No existing page, route, feed field, visual surface, or unrelated feature is intentionally removed or redesigned.
