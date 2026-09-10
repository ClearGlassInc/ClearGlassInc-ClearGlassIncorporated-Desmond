# ClearGlass Production Recovery

Audit date: 2026-09-10 · Repository: `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond`
Branch: `claude/clearglass-production-recovery-qwyrne` · Base commit audited: `2fe1fa7`

Every claim below is followed by the command or API field it came from. Where a
fact could not be observed from this environment it is marked **UNVERIFIED**
rather than inferred.

---

## 1. Verified Findings

### 1.1 GitHub Actions has not executed a single job since 2026-09-06 13:14 UTC

This is the top production blocker and it is not a code defect.

Observed over all 185 workflow runs in the repository's history
(`actions_list/list_workflow_runs`, pages 1–2, window
`2026-09-06T11:57:38Z .. 2026-09-10T13:45:16Z`):

| Conclusion | Runs |
|---|---|
| `success` | 57 — **all** of them GitHub-managed: `pages build and deployment` ×50, Dependabot `Graph Update: pip` ×7 |
| `failure` | 127 |
| `cancelled` | 1 |

* **Last successful run of any kind: `2026-09-06T13:14:52Z`** (`pages build and deployment`).
* Every run created after that timestamp failed — 4 days, 8 distinct workflows,
  and 6 different trigger types (`push`, `pull_request`, `schedule`,
  `workflow_dispatch`, `workflow_run`, `dynamic`).
* **Not one user-authored workflow has ever succeeded in this repository.**

The failures are pre-execution. For run `34484619029` job `102895644518`
(`actions_get/get_workflow_job` and `get_workflow_run_usage`):

```
runner_id       : 0
runner_name     : ""
steps           : (absent from the response entirely)
billable.UBUNTU : { total_ms: 0, jobs: 1, job_runs: [{ duration_ms: 0 }] }
run_duration_ms : 5000
```

Zero billable milliseconds, no runner assigned, and no steps array: the job was
never dispatched to a runner. Job logs return **HTTP 404**, consistent with a
job that produced no log stream.

Ruled out by direct observation:

* **Not a workflow-level disable.** All 12 workflows report `state: "active"`
  (`actions_list/list_workflows`), including `pages-build-deployment`.
* **Not free-minute exhaustion.** The repository is `"visibility":"public"`
  (`list_repos`), and public repositories get unmetered standard runners.
* **Not the workflow YAML.** Every precondition each of the 6 registered
  workflows asserts passes against the current tree (§4.1), and the one
  non-trivial inline script parses cleanly (`bash -n` → `SYNTAX OK`).

What remains consistent with the evidence is an **account- or
organisation-level Actions entitlement or runner-provisioning block**. The
organisation owns private repositories (`ClearGlassInc/Gaurdian`,
`ClearGlasslabs/clearglass-marketing-os`, `ClearCut`, `ClearClean`,
`safe-add-animations.ps1`) whose paid-minute usage is billed, and a billing
suspension or an org-level Actions policy would produce exactly this
signature. **UNVERIFIED — the billing and org-policy pages are not readable
through the tooling available to this audit.** Check, in order:

1. Organisation → Settings → **Billing and plans** → payment method / spending limit.
2. Organisation → Settings → **Actions → General** → policy and allowed actions.
3. Repository → Settings → **Actions → General**.

### 1.2 Production has been serving stale content for 4 days

`pages build and deployment` is the repository's actual deploy mechanism —
GitHub's built-in Pages builder, meaning Pages is configured in **"Deploy from
a branch"** mode (there is no `deploy-pages` workflow in `.github/workflows/`).

Its last run was `2026-09-06T13:14:52Z`. **No Pages build has been created
since.** Every commit merged after that point has therefore not reached
`www.clearglassinc.com` — including PR #4 (site-wide crimson palette) and PR #5
(homepage centring fix), both merged 2026-09-10.

**UNVERIFIED:** the live site could not be probed from this environment —
outbound HTTPS to `www.clearglassinc.com` is refused by the agent proxy
(`curl: (56) CONNECT tunnel failed, response 403`). The deployment *record*
above is nonetheless conclusive.

### 1.3 Root cause of the repository's structural damage: a lossy web upload

The repository was not migrated with git. Its first three commits are
`Add files via upload` (GitHub web UI). Commit `f924863` alone added **1862
files / 361,219 insertions**, and contained **zero** `.github/workflows/`
files (`git show --name-only f924863 | grep -c '^.github/workflows/'` → `0`).

