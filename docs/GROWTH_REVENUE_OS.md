# ClearGlass Growth, Advertising & Revenue Operating System

**Status: BUILT AND TESTED LOCALLY. NOT DEPLOYED. NO LIVE PAYMENT TAKEN.**
Evidence date: **2026-09-24**. Branch `percival/charming-euler-3k9vu5`, from `main` at `dc8c78e`.

This document maps the master business loop onto the code that implements each
stage, records what this change added, and closes with the executive revenue
report. Everything marked **VERIFIED** has a test, a command output, or an API
read behind it. Everything else says **NOT VERIFIED** and why.

It extends, and does not replace, the CRCS design package in
[`docs/crcs/`](crcs/README.md) and the revenue definitions in
[`REVENUE_COMMAND_SYSTEM.md`](REVENUE_COMMAND_SYSTEM.md).

---

## 1. The loop, stage by stage

| Stage | Where it lives | State |
|---|---|---|
| Market intelligence | `scripts/market_intelligence_lane.py` (weekly scaffold, every signal marked unverified) | EXISTED |
| Demand discovery → opportunity | `tools/growth_registry.py` + `data/growth/opportunities.json` | **NEW**. Registry is empty: no demand is claimed |
| Audience, positioning, content | `clearglass_marketing_os_v2/`, `agents/*`, blog + Insights generators | EXISTED, unchanged |
| Advertising plan | `tools/campaign_registry.py` + `data/campaigns/` (5 drafts, all incomplete) | EXISTED |
| Advertising money | `control-plane/app/governance.py`: `create/fund/activate/scale_ad_campaign` always escalate | **NEW** gates |
| Landing page → offer | static site pages; offers in `control-plane/app/data/pricebook.json` (4 SKUs) | EXISTED |
| Lead | `POST /revenue/leads` (CRCS) | EXISTED |
| Order | `POST /commerce/orders` → `CG-ORD-YYYY-XXXXXXXX` | **NEW** |
| Stripe / PayPal | `POST /commerce/orders/{ref}/checkout` `{provider: stripe \| paypal}` | **NEW** (adapters existed) |
| Payment verification | `/webhooks/stripe` (signature, 300 s tolerance), `/webhooks/paypal` (PayPal verify API) | EXISTED; now also moves the ClearGlass order |
| Unified revenue ledger | `orders` table + `order_ledger.revenue_breakdown` | EXISTED; cockpit now splits Stripe / PayPal |
| Customer | `customers` via `upsert_customer_for_order` | EXISTED |
| Fulfillment | `service_orders`, opened only from verified **live** money on an unflagged order | EXISTED; now driven from the ClearGlass order |
| Reconciliation | `control-plane/app/reconciliation.py`, `POST /commerce/reconciliation`, `python -m app.reconciliation` | **NEW** |
| Revenue intelligence | `/revenue/cockpit`, admin `/revenue` page | EXTENDED |
| Experiments / optimization | `tools/growth_registry.py` + `data/growth/experiments.json` | **NEW**. Registry is empty |

---

## 2. Payment architecture

```text
                    OFFER (price book, server-side)
                              |
                POST /commerce/orders  ->  CG-ORD-2026-XXXXXXXX  (CREATED)
                              |
          POST /commerce/orders/{ref}/checkout {provider}
                 |                                   |
     Stripe Checkout Session                PayPal Orders v2 order
     metadata.cg_order_ref = ref            purchase_units[].invoice_id = ref
     client_reference_id   = ref            PayPal-Request-Id = ref-paypal
                 |                                   |
     checkout.session.completed             CHECKOUT.ORDER.APPROVED -> PAYMENT_PENDING
     (signed, 300 s tolerance)                 + capture approval queued (human)
                 |                          POST /paypal/capture (claims approval once)
                 |                          PAYMENT.CAPTURE.COMPLETED (PayPal-verified)
                 +------------------+----------------+
                                    |
                     order_ledger.record_payment_order   (idempotent on processor id)
                                    |
                     commerce_orders.on_payment_booked   (row-locked on Postgres)
                                    |
             PAID  |  PAYMENT_PROCESSING  |  PAYMENT_FAILED  |  flag RECONCILIATION REQUIRED
                                    |
          live + unflagged -> service order + operator_action_required event
```

