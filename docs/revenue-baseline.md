---
schema: clearglass.revenue-baseline/v1
baseline_date: "2026-09-24"
baseline_time_utc: "2026-09-24T20:45Z"
repository: ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond
remote: https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond
owner: ClearGlassInc
default_branch: main
baseline_head: e4234c9ec022fb14d263b19d3d702e86f5c59593
baseline_head_equals_origin_main: true
working_tree: clean
submodules: none
license_file: LICENSE
deployment:
  static_site:
    platform: github-pages
    mode: deploy-from-branch
    branch: main
    custom_domain: www.clearglassinc.com
    state: live (last verified 2026-09-23, docs/AUDIT-2026-09-23.md)
    observed_in_this_baseline: false
  commerce_stack:
    platform: render
    blueprint: render.yaml
    services: [clearglass-commerce-api, clearglass-commerce-storefront, clearglass-commerce-admin, clearglass-commerce-db]
    state: not deployed (last verified 2026-09-24, docs/AUDIT-2026-09-24.md)
production_url: https://www.clearglassinc.com
staging_url: none
ci:
  workflows: 81
  scheduled: 36
  contents_write: 16
  actions_sha_pinned: 255/255
  runners_dispatched: false
  local_gate: scripts/ci_local.py
stripe:
  code: built (control-plane checkout, subscriptions, signed webhooks, refunds, disputes)
  payment_links_on_site: 9
  price_book_skus_with_live_price: 3
  account_can_charge: unknown
  last_verified_account_state: {date: "2026-08-05", charges_enabled: false, payouts_enabled: false, webhook_endpoints: 0}
paypal:
  code: built (Orders v2, verified webhooks, human-gated capture)
  credentials_configured_on_any_host: false
  incoming_customer_payments_last_30_days: 0
  verified: "2026-09-24"
slack:
  revenue_events: not implemented
  config_key: SLACK_WEBHOOK_URL (declared in control-plane config, read nowhere in control-plane/app)
  live_use: bots/defender/alerting.py only
analytics:
  loader: analytics.js
  provider: none (disabled by default)
  pages_loading_loader: 90
lead_capture_live: formsubmit.co relay to a personal mailbox (4 pages) and mailto links (35 pages)
lead_capture_built_not_deployed: control-plane /revenue/leads
tests:
  control_plane: {passed: 692, skipped: 5}
  root: {passed: 1644, skipped: 12}
  ci_local: {passed: 10, failed: 0, skipped: 1}
verified_revenue_cad: 0
verified_live_payments: 0
verified_customers: 0
recorded_opportunities: 0
offer_threshold_met: false
top_offer: {name: Security Quick-Audit, price_cad: 249, score: 66}
owner_gate:
  paying_commitments_required: 3
  paying_commitments_recorded: 0
  gross_margin_floor_pct: 70
  delivery_hours_per_week_max: 10
---

# ClearGlass Revenue Baseline

**What this document is:** a read-only snapshot of the repository's revenue
capability at one commit. It sells nothing, changes no system, and claims no
revenue. Evidence date **2026-09-24**. It extends
[`AUDIT-2026-09-24.md`](AUDIT-2026-09-24.md), [`GROWTH_REVENUE_OS.md`](GROWTH_REVENUE_OS.md)
and [`crcs/README.md`](crcs/README.md), and re-checks their revenue facts at `e4234c9`.

**Labels.** **VERIFIED** means observed in this session with the command or API
named. **CARRIED** means verified by an earlier dated document and not re-checked
here, with the reason. **INFERENCE** means reasoned from verified facts.
**ASSUMPTION** means not verified. **UNKNOWN** means cannot be determined with
this session's access.

**Bottom line.** VERIFIED: the code is not what blocks revenue. The repository
passes all 2,336 tests, and it holds built payment and lead paths plus nine Stripe
Payment Links. Verified revenue is CAD 0: no payment, no customer, no recorded
demand. The blockers are account state, owner decisions and the absence of buyer
conversations.

---

## 1. Identity

