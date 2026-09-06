# Auto-Store Workflow — Operator Runbook

The auto-store pipeline (`.github/workflows/auto-store.yml`) is the end-to-end
release path for the ClearGlass storefront (`store.html` / `pricing.html`) and
the **autostore control plane** (`apps/autostore/`). It is the executable form
of the [SOUL.md](../SOUL.md) charter: grow and protect revenue with measurable,
auditable, rollback-safe automation.

```
validate ─▶ test ─▶ checkout-health ─▶ deploy ─▶ verify
                                          └────────────▶ rollback (on failure)
(any failure) ─────────────────────────────────────────▶ alert
```

## What each stage does

| Stage | Job | Guarantee |
|---|---|---|
| Validate | `validate` | `ruff` lint, workflow-doctor hygiene, and **store-data sync** (`store_sync.py --check`) — the committed catalog must match `store.html`. |
| Install + Test | `test` | Installs the toolchain via the reusable `store-setup` action; runs the root bot/agent suite **and** the autostore control-plane trust loop. |
| Checkout health | `checkout-health` | Static money-safety smoke (`store_smoke_bot.py`): every SKU wired into all checkout maps, only safe Stripe links, e-Transfer fallback intact. Runs **before** deploy. |
| Deploy | `deploy` | Gated on the `production` environment (add required reviewers for human approval). Records the release marker, **promotes the rollback anchor**, and triggers the control-plane deploy. |
| Verify | `verify` | Post-deploy checkout smoke + optional live `/healthz` probe with retry/backoff. |
| Rollback | `rollback` | Runs only if deploy/verify failed: triggers the control-plane rollback hook and surfaces the last-known-good catalog. |
| Alert | `alert` | Any failure opens/updates a `auto-store-alert` tracking issue. Best-effort — alerting never fails the pipeline. |

## Triggers

- **pull_request** — validate + test + checkout-health only. **No deploy** (AI/PR
  work can never reach production from here — honors the "no direct push to
  protected branches" constraint).
- **push to `main`** — validate + test + checkout-health only. A merge does not
  grant production authority or attempt a deploy when runtime configuration is
  absent.
- **schedule** (daily 12:00 UTC) — drift + checkout-health guard, no deploy.
- **workflow_dispatch** — set `deploy=true` and provide the approved
  `change_ticket` reference to request the deploy/verify path. The protected
  `production` environment remains the human authorization boundary.

## Store-data sync (`scripts/store_sync.py`)

`store.html` is the single source of truth. The sync distils it into
`data/store/catalog.json` (deterministic, hash-stamped) so downstream consumers
read JSON instead of re-parsing HTML — faster and far less brittle.

```bash
python scripts/store_sync.py --check     # CI gate: committed catalog in sync?
python scripts/store_sync.py --write      # regenerate catalog.json after a store edit
python scripts/store_sync.py --promote    # record last-known-good rollback anchor
```

> **Revenue continuity:** live card checkout being *off* is a healthy state. When
> the Stripe account has paused capabilities, every checkout link is empty and the
> storefront falls back to **Interac e-Transfer + confirmed invoice** — revenue
> keeps flowing. The catalog records this as `fallback_note`; the pipeline treats
> it as a known-good state, not a failure.

## Secrets (least privilege, GitHub Secrets only)

| Secret | Used by | Effect if unset |
|---|---|---|
| `RENDER_DEPLOY_HOOK_URL` | `deploy` | Preflight fails before a release marker is promoted. |
| `RENDER_ROLLBACK_HOOK_URL` | `deploy`, `rollback` | Preflight fails before deployment; no release proceeds without a tested rollback hook. |
| `CONTROL_PLANE_URL` | `deploy`, `verify` | Preflight fails before deployment because post-release health cannot be verified. |

`GITHUB_TOKEN` is the default least-privilege token; only `alert` widens to
`issues: write`. No long-lived credentials live in the repo.

## Rollback (target: < 2 minutes)

Automatic on deploy/verify failure. Manual, if ever needed:

```
Render Dashboard → control-plane service → Deploys → Rollback to last green
```

The last-known-good catalog hash is uploaded as the `store-rollback-anchor-<run_id>`
artifact (30-day retention) and printed in the rollback job summary.

## After editing the storefront

1. Edit `store.html` (and `pricing.html` to match).
2. `python scripts/store_sync.py --write` and commit `data/store/catalog.json`.
3. Open a PR — validate/test/checkout-health run automatically.
4. Merge to `main`; confirm the validation-only run is green.
5. Dispatch **Auto-Store** with `deploy=true` and the approved change-ticket
   reference; approve the protected `production` environment; verify the run
   and production health before closing the ticket.
