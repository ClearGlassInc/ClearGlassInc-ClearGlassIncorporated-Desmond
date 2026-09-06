# Engineering Guidelines

Engineering standards for the `ClearGlassInc.github.io` monorepo. This complements
[`CONTRIBUTING.md`](CONTRIBUTING.md) (branch strategy, finance-bot workflow, CI
standards) and [`CLAUDE.md`](CLAUDE.md) (repo map + commerce safety model). Where
they overlap, those documents are authoritative for their topic; this file states
the cross-cutting engineering bar.

## Principles

1. **Understand before changing.** This repo is a static marketing site *plus*
   several independently deploying backends. Identify which subtree you are in
   (see the repo map in `CLAUDE.md`) before editing, and read its tests and CI
   gate first.
2. **Smallest safe change.** No speculative abstractions, no unrelated refactors,
   no style churn. Solve the problem in front of you.
3. **Preserve what ships.** Static-site changes deploy live via GitHub Pages;
   keep `.nojekyll`, `CNAME`, redirect and header files intact. Do not remove or
   rename published pages, feeds, or assets as a side effect of an unrelated fix.

## The commerce safety model is non-negotiable

For anything under `clearglass-commerce/`, the core invariant is
**read-only analysis → draft → human approval → execution.**

- `control-plane/app/governance.py` scores every proposed action 0–100 and routes
  low → auto-execute, medium → queue approval, high/critical → **blocked until an
  `approvals` row reaches `approved`**.
- Never add a code path that lets a high/critical action (pricing, payment, tax,
  refund, fulfillment, reorders, mass outbound) execute without an approval.
  `daily_loop.py`'s governance self-check and `tests/test_governance.py` exist to
  fail exactly that, by design.
- Every material change writes to the append-only audit ledger (`events` table,
  `app/audit.py`) with a risk score. Log every action.
- Never fabricate inventory, reviews, sales, or urgency.

## Per-stack workflow

**Static site (root `*.html` / `*.css` / `*.js`, `assets/`, `data/`):** edit in
place, keep markup accessible, verify links and that `sitemap.xml` still resolves.
No build step — changes deploy through GitHub Pages.

**Commerce control plane** (`clearglass-commerce/control-plane`):
```bash
pip install -r requirements.txt   # fastapi, sqlalchemy, stripe, httpx, …
ruff check .                      # must pass
python -m pytest tests/ -q        # must pass
python -m app.daily_loop --json   # governance self-check + report (stdlib only)
```
`requirements.txt` pins `httpx` because `TestClient` needs it — without it the
webhook→DB→`/payouts` money-movement tests silently skip. Do not drop that pin.

**Commerce frontend** (`clearglass-commerce/storefront`, `.../admin`):
```bash
npm ci && npm run build           # tsc --noEmit + next build (the CI gate)
```

**Bots / scripts** (`bots/`, `scripts/`): Python 3.11, `python -m pytest`. See
`CONTRIBUTING.md` for the finance-bot contract (`Decimal` for all money, frozen
dataclasses, workflow inputs mirroring env vars).

## Code style

- Match the surrounding code. The commerce control plane is typed Python; the
  stdlib-only modules (`governance.py`, `daily_loop.py`, parts of `payments.py`)
  must stay dependency-free so they run in minimal CI — if you add a dependency
  there, update the corresponding gate.
- Financial arithmetic uses `Decimal`, never `float`.
- Output files are UTF-8.

## Security

- Never commit secrets. Stripe keys are runtime env vars; the store runs in safe
  **mock mode** with no key. Use GitHub Actions secrets for all sensitive values.
- Workflows declare explicit least-privilege `permissions:` blocks.
- Validate inputs, sanitize outputs, fail closed. See `SECURITY.md` for reporting.

## CI gates that must stay green

- **Commerce Deploy** — ruff + full pytest on `clearglass-commerce/**`.
- **Commerce Frontend CI** — `tsc --noEmit` + `next build` for storefront/admin.
- **Commerce Daily Loop** — storefront smoke + governance self-check + report.

## Commits & pull requests

- Branch from `main` using the `CONTRIBUTING.md` naming scheme. One logical change
  per PR, clear title and description, CI green before merge. Open as draft first.
