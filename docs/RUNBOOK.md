# Runbook

**Recorded against:** `79c493b` (2026-09-15)
**Companions:** `docs/ARCHITECTURE.md` (what the systems are),
`docs/BASELINE.md` (verified state and risk register),
`docs/INCIDENT_RESPONSE.md`, `docs/REVENUE_OPERATIONS.md`.

Procedures only. Every command below was run against this commit unless the step
says otherwise.

---

## 0. Read this first

**CI does not work.** GitHub Actions has dispatched no runners since 2026-09-10
(`docs/BASELINE.md` F1). Every check fails in seconds with no logs. A green check
would be meaningless and a red one carries no information.

**Until an owner clears that, you are the CI.** Run the gates locally before
every push. This is not optional hygiene — it is currently the only verification
that exists.

```bash
pip install pytest pytest-cov pyyaml "ruff==0.15.8"
pip install -r control-plane/requirements.txt
python3 scripts/ci_local.py
```

Expected on a healthy `main`: **9 passed, 0 failed, 1 skipped.** The skip is
`lighthouse`, network-gated; re-run with `--with-network` to include it.

`scripts/ci_local.py --list` shows what it covers. **Keep it in step with
`ci.yml`** — a job added there and not here under-reports, which is the exact
failure mode it exists to prevent.

---

## 1. Verify the repository

### 1.1 Full local gate run

```bash
python3 scripts/ci_local.py            # 10 gates mirrored from ci.yml
python3 -m pytest tests/ -q            # expect 1253 passed, 5 skipped
cd control-plane && python3 -m pytest tests/ -q   # expect 378 passed, 1 skipped
```

### 1.2 Governance self-checks

```bash
python -m bots.rfed_audit_bot --self-check              # RFED invariants, stdlib only
cd control-plane && python -m app.daily_loop --json     # governance self-check + report
```

### 1.3 Node — currently partly broken

```bash
npm ci && npm run typecheck                  # root
cd storefront && npm ci && npm run build     # storefront
cd admin && npm ci                           # FAILS — see §6.1
```

**`admin/` exits 1.** Do not treat that as your mistake; it is `docs/BASELINE.md`
F6 and it is on `main`.

---

## 2. Add or rename a page on the static site

Skipping any step breaks seven tests. This is not theoretical — it is F5, which
reached `main` on 2026-09-15.

```bash
# 1. Register it — edit tools/internal_links.py:
#      • add "path/to/page.html": ("Title", "description") to PAGES
#      • add the path to a cluster
#    Title and description come from the page's own <title> and meta description.

# 2. Add it to sitemap.xml, with lastmod = the page's real publication date.
#    Do NOT copy a sibling's lastmod.

# 3. Run the generators. All are additive and idempotent.
python3 tools/shared_layers.py          # future-buttons css/js + logo-badge
python3 tools/tab_icons.py              # tab-icon block
python3 tools/internal_links.py         # related-content block
python3 tools/generate_search_assets.py # sitemap, feed, intent map

# 4. Add one grid link by hand in authority-network.html.
#    tools/authority_network.py is check-and-report only and never writes links.

# 5. Bump VERSION in sw.js (cg-vNN → cg-vNN+1) so cached tabs refetch.

# 6. Verify.
python3 scripts/ci_local.py             # must be 9 passed, 0 failed
git status --short                      # must be clean after the run
```

Dry-run any generator first with `--dry-run`; `--check` verifies freshness
without writing.

**Never hand-edit a generated block.** Regenerate it.

### 2.1 If `generated search assets are current` fails

The gate compares generator output against **what is committed**, and writes the
regenerated output into the working tree. Run
`python3 tools/generate_search_assets.py`, then **commit the result** — the gate
stays red until the output is committed, not merely present. (R12.)

---

## 3. Run the stack locally

```bash
docker compose up --build
```

| Service | Address | Notes |
|---|---|---|
| postgres | `127.0.0.1:5432` | healthcheck-gated |
| control-plane | `127.0.0.1:8000` | `/docs` for OpenAPI |
| storefront | `127.0.0.1:3000` | |
| admin | `127.0.0.1:3001` | |

