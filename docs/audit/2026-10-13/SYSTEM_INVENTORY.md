# ClearGlass System Inventory & Product Integration Audit

**Discovery date:** 2026-10-13  
**Repository actually inspected:** `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond`  
**Target branch:** `feat/system-wiring-product-catalog` (additive audit branch)  
**Base commit:** `b5709c7bb10bc196b592537e21e94cfd65a65f73`  
**Base tree:** `cff3be174f4528e97ffaa2b6aff1b60a71f16559`  
**Inspection mode:** GitHub tree and file content, read-only before this document was added.

## Repository identity exception

The user-specified target `ClearGlasslabs/ClearGlassIncorporated-Desmond` returned GitHub 404. The closest verified match is `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond`, whose `main` branch contains the ClearGlass website, current product catalog, and the surrounding platform modules described here. This audit and any proposed change set must retain that repo mismatch in its PR metadata.

## Discovery counts

The recursive tree was complete (`truncated: false`): 3,452 entries, 2,938 files and 514 directories. It includes 119 root-level HTML pages; 82 entries in `data/products.json`; 96 GitHub Actions/CircleCI workflow files; 681 Python files; 425 JSON files; 133 TypeScript files; 104 JavaScript files; and 102 TSX files.

A tree entry proves the path exists at the audited commit; it does not prove the file was executed, the public page loads in a browser, an integration is connected, or a configured service is deployed.

## System inventory

