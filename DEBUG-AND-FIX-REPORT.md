# ClearGlass — Debug & Fix Report

Date: 2026-09-10 · Branch: `percival/quirky-einstein-gc7qbf` · PR
[#9](https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond/pull/9)
· Base audited: `2fe1fa7` (main)

Every number below was measured by running the thing. Where something was not
measured it says so rather than carrying a zero.

---

## 1. Executive summary

| | Before | After |
|---|---|---|
| `pytest` (project config) | **Interrupted** — 2 collection errors, **0 tests ran** | **1817 passed**, 4 skipped, 0 failed |
| `ruff check .` | 30 errors | **All checks passed!** |
| `scripts/audit_github_actions.py` | 11 errors, 2 governance findings | **0 errors, 0 governance findings** |
| Registered workflows | 6 hand-written stubs | **74**, all passing the safety audit |
| `npm audit` (root) | 3 advisories (2 high) | **0 vulnerabilities** |
| Money-safety gate tests | **0 of 3 existed** | 3, each mutation-tested |
| Site generators `--check` | 3 stale | all clean and idempotent |

* **The whole CI/CD surface was dead.** 78 workflow files sat in a top-level
  `workflows/` directory GitHub Actions never reads. Neither `pytest` nor
  `ruff` had any gate at all.
* **Three modules the test suite imports did not exist**, and the suite aborted
  during collection on two of them — so under the project's own configuration,
  no test ran.
* **The three money-safety gate tests `CLAUDE.md` says enforce the invariants
  were absent.** The security code is real; nothing was checking it.
* **`logo.png` was missing from the repository**, 404ing on 41 pages and in the
  PWA manifest of all three store pages.
* **Every commerce CI job would have failed at `cd`** — 18 references to a
  `clearglass-commerce/` directory the web upload had stripped.
* **GitHub Actions executes zero jobs org-wide.** Not a code defect, and the one
  finding here that no code change can fix — see §5.

---

## 2. Root cause

The repository's first three commits are `Add files via upload` (GitHub web UI).
That upload dropped dot-directories and stripped leading path segments. Commit
`f924863` added 1862 files and contained **zero** `.github/workflows/` files.

The source was not lost — it landed at the wrong paths:

| Expected | Actual | Fixed |
|---|---|---|
| `.github/workflows/` (78) | `workflows/` | ✅ copied |
| `.github/actions/` | `actions/` | ✅ copied |
| `.github/ISSUE_TEMPLATE/` | `ISSUE_TEMPLATE/` | ✅ copied |
| `clearglass-commerce/control-plane/` | `control-plane/` | ✅ paths corrected |
| `agent_army/secure_runtime/` | `secure_runtime/` | ✅ moved back |
| `agent_army/AGENT_POLICY.md` | `AGENT_POLICY.md` | ✅ moved back |
| `docs/rfed_audit_trail_spec.md` | `rfed_audit_trail_spec.md` | ✅ doc corrected |

Nearly every defect below is a consequence of this one event.

---

## 3. Findings and fixes

### ERR-001 — 78 workflows inert; no CI gate on anything · **Critical**

`.github/workflows/` held 6 hand-written stubs; `workflows/` held 78 files
GitHub never reads. `CLAUDE.md`'s "CI gates that must stay green" described
gates that were not wired up.

**Fix.** Copied — never moved — `actions/`, `ISSUE_TEMPLATE/` and 72 workflows
into `.github/`. The flattened trees remain as the rollback source.

**Six of the 78 are not workflows at all.** No `on:` trigger, no `jobs:` map:
they are marketing-OS pipeline playbooks in that system's own DSL
(`mode: dry-run | analysis-only | fail-closed`). Registering them would have
produced six permanently invalid workflows and a red X on every push, forever.
Moved to `clearglass_marketing_os_v2/pipelines/` with a README recording how
they were identified. `scripts/audit_github_actions.py` flagged exactly these
six and no others.

### ERR-002 — Supply chain: an action pinned by mutable tag · **High**

`visual-restoration.yml` pinned `actions/checkout@v4` while all 239 other
external references pin a full commit SHA. A tag can be repointed by its owner
at any time, and it would run with that workflow's permissions.

**Fix.** Pinned to `df4cb1c0` (v6.0.3), the SHA 91 other steps already use.

### ERR-003 — Unattended jobs could push to the repo ungated · **High**

`auto-heal.yml` job `heal` and `minerals-data-sync.yml` job `sync` combined
`contents: write` with a `git push` and no protected environment. The repo's own
auditor raises `GOVERNANCE:` on exactly that shape.

**Fix.** Both bound to `environment: automation-write`, the gate
`workflow-doctor.yml` and 7 others already use.

### ERR-004 — Every commerce CI job would fail at `cd` · **Critical**

18 references across 5 workflows pointed at `clearglass-commerce/`.
`commerce-frontend-ci.yml` set
`working-directory: clearglass-commerce/${{ matrix.app }}`, so a stated "CI gate
that must stay green" could never have run a single step.

**Fix.** Corrected to the real tree, then each gate run locally:

```
ruff check control-plane                          All checks passed!
pytest control-plane/tests                        98 passed
storefront: npm ci, tsc --noEmit, next build      exit 0
admin:      npm ci, tsc --noEmit, next build      exit 0
python -m app.daily_loop --json                   "governance_failures": []
python -m bots.rfed_audit_bot --self-check        SELF-CHECK PASSED
```

### ERR-005 — The three money-safety gates did not exist · **Critical**

`CLAUDE.md` states two access-control gates are "enforced by test rather than
convention, because convention is what fails silently", and that an approval
bypass "will fail `tests/test_governance.py`, by design". **None of the three
files existed.** Someone could have added a mutating route without a
credential, a price field to the checkout contract, or an approval bypass, and
all 98 control-plane tests would still have passed.

**Fix.** All three written, each **mutation-tested** to prove it is not
decoration:

| Mutation | Result |
|---|---|
| removed `dependencies=admin` from the orders router | `test_every_mutating_route_rejects_an_unauthenticated_caller` **FAILED** |
| added `amount: int \| None` to `CheckoutLineItem` | 3 pricebook tests **FAILED** |
| commented `"trigger_refund"` out of `ALWAYS_ESCALATE` | 2 governance tests **FAILED** |

`control-plane/app/` was byte-identical to HEAD afterwards.

`test_route_auth_coverage.py` checks **behaviour, not structure**: it sets
`ADMIN_API_KEY`, calls every mutating operation in the served OpenAPI schema
with no credential, and requires 401/403. That choice is load-bearing — the
first draft introspected `app.routes` for `APIRoute` instances, and in the
FastAPI version pinned here `include_router` leaves a nested `_IncludedRouter`
instead, so the walk saw **3 routes out of 30** and would have reported a fully
open surface as fully gated.

### ERR-006 — `logo.png` 404ing in production · **High**

Missing from the repository entirely. `platform.js` injects it as
`apple-touch-icon` on **41 pages** and `manifest.webmanifest` declares it as a
PWA icon on all three store pages.

**Fix.** Restored from `icon-512.png`, the largest surviving member of its
generated family. It is 512px, not the 1024px `generate_favicons.py` declares;
no larger member survives, and the manifest declares `"sizes": "any"`, so
nothing now lies about it. Regenerate from the original source when found.

### ERR-007 — Nine pages shipped without any shared layer · **Medium**

No tab-icon block, no ClearGlass logo mark, neither half of the future-button
layer; seven were unregistered in `tools/internal_links.py`.

**Fix.** Registered in the site graph and regenerated. Both hand-maintained
layers now have a generator (`tools/shared_layers.py`) — additive, idempotent,
stdlib-only, never removes markup, and leaves the homepage hero alone (that
page proves its mark with a direct `clearglass-logo` image).

### ERR-008 — Duplicate indexable content · **Low**

`guardian_command_nexus_spec.html` at the root duplicates the `docs/` copy; all
9 inbound links target the `docs/` URL, which is the one in `sitemap.xml`. A
sales checklist under `assets/` had no inbound links at all.

**Fix.** Both keep their URL (nothing 404s) and are now `noindex` with a
canonical pointing at the surviving page.

### ERR-009 — Three absent modules aborted the suite · **Critical**

`agent_army/`, `scripts/workflow_doctor.py`,
`scripts/validate_production_deploy.py`. Not recoverable:
`ClearGlasslabs/ClearGlassInc.` — the candidate upstream named in
`PRODUCTION-RECOVERY.md` §3.3 — was cloned and inspected, and is an unrelated
184-file project containing none of them.

**Fix.** Each rebuilt from the contract its own tests and callers already pin.
`agent_army/` **did** exist — the upload scattered its members to the root
(`agent-army-crypto.yml` declares `working-directory: agent_army/secure_runtime`,
and `secure_runtime/README.md`'s own build steps say `cd agent_army/secure_runtime`).
`config.json` derives from `AGENT_POLICY.md`: its four approval gates are that
document's four external-action gates verbatim.

Matching is **word-anchored, not substring** — `preserv` catches "preserving"
while `ads` does not catch "downloads" and `dm` does not catch "admin". Naive
substring matching would have attached a paid-spend approval gate to unrelated
plans: gating that looks like it works while firing at random.

### ERR-010 — Side Store: right catalog, wrong file · **High**

Five failures blamed on an absent subsystem. The Side Store's 57-SKU catalog is
embedded inside `side-store.html`; an earlier pass had pointed the test at
`data/store/catalog.json`, which is a **different** catalog — the five
ClearGlass service engagements with live Stripe URLs, priced in the hundreds.
Conforming that file to the test would have destroyed live commerce data.

**Fix.** `tools/side_store_catalog.py` projects the page's array into
`data/side-store/catalog.json`, failing closed on a SKU over the $10 cap, a
duplicate id, or a missing field.

The pricing test needed a Node module that did not exist. **The math did**: the
cart logic computes free-shipping thresholds, a tiered bundle discount and
Ontario HST — deciding what customers are charged, with no test of any kind.
`side-store/lib/store.mjs` is a faithful port, **differential-tested against the
page's own inline `price()` across 5000 randomized carts: 0 divergences.**
11 cases now cover it, including:

* tax is charged on shipping, not only on goods;
* the **discounted** subtotal decides free shipping, not the gross subtotal —
  the regression that would give away shipping on every discounted order;
* `cents(6.99)` is 699, not 698 (`6.99 * 100` is `698.9999999999999` in IEEE
  754; truncating undercharges a cent per unit on the catalog's most common
  price point).

`assertPageConstantsMatch` fails if a constant drifts from the shipped page, so
the module can never test arithmetic no customer sees.

### ERR-011 — Two walkers broke once the app was built · **Medium**

`tests/test_future_buttons.py` and `tools/build_pages.py` excluded
`node_modules` but not `.next` — the same defect already fixed once in
`tools/seo_audit.py`. `tools/advanced_seo_growth.py` had a subtler version: it
tested only `rel.parts[0]`, so `storefront/.next/` slipped past a guard that
looked correct.

**Fix.** All three exclude build output; the last checks every path segment.

### ERR-012 — `postcss` high advisory · **High**

`next@15.5.25` pins `postcss` at exactly `8.4.31` (XSS via unescaped
`</style>`; arbitrary file read via `sourceMappingURL`). npm offered only
`next@16` — a major.

**Fix.** An `overrides` entry pinning `postcss ^8.5.28`, inside the same semver
major, validated by a full `next build` + `tsc --noEmit` (both exit 0) and 8/8
node tests. `sharp` resolved by non-major `npm audit fix` in the same pass.
**`npm audit`: 0 vulnerabilities**, down from 3.

### ERR-013 — Two workflows hard-failed on absent subsystems · **Medium**

`apps/autostore/` and `apps/artemis-browser/` are not in this repository.
Hard-failing makes CI permanently red, which trains people to ignore it;
silently skipping hides the gap.

**Fix.** Both conditional **and loud** — a `::warning::` annotation names the
missing tree on every run, and the check returns in full the moment it exists.

### ERR-014 — 30 lint findings · **Low**

**Fix.** `tools/crimson_recolor.py`'s `l` (HLS lightness) renamed to
`lightness`, **differential-tested over 4096 colours: 0 mismatches**. Compound
statements in the Playwright scripts split one per line under a hard gate — each
file's AST must dump identically to the original's. An earlier blind split
corrupted a multi-line call; the AST gate is what caught it.

### ERR-015 — `CLAUDE.md` misdirected every agent that read it · **Medium**

It described the pre-upload layout: `clearglass-commerce/`, `apps/autostore/`,
"~29 workflows", and two doc paths that do not resolve.

**Fix.** Corrected, plus a warning about the flattening itself, a note that
`workflows/` is a rollback archive to copy from and never move, and a flag that
the two catalogs must not be conflated.

---

## 4. Org-wide audit

`operations/github_audit_report.csv` — 31 repositories, every value measured by
shallow-cloning each repo, inspecting it, and resolving npm advisories from
lockfiles.

* **26 reachable, 5 unreachable** (private: `Gaurdian`,
  `clearglass-marketing-os`, `ClearCut`, `ClearClean`,
  `safe-add-animations.ps1`). Anonymous git cannot read them; auditing them
  needs credentialed attachment.
* **17 of 26 are forks** of upstream projects. Their advisories and unpinned
  actions are **inherited, not authored at ClearGlass** — the CSV marks this,
  because remediating them means updating a fork, not fixing ClearGlass code.
* **299 workflows registered across the org — none of them execute** (§5).
* **122 critical+high npm advisories across 9 repos**, concentrated in:
  `ClearGlasslabs/hermes-agent` (43), `ClearWire` (25), `vscode` (18),
  `ClearGlassIncorp/hermes-agent` (13), `gods-eye-view` (9),
  `workflow-artifacts` (9). All six are forks.
* **255 unpinned external actions across 23 repos** — `workflow-artifacts` (69),
  `ClearWire` (54), `claude-agent-sdk-python` (38), `ClearGlassInc/Opal-Koboi`
  (19). Each is a mutable reference its owner can repoint.
  `ClearGlassInc/Opal-Koboi` is **not** a fork, so its 19 are ClearGlass's own.
* **15 repos have no lockfile**, so their npm advisories cannot be resolved at
  all and `npm ci` would fail in CI.

Only this repository had the inert-workflow defect.

---

## 5. The finding no code change can fix

**GitHub Actions executes zero jobs in this organisation.** Measured on this
PR's own head minutes after pushing:

```
run 34532954435   run_duration_ms 7000   billable.UBUNTU.total_ms 0
job 103057819702  conclusion failure     runner_id 0   runner_name ""
                  steps: (absent from the response entirely)
```

Zero billable milliseconds, no runner assigned, no steps array: **the job was
never dispatched.** It did not fail while running — it failed before running.
The same signature covers 127 prior failures across 8 workflows and 6 trigger
types. No user-authored workflow has ever succeeded in this repository.

Ruled out by observation: workflows are `state: "active"`; the repo is public,
so standard runners are unmetered; every precondition the workflows assert
passes against this tree.

**This is an owner action, not an engineering one.** In order:

1. Organisation → Settings → **Billing and plans** → payment method / spending limit
2. Organisation → Settings → **Actions → General** → policy and allowed actions
3. Repository → Settings → **Actions → General**

Confirm by dispatching **Cert Bot** (`workflow_dispatch`, ~5s, no secrets,
read-only) and checking `get_workflow_run_usage` reports **non-zero**
`billable.UBUNTU.total_ms`. That number is the pass/fail signal — a green tick
alone is not, since these jobs currently fail without ever running.

---

## 6. Remaining risks

| # | Risk | Severity | Note |
|---|---|---|---|
| R1 | Actions entitlement blocked org-wide | **Critical** | §5 — owner action, blocks everything downstream |
| R2 | Merging PR #9 activates 33 scheduled jobs, 32 write-capable workflows and 14 credential paths at once | **High** | Explicitly requested. Rollback: delete from `.github/workflows/`; the archive is intact |
| R3 | `scripts/stripe-sync/` is missing its type contract, CLI entrypoint and `sync:stripe` npm script | **High** | 1683 lines of live-Stripe logic, entirely untypechecked (`scripts` is excluded from `tsconfig.json`). **Not rebuilt** — inferring the CLI semantics of a tool that mutates live Stripe products is where fabrication turns into charging customers wrong |
| R4 | 122 crit+high advisories across 9 org repos | **High** | Mostly forks; see §4 |
| R5 | 255 unpinned actions across 23 repos | **Medium** | `ClearGlassInc/Opal-Koboi`'s 19 are ClearGlass-authored |
| R6 | 15 repos have no lockfile | **Medium** | `npm ci` fails outright; advisories unresolvable |
| R7 | 5 private repos unaudited | **Medium** | Need credentialed attachment |
| R8 | Site CSP carries `script-src 'unsafe-inline'` + 2 CDNs | **High** | `security/HARDENING_AND_THREAT_MODEL.md` §3 — stated, not hidden |
| R9 | Cloudflare: 3 deployed Workers, no committed config matches any | **Medium** | Unchanged from the prior audit |
| R10 | Homepage animations reflow continuously (15.1px jitter) | **Medium** | Touching the live hero was out of scope |
| R11 | `logo.png` is 512px, not the declared 1024px | **Low** | Pending the original source |

---

## 7. Next actions, highest value first

1. **Restore the Actions entitlement** (§5). Owner action, minutes, unblocks
   everything else. Nothing in CI can be verified until this is done.
2. **Merge PR #9**, then confirm a `pages build and deployment` run appears and
   the site serves current content.
3. **Recover `scripts/stripe-sync/`** (R3) from wherever the original lives, or
   decide the sync is retired and delete `sync-stripe-products.yml`. Do not
   rebuild it by inference.
4. **Attach the 5 private repos** and re-run the audit over them.
5. **Triage the 122 advisories** (R4) — for forks, decide whether to sync
   upstream or archive the fork.
6. **Add lockfiles** to the 15 repos without them (R6): one `npm install`
   commit each, and `npm ci` starts working.
7. **Remove `'unsafe-inline'`** from the site CSP (R8) — the largest remaining
   hardening item, and the most involved.

---

## 8. Runbook

```bash
# Full suite (the project's own configuration)
python3 -m pytest                                   # 1817 passed

# Lint — must pass repo-wide
ruff check .

# Workflow safety: fail-closed, offline, no API access
python3 scripts/audit_github_actions.py             # 0 errors
python3 scripts/workflow_doctor.py                  # audit; --fix to repair

# Site generators — all idempotent, all support --check
python3 tools/tab_icons.py --check
python3 tools/internal_links.py --check
python3 tools/shared_layers.py --check
python3 tools/side_store_catalog.py --check
python3 tools/security_release_manifest.py --check

# Commerce control plane
cd control-plane && ruff check . && python3 -m pytest tests/ -q
python3 -m app.daily_loop --json                    # governance_failures: []
python3 -m bots.rfed_audit_bot --self-check

# Frontends (each deploys independently)
cd storefront && npm ci && npx tsc --noEmit && npm run build
cd admin      && npm ci && npx tsc --noEmit && npm run build

# Side Store pricing
node --test side-store/lib/store.test.mjs           # 11/11
```

**Rollback.** Each commit on PR #9 reverts independently. Workflow registration
rolls back by deleting files from `.github/workflows/` — `workflows/` is intact
and untouched. No static page content changed except additive tag insertion and
regenerated link blocks; bump `VERSION` in `sw.js` after any content revert.

**Two standing rules for this repository.**

* `workflows/` is the intact archive. Always **copy** into `.github/workflows/`,
  never move.
* **A green check here is not evidence a job ran.** Confirm
  `billable.UBUNTU.total_ms > 0` before trusting any Actions result.