Stripe and PayPal stay separate processors. ClearGlass keeps one record: the
`commercial_orders` row, with every processor settlement in `orders` pointing
back to it through `orders.order_ref`.

### Payment states

`CREATED → CHECKOUT_STARTED → PAYMENT_PENDING / PAYMENT_PROCESSING → PAID →
PARTIALLY_REFUNDED / REFUNDED / DISPUTED → CHARGEBACK`, plus `PAYMENT_FAILED`
and `CANCELED`. The full edge table is `control-plane/app/order_states.py`
`TRANSITIONS`; a PostgreSQL `CHECK` constraint (migration 010) refuses any
other value.

- Every state that says something about money can be entered **only on
  verified processor evidence**. A browser redirect, an unsigned webhook or a
  request body cannot make an order `PAID` (`test_money_states_need_verified_evidence`,
  `test_an_unsigned_stripe_event_cannot_pay_an_order`).
- Fulfillment is **derived** from the service order that exists, never stored:
  `NOT_STARTED`, `FULFILLMENT_PENDING`, `FULFILLING`, `COMPLETED`, or `HELD`
  while money is in question (refund, dispute, reconciliation flag).

### Duplicate payment protection

| Layer | Mechanism |
|---|---|
| Unique order id | `commercial_orders.order_ref` UNIQUE, 40 random bits, Crockford base32 |
| Second checkout | refused (409) once money is received or a payment is in flight |
| Double click / retry | Stripe idempotency key `ref:stripe:<hash(email)>`; `PayPal-Request-Id` |
| PayPal duplicate | `invoice_id = ref`; PayPal accounts refuse a repeated invoice id by default |
| Processor redelivery | `orders.external_ref` UNIQUE (migration 004) |
| Concurrent webhooks | `SELECT … FOR UPDATE` on the order row (Postgres) |
| Queued PayPal capture, order already paid by Stripe | `POST /paypal/capture` refuses (409) before claiming the approval, even if a human approved it |
| Both processors paid anyway | both rows kept, order flagged `DUPLICATE_PAYMENT`, fulfillment `HELD`, reported critical. Nothing is deleted; the fix is a refund at the processor |

### Reconciliation

`python -m app.reconciliation [--provider-export FILE] [--json]` (exit 2 on any
critical or high finding) or `POST /commerce/reconciliation` (admin). It reads
and reports; it never writes.

- **Always:** duplicate payments, paid-without-payment, payment-not-applied,
  amount / currency / environment mismatches, unknown order references,
  paid-without-fulfillment, fulfillment-without-payment, unlinked legacy
  payments, unmatched refund / dispute events, rejected webhooks, stale checkouts.
- **Only with a processor export:** payments missing from the ledger, ledger
  payments missing at the processor, and amount / currency / refund / status /
  livemode / dispute disagreements. Without an export the report says
  `NOT VERIFIED` and does not infer agreement. Raw Stripe Charge lists are
  accepted as-is; PayPal records must be normalized
  (`{provider, reference, amount, currency, status, amount_refunded, livemode}`).

Subscription renewals (`invoice.paid`) are booked into the ledger without an
order reference, because Stripe raises them long after checkout. Reconciliation
lists them as `UNLINKED_PAYMENT` (information); verified MRR comes from the
`subscriptions` table, not from ClearGlass orders.

### Attribution

The lead's own recorded campaign wins over anything the browser sends, and the
campaign travels server-side: lead → ClearGlass order → Stripe metadata
(`cg_utm_*`) → verified webhook → ledger row → cockpit "revenue by campaign".
A campaign code is `CG-<CHANNEL>-<AUDIENCE>-<OFFER>-<YYYY>-Q<n>`
(`tools/campaign_registry.py`). PayPal payments carry the campaign on the
ClearGlass order, not on the PayPal record.

