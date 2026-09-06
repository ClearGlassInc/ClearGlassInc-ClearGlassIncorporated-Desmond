# ClearGlassInc Artemis

<div align="center">

![ClearGlassInc Artemis](assets/images/clearglass-logo.png)

## Governed intelligence infrastructure for decisions that cannot afford guesswork

**Fuse operational data, deploy policy-constrained AI agents, and preserve human authority at every consequential action.**

[**Explore the live platform →**](https://www.clearglassinc.com/) · [**Review the Artemis architecture →**](docs/clearglassinc_artemis_self_evolving_platform.md) · [**Start a discussion →**](https://github.com/ClearGlassInc/ClearGlassInc.github.io/discussions)

[![Website](https://img.shields.io/badge/Website-Live-00e5ff?style=for-the-badge)](https://www.clearglassinc.com/)
[![License](https://img.shields.io/badge/License-See%20LICENSE-8b5cf6?style=for-the-badge)](LICENSE)
[![Security](https://img.shields.io/badge/Security-Policy-39ff88?style=for-the-badge)](SECURITY.md)
[![Contributions](https://img.shields.io/badge/Contributions-Welcome-f8fafc?style=for-the-badge)](CONTRIBUTING.md)

</div>

---

ClearGlassInc Artemis is an engineering monorepo and live product surface for secure automation, defensive intelligence, governed commerce, and high-assurance agent systems. It turns fragmented data and workflows into auditable decision support—without allowing model output to manufacture authority.

> [!IMPORTANT]
> **See the system, then inspect the evidence.** Visit the [live ClearGlassInc experience](https://www.clearglassinc.com/), explore the implementation map below, and star the repository if governed agentic systems belong in your technical radar.

## Why this matters

Most AI demonstrations optimize for fluent output. Mission-critical systems must optimize for **traceable evidence, bounded authority, reversible deployment, and measurable operator trust**. Artemis treats AI output as untrusted until deterministic policy checks and, where required, explicit human approval make the next transition valid.

### What makes Artemis different

| Ordinary AI project | ClearGlassInc Artemis |
| --- | --- |
| Chat interface as the product | Ontology, policy, agents, approval, audit, and deployment as one system |
| Model confidence as authority | Evidence lineage and deterministic authorization outside the model |
| Autonomous action by default | Read-only analysis → draft → human approval → governed execution |
| Architecture claims without boundaries | Implemented components are separated from clearly labeled target-state blueprints |
| One-shot launch | Operational docs, tests, security gates, and an evolving product surface |

## Platform highlights

- **Governed agent workflows** — typed tools, risk-scored transitions, approval queues, and append-only material-action records.
- **Full-stack intelligence design** — operator interfaces, Python services, ontology contracts, retrieval, event processing, and model routing.
- **Palantir-aligned blueprint** — precise roles for Gotham, Foundry, AIP, and Apollo without implying unverified provisioning.
- **Secure-by-construction controls** — need-to-know access, zero-trust boundaries, provenance, rollback, and policy-as-code.
- **Production delivery surfaces** — GitHub Pages, containerized services, CI gates, health checks, and independently deployable applications.

## Start here

| Your goal | Best entry point |
| --- | --- |
| Experience the brand and products | [Visit clearglassinc.com](https://www.clearglassinc.com/) |
| Understand the end-to-end platform | [Read the self-evolving Artemis blueprint](docs/clearglassinc_artemis_self_evolving_platform.md) |
| Inspect Gotham / Foundry / AIP / Apollo alignment | [Read the Palantir AIP blueprint](docs/clearglassinc_artemis_palantir_aip_blueprint.md) |
| Evaluate defensive agent governance | [Explore Sentinel](sentinel/README.md) |
| Review governed commerce automation | [Explore ClearGlass Commerce](clearglass-commerce/README.md) |
| Help shape the roadmap | [Open a feature request](https://github.com/ClearGlassInc/ClearGlassInc.github.io/issues/new?template=feature_request.md) |

---

## Vision

ClearGlassInc exists to build systems that increase autonomy, intelligence, operational efficiency, and ownership.

The objective is not temporary trends.

The objective is infrastructure.

We engineer frameworks that merge:

- Artificial Intelligence
- Automation
- Blockchain Systems
- Digital Asset Infrastructure
- High-performance Software
- Strategic Information Systems
- Licensing Models
- Scalable Revenue Architecture

---

## Core Philosophy

- Forward is the only direction.
- Precision over noise.
- Systems over chaos.
- Ownership over dependency.
- Execution over theory.

ClearGlassInc operates with a long-term mindset focused on resilient architecture and strategic technological positioning.

---

# Primary Areas

## AI Systems

Development of intelligent automation systems using:

- LLM integrations
- Autonomous workflows
- Multi-agent orchestration
- Predictive analysis
- Data intelligence pipelines

---

## Cryptocurrency Infrastructure

Research and deployment involving:

- Trading systems
- Blockchain integrations
- Smart contracts
- Wallet infrastructure
- On-chain analytics
- Tokenized ecosystems
- Decentralized finance frameworks

---

## Software Engineering

Production-grade development focused on:

- Backend systems
- API architecture
- Cloud deployment
- Secure infrastructure
- Performance optimization
- Scalable distributed systems

---

## Automation

Automation frameworks designed to reduce friction and maximize leverage.

Includes:

- Business automation
- AI-assisted execution
- Infrastructure scripting
- Workflow orchestration
- Monitoring systems
- Autonomous operational tooling

---

# Technology Stack

## Languages

- Python
- JavaScript
- TypeScript
- Solidity
- Go
- Bash

## Infrastructure

- Docker
- Linux
- GitHub Actions
- Kubernetes
- Cloudflare
- PostgreSQL
- Redis

## AI / ML

- OpenAI APIs
- Local LLM deployment
- Vector databases
- Embedding pipelines
- Retrieval systems

## Blockchain

- Ethereum
- Solana
- LayerZero
- Smart contracts
- Web3 integrations

---

# Repository Structure

This repository is a website and engineering monorepo. The active top-level entry points are:

| Path | Purpose | Primary checks |
| --- | --- | --- |
| `index.html`, `*.html`, `assets/` | Static GitHub Pages website and product pages. | `python scripts/site_reliability_audit.py` |
| `artemis/` | Installable Artemis Python package and environmental risk module. | `python -m pytest artemis/tests` |
| `deployment/artemis/` | Containerized Artemis FastAPI model-service deployment. | `uvicorn deployment.artemis.app.main:app` / Docker build |
| `bots/`, `scripts/`, `tests/` | Operational automation bots, repository audits, release/content tooling. | `python -m pytest tests` |
| `sentinel/` | Sentinel defensive intelligence package and tests. | `python -m pytest sentinel/tests` |
| `clearglass-commerce/` | Commerce control plane plus Storefront/Admin Next.js apps. | `pytest control-plane/tests`; `npm ci && npm run build` in each frontend |
| `apps/autostore/` | Autostore control plane, cockpit UI, and Docker Compose deployment. | `docker compose`; `npm ci && npm run build` in `cockpit` |
| `services/clearglass_agent_service/` | Render-deployed lawful risk-intelligence API service. | Docker build / `/health` |
| `.github/workflows/` | CI/CD workflows for tests, audits, Pages, commerce, policy, security, and scheduled bots. | GitHub Actions |
| `docs/`, top-level `*.md` | Long-form architecture, governance, and product documentation. | Markdown review |

## Local static-site run

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Python tooling

The Python packages and bots target Python 3.11+ unless a package-specific README says otherwise. The root pytest configuration now includes the major Python test roots.

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e .[test]
python -m pip install -r requirements.txt
python -m pytest -q
```

## Frontend tooling

Each Next.js app is intentionally self-contained. Install dependencies in the app directory before building.

```bash
cd clearglass-commerce/storefront && npm ci && npm run build
cd ../admin && npm ci && npm run build
cd ../../apps/autostore/cockpit && npm ci && npm run build
```

## Stripe product-catalogue sync

`scripts/sync-stripe-products.ts` reads the products published on the GitHub
Pages site and creates or updates the matching Stripe Products and Prices. It
reads structured data only — it never scrapes rendered HTML for a price — and it
is idempotent: running it ten times produces the same one Stripe Product per SKU.

**Every run is a dry run until you pass `--apply`.** Nothing is ever deleted.

### Product sources and their schemas

| `--source` | File | Shape |
|---|---|---|
| `side-store` | `side-store.html` | `<script id="catalog" type="application/json">` — the same JSON island the page itself renders |
| `store` | `data/store/catalog.json` | Generated from `store.html` by `scripts/store_sync.py` |
| `pricebook` | `clearglass-commerce/control-plane/app/data/pricebook.json` | Commerce control-plane price book — **opt-in**, see below |

Default is `side-store,store` (everything on Pages). `--source all` adds the
price book. A `side-store` entry looks like this:

```json
{
  "id": "sku_001",
  "sku": "USB-C-C-1M",
  "name": "USB-C to USB-C Cable 1m",
  "category": "USB Cables",
  "price": 6.99,
  "description": "60W fast-charge, braided."
}
```

`sku` and `name` are required. `price` is major units (dollars) and is converted
to integer cents on the decimal string, not by multiplying a float. `image` or
`images` are optional; relative paths resolve against the Pages base URL. There
is no stock field, so no inventory status is sent to Stripe — the sync will not
invent availability it cannot read.
`data/store/catalog.json` differs in one way that matters: its `amount_cents`
is already in minor units, and its `price_display` copy is what decides whether
the amount is exact or quote-driven.

The price book is opt-in because its offers already name Stripe Prices in the
**live** account. Those ids mean nothing against a test key, so the sync verifies
any source-supplied id against the target account before reusing it and falls
back to creating a fresh record when it does not resolve.

### How the mapping works

| Source | Stripe |
|---|---|
| `<adapter>:<sku>` | `product.metadata.source_id` — the stable external identifier |
| Page URL of the listing | `product.metadata.source_url` |
| `owner/repo` | `product.metadata.source_repository` |
| sha256 of the normalised product | `product.metadata.source_hash` — drives update-vs-no-op |
| `name`, `description`, `images` | Product `name`, `description`, `images` |
| `category` | `product.metadata.source_category` |
| inventory status, **only where a source states one** | `product.metadata.inventory_status` |
| One variant | One Price, tagged `price.metadata.variant_key` |
| `price` / `amount_cents` | `unit_amount`, integer minor units |
| Billing interval, where the source states one | `price.recurring` |

Everything this tool creates carries `metadata.managed_by = clearglass-site-sync`,
and that marker is what the sync searches on. There is one deliberate exception:
when a source *names* a Stripe id — as the price book does — that id is checked
against the target account and adopted if it resolves, marker or not. That is the
point of the hint: those Stripe objects predate this tool and it must not create
second copies of them. Adoption is still narrow — a hinted Product owned by a
different `source_id` is refused, and a hinted Price that charges something other
than what the source says **blocks that product** rather than minting a new Price
at the source's amount. Unmarked, unhinted Stripe records are never touched,
adopted, or reported as orphans.

Orphan reporting is scoped to the sources a run actually read. A
`--source side-store` run will not describe your price-book products as removed
from the site — it never looked at them.

Lookup is by `source_id` over a full paginated `products.list`, not
`products.search`: the search index is eventually consistent, and a stale miss
there would create a duplicate. Creates additionally carry a content-derived
idempotency key, so a run that dies mid-flight and is retried reuses the
original object rather than minting a second one.

### Prices change by addition, never mutation

A Stripe Price is immutable in amount and currency. When a listed price changes,
the sync creates a **new** Price and leaves the old one active — existing
subscriptions keep billing against it. Pass `--deactivate-old-prices` to retire
the superseded Price once you have confirmed nothing references it; without the
flag, the plan still lists it so you can see what was left behind.

A product removed from the site produces an `orphan-warning` row. It is never
archived or deleted automatically — archive it in the Stripe Dashboard if that
is what you want.

### Running it locally

```bash
npm ci

# Review the mapping with no credential and no network at all:
npm run sync:stripe -- --source all --offline

# Dry run against your Stripe test account (reads Stripe, writes nothing):
export STRIPE_SECRET_KEY=sk_test_...
npm run sync:stripe

# Write to Stripe test mode:
npm run sync:stripe -- --apply

# One source, and retire superseded prices:
npm run sync:stripe -- --source side-store --apply --deactivate-old-prices

npm test          # offline, fully mocked — no Stripe credential required
npm run typecheck
```

Options: `--source`, `--apply`, `--live`, `--deactivate-old-prices`,
`--offline`, `--check-images`, `--base-url`, `--repository`, `--currency`,
`--report`, `--expect-plan-hash`, `--json`, `--help`. Exit codes: `0` clean,
`1` a product failed or needs manual correction, `2` refused for a configuration
or safety reason.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `STRIPE_SECRET_KEY` | for anything that reaches Stripe | Read from the environment only. Never commit it, never put it in client-side JS. |
| `ALLOW_STRIPE_LIVE_SYNC` | only for `--live` | Must be exactly `true`. |
| `SITE_BASE_URL` | no | Pages origin. Defaults to `https://www.clearglassinc.com`. |
| `GITHUB_REPOSITORY` | no | Written to `source_repository` metadata. |

The runtime dependency surface is deliberately small — `stripe`, `typescript`,
and `@types/node`, nothing else. `npm run sync:stripe` compiles with `tsc` and
runs the output rather than transpiling on the fly, which keeps a bundler (and
its transitive dependencies) out of the tree entirely.

`typescript` sits in `dependencies` rather than `devDependencies` on purpose:
`clearglassinc-military-op.yml` runs `npm ci` with `NODE_ENV=production`, which
omits dev dependencies, and the type check and tests must still run there.

### Test mode versus live mode

Test mode is the default and needs nothing but an `sk_test_…` key. Live mode
requires **three independent signals to agree**, and any two without the third
is a refusal:

1. `--live` on the command line,
2. `ALLOW_STRIPE_LIVE_SYNC=true` in the environment,
3. a genuinely live (`sk_live_…` / `rk_live_…`) secret key.

A live key with no `--live` is also refused, so a mis-filed secret cannot quietly
write to production. In CI there is a fourth gate: the applying live job is bound
to the `stripe-live` environment and reads a separate `STRIPE_LIVE_SECRET_KEY`.

**Live changes go plan → approve → apply, and the approval is bound to the plan.**
The workflow computes the live plan in a job with no environment gate, which
writes nothing and publishes the plan plus its `plan_hash` to the run summary.
Only then does the applying job request `stripe-live` approval — so the reviewer
is approving a plan they can read. That job recomputes the plan and passes
`--expect-plan-hash`; if the catalogue or the Stripe account moved in between, the
hash no longer matches and the run stops with exit 2 rather than applying changes
nobody signed off on. `live=true, apply=false` gives you the live plan on its own.

### Running it from GitHub Actions

`.github/workflows/sync-stripe-products.yml` runs on `workflow_dispatch` with
`apply` (default `false`) and `live` (default `false`) inputs, plus `sources` and
`deactivate_old_prices`. It installs with `npm ci`, runs the type check and the
test suite **before** any sync job, and uploads the JSON report as a workflow
artifact. Test-mode runs are a single job; live runs split into the planning and
applying jobs described above. It also runs automatically after a successful
`Deploy Pages` run — as a dry-run drift check, which cannot write because
`workflow_run` carries no inputs.

To add the credential: **Settings → Secrets and variables → Actions → New
repository secret**, named `STRIPE_SECRET_KEY`, holding your `sk_test_…` key.
For live sync, add `STRIPE_LIVE_SECRET_KEY` as a secret **on the `stripe-live`
environment** (Settings → Environments), and add a repository *variable*
`ALLOW_STRIPE_LIVE_SYNC` set to `true`. Keeping the opt-in in a variable rather
than an input means turning live sync on is a separate, auditable act from
requesting a run.

The secret is never interpolated into a `run:` script, never printed, and never
reaches the report. Any key-shaped string in an error message is redacted before
it is logged.

### Recovering from a failed sync

The script is safe to re-run: that is the recovery procedure. A failure on one
product is recorded and the rest of the catalogue continues, so a partial run
leaves a consistent Stripe account, not a half-written one.

1. Read `stripe-sync-report.json` (the workflow artifact) — `failures` names what
   broke, `manual_correction_required` what was withheld for bad source data,
   `blocked` what Stripe itself contradicted, and `resolved` the exact Product
   and Price ids that were written before the run stopped. Nothing in the report
   contains credential material; the whole document is redacted before it is
   written.
2. Fix the source data, or the Stripe-side cause.
3. Re-run the dry run and confirm the plan says what you expect.
4. Re-run with `--apply`. Content-derived idempotency keys mean products that
   already synced are not duplicated; they show as `product-unchanged`.

If the plan reports `several Stripe products claim this source_id`, the sync
refuses to apply until you merge them by hand in the Dashboard — it will not
guess which record is the real one. Nothing in this tool deletes a Stripe object,
so a bad run is always recoverable by editing the source and syncing again.

### Products that currently need manual correction

Three engagements in `data/store/catalog.json` are withheld because their listed
price is a floor rather than an amount: `hardening` ("from CAD $2,500"), `phipa`
("from CAD $3,000") and `monitoring` ("from CAD $600 / month"). A Stripe Price
needs one exact number. Give each a fixed amount in `store.html` and re-run
`python scripts/store_sync.py --write`, or leave them as quote-driven
engagements outside Stripe.

## Continuous integration

Workflows in `.github/workflows/` cover the active CI/CD paths, including:

- `ci.yml` — Python tests, Ruff lint, site reliability audit, workflow doctor, and OSINT deck validation.
- `sync-stripe-products.yml` — manual Stripe catalogue sync (dry run by default) plus a post-deploy drift check.
- `pages.yml` — GitHub Pages deployment for the static site.
- `commerce-frontend-ci.yml` and `commerce-deploy.yml` — commerce frontend validation and deployment.
- `auto-store.yml` — Autostore validation/deployment path.
- `security.yml`, `api-security-audit.yml`, `policy-gate.yml`, `release-supply-chain.yml`, and `ip-protection-scan.yml` — security, policy, and supply-chain checks.
- Scheduled automation workflows such as `bot-orchestrator.yml`, `content-pipeline.yml`, `control-surface-feeds.yml`, `defender-watch.yml`, and `health-monitor.yml`.

## Documentation

The canonical index of long-form documentation lives in `docs/README.md`. Notable entry points:

- Corporate and governance: `docs/clearglassinc_artemis_enterprise_corporate_layer.md`
- Platform architecture: `docs/clearglassinc_artemis_palantir_aip_blueprint.md`
- Self-evolving platform spec: `docs/clearglassinc_artemis_self_evolving_platform.md`
- Secure deployment agent prompt: `CLEARGLASS_SECURE_DEPLOYMENT_AGENT_PROMPT.md`
- Executive profile: `docs/desmond_otieno_odhiambo_executive_profile.md`

Top-level `*.md` blueprints (e.g. `ARTEMIS_INTELLIGENCE_PLATFORM_BLUEPRINT.md`, `CLEARGLASSINC_ARTEMIS_PRODUCTION_ARCHITECTURE.md`) are historical snapshots kept for reference.

## Security

Report vulnerabilities privately to **clearglass369@gmail.com**. Scope, response SLAs, and safe-harbor terms are defined in `SECURITY.md`.

## Leadership

Founder & Chairman **Desmond Otieno Odhiambo**. See `docs/Desmond_Otieno_Odhiambo_executive_profile.md`.

## Architecture Blueprints

- [ClearGlassInc Artemis full-stack intelligence blueprint](CLEARGLASSINC_ARTEMIS_FULL_STACK_INTELLIGENCE_BLUEPRINT.md)
- [ClearGlassInc Artemis local SEO and multi-channel growth intelligence plan](CLEARGLASSINC_ARTEMIS_LOCAL_SEO_GROWTH_PLAN.md)

## ClearGlass Growth Entity

Run the local manual-review growth command system with PowerShell 7:

```powershell
pwsh -ExecutionPolicy Bypass -File .\ClearGlass-GrowthEntity.ps1 -Mode Sample -OpenFolder
pwsh -ExecutionPolicy Bypass -File .\ClearGlass-GrowthEntity.ps1 -Mode Full -OpenFolder
```

The script creates `ClearGlassGrowthEntity/` with configuration, content scoring exports,
daily posting briefs, finance action files, and logs. It is intentionally a planning and
compliance-review system only; do not store passwords, tokens, cookies, or API secrets in it,
and do not use it for fake engagement, mass DMs, scraping, or platform-bypass behavior.

## Threads Growth Command Center V3

Run the Python-first, compliant Threads growth command center locally:

```bash
python -m bots.threads_growth_command_center --mode all --brand-name ClearGlassInc --root-path ./ThreadsGrowthCommandCenter_V3
python -m bots.threads_growth_command_center --mode add-kpi --root-path ./ThreadsGrowthCommandCenter_V3 --followers 100 --posts 3 --replies 40 --likes 80 --reposts 10 --impressions 1000 --profile-visits 25 --notes "Manual daily closeout"
```

The system creates a 30-day content calendar, daily manual execution brief,
copy-editing draft files, KPI tracker, engagement tracker, backups, and a
self-contained HTML dashboard. It is intentionally a planning, drafting, and
measurement system only: zero botting, zero scraping, no automated follows,
likes, comments, reposts, DMs, or storage of platform cookies/session tokens.

---

## Use cases

- **Operational intelligence:** triage signals, correlate evidence, and prepare reviewable decision packages.
- **High-assurance automation:** separate analysis, drafting, authorization, execution, and audit.
- **Defensive monitoring:** operate bounded, fail-closed agents over approved data and tools.
- **Governed commerce:** automate low-risk work while preserving approval for financial and material actions.
- **Architecture research:** evaluate ontology, agent, policy, deployment, and self-improvement patterns without confusing target state with deployed fact.

## Evidence, not invented social proof

Evaluate ClearGlassInc Artemis through its public code, tests, threat models, release history, and live product surfaces. Testimonials, customer logos, performance claims, and adoption metrics should appear here only when they are attributable, permissioned, and verifiable.

> [!NOTE]
> Palantir-aligned documents describe an integration architecture. They do not, by themselves, prove that Gotham, Foundry, AIP, Apollo, coalition infrastructure, or production environments are provisioned.

## Roadmap

- Harden reproducible evaluation fixtures for governed agent transitions.
- Expand ontology-driven examples with explicit confidence, temporal state, and lineage.
- Improve operator-facing provenance and approval explanations.
- Publish measurable performance and reliability evidence when reproducible data exists.
- Continue accessibility, Pages reliability, security, and supply-chain improvements through existing review gates.

Roadmap items are proposals, not promises or evidence of deployment. Track concrete work through [issues](https://github.com/ClearGlassInc/ClearGlassInc.github.io/issues) and [releases](https://github.com/ClearGlassInc/ClearGlassInc.github.io/releases).

## Frequently asked questions

### Is Artemis fully autonomous?

No. Artemis is designed to automate bounded analysis and drafts while keeping deterministic policy and human authorization at consequential boundaries.

### Is every architecture blueprint already deployed?

No. Target-state documents are specifications. Source code, runtime checks, deployment records, and explicit status labels define what is implemented.

### Is ClearGlassInc affiliated with Palantir?

This repository does not claim an affiliation. Gotham, Foundry, AIP, and Apollo name the intended responsibilities in a Palantir-aligned integration design.

### How can I contribute?

Read [CONTRIBUTING.md](CONTRIBUTING.md), follow the [Code of Conduct](CODE_OF_CONDUCT.md), and select a narrowly scoped issue. Include the checks you actually ran and preserve all governance boundaries.

### How do I report a security issue?

Follow [SECURITY.md](SECURITY.md) and use the private reporting route. Do not disclose vulnerability details in a public issue or Discussion.

## Help advance governed agent engineering

- **Star** the repository if you want to find the architecture again.
- **Watch releases** if you want meaningful milestone notifications.
- **Fork and remix** a trust-boundary diagram for your domain, then share the evidence and assumptions in Discussions.
- **Challenge an invariant** with a reproducible failure case or focused issue.
- **Share responsibly:** send another engineer the [governance architecture](docs/clearglassinc_artemis_self_evolving_platform.md), not an unsupported slogan.

The complete, ethics-first launch sequence, channel copy, experiments, metrics, and automation boundaries live in the [GitHub Growth and Launch Playbook](docs/GITHUB_GROWTH_LAUNCH_PLAYBOOK.md).

## License and contact

See [LICENSE](LICENSE) for repository terms and check subtree-specific documentation before reuse. For product discovery, visit [www.clearglassinc.com](https://www.clearglassinc.com/). Use GitHub Discussions for public technical questions and [SECURITY.md](SECURITY.md) for vulnerabilities.
