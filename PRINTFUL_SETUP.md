# Printful dropship fulfillment — setup and current state

ClearGlass sells; Printful prints and ships. This page covers what is wired, what
is not, and the human steps that no amount of code can do for you.

**Status: not connected.** `PRINTFUL_API_KEY` is unset, so the control plane runs
in mock mode, places no supplier orders, and makes no network calls to Printful.
Nothing on this page has been executed against a live account.

## The one rule

**Money in does not imply a parcel out.** A paid order that cannot ship — bad
address, no supplier variant, supplier unreachable — is marked `unfulfillable`
and written to the audit ledger. It is never silently marked done. The customer
has been charged, so it is an open obligation until a human closes it.

Nothing in this integration invents product data. Images, prices, variants and
delivery estimates all come from Printful's own API responses. A catalogue the
control plane cannot read is a catalogue that does not get published.

## Order lifecycle

| Status | Meaning | Who moves it |
|---|---|---|
| `pending` | Paid; nothing sent to the supplier | — |
| `drafted` / `awaiting_approval` | Draft booked at Printful. Costs nothing, prints nothing, deletable | automatic |
| `confirmed` | Human approved. Printful is printing and will ship | **human approval** |
| `shipped` | Tracking received from the supplier | supplier webhook |
| `unfulfillable` | Cannot ship — needs a human, possibly a refund | — |

Drafting is automatic on purpose: the customer has already paid, the draft costs
nothing, and gating the free half of the work would strand a paid order in a
queue. **Confirmation is what spends money and starts an irreversible print run**,
so `printful_confirm_order` is in `ALWAYS_ESCALATE` and cannot execute without an
approved `approvals` row. `PRINTFUL_AUTO_CONFIRM` records that you *want*
hands-off confirmation; it does **not** open the gate, and
`tests/test_printful.py` asserts that it doesn't.

## What you have to do (none of it can be done from code)

1. **Create a Printful account** at <https://www.printful.com> and set up a store.
   Free; no upfront inventory cost.
2. **Add products to the store.** Printful calls these "sync products" — a
   catalogue item plus your artwork. The sync *variant* id is what an order line
   references. Until at least one exists there is nothing to sell.
3. **Add a billing method.** Printful charges you per order at confirmation. With
   no card on file, confirmation fails and orders sit unfulfilled.
4. **Create an API token** — Dashboard → Settings → Developers → new private
   token. Set it as `PRINTFUL_API_KEY`. Never commit it.
5. **Register the shipment webhook** at
   `https://<control-plane-host>/fulfillment/webhooks/printful/<PRINTFUL_WEBHOOK_SECRET>`
   for the `package_shipped` event. Generate the secret yourself
   (`openssl rand -hex 32`) and set it as `PRINTFUL_WEBHOOK_SECRET`.
6. **Activate Stripe.** Still the hard blocker — see `STRIPE_SETUP.md`. The
   account cannot accept a payment today, so no order can reach fulfillment at
   all until `charges_enabled: true`.
There is no eighth step you can do from a dashboard: shipping-address collection
is **code**, and it is not written yet — see below.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `PRINTFUL_API_KEY` | to leave mock mode | OAuth token, sent as `Authorization: Bearer`. Unset ⇒ no supplier calls at all |
| `PRINTFUL_WEBHOOK_SECRET` | **yes, in production** | Path secret on the shipment webhook. Unset ⇒ the webhook rejects everything |
| `PRINTFUL_STORE_ID` | multi-store accounts only | Sent as `X-PF-Store-Id` |
| `PRINTFUL_AUTO_CONFIRM` | no (default off) | Records intent to auto-confirm. Does not bypass the approval gate |
| `PRINTFUL_API_BASE` | no | Defaults to `https://api.printful.com` |

The webhook secret being unset is the safe direction: it rejects every call
rather than accepting all of them. Failing open there would let anyone mark
orders shipped and suppress the tracking a customer is waiting for.

## Endpoints

| Route | Auth | What it does |
|---|---|---|
| `GET /fulfillment/connection` | open | Credential presence. No network call |
| `POST /fulfillment/verify` | admin | Read-only store identity check |
| `GET /fulfillment/catalog` | admin | The supplier's real products, variants, images, prices |
| `GET /fulfillment/exceptions` | admin | Paid orders that cannot ship — the queue to work |
| `GET /fulfillment/orders/{id}` | admin | Fulfillment state and tracking for one order |
| `POST /fulfillment/shipments/{id}/confirm` | admin | Queues an approval, or spends one — see below |
| `POST /fulfillment/webhooks/printful/{secret}` | URL secret | Applies `package_shipped` tracking. Idempotent, rate limited |

Only `/connection` is open. `/catalog` is gated because each call is a full
paginated scan of the supplier store; `/orders/{id}` because it exposes tracking,
supplier ids and our cost basis behind a sequential integer. A customer-facing
"where is my parcel" view needs a per-order capability token, which does not
exist yet.

`POST /shipments/{id}/confirm` is two-phase. With no approved approval for that
shipment it queues one and returns its id, sending nothing to the supplier. Once
a human approves, calling it again claims that approval — exactly once — and
confirms with Printful. So the same endpoint both proposes and executes,
depending on whether a human has decided yet.

## Running it

```bash
cd clearglass-commerce/control-plane
python -m pytest tests/test_printful.py tests/test_fulfillment.py -q   # 48 tests, offline
psql "$DATABASE_URL" -f migrations/005_fulfillment.sql                 # shipping + shipments
```

The whole suite runs with no Printful credential and no network — every call goes
through an injected requester. A green run is **not** evidence that live
fulfillment works; only a real test order is.

## What is not wired yet

Being explicit, because a half-integration that looks complete is worse than one
that doesn't:

- **Shipping addresses are not collected at checkout.** `create_checkout_session`
  in `app/payments.py` passes `billing_address_collection` but not
  `shipping_address_collection`, so Stripe returns no destination and
  `apply_shipping_details` has nothing to capture. Every physical order would
  therefore land `unfulfillable` — correctly, but uselessly. This is not a
  dashboard toggle: it is a per-session API parameter, and it cannot simply be
  switched on for everything, because demanding a shipping address for a
  90-minute consultation is wrong. Closing it needs a `requires_shipping` flag
  per price-book offer plus an allowed-countries policy, which is the same
  missing distinction as the next item.
- **Automatic draft booking on payment is not connected.** `book_supplier_draft`
  is written and tested, but the Stripe webhook does not call it, because an
  order does not yet record *what was bought*. `Order` has a total and no line
  items, and the price book maps a SKU to a Stripe Price with no Printful
  `sync_variant_id`. Two things close this: an `order_items` table, and a
  `printful_sync_variant_id` field per price-book offer. Until then, drafts are
  booked by calling `book_supplier_draft` with explicit items.
- **Shipping cost at checkout.** `printful.estimate_shipping` returns the
  supplier's real rates and delivery windows, but checkout does not call it, so
  shipping is not yet charged to the customer or shown before payment.
- **Consumer-facing policies.** Canadian selling needs accurate delivery windows,
  a returns/refund policy, business identification, and GST/HST registration once
  you pass the small-supplier threshold. Printful ships from several countries,
  so customs and duty disclosure matter for cross-border orders. None of this is
  written yet, and none of it should be guessed at.
