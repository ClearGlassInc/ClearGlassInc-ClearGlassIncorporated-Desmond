# PRODUCTION-RECOVERY.md

Audit window: 2026-09-10 20:23–20:30 UTC  
Auditor: independent GitHub + live-edge pass (no assumed facts)  
Requested URL: `https://github.com/ClearGlassInc/ClearGlassIncorporated-Desmond`  
Audited production repository: `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond`  
Default branch / HEAD at audit start: `main` @ `69373f9b44916569a1f3fe3424be323d05dbf9d6`  
HEAD commit: `Merge pull request #7 from ClearGlassInc/claude/clearglass-production-recovery-qwyrne` (2026-09-10T17:28:34Z)

**Final readiness: NOT PRODUCTION-READY.**  
Successful static homepage is live. CI, user workflows, Pages rebuilds after 2026-09-06, and backend health checks are not verified green.

Every claim below is tagged with the observation that produced it. Anything not observed is marked **UNVERIFIED**.

---

## 0. Scope correction (must be read first)

| Check | Result | Evidence |
|---|---|---|
| Requested repo URL | **HTTP 404** | `GET https://github.com/ClearGlassInc/ClearGlassIncorporated-Desmond` → “Page not found”; GitHub API `GET /repos/ClearGlassInc/ClearGlassIncorporated-Desmond` → 404 |
| Org public repo that matches the name + has Pages + admin on this token | `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond` | GitHub repo search; `permissions.admin=true`; `has_pages=true`; `pushed_at=2026-09-10T17:28:34Z` |
| Name-collision copy | `connectors-testing-pplx/ClearGlassIncorporated-Desmond` | Public search hit; `permissions.pull=true` only; `has_pages=false`; last push 2026-09-07. **Not used as the production target.** |
| Authenticated GitHub actor | `ClearGlasslabs` (id 77194670) | `github___get_me` |

This audit proceeds against the org repository that exists and that this account can write. It does **not** treat the 404 URL as a live codebase.

Prior recovery work already exists in-tree: `PRODUCTION-RECOVERY.md` on `main` (blob SHA `f5f39dd…`), produced on branch `claude/clearglass-production-recovery-qwyrne` and merged via PR #7. This file is an independent re-verification against HEAD plus live HTTP/DNS, not a copy of that document.

---

## 1. Verified Findings

### 1.1 Repository identity

| Field | Observed value | Source |
|---|---|---|
| full_name | `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond` | repo search object |
| visibility | public | same |
| default_branch | `main` | same |
| language | HTML | same |
| has_pages | true | same |
| has_issues | true | same |
| is_template | true | same |
| releases | **none** | `list_releases` → `[]` |
| open issues | 0 | search object `open_issues_count=0` |
| repo security advisories | **none listed** | `list_repository_security_advisories` → `[]` |
| CNAME | `www.clearglassinc.com` | file `CNAME` on `69373f9` |
| `.nojekyll` | present (1 byte) | root listing |
| branches | `main`, `backup/pre-legacy-visual-2026-09-08`, 4 `claude/*` / `copilot/*` / `code-coverage-agent/*` branches | `list_branches` (8 total); **none protected** |

`main` is not branch-protected. That is an operational risk, not a build failure.

### 1.2 Live website (verified 2026-09-10 20:25 UTC)

