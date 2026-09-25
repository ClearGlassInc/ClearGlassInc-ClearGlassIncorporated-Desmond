# Store Go-Live Runbook — enabling live Stripe card checkout

This is the human checklist for turning the storefront's buy buttons into live
card payments. It pairs with the `SOUL.md` charter ("take live card payments")
and is enforced by `bots/store_smoke_bot.py`.

## Current state (safe default)

Every engagement on `store.html` / `pricing.html` ships with an **empty**
checkout link, so each buy button uses the **confirmed-invoice / Interac
e-Transfer** flow. Nothing is auto-charged, no card details touch the site, and
no API keys live in the repo. This is the safe resting state.

```js
// store.html and pricing.html
var CHECKOUT = {
  "quick-audit": "",   // empty  -> invoice / e-Transfer fallback
  "hardening":   "",
  "phipa":       "",
  "monitoring":  ""
};
```

## Steps only the account owner can do

These require the ClearGlass Stripe account and cannot be automated from CI —
do them yourself, then let the validator check your work.

1. **Confirm live account readiness.** The 2026-09-25 read-only reconciliation found
   `charges_enabled: true` and `payouts_enabled: true`. No activation change is required by this audit.
2. **Do not create new Products or Prices as part of this audit.** Live Payment Links already exist
   for the currently configured offers. A Payment Link URL contains no secret API key and may be
   committed only when it is intentionally approved for public use.
3. **Reconcile each existing URL before changing repository wiring.** Compare the URL and its Stripe
   Price against the live account; do not overwrite a working link with a newly created object.
   Paste each verified URL into the appropriate `CHECKOUT` map in *both* files (`store.html` and
   `pricing.html`), keyed by the same SKU. Keep the SKU set identical across the
   two pages.
4. **Open a PR.** The storefront smoke test runs automatically and will block
   the merge unless every change is safe (see below).

## What the smoke test enforces automatically

`bots/store_smoke_bot.py` (run on every PR and on the daily schedule) fails the
build if:

- a non-empty checkout link is **not** a valid
  `https://(buy|book|checkout).stripe.com/<path>` URL — this catches typos,
  `http://` links, and wrong/unsafe domains before they ship;
- `store.html` and `pricing.html` enable **live card checkout for a different
  set of SKUs** (e.g. card checkout on the store but invoice-only on pricing for
  the same service);
- any SKU loses its wiring across the `CHECKOUT` / `LABEL` / `SHORT` /
  `ETX_AMOUNT` maps, its buy CTA, or its price;
- the runtime Stripe-link guard or the "nothing is auto-charged" guarantee is
  removed.

Verify locally any time:

```bash
python bots/store_smoke_bot.py      # PASS / FAIL + count of live SKUs
python -m pytest tests/test_store_smoke_bot.py -q
```

## Rollback

To take any SKU back off live checkout, set its `CHECKOUT` value back to `""` in
both files. The button immediately reverts to the invoice / e-Transfer flow.
No other change is required, and the smoke test stays green.
