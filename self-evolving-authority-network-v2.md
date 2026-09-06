# ClearGlass Self-Evolving Authority Network v2

## Executive standard

ClearGlass Inc. operates as one connected authority system. The home page is the company authority hub. Pillars define the major subject domains. Cluster pages provide technical depth. Proof and architecture pages establish trust. Service pages convert qualified intent into governed engagements. Blog posts expand discovery and route readers into the relevant platform, proof, and service path.

The production system uses two layers:

1. `tools/internal_links.py` preserves the established static, crawlable related-content blocks.
2. `tools/authority_network.py` discovers every indexable page across every `sitemap*.xml`, attaches reviewed supplemental pages without reshuffling stable links, measures graph health, and fails CI when the network needs to evolve.

The public map is `authority-network.html`.

---

## 1. Full site linking strategy

### Authority flow

```text
Discovery
  → subject pillar
    → technical cluster
      → architecture / governance / proof
        → service or engagement
          → pricing / store / onboarding
```

### Link selection hierarchy

Every internal link must satisfy at least one of these purposes:

1. **Structural:** home, pillar, breadcrumb, global navigation, or semantic footer.
2. **Explanatory:** move from an overview to deeper technical detail.
3. **Lateral:** connect a page to a closely related sibling or adjacent domain.
4. **Proof:** connect a claim, service, or platform to architecture, governance, specifications, or implementation evidence.
5. **Conversion:** move qualified intent to services, pricing, store, readiness, or onboarding.

Links that satisfy none of these purposes are not added.

### Density controls

- Standard generated blocks expose a rotated window of four supporting pages.
- Pillars expose only the highest-signal supporting pages.
- Every generated block carries no more than two CTA links.
- Global navigation carries primary destinations, not the entire sitemap.
- The dedicated authority-grid page may expose the full graph because mapping is its explicit purpose.

### Self-evolving controls

The controller continuously checks:

- every sitemap page is registered;
- every registered page appears in at least one sitemap;
- every page is assigned to one primary cluster;
- every page receives inbound authority;
- every page is reachable from home;
- crawl depth remains within four clicks;
- every page has a path to a commercial conversion target;
- legacy generated blocks remain byte-stable;
- newly discovered pages receive a deterministic cluster recommendation;
- generic anchors are surfaced as improvement recommendations.

The system does **not** autonomously rewrite editorial content or invent relationships. It proposes deterministic, inspectable changes and blocks release until the graph is intentionally updated.

---

## 2. Page hierarchy map

```text
ClearGlass Inc. Home — authority hub
├── Cyber Defense & Security Operations
│   ├── Cyber Defense Console — pillar
│   ├── SENTINEL, GUARDIAN, BLUEDESK, Artemis Blue Team
│   ├── STEGOFORGE, ATT&CK Prompt Integrator
│   └── Environmental Cyber-Risk and GUARDIAN specification
├── Intelligence & OSINT
│   ├── Intelligence — pillar
│   ├── Flowsint, Ontario OSINT, Network Flow Intelligence
│   ├── ClearGlass NEXUS and NEXUS v12
│   └── Command Surface, Interface, and Platform Architecture
├── Artemis Platform
│   ├── Artemis OS — pillar
│   ├── ARTEMIS IV and AI Cyber Intelligence Platform
│   ├── Self-Evolving Platform and Artemis 2040
│   └── ZEPHYR and Air Systems Control
├── Command & Autonomous Operations
│   ├── PERCIVAL OS — pillar
│   ├── AVALON, Agent Mesh, AI Operator
│   ├── CONDUIT, PostLoop, Command Console
│   ├── Control Surface, Systems, Event Control, CG OS, PERCIVAL Build
│   └── Advanced Systems Catalog and AutoMap Orchestration
├── Legal, Tax & Compliance
│   ├── Legal Infrastructure — pillar
│   ├── AEGIS, ClearCounsel, Banking Law, ClearTax
│   ├── Procurement Legal-Tech, AI Liability, AI Legal Council
│   └── Privacy, terms, incorporation, governance, banking, IP and shares
├── Healthcare Intelligence
│   ├── ClearPulse — pillar
│   ├── ClearPulse Architecture
│   └── PHIPA Readiness and Checklist
├── Government & Procurement
│   ├── Government Solutions — pillar
│   ├── Procurement Readiness and Federal Supplier Handoff
│   ├── Counter-UAS and Traffic Enforcement
│   └── Storm-Adaptive Transit Digital Twin
├── Services & Engagements
│   ├── Services & Engagements — pillar
│   ├── Store and Pricing
│   ├── Security Quick-Audit and Hardening Sprint
│   ├── Autonomous Threat Modeling
│   ├── SMB Cyber Trust Kit and SMB Suite
│   └── Revenue Engine and Side Store
├── Web Design & UI Engineering
│   ├── Web Design & Development — pillar
│   ├── Ultra Glass, ClearGlass Ultra, Aurora Glass
│   └── Button Lab, Button System, Hover Menu
├── Opal-Koboi Automation
│   ├── Opal-Koboi — pillar
│   └── Product asset library and six system assets
├── ClearGlass Intelligence
│   ├── Blog hub — pillar
│   ├── Governed AI and agentic-security articles
│   ├── Cyber-defense and secure-deployment articles
│   ├── OSINT and public-accountability articles
│   ├── Autonomous threat modeling and post-quantum security
│   ├── Digital twins and frontier intelligence
│   └── Revenue, execution and product case studies
└── Company & Operations
    ├── Home — pillar
    ├── Public Authority Grid
    ├── Investor Data Room
    └── Client, CRM, incorporation, supplier and payments handoffs
```

