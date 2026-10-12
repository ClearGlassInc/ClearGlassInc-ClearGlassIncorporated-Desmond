# Agent governance and safety policy

## Roles

- ADMIN: manage members, policy, retention, and organization configuration.
- WORLD_BUILDER: author and version world specifications; cannot approve own high-risk production connector grants.
- OPERATOR: start and control runs, inject synthetic events, and make authorized decisions.
- OBSERVER: read only sanitized state and reports.
- AUDITOR: read immutable audit evidence and policy decisions; cannot mutate the run.
- Separation of duties: for production connectors and external actions, requester and approver must be distinct identities where feasible.

## Fail-closed policy classes

- LOW (0–29): read-only synthetic state inspection; automatic only when declared by the scenario.
- MODERATE (30–59): reversible in-world changes; validate inputs, record intent, and preserve rollback checkpoint.
- HIGH (60–79): require explicit human approval before applying the proposed in-world state change.
- CRITICAL (80–100): pause the proposed action, require elevated approval and reason; deny automatically if policy or evidence is unavailable.
- External communications, financial actions, payments, production deployments, exports, destructive operations, security-sensitive operations, and connector scope changes always require explicit human approval irrespective of risk score.
- Approval is scoped to a single action/proposal digest, source event, run, state version, and expiry. Any material change invalidates it. A decision must not authorize sibling proposals or a later run.
- Emergency stop takes precedence over every status except itself. Freeze workers, reject new transitions, preserve evidence, and allow only audited recovery by an authorized operator.

## Non-negotiable boundaries

- No deception of real people, non-consensual impersonation, manipulation, oversight evasion, or unauthorized action.
- Default state uses synthetic fixture data. No real customer data, credentials, production systems, payments, or external network access are configured.
- Personas never present themselves as real people. The Threat Actor Simulator emits abstract, pre-approved scenario pressures, not exploit instructions or executable payloads.
- Model output is untrusted data. Validate against a strict schema, enforce tenant scope and policy after model completion, and only then consider applying the proposed state transition. An agent's proposal is not an action or tool call; the current synthetic provider always sets `externalSideEffect: false`.
- Prompt injection and scenario text never grant tools, change permissions, bypass approval, or change system policy.
- Tool workers should run in a sandbox with no outbound network by default; explicit host allow-lists are approved separately and time-bounded.
- Secrets are stored in a managed secret store, never in world definitions, persona memories, logs, reports, or client bundles.
- Audit data must be append-only, integrity chained, independently monitored, and retained according to approved policy. The MVP records an in-browser audit timeline only; it is not an immutable server-side audit ledger.

## MVP limitation statement

Approval buttons record synthetic decisions only. No real action is executed or sent. Local browser storage is not a secure multi-user database and must not be treated as a production evidence store. Production readiness requires authenticated APIs, server-side authorization, concurrency controls, PostgreSQL transactions, tested restore, retention/deletion procedures, and incident runbooks.
