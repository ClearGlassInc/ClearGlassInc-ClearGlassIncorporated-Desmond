# ClearGlass Inc. — SEO Strategy & Execution Plan

**Domain:** www.clearglassinc.com · **Prepared:** 2026-07-28
**Scope:** technical SEO, structured data, local search, content, internal linking, measurement.

---

## 0. Read this first — the brief did not match the business

The brief asked to optimise for **glass repair, storefront replacement, window
replacement, shower enclosures, and emergency glazing service**. ClearGlass Inc.
does not sell any of those. The name reads like a glazier; the company is not one.

What the site actually sells, verified across all 141 pages:

| Real offering | Evidence |
|---|---|
| Governed AI automation & autonomous agents | `ai-operator.html`, `artemis-*.html`, `percival-os.html`, `conduit.html` |
| Cybersecurity consulting & zero-trust architecture | `cyber-defense-console.html`, `guardian.html`, `bluedesk.html` |
| OSINT / investigative tooling | `flowsint.html`, `Ontario-osint.html`, `blog/osint-workflow-*` |
| Legal-tech & compliance (PHIPA, procurement) | `corporate-legal-advisor.html`, `offers/phipa-readiness.html` |
| Government & federal solutions | `government.html`, `operations/federal-supplier-handoff.html` |
| Website design & development | `web-design.html` |
| Fixed-fee security engagements | `offers/security-quick-audit.html`, `offers/hardening-sprint.html` |

**Business identity (from `index.html` structured data):** ClearGlass Inc.,
Burlington, Ontario, Canada · +1-289-707-0269 · founded 2024 · founder Desmond
Otieno Odhiambo.

Building glazing pages would have been the textbook definition of a **doorway
page** — content created to catch traffic for services that do not exist. It
would have failed, and it violates the brief's own safety rules. **This strategy
therefore targets the real business.** Everything below is built on the actual
service lines.

> If ClearGlass genuinely intends to enter the glazing market, that is a new
> service line requiring real capability first — not an SEO task.

---

## 1. Prioritized SEO action plan

Ordered by **impact ÷ effort**. Status reflects work shipped in this change.

### Tier 1 — shipped in this change

| # | Action | Why it matters | Status |
|---|---|---|---|
| 1 | Added `Service` + `FAQPage` + `BreadcrumbList` schema to `web-design.html` | Money page had **zero** structured data | ✅ Done |
| 2 | Added `Service`/`OfferCatalog` schema to `smb.html`, `government.html`, `pricing.html` | All three had zero structured data | ✅ Done |
| 3 | Added 5 orphaned pages to `sitemap.xml` | They were invisible to crawler discovery | ✅ Done |
| 4 | Registered 2 orphaned pages in the authority network and gave them real inbound links | They were in the sitemap but no page linked to them | ✅ Done |
| 5 | Added `url` to 44 `Organization` schema nodes across 30 pages | Missing required property blocked rich-result eligibility | ✅ Done |
| 6 | Added the real social profiles to `sameAs` | Entity consolidation for a Knowledge Panel | ✅ Done |
| 7 | Added `areaServed` + `serviceArea` geo targeting to homepage | Local relevance for Burlington / Halton / GTA | ✅ Done |
| 8 | Added missing canonicals (3 pages) and static `<h1>`s (2 pages) | Duplicate-signal and topic-clarity fixes | ✅ Done |
| 8b | Flagged `platform-command-center.html`: `noindex` **and** in the sitemap | Needs an owner decision — see §3 | ⚠️ Open |
| 9 | Built `tools/seo_audit.py` + `tools/seo_dashboard.py` + `seo-dashboard.html` | Continuous measurement instead of one-off audits | ✅ Done |

**Result: health score 63 → 79/100, blocking errors 10 → 0, sitemap coverage 100%.**

### Tier 2 — highest-value work remaining (owner action required)

