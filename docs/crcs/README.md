# ClearGlass Revenue Command System (CRCS) — Phase 1 design package

**Status: DESIGN ONLY.** Nothing in this directory is deployed, live, or able to take a
payment. No money has moved, no customer record exists in a live system, and no outbound
contact has been made. Evidence date: **2026-09-24**.

| Document | Contents |
|---|---|
| [README.md](README.md) | Verified state, executive summary, the eight owner questions |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Component, data-flow and trust-boundary diagrams; threat model; gap analysis against CRCS v1 |
| [../../adr/0002-crcs-extend-existing-control-plane.md](../../adr/0002-crcs-extend-existing-control-plane.md) | Architecture decision record: extend the control plane, do not start a new stack |
| [DATA_MODEL.md](DATA_MODEL.md) | All 27 entities: purpose, classification, retention, access, audit, deletion; role matrix |
| [FILE_TREE.md](FILE_TREE.md) | Target tree, each path marked EXISTS / CHANGE / NEW / DEFERRED |
| [IMPLEMENTATION_SEQUENCE.md](IMPLEMENTATION_SEQUENCE.md) | Phase 0–4 work items, each with its commercial rationale and failure mode |
| [OWNER_CONFIRMATION_CHECKLIST.md](OWNER_CONFIRMATION_CHECKLIST.md) | Decisions, human-only account actions, and approvals that gate each phase |

`docs/REVENUE_COMMAND_SYSTEM.md` describes the CRCS v1 code already on `main`. This package
supersedes its roadmap sections; its revenue definitions are carried forward unchanged.

---

## 1. Verified state (read before anything else)

| # | Fact | Source |
|---|---|---|
| S1 | CRCS v1 code exists: public `/revenue/leads`, `/revenue/public-offer`, `/revenue/checkout`, `/revenue/health`; admin `/revenue/cockpit`, lead stages, control log, service orders, delivery confirmation | `control-plane/app/routers/revenue.py`, `control-plane/migrations/007_revenue_command.sql`, commit `0cfcfff` |
| S2 | **No deployed control plane found.** The connected Render workspace holds no control-plane service and no Postgres instance; its two services build from a different repository and were last updated 2025-12-13. No other host for the control plane is named anywhere in this repo | Render API `list_services`, `list_postgres_instances`, queried 2026-09-24 |
| S3 | The public CRCS form cannot submit: the `cg-revenue-api` meta tag is empty, and there is no API host to put in it (S2) | `revenue-command.html:19`; `docs/AUDIT-2026-09-23.md` R-CRCS |
| S4 | **The live Stripe account cannot charge.** `charges_enabled: false`, `payouts_enabled: false`, 0 webhook endpoints, 5 onboarding items past due. Not re-verified since 2026-08-05 | `STRIPE_SETUP.md` §1, `STRIPE_LIVE_READINESS.md` |
| S5 | Four different entry prices are public or configured: CAD 125, 249, 297, 1,250 | `docs/AUDIT-2026-09-23.md` R3 |
| S6 | The lead channel that works today: `index.html` and three `offers/*.html` pages post to `formsubmit.co`, which relays to a personal mailbox. The privacy policy does not name that processor | `index.html:937,1222`; `offers/hardening-sprint.html:168`; `legal/privacy.html` §4 |
| S7 | The cockpit asks the owner to type the master admin key into a public page | `revenue-command.html:67,99`; AUDIT R-KEY |
| S8 | The admin app login redirects to any host: `next=//evil.example` passes `startsWith("/")` and resolves off-site. Its token comparison is not constant-time and it has no lockout | `admin/app/api/login/route.ts:13,26`; reproduced with Node's `URL` on 2026-09-24 |
| S9 | GitHub Actions dispatches no runners. A green check is absence of signal | `CLAUDE.md` deploy-blocker notice; `docs/BASELINE.md` F1 |
| S10 | A Calendly account is connected to the owner's Claude session (account created 2026-09-14). No event type is referenced anywhere in the repo | Calendly API `users/me`, 2026-09-24 |
| S11 | Four different contact addresses are in use across Stripe docs, the form relay, the Calendly account, and `security.txt` | `STRIPE_LIVE_READINESS.md`, `index.html`, Calendly API, `.well-known/security.txt` |
| S12 | `revenue-command.html` stores first-touch UTM in `localStorage` with no expiry; the privacy policy says technical cookies are session-scoped and does not disclose persistent browser storage | `revenue-command.html:79-80`; `legal/privacy.html` §10 |
| S13 | This session could not reach `www.clearglassinc.com` or `*.onrender.com` (network policy). Production behaviour is **not observed** | proxy 403, 2026-09-24 |

