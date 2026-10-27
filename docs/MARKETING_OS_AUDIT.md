# ClearGlass Marketing OS — Infrastructure Audit & Build Plan

**Audit date:** 2026-10-27
**Auditor scope:** this repository only, read at commit `14a9e0b`.
**Evidence rule:** every "Existing Asset" cell names a file or command output in
this repo. Nothing here claims a customer, a ranking, a visitor count, a
testimonial, a partnership or a revenue figure, because this repository
contains evidence for none of those. Where a number would normally go and no
evidence exists, the cell reads `NO DATA`.

| Legend | Meaning |
|---|---|
| **VERIFIED** | Read directly from a file in this repo on 2026-10-27 |
| **NO DATA** | The repo holds no evidence either way — not zero, *unmeasured* |
| **BLOCKED** | Exists in code but cannot run for a stated reason |

---

## The five blockers, ranked

Read this before the table. Four of the thirteen layers below are gated by
these, and three of the five are **not fixed by writing code**.

1. **Site analytics is switched off.** `analytics.js:37` is `provider: ""`, and
   `analytics.js:43` is `if (!provider) return;`. No page reports a visit.
   Every KPI in a marketing plan — traffic, conversion rate, funnel
   drop-off, campaign attribution — is therefore **unmeasurable today**, not
   poor. *Fix: one config line. Owner, ~10 minutes.*

2. **GitHub Actions dispatches no runners.** Verified in `CLAUDE.md` and
   `docs/audit/2026-10-27-recovery.md`: job `122121602803` reports
   `runner_id: 0` with the annotation *"The job was not started because your
   account is locked due to a billing issue."* **38 scheduled workflows are
   dead.** Any autonomous marketing loop built on `schedule:` triggers will
   silently publish nothing. *Fix: org billing settings. Not a code change.*

3. **The site's only lead form is inert.** `revenue-command.html:19` is
   `<meta name="cg-revenue-api" content="">`, and line 112 is
   `if(!API_BASE)return;`. The submit handler exits before the fetch. The
   control plane's `POST /revenue/leads` endpoint exists and is tested, but
   nothing is deployed for the page to call. *Fix: deploy control plane, set
   the meta. See `DEPLOY.md`.*

4. **Content cadence has collapsed.** `datePublished` across `blog/*.html`,
   51 dated briefs: **Jun 2; Jul 32; Aug 7; Sep 9; Oct 1** — the last dated
   2026-10-06, **21 days ago**. July was a one-month burst of 32 briefs that
   was never going to be sustainable, and output has fallen every month since.
   The problem is not that the engine stopped; it is that it was run at a rate
   nobody could hold, and no sustainable floor was ever set.

5. **Zero of five campaigns are approvable.** `data/campaigns/burlington-campaign-packages.json`
   is `status: draft_requires_human_approval`. All five entries have
   `spend_ceiling_cad: null` and no `state`. Three of five
   (`ransomware-readiness-burlington-smes`, `nonprofit-cyber-resilience`,
   `ai-governance-ontario`) have `landing_page: null`. Per `CLAUDE.md`, a
   campaign needs a sellable SKU **and** a landing page loading
   `cg-attribution.js` **and** an owner-set spend ceiling before `approved`.

---

## PHASE 1 — Infrastructure audit