| Field | Value | Label and evidence |
|---|---|---|
| Repository | `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond` | VERIFIED, `git remote -v` (single remote) |
| Remote | `https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond` | VERIFIED, no credentials in the URL |
| Owner / organization | `ClearGlassInc` | VERIFIED, remote path. Workflow runs are triggered by the `ClearGlasslabs` account (GitHub Actions API) |
| Repository root | `/home/user/ClearGlassInc-ClearGlassIncorporated-Desmond` in this session | VERIFIED |
| Default branch | `main` | VERIFIED, `git remote show origin` |
| Current branch | `percival/eloquent-johnson-9tcqbh` (session branch, created at `main`) | VERIFIED |
| HEAD | `e4234c9ec022fb14d263b19d3d702e86f5c59593`, equal to `origin/main` after `git fetch` | VERIFIED |
| Latest commit | "Merge pull request #121 …", author as recorded: Desmond Otieno, 2026-09-24T12:15:25-04:00 | VERIFIED, `git log -1` |
| Working tree | Clean at baseline | VERIFIED, `git status --short` empty |
| Worktrees / submodules | One worktree; no `.gitmodules` | VERIFIED |
| License | `LICENSE` present | VERIFIED |

**Repository disambiguation.** The checkout has exactly one remote, and this
session's GitHub scope is exactly this repository, so the target is not ambiguous.
Two other names appear in documentation and are **not** candidates for this work:

