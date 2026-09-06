# Procurement Legal Tech — product and launch blueprint

## Assumptions requiring owner confirmation before activation

This build assumes but does not activate: **(1)** final legal company name and contact details; **(2)** stated plan limits and CAD pricing; **(3)** a 14-day trial; **(4)** Stripe account, products, portal, tax, invoice, and recovery configuration; **(5)** refund and cancellation policy; **(6)** final privacy policy and terms; **(7)** security claims supported by production evidence; **(8)** whether sensitive document uploads are permitted and their classification; and **(9)** support response expectations. Commerce, email campaigns, analytics, indexing, and public security claims remain disabled until the owner confirms these items.

## 1. Product positioning statement

**Procurement Legal Tech** is a lightweight operational command center for 5–50 person businesses managing vendors, agreements, documents, renewals, approvals, and obligations without enterprise procurement software. **Promise:** Stop losing track of the business commitments that cost you money. **Tagline:** Know what’s due. Know who owns it. Keep business moving.

## 2. Ideal customer profile

Founders and operations leads at small firms; agencies coordinating vendors, client agreements, and contractors; consultants and regulated small businesses that need orderly records; and growing teams that have missed a renewal, lost an agreement, paid an unnecessary charge, or lacked a clear owner. It is not positioned for enterprise procurement departments.

## 3. Core customer pain points

Missed renewals create preventable spend; distributed agreements cannot be found at decision time; unassigned obligations stall work; spreadsheets become stale and untrusted; and enterprise suites are too complex for the job.

## 4. Clear value proposition

A starter workspace turns scattered records into a calm operating rhythm in ten minutes: import essentials, assign an owner, schedule reminders, and make approvals visible. Customers gain visibility, accountability, and structure without enterprise overhead.

## 5. Full homepage copy

The canonical copy is implemented in `app/page.tsx` in the required sequence: announcement, supplied hero, four pain cards, six benefit-led features, four-step workflow, ROI estimator, pricing, comparison, trust, twelve FAQs, final CTA, and exact disclaimer. Mock metrics state **Illustrative example data**.

## 6. Full pricing-page copy

`app/pricing/page.tsx` and `lib/plans.ts` contain Control (CAD $12/month or $120/year; 3 users), Oversight ($39/$390; 15), and Command ($99/$990; 50), complete inclusions, cancellation/tax copy, and trial explanation. Annual totals equal ten monthly payments and truthfully support “Save 20%.” Add-ons appear only after plan selection and remain unchecked.

## 7. Pricing and entitlement data model

Stable internal `Plan` keys map server-side to member/workspace caps, workflow/reporting tiers, audit export, onboarding, and support. Stripe price IDs are environment configuration, never browser authority. Add-ons are independent opt-in entitlements. Store Stripe IDs and state, never raw payment data. Entitlements supplement—not replace—workspace role authorization.

## 8. Stripe product and price configuration plan

After approval, create three Products and six immutable CAD Prices: Control `1200/month`, `12000/year`; Oversight `3900/month`, `39000/year`; Command `9900/month`, `99000/year`. Separate Prices: setup `7900` once, quoted migration from `19900`, templates `1500/month`, support `2500/month`. Use Checkout, automatic tax only after nexus review, and Portal. Derive amounts server-side. Verify webhook signatures; deduplicate by Stripe event ID in the same database transaction as entitlement updates; log event types without customer details. This build creates no Stripe objects.

## 9. Trial, upgrade, downgrade, cancellation, and payment-failure user flows

- **Trial:** verified signup → idempotent starter workspace/sample records/checklist → `trialEndsAt=now+14d` → exact end-date notices → read-only on expiry; no card or charge.
- **Upgrade:** Owner/Billing Manager chooses plan → server price lookup → Checkout → signed webhook activates entitlement and appends audit event; redirects never prove payment.
- **Downgrade:** disclose lost access and over-limit state → explicit confirmation → period-end scheduling; never automatically delete data.
- **Cancellation:** Portal shows effective date/consequences → period-end cancellation by default → confirmation and audit record.
- **Failure:** verified failure sets `PAST_DUE`; transactional service notice; bounded recovery; owner-approved grace period; restore idempotently after verified payment.

## 10. Database schema

`prisma/schema.prisma` models users, workspace roles, vendors, agreements/documents with scan state, approvals, subscription state, deduplicated Stripe events, consent, and append-only audit events. Production additionally requires PostgreSQL row-level security, tenant context, append-only audit permissions, reviewed migrations, retention, and backup-restore tests.

## 11. API routes and authorization requirements

| Route | Required server control |
|---|---|
| Workspace create | Verified user, rate limit, idempotency key |
| Workspace reads/writes | Membership-derived tenant scope; validated payload |
| Vendors/agreements | Member write; append audit |
| Upload | Membership; magic-byte/MIME/20 MB checks; private presign; quarantine and scanner callback |
| Members | Owner/Admin; member cap; cannot remove last Owner |
| Approval decision | Designated approver; strict state transition; idempotency |
| Checkout/Portal | Owner/Billing Manager; CSRF/origin; server price mapping; rate limit |
| Stripe webhook | Raw body, signature, freshness, event-ID dedupe, transaction |

Cookies must be `Secure`, `HttpOnly`, and `SameSite=Lax`; cookie-auth mutations enforce CSRF/same-origin. Every protected query derives workspace scope from authenticated membership. Current commerce adapters intentionally fail closed.

