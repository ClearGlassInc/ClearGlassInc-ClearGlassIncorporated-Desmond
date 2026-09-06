<!-- Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved. -->
# Self-Healing Platform Audit — ClearGlassInc / Desmond Otieno Odhiambo

Scope: the autonomous-recovery / self-healing stack under `sentinel/` (the
PHOENIX engines) and the CI gates that protect it. This pass focuses on
resilience, safety, and CI trust rather than cosmetic change, per the platform
doctrine in `CLAUDE.md` (read-only → draft → human approval → execution;
fail-closed; everything audited).

## 1. Repository assessment

**What the repo already does well.** The self-healing core is genuinely
production-grade, not placeholder code. `sentinel/sentinel/selfheal.py` (PHOENIX)
implements the full governed loop — `detect → classify → plan → GATE → contain
→ remediate → verify → learn` — with the right safety properties baked in:

- **Fail-closed gating.** `gate()` only returns `AUTO` for safe-listed,
  reversible, sub-`RISK_HIGH`, confident actions; anything else is `PROPOSE`
  (human approval) or `ESCALATE`. Unverifiable detection escalates.
- **Robust detection.** `AnomalyDetector` uses median + MAD (not mean/stddev),
  so the spikes it hunts don't poison its own baseline, and it is fail-closed on
  confidence when history is thin.
- **Loop prevention.** `IncidentMemory` exhausts an action after repeated
  failures for a signature, forcing the ladder toward escalation instead of
  thrashing.
- **Containment before remediation**, exponential backoff with decorrelated
  jitter, a three-state circuit breaker, and a hash-chained tamper-evident
  audit log (`audit.py`) verified on every incident.
- Pure-stdlib orchestration with injected `executor`/`verifier` adapters, so the
  trust loop is fully testable without touching production systems. 303 unit
  tests pass; the package is ruff-clean.

**What was missing / blocking (addressed in this pass).**

1. **CI gap (observability).** The `Phoenix Self-Heal` workflow gated *only*
   `test_selfheal.py`, and `ci.yml` runs only the root `tests/`. That left
   `phoenix.py` (the engine exported from `sentinel/sentinel/__init__.py`) plus
   ~270 tests (governor, policy, capability, identity, mission-memory, percival,
   pfas…) **ungated on pull requests** — they could regress with CI green.
2. **Learning did not survive restarts.** `IncidentMemory` was explicitly
   "durable-in-spirit" but in-process only. Every redeploy erased learned fix
   effectiveness and loop-prevention streaks — undercutting the "continuous
   learning from incident outcomes" mandate.

**Still open (recommended next, not done here).**

3. **Two parallel PHOENIX engines.** `phoenix.py` and `selfheal.py` are both
   "PHOENIX — governed self-healing engine" with overlapping responsibility but
   divergent APIs (`FailureClass`/`IncidentState`/`RecoveryPolicy`/`ErrorBudget`
   vs `IncidentClass`/`Disposition`/`gate()`). Both are tested and green, so
   this is a maintainability/trust hazard, not a live bug — it needs a
   deliberate consolidation (see §3), not a blind delete.

## 2. Best upgrades (ranked)

| # | Upgrade | Value | Risk | Status |
|---|---------|-------|------|--------|
| 1 | Gate the full sentinel suite + package lint in CI | High | Low | **Done** |
| 2 | Restart-durable incident memory (persist learning) | High | Low | **Done** |
| 3 | Consolidate the two PHOENIX engines to one canonical module | High | Med | Proposed |
| 4 | Multi-incident correlation (blast-radius across concurrent incidents) | Med | Med | Proposed |
| 5 | Incident replay / simulation harness from persisted memory | Med | Low | Proposed |
| 6 | Error-budget-driven auto-freeze of risky remediation classes | Med | Med | Proposed |

## 3. Refactor plan

