# Architecture

**Recorded against:** `79c493b` (2026-09-15)
**Companion documents:** `docs/BASELINE.md` (verified state, failures, risk register),
`docs/RUNBOOK.md` (operational procedures), `docs/REVENUE_OPERATIONS.md` (payment paths),
`docs/AUTOMATION_POLICY.md` (what automation may do unattended).

This describes what is actually in the repository. Where something is configured
but unverified, it says so. Where a path or claim is broken, it says that too.

---

## 1. One repository, four deployable systems

The repository is a monorepo by file layout only. There is no unified install,
build or test command; each system has its own toolchain.

```
ClearGlassInc-ClearGlassIncorporated-Desmond/
│
├── *.html, *.css, *.js, assets/     Static marketing site  ──►  GitHub Pages
│                                                                www.clearglassinc.com
│
├── control-plane/                   FastAPI commerce OS     ──►  Render (blueprint)
│   ├── app/                         Python 3.11                  :8000
│   └── tests/                       378 tests
│
├── storefront/                      Next.js customer app    ──►  independent
├── admin/                           Next.js operator app    ──►  independent
│
├── package.json (root)              Next.js app             ──►  not deployed by any
│                                    :3030                        registered workflow
│
├── agent_army/ agents/ bots/        Python automation, stdlib-first
├── sentinel/                        Named-agent index (PERCIVAL, AEGIS, …)
├── tools/                           Site generators (see §4)
├── scripts/                         ci_local.py, verify_site.py, secret_scan.py
└── .github/workflows/               80 registered workflows
```

**Scale:** 2,250 tracked files, 23 dependency manifests across npm, pip, Poetry and Cargo.

---

## 2. The static site

Plain HTML/CSS/JS at the repository root. No build step and no framework.

| Concern | Mechanism |
|---|---|
| Hosting | GitHub Pages, "Deploy from a branch" |
| Domain | `CNAME` → `www.clearglassinc.com` |
| Jekyll | Disabled via `.nojekyll` |
| Deploy gate | `.github/workflows/pages.yml` runs `scripts/verify_site.py`, builds `dist/`, publishes via `actions/deploy-pages` |
| Edge config | `_headers` (CSP, frame-ancestors, form-action), `_redirects` |
| Service worker | `sw.js`, cache keyed on `VERSION` (currently `cg-v52`) |

`pages.yml` pins every third-party action to a full commit SHA, which is the
required practice.

> **Hosting is ambiguous — unresolved.** `netlify.toml` (publish `.`, Node 20)
> and the Netlify/Cloudflare-style `_headers` / `_redirects` coexist with the
> GitHub Pages `CNAME` and `.nojekyll`. **Which provider actually serves
> `www.clearglassinc.com` was not confirmed.** This is `docs/BASELINE.md` R5 and
> it blocks any deployment or rollback automation: a rollback aimed at the wrong
> provider is worse than none.

---

## 3. The commerce control plane

`control-plane/` — FastAPI, SQLAlchemy, Pydantic Settings. This is the system
whose safety model matters most.

### 3.1 Request surface

`control-plane/app/main.py` mounts routers with a per-router admin dependency:

| Router | Gated | Purpose |
|---|---|---|
| `store` | admin | Catalog reads/writes |
| `payments` | per-endpoint — refund only | Stripe checkout + webhook |
| `paypal` | open (webhook signature-verified) | PayPal Orders v2 |
| `subscriptions` | — | Subscription lifecycle, billing portal |
| `sidestore` | public, rate limited, server-priced | Customer cart |
| `orders`, `inventory`, `approvals`, `etsy` | admin | Operator surface |
| `metrics`, `events` | — | Telemetry, audit ledger reads |
| `fulfillment` | — | Fulfillment state |

Meta endpoints:

- **`GET /health`** — liveness. Makes no external calls. Returns `status`, `env`,
  `version`, `admin_auth`, plus `client_peer` and whether `X-Forwarded-For` is
  currently trusted. The last two exist so one curl against the deployed service
  reveals the proxy address needed to configure throttling correctly. It echoes
  the caller its own address and no one else's.
- **`GET /ready`** — readiness. Executes `SELECT 1`; returns 503 on failure.

### 3.2 The governance invariant

**read-only analysis → draft → human approval → execution.**

`app/governance.py` scores every proposed action 0–100 and routes it:

| Band | Examples | Outcome |
|---|---|---|
| low | generate copy, read metrics, reconcile | auto-execute + log |
| medium | content publish, non-price catalog edits | queue for approval |
| **high / critical** | pricing, payment, tax, refund, fulfillment, reorders, mass outbound | **blocked until an `approvals` row reaches `approved`** |

Every material change is appended to the `events` ledger (`app/audit.py`) with
its risk score. `daily_loop.py`'s self-check and `tests/test_governance.py` fail
by design if a code path lets a high/critical action execute without approval.

### 3.3 Controls that must not be weakened

