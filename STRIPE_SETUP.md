# Stripe setup — connection state and what it takes to go live

Status of the live Stripe account as verified against the Stripe API on **2026-09-25**.
This section is a point-in-time reconciliation; re-run the read-only Stripe audit before relying on it for a later commercial decision.

## 1. Connection check (verified, not assumed)

| Check | Result | Source |
|---|---|---|
| Account reachable | ✅ `acct_1RlYxRL8uR92FksU` | `GET /v1/account` |
| Mode | **live** (`livemode: true`) | `GET /v1/balance` |
| Country / default currency | CA / CAD | account object |
| **Can accept charges** | ✅ `charges_enabled: true` | account object |
| **Can pay out** | ✅ `payouts_enabled: true` | account object |
| Onboarding submitted | ✅ `details_submitted: true` | account object |
| Capabilities | ✅ card payments and multiple additional payment methods active/pending | account object |
| Bank account attached | ✅ one payout account configured | account object |
| Webhook endpoints | ❌ **0 registered** | `GET /v1/webhook_endpoints` |
| Checkout Sessions ever created | Not used as a revenue-proof source in this audit | Stripe API |
| Live charges | **0 returned** | `GET /v1/charges` |

**Bottom line: Stripe live mode is enabled and the account can accept charges and pay out.**
No live charge was returned by the read-only audit, so verified revenue remains **CAD $0**.
The absence of a charge does not prove that a buyer path has never been used outside the queried
window; it is simply the current Stripe charge-list evidence available to this audit.

The account currently reports no past-due or currently-due requirements. No onboarding action is
being requested from this repository.

## 1a. The catalogue: Stripe is the source of truth

The control-plane price book names three **live, active** Stripe Prices. The storefront also
has separate live Payment Links for additional offers. Live checkout passes `line_items[].price`
where the control plane is used; hosted Payment Links are governed by their Stripe Price objects.

| SKU | Stripe Price | Amount |
|---|---|---|
| `risk-audit-90` | `price_1U0wl3L8uR92FksUMVIa9nUl` | CAD $297 one-time |
| `business-protection-monthly` | `price_1U0wlFL8uR92FksUG6ZT87rG` | CAD $100 / month |
| `business-protection-annual` | `price_1U0wlOL8uR92FksUJjFEMvGT` | CAD $1,000 / year |

`amount` in `app/data/pricebook.json` is display and mock-mode arithmetic only.
`tests/test_pricebook.py::test_every_offer_names_a_real_stripe_price` fails if an
offer is added without a Price, because an inline amount reintroduces a second place
a price can live.

**Current storefront reconciliation:** the live Stripe account now contains active Prices and
Payment Links for the storefront offers, including Quick-Audit, Hardening, PHIPA, Monitoring,
Guardian Command Nexus, Critical Minerals Compliance Strategy, and the two Business Protection
billing intervals. These hosted Payment Links are distinct from the three-SKU control-plane
price book. Do not infer that every storefront offer is routed through `POST /checkout/session`.
The repository's historical statements that these offers had no live Stripe Price or empty
checkout URLs are stale and are superseded by this reconciliation.

### Two follow-ups that need a human

1. **Tax fields are unset on all three Prices** — `tax_behavior: "unspecified"` and
   `tax_code: null` on both products. Stripe Tax needs them. `tax_behavior` is
   effectively **immutable once set**, so this is a one-way door on live pricing
   objects and is deliberately left for you rather than changed from here.
2. **`checkout/index.html` is a second checkout surface.** It hardcodes the same
   three price IDs but its `STRIPE_LINKS` are empty, so every button currently falls
   back to a `mailto:`. Either wire it to Payment Links, or point it at this control
   plane, so there is one checkout path rather than two that can drift.

## 2. Architecture

Stripe **Checkout Sessions**, hosted page, redirect flow. Not Elements, not Connect:

- **Not Connect** — ClearGlass sells its own services and collects its own revenue.
  There are no connected accounts (`GET /v1/accounts` is empty) and no third-party
  sellers to pay. Connect would add onboarding, KYC and payout obligations for a
  marketplace that does not exist.
