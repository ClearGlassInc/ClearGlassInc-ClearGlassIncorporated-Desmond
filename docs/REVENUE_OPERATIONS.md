# Revenue operations

How money reaches ClearGlass, what is actually wired, and what is still missing.

Read `CLAUDE.md` first for the commerce OS safety model. This document covers
the payment paths specifically.

## Status, honestly

| Channel | Code | Credentials | Verified end to end | Booking revenue |
|---|---|---|---|---|
| Stripe Checkout | Built | Runtime env vars; see `STRIPE_SETUP.md` | Not verified in this change | See `STRIPE_LIVE_READINESS.md` |
| Stripe subscriptions | Built | As above | Not verified in this change | As above |
| PayPal Orders v2 | **Built in this change** | **None configured** | **No — sandbox test not yet run** | **No** |
| Etsy Open API v3 | Built, writes human-gated | OAuth2 handshake required (`ETSY_CONNECT.md`) | Connection state is credential presence only | Reconciliation only |
| Printful fulfillment | Built, confirmation human-gated | None configured | No | n/a |

**No integration is live until a sandbox test and a production verification have
both been recorded.** PayPal in particular is code-complete and credential-empty:
it runs in mock mode, creates no order at PayPal, and books nothing. Nothing in
this repository should be read as a statement that it is taking payments.

This machinery enables income; it does not produce it. It cannot create products,
customers, or demand, and no part of it should be described as guaranteeing
revenue.

## The rule every channel obeys

**A redirect is not a receipt.** A browser success page proves the customer
reached a URL, nothing more — anyone can open it. Fulfillment starts only when a
server-side webhook, whose signature verified, says the money arrived.

Three consequences, all enforced in code:

1. **Prices are resolved server-side.** `POST /checkout/session` and
   `POST /paypal/order` take SKUs and quantities only. Amounts come from
   `control-plane/app/pricebook.py`. `tests/test_pricebook.py` asserts the
   `CheckoutLineItem` schema is exactly `{sku, quantity}` — do not add a
   price-shaped field back to that contract.
2. **Booking is idempotent.** Both processors settle through
   `control-plane/app/order_ledger.py`, keyed on `orders.external_ref`. A
   redelivered webhook is a no-op, not a second sale. A pending order that later
   settles is *promoted*, not duplicated.
3. **Money in does not imply a parcel out.** A paid order that cannot be
   reconciled or shipped becomes `unfulfillable` and stays visible. It is never
   quietly marked done.

## Stripe

Documented in `STRIPE_SETUP.md` and `STRIPE_LIVE_READINESS.md`. Key behaviours:

- `checkout.session.completed` books `paid` only when `payment_status` is paid;
  asynchronous methods stay `pending` until `async_payment_succeeded`.
- `invoice.paid` books subscription renewals; the first invoice of a subscription
  is skipped because its checkout session already booked it.
- Refunds, disputes and failed payments are logged for a human, never actioned.
- Payout events record masked destination metadata only — never account or
  routing numbers.

## PayPal

Built in `control-plane/app/paypal.py` and `control-plane/app/routers/paypal.py`.

**Flow:** `POST /paypal/order` (cart) or `POST /commerce/orders/{ref}/checkout`
with `provider: paypal` (a ClearGlass order, see `docs/GROWTH_REVENUE_OS.md`)
creates a CAPTURE-intent order priced from the price book → buyer approves at
PayPal → `CHECKOUT.ORDER.APPROVED` moves the ClearGlass order to
`PAYMENT_PENDING` and queues a `paypal_capture_order` approval → a human
approves it → `POST /paypal/capture` claims that approval once and captures →
`PAYMENT.CAPTURE.COMPLETED` webhook books the order.

Before 2026-09-24 the capture step was a dead end: `POST /paypal/capture` only
queued an approval, and nothing ever ran an approved one.

**What is deliberately not fulfillment:**

- `CHECKOUT.ORDER.APPROVED` — the buyer clicked pay. The money has not moved.
  Logged and the capture approval queued; never booked.
- `PAYMENT.CAPTURE.PENDING` — PayPal is holding the capture for review. Booked
  as `pending`; treating a held capture as revenue reports money that may never
  land.
- `PAYMENT.CAPTURE.DENIED` / `DECLINED` — booked as `failed`.

