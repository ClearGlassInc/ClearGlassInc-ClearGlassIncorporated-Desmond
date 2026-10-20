-- Durable Stripe event inbox, transactional outbound jobs, and resumable reconciliation.
-- Additive migration after 001–010. Does not rewrite existing order/event rows.

CREATE TABLE IF NOT EXISTS stripe_event_inbox (
    id BIGSERIAL PRIMARY KEY,
    account_scope VARCHAR(160) NOT NULL,
    stripe_event_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(160) NOT NULL,
    related_object_id VARCHAR(255),
    livemode BOOLEAN NOT NULL DEFAULT FALSE,
    event_format VARCHAR(16) NOT NULL DEFAULT 'snapshot'
        CHECK (event_format IN ('snapshot', 'thin')),
    source VARCHAR(24) NOT NULL DEFAULT 'webhook',
    verification_method VARCHAR(32) NOT NULL,
    verified_at TIMESTAMPTZ,
    payload_sha256 CHAR(64) NOT NULL,
    raw_payload TEXT,
    state VARCHAR(24) NOT NULL DEFAULT 'pending'
        CHECK (state IN ('pending', 'processing', 'retry', 'succeeded', 'dead_letter')),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    lease_owner VARCHAR(160),
    lease_expires_at TIMESTAMPTZ,
    fencing_token INTEGER NOT NULL DEFAULT 0,
    last_error_code VARCHAR(80),
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_stripe_inbox_account_event UNIQUE (account_scope, stripe_event_id)
);
CREATE INDEX IF NOT EXISTS idx_stripe_inbox_claim
    ON stripe_event_inbox(state, next_attempt_at, received_at);
CREATE INDEX IF NOT EXISTS idx_stripe_inbox_object
    ON stripe_event_inbox(related_object_id);

CREATE TABLE IF NOT EXISTS stripe_outbox_jobs (
    id BIGSERIAL PRIMARY KEY,
    operation_key VARCHAR(320) NOT NULL UNIQUE,
    job_type VARCHAR(80) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    state VARCHAR(24) NOT NULL DEFAULT 'pending'
        CHECK (state IN ('pending', 'processing', 'retry', 'succeeded', 'dead_letter')),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    lease_owner VARCHAR(160),
    lease_expires_at TIMESTAMPTZ,
    fencing_token INTEGER NOT NULL DEFAULT 0,
    last_error_code VARCHAR(80),
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_stripe_outbox_claim
    ON stripe_outbox_jobs(state, next_attempt_at, created_at);

CREATE TABLE IF NOT EXISTS stripe_reconciliation_checkpoints (
    name VARCHAR(120) PRIMARY KEY,
    window_start_at TIMESTAMPTZ,
    cursor_event_id VARCHAR(255),
    last_completed_at TIMESTAMPTZ,
    last_result TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
