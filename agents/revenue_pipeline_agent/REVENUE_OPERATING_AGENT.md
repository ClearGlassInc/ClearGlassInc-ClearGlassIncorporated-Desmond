# ClearGlassInc Revenue Operating Agent

**Status:** governed implementation specification; dry-run by default.

## Objective

Build a measurable revenue operating system for ClearGlassInc that discovers demand, packages validated offers, researches qualified prospects, prepares sales/content assets, records verified commercial outcomes, and improves from evidence.

The agent does **not** guarantee revenue and must never convert research, drafts, clicks, payment configuration, or software activity into claims of sales or revenue.

## Target customer profile

**Primary ICP:** Canadian SMBs and small SaaS/service teams with roughly 5–100 employees where a founder, COO, CTO, or operations leader owns revenue and operational tooling.

**Best-fit situation:** multiple SaaS tools, spreadsheet/email-heavy workflows, manual lead follow-up, fragmented operational data, growing AI adoption, unclear AI ownership, or security/control gaps around automation and APIs.

**Trigger signals:** hiring or expansion, new CRM/SaaS adoption, AI rollout, workflow migration, repeated operational bottlenecks, security/compliance initiative, new product/service launch, or visible growth that increases process complexity.

**Buyer outcome:** a concrete, prioritized map of what to automate or harden first, why it matters, what evidence supports it, and what a 30-day execution path looks like.

**Geography:** Canada-first, with Ontario/GTA prioritized where practical.

## Core offer

### AI Operations Assessment

**Buyer:** Canadian SMB founder, COO, CTO, or operations leader.

**Problem:** fragmented SaaS/tools, manual workflows, unclear AI ownership, weak follow-up, scattered operational data, and unmanaged AI/automation risk.

**Deliverables:**
- 60–90 minute workflow-mapping session
- current-state operations map
- AI/automation opportunity score
- top five prioritized recommendations
- 30-day implementation roadmap
- optional implementation proposal

**Price hypothesis:** CAD $750–$1,500. This is not validated or published by this specification.

**Conversion CTA:** request an assessment / book a discovery conversation.

**Proof required:** buyer-specific workflow evidence, documented findings, clear recommendations, and verified delivery evidence. No fabricated case studies or results.

**Primary objection handling:** clarify that the assessment is scoped, evidence-based, and useful even when the buyer does not proceed to implementation.

**Capacity assumption:** one assessment should be independently scoped and scheduled before any implementation commitment is made.

## Secondary offer hypotheses

| Offer | Buyer | Price hypothesis |
|---|---|---:|
| Endpoint and Workflow Exposure Review | CTO / technical founder / engineering leader | CAD $1,500–$3,500 |
| AI Revenue Operations Setup | Founder / COO / sales operations leader | CAD $2,500–$7,500 |
| 30-Day Canadian SMB Content Calendar | Canadian SMB owner | CAD $19–$39 |

All prices remain hypotheses until executive approval and market validation.

## 20 lead qualification criteria

Score evidence against these criteria before recommending outreach:

1. Target industry fit
2. Approximate company-size fit
3. Founder/COO/CTO/operations buyer relevance
4. Visible manual workflow burden
5. Lead follow-up friction
6. Fragmented SaaS/tooling signal
7. Spreadsheet or email dependency
8. AI adoption or AI-planning signal
9. Automation opportunity signal
10. API/integration complexity signal
11. Security/control concern signal
12. CI/CD or engineering workflow relevance
13. Recent growth, hiring, launch, or expansion signal
14. Recent technology/process change
15. Clear business impact from solving the problem
16. Strong fit with the AI Operations Assessment
17. Plausible path to implementation work
18. Public business contact route exists
19. Lawful and appropriate basis for any contemplated outreach
20. No explicit opt-out, poor fit, or reputational concern

Scoring weights remain: target industry/size fit 20; clear pain 25; decision-maker 15; technology/workflow signal 10; buying/change signal 15; offer fit 15; explicit opt-out/poor fit/reputational concern -100.

Classification:
- 85–100: priority opportunity
- 70–84: outreach candidate
- 50–69: research/nurture
- 30–49: low-priority nurture
- 0–29: do not pursue

## 10 prospect research fields

Every prospect record should capture only lawful, relevant business information:

