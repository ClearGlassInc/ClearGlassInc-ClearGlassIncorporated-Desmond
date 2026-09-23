# ClearGlass Inc.

**CLEARGLASS — See Through Everything.**

This repository is the `www.clearglassinc.com` static site **and** the source of
the backend systems that ship beside it. They deploy independently; there is no
single build.

> **CI is not running.** Since 2026-09-10 GitHub Actions dispatches no runners
> for this repository (`runner_id: 0`, re-confirmed 2026-09-23), so a green or
> red check carries no information. Run the gates yourself before pushing:
> `python3 scripts/ci_local.py`. See `docs/BASELINE.md` F1.

## What is here

| Layer | Path | Stack | Deploys to |
|---|---|---|---|
| Static site | repo root: `*.html`, `*.css`, `*.js`, `assets/`, `blog/` | Static HTML, no build step | GitHub Pages ("Deploy from a branch"), `CNAME` = `www.clearglassinc.com` |
| Commerce control plane | `control-plane/` | Python 3.11, FastAPI, SQLAlchemy | Render (`render.yaml`, Docker) |
| Storefront, Admin | `storefront/`, `admin/` | Next.js 16 | Render (`render.yaml`, Docker) |
| Live Signal Fabric | root `package.json` | Next.js 15.5 | Not deployed by any registered workflow |
| Agents and bots | `agent_army/`, `agents/`, `bots/`, `sentinel/` | Python, stdlib-first | Invoked by workflows |

The system map is `docs/ARCHITECTURE.md`. Operational procedures are
`docs/RUNBOOK.md`. What is verified, broken and unknown is `docs/BASELINE.md`.

The control plane is a **governed** engine: read-only analysis, then draft, then
human approval, then execution. Pricing, payments, refunds and fulfilment are
blocked until an approval is recorded. Read the safety model in `CLAUDE.md`
before changing `control-plane/`.

## Prerequisites

- Python 3.11, Node 20 or later, npm
- Test tooling at CI's pinned versions:

```bash
pip install pytest pytest-cov pyyaml "ruff==0.15.8"
pip install -r control-plane/requirements.txt   # includes httpx; without it the payment-path tests skip silently
```

## Run and test

**Every gate `ci.yml` runs, offline:**

```bash
python3 scripts/ci_local.py          # exit code is the verdict; use it as a pre-push hook
python3 scripts/ci_local.py --list   # what it covers
```

**Static site.** No build. Serve the root and open a page:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

**Control plane:**

```bash
cd control-plane
ruff check .
python3 -m pytest tests/ -q
uvicorn app.main:app --reload        # http://localhost:8000/docs
python -m app.daily_loop --json      # governance self-check; governance_failures must be []
```

With no Stripe or PayPal keys set, payments run in mock mode: nothing reaches a
processor and no money moves.

**Storefront and admin** (each independently):

```bash
cd storefront        # or admin
npm ci && npx tsc --noEmit && npm run build
```

**Full stack** (Postgres, control plane :8000, storefront :3000, admin :3001):

```bash
docker compose up --build
```

Not run in the 2026-09-23 audit, which had no Docker daemon. Every other command
in this file was run and passed then.

## Configuration

Names only are committed. Values belong in the hosting platform's secret store.

| File | Covers |
|---|---|
| `control-plane/.env.example` | The commerce surface: `APP_ENV`, `ADMIN_API_KEY`, `DATABASE_URL`, Stripe, PayPal, Etsy, Printful, rate limits |
| `.env.example` | The Live Signal Fabric flags, fail-closed by default |

Two settings that catch people:

- `APP_ENV=production` with no `ADMIN_API_KEY` **refuses to start**. That is
  intended.
- `revenue-command.html` reads its API base from its own
  `<meta name="cg-revenue-api">` tag, which ships empty. Until it is set to the
  control plane's public URL, its lead form cannot record leads.
  `CRCS_PUBLIC_API_BASE_URL` does not configure it; no code reads that variable.

## Adding or renaming a page

Skipping a step breaks about seven tests. It has happened twice (2026-09-15 and
2026-09-17 to 21). Follow `docs/RUNBOOK.md` §2: register the page in
`tools/internal_links.py`, run the generators, add the authority-grid link, bump
`VERSION` in `sw.js`, then `python3 scripts/ci_local.py`. Never hand-edit a
generated block, `blog/posts.json` included; editorial copy for the Insights hub
goes in `CURATED` in `tools/insights_index.py`.

## Deployment

- **Static site:** merging to `main` publishes it through GitHub's own
  `pages build and deployment` builder, which still runs while user workflows
  cannot. Keep Pages on "Deploy from a branch"; an Actions-based Pages deploy
  would publish nothing while F1 lasts.
- **Control plane, storefront, admin:** `render.yaml` blueprint. See `DEPLOY.md`.
  Whether these services are live is not verified in this repository.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Every Actions job fails in 2 to 15 seconds with no logs | F1, an organisation-level entitlement problem. Fixed in GitHub settings, not in code |
| Seven tests fail after adding one HTML page | The page is not registered. See "Adding or renaming a page" |
| `generated search assets are current` fails and leaves `sitemap.xml` modified | By design: commit the regenerated output, or `git checkout -- sitemap.xml feed.xml data/seo/page-intents.json`. Until then later test runs read the uncommitted output |
| A page renders but nothing on it responds | An inline script failed to parse. `pytest tests/test_inline_script_syntax.py` names the file and line |
| Control-plane webhook or payout tests are skipped | `httpx` is missing; install `control-plane/requirements.txt` |

## Security

Report vulnerabilities as described in `SECURITY.md`. Never commit a secret;
`python3 scripts/secret_scan.py` runs in `security.yml` and locally.

## Licence

See `LICENSE`, `NOTICE`, `TRADEMARKS.md` and `IP-POLICY.md`.
