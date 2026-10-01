# Multi-system reconciliation

Section 1 of the owner's *Multi-System Revenue Operating Command* (2026-10-01):
read every connected system before changing anything, then rank what the
evidence says. Counts only. This repository is public, so prospect names,
mailbox addresses and thread IDs stay out of it.

## 2026-10-01, 20:54 to 21:20 UTC

Read from a Claude session holding Gmail, PayPal, Calendly, Google Calendar,
Google Drive and GitHub. **Not available in this session: Stripe, Superhuman,
Etsy.** Stripe rows come from the owner's own reads and are labelled as such.
This adds to the day's kernel report ([`daily/2026-10-01.md`](daily/2026-10-01.md))
and to the evening re-read in draft PR #164. It does not replace either.

### Reconciliation table

| System | State | Evidence | Commercial significance |
|---|---|---|---|
| **Stripe** | Live. `charges_enabled` true, `payouts_enabled` true, 0 live charges, 0 webhook endpoints | OWNER-REPORTED 2026-10-01 (charges, payouts, 0 charges, 5 active storefront Payment Links, Quick-Audit Price CAD 249). Matches the owner's API read committed in `STRIPE_SETUP.md` on 2026-09-25 (`ad54d75`), which also records 0 webhook endpoints. Not re-read from here | Card checkout works. **Verified revenue: CAD 0.** With no webhook, a Payment Link sale reaches nothing ClearGlass runs. Stripe's own email is the only notice (see the inbox map below) |
| **Superhuman** | Not connected to this session | OWNER-REPORTED: one linked account, a Gmail address | That address is not the one the outreach was sent from or the forms post to. Working the pipeline in Superhuman shows none of it (D12) |
| **Gmail** (the outreach and form mailbox) | 0 replies, 0 bounces | Every outreach thread since 17 Sep still holds only sent messages. 0 messages from any recipient domain of those threads, or from mailer-daemon or postmaster, since 17 Sep, spam and trash included. 27 threads since 1 Oct, every one a newsletter, alert or notification | Conversations: 0. Nothing to answer tonight |
| | No Stripe mail, ever | `from:stripe.com`, all folders, trash included: 0 results | Stripe notifies some other mailbox. Which one is not recorded anywhere (AQ-1001-9) |
| **PayPal** | Reachable. CAD 0 incoming | Reporting API at 20:54 UTC, data refreshed to 18:29:59 UTC: 30 Sep to now holds 1 record, the funding event `T0700` of CAD 1.68, status Denied. Invoicing API: 0. Disputes API: 0 | The `401 Unauthorized` recorded in PR #164 (20:15 to 20:45 UTC) did not persist. AQ-1001-8 may not be needed |
| **Calendly** | 0 bookings | 0 events since 1 Sep, active or canceled. The account is on a Hotmail address | Meetings: 0 |
| **Google Calendar** | 0 events | 1 to 9 Oct | — |
| **Private pipeline sheet** | 0 calls logged | Drive `modifiedTime` 2026-09-30 19:46:39 UTC, the minute it was created | AQ-1001-1 (the calls) has not started |
| **Etsy** | Not connected to this session | `tools/growth_registry.py --check`: 0 opportunities, 0 experiments, 0 competitor observations | No marketplace signal is claimed. Etsy stays market intelligence only, lowest in the source hierarchy |
| **GitHub** | `main` at `031cdcd`. 1 open PR (#164, draft, another session). The 10 newest Actions runs failed or were cancelled in 2 to 11 s | GitHub API at 20:55 UTC. Same pattern as F1 in `CLAUDE.md` | Engineering is not the bottleneck. No scheduled automation can run until the org setting is fixed |
| **Website** | The primary offer's own page could not take a card payment | `offers/security-quick-audit.html`: "Buy a Quick-Audit" was a `mailto:` asking for a checkout link to be emailed back, under a comment reading "paste $249 Quick-Audit Payment Link". The live link was only on `store.html` and `pricing.html` | **Fixed in this change.** The button opens the catalog's live checkout; `tests/test_quick_audit_checkout.py` keeps the two in step. Goes live when the owner merges |

### Corrections to the record

1. **D1 was stale for six days.** The decision log (opened 2026-09-25) and the
   daily reports of 30 September and 1 October treat Stripe's charge state as
   unknown, last known `false` on 2026-08-05. The owner committed an API read
   showing `charges_enabled: true` on 2026-09-25 (`ad54d75`, in
   `STRIPE_SETUP.md`), and reported the same today. D1 is closed in
   [`revenue-decisions.md`](revenue-decisions.md).
2. **"20 pages" carried the CAD 249 offer, but only 2 carried its Payment Link.**
   The kernel's entry-offer table listed the Quick-Audit's payment path as
   "Stripe Payment Link plus e-Transfer" across 20 pages. Before this change,
   `store.html` and `pricing.html` were the only pages with the link.
3. **Payment Link counts disagree.** The site publishes 9 distinct Stripe
   links: `…Ni00` to `…Ni08`. The catalog holds 5 (`…Ni03` to `…Ni06`, `…Ni08`),
   D1 said nine, and the owner's read today counted 5 active storefront links.
   The other four are `…Ni00`, `…Ni01` and `…Ni02` on `checkout/index.html`
   (the CAD 297 audit and the two Business Protection plans), and `…Ni07` on
   `offers/guardian-command-nexus-blueprint.html` (CAD 199). If any of these is
   deactivated in Stripe, a buyer who clicks it gets an error page (AQ-1001-10).

### Where each signal lands

The same owner works from four mailboxes. Named here by provider only.

| Signal | Lands in | Read by a connected system? |
|---|---|---|
| Replies to outreach | Gmail mailbox A (the sending account) | Yes: Gmail connector |
| Website form leads (FormSubmit) | Gmail mailbox A | Yes, once the relay is activated (D11) |
| Offer-page buyer emails and the e-Transfer contact | iCloud (the published contact address) | No |
| Calendly booking notices | Hotmail (the Calendly account) | Only through the Calendly API |
| Stripe payment notices | Unknown. Not mailbox A | No |
| Superhuman | Gmail mailbox B | No connector here. Receives none of the rows above |

The one signal that proves revenue, a Stripe payment, goes to a mailbox
nothing reads on a schedule. A Quick-Audit bought by card tonight would wait
until the owner happened to open it, against a published 3-business-day
delivery promise.

### What the operating command asks for, and where it already exists

Most of the 22 sections are already built and tested. They are not deployed,
because nothing needs them at CAD 0.

| Section | Already in this repository | State |
|---|---|---|
| §4 pipeline with an auditable record per transition | `control-plane/app/order_states.py`, `commerce_orders.py`, the `events` ledger (`app/audit.py`) | Built, tested, not deployed |
| §6 Stripe idempotency, refunds and disputes reduce revenue | Migration 004 (idempotent webhook), `order_ledger.revenue_breakdown` (migration 009) | Built, tested. Not on the Payment Link path: 0 webhook endpoints |
| §7 outreach: research, draft, review, send | `bots/outreach_preflight.py`, `offers/outreach/README.md` rule 7 | In use. Blocks every send until D4 is closed |
| §12 human approval gates | `app/governance.py` `ALWAYS_ESCALATE`, the approval queue in each daily report | In use |
| §14 reconciliation, never silent repair | `control-plane/app/reconciliation.py` (reports, never writes) | Built, not deployed |
| §17 Etsy and marketplace intelligence held to evidence | `tools/growth_registry.py`, `data/growth/` | Built. 0 entries |
| §19 to §20 daily loop and end-of-day report | `docs/revenue/daily/` | Run by hand. Scheduled runs blocked by F1 |
| §13 post-payment automation | Webhook → order → fulfillment in `control-plane/` | Deploy at the first card sale, not before. Until then, the owner fulfils by hand from Stripe's email |

Nothing in the table is missing a line of code that stands between today and
the first payment. The gaps are owner settings and owner time.

### Approval queue: additions

AQ-1001-1 to AQ-1001-8 stand as written in the daily report and PR #164.

| ID | Action | Why it matters | Risk | Exact change |
|---|---|---|---|---|
| AQ-1001-9 | Confirm where Stripe sends successful-payment email, and that it is on | With 0 webhooks it is the only notice of a card sale | None | Stripe Dashboard, your user's notification settings: turn on email for successful payments. Send it to a mailbox you read daily, ideally mailbox A |
| AQ-1001-10 | Check the 9 published Payment Links are active | Owner's read counted 5 active. A deactivated link shows the buyer an error | None to check. Removing a link from a page is a gated pricing-page edit | Stripe Dashboard → Payment Links: confirm `…Ni00`, `…Ni01`, `…Ni02` and `…Ni07` are active. Name any that are not, and each one comes off its page |
| AQ-1001-11 | Merge the Quick-Audit button change | The primary offer's page can now take a card payment | Low. Same link, same CAD 249 price already on `store.html` and `pricing.html`. Refund and authorization terms are still missing from every paid page (D3), as they already were | Merge this pull request after AQ-1001-9 |

### Next highest-value action

```text
NEXT REVENUE ACTION:
Tonight, 5 minutes: AQ-1001-9 (Stripe payment email to a mailbox you read),
then merge the Quick-Audit button change (AQ-1001-11).
Friday 2 October, 09:00 to 12:00 Eastern: the calls in PR #164's plan,
accounting and legal firms first. A firm that says "send me something"
now gets a page it can pay on.
```

**Evidence for "nothing moved":** PayPal 1 denied funding record and 0 invoices
(20:54 UTC); Gmail 0 replies (20:56 UTC); Calendly 0 events (20:54 UTC); sheet
`modifiedTime` 2026-09-30 19:46:39 UTC.