| # | Layer | Existing Asset (verified) | Status | Gap | Upgrade Required | Priority | Owner | Metric |
|---|---|---|---|---|---|---|---|---|
| 1 | Brand identity & messaging | `llms.txt` (43 lines), `llms-full.txt` (220 lines) — positioning, founder, Burlington ON base | VERIFIED · strong | Positioning is stated for machines, not compressed into one human-facing promise | Single positioning line reused across every offer page `<h1>` and LinkedIn bio | QUICK WIN | Desmond | Message consistency across 9 offer pages |
| 2 | Website architecture & conversion | 119 root `*.html`, 176 `sitemap.xml` URLs, 7 offer pages (+ `index`/`thank-you`) | VERIFIED | Only `revenue-command.html` has a lead form, and it is inert (Blocker 3). Live paths are Stripe link / Calendly / `mailto:` | Deploy control plane; set `cg-revenue-api`; add one form to the top 3 offer pages | BUILD | Desmond | Form submits per week |
| 3 | SEO / GEO / AEO | 176 sitemap URLs; **77 pages** carry `application/ld+json`; `llms.txt` + `llms-full.txt` + `robots.txt` present | VERIFIED · above average for AEO | **Only 2 pages carry `FAQPage` schema.** Answer engines preferentially cite Q&A-structured markup | Add `FAQPage` to the 7 offer pages + top 10 briefs | QUICK WIN | Desmond | Pages with FAQPage: 2 → 17 |
| 4 | Content engine | 53 `blog/*.html` (51 dated briefs); `tools/insights_index.py` with `CURATED` editorial control | VERIFIED · real asset | Declining every month since a 32-brief July burst: Aug 7, Sep 9, **Oct 1** (Blocker 4) | Sustainable weekly floor, not another burst; 4-brief buffer before resuming | QUICK WIN | Desmond | Briefs per month ≥ 4, held 3 months |
| 5 | Lead capture & CRM | `control-plane` `POST /revenue/leads`, opaque `reference` return, lead stage in audit ledger | VERIFIED code, BLOCKED runtime | Not deployed; no CRM of any kind in repo | Deploy per `DEPLOY.md` (Render blueprint); CRM can stay a spreadsheet until volume justifies one | BUILD | Desmond | Leads captured |
| 6 | Email & lifecycle | `offers/outreach/email-templates.md`, `canada-us-newsletter-pitches.md`, `lead-list-template.csv`, `bots.outreach_preflight` | VERIFIED · templates only | No nurture sequence, no ESP, no list. `CLAUDE.md` records that on 2026-09-29 drafts containing `[ADD MAILING ADDRESS BEFORE SENDING]` **were sent as-is** | Mandatory `python -m bots.outreach_preflight` gate before any send; 5-email nurture after an ESP exists | BUILD | Desmond | Preflight pass rate 100% |
| 7 | Social distribution | 5 LinkedIn post drafts embedded in the Burlington campaign JSON | VERIFIED · drafts only | **No repurposing tooling exists** — `ls tools/ \| grep -i social\|linkedin\|repurpos` returns nothing | `tools/social_repurpose.py`: brief → 1 LinkedIn post + 1 X thread, written to a review file, never posted | BUILD | Desmond | Posts shipped per brief |
| 8 | Paid media readiness | `data/campaigns/burlington-campaign-packages.json` (5 campaigns), `tools/campaign_registry.py`, `assets/js/cg-attribution.js` on 11 pages | VERIFIED · 0 approvable | Blocker 5: no spend ceilings, 3 of 5 without landing pages | Build the 3 missing landing pages **or** cut those campaigns; set ceilings on what remains | SCALE | Desmond | Campaigns passing `--check` |
| 9 | Analytics & attribution | `analytics.js` (provider off), `cg-attribution.js` (UTM → lead form) on 11 pages, `tools/marketing_report.py` | VERIFIED · **OFF** | Blocker 1. Attribution plumbing is built and carries UTMs, but there is no traffic data to attribute | Set `provider: "plausible"` | **QUICK WIN** | Desmond | Analytics reporting: no → yes |
| 10 | AI agents & workflow automation | `agent_os/` (head agent, SQLite, leases, hash-chained log), `agent_army/`, `sentinel/`, 85 workflows (38 scheduled) | VERIFIED code, **BLOCKED** runtime | Blocker 2: no runner has started since 2026-09-06 | Fix billing, **or** run the loops locally on a cron until it is fixed | BUILD | Desmond (billing) | Scheduled jobs completing > 0 |
| 11 | Technical credibility | 53 briefs, `truth_forensics/` + browser twin with parity test, `docs/` (40+ specs), public governance model | VERIFIED · **strongest layer** | Credibility is buried in `docs/`; no single page shows a buyer the governance model | One "How ClearGlass works" proof page citing the audit ledger + RFED chain | BUILD | Desmond | Inbound citing the proof page |
| 12 | Cyber & trust positioning | Governance scoring (`control-plane/app/governance.py`), RFED hash-chained audit trail, `require_admin` route gate with test coverage | VERIFIED · genuinely differentiated | Not translated into buyer language anywhere on the marketing site | Convert the safety model into 3 buyer-facing proof claims | BUILD | Desmond | Objection-handling use |
| 13 | Compliance & brand-risk | `data/compliance/advertising-sources.json`, `legal/privacy.html` §10, advertising controls in `tools/campaign_registry.py` | VERIFIED · controls real, sources unread | The compliance file's own `provenance` states **none of the source pages were fetched** — the egress proxy refused every host. No platform requirement is actually verified | Owner re-reads each platform policy before any spend; set `fetched` dates | BUILD | Desmond | Sources with a real `fetched` date |

