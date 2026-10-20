# Stripe Payment Operations

Status: proposed implementation on `feat/durable-stripe-payment-ops`. This document does **not** assert that the worker or reconciler has been deployed or that live Stripe configuration has been changed.

## Architecture

Both existing Stripe URLs now enter the same signed ingress:

- `POST /webhooks/stripe`
- `POST /subscriptions/webhook` (kept as a compatibility URL)

The ingress reads a bounded raw body, verifies the Stripe signature and timestamp, locks the expected account/environment, and inserts into `stripe_event_inbox`. It returns `2xx` only after that transaction commits. A duplicate is acknowledged without resetting the original job state. Storage failure returns `503`, allowing Stripe to retry. An unsupported, verified event type is still durably accepted: the worker records an explicit no-op or dead-letter path instead of repeating an unbounded HTTP retry loop.

Workers claim rows with a database lease, increment a fencing token, and execute the existing order/subscription handlers in a transaction that also marks the inbox row complete. Slow Stripe API reads are outside the business transaction. Expired leases can be reclaimed. Retry backoff is exponential with jitter; exhausted/permanent failures are dead-lettered. Event id and business-operation idempotency both remain necessary: a unique Stripe event is not the same thing as a unique purchase.

`stripe_outbox_jobs` stores operator-alert deliveries produced in the same transaction as the local state change. The current sender supports sanitized Slack incoming-webhook alerts only. External webhook delivery is at-least-once, not exactly-once; use the stable operation key when triaging duplicate notifications. It never sends payment credentials, full webhook bodies, customer email, or unfiltered exception text to Slack.

## Payment transition rules

For one-time Checkout, `checkout.session.completed` does not by itself mark an order paid. The event's `payment_status` must be `paid`; delayed payments remain pending until `checkout.session.async_payment_succeeded`, and failed delayed payments are recorded without allowing an old failure event to downgrade a later paid ledger entry. Where an API secret is configured, the worker refreshes the current object before applying these transitions.

Zero-total Checkout is disabled by default. It is only accepted when `STRIPE_ALLOW_ZERO_TOTAL_ORDERS=true`, the verified Session total is zero, and the matching backend-created ClearGlass order is also zero in the same currency. Do not enable it merely to make a test pass.

Subscriptions still use the existing state machine, server-owned price book, audit ledger, and entitlement rules. The inbox completion and the handler's local writes commit in one database transaction. Existing ClearGlass fulfillment remains approval-governed; the payment worker does not auto-confirm a supplier order or bypass an operator gate.

## Environment settings

Secrets belong in the deployment provider's secret store, never this repository.

| Variable | Purpose |
|---|---|
| `STRIPE_SECRET_KEY` | Optional API access used for current-object reads and reconciliation; keep test/live credentials separate. |
| `STRIPE_WEBHOOK_SECRET` | Required to accept Stripe webhook traffic. In production, if the Stripe API key is configured, startup fails closed without this secret. |
| `STRIPE_EXPECTED_LIVEMODE` | Explicit `live` or `test` fence. If omitted, the ingress infers the expected mode from a recognized Stripe API key prefix; production fails closed when the expected mode cannot be established. |
| `STRIPE_ACCOUNT_ID` | Empty means the platform account only. Set it only when this deployment is intentionally scoped to that Connect account. |
| `STRIPE_WEBHOOK_PREVIOUS_SECRET` and `STRIPE_WEBHOOK_PREVIOUS_SECRET_ACCEPT_UNTIL` | Optional rotation overlap. The previous secret is accepted only until the explicit ISO-8601 cutoff; remove both after rotation. |
| `STRIPE_WEBHOOK_MAX_PAYLOAD_BYTES` | Maximum accepted request body; default 1 MiB. Configure a compatible ingress/proxy limit too. |
| `STRIPE_EVENT_LEASE_SECONDS` | Worker lease duration; default 60 seconds. |
| `STRIPE_EVENT_MAX_ATTEMPTS` | Attempts before event dead-letter; default 12. |
| `STRIPE_OUTBOX_MAX_ATTEMPTS` | Attempts before outbound job dead-letter; default 10. |
| `STRIPE_PAYLOAD_RETENTION_DAYS` | Default 30 days. The worker scrubs raw payloads from succeeded inbox rows after this period; minimal event/hash/state metadata remains. Dead-letter payloads are retained until handled. |
| `SLACK_WEBHOOK_URL` | Optional incoming-webhook URL for sanitized operator alerts. It must be stored as a secret and use the approved Slack host. |

