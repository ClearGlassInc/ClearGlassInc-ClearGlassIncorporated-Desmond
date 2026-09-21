-- ClearGlass Revenue Command System — additive migration after 006_subscriptions.sql.

ALTER TABLE orders ADD COLUMN IF NOT EXISTS environment VARCHAR(16) NOT NULL DEFAULT 'unknown';

CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(160) NOT NULL,
    email VARCHAR(254) NOT NULL,
    company VARCHAR(240),
    website VARCHAR(500),
    role VARCHAR(160),
    service_interest VARCHAR(160) NOT NULL,
    primary_goal TEXT NOT NULL DEFAULT '',
    current_challenge TEXT NOT NULL DEFAULT '',
    business_context TEXT NOT NULL DEFAULT '',
    desired_timeline VARCHAR(80),
    investment_range VARCHAR(80),
    notes TEXT NOT NULL DEFAULT '',
    source VARCHAR(120) NOT NULL DEFAULT 'direct',
    landing_page VARCHAR(500),
    referrer VARCHAR(500),
    utm_first_source VARCHAR(120),
    utm_first_medium VARCHAR(120),
    utm_first_campaign VARCHAR(160),
    utm_last_source VARCHAR(120),
    utm_last_medium VARCHAR(120),
    utm_last_campaign VARCHAR(160),
    consent_marketing BOOLEAN NOT NULL DEFAULT FALSE,
    stage VARCHAR(40) NOT NULL DEFAULT 'NEW',
    owner VARCHAR(120) NOT NULL DEFAULT 'unassigned',
    next_action TEXT NOT NULL DEFAULT 'Review new lead',
    next_action_at TIMESTAMPTZ,
    lead_score INTEGER NOT NULL DEFAULT 0,
    score_explanation TEXT NOT NULL DEFAULT '',
    expected_value_cad NUMERIC(12,2),
    monthly_recurring_value_cad NUMERIC(12,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_next_action_at ON leads(next_action_at);

CREATE TABLE IF NOT EXISTS lead_activities (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    activity_type VARCHAR(64) NOT NULL,
    actor VARCHAR(120) NOT NULL DEFAULT 'system',
    detail TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lead_activities_lead ON lead_activities(lead_id, created_at DESC);

CREATE TABLE IF NOT EXISTS service_orders (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
    lead_id INTEGER REFERENCES leads(id) ON DELETE SET NULL,
    sku VARCHAR(120) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'INTAKE_REQUIRED',
    scope_status VARCHAR(40) NOT NULL DEFAULT 'AWAITING_SCOPE_CONFIRMATION',
    delivery_owner VARCHAR(120) NOT NULL DEFAULT 'unassigned',
    due_at TIMESTAMPTZ,
    customer_next_step TEXT NOT NULL DEFAULT 'Complete the secure intake.',
    internal_checklist JSONB NOT NULL DEFAULT '[]'::jsonb,
    file_links JSONB NOT NULL DEFAULT '[]'::jsonb,
    delivery_confirmed_at TIMESTAMPTZ,
    follow_up_at TIMESTAMPTZ,
    delivery_cost_cad NUMERIC(12,2),
    testimonial_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_service_orders_status ON service_orders(status);
CREATE INDEX IF NOT EXISTS idx_service_orders_lead ON service_orders(lead_id);

CREATE TABLE IF NOT EXISTS revenue_control_logs (
    id SERIAL PRIMARY KEY,
    action_date VARCHAR(10) NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL DEFAULT '',
    expected_outcome TEXT NOT NULL DEFAULT '',
    action_taken TEXT NOT NULL DEFAULT '',
    evidence TEXT NOT NULL DEFAULT '',
    result TEXT NOT NULL DEFAULT '',
    next_action TEXT NOT NULL DEFAULT '',
    due_date VARCHAR(10),
    owner VARCHAR(120) NOT NULL DEFAULT 'unassigned',
    status VARCHAR(40) NOT NULL DEFAULT 'NOT_STARTED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_revenue_control_logs_day ON revenue_control_logs(action_date DESC);
CREATE INDEX IF NOT EXISTS idx_revenue_control_logs_status ON revenue_control_logs(status);

CREATE TABLE IF NOT EXISTS integration_health (
    id SERIAL PRIMARY KEY,
    integration VARCHAR(80) UNIQUE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'UNKNOWN',
    last_success_at TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ,
    details TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
