# ClearGlassInc Artemis — Burlington Exposure Baseline

> **Evidence status (2026-07-30): baseline collection ready; live accounts not connected.** Zero is not substituted for unavailable data. No ranking, competitor, review, traffic, Palantir provisioning, or service-area claim in this brief is represented as verified.

## Objective and 90-day targets

| Outcome | Baseline | Day-90 target | Source / cadence |
|---|---|---|---|
| Top-three geo-grid cells for three approved non-brand terms | pending first scan | +30% relative green cells | approved local rank tracker, monthly, identical grid |
| Burlington/Halton organic sessions | pending GA4 validation | +40% versus prior comparable 90 days | GA4 aggregate, weekly |
| Qualified local inbound leads | pending CRM audit | 10/month with locality evidence | CRM, weekly |
| GBP discovery and actions | pending GBP export | +25% actions without policy incidents | GBP performance, weekly |
| Local earned mentions | pending citation audit | 2 legitimate mentions/month | verified URLs, monthly |

Targets are hypotheses, not guarantees. Use a 90-day pre-period adjusted for seasonality and consent changes. A “green” cell means rank 1–3 in a fixed 7×7 or 9×9 Burlington grid with unchanged centre, spacing, device/language, keywords, and scan vendor.

## Recon contract

1. Export **aggregate** GBP searches, views, calls, website clicks, direction requests, and date ranges. Record profile ID and timezone separately in a secret store.
2. Export GA4 Burlington, Oakville, Hamilton, Milton, and Dundas sessions/conversions by landing page and source. Apply privacy thresholds; do not retain IP addresses.
3. Export Search Console query/page/country/device aggregates. Join only at aggregate grain.
4. Export Instagram, TikTok, and LinkedIn post metrics, follower-region aggregates, posting time, format, and link tags.
5. Export CRM qualified outcome and locality evidence with pseudonymous IDs. Do not place contact data in prompts or reports.
6. Run each core term on a fixed grid: `software architect Burlington`, `cybersecurity consultant Burlington`, `AI automation Burlington`, and brand-control `ClearGlass Burlington`.

Store each import with source, extraction time, coverage period, timezone, schema version, row count, consent/purpose, and checksum. Reject malformed, duplicate, over-granular, or lineage-free data.

## Competitor scan (evidence template)

Do not preselect competitors from memory. For each non-brand keyword, record the five businesses appearing most often across the fixed grid, then verify they offer the relevant service. Never scrape contrary to terms.

| Field | Required evidence |
|---|---|
| Identity | exact business/profile name and first-party URL |
| GBP | primary/secondary categories, completeness, hours, post/photo cadence, review count/date distribution; no reviewer PII |
| Site | relevant landing URL, unique local value, LocalBusiness/Service schema, CWV field data, indexability |
| Content/social | public cadence and formats over a declared window; engagement reported, not inferred |
| Citations | legitimate directory/local publication URLs and NAP consistency |
| Grid | keyword, cell coordinates, observed rank, scan timestamp/vendor |

Score evidence completeness separately from marketing strength. Manual verification is required for identity collisions and service relevance.

## Local opportunity map

### Priority geography

- **Primary:** Burlington citywide; validate service coverage before naming Aldershot, Brant Hills, Central/Downtown, Headon Forest, Mountainside, Orchard, Roseland, and Tyandaga.
- **Secondary:** Oakville, Hamilton, Milton, and Dundas only after operational coverage and unique local usefulness are documented.
- Pages are not created merely because a place appears here. Each page needs verified service availability, distinct evidence, and user value; otherwise use one truthful service-area page.

### Community anchors (research leads, not endorsements or partnerships)

Downtown Brant Street, Burlington waterfront, Royal Botanical Gardens, Joseph Brant Museum, Burlington Public Library, local BIAs, chambers/economic-development organizations, coworking and technology meetups, and major public festivals are candidate research topics. Confirm names, dates, rights, relevance, and outreach eligibility from first-party sources before use. Do not imply affiliation.

### Publication and citation discovery

Research official municipal/community calendars, local chambers/BIAs, legitimate Canadian directories, local journalism, association member pages, university/college event listings, and partner websites. Accept a placement only when editorially relevant and truthful; reject paid link schemes, bulk directories, reciprocal-link farms, fake events, and manufactured citations.

## Baseline acceptance gate

Baseline is complete only when account owners authorize read-only access, metric definitions reconcile, geography and timezone are fixed, grid scans are reproducible, competitor evidence has URLs/timestamps, consent and retention are approved, and the signed dataset checksum is logged. Until then, automation remains `analysis_and_draft_only`.
