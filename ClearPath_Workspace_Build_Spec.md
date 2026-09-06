# ClearPath Workspace — Build-Ready Product & Business Spec

_All prices approximate, in CAD, subject to tax, supplier licensing, FX, and payment-processor fees._

---

## 1. Overview
ClearPath Workspace is an independent productivity-subscription brand for Canadian SMBs, freelancers, remote teams, and entrepreneurs. It combines seat-based SaaS subscriptions, onboarding/migration services, and support add-ons, run with minimal daily admin by a small family team.

---

## 2. Pricing & Plans

| Plan | Monthly billing (per user/mo) | Annual billing (per user/mo) | Video/Chat | Desktop Apps + Offline | Support Tier |
|---|---|---|---|---|---|
| Business Basic (No Teams) | ~$7.20* | ~$6.00* | No | No | Standard |
| Business Basic | $9.72* | $8.10* | Yes | No | Standard |
| Business Standard | ~$20.40* | ~$17.00* | Yes | Yes | Enhanced |

*Approximate. Excludes GST/HST/PST, supplier licensing changes, currency fluctuation, and payment-processor fees.

"Business Standard" = **Most Popular** badge.

---

## 3. Database Schema (PostgreSQL DDL sketch)

```sql
-- Identity & Org
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  mfa_enabled BOOLEAN DEFAULT FALSE,
  mfa_secret TEXT,
  email_verified_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  billing_email TEXT NOT NULL,
  province TEXT,
  stripe_customer_id TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE org_members (
  org_id UUID REFERENCES organizations(id),
  user_id UUID REFERENCES users(id),
  role_id UUID REFERENCES roles(id),
  invited_at TIMESTAMPTZ,
  joined_at TIMESTAMPTZ,
  PRIMARY KEY (org_id, user_id)
);

CREATE TABLE roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,          -- owner, admin, member, billing
  permissions JSONB NOT NULL
);

-- Plans & Features
CREATE TABLE features (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT UNIQUE NOT NULL,    -- 'video_chat', 'offline_desktop', etc.
  description TEXT
);

CREATE TABLE plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT UNIQUE NOT NULL,    -- 'basic_no_teams','basic','standard'
  name TEXT NOT NULL,
  monthly_price_cents INT NOT NULL,
  annual_price_cents INT NOT NULL,
  stripe_price_id_monthly TEXT,
  stripe_price_id_annual TEXT,
  is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE plan_features (
  plan_id UUID REFERENCES plans(id),
  feature_id UUID REFERENCES features(id),
  PRIMARY KEY (plan_id, feature_id)
);

-- Billing
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id),
  plan_id UUID REFERENCES plans(id),
  stripe_subscription_id TEXT UNIQUE,
  status TEXT NOT NULL,        -- trialing, active, past_due, canceled, paused
  billing_interval TEXT NOT NULL, -- monthly, annual
  seat_count INT NOT NULL DEFAULT 1,
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  trial_end TIMESTAMPTZ,
  cancel_at_period_end BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE subscription_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subscription_id UUID REFERENCES subscriptions(id),
  stripe_item_id TEXT,
  quantity INT NOT NULL,
  unit_price_cents INT NOT NULL
);

CREATE TABLE invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id),
  subscription_id UUID REFERENCES subscriptions(id),
  stripe_invoice_id TEXT UNIQUE,
  status TEXT NOT NULL,        -- draft, open, paid, uncollectible, void
  subtotal_cents INT,
  tax_cents INT,
  total_cents INT,
  currency TEXT DEFAULT 'CAD',
  issued_at TIMESTAMPTZ,
  paid_at TIMESTAMPTZ
);

CREATE TABLE invoice_lines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id UUID REFERENCES invoices(id),
  description TEXT,
  quantity INT,
  unit_price_cents INT,
  amount_cents INT
);

CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id UUID REFERENCES invoices(id),
  stripe_payment_intent_id TEXT UNIQUE,
  amount_cents INT,
  status TEXT,                 -- succeeded, failed, refunded
  method TEXT,                 -- card, ach, etc.
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE taxes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id UUID REFERENCES invoices(id),
  jurisdiction TEXT,           -- 'ON-HST','BC-GST+PST', etc.
  rate_percent NUMERIC(5,2),
  amount_cents INT
);

CREATE TABLE coupons (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT UNIQUE NOT NULL,
  percent_off NUMERIC(5,2),
  amount_off_cents INT,
  max_redemptions INT,
  expires_at TIMESTAMPTZ,
  active BOOLEAN DEFAULT TRUE
);

CREATE TABLE coupon_redemptions (
  coupon_id UUID REFERENCES coupons(id),
  org_id UUID REFERENCES organizations(id),
  redeemed_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (coupon_id, org_id)
);

CREATE TABLE trials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id),
  plan_id UUID REFERENCES plans(id),
  started_at TIMESTAMPTZ DEFAULT now(),
  ends_at TIMESTAMPTZ,
  converted BOOLEAN DEFAULT FALSE
);

-- Affiliates / Referrals
CREATE TABLE affiliates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  code TEXT UNIQUE NOT NULL,
  commission_percent NUMERIC(5,2) DEFAULT 10.0,
  payout_email TEXT,
  status TEXT DEFAULT 'active'
);

CREATE TABLE referrals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  affiliate_id UUID REFERENCES affiliates(id),
  referred_org_id UUID REFERENCES organizations(id),
  status TEXT,                 -- pending, converted, paid
  commission_cents INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Digital Products / Orders
CREATE TABLE digital_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  price_cents INT NOT NULL,
  file_object_key TEXT,        -- S3 key
  active BOOLEAN DEFAULT TRUE
);

CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id),
  product_id UUID REFERENCES digital_products(id),
  stripe_payment_intent_id TEXT,
  amount_cents INT,
  status TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Support / Audit / Consent / Automation
CREATE TABLE support_tickets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id),
  requester_id UUID REFERENCES users(id),
  subject TEXT,
  status TEXT DEFAULT 'open',
  priority TEXT DEFAULT 'normal',
  assigned_to UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id UUID REFERENCES users(id),
  action TEXT NOT NULL,
  target_type TEXT,
  target_id UUID,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE marketing_consents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  channel TEXT,                 -- email, sms
  consent_type TEXT,            -- express, implied
  granted_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,
  source TEXT                   -- signup_form, checkbox, etc.
);

CREATE TABLE automation_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id),
  event_type TEXT NOT NULL,     -- trial_reminder, dunning_step1, winback, etc.
  payload JSONB,
  status TEXT DEFAULT 'pending',
  scheduled_for TIMESTAMPTZ,
  processed_at TIMESTAMPTZ
);

CREATE TABLE webhook_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,       -- 'stripe'
  event_id TEXT UNIQUE NOT NULL,  -- idempotency key
  type TEXT NOT NULL,
  payload JSONB NOT NULL,
  received_at TIMESTAMPTZ DEFAULT now(),
  processed_at TIMESTAMPTZ
);
```

