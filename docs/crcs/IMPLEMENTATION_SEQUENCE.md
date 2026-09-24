# CRCS — Implementation sequence

**Rule: sell before building.** A phase starts only when its entry gate is met. Engineering
that is not on this list, or is on it but whose gate is closed, is deferred.

Each work item answers the five questions the specification requires:

- **Outcome** — which customer or revenue outcome it supports
- **Proof** — the measurable event that shows it works
- **Why now** — the evidence that justifies building it at this point
- **Then** — the commercial action that follows deployment
- **If it fails** — the consequence and the fallback

---

## Phase 0 — Make what exists safe and truthful

**Entry gate:** none (code on a feature branch, no external action).
**Exit gate:** `python3 scripts/ci_local.py` green; owner approves the merge (publishing).
**Size:** about one working day.

| ID | Work item | Outcome | Proof | Why now | Then | If it fails |
|---|---|---|---|---|---|---|
| 0.1 | Admin login: same-origin `next` only, constant-time token compare, lockout after 5 failures per 15 min | Owner can safely open the admin app to the internet | Test: `next=//x` redirects to `/`; 6th bad token gets 429 | Open redirect confirmed (S8); admin must be exposed before any lead can be read in production | Phase 1 admin screens can go live | Admin stays unexposed; no production lead review possible |
| 0.2 | Remove the cockpit and admin-key field from `revenue-command.html` | Lead PII cannot be read through a public page | Page contains no `admin-key` input; test asserts it | Master key typed into a public page (S7) | Cockpit moves to `admin/` in 1.9 | Key exposure risk remains; do not publish the API host |
| 0.3 | Lead form returns an opaque `public_ref`, not the sequential id | Prospects cannot be counted or enumerated | Test: response has no integer id | Sequential id in response (T5) | Booking handoff carries `public_ref` | Enumeration of lead volume |
| 0.4 | Honeypot answers 201 with a dummy reference and stores nothing | Spam stops learning what triggers rejection | Test: honeypot hit → 201, no row | Honeypot answers 400 today (T4) | Cleaner pipeline | More adaptive spam; Turnstile becomes necessary sooner |
| 0.5 | Hash the email in `checkout_started` audit target | Audit ledger holds no personal data | Test: no `@` in any CRCS audit target | Rule 1 in DATA_MODEL.md | Ledger can be retained 7 years without a privacy conflict | Personal data in an undeletable table |
| 0.6 | First-touch UTM in `sessionStorage`, not `localStorage` | Tracking matches the published notice | No `localStorage` write in CRCS scripts | Contradiction with privacy §10 (S12) | Attribution stays usable per session | Undisclosed persistent storage |
| 0.7 | If `cg-revenue-api` is empty, the form is replaced by the owner-confirmed contact route instead of a form that errors | No visitor submits into a dead form | Page with empty meta shows the fallback, not the form | Form cannot submit today (S3) | Leads reach the owner through the fallback | Silent lead loss (current state) |
| 0.8 | Privacy notice: name the form relay or retire it (text change) | Consent collected on current forms is informed | Updated §4 published | Undisclosed processor (S6) | Current lead channel stays lawful to use | **Owner approval required** (public publishing). Until then, S6 remains open |

---

## Phase 1 — Minimum sellable path

Split into three tracks so capture is not held hostage to payments.

### Track 1A — Capture (lead → booked call)

**Entry gate:** Q2 (API host), Q5 (hosting, calendar), Q6 (admin) answered; owner approves
creating the host and database (H2, H3 in the checklist).
**Exit gate:** one real visitor's qualification recorded in production and visible in the
admin app; one booking recorded or manually marked.

