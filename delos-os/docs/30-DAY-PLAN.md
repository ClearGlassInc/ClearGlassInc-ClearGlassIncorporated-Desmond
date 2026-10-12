# DELOS OS 30-day build plan

Start: October 12, 2026. Target pilot-readiness review: November 11, 2026. Dates represent milestones, not a guarantee of production launch.

## Days 1–4 · Safe command console (Oct 12–16)

Deliverable: isolated Next.js app, responsive command console, Operation Glassfall fixtures, documented scope, start/pause/advance/stop controls.
KPIs: app build succeeds; no root package/workflow edits; 7 personas visible; every action marked synthetic.
Gate: design and accessibility review; branch preview reviewed before merge.

## Days 5–8 · Deterministic simulation kernel (Oct 17–20)

Deliverable: typed world state, scheduled injects, risk scoring, approval requests, checkpoints, forks, restore, and tests.
KPIs: 8 unit tests; 72 simulated hours completes; invalid events rejected; stop freezes transitions.
Gate: test and typecheck green; deterministic replay from same seed gives the same world outcome (apart from timestamps/IDs).

## Days 9–14 · Auth and persistent data model (Oct 21–26)

Deliverable: OAuth/OIDC integration design, tenant-scoped RBAC middleware, PostgreSQL migrations and repository interface, Redis event queue.
KPIs: 100% routes default-deny before role grant; cross-tenant tests all denied; migration runs only in non-production with verified DATABASE_URL.
Gate: separate requester/approver test, session expiry test, and restore test pass.

## Days 15–19 · Governed persona/provider runtime (Oct 27–31)

Deliverable: synthetic provider interface and provider-pluggable persona proposals, server-side schema validation, policy gate, approval expiry/state-version checks, Markdown and JSON exports.
KPIs: current synthetic provider reports zero external side effects; all high-risk proposals are event-linked and approval-gated; every rejected proposal has a policy reason.
Gate: threat-model review, dependency audit, and reviewed prompt-injection tests.

## Days 20–24 · Observability and branch analysis (Nov 1–5)

Deliverable: structured metrics/traces, queue failure handling, report KPIs, scenario replay and branch comparison.
KPIs: event-to-audit correlation 100%; failed worker jobs visible; report references timeline event IDs; replay mismatch test fails closed.
Gate: incident-response and data-retention review.

## Days 25–30 · Controlled pilot readiness (Nov 6–11)

Deliverable: staging deployment, operator runbook, backup/restore evidence, pilot exercise, customer boundary and consent copy.
KPIs: critical/high security findings = 0 before pilot; all required CI gates pass; exercise completed with audit coverage and after-action report.
Gate: explicit human authorization for production integration and any external connector. Do not launch if auth, tenant isolation, approvals, or backup/restore are unverified.