All bound to loopback. With no Stripe or PayPal credentials every payment path
runs in **mock mode**: no order is created at any processor and no money moves.

API only:

```bash
cd control-plane
pip install -r requirements.txt
uvicorn app.main:app --reload     # http://localhost:8000/docs
```

Health checks:

```bash
curl -fsS localhost:8000/health   # liveness; no external calls
curl -fsS localhost:8000/ready    # readiness; executes SELECT 1, 503 on failure
```

---

## 4. Deploy

### 4.1 Static site — GitHub Pages

Source must stay on **"Deploy from a branch."** Merging to `main` publishes.

`.github/workflows/pages.yml` runs `scripts/verify_site.py`, builds `dist/`, and
publishes. That script **is present** (restored in `be0b7cd`) — `CLAUDE.md` still
carries a stale notice claiming it is missing (R10).

Because Actions dispatches no runners, the Actions-based path is inert today.
Pages continues to serve from the branch.

### 4.2 Commerce stack — Render — BROKEN

**Do not attempt the Render blueprint without fixing it first.** `render.yaml`
declares three Docker contexts under `./clearglass-commerce/`, a directory that
is not in this repository (F7):

| Declared | Actual |
|---|---|
| `./clearglass-commerce/control-plane/` | `./control-plane/` |
| `./clearglass-commerce/storefront/` | `./storefront/` |
| `./clearglass-commerce/admin/` | `./admin/` |

`docker-compose.yml` already uses the correct paths, which is how the local stack
still works. `DEPLOY.md` carries the same stale prefix in its Fly.io command.

Fixing `render.yaml` is a **protected-path change**: pull request and human
approval, never auto-merge.

### 4.3 After any successful deploy

Record the deployment identifier before doing anything else. It is the rollback
target, and after a failure is the worst time to go looking for it.

---

## 5. Roll back

**Never roll forward repeatedly after a failed production deploy.** Roll back,
capture evidence, open a remediation PR.

### 5.1 Repository-level

```bash
git revert <merge-commit>        # preferred: preserves history
git push origin main
```

Every PR in this repository states its rollback command. Use the one the PR
names.

### 5.2 Static site

Reverting the merge and letting Pages republish is the rollback. If the service
worker is serving stale assets, confirm `sw.js` `VERSION` changed in the revert.

### 5.3 Commerce stack

Render redeploys a previous successful deploy from its dashboard. **This path is
untested here** and is gated behind F7.

### 5.4 Always

Open an incident record with logs, deploy ID, commit SHA and rollback status.
See `docs/INCIDENT_RESPONSE.md`.

---

## 6. Known-broken procedures

### 6.1 `admin/` will not install

```
cd admin && npm ci
npm error code ERESOLVE
npm error While resolving: react-dom@18.3.1
npm error Found: react@19.3.0
npm error peer react@"^18.3.1" from react-dom@18.3.1
exit code: 1
```

`admin/package.json` declares `react: ^19.3.0` beside `react-dom: ^18.3.0`. They
must share a major. Behind it, `typescript: ^5.4.0` in the manifest versus
`7.0.2` in the lockfile — outside the range, so `npm ci` would fail on that too.

**Blocked on a decision, not on effort.** Next 16 accepts React 18 or 19, and
this repository contains both choices (`storefront/` on 18; root and
`apps/artemis-engineering` on 19). Picking one silently would commit `admin/` to
a major nobody chose. Manifests and lockfiles are protected paths.

Unaffected: `storefront/`, repo root, `apps/artemis-engineering` — all carry
matching `react` / `react-dom`.

### 6.2 CI checks

All of them. F1. Nothing to fix in this repository.

---

## 7. Payments — operating rules

Detail in `docs/REVENUE_OPERATIONS.md`. Non-negotiable:

- **A redirect is not a receipt.** Fulfillment starts only on a
  signature-verified server-side webhook.