---

## 4. API Design (REST, versioned `/api/v1`)

### Auth
- `POST /auth/signup` — email, password → creates user, sends verification email
- `POST /auth/verify-email` — token
- `POST /auth/login` — email, password → session/JWT
- `POST /auth/mfa/setup` — returns TOTP secret/QR
- `POST /auth/mfa/verify` — code
- `POST /auth/logout`

### Organizations
- `POST /orgs` — create org (owner = current user)
- `GET /orgs/:id`
- `POST /orgs/:id/invite` — email, role
- `POST /orgs/:id/members/:userId/role` — change role
- `DELETE /orgs/:id/members/:userId`

### Plans & Checkout
- `GET /plans` — public, returns pricing matrix
- `POST /checkout/session` — { planKey, seatCount, billingInterval, couponCode? } → Stripe Checkout URL
- `POST /checkout/consultation` — lead capture for "free trial/consultation" CTA

### Subscriptions
- `GET /orgs/:id/subscription`
- `POST /orgs/:id/subscription/change-plan` — { planKey, seatCount, billingInterval } (proration handled by Stripe)
- `POST /orgs/:id/subscription/cancel` — { atPeriodEnd: true, reason }
- `POST /orgs/:id/subscription/pause`
- `POST /orgs/:id/subscription/reactivate`

### Billing
- `GET /orgs/:id/invoices`
- `GET /invoices/:id/pdf`
- `POST /orgs/:id/billing-portal` — returns Stripe customer portal URL
- `POST /coupons/validate` — { code }

### Webhooks
- `POST /webhooks/stripe` — signature-verified via `Stripe-Signature` header; write to `webhook_events` (idempotent on `event_id`) then enqueue processing job

### Admin (requires admin RBAC + MFA)
- `GET /admin/customers`
- `POST /admin/refunds` — requires approval workflow (dual sign-off if > threshold)
- `GET /admin/reports/mrr`, `/arr`, `/churn`, `/cac`, `/clv`
- `GET /admin/audit-logs`
- `POST /admin/coupons`
- `GET /admin/fraud-alerts`

### Support
- `POST /tickets`
- `GET /tickets/:id`
- `POST /tickets/:id/reply`

### Affiliates
- `POST /affiliates/apply`
- `GET /affiliates/:id/dashboard`
- `GET /affiliates/:id/referrals`

---

## 5. Payment & Webhook Flow

