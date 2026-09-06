# ClearGlassInc Artemis Enterprise Architecture Agent

This package defines a governed agent that combines three accountable roles:

- **Enterprise architect** — aligns business capabilities, domain boundaries,
  data governance, platform strategy, and migration decisions.
- **Principal engineer** — turns decisions into production-ready, Python-first
  implementation plans, contracts, code, tests, and operational controls.
- **Engineering manager** — structures work into priorities, milestones,
  dependencies, owner roles, review gates, and measurable outcomes.

## Package contents

| File | Purpose |
| --- | --- |
| `agent.json` | Discoverable identity, modes, permissions, and non-negotiable guardrails. |
| `system_prompt.md` | Mission, architecture standards, Palantir-native design mode, self-improvement doctrine, and response contract. |
| `developer_prompt.md` | Deterministic runtime, approval, evidence, and precision-implementation rules. |

## Recommended runtime pattern

1. Load the manifest and prompts from private, least-privilege server-side
   storage; do not ship confidential source prompts to a browser bundle.
2. Bind every run to an authenticated actor, tenant, purpose, compartments,
   allowed tools, time and cost budgets, and a correlation ID.
3. Start new integrations in advisory or audit-only mode.
4. Enforce access and action policy outside the model, adjacent to each protected
   data read and side effect.
5. Require artifact-bound human approval before consequential execution or
   promotion of a self-improvement candidate.
6. Record redacted, append-only evidence for intake, decisions, approvals, tool
   calls, versions, results, and rollback state.

## Status

This is an agent definition and target operating contract, not evidence that a
Palantir tenant, connector, model, workflow, or deployment has been provisioned.
Runtime adapters must be implemented and verified against the authorized
ClearGlassInc Artemis environment before operational use.
