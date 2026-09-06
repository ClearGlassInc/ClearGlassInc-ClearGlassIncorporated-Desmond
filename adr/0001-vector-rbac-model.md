# ADR 0001 — Vector-DB RBAC model for the Intelligence Layer

- **Status:** Accepted
- **Date:** 2026-06-04
- **Context layer:** SENTINEL Governance Shell / JARVIS·PERCIVAL OS Knowledge Intelligence
- **Decision owners:** ClearGlass Inc.

## Context

Phase-One requires permission-aware document Q&A. The open question: how to
enforce RBAC at the vector-database level. Two pure options were on the table:

1. **Metadata-only filtering at query time** — one shared index; every query
   carries an ACL predicate.
2. **Physical isolation per user** — a separate namespace/collection per user.

Both are inadequate alone:

- *Metadata-only* is **fail-open by construction**: a single omitted predicate,
  an ANN post-filter recall gap, or a poisoned/stale `allowed_roles` value
  leaks data. A filter omission returns *everything* — the opposite of our
  fail-closed doctrine.
- *Per-user physical isolation* causes **namespace explosion** (10⁴–10⁶
  partitions), cold-start latency, cost, and makes cross-user sharing
  intractable. Right primitive, wrong granularity.

## Decision

Adopt a **hybrid, defense-in-depth** model:

1. **Tenant boundary = hard partition.** One namespace/collection per tenant
   (Pinecone namespace; Milvus partition-key or collection). Gives blast-radius
   containment, per-tenant deletion (GDPR "forget"), and per-tenant KMS keys.
2. **Role / sensitivity = ACL metadata pre-filter** applied *inside* the tenant
   partition (`tenant_id`, `doc_id`, `sensitivity`, `allowed_roles[]`, `owner`).
   This is an **optimization** that narrows candidates and keeps ANN recall high
   (the per-tenant index stays small).
3. **Authority = post-retrieval re-authorization** of every returned `doc_id`
   against Postgres RBAC, before any chunk enters the LLM context. The vector
   filter is never trusted as the gate. A vector-layer bug or poisoned metadata
   degrades to *missed results*, never *leaked results*.

### Mapping to the Governance Shell equation

`R_data ⊆ P_user` is enforced as:
- (a) tenant namespace selected **server-side** from the authenticated
  principal — never from a client-supplied field; **AND**
- (b) ACL predicate `allowed_roles ∩ user_roles ≠ ∅ ∧ sensitivity ≤ clearance`
  injected into the vector query; **AND**
- (c) authoritative Postgres recheck of the candidate `doc_id`s.

**Fail-closed:** if `P_user` cannot be resolved (e.g. DB timeout), the Shell
emits a deny-all filter (`WHERE false`) and the gate returns **Denied** — an
unverifiable boundary is never treated as permissive.

## Selective exception

High-sensitivity *compartments* (legal hold, classified projects) may warrant
**project/user-level physical isolation** as an explicit exception — not the
default.

## Consequences

- **Positive:** fail-closed; breach-containing; high recall; clean per-tenant
  delete + key isolation; provider-agnostic.
- **Negative:** per-tenant namespace + key adds provisioning overhead → automate
  at tenant-create. Two-step authorization (filter + recheck) adds one Postgres
  round-trip per retrieval → mitigated by short statement timeout + caching of
  `P_user` per request.
- **Validation:** recall test harness required before Phase-One exit to confirm
  in-partition filtering does not degrade retrieval quality.

## Reference implementation

`sentinel/` — runnable, 11 passing proof tests, including cross-tenant
containment when the vector store deliberately leaks.