| System / Product | Evidence paths | Type | User-facing? | Current status | Integration risk | Proposed catalog entry |
|---|---|---|---|---|---|---|
| ClearGlass public website | `index.html`, `netlify.toml`, `.github/workflows/pages.yml` | Static website | Yes | UNKNOWN / NEEDS REVIEW for live release health | High | Preserve homepage, route and SEO baseline |
| Product Command Center | `products.html`, `assets/js/product-command-center.js`, `assets/css/product-command-center.css` | Catalog UI | Yes | UNKNOWN / NEEDS REVIEW; live snapshot showed loading state | High | Retain canonical catalog page, validate browser rendering |
| Portfolio catalog | `data/products.json` | Product registry | Yes; consumed by Products page | 82 entries, no source/audience/verification fields | High | Extend current entries additively and preserve IDs/routes/order |
| Global navigation | `nav.js` | Shared navigation | Yes | 84 hard-coded items; 2 not in JSON catalog; XENOLITH absent | High | Preserve current items; reconcile without deleting destinations |
| SEO / route index | `sitemap.xml`, `robots.txt`, `llms.txt`, `feed.xml` | SEO metadata | Yes | 174 URLs in `sitemap.xml`; 7 existing catalog routes not in main sitemap | High | Review route/canonical status before additive updates |
| Platform naming registry | `data/platform/registry.json`, `platform/catalog/catalog-info.yaml` | Platform taxonomy | Mostly internal | Registry explicitly says taxonomy does not prove provisioning | Medium | Use as evidence of names only |
| Live Signal Fabric | `page.tsx`, `layout.tsx`, `lib/`, `package.json` | Next.js application | Possible UI; production hosting unknown | UNKNOWN / NEEDS REVIEW; source contains fail-closed/fallback copy | High | Label prototype/internal until live source is verified |
| Operations Platform | `app/operations/page.tsx`, `app/api/operations/route.ts`, `lib/operations/`, `tests/operations.test.ts` | Evidence/incident workflow | Source UI route exists | PROTOTYPE; mock store, no trusted live identity/durable store verified | High | Label synthetic/demo; don't claim production persistence |
| ARTEMIS codebase | `artemis/`, `deployment/artemis/`, `artemis_platform/` | Python APIs/agent tooling | Multiple UI surfaces; API deployment unknown | PROTOTYPE / UNKNOWN | High | Consolidate names and verify each distinct surface |
| ARTEMIS FAWL | `artemis-fawl/README.md`, `artemis-fawl/index.html`, `agents/artemis_fawl_revenue.py` | Static workflow/intelligence demo | Static page exists | BETA / DEMO; README says metrics simulated and no external execution | Medium–High | Add one clearly labelled demo entry; preserve synthetic disclaimer |
| DELOS OS | `delos-os/README.md`, `delos-os/app/page.tsx`, `delos-os/lib/`, `delos-os/tests/` | Synthetic-world simulator | Source UI exists; hosting unknown | PROTOTYPE; local browser storage, deterministic synthetic provider, no production control plane | High | Internal/prototype entry with contact CTA, no claim of live integration |
| OSINT Fraud Detection Dashboard | `apps/osint-fraud-dashboard/README.md`, `apps/osint-fraud-dashboard/src/app/`, `apps/osint-fraud-dashboard/docs/PRODUCTION_READINESS.md` | Case/evidence dashboard | Local UI/demo only | PROTOTYPE; synthetic fixtures, README says not deployed | High | Internal prototype entry; disclose synthetic-only data |
| AI Gateway | `clearglass-ai-proxy/README.md`, `clearglass-ai-proxy/src/`, `clearglass-ai-proxy/wrangler.toml` | Authenticated AI API proxy | API, no standalone public UI confirmed | PLANNED / IN DEVELOPMENT until deployment verified | High | Internal development entry; never expose provider credential values |
| AgentOps | `clearglass-agentops/README.md`, `clearglass-agentops/apps/`, `clearglass-agentops/packages/` | Agent orchestration, policy and connectors | Internal | PROTOTYPE / UNKNOWN; runtime not confirmed | High | Internal system entry, not an unverified public product |
| Private Agent Service | `services/clearglass_agent_service/README.md`, `services/clearglass_agent_service/main.py`, `fly.toml` | Python API | Backend; hosting unknown | UNKNOWN / NEEDS REVIEW; Fly config is not proof of deployment | High | Internal/private entry; do not expose endpoint URLs |
| Commerce control plane | `control-plane/app/main.py`, `control-plane/app/data/pricebook.json`, `control-plane/tests/` | FastAPI payments/orders/fulfillment/admin APIs | Backend only | UNKNOWN / NEEDS REVIEW; live transaction path not verified | Critical | Internal system entry; keep price authority separate |
| Commerce admin | `admin/app/`, `admin/lib/`, `render.yaml` | Admin/approval UI | Restricted admin UI design | INTERNAL / ADMIN; runtime unknown | Critical | No public dashboard link |
| Commerce storefront | `storefront/app/`, `storefront/lib/catalog.ts`, `storefront/package.json` | E-commerce frontend | Public-facing app source; live hosting unknown | UNKNOWN / NEEDS REVIEW | Critical | Keep commerce checkout routes/catalog separate |
| ClearGlass Shield harness | `shield/README.md`, `shield/g01_suite.py`, `shield/tests/` | Isolated security test harness | Not customer-facing | PROTOTYPE; README says non-production/disposable | High | Do not advertise as production security/VPN service |
| Governed AI Automation Kit | `product/automation-kit/README.md`, `product/automation-kit/tests/`, `product/automation-kit/validation/` | Internal toolkit | No; README says not public/marketplace/payment product | INTERNAL / ADMIN | Medium | Internal record only; publishing is outside current MVP authorization |
| Agents | `agents/*/agent.json`, `agents/*/system_prompt.md` | Role/agent definitions | Mostly internal | UNKNOWN / NEEDS REVIEW; prompts/manifests don't prove execution | High | Inventory capabilities, do not label all as live products |
| Bots | `bots/`, `bots/config/bot_registry.json`, `scripts/bot_runner.py` | Automation code | Mostly internal | UNKNOWN / NEEDS REVIEW; execution not confirmed | High | Internal registry only except separately verified public tools |
| CI/CD and scheduled automation | `.github/workflows/`, `.circleci/config.yml`, `workflows/` | CI, release, scheduled jobs | Internal infrastructure | UNKNOWN / NEEDS REVIEW; current scheduled runs include failures | Critical for release; high for integrations | Track system health separately; do not create product cards per workflow |
| Static-site deployment | `.github/workflows/pages.yml`, `.github/workflows/site-integrity-and-deploy.yml`, `netlify.toml` | Deployment config | Internal | UNKNOWN / NEEDS REVIEW for current serving status | Critical | Reuse current gates; never deploy during catalog change without approval |
| Commerce deployment | `render.yaml`, `.github/workflows/commerce-deploy.yml` | Hosting/deploy config | Internal | UNKNOWN / NEEDS REVIEW | Critical | Do not equate config with running service |
| IESO feed | `.github/workflows/ieso-public-feed.yml`, `scripts/ieso_public_feed.py`, `data/grid/ieso-public.json` | Public data refresh | Supports GridShield | UNKNOWN / NEEDS REVIEW; latest checked run failed | High | Keep freshness/provenance explicit; preserve last known snapshot |
| Service offers catalog | `data/store/catalog.json`, `store.html` | Commercial services | Yes | UNKNOWN / NEEDS REVIEW; five payment links present, successful checkout not verified | Critical | Keep separate from systems portfolio; do not claim payment availability |
| Side Store | `data/side-store/catalog.json`, `side-store.html`, `tools/side_store_catalog.py` | Physical SKU catalog | Yes | UNKNOWN / NEEDS REVIEW; 57 items | High | Maintain separate SKU schema |
| Catalog contract tooling | `tools/catalog_contract.py`, `tests/test_catalog_contract.py`, `docs/CATALOG_SCHEMA.md` | Validation utility | Internal | Code/tests exist; current execution not performed in this audit | High | Keep report-only until required commercial policy values are supplied |