**Verification fails closed.** PayPal signs with a certificate chain, and the
supported way to check it is PayPal's own `verify-webhook-signature` API. That
requires working credentials *and* `PAYPAL_WEBHOOK_ID`. Missing either, a
verification API that is unreachable, a missing signature header, or a
certificate URL that is not on a PayPal host — each is a rejection. There is no
development shortcut that accepts an unverified PayPal event, because unlike a
signature we compute ourselves there is nothing to fall back to.

**Catalogue reconciliation.** Each order carries its SKUs in `custom_id`. On
capture, `check_against_catalog` re-prices that cart from the price book and
compares. A mismatch does not reject the payment — the money has arrived and
cannot be un-received — but the order is marked `unfulfillable`, a
`paypal_capture_catalog_mismatch` event is written, and nothing ships until a
human looks.

**Recurring plans are refused.** PayPal bills subscriptions through a different
API with its own plan objects; charging one once as a one-off would take the
first payment and silently never take another.

### PayPal setup checklist — none of this is done

- [ ] Create a PayPal REST app; record the client ID and secret.
- [ ] Set `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` in the platform secret
      manager. Never in source control.
- [ ] Create a webhook subscription pointing at `POST /webhooks/paypal`,
      subscribed to `PAYMENT.CAPTURE.COMPLETED`, `PENDING`, `DENIED`,
      `DECLINED`, `REFUNDED`, `REVERSED`, `CUSTOMER.DISPUTE.CREATED`,
      `UPDATED`, `RESOLVED`, and `CHECKOUT.ORDER.APPROVED`.
- [ ] Set `PAYPAL_WEBHOOK_ID` to that subscription's id. Until this is set, every
      notification is refused and no PayPal payment will ever be booked.
- [ ] Set `PAYPAL_RETURN_URL` to the storefront's `/paypal/return` and
      `PAYPAL_CANCEL_URL` to its `/cancel` (both pages exist).
- [ ] Run a full sandbox purchase against `PAYPAL_API_BASE` =
      `https://api-m.sandbox.paypal.com`; confirm one order row, `paid`, with the
      catalogue amount, and confirm a redelivered webhook adds nothing.
- [ ] Only then point `PAYPAL_API_BASE` at `https://api-m.paypal.com` and repeat
      the verification with a real low-value purchase.
- [ ] Record both verifications in `docs/CHANGELOG.md` before describing PayPal
      as live anywhere.

## Etsy

Connecting the shop is a human OAuth2 (PKCE) step — `python -m app.etsy_connect`,
documented in `ETSY_CONNECT.md`. Connection state is credential presence only;
`POST /etsy/verify` is a read-only identity check.

Connecting unlocks nothing on its own: every Etsy write — publish, update,
reprice, inventory sync, order management — is in `ALWAYS_ESCALATE` and waits on
an approval row. Start with read-only order and inventory reconciliation; permit
narrowly constrained inventory updates only after the catalogue mapping is proven
correct against real receipts.

If Etsy permissions, listing state, inventory or order data are inconsistent,
synchronisation stops and alerts rather than guessing.

## Exception queues

These conditions each need a human and are visible in the `events` ledger:

| Condition | Where it surfaces |
|---|---|
| Paid but fulfillment failed | `order.fulfillment_status = unfulfillable` |
| Capture does not match the catalogue | `paypal_capture_catalog_mismatch` |
| Webhook signature failure | `paypal_webhook_rejected`, or a 400 from the Stripe route |
| Duplicate settlement event | `order_event_duplicate_skipped` |
| Refund, dispute or reversal | `refund_settled`, `dispute_opened`, `capture_reversed`, plus the order change: `order_refunded`, `order_partially_refunded`, `order_dispute_<status>` |
| Refund or dispute matching no order | `refund_unmatched`, `dispute_unmatched` |
| Payment failed | `payment_failed`, `subscription_payment_failed` |
| Capture with no identifier | `paypal_capture_unidentified` |

## Daily reconciliation

`python -m app.daily_loop --json` runs the governance self-check and the
executive report. What a daily summary must contain is listed in
`docs/INCIDENT_RESPONSE.md`; report **verified** sales from the ledger, never
projected or assumed figures.
