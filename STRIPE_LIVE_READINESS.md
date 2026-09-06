# Stripe Live Readiness — ClearGlass Inc.

Last verified: 2026-08-05

## Connected account

- Stripe account: `acct_1RlYxRL8uR92FksU`
- Country: Canada
- Default currency: CAD
- Charges enabled: **No**
- Payouts enabled: **No**
- Details submitted: **No**

## Live products already created

| Offer | Product ID | Price ID | Amount |
|---|---|---|---:|
| ClearGlass 90-Minute Cyber Risk Audit | `prod_V0yiCBgBCIm6vC` | `price_1U0wl3L8uR92FksUMVIa9nUl` | CAD $297 one-time |
| ClearGlass Business Protection | `prod_V0yi3FfwJbHtvw` | `price_1U0wlFL8uR92FksUG6ZT87rG` | CAD $100/month |
| ClearGlass Business Protection | `prod_V0yi3FfwJbHtvw` | `price_1U0wlOL8uR92FksUJjFEMvGT` | CAD $1,000/year |

These objects are in Stripe live mode. They are not test-mode objects.

## Current Stripe requirements

The account API reports these items as past due and currently due:

- `business_profile.product_description`
- `business_profile.support_phone`
- `business_profile.url`
- `tos_acceptance.date`
- `tos_acceptance.ip`

Payment Links also require a public business name. Use:

- Public business name: `ClearGlassInc`
- Website: `https://www.clearglassinc.com`
- Product description: `Cybersecurity, AI-risk advisory, security assessments, defensive automation, and recurring business protection services.`
- Statement descriptor: `CLEARGLASS`
- Support email: `desmondotieno@icloud.com`
- Support phone: account owner must enter and verify a controlled business phone number.

The account owner must personally review and accept Stripe's services agreement. Do not automate, fabricate, or backdate Terms of Service acceptance, IP address, identity information, or bank details.

## Payout requirement

Add and verify a Canadian bank account under Stripe payout settings. Card revenue is not operationally complete until payouts are enabled.

## Checkout wiring

The public checkout hub is:

- `https://www.clearglassinc.com/checkout/`
- Source: `checkout/index.html`

The page contains the live Product and Price IDs and safely falls back to a secure-checkout request email while Stripe is inactive.

After Stripe activation:

1. Create one live Payment Link for each Price ID.
2. Set the three `STRIPE_LINKS` values in `checkout/index.html`.
3. Set matching links in `store.html` and `pricing.html` where applicable.
4. Run `python bots/store_smoke_bot.py`.
5. Confirm `charges_enabled=true`, `payouts_enabled=true`, and all checkout links open on `https://buy.stripe.com/`.
6. Complete a low-value live purchase and verify payment, receipt, webhook/event record, refund path, and payout destination.

## Security controls

- Never commit Stripe secret keys.
- Payment Link URLs are safe to publish; secret API keys are not.
- Never collect raw card data on ClearGlassInc.com.
- Keep Stripe-hosted checkout enabled for PCI scope reduction and built-in authentication handling.
