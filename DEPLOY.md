# Deploying the ClearGlass Commerce store

The control plane is a stateless FastAPI container + a Postgres database. The storefront and
admin are Next.js apps. Below are three paths — pick one.

## A. Render (one blueprint, recommended)

`render.yaml` in this folder provisions the API **and** a managed Postgres 16 database.

1. Push this repo to GitHub.
2. Render → **New +** → **Blueprint** → select the repo.
3. After the first deploy, open the `clearglass-commerce-api` service → **Environment** and set the
   `sync:false` secrets: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY`.
4. The service exposes `GET /health` (liveness) and `GET /ready` (database reachability);
   Render uses `/health` for health checks.
5. Point a Stripe webhook at `https://<your-service>.onrender.com/webhooks/stripe` and paste the
   signing secret into `STRIPE_WEBHOOK_SECRET`.

The blueprint deploys **all three services** — API, storefront, admin — plus the database.

`AUTO_CREATE_TABLES=true` creates the schema on first boot. It creates missing **tables** only,
never a missing column or a trigger, so on its own a database drifts behind every additive
migration (after `008_lead_public_ref.sql`, `POST /revenue/leads` answered 500 on an older
database). The blueprint therefore also sets `RUN_MIGRATIONS=true`: at startup the API applies
each pending file in `control-plane/migrations/` once, in order, in one transaction, and records
it in `schema_migrations`. Seed files are never applied. That also installs the append-only
ledger trigger from `001_init.sql`, which `create_all` never did.

```bash
python -m app.migrate --status   # applied / pending, changes nothing
python -m app.migrate            # apply pending (what RUN_MIGRATIONS does at boot)
python -m app.migrate --check    # exit 1 if a mapped column is missing
```

The SQL files alone produce every column the ORM maps (verified on Postgres 16), so
`AUTO_CREATE_TABLES=false` with `RUN_MIGRATIONS=true` is the hardened setting ADR 0002 asks for.
The blueprint keeps both on until an owner flips it.

### Continuous deploy (GitHub Actions)

`.github/workflows/commerce-deploy.yml` runs on every push to `main` that touches
`control-plane/**`, `storefront/**` and `admin/**`: it gates on `ruff` + the test suite, then triggers a Render deploy via a
**Deploy Hook**. To enable it:

1. Render → your API service → **Settings** → **Deploy Hook** → copy the URL.
2. GitHub → repo **Settings** → **Secrets and variables** → **Actions** → add
   `RENDER_DEPLOY_HOOK_URL`.

Without the secret the deploy step is skipped (the test gate still runs), so the workflow is safe
to merge before you have a Render account.

## B. Docker Compose (self-host / VPS)

```bash
cp .env.example .env          # fill DATABASE_URL + STRIPE_* (or leave blank for mock mode)
docker compose up --build     # db + api(:8000) + storefront(:3000) + admin(:3001)
docker compose exec db psql -U commerce -d commerce -f /migrations/001_init.sql
```

## C. Fly.io (API only)

```bash
fly launch --dockerfile control-plane/Dockerfile --no-deploy
fly postgres create && fly postgres attach <db>     # sets DATABASE_URL
fly secrets set STRIPE_SECRET_KEY=... STRIPE_WEBHOOK_SECRET=...
fly deploy
```

## Verify a live deploy

```bash
BASE=https://<your-host>
curl $BASE/health
# customer purchase (mock unless a live Stripe key is set):
curl -X POST $BASE/checkout/session -H 'Content-Type: application/json' \
  -d '{"items":[{"name":"Aurora Lamp","amount":4900,"quantity":1}],"customer_email":"a@b.com"}'
# a pricing change is gated — returns queued_for_approval, never executes inline.
# Admin endpoints require the bearer token in production (see "Admin authentication"):
curl -X POST $BASE/store/update-pricing -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -d '{"sku":"AURORA-STD","old_price":49,"new_price":59}'
curl -H "Authorization: Bearer $ADMIN_API_KEY" "$BASE/approvals?status=pending"
curl "$BASE/events?limit=20"
```

## Admin authentication