## 12. Next.js folder structure

`app/` contains App Router pages, metadata, sitemap, robots and API adapters; `components/` accessible interactive UI; `lib/` validated configuration and plan contracts; `prisma/` PostgreSQL schema; `docs/` operating blueprint; `public/` approved static assets.

## 13. Reusable React component architecture

`Header`/`Footer` provide landmarks and disclaimer; `Dashboard` is a clearly illustrative preview; `RoiCalculator` computes transparent estimates; `Pricing` owns interval selection and explicit add-on consent. Future `WorkspaceShell`, forms, and entitlement guards remain server-authorized. UI never decides authorization.

## 14. Fully implemented responsive homepage and pricing page

`app/page.tsx` and `app/pricing/page.tsx` implement both routes with the required glass UI, restrained cyan/violet accents, responsive grids, precise copy, and disabled commerce boundary.

## 15. Accessible UI states and motion design

Semantic landmarks/headings, labelled numeric inputs, `aria-pressed` billing controls, table caption/headers, native FAQ disclosures, skip navigation, visible focus, and responsive reflow are implemented. `prefers-reduced-motion` suppresses motion. Before launch test keyboard-only, VoiceOver/NVDA, 200%/400% zoom, 320 px reflow, contrast, and console errors.

## 16. Lifecycle email copy

Every email footer identifies the owner-approved legal sender/address and says: “You received this because you started a workspace or explicitly opted in. Manage preferences or unsubscribe.” Product notices and marketing consent are separate.

1. **Immediate — Your operational command center is ready:** “Your starter workspace is ready. Add one real vendor and its next renewal date—it usually takes less than five minutes. [Add my first vendor]”
2. **Day 1 — The fastest way to get value today:** “Open one vendor or agreement and assign the person responsible. Clear ownership turns a record into action. [Assign an owner]”
3. **Day 3 — Never let a renewal surprise you again:** “Choose a renewal, confirm its notice window, and select who should be reminded. You remain responsible for checking terms. [Set a reminder]”
4. **Day 6 — A simple workflow your team can use this week:** “Activate one essential template and adapt it to your process. [Choose a template]”
5. **Day 10 — Need help getting organized?:** “Guided Workspace Setup is an optional CAD $79 one-time service. Nothing was added to your account. [Review optional setup]”
6. **Day 12 — Your free workspace ends in 2 days:** “Your trial ends [date/time zone]. Plans start at CAD $12/month or $120/year; taxes apply. No card is on file and you will not be charged unless you choose. [Compare plans]”
7. **Day 14 — Keep your operational records working for you:** “Your trial ends today. Review the exact plan price and terms before confirming. [Choose a plan]”
8. **Seven-day post-trial final:** “Review one renewal: confirm notice date, owner, usage, and decision. This is the last promotional trial email unless you opt in. [Review options]”

The queue suppresses withdrawn marketing consent, records provider IDs, bounds retries, and stops after the single post-trial message.

## 17. SEO metadata, Open Graph, sitemap, robots, and JSON-LD SaaS Product schema

`app/layout.tsx`, `sitemap.ts`, and `robots.ts` implement metadata routes. Robots blocks indexing until approval and the placeholder domain is replaced. At launch add an approved 1200×630 OG asset and trusted-constant JSON-LD `SoftwareApplication` with `BusinessApplication`, Web OS, CAD Offers matching live totals, and `P14D`; publish no Offers before commerce approval.

## 18. Analytics plan

Analytics stays off pending consent review. Privacy-minimized first/last-touch source captures UTM/referrer without identifier-bearing URLs. Events: workspace/sample/vendor/renewal/owner/reminder/template, checkout, activation, plan change, cancellation. Activation = real vendor + renewal + owner in 24h. Trial conversion = paid / eligible ended trials. Compute MRR from verified invoices; ARPU = MRR / paid accounts; expansion = positive account MRR delta; churn = lost starting MRR; CAC = attributable approved spend / customers; cohort LTV = ARPU × gross margin / account churn. Exclude sample/internal data.

## 19. Launch checklist

Owner signs nine confirmations; counsel approves terms/privacy/refunds/cancellation/CASL; replace domain/contact; threat-model auth/billing/uploads/tenancy/webhooks/queues; separate local/staging/production secrets/databases/storage; verify email/MFA/roles/last-owner; review Stripe test clocks/tax/portal/replay; verify private object storage/quarantine/scanning/retention; run unit/integration/negative-auth/replay/concurrency/migration/restore/accessibility/browser/load tests; configure privacy-safe logs/alerts/SLO/on-call/incident response; soft-launch behind commerce gate; validate one test-mode subscription; obtain explicit production approval and preserve instant fail-closed rollback.

## 20. Risk and compliance checklist

Exact disclaimer; no government affiliation/advice/guarantees; no fabricated reviews/logos/activity/urgency or unsupported certifications/security claims; CAD/tax/fees visible and add-ons unchecked; CASL consent/sender/opt-out and retention/subprocessors reviewed; default-deny RBAC/tenant scoping/rate limiting/revocation/audit tested; decide upload classification then validate/quarantine/scan/retain; no card data and transactional webhook dedupe; bounded queues/retries/DLQ/restore drills; dependency, provenance, secret, CSP, monitoring, canary, rollback, named owner and observation window reviewed.

> Procurement Legal Tech is an operational organization tool. It does not provide legal, tax, procurement, cybersecurity, or compliance advice.
