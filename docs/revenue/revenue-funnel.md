# Revenue Funnel

**As of 2026-09-25.** Every count is labelled VERIFIED, PENDING, PIPELINE,
TEST or UNKNOWN. Only VERIFIED processor payments count as revenue. All of
them are zero today.

## Stage by stage

| Stage | Count | Label | Where it is recorded | Evidence |
|---|---|---|---|---|
| Visitors (website) | unknown | UNKNOWN | Nowhere: `analytics.js` ships with `provider: ""` | `analytics.js` CONFIG |
| Reach (LinkedIn) | 1,059 members reached, 2,029 impressions, week of 15–21 Sep | VERIFIED (owner export) | Owner's LinkedIn analytics | `AggregateAnalytics_…_2026-09-15_2026-09-21.xlsx` |
| Offer seen | unknown | UNKNOWN | Nowhere | Analytics off |
| Leads (inbound) | unknown | UNKNOWN | The owner's mailbox, through the formsubmit.co relay on 4 pages. The CRCS `leads` table is not deployed | `index.html`, `offers/*.html` form actions |
| Leads (outbound) | 10 listed, 0 contacted | VERIFIED | `offers/outreach/lead-list-oakville-burlington.csv` | Every row `Status: New` |
| Qualified | 0 | VERIFIED | Same file (would become `Qualified` after a reply) | — |
| Conversations | 0 | VERIFIED | — | — |
| Meetings | 0 | UNKNOWN until the Calendly bookings are read | Calendly `30min` event | Event type is active (Calendly, 2026-09-24) |
| Proposals | 0 | VERIFIED | — | — |
| Checkout started | 0 | UNKNOWN | Stripe (unreadable in this session) | — |
| Paid | CAD 0 | VERIFIED for PayPal (0 incoming in 30 days, read 2026-09-24). UNKNOWN for Stripe | Stripe and PayPal dashboards; control-plane ledger once deployed | — |
| Delivered | 0 | VERIFIED | — | — |
| Repeat / recurring | CAD 0 MRR | VERIFIED (no subscriptions table deployed) | — | — |

Pipeline value: **CAD 0**. Ten uncontacted names are not pipeline.

## How each transition is recorded today

Every transition needs a timestamp, source, status, owner, next action and
evidence. Until the control plane is deployed, the records are split:

| Transition | Record | Timestamp | Evidence to keep |
|---|---|---|---|
| Listed → Contacted | Lead sheet row: `Status`, `Next_action` | Send date | Copy of the sent email |
| Contacted → Qualified | Lead sheet row | Reply date | The reply |
| Qualified → Meeting | Calendly booking | Booking time | Calendly event |
| Meeting → Proposal | Lead sheet row | Send date | The proposal or statement of work (template: `docs/CLEARGLASS-24H-RESCUE-SALES-KIT.md` §3) |
| Proposal → Paid | Stripe or PayPal dashboard, or a bank record for e-Transfer | Processor time | Processor reference. A payment redirect is not proof |
| Paid → Delivered | Delivery report | Delivery date | Report and customer confirmation |

**Privacy constraint.** This repository is public, so a live pipeline with
named prospects, replies and deal notes must not be kept here. Keep the working
copy of the lead sheet somewhere private (**D6** in
[`revenue-decisions.md`](revenue-decisions.md)). After the control plane is
deployed, the CRCS `leads`, `lead_activities` and `orders` tables hold these
transitions, and every one also writes to the append-only ledger, which feeds
the Slack revenue channel (`docs/REVENUE_OPERATIONS.md` § Slack revenue channel).

## The one number to move this week

**Conversations: 0 → 5.** Every later stage depends on it, and no code changes
it. The drafts for the first 10 conversations were delivered to the owner
privately, not committed here.