| Probe | Result |
|---|---|
| `https://www.clearglassinc.com/` | HTTP/2 **200**; `server: GitHub.com`; `content-type: text/html`; `last-modified: Sun, 06 Sep 2026 13:15:18 GMT`; body length 191232 |
| `https://clearglassinc.com/` | HTTP/2 **301** → `https://www.clearglassinc.com/` |
| `https://clearglassinc.github.io/ClearGlassInc-ClearGlassIncorporated-Desmond/` | HTTP/2 **301** → `https://www.clearglassinc.com/` |
| DNS `www.clearglassinc.com` / `clearglassinc.com` | `185.199.108–111.153` = **GitHub Pages** (`clearglassinc.github.io`) |
| TLS | Let’s Encrypt `YR2`; `CN=clearglassinc.com`; `notBefore=2026-07-13`; `notAfter=2026-10-11` (~31 days remaining at audit time) |
| Page title / H1 | `ClearGlass Inc — AI Automation, Cybersecurity & Operational Strategy` |
| `robots.txt` | HTTP 200, last-modified 2026-09-06 13:15:18 GMT |
| `sitemap.xml` | HTTP 200, same last-modified |
| `/.well-known/security.txt` | HTTP **404** |
| `/health` | HTTP **404** (static Pages origin; no application health endpoint on this host) |

Conclusion: the public site is a **GitHub Pages static origin** with a custom domain. It is **up**. It is also **stale relative to `main`**.

