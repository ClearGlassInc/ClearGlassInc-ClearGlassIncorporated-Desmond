# Stripe Account Live & Earning Audit — 2026-07-29

**Business:** ClearGlass Inc.<br>
**Audit type:** Read-only repository and local-runtime evidence review<br>
**Audit boundary:** No authenticated Stripe Dashboard session, production secret store,
production database, production API logs, or business bank statement was available. No live
charge, payout, configuration change, or hosted webhook test was attempted.

## Executive result

**Evidence-backed health score: 1/22 PASS (4.5%).** One item can be established from source;
nineteen require account-owner verification; two fail the production-readiness review. This is
not a claim that the Stripe account itself has failed nineteen checks. `NEEDS VERIFICATION` means
the relevant account or financial evidence was outside the audit boundary.

The public static store is **not accepting Stripe card payments**: all four Stripe Payment Link
values are empty and the catalogue explicitly reports that live card checkout is disabled. The
commerce control plane also defaults to mock checkout when `STRIPE_SECRET_KEY` is absent. No
Stripe-related environment variables were present in the audit shell. These safe defaults do not
prove what is configured in the independently deployed production runtime or Stripe account.

### Critical blockers to earning through the audited storefront

1. **Live card checkout is disabled on the public static storefront.** Create live Payment Links
   only after account capabilities, identity verification, bank destination, and payment methods
   are confirmed; then add the approved links using `docs/STORE_GO_LIVE.md`.
2. **The production Stripe account/runtime could not be authenticated or observed.** Items 1–10
   and 14–22 must be attested by an authorized account owner before declaring the account live.
3. **The backend does not explicitly classify Stripe SDK failures.** A live API failure currently
   bubbles out of checkout creation instead of producing the required safe, observable error
   contract (item 13).

## Evidence and scoring rules

- `PASS`: direct repository evidence establishes the requirement, or an executed check proves it.
- `FAIL`: direct evidence contradicts the requirement or a required control is absent.
- `NEEDS VERIFICATION`: only the Stripe Dashboard, production runtime, support record, or bank
  statement can establish the result. It is deliberately not scored as a pass.
- Secret values, full bank details, identity documents, and customer data must never be copied
  into this report, a ticket, chat, or git. Record only masked identifiers and dated attestations.
- Dashboard navigation labels can change. Use Stripe's current Dashboard and documentation rather
  than treating the prompt's menu wording as an immutable interface contract.

## Phase 1 — Account is in live mode

### 1. Dashboard live mode

- **Status:** NEEDS VERIFICATION
- **Current value:** No authenticated Dashboard evidence was available. Repository checkout is
  disabled/mock by default, which is not evidence of the Dashboard mode.
- **Action needed:** Account owner signs in directly at `dashboard.stripe.com`, selects the live
  environment, and records a dated screenshot showing the account identifier and live-mode
  indicator, with sensitive data redacted. Do not share login credentials.
- **Priority:** CRITICAL
- **Estimated time:** 2–5 minutes.

### 2. Live API keys in the production runtime

- **Status:** NEEDS VERIFICATION
- **Current value:** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and
  `STRIPE_PUBLISHABLE_KEY` are empty in the committed template; no Stripe variables were present
  in the audit shell. Production secrets are intentionally outside git. The backend treats any
  non-empty secret as “live” and does not validate its prefix, so a test key can enable its live
  code path. Stripe key prefixes are `pk_live_` and `sk_live_`; a least-privilege restricted live
  secret can use `rk_live_` and should not be rejected merely because it is restricted.
- **Action needed:** In the production secret manager, have an authorized operator verify only the
  prefixes and key identifiers (never values). Confirm publishable `pk_live_` and secret
  `sk_live_` or approved restricted `rk_live_` belong to the same live account. Add a fail-closed
  production startup check that rejects test prefixes and blank webhook secrets.
- **Priority:** CRITICAL
- **Estimated time:** 10–20 minutes for verification; 1–2 engineering hours for the startup guard.

### 3. No restriction or verification banner