## Existing portfolio catalog: complete inventory

All entries were present in `data/products.json`. A local `productUrl` whose file exists in the tree is evidence of a source destination, not a successful production route. Existing `available` values remain source data; assessed status does not promote any untested page to operational.

| ID | Product | Existing status | Evidence path | Proposed action |
|---|---|---|---|---|
| `cg-001` | XENOLITH | `available` | **UNKNOWN / NEEDS REVIEW** | `/xenolith.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-002` | Artemis IV Core | `available` | **UNKNOWN / NEEDS REVIEW** | `/artemis-iv.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-003` | Artemis VI | `available` | **UNKNOWN / NEEDS REVIEW** | `/artemis.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-004` | Artemis OS | `available` | **UNKNOWN / NEEDS REVIEW** | `/artemis-os.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-005` | Artemis 2040 | `available` | **UNKNOWN / NEEDS REVIEW** | `/artemis-2040.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-006` | Artemis Self-Evolving | `available` | **UNKNOWN / NEEDS REVIEW** | `/artemis-self-evolving-platform.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-007` | AI Cyber Intelligence | `available` | **UNKNOWN / NEEDS REVIEW** | `/artemis-ai-cyber-intelligence-platform.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-008` | AVALON · Artemis + Percival | `available` | **UNKNOWN / NEEDS REVIEW** | `/artemis-percival.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-009` | PERCIVAL OS | `available` | **UNKNOWN / NEEDS REVIEW** | `/percival-os.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-010` | SENTINEL | `available` | **UNKNOWN / NEEDS REVIEW** | `/sentinel.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-011` | GUARDIAN | `available` | **UNKNOWN / NEEDS REVIEW** | `/guardian.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-012` | ClearGlass NEXUS | `available` | **UNKNOWN / NEEDS REVIEW** | `/clearglass-nexus.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-013` | NEXUS v12 | `available` | **UNKNOWN / NEEDS REVIEW** | `/ClearGlass-NEXUS-v12-FINAL.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-014` | Intelligence Command Surface | `available` | **UNKNOWN / NEEDS REVIEW** | `/intelligence-command-surface.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-015` | Intelligence Interface | `available` | **UNKNOWN / NEEDS REVIEW** | `/intelligence-interface.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-016` | Flowsint | `available` | **UNKNOWN / NEEDS REVIEW** | `/flowsint.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-017` | Network Flow Intelligence | `available` | **UNKNOWN / NEEDS REVIEW** | `/clearglass.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-018` | Ontario OSINT Deck | `available` | **UNKNOWN / NEEDS REVIEW** | `/Ontario-osint.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-019` | Agent Mesh | `available` | **UNKNOWN / NEEDS REVIEW** | `/agentmesh.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-020` | AI Operator Workspace | `available` | **UNKNOWN / NEEDS REVIEW** | `/ai-operator.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-021` | CONDUIT | `available` | **UNKNOWN / NEEDS REVIEW** | `/conduit.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-022` | AutoMap | `available` | **UNKNOWN / NEEDS REVIEW** | `/automap.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-023` | Command Console | `available` | **UNKNOWN / NEEDS REVIEW** | `/command-console.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-024` | Event Control Surface | `available` | **UNKNOWN / NEEDS REVIEW** | `/saas-platform.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-025` | Systems Console | `available` | **UNKNOWN / NEEDS REVIEW** | `/systems.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-026` | Control Surface | `available` | **UNKNOWN / NEEDS REVIEW** | `/control-surface.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-027` | CG OS | `available` | **UNKNOWN / NEEDS REVIEW** | `/CG-os.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-028` | ZEPHYR Air Control | `available` | **UNKNOWN / NEEDS REVIEW** | `/air-control.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-029` | Air Systems Control | `available` | **UNKNOWN / NEEDS REVIEW** | `/air-systems-control.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-030` | ClearPulse | `available` | **UNKNOWN / NEEDS REVIEW** | `/clearpulse.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-031` | ClearBank Legal AI | `available` | **UNKNOWN / NEEDS REVIEW** | `/banking-law-advisor.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-032` | ClearTax AI | `available` | **UNKNOWN / NEEDS REVIEW** | `/tax.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-033` | Government Solutions | `available` | **UNKNOWN / NEEDS REVIEW** | `/government.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-034` | SMB Suite | `available` | **UNKNOWN / NEEDS REVIEW** | `/smb.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-035` | Artemis IV Core · Asset | `available` | **UNKNOWN / NEEDS REVIEW** | `/products/opal-koboi/artemis-iv-core.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-036` | Artemis VI · Asset | `available` | **UNKNOWN / NEEDS REVIEW** | `/products/opal-koboi/artemis-vi.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-037` | Guardian · Asset | `available` | **UNKNOWN / NEEDS REVIEW** | `/products/opal-koboi/guardian.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-038` | Ultra Glass | `available` | **UNKNOWN / NEEDS REVIEW** | `/ultra-glass.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-039` | ClearGlass Ultra | `available` | **UNKNOWN / NEEDS REVIEW** | `/clearglass-ultra.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-040` | Advanced Systems Catalog | `available` | **UNKNOWN / NEEDS REVIEW** | `/advanced-features-tools-systems.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-041` | Artemis Blue Team | `available` | **UNKNOWN / NEEDS REVIEW** | `/artemis-blue-team.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-042` | Cyber Defense Console | `available` | **UNKNOWN / NEEDS REVIEW** | `/cyber-defense-console.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-043` | Intelligence Platform | `available` | **UNKNOWN / NEEDS REVIEW** | `/intelligence-platform.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-044` | Intelligence Services | `available` | **UNKNOWN / NEEDS REVIEW** | `/intelligence.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-045` | Percival Build | `available` | **UNKNOWN / NEEDS REVIEW** | `/percival-build.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-046` | Command Center | `available` | **UNKNOWN / NEEDS REVIEW** | `/command-center.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-047` | Platform Command Center | `available` | **UNKNOWN / NEEDS REVIEW** | `/platform-command-center.html` | Preserve legacy route and record; current page is `noindex`, so set `seoIndexable: false` and exclude from sitemap/ItemList pending owner resolution |
| `cg-048` | Authority Network | `available` | **UNKNOWN / NEEDS REVIEW** | `/authority-network.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-049` | BLUEDESK | `available` | **UNKNOWN / NEEDS REVIEW** | `/bluedesk.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-050` | BLUEDESK Mobile | `available` | **UNKNOWN / NEEDS REVIEW** | `/bluedesk-mobile.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-051` | SMB Cyber Trust Kit | `available` | **UNKNOWN / NEEDS REVIEW** | `/smb-cyber-trust-kit.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-052` | Environmental Cyber Risk | `available` | **UNKNOWN / NEEDS REVIEW** | `/environmental-cyber-risk.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-053` | StegoForge | `available` | **UNKNOWN / NEEDS REVIEW** | `/stegoforge.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-054` | ATT&CK Prompt Core | `available` | **UNKNOWN / NEEDS REVIEW** | `/attack-prompt-core.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-055` | PostLoop | `available` | **UNKNOWN / NEEDS REVIEW** | `/postloop.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-056` | Revenue Engine | `available` | **UNKNOWN / NEEDS REVIEW** | `/revenue-engine.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-057` | Opal-Koboi Assets | `available` | **UNKNOWN / NEEDS REVIEW** | `/products/opal-koboi/index.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-058` | Revenue Engine · Asset | `available` | **UNKNOWN / NEEDS REVIEW** | `/products/opal-koboi/revenue-engine.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-059` | Aurora Glass | `available` | **UNKNOWN / NEEDS REVIEW** | `/futuristic.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-060` | Button System | `available` | **UNKNOWN / NEEDS REVIEW** | `/button-system.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-061` | Button Lab | `available` | **UNKNOWN / NEEDS REVIEW** | `/button-lab.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-062` | Web Design & Development | `available` | **UNKNOWN / NEEDS REVIEW** | `/web-design.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-063` | Store | `available` | **UNKNOWN / NEEDS REVIEW** | `/store.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-064` | Side Store | `available` | **UNKNOWN / NEEDS REVIEW** | `/side-store.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-065` | Pricing | `available` | **UNKNOWN / NEEDS REVIEW** | `/pricing.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-066` | Hover Menu | `available` | **UNKNOWN / NEEDS REVIEW** | `/hover-menu.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-067` | CLEARSIGHT | `available` | **UNKNOWN / NEEDS REVIEW** | `/clearsight.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-068` | ClearPulse Architecture | `available` | **UNKNOWN / NEEDS REVIEW** | `/clearpulse-architecture.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-069` | AEGIS | `available` | **UNKNOWN / NEEDS REVIEW** | `/aegis.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-070` | ClearCounsel | `available` | **UNKNOWN / NEEDS REVIEW** | `/corporate-legal-advisor.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-071` | Counter-UAS OS | `available` | **UNKNOWN / NEEDS REVIEW** | `/counter-uas-commercialization-os.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-072` | Speed Vision AI | `available` | **UNKNOWN / NEEDS REVIEW** | `/traffic-enforcement.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-073` | SATS Digital Twin | `available` | **UNKNOWN / NEEDS REVIEW** | `/sats-digital-twin.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-074` | SMB Suite · Asset | `available` | **UNKNOWN / NEEDS REVIEW** | `/products/opal-koboi/smb-suite.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-075` | Procurement Legal Tech | `available` | **UNKNOWN / NEEDS REVIEW** | `/procurement-legal-tech.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-076` | ClearGlass Revenue Machine | `internal` | **INTERNAL / ADMIN** | `/ClearGlass-Revenue-Machine.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-077` | ClearGlass Revenue OS v2 | `internal` | **INTERNAL / ADMIN** | `/clearGlass-revenue-os-v2.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-078` | ClearGlass Shield | `architecture-stage` | **PLANNED / IN DEVELOPMENT** | `/shield.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-079` | Shield G01 Verification Console | `simulation` | **PROTOTYPE** | `/clearglass_x5f_shield_x5f_g01_x5f_verified.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-080` | Shield Nexus Simulation | `simulation` | **PROTOTYPE** | `/shield_x5f_nexus_x5f_live_x5f_all.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-081` | GridShield-Ontario v6.0 ULTRA | `simulation` | **PROTOTYPE** | `/gridshield_x5f_v6_x5f_ultra_x5f_do.html` | Preserve entry; add evidence metadata; do not claim operational until verified |
| `cg-082` | Ontario Power Grid Live Demo | `demo` | **BETA / DEMO** | `/ontario_x5f_power_x5f_grid_x5f_live.html` | Preserve entry; add evidence metadata; do not claim operational until verified |