1. Frontend calls `POST /checkout/session` → backend creates/reuses Stripe Customer, creates Checkout Session with selected Price ID (per plan/interval) and seat quantity, tax collection enabled (Stripe Tax), coupon applied if valid.
2. Customer completes checkout on Stripe-hosted page (PCI compliance offloaded — no card data touches our servers).
3. Stripe sends `checkout.session.completed`, `invoice.paid`, `customer.subscription.updated`, etc. to `/webhooks/stripe`.
4. Handler verifies `Stripe-Signature` using webhook secret; rejects on failure.
5. Event `id` checked against `webhook_events` table — if seen, return 200 immediately (idempotency).
6. Otherwise store event, enqueue background job (Redis queue) to update `subscriptions`, `invoices`, `payments`, entitlements.
7. Dunning: on `invoice.payment_failed`, trigger automation_event `dunning_step1/2/3`; Stripe Smart Retries handle retry cadence; after grace period, subscription moves to `past_due` → `canceled`, entitlements revoked.
8. Refunds: admin-initiated via `/admin/refunds`, calls Stripe Refund API, requires approval workflow logged in `audit_logs`.

---

## 6. Automation Workflow Map (event → trigger → action)

| Event | Trigger | Action |
|---|---|---|
| Signup complete | `user.created` | Welcome email #1, create org, start email-verify timer |
| Trial started | `trial.created` | Schedule day 3/7/13 nurture emails |
| Trial ending in 3 days | scheduled job | Conversion-nudge email + in-app banner |
| Payment succeeded | `invoice.paid` webhook | Receipt email, update entitlements |
| Payment failed | `invoice.payment_failed` webhook | Dunning email sequence (3 steps), admin alert if high-value account |
| Renewal upcoming | scheduled job (T-7 days) | Renewal reminder email |
| Cancellation requested | `subscription.cancel` | Survey email, schedule win-back at 30/60/90 days |
| Ticket resolved | `ticket.status=resolved` | Review-request email (only to verified customers) |
| New affiliate referral | `checkout.session.completed` with ref code | Log referral, calculate commission, notify affiliate |
| Unusual payment pattern | fraud rule engine | Flag in admin fraud queue, block processing pending review |

All marketing automations check `marketing_consents` before sending and include unsubscribe/preference-center links (CASL compliance).

---

## 7. RBAC Model (roles.permissions JSONB example)

```json
{
  "owner":   {"billing": "full", "users": "full", "settings": "full", "refunds": "approve"},
  "admin":   {"billing": "view", "users": "manage", "settings": "manage", "refunds": "request"},
  "billing": {"billing": "full", "users": "view"},
  "member":  {"billing": "none", "users": "view"}
}
```
Admin-portal staff roles (separate from customer roles): `super_admin`, `support_agent`, `finance_ops`, `marketing_ops` — each scoped via granular permission checks + mandatory MFA + session timeout (e.g., 30 min idle).

---

## 8. Environment & Infra Checklist

- [ ] Next.js/TypeScript app (App Router), separate `dev`/`staging`/`prod` Vercel or container environments
- [ ] PostgreSQL (managed, e.g., RDS/Neon) with automated daily backups + PITR
- [ ] Redis (queues via BullMQ, rate limiting)
- [ ] Stripe account in CAD, Stripe Tax enabled, webhook endpoint + signing secret per environment
- [ ] Transactional email provider (Postmark/SES) with SPF/DKIM/DMARC configured
- [ ] S3-compatible object storage for invoices/digital products, signed URLs only
- [ ] Secrets manager (Vercel/Doppler/AWS Secrets Manager) — no secrets in repo
- [ ] CI/CD: lint → unit tests → integration tests → SAST scan → deploy to staging → manual approval → prod
- [ ] Monitoring: Sentry (errors), Better Uptime/status page, structured logs
- [ ] Security headers: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- [ ] Rate limiting on auth + checkout + webhook endpoints
- [ ] CSRF tokens on all state-changing form submissions

---

## 9. Compliance Pre-Launch Checklist

- [ ] PIPEDA: privacy policy, data access/deletion request process, breach-notification procedure
- [ ] CASL: consent records (`marketing_consents`), unsubscribe on every marketing email, accurate sender identification
- [ ] GST/HST/PST registration and correct provincial tax rates via Stripe Tax
- [ ] Clear auto-renewal and cancellation disclosures (province-specific consumer protection, e.g., Quebec)
- [ ] WCAG 2.1 AA accessibility audit
- [ ] Written licensing/reseller agreements before any third-party branding or resale claims
- [ ] Legal review by Canadian lawyer; tax/pricing review by accountant

---

## 10. Family Ops — Approval Workflow Thresholds (suggested)

| Action | Approver | Threshold |
|---|---|---|
| Refund | Owner (or Finance Ops if < $100) | Dual sign-off if > $500 |
| Pricing change | Owner only | Always |
| New supplier contract | Owner only | Always |
| Marketing campaign spend | Marketing Ops, notify Owner | > $250 needs Owner sign-off |
| Account deletion | Owner | Always, logged in audit_logs |

---

_Next suggested step: turn Section 3 into actual migration files (e.g., Prisma/Drizzle schema) and Section 4 into an OpenAPI spec — happy to generate either._
