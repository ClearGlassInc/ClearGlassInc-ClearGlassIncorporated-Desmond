# ClearGlassInc Platform Audit

**Prepared for:** ClearGlassInc — founder Desmond Otieno Odhiambo
**Scope:** Full monorepo (`ClearGlassInc.github.io`) — static site, commerce OS, agents, workflows
**Posture:** Principal-architect review. High-impact, non-breaking improvements over cosmetics.

> **Status of this document.** Section 1–5 below is the assessment and plan. Two
> high-value items from it are now shipped: **admin authentication on the commerce
> control plane** (§2, item 1) and **approver identity binding** (§2, item 2 — every
> approval decision is now attributed to the authenticated credential, not a
> self-asserted request field). The rest is a ranked roadmap, not yet built.

---

## 1. Repository assessment

### What the repo does well

- **The commerce OS is genuinely good engineering.** `clearglass-commerce/control-plane`
  is typed Python, small and readable (~1,900 LOC), with a real safety model:
  `governance.py` scores every action 0–100 and `service.py` runs a single
  score → gate → execute → audit pipeline. It **fails closed** (unknown actions default to
  high risk), keeps money-movement modules stdlib-only so they run in minimal CI, and has a
  real test suite. This is the crown jewel and the right thing to build the platform around.
- **Payments are handled with discipline.** Stripe webhooks are signature-verified, the app
  runs in safe mock mode with no key, payout bank metadata is masked, and the audit ledger
  redacts secret-looking fields (`audit.py::_SECRET_KEYS`).
- **The static site has a real internal-linking system** (`tools/internal_links.py`),
  generated and idempotent, with a `--check` freshness gate — better than most marketing sites.
- **CI breadth exists** — 41 workflows cover Pages deploy, commerce gates, security scans,
  and scheduled loops.

### What is missing or blocking top-tier status

1. **The approval gate had no lock on the door (now fixed).** Every mutating admin endpoint
   — approve/reject, live pricing, refunds, catalog writes — was unauthenticated, and
   `decided_by` was a self-asserted string. The entire safety model rested on a gate anyone
   on the network could open. *This audit closes it (see §2.1).*
2. **Documentation bloat is drowning the real system.** 36 root-level `.md` files (~772 KB),
   **26** of them overlapping "ARTEMIS / OS / blueprint" vision docs (`ARTEMIS_AIP_ARCHITECTURE`,
   `ARTEMIS_SELF_EVOLVING_PLATFORM_BLUEPRINT`, `CLEARGLASSINC_ARTEMIS_*` ×6, `JARVIS_OS`,
   `PERCIVAL_OS`, `KIMI_K3` …). Most describe unprovisioned target states. A newcomer cannot
   tell what is real from what is aspirational — the #1 barrier to trust and handoff.
3. **Binary bloat at the repo root.** ~8 MB of images sit outside `assets/`, including
   **three ~1 MB copies of the same logo** (`logo.png`, `Logo.png`, `ClearGlass Logo.png` —
   case-only duplicates that also break on case-insensitive checkouts) and a 2.6 MB iOS
   screenshot with `.webp` variants. This bloats every clone and Pages deploy.
4. **CI sprawl with no clear ownership.** 41 workflows include overlapping/ambiguous pipelines
   (`agent-army`, `agent-army-crypto`, `burlington-military-op`, `clearglassinc-military-op`,
   `burlington-release`, `artemis-deploy`, `dispatch-all-workflows`). Many are scheduled loops
   that cost minutes and can mask real failures. No single "what must stay green" contract
   beyond the three commerce gates in `CLAUDE.md`.
5. **Superseded code kept alongside active code.** `apps/autostore` + `apps/air-control`
   appear superseded by `clearglass-commerce/` (per `CLAUDE.md`) but remain, doubling the
   surface a reader must understand.
6. **Observability is log-level only.** No structured request logging, request IDs, metrics
   endpoint, or error tracking on the control plane. The audit ledger is excellent for
   *business* events but there's no *operational* telemetry (latency, error rate, health of
   scheduled loops).
7. **No dependency pinning / lockfile for the control plane.** `requirements.txt` pins a few
   packages by name; there's no hash-locked, reproducible install, which weakens the
   supply-chain story the `release-supply-chain.yml` workflow implies.

**Bottom line:** the core is strong and safe; the platform is held back by an unlocked admin
door (now fixed), documentation and asset bloat that obscure what's real, and CI/telemetry
that don't yet match the quality of the commerce core.

---

## 2. Best upgrade opportunities (ranked by leverage)

