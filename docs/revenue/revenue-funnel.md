# Revenue Funnel

**As of 2026-09-29.** Every count is labelled VERIFIED, PENDING, PIPELINE,
TEST or UNKNOWN. Only VERIFIED processor payments count as revenue. All of
them are zero today.

**Correction.** The 2026-09-25 version of this table said 0 outbound leads
were contacted. That was wrong when it was written: the Quick-Audit emails went
out on 2026-09-20. The rows below are re-read from the connected systems on
2026-09-29. Counts only: prospect names stay out of this public repository.

## Stage by stage

| Stage | Count | Label | Where it is recorded | Evidence |
|---|---|---|---|---|
| Visitors (website) | unknown | UNKNOWN | Nowhere: `analytics.js` ships with `provider: ""` | `analytics.js` CONFIG |
| Reach (LinkedIn) | 1,059 members reached, 2,029 impressions, week of 15–21 Sep | VERIFIED (owner export) | Owner's LinkedIn analytics | `AggregateAnalytics_…_2026-09-15_2026-09-21.xlsx` |
| Offer seen | unknown | UNKNOWN | Nowhere | Analytics off |
| Leads (inbound) | unknown | UNKNOWN | The owner's mailbox, through the formsubmit.co relay on 4 pages. The CRCS `leads` table is not deployed. Until 2026-09-29 the homepage's direct-contact address was on `clearglassinc.com`, which has no MX record, so mail to it bounced (see below) | `index.html`, `offers/*.html` form actions |
| Leads (outbound) | Quick-Audit: 9 contacted on 2026-09-20 (8 firms, 1 business association); 1 follow-up sent 2026-09-22; 7 follow-ups drafted 2026-09-29, not sent. Other outbound 18–20 Sep: 1 municipal vendor-intake thread, 4 cold emails to enterprise engineering leads | VERIFIED (owner's sent mail, read 2026-09-29) | Owner's mailbox. `offers/outreach/lead-list-oakville-burlington.csv` still reads `Status: New` on every row: the sheet is not being updated | Sent messages |
| Replies | 0 of 14 commercial threads; 0 bounces | VERIFIED (mailbox search by recipient domain, 2026-09-29) | Owner's mailbox | — |
| Qualified | 0 | VERIFIED | Would follow a reply | — |
| Conversations | 0 | VERIFIED | — | — |
| Meetings | 0 | VERIFIED: no Calendly booking since 2026-09-01, active or canceled (Calendly API, 2026-09-29) | Calendly `30min` event, still named "30 Minute Meeting" | Event type active since 2026-09-14 |
| Proposals | 0 | VERIFIED | — | — |
| Checkout started | 0 | UNKNOWN | Stripe (no connector in this session; network policy blocks `buy.stripe.com`) | — |
| Paid | CAD 0 | VERIFIED for PayPal: 72 records 30 Aug–29 Sep, every one a funding (`T0700`) or outgoing pre-approved payment (`T0003`) event; 0 incoming customer payments, 0 invoices, 0 disputes (PayPal API, 2026-09-29). UNKNOWN for Stripe | Stripe and PayPal dashboards; control-plane ledger once deployed | — |
| Delivered | 0 | VERIFIED | — | — |
| Repeat / recurring | CAD 0 MRR | VERIFIED (no subscriptions table deployed) | — | — |

Pipeline value: **CAD 0**. Contacted prospects who have not replied are not
pipeline.

**Inbound path defect (found and fixed 2026-09-29).** `clearglassinc.com`
publishes no MX record (MX NoAnswer on the apex and on `www`; the A records are
GitHub Pages, which accepts no mail). The homepage "Email Desmond" button, its
Outlook compose link, two counter-UAS page CTAs, both `security.txt` copies,
`SECURITY.md`, `CODE_OF_CONDUCT.md` and the GitHub issue-template inquiry link
all pointed at addresses on that domain, so a prospect who used them got a
bounce and ClearGlass never saw the lead. They now point at the address the
offer pages and outreach already use. `tests/test_contact_addresses.py` keeps
it that way until the domain accepts mail. Making the domain mailbox work is
still owner decision **D5**.

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
it. Nine first touches drew no replies in nine days. The seven follow-ups sit
as drafts in the owner's mailbox, threaded to the originals. Each opens with a
fact read from the prospect's public DNS records and offers a one-word exit
("pass" or "covered"), so silence becomes a recorded answer. None can be sent
until a CASL mailing address is filled in (**D4**).
