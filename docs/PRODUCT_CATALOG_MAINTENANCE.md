# Product Catalog Maintenance

## Sources of truth

- `data/products.json` is the source for the public website's systems and demonstration catalog.
- `nav.js` contains the site's legacy primary/mobile product navigation. Existing destinations are retained for compatibility; new public entries must be reconciled with the JSON catalog.
- `products.html` owns the catalog page's canonical URL, Open Graph metadata, and `CollectionPage` JSON-LD with a public-route `ItemList`.
- `sitemap.xml` lists discoverable public routes, not every implementation file or internal prototype.
- `data/store/catalog.json`, `data/side-store/catalog.json`, `control-plane/app/data/pricebook.json`, and `storefront/lib/catalog.ts` are distinct commerce sources. Do not merge their entries into the portfolio catalog.

## Required metadata

Each portfolio record keeps its existing ID, slug, name, description, category, status, productUrl and any existing display attributes. Add or maintain:

- `tagline`: derived from an existing short description/description unless the source provides an approved tagline.
- `audience`: use a documented audience or explicitly state that the current evidence does not specify it.
- `keyCapabilities`: capabilities supported by code/docs/tests; if derived from legacy tags, the evidence notes must say the tags were not independently verified.
- `sourcePath`: repository file that substantiates the entry.
- `publicUrl` or `internalRoute`: relative public route only when a safe public surface is intended; internal systems must not advertise private service endpoints.
- `repositoryPath`, `documentationLink`, `ctaLabel`, `ctaDestination`, `seoTitle`, `seoDescription`, `keywords`, `last_verified` (ISO date), `evidence_notes`.
- `integrationStatus`: the conservative, evidence-based assessment. It is independent of the pre-existing `status` and never overwrites that field.
- `seoIndexable`: explicit boolean for search indexing, separate from card visibility. Set `false` when the destination uses a `noindex` robots directive or public/private intent remains unresolved. Such routes stay in the catalog only as required, but are excluded from sitemap additions and the JSON-LD `ItemList`.
- `catalogVisibility`: `public` or `internal`. Internal cards use the safe `/index.html#contact` CTA and do not expose the implementation route as a card destination.

## Integration status definitions

Use only these inventory values:

- `LIVE / OPERATIONAL`: a successful current browser/API check, current-source/freshness check where relevant, and successful applicable CI/release checks support the claim.
- `BETA / DEMO`: an explicitly labelled demo with verified boundaries and no implied production operation.
- `INTERNAL / ADMIN`: internal service, restricted tool, backend, or admin surface; safe contact CTA only.
- `PROTOTYPE`: implemented prototype, simulation, mock provider, synthetic data, or non-production harness.
- `PLANNED / IN DEVELOPMENT`: architecture, roadmap or design-stage implementation.
- `ORPHANED / NEEDS WIRING`: a distinct supported capability exists in source but its intended discovery surface is missing; check for duplicates before adding a card.
- `UNKNOWN / NEEDS REVIEW`: evidence is incomplete or current runtime/deployment cannot be verified.

Do not infer operational status from a file name, catalog field named `available`, manifest, deployment configuration, workflow definition, screenshot, or previous audit alone.

## Adding or updating an entry

1. Inspect the actual implementation, supporting docs/tests, route and integrations before changing the record.
2. Search the existing catalog for a duplicate name, ID, slug, or related route. Prefer a `relatedRoutes` reference over a second card where a demo is another view of the same system.
3. Keep every existing ID, slug, productUrl, ordering and status unless a separately approved change specifically requires otherwise.
4. Populate metadata from evidence. If an audience/capability cannot be established, state that in the record rather than invent it.
5. For an internal service, use `catalogVisibility: "internal"`, `publicUrl: null`, a clearly marked `internalRoute` description, and `ctaDestination: "/index.html#contact"`. Never put credentials, tokens or private endpoint URLs in catalog data, docs, PR text or screenshots.
6. For a public demo, retain a demo/prototype assessment and show the synthetic-data or read-only boundary.
7. Add public product cards to `nav.js` without deleting or reordering existing destinations. Internal-only catalog records do not need public navigation links.
8. Keep the public `ItemList` JSON-LD synchronized with `catalogVisibility`, `publicUrl`, and `seoIndexable`. Exclude any `seoIndexable: false` destination. Do not index private route targets or market simulations as operational services.
9. Add a canonical sitemap URL only for an intended, indexable public route whose URL and robots directives have been checked. Do not add noindex pages, source files, drafts, internal routes, aliases or duplicate routes by default.

## Validation checklist

Run the available checks from the repository root:

```bash
python -m unittest tests.test_product_command_center
python -m pytest tests/test_product_command_center.py
python scripts/verify_site.py
node --check nav.js
node --check assets/js/product-command-center.js
python -c "import json; json.load(open('data/products.json', encoding='utf-8'))"
python tools/catalog_contract.py --json
```

The last command audits the three **commerce** catalogs; it does not replace tests of `data/products.json`. The commerce contract's `--strict` mode is deliberately not a release gate until required commercial policy values are supplied.

For material UI changes, open the Products page in a real browser at desktop and mobile widths; verify cards, search, filters, comparison, CTA destinations, status labels and console/network errors. A source-tree existence check or crawler snapshot alone is not a browser render test.

Record the exact command, exit code, and CI run link. When a command cannot be run in the current environment, record `NOT_EXECUTABLE_IN_THIS_ENVIRONMENT`, not a pass. Do not merge or deploy if a required validation fails. Production deploys, DNS and secret/permission changes require separate approval.

## Rollback

The catalog integration is designed to be reversible without production migrations. Close the pull request unmerged or revert the relevant additive commits. Do not delete the legacy route files as part of rollback; the legacy navigation and destinations are compatibility surfaces.
