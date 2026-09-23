# Changelog

Human-readable record of notable changes. Automation-specific entries live in
`docs/AUTOMATION_CHANGELOG.md`; verified state and open findings live in
`docs/BASELINE.md`.

Dates are UTC. Every entry names the evidence it rests on. Nothing here is
recorded as done unless it was observed.

---

## 2026-09-23

`main` had gone red again. 156 commits (PRs #52 to #101) merged with no CI,
because F1 still holds: job `107260634855` today reported `runner_id: 0`.
Every item below was verified locally. Full per-issue report:
`docs/AUDIT-2026-09-23.md`.

### Fixed

- **The Revenue Command lead form wrote prospects' personal data into the
  URL** (live since 2026-09-21). A `//$/` regex parsed as a comment, the
  script died, and the form fell back to a native GET. Reproduced in
  Chromium; fixed, and the form is now `method="post"`.
- **Two more pages were dead on load:** `artemis-iv.html` (duplicate
  `const`) and `counter-uas-commercialization-os.html` (stray `)`).
- **14 pages shipped outside the site graph** (F5 again, at scale): 21 root
  tests and 5 of 10 `ci_local` gates red. Four registered as public pages;
  ten raw uploads classified and marked noindex.
- **Hand edits to generated Insights files** would have been erased by the
  next regeneration. The editorial copy now lives in `CURATED`.
- **`sharp`, `nanoid`, `baseline-browser-mapping`** advisories patched in
  storefront **and** admin (2 high + 1 moderate each → 0).
- **`/revenue/checkout` revealed which leads exist** (404 vs 403 on
  sequential ids). Latent until payments are enabled.
- **Storefront and admin containers ran as root** and had no
  `.dockerignore`.
- **The README described a codebase that is not here** (0 of 13 named files
  exist). Moved to `docs/proposals/`; README rewritten from verified facts.
- A test pinned one exact action SHA, so Dependabot bumps turned `main` red;
  it now asserts SHA-pin shape. Four ruff errors cleared. Two dead
  `.env.example` keys marked unread.

### Added

- `tests/test_inline_script_syntax.py`: every inline script on every page
  must parse (298 blocks, one Node process).
- `docs/AUDIT-2026-09-23.md`.

### Verified

| Target | Result |
|---|---|
| `python3 scripts/ci_local.py` | 4/6/1 → **10 passed, 0 failed**, 1 skipped (Lighthouse, network) |
| `pytest tests/` | 21 failed → **1568 passed**, 12 skipped |
| `pytest control-plane/tests/` | **402 passed**, 1 skipped |
| storefront, admin: `npm ci`, `tsc --noEmit`, `next build` | exit 0 |
| `npm audit` root / storefront / admin | 0 / 0 / 0 |
| `pip-audit` control plane | no known vulnerabilities |
| Secrets, current tree and full history | none |
| Reflected DOM XSS, 93 pages in Chromium | 0 hits (probe validated on a planted positive) |

### Not verified

The live site (this session's network policy blocked it), the Docker image
builds (no daemon), and Render. See the audit's §4.

---

## 2026-09-15

The day the repository's own tests started being run again. GitHub Actions has
dispatched no runners since 2026-09-10 (`docs/BASELINE.md` F1), so every change
below was verified with `python3 scripts/ci_local.py` locally. **CI reported
nothing for any of them.**

### Fixed

- **`commerce.selfcheck` ran in a directory that does not exist** (F8, #67).
  `agent_os/operator.py` set the capability's working directory to
  `clearglass-commerce/control-plane`. `_default_runner` catches the resulting
  `OSError` and returns 127, so the failure was silent. Corrected to
  `control-plane`; measured 127 → 0. Added
  `test_every_capability_runs_in_a_directory_that_exists`, which fails against
  the old constant.

- **The Render blueprint could not build** (F7, #55). `render.yaml` declared all
  three Docker contexts under `clearglass-commerce/`, a directory the upload
  flattening removed, while `DEPLOY.md` recommended the blueprint as the primary
  deploy path. All six path declarations corrected; all now resolve on disk.
  The four Render service identities were deliberately preserved — two appear in
  `cors_allow_origins`, so a blanket find-replace would have altered the deployed
  origin allowlist.

- **`main` was red: an unregistered page broke seven tests** (F5, #53). A new
  blog page was added and registered nowhere, shipping to a live site with no
  internal links, no sitemap entry, no tab icon and no logo. Repaired through the
  documented generators. `pytest tests/` went from 7 failed to 0.

- **`admin/` could not be installed** (F6, #56, by another contributor).
  `react ^19.3.0` beside `react-dom ^18.3.0` made `npm ci` exit 1, so the admin
  app could not be built or deployed. Verified fixed here: `npm ci` and
  `next build` both exit 0.

- **Stale guidance corrected** (R10). `CLAUDE.md` carried a standing notice that
  `scripts/verify_site.py` was missing. It was restored in `be0b7cd`, is present,
  and exits 0. The notice now records the real deploy blocker, which is F1.
  `ENGINEERING_GUIDELINES.md` had four stale commerce paths.

### Added

- `docs/BASELINE.md` (#52) — verified state, eight classified failures, risk
  register, revenue-flow state, and a five-stage non-production test plan.
- `docs/ARCHITECTURE.md` and `docs/RUNBOOK.md` (#54) — the system map and the
  operational procedures, including the add-a-page procedure whose absence
  produced F5.
- `docs/CHANGELOG.md` — this file.

### Verified

Recorded because "not verified" and "working" are different states, and this
repository has been conflating them.

| Target | Result |
|---|---|
| `python3 scripts/ci_local.py` | 9 passed, 0 failed, 1 skipped (Lighthouse, network-gated) |
| `pytest tests/` | 1253 passed, 5 skipped |
| `pytest control-plane/tests/` | 378 passed, 1 skipped |
| root — `npm ci`, `tsc --noEmit` | exit 0, **0 vulnerabilities** |
| `storefront/` — `npm ci`, `next build` | exit 0 |
| `admin/` — `npm ci`, `next build` | exit 0 |

### Known issues opened

- **3 dependency vulnerabilities in `storefront/`** — 2 high, 1 moderate:
  `nanoid` (custom generators can loop indefinitely at size zero), `sharp`
  (libheif, GHSA-g89c-p67h-r497 and GHSA-2jg2-4ch7-h545), and
  `baseline-browser-mapping` (process termination on invalid input). Surfaced by
  `npm audit`; not remediated here. Lockfiles are a protected path.

- **~70 stale `clearglass-commerce/` references remain in prose.** Not swept,
  deliberately. Several are *correct as history* — `CLAUDE.md` records that the
  tree "lost its `clearglass-commerce/` parent", and `DEBUG-AND-FIX-REPORT.md`
  documents the damage. A blanket find-replace would corrupt an accurate incident
  record. Two others must never be swept: a `User-Agent` string in
  `control-plane/app/printful.py`, and what appears to be a path allowlist in
  `agents/*/agent.json`.

### Unchanged and still blocking

F1 (Actions entitlement), R3 (three live entry prices with no SKU for the
CAD 1,250 assessment), R5 (which provider serves the live domain), R6 (no
staging environment), R7 (`main` unprotected), R8 (catalog lacks the fields
needed to validate a checkout). All require an owner decision or an
owner-settings change. See `docs/BASELINE.md`.

**No payment channel is live.** No integration has completed both a sandbox test
and a production verification, so none may be described as live.
