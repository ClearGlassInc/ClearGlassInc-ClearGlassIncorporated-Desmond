# ClearGlass Inc — Full-Spectrum Search Visibility Strategy

**Property:** `https://www.clearglassinc.com` (GitHub Pages, served static via `.nojekyll`)
**Entity:** Desmond Otieno Odhiambo — Founder & Chairman, Software Architect
**Positioning:** Enterprise cybersecurity · AI automation · autonomous agents · OSINT · digital investigations · financial-crime analysis
**Prepared:** 2026-06-18

> This document is the source of truth for SEO/GEO work on this repo. It pairs with the technical fixes already committed on branch `claude/github-seo-strategy-npwm5l` (loader crawler-guard, consolidated JSON-LD with a `Person` entity, `ProfessionalService` schema, fixed `README.md` fence, corrected meta description).

---

## 1. Executive Summary

ClearGlass already has the hard parts most GitHub Pages sites skip: a sitemap (64 URLs), `robots.txt`, security headers (`_headers`), a PWA manifest, inline JSON-LD, and Bing/Google verification files. The site is **not under-built — it is under-disciplined**. The ranking ceiling today is set by four things:

1. **Crawlability risk (highest severity).** The homepage `<head>` ran *two* client-side `window.location.replace()` redirects to cinematic loader pages (`cg-loader.html`, `loader.html`) on cold visits. A search/AI crawler hitting `/` with no cookie/referrer would be bounced into an interstitial — risking the loader being indexed instead of the real page, and tanking LCP. **Fixed** in this branch by adding a crawler user-agent guard, but the loader pattern should be retired on indexable pages entirely (see §3/§4).
2. **Weak entity grounding for the person.** The brand is a personal-authority play ("Software Architect & COO"), but structured data described only an `Organization`/`LocalBusiness`. **Fixed** by adding a `Person` entity (Desmond) wired via `founder`/`worksFor`, plus `knowsAbout` topics and `sameAs`. This is the #1 lever for AI-search citation and Knowledge-Panel eligibility.
3. **Topical sprawl.** ~80 top-level HTML pages (Artemis IV/VI, Percival, Guardian, Sentinel, Conduit, Nexus, Avalon…) with overlapping names and no clear silo hierarchy. Crawl budget and link equity are diluted across near-duplicate product surfaces. The fastest gains come from **consolidating into silos** and making each page about exactly one topic.
4. **Backlink/authority vacuum.** A `github.io` subdomain inherits some of github.com's trust but builds none of its own. There is effectively no off-site citation graph yet. Authority work (LinkedIn, dev.to, GitHub org profile, digital PR) is the long-pole for competitive head terms.

**The fastest path to ranking gains, in order:** (1) kill crawler interstitials → (2) ship per-page titles/descriptions/canonicals + `Person`/`Service` schema → (3) collapse to clean silos with internal linking → (4) publish 3–5 authoritative cornerstone articles → (5) build the off-site citation graph.

---

## 2. Prioritized Action Plan (highest ranking impact first)

| # | Action | Impact | Effort | Status |
|---|--------|--------|--------|--------|
| P0 | Stop redirecting crawlers off the homepage/loader pages | 🔴 Critical | Done | ✅ committed (UA guard); **recommend full removal on indexable pages** |
| P0 | Add `Person` + `ProfessionalService` JSON-LD, link via `@id` graph | 🔴 Critical | Done | ✅ committed |
| P0 | Fix `README.md` unclosed code fence (everything below rendered as code) | 🟠 High | Done | ✅ committed |
| P0 | Complete truncated homepage meta description (`…`) | 🟠 High | Done | ✅ committed |
| P1 | Create the **GitHub org profile README** (separate `.github` repo) | 🔴 Critical | 1h | ⬜ see §3 (template provided) |
| P1 | Unique `<title>` + `<meta description>` + `<link canonical>` + OG/Twitter per page | 🔴 Critical | 1–2 days | ⬜ |
| P1 | Define silos + add breadcrumb nav + `BreadcrumbList` schema | 🟠 High | 1 day | ⬜ |
| P1 | Optimize `og:image` (currently a 2.8 MB iOS screenshot PNG; `.webp` already exists) | 🟠 High | 1h | ⬜ |
| P2 | Consolidate/redirect near-duplicate product pages; pick canonical per product | 🟠 High | 2 days | ⬜ |
| P2 | Cornerstone content hub (`/blog`, OSINT/security resource hub) | 🟠 High | ongoing | ⬜ |
| P2 | Submit sitemap to Google Search Console + Bing Webmaster Tools, request indexing | 🟠 High | 30 min | ⬜ |
| P3 | Backlink/digital-PR program (LinkedIn, dev.to, GitHub Discussions, citations) | 🟡 Medium-long | ongoing | ⬜ |
| P3 | FAQ schema + chunkable Q&A blocks for AI answer engines | 🟡 Medium | 1 day | ⬜ |

