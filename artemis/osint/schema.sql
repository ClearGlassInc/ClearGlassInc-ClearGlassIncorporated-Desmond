-- ARTEMIS OSINT canonical PostgreSQL/PostGIS schema.
-- Additive: does not alter existing ClearGlass tables.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS osint_sources (
    source_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    categories JSONB NOT NULL,
    integration_mode TEXT NOT NULL,
    public_api TEXT NOT NULL,
    authentication TEXT NOT NULL,
    rate_limit TEXT NOT NULL,
    license TEXT NOT NULL,
    terms_concern TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    update_frequency TEXT NOT NULL,
    ingestion_method TEXT NOT NULL,
    endpoint TEXT,
    adapter TEXT NOT NULL,
    phase INTEGER NOT NULL CHECK (phase BETWEEN 1 AND 4),
    enabled_by_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS osint_datasets (
    dataset_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES osint_sources(source_id),
    external_dataset_id TEXT,
    name TEXT NOT NULL,
    version TEXT,
    license TEXT NOT NULL,
    terms TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS osint_source_metadata (
    source_id TEXT PRIMARY KEY REFERENCES osint_sources(source_id),
    observed_limit TEXT,
    attribution_text TEXT,
    documentation_url TEXT,
    parser_version TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS osint_locations (
    location_id TEXT PRIMARY KEY,
    geom geometry(Point, 4326) NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_osint_locations_geom ON osint_locations USING GIST (geom);

CREATE TABLE IF NOT EXISTS osint_observations (
    observation_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES osint_sources(source_id),
    dataset_id TEXT REFERENCES osint_datasets(dataset_id),
    location_id TEXT REFERENCES osint_locations(location_id),
    observed_at TIMESTAMPTZ NOT NULL,
    kind TEXT NOT NULL,
    value JSONB NOT NULL,
    confidence NUMERIC(5,4),
    provenance_sha256 CHAR(64) NOT NULL,
    source_record_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_osint_observations_source_time
    ON osint_observations(source_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_osint_observations_location_time
    ON osint_observations(location_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS osint_events (
    event_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES osint_sources(source_id),
    dataset_id TEXT REFERENCES osint_datasets(dataset_id),
    location_id TEXT REFERENCES osint_locations(location_id),
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    title TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    provenance_sha256 CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_osint_events_type_time
    ON osint_events(event_type, occurred_at DESC);

CREATE TABLE IF NOT EXISTS osint_assets (
    asset_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES osint_sources(source_id),
    external_id TEXT,
    asset_type TEXT NOT NULL,
    uri TEXT NOT NULL,
    checksum CHAR(64),
    rights_statement TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS osint_alerts (
    alert_id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES osint_sources(source_id),
    event_id TEXT REFERENCES osint_events(event_id),
    severity TEXT NOT NULL CHECK (severity IN ('info','low','medium','high','critical')),
    status TEXT NOT NULL CHECK (status IN ('open','acknowledged','resolved','suppressed')),
    rule_id TEXT,
    title TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS osint_audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    decision TEXT NOT NULL,
    request_id TEXT,
    payload_sha256 CHAR(64) NOT NULL,
    previous_hash CHAR(64) NOT NULL,
    chain_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_osint_audit_time ON osint_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_osint_alerts_open ON osint_alerts(status, created_at DESC);