- `ClearGlassInc.github.io`. `CLAUDE.md` uses it as the site's name. The site is
  served from **this** repository (`CNAME` = `www.clearglassinc.com`; Pages run #177
  deployed this repo's `main`, per `AUDIT-2026-09-23.md`).
- `dezzy711/ClearGlass`. It backs two legacy Render services whose last three deploys
  failed (`AUDIT-2026-09-24.md` B5). It is outside this repository.

---

## 2. Architecture

| Layer | Stack | Deploys to | State |
|---|---|---|---|
| Static site: 101 root pages, 191 HTML files outside the Next.js apps, 167 sitemap URLs | HTML/CSS/JS, stdlib Python generators in `tools/` | GitHub Pages, deploy from branch `main`, `.nojekyll` | CARRIED live (2026-09-23). Not observed here: the proxy returned 403 for `www.clearglassinc.com` |
| Control plane `control-plane/` | FastAPI, SQLAlchemy 2, Pydantic 2, Stripe SDK, httpx; Python 3; Dockerfile | Render (`render.yaml`) | CARRIED not deployed (Render workspace read 2026-09-24). Not re-read: the Render connector needs an owner-chosen workspace |
| Storefront, admin | Next.js 16, TypeScript, npm lockfiles | Render (Docker) | CARRIED not deployed |
| Database | Postgres 16 (Render), SQLite (dev/tests); migrations `001`–`010`, runner `app/migrate.py` | Render | CARRIED not provisioned |
| Automation | 81 workflows, `bots/`, `sentinel/`, `agent_army/`, n8n exports in `deployment/` | GitHub Actions | VERIFIED inert: every run on `e4234c9` fails in 3–5 s (for example Commerce Daily Loop run `36036357695`: one job, 3 s, no steps) |
| Edge | `infra/cloudflare/workers/wrangler.toml`, `clearglass-ai-proxy/wrangler.toml` | Cloudflare | UNKNOWN whether deployed |

**APIs.** VERIFIED from `app.openapi()`: 61 operations on 58 paths, from 14
routers (`approvals`, `commerce`, `etsy`, `events`, `fulfillment`, `inventory`,
`metrics`, `orders`, `payments`, `paypal`, `revenue`, `sidestore`, `store`,
`subscriptions`). Four webhooks:

- `POST /webhooks/stripe`: Stripe signature verified, 300 s tolerance.
- `POST /subscriptions/webhook`: Stripe signature verified.
- `POST /webhooks/paypal`: verified through PayPal's API; fails closed.
- `POST /fulfillment/webhooks/printful/{secret}`: authenticated by a shared
  secret in the URL path.

**Authentication.** Mutating admin routes require `Authorization: Bearer` with
`ADMIN_API_KEY` (`app/security.py`). Production with no key refuses to start.
Coverage is enforced by `tests/test_route_auth_coverage.py`.

**Environment variable names (no values).**

- Control plane (`control-plane/.env.example`): `APP_ENV`, `DATABASE_URL`,
  `AUTO_CREATE_TABLES`, `RUN_MIGRATIONS`, `CORS_ALLOW_ORIGINS`, `ADMIN_API_KEY`,
  `REQUIRE_APPROVAL_FOR_HIGH_RISK`, `RATE_LIMIT_*`, `TRUSTED_PROXY_*`,
  `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY`,
  `STRIPE_AUTOMATIC_TAX`, `CHECKOUT_SUCCESS_URL`, `CHECKOUT_CANCEL_URL`,
  `STRIPE_PORTAL_RETURN_URL`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`,
  `PAYPAL_WEBHOOK_ID`, `PAYPAL_API_BASE`, `PAYPAL_RETURN_URL`, `PAYPAL_CANCEL_URL`,
  `PAYOUT_*`, `ETSY_*`, `PRINTFUL_*`, `ESCALATION_EMAIL`, `SLACK_WEBHOOK_URL`,
  `CRCS_*`, `REVENUE_LEAD_RATE_LIMIT_PER_MINUTE`, `REVENUE_ADMIN_EXPORT_LIMIT`.
- Workflow secrets referenced (34 names). Revenue-relevant: `STRIPE_SECRET_KEY`,
  `STRIPE_LIVE_SECRET_KEY`, `RENDER_DEPLOY_HOOK_URL`, `RENDER_ROLLBACK_HOOK_URL`,
  `CONTROL_PLANE_URL`, `DATABASE_URL`, `DEFENDER_SLACK_WEBHOOK_URL`,
  `GMAIL_USER`, `GMAIL_APP_PASSWORD`. Whether any is set is UNKNOWN: secret
  values are not readable, and runners do not start.

**Third-party integrations in code:** Stripe, PayPal, Etsy (OAuth PKCE), Printful,
Slack and Discord (Defender alerts only), Google Search Console, Bing, IndexNow,
Cloudflare, OpenAI and Anthropic APIs, formsubmit.co.

---

## 3. Revenue capability inventory

Only assets with code or a file behind them are listed. "Delivery state" says
whether ClearGlass can deliver it today, not whether it is marketed.

| Existing asset | Repository evidence | Delivery state | Customer problem | Monetization readiness | Risks / constraints |
|---|---|---|---|---|---|
| Quick-Audit collector: read-only Windows posture plus SPF/DMARC, branded HTML report | `tools/Invoke-CGSecurityAudit.ps1` (144 lines, `-Confirmed` authorization gate) | Operator-run. **Not executed in this session** (no PowerShell here) and has no test | Owner of a small office does not know the posture of their endpoints or email domain | **Highest.** Named in its own header as the delivery tool for the Security Quick-Audit | Windows only. Needs written authorization per engagement |
| Email DNS verifier: SPF, DKIM, DMARC | `operations/email/verify_email_dns.py --domain`, `tests/test_email_dns_verifier.py` | Works on any domain, read-only, stdlib | Domain spoofing and deliverability exposure | High, as a component of the Quick-Audit | Passive public DNS only |
| TLS expiry check | `scripts/cert_bot.py`, `CERT_BOT_HOSTS`, `tests/test_cert_bot.py` | Works on any host list | Surprise certificate expiry | Component only | None material |
| API authorization / IDOR audit | `scripts/access_control_audit.py --config`, `scripts/api_security_scanner.py --base-url --endpoints`, tests present | Works against declared, authorized endpoints | Broken access control in a client API | Component of a larger engagement | Requires written authorization and client test tokens |
| Secret scan | `scripts/secret_scan.py --root` | Works on any checked-out tree | Credentials committed to source | Component | Pattern-based; client repo access needed |
| Workflow / repo audits | `scripts/audit_github_actions.py`, `scripts/workflow_doctor.py`, `scripts/site_reliability_audit.py` | INFERENCE: written for **this** repository's paths (no target argument); adaptation needed for a client repo | CI/CD hygiene | Not deliverable to a client without change | Must not be sold as-is |
| Governed commerce OS: orders, Stripe + PayPal, reconciliation, approvals, audit ledger | `control-plane/`, 692 passing tests | Built, **not deployed** | ClearGlass's own revenue operations | Internal infrastructure, not a product | Needs host, DB, keys |
| RFED audit trail | `bots/rfed_audit_bot.py`, `deployment/rfed/`, self-check PASS | Works locally | Audit evidence for agentic automation | Prototype. No external buyer evidence | Do not market as a compliance control |
| CashPulse n8n workflows | `deployment/cashpulse/` (lead capture, invoice dunning) | Export files only; no deployed instance known | Late invoices, slow lead response | Needs n8n, Supabase, Stripe, Twilio and Slack per client | Pilot only, with written scope |
| Guardian Command Nexus Blueprint (digital) | Offer page `offers/guardian-command-nexus-blueprint.html`, Payment Link `…Ni07`, free summary `docs/guardian_command_nexus_spec.html` | UNKNOWN: the paid deliverable file was not located in the repository | Unclear buyer problem | Low | Delivered manually by email within one business day, per the page |
| Governed AI Automation Operating Kit | `docs/products/governed-ai-automation-operating-kit.md` | Specification only; the file says "not a public listing" | Automation planning | Not saleable | Its own status forbids selling it |
| Side Store: 57 SKUs, CAD 2.49–9.99 | `side-store.html`, `data/side-store/catalog.json` | Physical cables and adapters | Commodity resale | **Reject**: not a repository capability | Inventory and fulfillment exposure |

---

## 4. Current funnel inventory

| Stage | Existing implementation | Evidence | Status | Gap | Priority |
|---|---|---|---|---|---|
| Acquisition | SEO: sitemap (167 URLs), IndexNow/Bing/GSC scripts, blog and Insights hub; 5 draft campaigns in `data/campaigns/` | Generators pass `ci_local.py` | Built. Traffic UNKNOWN | No traffic data (analytics off) | High |
| Landing page | `offers/security-quick-audit.html`, `hardening-sprint.html`, `phipa-readiness.html`, `canada-us-control-assessment.html`, `guardian-command-nexus-blueprint.html`; `store.html`, `pricing.html` | VERIFIED files | Live (CARRIED) | Too many offers; see Pricing | High |
| CTA | 161 pages load `logo-badge.js`, a BUY/BOOK dock listing 8 Payment Links; homepage CTAs point to `store.html`, `#contact` and two different mailto addresses | VERIFIED grep | Live | Three contact addresses on `index.html` alone | Medium |
| Lead capture | 4 forms post to `formsubmit.co`, relayed to a personal mailbox; `revenue-command.html` form is hidden while `cg-revenue-api` is empty | VERIFIED | Partially works | Processor not named in `legal/privacy.html`; no durable lead record | High |
| Qualification | CRCS lead stages in control plane | `app/routers/revenue.py` | Built, not deployed | No live qualification | Medium |
| Booking / contact | mailto on 35 pages; a Calendly account exists but no event type is referenced in the repo (CARRIED, `crcs/README.md` S10) | VERIFIED grep for `calendly.com`: 0 pages | Email only | No booking link | High |
| Offer | Price book: 4 SKUs; site: 8 Payment Link offers plus 1 booking link | `control-plane/app/data/pricebook.json`, `logo-badge.js`, `data/store/catalog.json` | Built | Two catalogs that do not match | High |
| Pricing | Public CAD entry prices: 125, 199, 249, 297, 1,499; retainers 100/month, 600/month, 1,000/year; projects from 2,500 and 3,000 | VERIFIED grep of HTML | Live | Price sprawl; three different CAD 199–297 entry offers | Critical |
| Checkout / payment | 9 Stripe Payment Links on the static site; control-plane Checkout Sessions (not deployed); Interac e-Transfer by email (30 pages) | VERIFIED links; UNKNOWN whether Stripe can charge | UNKNOWN | Stripe account state unverified since 2026-08-05 | Critical |
| Payment verification | Signed Stripe webhook → idempotent ledger (control plane only) | Tests pass | **Absent for the live path** (INFERENCE, §5) | No known webhook receives Payment Link purchases | Critical |
| Fulfillment | Control plane opens a service order only on verified live money; static path is manual email | Tests pass | Manual for the live path | No record of who paid for what, outside the Stripe Dashboard | High |
| Onboarding | Quick-Audit page: written authorization, domain/tenant intake by email | VERIFIED page text | Manual | No authorization template in `legal/` | Medium |
| Support | Email | — | Manual | Four contact addresses in use (CARRIED S11) | Medium |
| Retention | Subscriptions and billing portal in control plane; retainers on Payment Links | Code | Not deployed | Recurring offers without verified recurring delivery | Low (defer) |
| Analytics | `analytics.js` loaded on 90 pages, `provider: ""` | VERIFIED | **Off** | No page, CTA or checkout measurement | High |
| Revenue reporting | `/revenue/cockpit`, `app.reconciliation`, admin `/revenue` | Tests pass | Not deployed | Only the Stripe/PayPal dashboards can report today | Medium |

---

## 5. Payment and fulfillment audit

| Item | Static site (live path) | Control plane (built, not deployed) |
|---|---|---|
| Provider evidence | 9 Payment Links: `buy.stripe.com/…Ni00`–`…Ni07`, `book.stripe.com/…Ni08` | Checkout Sessions with price-book Price IDs; PayPal Orders v2 |
| Checkout path | Hosted Stripe page | Hosted Stripe page / PayPal approval |
| Webhook path | **None known.** INFERENCE: 0 endpoints were registered (CARRIED, 2026-08-05) and no control plane is deployed (CARRIED), so a Payment Link purchase reaches nothing ClearGlass runs | `/webhooks/stripe`, `/webhooks/paypal` |
| Signature verification | n/a | Stripe SDK signature, 300 s tolerance; PayPal verify API; both fail closed |
| Idempotency | Stripe-side only | `orders.external_ref` UNIQUE; row lock on `commercial_orders` |
| Fulfillment trigger | Owner sees the payment in the Stripe Dashboard or an email, then delivers by hand | Service order only from verified live money on an unflagged order |
| Order / revenue persistence | Stripe only | `orders`, `commercial_orders`, `events` (append-only trigger via migrations) |
| Refund / cancellation | **No refund or cancellation terms** found in `legal/terms.html` (0 matches) or on `store.html`, `pricing.html`, `checkout/index.html`. The blueprint page alone says "case by case" | Refunds and disputes are subtracted from revenue (migration 009) |
| Subscription lifecycle | Retainer Payment Links `…Ni01`, `…Ni02`, `…Ni06` with no ClearGlass-side lifecycle | `invoice.paid`, failure and portal handling, not deployed |
| Customer data exposure | formsubmit.co relay is not disclosed in the privacy policy | Public routes return opaque references only |
| Blockers | Stripe charge capability UNKNOWN; no refund terms | No host, no database, no keys |

**Payment Link map** (IDs are public in page source; amounts are as displayed on the site):

| Link | Offer | Display price | Where |
|---|---|---|---|
| `…Ni00` | 90-Minute Cyber Risk Audit (`risk-audit-90`) | CAD 297 | `checkout/index.html`, `logo-badge.js` |
| `…Ni01` | Business Protection monthly | CAD 100/month | same |
| `…Ni02` | Business Protection annual | CAD 1,000/year | same |
| `…Ni03` | Security Quick-Audit | CAD 249 | `store.html`, `pricing.html`, `logo-badge.js`, `data/store/catalog.json` |
| `…Ni04` | M365 + Windows Hardening Sprint | from CAD 2,500 | same |
| `…Ni05` | PHIPA Readiness | from CAD 3,000 | same |
| `…Ni06` | Managed Monitoring | from CAD 600/month | same |
| `…Ni07` | Guardian Command Nexus Blueprint | CAD 199 | `offers/guardian-command-nexus-blueprint.html`, `logo-badge.js` |
| `…Ni08` (book.stripe.com) | Critical Minerals Compliance Strategy | CAD 1,499 | `store.html`, `platform.js`, `data/store/catalog.json` |

INFERENCE: the "from" prices (`…Ni04`–`…Ni06`) are fixed-amount links for offers
the site says are scoped on a call, so a buyer can pay before scope exists. The
catalog labels them as deposits.

**Processor activity (read-only).** PayPal, 2026-08-25 to 2026-09-24: 90 records,
all funding, currency-conversion or outgoing pre-approved-payment event codes
(`T0700`, `T0200`, `T0003`); **0 incoming customer payments**. VERIFIED, PayPal
reporting API. Stripe: **not readable in this session** (connector not authorized;
network policy blocks `buy.stripe.com`).

---

## 6. Security and operational risks

| Finding | Severity | Evidence | Revenue impact | Required remediation | Owner approval needed |
|---|---|---|---|---|---|
| GitHub Actions dispatches no runners | High | Every run on `e4234c9` fails in 3–5 s | No CI signal; scheduled revenue and report bots inert | Organisation settings: billing, spending limit, allowed actions | Yes (org owner) |
| `main` unprotected | High | CARRIED `AUDIT-2026-09-24.md` S6 | An unreviewed change can reach the live site that holds the Payment Links | Protect `main`; run `ci_local.py` as a pre-push hook | Yes |
| Live payments with no ClearGlass-side record | High | §5 | A paid order can be missed or delivered twice; no reconciliation | Register a Stripe webhook to a deployed control plane, or keep a manual ledger | Yes |
| No refund / cancellation terms on paid pages | High | §5 | Chargeback exposure; Stripe activation asks for these policies (ASSUMPTION, Stripe docs not reachable here) | Owner-approved terms, linked from every paid page | Yes (legal text) |
| Lead processor undisclosed in privacy policy | Medium | `legal/privacy.html` has no formsubmit mention | Privacy-trust gap on the only working lead path | Disclose it, or move leads to the control plane | Yes |
| Master admin key typed into a public page | Medium | CARRIED S4 | Key exposure once the cockpit is used | Scoped read-only key | Yes |
| Security headers | Low | `_headers` sets CSP, HSTS and others, but INFERENCE: GitHub Pages does not apply `_headers`; 1 page sets CSP by meta tag | Weak browser hardening on pages with checkout links | Edge (Cloudflare) headers or meta CSP | Yes |
| Action supply chain | Pass | 255/255 `uses:` pinned to full SHAs; every workflow declares `permissions:` | — | Keep | — |
| Printful webhook secret travels in the URL path | Low | `/fulfillment/webhooks/printful/{secret}` | Path secrets can appear in proxy and access logs | Keep it out of logs; rotate if a log leaks | No (not deployed) |
| `pull_request_target` | Review | 2 workflows use it | Untrusted-input risk if they check out PR code | Review both | No |
| Committed secrets | Pass | `scripts/secret_scan.py`: none | — | — | — |
| Dependency audit | CARRIED pass | `npm audit` 0/0/0 (2026-09-24) | — | Constraints file for Python (R4) | No |
| Public exposure of this file | Low | `docs/` is served by Pages from `main` | Merging publishes this report | Merge only if the owner accepts publication, like the other audits in `docs/` | Yes |

---

## 7. Revenue gaps

- **Critical:** Stripe charge capability unknown (last known: cannot charge). No
  single entry offer or price. Live Payment Links reach no webhook ClearGlass runs.
- **High:** No refund or cancellation terms. No analytics. No booking link. Leads go
  to a mailbox, not a record. Actions inert. `main` unprotected.
- **Medium:** Control plane not deployed. Four contact addresses. The admin key
  is typed into a public page. Two catalogs that disagree.
- **Low:** Retainer offers with no verified recurring delivery. Legacy Render
  services failing on another repository.

---

## 8. Offer scoring (0–100; sell only at 80 or more)

Weights: implementation evidence 25, buyer pain and urgency 20, reliable
deliverable 15, time to first paid delivery 15, margin 10, risk and compliance
clarity 10, differentiation 5. Scores are this baseline's assessment of the
evidence above. Buyer urgency is scored low for every offer because the repository
holds **zero** recorded opportunities, leads or conversations
(`tools/growth_registry.py --check`: 0 and 0).

| Rank | Offer | Evidence | Pain | Deliver | Time | Margin | Risk | Diff | Score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Security Quick-Audit, CAD 249, live link `…Ni03` | 19 | 8 | 12 | 10 | 8 | 6 | 3 | **66** |
| 2 | 90-Minute Cyber Risk Audit, CAD 297, live link `…Ni00`, live Stripe Price | 13 | 8 | 9 | 10 | 9 | 5 | 2 | **56** |
| 3 | Guardian Command Nexus Blueprint, CAD 199, live link `…Ni07` | 12 | 3 | 10 | 10 | 10 | 5 | 3 | **53** |
| — | Rapid Website & Deployment Diagnostic, CAD 125 placeholder | 14 | 8 | 9 | 5 | 8 | 5 | 3 | 52 (no Stripe Price; site tools are repo-bound) |
| Reject | Managed Monitoring, PHIPA Readiness, Critical Minerals, Business Protection retainers, Side Store | — | — | — | — | — | — | — | Monitoring, regulatory or recurring promises without verified delivery capacity, or commodity resale |

**Verdict: NO SALEABLE OFFER VERIFIED at the 80 threshold.** The Security Quick-Audit
is closest, and its gap is small and mostly non-code.

Smallest completion plan for it (each step moves a named score):

1. **Owner:** confirm `charges_enabled: true` in the Stripe Dashboard. Time +3.
2. **Owner:** approve refund, cancellation and assessment-authorization terms.
   Start from `legal/master_services_agreement_template_ontario.md` and link them
   from the page. Risk +3.
3. **Operator:** run `tools/Invoke-CGSecurityAudit.ps1 -Domain <owned domain>
   -Confirmed` on a ClearGlass-owned Windows machine, and keep the report as the
   internal sample. Either tool or drop the M365 / Entra scope line: no Graph
   tooling exists in the repo. Evidence +3, Deliver +2.
4. **Owner:** 5–10 individually written conversations with known Burlington/Halton
   contacts (no bulk sends), each recorded in `data/growth/opportunities.json`.
   Pain +6 to +8. **No code can do this step, and it matters most.**

Projected after 1–4: 83–85 (INFERENCE; depends on step 4's real answers).

---

## 9. Recommended fastest legitimate revenue path

| Field | Recommendation |
|---|---|
| Chosen implemented capability | `tools/Invoke-CGSecurityAudit.ps1` + `operations/email/verify_email_dns.py` + `scripts/cert_bot.py` |
| Target customer | Owner-operated small office in Burlington / Halton (5–50 staff) on Windows, with its own email domain |
| Specific paid offer | **Security Quick-Audit**, CAD 249 one-time, the price already on the live link `…Ni03` (no new Stripe object) |
| Delivery method | Written authorization → collector plus DNS and TLS checks → top-10 risk-ranked HTML report within 3 business days → optional 15-minute walkthrough (all already stated on `offers/security-quick-audit.html`) |
| Required proof | One internal sample report produced by the collector; signed authorization per client |
| Price hypothesis | CAD 249. Unvalidated: 0 buyer data points |
| Payment path | Existing Payment Link `…Ni03`, or Interac e-Transfer on invoice (already offered on the page). No new code |
| Fulfillment path | Manual, logged in a one-row-per-order sheet until the control plane is deployed |
| Time to launch | Owner-bound: hours if Stripe is already active; otherwise however long Stripe onboarding takes |
| Dependencies | Steps 1–3 in §8 |
| Risks | Scope creep into hardening; M365 claim without tooling; no refund terms |
| Approval gates | Offer, price and terms (owner); any Stripe change; every outbound message |
| Validation metric | 1 verified paid Quick-Audit, delivered, with 0 refunds |

**Why not build first.** The Slack revenue events, dashboard and qualification
engine asked for in the master prompt belong to the control plane, which is not
deployed. Building them now creates notifications for events that cannot occur.
The second milestone starts when the first paid order exists.

**Owner decisions, in order:**

1. Is Stripe live (`charges_enabled`)? If not, finish the five past-due items.
2. Pick one entry offer. Recommended: Quick-Audit CAD 249. Retire CAD 125, 199 and
   297 as entry offers, or state how each differs.
3. Approve refund, cancellation and authorization terms.
4. Pick one contact address and one booking link.
5. Decide whether to publish this file (it is public once merged to `main`).

---

## 10. Operating gate set by the owner (2026-09-24)

| Gate | Rule | State at this baseline |
|---|---|---|
| Validation first | No new infrastructure or feature work until **3 paying client commitments** exist | 0 commitments. §9 "Why not build first" applies |
| Margin floor | Gross margin above **70%** per offer | Not measurable yet. Quick-Audit inputs: price CAD 249; processor fee UNKNOWN (Stripe pricing not verifiable here); operator hours per audit UNKNOWN until the first delivery is timed. Record both on delivery 1 |
| Delivery load | Standard delivery under **10 hours per week** | UNKNOWN until delivery 1 is timed |
| Surplus allocation | Applies only to **verified net profit** after tax, fees and refunds | CAD 0 verified, so nothing to allocate. The investment policy is the owner's and is kept out of this public repository |

---

## 11. No-guess declaration

| Unknown | Why it matters | Evidence needed | Blocking |
|---|---|---|---|
| Stripe `charges_enabled` / `payouts_enabled` today | Decides whether 9 live links can take money | Stripe Dashboard or `GET /v1/account` (connector unauthorized here) | **Yes** |
| Whether the 9 links belong to the account last verified | Payout destination | Stripe Dashboard → Payment Links | Yes |
| Stripe webhook endpoints today | Fulfillment signal | `GET /v1/webhook_endpoints` | Yes, for milestone 2 |
| Site live state and traffic | Acquisition baseline | Browser check; analytics provider enabled | No |
| Whether the Quick-Audit collector runs cleanly | Delivery proof | One run on Windows PowerShell 5.1+ | Yes |
| Paid Guardian blueprint file | Deliverability of offer 3 | Owner locates the file | No |
| Render workspace contents today | Control-plane path | Owner selects the workspace; `list_services` | No (milestone 2) |
| Which workflow secrets are set | Automation readiness | Repository settings → Secrets (names only) | No |
| Buyer demand at any price | Offer score, price | Recorded conversations | **Yes** |
| Cloudflare workers deployed | Edge headers, proxy | Cloudflare dashboard | No |

---

## 12. Re-verify this baseline

```bash
git fetch origin main && git rev-parse origin/main          # HEAD moved?
python3 scripts/ci_local.py                                 # 10 passed, 1 skipped
(cd control-plane && ruff check . && python -m pytest tests/ -q)   # 692 passed, 5 skipped
python -m pytest tests/ -q                                   # 1644 passed, 12 skipped
(cd control-plane && python -m app.daily_loop --json)       # governance_failures: []
python -m bots.rfed_audit_bot --self-check                  # PASSED
python3 tools/growth_registry.py --check                    # opportunities, experiments
python3 scripts/secret_scan.py                              # no secrets
grep -rhoE 'https://(buy|book)\.stripe\.com/[A-Za-z0-9]+' --include='*.html' --include='*.js' . | sort -u   # 9 links
```
