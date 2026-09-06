# Website Design & Development — Growth Infrastructure

Status: additive public experience implemented; sensitive application services remain target-state and disabled. Owner approval is required before collection, AI processing, experiments, authentication, or deployment changes.

## Existing-site inspection and architecture map

`web-design.html` is a static GitHub Pages route with shared CSS/JavaScript, an existing light-crimson presentation, media showcase, Artemis reference architecture, services, process, FAQ, contact pathway, and generated internal links. The upgrade adds a scoped dark growth-system experience without removing those assets. GitHub Actions validates and builds a static Pages artifact; there is no server runtime on this route.

## Experience, UX, conversion, SEO, accessibility, and performance audits

The new information architecture follows problem → system → self-identification → transparent recommendation → human next step. The primary CTA enters the anonymous readiness scan. Semantic headings, native form controls, textual SVG equivalents, strong focus treatment, forced-color support, and reduced-motion rules keep essential content independent of JavaScript and graphics APIs. Metadata, canonical routing, sitemap membership, legacy content, and internal links remain unchanged. CSS/SVG is the active visual layer; WebGPU, WebGL, and Canvas are capability-detected but deliberately not initialized, avoiding an eager graphics payload. Existing external fonts, video, inline legacy code, and a large HTML document remain measured risks.

## Design tokens and component hierarchy

The scoped `growth-system` tokens define color, fluid spacing, typography, radius, shadow/glow, motion, content z-index, responsive breakpoints (900/580px), and compact control density. Components are `GrowthSystem → Hero + ControlLayer → ServiceLayers → ReadinessScan → DigitalTwin → IntelligenceLayer → ExperimentPreview`. Neon conveys active hierarchy; borders and text preserve meaning without glow.

## State machines and AI safety model

```text
Recommendation: OBSERVED → HYPOTHESIS → DRAFTED → HUMAN_REVIEW → APPROVED → STAGED → VERIFIED → PUBLISHED
                              └──────────── reject / revise ────────────┘

Experiment: DRAFT → REVIEWED → APPROVED → STAGED → ACTIVE → CONCLUDED → ARCHIVED
                         └── one-action rollback to signed last-known-good ──┘
```

Models are untrusted drafting components. They receive policy-filtered evidence, typed tools, bounded budgets, approved data sources, and no publishing capability. Recommendations must record evidence, confidence, benefit, effort, risk, data sources, model/prompt versions, reviewer, status, and append-only history. The public page sends no content to a model.

## Data model, API contracts, and authorization matrix

Target-state records: `Tenant`, `Workspace`, `Principal`, `Assessment`, `AssessmentAnswer`, `Recommendation`, `EcosystemNode`, `Evidence`, `Lead`, `ConsentEvent`, `Experiment`, `Variation`, `Approval`, `Version`, and `AuditEvent`. Every tenant record carries `tenant_id`; authorization is enforced server-side adjacent to every resource operation.

| API | Anonymous | Workspace member | Reviewer | Publisher |
|---|---:|---:|---:|---:|
| `POST /v1/readiness/evaluate` | allowed, no persistence | allowed | allowed | allowed |
| `POST /v1/leads` | consent + CSRF + rate limit | allowed | allowed | allowed |
| `GET /v1/workspaces/{id}` | deny | scoped | scoped | scoped |
| `POST /v1/recommendations/{id}/approve` | deny | deny | allowed | allowed |
| `POST /v1/releases/{id}/publish` | deny | deny | deny | explicit publisher + distinct approval |

Lead input uses a strict schema for name, business email, company, normalized HTTPS website, objective, platform, timeline, stage, optional budget, message, contact consent, and optional marketing consent. The server must reject unknown/oversized fields, verify origin and CSRF, use a honeypot, rate limits, bot scoring, an idempotency key, and duplicate protection. It writes the consent event and structured lead atomically, then queues confirmation and internal notification through an allowlisted provider. No server is deployed here, so lead capture remains disabled.

## Privacy data flow and analytics event dictionary

Browser → consent controller → first-party event endpoint → schema validation/bot filter → minimized event store → daily aggregates. Raw IP addresses are neither persisted nor used for fingerprinting. Withdrawal stops optional events; export/deletion resolves only consented identifiers. Default retention is 30 days for raw consented events and 13 months for non-identifying aggregates, subject to owner/legal approval.

