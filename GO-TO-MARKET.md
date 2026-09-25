# Go-To-Market — the actual playbook

**Start here.** This is the honest, ordered list of what turns this site into
revenue. The repo automates *site health and safety*; it does **not** acquire or
convert customers on its own, and no file here pretends to. Customers come from
the five steps below — most are yours to do, and they take an afternoon, not a
bot.

## What is automated vs. what is you

| Capability | State | Owner |
| --- | --- | --- |
| CI, tests, storefront smoke test, site-health, daily governance | **Running** | Automated |
| Checkout-link safety validation | **Running** (CI) | Automated |
| Analytics wiring (site-wide loader) | **Built, OFF by default** | You flip it on (Step 1) |
| Search discoverability (sitemap, robots, meta) | **In place** | You submit to Search Console (Step 2) |
| Taking card payments | **Live Payment Links exist; buyer completion not independently verified** | **You / audit** (Step 3) |
| Traffic & outreach | **Drafts ready** | **You** send (Step 4) |

## The five steps, in order

### 1. Measure — turn analytics on (free, ~2 min)
You currently cannot tell if anyone visits. Fix that first.
→ Follow `docs/ANALYTICS.md` (GA4: paste one `G-XXXXXXXXXX` ID into `analytics.js`).
- [ ] Analytics enabled and showing visits

### 2. Be findable — confirm search indexing
The sitemap, `robots.txt`, and page meta are in place (all money pages included).
The remaining step is yours:
- [ ] Verify the site in [Google Search Console](https://search.google.com/search-console) and submit `https://www.clearglassinc.com/sitemap.xml`
- [ ] Verify in [Bing Webmaster Tools](https://www.bing.com/webmasters) (the repo already ships a `BingSiteAuth.xml`)

### 3. Verify the buyer path — do not confuse configuration with a sale
The live Stripe account is enabled for charges and payouts, and the repository contains live hosted
Payment Links. The remaining evidence gap is end-to-end buyer-path completion: this audit did not
submit a payment, and Stripe currently reports zero live charges and zero registered webhook endpoints.
→ Use `docs/STORE_GO_LIVE.md` for the human verification sequence. Do not create products or prices
just to satisfy this checklist.
- [x] Live Stripe Payment Links exist for the currently configured offers
- [ ] Public offer → hosted Stripe checkout → non-payment abandonment path independently verified
- [ ] Signed webhook endpoint registered and verified for any fulfillment path that depends on it
- [ ] First real customer payment recorded by Stripe before revenue is counted

### 4. Reach out — send the drafts (human, CASL-compliant)
Traffic doesn't appear on its own. Send a *small, targeted, relevant* batch.
→ Use `marketing/outreach/` (Quick-Audit email, Hardening-Sprint email, PHIPA
one-pager, LinkedIn). Read the CASL rules in that folder's README first.
- [ ] 5–10 personalized messages sent to real, relevant contacts
- [ ] One follow-up per contact, then stop; honour every opt-out

### 5. Iterate — read the numbers weekly
With Step 1 live, you can finally answer "am I getting customers?" honestly:
- [ ] Each week: check visitors, traffic sources, and how many reach `store.html`
- [ ] Double down on whatever channel actually drives store visits; drop the rest

## The one-line truth
Steps 1–5 are the business. The software keeps the site healthy and safe; **the
selling is real-world work that no agent in this repo does for you.** Do Step 1
today — without measurement, everything else is guessing.
