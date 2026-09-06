# ClearGlass Autonomous E‑Commerce Operator

A repo‑first, **governed** commerce engine. The system can *draft, detect, score, and
recommend* automatically — but pricing, refunds, payments, fulfillment and legal‑exposure
changes always pass through a **human approval gate**. Every material change is written to an
append‑only audit ledger with a risk score.

> Controlled autonomy, not a money printer. Read‑only analysis → draft → approval → execution.

## Architecture

```
clearglass-commerce/
├── control-plane/        FastAPI service that governs every change + writes the audit ledger
│   ├── app/
│   │   ├── main.py           app factory, routers, request audit
│   │   ├── config.py         env-driven settings (pydantic-settings)
│   │   ├── db.py             SQLAlchemy engine/session
│   │   ├── models.py         ORM tables (products … events, approvals)
│   │   ├── schemas.py        request/response contracts
│   │   ├── audit.py          append-only event writer
│   │   ├── governance.py     risk scoring + approval gating (the safety core)
│   │   ├── daily_loop.py     stdlib-only daily executive report (runs in CI)
│   │   └── routers/          store / orders / inventory / metrics / events / approvals
│   ├── migrations/       001_init.sql, 002_seed.sql
│   └── tests/            governance + smoke tests
├── agents/               master prompt + per-role prompts + output JSON schemas
├── storefront/           Next.js public shop (scaffold)
├── admin/                Next.js admin cockpit (scaffold)
├── docker-compose.yml    postgres + control-plane + storefront + admin
└── .env.example          configuration template (no secrets committed)
```

## Build order

1. **FastAPI control plane** — `control-plane/app`
2. **Postgres schema + migrations** — `control-plane/migrations`
3. **Next.js storefront + admin** — `storefront/`, `admin/`
4. **Audit ledger** — `events` table + `app/audit.py`
5. **Automation jobs** — `.github/workflows/commerce-daily-loop.yml`
6. **Agents** — `agents/`
7. **Analytics & alerting** — `routers/metrics.py`, `daily_loop.py`

## Quick start

```bash
cp .env.example .env            # fill in DATABASE_URL, STRIPE_*, etc.
docker compose up --build       # postgres + control-plane (:8000) + storefront (:3000) + admin (:3001)
# apply schema:
docker compose exec db psql -U commerce -d commerce -f /migrations/001_init.sql
```

Control-plane only, no Docker:

```bash
cd control-plane
pip install -r requirements.txt
uvicorn app.main:app --reload      # http://localhost:8000/docs
```

## Governance — what is gated

`app/governance.py` scores every proposed action 0–100 and routes it:

| Risk | Examples | Behaviour |
|------|----------|-----------|
| **low** (auto) | generate copy, read metrics, reconcile reports, draft messages | execute + log |
| **medium** (review) | content publish, non-price catalog edits, campaign drafts | queue approval |
| **high / critical** (block) | pricing, payment/tax settings, refunds, fulfillment rules, low-stock reorders, mass outbound | **approval required** before any execution |

Nothing in the high/critical tier executes without an `approvals` row reaching `approved`.

## Endpoints

| Method | Path | Tier |
|--------|------|------|
| `POST` | `/store/refresh-products` | medium |
| `POST` | `/store/generate-copy` | low |
| `POST` | `/store/update-pricing` | **high → approval** |
| `POST` | `/checkout/session` | customer revenue (logged) |
| `POST` | `/webhooks/stripe` | signed ingest → writes paid orders (idempotent on redelivery) |
| `POST` | `/payments/refund` | **critical → approval** |
| `GET`  | `/payments/payout-account` | low masked bank metadata |
| `GET`  | `/payouts` | low settlement records |
| `POST` | `/orders/reconcile` | low |
| `POST` | `/inventory/check` | low (reorder = high) |
| `GET`  | `/metrics/overview` | low |
| `GET`  | `/events` | low |
| `POST` | `/approvals/{id}/approve` | human |
| `POST` | `/approvals/{id}/reject` | human |
| `GET`  | `/etsy/connection` | low connection state (no network) |
| `POST` | `/etsy/verify` | low read-only identity/permission/sync check |
| `POST` | `/etsy/publish-listing` | **high → approval** |
| `POST` | `/etsy/sync-inventory` | **high → approval** |
| `POST` | `/etsy/orders/manage` | **high → approval** |

## Connecting the Etsy shop

Etsy only mints a token after the shop owner approves the scopes in a browser, so
connecting is a human step — run it once with `python -m app.etsy_connect` (OAuth2 PKCE,
stdlib only, no secret ever written to disk) and store the printed tokens as runtime env
vars. Full walkthrough in **[ETSY_CONNECT.md](ETSY_CONNECT.md)**.

Connecting grants no autonomy: every Etsy write stays in `ALWAYS_ESCALATE` and can only
be queued for approval, and before connection the write routes fail closed with
`blocked_not_connected`.

## Revenue settlement / bank wiring

Earned revenue is collected through Stripe Checkout and settled by Stripe automatic payouts to the external bank account configured in Stripe. The repository stores only masked payout metadata (`PAYOUT_EXTERNAL_ACCOUNT_ID`, `PAYOUT_BANK_NAME`, `PAYOUT_BANK_LAST4`, `PAYOUT_BANK_ROUTING_HINT`) so operators can verify the destination without exposing account/routing/transit numbers.

The control plane exposes `GET /payments/payout-account` for masked destination status and `GET /payouts` for webhook-recorded settlement events. It does **not** accept bank credentials or initiate arbitrary wires; actual money movement stays inside Stripe's payout controls and requires dashboard/API-secret configuration outside git.

## Operating rules (enforced by code + prompt)

1. Prefer verified data over assumptions.
2. Never fabricate inventory, reviews, sales, or urgency.
3. Never change live pricing/tax/payment/refund/fulfillment without approval.
4. Never send outbound messages that could violate platform/privacy/consent rules.
5. Log every action: timestamp, actor, target, payload, result, risk score.
6. Read-only analysis → draft → approval → execution.
7. One store, one niche, one offer stack until metrics prove expansion is safe.
8. Stop and escalate on missing data or low confidence.

© ClearGlass Inc. — Clarity Is Power.