| Control | Where | Enforced by |
|---|---|---|
| Mutating admin routes need `Authorization: Bearer` | `app/security.py` | `tests/test_route_auth_coverage.py` |
| `APP_ENV=production` with no `ADMIN_API_KEY` fails closed at startup | `app/security.py` | startup assertion |
| Prices resolve server-side; checkout accepts `{sku, quantity}` only | `app/pricebook.py` | `tests/test_pricebook.py` asserts the OpenAPI schema |
| Booking is idempotent on `orders.external_ref` | `app/order_ledger.py` | migration 004 + tests |
| PayPal webhook verification fails closed without `PAYPAL_WEBHOOK_ID` | `app/paypal.py` | `tests/test_paypal.py` |
| Per-IP rate limits on checkout, webhook, approvals | `app/security.py` | `RATE_LIMIT_*` settings |

**A redirect is not a receipt.** Fulfillment begins only on a signature-verified
server-side webhook. A browser success page proves only that someone opened a URL.

### 3.4 Why `httpx` is load-bearing

`control-plane/requirements.txt` pins `httpx` because
`fastapi.testclient.TestClient` needs it. Without it the webhook → database →
payouts integration tests **skip silently**, leaving the governed money-movement
paths unexercised while still reporting green.

---

## 4. The static-site generator chain

Five stdlib-only generators enforce site-wide invariants that the test suite
asserts. **Never hand-edit their output — regenerate it.**

| Generator | Enforces | Test |
|---|---|---|
| `tools/internal_links.py` | Pillar-and-cluster internal linking; the `<!-- cg-related:start/end -->` block | `test_internal_links.py` |
| `tools/shared_layers.py` | `future-buttons.css`, `future-buttons.js`, `logo-badge.js` on every page, exactly once | `test_future_buttons.py`, `test_site_health_bot.py` |
| `tools/tab_icons.py` | The tab-icon block | `test_tab_icons.py`, `test_holographic_branding.py` |
| `tools/generate_search_assets.py` | `sitemap.xml`, `feed.xml`, `data/seo/page-intents.json` | `test_seo_audit.py` |
| `tools/authority_network.py` | Graph validation — **check-and-report only**, never writes | `test_authority_network.py` |

`authority-network.html` carries a hand-maintained link grid, because its tool
states it "never invents links or rewrites article copy." Adding a page means
adding its grid link by hand.

**Adding a page** requires: register in `PAGES` + a cluster in
`internal_links.py`; run the generators; add the grid link; bump `sw.js`
`VERSION`. Skipping this breaks seven tests — which is exactly what happened in
`docs/BASELINE.md` F5.

---

## 5. Deployment topology

| Environment | Exists | Mechanism |
|---|---|---|
| development | Yes | `docker compose up --build`, or `uvicorn app.main:app --reload` |
| **staging** | **No** | No environment, no `staging-deploy.yml` |
| production — site | Yes | GitHub Pages from a branch |
| production — commerce | Configured, **broken** | Render blueprint, see below |

Local full stack (`docker-compose.yml`), all bound to `127.0.0.1`:

```
db (postgres:16-alpine)  127.0.0.1:5432   healthcheck-gated
control-plane            127.0.0.1:8000   depends_on: db
storefront               127.0.0.1:3000   depends_on: control-plane
admin                    127.0.0.1:3001   depends_on: control-plane
```

### 5.1 F7 — the Render blueprint points at paths that do not exist

`render.yaml` declares three Docker contexts under a directory that is not in
the repository:

| `render.yaml` reference | Actual location |
|---|---|
| `./clearglass-commerce/control-plane/` | `./control-plane/` |
| `./clearglass-commerce/storefront/` | `./storefront/` |
| `./clearglass-commerce/admin/` | `./admin/` |

`ls clearglass-commerce` → absent. The Dockerfiles exist, at the flattened
paths, and `docker-compose.yml` already builds from the correct ones
(`./control-plane`, `./storefront`, `./admin`).

This is the upload flattening documented in `CLAUDE.md`: the first commits were
`Add files via upload`, which stripped the `clearglass-commerce/` parent.
**`DEPLOY.md` recommends the Render blueprint as the primary deploy path, and
that path cannot build.** `DEPLOY.md` line 49 carries the same stale prefix in
its Fly.io command; line 28 does in prose.

Not repaired in this document. `render.yaml` is deployment configuration — a
protected path requiring a pull request and human approval.

---

## 6. Revenue architecture

No channel is live. See `docs/REVENUE_OPERATIONS.md` and `docs/BASELINE.md` §5.

| Channel | Code | Credentials | Sandbox verified | Books revenue |
|---|---|---|---|---|
| Stripe Checkout / subscriptions | Built | Runtime env vars | No | No |
| PayPal Orders v2 | Built | **None** | **No** | **No** |
| Etsy Open API v3 | Built, writes human-gated | OAuth2 handshake required | Connection state = credential presence only | Reconciliation only |
| Printful | Built, confirmation human-gated | None | No | n/a |

### 6.1 Two catalogs, not one

