# CLAUDE.md

Guidance for agents working in this repository.

## What this repo is

`ClearGlassInc.github.io` is the ClearGlass Inc. GitHub Pages site **plus** the
source for several backend systems that ship from the same monorepo. The root is
a large static marketing/product site (many top-level `*.html` pages, shared
`*.css`/`*.js`, `assets/`, `sitemap.xml`). Backend systems live in their own
subtrees and deploy independently.

The flagship backend is the **Autonomous E‑Commerce Operator** in
`clearglass-commerce/` — a *governed* commerce engine. Treat its safety model
(below) as non‑negotiable when changing it.

## Map of the repo

| Path | What it is |
|------|-----------|
| `*.html`, `*.css`, `*.js` (root) | Static GitHub Pages site (product/landing pages, shared UI) |
| `clearglass-commerce/` | **Active** governed e‑commerce OS: FastAPI control plane + Next.js storefront/admin + agent prompts |
| `apps/autostore/` | Earlier/parallel control plane + cockpit. Appears superseded by `clearglass-commerce/` — confirm before extending it |
| `agents/` | Per‑agent definitions (`agent.json`, `system_prompt.md`, tool schemas) |
| `bots/` | Standalone Python automation bots invoked by workflows (e.g. `store_smoke_bot.py`) |
| `deployment/` | Per-product deployment layers: n8n workflow exports, ledger SQL, runbooks (`cashpulse/`, `rfed/`) |
| `data/` | Committed JSON feeds: `data/store/catalog.json`, `data/control-surface/*` |
| `operations/` | Generated reports + handoff pages (priority matrix, SEO, health, defender) |
| `sentinel/` | Named-agent index (PERCIVAL, SENTINEL, AEGIS, PFAS, Agent Mesh) — keyless, stdlib-only, fail-closed Python agents; see `sentinel/PERCIVAL_AGENTS.md`. Includes the real PERCIVAL governor/identity/capability/mission-memory stack plus target-state v9 distributed-architecture docs (nothing in those docs is provisioned — see their own status banners) |
| `.github/workflows/` | ~29 workflows: CI, Pages deploy, commerce gates, scheduled bot loops |

## The commerce OS safety model (read before touching `clearglass-commerce/`)

Core invariant: **read‑only analysis → draft → human approval → execution.**
`control-plane/app/governance.py` scores every proposed action 0–100 and routes it:

- **low** (generate copy, read metrics, reconcile) → auto‑execute + log
- **medium** (content publish, non‑price catalog edits) → queue approval
- **high / critical** (pricing, payment/tax/refund/fulfillment, reorders, mass
  outbound) → **blocked until an `approvals` row reaches `approved`**

Every material change is written to an append‑only audit ledger (`events` table,
`app/audit.py`) with a risk score. Do not add a code path that lets a
high/critical action execute without an approval — `daily_loop.py`'s governance
self‑check (and `tests/test_governance.py`) will fail if you do, by design.

Operating rules also enforced in code/prompt: never fabricate inventory, reviews,
sales, or urgency; never change live pricing/tax/payment/refund/fulfillment
without approval; log every action.

The gate is also access-controlled: mutating admin endpoints (approvals, pricing,
refunds, catalog/order/inventory writes) require an `Authorization: Bearer <key>`
credential (`ADMIN_API_KEY`, see `app/security.py`). Unset = open dev/mock mode;
`APP_ENV=production` with no key **fails closed at startup**. Customer checkout, the
signature-verified Stripe webhook, and read-only telemetry stay open. Don't add a
mutating admin route without gating it behind `require_admin`.

Prices are resolved server-side. `POST /checkout/session` takes **SKUs and quantities
only**; amounts come from the price book (`app/pricebook.py`, `app/data/pricebook.json`)
and never from the request body, because a checkout line item's `amount` goes straight
into Stripe's `unit_amount`. `tests/test_pricebook.py` enforces this, down to asserting
the `CheckoutLineItem` OpenAPI schema has exactly `{sku, quantity}` — don't add a
price-shaped field back to that contract. Stripe account/go-live state is documented in
`clearglass-commerce/STRIPE_SETUP.md`.

Abuse/resilience controls (also in `app/security.py`): checkout, the Stripe webhook,
and approval decisions carry per-IP rate limits (`RATE_LIMIT_*_PER_MINUTE`), and the
webhook is idempotent on redelivery via `orders.external_ref` (migration 004).
`GET /ready` reports database reachability. Don't weaken these when editing routers.

## Running & testing the commerce control plane

```bash
cd clearglass-commerce/control-plane
pip install -r requirements.txt        # fastapi, sqlalchemy, stripe, httpx (TestClient), …
ruff check .                           # lint (must pass)
python -m pytest tests/ -q             # full suite; payout/resilience tests need the full web stack (httpx)
uvicorn app.main:app --reload          # http://localhost:8000/docs
python -m app.daily_loop --json        # governance self-check + executive report (stdlib only)
python -m app.etsy_connect --status    # Etsy connection state; omit --status for the OAuth flow
```

