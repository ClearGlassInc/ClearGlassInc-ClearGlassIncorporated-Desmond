# Operations handoff

What changed, what runs on its own, and what still needs you.

Written for the person who has to operate this, not for a reviewer. Every claim
below is either verifiable from the repository or explicitly marked as not yet
verified.

## What was changed

### PayPal Orders v2 — new, not live

The repository had no PayPal integration of any kind. It now has one, built to
the same rules as the Stripe path.

- `control-plane/app/paypal.py` — order creation priced from the server-side
  price book, capture, fail-closed webhook verification, catalogue
  reconciliation.
- `control-plane/app/routers/paypal.py` — the customer order endpoint, the
  verified webhook, and an admin capture endpoint that queues for approval
  rather than moving money inline.
- `control-plane/tests/test_paypal.py` — 47 tests covering signature
  verification, replay protection, idempotency, pending/denied handling,
  catalogue mismatch, and the fulfillment gate.

**It is not taking payments.** No credentials are configured, the API base
defaults to the sandbox, and it has not been run against PayPal. See the setup
checklist in `docs/REVENUE_OPERATIONS.md`.

### A shared order ledger

`control-plane/app/order_ledger.py` now holds the one implementation of "book
this payment exactly once". Stripe and PayPal both settle through it, keyed on
`orders.external_ref`. Previously that logic lived inside the Stripe router;
adding a second processor would have meant a second copy, and two copies of that
rule drift in the direction where one of them starts counting a retry as revenue.

The Stripe path's behaviour is unchanged — the router is now an adapter that
adds the Stripe-specific address parsing.

### Automation governance, as enforceable code

`scripts/automation_governance.py` decides what a bot may merge and whether the
repository is healthy enough to be changing itself. `tests/test_automation_governance.py`
holds it to that. Policy is in `docs/AUTOMATION_POLICY.md`.

Writing the tests found a real bug in the classifier: `lstrip("./")` was
stripping leading dots, so **every dotfile path — including
`.github/workflows/**` and `.env*` — silently fell out of the protected set**
while the policy still reported itself as enforcing. Fixed, and the dotfile cases
are now in the test matrix.

### Two pre-existing red gates, fixed

Both were failing on the branch before this change:

1. `control-plane/tests/test_route_auth_coverage.py` was failing because
   `/subscriptions/portal` and `/subscriptions/webhook` had shipped without an
   exemption entry. Both are legitimately safe open — verified by reading them —
   and now carry written justifications. `/subscriptions/portal` was also missing
   the per-IP throttle its twin `/billing/portal` has, so it got one rather than
   an exemption claiming protection it did not have.
2. `scripts/audit_github_actions.py` (run by `ci.yml`) was failing because
   `revenue-pipeline-agent.yml` used an unpinned `actions/checkout@v4`. Pinned to
   a full SHA, with `persist-credentials: false` and a job timeout.

### Supporting changes

- `scripts/secret_scan.py` — the credential scan extracted from
  `security.yml`'s inline heredoc so the Maintenance Review breaker and the
  Security gate read one pattern list. Two Stripe live-key patterns added.
  Tested in `tests/test_credential_scan.py`.
- `.github/workflows/maintenance-review.yml` — the scheduled improvement loop.
  Weekly. Proposes; never merges. Its only write permission is `issues: write`.
- `.github/workflows/rollback.yml` — one documented way back to a known-good
  deployment, manual dispatch only.
- `.github/dependabot.yml` — weekly updates, grouped, labelled
  `human-approval-required`, never auto-merged.
- `control-plane/.env.example` — variable names only.
- `docs/AUTOMATION_POLICY.md`, `docs/REVENUE_OPERATIONS.md`,
  `docs/INCIDENT_RESPONSE.md`.

## What is automated

| Runs on its own | What it does | What it cannot do |
|---|---|---|
| Stripe webhook | Books verified payments idempotently | Refund, reprice, fulfill without reconciling |
| PayPal webhook | Same, once credentials exist | Accept an unverified event, ever |
| Commerce Daily Loop | Governance self-check, executive report | Change anything |
| Maintenance Review (weekly) | Collects evidence, evaluates breakers, files a backlog issue | Push, merge, or edit any file |
| Dependabot (weekly) | Opens update PRs | Merge them |

## What still requires you

Everything that moves money or changes what customers see:

