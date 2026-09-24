# CRCS — Data model

Covers all 27 entities in the CRCS specification. Where the repository already has a
table that does the job, it is reused rather than duplicated
([ADR 0002](../../adr/0002-crcs-extend-existing-control-plane.md), rule 1).

Retention periods are taken from the **published** privacy policy
(`legal/privacy.html` §6) so the system cannot contradict what visitors were told. Periods
the policy does not cover are staging defaults, **BLOCKED on Q7**.

---

## 1. Classification levels

| Level | Name | Examples | Minimum handling |
|---|---|---|---|
| C0 | Public | Offer names, published prices, published content | Integrity only |
| C1 | Internal | Control log, integration health, aggregate metrics | Authenticated read |
| C2 | Confidential-personal | Lead name, work email, company, role, website, consent, attribution | Role-gated read; never in analytics or logs |
| C3 | Restricted | Free-text qualification answers, delivery notes and file links, payment references, password hashes, TOTP secrets, session hashes | OPERATOR+ read; access to free text is itself audited; never exported by default |

Three design rules follow from this table:

1. **Audit payloads carry IDs, not people.** `events.payload` and `events.target` hold
   record IDs and enums only. v1 broke this once: `checkout_started` wrote the buyer's
   email as `target` when there was no lead. Fixed in Phase 0: the target is the lead id,
   or `buyer:` plus an HMAC of the address keyed by `CRCS_AUDIT_HASH_KEY`
   (`routers/revenue.py::_buyer_ref`). The ledger is also admin-only now; it was served
   unauthenticated at `GET /events`.
2. **Free text lives in one table.** Qualification free text moves from `leads` to
   `qualification_responses`, so it can have its own access rule and a shorter retention
   period without touching pipeline metadata.
3. **Analytics is allow-listed.** `analytics_events.properties` accepts only keys named in
   the event schema; unknown keys are dropped server-side, not stored.

---

## 2. Entity register — where each entity lives

Disposition: **EXISTS** (reused as is), **EXTEND** (existing table, new columns),
**NEW**, **DEFERRED** (with the evidence that would trigger it).

| # | Entity | Physical table | Disposition | Phase | Purpose |
|---|---|---|---|---|---|
| 1 | users | `users` | NEW | 1 | Named people who can sign in to the admin app |
| 2 | roles | `roles` | NEW (3 fixed rows) | 1 | ADMIN, OPERATOR, VIEWER |
| 3 | sessions | `sessions` | NEW | 1 | Server-side admin sessions, revocable |
| 4 | leads | `leads` | EXTEND | 0–1 | One inbound prospect and their pipeline state |
| 5 | lead_consent | `lead_consent` | NEW | 1 | Consent grants and withdrawals, append-only |
| 6 | lead_activities | `lead_activities` | EXISTS | — | Timeline of everything that happened to a lead |
| 7 | lead_assignments | `leads.owner` + `lead_activities` (`owner_changed`) | EXISTS as column | DEFERRED | Separate table when a second operator is added |
| 8 | qualification_responses | `qualification_responses` | NEW (moves 4 free-text columns out of `leads`) | 1 | Free-text answers, versioned by form |
| 9 | offers | `offers` | NEW | 1 | Offer ladder as data: scope, exclusions, CTA, enabled flag |
| 10 | service_orders | `service_orders` | EXISTS | — | A paid service awaiting or in delivery |
| 11 | payment_records | `orders` | EXTEND | 1 | One payment: provider, reference, amount, status, environment |
| 12 | invoices_or_payment_requests | `payment_requests` | NEW | 2 | Owner-approved invoice or payment link for proposal-based work |
| 13 | customer_records | `customers` | EXTEND | 1 | A buyer who has paid at least once |
| 14 | opportunities | `opportunities` | DEFERRED → 2 | 2 | Trigger: first lead reaches DISCOVERY_COMPLETE |
| 15 | proposals | `proposals` | DEFERRED → 2 | 2 | Trigger: first opportunity needs a written scope |
| 16 | delivery_projects | `service_orders` | EXISTS | — | One project per paid order; multi-order projects DEFERRED to the first sprint sale |
| 17 | delivery_tasks | `delivery_tasks` | NEW | 1 | Internal checklist rows created on verified payment |
| 18 | testimonials | `testimonials` | DEFERRED → 2 | 2 | Trigger: first customer-confirmed delivery |
| 19 | referrals | `referrals` | DEFERRED → 2 | 2 | Same trigger as testimonials |
| 20 | content_items | `content_items` | DEFERRED → 2 | 2 | Trigger: first resource offered as a lead magnet |
| 21 | analytics_events | `analytics_events` | NEW | 1 | First-party funnel events, allow-listed properties |
| 22 | attribution_records | UTM columns on `leads` | EXISTS as columns | DEFERRED | Separate table only if multi-touch reporting is needed |
| 23 | revenue_control_logs | `revenue_control_logs` | EXTEND (update route, `updated_at`) | 1 | Daily commercial action and its evidence |
| 24 | audit_logs | `events` | EXTEND (hash chain) | 2 | Append-only record of every material action |
| 25 | integration_health | `integration_health` | EXISTS, not yet written | 1 | Last success and failure per integration |
| 26 | feature_flags | host environment variables | EXISTS as env | DEFERRED | Money-gating flags stay in env so changing them is a host-level, audited act |
| 27 | system_notifications | `system_notifications` | NEW | 1 | Internal alerts to the owner; never customer-facing |

