-- ClearGlass Operations Platform
-- Draft only: NOT APPLIED.
-- Reason: repository discovery found no configured database provider.
-- Apply only after an approved PostgreSQL persistence adapter, retention design,
-- backup/restore plan, and migration owner exist.

create extension if not exists pgcrypto;

create table if not exists cg_operations_tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists cg_operations_cases (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references cg_operations_tenants(id),
  reference text not null,
  title text not null,
  created_by text not null,
  status text not null check (status in ('open','closed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, reference)
);

create table if not exists cg_operations_incidents (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references cg_operations_tenants(id),
  case_id uuid references cg_operations_cases(id),
  title text not null,
  description text not null default '',
  category text not null,
  priority text not null check (priority in ('low','medium','high','critical')),
  status text not null check (status in ('open','assigned','in_review','resolved','closed')),
  created_by text not null,
  assigned_to text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists cg_operations_evidence_items (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references cg_operations_tenants(id),
  incident_id uuid not null references cg_operations_incidents(id),
  filename text not null,
  content_type text not null,
  size_bytes bigint not null check (size_bytes >= 0),
  sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  storage_key text not null,
  status text not null check (status in ('quarantined','available','rejected','held')),
  created_by text not null,
  created_at timestamptz not null default now(),
  version integer not null default 1 check (version > 0),
  current_version_id uuid
);

create table if not exists cg_operations_evidence_versions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references cg_operations_tenants(id),
  evidence_item_id uuid not null references cg_operations_evidence_items(id),
  version integer not null check (version > 0),
  sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  size_bytes bigint not null check (size_bytes >= 0),
  storage_key text not null,
  created_by text not null,
  created_at timestamptz not null default now(),
  original boolean not null default false,
  unique (evidence_item_id, version)
);

alter table cg_operations_evidence_items
  add constraint fk_current_evidence_version
  foreign key (current_version_id) references cg_operations_evidence_versions(id);

create table if not exists cg_operations_custody_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references cg_operations_tenants(id),
  evidence_id uuid not null references cg_operations_evidence_items(id),
  actor text not null,
  action text not null,
  evidence_sha256 text not null check (evidence_sha256 ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now()
);

create table if not exists cg_operations_audit_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references cg_operations_tenants(id),
  actor text not null,
  action text not null,
  entity_type text not null,
  entity_id uuid not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_cg_ops_cases_tenant on cg_operations_cases(tenant_id);
create index if not exists idx_cg_ops_incidents_tenant on cg_operations_incidents(tenant_id);
create index if not exists idx_cg_ops_evidence_incident on cg_operations_evidence_items(tenant_id, incident_id);
create index if not exists idx_cg_ops_evidence_versions_item on cg_operations_evidence_versions(tenant_id, evidence_item_id);
create index if not exists idx_cg_ops_custody_evidence on cg_operations_custody_events(tenant_id, evidence_id);
create index if not exists idx_cg_ops_audit_tenant_created on cg_operations_audit_events(tenant_id, created_at);

-- Rollback (when/if this migration is actually applied):
-- The evidence-version foreign keys must be removed in dependency order.
-- alter table cg_operations_evidence_items drop constraint if exists fk_current_evidence_version;
-- drop table cg_operations_audit_events;
-- drop table cg_operations_custody_events;
-- drop table cg_operations_evidence_versions;
-- drop table cg_operations_evidence_items;
-- drop table cg_operations_incidents;
-- drop table cg_operations_cases;
-- drop table cg_operations_tenants;
