# ADR 0002 — Build CRCS on the existing control plane, not a new stack

- **Status:** Proposed (owner acceptance required)
- **Date:** 2026-09-24
- **Context layer:** ClearGlass Revenue Command System (CRCS)
- **Decision owners:** ClearGlass Inc.
- **Related:** `docs/crcs/ARCHITECTURE.md`, `docs/REVENUE_COMMAND_SYSTEM.md`, `CLAUDE.md`

## Context

The CRCS specification recommends by default a unified Next.js 15+ TypeScript app with
PostgreSQL and Prisma or Drizzle (Option A), or Astro plus a backend service (Option B).

This repository already contains, on `main`:

| Capability the spec needs | Where it already exists | Evidence it works |
|---|---|---|
| Hosted Stripe checkout, server-side pricing | `control-plane/app/payments.py`, `pricebook.py` | `tests/test_pricebook.py` pins the checkout schema to `{sku, quantity}` |
| Signed webhook, live/test split, idempotent redelivery | `routers/payments.py`, migrations 004 and 006 | Signature policy: `tests/test_stripe_webhook_policy.py`. Redelivery: `test_subscriptions.py::test_redelivered_event_is_skipped_and_recorded` (subscription webhook only). **Untested today:** checkout-webhook redelivery on `orders.external_ref` and the live-only CRCS provisioning branch; Phase 1 adds both |
| Risk-scored approval gate | `governance.py` | `tests/test_governance.py`, `daily_loop.py` self-check |
| Append-only audit ledger | `audit.py`, `events` | Used by every mutating route |
| Admin gating enforced by test | `security.py` `require_admin` | `tests/test_route_auth_coverage.py` |
| Per-IP throttles, trusted-proxy handling | `security.py` | `tests/test_subscriptions.py` asserts 429s on the throttled routes |
| Leads, stages, activities, service orders, control log | `routers/revenue.py`, migration 007 | `tests/test_revenue_routes.py` |
| Authenticated operator UI shell | `admin/` (Next.js, signed session cookie) | `admin/middleware.ts`, `lib/session.ts` |
| Subscriptions for recurring revenue | migration 006, `routers/subscriptions.py` | `tests/test_subscriptions.py` |

Constraints that apply regardless of stack:

1. **GitHub Actions dispatches no runners** (`docs/BASELINE.md` F1). Pages publishes only
   through branch deploy. A public site that needs a build step (Next.js, Astro) would stop
   publishing unless hosting moves too.
2. **No revenue has been verified.** Stripe cannot charge (`STRIPE_SETUP.md`), and the
   no deployed control plane was found (the connected Render workspace holds no service
   or database for it, 2026-09-24).
3. **One operator.** There is no second person to justify SSO or a multi-tenant design.

## Options

| | A. New Next.js + Prisma app | B. Astro + new backend | C. Extend control plane + admin app (chosen) |
|---|---|---|---|
| Time to first captured lead | Weeks: rebuild forms, auth, payments, audit | Weeks: same, plus two stacks | Days: host + one meta tag + Phase 0 fixes |
| Reuses tested payment and governance code | No, must be ported and re-tested | No | Yes |
| Audit ledger | Second ledger, or cross-stack writes | Second ledger | One ledger |
| Public site deploy | Needs a build host; Pages branch deploy lost | Same | Unchanged (static) |
| Attack surface | Two backends during migration | Two or three | One backend, one admin app |
| TypeScript strict end-to-end | Yes | Partly | Admin/storefront only; Python typed + ruff |
| Relational pipeline, jobs, RBAC | Build | Build | Extend existing models |

## Decision

**Option C.** Keep the public site static on GitHub Pages. Keep the FastAPI control plane
as the single system of record and the single audit ledger. Put every owner-facing
screen in the existing Next.js `admin/` app, which calls the control plane from its
server. Add RBAC, adapters, and the missing entities to the control plane as additive
numbered SQL migrations.

## Consequences

**Positive**

- The first lead can be captured as soon as the owner approves a host; no rewrite stands
  between the business and its first conversation.
- Payment verification, idempotency and approval gating stay on code that already has
  tests.
- One place to answer "why does the cockpit show this number": the `events` ledger.

**Negative, accepted**

- Schema management is hand-written SQL migrations plus SQLAlchemy models, not Prisma.
  Mitigation: a migration-parity test (models vs. migrations) in Phase 1.
- Two languages. The owner-facing UI is TypeScript strict; the system of record is Python.
- The public pages stay hand-authored HTML. Mitigation: shared form script and design
  tokens in one file each.

**Rules this decision imposes**

1. No second payment webhook handler, audit ledger, or lead table anywhere in the repo.
2. The browser never holds a control-plane credential. Admin screens live only in `admin/`.
3. `AUTO_CREATE_TABLES=false` in production; numbered migrations are the schema source.
4. Every new mutating route uses `require_role` and appears in
   `test_route_auth_coverage.py`.

## Revisit when

- A second operator needs access through a company identity provider, **or**
- public pages need per-request server rendering (personalisation, gated content), **or**
- the Pages branch-deploy constraint is lifted **and** a measured performance or
  conversion problem is traced to the static site.
