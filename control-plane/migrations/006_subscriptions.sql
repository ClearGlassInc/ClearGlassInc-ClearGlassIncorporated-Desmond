-- ClearGlass Commerce — durable Stripe subscription state.
-- Stripe remains the billing source of truth; this table is the application's entitlement cache.
-- Safe to apply after migrations 001–005. No existing rows are removed or rewritten.

CREATE TABLE IF NOT EXISTS subscriptions (
    id BIGSERIAL PRIMARY KEY,
    stripe_customer_id VARCHAR(120) NOT NULL UNIQUE,
    stripe_subscription_id VARCHAR(120) UNIQUE,
    customer_email VARCHAR(254),
    plan VARCHAR(120) NOT NULL,
    stripe_price_id VARCHAR(120),
    interval VARCHAR(16),
    status VARCHAR(32) NOT NULL,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_email ON subscriptions(customer_email);
CREATE INDEX IF NOT EXISTS idx_subscriptions_price ON subscriptions(stripe_price_id);

-- Stripe webhook idempotency ledger. Event IDs are globally unique within an account.
CREATE TABLE IF NOT EXISTS stripe_events (
    id VARCHAR(120) PRIMARY KEY,
    event_type VARCHAR(120) NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_stripe_events_received_at ON stripe_events(received_at DESC);
