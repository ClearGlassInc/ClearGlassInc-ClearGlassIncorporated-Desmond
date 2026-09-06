# Compliance Controls

## Current safeguards

- Manual workflow dispatch for controlled execution.
- Node 20 runtime gate.
- Debug pass required before release manifest creation.
- JSON reports retained as deployment evidence.
- Infrastructure templates are stubs until real environment secrets are configured.

## Production gates still required

- Azure subscription and resource group confirmation.
- GitHub environment protection rules.
- Secret inventory and rotation schedule.
- Human approval before production deployment.