## Uncatalogued pages and possible wiring candidates

The tree contains 43 root-level HTML pages not represented as catalog destinations. Candidates requiring product-vs-demo-vs-duplicate review include:

- Dashboards / operational systems: `ClearGlass-Ops-Dashboard.html`, `Clearglass-Shield-Dashboard.html`, `GridShield-Ontario-V6-0-ULTRA-FINAL.html`, `Ontario-Power-Grid-Live.html`, `Orelogic-Final-Dashboard-Production.html`, `Orelogic-V4-Ultra-Beyond.html`, `mission-control.html`, `project-board.html`, `workspace.html`.
- Product-like variants and specializations: `artemis-nonprofit-os.html`, `artemis-vi.html`, `business-productivity-suite.html`, `clearglass-sat-mission-deploy.html`, `global-growth-engine.html`, `intelligence-graph.html`, `minerals.html`, `revenue-command.html`, `threads.html`, `plans.html`.
- GridShield variants to compare, not independently list without proof: `Gridshield-Ontario-V3-Ics.html`, `Gridshield-V7-Ultra-Formal.html`, `Gridshield-V8-Live-Wire.html`, `ontario_x5f_power_x5f_grid_x5f_live (1).html`.
- Possible design, draft, or duplicate surfaces: `clearglass_x5f_pricing_x5f_preview.html`, `clearglass_x5f_rescue_x5f_draft_x5f_landing.html`, `clearglass_x5f_shield_x5f_dashboard.html`, `Fantasy-Command-Live (1).html`, `Fantasy-Command-Live (2).html`, `fantasy-command-live.html`, `Fantasy-Pool-Dashboard.html`, `guardian_command_nexus_spec.html`, `HoloSurg-surgical-visualization-blueprint.html`, `Clearglass-Animation-Repair-Ultracode.html`.
- SEO support pages: `seo-authority-hub.html`, `seo-dashboard.html`.
- Infrastructure, not products by default: `404.html`, `cg-loader.html`, `loader.html`, `offline.html`, the Google verification HTML, `header-mockup-2040.html`, `index.html`, and `products.html`.