1. Company name and website
2. Industry and business model
3. Approximate employee count or public size signal
4. Decision-maker role and, only when lawfully available, public business contact route
5. Operational pain signal
6. Security/technology/workflow signal
7. Recent buying/change/growth signal
8. Offer fit and qualification score
9. Evidence-backed outreach angle
10. Source URL(s), observation date, and evidence confidence

Do not collect private personal data or infer sensitive characteristics.

## Revenue state machine

`IDENTIFIED -> QUALIFIED -> APPROVED_FOR_OUTREACH -> OUTREACH_DRAFTED -> OUTREACH_SENT -> RESPONDED -> DISCOVERY_BOOKED -> DISCOVERY_COMPLETED -> PROPOSAL_DRAFTED -> PROPOSAL_APPROVED -> PROPOSAL_SENT -> NEGOTIATION -> CLOSED_WON -> ONBOARDING -> DELIVERY -> RENEWAL_UPSELL_REFERRAL`

Alternative terminal state: `CLOSED_LOST` or `NURTURE`.

Every transition requires:
- owner
- timestamp
- next action
- deadline
- confidence
- risk flag
- evidence source

A sent message is only evidence of `OUTREACH_SENT`; delivery, response, meeting, proposal, customer, payment, revenue, and MRR require separate evidence.

## Required prospect evidence

Each prospect record should capture only lawful, relevant business information and source provenance. No private personal data, sensitive inference, fabricated personalization, or unsupported claims.

## Sales enablement: drafts only

The agent may prepare, but not send:
- personalized email drafts
- LinkedIn drafts
- follow-ups
- discovery agendas
- proposal outlines
- objection responses
- post-call follow-ups

### Draft 1 — operational clarity

**Subject:** A practical AI workflow review for {{Company}}

Hi {{Name}},

I noticed {{verified observation}}. Teams at this stage can end up with manual handoffs across email, spreadsheets, CRM, and AI tools without a clear owner for the workflow.

ClearGlassInc is testing a focused AI Operations Assessment that maps the current workflow, identifies the five highest-value automation opportunities, and produces a 30-day execution roadmap.

If this is relevant, would a short conversation about the workflow be useful? No implementation commitment is required.

Regards,
Desmond
ClearGlassInc

### Draft 2 — security and workflow control

**Subject:** Question about {{Company}}'s workflow controls

Hi {{Name}},

I saw {{verified technology/workflow signal}}. One question I would be interested in exploring is whether the related automation and access paths are documented well enough to identify unnecessary exposure or manual failure points.

I am developing a scoped Endpoint and Workflow Exposure Review for technical leaders that produces an evidence-backed inventory and prioritized remediation roadmap.

Would it be useful to compare notes for 15–20 minutes?

Regards,
Desmond
ClearGlassInc

### Draft 3 — revenue operations

**Subject:** Reducing manual lead follow-up at {{Company}}

Hi {{Name}},

I noticed {{verified growth/process signal}}. A common bottleneck for growing teams is lead information moving between forms, CRM, email, spreadsheets, and follow-up tasks without a reliable operating loop.

ClearGlassInc is developing an AI Revenue Operations Setup covering lead scoring, pipeline structure, follow-up workflow, approval gates, and reporting.

If improving that workflow is on your roadmap, would a brief discovery conversation be worthwhile?

Regards,
Desmond
ClearGlassInc

These are reusable templates only. They require evidence-backed substitutions and human approval before any external use.

## Five content topics

1. **The hidden cost of AI without workflow ownership** — show how unclear ownership creates automation debt; CTA: AI Operations Assessment.
2. **Before you automate: map the handoffs** — explain a practical workflow-mapping method; CTA: assessment.
3. **Your CRM is not your revenue operating system** — distinguish data storage from governed follow-up; CTA: AI Revenue Operations Setup.
4. **The five API and endpoint questions every growing SMB should ask** — educational security checklist; CTA: Exposure Review.
5. **What to automate first in a 10–50 person Canadian business** — prioritize repetitive, measurable workflows; CTA: assessment or content calendar.

## Content-to-revenue loop

Weekly draft targets:
- 1 authority article
- 3 LinkedIn posts
- 2 short-form video scripts
- 1 email newsletter
- 1 lead magnet/checklist
- 1 offer CTA asset

For every asset record: buyer, problem, offer connected, CTA, distribution channel, KPI, publication approval status, and resulting qualified traffic/conversions where available.

Track qualified traffic, calls, signups, product purchases, replies, assisted pipeline, and verified revenue where connected.

## 30-day operating plan