---

## 3. Current Visibility Audit (findings, grounded in the repo)

| Area | Finding | Fix |
|------|---------|-----|
| **GitHub Pages setup** | `.nojekyll` present, served from `main`; `_headers`/`_redirects`/`netlify.toml`/`render.yaml`/`fly.toml` all present — multi-host config is fine but `_headers`/`_redirects` are **Netlify/Cloudflare-only and ignored by GitHub Pages**. Don't rely on them for prod headers. | Treat GitHub Pages as the source of truth; replicate critical headers via `<meta>` where possible, or move to Cloudflare Pages if header control matters. |
| **Crawlability** | Two JS redirects to loaders fired on cold visits. | ✅ Guarded for bots; retire loaders on indexable routes. |
| **Profile SEO** | No GitHub **org** profile README exists (`.github/profile/README.md` lives in a repo literally named `.github`, not this repo). | Create it — template in this section. |
| **Repository naming** | Product names (Artemis, Percival, Guardian…) are brand-evocative but not keyword-bearing. | Keep brand names; add keyword-rich repo **descriptions** + topics. |
| **README structure** | Unclosed ```` ``` ```` fence + duplicated `# ClearGlassInc.` heading → body rendered as one code block. | ✅ Fixed. |
| **Metadata** | Homepage description truncated with `…`; many product pages likely share/lack unique titles. | ✅ Homepage fixed; audit all pages (§4 tooling). |
| **Internal linking** | `nav.js`/footer provide nav, but no breadcrumb trail or silo structure; orphan-risk for deep product pages. | Add breadcrumbs + hub→spoke links. |
| **External backlinks** | Effectively none beyond github.com. | §6 program. |
| **Page speed / CWV** | Homepage ships large inline CSS + Google Fonts + heavy hero imagery; loader redirect added a full extra navigation. og:image is 2.8 MB. | Self-host/`font-display:swap` (already `&display=swap` ✅), preload hero, serve `.webp`, drop loader. |
| **Mobile usability** | `viewport` meta present with `viewport-fit=cover` ✅. | Verify tap targets/CLS via Lighthouse mobile. |
| **Structured data** | Was Org + LocalBusiness only; `schema.json` was **orphaned** (standalone file crawlers never fetch) and **inconsistent** with inline JSON-LD. | ✅ Consolidated graph with `@id` refs; `schema.json` reconciled as the canonical template. |
| **Social previews** | OG/Twitter tags present ✅ but image is an unoptimized screenshot. | Ship a purpose-built 1200×630 OG card. |
| **AI readability** | Dense single-topic-per-page is weak; no FAQ blocks; content is design-heavy with little crawlable prose. | §7. |

### 3a. GitHub Org Profile README (create in a repo named `.github`)

> ⚠️ This file does **not** belong in `clearglassinc.github.io`. For an organization, the profile README must live at `ClearGlassInc/.github/profile/README.md`. Create that repo, then add:

