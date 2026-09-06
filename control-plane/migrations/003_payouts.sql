-- ClearGlass Commerce — payouts table (Postgres).
-- Records Stripe payout settlements to the platform's connected bank account.
-- No raw bank details are stored: `destination` holds Stripe's opaque external-account
-- token (e.g. ba_…), never an account or routing number. `amount` is in major units.

CREATE TABLE IF NOT EXISTS payouts (
    id               SERIAL PRIMARY KEY,
    stripe_payout_id VARCHAR(120) UNIQUE NOT NULL,
    amount           NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency         VARCHAR(3)  NOT NULL DEFAULT 'CAD',
    status           VARCHAR(32) NOT NULL DEFAULT 'pending',
    destination      VARCHAR(120),
    tenant_id        VARCHAR(120),
    arrival_date     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_payouts_tenant ON payouts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_payouts_created ON payouts(created_at DESC);
