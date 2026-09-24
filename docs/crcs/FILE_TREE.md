# CRCS — Target file tree

Only CRCS-relevant paths are shown. Markers:

- **EXISTS** — on `main` today, used as is
- **CHANGE Pn** — existing file modified in phase *n*
- **NEW Pn** — created in phase *n*
- **DEFERRED** — not created until the stated trigger
- **DONE P0** — Phase 0 change made; evidence in
  [IMPLEMENTATION_SEQUENCE.md](IMPLEMENTATION_SEQUENCE.md#phase-0-status)

Phase numbers match [IMPLEMENTATION_SEQUENCE.md](IMPLEMENTATION_SEQUENCE.md).

```text
.
├── index.html                                   CHANGE P0  lead form target: owner decision on the form relay (S6)
├── revenue-command.html                         DONE P0    cockpit and admin-key field removed; opaque reference; session-scoped
│                                                           UTM; form hidden until an API host is set; honeypot hidden from AT
│                                                CHANGE P1  becomes a redirect to /start/
├── start/
│   └── index.html                               NEW P1     multi-step qualification, error summary, consent
├── payment-status.html                          NEW P1     VERIFYING / CONFIRMED from the API, never from the URL
├── services.html                                NEW P1     four-rung ladder, one primary CTA per offer
├── methodology.html                             NEW P1     how a diagnostic and an audit are run; stated limits
├── proof.html                                   DEFERRED   methodology validation; trigger: first delivered engagement with written permission
├── offers/
│   ├── rapid-diagnostic.html                    NEW P1     entry offer page (Q1, Q3)
│   ├── revenue-systems-audit.html               NEW P1     core offer page
│   ├── thank-you.html                           EXISTS     reused as the lead confirmation page
│   ├── security-quick-audit.html                CHANGE P1  retire or redirect per the single entry price (S5)
│   ├── hardening-sprint.html                    CHANGE P0  form target (S6)
│   ├── phipa-readiness.html                     CHANGE P0  form target (S6)
│   └── canada-us-control-assessment.html        CHANGE P0  form target (S6)
├── blog/                                        EXISTS     insights listing; content-to-offer mapping DEFERRED to P2
├── legal/
│   ├── privacy.html                             CHANGE P0  name processors, disclose browser storage (owner approval: public text)
│   │                                            CHANGE P1  CRCS retention, consent withdrawal, request process
│   ├── terms.html                               CHANGE P1  service terms and refund policy (Q3)
│   ├── accessibility.html                       EXISTS     add CRCS feedback route in P1
│   ├── cookies.html                             NEW P1     storage and analytics preferences
│   └── responsible-disclosure.html              NEW P1     human-readable page for the route in .well-known/security.txt
├── assets/
│   ├── css/crcs-tokens.css                      NEW P1     Command Realm design tokens (one file)
│   └── js/crcs-form.js                          NEW P1     shared validation, error summary, attribution, analytics beacon
├── sitemap.xml                                  CHANGE P1  new public pages
├── tools/internal_links.py                      CHANGE P1  register new pages (PAGES + cluster)
├── sw.js                                        CHANGE P1  bump VERSION when pages change
│
├── control-plane/
│   ├── .env.example                             DONE P0    CRCS_AUDIT_HASH_KEY
│   │                                            CHANGE P1  every new setting, with safe defaults
│   ├── app/
│   │   ├── main.py                              DONE P0    /metrics and /events behind require_admin
│   │   ├── config.py                            DONE P0    crcs_audit_hash_key
│   │   │                                        CHANGE P1  new settings (test_settings_references.py enforces)
│   │   ├── models.py                            DONE P0    leads.public_ref
│   │   │                                        CHANGE P1  Phase 1 tables (DATA_MODEL.md §4)
│   │   ├── schemas.py                           DONE P0    RevenueLeadReceipt; checkout takes `reference`
│   │   │                                        CHANGE P1  tightened enums, allow-listed analytics
│   │   ├── revenue_service.py                   DONE P0    is_spam_trap
│   │   │                                        CHANGE P1  consent rows, free-text split, delivery tasks
│   │   ├── rbac.py                              NEW P1     users, scrypt, TOTP (stdlib), sessions, require_role
│   │   ├── consent.py                           NEW P1     signed unsubscribe and withdrawal tokens
│   │   ├── crcs_offers.py                       NEW P1     offers repository, seeded from pricebook.json
│   │   ├── notifications.py                     NEW P1     internal owner alerts
│   │   ├── integration_health.py                NEW P1     record success and failure per adapter
│   │   ├── retention.py                         NEW P1     dry-run report only; deletion job P2 after Q7
│   │   ├── adapters/
│   │   │   ├── __init__.py                      NEW P1     Protocols, timeout and retry policy, health hook
│   │   │   ├── payment_stripe.py                NEW P1     wraps payments.py; adds idempotency key
│   │   │   ├── payment_manual.py                NEW P1     MANUALLY_RECONCILED with evidence, ADMIN only
│   │   │   ├── calendar_link.py                 NEW P1     booking-URL handoff with manual fallback
│   │   │   ├── calendar_calendly.py             NEW P1     signed booking webhook (BLOCKED Q5)
│   │   │   ├── email_log.py                     NEW P1     renders and stores drafts; sends nothing
│   │   │   ├── email_provider.py                DEFERRED   trigger: Q5 names a provider
│   │   │   ├── crm_internal.py                  NEW P1     internal tables are the system of record
│   │   │   ├── crm_external.py                  DEFERRED   trigger: owner adopts an external CRM
│   │   │   ├── analytics_first_party.py         NEW P1     analytics_events, allow-list enforced
│   │   │   ├── bot_turnstile.py                 NEW P1     verifier present, disabled by default
│   │   │   └── storage_links.py                 NEW P1     link references only; uploads DEFERRED
│   │   ├── routers/
│   │   │   ├── revenue.py                       DONE P0    receipt with opaque reference; silent honeypot; keyed-hash
│   │   │   │                                               audit target; cockpit no longer 500s on SQLite
│   │   │   │                                    CHANGE P1  require_role, offers, consent, checkout-status
│   │   │   ├── auth.py                          NEW P1     login, TOTP verify, logout, session list
│   │   │   ├── calendar_webhook.py              NEW P1     /webhooks/calendar
│   │   │   └── payments.py                      EXISTS     Stripe webhook; provisions only from verified live events
│   │   └── data/
│   │       ├── pricebook.json                   CHANGE P1  Stripe Price id for the chosen offer (owner creates it)
│   │       └── offers.seed.json                 NEW P1     four offers; prices marked PLACEHOLDER until Q3
│   ├── migrations/
│   │   ├── 008_lead_public_ref.sql              DONE P0    leads.public_ref UUID, backfilled, unique
│   │   └── 009_crcs_phase1.sql                  NEW P1     DATA_MODEL.md §4
│   └── tests/
│       ├── test_rbac.py                         NEW P1     role matrix, lockout, MFA, session expiry
│       ├── test_consent.py                      NEW P1     grant, withdraw, unsubscribe token tamper
│       ├── test_crcs_offers.py                  NEW P1     disabled offers never public; price not in offers table
│       ├── test_calendar_webhook.py             NEW P1     bad signature rejected; booking cannot lose a lead
│       ├── test_analytics_allowlist.py          NEW P1     free text and unknown keys never stored
│       ├── test_payment_status.py               NEW P1     success URL alone never yields CONFIRMED
│       ├── test_crcs_webhook_provisioning.py    NEW P1     redelivered checkout event books one order; test-mode
│       │                                                   and unverified events never provision a service order
│       ├── test_crm_failure.py                  NEW P1     adapter failure keeps the lead and raises a notification
│       ├── test_migration_parity.py             NEW P1     models match numbered migrations
│       ├── test_revenue_routes.py               DONE P0    receipt shape, silent honeypot, reference-only checkout,
│       │                                                   no email in the ledger, admin-only ledger and metrics
│       └── test_route_auth_coverage.py          CHANGE P1  recognise require_role
│
├── admin/
│   ├── app/api/login/route.ts                   DONE P0    same-origin redirect only, constant-time compare, lockout,
│   │                                                       303, fails closed in production with no token
│   │                                            CHANGE P1  delegates to control-plane /auth (per-user, TOTP)
│   ├── app/api/auth/login/route.ts              DONE P0    same guard; its own `next` check was bypassable
│   ├── app/login/page.tsx                       DONE P0    reads the async searchParams; accessible error message
│   ├── middleware.ts                            DONE P0    default deny via lib/route-policy.ts
│   ├── lib/login-guard.ts                       DONE P0    safeNextPath, constantTimeEqual, LoginThrottle
│   ├── lib/route-policy.ts                      DONE P0    which paths are public
│   ├── lib/api.ts                               DONE P0    server-only; sends ADMIN_API_KEY to the control plane
│   ├── tests/login-guard.test.mjs               DONE P0    node --test; run by tests/test_admin_login_guard.py
│   ├── app/revenue/page.tsx                     DONE P0    read-only cockpit: warning, figures with definitions,
│   │                                                       health, leads, control log
│   │                                            CHANGE P1  due-action focus, links to lead records
│   ├── app/revenue/leads/page.tsx               NEW P1     pipeline list, filters, stage change
│   ├── app/revenue/leads/[ref]/page.tsx         NEW P1     lead record, timeline, consent, free text (audited)
│   ├── app/revenue/control-log/page.tsx         NEW P1     Revenue Control Log
│   ├── app/revenue/delivery/page.tsx            NEW P1     delivery workspace
│   └── app/revenue/drafts/page.tsx              NEW P1     draft queue; send requires approval
│
├── tests/test_crcs_public_page.py              DONE P0    no admin credential on any public page; storage; fallback
├── tests/test_admin_login_guard.py              DONE P0    runs the admin Node suite inside the root pytest gate
├── e2e/crcs/                                    NEW P1     Playwright: lead persisted, checkout created, webhook
│                                                           idempotent, role access, consent withdrawal, CRM failure,
│                                                           keyboard-only qualification, error states
├── scripts/
│   ├── ci_local.py                              CHANGE P1  add CRCS gates (authoritative while Actions is down)
│   └── crcs_launch_gate.py                      NEW P1     production env validation; exits non-zero on any BLOCKED item
├── .github/workflows/crcs.yml                   DEFERRED   trigger: Actions dispatches runners again (BASELINE F1, §11)
├── render.yaml                                  CHANGE P1  AUTO_CREATE_TABLES=false; pre-deploy migration; CRCS env keys
│
├── adr/0002-crcs-extend-existing-control-plane.md   NEW P0 (this change)
└── docs/crcs/
    ├── README.md, ARCHITECTURE.md, DATA_MODEL.md    NEW P0 (this change)
    ├── FILE_TREE.md, IMPLEMENTATION_SEQUENCE.md     NEW P0 (this change)
    ├── OWNER_CONFIRMATION_CHECKLIST.md              NEW P0 (this change)
    ├── runbooks/                                    NEW P1  incident, backup-restore, deploy-rollback, launch checklist,
    │                                                        weekly revenue review, access review, privacy requests
    └── revenue-pack/                                NEW P1  form copy, DRAFT FOR APPROVAL templates, discovery agenda,
                                                             audit scope, proposal, confirmations, 7-day plan
```

## Why no new workflow file

Actions dispatches no runners (`docs/BASELINE.md` F1). A workflow added now reports
nothing, and a missing check reads as a passing one. The CRCS gates go into
`scripts/ci_local.py`, which runs offline and exits non-zero on failure. The workflow is
written when F1 is cleared and its first run can be observed.