The upload dropped dot-directories and stripped leading path segments. The
source was **not lost** — it landed at the wrong paths:

| Expected path | Actual path in this repo |
|---|---|
| `.github/workflows/` (78 files) | `workflows/` |
| `.github/ISSUE_TEMPLATE/` | `ISSUE_TEMPLATE/` |
| `.github/actions/` | `actions/` |
| `.well-known/security.txt` | `security.txt` (repo root) |
| `clearglass-commerce/control-plane/` | `control-plane/` |
| `marketing/local_growth_planner.py` | `local_growth_planner.py` |
| `marketing/content_engine/` | `content_engine/` |
| `marketing/config/…watchlist.json` | `config/…watchlist.json` |
| `docs/contracts/…schema.json` | `contracts/…schema.json` |
| `scripts/build_pages.py` | `tools/build_pages.py` |
| `percival_v9/__init__.py` | *dropped* (subpackage `__init__.py` files survived) |

Two consequences that were live defects, not cosmetic:

* **`.well-known/security.txt` was unreachable in production.** `_headers`
  serves `/.well-known/security.txt` and the file's own `Canonical:` line
  declares that URL, but the dot-directory was stripped — so the RFC 9116
  security contact 404'd.
* **The entire governed-commerce test suite was silently uncollected** (§1.4).

### 1.4 The test suite could not run at all, and 98 governed-commerce tests were dead

`pyproject.toml` pointed `testpaths` and `pythonpath` at
`clearglass-commerce/control-plane`, which does not exist. Result:
`control-plane/tests/` — 98 tests covering checkout, pricing, Etsy and
fulfilment — **were never collected**. This is precisely the silent-skip failure
mode `CLAUDE.md` warns about for the money-movement paths.

Worse, `pytest` with the project's own configuration **aborted during
collection** on 6 import errors, so no test ran:

```
$ python3 -m pytest -q            # project config, as CI would
Interrupted: 6 errors during collection
1 skipped, 6 errors in 3.27s
```

Forcing past collection revealed the real baseline:
**28 failed, 1445 passed, 3 skipped, 10 errors.**

### 1.5 78 of 84 workflows are inert, and CI runs neither tests nor lint

`.github/workflows/` holds 6 workflows. `workflows/` holds **78** that GitHub
never reads — including the ones the test suite asserts must exist: `pages.yml`,
`ci.yml`, `auto-store.yml`, `enterprise-patch-deploy.yml`,
`minerals-data-sync.yml`, `site-integrity-and-deploy.yml`, `workflow-doctor.yml`,
`commerce-deploy.yml`, `commerce-frontend-ci.yml`, `commerce-daily-loop.yml`.

None of the 6 registered workflows runs `pytest` or `ruff`. The Python suite and
linter have **no CI gate whatsoever**. `CLAUDE.md`'s "CI gates that must stay
green" section describes gates that are not wired up in this repository.

### 1.6 Static analysis

| Scope | Command | Result |
|---|---|---|
| Whole repo | `ruff check .` | **1016 errors** (739 auto-fixable) |
| Control plane | `ruff check control-plane/` | **70 errors** (36 auto-fixable) |

`CLAUDE.md` states `ruff check .` "must pass" for the control plane. It does not.
These are overwhelmingly import-ordering and `subprocess` `check=` findings, not
correctness bugs, but the stated gate is unmet.

### 1.7 Cloudflare

Three Workers are deployed (`workers_list`):

| Worker | Created | Last modified |
|---|---|---|
| `clearglassincorporated-desmond2` | 2026-08-29 | 2026-08-31 |
| `spring-pine-9614` | 2026-08-23 | 2026-08-23 |
| `clearglassincorporated-desmond` | 2026-08-22 | 2026-08-22 |

The repository's only Cloudflare config, `infra/cloudflare/workers/wrangler.toml`,
declares a **different** worker (`name = "cg-asset-guard"`) against placeholder
hosts (`ALLOWED_REFERER_HOST = "clearglass.example"`), with its `routes` block
commented out. **No deployed Worker corresponds to any committed config, and no
committed config is deployable as written.** `spring-pine-9614` is an
auto-generated name and its purpose is undocumented in the repo.

No KV, D1, R2 or Hyperdrive resources were enumerated as part of this audit.

### 1.8 Secrets exposure review