- **Never** auto-refund, discount, reprice, or change tax/shipping settings.
- **Never** publish, deactivate, edit, reprice or renew an Etsy listing without
  human approval.
- Unset credentials are safe — every integration runs in mock mode, makes no
  network call, and moves no money.
- `APP_ENV=production` with no `ADMIN_API_KEY` **fails closed at startup**. That
  is intended; supply the key rather than removing the check.
- Never log card data, access tokens, API secrets, or full sensitive personal data.

### 7.1 Connecting Etsy

Human OAuth2 (PKCE) step. The CLI prints tokens for a runtime secret store and
never persists one.

```bash
cd control-plane
python -m app.etsy_connect --status     # connection state
python -m app.etsy_connect              # OAuth flow — see ETSY_CONNECT.md
```

Connecting unlocks nothing on its own: every Etsy write is in `ALWAYS_ESCALATE`.

### 7.2 Claiming an integration is live

Requires **both** a recorded sandbox test and a recorded production
verification. Neither exists for any channel today. Until both are recorded, no
integration may be described as live — including in a commit message or a PR.

---

## 8. Secrets

Names only, never values. Full inventory in `control-plane/.env.example`
(complete) and `docs/BASELINE.md` §7.

Set every runtime secret in the hosting platform's secret manager — Render
environment groups or equivalent. Never in a file, never in a commit.

Blocking today:

| Variable | Blocks |
|---|---|
| `ADMIN_API_KEY` | Production startup — the app refuses to boot without it |
| `PAYPAL_WEBHOOK_ID` | All PayPal webhook verification; every notification is refused |
| `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` | PayPal order creation |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Stripe checkout and webhook booking |
| `ETSY_KEYSTRING` / `ETSY_SHARED_SECRET` / `ETSY_ACCESS_TOKEN` / `ETSY_REFRESH_TOKEN` | Etsy reconciliation |

Scan before pushing:

```bash
python3 scripts/secret_scan.py
```

### 8.1 Rate limiting behind a proxy

`TRUSTED_PROXY_HOPS` and `TRUSTED_PROXY_IPS` ship disabled. Behind Render or
Cloudflare, leaving them unset collapses every caller into one throttle bucket —
one abusive client can 429 the whole storefront.

To configure: curl `/health` on the deployed service, read `client_peer`, then
set `TRUSTED_PROXY_IPS=<that address or its /32>` and `TRUSTED_PROXY_HOPS=1`.
Set **both**. An RFC1918-wide allowlist is not sufficient — it trusts the exact
ingress a bypass would run on.

---

## 9. Owner-only actions

None of these can be done from this repository. Each blocks work that is
otherwise ready.

| Action | Where | Unblocks |
|---|---|---|
| Restore Actions entitlement — billing, spending limit, allowed-actions policy, Actions toggle | GitHub org + repo settings | F1; CI, staging, deploy, rollback, scheduled automation |
| Confirm which provider serves `www.clearglassinc.com` | Hosting dashboards | R5; deployment and rollback automation |
| Protect `main` | Repo → Settings → Branches | R7 |
| Decide `admin/`'s React major, and whether TypeScript 7 was intended | — | F6 |
| Resolve the 1,250 / 297 / 249 price conflict | — | R3 |
| Supply payment and Etsy credentials | Render environment group | Every revenue channel |

**Gate 0** — the measurable exit condition for F1: any user-authored workflow job
reporting `runner_id != 0` with a non-empty `steps` array. Until then, treat
every check on every PR as unreported.

---

## 10. Before you push — checklist

- [ ] `python3 scripts/ci_local.py` → 9 passed, 0 failed
- [ ] `git status` clean after the gate run
- [ ] Generated files regenerated by their generator, not hand-edited
- [ ] `sw.js` `VERSION` bumped if pages changed
- [ ] No secret value in the diff; `scripts/secret_scan.py` clean
- [ ] Protected path touched? → PR + human approval, no auto-merge
- [ ] PR states risk level, test evidence, rollback command, and a
      PASS / BLOCKED / NEEDS-HUMAN-APPROVAL status