| # | Upgrade | Why it's high-leverage | Effort |
|---|---------|------------------------|--------|
| **1** | **Admin auth on the control plane** ✅ *shipped in this change* | The safety model is only real if the gate is locked. Highest risk-reduction per line. | S |
| 2 | **Approver identity binding + audit** ✅ *shipped* | Record the *authenticated* principal on every approval, not a self-asserted `decided_by`. Completes item 1. | S |
| 3 | **Observability layer** (request IDs, structured logs, `/metrics`, error tracking) | Turns a demo into an operable service; prerequisite for scaling under load. | M |
| 4 | **Documentation consolidation** | Collapse 26 blueprint docs into one `docs/` tree with clear "real vs. target" status banners. Biggest trust/maintainability win. | M |
| 5 | **Repo weight reduction** | Move root images to `assets/`, dedupe the 3 logos, drop superseded `apps/`. Faster clone/deploy, less confusion. | S |
| 6 | **CI consolidation + cost control** | Merge overlapping workflows, define one required-checks contract, gate scheduled loops behind concurrency + failure alerting. | M |
| 7 | **Dependency locking / reproducible builds** | Hash-locked installs for the control plane; Dependabot already exists — wire it to a lockfile. | S |
| 8 | **Rate limiting + idempotency keys** on money endpoints | Defense-grade hardening for checkout/refund under abuse or retries. | M |
| 9 | **Retrieval/knowledge layer over the governed ledger** | The `events` audit ledger + catalog is a ready-made corpus; a read-only RAG "ask the operator" surface is real leverage *without* touching the write path. | L |
| 10 | **Idempotent, resumable daily loop with alerting** | The scheduled governance loop should be observable and page on failure, not fail silently. | M |

---

## 3. Refactor plan (what to change, simplify, remove)

**Build next**
- `app/security.py` — admin bearer auth + fail-closed startup. **(done)**
- `app/observability.py` — request-ID middleware, structured JSON logging, `/metrics`.
- Approver-identity plumbing: thread the `require_admin` principal into `approvals._decide`
  and the audit `actor`, replacing self-asserted `decided_by`.

**Simplify**
- **Docs:** create `docs/` with `docs/architecture/` (real systems) and
  `docs/vision/` (target-state, each with a status banner). Replace the 26 root blueprints
  with **one** canonical architecture doc + a vision index. Keep `CLAUDE.md`, `README`,
  `DEPLOY.md`, `CONTRIBUTING`, `SECURITY`.
- **Workflows:** collapse `agent-army*`, `*-military-op`, `burlington-*`, `artemis-deploy`,
  `dispatch-all-workflows` into a small, named set. Add a `concurrency:` group to every
  scheduled workflow and a failure notification.

**Remove / archive** (confirm with maintainer first)
- Superseded `apps/autostore` and `apps/air-control` — archive to a branch/tag, drop from `main`.
- Duplicate root images: keep one `assets/brand/logo.png`; delete `Logo.png` +
  `ClearGlass Logo.png`; move the iOS screenshots into `assets/` or drop if unused.

**Do not touch** (working invariants)
- `governance.py`, `service.py`, `audit.py` risk logic — the gate is correct; only *add*
  access control around it, never a bypass.
- The Stripe webhook signature path and mock-mode behavior.
- The generated internal-link blocks — regenerate via the tool, never hand-edit.

---

## 4. Implementation plan (per major upgrade)

### 4.1 Admin authentication ✅ (shipped)
- **Purpose:** make the approval gate meaningful — only credentialed operators can approve,
  price, refund, or write catalog/inventory.
- **Architecture:** `app/security.py` exposes `require_admin` (FastAPI dependency, constant-time
  `hmac.compare_digest`, comma-separated keys for rotation) and `verify_startup_posture`
  (fails closed when `APP_ENV=production` and no `ADMIN_API_KEY`). Wired at the router level for
  `store`/`orders`/`inventory`/`approvals` and per-endpoint for `/payments/refund`. Customer
  checkout, the signature-verified webhook, and read-only telemetry stay open.
- **Dependencies:** none new (stdlib `hmac` + existing FastAPI).
- **Risks:** locking out a caller that isn't configured with the key → mitigated by open
  dev/mock default and a loud startup warning; `render.yaml` now `generateValue`s the key.
- **Testing:** 12 tests in `tests/test_security.py` (open mode, 401/403/valid, rotation,
  fail-closed startup). Full suite: **41 passed**, ruff clean.
- **Rollout:** already backward-compatible (dev unchanged). Production: set `ADMIN_API_KEY`,
  redeploy, confirm `GET /health → admin_auth: enabled`, give the admin UI the same key.

### 4.1b Approver identity binding ✅ (shipped)
- **Purpose:** make the audit ledger truthful — a pricing/refund approval must be
  attributable to *who actually held the credential*, not to a name typed into the
  request body. This is what turns "the gate is locked" (§4.1) into "we know who
  opened it."
- **Architecture:** `routers/approvals.py` now captures the principal returned by
  `require_admin` (already applied router-wide) and resolves the decider via
  `_resolve_decider`: the authenticated credential is authoritative, so `admin` is
  written to both `Approval.decided_by` and the audit `actor`. The self-asserted
  `DecisionRequest.decided_by` is demoted to an optional display label and preserved
  only as an `asserted_by` annotation in the event payload when it differs. Open
  dev/mock mode (no key) falls back to the request label for readability, matching the
  platform's existing open-mode philosophy.