- **Not Elements** — Elements buys design control at the cost of owning PCI scope,
  payment-method logic and SCA handling. The storefront has no custom-checkout
  requirement that justifies that.
- **Checkout Sessions** — Stripe hosts the page, dynamic payment methods (cards,
  Link, Apple Pay, Google Pay) are enabled from the Dashboard with no code change,
  and Apple/Google Pay give the one-click flow without an Express Checkout Element.

Subscription support is in place: the two Business Protection offers are recurring,
and a cart containing either produces a `subscription`-mode session.

## 3. Required Stripe Dashboard settings

Each of these is a human step; none can be done from code.

1. **Account activation:** currently complete according to the live account object; no repository action is required.
2. **Payout configuration:** currently present according to the live account object; keep payout-account details out of the repository.
3. **Enable payment methods** — Settings → Payment methods. Cards + Link at minimum;
   Apple Pay and Google Pay require domain verification for one-click.
4. **Register the webhook endpoint** (see §5) and copy its signing secret into
   `STRIPE_WEBHOOK_SECRET`.
5. **Stripe Tax** (only if you are registered to collect) — Settings → Tax: set the
   origin address, add a registration per jurisdiction (GST/HST for CA), and pick a
   default product tax code. **Then** set `STRIPE_AUTOMATIC_TAX=true`. Enabling the
   env var before the Dashboard side is configured makes Stripe reject session
   creation, which is why it defaults to off.
6. **Radar** — the default rules are active on all accounts. Review Radar → Rules
   after the first live payments; no code change needed.

## 4. Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `STRIPE_SECRET_KEY` | to leave mock mode | Unset ⇒ deterministic mock sessions, no network |
| `STRIPE_WEBHOOK_SECRET` | **yes, in production** | Unset ⇒ webhooks are accepted but marked unverified |
| `STRIPE_PUBLISHABLE_KEY` | no | Not used by the hosted-page flow |
| `STRIPE_AUTOMATIC_TAX` | no (default off) | `true` turns on Stripe Tax; requires §3.5 first |
| `STRIPE_PORTAL_RETURN_URL` | yes for subscriptions in production | Return destination after the hosted customer portal |
| `STRIPE_INTEGRATION_VERSION` | no (default `v1`) | Subscription metadata contract version |
| `PRICEBOOK_PATH` | no | Overrides the bundled `app/data/pricebook.json` |
| `CHECKOUT_SUCCESS_URL` / `CHECKOUT_CANCEL_URL` | yes in production | `{CHECKOUT_SESSION_ID}` is appended automatically if absent |
| `PAYOUT_EXTERNAL_ACCOUNT_ID` | for payout reconciliation | Stripe `ba_…` token |

`STRIPE_WEBHOOK_SECRET` being unset is a hard production blocker: `verify_webhook` returns
`verified: false`, and the webhook route rejects that event whenever a Stripe key is configured
or `APP_ENV` is production. In development mock mode (no Stripe key and non-production), the
route retains the offline fixture behavior. Production must therefore have
`STRIPE_WEBHOOK_SECRET` configured before signed webhook processing can succeed.

## 5. Webhooks to configure

Endpoint: `https://<control-plane-host>/webhooks/stripe`

| Event | Why |
|---|---|
| `checkout.session.completed` | Books the order. Honours `payment_status`, so an async method books `pending`, not `paid` |
| `checkout.session.async_payment_succeeded` | Promotes that pending order to paid |
| `checkout.session.async_payment_failed` | Marks it failed |
| `invoice.paid` | Subscription renewals — without it, only month one is ever recorded |
| `invoice.payment_failed` | Failed renewal, needs dunning |
| `customer.subscription.created` / `.updated` / `.deleted` | Lifecycle visibility, scheduled changes, and cancellation |
| `customer.subscription.paused` / `.resumed` | Pause/resume lifecycle visibility |
| `charge.refunded` | Sets the order's cumulative `amount_refunded`; a full refund marks it `refunded`. Confirmed revenue drops by the refund |
| `charge.dispute.created` / `.updated` / `.closed` | Records the dispute status on the order. Open and lost disputes are held out of confirmed revenue; a won dispute counts again |
| `payment_intent.payment_failed` | Failed payment visibility |
| `payout.created` / `.updated` / `.paid` / `.failed` / `.canceled` | Settlement to the bank account |