### Navigation/sitemap reconciliation

- `nav.js`: 84 hard-coded items.
- Navigation items absent from JSON catalog: Shield Concept Dashboard (`clearglass_x5f_shield_x5f_dashboard.html`) and GridShield-Ontario Evidence Console (`GridShield-Ontario-V6-0-ULTRA-FINAL.html`).
- Existing catalog item absent from navigation: XENOLITH (`xenolith.html`).
- `sitemap.xml`: 174 URLs; the branch restores the original URL set rather than adding the Platform Command Center route.
- The Platform Command Center page has an explicit `noindex` directive, and repository SEO documentation conflicts about whether it should be public or private. Preserve the page, legacy catalog `productUrl`, and global navigation; use `seoIndexable: false` and omit it from the sitemap and public ItemList until the owner resolves scope.
- `ClearGlass-Revenue-Machine.html` and `clearGlass-revenue-os-v2.html` are internal/noindex; the Shield G01, Shield Nexus, GridShield v6, and Ontario Power Grid demo pages explicitly use `noindex,nofollow`. Their demo cards remain clearly labelled, but `seoIndexable` is false and these routes stay out of the sitemap/structured-data ItemList.

Consolidation proposal: keep one canonical card for Shield and one for GridShield when the evidence confirms the nav-only surfaces are alternate/demo views of the same product. Preserve existing routes and associate them as related surfaces; add no duplicate cards by name alone.