---

## 3. Entity register — governance

Access column = lowest role that can **read**; writes are in §5.

| # | Entity | Class | Retention (source) | Read access | Audit events | Deletion / anonymisation |
|---|---|---|---|---|---|---|
| 1 | users | C3 | Active + 1 year after deactivation (staging default) | ADMIN | created, role_changed, deactivated, mfa_enrolled | Deactivate; keep id and display name for audit attribution |
| 2 | roles | C1 | Permanent | ADMIN | — (seeded by migration) | Not deletable |
| 3 | sessions | C3 | 30 days after expiry | ADMIN | login_succeeded, login_failed, session_revoked | Hard delete |
| 4 | leads | C2 | Non-converting: 24 months after last activity (staging default, Q7). Converted: becomes a customer record | VIEWER (metadata) | created, stage_changed, owner_changed, anonymised | Anonymise: null name, email, company, website, role; keep stage, source, dates, score |
| 5 | lead_consent | C2 | Until withdrawal + 3 years (privacy §6, marketing) | OPERATOR | granted, withdrawn | Keep withdrawal proof; drop email after period |
| 6 | lead_activities | C2 | Follows the lead | VIEWER | — (is itself a log) | Free-text `detail` cleared on lead anonymisation |
| 7 | lead_assignments | C1 | Follows the lead | VIEWER | owner_changed | Follows the lead |
| 8 | qualification_responses | C3 | Non-converting: 12 months (staging default, Q7). Converted: 5 years after engagement (privacy §6) | OPERATOR; each read audited | response_viewed | Hard delete |
| 9 | offers | C0 | Permanent; versions kept | PUBLIC (enabled only) | offer_changed (price changes routed through approval) | Retire, never delete |
| 10 | service_orders | C3 | 5 years after engagement (privacy §6) | OPERATOR | provisioned, status_changed, delivery_confirmed | Anonymise notes after period |
| 11 | payment_records | C3 | 7 years from fiscal year end (privacy §6, CRA) | VIEWER (aggregate), OPERATOR (row) | payment_verified, payment_failed, manually_reconciled, refunded | Never deleted inside 7 years; then pseudonymise the customer link |
| 12 | payment_requests | C3 | 7 years (CRA) | OPERATOR | drafted, approved, sent, paid, voided | As payment_records |
| 13 | customer_records | C2 | 5 years after last engagement (privacy §6) | OPERATOR | created, consent_changed | Anonymise; financial links survive per row 11 |
| 14 | opportunities | C2 | Follows the lead | VIEWER | stage_changed, value_changed | Follows the lead |
| 15 | proposals | C3 | Won: 7 years (contract). Lost: 24 months (staging default) | OPERATOR | drafted, approved, sent, accepted, declined | Hard delete lost proposals after period |
| 16 | delivery_projects | C3 | As service_orders | OPERATOR | as service_orders | As service_orders |
| 17 | delivery_tasks | C1 | As service_orders | OPERATOR | completed | As service_orders |
| 18 | testimonials | C2 | Private feedback: 5 years. Public-use consent: until withdrawn | OPERATOR | requested_draft, approved_send, received, public_consent_granted, public_consent_withdrawn | Withdrawal unpublishes within one working day (staging default) |
| 19 | referrals | C2 | 24 months (staging default) | OPERATOR | drafted, approved_send, received | Anonymise |
| 20 | content_items | C0/C1 | Permanent while published | PUBLIC (published only) | published, updated, unpublished | Unpublish; keep history |
| 21 | analytics_events | C1 | 26 months rolling (privacy §6) | VIEWER | — | Hard delete by job; aggregates kept |
| 22 | attribution_records | C2 | Follows the lead | VIEWER | — | Follows the lead |
| 23 | revenue_control_logs | C1 | 7 years (supports financial evidence) | VIEWER | created, updated | Not deletable |
| 24 | audit_logs | C1 (IDs only) | 7 years (financial evidence); security events 5 years (privacy §6) | ADMIN | — (is the log) | Never mutated; contains no personal data by rule 1 |
| 25 | integration_health | C1 | Current row only; history in events | VIEWER | status_changed | Overwritten in place |
| 26 | feature_flags | C1 | Host config history | Host access | Host audit log + deploy record | — |
| 27 | system_notifications | C1 | 90 days (staging default) | VIEWER | acknowledged | Hard delete |