### Gap classification roll-up

- **QUICK WIN (0–7 days):** analytics on · FAQPage schema · cadence restart · positioning line
- **BUILD (8–30 days):** control plane deploy + live lead form · social repurposing tool · proof page · preflight gate · outreach nurture
- **SCALE (31–90 days):** paid media · CRM · agent-driven loops (gated on billing)

---

## PHASE 2 — Completing the Marketing OS

### 2.1 Positioning statement

> ClearGlass gives Ontario organisations evidence-grade visibility into their
> cyber and AI risk — read-only assessments that end in a ranked list of
> findings with owners and next actions, not a fear pitch.

Source of truth for the claim set: `llms.txt`, `docs/GROWTH_REVENUE_OS.md`.
**Note:** "evidence-grade" is defensible here *because* the repo ships an
append-only audit ledger and a hash-chained RFED trail. Do not use the phrase
in a context where that evidence is not reachable.

### 2.2 ICP segments

Derived from the SKUs that exist and the campaign audience fields — **not invented**:

| Segment | Evidence in repo | Entry SKU |
|---|---|---|
| Burlington / Halton SMEs, 5–100 staff | `burlington-cyber-risk-checkup.audience` | `quick-audit` |
| Ontario healthcare & allied-health custodians | `phipa` SKU, `offers/phipa-readiness.html` | `phipa` |
| M365-dependent small orgs | `m365-account-protection` campaign, `hardening` SKU | `hardening` |
| Critical-minerals / industrial suppliers | `critical-minerals-compliance` SKU, `docs/INDUSTRIAL_SUPPLIER_QUALIFICATION.md` | `critical-minerals-compliance` |

Ontario nonprofits and AI-governance buyers appear as campaign drafts with **no
matching SKU and no landing page**. They are not yet ICPs — they are untested
hypotheses. Treat them as such.

### 2.3 Offer architecture (real SKUs, real prices, from `data/store/catalog.json`)

| Tier | Offer | Price | Checkout |
|---|---|---|---|
| Lead magnet | PHIPA Readiness Checklist (`offers/phipa-readiness-checklist.html`) | free | — |
| Entry | **Security Quick-Audit** | CAD $249 one-time | Stripe link live |
| Core | **M365 + Windows Hardening Sprint** | from CAD $2,500 fixed fee | Stripe link live |
| Core | **PHIPA Readiness** | from CAD $3,000 assessment | Stripe link live |
| Core | **Critical Minerals Compliance Strategy** | CAD $1,499 one-time | Stripe link live |
| Retention | **Managed Monitoring** | from CAD $600 / month | Stripe link live |

**This is the finding that matters most in Phase 2:** the offer ladder is
already complete and already takes money. `live_checkout_enabled` is set and
all five Stripe URLs resolve to `buy.stripe.com` / `book.stripe.com`. The
constraint on revenue is **not** a missing funnel. It is that no instrument on
the site can tell you whether a single human has reached these pages.

