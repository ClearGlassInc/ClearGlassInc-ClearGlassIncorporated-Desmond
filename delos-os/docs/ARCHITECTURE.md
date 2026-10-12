# DELOS OS architecture

Tagline: Design reality. Test every outcome.

## Product vision in five points

1. Give operators one command center to create and control synthetic worlds for strategy, cyber resilience, crisis response, product testing, and training.
2. Make simulated world state explicit, revisioned, replayable, and forkable so decisions can be compared against a common baseline.
3. Give every persona a bounded identity, objective, knowledge boundary, memory scope, permission set, risk level, and approval requirement.
4. Place governance in the execution path: default-deny tools, human approvals for high-impact actions, an emergency stop, and a traceable audit record.
5. Turn every run into decision intelligence: timeline, risk changes, approval quality, objective progress, missed opportunities, and actionable recommendations.

## Text architecture diagram

Operator browser
  -> Next.js command console (presentation only; local demo state for MVP)
  -> AuthN / AuthZ middleware (production gate; OAuth/OIDC + tenant-scoped RBAC)
  -> Simulation API (validate command, authorize role, idempotency key, audit intent)
  -> Policy Decision Point (allow / require approval / deny)
  -> Simulation Kernel (deterministic state transitions and versioned snapshots)
  -> Event log + audit chain (append-only writes; PostgreSQL)
  -> Redis queue / worker pool (future asynchronous persona turns and replay jobs)
  -> Persona Runtime (provider-agnostic; schema-validated outputs)
  -> Tool Gateway (deny-all by default; sandbox and explicit allow-list only)
  -> Report Generator (Markdown/JSON first; PDF after renderer testing)
  -> Observability (structured logs, metrics, traces, redacted payloads)

The browser prototype intentionally bypasses no production policy: it has no external connectors, no LLM credentials, no customer-data ingestion, and no tool-execution gateway. The PostgreSQL schema and API contract are design artifacts until migrations, authentication, tenant isolation, and a server-side database are wired and tested.

## Layer boundaries

- World Forge: validates a world definition and immutable revision.
- Persona Engine: validates persona schemas and knowledge/tool boundaries.
- Agent Operations: state reads and proposals only; all proposed actions enter the policy gate before mutation.
- Narrative Director: produces scenario injects; cannot amend canonical history except through an audited event.
- Reality Engine: applies deterministic domain events; a provider response is a proposal, never executable authority.
- Command Console: reads state and issues authenticated operator commands.
- Governance Core: role checks, approval separation of duties, global stop, retention, audit hash chain, and export authorization.
- Intelligence: creates reports from recorded facts, labeling assumptions and unresolved items.
