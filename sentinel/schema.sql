-- SENTINEL — Postgres RBAC + audit schema (authoritative access gate).
-- The vector store metadata filter is an optimization; THIS is the source of
-- truth re-checked on every retrieval before any chunk enters the LLM context.

CREATE TABLE tenants (
    tenant_id   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
    user_id     TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id),
    clearance   INT  NOT NULL DEFAULT 1,          -- sensitivity ceiling
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roles (
    role        TEXT PRIMARY KEY                  -- e.g. analyst, admin, auditor
);

CREATE TABLE user_roles (
    user_id     TEXT NOT NULL REFERENCES users(user_id),
    role        TEXT NOT NULL REFERENCES roles(role),
    PRIMARY KEY (user_id, role)
);

CREATE TABLE documents (
    doc_id      TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id),
    sensitivity INT  NOT NULL DEFAULT 1,
    source      TEXT NOT NULL,                    -- provenance pointer
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_documents_tenant ON documents(tenant_id);

CREATE TABLE doc_acl (
    doc_id      TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    role        TEXT NOT NULL REFERENCES roles(role),
    PRIMARY KEY (doc_id, role)
);

-- Append-only, tamper-evident audit (hash chain anchored in the app layer).
CREATE TABLE audit_log (
    seq         BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor       TEXT NOT NULL,
    action      TEXT NOT NULL,
    detail      JSONB NOT NULL,
    prev_hash   TEXT NOT NULL,
    entry_hash  TEXT NOT NULL
);
-- Enforce append-only at the DB layer (no UPDATE/DELETE on audit_log):
REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;

-- Authoritative re-authorization query (parameterized) used by PostgresRBAC:
--
--   SELECT d.doc_id
--   FROM   documents d
--   JOIN   doc_acl  a ON a.doc_id = d.doc_id
--   JOIN   user_roles ur ON ur.role = a.role
--   JOIN   users u ON u.user_id = ur.user_id
--   WHERE  d.doc_id    = ANY(:doc_ids)
--     AND  d.tenant_id = u.tenant_id          -- hard tenant boundary
--     AND  d.tenant_id = :tenant_id
--     AND  d.sensitivity <= u.clearance       -- clearance ceiling
--     AND  ur.user_id = :user_id;             -- role grant
--
-- Run under a short statement_timeout; on ANY error the app raises RBACError
-- and the Governance Shell denies (fail-closed).