---

## 3. Human authorization gates added

| Action | Score | Gate |
|---|---|---|
| `research_market_signals`, `analyze_attribution` | 5 | auto, logged |
| `estimate_ad_budget` / `draft_experiment` / `draft_ad_campaign` | 10–20 | auto, logged (drafts only) |
| `declare_experiment_winner` | 40 | queued for review |
| `create_ad_campaign` | 70 | **always escalate** |
| `send_mass_outreach` | 85 | **always escalate** |
| `activate_ad_campaign`, `record_manual_payment` | 88 | **always escalate** |
| `scale_ad_campaign`, `contractual_commitment`, `deploy_high_risk_change` | 90 | **always escalate** |
| `fund_ad_campaign` | 92 | **always escalate** |
| `activate_live_payments` | 100 | **always escalate** |

The same ad-spend and money actions are escalated in `agent_os/governance.py`,
so an agent-layer proposal cannot route around the control plane.
`launch_campaign`, already escalated in `agent_os`, is now in the control
plane's `ALWAYS_ESCALATE` too. `python -m app.daily_loop`
self-check: PASS.

---

## 4. Operating it

```bash
cd control-plane
python -m pytest tests/ -q                 # 692 passed, 5 skipped
python -m app.reconciliation --json        # ledger-internal reconciliation
python -m app.reconciliation --provider-export stripe_charges.json
python -m app.migrate --status             # 010_commercial_orders.sql pending on an existing DB
python3 ../tools/growth_registry.py --check
```

API, for the storefront and any landing page:

| Route | Who | Purpose |
|---|---|---|
| `POST /commerce/orders` `{sku, quantity, reference?, customer_email?, attribution?}` | public, rate limited | open a ClearGlass order |
| `POST /commerce/orders/{ref}/checkout` `{provider, customer_email?}` | public, rate limited | Stripe or PayPal checkout URL |
| `GET /commerce/orders/{ref}/status` | public, rate limited | `payment_verified` only after a signed webhook |
| `GET /commerce/orders`, `GET /commerce/orders/{ref}` | admin | orders with every linked payment |
| `POST /commerce/orders/{ref}/cancel` | admin | unpaid orders only |
| `POST /commerce/reconciliation` | admin | reconciliation report |
| `POST /paypal/capture` | admin | first call queues approval; after approval, next call captures once |

