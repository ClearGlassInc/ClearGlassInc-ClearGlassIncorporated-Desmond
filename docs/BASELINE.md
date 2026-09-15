# Production Baseline and Risk Register

**Baseline commit:** `16057ab91afa073c092d5b43ae338fb0f37e9b49`
**Baseline date:** 2026-09-15
**Default branch:** `main`
**Observed by:** read-only discovery pass. No file was modified to produce this report.

This document is the reference point every later automation change is measured
against. It records what is verified, what is broken, and what is unknown. It
does not record intentions.

---

## 1. What this repository is

A single repository holding several independently deployed systems.

| Layer | Path | Stack | Deploys to |
|---|---|---|---|
| Static marketing site | repo root (`*.html`, `*.css`, `*.js`, `assets/`) | Static, no build step | GitHub Pages, `www.clearglassinc.com` |
| Commerce control plane | `control-plane/` | Python 3.11, FastAPI, SQLAlchemy, Pydantic Settings | Render (`render.yaml` blueprint) |
| Storefront | `storefront/` | Next.js | Independent |
| Admin | `admin/` | Next.js | Independent |
| Root Next.js app | `package.json` (`next dev -p 3030`) | Next.js + tsx tests | Not currently deployed by any registered workflow |
| Agent / bot tooling | `agent_army/`, `agents/`, `bots/`, `sentinel/` | Python, stdlib-first; one Rust sidecar | Invoked by workflows |

**Scale:** 2,250 tracked files. 23 dependency manifests across npm, pip, Poetry
and Cargo. This is a monorepo in file layout but not in tooling: there is no
single install, build or test command that covers it.

---

## 2. Build and test commands, with verified results

Run from the repository root unless stated otherwise. Results below were
observed on the baseline commit on 2026-09-15.

| Command | Scope | Result | Duration |
|---|---|---|---|
| `python3 -m pytest tests/ -q` | Root Python suite | **7 failed, 1246 passed, 5 skipped** — see F5 | 12.9s |
| `cd control-plane && python3 -m pytest tests/ -q` | Commerce control plane | **378 passed, 1 skipped** | 3.5s |
| `ruff check .` | Python lint, pinned `ruff==0.15.8` | **pass** | 0.1s |
| `python3 scripts/ci_local.py` | The 10 gates mirrored from `ci.yml` | **6 passed, 3 failed, 1 skipped** — see F5 | ~26s |

The single skip in `ci_local.py` is `lighthouse`, which is network-gated and
re-runs with `--with-network`. The three failures are F5 below, and are present
on `main` itself, not introduced by this document.

For reference, the same commands returned **1253 passed / 5 skipped** and
**9 gates passed / 0 failed** at commit `08d2462`, one commit earlier. The
regression arrived with `16057ab`.

Prerequisites, matching CI's pins:

```bash
pip install pytest pytest-cov pyyaml "ruff==0.15.8"
pip install -r control-plane/requirements.txt   # fastapi, sqlalchemy, stripe, httpx
```

`httpx` is load-bearing, not incidental. `fastapi.testclient.TestClient`
requires it, and without it the webhook to database to payouts integration
tests skip silently, leaving the governed money-movement paths unexercised.

Node build commands exist (`npm ci && npm run build` in `storefront/` and
`admin/`; `npm run typecheck` at root) but were **not executed in this pass**.
Their current status is `NOT VERIFIED`.

---

## 3. Known failures

### F1 — GitHub Actions does not dispatch runners — CRITICAL

**Every registered workflow job fails before executing a step.** This is not a
test failure. It is an infrastructure failure that makes the entire CI/CD
mission non-deliverable until an owner resolves it.

Evidence collected on the baseline commit:

| Signal | Observation |
|---|---|
| Check output | `Lint (ruff)` check run `104360569423` returns `title`, `summary` and `text` all empty |
| Job logs | HTTP 404. Nothing was written |
| Job payload | `runner_id: 0`, `runner_name: ""`, `steps` absent (`PRODUCTION-RECOVERY.md` §1.4) |
| Run duration | 4 to 15 seconds for whole runs. Run `34989436788` at 15:35:11Z to 15:35:15Z |
| Spread | Every recent run on `main` across `ci.yml`, `repository-health.yml`, `defender-watch.yml`, `site-integrity-and-deploy.yml`, `seo-dashboard.yml`, `sync-stripe-products.yml`, `sales-ops-briefing.yml` |
| Duration of outage | First recorded 2026-09-10. Still failing 2026-09-15 |