---

## 2. Executive summary

**Revenue model.** A four-rung service ladder: Rapid Diagnostic (entry) → AI & Security
Revenue Systems Audit (core) → Rapid Implementation Sprint (proposal) → Managed Optimization
& Technical Advisory (monthly). Offers live in the database, not in code. Revenue is
counted only from provider-verified or manually reconciled payments.

**Primary conversion for Phase 1: qualified lead → booked discovery call.** Not checkout.
Card checkout cannot work until the owner completes Stripe onboarding (S4), which no code
can do. A booked call needs one Calendly event type and a working lead endpoint. Checkout
becomes the primary conversion the day `charges_enabled` reads `true`.

**First paid offer: Rapid Website & Deployment Diagnostic, CAD $125 placeholder** —
**BLOCKED** on Q1 and Q3. It has no Stripe Price yet (`stripe_price_id: null` in
`control-plane/app/data/pricebook.json`). The only offer with a live Stripe Price is
`risk-audit-90` at CAD $297. The owner must pick one entry price and retire the other three
from public pages (S5); a buyer who sees four entry prices trusts none of them.

**Revenue-control operating rule.** A day is not closed until the Revenue Control Log holds
a row for a sales, delivery, collection, retention or referral action with status
`IN_PROGRESS` or `COMPLETED`. Engineering work does not satisfy it. v1 already computes
this as `revenue_action_required`; Phase 1 surfaces it as the cockpit's first element.

**What is actually blocking revenue, in order.** None of the top four is code.

1. Stripe onboarding incomplete (S4) — owner, Stripe Dashboard.
2. No control-plane host or database (S2) — owner approval to create them.
3. Four entry prices (S5) — one owner decision.
4. No named admin, support address, or booking event type (S10, S11) — owner decisions.
5. The admin surface is unsafe to expose (S7, S8) — code, Phase 0.

**The honest call.** CRCS v1 is more software than the business can currently use: a
lead pipeline with no host, a checkout with no chargeable account. Building the full spec
before items 1–4 are closed would be engineering substituting for sales — the exact
failure the operating rule forbids. Phase 0 is therefore small, and Phase 1 is gated on
the owner answers below.

---

## 3. The eight owner questions

Every answer is currently **BLOCKED**. Each row states the evidence found, a safe default
for **local and staging only**, and what the answer unblocks. No safe default is a
production claim.

### Q1 — Which exact offer should accept payment first?

- **Status:** BLOCKED
- **Evidence:** `crcs_first_offer_sku = rapid-website-deployment-diagnostic`
  (`control-plane/app/config.py`), CAD 12500 cents, no Stripe Price.
  `risk-audit-90` (CAD $297) has a live Price but is a different offer. `quick-audit`
  (CAD 249) and a CAD 1,250 outreach assessment are also public (S5).
- **Staging default:** `rapid-website-deployment-diagnostic`, with
  `CRCS_RAPID_DIAGNOSTIC_ENABLED=false`.
- **Unblocks:** Stripe Price creation, offer-page copy, checkout wiring, retirement of the
  other entry prices.

### Q2 — What is the actual public business domain?

- **Status:** PARTIAL. The static site is `www.clearglassinc.com` (`CNAME`). The API host
  is **BLOCKED**: no control-plane service exists (S2).
- **Staging default:** site served locally; API at `http://localhost:8000`;
  `cg-revenue-api` left empty in the committed page.
- **Proposed, needs confirmation:** `api.clearglassinc.com` pointed at the control-plane
  host. Requires DNS access and the Q5 hosting answer.
- **Unblocks:** the lead form (S3), CORS allow-list, Stripe webhook URL, checkout
  success/cancel URLs.

### Q3 — What price, currency, refund policy and delivery promise are approved for the first paid offer?

- **Status:** BLOCKED
- **Evidence:** CAD 125 placeholder in the price book. No refund policy for CRCS offers
  exists in `legal/terms.html` or the repo. The "within 24 hours" promise is conditional on
  owner-confirmed capacity.
- **Staging default:** CAD, 12500 cents, tax-exclusive. Refund text rendered as
  `DRAFT — NOT PUBLISHED`. No delivery time shown; the page says "delivery window confirmed
  at scope confirmation".