- Approving any high/critical action in the `approvals` queue — pricing, refunds,
  payment/tax/fulfillment settings, inventory reorders, every Etsy write, every
  Printful order confirmation, every PayPal capture.
- Merging any pull request touching payments, auth, workflows, migrations,
  dependencies, infrastructure, or published legal text.
- Running the rollback workflow and naming the target revision.
- The PayPal sandbox and production verifications.

## Required secrets and where they go

All of these are runtime environment variables in the hosting platform's secret
manager. **None belong in this repository.** Names are listed in
`control-plane/.env.example`.

| Area | Variables | Set in |
|---|---|---|
| Admin auth | `ADMIN_API_KEY` | Platform env. Required in production or the app fails closed at startup |
| Stripe | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY` | Platform env |
| PayPal | `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, `PAYPAL_API_BASE` | Platform env |
| Etsy | `ETSY_KEYSTRING`, `ETSY_SHARED_SECRET`, `ETSY_ACCESS_TOKEN`, `ETSY_REFRESH_TOKEN` | Platform env, via `python -m app.etsy_connect` |
| Printful | `PRINTFUL_API_KEY`, `PRINTFUL_WEBHOOK_SECRET` | Platform env |
| Deployment | `RENDER_DEPLOY_HOOK` | GitHub `production` environment secrets |
| Health check | `PRODUCTION_HEALTH_URL` | GitHub repository variable |
| Breaker inputs | `PRODUCTION_HEALTH_PASSING`, `CONSECUTIVE_DEPLOY_FAILURES` | GitHub repository variables |
| Proxy awareness | `TRUSTED_PROXY_HOPS`, `TRUSTED_PROXY_IPS` | Platform env. Both, or neither works |

Still to configure externally: the PayPal webhook subscription, the GitHub
`production` environment with required reviewers, and branch protection with
required status checks on the default branch.

## Validating this change

```bash
# Control plane: lint and the full suite (378 tests)
cd control-plane
pip install -r requirements.txt && pip install pytest "ruff==0.15.8"
ruff check . && python -m pytest tests/ -q

# Automation policy, credential scan, and the repository suite
cd ..
python3 scripts/automation_governance.py --self-check
python3 scripts/secret_scan.py
python -m pytest tests/test_automation_governance.py tests/test_credential_scan.py -q

# Workflow safety invariants (what ci.yml's workflow-doctor job runs)
python3 scripts/workflow_doctor.py
python3 scripts/audit_github_actions.py

# Everything ci.yml runs, offline
python3 scripts/ci_local.py
```

## Rolling this back

Nothing here changes an existing behaviour that could not be reverted by
reverting the merge commit. The two behavioural edits to existing code are the
`/subscriptions/portal` throttle and the Stripe router's delegation to the shared
ledger; both are covered by the existing suite.

For a deployment-level rollback, see `docs/INCIDENT_RESPONSE.md`.

## Known risks

1. **CI reports nothing.** GitHub Actions has not dispatched runners for this
   organisation since 2026-09-06 (`PRODUCTION-RECOVERY.md` §1.1). A green check
   is the absence of signal, not success. Everything above was run locally; the
   commands are listed so you can repeat them. This is fixed in organisation
   settings, not in this repository.
2. **PayPal is unverified.** Code-complete, credential-empty, never run against
   PayPal. Treat it as untested until the sandbox checklist has been completed.
3. **The breakers depend on signals that do not exist yet.**
   `PRODUCTION_HEALTH_PASSING` and `CONSECUTIVE_DEPLOY_FAILURES` are repository
   variables nothing currently writes. Until something does, they default to
   unsafe and the breakers report halted — which is the correct answer, but it
   means the Maintenance Review loop will report halted every week until real
   health signals are wired.
4. **`paypal.py` is not covered by `test_route_auth_coverage`'s reasoning about
   live credentials.** The webhook's verification is unit-tested against the real
   implementation, but the router tests stub verification. An end-to-end test
   against PayPal's sandbox is the missing coverage, and it needs credentials.
5. **No staging environment exists.** `docs/INCIDENT_RESPONSE.md` assumes a
   rollback target that was previously healthy in production. Without staging,
   the first place a change is exercised under real traffic is production.

## First 30 days — what to measure

Targets, not predictions. None of these is a revenue forecast, and nothing in
this system can guarantee income.