| # | Action | Effort | Impact |
|---|---|---|---|
| 10 | **Claim & complete Google Business Profile** | 2h + verification | Highest local ROI available. Nothing else unlocks map visibility. |
| 11 | **Publish business hours** on the site, then add `openingHoursSpecification` | 1h | Deliberately omitted from schema — inventing hours would be fabrication |
| 12 | Verify the domain in **Bing Webmaster Tools**, import from GSC | 30m | Bing feeds Copilot and ChatGPT search |
| 13 | Rewrite 61 over-long meta descriptions | 4h | Snippet control; currently Google rewrites them |
| 14 | Shorten 41 over-length title tags | 3h | Truncated titles lose the keyword or the brand |
| 15 | Split `clearglass-nexus.html` (384 KB) and `ClearGlass-NEXUS-v12-FINAL.html` (308 KB) | 1d | Direct LCP / Core Web Vitals cost |
| 16 | Resolve the `loader.html` first-visit redirect (see §3) | 2h | Bot/user divergence carries cloaking risk |
| 17 | Build 4 service-area pages (Burlington, Hamilton, Oakville, GTA) | 2d | Local commercial intent — only if genuinely served |
| 18 | Collect real customer reviews | ongoing | Trust signal, and required for review rich results |

---

## 2. Exact on-page optimizations for key pages

Character counts verified. Titles target ≤60, descriptions 140–160.

### `index.html` — homepage
- **Current title (68):** `ClearGlass Inc — AI Automation, Cybersecurity & Operational Strategy`
- **Proposed (57):** `AI Automation & Cybersecurity Consulting | ClearGlass Inc`
- **Current description (172)** is over length; tighten the buyer signal:
- **Proposed description (142):** `ClearGlass Inc. designs governed AI automation, zero-trust cybersecurity, and OSINT systems for high-trust organizations. Burlington, Ontario.`
- **H1:** must contain the category, not only the brand — `Governed AI automation and cybersecurity for high-trust organizations`
- Add a visible NAP block (name, address, phone) in the footer. Schema alone is not enough; the crawler wants the text to corroborate it.

### `web-design.html` — strongest commercial-intent page
- **Current title (70):** `Website Design & Development — Growth Infrastructure | ClearGlass Inc.`
- **Proposed (56):** `Website Design & Development Burlington | ClearGlass Inc`
- **Proposed description (147):** `Fast, secure, accessible websites engineered as growth infrastructure. Architecture, front-end build, Core Web Vitals and SEO. Burlington, Ontario.`
- ✅ `Service` + `FAQPage` + `BreadcrumbList` schema added — the 6 FAQ entries mirror the visible `<details>` copy exactly, as Google requires.

### `pricing.html` — conversion page
- **Current title (58):** `Pricing & Engagements — Start with ClearGlass | ClearGlass`
- **Proposed (53):** `Fixed-Fee Security & Web Engagements | ClearGlass Inc`
- Add visible prices. `OfferCatalog` schema is shipped but carries no `price` — Google will not show a price rich result without one, and inventing prices is not an option.

### `government.html`
- **Current title (58):** `ClearGlass Inc. — Federal & Government Solutions | FedRAMP`
- ⚠️ **Verify the FedRAMP claim.** If ClearGlass is not FedRAMP authorised, remove the term — an unsupported compliance claim is a trust and legal risk far larger than any ranking gain.
- **Proposed (55):** `Government & Federal AI Security Solutions | ClearGlass`

### `smb.html`
- **Current title (44):** `SMB Suite — ClearGlass · Intelligent Systems`
- **Proposed (51):** `AI & Cyber Security for Small Business | ClearGlass`
- The H1 is `sr-only`. For a commercial page the primary heading should be **visible** — it is the strongest on-page relevance signal.

### `offers/phipa-readiness.html` — best long-tail opportunity
- "PHIPA readiness" is low-competition, high-intent, and Ontario-specific. Give it a dedicated FAQ block plus `FAQPage` schema, and link it from every healthcare-adjacent page.

---

## 3. Technical SEO checklist

### ✅ Already correct
- [x] HTTPS with canonical host `www.clearglassinc.com` (CNAME)
- [x] `robots.txt` allows all major crawlers, and explicitly welcomes AI answer engines (GPTBot, ClaudeBot, PerplexityBot) — a genuine advantage for AI-search citation
- [x] `sitemap.xml` valid, 131 URLs, **zero dead entries**, 100% coverage of indexable pages
- [x] Mobile viewport meta on every page
- [x] Service worker + offline page
- [x] `lang="en"` throughout
- [x] Zero broken internal links
- [x] Canonical on every indexable page

### ⚠️ Needs attention

