# Revenue Funnel

**As of 2026-09-29, 22:20 UTC** (connected systems re-read 22:16–22:20 UTC). Every count is labelled VERIFIED, PENDING, PIPELINE,
TEST or UNKNOWN. Only VERIFIED processor payments count as revenue. All of
them are zero today.

**Re-read 2026-09-30, 17:04–17:20 UTC: no stage changed.** 0 replies,
0 bookings, CAD 0 in PayPal. See [`daily/2026-09-30.md`](daily/2026-09-30.md).

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
| Leads (inbound) | 0 received through the site forms since they were pointed at the owner's mailbox (2026-09-06) | VERIFIED: no email from formsubmit.co in the mailbox, in any folder including spam and trash (mailbox search, 2026-09-29 22:20 UTC). No activation email is in the mailbox either, so the relay has not been activated (**D11**). Until 2026-09-29 the homepage signup also reported "Thanks" for a submission the relay refused (fixed; `tests/test_homepage_subscribe_handler.py`) | The owner's mailbox, through the formsubmit.co relay on 4 pages. The CRCS `leads` table is not deployed. Until 2026-09-29 the homepage's direct-contact address was on `clearglassinc.com`, which has no MX record, so mail to it bounced (see below) | `index.html`, `offers/*.html` form actions |
| Leads (outbound) | Quick-Audit: 9 contacted on 2026-09-20 (8 firms, 1 business association); 1 follow-up sent 2026-09-22; 7 follow-ups sent 2026-09-29, 21:29–21:31 UTC, without a mailing address (**D4**). The business-association and municipal vendor-intake threads were also followed up 2026-09-29. Other outbound 18–20 Sep: 4 cold emails to enterprise engineering leads | VERIFIED (owner's sent mail, read 2026-09-29 22:18 UTC) | Owner's mailbox. `offers/outreach/lead-list-oakville-burlington.csv` still reads `Status: New` on every row: the sheet is not being updated | Sent messages |
| Replies | 0 of 14 commercial threads; 0 bounces | VERIFIED (mailbox search by recipient domain, 2026-09-29 22:19 UTC, 50 minutes after the follow-ups) | Owner's mailbox | — |
| Qualified | 0 | VERIFIED | Would follow a reply | — |
| Conversations | 0 | VERIFIED | — | — |
| Meetings | 0 | VERIFIED: no Calendly booking since 2026-09-01, active or canceled (Calendly API, 2026-09-29 22:17 UTC) | Calendly `30min` event, still named "30 Minute Meeting" | Event type active since 2026-09-14 |
| Proposals | 0 | VERIFIED | — | — |
| Checkout started | 0 | UNKNOWN | Stripe (no connector in this session; network policy blocks `buy.stripe.com`) | — |
| Paid | CAD 0 | VERIFIED for PayPal: 76 records 30 Aug–29 Sep, every one a funding (`T0700`), outgoing pre-approved payment (`T0003`) or currency-conversion (`T0200`) event; 0 incoming customer payments, 0 invoices, 0 disputes (PayPal API, 2026-09-29 22:17 UTC). UNKNOWN for Stripe | Stripe and PayPal dashboards; control-plane ledger once deployed | — |
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
it. Nine first touches drew no replies in nine days. The seven follow-ups went
out on 29 September at 21:29–21:31 UTC, threaded to the originals. Most open
with a fact read from the prospect's public DNS records, and each offers a
one-word exit ("pass" or "covered"), so silence becomes a recorded answer.

The playbook allows at most two follow-ups, so each of these prospects has one
touch left. From here a reply is the only event that moves the number: answer
it the same business day, with a signature that passes
`python -m bots.outreach_preflight` (which needs **D4** closed). New prospects
are the other lever, and they are also gated on **D4**.