Connecting the Etsy shop is a human OAuth2 (PKCE) step — `app/etsy_oauth.py` +
`python -m app.etsy_connect`, documented in `clearglass-commerce/ETSY_CONNECT.md`. The
CLI prints tokens for a runtime secret store and never persists one. Connection state is
credential presence only; `POST /etsy/verify` is a read-only identity/permission check.
Connecting unlocks nothing on its own: every Etsy write is in `ALWAYS_ESCALATE`.

Note: `requirements.txt` pins `httpx` because `fastapi.testclient.TestClient`
needs it. Without it the webhook → DB → `/payouts` integration tests **silently
skip** (or error at collection on envs that have fastapi but not httpx) — so the
governed money‑movement paths would go unexercised. The `Commerce Deploy`
workflow installs `requirements.txt` for the same reason.

Storefront / admin (Next.js, deploy independently):

```bash
cd clearglass-commerce/storefront   # or admin
npm ci && npm run build             # Commerce Frontend CI runs tsc --noEmit + next build
```

Full stack via Docker: `cd clearglass-commerce && docker compose up --build`
(postgres + control‑plane :8000 + storefront :3000 + admin :3001). Deploy paths
are documented in `clearglass-commerce/DEPLOY.md` (Render blueprint recommended).

## CI gates that must stay green

- **Commerce Deploy** (`commerce-deploy.yml`): `ruff` + full pytest on
  `clearglass-commerce/**`, then optional Render deploy hook.
- **Commerce Frontend CI** (`commerce-frontend-ci.yml`): `tsc --noEmit` +
  `next build` for storefront and admin.
- **Commerce Daily Loop** (`commerce-daily-loop.yml`): storefront smoke test +
  governance self‑check + executive report + RFED governance self‑check
  (scheduled 13:00 UTC).
- **CI** (`ci.yml`): root `pytest tests/`, which covers the RFED core and the
  Python↔n8n hash-parity gate.

Two access-control gates are enforced by test rather than convention, because
convention is what fails silently:
`clearglass-commerce/control-plane/tests/test_route_auth_coverage.py` asserts
every mutating route is behind `require_admin` or on a justified allow-list, and
`tests/test_rfed_hash_parity.py` pins the two RFED implementations together. See
`security/RMM_AUTH_BYPASS_HARDENING.md` for why.

## Internal linking system (static site)

Every indexable page carries a generated "Continue exploring" block (marked
`<!-- cg-related:start/end -->`) that implements the site's pillar-and-cluster
internal linking: breadcrumb → topic pillar, rotated sibling links, curated
cross-cluster bridges, and a per-cluster CTA path. The site graph and generator
live in `tools/internal_links.py` (stdlib only).

- **Adding/renaming a page?** Add it to `PAGES` and a cluster in
  `tools/internal_links.py`, then run `python3 tools/internal_links.py`
  (idempotent; `--check` verifies freshness). Add the URL to `sitemap.xml`.
- Don't hand-edit the generated blocks — regenerate them.
- Full-viewport HUD pages (`body{overflow:hidden}`) are listed in
  `FIXED_VIEWPORT` and get a fixed corner chip instead of a footer block.
- When many pages change, bump `VERSION` in `sw.js` so returning visitors'
  service-worker caches refresh.

## The RFED™ audit trail (agentic workflows)

`bots/rfed_audit_bot.py` is the governed audit trail for agentic automation —
the same safety model as the commerce OS, applied to actions a model influences.
RFED = **R**ecorded **F**actual **E**vidence of **D**ecision: every action is
recorded as Request → Facts → Evidence → Decision and sealed into a SHA-256 hash
chain, so altering any past record breaks every link after it.

```bash
python -m bots.rfed_audit_bot --self-check          # governance invariants (stdlib only)
python -m bots.rfed_audit_bot --verify ledger.jsonl # replay a ledger's hash chain
python -m bots.rfed_audit_bot --summary ledger.jsonl
```

Same invariant as commerce: **read-only analysis → draft → human approval →
execution.** Actions touching access, credentials, remote execution, or data
export score 92–100 and always escalate; `modify_audit_log` is blocked outright;
unknown actions fail closed at 85. Ungrounded output (no citations), low
confidence, and injection markers in untrusted facts each hard-gate on their own.

- The n8n layer (`deployment/rfed/workflow_rfed_audit_trail.json`) **mirrors** the
  Python risk tables. Change one, change both, then run
  `tests/test_rfed_hash_parity.py` — it asserts byte-identical canonical JSON and
  identical chain hashes across the two implementations.
- Approvals **append a new record**; they never mutate the original.
- Bump `POLICY_VERSION` when the risk table or gating logic changes.
- Spec: `docs/rfed_audit_trail_spec.md`. Deploy runbook: `deployment/rfed/README.md`.

## Conventions

- Match the style of surrounding code; the commerce control plane is typed
  Python with stdlib‑only modules where noted (`governance.py`, `daily_loop.py`,
  parts of `payments.py`) so they run in minimal CI environments — keep them that
  way unless you also update the relevant gate.
- Don't commit secrets. Stripe keys are runtime env vars; the store runs in safe
  **mock mode** with no key.
- Static site changes deploy via GitHub Pages; keep `.nojekyll` and existing
  redirect/header files intact.
