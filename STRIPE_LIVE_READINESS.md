# Stripe Live Readiness — ClearGlass Inc.

Last verified: 2026-09-25

## Connected account

- Stripe account: `acct_1RlYxRL8uR92FksU`
- Country: Canada
- Default currency: CAD
- Charges enabled: **Yes**
- Payouts enabled: **Yes**
- Details submitted: **Yes**

## Live products already created

| Offer | Product ID | Price ID | Amount |
|---|---|---|---:|
| ClearGlass 90-Minute Cyber Risk Audit | `prod_V0yiCBgBCIm6vC` | `price_1U0wl3L8uR92FksUMVIa9nUl` | CAD $297 one-time |
| ClearGlass Business Protection | `prod_V0yi3FfwJbHtvw` | `price_1U0wlFL8uR92FksUG6ZT87rG` | CAD $100/month |
| ClearGlass Business Protection | `prod_V0yi3FfwJbHtvw` | `price_1U0wlOL8uR92FksUJjFEMvGT` | CAD $1,000/year |

These objects are in Stripe live mode. They are not test-mode objects.

## Current Stripe requirements

The live account read on 2026-09-25 reports no currently-due or past-due requirements and `details_submitted: true`.
The account is enabled for charges and payouts. No Dashboard remediation is identified by this audit.

The account's business profile and support configuration were read only for reconciliation; no values were
changed by this audit.

## Payout status

Payouts are enabled and a payout account is configured according to the live account object. No bank
coordinates are recorded here.

## Checkout wiring

The public checkout hub is:

- `https://www.clearglassinc.com/checkout/`
- Source: `checkout/index.html`

The page contains the live Product and Price IDs and safely falls back to a secure-checkout request email while Stripe is inactive.

Current reconciliation:

1. Live Payment Links already exist for the storefront offers and for the three control-plane SKUs.
2. `store.html`, `pricing.html`, `checkout/index.html`, and the Guardian offer page contain hosted Stripe routes in the repository.
3. The live account has **0 registered webhook endpoints**. This is a manual Stripe Dashboard configuration item if webhook-backed order fulfillment is required.
4. The audit did **not** submit a payment. Therefore checkout completion and webhook settlement are **NOT VERIFIED**.
5. A live charge query returned **0 charges**, so verified Stripe revenue remains **CAD $0**.

## Security controls

- Never commit Stripe secret keys.
- Payment Link URLs are safe to publish; secret API keys are not.
- Never collect raw card data on ClearGlassInc.com.
- Keep Stripe-hosted checkout enabled for PCI scope reduction and built-in authentication handling.
