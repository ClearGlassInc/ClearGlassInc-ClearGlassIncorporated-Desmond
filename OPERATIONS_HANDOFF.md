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
