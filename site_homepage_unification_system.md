# ClearGlass Website Homepage Unification System

## Pages that need to be matched to the homepage

All indexable static webpages should inherit the homepage system through `tokens.css`, `ui.css`, `brand-system.css`, and `nav.js`. Priority groups:

1. **Primary market pages** — `index.html`, `government.html`, `pricing.html`, `store.html`, `offers/index.html`, `web-design.html`, and `blog/index.html`.
2. **Platform and product pages** — Artemis, PERCIVAL, GUARDIAN, BLUEDESK, NEXUS, ClearPulse, Flowsint, Conduit, command surfaces, SMB, legal, tax, air-control, and Opal-Koboi product pages.
3. **Operational consoles and prototypes** — command dashboards, control surfaces, intelligence interfaces, autonomous operations pages, and design-system pages.
4. **Support pages** — legal pages, thank-you pages, redirects, offline/404 pages, and generated related-link blocks.

## Homepage elements to reuse across the site

- Fixed premium glass navigation with the complete product catalog and one clear booking CTA.
- Crystal-light palette: sky, violet, pink, mint, amber, and deep ink.
- Editorial serif display headings paired with clean sans-serif body copy and mono-eyebrows.
- Hero rhythm: narrow eyebrow, large strategic claim, calm explanatory copy, primary/secondary CTAs.
- Glass cards with soft borders, rounded corners, subtle lift, and restrained glow.
- Section header pattern: mono tag, serif headline, concise supporting paragraph.
- Product-card pattern: product era label, product name, description, two or more preserved proof/features, and a clear open/explore CTA.
- Related-link blocks that keep users moving through the ClearGlass network.

## Navigation standards

- Global navigation is the source of truth for wayfinding and is injected by `nav.js`.
- The Products menu must mirror the full catalog, not only highlighted flagship pages.
- Top-level labels stay simple: Vision, Services, Products, Government, Insights, Contact, and Book a Security Engagement.
- Product labels use the shortest recognizable product name with a one-line scan hint.
- Mobile navigation exposes the same product catalog as desktop.
- CTA language is standardized around `Book a Security Engagement`, `Open [Product]`, `Explore [Product]`, and `See pricing & plans`.

## Heading, spacing, and flow standards

- Every page should follow a homepage-like sequence: hero → trust/mission strip → capability sections → product or workflow cards → governance/evidence → CTA → related links.
- Headings use title-style strategic language rather than fragmented labels.
- Eyebrows use uppercase mono labels for category, stage, or product family.
- Sections use generous vertical rhythm: roughly 80–140px desktop spacing and compact but breathable mobile spacing.
- Cards use two-column or responsive grid structure with equal card rhythm.
- CTAs appear after meaningful context, not before users know what action means.

## Rewritten global page structure

```text
1. Global glass navigation
2. Hero
   - Product/family eyebrow
   - Homepage-tone H1
   - Existing page content rewritten into one concise lead
   - Primary CTA + secondary CTA
3. Mission / positioning strip
   - Preserve original purpose, audience, and value proposition
4. Core capabilities
   - Existing features organized as consistent glass cards
5. Workflow / architecture / evidence
   - Preserve diagrams, tables, consoles, specs, and technical sections
6. Governance and trust
   - Human approval, auditability, privacy/security, provenance, or reliability notes when applicable
7. Product links and next-step CTAs
   - Cross-links to related ClearGlass systems
8. Generated related-link block
9. Footer / legal / metadata
```

## Final products list and nav list

The global product and navigation catalog is maintained in `nav.js` and is mirrored by the homepage `Full Product Catalog` section. Current product entries:

- Artemis IV Core
- Artemis VI
- Artemis OS
- Artemis 2040
- Artemis Self-Evolving
- AI Cyber Intelligence
- AVALON · Artemis + Percival
- PERCIVAL OS
- SENTINEL
- GUARDIAN
- BLUEDESK
- BLUEDESK Mobile
- ClearGlass NEXUS
- NEXUS v12
- Intelligence Command Surface
- Intelligence Interface
- Flowsint
- Network Flow Intelligence
- Ontario OSINT Deck
- Agent Mesh
- AI Operator Workspace
- CONDUIT
- PostLoop
- AutoMap
- Command Console
- Event Control Surface
- Systems Console
- Control Surface
- CG OS
- CLEARSIGHT
- ZEPHYR Air Control
- Air Systems Control
- ClearPulse
- ClearPulse Architecture
- AEGIS
- ClearCounsel
- ClearBank Legal AI
- ClearTax AI
- Government Solutions
- Counter-UAS OS
- Speed Vision AI
- SATS Digital Twin
- SMB Suite
- SMB Cyber Trust Kit
- Revenue Engine
- Opal-Koboi Assets
- Artemis IV Core · Asset
- Artemis VI · Asset
- Guardian · Asset
- Revenue Engine · Asset
- SMB Suite · Asset
- Ultra Glass
- ClearGlass Ultra
- Aurora Glass
- Button System
- Button Lab
- Web Design & Development
- Store
- Side Store
- Pricing
