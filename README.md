# ClearGlass — Secure Subscription System

**Brand:** CLEARGLASS — See Through Everything.  
**Purpose:** Cybersecurity, AI governance, digital resilience, intelligence, automation, risk engineering, evidence provenance, auditable decision-making.

Production-capable paid subscription built on **Next.js 14 App Router + Prisma + Auth.js + Stripe**.

---

## 1. Repository Findings (actual evidence)

- Previous artifact: React + Tailwind (zinc palette, accent #0a66c2, rounded-[16px]/[20px], branch/PR workflow note).
- No package.json/backend detected in uploaded workspace — treated as static-first repo.
- Decision: Keep front-end design language, add minimal secure backend compatible with Vercel/Cloudflare Pages/Netlify.
- Existing pages: rescue landing draft only — pricing/dashboard/subscription added without deleting existing functionality.
- No existing auth or DB — implemented smallest secure compatible: **Prisma (Postgres) + Auth.js Email magic link + Resend**.

## 2. Architecture Decision

**Chosen:** Next.js API Routes + Prisma Postgres + Auth.js + Stripe Checkout + Webhook + Customer Portal.

Why secure & compatible:
- Server-only Stripe secret key (`lib/stripe.ts` reads `getEnv()` server-side only).
- Pricing page sends only `planKey` — server resolves allowlisted Price ID from env.
- Webhook uses raw body + `stripe.webhooks.constructEvent` with `STRIPE_WEBHOOK_SECRET`.
- Idempotency via `ProcessedEvent` table (unique `stripeEventId`).
- Entitlement checked server-side in `lib/entitlement.ts` — never from localStorage or success page.
- Auth required for dashboard/account/portal — Customer ID retrieved only from DB.
- Deployment compatible: Vercel Functions (or Netlify/Cloudflare via next-on-pages). No secrets in client bundle.
- Minimal data: User, stripeCustomerId, Subscription (status, period end, entitlement), ProcessedEvent, AuditLog. No card data.

What requires manual Stripe Dashboard setup: products/prices, portal config, webhook endpoint, tax.

## 3. Implementation Plan

Files to add:
- `app/` marketing + pricing + dashboard + success/cancel/account/login
- `app/api/checkout`, `webhook`, `portal`, `me`
- `lib/env.ts`, `plans.ts`, `stripe.ts`, `db.ts`, `entitlement.ts`, `auth.ts`, `rateLimit.ts`
- `components/Header.tsx`, `PricingCard.tsx`
- `prisma/schema.prisma`
- `__tests__/plans.test.ts`, `entitlement.test.ts`
- `.env.example`, `tailwind.config.ts`, `next.config.js`, etc.

Files modified: none (greenfield scaffold preserving design system).

Files not touched: existing rescue draft artifact kept separate (do not delete).

Risks: If deploying to pure GitHub Pages, serverless companion required. Resend needed for email in prod, else dev console log.

## 4. Implementation (done in this scaffold)

- Plan registry with 5 keys: signal_monthly/annual, assurance_monthly/annual, northstar_enterprise — maps to env vars, entitlement keys, features.
- Checkout endpoint: validates planKey (zod), rate limit, resolves allowlisted Price ID, creates Stripe Checkout Session subscription mode, success/cancel URLs from `APP_BASE_URL`, metadata (planKey, entitlement, userId, environment), returns URL.
- Webhook endpoint: reads raw body, verifies signature, handles 7 events, idempotent, upserts subscription, audit logs.
- Access control: `getEntitlement()` checks active/trialing/past_due (policy: past_due still entitled briefly), `cancel_at_period_end` preserves until period end.
- Customer Portal: requires auth, retrieves Customer ID from DB only, creates portal session.
- UI: pricing with loading/disabled/error/success states, success page does NOT grant access — polls `/api/me`, dashboard redirects non-entitled to pricing message.
- Security: env validation at startup, CSP headers in next.config, rate limiting, no secrets in client, `.env.example` no real values.

## 5. Validation Results

Run:
```
npm install
npx prisma generate
npx prisma db push (or migrate)
npm run test  # vitest — plan allowlist, injection, entitlement hierarchy
npm run lint
npm run build
```

Expected:
- Tests pass: allowlist maps only to env Price IDs, invalid plan fails, injection rejected.
- Build passes with `APP_BASE_URL`, `DATABASE_URL`, `AUTH_SECRET`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` set (use .env.example template).
- Secret scan: `grep -R "sk_live" --exclude-dir=node_modules` must be empty, no `whsec_` in repo.

## 6. Stripe Dashboard Checklist

1. Products:
   - Create Product: ClearGlass Signal, ClearGlass Assurance, ClearGlass Northstar (if self-serve)
2. Recurring Prices:
   - Signal Monthly — e.g., $49/mo, copy Price ID → STRIPE_PRICE_SIGNAL_MONTHLY
   - Signal Annual — e.g., $490/yr
   - Assurance Monthly — e.g., $199/mo
   - Assurance Annual — e.g., $1990/yr
   - Northstar Enterprise — leave empty if sales-led, else annual
3. Customer Portal:
   - Settings → Billing → Customer Portal → Enable, allow: cancel, update payment method, invoices, promotion codes.
   - Set Business info, terms, privacy.
4. Webhook endpoint:
   - URL: `https://yourdomain.com/api/webhook` (Vercel deployment URL)
   - Events: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`, `customer.updated`
   - Copy Signing secret → STRIPE_WEBHOOK_SECRET
5. Test mode verification:
   - Use Stripe CLI: `stripe listen --forward-to localhost:3000/api/webhook`
   - Test card: 4242 4242 4242 4242, any future date, CVC any, ZIP any.
   - Complete checkout → verify webhook 200, DB subscription active, dashboard unlocks.
6. Live mode transition:
   - Repeat products/prices in Live mode, new Price IDs, new webhook endpoint with live URL, new STRIPE_WEBHOOK_SECRET, switch keys.

## 7. Deployment Checklist

**Vercel (recommended):**
- Import repo, Framework: Next.js
- Env vars: set all from .env.example (DATABASE_URL = Neon/Vercel Postgres), AUTH_SECRET=`openssl rand -base64 32`, APP_BASE_URL=`https://yourdomain.com`
- Build: `next build`
- After deploy, set webhook URL in Stripe to `https://yourdomain.com/api/webhook`
- Test: `curl https://yourdomain.com/api/me` → unauthenticated false
- Real test: sign in via /login, go /pricing, checkout with test card, wait for webhook, /dashboard should show entitled

**Cloudflare Pages:**
- Use `@cloudflare/next-on-pages`, set compatibility, env vars in Pages settings, D1/Neon for Postgres or adapt schema to D1 SQLite.

**Netlify:**
- Next.js plugin, env vars in Netlify UI, same webhook URL.

Database:
- For local: change prisma datasource provider to sqlite for dev.db quickly if needed, but prod must be Postgres.
- `npx prisma migrate dev --name init`

## 8. Final Acceptance Checklist

- [ ] Pricing page renders with 3 tiers (Signal/Assurance/Northstar) using existing design system
- [ ] Plan selection sends only planKey, not Price ID
- [ ] Checkout Session created server-side with allowlisted Price ID
- [ ] Stripe Checkout receives user correctly (email or customer)
- [ ] Webhook signature verification works with raw body
- [ ] Verified event updates subscriber status (upsert + audit)
- [ ] Duplicate webhook event ignored (ProcessedEvent unique)
- [ ] Subscriber access server-authorized (dashboard redirects if none)
- [ ] Customer Portal works (retrieves Customer ID from DB only)
- [ ] Cancellation at period end preserves until period end, deleted revokes
- [ ] Success page does not grant access by itself (polls /api/me)
- [ ] No secrets in repo, .env.example only placeholders
- [ ] Build, lint, tests pass
- [ ] Documentation complete
- [ ] Live mode not claimed until live keys + webhook + e2e verified

## 9. Security Notes

- Never expose `STRIPE_SECRET_KEY` or `STRIPE_WEBHOOK_SECRET` in browser. Checked: only imported in `lib/stripe.ts`, `app/api/*` (server only).
- Checkout rate limit per IP (default 10/min, env configurable).
- Safe errors: generic messages to client, detailed logs server-side only.
- CSP, X-Frame DENY, nosniff in next.config.
- Minimal data: no card numbers, no CVV.

## 10. Known Limitations & Future

- Seat-based billing not implemented (quantity=1). Add `quantity` + org membership table later.
- Trial periods: Stripe trial supported via dashboard price config; entitlement treats trialing as entitled.
- Promotional access / manual grant: add `manualEntitlement` table and merge logic in `getEntitlement`.
- Enterprise contracts not billed via Checkout: create subscription via Stripe API directly and same webhook path.
- Auth: Email magic link only. Add OAuth (Google, GitHub) if needed via Auth.js providers.
- For GitHub Pages only hosting, you must deploy this Next.js app separately and link from static site, as secret keys cannot live in static.

---

## Run Locally

```bash
cp .env.example .env.local
# fill values
npm install
npx prisma generate
npx prisma db push
npm run dev
# in another terminal
npm run stripe:listen
# open http://localhost:3000/pricing
```
