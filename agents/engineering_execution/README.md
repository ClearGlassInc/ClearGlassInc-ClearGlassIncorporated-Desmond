# ClearGlass Engineering Execution Agent

A staff-engineer / engineering-manager agent for shipping production-grade
software and running technical delivery with clarity and precision.

- **`agent.json`** — manifest (role, modes, pipeline, operating principles,
  safety model, response template), matching the layout used by the other
  agents in `agents/`.
- **`system_prompt.md`** — the full system prompt: core operating principles,
  coding standards, engineering-management standards, response format, and
  behavior rules.

## What it does

Assesses requests, recommends the best approach, breaks work into concrete
steps with milestones and dependencies, writes clean production-ready code
with explicit error handling and tests where appropriate, and closes every
response with risks, edge cases, validation steps, and the next best action.

## Guardrails

Never hallucinates APIs, behaviors, or dependencies; states uncertainty
plainly; preserves existing behavior unless a change is requested; and abides
by the repo-wide rules — no secrets in commits and no weakening of the
commerce OS approval gates or audit ledger.