`PRODUCTION-RECOVERY.md` §1.4 rules out workflow YAML and public-repo minute
quotas as sufficient causes. The remaining explanation is organisation-level
entitlement: a billing hold, an Actions spending limit, an allowed-actions
policy, or the Actions disable toggle. §3.3 lists those as owner-only settings
pages that no repository token can reach.

**Consequence for reporting.** A red check on this repository currently carries
no information, and a green one would carry none either. `CLAUDE.md` states this
directly: *"a green check is absence of signal, not success."*

**Exit condition (Gate 0).** Any user-authored workflow job reporting
`runner_id != 0` with a non-empty `steps` array.

**Consequence already realised.** Pull requests #30 through #51 merged into
`main` with no verified CI signal. That includes #37, which added the governed
PayPal channel, automation circuit breakers and their tests. Those tests have
never run in CI. They pass locally; that is the only reason their state is known
at all.

### F2 — Workflow surface is unmaintainable — HIGH

| Metric | Count |
|---|---:|
| Registered workflows in `.github/workflows/` | 80 |
| Scheduled workflows, firing without any push | 36 |
| Workflows requesting `contents: write` | 16 |
| Lifetime workflow runs | 2,050 |

Eighty workflows means a single push produces roughly eighty check results. At
present all of them are red, so the signal-to-noise ratio is zero. When
entitlement returns, 36 scheduled workflows will begin firing on their own
timers and 16 of them can commit back to the repository. That is a large
uncontrolled surface to re-energise in one step.

`PRODUCTION-RECOVERY.md` §1.5 already warns against bulk-registering the
separate 72-file `workflows/` archive for exactly this reason. The same caution
applies in reverse to what is already registered.

### F3 — Deploy gate depends on a script the workflows expect — resolved, verify

