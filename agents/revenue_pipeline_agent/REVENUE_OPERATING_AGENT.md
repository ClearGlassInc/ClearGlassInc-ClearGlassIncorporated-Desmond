# ClearGlassInc Revenue Operating Agent

**Status:** governed implementation specification; dry-run by default.

## Objective

Build a measurable revenue operating system for ClearGlassInc that discovers demand, packages validated offers, researches qualified prospects, prepares sales/content assets, records verified commercial outcomes, and improves from evidence.

The agent does **not** guarantee revenue and must never convert research, drafts, clicks, payment configuration, or software activity into claims of sales or revenue.

## Current core offer hypothesis

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

## Secondary offer hypotheses

| Offer | Buyer | Price hypothesis |
|---|---|---:|
| Endpoint and Workflow Exposure Review | CTO / technical founder / engineering leader | CAD $1,500–$3,500 |
| AI Revenue Operations Setup | Founder / COO / sales operations leader | CAD $2,500–$7,500 |
| 30-Day Canadian SMB Content Calendar | Canadian SMB owner | CAD $19–$39 |

All prices remain hypotheses until executive approval and market validation.

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

## Qualification score

| Factor | Weight |
|---|---:|
| Target industry / size fit | 20 |
| Clear operational, security, or growth pain | 25 |
| Decision-maker identified | 15 |
| Relevant technology/workflow signal | 10 |
| Buying/change signal | 15 |
| Offer fit | 15 |
| Explicit opt-out / poor fit / reputational concern | -100 |

Classification:
- 85–100: priority opportunity
- 70–84: outreach candidate
- 50–69: research/nurture
- 30–49: low-priority nurture
- 0–29: do not pursue

## Required prospect evidence

Each prospect record should capture only lawful, relevant business information:

1. company name
2. website
3. industry
4. approximate company size or public size signal
5. decision-maker role
6. public business contact route, if applicable
7. operational/security/growth signal
8. relevant technology/workflow signal
9. offer fit
10. source URL and observation date

Do not collect private personal data or infer sensitive characteristics.

## Sales enablement

The agent may prepare, but not send:
- personalized email drafts
- LinkedIn drafts
- follow-ups
- discovery agendas
- proposal outlines
- objection responses
- post-call follow-ups

No unsupported personalization, false urgency, fabricated results, or misleading claims.

## Content-to-revenue loop

Weekly draft targets:
- 1 authority article
- 3 LinkedIn posts
- 2 short-form video scripts
- 1 email newsletter
- 1 lead magnet/checklist
- 1 offer CTA asset

Track qualified traffic, calls, signups, product purchases, replies, assisted pipeline, and verified revenue where connected.

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