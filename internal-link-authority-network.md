# ClearGlass Internal-Link Authority Network

## Operating objective

ClearGlass Inc. is structured as one connected authority system rather than a collection of isolated pages. The home page is the authority hub; pillar pages define the major subject domains; cluster pages deepen those domains; proof and architecture pages reinforce trust; service pages create commercial paths; and the blog expands discovery coverage.

The production source of truth is `tools/internal_links.py`. It generates crawlable, static, marker-delimited related-content blocks for every mapped page and validates that no mapped page is missing, orphaned, duplicated across clusters, or stale.

## Page hierarchy

```text
Home / Company authority hub
├── Cyber Defense & Security Operations
│   ├── Sentinel, Guardian, BLUEDESK, Artemis Blue Team
│   ├── Stegoforge, ATT&CK Prompt Integrator
│   └── Environmental cyber-risk and Guardian specification
├── Intelligence & OSINT
│   ├── Flowsint, ClearGlass NEXUS, Ontario OSINT
│   ├── Network Flow Intelligence
│   └── Intelligence command, interface, platform and NEXUS v12 pages
├── Artemis Platform
│   ├── Artemis IV, Artemis AI Cyber Intelligence
│   ├── Self-Evolving Platform, Artemis 2040
│   └── Zephyr and Air Systems Control
├── Command & Autonomous Operations
│   ├── AVALON, Agent Mesh, AI Operator
│   ├── Conduit, PostLoop, Command Console
│   └── Control Surface, Systems, Event Control, CG OS and Percival Build
├── Legal, Tax & Compliance
│   ├── AEGIS, ClearCounsel, Banking Law, ClearTax
│   ├── Procurement legal-tech and AI liability
│   └── Privacy, terms and corporate governance documents
├── Healthcare Intelligence
│   ├── ClearPulse architecture
│   └── PHIPA readiness and checklist
├── Government & Procurement
│   ├── Procurement readiness and federal supplier handoff
│   └── Counter-UAS and traffic-enforcement platforms
├── Services & Engagements
│   ├── Store, pricing and service offers
│   ├── SMB Cyber Trust Kit and SMB Suite
│   └── Security Quick-Audit, Hardening Sprint and Revenue Engine
├── Web Design & UI Engineering
│   ├── Ultra Glass, ClearGlass Ultra and Aurora Glass
│   └── Button and navigation component studies
├── Opal-Koboi Automation
│   └── Product asset library and system assets
├── ClearGlass Intelligence / Insights
│   └── Governed AI, cyber defense, OSINT, architecture and business execution essays
└── Company & Operations
    ├── Investor data room
    └── Client onboarding, CRM, incorporation and payments handoffs
```

## Pillar-to-cluster matrix

| Pillar | Primary intent | Supporting depth | Conversion path |
|---|---|---|---|
| `cyber-defense-console.html` | Defensive security authority | Sentinel, Guardian, BLUEDESK, blue-team and analysis systems | Store, Security Quick-Audit |
| `intelligence.html` | OSINT and intelligence authority | Flowsint, NEXUS, Ontario OSINT and intelligence interfaces | Store, pricing |
| `artemis-os.html` | Artemis platform authority | Artemis IV, self-evolving AI, cyber intelligence and air systems | Pricing, store |
| `percival-os.html` | Autonomous operations authority | Agent Mesh, AI Operator, Conduit, PostLoop and command surfaces | Services, pricing |
| `legal/index.html` | Legal and compliance authority | Legal AI, tax, procurement, governance and policy pages | Store, services |
| `clearpulse.html` | Healthcare intelligence authority | Architecture and PHIPA readiness resources | PHIPA assessment, store |
| `government.html` | Public-sector and procurement authority | Supplier readiness, Counter-UAS and traffic enforcement | Store, procurement readiness |
| `offers/index.html` | Commercial services authority | Audits, sprints, SMB services, pricing and store | Store, pricing |
| `web-design.html` | Design engineering authority | Glass interfaces, component systems and interaction studies | Store, pricing |
| `opal/index.html` | Automation asset authority | Opal-Koboi product and platform assets | Store, pricing |
| `blog/index.html` | Discovery and topical expansion | Governed AI, cybersecurity, OSINT and execution essays | Store, pricing |
| `index.html` | Company authority hub | Investor and operational handoff pages | Store, pricing |

## Anchor standard

Anchors must describe the destination and its value. The generated pattern is:

```html
<a href="target.html"><b>Target name</b> — concise target description</a>
```

Approved examples:

- `Cyber Defense Console — the ClearGlass command center for defensive operations`
- `Flowsint — OSINT investigation graph for domains, IPs and transforms`
- `PERCIVAL OS — mission-ready governed command center`
- `Procurement Readiness — verified supplier-registration status`
- `Security Quick-Audit — a focused $249 security review`

Avoid `click here`, `learn more`, `read more`, bare URLs, vague product names without context, and repeated exact-match anchors that do not read naturally.

## Link-layer rules

### Home hub

The home page links to every major pillar, the services layer, pricing, store, investor information and the highest-value proof systems. It remains the shortest path to every primary domain.

### Pillar pages

Each pillar links to its strongest supporting pages, adjacent pillars where semantically justified, and a controlled two-link CTA path. Pillars do not become link directories; only the highest-signal links appear in the visible authority block.