`CLAUDE.md` carries a standing deploy-blocker notice stating
`scripts/verify_site.py` is missing and that GitHub Pages must therefore stay on
"Deploy from a branch". Commit `be0b7cd` ("fix: restore missing
scripts/verify_site.py deploy gate") restored it. The file is present on the
baseline commit.

**`CLAUDE.md` has not been updated** and still instructs agents that the script
is absent. That is a documentation defect, not a code defect, but it is the kind
that causes an avoidable production mistake. Classified LOW risk, in scope for a
later documentation PR.

### F5 — `main` is currently red: an unregistered page broke seven tests — HIGH

**This is a live regression on the default branch, introduced today, and it is
the clearest available demonstration of what F1 costs.**

Commit `16057ab` ("Add 15 Sep 2026 strategic chokepoint open-source sitrep")
changed exactly one file:

```
blog/2026-09-15-strategic-chokepoint-sitrep.html | 41 ++++++++++++++++++++++++
1 file changed, 41 insertions(+)
```

A new indexable HTML page was added and registered nowhere. `CLAUDE.md` states
the required procedure: add the page to `PAGES` and a cluster in
`tools/internal_links.py`, run `python3 tools/internal_links.py`, and add the
URL to `sitemap.xml`. None of that was done.

Seven tests fail as a result:

| Test | Assertion |
|---|---|
| `test_authority_network.py::test_every_indexable_sitemap_page_is_registered` | page not registered |
| `test_future_buttons.py::test_every_deployable_page_loads_enhancement_once` | enhancement script missing |
| `test_holographic_branding.py::test_every_public_html_page_declares_a_tab_icon` | no tab icon |
| `test_internal_links.py::test_every_html_page_is_mapped_or_explicitly_excluded` | `discovered != mapped \| excluded` |
| `test_seo_audit.py::TestLiveSite::test_every_indexable_page_is_in_the_sitemap` | absent from `sitemap.xml` |
| `test_site_health_bot.py::TestLogoCoverage::test_every_shipped_page_has_logo` | no logo |
| `test_tab_icons.py::test_every_page_in_the_repo_is_complete` | incomplete |

Three `ci_local.py` gates fail with it: `python-tests`, `search-integrity`
(generated search assets are current), `search-integrity` (generated internal
links).

**Why it reached `main`.** The repository's own test suite catches this exact
mistake, which is what those tests are for. CI never ran them, because of F1.
The page shipped to the default branch of a live site with no internal links, no
sitemap entry, no tab icon and no logo.

This is R2 stated as a fact rather than a hypothetical: merging without CI has
now produced a real defect on `main`. Repair is tracked separately from this
baseline and is a small, well-specified change.

**Side observation, refined after testing both states.** The
`search-integrity` gate compares generator output against **what is committed**,
and writes the regenerated output into the working tree. The consequence is
conditional:

- Generated assets already current: the gate passes and `git status` stays
  clean. Verified.
- Generated assets stale: the gate fails *and* leaves
  `data/seo/page-intents.json`, `feed.xml` and `sitemap.xml` modified in the
  working tree. Verified on `main` at `16057ab`.

So the tree is mutated exactly when the operator is most likely to be confused
by it — during a failing run, where a subsequent `git add -A` would silently
stage generated output the operator never reviewed. The gate is doing real work
and the failure message is clear ("Re-run `tools/generate_search_assets.py` and
commit the result"), so this is a usability sharp edge, not a defect.
Classified LOW: either make the check write to a temp tree, or have it state
that it has modified the working tree.

### F4 — Node build status largely unknown — MEDIUM

Node builds were not executed for the root app, `storefront/` or
`apps/artemis-engineering`. Their status is `NOT VERIFIED`, not "passing".

`admin/` was executed, and it is broken. See F6.

### F6 — `admin/` cannot be installed: `npm ci` exits 1 — HIGH

`Commerce Frontend CI` runs `npm ci && next build` for `storefront` and `admin`.
On `main`, the first command fails for `admin`, so the app cannot be installed,
cannot be built, and cannot be deployed.

Reproduced on `origin/main`:

```
cd admin && npm ci
npm error code ERESOLVE
npm error While resolving: react-dom@18.3.1
npm error Found: react@19.3.0
npm error Could not resolve dependency:
npm error peer react@"^18.3.1" from react-dom@18.3.1
exit code: 1
```

**Root cause — React major mismatch.** `admin/package.json` declares
`react: ^19.3.0` alongside `react-dom: ^18.3.0`. React and ReactDOM must share
a major version. `react-dom@18.3.1` declares a peer of `react@^18.3.1`, which
`react@19.3.0` cannot satisfy.

**Second defect, latent behind the first.** `admin/package.json` declares
`typescript: ^5.4.0`, which resolves to `>=5.4.0 <6.0.0`. `admin/package-lock.json`
pins `node_modules/typescript` to **7.0.2**, which is outside that range. `npm ci`
validates the lockfile against the manifest, so this would fail on its own even
once the React conflict is resolved. This arrived with PR #50,
"deps(admin): bump typescript from 5.9.3 to 7.0.2 in /admin", merged
2026-09-15 with no CI verification.

**Scope — `admin/` only.** Verified consistent elsewhere:

| Project | react | react-dom | Consistent |
|---|---|---|---|
| `admin/` | `^19.3.0` | `^18.3.0` | **No** |
| `storefront/` | `^18.3.0` | `^18.3.0` | Yes |
| repo root | `19.1.1` | `19.1.1` | Yes |
| `apps/artemis-engineering` | `19.1.1` | `19.1.1` | Yes |

**Not repaired here, and deliberately so.** `package.json` and lockfiles are
protected paths requiring a pull request and human approval. The React fix is
also a genuine product decision rather than a mechanical correction: Next 16
accepts `^18.2.0 || ^19.0.0`, so `admin/` can move either way, and the codebase
currently contains both choices — `storefront/` on React 18, root and
`apps/artemis-engineering` on React 19. Picking one silently would align
`admin/` with a major version nobody chose for it. The same question applies to
whether TypeScript 7 was intended at all.

This is the second confirmed defect on `main` traceable to F1, after F5.

---

## 4. Deployment path

| Environment | Exists | Mechanism | Verified |
|---|---|---|---|
| development | Partial | Local `uvicorn`, `docker compose up --build` | Not this pass |
| staging | **No** | No staging environment, no `staging-deploy.yml` | n/a |
| production (site) | Yes | GitHub Pages, "Deploy from a branch", `CNAME` = `www.clearglassinc.com` | Live site not probed this pass |
| production (control plane) | Configured | `render.yaml` blueprint, optional Render deploy hook in `commerce-deploy.yml` | Not verified |

Also present: `netlify.toml` (publish `.`, Node 20) and `_headers` / `_redirects`
(Netlify/Cloudflare-style edge config) alongside the GitHub Pages `CNAME` and
`.nojekyll`. **Multiple hosting configurations coexist in one repository.** Which
one actually serves `www.clearglassinc.com` was not confirmed in this pass and is
recorded as `UNKNOWN`. Resolving that ambiguity is a prerequisite to any
deployment or rollback automation, because a rollback aimed at the wrong
provider is worse than none.

There is `.github/workflows/rollback.yml` but no `production-deploy.yml` and no
`staging-deploy.yml`.

---

## 5. Revenue-flow state

No channel is live. This restates `docs/REVENUE_OPERATIONS.md` and adds the
account-side observation.

| Channel | Code | Credentials | Sandbox verified | Production verified | Books revenue |
|---|---|---|---|---|---|
| Stripe Checkout | Built | Runtime env vars | No | No | No |
| Stripe subscriptions | Built | Runtime env vars | No | No | No |
| PayPal Orders v2 | Built | **None configured** | **No** | **No** | **No** |
| Etsy Open API v3 | Built, writes human-gated | OAuth2 handshake required | Connection state is credential presence only | No | Reconciliation only |
| Printful | Built, confirmation human-gated | None configured | No | No | n/a |

**Catalog conflict — HIGH.** Three different entry prices are simultaneously
resolvable by a prospect:

| Source | SKU / offer | Price |
|---|---|---|
| `data/store/catalog.json` | `quick-audit`, live Stripe checkout URL | CAD 249.00 |
| `control-plane/app/data/pricebook.json` | `risk-audit-90` | CAD 297.00 |
| `commercial/OUTREACH_2026-09-15.md` | AI Operations & Exposure Assessment | CAD 1,250.00 |

The price book contains exactly three SKUs: `risk-audit-90` (297.00),
`business-protection-monthly` (100.00/mo), `business-protection-annual`
(1,000.00/yr). **There is no SKU for the CAD 1,250 assessment.** The offer the
commercial documents direct the business to sell is not purchasable through any
configured path.

Separately, `data/store/catalog.json` carries five entries marked
`live_checkout: true` with `buy.stripe.com` URLs. Whether any has ever taken a
payment is `UNKNOWN`: no Stripe read source is connected to this session.

**Account-side observation (PayPal, business account, read 2026-09-15):** 39
transactions between 2026-09-01 and 2026-09-15, of which 4 successful records
covering 2 outbound subscription payments and 35 denied charge attempts.
**Zero inbound customer receipts. Zero outstanding invoices.** This is an
observation about the business account, and is independent of the control
plane's PayPal integration being credential-empty. Neither fact is evidence for
the other.

**Canonical catalog schema gap.** Neither catalog file carries the full field
set a governed catalog requires: `product_type`, tax/shipping policy,
`fulfillment_type`, delivery entitlement, Etsy listing ID, PayPal reference ID,
inventory source, or refund policy reference are absent or partial. Until that
schema exists in one canonical place, "reject any checkout whose SKU, amount,
currency or product type does not match the catalog" cannot be fully enforced,
because the catalog does not carry the fields to check against.

What **is** already enforced in code, and must not be weakened:

- Prices resolve server-side. `POST /checkout/session` and `POST /paypal/order`
  accept SKUs and quantities only. `tests/test_pricebook.py` asserts the
  `CheckoutLineItem` OpenAPI schema is exactly `{sku, quantity}`.
- Booking is idempotent through `control-plane/app/order_ledger.py`, keyed on
  `orders.external_ref`.
- A redirect is not a receipt. Fulfillment starts only on a signature-verified
  server-side webhook.
- PayPal webhook verification fails closed without `PAYPAL_WEBHOOK_ID`.
- Mutating admin routes require `require_admin`; `APP_ENV=production` with no
  `ADMIN_API_KEY` fails closed at startup.
- `control-plane/tests/test_route_auth_coverage.py` asserts every mutating route
  is gated or on a justified allow-list.

---

## 6. Risk register

| ID | Risk | Severity | Evidence | Owner action required |
|---|---|---|---|---|
| R1 | Actions dispatches no runners; no CI signal exists | CRITICAL | F1 | Yes — org billing / Actions policy |
| R2 | 22 PRs merged to `main` with zero verified CI | HIGH | F1, PR #30–#51 | No — mitigated by `scripts/ci_local.py` |
| R2a | **`main` is red now.** Unregistered page broke 7 tests | HIGH | F5 | No — small repair PR |
| R3 | Three live entry prices; assessment has no SKU | HIGH | §5 | Yes — pricing decision |
| R4 | 36 scheduled workflows, 16 with `contents: write`, all dormant and all will resume at once | HIGH | F2 | Yes — staged re-enable |
| R5 | Hosting ambiguity: Pages, Netlify and edge configs coexist | HIGH | §4 | Yes — confirm the serving provider |
| R6 | No staging environment | HIGH | §4 | Yes — provision |
| R7 | `main` is not branch-protected | HIGH | `PRODUCTION-RECOVERY.md` §1.1 | Yes — repo settings |
| R8 | Canonical catalog lacks the fields needed to validate a checkout | MEDIUM | §5 | No — schema work |
| R9 | Node build/typecheck unverified for root, storefront, artemis | MEDIUM | F4 | No |
| R9a | **`admin/` cannot be installed.** `npm ci` exits 1; app is undeployable | HIGH | F6 | Yes — React major decision |
| R10 | `CLAUDE.md` deploy-blocker notice is stale | LOW | F3 | No |
| R12 | `search-integrity` gate leaves generated files dirty when they are stale | LOW | F5 side observation | No |
| R11 | No Stripe read source connected, so cash reporting cannot be completed | HIGH | §5 | Yes — connect or export |

---

## 7. Missing credentials and configuration

Every name below is a variable name only. No value is recorded anywhere in this
repository, and none should be.

**Already documented** in `control-plane/.env.example`, which is complete and
names-only: `APP_ENV`, `ADMIN_API_KEY`, `DATABASE_URL`, `CORS_ALLOW_ORIGINS`,
the `RATE_LIMIT_*` and `TRUSTED_PROXY_*` group, `STRIPE_SECRET_KEY`,
`STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY`, `PAYPAL_CLIENT_ID`,
`PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, `PAYPAL_API_BASE`, the `ETSY_*`
group, the `PRINTFUL_*` group, the masked `PAYOUT_*` group, `ESCALATION_EMAIL`,
`SLACK_WEBHOOK_URL`.

**Not set anywhere, and each blocks a specific capability:**

| Variable | Blocks | Set where |
|---|---|---|
| `PAYPAL_WEBHOOK_ID` | All PayPal webhook verification; every notification is refused | Render environment group |
| `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` | PayPal order creation; integration stays in mock mode | Render environment group |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Server-side Stripe checkout and webhook booking | Render environment group |
| `ETSY_KEYSTRING` / `ETSY_SHARED_SECRET` / `ETSY_ACCESS_TOKEN` / `ETSY_REFRESH_TOKEN` | Etsy reconciliation. Obtained via `python -m app.etsy_connect` | Render environment group |
| `ADMIN_API_KEY` | Production startup. The app fails closed without it | Render environment group |

The root `.env.example` covers only the `LIVE_FABRIC_*` group plus
`DATABASE_URL`, `REDIS_URL` and `OTEL_EXPORTER_OTLP_ENDPOINT`. It does not
describe the commerce surface. That is correct separation, not a defect, but a
reader who opens only the root file will not see the payment variables.

---

## 8. Unresolved operating parameters

The following were requested as configuration but never supplied. They are
recorded as open, not guessed. Fabricating any of them would put an invented
merchant or fulfillment detail into a governed system.

| Parameter | Status | Note |
|---|---|---|
| Production URL(s) | **Derived** | `www.clearglassinc.com`, from `CNAME` and `sitemap.xml` |
| Hosting platform | **AMBIGUOUS** | Pages, Netlify and edge configs all present. Must be confirmed by the owner |
| Runtimes | **Derived** | Python 3.11, Node 20, static HTML |
| Default branch | **Derived** | `main` |
| Etsy shop name/ID | **OPEN** | `ETSY_SHOP_ID` / `ETSY_SHOP_NAME` unset. A profile URL default exists in config but is not a confirmed shop identity |
| Stripe account | **OPEN** | Live `buy.stripe.com` URLs exist in the catalog; the owning account is not recorded here |
| PayPal merchant account | **OPEN** | No merchant identity configured |
| Approved product catalog location | **CONTESTED** | Two files disagree. See §5 |
| Digital fulfillment source | **OPEN** | No object storage, signed-link service or license/entitlement service is configured |
| Physical fulfillment provider | **PARTIAL** | Printful code exists, credential-empty |
| Alert recipient | **PARTIAL** | `ESCALATION_EMAIL` defaults to `info@clearglassinc.com` in config; unset in practice |

---

## 9. Required-deliverable gap analysis

Most of the requested deliverables already exist. This is a gap list, not a
rebuild list. Nothing in the "present" column should be overwritten.

| Deliverable | State |
|---|---|
| `.github/workflows/ci.yml` | PRESENT |
| `.github/workflows/maintenance-review.yml` | PRESENT |
| `.github/workflows/rollback.yml` | PRESENT |
| `.github/workflows/staging-deploy.yml` | **ABSENT** — blocked on R1 and R6 |
| `.github/workflows/production-deploy.yml` | **ABSENT** — blocked on R1 and R5 |
| `.github/dependabot.yml` | PRESENT, 88 lines |
| `CODEOWNERS` | PRESENT at repo root, 49 lines |
| `.env.example` | PRESENT at root and in `control-plane/`, names only |
| `docs/AUTOMATION_POLICY.md` | PRESENT |
| `docs/REVENUE_OPERATIONS.md` | PRESENT |
| `docs/INCIDENT_RESPONSE.md` | PRESENT |
| `docs/AUTOMATION_CHANGELOG.md` | PRESENT |
| `OPERATIONS_HANDOFF.md` | PRESENT at repo root, 195 lines |
| `docs/BASELINE.md` | **THIS FILE** |
| `docs/ARCHITECTURE.md` | **ABSENT** |
| `docs/RUNBOOK.md` | **ABSENT** |
| `docs/CHANGELOG.md` | **ABSENT** |
| Payment webhook signature / idempotency tests | PRESENT — `control-plane/tests/test_paypal.py`, `test_fulfillment.py`, `test_pricebook.py`, `test_route_auth_coverage.py` |

---

## 10. Non-production test plan

Every step below runs locally or against a sandbox. **No step touches
production, moves money, contacts a customer, or changes a live price.**

**Stage 1 — offline gates, no credentials, no network.**

```bash
pip install pytest pytest-cov pyyaml "ruff==0.15.8"
pip install -r control-plane/requirements.txt
python3 scripts/ci_local.py                       # expect 9 passed, 1 skipped
python3 -m pytest tests/ -q                       # expect 1253 passed, 5 skipped
cd control-plane && python3 -m pytest tests/ -q   # expect 378 passed, 1 skipped
python3 -m bots.rfed_audit_bot --self-check
cd control-plane && python -m app.daily_loop --json
```

**Stage 2 — Node, currently unverified.**

```bash
npm ci && npm run typecheck                       # root
cd storefront && npm ci && npm run build
cd admin && npm ci && npm run build
```

Record the result. Do not assume it passes.

**Stage 3 — local full stack, mock mode, no credentials.**

```bash
docker compose up --build    # postgres + control-plane :8000 + storefront :3000 + admin :3001
curl -fsS localhost:8000/ready
```

With no Stripe or PayPal credentials the payment paths run in mock mode: no
order is created at any processor and no money moves.

**Stage 4 — payment webhook behaviour, fixtures only.**

Exercise the existing suites. They must continue to demonstrate: signature
verification fails closed on a missing or bad signature; a redelivered event is
a no-op via `orders.external_ref`; `CHECKOUT.ORDER.APPROVED` and
`PAYMENT.CAPTURE.PENDING` do not book revenue; a denied capture books `failed`.

**Stage 5 — sandbox, owner-gated.**

PayPal sandbox end-to-end and Stripe test-mode checkout. **Requires credentials
the owner must supply through the hosting platform's secret manager.** Not
startable from this repository. Until Stage 5 and a subsequent production
verification are both recorded, no integration may be described as live.

---

## 11. Status

**BLOCKED** on R1 (GitHub Actions entitlement), which is an owner action in
organisation settings and cannot be resolved from this repository.

The CI/CD, staging, production-deploy, rollback-verification and scheduled
self-improvement portions of the automation mission are gated behind Gate 0.
Building new workflow files before Gate 0 clears would add unverifiable YAML to
a repository that already has 80 workflows producing no signal.

Work that remains available and unblocked, in priority order:

1. **Repair F5.** `main` is red right now. Register
   `blog/2026-09-15-strategic-chokepoint-sitrep.html` per the documented
   procedure and regenerate. Small, reversible, fully verifiable locally.
2. Documentation: `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`,
   `docs/CHANGELOG.md`.
3. Canonical catalog schema (R8).
4. Stale `CLAUDE.md` deploy-blocker notice (R10).
5. Repair `admin/` (R9a/F6). Needs an owner decision on which React major
   `admin/` targets, then a protected-path PR for the manifest and lockfile.
6. Verify the remaining Node builds (R9).
7. Make the `search-integrity` gate write to a temp tree, or have it state that
   it modified the working tree (R12).

Each is a separate small PR. None of them requires Gate 0.