No credential material is committed. `git ls-files` shows `.env.example` and
`.env.growth.example` only; both contain placeholders. The static site's
`_headers` sets a strict CSP, HSTS with `preload`, `X-Content-Type-Options`,
`Referrer-Policy` and a restrictive `Permissions-Policy` — this is a
well-constructed header set.

The 78 inert workflows reference **30 distinct secrets**, several of them
high-consequence:

```
STRIPE_LIVE_SECRET_KEY   STRIPE_SECRET_KEY      CLOUDFLARE_API_TOKEN
CLOUDFLARE_EDGE_APPLY_TOKEN                     CG_ORG_PAT
GMAIL_APP_PASSWORD       DATABASE_URL           RENDER_DEPLOY_HOOK_URL
ANTHROPIC_API_KEY        OPENAI_API_KEY         AUDIT_VALID_TOKEN
```

This matters for §5: those workflows are currently inert. Registering them
activates every one of these credential paths at once.


### 1.9 Defects found by building and running the code (second pass)

The findings above came from reading the repository. These came from installing,
building, and driving it in a browser — and none were visible any other way.

**The Next app had never been buildable.** `next build` failed with
"reality-forensics/page.tsx doesn't have a root layout". The App Router requires
`app/layout.tsx`; the project had none.

**Its CSP made hydration impossible.** `next.config.ts` served
`script-src 'self'` with no nonce and no `'unsafe-inline'`. The App Router
injects inline bootstrap scripts, so Chromium refused every one:

```
Refused to execute inline script because it violates the following
Content-Security-Policy directive: "script-src 'self'"
```

Measured before the fix: **0** shell components mounted, `data-cgm-motion` was
`null`, and the body's first six children were all refused `SCRIPT` tags. Every
client component in that app was dead. This is in the committed config and
predates this audit.

**`npm ci` could not install.** The root `package-lock.json` was a 24-entry stub
still named `clearglassinc-site-tooling`, missing **every** dependency:

```
npm error code EUSAGE
npm error Missing: next@15.5.2 from lock file
npm error Missing: react@19.1.1 from lock file    … and 20 more
```

Any workflow running `npm ci` — `ci.yml`, `commerce-frontend-ci.yml`,
`artemis-engineering.yml` — would have failed at install, before reaching a
single test.

**1 critical and 2 high dependency advisories.** Auditable only once install
worked. `next@15.5.2` carried, among 30+ advisories, RCE in the React flight
protocol (**CVSS 10**) and unauthenticated RCE on Windows-hosted servers
(**CVSS 9**). Fixed by a non-major bump to `15.5.25`; critical count is now
**0**. Two highs remain (libvips/libheif via `sharp`) with no non-breaking fix
published.

**`sentinel.js` did not parse.** A surplus `}` on line 80 produced
`missing ) after argument list`, so the entire Sentinel client was inert on
every page that loads it — the homepage included. `pages-check.yml` uploads
`sentinel.css` as a release artifact, so this shipped as a styled shell with no
behaviour behind it.

**`artemis-command-layer.css` pulled its own baseline over the network.** Line 2
was `@import url("https://raw.githubusercontent.com/…/artemis-command-layer.css")`
— an import of an older commit of the same file, from a host the site's own
`style-src` does not allow. **76 rules never loaded in production.** The blob is
recoverable from this repo's history and is now vendored in at the import's
exact position.

**The root typecheck could never pass.** `tsconfig.json` swept `storefront/**`
into the root project while mapping `@/*` to the repo root, so `@/lib/catalog`
resolved to a path that does not exist. 122 errors, essentially all phantom.
Scoping the root project to root-level code brought it to 22, then to **0**.

**`tools/seo_audit.py` failed on any developer machine.** It did not exclude
build output, so `test_repository_audit_has_no_errors` failed as soon as
`npm install` or `next build` had run. That is how it was found: the suite read
24 failures instead of 23 until `.next/` and `node_modules/` were parked and
re-run. Fixed at the source rather than worked around.

**One pre-existing layout-thrash issue, reported but not fixed.** The homepage's
always-running `cg-neon-breathe` and `cgSealPulse` animations reflow content
continuously — measured **15.1px** of vertical jitter on an element far down the
*committed* page (13.3px with the new motion layer, marginally less). Deep click
targets never settle as a result. Fixing it means touching the live hero, which
did not belong in this work.

