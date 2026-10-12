# DELOS OS

Design reality. Test every outcome.

DELOS OS is ClearGlass Inc.'s synthetic-world simulation command center. This folder is isolated from the existing site application to avoid changing root scripts, routes, or current workflows.

## Operation Glassfall

The demo models a 72-hour synthetic enterprise crisis with seven bounded personas, scripted defensive injects, human approval recording, risk scores, a global stop, checkpoint/fork/restore, a replayable timeline, and Markdown/JSON after-action exports.

## Local run

Run these commands from this folder:

- npm install
- npm run dev
- npm test
- npm run typecheck
- npm run build

The app uses port 3031 in development. It stores prototype state in local browser storage on that browser only. Clear the browser storage to reset; the UI also offers a reset control.

## Important boundaries

This is a working UI and deterministic simulation prototype, not a production control plane. It does not use external LLM APIs, tools, production systems, credentials, payment systems, customer data, or external networks. Approval decisions are recorded as synthetic decisions only. There is no server-side database or authenticated multi-user identity in this increment.

The Prisma schema, API specification, governance policy, and 30-day plan describe the production path. Do not run migrations or enable integrations until database access, authentication, tenant isolation, approval enforcement, and non-production deployment context are verified.

## Main directories

- app: command console
- lib: typed state model, scenario fixture, simulation transitions, report generation
- tests: unit tests for policy gates and simulation behavior
- prisma: future PostgreSQL data model
- docs: architecture, API, governance, delivery gates