Build nothing new at the offer layer until Blocker 1 is cleared.

### 2.4 Message hierarchy

- **Brand promise:** You will end the engagement knowing what to fix first, and why.
- **Proof pillar 1 — governed by construction:** every material action is
  risk-scored and written to an append-only ledger (`control-plane/app/governance.py`, `app/audit.py`).
- **Proof pillar 2 — tamper-evident:** RFED seals each decision into a SHA-256
  chain; altering a past record breaks every link after it (`bots/rfed_audit_bot.py`).
- **Proof pillar 3 — read-only first:** assessments do not touch production.
- **Objection "you're one person":** the governance model and audit trail are
  the deliverable's quality floor, independent of headcount.
- **Objection "why not a big firm":** fixed fee, 3-day finding window, named owner.

### 2.5 Funnel

`llms.txt` / brief / LinkedIn → offer page → **(instrumented CTA)** → Stripe
checkout *or* Calendly scoping call → delivery → Managed Monitoring retention.

The live funnel has exactly one measurement point today: Stripe tells you about
a completed payment. Everything upstream of the payment is dark.

### 2.6 Content pillars & cluster map

Pillars, each mapping to a SKU so content feeds revenue rather than vanity:

1. **Practical SME security** → `quick-audit`
2. **M365 / identity hardening** → `hardening`
3. **Ontario health-data & PHIPA** → `phipa`
4. **AI governance & agent safety** → no SKU yet — *decide: build one or stop publishing into it*
5. **Supply-chain / critical minerals compliance** → `critical-minerals-compliance`

Pillar 4 is the test: ClearGlass has the deepest technical evidence there
(`agent_os/`, RFED, governance scoring) and nothing to sell against it.

**Cadence:** one brief per week, same weekday, published through
`tools/insights_index.py`. Four drafted before restarting, so one bad week does
not break the streak again.

### 2.7 Landing page blueprint (highest-priority offer: `quick-audit`)

Existing page: `offers/security-quick-audit.html` — already loads
`cg-attribution.js`, already carries the Stripe link, Calendly link and
e-Transfer `mailto:`. It needs **four additions, not a rewrite**:

1. `FAQPage` JSON-LD (5 questions) — AEO citation surface
2. An instrumented CTA click event (inert until the analytics provider is set)
3. The one-line positioning statement as the `<h1>` deck
4. One proof line linking the governance model

### 2.8 Email nurture outline (build only after an ESP exists)

5 emails, triggered by checklist download: (1) deliver + one finding to check
today, (2) the single most common M365 misconfiguration, (3) what a Quick-Audit
report actually looks like, (4) PHIPA / sector-specific angle, (5) scoping call
offer. **Hard gate:** `python -m bots.outreach_preflight` on the exact text of
every email before any send. That gate exists because of the 2026-09-29
placeholder incident recorded in `CLAUDE.md`.

### 2.9 Social repurposing workflow

`tools/social_repurpose.py` (to build, stdlib-only, matching repo convention):
reads a published brief → emits one LinkedIn post and one X thread into
`data/social/queue/` as drafts → **writes files only, never posts.** Owner
copies and publishes manually. No platform credential enters this repo.

### 2.10 AI agent workflow map

`agent_os/head.py` already does objective → bounded mission → delegated tasks
across five worker agents with approval gates and a hash-chained event log.
Marketing work maps onto the existing roles: `repository` (draft), `verification`
(fact-check against sources), `integration` (publish to the site tree),
`security` (claim review), `deployment` (ship). **No new agent framework is
needed — and none of it runs on a schedule until Blocker 2 is cleared.**

### 2.11 Reporting dashboard spec

`tools/marketing_report.py` already reports only what the repo proves. Extend it
with: briefs published (30d), pages with FAQPage, campaigns passing `--check`,
analytics provider state, lead-form live state. Every row cites its file. Rows
with no evidence print `NO DATA` — never `0`.

