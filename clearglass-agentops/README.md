# ClearGlass AgentOps

Repository workspace for the AgentOps bot system.

## Layout

- `apps/bot-api` — API surface for bot operations.
- `apps/copilot-extension` — extension entrypoint.
- `packages/agent-core` — orchestration primitives.
- `packages/policy-engine` — policy checks before debug/deploy tasks.
- `packages/connectors` — integration adapters.
- `packages/audit-logger` — run records and compliance events.
- `packages/schemas` — shared JSON schemas.
- `infra/bicep` — Azure Bicep templates.
- `infra/terraform` — Terraform templates.
- `docs/architecture` — architecture notes.
- `docs/runbooks` — operating procedures.
- `docs/compliance` — compliance controls.

## Commands

```bash
cd clearglass-agentops
npm run doctor
npm run debug
npm run deploy
```
