# CRCS — Owner confirmation checklist

Three kinds of item, none of which code can complete:

- **D — Decisions.** Only the owner can make them.
- **H — Human-only account actions.** Done by the owner in a provider dashboard; no
  credential, identity document, or terms acceptance is ever handled by an agent.
- **A — Approvals for external actions.** Each is a yes/no on one specific action.

Tick an item only when its evidence exists. "Evidence" means something a second person
could check, not a statement that it was done.

---

## D — Decisions

| ID | Decision | Answer format | Evidence | Unblocks |
|---|---|---|---|---|
| D1 (Q1) | First offer to accept payment | One SKU | Recorded in this file | 1.10, 1.11 |
| D2 (Q2) | API host name | e.g. `api.clearglassinc.com` | DNS record resolves to the host | 1.1, 1.2 |
| D3 (Q3) | Price, currency, tax treatment | CAD amount; tax-inclusive or exclusive | Stripe Price exists with that amount | 1.10, 1.11 |
| D4 (Q3) | Refund policy text | Final wording | Published in `legal/terms.html` | A3 |
| D5 (Q3) | Delivery promise | A window the owner can meet, or "confirmed at scope" | Recorded in `offers.delivery_promise` | Offer page copy |
| D6 (Q4) | Payment provider(s) | Stripe; PayPal as manual fallback yes/no | Recorded | 1.11, 1.14 |
| D7 (Q5) | CRM, email, calendar, analytics, hosting | One provider each, or the staging default | Recorded; privacy notice lists every processor | Adapters, CSP, notice |
| D8 (Q6) | Initial admin: one named person and one business address | Name + address | User row created with MFA enrolled | 1.6 |
| D9 | One public support address (four are in use today, S11) | One address | Same address on Stripe, offer pages, payment pages, `security.txt` policy | A3 |
| D10 (Q7) | Retention for non-converting leads and free text | Months | Recorded in DATA_MODEL.md §3 | 2.4 |
| D11 (Q8) | The one campaign for the first seven days | Name, audience, channel, `utm_campaign` value | Recorded in the Revenue Control Log | Day 2–7 plan |
| D12 | Retire, redirect, or re-price the other entry offers (CAD 249, 297, 1,250) | Per page | Only one entry price visible on public pages | 1.10 |
| D13 | Form relay on `index.html` and `offers/*.html`: keep (and disclose) or replace | Keep / replace | Privacy §4 names it, or the forms post to the control plane | 0.8 |
| D14 | Accept ADR 0002 | Accept / reject | Status line in the ADR | All Phase 1 work |

## H — Human-only account actions

| ID | Action | Where | Evidence | Unblocks |
|---|---|---|---|---|
| H1 | Complete Stripe onboarding: product description, support phone, business URL, terms acceptance; attach and verify a Canadian bank account | Stripe Dashboard → Account onboarding, Bank accounts | `charges_enabled: true`, `payouts_enabled: true` on the account object | Track 1B |
| H2 | Create the control-plane web service and Postgres from `render.yaml` (or the D7 host) | Hosting dashboard | Service and database listed; `/ready` returns 200 | 1.1 |
| H3 | Put secrets in the host secret store: `ADMIN_API_KEY` (control plane **and** admin app, which now sends it server-side), `ADMIN_LOGIN_TOKEN` (admin app; at least 24 random characters), `ADMIN_SESSION_SECRET`, `CRCS_AUDIT_HASH_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, calendar webhook secret | Hosting dashboard, never the repo | `crcs_launch_gate.py` reports each as present (never its value) | 1.1, 1.11, 1.15 |
| H4 | Register the Stripe webhook endpoint for the events in `STRIPE_SETUP.md` §5 | Stripe Dashboard → Webhooks | Endpoint listed; test delivery 2xx | 1.11 |
| H5 | Create the Stripe Price for the D1 offer and give its id | Stripe Dashboard → Products | Price id in `pricebook.json` | 1.11 |
| H6 | Decide Stripe Tax fields (`tax_behavior` is effectively one-way once set) | Stripe Dashboard → Tax | Recorded; `STRIPE_AUTOMATIC_TAX` set to match | 1.11 |
| H7 | Create one Calendly event type for discovery calls; confirm the plan supports webhooks, or accept the manual fallback | Calendly | Event URL recorded; webhook subscription listed, or fallback accepted | 1.5 |
| H8 | DNS record for the D2 host | DNS provider | Record resolves; TLS certificate valid | 1.2 |
| H9 | Clear GitHub Actions runner dispatch (billing, spending limit, allowed-actions policy, Actions toggle) | GitHub organisation settings | A job reports a non-zero `runner_id` | CI signal; `.github/workflows/crcs.yml` |
| H10 | Protect `main`: require one review | GitHub repository settings | Branch protection rule visible | Safe merges |
| H11 | Optional: edge proxy for public-page headers (HSTS, `frame-ancestors`) | DNS/CDN provider | `curl -I` shows the headers on the live site | T18 fully closed |

## A — Approvals for external actions

Each approval covers **one** action at **one** time. Approval of one does not imply another.

| ID | Action | What happens when approved | Reversible? |
|---|---|---|---|
| A1 | Merge Phase 0 to `main` | GitHub Pages publishes the changed pages | Yes: revert commit |
| A2 | Create the production host and database (H2) and run migrations 001–008 in order (009 when Phase 1 lands) | A public API exists; tables created | Service yes; data retained per policy |
| A3 | Set `CRCS_RAPID_DIAGNOSTIC_ENABLED=true` in production | Real buyers can pay | Yes: flag off; paid orders remain |
| A4 | Publish privacy, terms, cookie and disclosure page changes | Public legal text changes | Yes, but versions must be kept |
| A5 | Send each outbound message or batch (DRAFT FOR APPROVAL) | People are contacted | **No** |
| A6 | Send each proposal or payment request | A commercial offer is made | **No** |
| A7 | Any refund | Money moves | **No** |
| A8 | Grant a role to a second person | Another human can read lead data | Yes: revoke session and role |
| A9 | Publish a testimonial (requires recorded public-use consent) | Public claim about a customer | Yes, but already seen |

---

## Status as of 2026-09-24

| Group | Done | Open |
|---|---|---|
| D | 0 / 14 | All |
| H | 0 / 11 verified | All. H1 was last observed incomplete on 2026-08-05 (`STRIPE_SETUP.md`) |
| A | 0 / 9 | All. This change requests none of them; it is a draft pull request |