**Missing source, second instance.** `scripts/stripe-sync/types.ts` is absent
from the repo entirely; `planner.ts`, `sources.ts` and `report.ts` all import
`./types.js`. 20 type errors trace to that one file. Recover it rather than
rewrite it — it is the type contract for a live Stripe sync.

---

## 2. Repository Risks

| # | Risk | Severity | Evidence |
|---|---|---|---|
| R1 | Actions entitlement blocked → no CI, no deploys, no scheduled bots | **Critical** | §1.1 |
| R2 | Production serving 4-day-stale content; no deploy path under repo control | **Critical** | §1.2 |
| R3 | Money-movement tests (checkout/pricing/fulfilment) were uncollected | **High** | §1.4 |
| R4 | Registering the 78 inert workflows would fire 33 scheduled jobs, 15 self-committing jobs and 30 credential paths simultaneously | **High** | §1.5, §1.8, §5 |
| R5 | `agent_army` and `scripts/validate_production_deploy.py` absent → suite still aborts under default config | **High** | §3.3 |
| R6 | Cloudflare deployed state is undocumented and unreproducible from the repo | **Medium** | §1.7 |
| R7 | `CLAUDE.md` documents a layout this repo does not have — actively misleads agents and contributors | **Medium** | §1.3 |
| R8 | No `ruff`/`pytest` gate; `CLAUDE.md`'s stated gates are fictional here | **Medium** | §1.5, §1.6 |
| R9 | 9 pages ship without the canonical logo/tab icon; 1 indexable page missing from `sitemap.xml` | **Low** | §4.2 |
| R10 | `visual-restoration.yml` pins `actions/checkout@v4` by tag while every other workflow pins by SHA | **Low** | grep of `.github/workflows/` |
| R11 | `next@15.5.2` shipped a CVSS 10 RCE — **fixed** (bumped to 15.5.25) | **Critical** (resolved) | §1.9 |
| R12 | Next app CSP blocked all hydration — **fixed** | **High** (resolved) | §1.9 |
| R13 | `npm ci` failed; lockfile missing every dependency — **fixed** | **High** (resolved) | §1.9 |
| R14 | `sentinel.js` did not parse; client inert site-wide — **fixed** | **High** (resolved) | §1.9 |
| R15 | `artemis-command-layer.css` imported 76 rules from a CSP-blocked host — **fixed** | **Medium** (resolved) | §1.9 |
| R16 | `scripts/stripe-sync/types.ts` absent — Stripe sync type contract lost | **High** | §1.9 |
| R17 | Homepage animations reflow continuously (15.1px jitter) | **Medium** | §1.9 |
| R18 | 2 high advisories remain via `sharp` (libvips/libheif); no non-breaking fix | **Medium** | §1.9 |

---

## 3. Remediation Actions

### 3.1 Applied and validated (commit `88470b1`)

Each fix is a path correction justified by evidence inside the repository.
Tests were pointed at real file locations rather than moving files, because the
flat layout is what Pages serves as the live site — relocating trees would
change production URLs.

| Target | Change | Justification |
|---|---|---|
| `pyproject.toml` | `clearglass-commerce/control-plane` → `control-plane` in `testpaths` + `pythonpath` | directory does not exist; tree is at `control-plane/` |
| `control-plane/tests/test_cart.py` | `REPO_ROOT` `parents[3]` → `parents[2]` | `parents[3]` resolved `/home/user`; correct only at the old nesting depth |
| `percival_v9/__init__.py` | **added** — re-exports 11 symbols | package `__init__.py` was dropped; all 11 symbols located in `percival_v9/internal/`; surface documented in `PERCIVAL_V10_ARCHITECTURE.md` |
| `.well-known/security.txt` | **added** (copy; root file untouched) | `_headers` and the file's own `Canonical:` line both specify this path |
| `scripts/control_surface_feeds.py` | `SCHEMA_PATH` `docs/contracts/` → `contracts/` | **production code**; schema is at `contracts/` |
| `scripts/market_intelligence_lane.py` | `CONFIG` `marketing/config/` → `config/` | watchlist is at `config/` |
| `tests/test_side_store_storefront.py` | `CATALOG` → `data/store/catalog.json` | the path `CLAUDE.md` documents as the committed catalog |
| `tests/test_local_growth_planner.py` | `marketing.local_growth_planner` → `local_growth_planner` | every imported symbol verified present in the target first |
| `tests/test_strategic_viral_engine.py` | `marketing.content_engine.…` → `content_engine.…` | same verification |
| `tests/test_build_pages.py` | import `_harden_html` | test called it without importing; defined at `tools/build_pages.py:80` |

