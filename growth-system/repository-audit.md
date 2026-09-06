# ClearGlass Burlington Cyber Market Repository Audit

## Current state

- The repository is a GitHub Pages marketing site plus multiple independently deployed backend/control-plane systems.
- Existing governance doctrine in `CLAUDE.md` requires read-only analysis, draft generation, human approval, and append-only auditability for consequential automation.
- Existing Python bots and tests provide a compatible pattern for stdlib-only deterministic control modules.

## Implementation decision

This increment adds a governed Burlington growth-system layer without rewriting the homepage or commerce systems. It uses configuration, structured campaign data, deterministic Python controls, static command-center UI, and focused tests.

## Assumptions

- Campaign packages are drafts until Desmond or an authorized operator approves publication, outreach, ad launch, budget changes, or third-party integrations.
- Live market research and personal-data collection must run through approved tools outside committed repository data.