The `Last-Modified` header (2026-09-06 13:15:18 GMT) matches the last successful Pages workflow run (§1.3) to the second. Commits merged on 2026-09-10 (PRs #4, #5, #6, #7), including `.well-known/security.txt` now present on `main`, are **not** on the live edge.

Cloudflare is **not** the public DNS/edge for this hostname. A Cloudflare Pages/Workers/KV/D1 review of the *live hostname* therefore cannot be completed from DNS: the A/ALIAS answers are GitHub Pages IPs. Repo-side Cloudflare config is covered in §1.7.

### 1.3 GitHub Pages deploy mechanism

Registered workflow:

- Name: `pages-build-deployment`
- Path: `dynamic/pages/pages-build-deployment` (GitHub-managed, not a file under `.github/workflows/`)
- ID: `351526813`
- State: `active`

Latest runs (`actions_list` on workflow id `351526813`):

| Run | Created | Conclusion | HEAD SHA | Commit message |
|---|---|---|---|---|
| 51 / `34035508995` | 2026-09-06T13:14:52Z | **success** | `1fa058e` | Add files via upload |
| 50 | 2026-09-06T13:13:32Z | success | `84acff1` | Add files via upload |
| …runs 42–49… | 2026-09-06 | success | various | Add files via upload |

No `pages-build-deployment` run exists after 2026-09-06T13:14:52Z. `main` is now `69373f9` (2026-09-10T17:28:34Z). Pages is configured as **Deploy from a branch** (no `actions/deploy-pages` workflow in `.github/workflows/`). When that builder stops creating runs, the custom domain keeps serving the last successful artifact.

### 1.4 User-authored Actions do not execute

`.github/workflows/` contains **6** files. All 6 plus 6 GitHub-managed/dynamic workflows report `state: active` (`list_workflows`, total_count=12).

Registered user workflows:

| Workflow | File | Triggers |
|---|---|---|
| ARTEMIS Engineering CI | `artemis-engineering.yml` | push/PR on `apps/artemis-engineering/**`, dispatch |
| Auto Heal | `auto-heal.yml` | cron `17 4 * * *`, dispatch |
| Cert Bot | `cert-bot.yml` | cron `17 6 * * *`, dispatch |
| ClearGlass GitHub Pages Check | `pages-check.yml` | push `main`, dispatch |
| Site Reliability Audit | `site-reliability.yml` | push/PR path filters, weekly cron, dispatch |
| Apply ClearGlass visual restoration layer | `visual-restoration.yml` | push `main`, dispatch |

Latest `main` push (`69373f9`, 2026-09-10T17:28:37Z) produced:

| Run | Workflow | Conclusion | Duration |
|---|---|---|---|
| `34508447415` | Pages Check | **failure** | ~5s |
| `34508447340` | Visual restoration | **failure** | ~5s |
| `34508447416` | Site Reliability Audit | **failure** | ~4s |

Job `102976294854` (`validate-site` on run `34508447415`):

```
status        : completed
conclusion    : failure
runner_id     : 0
runner_name   : ""
started_at    : 2026-09-10T17:28:38Z
completed_at  : 2026-09-10T17:28:41Z
steps         : absent from the job payload
```

That is a **pre-runner failure**. The job was never assigned a GitHub-hosted runner, so YAML body, `index.html` markers, and action SHAs were never evaluated on this run. The same ~4–5 second signature repeats across Pages Check, Site Reliability, and Visual Restoration on every `main` push observed on 2026-09-10.

Dependabot’s managed `Graph Update: pip` run `34498916171` (2026-09-10T15:56:31Z) concluded **success**. GitHub-managed jobs can still complete. User-authored `runs-on: ubuntu-latest` jobs on this repository currently cannot.

**UNVERIFIED (org settings, not readable here):** billing hold, Actions policy, allowed-actions list, or spending limit. Those pages are outside the connected GitHub tools. They are the remaining consistent explanation after YAML and public-repo minute quotas are ruled out as *sufficient* causes.

### 1.5 Seventy-eight workflows are inert

Directory `workflows/` (repo root, **not** `.github/workflows/`) contains **78** YAML files, including `ci.yml`, `pages.yml`, `commerce-deploy.yml`, `auto-store.yml`, `workflow-doctor.yml`, `site-integrity-and-deploy.yml`. GitHub Actions only loads `.github/workflows/*`. Those 78 files are documentation/source copies, not registered workflows.

They must **not** be bulk-copied into `.github/workflows/`. Several are scheduled, several write back to the repo, and they reference high-consequence secret names (see §1.8). Registering them while runner provisioning is already failing would multiply failed runs and, if entitlement returns, could fire Stripe/Cloudflare/Gmail side effects.

### 1.6 Architecture / package / deployment maps (observed tree only)

**Architecture (what this repo actually is on `main`)**

```
Public edge          GitHub Pages (www.clearglassinc.com) ← CNAME + .nojekyll + root HTML/CSS/JS
Optional Next fabric root package.json (@clearglass/live-signal-fabric, next 15.5.25) — not what Pages serves as the homepage
Commerce             control-plane/ (FastAPI, Docker) + storefront/ + admin/
Other apps           apps/artemis-engineering/, clearglass-agentops/, clearglass-air-control/, procurement-legal-tech/
Orchestration docs   percival_v9/, ARTEMIS_*.md, DEPLOY.md
Inert CI copies      workflows/ (78 files)
Live CI              .github/workflows/ (6 files) — registered, not executing
```

**Package map (package.json files found by code search)**

| Path | Role implied by path |
|---|---|
| `/package.json` | `@clearglass/live-signal-fabric` — Next 15.5.25, React 19.1.1, scripts: dev/build/start/typecheck/test |
| `admin/package.json` | commerce admin |
| `storefront/package.json` | commerce storefront |
| `clearglass-agentops/package.json` | agent ops app |
| `clearglass-air-control/package.json` | air-control app |
| `procurement-legal-tech/package.json` | legal-tech app |
| `apps/artemis-engineering/package.json` | Artemis engineering CI target |

**Container map (Dockerfiles found by code search)**

`admin/Dockerfile`, `storefront/Dockerfile`, `control-plane/Dockerfile`, `deployment/artemis/Dockerfile`, `percival_v9/deploy/Dockerfile.governor`, `services/clearglass_agent_service/Dockerfile`

No evidence was collected that any of those images are built or published in this repository’s Actions history. **No GitHub Releases exist.**

**Deployment map**

| Target | Status |
|---|---|
| GitHub Pages + `www.clearglassinc.com` | Live, stale (last build 2026-09-06) |
| `github-pages` environment | **UNVERIFIED** (no environments list tool returned data this pass) |
| `production` / `staging` / `automation-write` named environments | **UNVERIFIED** — names appear in the operator directive, not in any file read this pass |
| Render blueprint (`DEPLOY.md` + `render.yaml` referenced) | Documented only. Live `/health` on the public hostname is 404. |
| Fly.io / docker-compose | Documented in `DEPLOY.md` only |

### 1.7 Cloudflare review (repo + DNS only)

Repo file `infra/cloudflare/workers/wrangler.toml`:

- Worker name: `cg-asset-guard`
- Routes: **commented out**
- `ALLOWED_REFERER_HOST = "clearglass.example"` (placeholder)
- Secret `ASSET_SIGNING_SECRET` instructed to be set out of band

Live DNS for `clearglassinc.com` / `www` is GitHub Pages, not a Cloudflare anycast prefix. Therefore:

- Pages / Workers / KV / D1 / SSL / redirects **in front of the public site** are **not observed**
- Prior audit text that listed three deployed Workers (`clearglassincorporated-desmond`, `clearglassincorporated-desmond2`, `spring-pine-9614`) is **not re-verified in this pass** (no Cloudflare account connector). Treat as **UNVERIFIED** until an authenticated `wrangler`/`Cloudflare API` listing is produced.

A PDF named `Cloudflare Domain Name Certificate.pdf` exists at repo root. Presence of a file is not proof of current DNS.

### 1.8 Secrets and credentials

Observed committed env templates:

- `.env.example` — feature flags default **fail-closed** (`LIVE_FABRIC_ENABLED=false`, `LIVE_FABRIC_PRODUCTION_APPROVED=false`); empty `DATABASE_URL`, `REDIS_URL`, snapshot token
- `.env.growth.example` — present (287 bytes); not re-opened this pass

No raw secret values were read out of git objects in this pass. `github___run_secret_scanning` was not pointed at the whole tree (tool requires file contents, not a repo crawl).

Secret **names** referenced by inert `workflows/*` and `DEPLOY.md` (names only):

`STRIPE_SECRET_KEY`, `STRIPE_LIVE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY`, `CLOUDFLARE_API_TOKEN`, `RENDER_DEPLOY_HOOK_URL`, `GMAIL_APP_PASSWORD`, `GMAIL_USER`, `DATABASE_URL`, `ADMIN_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, plus others listed in the prior in-repo audit.

Whether those GitHub Actions secrets actually exist in repo settings is **UNVERIFIED**.

### 1.9 Static analysis / tests / build (this pass)

This pass did **not** clone the full working tree and re-run `pytest`, `ruff`, or `next build`. Those numbers in the already-merged `PRODUCTION-RECOVERY.md` are **prior-audit claims**, not re-measured here.

Independently verified now:

| Item | Status |
|---|---|
| Root `package.json` pins `next@15.5.25` (not 15.5.2) | file on `69373f9` |
| Live homepage H1 matches `pages-check.yml` required string | live title + workflow YAML |
| `.well-known/security.txt` exists on `main` | directory listing |
| Same path 404s in production | live HTTP |
| `DEPLOY.md` documents `/health` and `/ready` on a Render/FastAPI control plane | file; those paths 404 on the public Pages host |
| User workflow YAML is syntactically present and least-privilege (`contents: read`) | six files read in full |

### 1.10 Security review (what can be stated)

| Control | Observation |
|---|---|
| Exposed secrets in files read | None in `CNAME`, six workflows, `.env.example`, `wrangler.toml`, `package.json`, `DEPLOY.md` |
| Insecure workflow permissions (registered set) | All six use `contents: read` (auto-heal also `actions: read`). No `pull-requests: write` / `contents: write` on the registered set. |
| `visual-restoration.yml` pinned `actions/checkout@v4` by **tag**; the other five pin checkout `df4cb1c…` (v6.0.3) by SHA | file contents; pin applied on this recovery branch |
| XSS / SSRF / CSRF / RCE / privilege escalation | **Not claimed scanned.** No CodeQL run results were fetched this pass beyond noting dynamic CodeQL workflows exist and are `active`. |
| Public repo advisories | empty list |
| Live TLS | valid Let’s Encrypt; expires 2026-10-11 |
| Live security.txt | missing on edge (404) even though present on `main` |
| Dependabot | graph-update workflow succeeded 2026-09-10 |

---

## 2. Repository Risks

| ID | Risk | Severity | Evidence |
|---|---|---|---|
| R1 | Requested canonical URL 404s; two similarly named repos exist | High | §0 |
| R2 | User Actions jobs never reach a runner | **Critical** | §1.4 |
| R3 | Pages builder has not run since 2026-09-06; production HTML is stale | **Critical** | §1.2, §1.3 |
| R4 | `main` is unprotected | High | `list_branches` `protected:false` |
| R5 | 78 inert workflows would activate secrets + schedules if copied blindly | High | §1.5, §1.8 |
| R6 | Public hostname has no `/health`; commerce health lives only in docs | Medium | live 404 vs `DEPLOY.md` |
| R7 | Cloudflare config in repo does not match live DNS | Medium | §1.7 |
| R8 | TLS expires 2026-10-11; cert-bot workflow cannot run while runners are blocked | Medium | cert dates + §1.4 |
| R9 | Duplicate public copy under `connectors-testing-pplx/` | Low | repo search |
| R10 | Checkout tag pin on `visual-restoration.yml` | Low | YAML; remediated on this branch |
| R11 | Environments named in the operator directive were not observed | Medium | UNVERIFIED |
| R12 | Test/lint/build gates described in `CLAUDE.md` / prior audit are not executing in Actions | High | §1.4, §1.9 |

---

## 3. Remediation Actions

### 3.1 Applied in this pass

| Change | Why it is safe | Validation |
|---|---|---|
| Rewrite `PRODUCTION-RECOVERY.md` with independently observed evidence, including the live-site probe the prior file marked UNVERIFIED | Documentation only | File content traces to API + `curl -sI` + DNS |
| Pin `actions/checkout` in `visual-restoration.yml` to SHA `df4cb1c069e1874edd31b4311f1884172cec0e10` (same as the other five workflows) | No behavior change intended; removes mutable tag | YAML diff only. **Cannot be proven green in Actions until R2 is cleared.** |

### 3.2 Deliberately not done

- Did not invent `ClearGlassInc/ClearGlassIncorporated-Desmond`.
- Did not copy `workflows/*` into `.github/workflows/`.
- Did not push a Pages rebuild that GitHub is not creating.
- Did not fabricate passing `pytest` / `ruff` / `next build` numbers.
- Did not rotate or print secrets.
- Did not change live DNS or Cloudflare.

### 3.3 Owner actions that this token cannot complete

1. GitHub.com → `ClearGlassInc` → Settings → Billing: confirm payment method and Actions spending limit.
2. Org + repo → Settings → Actions → General: allowed actions, fork PR settings, “Disable Actions” toggle.
3. Repo → Settings → Pages: confirm source branch/`/ (root)` and that the builder is enabled.
4. Repo → Settings → Branches: protect `main` (required reviewers + linear history).
5. After runners return: dispatch `pages-check.yml` and confirm a **new** `pages-build-deployment` run appears, then re-probe `Last-Modified` on `www.clearglassinc.com`.
6. Decide the canonical repo name. Either restore `ClearGlassInc/ClearGlassIncorporated-Desmond` as a redirect/rename or stop publishing the 404 URL.

---

## 4. Validation Evidence

```
# Requested repo
curl -sI https://github.com/ClearGlassInc/ClearGlassIncorporated-Desmond
# → 404

# Live edge
curl -sI https://www.clearglassinc.com/
# HTTP/2 200
# server: GitHub.com
# last-modified: Sun, 06 Sep 2026 13:15:18 GMT

getent hosts www.clearglassinc.com
# 185.199.108-111.153 clearglassinc.github.io

# Pages builder
actions_list method=list_workflow_runs resource_id=351526813
# newest success: 2026-09-06T13:14:52Z run 34035508995

# User workflow job
actions_get method=get_workflow_job resource_id=102976294854
# runner_id=0, no steps, conclusion=failure
```

HEAD SHA audited: `69373f9b44916569a1f3fe3424be323d05dbf9d6`.

---

## 5. Deployment Plan

Gate 0 — entitlement  
Restore GitHub-hosted runner dispatch for public workflows on `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond`. Evidence of success: any user workflow job with `runner_id != 0` and a non-empty `steps` array.

Gate 1 — do not expand surface  
Keep only the six registered workflows. Do not register the 78 copies.

Gate 2 — Pages  
Confirm Settings → Pages source is `main` / root. Push a no-op or re-run the Pages builder. Evidence: new `pages-build-deployment` run after 2026-09-06, and `Last-Modified` on `www.clearglassinc.com` moves forward. Confirm `/.well-known/security.txt` returns 200.

Gate 3 — static gates (after runners work)  
Dispatch `pages-check.yml` and `site-reliability.yml`. Both must reach steps and complete `success`.

Gate 4 — app CI (optional, separate product)  
`artemis-engineering.yml` only runs when `apps/artemis-engineering/**` changes. Root Next fabric and `control-plane` still have **no** registered test workflow. Add one later, scoped, with `contents: read` only.

Gate 5 — commerce  
Treat Render/Fly as a different system. Do not claim `www.clearglassinc.com/health` will ever be the control-plane probe; put `/health` on the API hostname documented in `DEPLOY.md`.

---

## 6. Rollback Plan

| Layer | Rollback |
|---|---|
| This documentation + checkout pin | Revert the commits on `grok/production-recovery-2026-09-10`; `main` stays at `69373f9` if the PR is not merged |
| Live Pages content | Last known good artifact is Pages run `34035508995` / SHA `1fa058e` (2026-09-06). Restoring that tree to `main` (or pointing Pages at `backup/pre-legacy-visual-2026-09-08`, SHA `73e8e1bd`) rolls the public site back. Verify with `Last-Modified` and H1. |
| Domain | CNAME file content is `www.clearglassinc.com`. Removing it would publish under `clearglassinc.github.io/ClearGlassInc-ClearGlassIncorporated-Desmond/` only after a Pages rebuild. Do not remove CNAME to “fix” CI. |
| Commerce / Stripe / Cloudflare | No live mutations were made. Nothing to roll back. |

---

## 7. Final Readiness Assessment

| Success criterion | Status | Notes |
|---|---|---|
| successful build | **NOT VERIFIED** | No user job executed a build this pass |
| passing tests | **NOT VERIFIED** | No test job executed |
| passing workflows | **FAIL** | User workflows fail pre-runner; Dependabot graph-update succeeds |
| successful deployment | **STALE PASS** | Last Pages success 2026-09-06; site still 200 |
| production health validation | **PARTIAL** | Homepage 200; `/health` 404; security.txt 404 |
| dependency integrity | **PARTIAL** | `next@15.5.25` pinned in root package.json; lockfile/audit not re-run here |
| security review completion | **PARTIAL** | Registered workflows least-privilege; no full SAST/DAST evidence this pass |
| deployment verification | **FAIL vs HEAD** | Live `Last-Modified` does not match `main` |

**Readiness verdict: NOT READY for “verified production.”**  
The public marketing origin is alive and served by GitHub Pages. It is four days behind `main`. Continuous integration and continuous deployment are not functioning for user-authored workflows. The repository name in the operator directive does not exist.

Do not announce production recovery complete until:

1. a user-authored workflow job shows `runner_id != 0` and `conclusion=success`, and  
2. `pages-build-deployment` runs against current `main`, and  
3. `curl -sI https://www.clearglassinc.com/` shows a `Last-Modified` at or after that run.