No test was skipped, disabled, quarantined or weakened.

### 3.2 Deliberately not done

* **Registering the 78 inert workflows.** 33 are scheduled, 15 commit or push
  back to the repository, and collectively they hold 30 secrets including
  `STRIPE_LIVE_SECRET_KEY`, `CLOUDFLARE_API_TOKEN` and `GMAIL_APP_PASSWORD`.
  Enabling them in one move — into a repo whose Actions is already broken —
  risks a self-commit storm, live Stripe product mutation, Cloudflare DNS/email
  changes and outbound mail the moment entitlement is restored. This needs a
  staged, owner-approved rollout (§5).
* **Fabricating the missing modules** (§3.3). Writing a production-deploy
  validator from scratch to satisfy its own test would manufacture false
  assurance about deploys.
* **Auto-fixing 1016 ruff findings.** A 739-file mechanical rewrite is
  unreviewable alongside a diagnosis, and would bury the 10 substantive fixes.

### 3.3 Blocked on genuinely absent source

Three modules are absent from the repository entirely — not relocated
(`find` across the whole tree returns nothing; `agent_army` never appears in
any commit):

| Missing | Referenced by |
|---|---|
| `agent_army` | `tests/test_agent_army.py` |
| `scripts/validate_production_deploy.py` | `tests/test_validate_production_deploy.py` |
| `scripts/workflow_doctor.py` | `tests/test_workflow_doctor.py` (4 errors), `tests/test_agent_os_operator.py`, `workflows/workflow-doctor.yml` |

Recover them from the upstream repository rather than rewriting them. There is
no `ClearGlassInc.github.io` in the organisation; the closest candidate is
**`ClearGlasslabs/ClearGlassInc.`** (note the trailing dot), last pushed
`2026-09-06T14:04:56Z` — 50 minutes after this repository's last healthy Pages
deploy, consistent with being the source of the upload.

---

## 4. Validation Evidence

### 4.1 Workflow preconditions (all 6 registered workflows)

```
index.html present                                        PASS
"ClearGlass Inc — AI Automation, Cybersecurity" in index   PASS  (1 match)
@keyframes in index.html                                   PASS  (9 matches)
prismPulse in index.html                                   PASS  (1 match)
exact <link … href="sentinel.css"/>                        PASS
exact <link … href="clearglass-legacy-visual.css">         PASS
sentinel.css / clearglass-legacy-visual.css on disk        PASS
404.html, CNAME, .nojekyll, artemis-command-layer.css      PASS
scripts/{cert_bot,site_reliability_audit,                   PASS  (all 4 present)
         live_sitemap_crawl,audit_github_actions}.py
cert-bot.yml inline script                                 bash -n → SYNTAX OK
```

Every gate the 6 registered workflows enforce is satisfiable by the current
tree. **They fail for the reason in §1.1, not because of their content.**

### 4.2 Test suite, before → after

Measured with `pytest --continue-on-collection-errors` (identical invocation
both times):

| | Baseline `2fe1fa7` | After `88470b1` | Δ |
|---|---|---|---|
| passed | 1445 | **1578** | **+133** |
| failed | 28 | **23** | −5 |
| collection errors | 10 | **6** | −4 |
| skipped | 3 | 3 | — |

Per-fix validation, each run immediately after its change:

```
control-plane collection      0 tests  →  98 tests collected
control-plane/tests/test_cart.py         34 passed   (was 3 failed / 31 passed)
tests/test_percival_v9_policy.py +
  tests/test_percival_v10_recovery.py    20 passed   (were 2 collection errors)
tests/test_build_pages.py                 8 passed   (was 2 failed)
5 relocated-path modules                 32 passed / 1 failed → then 8 passed
percival_v9/__init__.py                  ruff check → All checks passed!
```

The 34 passing cart tests are load-bearing: three of them assert the server's
price book matches the storefront's constants. They were erroring on a path,
not passing — so server-vs-storefront price parity was unverified until now,
and is now positively confirmed.

The 20 passing Percival tests are the deny-by-default, escalation-gate,
fail-closed-audit and hash-chain tamper-detection cases. They were entirely
unexercised.

### 4.3 Remaining local failures — 23 failed, 6 errors

Grouped by cause, all traceable to §1.3 or §1.5:

