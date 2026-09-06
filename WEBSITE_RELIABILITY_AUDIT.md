# Website Reliability and Connectivity Audit

**Audit date:** 2026-07-26
**Scope:** GitHub Pages static site, all repository-owned HTML, navigation/assets/fragments, robots and sitemap connections, and all GitHub Actions definitions.
**Production-verification rule:** `live` is reserved for a successful remote response. The audit environment received an upstream HTTP 403 for the canonical host, so every deployed route remains **unknown** even where its checked-in route is valid.

## Executive status

| Surface | Status | Evidence and risk |
|---|---|---|
| Checked-in site graph | **live (repository artifact)** | The enhanced offline crawl resolves local and canonical same-site links, Pages-style directory routes, assets, and fragments with zero remaining errors. |
| Production site and 132 unique sitemap resources | **unknown** | The canonical origin returned HTTP 403 to this audit environment. This may be an egress/proxy limitation; it is not evidence that production is down. |
| Pages source method | **live (source configuration)** | `pages.yml` publishes the repository root on pushes to `main`, requires build before deploy, creates `dist/index.html`, preserves `.nojekyll`, and uses the official Pages artifact flow. |
| GitHub Pages repository setting / protected environment | **unknown** | The checkout has no Git remote or authenticated GitHub API context, so the configured Pages source and environment reviewer rules cannot be independently confirmed. |
| Workflow definitions | **live (offline validation)** | 52/52 parse and pass fail-closed structural validation; 49 are ready and 3 need improvement. Hosted run history and secret authorization remain unknown. |
| Crawl directives | **live (repository artifact)** | `robots.txt` is syntactically valid after removing a stray `</content>` token; all three declared sitemap files exist. |

## Repairs shipped

| Priority | Failure risk | Exact correction |
|---|---|---|
| P0 | A malformed `robots.txt` line could be ignored unpredictably by crawlers. | Removed the stray `</content>` token and added deterministic robots/sitemap validation. |
| P0 | One case-mismatched Ontario OSINT canonical URL resolved to a nonexistent Linux/Pages path. | Matched the canonical to `/Ontario-osint.html`. |
| P1 | Nineteen CTA/menu/footer fragment paths targeted missing anchors. | Retargeted links to existing sections, added the `#top`, `#exposure`, and `#vendor` anchors, and connected mockup navigation to real site routes. |
| P1 | The previous crawler checked file existence only and could report disconnected fragments as healthy. | Added fragment, same-origin absolute URL, directory-index, canonical sitemap target, and robots sitemap checks with regression coverage. |
| P1 | The offline audit, workflow audit, generated-link check, and production crawl were separate manual operations. | Added one fail-closed weekly/manual workflow: offline gates run for changes, while scheduled/manual runs crawl all 132 unique sitemap routes and retain machine-readable evidence for 30 days. |
| P1 | The reliability audit called a missing `check_robots` function and crashed before reporting results. | Restored deterministic robots validation and added a regression test for malformed directives and missing sitemap targets. |

## Corrected routing structure

- Root deployment: `main` → Pages build job → validated `dist/` artifact → `github-pages` environment → deploy job.
- Canonical origin: `https://www.clearglassinc.com`; root source contains `index.html`, `CNAME`, `.nojekyll`, and `robots.txt`.
- Navigation uses explicit checked-in `.html` routes or directory routes backed by `index.html`; in-page links now resolve to a real `id`/named anchor.
- Crawl discovery: `robots.txt` → `sitemap.xml`, `sitemap-authority-network.xml`, and `sitemap-autonomous-threat-modeling.xml` → checked-in resources.

## Complete page and connection inventory

`Local refs` includes menus, footer links, CTAs, stylesheets, scripts, images, and same-origin absolute URLs. **Production is unknown for every row** until the post-deploy remote crawl succeeds.