- **Status:** NEEDS VERIFICATION
- **Current value:** The go-live runbook records historical evidence that “Multiple capabilities
  paused” was shown. That statement is not current Dashboard evidence and must be rechecked.
- **Action needed:** Review live Dashboard alerts and the account capability/requirements status.
  Resolve every currently due or past-due business, representative, ownership, identity, website,
  and bank request through Stripe's secure interface. Do not upload KYC material to this repo.
- **Priority:** CRITICAL
- **Estimated time:** 5–15 minutes to inspect; same day to several business days if Stripe reviews
  documents.

## Phase 2 — Account can receive money

### 4. Bank account linked and verified

- **Status:** NEEDS VERIFICATION
- **Current value:** No Dashboard or bank evidence was available. The repository stores only
  optional masked payout metadata; the committed values are examples, not production evidence.
- **Action needed:** Two authorized people should compare Stripe's masked destination, legal owner,
  country, currency, and last four digits with a current void cheque/PAD form or bank portal.
  Complete any verification in Stripe. Never paste routing or account numbers into git.
- **Priority:** CRITICAL
- **Estimated time:** 10–20 minutes; 1–3 business days if microdeposit verification is required.

### 5. Payouts enabled and scheduled

- **Status:** NEEDS VERIFICATION
- **Current value:** Code describes automatic Stripe payouts, but no live payout configuration or
  pause state was available.
- **Action needed:** Confirm payouts are enabled in the live account, select daily or weekly per the
  finance owner's cash-management decision, and document the decision date and approver. Do not
  change the schedule autonomously.
- **Priority:** CRITICAL
- **Estimated time:** 5–10 minutes, excluding an account restriction review.

### 6. Payout and bank currencies compatible

- **Status:** NEEDS VERIFICATION
- **Current value:** The example metadata lists a Canadian destination and `CAD,USD`; this is a
  placeholder and cannot prove the bank accepts the live settlement currencies.
- **Action needed:** Compare every enabled settlement currency with Stripe's external-account
  currency and the bank account's supported currency. Use a CAD account for CAD settlement and a
  supported USD account/settlement path for USD; obtain finance approval before changing either.
- **Priority:** HIGH
- **Estimated time:** 10–20 minutes; up to several business days if a new currency account is needed.

## Phase 3 — Payment processing is active

### 7. At least one payment method enabled

- **Status:** FAIL
- **Current value:** The audited public store and pricing page contain no Stripe Payment Links, so
  customers cannot use an enabled Stripe method through those pages. Dashboard-level card, ACH,
  Apple Pay, and Google Pay settings remain unknown.
- **Action needed:** First confirm cards are active in the live Dashboard and perform required
  domain/payment-method setup. Then create one approved live Payment Link per SKU and add the same
  mapping to both public pages. Add other methods only after currency, country, refund, support, and
  reconciliation workflows are ready.
- **Priority:** CRITICAL
- **Estimated time:** 20–45 minutes after account activation; longer if domain or capability review
  is required.

### 8. Business is permitted by Stripe

- **Status:** NEEDS VERIFICATION
- **Current value:** Repository content presents security/compliance consulting and software, but
  source review cannot determine Stripe's classification, actual fulfillment, jurisdictions, or
  account underwriting decision.