**1. The first-visit loader redirect (`index.html`, lines 18–33)**
JavaScript redirects first-time visitors to `/loader.html`, with a user-agent
test that exempts crawlers. Serving crawlers a different experience than users
is the mechanism search engines classify as **cloaking**, even when the intent is
benign. The risk is small (the bot path shows *more* content, not less) but it is
unnecessary. Prefer one of:
  - render the loader as an overlay on the real page, no navigation; or
  - drop the UA test and let the redirect apply to everyone equally.

**2. Page weight** — `clearglass-nexus.html` 384 KB, `ClearGlass-NEXUS-v12-FINAL.html` 308 KB, `artemis-iv.html` 168 KB, `index.html` 152 KB. All inline CSS/JS. Extract shared CSS to a cached external file.

**3. Duplicate content** — `clearglass-nexus.html` and `ClearGlass-NEXUS-v12-FINAL.html` carry identical titles and near-identical content. Pick the canonical one and point the other at it with `rel=canonical`.

**4. Render-blocking Google Fonts** — the homepage blocks on a 3-family stylesheet. Add `media="print" onload="this.media='all'"` or self-host.

**5. Meta description length** — 61 pages exceed 165 characters (worst: 269).

**6. Title length** — 41 pages exceed 62 characters (worst: 124).

**7. Heading hierarchy** — 39 pages skip a level (e.g. `h2` → `h4`).

**8. Multiple H1s** — `bluedesk.html`, `flowsint.html`, `postloop.html`.

**9. `platform-command-center.html` is `noindex` *and* listed in the sitemap.** This is a contradictory signal and needs an owner decision, not a guess:
  - **If the page is meant to be public** (it has a title, description, `<h1>`, 56 KB of content, and is a registered member of the internal link graph) — remove the `noindex`. The evidence leans this way; the `noindex` arrived in an unrelated workflow-remediation PR.
  - **If it is meant to be internal** — remove it from `sitemap.xml` *and* from `PAGES` in `tools/internal_links.py`, which also drops the internal links pointing at it.

  Left as-is pending that call, because either fix changes what the site publishes. `noindex` wins regardless, so the page is not in the index today either way — the cost is a little wasted crawl budget.

### Continuous verification
```bash
python3 tools/seo_audit.py          # full audit; exit 1 on blocking errors
python3 tools/seo_audit.py --write  # refresh data/seo/audit.json
python3 tools/seo_audit.py --strict # also fail on warnings
```
The `SEO Dashboard` workflow runs this on every push touching HTML.

---

## 4. Structured data plan

### Shipped

| Page | Schema |
|---|---|
| `index.html` | `Organization`, `Person`, `ProfessionalService`, `WebSite` — now with full `sameAs`, `areaServed`, `serviceArea`, `hasOfferCatalog` |
| `web-design.html` | `Service` + `OfferCatalog`, `FAQPage` (6 Q&A), `BreadcrumbList` |
| `pricing.html` | `CollectionPage`, `OfferCatalog` (4 offers), `BreadcrumbList` |
| `government.html` | `Service` + `OfferCatalog`, `BreadcrumbList` |
| `smb.html` | `Service` + `OfferCatalog`, `BreadcrumbList` |
| 30 blog/legal pages | `Organization.url` added — 44 nodes made rich-result eligible |

All nodes use `@id` references pointing at `https://www.clearglassinc.com/#org`,
so the graph resolves to one entity rather than 40 disconnected copies. This is
the single most important structured-data decision for Knowledge Panel eligibility.

### Next
1. `Article`/`TechArticle` on all 26 blog posts with `author`, `datePublished`, `dateModified`.
2. `BreadcrumbList` site-wide — pairs with the existing "Continue exploring" blocks.
3. `FAQPage` on `conduit.html` and `store.html` (both already have visible FAQ copy).
4. `Review`/`AggregateRating` — **only** once real, verifiable reviews exist. Fabricated reviews are a manual-action risk and are explicitly out of scope.
5. `VideoObject` if demo videos are published.

### Validation
- Rich Results Test: https://search.google.com/test/rich-results
- Schema validator: https://validator.schema.org/
- Local: `python3 tools/seo_audit.py` checks JSON-LD parses and required properties.

---

## 5. Local SEO & map visibility plan

Local strategy for a **B2B consultancy in Burlington, Ontario** — not a retail storefront.

### The blocker
Map-pack visibility requires a **Google Business Profile**. Nothing on the
website substitutes for it. This is step one and everything else compounds from it.