## Recent automation evidence and release limitations

Current main-branch run summaries showed failures on 2026-10-13 for IESO Public Feed, Multi-Repo Audit and repeated Auto Heal runs. The connector could not retrieve usable job logs; root causes are not asserted. An older 2026-10-01 audit is not treated as proof of current CI or deployment health.

A web snapshot of `https://www.clearglassinc.com/products.html` showed the page shell and loading placeholders, but it does not establish whether a full browser completed client-side rendering. Browser-level desktop/mobile verification is therefore a release gate.

## Proposed implementation plan

1. Confirm the actual repository identity (the supplied `ClearGlasslabs/...` path is 404; this candidate is the closest verified match).
2. Preserve the current catalog as baseline; create an additive inventory and risk register.
3. Add required metadata fields to existing product records, retaining every existing ID, name, URL, ordering and status.
4. Add the verified public demo ARTEMIS FAWL only with an explicit demo/synthetic status; list unhosted backend/prototype systems as internal entries using safe contact destinations rather than exposing private endpoints.
5. Preserve current navigation items and ordering, append XENOLITH, and include the ARTEMIS FAWL demo. Keep the Shield/GridShield related surfaces consolidated unless code evidence demonstrates distinct products.
6. Add catalog CTA/status rendering that honors explicit internal-vs-public classification; preserve existing legacy `productUrl` values as source data.
7. Preserve the canonical URL and JSON-LD `CollectionPage` schema. Keep `ItemList` limited to public, indexable destinations; any explicit `noindex` route has `seoIndexable: false` and is excluded while its catalog card/legacy route is preserved. Never describe internal or simulated systems as live services.
8. Update tests for the expanded registry, required metadata, safe internal CTAs, original IDs/URLs, and destination existence.
9. Run catalog tests, site integrity, schema/JSON parsing, JS syntax, tests/typecheck/build where available, desktop/mobile rendering, sitemap consistency, and workflow YAML validation. If the environment cannot run a gate, record `NOT_EXECUTABLE_IN_THIS_ENVIRONMENT`.
10. Open a reviewable PR with changed-file and validation evidence; do not merge or deploy.

## Rollback and safety

- All changes are to be additive or narrowly edited on `feat/system-wiring-product-catalog`; no production deployment, DNS change, permission change, secret mutation or dependency upgrade is part of this plan.
- Rollback: close the PR without merging, or revert its individual commits. No production database migration is planned.
- Secret values are excluded from this audit. The failed workflow causes remain unknown until usable logs or a successful rerun are available.