- **Keep:** `selfheal.py` as the canonical engine — it owns the CLI self-check
  (`--check`) that CI uses as a fail-closed gate, and has the tighter,
  fully-exercised `gate()`/`classify()` policy surface.
- **Consolidate (next PR):** fold the genuinely additive concepts from
  `phoenix.py` (first-class `ErrorBudget`, `blast_radius()`, `RecoveryPolicy`)
  into `selfheal.py`, then reduce `phoenix.py` to a thin deprecated re-export so
  `__init__`, `phoenix_demo.py`, the briefs, and `test_phoenix.py` keep working
  while there is one source of truth. Do this behind the now-widened CI gate so
  any divergence is caught immediately.
- **Remove:** nothing yet — both engines are load-bearing for their tests until
  consolidation lands. No dead code was deleted blindly.
- **Simplify:** none required in the core loop; it is already tight.

## 4. Implementation plan (changes in this PR)

### Upgrade 1 — Full-stack CI gate (`.github/workflows/phoenix-self-heal.yml`)
- **Purpose:** stop silent regressions in the exported engine and governance
  stack. **Architecture:** widen the existing sentinel-subtree gate to
  `ruff check sentinel/sentinel sentinel/tests` and `pytest sentinel/tests`
  (both engines + governance/policy/identity/memory), keeping the
  `python -m sentinel.selfheal --check` safety-invariant gate.
- **Dependencies:** none new (stdlib + pytest/ruff already installed in-job).
- **Risks:** a previously-ungated test could now fail the gate — verified
  locally that all 303 pass and the package is ruff-clean, so the gate goes
  green on merge. **Rollout:** path-filtered to `sentinel/**`; no runtime impact.

### Upgrade 2 — Restart-durable incident memory (`sentinel/sentinel/selfheal.py`)
- **Purpose:** learning (fix effectiveness + loop-prevention streaks) must
  survive process restarts so PHOENIX keeps improving MTTR across redeploys.
- **Architecture:** additive, stdlib-only methods on `IncidentMemory` —
  `to_state()`/`load_state()`/`from_state()` (full attempts/successes +
  consecutive-fail streaks, not the lossy `snapshot()`), plus `save(path)`
  (atomic temp-write + `os.replace`) and `load(path)`. A new optional
  `--memory PATH` CLI flag loads prior state, runs the self-check, and saves it
  back. `run_self_check(memory=…)` gained an optional parameter (backward
  compatible).
- **Safety:** the load path fail-*opens* on a **missing** file only (empty prior
  = no learning yet); the safety gate still fails **closed** on every decision
  regardless of memory contents, so persistence never relaxes a guardrail.
- **Testing:** 4 new tests — state round-trip preserves effectiveness/config,
  save/load survives a restart including an exhausted streak, missing-file load
  is fresh, and the `--memory` CLI persists across two runs while the gate stays
  green. **Risks:** low; existing frozen behavior unchanged, corrupt-file load
  fails loudly rather than silently mislearning.

## 5. Future direction

Toward a defense-grade recovery system for ClearGlassInc:

- **One canonical engine** (§3) with a documented, versioned recovery-plan
  schema, so playbooks and adapters are pluggable per incident type.
- **Correlation layer** above single-incident handling: group concurrent
  anomalies by shared blast radius and drive containment once, not per-incident.
- **Simulation / chaos harness** that replays persisted incident memory to
  benchmark recovery-quality regressions before they reach production — turning
  the new durable memory into an evaluation asset.
- **Error-budget governance:** when a service's budget is burned, auto-raise the
  approval bar (freeze `rollback`/`failover`-class actions to human-only) until
  the budget recovers — error budgets driving policy, not just reporting.
- **Signed audit export** for post-incident review, extending the existing
  hash-chained ledger with an operator-facing incident timeline.

All future work stays inside the non-negotiable doctrine: contain before you
fix, verify before you close, escalate when confidence is low, and audit
everything.
