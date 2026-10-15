# ClearGlass Revenue Activation — Execution Record

**Audit date:** 2026-10-15  
**Repository:** `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond`  
**Status:** Prepared for review; production launch is blocked pending the gates below.

## Executive result

The revenue activation work has been advanced through a repository-backed execution record and a non-production review branch. No live Stripe objects, prices, payment links, account settings, payouts, charges, production deployments, or public site content were changed. No external messages were sent. No revenue, conversion, or fulfillment success is claimed.

## Evidence observed

- The Stripe live account is `acct_1RlYxRL8uR92FksU`; prior repository audit dated 2026-09-25 recorded Canada/CAD, charges enabled, payouts enabled, and details submitted. Re-check the Dashboard before launch because this repository record is point-in-time.
- The recent read-only Stripe checks returned CAD 0 available and CAD 0 pending balance, no registered webhook endpoints, and no PaymentIntents in the query. These results do not replace a complete historical charge/refund/dispute/payout reconciliation.
- The storefront (`store.html`) routes Security Quick-Audit to a hosted Payment Link and labels it CAD $249.
- The separate `checkout/index.html` hub routes a “90-Minute Cyber Risk Audit” to a different hosted Payment Link and labels it CAD $297. These may be intentionally different offers, but offer names, scope, product IDs, price IDs, and landing-page promises must be reconciled before sending traffic.
- The checkout hub contains live hosted links for the $297 audit and the $100/month and $1,000/year Business Protection plans.
- The repository's `STRIPE_SETUP.md` describes a control-plane checkout implementation with `/webhooks/stripe` and a separate `/subscriptions/webhook` endpoint, but the production host and current deployment of that control plane have not been verified.
- A Vercel project search for “ClearGlass” returned no matching projects. This is not proof that no production hosting exists; identify the actual host and repository/deployment linkage.
- The existing readiness documentation is dated 2026-09-25. Treat its account-status claims as historical until rechecked.

## Selected initial offer (proposal, not published)

**Security Quick-Audit — CAD $249**, using the existing storefront offer and its existing hosted Stripe Payment Link. Keep the existing price unchanged. Before launch, confirm the linked Stripe product/price, precise scope, deliverable, delivery window, exclusions, refund terms, privacy/data handling, tax treatment, and support path. Do not silently substitute the separate CAD $297 90-minute audit.

Proposed deliverable: a scoped, read-only security posture review and prioritized findings report. Exclude penetration testing, exploitation, incident response, remediation execution, continuous monitoring, legal advice, compliance certification, and guarantees unless separately scoped and approved. Any customer-facing delivery promise remains subject to owner approval.

## Blockers and acceptance criteria

### P0 — Reconcile product and checkout mapping
- [ ] Export/read the active Stripe Products, Prices, Payment Links, and their line items in the correct live account.
- [ ] Create one source-of-truth mapping: public offer slug → scope/version → Stripe Product ID → Price ID → Payment Link ID → amount/currency/interval.
- [ ] Decide whether CAD $249 Quick-Audit and CAD $297 90-Minute Audit are distinct SKUs. Keep both only if scope and copy clearly distinguish them.
- [ ] Verify every button reaches the intended hosted checkout and the amount displayed matches the Stripe Price.
- [ ] No live Price or Payment Link changes without explicit, offer-specific approval.

### P0 — Identify and secure the production checkout host
- [ ] Identify the actual production host, project, repository, domain, and deployment SHA.
- [ ] Verify TLS, deployment rollback, protected environment variables, access controls, and production/staging separation.
- [ ] Confirm the deployed application actually serves the checkout and webhook routes described in `STRIPE_SETUP.md`.
- [ ] Never place Stripe secret keys or webhook signing secrets in the repository, browser bundle, logs, or public issue text.

### P0 — Webhook-backed payment and fulfillment
- [ ] Deploy the webhook receiver to the verified host only after tests and owner approval.
- [ ] Register the required Stripe endpoints in the correct mode; use test mode first.
- [ ] Configure signing secrets in the host's secret store; verify signatures against the raw request body.
- [ ] Verify idempotent handling of checkout completion, asynchronous payment success/failure, refunds, disputes, subscription lifecycle, and payout events actually supported by the application.
- [ ] Prove duplicate webhook delivery cannot create duplicate orders or duplicate fulfillment.
- [ ] Treat the success redirect as UX only; payment status must come from verified Stripe events/API reconciliation.
- [ ] Use a durable order ledger and fulfillment queue; retain unmatched events for reconciliation.

### P1 — Customer terms and tax
- [ ] Approve offer scope, prerequisites, access method, delivery window, refund/cancellation policy, privacy/data-handling terms, and support contact.
- [ ] Confirm Canadian GST/HST registration and tax obligations with a qualified adviser; do not enable automatic tax until Stripe Tax registrations/product tax settings are correctly configured.
- [ ] Review subscription renewal, cancellation, failed-payment, and customer-portal behavior before selling recurring plans.

### P1 — Test-mode evidence
- [ ] Successful test payment produces one order with the correct SKU, amount, currency, customer reference, and payment state.
- [ ] Declined payment, abandoned checkout, asynchronous failure, forged signature, duplicate delivery, refund, dispute, and subscription renewal are exercised.
- [ ] Unknown SKU, tampered client-supplied amount, customer-ID substitution, and unauthorized fulfillment are rejected.
- [ ] CI, type checks, unit tests, security checks, and deployment preview pass; attach run URLs/commit SHA to the review.
- [ ] Reconcile test events against the order ledger; test events are never counted as revenue.

### P2 — Controlled launch and revenue measurement
- [ ] Owner approves the exact offer, copy, price, terms, host, endpoint, and launch window.
- [ ] Complete one owner-authorized production smoke test only after all preceding gates pass.
- [ ] Reconcile gross successful payments, refunds, disputes, Stripe fees, payouts, and bank deposits as separate figures.
- [ ] Report funnel metrics only when analytics events are actually instrumented and verified.
- [ ] Review daily during the first week; pause promotion on any mismatch, unverified webhook, duplicate fulfillment, or unexplained payment/order discrepancy.

## Revenue dashboard baseline

| Metric | Baseline | Evidence rule |
|---|---:|---|
| Verified gross payments | CAD $0 in the queried evidence | Not a complete historical accounting statement |
| Available Stripe balance | CAD $0 | Point-in-time balance read |
| Pending Stripe balance | CAD $0 | Point-in-time balance read |
| Registered webhook endpoints | 0 | Current endpoint-list result |
| PaymentIntents returned by query | 0 | Query result, not proof no checkout attempts occurred |
| Checkout conversion | N/A | Do not report until funnel instrumentation is verified |
| Fulfilled paid orders | Unverified | Requires order-ledger and delivery evidence |
| Bank deposits | Unverified | Reconcile against bank statement; do not infer from Stripe balance |

## Approval boundary

This record authorizes no production deployment, public publication, external outreach, live price/Payment Link/account change, payment, refund, or charge. The safe next step is test-mode implementation and evidence gathering on a review branch. Production launch remains blocked until the owner explicitly approves the exact production actions after reviewing the evidence.