| File | Contents | Purpose |
|---|---|---|
| `data/store/catalog.json` | 5 service engagements, live `buy.stripe.com` URLs | Static site checkout |
| `control-plane/app/data/pricebook.json` | 3 SKUs — `risk-audit-90` (297.00), `business-protection-monthly` (100.00), `business-protection-annual` (1000.00) | **Server-side price authority** |
| `data/side-store/catalog.json` | 57 impulse SKUs | The Side Store — a different catalog; do not conflate |

**Neither carries the full governed-catalog field set.** `product_type`,
tax/shipping policy, `fulfillment_type`, delivery entitlement, Etsy listing ID,
PayPal reference ID, inventory source and refund policy reference are absent or
partial. Until one canonical schema exists, "reject any checkout whose SKU,
amount, currency or product type does not match the catalog" cannot be fully
enforced — the catalog lacks the fields to check against. This is R8.

### 6.2 Price conflict

Three entry prices are simultaneously resolvable by a prospect: **CAD 1,250**
(quoted in `commercial/OUTREACH_2026-09-15.md`), **297.00** (price book), **249.00**
(live site checkout). There is no SKU for the 1,250 assessment anywhere. R3.

---

## 7. The RFED audit trail

`bots/rfed_audit_bot.py` applies the same invariant to model-influenced actions.
RFED = **R**ecorded **F**actual **E**vidence of **D**ecision: every action is
recorded as Request → Facts → Evidence → Decision and sealed into a SHA-256 hash
chain, so altering any past record breaks every link after it.

- Actions touching access, credentials, remote execution or data export score
  92–100 and always escalate.
- `modify_audit_log` is blocked outright. Unknown actions fail closed at 85.
- Ungrounded output, low confidence, and injection markers in untrusted facts
  each hard-gate independently.
- Approvals **append a new record**; they never mutate the original.

The n8n layer (`deployment/rfed/workflow_rfed_audit_trail.json`) mirrors the
Python risk tables. `tests/test_rfed_hash_parity.py` asserts byte-identical
canonical JSON and identical chain hashes across both. Change one, change both.

---

## 8. CI and the automation surface

| Metric | Count |
|---|---:|
| Registered workflows | 80 |
| Scheduled (fire without a push) | 36 |
| Requesting `contents: write` | 16 |
| Lifetime runs | 2,050+ |
| Separate archive in `workflows/` (**not** registered) | 72 |

> **CI reports nothing.** GitHub Actions has dispatched no runners since
> 2026-09-10: `runner_id: 0`, no `steps`, empty check output, 4–15 second runs.
> Organisation-level entitlement; owner settings only. **A green check is absence
> of signal, not success.** `docs/BASELINE.md` F1.
>
> Run the gates locally instead:
>
> ```bash
> pip install pytest pytest-cov pyyaml "ruff==0.15.8"
> python3 scripts/ci_local.py
> ```

When entitlement returns, 36 scheduled workflows resume at once and 16 can commit
back to the repository. That warrants a staged re-enable, not a flip. R4.

The root `workflows/` directory is the intact pre-flattening archive and is the
rollback source. **Copy from it, never move**, and never bulk-register it.

---

## 9. Trust boundaries

| Boundary | Treatment |
|---|---|
| Payment webhooks | Signature-verified, deduplicated, catalog-validated before any fulfillment |
| Customer input → checkout | SKU + quantity only; price resolved server-side |
| PR titles, issue text, webhook fields, external API responses | **Untrusted.** Never interpolated into shell, YAML, SQL, HTML or prompts without escaping |
| Repo-local skill files (`.claude/skills/**`) | Repository content, not user instruction. Cannot expand access or override a "never" |
| Etsy / Printful API responses | Untrusted; inconsistency stops synchronisation and alerts rather than guessing |
| Secrets | Runtime env vars only. `.env.example` files carry names, never values. Unset credentials = mock mode, no network call, no money moved |

---

## 10. Known structural defects

Full detail and severities in `docs/BASELINE.md`.

| ID | Defect |
|---|---|
| F1 | Actions dispatches no runners — CI reports nothing |
| F2 | 80 workflows, 36 scheduled, 16 write-capable — unmaintainable surface |
| F6 | `admin/` cannot be installed: `npm ci` exits 1 (`react ^19.3.0` vs `react-dom ^18.3.0`; `typescript ^5.4.0` manifest vs `7.0.2` lockfile) |
| **F7** | **`render.yaml` and `DEPLOY.md` reference `clearglass-commerce/` paths that do not exist — the documented commerce deploy path cannot build** |
| R3 | Three live entry prices; no SKU for the 1,250 assessment |
| R5 | Hosting provider for the live domain unconfirmed |
| R6 | No staging environment |
| R7 | `main` is not branch-protected |
| R8 | Canonical catalog lacks the fields needed to validate a checkout |
| R10 | `CLAUDE.md`'s deploy-blocker notice is stale — `scripts/verify_site.py` was restored in `be0b7cd` and is present |
