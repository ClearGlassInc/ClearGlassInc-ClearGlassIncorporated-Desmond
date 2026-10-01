# Repository Inventory — 2026-10-01

**Commit:** `b53bfd7`. Counts from `git ls-files` (tracked files only). All
**VERIFIED** unless marked. `docs/ARCHITECTURE.md` describes how the parts fit;
this file lists what is there and how each part is run.

## Scale

| Measure | Count |
|---|---:|
| Tracked files | 2,583 |
| Files at the repository root | 687 |
| HTML pages (root: 119) | 215 |
| Python / TypeScript / JS / Markdown / Rust files | 632 / 147 / 115 / 677 / 2 |
| Root test modules / control-plane test modules | 143 / 23 |
| SQL migrations (`control-plane/migrations/`) | 10 (9 schema + `002_seed.sql`) |
| Workflows in `.github/workflows/` (archive in `workflows/`) | 85 (72) |
| Remote branches | 100+ (first API page); all `protected: false` |
| Repository visibility | **public** (GitHub API) |

## Deployable systems and how each one runs

| System | Path | Install | Build / check | Run locally | Deploys via | State |
|---|---|---|---|---|---|---|
| Static site | root `*.html`, `blog/`, `assets/`, `data/` | none | `python3 scripts/ci_local.py` | open files, or any static server | GitHub Pages, "Deploy from a branch", `CNAME` `www.clearglassinc.com` | **Live.** Pages run #253 deployed `b53bfd7` |
| Commerce control plane | `control-plane/` | `pip install -r requirements.txt` | `ruff check .`, `pytest tests/` | `uvicorn app.main:app --reload` | Render blueprint `render.yaml` (Docker) | **Not deployed** per 2026-09-24 (not re-verified) |
| Storefront | `storefront/` | `npm ci` | `tsc --noEmit`, `next build` | `npm run dev` | Render (Docker) | Not deployed (same source) |
| Admin | `admin/` | `npm ci` | same; `admin/tests/` via root pytest | `npm run dev` | Render (Docker) | Not deployed (same source) |
| Full local stack | `docker-compose.yml` | — | `docker compose config` | see `docs/RUNBOOK.md` §3 (corrected in this audit) | local only | Instructions were broken; fixed |
| Live-signal fabric | root `package.json` | `npm ci` | `npm run typecheck`, `npm test` | `next dev -p 3030` | none registered | Builds; not deployed |
| Rust secure-runtime sidecar | `agent_army/secure_runtime/` | `cargo` | `cargo test --locked` (5 pass) | — | invoked by `agent-army-crypto.yml` | Builds |
| AI proxy (Cloudflare Worker) | `clearglass-ai-proxy/` | `npm ci` | per `ai-proxy-deploy.yml` | — | `ai-proxy-deploy.yml` | Not verified this pass |
| Air control app | `clearglass-air-control/` | `npm ci` | — | — | none found | Lockfile audits clean |
| Artemis engineering app | `apps/artemis-engineering/` | `npm ci` | — | — | none found | Lockfile audits clean; outside every gate |

## Python subsystems (stdlib-first, run by tests or workflows)

`agent_army/`, `agent_os/`, `agents/`, `bots/`, `sentinel/`, `truth_forensics/`,
`tools/`, `scripts/`, `percival_v9/`, `qics/`, `shield/`, `xenolith/`,
`clearglass_agent_os/`, `clearglassinc_sdk/`, `services/clearglass_agent_service/`,
`deployment/artemis/app/`, `products/opal-koboi/`. Each is covered by modules in
`tests/` (143 in total); none has its own CI job beyond `ci.yml`'s `pytest tests/`.

## Dependency manifests