| Event | Purpose | Consent | Fields | Retention / aggregation | Owner / deletion |
|---|---|---|---|---|---|
| `hero_cta_viewed`, `hero_cta_selected` | CTA usability | analytics | page, CTA id, coarse device | 30d / daily count | Growth / erase raw |
| `capability_node_opened` | content interest | analytics | node id | 30d / daily count | Product / erase raw |
| `readiness_scan_started`, `readiness_scan_completed` | scan completion | analytics | scan version, complexity only | 30d / funnel | Product / erase raw |
| `service_objective_selected` | pathway interest | analytics | objective id | 30d / daily count | Growth / erase raw |
| `case_study_section_viewed` | content engagement | analytics | section id | 30d / daily count | Content / erase raw |
| `contact_form_started`, `contact_form_submitted` | lead flow | contact for submit | form version, outcome | 30d; lead under policy | Sales / delete on request where lawful |
| `strategy_call_request_completed`, `download_completed` | conversion | contact or analytics | artifact/action id | 30d / daily count | Growth / erase raw |

No analytics events are emitted by the current implementation because `ENABLE_ANALYTICS=false`.

## Threat model

| Threat | Surface / impact / likelihood | Prevention | Detection / response / residual risk |
|---|---|---|---|
| Cross-tenant access / BOLA | APIs; disclosure; medium | tenant-scoped queries, ABAC, deny default | authorization-denial alerts; revoke and investigate; implementation defects remain |
| Prompt injection / exfiltration | content and tools; disclosure/action; high | untrusted-content boundary, typed tools, egress allowlist | tool/audit anomaly alerts; disable model/tool; novel attacks remain |
| Form abuse | public lead API; spam/cost; high | origin/CSRF, rate limit, honeypot, idempotency | abuse thresholds; block and expire data; distributed bots remain |
| Credential/session compromise | auth; account control; medium | passkeys/MFA, short sessions, rotation, secure cookies | impossible-travel/token replay signals; revoke; endpoint compromise remains |
| Webhook forgery/replay | providers; false actions; medium | signature, timestamp, nonce, idempotency | signature-failure alerts; quarantine; provider-key compromise remains |
| Supply chain / malicious upload | build or files; execution; medium | pinned actions, scanning, content-type/size checks, isolation | provenance/EDR alerts; rollback/quarantine; zero-days remain |
| Tracking misuse | event pipeline; privacy harm; medium | consent, minimization, retention, no fingerprinting/sale | privacy audit; disable/export/delete; operator misuse remains |
| Hallucination / unauthorized publishing | AI workflow; false claims; high | evidence requirements, state machine, distinct approval | eval and audit alerts; revert and review; reviewer error remains |
| Insider misuse / configuration drift | admin/runtime; broad; medium | least privilege, separation, signed config | immutable audit/drift alerts; revoke/rollback; privileged collusion remains |

## CI/CD, cloud deployment, performance budget, tests, and rollback

The current Pages flow remains source → site checks → static artifact → artifact upload → protected Pages deployment. A future API should use separate build and deploy identities, SBOM/provenance, SAST/dependency/secret scans, policy tests, a protected environment, canary health gates, and signed rollback. It must not share browser credentials or Pages deployment authority.

Budgets: HTML ≤ 140 KB, page-specific JavaScript ≤ 20 KB minified, page-specific CSS ≤ 24 KB minified, eager images ≤ 250 KB each, zero eager GPU libraries, CLS ≤ 0.1, LCP ≤ 2.5s, INP ≤ 200ms. CI should reject missing security headers, unapproved third-party origins, accessibility regressions, and budget overruns.

Verification covers feature-flag defaults, forbidden network/storage behavior, no-JavaScript content, keyboard/focus semantics, reduced motion, SEO/internal links, asset integrity, static build, and browser accessibility/performance. Rollback is `git revert <release-commit>` followed by the same checks and an approved Pages deployment. Data rollback for a future API uses forward-only schema repair plus restoration of signed application versions; append-only audit and consent events are never rewritten.

## Staged implementation, production checklist, and roadmap

1. **Now:** static hero, service architecture, anonymous deterministic scan, demo twin, disabled AI/experiment controls.
2. **Review:** content, accessibility, privacy, threat model, measurement schema, and performance budgets.
3. **Backend pilot:** separate authenticated API, tenant policy, validated lead flow, consent ledger, notifications, and audit store.
4. **Controlled intelligence pilot:** offline recommendations only; evaluation and reviewer workflow before any staging capability.
5. **Measurement:** consented first-party aggregates; no experiment until baseline quality and guardrails are approved.

Production readiness requires named owners, data classification, DPA/provider review, threat-model sign-off, accessibility audit, load/abuse tests, restoration test, protected environment verification, alert ownership, incident runbook, and post-release observation. The first recommended experiment is a static primary-CTA label comparison using aggregate CTA-selection rate and guardrails for scan completion, accessibility errors, and page performance; no automatic publication is permitted.