| ID | Work item | Outcome | Proof | Why now | Then | If it fails |
|---|---|---|---|---|---|---|
| 1.1 | Deploy control plane + Postgres per `render.yaml`; migrations as pre-deploy step; `AUTO_CREATE_TABLES=false` | Lead capture has somewhere to land | `GET /ready` 200 from the public host; `/revenue/health` shows `database: ok` | No host exists (S2) | Set `cg-revenue-api` (1.2) | Form stays on fallback (0.7) |
| 1.2 | Set `cg-revenue-api` to the verified host; CORS allow-list = site origin only | Visitors can submit | Synthetic submission from staging creates a row; production smoke uses a marked test lead that is deleted | R-CRCS open | Announce the offer (Q8 campaign) | Revert meta tag; fallback returns |
| 1.3 | `start/index.html`: multi-step form, inline errors, error summary linking to fields, consent checkbox unticked by default | Completed qualifications | `qualification_started` → `qualification_submitted` rate measurable | v1 form is single-step with no error summary | Qualified leads routed to booking | Visitors abandon; measured by the same events |
| 1.4 | `lead_consent` + signed unsubscribe link + withdrawal endpoint | Marketing only to people who agreed | Test: withdrawal row written; later sends blocked | No withdrawal path exists | Nurture becomes possible (after approval) | No marketing email at all (safe default) |
| 1.5 | Calendar adapter: link handoff with `public_ref`; signed booking webhook; manual "mark booked" fallback | Booked discovery calls | `meeting_booked` activity on the right lead | Booking is the Phase 1 primary conversion | Owner runs the call from the discovery agenda | Manual fallback; `integration_health` DEGRADED + notification |
| 1.6 | RBAC: `users`, `sessions`, TOTP, `require_role`; admin app delegates login | Lead data readable only by named people | Role-matrix tests pass; VIEWER cannot read free text | Admin exposure is a precondition for 1.9 | Owner reviews leads daily | Keep admin app unexposed; no production review |
| 1.7 | Split free text into `qualification_responses`; audit each read | Free text has its own access rule and retention | `response_viewed` event per read | Most sensitive field set | — | Free text stays on `leads` under the broader rule |
| 1.8 | First-party `analytics_events` with allow-list; integration health writes; internal notifications | Funnel measurable without third-party tracking | Form completion rate and handoff health visible | Cockpit needs real denominators | Weekly revenue review has numbers | Cockpit shows "no data", never estimates |
| 1.9 | Admin cockpit, pipeline, lead record, Revenue Control Log with the missing-action warning | Owner acts on due commercial actions daily | A control-log row per working day | Operating rule needs a screen | Daily commercial action | Owner uses the API JSON directly |

### Track 1B — Collect (checkout → verified payment)

**Entry gate:** Q1, Q3, Q4 answered; Stripe `charges_enabled: true` and webhook endpoint
registered by the owner (H1, H4); owner approves live mode (A3).
**Exit gate:** one verified live payment recorded by webhook, reconciled against the Stripe
Dashboard.

| ID | Work item | Outcome | Proof | Why now | Then | If it fails |
|---|---|---|---|---|---|---|
| 1.10 | `offers` table seeded from `offers.seed.json`; offer pages read `/revenue/offers` | One entry offer, one price, everywhere | Only one entry price visible across public pages | Four entry prices (S5) | Offer promoted in the Q8 campaign | Static copy stays; price conflict persists |
| 1.11 | Stripe adapter wraps `payments.py`; passes an idempotency key; CRCS checkout accepts `public_ref`; tests for checkout-webhook redelivery and the live-only provisioning branch (both untested today) | Buyer pays on Stripe's hosted page | `checkout_started` then `payment_verified` for one live session; redelivery test books one order | Stripe activation complete | Delivery starts (1.13) | Checkout returns 503 with contact route; lead preserved |
| 1.12 | `payment-status.html` + `GET /revenue/checkout-status` | Buyer sees truthful state | Test: success URL without webhook shows VERIFYING | Spec: never trust browser success | Buyer completes intake | Page tells buyer to expect email; owner notified |
| 1.13 | On verified payment: service order, delivery tasks, tokenized intake link, owner notification | Paid work enters delivery the same day | Service order + tasks exist within 1 minute of the webhook | Payment without delivery loses the customer | Owner confirms scope with buyer | Notification SEV-2; manual intake by owner |
| 1.14 | Manual reconciliation path (ADMIN, evidence required) | PayPal or e-transfer payments counted correctly | `verification='MANUALLY_RECONCILED'` rows with evidence | Q4 fallback | Counts as confirmed revenue | Payment stays out of Confirmed Revenue |

### Track 1C — Operate

**Entry gate:** Track 1A live.