---

## 3. Pillar-to-cluster matrix

| Pillar | Search and user intent | Supporting cluster | Proof layer | Conversion path |
|---|---|---|---|---|
| `index.html` | ClearGlass company and systems authority | Every primary domain | Investors and operating handoffs | Services, pricing, store, onboarding |
| `cyber-defense-console.html` | Cyber defense and security operations | SENTINEL, GUARDIAN, BLUEDESK, blue team, analysis | GUARDIAN spec, security architecture articles | Quick-Audit, Hardening Sprint, Threat Modeling |
| `intelligence.html` | OSINT and intelligence systems | Flowsint, NEXUS, Ontario OSINT, interfaces | Platform architecture and field workflows | Services, pricing, onboarding |
| `artemis-os.html` | Governed AI platform | Artemis IV, cyber intelligence, self-evolution, air systems | Self-evolving platform articles | Services, pricing, store |
| `percival-os.html` | Agent orchestration and autonomous operations | Agent Mesh, AI Operator, CONDUIT, AutoMap, command surfaces | Agent governance and secure deployment | Services, pricing, threat modeling |
| `legal/index.html` | Legal, tax and compliance infrastructure | Legal AI, procurement, liability, governance documents | Articles, bylaws, resolutions, policies | Services, onboarding |
| `clearpulse.html` | Healthcare intelligence and PHIPA | Architecture and readiness resources | Forensic-AI architecture | PHIPA assessment, store |
| `government.html` | Government systems and procurement | Supplier readiness, Counter-UAS, traffic, transit | Procurement and legal-tech proof | Procurement readiness, onboarding |
| `offers/index.html` | Commercial services | Audits, sprints, threat modeling, SMB, revenue | Relevant platform and architecture pages | Store, pricing, onboarding |
| `web-design.html` | Premium web and interface engineering | Glass systems and component studies | Design-system pages | Pricing, store, onboarding |
| `opal/index.html` | Deployable automation assets | Product asset sheets | Corresponding platform pages | Store, pricing |
| `blog/index.html` | Technical education and discovery | Governed AI, cyber, OSINT, infrastructure, execution | Linked platform and architecture pages | Relevant service, pricing, store |

---

## 4. Recommended anchor text for major pages

Use the target name plus a concise value statement.

| Target | Controlled anchor language |
|---|---|
| Home | `ClearGlass Inc. — governed intelligent systems` |
| Authority Grid | `ClearGlass Authority Network — the connected site knowledge graph` |
| Cyber Defense Console | `Cyber Defense Console — defensive operations command center` |
| Intelligence | `ClearGlass Intelligence — OSINT and operational intelligence systems` |
| Artemis OS | `Artemis OS — governed intelligence operating system` |
| PERCIVAL OS | `PERCIVAL OS — governed autonomous operations` |
| Agent Mesh | `Agent Mesh — multi-agent orchestration with controlled authority` |
| AutoMap | `AutoMap — architecture-aware orchestration and relationship mapping` |
| Government | `Government Solutions — resilient public-sector systems` |
| Procurement Readiness | `Procurement Readiness — verified supplier and bidding capability` |
| Services | `ClearGlass Services — governed security, AI and infrastructure engagements` |
| Autonomous Threat Modeling | `Autonomous Threat Modeling — continuous architecture-grounded security` |
| Security Quick-Audit | `Security Quick-Audit — focused exposure and control review` |
| Hardening Sprint | `Hardening Sprint — Microsoft 365 and Windows security implementation` |
| Blog | `ClearGlass Intelligence — technical research and implementation guidance` |
| Client Onboarding | `Start a ClearGlass engagement — governed client onboarding` |

Avoid `click here`, `learn more`, `read more`, bare URLs, unexplained acronyms, and repeated keyword-stuffed anchors.

---

## 5. Home-page internal links

The home hub should prioritize:

1. Cyber Defense Console
2. Intelligence & OSINT
3. Artemis OS
4. PERCIVAL OS
5. Government Solutions
6. Services & Engagements
7. Autonomous Threat Modeling
8. Legal Infrastructure
9. ClearPulse
10. ClearGlass Intelligence
11. Authority Grid
12. Investor Data Room

