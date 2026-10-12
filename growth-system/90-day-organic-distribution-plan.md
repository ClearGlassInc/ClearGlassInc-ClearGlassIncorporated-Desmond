# ClearGlass Inc. — 90-Day Organic Visibility & Distribution Plan

**Prepared:** 2026-10-12  
**Status:** Working plan / owner review required before external execution  
**Mission:** Turn ClearGlass's existing SEO, technical education, and blog assets into a consistent discovery → trust → qualified-inquiry system without breaking production or making unsupported growth claims.

## Executive decision

ClearGlass already has substantial owned-site foundations: a canonical homepage, robots directives, four sitemap references, a 174-URL primary sitemap, RSS/Atom feeds, `llms.txt`, search-engine verification files, structured data, an Insights hub, and existing topic clusters. The primary opportunity is disciplined distribution and measurement—not bulk-generating dozens of near-duplicate pages.

Use one evidence-reviewed flagship article at a time, distribute it in platform-appropriate formats, link back to the appropriate canonical resource, and record only verifiable aggregate outcomes. Every public communication remains a draft until the owner approves the exact asset and its release details.

## Current baseline (observed in repository, not analytics)

- Canonical public site: [clearglassinc.com](https://www.clearglassinc.com/)
- Existing editorial hub and RSS: [Insights](https://www.clearglassinc.com/blog/)
- Existing search authority hub: [SEO authority hub](https://www.clearglassinc.com/seo-authority-hub.html)
- Existing AI governance article: [Governed autonomy playbook](https://www.clearglassinc.com/blog/ai-agent-governance-governed-autonomy.html)
- Primary sitemap currently contains 174 unique URLs; robots.txt points to four sitemaps.
- `llms.txt`, `llms-full.txt`, an Atom feed, and a blog feed are present.
- The repository’s documented organic engine calls for daily short-form content, three LinkedIn assets per week, one weekly deep insight, and a monthly review.
- The original aspiration of two articles, five LinkedIn posts, three shorts, and one newsletter every week should be treated as a **target state**, not a reason to trade away technical accuracy or human review.

**Not yet verified by this repository audit:** Google Search Console and Bing Webmaster Tools account access, actual property verification in those accounts, sitemap-submission status, current indexing errors, query-level impressions/clicks, visitor analytics, opt-in subscriber-list availability, and attributable revenue. A verification file in a repository is not, by itself, evidence that an account is connected or a sitemap has been accepted.

## Guardrails — apply for all 90 days

1. **Preserve production.** Do not switch GitHub Pages deployment mode, deploy through Vercel, change DNS, rewire the domain, or enable new infrastructure as part of this plan.
2. **Approval before external action.** Posts, replies, videos, newsletters, guest pitches, podcast requests, advertising, and outreach require explicit approval for the exact channel/account, creative, destination, audience, and timing. This plan does not post or schedule anything.
3. **Truth before virality.** No invented metrics, customer names, case studies, assessment counts, certifications, compliance claims, or guaranteed rankings. Separate documented facts from hypotheses and recommendations.
4. **Privacy by default.** Do not turn on tracking pixels, remarketing, analytics, or lead-capture features as part of this plan. They are currently deliberately disabled in the growth-system feature flags. No personal information or prospect dossiers are committed to Git.
5. **No spend without authorization.** Paid placement and sponsored content are excluded unless the owner separately approves channel, budget ceiling, creative, targeting, landing page, measurement, and shutdown conditions.
6. **One source of truth.** Reuse existing URLs and topic clusters. Avoid creating another page if an established canonical page can be improved or distributed.

## Days 1–7 — Establish the baseline and ship one distribution pack

### 1. Search console verification (owner-operated)

- Confirm the `https://www.clearglassinc.com/` property in Google Search Console and the corresponding site in Bing Webmaster Tools.
- Verify that each console account can be accessed by an authorized owner. Do not share passwords or tokens in tickets or chat.
- Inspect the submitted sitemap list and record accepted/failed status, last-read date, indexed canonical URLs, crawl/indexing warnings, and the top queries/pages if data is available.
- Record a dated baseline: 28-day impressions, clicks, CTR, average position (where offered), organic landing-page clicks, brand vs non-brand queries, and top 20 pages.
- If console access is absent, document it as **not verified** and request owner setup; do not infer status from public files.

### 2. Use the existing content

- Take the AI Agent Governance article and generate a platform-specific pack (LinkedIn long-form, short posts, carousel, X/Threads thread, video outline and clips, opt-in newsletter draft).
- Keep claims grounded in the article and primary references. Keep Reddit/community responses individually relevant and disclose ClearGlass affiliation when sharing company content.
- Link to the single canonical article and the existing authority hub where appropriate. Use descriptive anchors in useful contextual links; do not stuff keywords.
- Review current homepage description and other public snippets against the live offer details. The homepage description should not advertise stale pricing when its checkout states a different current price. Keep pricing changes outside this metadata task.

### 3. Baseline the distribution process

Set up an owner-controlled log that captures publication approval, actual URL, publish timestamp, and weekly aggregate metrics. Do not record private profile details or individual user activity.

**Exit criteria:** baseline sheet completed or its gaps explicitly listed; first distribution pack reviewed; no content has been externally published without its own approval.

## Days 8–30 — Consistent distribution, one pillar at a time

### Editorial focus

Prioritize three connected topic clusters:

1. **AI agent governance:** agent ownership, least privilege, action risk tiers, review gates, traceability, revocation.
2. **Cybersecurity for Ontario organizations:** practical risk assessment, identity/access hygiene, incident readiness, secure automation.
3. **Evidence-aware OSINT and information integrity:** lawful collection, provenance, source evaluation, uncertainty, and chain of custody.

Choose one primary intent per page and keep each article anchored to an existing pillar/service page.

### Weekly production targets

**Weeks 2–3 ramp:** one carefully reviewed deep article or substantive update and one repurposing pack per week, plus up to three LinkedIn posts and two short-form clips derived from that content. Community replies are opportunistic, not quota-driven. Send no newsletter unless a consented list and unsubscribe process are verified.

**Weeks 4 onward target (subject to capacity):**
- Up to 2 substantive articles/posts for the website per week (only if research, source validation, distinct search intent, and editorial review pass).
- 5 LinkedIn posts/week, including repurposed formats rather than 5 independent research projects.
- 3 short video clips/week cut from reviewed explainers.
- 1 newsletter/week, only to a verified opt-in list with compliant unsubscribe handling.
- Relevant community participation on an as-needed basis, never copy-paste spam.

If review capacity falls behind, reduce publication volume rather than skipping evidence or approvals.

### Technical SEO maintenance (incremental only)

For new/updated indexable content, check title and meta-description length against `seo-targets.json`, canonical URL, robots/indexability, semantic headings, structured data validity, descriptive internal links, accessibility, mobile readability, sources and publication/update dates. Add sitemap entries only when an actual new canonical page ships; regenerate site-index/internal-link artifacts with the existing repository tools where required. Do not manually edit generated blocks.

**Exit criteria:** at least three approved/distributed packs, baseline captured, console/indexing blockers logged, no duplicate pages created purely to hit targets.

## Days 31–60 — Strengthen clusters and earned authority

- Review the first month’s impressions, clicks, engagement, saves/shares, outbound clicks, qualified inquiries, and booked discussions. Separate attention from business outcomes.
- Improve the 10–20 pages with the clearest search intent or measurable demand signal, beginning with titles/snippets, internal paths, factual clarity, and page usefulness.
- Add useful internal links from relevant articles to their topic pillar and one appropriate service page; keep anchors natural.
- Refresh older articles only when a source, recommendation, claim, date, or search intent has materially changed. Preserve canonical URLs unless a reviewed migration is necessary.
- Identify up to five genuinely relevant podcasts, trade associations, professional newsletters, or community events based on topic fit. Draft personalized pitches, record the public source and reason for relevance, and seek owner approval before any outreach.
- Invite substantive discussion and answer questions on platforms where ClearGlass can add original information. Follow each community’s policy and disclose affiliation where relevant.
- Evaluate YouTube search-friendly explainers using specific question-led titles, clear chapters, reviewed captions, and links to source material. Do not reuse other creators’ media without rights.

**Exit criteria:** two monthly measurement reviews are complete or access gaps are recorded; priority-page changes are evidence-led; any guest/podcast outreach is separately approved.

## Days 61–90 — Optimize based on outcomes

- Compare results against the Day 1 baseline using equivalent periods. Annotate seasonality, query mix, incomplete instrumentation, and small sample sizes.
- Identify pages/format pairs that earn meaningful search visibility or engagement and produce a focused second iteration.
- Update factual or outdated content with sources and dates. Merge/retire content only after a deliberate canonical/redirect review; do not delete pages based on a brief performance dip.
- Audit the internal-link graph and sitemap after any actual page additions; verify no broken URLs or unexpected canonical changes.
- Compare qualified inquiries, booked calls, proposals, wins, and verified revenue against attention metrics. Report unknowns as unknowns.
- Prepare the next 90-day editorial roadmap from the measured questions and gaps—not from a fixed quota of 100 articles, 100 posts, or 50 videos.

**Exit criteria:** dated 90-day report, evidence-backed top opportunities, list of technical/indexing issues with owners, and next-quarter plan approved.

## Weekly operating rhythm

**Monday:** review source freshness, topic selection, available search-console data, and prior results.  
**Tuesday:** draft the core article or substantive update with source links.  
**Wednesday:** editorial/factual review and platform repurposing.  
**Thursday:** accessibility, link, canonical, and destination checks; submit exact assets for approval.  
**Friday:** publish only approved items; record actual URL and aggregate platform-native metrics after posting.  
**Month-end:** review outcomes, risks, effort, and what to stop/start/continue.

These are proposed work blocks; they are not scheduled calendar events.

## KPI definitions

| Metric | Definition | Evidence source | Reporting rule |
|---|---|---|---|
| Search visibility | Impressions for selected relevant queries/pages | Search Console / Bing tools | Record date range; do not call impressions visits |
| Organic clicks | Clicks from search results | Search Console / Bing tools | Separate brand and non-brand where data allows |
| Snippet engagement | CTR by query/page | Search consoles | Interpret with position and query mix |
| Content engagement | Views, saves, shares, meaningful replies | Native platform analytics | Aggregate counts only |
| Owned-asset visits | Referrals to the canonical page | Approved first-party aggregate measurement if enabled later; otherwise platform outbound-click counts | No new tracking in this plan |
| Qualified inquiry | Inquiry that meets the owner-approved service fit criteria | Existing authorized CRM/records | Do not count likes as leads |
| Pipeline progression | Consultations, proposals, customers | Verifiable CRM/contract records | Record actual status only |
| Revenue | Completed and reconciled receipts | Authenticated billing/accounting records | No forecast reported as earned revenue |
| Quality | Assets passing evidence, accessibility, and approval checklists | Editorial release log | Track rework and blocked items |

## Decisions required from the owner before expanding execution

- Confirm authorized access to Google Search Console and Bing Webmaster Tools and export the initial baseline.
- Approve the exact first distribution pack and chosen channel/account/timing.
- Verify whether a valid opt-in newsletter list currently exists; otherwise keep newsletter assets as drafts.
- Separately authorize any new analytics, lead capture, mailing integration, podcast/association outreach, paid spend, or external publishing.
- Review current pricing and checkout offer details through the existing pricing owner; the SEO metadata correction does not change pricing itself.

## Definition of done

The program is working when ClearGlass can show a repeatable chain:

**Reviewed source → useful core asset → platform-specific draft → human approval → actual publication record → aggregate evidence → next decision.**

A ranking, viral reach, new customer, or revenue outcome is never guaranteed. The system’s job is to make useful expertise easier to discover and to prove what happened accurately.
