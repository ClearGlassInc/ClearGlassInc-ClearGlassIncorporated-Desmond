# PHOENIX — Autonomous Recovery / Self-Healing Audit

**Prepared for:** ClearGlassInc — founder Desmond Otieno Odhiambo
**Scope:** Recovery, resilience, and incident-response posture across the monorepo
**Posture:** Principal-architect + AI-SRE review. High-impact, non-breaking, safety-first.

> **Status of this document.** §1–5 are the assessment and plan. One high-value
> item — a **governed autonomous-recovery engine (PHOENIX)** — has already been
> built, tested, and shipped in this same change: `sentinel/sentinel/phoenix.py`,
> `sentinel/tests/test_phoenix.py` (27 passing proof tests), `phoenix_demo.py`, and
> [`sentinel/PHOENIX_RECOVERY_BRIEF.md`](sentinel/PHOENIX_RECOVERY_BRIEF.md). The
> rest is a ranked roadmap, deliberately **not** built yet — the repo's problem is
> not too few systems, it is too many half-real ones.

---

## 1. Repository assessment

### What the repo already does well (the recovery foundations exist)

- **A real fail-closed doctrine, in code.** `sentinel/sentinel/governance.py` (the
  SABER assurance gate), `governor.py` (deny-by-default `PolicyGovernor` that
  *degrades to deny-all when the audit ledger is unreachable*), and the commerce
  `governance.py` (0–100 risk scoring → gate → execute → audit) are genuinely good
  engineering and share one idea: **an action you cannot authorize or log does not
  run.** This is the correct backbone for self-healing.
- **A tamper-evident audit spine.** The hash-chained `audit.py` (both in `sentinel/`
  and `clearglass-commerce/control-plane/app/`) gives every decision a replayable,
  verifiable record — the precondition for "learn from every incident."
- **Resilience primitives already in the commerce plane.** `app/security.py` has
  per-IP rate limits, an idempotent Stripe webhook (`orders.external_ref`), and
  `GET /ready` DB-reachability. `test_resilience.py` exercises them.
- **Stdlib-only discipline** on the money-movement and governance modules keeps them
  runnable in minimal CI — the right constraint to preserve.

### What was missing (the recovery gaps)

The repo had **governance** and **audit**, but no closed *recovery loop* wiring them
to live failure signals. Concretely, before this change there was:

1. **No incident classification** — nothing mapped a failure signature to a handling
   strategy (retry vs. fallback vs. contain vs. escalate).
2. **No remediation gate** — the commerce governor scores *business* actions; nothing
   scored *recovery* actions for reversibility, blast radius, or confidence.
3. **No post-recovery verification** — no component insisted an incident stay open
   until an independent probe confirmed health was actually restored.
4. **No blast-radius containment step** — no "shed traffic / flag off before you fix."
5. **No anti-thrash control** — nothing stopped an automated fix from re-running the
   same failing action in a loop.
6. **No root-cause / fix-effectiveness memory** — no learning signal from one incident
   to the next.
7. **Backoff/jitter, circuit breakers, and recovery budgets** existed only as prose in
   the many blueprint docs, not as reusable code.

Items 1–7 are exactly what the shipped PHOENIX module now provides (see §2.1).

### What is *blocking* top-tier status (unchanged from `PLATFORM_AUDIT.md`)

- **Documentation/vision sprawl** — dozens of overlapping "ARTEMIS / OS / self-evolving
  / quantum" blueprints describe *unprovisioned* target states. The #1 barrier to trust
  is that a newcomer can't tell real from aspirational. **Do not add more of these.**
  This audit ships *code + one brief*, not another blueprint.

---

## 2. Best upgrades (ranked by recovery leverage)