```markdown
# ClearGlass Inc — Enterprise Cybersecurity, AI Automation & Autonomous Systems

> Clarity is power. We build zero-trust security platforms, autonomous AI agents, and
> investigative automation for organizations that cannot afford to guess.

**Founder & Chairman:** [Desmond Otieno Odhiambo](https://www.clearglassinc.com/#founder) —
software architect working across cybersecurity, AI engineering, OSINT, and financial-crime analysis.

### What we build
- 🛡️ **Cybersecurity platforms** — zero-trust fabric, threat detection, blue-team tooling
- 🤖 **AI automation & autonomous agents** — multi-agent orchestration, LLM workflows
- 🔍 **OSINT & digital investigations** — investigative automation, intelligence command surfaces
- 🏛️ **Software architecture** — secure, scalable, enterprise-grade systems
- 💳 **Financial-crime & fraud analysis** — risk intelligence pipelines

### Flagship systems
| System | Focus |
|--------|-------|
| [Artemis IV Core](https://www.clearglassinc.com/artemis-iv.html) | Self-evolving intelligence platform |
| [Guardian](https://www.clearglassinc.com/guardian.html) | Zero-trust security command center |
| [Sentinel](https://www.clearglassinc.com/sentinel.html) | Live geospatial intelligence |
| [Conduit](https://www.clearglassinc.com/conduit.html) | Enterprise workflow automation |

🌐 **Website:** https://www.clearglassinc.com
📩 **Work with us:** https://www.clearglassinc.com/offers/

<!-- Topics to set on key repos: cybersecurity, ai-automation, autonomous-agents,
     osint, software-architecture, zero-trust, threat-detection, llm, fraud-detection -->
```

---

## 4. Keyword & Topic Map

### Primary keywords (head — high intent, build pages around these)
- cybersecurity consulting
- AI automation services
- autonomous AI agents
- software architecture consulting
- OSINT tools / OSINT services
- enterprise workflow automation
- zero trust security platform

### Secondary keywords
- AI engineering consultant
- multi-agent orchestration platform
- threat detection software
- investigative automation
- financial crime / fraud analysis tools
- digital investigations services
- secure software architecture

### Long-tail (fast wins — low competition, high conversion)
- "autonomous agent framework for security operations"
- "OSINT automation for financial crime investigations"
- "zero trust architecture for small enterprises"
- "AI workflow automation for compliance teams"
- "how to build multi-agent OSINT pipelines"
- "software architect for cybersecurity startups Ontario / Canada"

### Entity-based keywords (for AI/Knowledge graph)
- Desmond Otieno Odhiambo · ClearGlass Inc · Artemis IV · Guardian · Percival · Sentinel
- Associate entities: zero trust, SPIFFE/mTLS, GNN anomaly detection, post-quantum crypto, LLM orchestration

### Intent clusters → content silos
| Intent | Cluster | Target page type |
|--------|---------|------------------|
| Commercial | "hire / consulting / services / pricing" | Services + pricing pages |
| Informational | "what is / how to / guide" | Blog + resource hub |
| Navigational | "ClearGlass / Artemis / Desmond" | Home, product, about |
| Investigational | "best OSINT tool / framework comparison" | Comparison + tool pages |

### Recommended silos
```
/                      ← brand hub (Person + Org entity home)
/about/                ← Desmond authority page (E-E-A-T)
/services/             ← commercial hub
  ├── /services/cybersecurity-consulting
  ├── /services/ai-automation
  ├── /services/osint-investigations
  └── /services/software-architecture
/platform/             ← product silo (Artemis, Guardian, Sentinel, Conduit, Percival)
/resources/            ← OSINT/security resource hub (informational, link magnet)
/blog/                 ← cornerstone articles feeding silos
/contact/
```

---

## 5. GitHub Optimization Plan

- **Profile README** → use §3a template (in the `.github` repo).
- **Pinned repositories** → pin the 6 that map to silos; rename-by-description, not by repo name.
- **Repo descriptions** (the searchable line): e.g. `Artemis — self-evolving autonomous AI security platform | zero-trust, multi-agent orchestration`.
- **Topics/tags** (set on each repo): `cybersecurity ai-automation autonomous-agents osint software-architecture zero-trust threat-detection llm fraud-detection`.
- **README headings** → one `# H1` per repo with the primary keyword; `## H2` sections matching search intent (Features, Architecture, Usage, Security).
- **Profile bio** → `Software Architect & Founder @ClearGlassInc · Cybersecurity · AI automation · OSINT · autonomous agents`.
- **Website link** → set to `https://www.clearglassinc.com` on profile + every flagship repo.
- **CONTRIBUTING/docs** → keep `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md` (all present ✅); add `docs/` index linking cornerstone content.
- **Commit/activity strategy** → consistent public commits build the contribution graph (a soft trust signal); ship the blog as markdown commits so each article is a public artifact.