| Metric | Target |
|---|---|
| Required CI checks passing on merges to the default branch | 100% (blocked on the runner entitlement) |
| Plaintext credentials found by the scan | 0 |
| Payment webhooks signature-verified, logged and idempotent | 100% |
| Fulfilled orders traceable to a verified payment event and a catalogue SKU | 100% |
| Rollback exercised at least once, deliberately, before it is needed | 1 |
| Production incidents attributable to an automated change | 0 |
| PayPal sandbox verification completed and recorded | 1 |
| Weekly report showing verified sales, refunds and exceptions | 4 |

---

# Session addendum — 2026-09-15

The section above documents the PayPal channel and remains accurate. This
addendum covers a separate production-automation pass on the same day, and
**supersedes nothing above it.**

Baseline commit for this pass: `16057ab`. Final commit: `c765a04`.

## What was changed

Seven pull requests, all merged, all verified locally before pushing.

| PR | Change | Class |
|---|---|---|
| #52 | `docs/BASELINE.md` — verified state, classified failures, risk register | docs |
| #53 | **F5** — registered an orphaned blog page; `pytest` 7 failed → 0 | fix |
| #54 | `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md` | docs |
| #55 | **F7** — `render.yaml` build contexts pointed at a directory that does not exist | fix, protected path |
| #67 | **F8** — `commerce.selfcheck` ran in a missing directory; exit 127 → 0 | fix |
| #68 | `docs/CHANGELOG.md`, corrected `CLAUDE.md` and `ENGINEERING_GUIDELINES.md` | docs |
| #69 | **R8** — canonical catalog contract, validator, owner checklist | feature |

**#56 was merged by another contributor** and independently verified here: it
repaired `admin/`, which could not be installed at all (`npm ci` exit 1).

Eight defects were classified F1–F8. Five are now fixed. **Every one of them
reached `main` through the CI gap described below** — and the repository's own
test suite was adequate to catch all of them.

## What is automated

Nothing new was automated in this pass, deliberately.

`--strict` on the catalog validator is the one new gate, and it is **switched
off**: `tests/test_catalog_contract.py::test_strict_is_not_wired_into_the_blocking_gate_yet`
fails if someone wires it in before the catalog fields exist. Turning it on
today would fail the build on all 65 SKUs to report what the tool already
reports on demand.

No scheduled workflow, auto-merge path or unattended mutation was added.

## What still requires you

Nothing below can be done from inside this repository.

| # | Action | Where | Unblocks |
|---|---|---|---|
| 1 | **Restore Actions entitlement** — billing, spending limit, allowed-actions policy, Actions toggle | GitHub org + repo settings | Everything. See below. |
| 2 | Confirm which provider serves `www.clearglassinc.com` | Hosting dashboards | Deploy + rollback automation (R5) |
| 3 | Resolve three live entry prices: 1,250 quoted / 297 price book / 249 live checkout — and **no SKU exists for the 1,250 assessment** | Business decision | Selling anything (R3) |
| 4 | Supply the catalog field values | `docs/CATALOG_SCHEMA.md` §4 | Governed checkout validation (R8) |
| 5 | Protect `main` | Repo → Settings → Branches | R7 |
| 6 | Decide on 3 `storefront/` vulnerabilities — `nanoid` (high), `sharp`/libheif (high), `baseline-browser-mapping` (moderate) | Protected path | R9b |
| 7 | Review 8 recurring agent routines, 6 firing within 13:00–13:08 UTC daily | Routines list | Circuit-breaker compliance |

### Item 1 is the one that matters

**GitHub Actions has dispatched no runners since 2026-09-10.** `runner_id: 0`,
no steps, empty check output, 4–15 second runs, every workflow, every PR.

The consequence is not "CI is flaky." It is that **a red check and a green check
both carry zero information.** Twenty-two PRs merged into `main` during the
outage. Three confirmed defects came through that gap in a single day.

Exit condition (**Gate 0**): any user-authored workflow job reporting
`runner_id != 0` with a non-empty `steps` array.

### Item 7, stated plainly

Eight recurring routines fire daily against this repository, six of them inside
an eight-minute window, several open-ended. The automation policy in this
repository allows **at most 1 auto-merged PR per day and 3 open bot PRs**. Eight
uncoordinated daily agents cannot honour either. Pull-request numbers advanced
from 55 to 67 in roughly an hour on 2026-09-15.

**No routine was disabled.** They are yours, several may be deliberate, and
deleting them is destructive.

## Required secrets, and where

Names only. Never a value, never in a file, never in a commit. Full inventory in
`control-plane/.env.example`, which is complete and names-only.

