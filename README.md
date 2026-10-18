# ClearGlass Inc.

This repository is a multi-application monorepo, not a single runtime. Components have separate toolchains and deployment boundaries. Integrate them through explicit, documented interfaces; do not try to import or start every component from one process.

## System map

| Component | Location | Stack / entry point | Integration boundary and status |
|---|---|---|---|
| Public static site | Repository root (`*.html`, `*.css`, `*.js`, `assets/`) | Static HTML/CSS/JavaScript; `tools/build_pages.py` prepares a Pages artifact | GitHub Pages workflows exist. Repository instructions record branch-based Pages publishing as the fallback because Actions jobs are not receiving runners. `netlify.toml` is also present, so confirm the custom domain's actual serving provider before changing hosting. |
| Commerce control plane | `control-plane/` | Python 3.11, FastAPI, SQLAlchemy, Pydantic Settings | Independent API and test suite; Render is the documented deployment target. Current production reachability is not verified by this README. Payment, approval, audit, and webhook safeguards must remain intact. |
| Customer storefront | `storefront/` | Independent Next.js app with its own `package.json` and lockfile | Separate install/build/start lifecycle; do not merge into the root Next.js application by assumption. |
| Operator admin | `admin/` | Independent Next.js app with its own `package.json` and lockfile | Separate lifecycle and security boundary; preserve existing login and authorization checks. |
| Root signal-fabric application | Root `package.json` | Next.js; `npm run dev` serves port `3030`; `npm run build`, `npm run start`, `npm run typecheck`, and `npm test` are declared | A separate application from the static site and the `storefront/` and `admin/` apps. `docs/ARCHITECTURE.md` records no registered deployment workflow for this root app. |
| Agent, automation, and intelligence modules | `agents/`, `agent_army/`, `artemis/`, `artemis_platform/`, `bots/`, `sentinel/`, `tools/` | Python tooling, with additional package-specific runtimes | Invoked through specific scripts and workflows. Keep execution boundaries, environment requirements, and approval controls explicit; do not start every agent as a side effect of application startup. |
| Additional independent systems | `apps/`, `services/`, `clearglass-ai-proxy/`, `delos-os/`, `clearglassinc_sdk/`, and other package subtrees | Package-specific Node.js, Python, and Rust manifests | Each component owns its documented install/test/build lifecycle. There is no evidence of one universal install/build/start command covering the full repository. |

## Prototype scope

The repository's existing prototype note remains in force: **prototype fixtures are synthetic; no real incidents are included.** The documented prototype stack is Next.js, TypeScript, Tailwind, Prisma, PostgreSQL, Zod, Docker Compose, and Jest. This statement does not establish that every listed service is provisioned or deployed.

## Validation and operational guidance

Start with the repository runbook and baseline rather than assuming that all workflows are runnable:

- [`AGENTS.md`](AGENTS.md) — repository-wide engineering and preservation rules.
- [`CLAUDE.md`](CLAUDE.md) — project-specific execution, safety, and deployment constraints.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — component boundaries and request/data flows.
- [`docs/BASELINE.md`](docs/BASELINE.md) — known failures, verified findings, and risk register.
- [`docs/RUNBOOK.md`](docs/RUNBOOK.md) — install and validation commands for the affected component.
- [`docs/audit/2026-10-01/INTEGRATION_MAP.md`](docs/audit/2026-10-01/INTEGRATION_MAP.md) — external integration inventory and credential names (never secret values).

The local mirror of the primary CI gates is declared in `scripts/ci_local.py`:

```bash
python3 scripts/ci_local.py
python3 scripts/ci_local.py --list
```

Run package-specific checks from that package's directory, following `docs/RUNBOOK.md`. These commands are documented entry points, not a claim that tests passed in the current environment.

## Current verification caveat

At repository commit `10c3d912f3774c946f7c8935882ff82556f5d402` (2026-10-18 review), recent GitHub Actions jobs were failing before any step appeared and their job logs were unavailable. This matches the previously documented runner-dispatch blocker. Until an authorized repository/organization administrator resolves it, a failed Actions job cannot be interpreted as an application-test result, and a green local check does not establish successful production deployment. Do not switch the Pages source, deploy, publish, or change production configuration based on this README.