| Ecosystem | Manifests | Pinned | Audit result |
|---|---|---|---|
| npm | 6 lockfiles: root, `storefront`, `admin`, `apps/artemis-engineering`, `clearglass-ai-proxy`, `clearglass-air-control` | lockfiles | 0 vulnerabilities in all 6 |
| pip | 7 `requirements*.txt` + 2 `pyproject.toml` | `control-plane`: **0 of 9 pinned**; `sentinel`: 0 of 6; `products/opal-koboi`: 0 of 6; `deployment/artemis/app`: 10 of 10; root: 3 of 4 | `pip-audit`: 0 known in all 7 |
| Cargo | `agent_army/secure_runtime/Cargo.lock` | lockfile | not audited (`cargo-audit` absent); one future-incompat warning |

**Drift observed (RISK).** `control-plane/requirements.txt` has lower bounds
only. The set resolved today differs from the one the 2026-09-24 audit
verified a week ago:

| Package | 2026-09-24 | 2026-10-01 |
|---|---|---|
| stripe | 15.6.1 | **16.0.0** (major) |
| SQLAlchemy | 2.0.54 | **2.1.1** |
| FastAPI | 0.141.1 | 0.142.2 |
| Starlette | 1.7.0 | 1.3.1 |

All 739 control-plane tests pass on the new set, so no defect today. But the
next Docker build at deploy time installs whatever is newest, and nothing has
tested that.

## Configuration and environment

| File | Holds | Note |
|---|---|---|
| `control-plane/.env.example` | Every commerce variable, names only | `APP_ENV=development`, `AUTO_CREATE_TABLES=false`, `RUN_MIGRATIONS=false` |
| `.env.example` (root) | `LIVE_FABRIC_*`, `DATABASE_URL`, `REDIS_URL`, `OTEL_EXPORTER_OTLP_ENDPOINT` | Not the commerce surface. `DEPLOY.md` §B used to tell you to copy this one for compose |
| `.env.growth.example`, `clearglass-ai-proxy/.env.example` | Names only | — |
| `render.yaml` | 3 Docker web services + Postgres | Sets `RUN_MIGRATIONS=true`; `ADMIN_API_KEY` and `CRCS_AUDIT_HASH_KEY` `generateValue` |
| `docker-compose.yml` | Postgres 16 + 3 services, loopback only | Requires `.env`; sets only `DATABASE_URL` |
| `netlify.toml`, `fly.toml`, `_headers`, `_redirects` | Other hosts' config | Coexist with Pages (BASELINE R5). Pages is what serves the site |
| `.circleci/config.yml` | CircleCI pipeline | Self-declared **INERT**: not connected |
| `CODEOWNERS` | `*` and `/.github/workflows/` → `@ClearGlassInc` | Present; ineffective without branch protection |
| `.github/dependabot.yml` | Update schedule | Present |

No tracked `.env`, `.pem`, `.key`, `.p12` or `id_rsa` file. `scripts/secret_scan.py`: clean.

## Generated and uploaded material at the root

| Group | Count | Note |
|---|---:|---|
| Dated reports `2026MMDDTHHMMSS.{json,md}` | 144 | 72 pairs from 2026-05-15 to 2026-08-09, all from the 2026-09-06 upload; templated, distinct |
| Other `*.md` (blueprints, plans, prompts, READMEs) | 235 | Mostly strategy documents |
| PDF / XLSX / XLS / CSV / TXT / ZIP | 45 | Includes personal and third-party data: see `SECURITY_REVIEW.md` S-N2 |
| Images | 21 | Screenshots, logos, icons |

Because the repository is public and Pages publishes every tracked file
(`.nojekyll`), everything in this table is downloadable from both GitHub and
`www.clearglassinc.com`. `tests/test_no_prospect_files_published.py` guards one
pattern (`offers/outreach/lead-list-*.csv`) and nothing else.

## Entry points that run without a human

| Entry point | Trigger | Can write to the repo |
|---|---|---|
| 38 scheduled workflows | cron | 12 of them (`contents: write`) |
| `auto-heal.yml` | every workflow completion + `*/30` cron | yes, by branch + PR |
| `content-pipeline.yml` | after `Bot Orchestrator` | yes |
| `sync-stripe-products.yml` | after `Deploy Pages` | no (dry run) |
| Dependabot | GitHub-managed | PRs only |

Every one of these except Dependabot and Pages is currently inert (F1).
