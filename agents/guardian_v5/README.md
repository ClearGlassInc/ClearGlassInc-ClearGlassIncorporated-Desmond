# ClearGlass Guardian v5.0

ClearGlass Guardian v5.0 is the governed Intelligence Command Interface for ClearGlass AgentOps. It is designed for enterprise-safe command execution, bounded autonomy, human approval gates, DLP controls, and structured auditability.

## Package Contents

- `system_prompt.md` — production system prompt for the Guardian v5 agent.
- `developer_prompt.md` — developer/runtime behavior contract.
- `tool_schema.json` — governed tool schema for deterministic orchestration.

## Runtime Pattern

Guardian v5 should be deployed behind a governed orchestration layer. The recommended execution pattern is:

1. Classify intent.
2. Plan a bounded workflow.
3. Evaluate policy.
4. Execute only approved low-risk actions.
5. Escalate high-risk or irreversible actions for approval.
6. Verify completion with evidence.
7. Write structured audit events.

## Default Controls

- Five-step bounded execution plan by default.
- Human approval for irreversible or externally visible actions.
- Deterministic tool usage before open-ended reasoning.
- Audit-only mode for new integrations.
- No raw secret logging.
- DLP inspection on prompts, tool inputs, intermediate data, and outputs.

## Intended Integration Targets

- Microsoft Agent Framework for orchestration, middleware, checkpointing, and human-in-the-loop controls.
- Azure AI Foundry for approved model execution.
- Copilot Studio for low-code enterprise user experience.
- Microsoft Purview, Entra ID, and Power Platform DLP for governance.

## Status

Initial production prompt package. Treat this as the source of truth for Guardian v5 behavior until runtime middleware and service code are added.