| Page / route | Title | Local refs | External refs | In sitemap | Repository connection | Production |
|---|---:|---:|---:|---:|---|---|
| `404.html` | ClearGlass Inc. · Redirecting · Intelligent Systems | 16 | 0 | no | live | unknown |
| `CG-os.html` | CG OS — Command HUD · ClearGlass Inc. | 30 | 3 | yes | live | unknown |
| `ClearGlass-NEXUS-v12-FINAL.html` | ClearGlass NEXUS v12 — DARPA Intelligence Platform \| ClearGlass Inc. | 23 | 1 | yes | live | unknown |
| `Ontario-osint.html` | ClearGlassInc · Ontario OSINT Control Deck | 24 | 3 | yes | live | unknown |
| `advanced-features-tools-systems.html` | ClearGlass · Advanced Features, Tools &amp; Systems | 33 | 11 | yes | live | unknown |
| `aegis.html` | AEGIS · Legal Process Shield — ClearGlass Inc. | 31 | 3 | yes | live | unknown |
| `agentmesh.html` | PERCIVAL · Agent Mesh — OSINT Orchestration — ClearGlass | 33 | 3 | yes | live | unknown |
| `ai-operator.html` | AI Operator Workspace · ClearGlass Inc. | 33 | 3 | yes | live | unknown |
| `air-control.html` | ZEPHYR · Air Systems Control Surface — ClearGlass Inc. | 25 | 3 | yes | live | unknown |
| `air-systems-control.html` | Artemis Air Systems Control Surface \| ClearGlass Inc. | 25 | 3 | yes | live | unknown |
| `apps/command-center/index.html` | ClearGlass Burlington Growth Command Centre | 1 | 0 | no | live | unknown |
| `artemis-2040.html` | ClearGlassInc Artemis 2040 Intelligence Platform | 21 | 0 | yes | live | unknown |
| `artemis-ai-cyber-intelligence-platform.html` | AI Cyber Intelligence Platform \| ClearGlassInc Artemis | 20 | 9 | yes | live | unknown |
| `artemis-blue-team.html` | ClearGlass Inc · Artemis Blue Team OSINT Command Center | 30 | 0 | yes | live | unknown |
| `artemis-fawl/index.html` | ARTEMIS // FAWL — ClearGlass Inc. | 7 | 1 | no | live | unknown |
| `artemis-iv.html` | CLEARGLASS INC · ARTEMIS IV · TACTICAL INTELLIGENCE CORE | 31 | 1 | yes | live | unknown |
| `artemis-os.html` | Artemis · Intelligence Operating System · ClearGlass Inc. | 46 | 12 | yes | live | unknown |
| `artemis-percival.html` | AVALON · ARTEMIS ⊕ PERCIVAL — Unified Fusion Core \| ClearGlass Inc. | 32 | 3 | yes | live | unknown |
| `artemis-self-evolving-platform.html` | ClearGlassInc Artemis — Self-Evolving AI Intelligence Platform | 17 | 2 | yes | live | unknown |
| `artemis.html` | ClearGlass NEXUS v12 — Intelligence Platform \| Ontario | 30 | 1 | yes | live | unknown |
| `attack-prompt-core.html` | ClearGlassInc Artemis — ATT&CK Prompt Integrator | 30 | 0 | yes | live | unknown |
| `authority-network.html` | ClearGlass Authority Network \| Connected AI, Cybersecurity, OSINT & Infrastructure | 163 | 0 | yes | live | unknown |
| `automap.html` | ClearGlass AutoMap · Agent Orchestration Architect | 23 | 4 | yes | live | unknown |
| `banking-law-advisor.html` | ClearBank Legal AI™ — Banking Law &amp; Regulatory | 62 | 10 | yes | live | unknown |
| `blog/ai-agent-governance-governed-autonomy.html` | AI Agent Governance: The Governed Autonomy Playbook — ClearGlass Inc. | 51 | 5 | yes | live | unknown |
| `blog/ai-agents-insider-threat.html` | AI Agents Are the New Insider Threat — ClearGlass Inc. | 51 | 5 | yes | live | unknown |
| `blog/almach-scalp-engine.html` | ALMACH Scalp Engine · Directional Neural Mesh \| ClearGlass Insights | 33 | 10 | yes | live | unknown |
| `blog/artemis-governed-ai-gtm-visual-growth-engine.html` | Governed AI Threat Modeling: The ClearGlassInc Artemis GTM Visual Growth Engine — ClearGlass Inc. | 31 | 3 | yes | live | unknown |
| `blog/autonomous-threat-modeling-2026.html` | Autonomous Threat Modeling in 2026 \| ClearGlass Inc. | 38 | 20 | yes | live | unknown |
| `blog/clearglass-agentops-microsoft-foundry-future-stack.html` | ClearGlass AgentOps: Microsoft Foundry Future Stack \| ClearGlass Insights | 35 | 0 | yes | live | unknown |
| `blog/clearglass-command-center-cyber-defense-console.html` | Inside the ClearGlass Command Center: Designing a Cyber Defense Console That Earns Trust \| ClearGlass Insights | 24 | 0 | yes | live | unknown |
| `blog/clearglass-platform-audit-2026.html` | The ClearGlass Platform Audit: Upgrading a Governed Monorepo Into a Future-Tech Platform — ClearGlass Inc. | 54 | 5 | yes | live | unknown |
| `blog/clearglass-secure-deployment-agent.html` | The Secure Deployment Agent: Governed Authorization for Every Production Change — ClearGlass Inc. | 52 | 5 | yes | live | unknown |
| `blog/clearglassinc-0-to-1m-corporate-execution-plan.html` | ClearGlassInc: The $0-to-$1,000,000 Corporate Execution Plan \| ClearGlass Insights | 30 | 3 | yes | live | unknown |
| `blog/clearglassinc-artemis-full-stack-ai-intelligence-platform-blueprint.html` | ClearGlassInc Artemis Full-Stack AI Intelligence Platform Blueprint — ClearGlass Inc. | 14 | 0 | no | live | unknown |
| `blog/clearglassinc-artemis-palantir-self-evolving-ai-intelligence-platform.html` | ClearGlassInc Artemis: Palantir Blueprint for a Self-Evolving AI Intelligence Platform — ClearGlass Inc. | 7 | 11 | yes | live | unknown |
| `blog/clearglassinc-artemis-resume-builder-self-evolving-intelligence-platform.html` | ClearGlassInc Artemis Resume Builder: Self-Evolving AI Intelligence Platform Blueprint — ClearGlass Inc. | 51 | 16 | yes | live | unknown |
| `blog/clearglassinc-artemis-self-evolving-ai-intelligence-platform.html` | ClearGlassInc Artemis: Self-Evolving AI Intelligence Platform — ClearGlass Inc. | 50 | 18 | yes | live | unknown |
| `blog/cybersecurity-architecture-for-agentic-software.html` | Cybersecurity Architecture for Agentic Software — ClearGlass Inc. | 50 | 5 | yes | live | unknown |
| `blog/digital-twin-simulation-tools-storm-adaptive-transit-2026.html` | Best Digital Twin Simulation Tools for Storm-Adaptive Transit Systems in 2026 — ClearGlass Inc. | 22 | 10 | yes | live | unknown |
| `blog/ethical-sales-system-100k-revenue-prompt.html` | Ethical Sales Psychology: A 100K Revenue System Prompt \| ClearGlass Insights | 29 | 3 | yes | live | unknown |
| `blog/frontier-intelligence-briefing-quantum-gravity-asi-biosecurity.html` | Frontier Intelligence Briefing: Quantum Gravity, ASI Timelines, Biosecurity &amp; the Economic Singularity — ClearGlass Inc. | 39 | 8 | yes | live | unknown |
| `blog/greenbelt-92-percent-access-beats-process.html` | 92%: When Access Beats Process — ClearGlass Insights | 11 | 5 | yes | live | unknown |
| `blog/index.html` | ClearGlass Intelligence \| Governed AI, Cyber Defense &amp; OSINT Systems | 88 | 20 | yes | live | unknown |
| `blog/master-investigator-legal-tech-osint-government-accountability.html` | Master Investigator: Legal-Tech OSINT for Government Accountability \| ClearGlass Insights | 24 | 0 | yes | live | unknown |
| `blog/osint-workflow-that-survives-contact-with-reality.html` | The OSINT Workflow That Survives Contact With Reality — ClearGlass Inc. | 51 | 5 | yes | live | unknown |
| `blog/post-quantum-security-advisor-clearglass-artemis.html` | Post-Quantum Security Advisor: The Commercial Quantum Wedge for ClearGlassInc Artemis — ClearGlass Inc. | 20 | 5 | yes | live | unknown |
| `blog/resume-builder.html` | Resume Builder PDF Export \| ClearGlass Intelligence | 25 | 0 | yes | live | unknown |
| `blog/zero-trust-is-outdated-adaptive-trust.html` | Zero Trust Is Outdated: The Case for Adaptive Trust Systems — ClearGlass Inc. | 38 | 5 | yes | live | unknown |
| `blog/zero-trust-is-outdated.html` | Zero Trust Is Outdated — ClearGlass Inc. | 51 | 5 | yes | live | unknown |
| `bluedesk-mobile.html` | BLUE DESK Mobile — CISO Risk Console Hero (9:16) \| ClearGlass Inc | 26 | 1 | yes | live | unknown |
| `bluedesk.html` | BLUEDESK — CISO Risk & Blue Team Console \| ClearGlass Inc | 33 | 13 | yes | live | unknown |
| `button-lab.html` | Button Lab · ClearGlass — Machined Glass Control System | 30 | 1 | yes | live | unknown |
| `button-system.html` | Button System — ClearGlass · Intelligent Systems | 27 | 0 | yes | live | unknown |
| `cg-loader.html` | ClearGlassInc · Initializing · Intelligent Systems | 15 | 4 | no | live | unknown |
| `clearglass-nexus.html` | ClearGlass NEXUS v12 — DARPA Intelligence Platform \| ClearGlass Inc. | 33 | 12 | yes | live | unknown |
| `clearglass-ultra.html` | ClearGlass Ultra — See Through Everything | 29 | 6 | yes | live | unknown |
| `clearglass.html` | ClearGlass · Network Flow Intelligence | 25 | 3 | yes | live | unknown |
| `clearpulse-architecture.html` | ClearPulse Architecture Whitepaper — Forensic AI for | 34 | 3 | yes | live | unknown |
| `clearpulse.html` | ClearPulse — Healthcare Intelligence Pipeline \| ClearGlass | 34 | 3 | yes | live | unknown |
| `clearsight.html` | CLEARSIGHT — Edge-AI Camera Vision System \| ClearGlass Inc | 20 | 3 | yes | live | unknown |
| `command-center.html` | ClearGlass Command Center — Executive Security Operations Deck | 17 | 6 | yes | live | unknown |
| `command-console.html` | ClearGlass — Command Console \| Cyber Intelligence | 31 | 11 | yes | live | unknown |
| `conduit.html` | CONDUIT · Workflow Automation — Self-Hosted, Open Source — ClearGlass Inc. | 76 | 16 | yes | live | unknown |
| `control-surface.html` | Systems Control Surface v3.1 — Command Dashboard \| ClearGlass Inc | 46 | 3 | yes | live | unknown |
| `corporate-legal-advisor.html` | ClearCounsel™ Corporate Legal AI — Senior Partner | 61 | 11 | yes | live | unknown |
| `counter-uas-commercialization-os.html` | Counter-UAS Commercialization OS — ClearGlass Inc. | 26 | 4 | yes | live | unknown |
| `cyber-defense-console.html` | ClearGlass Command Center · Cyber Defense Console — ClearGlass Inc. | 34 | 9 | yes | live | unknown |
| `docs/guardian_command_nexus_spec.html` | CLEARGLASS Guardian Command Nexus Specification | 23 | 0 | yes | live | unknown |
| `environmental-cyber-risk.html` | Environmental Cyber-Risk \| ClearGlassInc Artemis | 25 | 2 | yes | live | unknown |
| `flowsint.html` | Flowsint · OSINT Investigation Graph — Domains, IPs & Transforms \| ClearGlass Inc. | 45 | 4 | yes | live | unknown |
| `futuristic.html` | ClearGlass · Aurora Glass — Futuristic Control Surface | 30 | 10 | yes | live | unknown |
| `google23RWyXWkoxqgArev8achU8IfVxYC5EIUAYBsuTYKLFM.html` | (no title) | 0 | 0 | no | live | unknown |
| `government.html` | ClearGlass Inc. — Federal & Government Solutions \| FedRAMP | 58 | 10 | yes | live | unknown |
| `guardian.html` | CLEARGLASS GUARDIAN v5.0 — Intelligence Command Interface | 37 | 16 | yes | live | unknown |
| `header-mockup-2040.html` | ClearGlassInc. 2040 — Header Mockup | 8 | 3 | no | live | unknown |
| `hover-menu.html` | ClearGlassInc · Elegant Hover Menu | 31 | 0 | yes | live | unknown |
| `index.html` | ClearGlass Inc — AI Automation, Cybersecurity & Operational Strategy | 225 | 35 | yes | live | unknown |
| `intelligence-command-surface.html` | ClearGlass Intelligence Command Surface | 31 | 10 | yes | live | unknown |
| `intelligence-interface.html` | ClearGlass Intelligence Interface 2027 | 43 | 1 | yes | live | unknown |
| `intelligence-platform.html` | ClearGlass Intelligence Platform — Brand & Platform Architecture \| ClearGlass Inc. | 23 | 5 | yes | live | unknown |
| `intelligence.html` | ClearGlass Market Dominance · Intelligent Systems | 38 | 0 | yes | live | unknown |
| `investors/index.html` | Investor Data Room \| ClearGlass Inc. | 22 | 0 | yes | live | unknown |
| `legal/ai-liability.html` | AI Liability Framework \| ClearGlass Inc. | 36 | 14 | yes | live | unknown |
| `legal/articles.html` | Articles of Incorporation \| ClearGlass Inc. | 33 | 11 | yes | live | unknown |
| `legal/banking-resolution.html` | Banking &amp; Officer Resolution \| ClearGlass Inc. | 33 | 12 | yes | live | unknown |
| `legal/bylaws.html` | Corporate Bylaws \| ClearGlass Inc. | 33 | 13 | yes | live | unknown |
| `legal/content-policy.html` | Content Policy \| ClearGlass Inc. | 14 | 1 | yes | live | unknown |
| `legal/directors-resolution.html` | Initial Directors' Resolution \| ClearGlass Inc. | 33 | 11 | yes | live | unknown |
| `legal/index.html` | Legal Infrastructure \| ClearGlass Inc. | 53 | 5 | yes | live | unknown |
| `legal/ip-assignment.html` | IP Assignment Agreement \| ClearGlass Inc. | 33 | 12 | yes | live | unknown |
| `legal/legal-council.html` | AI Legal Council Framework \| ClearGlass Inc. | 37 | 19 | yes | live | unknown |
| `legal/nda.html` | Founder NDA &amp; Non-Compete \| ClearGlass Inc. | 33 | 13 | yes | live | unknown |
| `legal/privacy.html` | Privacy Policy \| ClearGlass Inc. | 33 | 18 | yes | live | unknown |
| `legal/share-subscription.html` | Share Subscription Agreement \| ClearGlass Inc. | 33 | 11 | yes | live | unknown |
| `legal/terms.html` | Terms of Service \| ClearGlass Inc. | 32 | 17 | yes | live | unknown |
| `loader.html` | ClearGlass · Initializing · Intelligent Systems | 12 | 3 | no | live | unknown |
| `offers/autonomous-threat-modeling.html` | Autonomous Threat Modeling Services \| ClearGlass Inc. | 30 | 3 | yes | live | unknown |
| `offers/hardening-sprint.html` | Microsoft 365 + Windows Hardening Sprint — ClearGlass Inc. | 26 | 4 | yes | live | unknown |
| `offers/index.html` | Services & Engagements — ClearGlass Inc. | 39 | 11 | yes | live | unknown |
| `offers/phipa-readiness-checklist.html` | PHIPA Readiness Checklist — ClearGlass Inc. | 20 | 0 | yes | live | unknown |
| `offers/phipa-readiness.html` | PHIPA Readiness — Free Checklist & Assessment — ClearGlass Inc. | 25 | 2 | yes | live | unknown |
| `offers/security-quick-audit.html` | Security Quick-Audit ($249) — ClearGlass Inc. | 25 | 3 | yes | live | unknown |
| `offers/thank-you.html` | Thank you — ClearGlass Inc. | 15 | 0 | no | live | unknown |
| `offline.html` | Offline · ClearGlass · Intelligent Systems | 15 | 0 | no | live | unknown |
| `opal/index.html` | Opal-Koboi — ClearGlass Inc. Advanced Automation | 30 | 2 | yes | live | unknown |
| `operations/client-onboarding.html` | Client Onboarding \| ClearGlass Inc. | 22 | 0 | yes | live | unknown |
| `operations/federal-supplier-handoff.html` | Federal Supplier Registration Handoff \| ClearGlass Inc. | 34 | 3 | yes | live | unknown |
| `operations/hubspot-handoff.html` | HubSpot Connection Handoff \| ClearGlass Inc. | 35 | 3 | yes | live | unknown |
| `operations/ontario-incorporation-handoff.html` | Ontario Incorporation Filing Handoff \| ClearGlass Inc. | 37 | 3 | yes | live | unknown |
| `operations/procurement-readiness.html` | Verified Procurement Reality \| ClearGlass Inc. | 37 | 3 | yes | live | unknown |
| `operations/stripe-handoff.html` | Stripe Connection Handoff \| ClearGlass Inc. | 34 | 3 | yes | live | unknown |
| `percival-build.html` | PERCIVAL BUILD · Spatial Workspace — ClearGlass Inc. | 26 | 3 | yes | live | unknown |
| `percival-os.html` | PERCIVAL OS · Mission-Ready Command Center — ClearGlass Inc. | 44 | 3 | yes | live | unknown |
| `platform-command-center.html` | ClearGlass · Platform Command Center | 19 | 0 | yes | live | unknown |
| `postloop.html` | PostLoop · Autonomous Content Engine — Multi-Account Publishing on Autopilot \| ClearGlass Inc. | 31 | 4 | yes | live | unknown |
| `pricing.html` | Pricing & Engagements — Start with ClearGlass \| ClearGlass | 35 | 4 | yes | live | unknown |
| `procurement-legal-tech.html` | Procurement & Legal-Tech Command Surface \| ClearGlass Inc. | 47 | 11 | yes | live | unknown |
| `products/opal-koboi/artemis-iv-core.html` | Artemis IV Core \| Opal-Koboi Assets | 27 | 0 | yes | live | unknown |
| `products/opal-koboi/artemis-vi.html` | Artemis VI \| Opal-Koboi Assets | 27 | 0 | yes | live | unknown |
| `products/opal-koboi/guardian.html` | Guardian \| Opal-Koboi Assets | 27 | 0 | yes | live | unknown |
| `products/opal-koboi/index.html` | Opal-Koboi Product Assets \| ClearGlassInc | 30 | 0 | yes | live | unknown |
| `products/opal-koboi/revenue-engine.html` | Revenue Engine \| Opal-Koboi Assets | 27 | 0 | yes | live | unknown |
| `products/opal-koboi/smb-suite.html` | SMB Suite \| Opal-Koboi Assets | 27 | 0 | yes | live | unknown |
| `products.html` | ClearGlass Inc. Products — Unified Product Suite | 168 | 3 | yes | live | unknown |
| `revenue-engine.html` | Revenue Engine — ClearGlass Inc. · AI-Driven Business | 78 | 11 | yes | live | unknown |
| `saas-platform.html` | ClearGlass • Event Driven Control Surface | 29 | 4 | yes | live | unknown |
| `sats-digital-twin.html` | SATS Digital Twin — Storm-Adaptive Transit Simulation \| ClearGlass Inc. | 27 | 3 | yes | live | unknown |
| `sentinel/ARTEMIS_FAWL_COMMAND_SURFACE.html` | ARTEMIS // FAWL — Governance Command Surface (Private) | 3 | 0 | no | live | unknown |
| `sentinel/PHOENIX_DASHBOARD.html` | PHOENIX — Self-Healing Operations Surface (Private) | 3 | 0 | no | live | unknown |
| `sentinel.html` | SENTINEL · Live Geospatial Command Center — ClearGlass Inc. | 31 | 5 | yes | live | unknown |
| `side-store.html` | ClearGlass Side Store — Electronics, Cables & Components \| ClearGlass Inc | 24 | 24 | yes | live | unknown |
| `smb-cyber-trust-kit.html` | SMB Cyber Trust Kit — Plain-Language Cyber Resilience \| ClearGlass Inc | 33 | 12 | yes | live | unknown |
| `smb.html` | SMB Suite — ClearGlass · Intelligent Systems | 31 | 0 | yes | live | unknown |
| `stegoforge.html` | STEGOFORGE · ClearGlassInc Artemis Cybersecurity Terminal | 30 | 3 | yes | live | unknown |
| `store.html` | ClearGlass Store — Book a Security Engagement | 32 | 3 | yes | live | unknown |
| `systems.html` | Systems Control Surface — PERCIVAL Operations Console \| ClearGlass Inc. | 33 | 2 | yes | live | unknown |
| `tax.html` | ClearTax AI™ — Precision Tax Intelligence · U.S. &amp; Canadian \| ClearGlass Inc. | 57 | 15 | yes | live | unknown |
| `traffic-enforcement.html` | Traffic Enforcement — Speed Vision AI \| ClearGlass Inc | 28 | 3 | yes | live | unknown |
| `ultra-glass.html` | ClearGlass — Ultra Glass. Governed Intelligence, Rendered Visible. | 38 | 6 | yes | live | unknown |
| `web-design.html` | Website Design & Development — Growth Infrastructure \| ClearGlass Inc. | 39 | 6 | yes | live | unknown |