**PayPal webhook subscription must include `CHECKOUT.ORDER.APPROVED`** (so the
capture approval is queued the moment a buyer approves) as well as the capture,
refund, reversal and dispute events. The setup checklist is in
[`REVENUE_OPERATIONS.md`](REVENUE_OPERATIONS.md#paypal-setup-checklist--none-of-this-is-done).

---

## 5. Executive revenue report — 2026-09-24

### CURRENT STATE (before this change)

A governed Stripe + PayPal money engine already existed on `main` (`dc8c78e`):
signature-verified Stripe webhooks, PayPal webhooks verified through PayPal's
API, idempotent booking, refunds and disputes subtracted from revenue
(migration 009), UTM attribution to Stripe metadata, the CRCS lead pipeline, an
admin cockpit, and a risk-scored approval gate. Gaps found against the master
prompt:

1. No ClearGlass order id; nothing tied a Stripe and a PayPal payment for one
   purchase together, so a double payment was invisible.
2. No explicit payment state machine; "paid" was a ledger row status only.
3. **An approved PayPal capture never executed.** `POST /paypal/capture` only
   queued an approval and nothing ran it afterwards, so a buyer could approve
   a PayPal payment the system could never collect.
4. No reconciliation beyond a count of pending orders.
5. No Stripe / PayPal revenue split.
6. No advertising-spend gates beyond `launch_campaign`.
7. `GET /payouts` and `GET /payments/payout-account` were unauthenticated:
   payout amounts and masked bank details were readable by anyone.
8. The storefront success page told every returning buyer "your payment was
   received" before any webhook; the PayPal return URL (`/paypal/return`)
   pointed at a page that did not exist.

### CHANGES

| Area | Files |
|---|---|
| Order ids + state machine | `control-plane/app/order_states.py` (new), `commerce_orders.py` (new), `models.py`, `migrations/010_commercial_orders.sql` (new) |
| Checkout, both processors | `routers/commerce.py` (new), `schemas.py`, `main.py`, `paypal.py` (`invoice_id`), `payments.py` (mock id) |
| Verification → order | `order_ledger.py`, `routers/payments.py`, `routers/paypal.py`, `revenue_service.py` |
| PayPal capture executes once | `routers/paypal.py`, `service.py` (`claim_approval` moved here), `fulfillment.py` |
| Reconciliation | `reconciliation.py` (new) |
| Cockpit | `routers/revenue.py` (provider split, order states, flags, checkout count; CRCS checkout books a ClearGlass order) |
| Gates | `control-plane/app/governance.py`, `agent_os/governance.py` |
| Payout exposure | `routers/payments.py` |
| Owner view | `admin/lib/api.ts`, `admin/app/revenue/page.tsx` |
| Buyer view | `storefront/lib/api.ts`, `storefront/lib/order-session.ts` (new), `storefront/lib/OrderStatusPanel.tsx` (new), `storefront/app/cart/page.tsx`, `storefront/app/success/page.tsx`, `storefront/app/paypal/return/page.tsx` (new) |
| Growth evidence | `tools/growth_registry.py` (new), `data/growth/opportunities.json`, `data/growth/experiments.json` (new, empty) |
| Tests | `control-plane/tests/test_order_states.py` (42), `test_commerce_orders.py` (42), `test_reconciliation.py` (30), `tests/test_growth_registry.py` (27), `test_route_auth_coverage.py` (two documented exemptions) |

### VERIFIED

- Control plane: **692 passed, 5 skipped** (baseline 446 / 5). `ruff check` clean.
- Six protections mutation-tested: removing the duplicate check, accepting
  unverified evidence, restoring the old capture route, fulfilling flagged
  orders, allowing checkout on a paid order, and capturing PayPal for an order
  Stripe already paid each turn a test red.
- PostgreSQL 16: migrations 001–010 applied, re-run is a no-op, `migrate --check`
  reports no missing column, `test_migrate` 9/9, and the `CHECK` constraint
  rejects an invalid state.
- End to end on PostgreSQL: order → Stripe checkout → unverified before webhook
  → signed webhook → `PAID` + service order → PayPal capture for the same order
  → flagged `DUPLICATE_PAYMENT`, fulfillment `HELD`, both payments kept →
  reconciliation 1 critical → cockpit Stripe 297 / PayPal 297.
- Admin app: `tsc --noEmit` and `next build` pass; `/revenue` rendered in
  Chromium showing the processor split and the flagged order.
- Storefront: `tsc --noEmit` and `next build` pass; in Chromium the cart offers
  card and PayPal, the success page shows "Payment submitted" until a signed
  webhook arrives, then "Payment verified"; the PayPal return page states that
  nothing is charged until capture.
- Growth registry: 27 tests; the z-test value is cross-checked against
  `statistics.NormalDist` (z = 2.1027, p = 0.0355 for 100/1000 vs 130/1000).
- `scripts/ci_local.py`: 10 of 10 offline gates pass (Lighthouse skipped: network).
- `python -m app.daily_loop`: governance self-check PASS.

### NOT VERIFIED

- Any production behaviour. Nothing is deployed and no control-plane host is
  known to exist (see BLOCKERS).
- Stripe account state. No Stripe connector in this session; last verified
  **2026-08-05**: `charges_enabled: false`, `payouts_enabled: false`
  (`STRIPE_SETUP.md`).
- Render hosting. The Render connector requires choosing a workspace, which is
  the owner's decision; it was not chosen. The CRCS package (2026-09-24) found no
  control-plane service or database.
- Live PayPal webhook delivery, PayPal `invoice_id` duplicate blocking on this
  account, and a real capture. Covered by tests with a stubbed transport only.
- GitHub Actions: dispatches no runners (`CLAUDE.md`), so no CI signal exists
  for this change beyond the local runs above.

### STRIPE

Code: checkout, subscriptions, billing portal, signed webhooks, refunds and
disputes, payouts, and now ClearGlass orders. Account: **cannot charge** as of
the last verification (2026-08-05). Live Prices exist for `risk-audit-90`,
`business-protection-monthly`, `business-protection-annual`.

### PAYPAL

Code: server-priced Orders v2, verified webhooks, gated capture (now executable
once approved), refunds, reversals, disputes. The PayPal account connected to
this session was read on 2026-09-24 (read-only, 30 days to 12:29 UTC): 90
transactions, of which 14 succeeded, all of them outgoing pre-approved payments
and their funding and currency-conversion legs. **0 incoming sales. 0
disputes.** Whether this is a business account able to receive ClearGlass sales
is NOT VERIFIED. No PayPal credentials or webhook id are configured in any known
host.

### PRODUCTS

Price book (`control-plane/app/data/pricebook.json`): `rapid-website-deployment-diagnostic`
CAD 125 (placeholder, no Stripe Price), `risk-audit-90` CAD 297,
`business-protection-monthly` CAD 100/month, `business-protection-annual`
CAD 1,000/year. Four different entry prices remain public across the site
(CRCS S5): PRICING DECISION — NOT MADE.

### CHECKOUT

Built: storefront single-offer carts → ClearGlass order → card or PayPal;
multi-offer carts → Stripe as before; CRCS `/revenue/checkout` → ClearGlass
order. Available to a real buyer today: **none verified**, because no host is
deployed and Stripe cannot charge.

### PAYMENTS · REVENUE · CUSTOMERS

**Verified live payments: 0. Verified revenue: CAD 0. Verified customers: 0.**
Every order in this document was created in a throwaway local database.

### CAMPAIGNS · ATTRIBUTION

Measured campaigns: **0**. `data/campaigns` holds 5 draft packages, none
approved or complete. No advertising money was spent or authorized. Attribution
is wired end to end but has never carried a real sale.

### FULFILLMENT

Outstanding: none (no paid order exists).

### RECONCILIATION

Unmatched records in any real ledger: NOT VERIFIED (no deployed database).
Running `python -m app.reconciliation` against production is the first check to
do after deploy.

### SECURITY

Payout routes gated; public order routes are rate limited and server-priced,
accept only SKU and quantity, and the public status route returns no PII or
processor id; order ids are
random; webhooks are authenticated, replay-limited (Stripe 300 s) and idempotent;
money states need verified evidence; the audit ledger stores no email addresses
from the new paths. The auth-coverage test lists the two new public POST routes
with written reasons.

### CI/CD

Local gates green (above). GitHub Actions: BLOCKED — PRE-EXISTING / VERIFIED CI
FAILURE (no runners since 2026-09-06, organisation settings). GitHub Pages
still deploys from the branch; the control plane, storefront and admin deploy
separately and are not deployed.

### BLOCKERS (none of them is code)

1. Stripe onboarding incomplete: `charges_enabled: false` (owner, Stripe Dashboard).
2. No control-plane host or database (owner approval to create them from `render.yaml`).
3. PayPal: confirm a business account, then set `PAYPAL_CLIENT_ID`,
   `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID` and `PAYPAL_API_BASE` on the host.
4. One entry price must be chosen and the other three retired.
5. PayPal capture is human-approved per order by existing policy. It is safe
   and now works, but it adds delay between a buyer's approval and the charge.
   Keeping or relaxing it is an owner decision; this change keeps it.

### NEXT AUTHORIZED REVENUE ACTION

No software action can produce revenue until blocker 1 or 3 is cleared. The
next action is the owner's: complete the past-due Stripe onboarding items so
`charges_enabled` reads `true`, and approve creating the control-plane host
(CRCS checklist H1, H2). The first check after deploy is
`python -m app.reconciliation --json` against the production database.
