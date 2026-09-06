-- ClearGlass Commerce — initial schema (Postgres).
-- The events table is the append-only audit ledger; approvals is the human gate.

CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    slug        VARCHAR(160) UNIQUE NOT NULL,
    title       VARCHAR(240) NOT NULL,
    status      VARCHAR(32)  NOT NULL DEFAULT 'draft',
    margin_pct  NUMERIC(6,2),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS variants (
    id          SERIAL PRIMARY KEY,
    product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku         VARCHAR(120) UNIQUE NOT NULL,
    price       NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency    VARCHAR(3)    NOT NULL DEFAULT 'CAD'
);

CREATE TABLE IF NOT EXISTS customers (
    id                SERIAL PRIMARY KEY,
    email             VARCHAR(254) UNIQUE NOT NULL,
    consent_marketing BOOLEAN NOT NULL DEFAULT false,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    status      VARCHAR(32) NOT NULL DEFAULT 'pending',
    total       NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency    VARCHAR(3)  NOT NULL DEFAULT 'CAD',
    source      VARCHAR(64),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS inventory (
    id                SERIAL PRIMARY KEY,
    variant_id        INTEGER NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
    on_hand           INTEGER NOT NULL DEFAULT 0,
    reorder_threshold INTEGER NOT NULL DEFAULT 10
);

CREATE TABLE IF NOT EXISTS campaigns (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(160) NOT NULL,
    channel     VARCHAR(48)  NOT NULL,
    status      VARCHAR(32)  NOT NULL DEFAULT 'draft',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS content_assets (
    id          SERIAL PRIMARY KEY,
    product_id  INTEGER REFERENCES products(id),
    kind        VARCHAR(48) NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    status      VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Append-only audit ledger. Do not UPDATE or DELETE rows.
CREATE TABLE IF NOT EXISTS events (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor       VARCHAR(120) NOT NULL,
    action      VARCHAR(80)  NOT NULL,
    target      VARCHAR(160),
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    result      VARCHAR(32) NOT NULL DEFAULT 'ok',
    risk_score  INTEGER NOT NULL DEFAULT 0,
    risk_tier   VARCHAR(16) NOT NULL DEFAULT 'low'
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_action ON events(action);

CREATE TABLE IF NOT EXISTS approvals (
    id           SERIAL PRIMARY KEY,
    action       VARCHAR(80) NOT NULL,
    target       VARCHAR(160),
    payload      JSONB NOT NULL DEFAULT '{}'::jsonb,
    risk_score   INTEGER NOT NULL DEFAULT 0,
    risk_tier    VARCHAR(16) NOT NULL DEFAULT 'high',
    status       VARCHAR(16) NOT NULL DEFAULT 'pending',
    requested_by VARCHAR(120) NOT NULL DEFAULT 'operator',
    decided_by   VARCHAR(120),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);

CREATE TABLE IF NOT EXISTS metrics_daily (
    id              SERIAL PRIMARY KEY,
    day             VARCHAR(10) UNIQUE NOT NULL,
    revenue         NUMERIC(14,2) NOT NULL DEFAULT 0,
    orders          INTEGER NOT NULL DEFAULT 0,
    conversion_rate NUMERIC(6,4) NOT NULL DEFAULT 0,
    aov             NUMERIC(12,2) NOT NULL DEFAULT 0,
    refund_rate     NUMERIC(6,4) NOT NULL DEFAULT 0
);

-- Guard against tampering with the ledger: block updates/deletes on events.
CREATE OR REPLACE FUNCTION events_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'events is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_events_no_update ON events;
CREATE TRIGGER trg_events_no_update
    BEFORE UPDATE OR DELETE ON events
    FOR EACH ROW EXECUTE FUNCTION events_append_only();