### Cluster pages

Each supporting page links back to its pillar, forward to rotated sibling pages, laterally through curated cross-cluster bridges, and onward to a relevant conversion path. Rotation prevents authority from pooling only on the first few pages in a cluster.

### Blog pages

Each article links to its blog pillar, adjacent essays and the product or service page that operationalizes the article’s subject. Discovery therefore progresses to proof and then conversion.

### Proof and architecture pages

Specifications, architecture pages and governance documents link to the platform or service they validate. Product pages link back to the most relevant proof page when the connection is useful to a buyer.

### Services and CTAs

Service pages link to proof, process, pricing and contact or booking paths. CTA anchors state the action and expected destination, such as `Book a security engagement`, `See pricing & plans`, or `Get the free PHIPA readiness checklist`.

### Navigation and footer

Global navigation carries only primary destinations. The generated `Continue exploring` authority block functions as the semantic footer layer on standard pages. Full-viewport command interfaces receive the same network through a compact, keyboard-accessible dock so the visual canvas is not disrupted.

## Visual signal standard

The authority block uses a dark glass surface, controlled luminous borders, compact high-contrast anchors, restrained hover illumination and a clear CTA separator. It must remain readable on both light and dark page themes, preserve whitespace and avoid continuous decorative animation. Full-viewport docks expand only on hover or keyboard focus. Reduced-motion preferences remain respected.

## Home-page links

Priority home destinations:

1. Cyber Defense Console
2. Intelligence & OSINT
3. Artemis Platform
4. PERCIVAL OS / Command & Autonomous Operations
5. Services & Engagements
6. Government & Procurement
7. Legal Infrastructure
8. Healthcare Intelligence
9. ClearGlass Intelligence blog
10. Investor Data Room

The home page should not expose every supporting page directly; pillars distribute authority downward.

## Major service-page links

- Services hub → pricing, store, Security Quick-Audit, Hardening Sprint, SMB Cyber Trust Kit, Revenue Engine and relevant proof pillars.
- Store → service hub, pricing, SMB Cyber Trust Kit and primary proof systems.
- Pricing → services hub, store and the main service categories.
- Security Quick-Audit → Cyber Defense Console, BLUEDESK, SMB Cyber Trust Kit and store.
- Hardening Sprint → Cyber Defense Console, Guardian, services hub and store.
- PHIPA Readiness → ClearPulse, architecture, checklist and store.

## Blog pillar and cluster links

The blog pillar exposes the strongest subject groups rather than every article equally. Individual articles link to:

- the blog pillar;
- one or more adjacent articles;
- the central product or platform page;
- a relevant service or pricing path.

Examples:

- AI agent governance → PERCIVAL OS and AI Operator.
- AI agents as insider threats → BLUEDESK and Cyber Defense Console.
- Agentic software security architecture → Agent Mesh and Cyber Defense Console.
- OSINT workflow → Flowsint and Intelligence.
- Government-accountability OSINT → Flowsint and Procurement Legal-Tech.
- Self-evolving AI → Artemis Self-Evolving Platform and Artemis OS.

## Footer structure

The semantic footer layer should remain compact:

```text
Authority domains
- Cyber Defense
- Intelligence & OSINT
- Artemis
- Autonomous Operations

Commercial
- Services
- Pricing
- Store
- Procurement Readiness

Trust
- Legal Infrastructure
- Privacy
- Terms
- Investor Data Room

Insights
- ClearGlass Intelligence
- Relevant cluster links selected per page
```

The global footer should not duplicate the entire sitemap. Per-page related links provide local relevance; global links provide structural consistency.

## CTA structure

Use a maximum of two primary next-step links in the generated authority block:

1. Immediate commercial action: book, start, request or obtain.
2. Evaluation action: pricing, services, readiness or proof.

CTA order follows user intent:

```text
Discovery → pillar → proof/process → service → pricing/store/intake
```

## Implementation order

1. Maintain the source-of-truth graph in `tools/internal_links.py`.
2. Add every new indexable page to `PAGES` and exactly one cluster.
3. Add curated cross-cluster bridges only where the relationship is defensible.
4. Regenerate blocks with `python3 tools/internal_links.py`.
5. Add the page to `sitemap.xml`.
6. Run `python3 tools/internal_links.py --check`.
7. Let the Internal Link Authority workflow verify graph integrity, inbound coverage and sitemap completeness.
8. Review the page visually on desktop, mobile, light, dark and full-viewport layouts.
9. Measure crawl depth, internal-link clicks, conversion progression and orphan-page count.
10. Expand clusters by adding depth, not by adding indiscriminate links.

## Maintenance rules

- Generated blocks are delimited by `<!-- cg-related:start -->` and `<!-- cg-related:end -->`.
- Do not hand-edit generated blocks.
- Do not place a page in multiple clusters unless the generator is deliberately redesigned for multi-parent taxonomy.
- Keep cross-cluster bridges curated and sparse.
- Keep anchor terminology consistent with page titles, metadata and service language.
- When the graph changes, regenerate all blocks and update the sitemap in the same pull request.
- The validation workflow is a release gate for changes affecting HTML, the sitemap, the graph generator or AI-readable site maps.