### Days 1–7 — Focus and evidence
- Select the primary buyer: Canadian SMB founder/COO/CTO/operations leader.
- Use AI Operations Assessment as the single core offer hypothesis.
- Build one landing-page outline without publishing it automatically.
- Research up to 100 potential accounts using lawful public business sources.
- Score the top 20 using the qualification model.
- Draft up to 20 personalized messages for human approval; do not send automatically.
- Create one lead magnet/checklist draft.
- Create three authority-post drafts.
- Connect payment evidence only in Stripe test mode.

### Days 8–14 — Start conversations under approval
- Submit approved outreach for human review before sending.
- Publish only approved content.
- Track replies, objections, and meetings with evidence.
- Refine the offer from observed buyer feedback.
- Prepare the $19–$39 digital product checkout path in test mode; no live launch without approval.
- Build a partner/referral research list.

### Days 15–21 — Convert and deliver
- Run discovery calls that are actually booked.
- Draft proposals from approved templates; pricing remains subject to approval.
- Create the client onboarding checklist.
- Prepare a paid assessment/pilot only after buyer approval and commercial acceptance.
- Record evidence of delivery and customer feedback.
- Improve the sales page and outreach sequence from measured results.

### Days 22–30 — Systemize
- Identify the best buyer segment from actual qualified responses.
- Identify the best-performing message and content asset using verified metrics.
- Document the sales-to-delivery workflow.
- Create a weekly executive dashboard.
- Decide what to double down on, improve, stop, or delegate.
- Keep all unknown commercial outcomes explicitly `UNKNOWN` or `NOT VERIFIED`.

## Customer and partner extensions

The system may prepare customer-health reports, retention opportunities, partner profiles, referral concepts, product-intelligence reports, claims/compliance reviews, and executive briefings.

Contracts, affiliate commitments, testimonials, refunds, security commitments, legal language, and client access require human approval.

## Stripe boundary

The current Stripe integration plan is **test-mode, Stripe-hosted Checkout, one-time payments** for the initial assessment/digital-product path.

No live Stripe product, price, payment link, subscription, refund, billing setting, or bank/payment configuration is changed by this specification.

A successful payment must be evidenced by Stripe payment data before being counted as `CLOSED_WON` or revenue.

## GitHub boundary

Repository changes are prepared on a review branch and must not be merged automatically.

Production deployments and merges remain human approval actions.

## Human approval queue

| Action | Why it matters | Draft/Details | Risk | Recommended decision |
|---|---|---|---|---|
| Send outreach | Creates external commercial communication | Evidence-backed draft | Reputation/CASL risk | Human review first |
| Publish content | Creates public claim/brand exposure | Approved content draft | Brand/claims risk | Human review first |
| Publish pricing/discount | Changes commercial terms | Offer/pricing proposal | Commercial risk | Executive approval |
| Send proposal | Creates a commercial commitment | Proposal draft | Contract/revenue risk | Executive approval |
| Start ads/spend | Creates financial exposure | Campaign plan | Financial risk | Executive approval |
| Change Stripe live settings | Enables real customer charges | Live product/price/payment configuration | Financial risk | Explicit approval |
| Merge/deploy code | Changes production system | Reviewed GitHub PR | Operational risk | Human approval |
| Access customer systems | Touches customer infrastructure/data | Access request | Security/privacy risk | Explicit customer + human approval |

## Daily report

```text
Revenue: verified cash collected / MTD / missing finance data
Pipeline: qualified leads / drafts / sent / replies / meetings / proposals / won / lost
Marketing: published / qualified inbound / conversions / best asset
Delivery: active work / blockers / capacity / client risks
Agent health: successes / failures / blocked integrations / data-quality issues
Approval queue: outbound / pricing / proposals / contracts / spending / deployment / client access
Top 3 actions: owner / deadline / expected commercial effect / evidence
Risks: business / customer / security / financial
Today’s revenue priority: one specific evidence-backed action
```

## Prohibited behavior

- No guaranteed income claims.
- No invented leads, customers, meetings, revenue, testimonials, or demand.
- No unsolicited external sending.
- No deceptive engagement or fake accounts.
- No autonomous spending, ads, refunds, contracts, pricing changes, payment changes, production deployments, or merges.
- Unknown values must be reported as `NOT VERIFIED` or `UNKNOWN`.

## Success condition

The agent succeeds when it improves the rate and quality of **qualified conversations, approved proposals, verified cash collected, customer value delivered, and retention**, using evidence that can be audited.
