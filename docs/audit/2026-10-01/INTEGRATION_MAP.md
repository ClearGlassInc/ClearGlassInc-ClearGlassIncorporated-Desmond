# Integration Map — 2026-10-01

Every external service the repository talks to, where the call lives, what
credential it needs, and whether anything can reach it today.

Two facts decide most of the "reachable" column:

- **F1 (VERIFIED today):** GitHub Actions dispatches no runners. No workflow
  integration can execute, whatever its secrets are.
- **Commerce stack not deployed** (VERIFIED 2026-09-24 on Render, not
  re-verified today): no control-plane integration runs in production. Locally
  and in tests every payment integration runs in **mock mode** without keys.

Secret *values* are never read. Whether a GitHub secret is set cannot be read
with this session's access: **UNKNOWN** throughout.

## Commerce control plane (`control-plane/app/`)

| Service | Module / route | Credential (env var) | Direction | Safety controls in code | Reachable today |
|---|---|---|---|---|---|
| Stripe Checkout, subscriptions, webhooks | `payments.py`, `routers/payments.py`, `routers/subscriptions.py` | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | out + signed webhook in | SKU-only checkout (`test_pricebook.py` pins `{sku, quantity}`); webhook signature + idempotency on `orders.external_ref`; per-IP rate limits | No (not deployed) |
| PayPal Orders v2 | `paypal.py`, `routers/paypal.py` | `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID` | out + verified webhook in | Webhook verification fails closed without `PAYPAL_WEBHOOK_ID`; capture is two-phase `claim_approval` | No |
| Etsy Open API v3 | `etsy.py`, `etsy_oauth.py`, `etsy_connect.py` | `ETSY_*` | out | OAuth2 PKCE by a human; every write in `ALWAYS_ESCALATE` | No |
| Printful | `printful.py`, `fulfillment.py` | `PRINTFUL_API_KEY`, `PRINTFUL_WEBHOOK_SECRET` | out + webhook in | Confirmation is approval-gated | No |
| Slack (revenue channel) | `revenue_notify.py` | `SLACK_WEBHOOK_URL` | out | Posted after commit from ledger rows; no PII; test money labelled | No |
| Anthropic (Sentinel `/sentinel/ask`) | `sentinel_ai.py`, `routers/sentinel.py` | `ANTHROPIC_API_KEY`, `SENTINEL_AI_ENABLED` | out | Off by default | No |
| Postgres | `db.py`, `migrate.py` | `DATABASE_URL` | — | Migration runner behind `RUN_MIGRATIONS`; `events` append-only trigger | Locally yes (verified on PG 16.14) |

## Static site (browser → third parties)

| Service | Where | Reachable today |
|---|---|---|
| Control plane API | `revenue-command.html` reads the `cg-revenue-api` meta tag | No: the tag was empty on 2026-09-24 and the API is not deployed, so the lead form records nothing |
| Stripe Payment Links | `data/store/catalog.json`: 5 `buy.stripe.com` URLs | Links exist; whether they take payment is **UNKNOWN** (no Stripe read in this pass) |
| IESO public data | `GridShield-Ontario*`, fed by `ieso-public-feed.yml` | Feed workflow inert (F1); page shows committed data |
| Web Speech API | `station-chat.js` (Sentinel Core voice) | Browser-local, opt-in |

## Workflow integrations (all inert while F1 holds)

| Service | Secret(s) | Workflow(s) | Writes to the service? | Gate |
|---|---|---|---|---|
| Stripe (test) | `STRIPE_SECRET_KEY` | `sync-stripe-products` | only on dispatch with `apply` | rejects non-test keys |
| Stripe (**live**) | `STRIPE_LIVE_SECRET_KEY` | `sync-stripe-products` | only `apply-live-mode` | dispatch + `ALLOW_STRIPE_LIVE_SYNC` + `stripe-live` environment + plan hash. The **plan** job reads the live key with no environment (S-N5) |
| Render | `RENDER_DEPLOY_HOOK_URL`, `RENDER_ROLLBACK_HOOK_URL`, `RENDER_DEPLOY_HOOK` | `commerce-deploy`, `auto-store`, `rollback` | deploy / rollback | skipped when unset; `auto-store` uses `production` environment |
| Cloudflare | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_EDGE_PLAN_TOKEN`, `CLOUDFLARE_EDGE_APPLY_TOKEN` | `ai-proxy-deploy`, `edge-security`, `cloudflare-email-routing*` | Worker deploy, edge config | edge apply: dispatch-only, `edge-<env>` environment |
| Google Search Console, Bing | `GSC_*`, `BING_*` | `seo-dashboard` | no (read) | — |
| IndexNow | `INDEXNOW_KEY` | `indexnow` | ping | — |
| Gmail SMTP | `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `BRIEFING_TO` | `sales-ops-briefing` | sends mail | scheduled daily |
| Discord / Slack alerts | `DEFENDER_*_WEBHOOK_URL` | `defender-watch` | posts | — |
| OpenAI | `OPENAI_API_KEY` | `ai-proxy-deploy`, `codex-autofix` | — | `codex-autofix` dispatch-only |
| Anthropic / Claude Code | `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN` | `agent` | can commit (`contents: write`) | dispatch-only |
| Other GitHub repos | `CG_ORG_PAT` | `multi-repo-audit` | scopes **UNKNOWN** | scheduled daily |
| `ClearGlasslabs/ClearCast` | — | `repository-health` (reusable workflow) | — | pinned to SHA `90a3d54` |
| API audit target | `AUDIT_VALID_TOKEN`, `AUDIT_LOW_PRIV_TOKEN`, `AUDIT_OTHER_USER_ID` | `api-security-audit` | probes a running API | weekly cron |
| Control plane | `CONTROL_PLANE_URL` | `auto-store` | — | — |

## Hosting

| Provider | Config present | Actually serving |
|---|---|---|
| GitHub Pages | `CNAME`, `.nojekyll`, `pages.yml` | **Yes.** "Deploy from a branch"; run #253 deployed `b53bfd7` |
| Render | `render.yaml` | Commerce not deployed (2026-09-24). Two legacy services from another repo fail to build (B5, carried) |
| Netlify | `netlify.toml` | No evidence it serves anything |
| Fly.io | `fly.toml` | No evidence |
| Cloudflare | `_headers`, `_redirects`, `edge-security.yml` | Edge config path exists. Whether Cloudflare fronts the domain is **UNKNOWN** in this pass |

## Unconnected or half-connected

- **Lead capture:** form, API route and ledger all exist and are tested; the
  deployed API and the meta tag that points at it do not. A lead submitted on
  the live site goes nowhere.
- **Local compose:** could not record a lead until this audit's doc fix (see
  `VALIDATION_REPORT.md` §3).
- **`apps/artemis-engineering`, `clearglass-air-control`:** build manifests and
  lockfiles exist; no workflow builds or deploys either.
- **`.circleci/config.yml`:** self-declared inert.