---

## 4. Phase 1 schema (proposed migration `010_crcs_phase1.sql`)

`008_lead_public_ref.sql` shipped in Phase 0 and added `leads.public_ref` (UUID, backfilled,
unique, defaulted). `009_revenue_integrity.sql` added refunds, disputes, the PaymentIntent
and UTM attribution to `orders`. The Phase 1 migration below starts at 010.

Additive only: no existing row is removed or rewritten except the free-text move, which
copies before it nulls. Money follows the existing convention (`NUMERIC(12,2)`, CAD).

```sql
-- Identity and access -------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    name VARCHAR(16) PRIMARY KEY CHECK (name IN ('ADMIN','OPERATOR','VIEWER'))
);
INSERT INTO roles(name) VALUES ('ADMIN'),('OPERATOR'),('VIEWER') ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(254) NOT NULL UNIQUE,
    display_name VARCHAR(120) NOT NULL,
    role VARCHAR(16) NOT NULL REFERENCES roles(name) DEFAULT 'VIEWER',
    password_hash VARCHAR(255) NOT NULL,          -- scrypt, stdlib hashlib
    totp_secret_enc VARCHAR(255),                 -- encrypted at rest; NULL = not enrolled
    mfa_required BOOLEAN NOT NULL DEFAULT TRUE,
    failed_logins INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DEACTIVATED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deactivated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token_sha256 CHAR(64) NOT NULL UNIQUE,        -- raw token never stored
    mfa_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,              -- absolute; idle timeout enforced in code
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

-- Leads: anonymisation marker (public_ref already added by 008) -------------
ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS anonymised_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS qualification_responses (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    form_version VARCHAR(16) NOT NULL,
    primary_goal TEXT NOT NULL DEFAULT '',
    current_challenge TEXT NOT NULL DEFAULT '',
    business_context TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_qualification_responses_lead ON qualification_responses(lead_id);

CREATE TABLE IF NOT EXISTS lead_consent (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE SET NULL,
    customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
    purpose VARCHAR(40) NOT NULL CHECK (purpose IN ('marketing_email','service_updates')),
    granted BOOLEAN NOT NULL,                     -- false row = withdrawal
    method VARCHAR(40) NOT NULL,                  -- form_checkbox | unsubscribe_link | owner_recorded
    notice_version VARCHAR(32) NOT NULL,          -- privacy notice version shown at the time
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lead_consent_lead ON lead_consent(lead_id, recorded_at DESC);

-- Offers as data ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS offers (
    sku VARCHAR(120) PRIMARY KEY,                 -- same key as pricebook.json
    rung VARCHAR(16) NOT NULL CHECK (rung IN ('ENTRY','CORE','IMPLEMENTATION','RECURRING')),
    name VARCHAR(160) NOT NULL,
    purpose TEXT NOT NULL,
    deliverables JSONB NOT NULL DEFAULT '[]'::jsonb,
    exclusions JSONB NOT NULL DEFAULT '[]'::jsonb,
    delivery_promise TEXT,                        -- NULL until the owner confirms capacity (Q3)
    price_display VARCHAR(80),                    -- e.g. 'CAD $125', 'Proposal-based'
    purchase_mode VARCHAR(16) NOT NULL CHECK (purchase_mode IN ('CHECKOUT','BOOKING','PROPOSAL','CONTRACT')),
    primary_cta_label VARCHAR(60) NOT NULL,
    primary_cta_event VARCHAR(60) NOT NULL,       -- analytics event the CTA must emit
    prerequisite_sku VARCHAR(120),                -- e.g. sprint requires audit
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- The charged amount is NOT in this table. It stays in pricebook.json and, in live
-- mode, the Stripe Price the price book names (test_pricebook.py enforces this).

-- Payments: manual reconciliation path ------------------------------------------
ALTER TABLE orders ADD COLUMN IF NOT EXISTS provider VARCHAR(16) NOT NULL DEFAULT 'stripe';
ALTER TABLE orders ADD COLUMN IF NOT EXISTS verification VARCHAR(24) NOT NULL DEFAULT 'WEBHOOK';
  -- WEBHOOK | MANUALLY_RECONCILED; only these two count as confirmed revenue
ALTER TABLE orders ADD COLUMN IF NOT EXISTS reconciled_by INTEGER REFERENCES users(id);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS reconciliation_evidence VARCHAR(255);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS refunded_amount NUMERIC(12,2) NOT NULL DEFAULT 0;

-- Delivery ------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS delivery_tasks (
    id SERIAL PRIMARY KEY,
    service_order_id INTEGER NOT NULL REFERENCES service_orders(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    owner VARCHAR(120) NOT NULL DEFAULT 'unassigned',
    due_at TIMESTAMPTZ,
    status VARCHAR(16) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','DONE','BLOCKED')),
    completed_at TIMESTAMPTZ
);
ALTER TABLE service_orders ADD COLUMN IF NOT EXISTS intake_token_sha256 CHAR(64);
ALTER TABLE service_orders ADD COLUMN IF NOT EXISTS intake_submitted_at TIMESTAMPTZ;

-- Telemetry and notifications -----------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_events (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(48) NOT NULL,                    -- one of the 23 allow-listed events
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    session_ref CHAR(22),                         -- random per browser session; not a fingerprint
    page VARCHAR(200),
    offer_sku VARCHAR(120),
    lead_id INTEGER REFERENCES leads(id) ON DELETE SET NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb -- allow-listed keys only
);
CREATE INDEX IF NOT EXISTS idx_analytics_events_name_time ON analytics_events(name, occurred_at DESC);

CREATE TABLE IF NOT EXISTS system_notifications (
    id SERIAL PRIMARY KEY,
    severity VARCHAR(8) NOT NULL CHECK (severity IN ('SEV-1','SEV-2','SEV-3','SEV-4','INFO')),
    kind VARCHAR(48) NOT NULL,
    message VARCHAR(500) NOT NULL,                -- IDs only, no personal data
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by INTEGER REFERENCES users(id)
);

ALTER TABLE revenue_control_logs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
```