---

## PHASE 3 — Automation designs

**Governing constraint, stated once and applying to all twelve:** while Actions
dispatches no runners, every `schedule:` trigger below is a design, not a
running system. Run them as local commands until billing is fixed. A workflow
that silently never fires is worse than no workflow, because it reports success
by absence.

| # | Automation | Trigger | AI role | Output | Human approval | Fallback | Metric |
|---|---|---|---|---|---|---|---|
| 1 | Topic selection | Weekly, local | `repository` | 5 ranked topics w/ sources | Owner picks 1 | Owner picks unaided | Topics w/ real source |
| 2 | SEO/GEO brief | Topic chosen | `repository` | Brief + FAQ block | Owner reviews | Manual outline | Briefs w/ FAQPage |
| 3 | Draft & publish | Brief approved | `repository`+`integration` | Brief in `blog/`, index regenerated | **Required before merge** | Hand-write | Briefs/month ≥ 4 |
| 4 | Social repurpose | Brief published | `repository` | Drafts in `data/social/queue/` | **Required before posting** | Manual write-up | Posts per brief |
| 5 | Lead capture | Form submit | none | Ledger row + opaque `reference` | n/a | `mailto:` fallback | Leads captured |
| 6 | Lead scoring | New lead | `verification` | Score + suggested route | Owner confirms | Manual triage | Scored leads |
| 7 | Nurture send | Download | none | Queued email | **Required + preflight** | No send | Preflight pass 100% |
| 8 | Conversion monitoring | Weekly | `verification` | Funnel + drop-off | Report only | Manual check | Weeks reported |
| 9 | Competitor watch | Weekly | `verification` | Entry w/ https source, date, ≤280-char quote | Owner before registry write | No entry | Entries passing `--check` |
| 10 | AEO visibility | Monthly | `verification` | Where ClearGlass is/isn't cited | Report only | Manual spot-check | Months reported |
| 11 | Weekly report | Weekly | `repository` | `tools/marketing_report.py` output | Report only | Run by hand | Reports produced |
| 12 | Monthly review | Monthly | `head` | Ranked recommendations | **Required for any change** | Owner review | Actions taken |

**Safeguards (all twelve):** no publish without approval · no outreach without
verified consent and preflight · no unsupported performance or security claim ·
no customer data in any generated artefact · every action lands in the
append-only ledger · no credential enters this repo.

---

## PHASE 4 — 30/60/90

### Days 0–30 — Make it measurable, then make it move

**Objective:** end the month able to answer "did anyone see this?"

| Deliverable | Depends on | Validation |
|---|---|---|
| Analytics provider set to Plausible | none | Live page shows a request |
| FAQPage schema on 7 offer pages | none | `grep -rl '"FAQPage"' --include=*.html . | wc -l` → 9 |
| 4 briefs published, weekly slot held | none | `datePublished` shows 4 Oct/Nov dates |
| Control plane deployed; `cg-revenue-api` set | `DEPLOY.md` | Test submit creates a ledger row |
| Billing unlocked, runners dispatching | **owner, org settings** | A job reports `runner_id != 0` |

**KPIs:** analytics reporting (no→yes) · pages w/ FAQPage (2→9) · briefs/month (1→4) · lead form live (no→yes)
**Risk:** billing stays locked → all automation stays manual. *Mitigation: every Phase 3 design runs as a local command; none of them requires Actions to produce its output.*

### Days 31–60 — Convert what the traffic data shows

Social repurposing tool · 5-email nurture behind preflight · proof page ·
landing-page upgrades on the two offer pages that analytics shows actually get
traffic — **not** all nine.
**KPIs:** posts per brief · preflight pass rate 100% · offer-page → checkout rate (first real baseline)

### Days 61–90 — Spend only against measured conversion