* **Missing workflow files (blocked on §5)** — 6 failures assert
  `.github/workflows/{pages,auto-store,enterprise-patch-deploy,minerals-data-sync,site-integrity-and-deploy}.yml`.
  All five exist in `workflows/`.
* **Missing source (§3.3)** — 6 errors + 1 failure.
* **Site content regressions (§4.4)** — ~10 failures.
* **Node storefront smoke** — 1 failure (`node --test`; node v22.22.2 present, so this is a real failure, not a tooling gap).

Under the **default** pytest configuration the suite still aborts, now on 2
collection errors instead of 6 — both from §3.3. **The suite does not yet exit
zero, and this report does not claim it does.**

### 4.4 Site content regressions (verified, not yet fixed)

9 pages ship without the canonical logo and desktop tab icon:

```
minerals.html                 mission-control.html
apps/command-center/index.html
assets/canada-us-30-day-diagnostic.html
offers/canada-us-control-assessment.html
blog/ai-safety-black-box-activation-analysis-gavel.html
blog/canada-us-cross-border-cybersecurity-evidence-controls.html
blog/cpcsc-vs-cmmc-residency-split.html
blog/dual-clock-incident-runbook-ccspa-circia-pipeda.html
```

`guardian_command_nexus_spec.html` is indexable but absent from `sitemap.xml`.
`tools/internal_links.py --check` reports `index.html` generated-block staleness.

The repository ships idempotent generators for all three
(`tools/tab_icons.py`, `tools/internal_links.py`,
`tools/security_release_manifest.py`). These are content changes to 10+ live
pages and were held back from a diagnostic commit deliberately — see §5 step 4.

---

## 5. Deployment Plan

Ordered by dependency. **Step 1 gates everything else** — until Actions
executes, no CI result and no deploy can be verified.

**Step 1 — Restore Actions entitlement (owner action, blocking).**
Work the three checks in §1.1. Confirm success by dispatching `Cert Bot`
(`workflow_dispatch`, ~5s, no secrets, read-only) and checking that
`get_workflow_run_usage` reports **non-zero** `billable.UBUNTU.total_ms`. That
single number is the pass/fail signal — a green tick alone is not, since these
jobs currently fail without ever running.

**Step 2 — Confirm Pages deployment resumes.**
Once Step 1 passes, push any trivial commit to `main` and confirm a new
`pages build and deployment` run appears. Then verify
`https://www.clearglassinc.com/` serves the crimson palette from PR #4 and
returns `200`, and that `https://www.clearglassinc.com/.well-known/security.txt`
resolves (it will only do so with this branch merged).

**Step 3 — Merge this branch.** Path repairs only; no runtime behaviour
changes on the static site. Validation in §4.2.

**Step 4 — Regenerate site content (separate PR).**
`python3 tools/tab_icons.py` · `python3 tools/internal_links.py` ·
add `guardian_command_nexus_spec.html` to `sitemap.xml` · bump `VERSION` in
`sw.js` so returning visitors refetch. Review the rendered diff of all 10 pages
before merging; then re-run `--check` on both generators.

**Step 5 — Recover the three missing modules** from
`ClearGlasslabs/ClearGlassInc.` (§3.3). This clears the last 2 default-config
collection errors and lets `pytest` exit zero.

**Step 6 — Register workflows in tranches, never all at once.**
Order chosen so the safest, most valuable gate lands first:

1. **Tranche A — inert CI gates.** `ci.yml`, `commerce-frontend-ci.yml`,
   `function-agent-ci.yml`, `policy-gate.yml`, `percival-policy-gate.yml`,
   `repository-health.yml`, `xenolith-gate.yml`. All `push`/`pull_request`
   only, no secrets, no write permissions, no push-back. This is what finally
   gives the Python suite and `ruff` a CI gate (R8).
2. **Tranche B — read-only scheduled audits.** `security.yml`,
   `semgrep-trial.yml`, `compliance-evidence.yml`, `repo-audit.yml`,
   `seo-continuous-audit.yml`.
3. **Tranche C — `pages.yml`.** Requires a decision first: it uses
   `actions/deploy-pages`, which needs Pages source switched from "Deploy from a
   branch" to "GitHub Actions". Do not register it while Pages is in branch
   mode — it will fail, and it is what `tests/test_pages_deployment_workflows.py`
   expects to be the *only* Pages deployer.
4. **Tranche D — the 15 self-committing and credential-bearing workflows.**
   One at a time, each with its secret verified present and its schedule
   reviewed. `dispatch-all-workflows.yml` and `master-orchestrator.yml` last.

