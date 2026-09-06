# AgentOps Architecture

ClearGlass AgentOps is structured as a small monorepo for operational bot work.

## Flow

1. Bot API receives status/debug/deploy commands.
2. Agent core creates an internal run object.
3. Policy engine validates the requested operation.
4. Connectors execute approved integrations.
5. Audit and reports are written for traceability.
6. Infrastructure templates remain staged until real cloud targets are configured.