Set every one in the hosting platform's secret manager — Render environment
groups or equivalent.

| Variable | What it blocks today |
|---|---|
| `ADMIN_API_KEY` | Production startup. The app **fails closed** without it, by design |
| `PAYPAL_WEBHOOK_ID` | All PayPal webhook verification — every notification is refused |
| `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` | PayPal order creation |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Stripe checkout and webhook booking |
| `ETSY_KEYSTRING` / `ETSY_SHARED_SECRET` / `ETSY_ACCESS_TOKEN` / `ETSY_REFRESH_TOKEN` | Etsy reconciliation |

Also: `TRUSTED_PROXY_HOPS` **and** `TRUSTED_PROXY_IPS` must be set together
behind a reverse proxy, or every caller shares one throttle bucket and a single
abusive client can 429 the storefront. `GET /health` reports `client_peer` so one
curl against the deployed service yields the value. An RFC1918-wide allowlist is
**not** sufficient — see `render.yaml`'s own comments.

## Exact validation steps

```bash
pip install pytest pytest-cov pyyaml "ruff==0.15.8"
pip install -r control-plane/requirements.txt

python3 scripts/ci_local.py                        # expect 9 passed, 0 failed, 1 skipped
python3 -m pytest tests/ -q                        # expect 1253 passed, 5 skipped
cd control-plane && python3 -m pytest tests/ -q    # expect 378 passed, 1 skipped
python3 tools/catalog_contract.py                  # gap report; exits 0 by design
python3 -m bots.rfed_audit_bot --self-check
cd control-plane && python -m app.daily_loop --json
```

Node, all verified on `c765a04`:

```bash
npm ci && npm run typecheck                    # root — exit 0, 0 vulnerabilities
cd storefront && npm ci && npm run build       # exit 0 (3 vulnerabilities, R9b)
cd admin && npm ci && npm run build            # exit 0 (was exit 1 before #56)
```

`git status` must be clean after a gate run. If `generated search assets are
current` fails, run `python3 tools/generate_search_assets.py` **and commit** —
the gate compares against what is committed, not the working tree.

Until Gate 0 passes, **the operator is the CI.** Run these before every push.

## Rollback

Every PR in this pass states its own rollback command, and each is a single
`git revert <merge-commit>`. No migration, schema change or data transformation
was introduced, so no rollback requires a data step.

Reverting #67 returns `commerce.selfcheck` to exit 127. Reverting #55 returns
the Render blueprint to a state where it cannot build. Reverting #53 returns
`main` to 7 failing tests.

## Known risks

Full register in `docs/BASELINE.md`. The ones that would surprise a new operator:

1. **No staging environment.** The first place a change meets real traffic is
   production. Unchanged from the section above.
2. **Hosting is ambiguous.** GitHub Pages `CNAME`, `netlify.toml`, and
   `_headers`/`_redirects` coexist. Which one serves the live domain is
   **unconfirmed**, and a rollback aimed at the wrong provider is worse than none.
3. **80 registered workflows**, 36 scheduled, 16 able to commit back. They are
   dormant only because runners are down. When entitlement returns they resume
   **at once** — stage that, do not flip it.
4. **No payment channel is live.** No integration has completed both a sandbox
   test and a production verification. None may be described as live.
5. **~70 stale `clearglass-commerce/` prose references remain**, deliberately
   unswept: several are *correct as history*, and two must never be swept — a
   `User-Agent` string in `control-plane/app/printful.py` and a path allowlist in
   `agents/*/agent.json`.

## First 30 days — what to measure

Operational readiness only. **None of these is a revenue target**, and nothing
here can guarantee income. Revenue targets are the owner's to set; this pass
produced no evidence that would support one.

| Metric | Now | Target |
|---|---|---|
| Gate 0: a job reporting `runner_id != 0` with steps | **0** | 1 |
| Defects reaching `main` without CI signal | 3 in one day | 0 |
| Catalog SKUs contract-complete | **0 of 65** | 65 |
| Live entry prices for the same offer | **3** | 1 |
| Payment channels with sandbox **and** production verification recorded | 0 | ≥1 |
| Hosting provider for the live domain, confirmed in writing | unknown | confirmed |
| `main` branch-protected | no | yes |
| Open high-severity dependency vulnerabilities | 2 | 0 |
| Recurring agent routines against this repository | 8 | ≤2 |