- **Unblocks:** Stripe Price creation, `CRCS_RAPID_DIAGNOSTIC_ENABLED=true`, payment
  confirmation copy.

### Q4 — Which payment provider account is approved: Stripe or PayPal?

- **Status:** BLOCKED
- **Evidence:** Stripe account exists in live mode but cannot charge (S4). Stripe webhook
  signature checks, idempotency (`orders.external_ref`, migration 004) and the
  live/test split (`orders.environment`) are built and tested. A PayPal adapter exists
  (`control-plane/app/paypal.py`) and a PayPal connector is attached to the owner's Claude session;
  neither proves an invoicing-enabled business account.
- **Staging default:** Stripe mock mode (no key) or a `sk_test_` key. No live key in any
  non-production environment.
- **Recommendation:** Stripe as the self-serve path, because its verification path is the
  one already tested. PayPal invoice as a manual fallback, recorded as a
  `MANUALLY_RECONCILED` payment by an ADMIN with evidence attached.
- **Unblocks:** Payment adapter selection, webhook registration, live-mode activation.

### Q5 — Which CRM, email, calendar, analytics and hosting providers are approved?

- **Status:** BLOCKED
- **Evidence:** CRM tables exist in the control plane (internal CRM). Calendly is connected
  (S10). No transactional email provider is referenced in `control-plane/app/`. No
  third-party analytics is loaded by the CRCS page. Render workspace exists but hosts
  nothing for this repo (S2); `render.yaml` defines the intended services.
- **Staging defaults:**

  | Capability | Staging default | Why it is safe |
  |---|---|---|
  | CRM | Internal Postgres tables | No external processor |
  | Email | `log` adapter: renders the message, stores it as a draft, sends nothing | Cannot contact anyone |
  | Calendar | Link handoff to a configured booking URL; manual-contact fallback when unset | Lead is saved before any handoff |
  | Analytics | First-party `analytics_events` table, allow-listed fields only | No third-party script, no free text |
  | Hosting | `docker compose up` | Nothing public |
  | Bot protection | Honeypot + per-IP rate limit; Turnstile verifier disabled | No third-party challenge |
  | File storage | Links only (no uploads) | No customer files held |

- **Unblocks:** adapter implementations, CSP `connect-src`/`frame-src` entries, the
  privacy notice's processor list, the hosting deploy.

### Q6 — Who will be the initial dashboard administrator?

- **Status:** BLOCKED
- **Evidence:** the admin app authenticates with one shared token (`ADMIN_LOGIN_TOKEN` or
  `ADMIN_API_KEY`) and has no per-person identity, lockout, or second factor (S8). Four
  contact addresses are in use (S11).
- **Staging default:** one local ADMIN user seeded from an environment variable, clearly
  marked non-production.
- **Unblocks:** RBAC seeding, MFA enrolment, the audit trail's actor names, the support
  route shown on payment pages.

### Q7 — What customer data may be stored, and for how long?

- **Status:** PARTIAL. `legal/privacy.html` §6 already publishes retention periods:
  financial/contractual 7 years (CRA); client engagement 5 years after engagement;
  analytics 26 months; marketing until opt-out or 3 years from last interaction; security
  incidents 5 years.
- **BLOCKED on:** confirming these apply to CRCS records, the period for leads that never
  convert, and whether free-text qualification answers may be kept beyond it.
- **Staging default:** apply the published periods ([DATA_MODEL.md](DATA_MODEL.md) maps
  them per entity); non-converting leads anonymised 24 months after last activity;
  synthetic data only in staging.
- **Unblocks:** retention job, privacy-request workflow, privacy-notice update for the form
  relay (S6).

### Q8 — What is the one real outreach or active lead campaign this system must support in the next seven days?

- **Status:** BLOCKED. Nothing in the repo identifies a live campaign with named, consenting
  prospects.
- **Staging default:** none. The system records `utm_campaign` first- and last-touch, so any
  campaign the owner starts is attributable without code.
- **Unblocks:** the Day 1–7 plan in [IMPLEMENTATION_SEQUENCE.md](IMPLEMENTATION_SEQUENCE.md),
  campaign-specific landing copy, the success threshold for Phase 1.

---

## 4. What this change does and does not do

- **Does:** add design documents and an ADR on a feature branch.
- **Does not:** change application code, publish a page, deploy anything, create a Stripe
  object, send an email, or create a live record. Merging to `main` publishes these files
  on GitHub Pages as static documents; that merge is an owner decision.
