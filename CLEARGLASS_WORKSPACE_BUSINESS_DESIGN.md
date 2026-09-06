# ClearGlass Workspace — Subscription Business Design

**Status:** Design document. Nothing in this file is provisioned unless a section
says it already exists in the repo.
**Owner:** ClearGlass Inc., Ontario, Canada
**Currency:** CAD throughout. All amounts are exclusive of GST/HST unless stated.
**Last revised:** 2026-08-06

> **Two things to read before acting on this document.**
>
> 1. **Get this reviewed.** Before you sell a seat, have a qualified Ontario
>    lawyer review the terms of service, refund/auto-renewal language, privacy
>    policy and any supplier/reseller agreement, and have a qualified Canadian
>    accountant (CPA) review the GST/HST registration position, the revenue
>    recognition treatment of annual prepayments, and the corporate structure.
>    This document is a design, not legal or tax advice.
> 2. **Nothing here promises income.** Every revenue figure in §5, §21 and §22 is
>    a *model* — an arithmetic consequence of assumptions that are stated inline
>    so you can disagree with them. They are not forecasts, not targets you are
>    entitled to, and not a claim that any of them will be reached.

---

## Contents

| # | Deliverable | § |
|---|---|---|
| 1 | Business name & positioning | [§1](#1-business-name--positioning) |
| 2 | Customer personas | [§2](#2-customer-personas) |
| 3 | Value proposition | [§3](#3-value-proposition) |
| 4 | Pricing matrix | [§4](#4-pricing-matrix) |
| 5 | Revenue model | [§5](#5-revenue-model) |
| 6 | Customer journey | [§6](#6-customer-journey) |
| 7 | Sitemap | [§7](#7-sitemap) |
| 8 | User flows | [§8](#8-user-flows) |
| 9 | Database schema | [§9](#9-database-schema) |
| 10 | API design | [§10](#10-api-design) |
| 11 | System architecture | [§11](#11-system-architecture) |
| 12 | Payment & webhook design | [§12](#12-payment--webhook-design) |
| 13 | Automation map | [§13](#13-automation-map) |
| 14 | Admin dashboard spec | [§14](#14-admin-dashboard-spec) |
| 15 | Threat model | [§15](#15-threat-model) |
| 16 | Compliance checklist | [§16](#16-compliance-checklist) |
| 17 | SEO strategy | [§17](#17-seo-strategy) |
| 18 | Email templates | [§18](#18-email-templates) |
| 19 | Launch plan | [§19](#19-launch-plan) |
| 20 | 30/60/90 roadmap | [§20](#20-306090-roadmap) |
| 21 | KPIs | [§21](#21-kpis) |
| 22 | Break-even analysis | [§22](#22-break-even-analysis) |
| 23 | Testing strategy | [§23](#23-testing-strategy) |
| 24 | Deployment plan | [§24](#24-deployment-plan) |
| 25 | Risk register | [§25](#25-risk-register) |
| — | Family operating model | [§26](#26-family-operating-model) |

---

## 0. The decision that gates everything

**How is the software actually delivered?** The pricing page (`workspace.html`)
promises business email on a customer's domain, encrypted file storage, shared
calendars, browser documents, video meetings and desktop apps. Three delivery
models are available, and the choice changes the unit economics, the compliance
surface and the risk register. **Do not sell a seat before this is chosen and
documented.**

| Model | What it means | Gross margin at $8.10/seat | Blocking prerequisite |
|---|---|---|---|
| **A — Self-hosted** *(assumed throughout this document)* | ClearGlass operates the stack (mail server, object storage, calendaring, collaborative editing, meetings) on infrastructure it controls | ~90% at scale; negative below ~30 seats | Operational capacity: mail deliverability, backups, 24/7 incident response |
| **B — Authorized reseller / white-label** | ClearGlass resells a third party's suite under a signed reseller or white-label agreement | 15–40%, set by the supplier's wholesale price | **A signed agreement.** Reselling licensed software without one is a contract and copyright violation and is out of scope for this business |
| **C — Managed service on the customer's own tenant** | The customer buys their own licences; ClearGlass sells setup, migration, administration and support | ~85% (labour-bound, not licence-bound) | Nothing — this is sellable today |

**Recommendation.** Model C is the only one you can sell this week without new
agreements or new infrastructure, and it is honest: you are selling the work you
already do. Model A is the one the pricing page currently describes; treat it as
a build, not a launch. If you pick A, §4's prices must be re-derived from real
infrastructure cost, not from a competitor's price list. If you pick B, the
supplier agreement must be signed and on file **before** the first checkout, and
§25-R3 stops being a risk and becomes a control.

The rest of this document is written for **Model A**, because it is the strictest
case — every compliance, security and cost obligation in it also covers B and C.

---

## 1. Business name & positioning

**Name:** ClearGlass Workspace
**Legal entity:** ClearGlass Inc. (Ontario, Canada)
**Domain:** `clearglassinc.com/workspace.html` → migrate to `workspace.clearglassinc.com` at §20 day 60
**Tagline:** *Flexible business productivity plans that scale with your team.*

**Positioning statement.** For Canadian small businesses, freelancers and remote
teams who need business email, files and collaboration but do not have an IT
department, ClearGlass Workspace is a per-seat productivity subscription that
includes the setup and migration work, unlike self-serve suites where the
onboarding is a help article and the support is a forum.

### Brand-positioning options

Three viable positions. They are mutually exclusive in messaging — pick one and
let it govern every page, or the site reads as three businesses.

| Option | Position | Headline emphasis | Best for | Risk |
|---|---|---|---|---|
| **A — The Done-For-You Suite** *(recommended)* | "The productivity suite that comes with someone who sets it up." | Setup, migration and support are included, not sold | P1 + P2, referral-led growth | Ties revenue to labour; must automate onboarding to scale |
| **B — The Canadian Alternative** | "Business productivity, run from Canada, answerable in Canada." | Data handling, tax, jurisdiction, a named human | P3 and procurement buyers | Requires real data-residency answers you must be able to defend |
| **C — The Security-First Workspace** | "Business email and files, built by people whose day job is security." | Encryption, access model, audit, incident response | Regulated-adjacent buyers | Raises the bar you are held to; a single incident is disproportionately damaging |

**Recommendation: A, with B as supporting proof.** A is the only position that
matches what ClearGlass can deliver on day one and is the hardest for a larger
competitor to copy — hyperscalers cannot profitably do a two-hour hands-on
migration for a four-person firm. Use B's jurisdiction language inside the
security section rather than as the headline. Do not lead with C until §16's
controls are independently verified.

**Alternate names**, if the CIPO search below returns a conflict: *ClearGlass
Works*, *Northline Workspace*, *Steady Workspace*, *Plainview Business Suite*.
All four are unverified — search before adopting.

**Name constraints already applied.** All plan names, feature names and copy are
original. No third-party product name, logo, trade dress or pricing is used, and
no reseller or partnership claim is made anywhere on the site. This is not a
stylistic preference — it is the difference between a business and a trademark
claim. Keep it.

**Naming checks still outstanding (do these before spending on the brand):**

- [ ] CIPO trademark search for "ClearGlass Workspace" in Nice classes 9, 42 and 45
- [ ] Ontario NUANS report for any operating-name registration
- [ ] Domain + social handle availability for `clearglassworkspace`
- [ ] Confirm "Workspace" is descriptive enough to be unregistrable as a standalone mark — expect to protect **ClearGlass**, not **Workspace**

---

## 2. Customer personas

### P1 — "Renu, the two-person consultancy"
- **Size:** 2–4 seats · **Plan:** Essentials · **Annual value:** ~$144–$288
- **Today:** Free consumer mail on a `@gmail.com` address, files in a personal cloud drive, invoices in a spreadsheet.
- **Trigger to buy:** A client asked for a `@company.ca` address, or a bank/insurer asked how client data is stored.
- **What she is really buying:** Looking like a real firm, without becoming a system administrator.
- **What kills the sale:** Anything that reads like a project. If setup looks like more than one conversation, she stays put.
- **Where she is:** Referrals from an accountant or lawyer; local business association; searching *"business email with my own domain Canada"*.

### P2 — "Marcus, the 12-person trades company"
- **Size:** 8–20 seats · **Plan:** Collaborate · **Annual value:** ~$777–$1,944
- **Today:** A mix of personal addresses, a shared login everyone knows, files on one office PC that is also the backup.
- **Trigger to buy:** Someone left and took the account; or a phishing email got paid; or a contract now requires "documented security controls".
- **What he is really buying:** Not having the company depend on one laptop and one person's memory.
- **What kills the sale:** Downtime during the switch. His crews cannot lose email for a day.
- **Where he is:** Word of mouth; a bookkeeper's recommendation; searching *"team email shared calendar small business Ontario"*.

### P3 — "Dana, the 35-person distributed agency"
- **Size:** 25–60 seats · **Plan:** Complete · **Annual value:** ~$5,100–$12,240
- **Today:** A real suite already, but nobody administers it; offboarding is inconsistent; nobody can answer an audit question.
- **Trigger to buy:** A client security questionnaire she could not complete, or a renewal quote that jumped.
- **What she is really buying:** Someone accountable, with a name and a phone number.
- **What kills the sale:** No answer on data residency, retention, or export. She will ask all three.
- **Where she is:** Peer networks; procurement search; RFP shortlists.

### Anti-persona — explicitly not a customer
Enterprises above ~250 seats (procurement cycles and SOC 2 requirements this
business cannot meet yet), regulated health and legal practices requiring
specific data-residency certifications, and anyone shopping purely on price. Say
no early; each one costs more in support than it returns.

---

## 3. Value proposition

**Core promise:** *Business-grade email, files and collaboration, set up for you,
on a per-person price you can change any month.*

Three differentiators, each of which must remain literally true:

1. **Setup is included, not sold separately.** Domain, DNS, mail routing,
   migration and user accounts are configured by ClearGlass during onboarding.
   The competitor equivalent is a documentation link.
2. **Per-seat and reversible.** Seats are added pro-rata and removed as a credit.
   No annual seat floor, no cancellation penalty, no "contact sales to
   downgrade".
3. **Answers, not badges.** Encryption, export, access model and tax handling are
   stated in specifics on the pricing page. Any customer can read the actual
   policies before buying.

**What this is not.** It is not the cheapest option, it is not a hyperscaler, and
it does not have compliance certifications it has not earned. Saying so in the
sales conversation is a feature for P3 and neutral for P1/P2.

**Proof obligations.** Every claim above is testable, and each has an owner in
§23. Do not add a claim to the site that has no test behind it.

---

## 4. Pricing matrix

Per person, per month, CAD, exclusive of GST/HST. These are the values already
live in `workspace.html`.

**Tier-name mapping.** The brief describes the tiers by their function
("Business Basic", "Business Basic Without Teams", "Business Standard"). Those
are descriptive labels borrowed from an existing vendor's catalogue, so the site
uses original names at the same price points. The mapping is exact:

| Brief's label | Price (annual) | Ships as | Why renamed |
|---|---|---|---|
| Business Basic Without Teams | $6.00 | **Essentials** | "Without Teams" names a third-party product; "Essentials" describes the tier on its own terms |
| Business Basic | $8.10 | **Collaborate** | The tier's distinguishing feature is collaboration, so name it that |
| Business Standard | $17.00 | **Complete** | Reads as a top tier rather than a middle one, which is what it is |

The ladder also runs cheapest-first so the comparison table reads left to right —
the brief listed $8.10 before $6.00, which inverts on a pricing page.

| | **Essentials** | **Collaborate** *(most popular)* | **Complete** |
|---|---|---|---|
| **Annual** (billed 12 months up front) | **$6.00** | **$8.10** | **$17.00** |
| **Monthly** (no commitment) | **$7.20** | **$9.72** | **$20.40** |
| Annual saving | 16.7% | 16.7% | 16.7% |
| Annual invoice, 1 seat | $72.00 | $97.20 | $204.00 |
| Business email on own domain | ✓ | ✓ | ✓ |
| Encrypted file storage & sharing | ✓ | ✓ | ✓ |
| Shared calendars & contacts | ✓ | ✓ | ✓ |
| Browser documents & spreadsheets | ✓ | ✓ | ✓ |
| Mobile access | ✓ | ✓ | ✓ |
| Spam filtering & account security | ✓ | ✓ | ✓ |
| Video meetings | — | ✓ | ✓ |
| Team chat & channels | — | ✓ | ✓ |
| Shared team drives | — | ✓ | ✓ |
| Priority email support | — | ✓ | ✓ |
| Desktop apps with offline access | — | — | ✓ |
| Advanced retention & audit controls | — | — | ✓ |
| Guided onboarding & migration | — | — | ✓ |
| Named support contact | — | — | ✓ |

**Add-ons (one-time, any plan)**

| SKU | What | Price |
|---|---|---|
| `ws-migration-standard` | Migration from an existing provider, up to 10 mailboxes | $450.00 |
| `ws-migration-plus` | Migration, 11–50 mailboxes | $1,200.00 |
| `ws-domain-setup` | Domain, DNS, SPF/DKIM/DMARC configuration | $150.00 |
| `ws-training-session` | 90-minute team onboarding session | $250.00 |

**Pricing rules that must hold in code**

- **The browser never sends a price.** `POST /checkout/session` accepts SKU and
  quantity only; the amount comes from the price book and, in live mode, from the
  Stripe Price it references. Enforced by
  `clearglass-commerce/control-plane/tests/test_pricebook.py`.
- **Trial:** 14 days, no card charged during trial, card collected at signup.
  Ontario's *Consumer Protection Act* and Stripe's own rules both require the
  post-trial charge to be disclosed before signup — it is, on `workspace.html`.
- **Proration:** seats added mid-period bill pro-rata; seats removed become a
  credit against the next invoice, not a refund. Stated on the page; must match
  the Stripe subscription configuration.
- **Grandfathering:** existing subscriptions keep their price through the current
  term. Price changes apply at renewal with **30 days' written notice**. Never
  reprice a live term.
- **Currency:** CAD only at launch. Do not add USD until §20 day 90 at the
  earliest — dual currency doubles the price-book surface and the tax logic.
- **Enterprise (50+ seats):** custom pricing, quoted individually, never
  published. Every quote goes through the §26 approval workflow.

### Coupons and promotions

Coupons are the one legitimate way an amount differs from the price book, so they
need the same discipline as prices.

| Rule | Detail |
|---|---|
| Where they live | Stripe Coupons/Promotion Codes — **never** a discount field on a request body |
| What the browser sends | A promotion **code string** only. Stripe validates it and computes the discount |
| Creation | Behind `require_admin` **and** an approval row (§13 A15). A coupon is a price change |
| Types allowed | Percentage or fixed-amount off; first-period or N-period; referral/affiliate attribution codes |
| Types not allowed | Anything requiring a false claim to justify — "48 hours only" on a code that renews monthly, "was $X" where $X was never charged |
| Stacking | One promotion code per subscription. No silent stacking |
| Expiry | Every code carries a real expiry date and a max redemption count |
| Audit | Creation, redemption and expiry each write a `workspace_events` row |

**Launch offers that are honest:** a genuine first-year discount for the Phase 1
cohort, a referral credit paid to both sides and disclosed, and a waived
migration fee on annual plans. All three are real, defensible, and need no
manufactured urgency.

---

## 5. Revenue model

**Primary:** per-seat recurring subscription (MRR/ARR).
**Secondary:** one-time onboarding, migration and training services (§4 add-ons).
**Tertiary:** annual prepayment, which is not extra revenue but is materially
cheaper to collect (below) and improves cash position.

### Revenue channels

Eleven channels, each with a delivery cost and a gate. Channels are ordered by
how soon they can legitimately start — do not open a later one to compensate for
a weak earlier one.

| # | Channel | Model | Gross margin | Gate before it can start |
|---|---|---|---|---|
| C1 | Seat subscriptions | Recurring, per seat | ~90% (Model A at scale) | §0 delivery model chosen |
| C2 | Onboarding & migration packages | One-time, $150–$1,200 | ~85% (labour) | Runbook written during customer one |
| C3 | Business setup & domain configuration | One-time, $150 | ~85% | None — sellable now |
| C4 | Premium technical support | Recurring add-on, ~$99/mo | ~80% | A stated SLA you can actually meet |
| C5 | Cybersecurity checkup packages | One-time, $297 | ~90% | **Already live** (`risk-audit-90`) |
| C6 | Website & automation consulting | Project, quoted | ~75% | Capacity — this competes with C1 for founder time |
| C7 | Downloadable templates, checklists, scripts | One-time, $19–$199 | ~98% | Original content only; no scraped or repackaged material |
| C8 | Affiliate commissions from authorized tools | Revenue share | 100% (no COGS) | Written affiliate agreement + **disclosed on every page** |
| C9 | Referral partnerships (accountants, bookkeepers) | Per-conversion fee | ~85% net | Written agreement; disclosed to the referred customer |
| C10 | White-label services | Wholesale | 30–50% | **Only where a contract permits it.** No contract, no channel |
| C11 | Enterprise plans (50+ seats) | Custom recurring | ~90% | Approval workflow per quote (§26) |

**Rules that bind every channel.** Affiliate and referral relationships are
disclosed in plain language wherever a recommendation appears — not in a footer,
next to the recommendation. Commission never changes what gets recommended; if a
tool is not what you would advise unpaid, it does not go on the page. No channel
markets to anyone without consent (§16, CASL). C10 does not exist until a
contract says it does.

**Digital products (C7) are the quiet compounder.** Zero marginal cost, no
support load, and they double as SEO lead magnets (§17). They are also the
easiest place to accidentally infringe — every template must be written from
scratch, not adapted from a competitor's.

### Effective payment-processing cost

Stripe Canadian domestic card pricing is **2.9% + $0.30 CAD** per successful
charge. The fixed $0.30 is charged **per invoice**, so it is diluted by both plan
price and billing frequency. Worst case shown — a **single-seat** subscription,
where the fixed fee has the fewest seats to spread across:

| Plan | Monthly billing | Annual billing |
|---|---|---|
| Essentials | $7.20 charge → $0.51 fee = **7.1%** | $72.00 charge → $2.39 fee = **3.3%** |
| Collaborate | $9.72 charge → $0.58 fee = **6.0%** | $97.20 charge → $3.12 fee = **3.2%** |
| Complete | $20.40 charge → $0.89 fee = **4.4%** | $204.00 charge → $6.22 fee = **3.0%** |

**Annual billing roughly halves the effective processing cost** — not because the
percentage rate changes, but because $0.30 is paid once a year instead of twelve
times. On a single Collaborate seat that is $3.86/year recovered; across 500
seats it is ~$1,930/year. This is why the annual toggle defaults to on, and it is
a better reason to push annual than "cash flow".

*(Card-not-present rates for international cards add ~0.8% and currency
conversion adds ~2%. Model those separately once non-Canadian customers exist.)*

### Revenue mix target at 12 months

| Stream | Share of revenue | Why |
|---|---|---|
| Recurring subscription (C1, C4) | 70% | The asset. Everything else exists to feed it |
| Onboarding / migration / setup (C2, C3) | 18% | High-margin, front-loaded, and the reason customers switch at all |
| Security & consulting (C5, C6) | 7% | Already sellable; also the strongest referral generator |
| Digital products (C7) | 3% | Small revenue, large SEO and lead-magnet value |
| Affiliate / referral (C8, C9) | 2% | Never optimise for this — it corrupts recommendations |

If subscription revenue falls below ~60% of the total, this has stopped being a
subscription business and become a consultancy with a software line. That is a
viable business, but it is not this plan, and the §22 economics do not describe
it.

### Cash timing

Annual prepayment collects 12 months on day 1 but is **deferred revenue**, not
earned revenue. Recognise 1/12 per month. Booking annual prepayments as revenue
is the single most common way a subscription business misreads its own health —
raise this specifically with the accountant in §16.

---

## 6. Customer journey

```
AWARENESS      →  CONSIDERATION  →  TRIAL        →  CONVERSION   →  ONBOARDING   →  RETENTION    →  EXPANSION
Search /          Pricing page,      14-day free     Stripe          Domain +        Support,        More seats,
referral /        comparison,        trial, card     Checkout,       migration,      quarterly       plan upgrade,
local network     policies read      on file         subscription    accounts live   check-in        add-ons
                                     no charge       created
     ↓                  ↓                 ↓               ↓                ↓               ↓              ↓
  Blog, SEO,        FAQ, security     Welcome +      Receipt +       Onboarding     Usage +         Seat-count
  consultation      section, legal    setup call     invite to       complete +      health email    review at
  offer             pages             booking        onboarding      training                       renewal
```

| Stage | Customer's question | What must exist | Success signal |
|---|---|---|---|
| Awareness | "Is there a Canadian option that isn't a hyperscaler?" | Indexed pricing page, comparison content, referral path | Session on `workspace.html` |
| Consideration | "What does it actually include, and what does it cost me?" | Comparison table, seat calculator, FAQ, published policies | Seat input changed, `#compare` viewed |
| Trial | "Will this break my email?" | Trial without charge, setup call booked within 24h | Trial started |
| Conversion | "Am I locked in?" | Cancel-anytime terms, hosted Stripe Checkout, disclosed post-trial charge | `checkout.session.completed` |
| Onboarding | "When does it work?" | Migration runbook, DNS cutover plan, rollback plan | First mail delivered on customer domain |
| Retention | "Is anyone paying attention?" | Support SLA by plan, quarterly check-in, incident comms | Renewal without a support escalation |
| Expansion | "Can we add the new hires?" | Self-serve seat add, pro-rata billing | Seat count increases |

**Two moments carry the whole journey.** The **setup call** (trial → conversion)
and the **DNS cutover** (onboarding). Everything else can be automated. Neither
of those should be.

**Explicitly excluded tactics.** No countdown timers, no fabricated "N people are
viewing", no fake scarcity, no pre-ticked upsells, no cancellation flow that
hides the cancel button, no unsolicited outbound to scraped lists, no
testimonials from anyone who is not a verified paying customer. These are not
just prohibited by the brief — CASL makes some of them a statutory penalty
(§16).

---

## 7. Sitemap

```
/
├── index.html ....................... Homepage — value proposition  [EXISTS]
├── workspace.html ................... Workspace pricing & plans     [EXISTS]
│   ├── #plans ....................... Plan cards + seat calculator
│   ├── #compare ..................... Feature comparison table
│   └── #faq ......................... Frequently asked questions
├── workspace-features.html .......... Feature detail pages          [BUILD — day 30]
│   ├── workspace-email.html ......... Business email deep-dive      [BUILD — day 30]
│   ├── workspace-storage.html ....... File storage & sharing        [BUILD — day 60]
│   └── workspace-migration.html ..... Migration service             [BUILD — day 30]
├── workspace-security.html .......... Security & data handling      [BUILD — day 60]
├── workspace-vs.html ................ Honest comparison guide       [BUILD — day 60]
├── pricing.html ..................... Consolidated pricing hub      [EXISTS]
├── checkout/ ........................ Hosted checkout entry         [EXISTS]
├── store.html ....................... Product store                 [EXISTS]
├── side-store.html .................. Side Store                    [EXISTS]
├── plans.html ....................... Guardian per-seat tiers       [EXISTS]
├── offers/
│   └── guardian-command-nexus-blueprint.html                        [EXISTS]
├── legal/
│   ├── terms.html ................... Terms, refunds & cancellation [EXISTS]
│   ├── privacy.html ................. Privacy policy                [EXISTS]
│   ├── content-policy.html .......... Acceptable use                [EXISTS]
│   ├── accessibility.html ........... Accessibility commitment      [EXISTS]
│   ├── workspace-dpa.html ........... Data processing addendum      [BUILD — day 60]
│   └── cookies.html ................. Cookie & tracking notice      [BUILD — day 30]
├── resources/ ....................... Resource centre hub           [BUILD — day 60]
│   ├── templates.html ............... Downloadable templates (C7)   [BUILD — day 60]
│   ├── checklists.html .............. Business setup checklists     [BUILD — day 60]
│   └── guides.html .................. Long-form guides              [BUILD — day 90]
├── blog/ ............................ Topic cluster content         [BUILD — day 30+]
├── support.html ..................... Support hub, SLA, contact     [BUILD — day 30]
├── contact.html ..................... Contact + consultation form   [BUILD — day 30]
├── customers.html ................... Verified testimonials only    [BUILD — day 90]
├── partners.html .................... Referral & affiliate program  [BUILD — day 90]
├── sitemap.xml / robots.txt / feed.xml                              [EXISTS]
└── app.clearglassinc.com (separate origin)
    ├── /signup /login /forgot /verify-email /mfa
    ├── /dashboard ................... Plan, usage, entitlements
    ├── /dashboard/team .............. Users, invitations, roles
    ├── /dashboard/billing ........... Invoices, portal, plan change
    ├── /dashboard/security .......... Sessions, MFA, activity log
    ├── /dashboard/preferences ....... Notification & marketing consent
    ├── /dashboard/support ........... Tickets
    └── /admin/internal .............. Staff-only, §14
```

**Cookie consent and marketing preferences.** A consent banner is required
before any non-essential cookie or tracking pixel fires — not after, and not
with analytics pre-enabled. Essential/functional cookies run without consent;
analytics and retargeting do not fire until the visitor opts in, and the choice
is revocable from `legal/cookies.html` and from `/dashboard/preferences`. Consent
state (timestamp, scope, method, version of the notice) is recorded in
`marketing_consent` (§9) because under PIPEDA and CASL the burden of proving
consent is yours.

New pages must be added to `PAGES` in `tools/internal_links.py`, regenerated with
`python3 tools/internal_links.py`, and added to `sitemap.xml`. Bump `VERSION` in
`sw.js` when several change at once.

---

## 8. User flows

### 8.1 Trial signup → first login

```
Visitor on workspace.html
  → selects plan + seat count
  → POST /workspace/trial  {plan_sku, seats, email, org_name, domain}
  → validate: email deliverable, domain not already claimed, seats 1..500
  → create tenant (status=trialing) + owner user (status=invited)
  → Stripe Customer created (email + tenant_id metadata)
  → Stripe Checkout Session, mode=subscription, trial_period_days=14
  → redirect to Stripe-hosted page (card collected, NOT charged)
  → checkout.session.completed webhook
  → tenant.status=trialing, subscription row written, trial_ends_at set
  → transactional email T1 (§18) + setup-call booking link
  → owner sets password via single-use token (24h TTL) → first login
```

**Failure branches:** abandoned checkout → tenant stays `pending`, purged after
7 days; duplicate domain → 409 with a support contact, never a silent merge;
card declined at trial end → §8.4.

### 8.2 Trial → paid conversion

```
Day 11: email T3 "your trial ends in 3 days" (transactional, not marketing)
Day 14: Stripe charges the subscription automatically
  → invoice.payment_succeeded webhook
  → tenant.status = active, current_period_end set
  → email T4 receipt with itemised GST/HST
Day 14 (alternate): customer cancelled during trial
  → subscription cancelled at Stripe, tenant.status = cancelled
  → data retained 30 days, then purged (§16)
  → email T9 "your trial ended, here's your export"
```

### 8.3 Seat change

```
Admin → /admin/users → Add person
  → POST /workspace/seats {delta: +1}
  → require_admin (tenant-scoped) + seat cap check
  → Stripe subscription item quantity updated, proration_behavior=create_prorations
  → customer.subscription.updated webhook → seats persisted
  → provisioning job creates the mailbox + storage quota
  → email T6 "person added, your next invoice will show..."

Removal is the same path with delta:-1 and proration_behavior=create_prorations,
producing a credit balance rather than a refund. The mailbox is suspended
immediately and purged after 30 days — the customer is told both dates.
```

### 8.4 Failed payment (dunning)

```
invoice.payment_failed
  → attempt 1: retry day 3   + email T7a (fix your card)
  → attempt 2: retry day 5   + email T7b
  → attempt 3: retry day 7   + email T7c (final notice, date of suspension)
  → day 10: tenant.status = past_due → service read-only (mail delivers, no send)
  → day 24: tenant.status = suspended → all access blocked, data retained
  → day 54: data purged after two further notices
```

Never delete customer data on a failed payment without two prior written notices
and a stated purge date. Locking out a business from its own mail is severe;
deleting it is unrecoverable.

### 8.5 Cancellation

One click from the account page. No retention interstitial, no "are you sure"
chain, no phone-only cancellation. The confirmation screen states: the last day
of paid access, the export link, and the purge date. That is the whole flow.

---

## 9. Database schema

PostgreSQL, following the existing control plane conventions. Next migration
number is **006** (`005_fulfillment.sql` is the current head).

```sql
-- 006_workspace.sql

CREATE TABLE tenants (
    id                  BIGSERIAL PRIMARY KEY,
    public_id           UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    org_name            TEXT NOT NULL,
    primary_domain      TEXT UNIQUE,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','trialing','active','past_due',
                                          'suspended','cancelled','purged')),
    country             CHAR(2) NOT NULL DEFAULT 'CA',
    province            TEXT,
    stripe_customer_id  TEXT UNIQUE,
    trial_ends_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    public_id       UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    email           TEXT NOT NULL,
    display_name    TEXT,
    role            TEXT NOT NULL DEFAULT 'member'
                    CHECK (role IN ('owner','admin','member')),
    status          TEXT NOT NULL DEFAULT 'invited'
                    CHECK (status IN ('invited','active','suspended','removed')),
    password_hash   TEXT,                 -- argon2id; NULL until first login
    mfa_secret_enc  BYTEA,                -- envelope-encrypted, never plaintext
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, email)
);
CREATE INDEX users_tenant_idx ON users(tenant_id) WHERE status <> 'removed';

CREATE TABLE plans (
    sku             TEXT PRIMARY KEY,        -- 'ws-essentials-annual', …
    name            TEXT NOT NULL,
    tier            TEXT NOT NULL CHECK (tier IN ('essentials','collaborate','complete')),
    interval        TEXT NOT NULL CHECK (interval IN ('month','year')),
    unit_amount     INTEGER NOT NULL,        -- CAD cents per seat per interval
    currency        CHAR(3) NOT NULL DEFAULT 'cad',
    stripe_price_id TEXT NOT NULL UNIQUE,    -- authority for live charges
    active          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE subscriptions (
    id                      BIGSERIAL PRIMARY KEY,
    tenant_id               BIGINT NOT NULL REFERENCES tenants(id),
    plan_sku                TEXT NOT NULL REFERENCES plans(sku),
    seats                   INTEGER NOT NULL CHECK (seats BETWEEN 1 AND 500),
    status                  TEXT NOT NULL,   -- mirrors Stripe subscription status
    stripe_subscription_id  TEXT UNIQUE,
    stripe_item_id          TEXT,
    current_period_start    TIMESTAMPTZ,
    current_period_end      TIMESTAMPTZ,
    cancel_at_period_end    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX subs_one_active_per_tenant
    ON subscriptions(tenant_id)
    WHERE status IN ('trialing','active','past_due');

CREATE TABLE invoices (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES tenants(id),
    stripe_invoice_id   TEXT NOT NULL UNIQUE,
    subtotal            INTEGER NOT NULL,    -- cents, pre-tax
    tax                 INTEGER NOT NULL DEFAULT 0,
    total               INTEGER NOT NULL,
    currency            CHAR(3) NOT NULL DEFAULT 'cad',
    status              TEXT NOT NULL,
    hosted_invoice_url  TEXT,
    period_start        TIMESTAMPTZ,
    period_end          TIMESTAMPTZ,
    paid_at             TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE domains (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    domain          TEXT NOT NULL UNIQUE,
    verified_at     TIMESTAMPTZ,
    verify_token    TEXT NOT NULL,
    mx_ok           BOOLEAN NOT NULL DEFAULT FALSE,
    spf_ok          BOOLEAN NOT NULL DEFAULT FALSE,
    dkim_ok         BOOLEAN NOT NULL DEFAULT FALSE,
    dmarc_ok        BOOLEAN NOT NULL DEFAULT FALSE,
    last_checked_at TIMESTAMPTZ
);

-- Append-only. Same contract as the existing `events` ledger.
CREATE TABLE workspace_events (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT REFERENCES tenants(id),
    actor           TEXT NOT NULL,           -- 'user:<uuid>' | 'system' | 'stripe'
    action          TEXT NOT NULL,
    risk_score      SMALLINT NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ws_events_tenant_time ON workspace_events(tenant_id, created_at DESC);
REVOKE UPDATE, DELETE ON workspace_events FROM PUBLIC;

CREATE TABLE webhook_deliveries (
    stripe_event_id TEXT PRIMARY KEY,        -- idempotency: PK collision = replay
    type            TEXT NOT NULL,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at    TIMESTAMPTZ,
    outcome         TEXT
);
```

### Entitlements, commerce and consent (`007_workspace_commerce.sql`)

```sql
-- ── Entitlements ──────────────────────────────────────────────────────────
CREATE TABLE features (
    key         TEXT PRIMARY KEY,            -- 'video_meetings', 'desktop_apps', …
    name        TEXT NOT NULL,
    description TEXT,
    metered     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE plan_features (
    plan_sku    TEXT NOT NULL REFERENCES plans(sku) ON DELETE CASCADE,
    feature_key TEXT NOT NULL REFERENCES features(key) ON DELETE CASCADE,
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    limit_value INTEGER,                     -- NULL = unlimited (e.g. storage GB)
    PRIMARY KEY (plan_sku, feature_key)
);

-- Entitlement is DERIVED from (subscription.plan_sku → plan_features), never
-- stored per tenant. A cached copy is the classic way a cancelled customer keeps
-- premium access forever.
CREATE VIEW tenant_entitlements AS
SELECT s.tenant_id, pf.feature_key, pf.enabled, pf.limit_value
FROM subscriptions s
JOIN plan_features pf ON pf.plan_sku = s.plan_sku
WHERE s.status IN ('trialing', 'active', 'past_due');

CREATE TABLE roles (
    key         TEXT PRIMARY KEY,            -- 'owner','admin','member'
    name        TEXT NOT NULL,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb
);

-- ── Billing detail ────────────────────────────────────────────────────────
CREATE TABLE subscription_items (
    id                  BIGSERIAL PRIMARY KEY,
    subscription_id     BIGINT NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    stripe_item_id      TEXT UNIQUE,
    plan_sku            TEXT NOT NULL REFERENCES plans(sku),
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE payments (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           BIGINT NOT NULL REFERENCES tenants(id),
    invoice_id          BIGINT REFERENCES invoices(id),
    stripe_charge_id    TEXT UNIQUE,
    stripe_pi_id        TEXT,
    amount              INTEGER NOT NULL,    -- cents
    currency            CHAR(3) NOT NULL DEFAULT 'cad',
    status              TEXT NOT NULL,       -- succeeded|failed|refunded|disputed
    card_brand          TEXT,                -- display only, from Stripe
    card_last4          CHAR(4),             -- display only. NOT a PAN
    failure_code        TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tax_records (
    id              BIGSERIAL PRIMARY KEY,
    invoice_id      BIGINT NOT NULL REFERENCES invoices(id),
    jurisdiction    TEXT NOT NULL,           -- 'CA-ON'
    tax_type        TEXT NOT NULL,           -- 'HST','GST','PST','QST'
    rate_bps        INTEGER NOT NULL,        -- 1300 = 13.00%
    taxable_amount  INTEGER NOT NULL,
    tax_amount      INTEGER NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX tax_records_juris_time ON tax_records(jurisdiction, created_at);

CREATE TABLE coupons (
    code                TEXT PRIMARY KEY,
    stripe_coupon_id    TEXT NOT NULL UNIQUE,
    kind                TEXT NOT NULL CHECK (kind IN ('percent','amount')),
    value               INTEGER NOT NULL,    -- bps if percent, cents if amount
    duration            TEXT NOT NULL CHECK (duration IN ('once','repeating','forever')),
    duration_months     INTEGER,
    max_redemptions     INTEGER,
    redemption_count    INTEGER NOT NULL DEFAULT 0,
    expires_at          TIMESTAMPTZ,
    affiliate_id        BIGINT,              -- FK added below
    approved_by         TEXT NOT NULL,       -- approvals row id — never NULL
    active              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE trials (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    plan_sku        TEXT NOT NULL REFERENCES plans(sku),
    seats           INTEGER NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ends_at         TIMESTAMPTZ NOT NULL,
    outcome         TEXT CHECK (outcome IN ('converted','cancelled','expired')),
    outcome_at      TIMESTAMPTZ,
    UNIQUE (tenant_id, started_at)
);

-- ── Partners ──────────────────────────────────────────────────────────────
CREATE TABLE affiliates (
    id                  BIGSERIAL PRIMARY KEY,
    public_id           UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    email               TEXT NOT NULL UNIQUE,
    kind                TEXT NOT NULL CHECK (kind IN ('affiliate','referral_partner')),
    commission_bps      INTEGER NOT NULL,
    agreement_signed_at TIMESTAMPTZ,         -- no payout without this
    payout_method       TEXT,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','active','suspended','terminated')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE coupons ADD CONSTRAINT coupons_affiliate_fk
    FOREIGN KEY (affiliate_id) REFERENCES affiliates(id);

CREATE TABLE referrals (
    id              BIGSERIAL PRIMARY KEY,
    affiliate_id    BIGINT NOT NULL REFERENCES affiliates(id),
    tenant_id       BIGINT REFERENCES tenants(id),
    code            TEXT NOT NULL,
    landed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    converted_at    TIMESTAMPTZ,
    commission_amt  INTEGER,                 -- cents, computed at conversion
    paid_at         TIMESTAMPTZ,
    clawed_back_at  TIMESTAMPTZ,             -- refund/chargeback within window
    UNIQUE (affiliate_id, tenant_id)
);

-- ── Digital products ──────────────────────────────────────────────────────
CREATE TABLE digital_products (
    sku             TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT,
    stripe_price_id TEXT NOT NULL UNIQUE,    -- price authority, same as plans
    amount          INTEGER NOT NULL,        -- display/mock only
    currency        CHAR(3) NOT NULL DEFAULT 'cad',
    file_key        TEXT NOT NULL,           -- object-storage key, never public
    license_terms   TEXT NOT NULL,
    active          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE orders (
    id                  BIGSERIAL PRIMARY KEY,
    public_id           UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tenant_id           BIGINT REFERENCES tenants(id),   -- NULL = guest purchase
    email               TEXT NOT NULL,
    stripe_session_id   TEXT UNIQUE,
    subtotal            INTEGER NOT NULL,
    tax                 INTEGER NOT NULL DEFAULT 0,
    total               INTEGER NOT NULL,
    currency            CHAR(3) NOT NULL DEFAULT 'cad',
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','paid','refunded','failed')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE order_items (
    id          BIGSERIAL PRIMARY KEY,
    order_id    BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    sku         TEXT NOT NULL REFERENCES digital_products(sku),
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_amount INTEGER NOT NULL             -- resolved server-side at purchase
);

CREATE TABLE download_grants (
    id              BIGSERIAL PRIMARY KEY,
    order_id        BIGINT NOT NULL REFERENCES orders(id),
    sku             TEXT NOT NULL REFERENCES digital_products(sku),
    token           TEXT NOT NULL UNIQUE,
    max_downloads   INTEGER NOT NULL DEFAULT 5,
    download_count  INTEGER NOT NULL DEFAULT 0,
    expires_at      TIMESTAMPTZ NOT NULL,
    UNIQUE (order_id, sku)
);

-- ── Support ───────────────────────────────────────────────────────────────
CREATE TABLE support_tickets (
    id              BIGSERIAL PRIMARY KEY,
    public_id       UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tenant_id       BIGINT REFERENCES tenants(id),
    opened_by       BIGINT REFERENCES users(id),
    subject         TEXT NOT NULL,
    priority        TEXT NOT NULL DEFAULT 'normal'
                    CHECK (priority IN ('low','normal','high','urgent')),
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','pending','resolved','closed')),
    assigned_to     TEXT,                    -- §26 role key
    first_reply_at  TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE support_messages (
    id          BIGSERIAL PRIMARY KEY,
    ticket_id   BIGINT NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    author      TEXT NOT NULL,               -- 'user:<uuid>' | 'staff:<id>'
    body        TEXT NOT NULL,
    internal    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Consent & automation ──────────────────────────────────────────────────
-- Append-only. Current state is the latest row per (email, channel).
CREATE TABLE marketing_consent (
    id              BIGSERIAL PRIMARY KEY,
    email           TEXT NOT NULL,
    tenant_id       BIGINT REFERENCES tenants(id),
    channel         TEXT NOT NULL CHECK (channel IN ('newsletter','product_updates',
                                                     'offers','analytics_cookies',
                                                     'retargeting_cookies')),
    granted         BOOLEAN NOT NULL,
    basis           TEXT NOT NULL CHECK (basis IN ('express','implied')),
    source          TEXT NOT NULL,           -- 'signup_form','cookie_banner',…
    notice_version  TEXT NOT NULL,           -- which policy text they saw
    ip              INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX consent_lookup ON marketing_consent(email, channel, created_at DESC);
REVOKE UPDATE, DELETE ON marketing_consent FROM PUBLIC;

CREATE TABLE automation_events (
    id              BIGSERIAL PRIMARY KEY,
    automation_key  TEXT NOT NULL,           -- 'A5','A12', … from §13
    tenant_id       BIGINT REFERENCES tenants(id),
    dedupe_key      TEXT NOT NULL,
    risk_score      SMALLINT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued','awaiting_approval','executed',
                                      'failed','cancelled')),
    approval_id     BIGINT,                  -- required when risk_score >= 70
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    scheduled_for   TIMESTAMPTZ,
    executed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (automation_key, dedupe_key)      -- an automation fires once per subject
);

CREATE TABLE sessions (
    id              TEXT PRIMARY KEY,        -- opaque, high-entropy
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id       BIGINT NOT NULL REFERENCES tenants(id),
    ip              INET,
    user_agent      TEXT,
    mfa_satisfied   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ
);
CREATE INDEX sessions_user ON sessions(user_id) WHERE revoked_at IS NULL;
```

**Three schema decisions worth defending**

- **`tenant_entitlements` is a view, not a table.** Entitlement is derived from
  the live subscription every time it is checked. A materialised per-tenant
  entitlement row is how a cancelled customer keeps paid features indefinitely —
  the cache outlives the subscription and nobody notices until an audit.
- **`marketing_consent` and `automation_events` are append-only**, like the audit
  ledger. Consent is a legal record; overwriting it destroys the only evidence
  that CASL asks you to produce.
- **`automation_events` has `UNIQUE (automation_key, dedupe_key)`.** This is what
  stops a retry loop from sending the same customer eleven "final notice" emails.
  Every automation must supply a dedupe key derived from its subject, not a
  timestamp.

**Schema rules, non-negotiable**

- **No card data. Ever.** There is no column for a PAN, CVC, expiry or
  cardholder name, and there must never be one. The only payment identifiers
  stored are Stripe tokens (`cus_…`, `sub_…`, `in_…`). Adding a card column would
  move this business from PCI SAQ A into SAQ D and is grounds for reverting the
  migration.
- **`tenants` and `users` use `ON DELETE RESTRICT`.** Customer records are never
  cascade-deleted by an application bug; purging is a deliberate, logged job.
- **Every mutation writes to `workspace_events`** with a risk score, matching the
  existing audit ledger contract in `app/audit.py`.
- **`mfa_secret_enc` is envelope-encrypted** with a KMS-held key, not stored as
  a plaintext TOTP secret.
- **Tenant isolation is enforced at the query layer** — every workspace query
  filters on `tenant_id` from the session, never from a request parameter (§15,
  T4).

---

## 10. API design

FastAPI, mounted alongside the existing control plane. Same conventions:
`require_admin` on mutating admin routes, server-side price authority, audit
ledger on every material change.

### Public / customer

| Method | Path | Auth | Notes |
|---|---|---|---|
| `GET` | `/workspace/plans` | none | Plan catalogue. Read-only, cacheable |
| `POST` | `/workspace/trial` | none + rate limit | Starts trial. Body: `{plan_sku, seats, email, org_name, domain}`. **No amount field** |
| `POST` | `/workspace/checkout/session` | none + rate limit | Body: `{plan_sku, seats}` only. Amount resolved server-side from the price book |
| `POST` | `/workspace/webhook/stripe` | signature | Signature-verified, idempotent on `stripe_event_id` |
| `GET` | `/workspace/me` | session | Current tenant, plan, seats, period end |
| `POST` | `/workspace/portal` | session | Returns a Stripe Billing Portal URL for card/invoice self-service |
| `GET` | `/ready` | none | DB reachability (already exists) |

### Tenant admin (owner/admin role, tenant-scoped)

| Method | Path | Notes |
|---|---|---|
| `GET` | `/workspace/users` | Users in the caller's tenant only |
| `POST` | `/workspace/users` | Invite. Triggers a seat increase if at capacity |
| `DELETE` | `/workspace/users/{id}` | Suspend + schedule purge. Never immediate deletion |
| `POST` | `/workspace/seats` | `{delta}`. Pro-rata via Stripe |
| `POST` | `/workspace/plan` | `{plan_sku}`. Upgrade immediate, downgrade at period end |
| `POST` | `/workspace/domains` | Add domain, returns the verification token |
| `GET` | `/workspace/domains/{id}/status` | MX/SPF/DKIM/DMARC check results |
| `GET` | `/workspace/export` | Async job → signed, time-limited download |
| `POST` | `/workspace/cancel` | One call, no retention gate |
| `POST` | `/workspace/pause` | Pause up to 3 months; access read-only, billing stops |
| `POST` | `/workspace/reactivate` | Resume a paused or recently-cancelled tenant |
| `GET` | `/workspace/entitlements` | Derived from the live subscription, never cached |
| `GET` | `/workspace/invoices` | List + `hosted_invoice_url` per invoice |
| `GET` | `/workspace/activity` | Account + security event log for this tenant |
| `GET`/`PUT` | `/workspace/preferences` | Notification + marketing consent. Writes append to `marketing_consent` |
| `POST` | `/workspace/tickets` | Open a support ticket |
| `GET` | `/workspace/tickets/{id}` | Ticket + non-internal messages |

### Commerce (digital products, C7)

| Method | Path | Auth | Notes |
|---|---|---|---|
| `GET` | `/products` | none | Catalogue |
| `POST` | `/products/checkout/session` | none + rate limit | Body `{items:[{sku, quantity}]}`. **No amounts** |
| `GET` | `/downloads/{token}` | token | Signed, expiring, download-count limited |
| `POST` | `/promo/validate` | none + rate limit | Code string in, `{valid, description}` out. **Never returns the computed discount** — Stripe applies it |
| `GET` | `/r/{code}` | none | Affiliate/referral landing. Sets a first-party attribution cookie **only after consent** |

### Staff (`require_admin`, `ADMIN_API_KEY`)

| Method | Path | Governance |
|---|---|---|
| `GET` | `/admin/workspace/tenants` | read-only, low risk |
| `GET` | `/admin/workspace/tenants/{id}` | read-only |
| `POST` | `/admin/workspace/tenants/{id}/suspend` | **high** → approval required |
| `POST` | `/admin/workspace/tenants/{id}/credit` | **critical** → approval required |
| `POST` | `/admin/workspace/tenants/{id}/purge` | **critical** → approval + 2 notices |
| `POST` | `/admin/workspace/plans/{sku}/price` | **critical** → approval required |
| `GET` | `/admin/workspace/events` | audit ledger, read-only |
| `POST` | `/admin/workspace/refunds` | **critical** → approval required |
| `POST` | `/admin/workspace/coupons` | **critical** → approval required (a coupon is a price) |
| `POST` | `/admin/workspace/affiliates/{id}/approve` | **high** → approval; blocked until `agreement_signed_at` is set |
| `POST` | `/admin/workspace/affiliates/payouts` | **critical** → approval required |
| `GET` | `/admin/workspace/tickets` | read-only queue |
| `POST` | `/admin/workspace/tickets/{id}/reply` | medium → auto, audited |
| `POST` | `/admin/workspace/campaigns/send` | **critical** → approval; bulk outbound is `ALWAYS_ESCALATE` |
| `GET` | `/admin/workspace/reports/tax` | read-only, from `tax_records` |
| `GET` | `/admin/workspace/reports/revenue` | MRR/ARR/churn/LTV/CAC, read-only |
| `GET` | `/admin/workspace/fraud` | read-only alert queue |

### Cross-cutting contracts

- **Price authority.** No request body on any route carries an amount, a price,
  a discount or a currency. `test_pricebook.py` asserts the OpenAPI schema for
  checkout line items is exactly `{sku, quantity}` — the equivalent assertion
  must be added for `/workspace/checkout/session`.
- **No caller-supplied redirect URLs.** `success_url` and `cancel_url` are
  server-side constants. A caller-supplied redirect on a checkout route is a
  phishing primitive; it was removed from the existing checkout schemas for
  exactly this reason and must not come back.
- **Route auth coverage is a test, not a convention.**
  `tests/test_route_auth_coverage.py` must be extended so every new mutating
  workspace route is behind `require_admin`, behind a tenant session, or on a
  justified allow-list.
- **Rate limits** on `/workspace/trial`, `/workspace/checkout/session`,
  `/workspace/webhook/stripe` and login, per IP and per email.
- **Errors** return a stable `{error: {code, message}}` shape. Never leak whether
  an email exists on signup or password reset (user enumeration, §15 T6).
- **Idempotency.** Every Stripe write sends an `Idempotency-Key`. Every webhook
  is deduplicated on `stripe_event_id`.

---

## 11. System architecture

```
                          ┌─────────────────────────────────┐
     Customer browser ───▶│  GitHub Pages (static)          │
                          │  workspace.html, pricing, legal │
                          └───────────────┬─────────────────┘
                                          │ HTTPS
                          ┌───────────────▼─────────────────┐
                          │  app.clearglassinc.com          │
                          │  Next.js — signup, dashboard,   │
                          │  tenant admin                   │
                          └───────────────┬─────────────────┘
                                          │ JSON over HTTPS
                          ┌───────────────▼─────────────────┐
                          │  Control plane (FastAPI)        │
                          │  ┌───────────────────────────┐  │
                          │  │ governance.py  0–100 risk │  │
                          │  │ security.py  require_admin│  │
                          │  │ pricebook.py  price auth  │  │
                          │  │ audit.py  append-only     │  │
                          │  └───────────────────────────┘  │
                          └──┬────────┬────────┬────────────┘
                             │        │        │
              ┌──────────────▼┐  ┌────▼─────┐  ▼──────────────┐
              │ PostgreSQL    │  │ Stripe   │  │ Redis         │
              │ tenants,users │  │ (tokens  │  │ queues, rate  │
              │ subs, events  │  │  only)   │  │ limits, cache │
              └───────────────┘  └──────────┘  └──────┬───────┘
                                                      │
                                          ┌───────────▼───────────┐
                                          │ Background workers    │
                                          │ provisioning, billing,│
                                          │ automation, exports   │
                                          └───────────┬───────────┘
                                                      │
        ┌──────────────┬──────────────┬───────────────┼──────────┬─────────────┐
        ▼              ▼              ▼               ▼          ▼             ▼
  Mail platform   Object storage   Calendar       Meetings   Transactional  Monitoring
  (MX/SPF/DKIM)   (encrypted,      (CalDAV)       (SFU)      email          logs, errors,
                   versioned)                                provider       alerts, uptime
```

### Stack

| Layer | Technology | Note |
|---|---|---|
| Marketing site | Static HTML/CSS/JS on GitHub Pages | Already deployed |
| Web app | **Next.js + TypeScript** | Matches the brief and the existing `storefront`/`admin` apps in this repo |
| App API | Next.js route handlers (Node runtime) for session, dashboard and product reads | Co-located with the UI; nothing money-shaped |
| Control plane | **FastAPI (Python)** — billing, entitlements, governance, audit | See the deviation note below |
| Database | PostgreSQL 16, single primary + read replica, PITR | |
| Queue / cache / rate limit | **Redis** | Durable queues for workers; token-bucket rate limits; short-TTL cache. Never the source of truth |
| Workers | Node or Python consumers off Redis streams | Idempotent, retried with backoff, dead-letter queue |
| Payments | Stripe (Checkout, Billing, Tax, Billing Portal) | |
| Transactional email | Dedicated provider, separate subdomain + DKIM from customer mail | Isolates your sending reputation from customers' |
| Object storage | S3-compatible, versioned, encrypted, **no public buckets** | Digital products and exports served by signed expiring URL |
| Monitoring | Uptime checks on `/ready`, structured logs, error tracking, alert routing to on-call | |
| CI/CD | GitHub Actions — lint, tests, `tsc --noEmit`, `next build`, dependency + secret scanning | Extends the existing workflows |
| IaC | Terraform for infrastructure, `docker-compose` for local | Every environment reproducible from code |
| Secrets | Runtime secret manager; nothing in git | Quarterly rotation |

**Deviation from the brief, stated plainly.** The brief specifies Node/serverless
for the API. The money paths — price authority, governance scoring, the approval
gate and the audit ledger — already exist, tested, in the Python control plane in
this repo, and they are enforced by CI gates that would have to be rebuilt from
scratch in Node. Rewriting them would trade a working, test-enforced safety model
for a language preference. **Recommendation: Next.js/TypeScript for everything
customer-facing, Python control plane for anything that touches money or
governance.** If a single-language stack matters more than the existing gates,
that is a legitimate call — but it is a rewrite of §12, §13 and §15's controls,
not a configuration change, and it should be scheduled as one.

### Web application security baseline

| Control | Implementation |
|---|---|
| Security headers | HSTS (preload), CSP with no `unsafe-inline`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` |
| CSRF | SameSite=Lax cookies + per-session token on state-changing form posts |
| Input validation | Schema validation at the boundary (Pydantic / Zod). Reject unknown fields — never ignore them |
| Output encoding | Framework auto-escaping; no `dangerouslySetInnerHTML` on user content |
| Rate limiting | Redis token bucket per IP **and** per account on auth, checkout, webhook, promo validation |
| Bot / abuse | Proof-of-work or CAPTCHA on signup after threshold; velocity checks on card attempts |
| Sessions | Opaque high-entropy ids in `sessions`, HttpOnly + Secure cookies, idle and absolute timeouts, revocable from `/dashboard/security` |
| Passwords | argon2id, breach-list check on set, no composition rules that push people to `Password1!` |

**Decisions and why**

| Decision | Choice | Rationale |
|---|---|---|
| Marketing site | Static, GitHub Pages | Already deployed, zero cost, no attack surface |
| App | Separate origin `app.clearglassinc.com` | Cookie isolation from the marketing site; a static-site XSS cannot reach a session cookie |
| Backend | Extend the existing FastAPI control plane | Governance, audit ledger, price book and admin auth already exist and are test-enforced. A second backend would fork the safety model |
| Database | PostgreSQL, single primary + PITR | Relational integrity matters more than scale here |
| Payments | Stripe Checkout + Billing Portal (hosted) | Keeps ClearGlass in PCI SAQ A. Subscriptions, proration, dunning, tax and invoicing are Stripe's problem, not a build |
| Provisioning | Async worker off a durable queue | Mailbox creation must survive a webhook timeout and be retried idempotently |
| Secrets | Runtime env vars / secret manager | Nothing in git. `APP_ENV=production` with no `ADMIN_API_KEY` already fails closed at startup |

**Failure posture.** Fail closed. If the price book cannot be read, checkout
returns 503 rather than guessing. If Stripe Tax is unavailable in live mode,
checkout returns 503 rather than under-charging tax — this pattern already exists
in `routers/sidestore.py` and should be copied verbatim.

---

## 12. Payment & webhook design

### Model

**Stripe Checkout in `subscription` mode**, plus the **Stripe Billing Portal**
for card updates, invoice history and cancellation. Not Payment Intents — this is
recurring billing with proration, dunning and tax, all of which Stripe Billing
implements correctly and a hand-rolled Payment Intent flow does not. Not Elements
— hosting the card field would pull ClearGlass from PCI SAQ A into SAQ A-EP for
no gain.

### Card-data position

ClearGlass **never sees, transmits or stores a card number, CVC or expiry.** Card
entry happens on Stripe's domain. The only artefacts that reach ClearGlass are
opaque tokens (`cus_…`, `sub_…`, `in_…`, `pm_…`). This is asserted on the pricing
page, must remain true in the schema (§9), and is the basis of the PCI position
in §16.

### Configuration

| Setting | Value |
|---|---|
| Mode | `subscription` |
| Trial | `trial_period_days: 14`, `payment_method_collection: always` |
| Tax | `automatic_tax: {enabled: true}` — Stripe Tax computes GST/HST from billing address |
| Tax code | `txcd_10103000` (SaaS) — confirm with the accountant before go-live |
| Tax behaviour | `exclusive` (prices shown pre-tax, as the page states) |
| Line items | `{price: <stripe_price_id>, quantity: <seats>}` — never `price_data` |
| Proration | `create_prorations` on seat and plan changes |
| Idempotency | `Idempotency-Key` on every write |
| `client_reference_id` | tenant `public_id`, so the webhook can resolve the tenant |
| Redirects | Server-side constants only |
| Portal | Card update + invoice history + cancel enabled; plan switching disabled (handled in-app so provisioning stays in step) |

### Webhooks to configure

| Event | Action | Idempotency |
|---|---|---|
| `checkout.session.completed` | Create/attach subscription, set `trialing`, enqueue provisioning | `stripe_event_id` PK |
| `customer.subscription.created` | Persist subscription + item ids | same |
| `customer.subscription.updated` | Sync seats, plan, status, period end; adjust provisioning | same |
| `customer.subscription.deleted` | `cancelled`; schedule 30-day purge; send export link | same |
| `customer.subscription.trial_will_end` | Send T3 (3 days out) | same |
| `invoice.paid` / `invoice.payment_succeeded` | Persist invoice, set `active`, send receipt | same |
| `invoice.payment_failed` | Enter dunning (§8.4) | same |
| `invoice.finalized` | Store `hosted_invoice_url` for the customer's records | same |
| `charge.dispute.created` | Freeze automated changes, alert staff, **never auto-refund** | same |
| `charge.refunded` | Reconcile ledger | same |

### Webhook handling rules

1. **Verify the signature first.** `stripe.Webhook.construct_event` with the
   endpoint secret, before parsing the body. An unsigned or badly-signed request
   is a 400 and an audit entry — it is not a payload to inspect.
2. **Insert into `webhook_deliveries` before processing.** A PK collision means
   this is a replay: return 200 and do nothing. Stripe retries aggressively; a
   non-idempotent handler double-provisions or double-credits.
3. **Return 200 fast, work asynchronously.** Handlers acknowledge and enqueue.
   Stripe times out at 20 seconds and a slow handler manufactures its own
   retry storm.
4. **Never trust the body over the API.** For anything money-shaped, re-read the
   object from Stripe by id rather than trusting the embedded copy.
5. **Never mutate price from a webhook.** Prices change in the price book and in
   Stripe, both behind approval (§10).
6. **Audit every webhook** to `workspace_events` with actor `stripe`.
7. **Commit before raising.** A validation failure that returns 400 must still
   persist its audit row — the session rolls back on an unhandled exception, and
   losing the record of a rejected event is worse than the rejection.

### Validation checklist before the first live charge

- [ ] Test-mode: trial signup → card collected → **no charge**
- [ ] Test-mode: trial converts on day 14 with a clock-advanced test clock
- [ ] Test-mode: seat +1 and −1 produce correct proration lines
- [ ] Test-mode: `4000000000000341` (attaches but fails) drives the full dunning sequence
- [ ] Test-mode: dispute event freezes automation and alerts, with no auto-refund
- [ ] Replay every webhook twice — assert exactly-once effects
- [ ] Tamper a webhook signature — assert 400 + audit row
- [ ] Send `{plan_sku, seats, unit_amount: 1}` — assert the extra field is rejected, not honoured
- [ ] Confirm GST/HST appears on an Ontario invoice at 13% and is itemised
- [ ] Confirm `success_url` cannot be influenced by the caller
- [ ] Live-mode smoke: one real $6.00 seat, verify receipt and invoice, then refund it

---

## 13. Automation map

| # | Trigger | Automation | Risk | Governance |
|---|---|---|---|---|
| A1 | `checkout.session.completed` | Create tenant, enqueue provisioning | 25 | auto |
| A2 | Provisioning job | Create mailboxes, storage quota, calendar | 35 | auto, audited |
| A3 | Domain added | Poll MX/SPF/DKIM/DMARC every 15 min for 48 h | 10 | auto |
| A4 | `trial_will_end` | Send T3 | 15 | auto |
| A5 | `invoice.payment_failed` | Dunning sequence T7a–c | 30 | auto |
| A6 | Day 10 past due | Downgrade to read-only | 55 | auto, notified |
| A7 | Day 24 past due | Suspend access | 75 | **approval** |
| A8 | Day 54 suspended | Purge data | 95 | **approval + 2 notices** |
| A9 | Seat change | Update Stripe quantity, provision/deprovision | 40 | auto, audited |
| A10 | Plan upgrade | Immediate, pro-rata | 40 | auto |
| A11 | Plan downgrade | Queued to period end | 40 | auto |
| A12 | Monthly | Revenue + churn + MRR report to owner | 10 | auto |
| A13 | Daily | Backup verification + restore drill sample | 20 | auto |
| A14 | Weekly | Deliverability check on outbound mail | 20 | auto |
| A15 | Any price change | — | 95 | **approval, always** |
| A16 | Any refund or credit | — | 90 | **approval, always** |
| A17 | Any bulk outbound email | — | 92 | **approval, always** |
| A18 | Quarterly | Check-in email to active tenants | 25 | draft → approval |
| A19 | Checkout abandoned > 4 h | One reminder, **only** with prior consent, once per 30 days | 45 | approval (first send), then auto |
| A20 | Cancellation submitted | Optional one-question exit survey, sent after cancellation completes | 20 | auto |
| A21 | 60 days after cancellation | Win-back offer — **only** to addresses with live consent | 50 | approval |
| A22 | Ticket created | Route by plan + keyword to the §26 role; SLA clock starts | 15 | auto |
| A23 | Consultation form submitted | Qualify (seats, current provider, timeline), route, acknowledge in 1 h | 20 | auto |
| A24 | Enterprise enquiry (50+ seats) | Draft a quote from the §4 matrix; **never send unreviewed** | 70 | **approval** |
| A25 | Referral code redeemed | Attribute, compute commission, hold for the 60-day clawback window | 30 | auto, audited |
| A26 | Invoice finalized | Store PDF + URL; file to the accounting export | 15 | auto |
| A27 | Quarter end | Assemble GST/HST report from `tax_records` for the CPA | 25 | auto, human-filed |
| A28 | 14 days after a completed onboarding | Ask that **verified customer** for a review. One ask, no reminders | 30 | auto |
| A29 | Content published | Ping sitemap, refresh internal links, bump `sw.js` VERSION | 15 | auto |
| A30 | Weekly | SEO monitoring — rankings, Search Console, broken links, CWV | 10 | auto |
| A31 | Payment anomaly (velocity, mismatched geo, repeated declines) | Flag for review; **never auto-block a paying customer** | 60 | approval to act |
| A32 | High-value signup, payment failure, or churn > threshold | Internal alert to the owner within minutes | 10 | auto |
| A33 | Digital product purchased | Issue a signed, expiring, count-limited download grant | 20 | auto |

### Automation rules that override any individual row

1. **Consent is checked at send time, not at queue time.** An unsubscribe between
   queueing and sending must suppress the message. Query `marketing_consent` in
   the sender, not the scheduler.
2. **Transactional and marketing are separate code paths.** Unsubscribing from
   marketing must never suppress a receipt, a dunning notice, or a security
   alert. If one function can send both, that is the bug.
3. **Every automation is deduplicated** on `(automation_key, dedupe_key)` (§9).
   A retry loop that sends eleven "final notice" emails is not a bug you get to
   apologise for once.
4. **Frequency cap:** no more than 2 marketing messages per address per month
   across all automations combined, counted centrally — not per campaign.
5. **A19 is the one to be most careful with.** Abandoned-checkout mail to someone
   who never consented is a CASL commercial electronic message. Send it only to
   addresses with a documented consent basis, and only once.
6. **A28 asks; it never incentivises.** Paying for a review, or asking only the
   customers you expect to be happy, produces a review corpus that is not
   evidence of anything. One ask, to everyone, after a real completed
   engagement.
7. **A31 flags, it does not block.** Automated fraud blocking on a small customer
   base produces more false positives than fraud caught, and a wrongly locked-out
   business is a customer you have lost.

The risk scores map onto the existing `governance.py` bands: **low** (0–39)
auto-executes and logs, **medium** (40–69) queues an approval, **high/critical**
(70–100) blocks until an `approvals` row reaches `approved`. A17 sits in
`ALWAYS_ESCALATE` deliberately — a bug that mails every customer is not
recoverable by apology, and CASL attaches statutory penalties to it.

---

## 14. Admin dashboard spec

### 14.0 Customer dashboard (tenant-facing) — for contrast

Before the staff portal, the customer's own view. Different audience, different
rule: **every screen answers a question the customer would otherwise email
about.**

| Screen | Shows | Can do |
|---|---|---|
| Overview | Active plan, seats in use vs paid, next renewal date and amount, trial days left | Jump to any action below |
| Team | Members, roles, invitation status, last activity | Invite, remove, change role, resend invite |
| Usage & entitlements | Which features their plan includes, storage used vs limit | See what an upgrade would add — stated, not teased |
| Billing | Invoices with downloadable PDFs, payment method (brand + last 4 only), billing address | Upgrade, downgrade, switch monthly↔annual, open the Stripe portal |
| Subscription | Plan, seats, billing period, renewal | **Pause**, cancel, reactivate — each one click, no retention maze |
| Security | Active sessions with IP and last-seen, MFA status, recent account activity | Revoke a session, reset MFA, change password |
| Preferences | Notification settings, marketing consent per channel, cookie choices | Opt in or out per channel, effective immediately |
| Support | Open tickets, history, SLA for their plan | Open a ticket, reply, close |

**Design rules.** No feature is shown as available and then blocked at click —
entitlements gate the UI honestly. No dark patterns anywhere in this list: cancel
is a button, not a maze; downgrade is as prominent as upgrade; the marketing
opt-out is not pre-ticked in the direction that suits us.

---

### Staff admin portal

Staff-only, behind `require_admin` + `ADMIN_API_KEY`, served on a separate path
from tenant admin.

### Screens

1. **Overview** — active tenants, seats, MRR, ARR, trials in flight, trial→paid
   conversion, logo and revenue churn, failed payments needing attention. Every
   figure links to the query behind it; no number appears without a drill-down.
2. **Tenants** — searchable list (org, domain, plan, seats, status, MRR, next
   renewal). Detail view shows the full `workspace_events` timeline.
3. **Approvals** — the governance queue from §13. Each row: action, risk score,
   requesting actor, diff of what will change, approve/reject with a mandatory
   reason. Nothing high/critical executes without a row here reaching `approved`.
4. **Billing** — invoices, failed payments and dunning stage, disputes, refunds
   pending approval, monthly reconciliation of Stripe payouts against the ledger.
5. **Provisioning** — job queue, failures, retries, mailbox/storage state per
   tenant, DNS verification status.
6. **Audit** — append-only `workspace_events`, filterable by tenant, actor,
   action, risk band. Export to CSV for an accountant or auditor.
7. **Health** — `/ready`, database, queue depth, mail deliverability, backup
   recency, last successful restore drill.
8. **Plans & entitlements** — plan/feature matrix editor. Price fields are
   read-only here; changing one routes through the approval queue and Stripe.
9. **Trials** — trials in flight, days remaining, conversion likelihood signals
   (setup call booked? domain verified? users invited?), and which ones nobody
   has contacted.
10. **Coupons & promotions** — active codes, redemption counts, expiry, and the
    approval row that authorised each one. A code with no approval row is an
    incident, not a row.
11. **Support** — ticket queue by priority and SLA breach risk, first-response
    and resolution times, per-tenant history.
12. **Affiliates & referrals** — partners, agreement status (payouts blocked
    until `agreement_signed_at` is set), attributed conversions, commissions
    owed, clawbacks pending.
13. **Digital products** — catalogue, sales, download grants issued and consumed,
    refund requests.
14. **Marketing** — campaigns, consent counts by channel, unsubscribe rate,
    frequency-cap headroom. Sending is gated on an approval row (A17).
15. **Revenue** — MRR, ARR, ARPA, expansion/contraction, cohort retention,
    LTV, CAC, payback. Each figure links to its query.
16. **Churn & retention** — cancellations with survey reasons, at-risk tenants
    (no login, support escalations, failed payment history), win-back eligibility
    filtered by live consent.
17. **Tax reports** — GST/HST by jurisdiction and period from `tax_records`,
    exportable for the CPA. Read-only; the filing is a human act.
18. **Fraud & anomalies** — the A31 queue. Flags only, with an explicit
    act/dismiss decision that is logged either way.

### Rules

- **Read by default.** Every mutating control is a distinct, labelled action that
  writes an audit row with the acting staff member's identity.
- **No raw SQL console.** Ever.
- **Impersonation, if built at all,** is read-only, requires a stated reason,
  notifies the tenant owner by email, and expires in 30 minutes.
- **No card data displayed** — last four digits and brand only, straight from
  Stripe, never stored.
- **MFA required** on every staff account. No exceptions, including the owner.

---

## 15. Threat model

Assets: customer mail and files (highest), credentials, billing tokens, the price
book, the audit ledger, the domain/DNS configuration.

| # | Threat | Vector | Impact | Control |
|---|---|---|---|---|
| T1 | **Price tampering** | Caller submits an amount or discount | Charging $0.01 for a $17.00 seat | Server-side price authority; request schema is `{sku, quantity}` only; asserted in `test_pricebook.py` |
| T2 | **Forged webhook** | Attacker POSTs a fake `invoice.paid` | Free service, poisoned ledger | Mandatory signature verification before parsing; audit on failure |
| T3 | **Webhook replay** | Stripe retry or attacker resend | Double provisioning, double credit | `webhook_deliveries` PK on `stripe_event_id` |
| T4 | **Tenant isolation break (IDOR)** | Request supplies another tenant's id | One customer reads another's mail — business-ending | `tenant_id` always from the session, never the request; row-level checks; a dedicated cross-tenant test suite |
| T5 | **Admin auth bypass** | Unauthenticated mutating route | Full control-plane compromise | `require_admin`; `test_route_auth_coverage.py` fails the build if a mutating route is unguarded |
| T6 | **User enumeration** | Different responses for known/unknown emails | Targeted phishing of real customers | Identical response and timing on signup, login and reset |
| T7 | **Credential stuffing** | Reused passwords | Account takeover | argon2id, MFA, per-IP and per-account rate limits, breach-list check on set |
| T8 | **Open redirect / checkout phishing** | Caller-supplied `success_url` | Customers redirected to a credential harvester after paying | Redirects are server-side constants — already removed from the checkout schemas |
| T9 | **Mail relay abuse** | Compromised seat used to send spam | Domain and IP blocklisting; all customers lose deliverability | Outbound rate limits per mailbox, spam scoring, automatic suspension on threshold, SPF/DKIM/DMARC enforced |
| T10 | **Insider / staff misuse** | Staff reads customer mail | Trust and privacy breach | No standing data access; impersonation read-only, reasoned, notified, expiring; every access audited |
| T11 | **Backup exposure** | Unencrypted or public backup store | Full data breach | Encrypted at rest, separate credentials, restore drills, no public buckets |
| T12 | **DNS hijack at cutover** | Registrar account compromise | Mail interception | Registrar MFA + transfer lock; cutover is a two-person change |
| T13 | **Secrets in git** | Key committed | Account compromise | Secret scanning in CI; runtime-only env vars; the repo already runs secret scanning |
| T14 | **Ledger tampering** | Editing history to hide an action | Loss of the audit trail's meaning | `workspace_events` is append-only, `UPDATE`/`DELETE` revoked; matches the existing RFED hash-chain posture |
| T15 | **Supply chain** | Malicious dependency | Arbitrary code execution | Pinned dependencies, lockfiles, Dependabot, review of new direct deps |
| T16 | **Dispute / friendly fraud** | Chargeback after service delivered | Revenue loss + Stripe penalties | Clear descriptor, itemised invoices, delivery evidence, dispute automation freeze (§12) |

**Highest residual risk: T4.** Every other item on this list is recoverable. A
cross-tenant read of customer email is not — it is a reportable breach under
PIPEDA and it ends the business's credibility. Budget accordingly: automated
cross-tenant tests on every route, on every build.

---

## 16. Compliance checklist

> Have a qualified Ontario lawyer and a Canadian CPA review this section
> specifically. The items below are the agenda for those meetings, not a
> substitute for them.

### Corporate & tax
- [ ] ClearGlass Inc. in good standing; annual returns filed
- [ ] **GST/HST registration.** Mandatory once taxable supplies exceed $30,000 CAD over four consecutive calendar quarters. Voluntary registration before that lets you claim input tax credits — ask the CPA which is better given the infrastructure spend
- [ ] Stripe Tax configured for CAD/Canada; nexus and tax code (`txcd_10103000`) confirmed by the CPA
- [ ] HST itemised on every invoice with the business number
- [ ] **Deferred revenue treatment for annual prepayments** confirmed with the CPA (§5)
- [ ] Provincial obligations reviewed if customers exist outside Ontario
- [ ] Cross-border digital-services rules reviewed before the first non-Canadian customer

### Privacy
- [ ] **PIPEDA** compliance: identified purposes, meaningful consent, limited collection, safeguards, openness, individual access, accountability
- [ ] Named Privacy Officer with published contact details
- [ ] Privacy policy states what is collected, why, where it is stored, how long, and who it is shared with — reviewed against actual practice, not aspiration
- [ ] **Breach response plan** meeting PIPEDA's "real risk of significant harm" reporting duty to the Privacy Commissioner and affected individuals
- [ ] Records-of-breach register maintained (required whether or not reported)
- [ ] Data Processing Addendum available for P3-type customers (`legal/workspace-dpa.html`)
- [ ] Sub-processor list published and kept current
- [ ] Data residency stated honestly — including where it is *not* Canadian
- [ ] Retention schedule published; deletion actually happens on schedule
- [ ] Access and correction request procedure, with a stated response time

### Anti-spam (CASL)
- [ ] Express or documented implied consent before any commercial electronic message
- [ ] Consent records retained with source, date and method
- [ ] Every commercial message identifies ClearGlass Inc. with a physical mailing address
- [ ] Working unsubscribe in every message, honoured within 10 business days
- [ ] **Transactional messages** (receipts, dunning, security alerts) separated from marketing in code, so an unsubscribe never suppresses a security notice
- [ ] **No purchased, scraped or rented contact lists.** CASL penalties reach $10M for corporations; this is not a grey area

### Consumer protection
- [ ] Ontario *Consumer Protection Act, 2002* reviewed for auto-renewal and negative-option disclosure
- [ ] Post-trial charge disclosed before signup (done on `workspace.html`)
- [ ] Renewal reminder before annual renewals
- [ ] Cancellation as easy as signup — one click, no retention maze (§8.5)
- [ ] Refund policy published and honoured as written
- [ ] All prices shown as approximate and pre-tax, with what is excluded stated (done)

### Payments
- [ ] **PCI-DSS SAQ A** — valid only while card entry stays on Stripe's hosted page. Re-assess if the checkout ever moves in-house
- [ ] No PAN, CVC or expiry in any datastore, log, backup or support ticket
- [ ] Stripe account business description and MCC accurate for the product actually sold
- [ ] Statement descriptor recognisable to reduce disputes

### Intellectual property
- [ ] No third-party trademark, logo, product name or trade dress used
- [ ] **No unauthorized resale of licensed software.** If Model B (§0) is chosen, the signed reseller agreement is on file before the first sale
- [ ] All site copy, imagery and code original or properly licensed; licences recorded
- [ ] Customer content ownership stated clearly — the customer owns their data

### Marketing conduct
- [ ] **Testimonials only from verified paying customers**, with written permission, presented without alteration of meaning
- [ ] No fabricated reviews, ratings, counts, logos or case studies
- [ ] No fake scarcity, countdown pressure, or invented "N people viewing"
- [ ] **No income or savings guarantees**, to customers or to any affiliate
- [ ] Comparison claims factual, sourced, dated, and updated when they go stale
- [ ] No dark patterns in signup, upsell or cancellation

### Accessibility
- [ ] WCAG 2.1 AA on all customer-facing pages
- [ ] AODA obligations reviewed with counsel as headcount grows
- [ ] Accessibility statement with a feedback channel (exists at `legal/accessibility.html`)

---

## 17. SEO strategy

The site already runs a pillar-and-cluster internal linking system
(`tools/internal_links.py`), a sitemap, a feed and page-intent generation. This
plan extends it rather than replacing it.

### Pillar

`workspace.html` — *business productivity plans for small teams*. Everything
below links up to it; it links down to each cluster page.

### Cluster: intent-mapped targets

| Intent | Query shape | Page | Priority |
|---|---|---|---|
| Transactional | "business email with own domain Canada" | `workspace-email.html` | High |
| Transactional | "small business email hosting Ontario" | `workspace-email.html` | High |
| Commercial | "business email vs free email for small business" | `workspace-vs.html` | High |
| Commercial | "how much does business email cost per user" | `workspace.html` | High |
| Informational | "how to set up email on my own domain" | `blog/` | Medium |
| Informational | "what are SPF DKIM DMARC and do I need them" | `blog/` | Medium |
| Informational | "how to migrate company email without downtime" | `workspace-migration.html` | Medium |
| Informational | "GST HST on software subscriptions Canada" | `blog/` | Medium |
| Local | "IT support small business Ontario" | `workspace.html` | Medium |
| Trust | "is my business email encrypted" | `workspace-security.html` | Low |

### Technical

- [ ] `Product` + `Offer` JSON-LD on `workspace.html` — matching the pattern already used on `offers/guardian-command-nexus-blueprint.html`
- [ ] `FAQPage` JSON-LD from the existing FAQ section
- [ ] `BreadcrumbList` JSON-LD
- [ ] `Organization` JSON-LD with the Ontario address
- [ ] Canonical tags; no duplicate pricing content across `pricing.html`, `plans.html` and `workspace.html` — each needs a distinct primary intent
- [ ] Open Graph + Twitter card images per page
- [ ] Core Web Vitals: LCP < 2.5s, CLS < 0.1, INP < 200ms
- [ ] Every new page registered in `PAGES` in `tools/internal_links.py`, regenerated, and added to `sitemap.xml`
- [ ] `sw.js` `VERSION` bumped when several pages change together

### Off-page — permitted methods only

Google Business Profile; local business association and chamber listings; genuine
guest articles for local business publications; a customer referral programme
with disclosed incentives; open-source contributions from the existing repo work.

**Prohibited, and not negotiable:** purchased links, private blog networks,
comment spam, directory spam, scraped-list outreach, AI-spun content published
without review, hidden text, doorway pages, or any content that misrepresents
what the service is. These carry manual-action risk that outlasts any short-term
gain, and several are also CASL or *Competition Act* exposure.

### Content calendar

**Cadence: one substantial piece per week.** Not three thin ones. A weekly
1,200-word article that answers a question a real customer asked beats daily
generated filler, which is both a ranking liability and a credibility one.

| Week | Type | Working title | Feeds |
|---|---|---|---|
| 1 | Guide | How to set up business email on your own domain (without breaking your current mail) | `workspace-email.html` |
| 2 | Explainer | SPF, DKIM and DMARC in plain English — and what happens if you skip them | Security cluster |
| 3 | Lead magnet | Small-business email migration checklist (PDF) | C7 + list building |
| 4 | Comparison | Self-hosted vs hosted business email: an honest cost comparison | `workspace-vs.html` |
| 5 | Guide | What GST/HST actually applies to software subscriptions in Canada | Trust + local |
| 6 | Case note | A real migration, start to finish — **with the customer's written permission** | Proof |
| 7 | Explainer | What "encrypted at rest" does and does not protect you from | `workspace-security.html` |
| 8 | Lead magnet | New-employee IT onboarding checklist (PDF) | C7 |
| 9 | Guide | Offboarding an employee's accounts without losing their work | Retention |
| 10 | Explainer | Why your business email lands in spam | `workspace-email.html` |
| 11 | Comparison | When you should *not* switch providers | Credibility |
| 12 | Guide | Business continuity for a team that lives in email | `workspace-security.html` |

Repeat the pattern quarterly with new topics drawn from **actual support
tickets** — the ticket queue is the best keyword research available, because it
is real questions from real buyers.

**Publication standard.** Every factual claim is verified before publishing and
dated. Comparison claims name their source and get re-checked quarterly; a stale
price comparison is a misleading one. Nothing is published unreviewed. Case notes
require the customer's written permission, and testimonials come only from
verified paying customers, quoted without editing their meaning.

### Measurement

Search Console impressions/clicks/position by cluster; organic sessions to
`workspace.html`; trial starts attributed to organic; ranking for the ten target
intents above. Review monthly. Content that has not moved in 90 days gets
rewritten or removed — not padded.

---

## 18. Email templates

All transactional mail is plain, signed (SPF/DKIM/DMARC), and identifies
ClearGlass Inc. with a mailing address. Transactional and marketing are separate
streams: unsubscribing from marketing must never suppress a receipt, a dunning
notice or a security alert.

| Id | Trigger | Type | Subject |
|---|---|---|---|
| T1 | Trial started | transactional | Your ClearGlass Workspace trial is live |
| T2 | Setup call booked | transactional | Your setup call — {date} |
| T3 | 3 days before trial ends | transactional | Your trial ends {date} |
| T4 | Payment succeeded | transactional | Receipt — ClearGlass Workspace {period} |
| T5 | Onboarding complete | transactional | Your team is live on {domain} |
| T6 | Seat added / removed | transactional | {n} people on your plan — what changes on your next invoice |
| T7a/b/c | Payment failed 1/2/3 | transactional | Payment didn't go through / Second attempt failed / Final notice before suspension |
| T8 | Renewal reminder (annual, −30d) | transactional | Your annual plan renews {date} |
| T9 | Cancelled | transactional | Your plan is cancelled — here's your export |
| T10 | Quarterly check-in | marketing | How's ClearGlass Workspace working for you? |
| T11 | Security alert | transactional | New sign-in to your ClearGlass account |
| T12 | Incident notice | transactional | Service incident — {summary} |
| T13 | Abandoned checkout (consent only) | marketing | You left a plan in your cart |
| T14 | Win-back, 60 days post-cancel (consent only) | marketing | What we fixed since you left |
| T15 | Digital product delivered | transactional | Your download — {product} |
| T16 | Review request, 14 days post-onboarding | transactional | Would you tell us how it went? |
| T17 | Newsletter | marketing | {topic} — ClearGlass monthly |

### Sequences

| Sequence | Steps | Consent basis | Exit condition |
|---|---|---|---|
| **Onboarding** | T1 (day 0) → T2 (on booking) → T5 (on completion) → T16 (day +14) | Transactional | Always completes |
| **Trial conversion** | T1 (day 0) → T3 (day 11) → T4 or T9 (day 14) | Transactional | Converts or cancels |
| **Dunning** | T7a (day 3) → T7b (day 5) → T7c (day 7) | Transactional | Payment succeeds, or suspension |
| **Renewal** | T8 (annual, −30 days) → T4 (on charge) | Transactional | Renews or cancels |
| **Abandoned checkout** | T13, once, 4 h after abandonment | **Express consent required** | One send only, ever |
| **Win-back** | T14, once at day 60 post-cancellation | **Live consent required** | One send; never repeated |
| **Newsletter** | T17 monthly | **Express opt-in** | Unsubscribe, honoured ≤ 10 business days |

**Frequency cap across all marketing sequences: 2 messages per address per
month**, counted centrally. Transactional mail is uncapped and unsuppressible —
a customer who unsubscribed from the newsletter still gets their receipt, their
dunning notice and their security alert. That separation lives in code (§13
rule 2), not in a person's discipline.

### T1 — Trial started

```
Subject: Your ClearGlass Workspace trial is live

Hi {first_name},

Your 14-day trial of ClearGlass Workspace {plan} is running for {seats} people.
No card has been charged, and none will be until {trial_end_date}.

The next step is a setup call. We configure your domain, email routing and
accounts with you — you don't do this alone:

  Book your setup call: {booking_url}

What you have right now:
  • Plan: {plan} — {seats} {people}
  • After the trial: ${amount} CAD per month, plus applicable GST/HST
  • Cancel any time before {trial_end_date} and you're not charged at all

Your account: {app_url}

If anything is unclear, reply to this email. It reaches a person.

— Desmond, ClearGlass Inc.
ClearGlass Inc., {mailing_address}, Ontario, Canada
```

### T3 — Trial ending

```
Subject: Your trial ends {trial_end_date}

Hi {first_name},

Your ClearGlass Workspace trial ends on {trial_end_date}. On that date, the card
on file is charged ${amount} CAD plus applicable GST/HST for {seats} {people} on
the {plan} plan, and billing continues {interval}ly.

If that's right, there's nothing to do.

To change the number of people, switch plans, or cancel before you're charged:
  {account_url}

Cancelling takes one click and there's no penalty.

— ClearGlass Inc.
{mailing_address}
```

### T7c — Final notice

```
Subject: Final notice — action needed before {suspension_date}

Hi {first_name},

We've tried three times to charge the card on file for invoice {invoice_number}
(${amount} CAD) and each attempt was declined.

What happens next, so there are no surprises:
  • {readonly_date} — sending is paused. Mail still arrives; nothing is deleted
  • {suspension_date} — access is suspended. Your data is retained
  • {purge_date} — data is permanently deleted, after two further notices

Update your card: {portal_url}

If there's a problem on our side, or you need different arrangements, reply and
we'll sort it out. We would rather fix this than lose you.

— ClearGlass Inc.
{mailing_address}
```

**Copy rules for every template.** No fabricated urgency and no invented
deadlines — every date named is a real system date. No claims about other
customers' results. No pressure language in cancellation flows. Marketing mail
carries a working unsubscribe honoured within 10 business days; transactional
mail states plainly why it was sent.

---

## 19. Launch plan

### Phase 0 — Gates (before anything ships)

Hard blockers. Do not proceed past any unchecked box.

- [ ] **§0 delivery model chosen and documented** — and if Model B, the reseller agreement signed and on file
- [ ] Lawyer review of terms, privacy, refund and auto-renewal language complete
- [ ] CPA review of GST/HST registration and deferred revenue complete
- [ ] Stripe account business description and MCC corrected to describe **this** product *(currently outstanding — the live account still describes an unrelated trading product)*
- [ ] Stripe Tax enabled and verified on a test Ontario invoice
- [ ] Products and Prices created in Stripe live mode; ids in the price book
- [ ] Webhook endpoint live, signature-verified, replay-tested
- [ ] Backup and **restore** verified — a backup you have never restored is a hope

### Phase 1 — Soft launch (weeks 1–2)

Three to five customers from the existing network. Manual onboarding, deliberately.

- [ ] Publish `workspace.html` price changes if the §0 decision moved them
- [ ] One real end-to-end purchase at $6.00, verified and refunded
- [ ] Onboard the first customer personally; write the runbook *while* doing it
- [ ] Instrument: trial starts, conversions, support volume per customer
- [ ] Success gate: **3 paying tenants, zero data incidents, onboarding under 4 hours each**

### Phase 2 — Public launch (weeks 3–6)

- [ ] `workspace-email.html`, `workspace-migration.html` published and indexed
- [ ] JSON-LD, canonicals, sitemap complete
- [ ] Google Business Profile live
- [ ] Referral programme with disclosed incentives
- [ ] Direct outreach **only** to people with an existing relationship or express consent
- [ ] Success gate: **10 paying tenants, trial→paid ≥ 25%, churn < 5%/month**

### Phase 3 — Scale (weeks 7–12)

- [ ] Self-serve onboarding for 1–5 seat tenants
- [ ] Comparison and security content published
- [ ] Partner referral agreements with accountants and bookkeepers
- [ ] Success gate: **30 paying tenants, CAC below the §22 ceiling**

**Launch is reversible.** If Phase 1's gate is missed, stop and fix rather than
proceeding on volume. Three unhappy customers in a referral-driven market is
worse than zero.

---

## 20. 30/60/90 roadmap

### Days 1–30 — Prove it works for one

| Area | Deliverable |
|---|---|
| Legal | Lawyer + CPA reviews complete; terms and privacy updated |
| Payments | Stripe live Products/Prices, Tax, webhook endpoint, one verified real charge |
| Product | Provisioning path working end-to-end for one tenant, even if partly manual |
| Backend | Migration `006_workspace.sql`; `/workspace/*` routes; auth-coverage tests extended |
| Content | `workspace-email.html`, `workspace-migration.html` |
| Ops | Backup + verified restore; monitoring on `/ready`; incident contact published |
| Business | Stripe business description corrected; first 3 customers onboarded personally |

**Exit criteria:** 3 paying tenants. One documented, repeatable onboarding.

### Days 31–60 — Make it repeatable

| Area | Deliverable |
|---|---|
| Product | Self-serve seat add/remove; Billing Portal; tenant admin dashboard |
| Backend | Dunning automation; async export; cross-tenant isolation test suite |
| Automation | A1–A14 from §13 running; approvals queue live for A7/A8/A15–A17 |
| Content | `workspace-security.html`, `workspace-vs.html`, DPA, first 4 blog posts |
| SEO | Full JSON-LD; Search Console baseline; Google Business Profile |
| Ops | Staff admin dashboard §14; runbooks for cutover, incident, restore |
| Business | Referral programme; accountant/bookkeeper partner conversations |

**Exit criteria:** 10 paying tenants. Onboarding under 2 hours. Trial→paid ≥ 25%.

### Days 61–90 — Make it scale

| Area | Deliverable |
|---|---|
| Product | Self-serve onboarding for 1–5 seats; automated DNS verification |
| Backend | Provisioning worker hardened; retries; queue observability |
| Automation | Monthly metrics report; quarterly check-in (drafted, approved, sent) |
| Content | 8 more posts; comparison pages updated with dated sources |
| Ops | Restore drill on a schedule; deliverability monitoring; status page |
| Business | Pricing review against real infrastructure cost; first annual cohort |

**Exit criteria:** 30 paying tenants. CAC below the §22 ceiling. Churn < 3%/month.

---

## 21. KPIs

| KPI | Definition | Target by day 90 | Review |
|---|---|---|---|
| MRR | Sum of monthly-normalised subscription revenue | Set from actuals after Phase 1 | Weekly |
| ARR | MRR × 12 | — | Monthly |
| Paying tenants | Tenants with status `active` | 30 | Weekly |
| Seats | Total billable seats | — | Weekly |
| ARPA | MRR ÷ paying tenants | ≥ $60 | Monthly |
| Trial→paid | Converted ÷ trials started | ≥ 25% | Weekly |
| Logo churn | Tenants cancelled ÷ tenants at period start | < 3%/month | Monthly |
| Revenue churn | MRR lost ÷ MRR at period start | < 3%/month | Monthly |
| Net revenue retention | (start + expansion − contraction − churn) ÷ start | > 100% | Quarterly |
| CAC | Sales + marketing spend ÷ new customers | Below §22 ceiling | Monthly |
| LTV:CAC | LTV ÷ CAC | ≥ 3:1 | Quarterly |
| CAC payback | CAC ÷ monthly contribution per customer | < 12 months | Quarterly |
| Gross margin | (Revenue − COGS) ÷ revenue | > 80% | Monthly |
| Onboarding time | Signup → first mail on customer domain | < 2 hours | Per customer |
| Support load | Tickets ÷ tenant ÷ month | < 2 | Monthly |
| Failed payment rate | Failed ÷ attempted invoices | < 5% | Monthly |
| Dispute rate | Disputes ÷ charges | < 0.1% | Monthly |
| Uptime | Mail + storage availability | > 99.5% | Monthly |
| Data incidents | Any unauthorised access | **0** | Continuous |
| Restore drill | Successful test restores | 1/month | Monthly |

**The two that matter most.** *Data incidents* — the only KPI whose target is
zero and whose failure is not recoverable by working harder. And *trial→paid* —
it is the earliest honest signal that the value proposition is real rather than
merely well-written.

---

## 22. Break-even analysis

All figures use **Collaborate at $8.10/seat/month** (annual billing), the tier the
pricing page marks most popular. Every assumption is stated so you can substitute
your own; the arithmetic follows from them.

### Assumptions

| Input | Value | Basis |
|---|---|---|
| Price per seat / month | $8.10 | §4, annual billing |
| Payment processing | ~3.2% | §5, annual billing, worst case |
| Infrastructure per seat | ~$0.55 | Model A estimate — **replace with measured cost after Phase 1** |
| Contribution margin per seat | **$7.29/month** | 90% of $8.10 |
| Fixed monthly cost | **$450** | Infrastructure baseline, domains, tooling, insurance. Excludes founder salary |

> Founder time is not costed here. That is a deliberate simplification, not a
> claim that your time is free — add a salary line before treating any number
> below as profit.

### Break-even

```
Break-even seats = Fixed cost ÷ Contribution per seat
                 = $450 ÷ $7.29
                 = 61.7  →  62 seats
```

**62 seats.** At an average of 8 seats per tenant, that is **~8 paying tenants** —
which is Phase 2's exit gate, not a distant goal. Below roughly 30 seats the
fixed cost dominates and gross margin is negative; that is expected and is the
reason Phase 1 is deliberately small.

### Seats required at each revenue level

| Monthly recurring revenue | Seats at $8.10 | Tenants at 8 seats avg | Contribution after fixed costs |
|---|---|---|---|
| $500 | 62 | ~8 | ~$2 |
| $1,000 | 124 | ~16 | ~$454 |
| $2,500 | 309 | ~39 | ~$1,802 |
| $5,000 | 618 | ~78 | ~$4,055 |
| $10,000 | 1,235 | ~155 | ~$8,554 |

*(Fixed cost held flat at $450 for arithmetic clarity. It will not stay flat —
support and infrastructure step up with volume. Re-derive this table with
measured costs at each Phase gate.)*

### LTV and the CAC ceiling

```
LTV = Contribution per seat per month ÷ monthly churn rate
```

| Monthly churn | Avg. seat lifetime | LTV per seat | Max CAC at 3:1 |
|---|---|---|---|
| 2% | 50 months | **$364.50** | **$121.50** |
| 3% | 33 months | **$243.00** | **$81.00** |
| 5% | 20 months | **$145.80** | **$48.60** |

At the §21 target of 3% monthly churn, **you may spend up to about $81 to acquire
a seat** and still hold a 3:1 LTV:CAC ratio. At 8 seats per tenant, that is
roughly **$648 per customer** — enough to fund real onboarding labour, which is
exactly the differentiator in §3. Note how sharply the ceiling falls as churn
rises: at 5% churn the same acquisition spend destroys value. **Retention is the
lever, not acquisition.**

### Sensitivity

| Change | Effect on break-even |
|---|---|
| Fixed cost $450 → $700 | 62 → 96 seats |
| Infrastructure $0.55 → $1.50/seat | Contribution $7.29 → $6.34; 62 → **71 seats** |
| All customers billed monthly ($9.72) rather than annually | Contribution $7.29 → $8.59; 62 → **53 seats** |
| Mix shifts to Complete ($17.00 annual) | 62 → **30 seats** |
| Mix shifts to Essentials ($6.00 annual) | Contribution $7.29 → $5.40; 62 → **84 seats** |

Note the third row: monthly billing has a *higher* effective processing cost
(§5) but a *higher* headline price, and the price increase wins — a monthly seat
contributes $8.59 against an annual seat's $7.29. Annual billing is still the
right default, because it buys retention and cash, not margin. Do not let the
"annual is cheaper to process" argument mislead you into thinking it is more
profitable per seat; it is not.

**Plan mix moves break-even more than any cost line.** Selling one Complete seat
is worth roughly two Collaborate seats or three Essentials seats. That is where
sales effort belongs.

### Three scenarios at 12 months

Scenario planning, not prediction. The point of the worst case is that it is
survivable; the point of the best case is that it is *not* the plan.

| | **Worst case** | **Expected case** | **Best case** |
|---|---|---|---|
| Paying tenants | 8 | 30 | 75 |
| Avg. seats/tenant | 5 | 8 | 11 |
| Total seats | 40 | 240 | 825 |
| Plan mix (Ess/Coll/Compl) | 50/40/10 | 30/50/20 | 20/50/30 |
| Blended price/seat | $7.94 | $9.25 | $10.35 |
| **MRR (subscription)** | **$318** | **$2,220** | **$8,539** |
| Services + products/mo (C2–C7) | $150 | $600 | $2,500 |
| **Total monthly revenue** | **$468** | **$2,820** | **$11,039** |
| Payment processing (~3.2%) | $15 | $90 | $353 |
| Infrastructure @ $0.55/seat | $22 | $132 | $454 |
| Fixed costs | $450 | $650 | $1,400 |
| Affiliate commissions | $0 | $40 | $200 |
| Refunds (~1%) | $5 | $28 | $110 |
| **Total costs** | **$492** | **$940** | **$2,517** |
| **Net contribution/mo** | **−$24** | **$1,880** | **$8,522** |
| **ARR run-rate** | $5,616 | $33,840 | $132,468 |
| Monthly churn | 6% | 3% | 2% |
| Support load | ~2 h/week | ~8 h/week | ~25 h/week |
| What it means | Below break-even. A side business, not a living. Decide at month 9 whether to fix churn or stop | Break-even cleared; funds part-time help; still not a full income for a family | Needs a second full-time operator. §26 roles stop being nominal |

**Read the worst case first.** It is not a disaster scenario — it is what happens
if acquisition is slower than hoped and churn runs at 6%, which is entirely
ordinary for a new subscription business. Note that it loses ~$24/month, meaning
**the downside is bounded at roughly $290/year plus your time.** That is a
genuinely low-risk experiment. The risk in this business is not money; it is
months of unpaid labour and the customer obligations you take on.

**Best case requires headcount.** 75 tenants at 8 seats is more support and
onboarding than one person delivers alongside everything else. If the best case
arrives, the constraint is people, not demand — plan the hire at ~40 tenants, not
at 75.

**What moves between the columns:** plan mix (§22 sensitivity) and churn. Not
traffic. Doubling visitors to a page that converts at 1% and churns at 6% doubles
the churn too.

> Nothing in this section is a forecast or a promise of income. These are
> conditional models: *if* the stated assumptions hold, the arithmetic follows.
> Assumptions frequently do not hold. No figure here is a guarantee, a target you
> are entitled to, or a claim that any revenue level will be reached.

---

## 23. Testing strategy

### Layers

| Layer | Scope | Gate |
|---|---|---|
| Unit | Price resolution, proration maths, tax rounding, dunning state machine | `pytest`, every PR |
| Contract | OpenAPI schema shape — especially that no price-shaped field exists on checkout | `pytest`, every PR |
| Auth coverage | Every mutating route behind `require_admin` or a tenant session | `test_route_auth_coverage.py`, every PR |
| Isolation | Cross-tenant access attempts on every route | dedicated suite, every PR |
| Integration | Webhook → DB → invoice → provisioning, against Stripe test mode | every PR |
| Governance | High/critical actions blocked without approval | `test_governance.py` + `daily_loop.py`, every PR + daily |
| E2E | Signup → trial → conversion → seat change → cancel | nightly |
| Frontend | `tsc --noEmit` + build | Commerce Frontend CI |
| Lint | `ruff check .` | every PR |
| Security scanning | SAST, dependency audit, secret scanning, container scan | every PR |
| DAST | Authenticated scan against staging | weekly |
| Restore drill | Backup restored into a scratch environment | monthly, manual sign-off |

### OWASP Top 10 coverage

| Risk | Control | Verified by |
|---|---|---|
| A01 Broken access control | Session-derived `tenant_id`; `require_admin`; role checks | Isolation suite + `test_route_auth_coverage.py`, every PR |
| A02 Cryptographic failures | TLS 1.2+, encryption at rest, argon2id, envelope-encrypted MFA secrets | Config test + TLS scan |
| A03 Injection | Parameterised queries only (SQLAlchemy); schema validation rejecting unknown fields; output auto-escaping | SAST + unit tests |
| A04 Insecure design | Governance gate, approval queue, fail-closed defaults, append-only ledger | `test_governance.py` + daily self-check |
| A05 Security misconfiguration | IaC-managed config; security headers asserted; prod fails closed without `ADMIN_API_KEY` | Header test + startup test |
| A06 Vulnerable components | Pinned deps, lockfiles, Dependabot, review of new direct deps | Dependency audit, every PR |
| A07 Auth failures | MFA, rate limits, breach-list check, no user enumeration, revocable sessions | Auth suite incl. timing-equality test |
| A08 Data integrity failures | Webhook signature verification; idempotency; no unsigned deserialisation | Webhook suite |
| A09 Logging failures | Append-only `workspace_events` on every mutation; alerting on anomalies | Audit-coverage test |
| A10 SSRF | No user-supplied URLs fetched server-side; egress allow-list on workers | SAST + review |

### Money-path tests that must exist

1. **Price authority.** Submitting `unit_amount`, `price_data`, `amount`,
   `discount` or `currency` on a checkout request is rejected, never honoured.
2. **Quote-to-charge parity.** The total quoted to the customer equals the total
   sent to Stripe, **to the cent**, across a generated matrix of plans × seat
   counts × billing intervals. Compare the actual Stripe line items against the
   quote — not the quote against the page, which is the same number twice and
   proves nothing.
3. **Proration.** Seat +1 and −1 mid-period produce the expected proration lines.
4. **Tax.** An Ontario billing address produces 13% HST, itemised.
5. **Webhook idempotency.** Every event replayed twice produces exactly one
   effect.
6. **Signature rejection.** A tampered signature is a 400 **and** an audit row.
7. **Dunning.** A card that attaches but fails drives the full T7a–c sequence and
   the read-only → suspend transitions on the right days.
8. **No auto-refund on dispute.** A dispute event freezes automation.
9. **Trial.** No charge during trial; charge on day 14; no charge if cancelled
   first.

### Test-environment rules

Stripe **test mode only** in CI, with test clocks for trial and renewal
transitions. Never a live key in CI. Seed data is synthetic — no real customer
record is ever copied into a test environment.

**One live-mode exception:** a single real charge at the lowest price during
Phase 1, verified and refunded, because test mode does not prove a live account
is correctly configured. Document it in the ledger.

---

## 24. Deployment plan

### Environments

| Env | Purpose | Stripe | Data |
|---|---|---|---|
| local | Development | test | synthetic |
| ci | Automated gates | test | ephemeral |
| staging | Pre-production rehearsal | test | synthetic |
| production | Live | **live** | real |

### Pipeline

```
PR → ruff + pytest + tsc + next build + auth-coverage + isolation
   → review
   → merge to main
   → deploy staging (automatic)
   → smoke: /ready, checkout dry-run, webhook replay
   → manual approval
   → deploy production (blue/green)
   → post-deploy: /ready, one test-mode checkout, webhook receipt, error rate
   → rollback if any check fails
```

### Deployment rules

- **Migrations are forward-only and backward-compatible for one release.** Add
  columns nullable, backfill, then enforce. Never a destructive migration in the
  same release as the code that stops using the column.
- **`APP_ENV=production` with no `ADMIN_API_KEY` fails at startup.** Already
  implemented. Keep it.
- **Secrets from the runtime secret store**, never from git. Rotation is
  quarterly and on any staff departure.
- **Webhook endpoint changes are two-step:** register the new endpoint, verify
  receipt, then remove the old one. Never a gap.
- **Static site** continues to deploy via GitHub Pages; `.nojekyll`, redirects
  and headers stay intact.
- **Deploy window:** business hours, never Friday afternoon, never during a
  customer's DNS cutover.
- **Rollback plan required in every PR description** — if it is not written down
  before the deploy, it does not exist during the incident.

### Backup & recovery

| | Target |
|---|---|
| Database backup | Continuous WAL + daily snapshot, 30-day retention |
| Object storage | Versioned + replicated |
| RPO | < 15 minutes |
| RTO | < 4 hours |
| Restore drill | Monthly, into a scratch environment, signed off |
| Backup encryption | At rest, separate credentials from production |

### Incident response

Detect → assess severity → communicate within 1 hour for customer-affecting
incidents → mitigate → resolve → **written post-mortem within 5 business days**,
blameless, published to affected customers when the incident touched their data.
If personal information may have been exposed, run the PIPEDA breach assessment
in §16 in parallel — not afterwards.

---

## 25. Risk register

Scored likelihood (L) and impact (I), 1–5. Exposure = L × I.

| # | Risk | L | I | Exp | Mitigation | Owner |
|---|---|---|---|---|---|---|
| **R1** | **Delivery model undecided** (§0) — selling a product with no confirmed way to deliver it | 4 | 5 | **20** | Phase 0 gate. No seat sold before the model is chosen and documented | Owner |
| **R2** | **Cross-tenant data exposure** | 2 | 5 | **10** | Session-derived `tenant_id`, automated isolation suite on every build, PIPEDA breach plan | Eng |
| **R3** | **Unauthorized software resale** if Model B is chosen without an agreement | 3 | 5 | **15** | Signed reseller agreement on file before the first sale, or Model A/C instead | Owner + counsel |
| R4 | Mail deliverability failure (blocklisting) | 3 | 4 | 12 | SPF/DKIM/DMARC, outbound rate limits, reputation monitoring, dedicated IP warm-up | Eng |
| R5 | Churn above 5%/month destroys unit economics (§22) | 3 | 4 | 12 | Onboarding quality, quarterly check-ins, churn reason capture, act on the reasons | Owner |
| R6 | Infrastructure cost exceeds the $0.55/seat estimate | 3 | 4 | 12 | Measure real cost during Phase 1; re-derive §22 before Phase 3; reprice at renewal with 30 days' notice | Owner |
| R7 | Founder is the single point of failure for onboarding | 4 | 3 | 12 | Written runbooks from customer one; hire or contract before 30 tenants | Owner |
| R8 | GST/HST handled incorrectly | 2 | 4 | 8 | CPA review, Stripe Tax, itemised invoices, quarterly reconciliation | CPA |
| R9 | Stripe account or MCC mismatch triggers review or hold | 3 | 4 | 12 | **Correct the business description before launch** (Phase 0, outstanding) | Owner |
| R10 | Data loss from an unverified backup | 2 | 5 | 10 | Monthly restore drills with sign-off; a backup never restored is not a backup | Eng |
| R11 | Trademark conflict on the brand | 2 | 3 | 6 | CIPO search before brand spend (§1) | Counsel |
| R12 | CASL breach from a marketing mistake | 2 | 4 | 8 | Consent records, transactional/marketing separation in code, bulk send in `ALWAYS_ESCALATE` | Owner |
| R13 | Chargebacks / friendly fraud | 3 | 2 | 6 | Clear descriptor, itemised invoices, delivery evidence, dispute freeze | Eng |
| R14 | Competitor undercuts on price | 4 | 2 | 8 | Compete on included setup and support, not price. Do not enter a price war you cannot fund | Owner |
| R15 | Key supplier changes terms or pricing | 3 | 3 | 9 | Pricing page already states supplier-pricing exposure; keep migration paths open; avoid single-supplier lock-in | Eng |
| R16 | Support load exceeds capacity | 3 | 3 | 9 | Track tickets/tenant/month; self-serve for the top 5 requests; stop selling before quality drops | Owner |
| R17 | Security incident (credential stuffing, ATO) | 3 | 4 | 12 | MFA everywhere, argon2id, rate limits, breach-list checks, alerting | Eng |
| R18 | Accessibility complaint | 2 | 3 | 6 | WCAG 2.1 AA testing; published accessibility statement and feedback channel | Eng |

### Top three, and what to do about them this week

1. **R1 — decide the delivery model.** Everything downstream is guesswork until
   this is settled. It is a decision, not a project; make it.
2. **R3 — if the answer is Model B, get the agreement signed first.** Selling
   licensed software without authorization is not a compliance detail, it is the
   whole business's legality.
3. **R9 — correct the Stripe business description.** The live account
   (`acct_1RlYxRL8uR92FksU`) still describes an unrelated trading product while
   sitting behind nine live checkout paths. There is no API operation for this
   field; it is a Dashboard-only change and it takes about two minutes. Until it
   is done, every payment page is misdescribed to the payment processor, which is
   exactly the kind of mismatch that triggers an account review.

---

## 26. Family operating model

Five roles. **Roles, not people** — at launch one person holds several, and that
is fine as long as the *approvals* stay separated. The separation that matters is
not who does the work; it is who signs off on it.

| Role | Owns | Decides alone | Cannot decide alone | Weekly time (expected case) |
|---|---|---|---|---|
| **Business Owner** | Strategy, contracts, compliance, financial approval | Pricing direction, which markets, whether to hire | Nothing above $500 without a second reviewer once the business supports one | 4–6 h |
| **Technical Operator** | Infrastructure, security, integrations, deploys, backups | Architecture, dependency choices, deploy timing | Production data deletion, price-book edits, secret rotation without notice | 6–10 h |
| **Customer-Success Operator** | Onboarding, migrations, support, retention | Ticket priority, scheduling, goodwill gestures under $50 | Refunds, credits, plan changes on a customer's behalf | 8–15 h |
| **Marketing Operator** | Content, campaigns, partnerships, analytics | Publishing schedule, topics, organic social | Any bulk send, any paid spend, any factual claim about the product | 4–8 h |
| **Finance Operator** | Invoices, taxes, reconciliation, reporting | Bookkeeping categorisation, monthly close | Filing without CPA review, writing off a receivable, changing payout details | 3–5 h |

### Separation of duties — the four that are non-negotiable

Everything else can collapse into one person. These four cannot, because each is
a well-known fraud or error path:

1. **The person who issues a refund is not the person who approves it.**
2. **The person who changes a price is not the person who approves it.**
3. **The person who adds an affiliate is not the person who approves their
   payout.**
4. **The person who deploys to production is not the only person who can restore
   from backup.**

Until there are two people, these are enforced by the **approval queue** (§14
screen 3) with a mandatory written reason and a 24-hour cooling period on
anything critical — a delay you impose on yourself is a weak control, but it is
not nothing, and it is auditable. When the second person arrives, they become
real.

### Approval thresholds

| Action | Approver | Second approver | Notes |
|---|---|---|---|
| Spend < $100/mo | Role owner | — | Logged |
| Spend $100–$500/mo | Business Owner | — | |
| Spend > $500/mo or any annual commitment | Business Owner | Finance Operator | |
| Refund < $100 | Customer Success | Finance Operator | 24 h cooling period |
| Refund ≥ $100 or any chargeback response | Business Owner | Finance Operator | |
| Any price change | Business Owner | Finance Operator | 30 days' customer notice (§4) |
| New coupon or promotion | Business Owner | Marketing | Approval row required (§4) |
| Bulk marketing send | Marketing | Business Owner | `ALWAYS_ESCALATE` (A17) |
| Supplier or reseller contract | Business Owner | **Lawyer** | Never signed same-day |
| Legal document or policy change | Business Owner | **Lawyer** | |
| Account deletion / data purge | Technical | Business Owner | Two customer notices first (§8.4) |
| Production schema migration | Technical | Business Owner | Rollback plan written first (§24) |
| Affiliate payout | Finance | Business Owner | Blocked until agreement signed |
| Enterprise quote | Business Owner | Finance Operator | A24 |
| Hiring | Business Owner | Finance Operator | |

### Weekly operating rhythm

| When | What | Who | Time |
|---|---|---|---|
| Mon 30 min | Week ahead: trials expiring, onboardings booked, approval queue | All | 30 m |
| Daily 10 min | Support queue triage, failed payments, alerts | Customer Success | 10 m |
| Wed | Content publish + SEO check | Marketing | 1 h |
| Fri 30 min | Numbers: MRR, trials, churn, tickets. Approval queue cleared to zero | All | 30 m |
| Monthly | Close the books; reconcile Stripe payouts to the ledger; review KPIs | Finance | 2 h |
| Monthly | Restore drill, dependency updates, access review | Technical | 2 h |
| Quarterly | GST/HST filing with CPA; pricing review; risk register review | Owner + Finance | 4 h |
| Annually | Lawyer review of policies; insurance; trademark watch | Owner | 4 h |

**Total expected-case load: roughly 25–45 hours/week across all roles.** That is
one full-time equivalent plus help, not a passive business. "Minimal daily
administration" is achievable — the daily load is about 10 minutes of triage —
but it is bought with the automation in §13, and that automation has to be built
first. Be honest with the family about the sequencing: the first 90 days are
front-loaded work in exchange for a low steady state afterwards.

### The rule that protects the family

**Never let a role be the only person who can do something.** Every role writes
its runbook as it works, in the repo, in plain language. If the Technical
Operator is unreachable for two weeks, someone else must be able to restore a
backup and answer a customer. That is not a process nicety in a family business —
it is what stops an ordinary life event from becoming a business failure.

---

## Appendix A — What already exists in this repo

| Asset | Path | State |
|---|---|---|
| Workspace pricing page | `workspace.html` | Live |
| Guardian per-seat tiers | `plans.html` | Live |
| Blueprint offer | `offers/guardian-command-nexus-blueprint.html` | Live |
| Store / Side Store / checkout | `store.html`, `side-store.html`, `checkout/` | Live |
| Legal pages | `legal/*.html` | Live |
| Server-side price authority | `clearglass-commerce/control-plane/app/pricebook.py` | Implemented + tested |
| Cart pricing (cent-exact) | `.../app/cart.py` | Implemented + tested |
| Payments / Checkout Sessions | `.../app/payments.py` | Implemented |
| Governance engine | `.../app/governance.py` | Implemented + tested |
| Admin auth | `.../app/security.py` | Implemented + test-enforced coverage |
| Audit ledger | `.../app/audit.py` | Implemented |
| Stripe account state | `clearglass-commerce/STRIPE_SETUP.md` | Documented |
| Internal linking generator | `tools/internal_links.py` | Live |

## Appendix B — Open items requiring the owner personally

These cannot be completed by automation, tooling, or anyone but the account
holder.

1. **Stripe business description + MCC** on `acct_1RlYxRL8uR92FksU` — Dashboard
   only, no API operation exists. Currently describes an unrelated trading
   product. **(R9, Phase 0 gate.)**
2. **The §0 delivery-model decision.** **(R1.)**
3. **Reseller agreement**, if Model B. **(R3.)**
4. **Lawyer and CPA engagement.** **(§16.)**
5. **Confirmation that the §4 prices are the intended prices** — they are
   currently working assumptions, not owner-confirmed figures.
6. **Etsy OAuth grant**, if the Etsy channel is still wanted — requires the
   owner's own consent flow (`python -m app.etsy_connect`).