The integration deliberately has no undocumented “accept unsigned in development” route. Configure a dedicated Stripe CLI signing secret for local signed-webhook tests, or use explicit unit tests around the verifier. A missing verifier configuration results in a safe refusal rather than an unverified event being booked.

## Deployable process commands

Run from `control-plane/` with the same environment and database configuration as the API. The web API must not run a long-polling worker inside its request process.

Start one or more dedicated worker processes:

```bash
python -m app.stripe_worker
```

Drain at most one event and one outbox job for a local/sandbox diagnostic:

```bash
python -m app.stripe_worker --once
```

Run a recent overlapping Stripe event scan every 15 minutes:

```bash
python -m app.stripe_reconcile --profile recent --max-pages 20
```

Run the wider sweep daily:

```bash
python -m app.stripe_reconcile --profile daily --max-pages 100
```

The reconciler reads Stripe's Events/Checkout APIs, backfills unseen event jobs, compares current Checkout state with the ledger, and opens operator alerts for mismatches or paid service orders that lack a delivery record. A partial event scan records a cursor for the next run. It does not charge, refund, adjust a payout, or silently clear a mismatch.

The existing Render blueprint currently describes the web API/storefront/admin but does not configure a dedicated worker or scheduler service. Those are separate rollout changes and must be reviewed and explicitly approved before being added. Do not assume a merged branch means a worker is running.

## Operator workflow

- Inspect inbox: `GET /ops/stripe-inbox?state=dead_letter` with admin authentication.
- Inspect alert outbox: `GET /ops/stripe-outbox?state=retry` with admin authentication.
- Replay one corrected inbox event: `POST /ops/stripe-inbox/{event_id}/replay`.
- Replay one corrected alert job: `POST /ops/stripe-outbox/{job_id}/replay`.
- Read the sanitized state and error code before replaying. A replay must not be used to “fix” a disputed amount, customer association, order ownership, refund, or double-payment discrepancy. Those need owner review.

## Release and rollback

1. Run migrations and tests against a disposable database first.
2. Validate with Stripe test credentials and the correct signed endpoint secret. Include duplicates, pending/delayed Checkout, out-of-order notifications, worker crashes, expired leases, database outage, and reconciliation backfill.
3. Before any production endpoint is changed, verify the account/environment scope, event subscriptions, body-size limits, secret rotation window, database backup, worker service, and schedule.
4. Roll out the database schema before switching Stripe's endpoint routing. Preserve a rollback plan for app code and migration compatibility; never delete inbox/audit rows as rollback cleanup.
5. Confirm successful processing through inbox state, local order ledger, entitlement/service order, and the reconciliation output. A successful HTTP acknowledgment proves only durable receipt, not completed fulfillment.

### Current limitations to clear before production

- No live key, webhook endpoint, account scope, or signing secret has been inspected or changed as part of this branch work.
- Automated tests and deployment CI results must be run and reviewed; this document is not a test certificate.
- The worker and reconciler need separately configured host processes/schedules; they are not part of the existing API process.
- V1 event backfill is implemented; Stripe thin notifications use the SDK adapter in the worker and require authenticated API reads. Ensure the chosen webhook destination/event family is supported by the pinned Stripe SDK before enabling a thin-event destination.
- External delivery is at-least-once. Ambiguous supplier/customer effects remain under ClearGlass's existing governed/manual review policy.