Resolve the three campaigns with no landing page (build or cut) · set spend
ceilings · owner re-reads each platform policy and sets `fetched` dates in
`data/compliance/advertising-sources.json` · decide pillar 4: build an
AI-governance SKU or stop publishing into it.
**KPIs:** campaigns passing `--check` · cost per qualified lead · pipeline contribution
**Risk:** spending against unmeasured funnels. *Mitigation: `tools/campaign_registry.py` already blocks approval without a ceiling and a landing page. Do not weaken it.*

---

## PHASE 5 — First execution sprint

### The single highest-impact next action

**Switch on privacy-respecting analytics, and instrument the five live Stripe
CTAs.**

**Why this and not content or funnel work.** The offer ladder is already
complete and already takes money — five SKUs, five live Stripe links,
`live_checkout_enabled` set. Building more funnel on top of an unmeasured one is
guessing with extra steps. This change takes minutes and converts every later
decision from opinion into evidence.

**And a compliance finding that makes it urgent.** `legal/privacy.html` §10
currently states: *"Our website uses minimal, privacy-respecting analytics. We
do not deploy advertising cookies or third-party tracking pixels."* Analytics is
off. **The published privacy policy describes a practice the site does not
currently have.** Setting `provider: "plausible"` — cookieless, no personal
data, no pixel — brings the site *into* alignment with its own policy. Setting
`provider: "ga4"` would contradict §10 and must not be chosen.

### Workflow

1. `analytics.js:37` → `provider: "plausible"`, confirm `domain`.
2. `analytics.js:23–24` notes `_headers` `connect-src` names neither provider.
   GitHub Pages ignores `_headers`, so this is latent — fix it anyway before any
   host that honours CSP serves the site.
3. Add a click event to the Stripe/Calendly CTA on each of the 7 offer pages.
   Events stay inert until the provider is set, so this is safe to land first.
4. Bump `VERSION` in `sw.js` so returning visitors' service-worker caches refresh.
5. Run `python3 scripts/ci_local.py` before pushing — **CI reports nothing right
   now, so a green check is absence of signal, not success** (`CLAUDE.md`).

### Required from the owner

- Plausible account + confirmation the domain matches
- Confirmation that cookieless analytics is the intended reading of privacy §10
- Whether the GitHub billing lock is being resolved, and when

### Success metric & checkpoint

Seven days after deploy: a non-zero visitor count and a measured
offer-page → checkout-click rate for at least one of the five SKUs. That number
is the first real input this marketing system has ever had.
**Checkpoint: 2026-11-03.**

---

## Missing information required

1. Traffic, ranking and conversion history — **none exists in this repo**, and none can be reconstructed. Measurement starts the day analytics is switched on.
2. Whether any of the five Stripe SKUs has sold. `docs/GROWTH_REVENUE_OS.md` §5 separates VERIFIED from NOT VERIFIED; no sale is recorded here.
3. Whether an email list or ESP exists outside this repo.
4. Social follower counts and posting history.
5. Whether the GitHub billing lock has a resolution date.
6. Budget ceiling for paid media.

## Assumptions made

1. The repo is a faithful picture of the marketing stack. If assets live only in Notion, Google Drive or a third-party tool, this audit under-counts them.
2. `live_checkout_enabled` plus well-formed Stripe URLs means checkout works. **Not verified by transaction** — no payment was attempted.
3. A weekly floor is sustainable for a solo operator. Unverified against actual capacity — but it is 1/8th of the July rate, which demonstrably was not.
4. Plausible is acceptable to the owner. GA4 is ruled out on the privacy-policy grounds above, not on preference.

## Recommended approval gates

| Action | Gate |
|---|---|
| Publish a brief | Owner review before merge |
| Post to social | Owner posts manually; no credential in repo |
| Send any email | Owner approval **+** `bots.outreach_preflight` pass |
| Activate a campaign | Owner sets `spend_ceiling_cad` **+** `governance` attestation |
| Change analytics provider | Owner **+** privacy-policy consistency check |
| Make a security or performance claim | Evidence cited or the claim is cut |