Phase 2 tables (`opportunities`, `proposals`, `payment_requests`, `testimonials`,
`referrals`, `content_items`, and the `events` hash-chain columns) are specified by the
fields in the CRCS specification and are not drafted until their trigger evidence exists.

---

## 5. Role and permission matrix

`A` = allowed. `A+appr` = allowed only after an `approvals` row reaches `approved`
(`governance.py`). `—` = denied. PUBLIC = anonymous visitor. SYSTEM = verified webhook or
scheduled job.

| Resource / action | PUBLIC | SYSTEM | VIEWER | OPERATOR | ADMIN |
|---|---|---|---|---|---|
| Read enabled offers | A | A | A | A | A |
| Edit offer copy, scope, CTA | — | — | — | draft | A+appr (medium) |
| Change a live price or enable checkout | — | — | — | — | A+appr (high) |
| Submit a qualification | A (write-only, no read-back) | — | — | — | — |
| Read lead metadata and pipeline | — | — | A | A | A |
| Read free-text answers (audited) | — | — | — | A | A |
| Change stage, owner, next action | — | A (payment, booking events) | — | A | A |
| Anonymise or delete a lead | — | A (retention job) | — | — | A (privacy request) |
| Export leads (audited) | — | — | — | — | A |
| Withdraw consent | A (signed link) | — | — | — | A (with evidence) |
| Record a verified payment | — | A (signed webhook) | — | — | — |
| Record a manually reconciled payment | — | — | — | — | A, evidence required |
| Refund | — | — | — | — | A+appr (critical) |
| Read payment rows | — | — | aggregate only | A | A |
| Edit delivery record and tasks | — | A (on payment) | — | A | A |
| Draft outbound email, proposal, testimonial or referral ask | — | A (on trigger, as draft) | — | A | A |
| Send any outbound message | — | — | — | — | A+appr |
| Publish a testimonial | — | — | — | — | A, with recorded public-use consent |
| Write the Revenue Control Log | — | — | — | A | A |
| Read the audit ledger | — | — | — | — | A |
| Manage users and roles | — | — | — | — | A+appr (high) |
| Read integration health, notifications | — | — | A | A | A |