- **Action needed:** The business owner and counsel compare every actual product/service and sales
  jurisdiction against Stripe's current
  [Restricted Businesses policy](https://stripe.com/legal/restricted-businesses). Submit requested
  documentation through Stripe and obtain written approval if the activity is restricted. Do not
  infer approval from the absence of an immediate warning.
- **Priority:** CRITICAL
- **Estimated time:** 30–60 minutes for review; several business days or more for underwriting.

### 9. No unexpected holds or reserves

- **Status:** NEEDS VERIFICATION
- **Current value:** No live balance, reserve, or support evidence was available.
- **Action needed:** Review live balances for reserve amounts, unavailable/pending funds, negative
  balances, and payout-impacting holds. Reconcile expected pending timing; open a Stripe support
  case for anything unexplained and retain the case ID (not private correspondence) in the audit.
- **Priority:** HIGH
- **Estimated time:** 10–20 minutes; support resolution varies from hours to weeks.

## Phase 4 — Integration is live

### 10. Live webhook endpoint registered and receiving events

- **Status:** NEEDS VERIFICATION
- **Current value:** Source implements `POST /webhooks/stripe`, and the handoff document proposes
  `https://api.clearglassinc.com/webhooks/stripe`, but registration, reachability, enabled status,
  subscribed events, and successful live deliveries were not observed. The handoff subscription
  list omits the payout events that populate the payout ledger.
- **Action needed:** In live Workbench/Webhooks, verify the production HTTPS endpoint is enabled and
  subscribed at minimum to the events the application consumes:
  `checkout.session.completed`, `payout.created`, `payout.updated`, `payout.paid`,
  `payout.failed`, and `payout.canceled`. Send a non-financial test event, confirm a 2xx response
  and a correlated, redacted audit record, then inspect delivery history. Align or remove unrelated
  documented invoice/subscription events.
- **Priority:** CRITICAL
- **Estimated time:** 20–45 minutes if the production endpoint is deployed and healthy.

### 11. Webhook signature verification works

- **Status:** NEEDS VERIFICATION
- **Current value:** The backend implements HMAC-SHA256 verification, constant-time comparison, and
  a five-minute timestamp tolerance; offline tests cover valid, tampered, stale/malformed, and
  missing-secret cases. However, when the webhook secret is absent, the route accepts unverified
  payloads. Production configuration and an end-to-end signed delivery were not observed.
- **Action needed:** Make `APP_ENV=production` fail startup unless `STRIPE_WEBHOOK_SECRET` is set;
  reject every unverified production webhook. Verify the live endpoint secret (not a Stripe CLI or
  test endpoint secret), rotate if exposed, and execute the end-to-end check in item 10.
- **Priority:** CRITICAL
- **Estimated time:** 15–30 minutes for configuration; 1–2 engineering hours for the fail-closed guard.

### 12. No test-mode Stripe objects in production code

- **Status:** PASS
- **Current value:** No `price_`, `prod_`, `coupon_`, or `cus_` identifiers are hard-coded in the
  audited checkout path. The backend creates inline `price_data` under the runtime key, and public
  Payment Link mappings are empty. Test-only webhook secrets and payout IDs occur only in tests.
- **Action needed:** None for source. Before activation, inventory live Dashboard products, Prices,
  coupons/promotion codes, tax rates, and Payment Links and record their live IDs in the approved
  configuration—not source secrets. Never copy a test object ID into production configuration.
- **Priority:** HIGH
- **Estimated time:** 15–30 minutes for the pre-launch live-object inventory.

### 13. Stripe error handling covers required categories

- **Status:** FAIL
- **Current value:** The checkout code calls `stripe.checkout.Session.create` without an explicit
  exception translation layer. There is no source-visible handling contract for `card_error`,
  `api_error`, `invalid_request_error`, or `authentication_error`; failures can become generic 500
  responses without stable customer messaging or operator classification.
- **Action needed:** Add a tested exception mapper using the installed Stripe SDK's current Python
  exception classes. Return safe, non-sensitive client errors, attach correlation IDs, log only
  sanitized type/request metadata, retry only transient idempotent operations with bounds, and
  alert immediately on authentication/configuration failures. Do not log keys, card data, or raw
  Stripe response bodies.
- **Priority:** HIGH
- **Estimated time:** 4–8 engineering hours including tests.

### 14. API version pinned and reviewed

- **Status:** NEEDS VERIFICATION
- **Current value:** No `stripe_version` is set in application code. `stripe>=10.0` has no upper
  bound, so dependency behavior may drift, and the live account/default webhook endpoint API
  versions were not observed.
- **Action needed:** Record the account and webhook endpoint API versions, review Stripe's current
  changelog against this integration, test an upgrade in test/sandbox mode, pin a reviewed SDK
  version in the lock/dependency process, and set an explicit API version where supported. Promote
  only after checkout, signature, event schema, refund governance, and payout regression tests pass.
- **Priority:** HIGH
- **Estimated time:** 2–4 hours for assessment/testing; longer if breaking changes exist.

## Phase 5 — Money is actually flowing

### 15. Successful live charges in the last 30 days

- **Status:** NEEDS VERIFICATION
- **Current value:** No live Payment/Charge records or production order database were available.
  The audited public Stripe checkout is disabled, so it cannot be credited with live card revenue.
- **Action needed:** In live mode, filter successful Payments to the prior 30 calendar days, exclude
  non-settled/refunded records as appropriate, and reconcile count, gross amount, fees, net amount,
  currency, and order IDs to the commerce ledger. Record aggregates only.
- **Priority:** CRITICAL
- **Estimated time:** 15–30 minutes.

### 16. Paid payout reached the business bank

- **Status:** NEEDS VERIFICATION
- **Current value:** No Stripe payout record, production payout ledger, or bank statement was
  available.
- **Action needed:** Select at least one live payout marked paid, match its amount/currency/date and
  masked destination to the bank credit, and record the reconciliation date and reviewer. Resolve
  timing/fee differences rather than forcing an exact match without explanation.
- **Priority:** CRITICAL
- **Estimated time:** 15–30 minutes; 2–7 business days may be needed for the first payout to settle.

### 17. Dispute rate and open cases healthy

- **Status:** NEEDS VERIFICATION
- **Current value:** No live dispute data was available. A universal “below 1%” statement is only an
  internal alert threshold; card-network monitoring programs use specific metrics, windows, and
  regional rules that must be checked in Stripe's current account guidance.
- **Action needed:** Record disputes and the relevant transaction denominator for a defined period,
  calculate the rate consistently, review Stripe's current monitoring status, and submit truthful,
  relevant evidence for every open case before its displayed deadline. Never fabricate evidence.
- **Priority:** HIGH
- **Estimated time:** 15–45 minutes; evidence preparation varies by case.

### 18. Refund rate below internal 5% threshold

- **Status:** NEEDS VERIFICATION
- **Current value:** No live payment/refund data was available. The 5% value is an internal operating
  threshold, not proof of a universal Stripe requirement.
- **Action needed:** Define whether the KPI is refund count or refunded value divided by settled
  payment count/value, calculate both for the same 30-day cohort, segment by SKU/reason, and review
  every anomaly. Keep refunds behind the existing human-approval control.
- **Priority:** MEDIUM
- **Estimated time:** 20–45 minutes.

## Phase 6 — Security and monitoring

### 19. Two-factor authentication enabled

- **Status:** NEEDS VERIFICATION
- **Current value:** No Stripe team/security settings were available.
- **Action needed:** Require phishing-resistant passkeys or security keys where Stripe supports
  them; otherwise use authenticator apps. Review every team member, remove stale access, retain
  recovery codes securely, and avoid SMS as the primary factor where alternatives are available.
- **Priority:** CRITICAL
- **Estimated time:** 10–20 minutes per user.

### 20. Operational email notifications enabled

- **Status:** NEEDS VERIFICATION
- **Current value:** No Dashboard communication preferences or mailbox delivery evidence was
  available. Application configuration contains optional escalation destinations but does not
  prove Stripe notifications.
- **Action needed:** Enable appropriate payment, dispute, payout failure/status, and account warning
  notifications for a monitored finance/operations distribution address. Trigger a safe test where
  supported and verify mailbox rules, spam handling, escalation ownership, and after-hours coverage.
- **Priority:** HIGH
- **Estimated time:** 10–20 minutes.

### 21. API keys recently reviewed/rotated

- **Status:** NEEDS VERIFICATION
- **Current value:** No key metadata, creation/last-used dates, access inventory, or rotation record
  was available. Secret values were not sought.
- **Action needed:** Inventory key IDs, scopes, owners, creation dates, last-used dates, and consuming
  workloads. Immediately rotate any key shared during development or exposed outside the secret
  manager. Use overlap rotation (add new, deploy, verify, revoke old), restricted keys and least
  privilege, then record approver and rollback. Rotate webhook secrets separately with a planned
  cutover.
- **Priority:** CRITICAL
- **Estimated time:** 30–90 minutes per integration, plus deployment observation time.

### 22. Customer-recognizable statement descriptor

- **Status:** NEEDS VERIFICATION
- **Current value:** No live account statement descriptor was available.
- **Action needed:** Have the owner confirm the descriptor meets Stripe's current country/account
  rules, is recognizable as ClearGlass Inc., and matches customer-facing receipts/support details.
  The prompt's 5–22 character range should be validated in the live form because constraints vary
  by descriptor type and payment configuration. Test with an authorized low-value live transaction
  only after all critical gates pass, then refund it through the governed process if appropriate.
- **Priority:** HIGH
- **Estimated time:** 5–15 minutes plus statement-posting time for end-to-end confirmation.

## Ordered remediation plan

| Step | Owner | Action and exit evidence | Items | Estimate |
|---:|---|---|---|---|
| 1 | Stripe account owner | Sign in directly, confirm live environment, team 2FA, alerts, business requirements, capabilities, and permitted-business status. Export/redact dated screenshots or attestations. | 1, 3, 8, 19, 20 | 30–90 min plus review time |
| 2 | Finance owner + second reviewer | Validate masked bank destination/currencies, payout enablement/schedule, holds/reserves, descriptor, and finance approval. | 4–6, 9, 22 | 30–60 min plus bank verification |
| 3 | Platform owner | Inventory production key IDs/prefixes/scopes and rotate exposed or stale credentials using the secret manager; never disclose values. | 2, 21 | 30–90 min/integration |
| 4 | Backend engineer | Add production startup validation, fail-closed webhook configuration, Stripe exception translation, explicit version policy, and focused tests. | 2, 11, 13, 14 | 1 engineering day |
| 5 | Platform owner + backend engineer | Verify live webhook registration, required checkout and payout subscriptions, TLS/reachability, signed delivery, 2xx response, redacted audit event, and retry/idempotency behavior. | 10, 11 | 30–60 min |
| 6 | Commerce owner | Confirm live card methods, create live objects/Payment Links, review SKUs/prices/tax/refund terms, obtain human approval, update both storefront maps, and run canonical smoke tests. | 7, 12 | 30–90 min after gates |
| 7 | Finance owner | Reconcile 30-day successful payments, at least one paid payout to the bank, disputes, and refunds using defined denominators. | 15–18 | 45–120 min after settlement |
| 8 | Release owner | Observe checkout/webhook/payout metrics, warnings, and reconciliation for 24–48 hours. Roll back public Payment Links to empty values if a critical invariant fails. | all | 24–48 h observation |

## Required launch evidence

The account may be labeled **Live & Earning** only when an authorized reviewer supplies all of the
following without exposing sensitive values:

- dated live-mode/account-capability attestation with no due verification requirements;
- masked bank destination and currency match, payout schedule/status, and two-person review;
- production key **IDs/prefixes/scopes** and rotation dates—not key values;
- enabled webhook endpoint, subscribed event list, recent successful signed delivery ID/time, and
  correlated application audit record;
- explicit Stripe API/webhook version and pinned SDK review record;
- a successful live payment reconciled through order, Stripe balance, paid payout, and bank credit;
- 30-day payment/refund/dispute aggregates with defined denominators;
- 2FA/team-access review, monitored alerts, descriptor verification, and rollback owner.

## Rollback and safety boundary

If checkout, webhook verification, account capabilities, bank matching, reconciliation, or account
security fails, remove/empty the Payment Links in both public checkout maps and redeploy. This
returns the site to confirmed-invoice/Interac fallback without changing Stripe objects. Revoke only
the affected key after the replacement is deployed and verified. All live pricing, refund, payment,
payout, tax, and fulfillment changes remain human-approved, logged, and reversible; this audit does
not authorize a charge, refund, payout, schedule change, or account configuration mutation.