**GBP setup:**
1. Claim "ClearGlass Inc." at business.google.com.
2. Choose the primary category deliberately — likely *Software Company*, *Computer Consultant*, or *Website Designer*. The primary category drives the majority of category-relevance ranking.
3. Because clients are visited rather than received, configure it as a **service-area business** (hides the street address, keeps map eligibility).
4. Set service areas: Burlington, Oakville, Hamilton, Milton, Mississauga, Toronto.
5. Complete every field — hours, services, description, photos. Completeness correlates with ranking.
6. Verify by postcard/phone.

### NAP consistency
One canonical format everywhere:
```
ClearGlass Inc.
Burlington, Ontario, Canada
+1-289-707-0269
```
The phone in schema (`+1-289-707-0269`) must match GBP and every citation **character for character**.

### Citations (build in this order)
Tier 1: Google Business Profile · Bing Places · Apple Business Connect · LinkedIn
Tier 2: Yelp Canada · Yellow Pages Canada · Canada411 · Clutch · GoodFirms
Tier 3: Burlington Chamber of Commerce · Halton Region business directory · Ontario tech directories · CanadianSME

### Reviews — the honest version
Reviews are the second-largest local ranking factor. The only sustainable method:
1. Ask every satisfied client directly, at project close.
2. Send a direct GBP review link.
3. Respond to all reviews, positive and negative.
4. Never incentivise, never gate by sentiment, never write them yourself. Fake reviews are the fastest route to a permanent profile suspension.

### Local content
Only build a city page where ClearGlass **genuinely serves that city** and can
say something specific about it. Four thin near-identical city pages are doorway
pages and will be filtered. One strong page beats four weak ones.

Defensible angles: Ontario PHIPA compliance (real regulatory specificity),
Ontario public-sector procurement, Burlington/Halton SMB cyber resilience.

---

## 6. Content & internal linking strategy

### Existing strength
The site already runs a real pillar-and-cluster system via `tools/internal_links.py`
— generated "Continue exploring" blocks with breadcrumbs, rotated sibling links,
cross-cluster bridges and per-cluster CTAs, on 128 pages. This is better internal
linking than most sites of this size. **Preserve it — never hand-edit generated
blocks; regenerate them.**

### Topic clusters

