BEGIN;
CREATE TYPE live_visibility AS ENUM ('public', 'authenticated', 'internal');
CREATE TABLE live_sources (
  id uuid PRIMARY KEY, name text UNIQUE NOT NULL, enabled boolean NOT NULL DEFAULT false,
  classification text NOT NULL CHECK (classification IN ('PUBLIC','AUTHENTICATED','WORKSPACE','ADMIN','INTERNAL','SECRET')),
  retention_days integer NOT NULL CHECK (retention_days BETWEEN 1 AND 3650), approved_by text, approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(), CHECK (NOT enabled OR (approved_by IS NOT NULL AND approved_at IS NOT NULL))
);
CREATE TABLE live_events (
  id text PRIMARY KEY, source_id uuid NOT NULL REFERENCES live_sources(id), type text NOT NULL, version integer NOT NULL CHECK (version > 0),
  occurred_at timestamptz NOT NULL, published_at timestamptz NOT NULL, visibility live_visibility NOT NULL,
  tenant_id uuid, correlation_id text NOT NULL, sequence bigint NOT NULL CHECK (sequence >= 0), payload jsonb NOT NULL,
  payload_hash text NOT NULL, expires_at timestamptz NOT NULL, inserted_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_id, tenant_id, type, sequence), CHECK (occurred_at <= published_at),
  CHECK ((visibility = 'public' AND tenant_id IS NULL) OR visibility <> 'public')
);
CREATE INDEX live_events_replay_idx ON live_events (visibility, tenant_id, published_at DESC);
CREATE TABLE live_stream_audit (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, occurred_at timestamptz NOT NULL DEFAULT now(), actor_hash text NOT NULL,
  action text NOT NULL, stream text NOT NULL, tenant_id uuid, outcome text NOT NULL, correlation_id text NOT NULL, detail jsonb NOT NULL DEFAULT '{}'
);
ALTER TABLE live_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_event_isolation ON live_events USING (tenant_id IS NULL OR tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
COMMIT;