| # | Upgrade | Leverage | Status |
|---|---|---|---|
| 1 | **Governed self-healing loop** (detect→classify→contain→plan→gate→execute→verify→learn) | Turns governance+audit into an actual recovery system; cuts MTTR while keeping safety | ✅ **Shipped** — `sentinel/sentinel/phoenix.py` |
| 2 | **Wire PHOENIX to real signals** — feed it `GET /ready`, webhook-failure counts, and Commerce Daily Loop health into `Signal`s | Makes the loop operate on live telemetry, not fixtures | Roadmap |
| 3 | **Durable incident memory + audit** — back `IncidentMemory`/`AuditLog` with the existing Postgres pattern | Learning survives restarts; incidents are replayable across time | Roadmap |
| 4 | **Rollback-safe deploy actions** — register `rollback`/`flag_off` handlers that call real feature-flag + deploy APIs behind the PHOENIX gate | Safe automated rollback is the single biggest MTTR win | Roadmap |
| 5 | **Incident replay / chaos harness** — property test that injects synthetic failure streams and asserts the loop never auto-runs an unsafe action | Continuous proof the guardrails hold as handlers grow | Partial (proof tests exist) |
| 6 | **Consolidate the blueprint docs** — collapse the ARTEMIS/OS set into one honest status page | Removes the trust barrier; unrelated to code but highest *maintainability* leverage | Roadmap (per `PLATFORM_AUDIT.md`) |

### 2.1 What shipped — the PHOENIX engine

`SelfHealingLoop.handle(signals, …)` runs the full loop under a fail-closed
`RecoveryPolicy`. Safety properties (each proven in `test_phoenix.py`):

- Escalation-class incidents (data corruption, security, payment) **never auto-run**.
- Only **reversible, low-risk, low-blast, high-confidence** steps auto-execute; every
  other step is refused and escalated with a reason.
- **Contain before remediate** for containment-class incidents.
- A **circuit breaker** + per-signature **loop guard** stop repeated-failure loops.
- Retries use **exponential backoff + full jitter** (deterministic under a seed).
- An incident is **RESOLVED only after an independent verifier** confirms restoration;
  a missing/raising verifier or a fix that ran-but-didn't-restore **escalates**.
- An **audit-write failure degrades the loop to deny-all**, matching `PolicyGovernor`.

It is stdlib-only and side-effect-free at its core (capabilities are injected), so it
drops into the same CI as the other governed modules and cannot itself cause harm.

---

## 3. Refactor plan

- **Keep:** `governance.py`, `governor.py`, `audit.py`, `security.py`, commerce
  `governance.py`/`service.py`. These are the crown jewels; PHOENIX reuses their
  patterns rather than replacing them.
- **Build next (small, real):** the four "roadmap" wirings in §2 (#2–#5). Each is an
  *adapter* around PHOENIX, not a new framework.
- **Simplify / remove (unchanged recommendation):** the overlapping blueprint `.md`
  set and duplicate root binaries flagged in `PLATFORM_AUDIT.md`. Adding features here
  is negative-value until real/aspirational is disentangled.
- **Do not:** add a code path that lets a high/critical or irreversible action execute
  without approval — in PHOENIX *or* the commerce plane. Both gates fail tests by design
  if you do.

---

## 4. Implementation plan (per upgrade)

**#1 Self-healing loop — DONE.**
- *Purpose:* close the detect→…→learn loop under governance.
- *Architecture:* pure-stdlib module; injected `handlers`, `verifier`, `policy`,
  `memory`, `breaker`, `audit`, `rng`, `sleep`. No side effects in core.
- *Dependencies:* none beyond `audit.py` + `models.py`.
- *Risks:* over-automation → mitigated by escalation-only classes, reversibility +
  blast-radius + confidence gates, and verify-before-close.
- *Testing:* 27 proof tests covering detection, classification, each gate branch,
  containment ordering, anti-thrash, learning, backoff, and audit tamper/deny-all.
- *Rollout:* additive; no existing behavior changed (276/276 suite green, ruff clean).
- *Safety/escalation:* anything unverifiable, irreversible, over-budget, unknown, or
  looping → **escalate, never run**.

**#2–#5 (roadmap):** each is an adapter that (a) maps a real telemetry source into
`Signal`s, (b) registers real runbook handlers behind the existing gate, and (c)
persists memory/audit to Postgres. Roll out one handler at a time, each behind a
feature flag, each with its own proof test, starting with the safest (read-only
health probes and `flag_off`) before `rollback`/`restart`.

---

## 5. Future direction

Make the platform feel advanced by making it *trustworthy*, not by adding more
blueprints. The differentiator for ClearGlassInc is a recovery system that can prove,
in code and tests, that it will **contain and escalate before it ever acts unsafely** —
and that every action it does take is reversible, verified, and auditable. PHOENIX is
the seed of that: a small, honest, fail-closed engine other systems can adopt one safe
handler at a time. The next unit of value is wiring it to one real signal and one real
rollback — not a tenth architecture doc.
