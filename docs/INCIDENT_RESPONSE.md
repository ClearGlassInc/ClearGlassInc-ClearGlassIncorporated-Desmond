# Incident response

What to do when production is broken, and what not to do.

## The one rule

**Roll back, capture evidence, then fix forward in a reviewed pull request.**

Never roll forward repeatedly after a failed production deployment. Each
speculative "this should fix it" commit deploys unreviewed code into an already
broken system, and the usual outcome is that the original fault becomes
impossible to isolate. A ten-minute outage becomes an afternoon.

## Rolling back

```
Actions → Rollback → Run workflow
  target_sha: <full 40-character SHA of the last known-good revision>
  reason:     <one line: what is broken>
  surface:    control-plane | storefront | admin
```

`.github/workflows/rollback.yml` will:

1. Refuse anything that is not a full SHA — a tag or branch name can move, so
   rolling back to a name redeploys whatever that name points at by the time the
   job runs, which is not a rollback.
2. Refuse a revision that was never an ancestor of the default branch. That
   revision was never the deployed state, so deploying it during an incident is
   shipping something new and unreviewed at the worst possible moment.
3. Run lint and the control-plane suite against the target before deploying it.
4. Deploy behind the `production` protected environment.
5. Poll the health endpoint until it passes, or fail loudly.
6. Open an incident issue with the target, the result, and the follow-up
   checklist — whether or not the deploy succeeded. A failed rollback is the
   more important one to have written down.

It is manual dispatch only. An automatic rollback on a failed health check can
flap between two broken states, and an automatic rollback of a data migration is
worse than the outage it is reverting. A human names the target.

**Finding the target SHA:** the last commit whose deployment was healthy. If
that is not obvious, `git log --first-parent origin/main` and pick the last merge
before the failing one.

## Automated change stops during an incident

Two consecutive failed deployments trip a circuit breaker in
`scripts/automation_governance.py` that halts **all** automated mutation — not
just merges to the failing surface. A red secret scan, a red payment test, or a
failing production health check does the same. See `docs/AUTOMATION_POLICY.md`.

Do not clear a breaker to unblock automation. The breaker is the correct state
until a human has established what broke.

## Money-side incidents

A payments incident has a second obligation beyond restoring service: customers
may have been charged.

**Immediately:**

1. Do **not** issue refunds in bulk, change prices, or alter payout settings.
   Every one of those is an always-escalate action and doing them by hand during
   an incident is how a bad hour becomes a chargeback wave.
2. Reconcile the incident window: every payment event against every order row.
   `python -m app.daily_loop --json` and the `events` ledger are the record.
3. Identify orders that are `paid` with `fulfillment_status` of `pending` or
   `unfulfillable`. Those are open obligations to real customers.

**Then, per condition:**

| Condition | Action |
|---|---|
| Paid, nothing shipped | Fulfill manually or refund. Record which, and why |
| Charged twice | Check `order_event_duplicate_skipped` — the ledger is idempotent, so a genuine double charge means two distinct processor ids, which is a processor-side issue |
| Capture does not match the catalogue | Held automatically. Establish what was actually bought before releasing it |
| Webhook signature failures in a run | Either a rotated secret or someone posting forged settlement events. Check which before re-enabling anything |
| Fulfillment sent twice | Stop the supplier order if it has not shipped; absorb it if it has. Then find why the idempotency key did not hold |

Never log payment card data, access tokens, API secrets, or full personal data
while investigating. `app/audit.py` redacts credential-shaped keys from the
ledger; do not route around it with ad-hoc logging.

## Daily operational summary

The daily summary should carry, from the ledger rather than from estimates:

- Production status, deployments and rollbacks
- CI pass/fail rate, open critical vulnerabilities
- Payment events by processor; **verified** gross sales
- Refunds and chargebacks
- Fulfillment successes and failures; inventory exceptions
- Etsy synchronisation status
- Open incidents
- Automated changes proposed, merged, blocked and rolled back

If a figure cannot be traced to a ledger row, report it as unavailable. A
projected number in an operational summary is a number someone will later act on
as if it were real.

## Escalation

`ESCALATION_EMAIL` and `SLACK_WEBHOOK_URL` in the control plane's environment.
Neither is a substitute for the incident issue — the issue is the durable record.

## Known standing risk

GitHub Actions has not dispatched runners for this organisation since
2026-09-06 (`PRODUCTION-RECOVERY.md` §1.1). While that holds, CI cannot tell you
whether a rollback target is good, and the Rollback workflow itself will not run.
**In that state, rollback is a manual operation via the hosting provider's
dashboard, and the incident record must be opened by hand.** Fixing the runner
entitlement is an organisation-settings task, not a repository one.
