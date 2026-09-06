# ClearGlass Advanced SEO Growth System

## Purpose

The growth engine applies one measurable SEO operating model across every indexable page. It does not promise rankings or manipulate search engines. It identifies technical and editorial defects, prioritizes evidence-based corrections, and prevents regressions in pull requests.

## Sitewide controls

1. **Search intent** — Each page receives a primary intent classification: informational, commercial, or navigational. Titles, H1s, descriptions, schema, and calls to action should reinforce that single purpose.
2. **Crawlability and indexation** — Existing sitemap, robots, canonical, orphan-page, broken-link, and indexability checks remain authoritative.
3. **Machine understanding** — The engine checks heading hierarchy and intent-appropriate Article, FAQ, Product, Service, Organization, and breadcrumb structured data.
4. **Core Web Vitals proxies** — It flags legacy image formats, unreserved image dimensions, blocking JavaScript, and excessive page weight for engineering review.
5. **Content clusters** — Pages are grouped into Artemis, cybersecurity, AI, government, procurement, SMB, trust/legal, services, blog, and corporate clusters. Mature clusters require a clear pillar with descriptive bidirectional links.
6. **Content quality** — Thin pages are flagged for original examples, evidence, comparisons, screenshots, FAQs, or removal/noindex when they have no strategic value.
7. **Internal authority flow** — Orphans, weak anchors, and pages with too few contextual links are surfaced. Important conversion pages should receive links from relevant high-authority informational pages.
8. **Trust** — Privacy, terms, accessibility, visible authorship, and maintenance dates are verified where relevant.
9. **Measurement** — The existing SEO dashboard integrates Search Console and Bing data. The growth backlog complements it with repository-level findings.
10. **Monthly cycle** — GitHub Actions runs the full growth audit on the first day of every month and on every SEO-relevant pull request.

## Commands

```bash
python3 tools/seo_audit.py
python3 tools/advanced_seo_growth.py
python3 tools/advanced_seo_growth.py --write
```

The `--write` command creates:

- `data/seo/advanced-growth.json` — complete machine-readable inventory and findings.
- `data/seo/advanced-growth.md` — prioritized editorial and engineering backlog.

## Operating rule

Errors are release blockers because they indicate missing canonicals, invalid schema, malformed heading structure, missing trust pages, or orphaned indexable pages. Warnings form the ranked growth backlog. Informational findings are optimization opportunities and should be addressed according to traffic, commercial value, and Search Console evidence.

Review high-impression, low-CTR pages first. Then improve URLs ranking in positions 8–20 before creating additional pages in the same cluster.