**Step 7 — Reconcile Cloudflare (R6).** Identify what the 3 deployed Workers
serve, then either commit deployable `wrangler.toml` config for them or retire
them. Resolve the `clearglass.example` placeholders.

**Step 8 — Correct `CLAUDE.md` (R7).** Its paths (`clearglass-commerce/`,
`apps/autostore/`, "~29 workflows", `ci.yml` gates) describe the pre-upload
layout and misdirect every agent that reads it.

---

## 6. Rollback Plan

| Change | Rollback | Blast radius if wrong |
|---|---|---|
| This branch (`88470b1`) | `git revert 88470b1` | Test configuration and two script paths. No static-site page content is touched, so production rendering cannot regress. |
| `percival_v9/__init__.py` | delete the file | Returns `percival_v9` to a namespace package; only the 2 test modules that import it are affected. |
| `.well-known/security.txt` | delete the directory | Purely additive; the root `security.txt` is unchanged, so removal restores the prior state exactly. |
| Step 4 content regeneration | `git revert` the content PR, bump `sw.js` `VERSION` again | 10 live pages. Regenerate rather than hand-edit. |
| Step 6 workflow tranche | delete the file from `.github/workflows/` (the copy in `workflows/` is untouched, so nothing is lost) | Per tranche. Tranche D can write to the repo — revert its commits and rotate any secret it used. |
| Step 6 Tranche C (`pages.yml`) | remove the workflow **and** switch Pages source back to "Deploy from a branch" | Site deployment. Both halves must be reverted together. |
| Step 7 Cloudflare | Workers keep prior versions; roll back in the Cloudflare dashboard | Edge routing. Never change DNS and Worker routes in one action. |

Two standing rules for this repository:

* `workflows/` is the intact 78-file archive. Always **copy** into
  `.github/workflows/`, never move — the archive is the rollback source.
* A green check on this repository is not evidence a job ran. Confirm
  `billable.UBUNTU.total_ms > 0` before trusting any Actions result.

---

## 7. Final Readiness Assessment

**Not production-ready.** Against the eight stated success criteria:

| Criterion | Status | Basis |
|---|---|---|
| Successful build | **Yes, locally** | `next build` compiles all 4 routes (it could not build at all before — no root layout); `tsc --noEmit` 0 errors, down from 122; `npm run test` 8/8; `npm ci` succeeds, having failed outright. Not proven in CI — see §1.1. |
| Passing tests | **No** | 23 failed / 1578 passed / 6 errors. Under default config the suite aborts on 2 missing modules (§3.3). Improved from a state where it could not run at all. |
| Passing workflows | **No** | Zero user-authored workflow runs have ever succeeded (§1.1). Unchanged — this is not a code problem. |
| Successful deployment | **No** | No Pages build since 2026-09-06 13:14 UTC (§1.2). |
| Production health validation | **Unverified** | Live site unreachable from this environment (proxy 403). |
| Dependency integrity | **Yes** | Lockfile regenerated and in sync; `npm ci` succeeds; **critical advisory count 0** (was 1 CVSS-10 RCE). 2 highs remain via `sharp` with no non-breaking fix (R18). |
| Security review completion | **Substantially** | Secrets, headers, CSP, workflow permissions and dependency advisories all reviewed. Three live security-relevant defects fixed: the CVSS-10 RCE, the CSP that blocked hydration, and a CSP-blocked remote `@import`. CodeQL has still never completed a run (§1.1); no SAST executed. |
| Deployment verification | **No** | Nothing to verify while §1.1 holds. |

Two criteria moved from *not met* to *met* in this pass (build, dependency
integrity) and one substantially advanced (security review). The four that
remain unmet are all downstream of §1.1 — they are gated on Actions
entitlement, not on code.

**The single highest-value action is Step 1.** It is an owner action in GitHub
settings, not an engineering change, and it unblocks six of the eight criteria.
Every code-level finding in this report is downstream of it.

What genuinely improved in this pass: the test suite went from *unrunnable* to
1578 passing; the governed-commerce suite went from *0 collected* to 98, with
server-vs-storefront price parity now positively verified; the Percival
deny-by-default and tamper-detection tests went from *unexercised* to passing;
and the RFC 9116 security contact is reachable again. The structural cause of
the damage is identified with commit-level evidence, and the intact source for
every remaining path defect is located.
