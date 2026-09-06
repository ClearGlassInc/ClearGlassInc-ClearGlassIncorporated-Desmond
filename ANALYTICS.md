# Website Analytics — how to see your visitors

Until you do the one step below, **you have no way to know if anyone visits the
site or clicks "Buy."** This wires analytics across all pages; you just pick a
provider and paste one value.

## Current state

`analytics.js` ships on every page (injected by `/stealth-glass.js`) but is
**off by default** — no third-party request, no cookies, no tracking — until a
provider is set. This is deliberate: nothing phones home until you choose.

## Turn it on (about 2 minutes)

Edit the `CONFIG` block at the top of [`analytics.js`](../analytics.js):

### Option A — Google Analytics 4 (free)
1. Create a property at <https://analytics.google.com> → copy the **Measurement
   ID** (looks like `G-XXXXXXXXXX`).
2. Set:
   ```js
   provider: "ga4",
   measurementId: "G-XXXXXXXXXX",
   ```
3. Commit. Analytics is live on the next deploy.
   ⚠️ GA4 sets cookies — add a line to your privacy policy.

### Option B — Plausible (paid, cookieless, simpler/privacy-first)
1. Add `www.clearglassinc.com` at <https://plausible.io>.
2. Set `provider: "plausible"` (the domain is already filled in).
3. Commit. No cookie banner needed.

## What you'll be able to see

Visitors per day, where they came from (search, social, direct, referrals),
which pages they land on, and how many reach `store.html` / `pricing.html`. That
is the only honest way to answer "am I getting customers?" — by measuring it.

## What analytics does NOT do

It **measures** traffic; it does not **create** it. Traffic comes from SEO and
outreach (see `marketing/outreach/`), and purchases require live checkout (see
`docs/STORE_GO_LIVE.md`). Analytics tells you whether those efforts are working.