Home should not expose every supporting page. Pillars distribute authority downward; the Authority Grid provides complete map access without cluttering the homepage.

---

## 6. Major service-page internal links

### Services hub

Link to pricing, store, onboarding, Security Quick-Audit, Hardening Sprint, Autonomous Threat Modeling, SMB Cyber Trust Kit, PHIPA Readiness, Revenue Engine, and relevant proof pillars.

### Autonomous Threat Modeling

Link to:

- Autonomous Threat Modeling in 2026;
- Cyber Defense Console;
- BLUEDESK;
- Agent Mesh;
- Security Architecture for Agentic Software;
- Services hub;
- pricing and onboarding.

### Security Quick-Audit

Link to Cyber Defense Console, BLUEDESK, SMB Cyber Trust Kit, Hardening Sprint, store, and pricing.

### Hardening Sprint

Link to Cyber Defense Console, GUARDIAN, Security Quick-Audit, services, store, and onboarding.

### PHIPA Readiness

Link to ClearPulse, ClearPulse Architecture, the printable checklist, services, and onboarding.

### Web Design & Development

Link to interface proof pages, Button System, services, pricing, and onboarding.

---

## 7. Blog-pillar internal links

The blog pillar should expose subject groupings rather than a flat chronological list:

- Governed AI and agent governance
- Agentic software security
- Cyber defense and secure deployment
- Autonomous threat modeling
- OSINT and accountability
- Critical infrastructure and digital twins
- Post-quantum and frontier security
- Business execution and ethical revenue systems

Each grouping should link to the relevant platform pillar and service path.

---

## 8. Cluster-article internal links

Every article should contain:

1. a route back to `blog/index.html`;
2. one primary platform or domain pillar;
3. one or two adjacent articles;
4. one proof, architecture, or governance page where available;
5. one relevant commercial next step.

Examples:

- Autonomous threat modeling → Cyber Defense Console, Agent Mesh, agentic-software security article, Threat Modeling service.
- AI agent governance → PERCIVAL OS, AI Operator, agentic-software security, Threat Modeling service.
- OSINT workflow → Intelligence, Flowsint, government-accountability OSINT, services.
- Digital twins → Government Solutions, SATS Digital Twin, Environmental Cyber-Risk, onboarding.
- Post-quantum security → Cyber Defense Console, Artemis OS, Threat Modeling service, pricing.

---

## 9. Footer link structure

```text
Authority
- Cyber Defense
- Intelligence & OSINT
- Artemis OS
- PERCIVAL OS
- Authority Grid

Solutions
- Government
- Healthcare
- Small Business
- Web Design

Commercial
- Services
- Autonomous Threat Modeling
- Pricing
- Store
- Client Onboarding

Trust
- Legal Infrastructure
- Privacy
- Terms
- Procurement Readiness
- Investor Data Room

Insights
- ClearGlass Intelligence
- Current page's relevant cluster links
```

The global footer remains compact. The per-page generated authority block carries context-specific depth.

---

## 10. CTA link structure

Use two controlled CTA layers:

### Primary action

- `Book a security engagement`
- `Start an autonomous threat-modeling assessment`
- `Begin governed client onboarding`
- `Request a PHIPA readiness assessment`

### Evaluation action

- `Review pricing and engagement models`
- `Explore the implementation architecture`
- `Check procurement readiness`
- `Read the technical threat-modeling framework`

CTA sequence:

```text
Discovery → pillar → proof → service → onboarding / pricing / store
```

---

## 11. Prioritized implementation order

1. Treat all `sitemap*.xml` files as the indexability source of truth.
2. Register every indexable page in the authority graph.
3. Preserve the stable legacy generated blocks.
4. Attach new pages as reviewed supplemental cluster members.
5. Add only explicit, defensible cross-cluster bridges.
6. Maintain the public Authority Grid.
7. Keep the shared navigation limited to primary destinations plus the Authority Grid.
8. Validate zero orphans and home reachability.
9. Validate a maximum four-click crawl depth.
10. Validate a conversion path from every page.
11. Surface generic native anchors as recommendations.
12. Fail CI when a new sitemap page is not mapped.
13. Review desktop, mobile, keyboard, contrast and reduced-motion behavior.
14. Monitor internal-link clicks, crawl depth, landing-page progression and assisted conversions.
15. Expand by adding technical depth, not indiscriminate link volume.

---

## Maintenance and governance

- Never hand-edit `cg-related` generated blocks.
- Never auto-write links into editorial paragraphs.
- Never create a relationship solely to increase link count.
- Preserve exact page purpose and primary cluster ownership.
- Add supplemental pages without reshuffling established sibling rotations.
- Require descriptive destination language.
- Keep commercial links relevant to the current intent.
- Use CI as the release gate for sitemap, HTML, graph, navigation, and AI-readable map changes.
- The network may diagnose and recommend improvements automatically; human-reviewed configuration remains the final authority.