Handling is idempotent on redelivery: orders key on `orders.external_ref`, payouts on
`stripe_payout_id`. Refunds and disputes find their order by `orders.payment_intent`
(migration 009) and set cumulative values, so a redelivered event changes nothing; one
that matches no order is flagged (`refund_unmatched`, `dispute_unmatched`), never dropped.
A refunded order is never promoted back to `paid` by a late settlement event.

Subscription lifecycle events go to a **second** endpoint, `/subscriptions/webhook`,
which de-duplicates on the Stripe event id (`stripe_events`). Register both.

Local testing:

```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
stripe trigger checkout.session.completed
```

Enable Stripe's hosted **Customer portal** in Dashboard → Settings → Billing →
Customer portal. `POST /billing/portal` accepts only the Checkout Session id returned
to that buyer, resolves the Stripe Customer server-side, and refuses one-time-payment
sessions. Configure cancellation at period end and payment-method updates in the
Dashboard; the portal never grants administrative price or refund authority.

Recurring Checkout sessions carry stable `business`, `source`, `environment`,
`subscription_type`, `billing_channel`, `customer_source`, `plan`, `product`, and
`integration_version` metadata. Environment is derived from the Stripe key prefix,
so test-mode subscriptions cannot be mislabeled as production.

## 6. Pricing is server-side — do not undo this

`POST /checkout/session` accepts **SKUs and quantities only**. Amounts are resolved
from `app/data/pricebook.json` via `app/pricebook.py`. Before this, the request body
carried `amount` and that value went straight into Stripe's `unit_amount` — a buyer
could post `amount: 1` and take a CAD $2,500 engagement for a cent.

`tests/test_pricebook.py` pins this, including a check that `CheckoutLineItem` in the
OpenAPI schema has exactly the fields `{sku, quantity}`. If you add a price-shaped
field back to that contract, the suite fails on purpose.

Changing a live price means changing the **Stripe Price** — that is what customers are
charged. Update the display copy in `app/data/pricebook.json` and
`storefront/lib/catalog.ts` to match. Live price changes through the API remain HIGH
risk and stay behind the approval gate.

## 7. Validation checklist

Run in order. Do not skip 1 — everything after it fails while the account is inactive.

- [x] `charges_enabled: true` and `payouts_enabled: true` on the live account as of 2026-09-25
- [x] A payout account is configured on the live account as of 2026-09-25
- [ ] `STRIPE_SECRET_KEY` set; `POST /checkout/session` returns `"mode": "live"` and a `checkout.stripe.com` URL
- [ ] Tampered cart refused: `{"items":[{"sku":"risk-audit-90","quantity":1,"amount":1}]}` still totals `29700`
- [ ] Unknown SKU returns 400 and leaves a `rejected` row in `/events`
- [ ] Webhook endpoint registered; `STRIPE_WEBHOOK_SECRET` set; a forged unsigned POST to `/webhooks/stripe` returns 400
- [ ] A real test-mode purchase produces an `orders` row with `status: paid` and the matching `external_ref`
- [ ] Redelivering that same webhook produces **no** second order (`order_event_duplicate_skipped` in `/events`)
- [ ] Subscription: `{"items":[{"sku":"business-protection-monthly","quantity":1}]}` returns `checkout_mode: "subscription"`
- [ ] A subscription renewal (`invoice.paid`, `billing_reason: subscription_cycle`) books a second order
- [ ] `GET /ready` reports the database reachable
- [ ] If Stripe Tax is on: a session shows non-zero `total_details.amount_tax` for a registered jurisdiction

## 8. What is still mock

With no `STRIPE_SECRET_KEY`, `create_checkout_session` returns a deterministic
`cs_mock_…` session and never calls Stripe. That is the correct default for CI and
local work, and it is why the whole test suite runs offline. It also means a green
test run is **not** evidence that live payments work — only the checklist above is.