---

## 6. Technical SEO Stack

| Job | Free / OSS | Premium / Enterprise | Automation-friendly (API) |
|-----|-----------|----------------------|---------------------------|
| Crawl & audit | Screaming Frog (free ≤500 URLs), Lighthouse CI | Sitebulb, Screaming Frog (paid), Ahrefs Site Audit | `lighthouse-ci`, Unlighthouse, Playwright |
| Log analysis | GoAccess | Splunk, Botify | GH Pages has no server logs → rely on GSC crawl stats |
| Backlinks | Google Search Console links report | Ahrefs, Semrush, Majestic | Ahrefs API, DataForSEO |
| Keyword research | Google Keyword Planner, Google Trends | Ahrefs, Semrush | DataForSEO, Keywords Everywhere API |
| Rank tracking | Manual SERP / GSC queries | SerpRobot, AccuRanker, Wincher | SerpApi, DataForSEO SERP API |
| Schema validation | [Schema.org validator](https://validator.schema.org), [Google Rich Results Test](https://search.google.com/test/rich-results) | — | `structured-data-testing-tool` (npm) in CI |
| Performance | Lighthouse, PageSpeed Insights, WebPageTest | Calibre, SpeedCurve | PSI API, `lighthouse-ci` GitHub Action |
| Broken links | `lychee`, `linkinator` | Ahrefs | **Add `lychee` as a GitHub Action** (see §below) |
| Indexation | GSC Coverage, `site:` operator | Ahrefs, IndexNow | GSC API, **IndexNow API** (Bing/Yandex/DuckDuckGo) |
| AI search | Manual prompting (ChatGPT/Perplexity/Claude), Otterly.ai | Profound, Peec AI, Otterly.ai | Otterly/Profound APIs |

**Recommended CI additions (drop into `.github/workflows/`):**
```yaml
# seo-checks.yml — runs on PRs touching HTML
name: SEO checks
on: { pull_request: { paths: ["**/*.html", "sitemap.xml", "schema.json"] } }
jobs:
  links:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Broken link check
        uses: lycheeverse/lychee-action@v2
        with: { args: "--no-progress './**/*.html'" }
  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: treosh/lighthouse-ci-action@v12
        with:
          urls: |
            https://www.clearglassinc.com/
            https://www.clearglassinc.com/offers/
          uploadArtifacts: true
```

**IndexNow (instant indexation for Bing, DuckDuckGo, Yandex, Brave):** generate a key, host `<key>.txt` at root, and ping on publish:
```bash
curl "https://api.indexnow.org/indexnow?url=https://www.clearglassinc.com/&key=YOUR_KEY"
```

---

## 7. Content Architecture (per-page targeting)

| Page | Primary keyword | Should rank for | Schema |
|------|-----------------|-----------------|--------|
| `/` (home) | ClearGlass Inc (brand) | branded + "enterprise cybersecurity AI platform" | Organization, Person, WebSite, ProfessionalService ✅ |
| `/about/` | Desmond Otieno Odhiambo | "software architect cybersecurity", author authority | `Person` + `ProfilePage` |
| `/services/` | cybersecurity consulting | service head terms | `Service` / `OfferCatalog` |
| `/services/ai-automation` | AI automation services | "AI workflow automation", "autonomous agents for ops" | `Service` |
| `/services/osint-investigations` | OSINT services | "OSINT automation", "digital investigations" | `Service` |
| Case studies | "[industry] cybersecurity case study" | proof / E-E-A-T | `Article` + `CreativeWork` |
| Project/product pages | product name + category | "[product] zero trust platform" | `SoftwareApplication` |
| `/blog/*` | long-tail informational | featured snippets, AI citations | `Article` + `FAQPage` |
| `/resources/` (OSINT/security hub) | "OSINT tools list", "security resources" | link magnet | `ItemList` / `Collection` |
| `/contact/` | "contact ClearGlass" | branded | `ContactPage` |

**Rule:** one page = one primary keyword = one search intent. Today's overlapping Artemis/Percival/Nexus pages violate this; pick one canonical page per product and 301/`rel=canonical` the rest.

---

## 8. Authority & Backlink Plan

1. **LinkedIn** — Desmond posts 2–3×/week on cybersecurity/AI/OSINT; link to cornerstone articles. Optimize the profile headline with the same entity keywords as the `Person` schema (factual consistency feeds AI knowledge graphs).
2. **dev.to / Hashnode / Medium** — republish cornerstone articles with `rel=canonical` back to `www.clearglassinc.com/blog/...` (canonical keeps ranking on your domain, gains the referral link).
3. **GitHub** — Discussions on flagship repos; answer issues in adjacent OSS (OSINT/security tooling) with a profile link; get listed in `awesome-osint` / `awesome-security` lists.
4. **Substack newsletter** — "ClearGlass Intelligence Brief"; each issue links 2–3 site pages.
5. **Communities** — r/netsec, r/OSINT, OSINT Curious, MITRE/ATT&CK adjacent forums; contribute, don't spam.
6. **Citations & directories** — Clutch/GoodFirms (consulting), Crunchbase (entity), relevant Canadian/Ontario business listings (NAP consistency with the `LocalBusiness` address).
7. **Digital PR** — publish an original OSINT/fraud research report → pitch to security press for links.
8. **Partnerships / guest content** — co-author with complementary vendors; guest posts on established security blogs.

**Quality bar:** 5 relevant, topically-aligned links > 100 generic ones. Track via GSC links report monthly.

---

## 9. AI Search Optimization (GEO)

- **Semantic clarity** — lead each page with a 2–3 sentence plain-language summary of *what it is and who it's for*. AI engines extract these.
- **Entity association** — `Person`/`Organization`/`Service` graph with `@id` cross-refs is shipped ✅; keep `sameAs` (LinkedIn, GitHub, Crunchbase) consistent everywhere.
- **Factual consistency** — name, title, credentials, address, phone must match byte-for-byte across site, schema, LinkedIn, and directories.
- **Citation density** — cite primary sources (NIST, MITRE ATT&CK, FATF for financial crime); AI engines prefer pages that themselves cite authorities.
- **Structured formatting** — short paragraphs, descriptive `H2/H3`, tables, definition lists. (This document's format is the target shape.)
- **Chunkable content** — self-contained sections under clear headings, each answerable standalone.
- **FAQ optimization** — add `FAQPage` schema; example below.
- **Machine-readable signals** — clean semantic HTML, `lang`, canonical, sitemap `lastmod`, and an `llms.txt` at root.

**FAQ block (paste into services/product pages):**
```html
<section itemscope itemtype="https://schema.org/FAQPage">
  <h2>Frequently asked questions</h2>
  <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">What does ClearGlass Inc do?</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
      <p itemprop="text">ClearGlass Inc builds enterprise cybersecurity platforms, AI
      automation, autonomous agents, and OSINT/investigative tooling, founded by
      software architect Desmond Otieno Odhiambo.</p>
    </div>
  </div>
</section>
```

**`/llms.txt` (create at repo root):**
```
# ClearGlass Inc
> Enterprise cybersecurity, AI automation, autonomous agents, OSINT, and software architecture.
> Founded by Desmond Otieno Odhiambo (Software Architect, Founder & Chairman).

## Core pages
- Home: https://www.clearglassinc.com/
- Services & pricing: https://www.clearglassinc.com/offers/
- Artemis IV (autonomous security platform): https://www.clearglassinc.com/artemis-iv.html
- Guardian (zero-trust command center): https://www.clearglassinc.com/guardian.html

## Contact
- Email: Desmondotieno@icloud.com
```

---

## 10. 30-Day Execution Plan

**Week 1 — Technical foundation (highest ranking impact)**
- ✅ Crawler-safe loader, consolidated `Person`/`Service` JSON-LD, README, meta description (done this branch).
- Create `ClearGlassInc/.github` repo + profile README (§3a). *(1h, high)*
- Verify GSC + Bing Webmaster Tools, submit `sitemap.xml`, request indexing of `/`. *(30 min)*
- Validate every page in Rich Results Test; fix errors. *(2h)*
- Optimize `og:image` to a 1200×630 `.webp` card. *(1h)*
- KPI baseline: record current impressions/clicks/avg-position from GSC.

**Week 2 — On-page & silos**
- Add unique `<title>`/`<meta description>`/canonical to top 15 pages. *(1–2 days, critical)*
- Build `/about/` authority page with `Person`+`ProfilePage` schema. *(half day)*
- Add breadcrumbs + `BreadcrumbList` schema. *(half day)*
- Pick canonical product pages; `rel=canonical` the duplicates. *(1 day)*
- Add `seo-checks.yml` (lychee + Lighthouse CI). *(1h)*

**Week 3 — Content & GEO**
- Publish 2 cornerstone articles (e.g., "Building autonomous OSINT pipelines", "Zero-trust for small enterprises"). *(2–3 days, high)*
- Add FAQ blocks + `FAQPage` schema to services + 2 product pages. *(half day)*
- Create `/llms.txt` and `/resources/` hub stub. *(half day)*

**Week 4 — Authority & measurement**
- Republish cornerstones to LinkedIn + dev.to with canonical back. *(half day)*
- Submit to 3 directories (Crunchbase, Clutch, one OSINT awesome-list PR). *(half day)*
- Set up the KPI dashboard (§11) and a weekly GSC export. *(2h)*
- Re-run Lighthouse; compare to Week-1 baseline.

---

## 11. KPI Dashboard

| Metric | Definition | Source | Target (90 days) |
|--------|------------|--------|------------------|
| Impressions | Times any URL appears in SERPs | GSC Performance | +200% vs Week-1 baseline |
| Clicks | Organic clicks to the site | GSC Performance | +150% |
| Avg. position | Mean position for tracked queries | GSC / rank tracker | Top 20 → top 10 for 5 long-tails |
| CTR | Clicks ÷ impressions | GSC | ≥ 3% sitewide |
| Index coverage | Valid indexed URLs ÷ submitted | GSC Coverage + `site:` | ≥ 90% of sitemap |
| Backlinks / ref. domains | Unique linking domains | GSC links / Ahrefs | +10 quality referring domains |
| Branded search | Impressions for "ClearGlass"/"Desmond Otieno Odhiambo" | GSC (query filter) | +100% |
| GitHub traffic | Repo + Pages views/clones | GitHub Insights → Traffic | trending up |
| Engagement | Avg. engagement time, pages/session | GA4 / Plausible | engagement time ≥ 45s |
| Core Web Vitals | LCP < 2.5s, INP < 200ms, CLS < 0.1 | PSI / CrUX | all "Good" |
| AI citation frequency | # of ChatGPT/Perplexity/Claude answers citing the domain for tracked prompts | Manual log / Otterly/Profound | ≥ 5 tracked prompts cite us |
| Rich result eligibility | Pages passing Rich Results Test | GSC Enhancements | Org/Person/FAQ valid, 0 errors |

**Measurement cadence:** GSC weekly export → tracking sheet; Lighthouse CI on every HTML PR; AI-citation prompt set run monthly against a fixed list of 10 queries.

---

## Appendix — What was changed in this branch

- `index.html`: crawler user-agent guard added to **both** loader redirects; consolidated two JSON-LD blocks into one `@graph` adding `Person` (Desmond), `ProfessionalService`, `ContactPoint`, and `@id` cross-references; completed truncated meta description.
- `schema.json`: reconciled to match the inline graph (was orphaned + inconsistent) so it can serve as the canonical schema template.
- `README.md`: closed the unterminated code fence and de-duplicated the heading so the repo page renders correctly.
- This document: `docs/SEO_STRATEGY.md`.
</content>