- **Dependencies:** none new — reuses the existing `require_admin` dependency and audit
  writer.
- **Risks:** none to the write path; governance/scoring untouched. Backward-compatible
  in dev (labels still flow through).
- **Testing:** two new tests in `tests/test_resilience.py` assert the credential —
  not the body — is recorded as `decided_by`/`actor`, and that the self-asserted label
  is preserved as `asserted_by`. Full suite: **52 passed**, ruff clean.

### 4.2 Observability layer
- **Purpose:** operate the service under real load; see latency/errors, correlate requests.
- **Architecture:** ASGI middleware assigning an `X-Request-ID`, JSON structured logs keyed by
  request ID + actor, a Prometheus-style `/metrics` (or lightweight counters), and optional
  Sentry DSN. Keep money modules stdlib-only; put telemetry in its own module so CI minimalism
  holds.
- **Dependencies:** `structlog` (or stdlib `logging` JSON formatter); optional `sentry-sdk`.
- **Risks:** log volume/PII — reuse `audit.py::_SECRET_KEYS` redaction; sample high-volume paths.
- **Testing:** middleware unit tests (request ID propagation, redaction); a smoke test asserting
  `/metrics` shape.
- **Rollout:** additive; ship behind env flags, enable in staging first.

### 4.3 Documentation consolidation
- **Purpose:** make the repo trustworthy and handoff-ready; separate real from aspirational.
- **Architecture:** `docs/architecture/` (systems that exist, each with a "Status: LIVE" banner
  and a pointer to the code) + `docs/vision/` (target states, "Status: NOT PROVISIONED"). One
  `docs/README.md` index. Root keeps only the essentials.
- **Dependencies:** none.
- **Risks:** breaking inbound links / SEO for the static site — add redirects, keep the
  internal-link tool's `PAGES` map in sync, update `sitemap.xml`.
- **Testing:** `tools/internal_links.py --check`; a link-check CI step.
- **Rollout:** one PR that moves + banners docs; no code behavior change.

### 4.4 Repo weight reduction
- **Purpose:** faster clones/deploys, less confusion.
- **Architecture:** consolidate brand assets under `assets/brand/`, dedupe logos, archive
  superseded `apps/`.
- **Risks:** a page references a moved/removed image → grep references first, add redirects.
- **Testing:** Pages build + link check; `git grep` for each removed filename.
- **Rollout:** staged — assets first (low risk), then `apps/` archival after maintainer sign-off.

### 4.5 CI consolidation
- **Purpose:** predictable, cheap, meaningful CI.
- **Architecture:** one required-checks contract (the 3 commerce gates + Pages + security);
  merge overlapping agent/release workflows; `concurrency:` + failure alerts on scheduled loops.
- **Risks:** dropping a workflow that something depends on → inventory triggers first.
- **Testing:** dry-run via `workflow_dispatch`; watch one full cycle before deleting anything.

---

## 5. Future direction — more advanced, intelligent, secure, and on-brand

ClearGlassInc's identity in this repo is a **governed, fail-closed, defense-grade autonomous
operator** — the differentiator is *trust*, not raw automation. Lean into that:

1. **Make "governed" the product, not a footnote.** Every autonomous capability should be
   demonstrably gated, authenticated, and audited. The auth work in this change is step one;
   identity-bound approvals, rate limits, and idempotency keys make the money path
   defense-grade. This is a moat competitors won't copy quickly.
2. **Grow intelligence on the read path first.** The append-only `events` ledger + catalog is a
   perfect corpus for a retrieval/"ask the operator" layer and for evaluation/benchmarking of
   agent decisions — all *read-only*, so it adds intelligence without ever risking the write
   path. Add offline evals that replay historical proposals and score the governor.
3. **Plugin-style agents around a stable core.** Keep `governance.py`/`service.py` as the
   immutable spine; let new agents register as governed action producers. New capability = new
   scored action type, never a new bypass. This is the scalable, event-driven architecture the
   vision docs gesture at — realized concretely.
4. **Observability as a first-class surface.** A live health/telemetry view (latency, error
   rate, loop status, approval backlog) turns the platform from "works in a demo" into "runs
   under pressure" — directly the "scale under pressure" ambition.
5. **Consolidate the vision, then execute it incrementally.** The 26 blueprints contain real
   ambition; the risk is they stay documents. Pick the top 2–3 (retrieval layer, agent
   orchestration on the governed core, telemetry) and ship them behind the same
   score → gate → audit discipline that already makes the commerce core trustworthy.

**Guiding principle:** every upgrade should make the platform *more trustworthy per feature*,
not just more capable. That is what makes ClearGlassInc feel like a serious technical platform
rather than a demo — and it is exactly what the existing commerce core already gets right.