Every "A" on a mutating row is enforced **server-side** by `require_role` and covered by
`test_route_auth_coverage.py`. The admin app hides controls a role cannot use, but that
is presentation, not enforcement.

---

## 6. Metric definitions (carried from v1, tightened)

| Metric | Definition | Source rows |
|---|---|---|
| Confirmed Revenue | Sum of `orders.total - refunded_amount` where `environment='live'`, `status='paid'`, and `verification IN ('WEBHOOK','MANUALLY_RECONCILED')` | `orders` |
| Test Revenue | Same, `environment='test'`. Shown separately, never added to Confirmed | `orders` |
| Pipeline | Sum of estimated value on open leads (Phase 2: open opportunities). Labelled **estimate** | `leads.expected_value_cad` |
| Contract value | Accepted proposals (Phase 2) | `proposals` |
| Invoiced | Sent, unpaid payment requests (Phase 2) | `payment_requests` |
| Outstanding | Invoiced minus paid | `payment_requests`, `orders` |
| MRR | Active recurring subscriptions normalised to monthly, plus owner-recorded signed recurring contracts. v1's owner-entered lead field moves to Pipeline | `subscriptions`, contracts |
| Refunded | Sum of `refunded_amount` in the period | `orders` |
| Close Rate | WON ÷ selected denominator: `WON+LOST` (default), all proposals sent, or all discovery calls completed. The denominator is printed next to the number | `leads`, `lead_activities` |
| Gross Margin | Confirmed Revenue minus recorded delivery costs. Shown as "no cost data" when no cost is recorded, never as 100% | `service_orders.delivery_cost_cad` |
| Show rate | Meetings held ÷ meetings booked | `lead_activities` |
| Form completion rate | `qualification_submitted` ÷ `qualification_started` | `analytics_events` |
| Checkout conversion | `payment_verified` ÷ `checkout_started` | `analytics_events` |