The approval gate only means something if not everyone can open it. Mutating admin
endpoints — `/approvals/*`, `/store/*`, `/orders/*`, `/inventory/*`, `/payments/refund` —
require an `Authorization: Bearer <key>` credential set via **`ADMIN_API_KEY`**.

- **Unset** → open dev/mock mode (local dev + tests run unchanged).
- **`APP_ENV=production` with no key** → the API **fails closed at startup** and will not
  boot — a production control plane must never be reachable without auth.
- Multiple comma-separated keys are accepted so credentials can be rotated with no downtime.
- Customer checkout, the signature-verified Stripe webhook, and read-only telemetry
  (`/metrics`, `/events`, `/health`) stay open by design. `GET /health` reports
  `"admin_auth": "enabled" | "disabled"` so you can confirm posture after deploy.

## Abuse controls & recovery

- **Rate limits** — checkout, the Stripe webhook, and approval decisions carry per-client-IP
  sliding-window throttles (`RATE_LIMIT_CHECKOUT_PER_MINUTE`, `RATE_LIMIT_WEBHOOK_PER_MINUTE`,
  `RATE_LIMIT_DECISIONS_PER_MINUTE`; `0` disables one). Exceeding a limit returns `429`.
- **Webhook idempotency** — `checkout.session.completed` orders are keyed on the Stripe
  checkout-session id (`orders.external_ref`); redelivered events are logged to the audit
  ledger as `order_paid_duplicate_skipped` instead of double-booking revenue.
- **Readiness** — `GET /ready` runs `SELECT 1` against the database and returns `503` when it
  is unreachable, so orchestrators can hold traffic during a database failover.

## Going from mock to real money

The store runs in **mock mode** with no Stripe key (safe for demos). To take real payments:
0. **Activate the Stripe account first.** Keys are useless while `charges_enabled` is
   false — as of the last check this account has not completed onboarding and has no
   bank account or webhook endpoint. See `STRIPE_SETUP.md` for the verified state, the
   outstanding requirements, and the full go-live checklist.
1. Add `STRIPE_SECRET_KEY` (live or test) → `/checkout/session` creates real Stripe Checkout URLs.
2. Add `STRIPE_WEBHOOK_SECRET` → `/webhooks/stripe` verifies signatures and rejects forgeries.
   Leaving it unset in production means a forged `checkout.session.completed` books a fake order.
3. Register the webhook events listed in `STRIPE_SETUP.md` §5 — `invoice.paid` in particular,
   or subscription renewals settle in Stripe and never reach the ledger.
4. Refunds stay behind the approval gate; approve via `/approvals/{id}/approve` before any money moves.

## Morning sales-ops briefing (email)

`.github/workflows/sales-ops-briefing.yml` runs every morning (≈07:17 ET), builds a factual
briefing from the control-plane database — yesterday + month-to-date revenue, run-rate forecast
movement, new/stalled/at-risk orders, operator activity, and data-quality/approval-gate issues —
then emails it via Gmail SMTP. Build it manually any time with:

```bash
cd control-plane
python -m app.sales_ops_briefing            # markdown to stdout
python -m app.sales_ops_briefing --json     # machine-readable
python -m app.sales_ops_briefing --email    # also email (needs the secrets below)
```

Add these repo **Actions secrets** to send real numbers (without them it runs in safe mode: a
clearly-marked "no live source" briefing, no email, no fabricated figures):

| Secret | Purpose |
|--------|---------|
| `DATABASE_URL` | Control-plane Postgres URL (read-only use by the briefing) |
| `GMAIL_USER` | Sending Gmail address |
| `GMAIL_APP_PASSWORD` | Gmail **App Password** (requires 2FA; not your account password) |
| `BRIEFING_TO` | Recipient(s), comma-separated (defaults to `GMAIL_USER`) |

> Coverage note: the source is commerce/Stripe, **not a deal CRM**. "Deals" map to orders and
> "rep activity" maps to operator/automation ledger activity. For true rep-level pipeline,
> forecast, and stage data, connect a CRM (HubSpot/Salesforce) as the source instead.