| ID | Work item | Outcome | Proof | Why now | Then | If it fails |
|---|---|---|---|---|---|---|
| 1.15 | `scripts/crcs_launch_gate.py`: validates production env (live key only with `APP_ENV=production`, webhook secret set, admin exists with MFA, CORS origin, no BLOCKED owner answer) | No accidental live activation | Script exits non-zero on the current repo state | Spec: env validation before deploy | Deploy checklist step | Deploy refused |
| 1.16 | Uptime check on `/revenue/health`; alert on webhook silence after a checkout | Broken conversion path found within 15 minutes | Alert fires in a staged outage drill | SLO targets need measurement | Weekly review includes SLO data | Owner discovers failures from buyers |
| 1.17 | Runbooks: incident (SEV-1..4), backup/restore with a tested restore, deploy/rollback, access review, privacy requests | Recoverable operations | One restore drill completed and logged | Database exists from 1.1 | — | Data loss on first incident |
| 1.18 | Meta CSP on CRCS pages; `security.txt` page; ASVS checklist mapped to risk | Public pages harder to tamper with | CSP present; no violations in the e2e run | T18 | — | Header gaps remain until edge proxy |
| 1.19 | e2e suite (Playwright, local Chromium) for the eight critical flows; axe checks on CRCS pages | Critical paths proven, including keyboard-only | Suite green in `ci_local.py` | Actions not running (S9) | Release notes cite results | Merge blocked |

---

## Phase 2 — Convert and retain (evidence-gated)

Starts per item when its trigger occurs, not on a date.

| ID | Work item | Trigger evidence | Outcome | Proof |
|---|---|---|---|---|
| 2.1 | `opportunities`, `proposals`, proposal approval + send | First lead reaches DISCOVERY_COMPLETE | Written scope for the audit or sprint | `proposal_sent` event after approval |
| 2.2 | `payment_requests` (invoice or payment link per proposal) | First accepted proposal | Contract value becomes invoiced then paid | `payment_verified` against a request |
| 2.3 | Testimonial and referral drafts, public-use consent | First customer-confirmed delivery | Voluntary, factual feedback | `testimonial_consent_received` |
| 2.4 | Retention job (deletion), privacy-request workflow, audited export | Q7 answered; first lead older than the retention period, or first request | Lawful retention | Job report; request closed within the stated window |
| 2.5 | Hash chain on `events`; integrity check job | First verified payment (financial evidence exists) | Tamper-evident ledger | Check passes daily; a tampered row fails it |
| 2.6 | `content_items` with content-to-offer mapping; lead magnet flow | First resource the owner approves for gated delivery | Tagged, consented nurture | `resource_delivered` |
| 2.7 | Turnstile enabled | Spam exceeds an owner-set threshold for a week | Pipeline quality | Spam rate drops; completion rate does not |

## Phase 3 — Expand (after three delivered engagements)

Customer status link (authenticated, no internal notes), managed-retainer offer using
the existing `subscriptions` flow, expansion-opportunity queue, external CRM connector if
the owner adopts one, file storage adapter if customers need to upload.

## Phase 4 — Deferred with reason

| Item | Reason |
|---|---|
| Third-party analytics vendor | First-party events answer every Phase 1 question without a new processor |
| Automated lead scoring beyond the explainable rules | Spec forbids automated high-impact decisions; volume does not justify it |
| Multi-tenant or white-label | One company, one operator |
| Framework migration of the public site | ADR 0002 revisit conditions not met |
| New CI workflow | Actions dispatches no runners (S9) |

---

## First seven days after the owner answers Q1–Q8

Commercial action leads every day. Engineering fills the remaining time and never
replaces the day's commercial row in the Revenue Control Log.

| Day | Commercial action (owner) | Evidence to log | Engineering (only after the commercial row exists) |
|---|---|---|---|
| 1 | Approve offer, price, refund text, support route. Complete Stripe onboarding items | Stripe account status `charges_enabled`; signed-off offer text | Phase 0 merged; 1.1 host created |
| 2 | Build the prospect list for the Q8 campaign from people the owner already knows; nothing is sent automatically | List exists with source per contact | 1.2, 1.3 |
| 3 | Approve and personally send the first outreach drafts (DRAFT FOR APPROVAL) | Count sent, by channel | 1.5, 1.6 |
| 4 | Take booked calls; record outcomes | `meeting_booked`, DISCOVERY_COMPLETE stages | 1.9 |
| 5 | Offer the entry diagnostic to qualified callers; send payment route | `checkout_started` or payment request | 1.10–1.13 (if Stripe active) |
| 6 | Deliver any paid diagnostic; reconcile payments against Stripe | `delivery_confirmed`, reconciled rows | 1.15–1.17 |
| 7 | Weekly revenue review: leads, calls, proposals, confirmed revenue, what failed | Review record | Re-plan Phase 1 remainder from the review |

Targets for each day (number of contacts, calls, offers) are set by the owner and recorded
in the control log. None are set here, because none can be justified from the repo.