## Complete workflow inventory

The status below is source-verifiable only. A workflow is not called operational until its hosted run, environment, secrets, artifact, and endpoint results are inspected.

| Workflow | Offline classification | Triggers | Exact residual risk |
|---|---|---|---|
| `agent-army-crypto.yml` | valid and ready | pull_request, push, workflow_dispatch | No source-verifiable failure. |
| `agent-army.yml` | valid and ready | pull_request, push, workflow_dispatch | No source-verifiable failure. |
| `agent-deployer.yml` | valid and ready | workflow_call, workflow_dispatch | No source-verifiable failure. |
| `agent-os.yml` | valid and ready | schedule, pull_request, workflow_dispatch | No source-verifiable failure. |
| `agent.yml` | valid and ready | workflow_dispatch | No source-verifiable failure. |
| `api-security-audit.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `artemis-browser.yml` | valid and ready | push, pull_request, workflow_dispatch | No source-verifiable failure. |
| `artemis-deploy.yml` | valid and ready | push, schedule, workflow_dispatch | No source-verifiable failure. |
| `artemis-fawl.yml` | valid and ready | pull_request, workflow_dispatch | No source-verifiable failure. |
| `auto-store.yml` | valid and ready | pull_request, push, schedule, workflow_dispatch | No source-verifiable failure. |
| `bot-orchestrator.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `burlington-military-op.yml` | valid and ready | workflow_dispatch, schedule | No source-verifiable failure. |
| `burlington-release.yml` | valid and ready | workflow_dispatch, schedule | No source-verifiable failure. |
| `cert-bot.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `ci.yml` | valid and ready | push, pull_request, workflow_dispatch | No source-verifiable failure. |
| `clearglassinc-military-op.yml` | valid but needs improvement | workflow_dispatch, schedule | top-level write permission applies to every job; move each write grant to its consuming job |
| `codex-autofix.yml` | valid and ready | workflow_dispatch | No source-verifiable failure. |
| `commerce-daily-loop.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `commerce-deploy.yml` | valid and ready | push, workflow_dispatch | No source-verifiable failure. |
| `commerce-frontend-ci.yml` | valid and ready | push, pull_request | No source-verifiable failure. |
| `compliance-evidence.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `content-pipeline.yml` | valid and ready | workflow_run, workflow_dispatch | No source-verifiable failure. |
| `control-surface-feeds.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `copilot-setup-steps.yml` | valid and ready | push, workflow_dispatch | No source-verifiable failure. |
| `daily-marketing-content.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `defender-watch.yml` | valid and ready | push, pull_request, schedule, workflow_dispatch | No source-verifiable failure. |
| `dependency-updater.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `dispatch-all-workflows.yml` | valid and ready | workflow_dispatch | No source-verifiable failure. |
| `health-monitor.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `internal-link-authority.yml` | valid and ready | pull_request, push, workflow_dispatch | No source-verifiable failure. |
| `ip-protection-scan.yml` | valid but needs improvement | push, pull_request, schedule | job 'scan' makes critical step 'Secret Pattern Scan' non-blocking; remove continue-on-error after its prerequisite is enabled; job 'scan' makes critical step 'Dependency Review' non-blocking; remove continue-on-error after its prerequisite is enabled |
| `master-orchestrator.yml` | valid and ready | workflow_dispatch, schedule | No source-verifiable failure. |
| `multi-repo-audit.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `organic-daily.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `organic-weekly-review.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `pages.yml` | valid and ready | push, workflow_dispatch | No source-verifiable failure. |
| `percival-policy-gate.yml` | valid and ready | pull_request, workflow_dispatch | No source-verifiable failure. |
| `percival-policy-reusable.yml` | valid and ready | workflow_call | No source-verifiable failure. |
| `phoenix-self-heal.yml` | valid and ready | push, pull_request, workflow_dispatch | No source-verifiable failure. |
| `policy-gate.yml` | valid and ready | pull_request, push, workflow_dispatch | No source-verifiable failure. |
| `pr-automation.yml` | valid and ready | pull_request | No source-verifiable failure. |
| `release-supply-chain.yml` | valid and ready | workflow_call | No source-verifiable failure. |
| `remove-homepage-crimson-loader.yml` | valid and ready | workflow_dispatch | No source-verifiable failure. |
| `repo-audit.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `sales-ops-briefing.yml` | valid and ready | schedule, workflow_dispatch | No source-verifiable failure. |
| `security.yml` | valid but needs improvement | pull_request, push, schedule | job 'dependency-review' makes critical step None non-blocking; remove continue-on-error after its prerequisite is enabled |
| `site-reliability.yml` | valid and ready | pull_request, push, schedule, workflow_dispatch | No source-verifiable failure. |
| `seo-optimizer.yml` | valid and ready | workflow_call, workflow_dispatch | No source-verifiable failure. |
| `thought-leadership.yml` | valid and ready | workflow_call, workflow_dispatch | No source-verifiable failure. |
| `viral-content.yml` | valid and ready | workflow_call, workflow_dispatch | No source-verifiable failure. |
| `workflow-doctor.yml` | valid and ready | schedule, push, workflow_dispatch | No source-verifiable failure. |
| `workflow-repair-agent.yml` | valid and ready | workflow_dispatch | No source-verifiable failure. |

## Prioritized rollout and verification

1. **Merge only after required checks pass.** The patch is static and reversible by reverting the commit.
2. **Confirm GitHub settings before deployment.** Repository owner verifies **Settings → Pages → Source = GitHub Actions**, the `github-pages` environment protection, `main` branch protection, custom-domain DNS, and HTTPS enforcement.
3. **Observe the Pages run.** Record commit SHA, actor, workflow/ref, run URL, build/deploy job results, artifact ID/digest, environment approval, published URL, and rollback owner.
4. **Post-deploy crawl.** Fetch the homepage, `robots.txt`, all three sitemaps, and all 132 unique sitemap resources; require expected 2xx responses, canonical consistency, no redirect loops, correct content type, and no browser-console failures.
5. **Integration verification.** Validate external forms/APIs with authorized test data. Authorization cannot be inferred from markup, and no secret or third-party account was modified during this audit.

## What to monitor after deployment

- Pages build/deploy duration, failures, artifact identity, and last-known-good commit.
- Homepage and sitemap-route availability, latency, TLS expiry, DNS/CNAME drift, redirect loops, and HTTP status distribution.
- Broken links/fragments, sitemap-to-file drift, robots changes, canonical-host/case mismatches, missing assets, and browser console errors.
- Third-party API/form synthetic transactions using non-production test identities; alert separately for authorization expiry, throttling, and schema drift.

## Weekly checks

- Confirm the scheduled `Site Reliability Audit` run completed both jobs; it runs `python3 scripts/site_reliability_audit.py`, `python3 tools/internal_links.py --check`, `python3 scripts/audit_github_actions.py --markdown`, focused regression tests, and the bounded live crawl.
- Retain and review the workflow's 30-day offline and live artifacts; the live JSON records status, final URL, content type, and error state for every unique sitemap route.
- Review workflow run history, disabled workflows, environment approvals, action pin drift, secret-name availability (never values), cache/artifact provenance, and alert-delivery success.
- Compare sitemap URLs, checked-in indexable pages, navigation entry points, and Search Console coverage; triage orphaned/non-indexed pages deliberately.

## Blockers and ownership

- **Repository administrator:** confirm remote Pages settings, protected environments, branch rules, and hosted workflow history.
- **DNS/domain owner:** confirm CNAME/HTTPS status and investigate the observed 403 from an independent network.
- **Integration owners:** verify third-party authorization and synthetic transactions. Until then those connections remain unknown.
