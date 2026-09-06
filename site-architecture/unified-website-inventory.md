# ClearGlass Inc. Unified Website Inventory and Harmonization Report

Status: implemented shared-shell harmonization layer. No files or meaningful content were removed.

## Site inventory method

The inventory was verified from repository evidence by scanning static HTML pages, sitemap entries, navigation/catalog data in `nav.js`, root shared CSS/JS assets, product sheets under `products/opal-koboi/`, blog routes, legal routes, operations handoff routes, and downloadable/static assets referenced by the site.

## Discovered route groups

- Root marketing and platform pages: homepage, Artemis family, PERCIVAL, SENTINEL, GUARDIAN, BLUEDESK, NEXUS, intelligence, command surfaces, legal-tech, government, healthcare, air-control, SMB, commerce, pricing, store, design-system, and UI lab pages.
- Product asset pages: `products/opal-koboi/` index and product sheets.
- Legal pages: legal index, privacy, terms, governance templates, content policy, legal-council materials.
- Offers and operations pages: PHIPA readiness, security audit, hardening sprint, threat modeling, handoff pages, onboarding and procurement readiness pages.
- Blog/resources pages: blog index plus AI governance, cyber architecture, Artemis, AgentOps, OSINT, deployment, and platform audit articles.
- Fixed-viewport command/HUD pages: Artemis FAWL and Sentinel command dashboards retain their specialized content while receiving the global shell where safe.
- Downloadable/static resources: image/logo assets, XML sitemaps, service worker, manifests, CSS, JS, data files, and committed product/support assets.

## Homepage elements reused site-wide

- Premium fixed glass navigation with logo, product mega-menu, primary CTA, keyboard focus states, and mobile menu behavior.
- Homepage-derived fonts: Cormorant Garamond display, Urbanist interface, IBM Plex Mono labels.
- Prism accent system: cyan, violet, pink, amber, mint gradient, glow layers, glass borders, rounded panels.
- Shared CTA language: View Product, Request an Assessment, See Capabilities, Contact ClearGlass, Book a Security Engagement.
- Card language: rounded glass panels, icon capsules, eyebrow metadata, soft shadows, hover lift, and consistent spacing.
- Responsive rules: desktop mega-menu, mobile full-catalog menu, compressed header dimensions, touch-friendly links.
- Accessibility standards: semantic nav landmark, `aria-label`, `aria-expanded`, visible focus outline, reduced duplicated menu markup via script injection.

## Pages requiring alignment and changes applied

All static pages using `nav.js` now inherit the homepage-matched shell. Pages with older local headers/footers keep their original content for compatibility, while the global shell sits above them as the canonical navigation system. The central gap was the absence of a complete product index; `products.html` now provides the unified catalog. Fixed command-surface pages remain functional exceptions for viewport-specific layouts, with the global shell added conservatively only where it did not remove page logic.

## Final global standards

- Navigation: Home, Products, Solutions, Company, Resources, Contact, plus a primary security-engagement CTA.
- Products: every verified product in `nav.js` appears in the desktop mega-menu, mobile catalog, and `products.html`.
- Headings: one page-level `h1`, section `h2`, card `h3`, monospace eyebrow labels.
- Layout: max-width containers near 1180px, 72–140px section rhythm, rounded glass panels, responsive grids.
- Buttons/CTAs: pill buttons with dark primary and glass secondary variants.
- Motion: subtle hover lift, menu transitions, design-system ambient FX where pages load `cg-design-system.js`.
- Footer/linking: existing generated related-link blocks remain untouched; public URLs are preserved.
- Accessibility: nav landmark, keyboard focus, large mobile targets, descriptive product labels.

## Reusable page template

1. Global navigation shell.
2. Context eyebrow or breadcrumb.
3. Hero with precise promise, value proposition, primary CTA, optional secondary CTA.
4. Strategic value section.
5. Capability cards.
6. Workflow/operating model.
7. Evidence/outcomes.
8. Ecosystem and related products.
9. Final CTA.
10. Existing footer or generated related-link block.

## Final product catalog

The authoritative implementation catalog is rendered in `products.html` from the verified `nav.js` product array. Categories used for the product listing are: Intelligence and command platforms; Cybersecurity and resilience; Industry solutions; Commercial tools, assets, and resources; Product ecosystem.

## Navigation map

Desktop: Home → Products mega-menu / All Products → Solutions → Company → Resources → Contact → Book a Security Engagement.

Mobile: Navigation links first, primary CTA, then every product link in the verified catalog.

## File-level change summary

- Added `products.html`: central product listing page with all verified product entries, grouped cards, homepage-derived visual system, SEO metadata, structured data, and CTAs.
- Updated `nav.js`: Products now links to the central catalog while preserving the accessible mega-menu and full mobile product list; top-level hierarchy now matches the directive.
- Updated `sitemap.xml`: added the new central products route.
- Updated `sentinel/ARTEMIS_FAWL_COMMAND_SURFACE.html`: added the global shell script without removing dashboard content.
- Added this report to document inventory, consolidation, standards, risks, and validation.

No files were removed.

## Validation report

Checks performed: repository status/diff review, product extraction from `nav.js`, static route discovery using `rg --files`, sitemap update, HTML syntax-oriented validation via Python parsing/check scripts, and link existence checks for product/catalog links.

Known limitations: this implementation uses a shared enhancement layer rather than manually rewriting every historical page body. Some legacy pages retain local headers/footers beneath the canonical global shell to avoid removing content or breaking page-specific behavior. Full visual regression, browser console review, and screen-reader testing require a browser QA pass outside this terminal run.

Recommended next actions: progressively migrate legacy local header/footer markup into reusable partials if the static site adopts a build step, and run a full browser-based accessibility/link crawl before publication.