| Pillar | Cluster pages | Commercial target |
|---|---|---|
| **Governed AI** (`ai-operator.html`) | artemis-*, percival-os, conduit, agentmesh | AI automation consulting |
| **Cyber defense** (`cyber-defense-console.html`) | guardian, bluedesk, aegis, sentinel | Security consulting, fractional CISO |
| **OSINT** (`flowsint.html`) | Ontario-osint, automap, stegoforge | Investigative tooling |
| **Legal-tech** (`corporate-legal-advisor.html`) | banking-law-advisor, tax, procurement-legal-tech | Compliance advisory |
| **Web** (`web-design.html`) | pricing, offers/* | Web design retainers |

### Content gaps worth filling
1. **PHIPA compliance guide for Ontario clinics** — low competition, high intent, real regulatory specificity.
2. **Microsoft 365 security hardening checklist** — direct feed to `offers/hardening-sprint.html`.
3. **Case studies with real numbers** — currently the weakest area. E-E-A-T depends on demonstrable outcomes.
4. **Comparison pages** — "governed AI vs. ungoverned agents", "adaptive trust vs. zero trust". The existing blog already argues these well.
5. **Founder authority page** — a proper `/about` consolidating the `Person` schema already in the homepage graph. Currently there is no dedicated about page, which weakens E-E-A-T.

### Linking rules
- Every blog post links to ≥1 money page with descriptive anchor text.
- Never "click here" — anchors carry relevance.
- New page → add to `PAGES` + a cluster in `tools/internal_links.py`, run it, add the URL to `sitemap.xml`.
- Bump `VERSION` in `sw.js` when many pages change.

---

## 7. 30 / 60 / 90-day roadmap

### Days 1–30 — foundation
| Task | Owner |
|---|---|
| ✅ Technical fixes, schema, sitemap, tooling | Shipped |
| **Claim & complete Google Business Profile** | Owner |
| Verify Bing Webmaster Tools; submit sitemap to both | Owner |
| Wire GSC + Bing secrets so the dashboard goes live | Owner |
| Publish business hours, then add `openingHoursSpecification` | Owner |
| Resolve or remove the loader UA-branching redirect | Dev |
| Verify or remove the FedRAMP claim | Owner |
| Add visible NAP to the site footer | Dev |
| Rewrite the 15 worst titles + meta descriptions | Content |

**Exit criteria:** GBP live and verified · both search consoles reporting · dashboard connectors green · 0 audit errors.

### Days 31–60 — content & authority
| Task | Owner |
|---|---|
| Fix remaining titles/descriptions (audit-driven) | Content |
| `Article` schema on all 26 blog posts | Dev |
| Split the two 300 KB+ pages; extract shared CSS | Dev |
| Publish `/about` founder authority page | Content |
| Publish PHIPA compliance guide | Content |
| Publish 2 case studies with real outcomes | Owner |
| Tier 1 + Tier 2 citations | Owner |
| Request reviews from every past client | Owner |
| Resolve nexus duplicate-content canonical | Dev |

**Exit criteria:** health score ≥ 90 · all blog posts with Article schema · ≥5 genuine reviews · ≥10 citations.

### Days 61–90 — expansion & compounding
| Task | Owner |
|---|---|
| Service-area pages **only where genuinely served** | Content |
| Comparison + educational content, 2/month cadence | Content |
| Core Web Vitals pass on all money pages | Dev |
| Competitor benchmark populated with real rank data | Owner |
| Local partnerships / Chamber membership | Owner |
| First quarterly review against the dashboard | All |

**Exit criteria:** measurable impression growth on target clusters · map-pack presence for branded + category terms in Burlington · 20+ tracked keywords with impressions.

### What is realistic
No one can guarantee rankings. Honest expectations for a domain founded in 2024
in competitive B2B categories:
- **Weeks 1–4:** indexing and crawl improvements appear in GSC. Little ranking movement.
- **Weeks 4–12:** branded and long-tail terms ("clearglass inc", "phipa readiness checklist") move first.
- **Months 3–6:** local map visibility, if GBP is claimed and reviews accumulate.
- **Months 6–12+:** competitive head terms ("cybersecurity consulting ontario"). These need sustained content and genuine authority.

The compounding assets are the **content** and the **reviews**. The technical
work in this change removes the ceiling; it does not by itself raise the floor.

---

# Appendices

## A. Keyword map by page

Search-intent-mapped. `data/seo/config.json` tracks these live.

| Page | Primary keyword | Secondary | Intent |
|---|---|---|---|
| `index.html` | ai automation consulting canada | governed ai, cybersecurity consulting ontario | Commercial |
| `web-design.html` | website design burlington ontario | web development burlington, core web vitals consultant | Transactional |
| `pricing.html` | fixed fee cybersecurity engagement | security audit pricing ontario | Transactional |
| `government.html` | government ai security solutions | federal cybersecurity vendor canada | Commercial |
| `smb.html` | small business cyber security ontario | ai automation for small business | Commercial |
| `offers/security-quick-audit.html` | small business security audit ontario | cyber security assessment ontario | Transactional |
| `offers/hardening-sprint.html` | microsoft 365 hardening service | entra id security hardening | Transactional |
| `offers/phipa-readiness.html` | phipa readiness | phipa compliance ontario | Transactional |
| `flowsint.html` | osint investigation platform | osint graph tool | Commercial |
| `guardian.html` | ai agent security | autonomous agent governance | Informational→Commercial |
| `ai-operator.html` | governed ai automation | human in the loop ai approval | Commercial |
| `cyber-defense-console.html` | cyber defense console | security operations dashboard | Commercial |
| `blog/zero-trust-is-outdated-adaptive-trust.html` | adaptive trust systems | zero trust alternative | Informational |
| `blog/ai-agent-governance-*.html` | ai agent governance | agentic ai governance framework | Informational |
| `blog/osint-workflow-*.html` | osint workflow | osint methodology | Informational |
| `blog/cybersecurity-architecture-*.html` | agentic software security | ai agent security architecture | Informational |

**Brand-defence set:** `clearglass inc`, `clearglassinc`, `clearglass artemis`,
`clearglass percival`, `desmond otieno odhiambo`. These should rank #1 — if they
do not, entity consolidation (§4) is incomplete.

## B. Sample title tags & meta descriptions

Verified character counts.

| Page | Title (len) | Meta description (len) |
|---|---|---|
| `index.html` | `AI Automation & Cybersecurity Consulting \| ClearGlass Inc` (57) | `ClearGlass Inc. designs governed AI automation, zero-trust cybersecurity, and OSINT systems for high-trust organizations. Burlington, Ontario.` (142) |
| `web-design.html` | `Website Design & Development Burlington \| ClearGlass Inc` (56) | `Fast, secure, accessible websites engineered as growth infrastructure. Architecture, front-end build, Core Web Vitals and SEO. Burlington, Ontario.` (147) |
| `pricing.html` | `Fixed-Fee Security & Web Engagements \| ClearGlass Inc` (53) | `Fixed-fee cybersecurity and web engineering engagements — security quick audit, Microsoft 365 hardening, PHIPA readiness. Ontario, Canada.` (138) |
| `government.html` | `Government & Federal AI Security Solutions \| ClearGlass` (55) | `Zero-trust security architecture, intelligence platforms and governed AI command surfaces for Canadian and US government agencies.` (130) |
| `smb.html` | `AI Automation & Cyber Security for Small Business` (49) | `Enterprise-grade AI automation and plain-language cyber resilience, sized for small and medium businesses. ClearGlass Inc, Ontario.` (131) |
| `offers/phipa-readiness.html` | `PHIPA Readiness for Ontario Custodians \| ClearGlass` (51) | `A practical PHIPA readiness path for Ontario health-information custodians — gap assessment, safeguards, and documented compliance evidence.` (140) |
| `flowsint.html` | `Flowsint — OSINT Investigation Graph \| ClearGlass Inc` (53) | `Map domains, IPs and infrastructure relationships with a transform-driven OSINT investigation graph built for defensible, source-graded work.` (141) |

**Formulas.** Titles: `Primary Keyword — Qualifier | ClearGlass Inc` ≤60 chars,
keyword first, brand last. Descriptions: what it is → who it serves → where →
differentiator, 140–160 chars, no keyword stuffing. Descriptions do not rank —
they drive click-through, which does.

## C. Internal linking architecture

```
                          index.html  (root authority)
                               │
      ┌──────────┬─────────────┼─────────────┬──────────┐
      ▼          ▼             ▼             ▼          ▼
 ai-operator  cyber-defense  flowsint  corporate-legal  web-design
  (Gov AI)     (Security)    (OSINT)    (Legal-tech)      (Web)
      │            │            │            │             │
   clusters     clusters     clusters     clusters      clusters
   artemis-*    guardian     Ontario-     banking-law    pricing
   percival-os  bluedesk     osint        tax            offers/*
   conduit      aegis        automap      procurement-
   agentmesh    sentinel     stegoforge   legal-tech
      │            │            │            │             │
      └────────────┴─────┬──────┴────────────┴─────────────┘
                         ▼
              blog/*  (26 posts — supporting/informational)
                         │
                         ▼   every post → ≥1 money page
              offers/*, pricing.html  (conversion)
```

**Rules.** Money pages sit ≤2 clicks from the homepage. Blog posts link *up* to
their pillar and *across* to one money page. Cross-cluster bridges are curated in
`EXTRA_LINKS`, not automatic. All of this is generated — edit
`tools/internal_links.py`, never the blocks.

```bash
python3 tools/internal_links.py          # regenerate
python3 tools/internal_links.py --check  # CI freshness gate
```

## D. LocalBusiness schema template

Live on `index.html` (as `ProfessionalService`, the correct `LocalBusiness`
subtype for a consultancy). Template for reuse on contact/location pages:

```json
{
  "@context": "https://schema.org",
  "@type": "ProfessionalService",
  "@id": "https://www.clearglassinc.com/#service",
  "name": "ClearGlass Inc",
  "url": "https://www.clearglassinc.com",
  "logo": "https://www.clearglassinc.com/assets/images/clearglass-logo.png",
  "image": "https://www.clearglassinc.com/assets/images/clearglass-logo.png",
  "telephone": "+1-289-707-0269",
  "email": "desmondotieno@icloud.com",
  "priceRange": "$$$",
  "currenciesAccepted": "CAD",
  "address": {
    "@type": "PostalAddress",
    "addressLocality": "Burlington",
    "addressRegion": "ON",
    "addressCountry": "CA"
  },
  "serviceArea": {
    "@type": "GeoCircle",
    "geoMidpoint": { "@type": "GeoCoordinates", "latitude": 43.3255, "longitude": -79.7990 },
    "geoRadius": 100000
  },
  "areaServed": [
    { "@type": "AdministrativeArea", "name": "Burlington, Ontario" },
    { "@type": "AdministrativeArea", "name": "Halton Region, Ontario" },
    { "@type": "AdministrativeArea", "name": "Hamilton, Ontario" },
    { "@type": "AdministrativeArea", "name": "Greater Toronto Area, Ontario" },
    { "@type": "Country", "name": "Canada" }
  ],
  "sameAs": [
    "https://github.com/ClearGlassInc",
    "https://www.linkedin.com/company/clearglassinc",
    "https://x.com/clearglassinc",
    "https://www.facebook.com/clearglassinc",
    "https://www.instagram.com/clearglassinc"
  ],
  "parentOrganization": { "@id": "https://www.clearglassinc.com/#org" }
}
```

**Add once the facts exist — do not invent them:**
```json
"openingHoursSpecification": [{
  "@type": "OpeningHoursSpecification",
  "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
  "opens": "09:00", "closes": "17:00"
}],
"geo": { "@type": "GeoCoordinates", "latitude": 0.0, "longitude": 0.0 },
"hasMap": "https://maps.google.com/?cid=YOUR_GBP_CID",
"aggregateRating": {
  "@type": "AggregateRating", "ratingValue": "0.0", "reviewCount": "0"
}
```
`openingHoursSpecification` was deliberately omitted from the shipped schema
because no hours are published anywhere on the site. `aggregateRating` must only
appear once real reviews exist — marking up fabricated ratings is a manual-action risk.

## E. The measurement stack

| Component | Path | Purpose |
|---|---|---|
| Audit engine | `tools/seo_audit.py` | 15 check classes across indexability, on-page, schema, links, weight. stdlib only. |
| Dashboard feed | `tools/seo_dashboard.py` | GSC + Bing connectors, keyword tracking, competitor module, alerting. |
| Dashboard UI | `seo-dashboard.html` | `noindex` internal page reading the JSON feeds. |
| Config | `data/seo/config.json` | Target keywords, competitors, alert thresholds. |
| Feeds | `data/seo/{audit,performance,alerts}.json`, `history.jsonl` | Current state + append-only trend. |
| Automation | `.github/workflows/seo-dashboard.yml` | Audit on push; full refresh daily 06:40 UTC. |

**Design rule: the tooling never invents a number.** Each connector reports
`live` / `unconfigured` / `error`, and any metric without a source is emitted as
`null` so the dashboard shows "not connected" rather than a plausible-looking zero.

**Alerts:** traffic drop (>30% clicks / >35% impressions WoW), average position
slip (≥5 places), index-coverage gaps, structured-data errors, Bing 5xx and
robots-blocked URLs, connector failures. Critical alerts fail the workflow run.

**Competitor module honesty note:** neither Search Console nor Bing Webmaster
Tools expose a rival's data — a property only ever reports on itself. The module
scores ClearGlass from live data and carries rival rows only where an operator
supplies a measurement from a rank-tracking source. Unverified rows are flagged
and excluded from the gap calculation. It will show an empty state until real
competitor data is added, which is the correct behaviour.

### Credentials to configure
| Secret | Where to get it |
|---|---|
| `GSC_CLIENT_ID` / `GSC_CLIENT_SECRET` / `GSC_REFRESH_TOKEN` | Google Cloud OAuth client, scope `webmasters.readonly` |
| `GSC_PROPERTY` | e.g. `sc-domain:clearglassinc.com` |
| `BING_API_KEY` | Bing Webmaster Tools → Settings → API access |
| `BING_SITE_URL` | `https://www.clearglassinc.com/` |

---

## Safety statement

Every recommendation is within Google and Bing webmaster guidelines. This
strategy contains **no** keyword stuffing, hidden text, cloaking, doorway pages,
purchased links, fabricated reviews, or fake structured data. Two requested items
were deliberately **not** built — glazing service pages (services the business
does not offer) and fabricated business hours/ratings — because both would be
misrepresentation. No ranking outcome is guaranteed; the timelines in §7 are
expectations, not promises.
