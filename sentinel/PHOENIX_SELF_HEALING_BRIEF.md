# PHOENIX — Governed Self-Healing Engine

> Resilience persona in the PERCIVAL / SENTINEL family. Closes the operational
> loop the rest of the mesh leaves open: **detect → classify → gate → contain →
> remediate → verify → learn** — autonomously where it is safe, escalated to a
> human where it is not.

- **Executable:** `sentinel/sentinel/selfheal.py` (pure stdlib, fail-closed)
- **Tests:** `sentinel/tests/test_selfheal.py` (23 property tests)
- **CI gate:** `.github/workflows/phoenix-self-heal.yml`
- **Private surface:** `sentinel/PHOENIX_DASHBOARD.html` (noindex; not in `sitemap.xml`)
- **Run it:** `python -m sentinel.selfheal` · `--json` · `--check`

## Why it exists

The repo already governs *change* (commerce approval gate) and *access*
(SENTINEL policy gate). PHOENIX governs *recovery* — the same doctrine applied
to incidents: read-only analysis → drafted plan → safe auto-execute **or**
human approval → verified execution, every step audited.

## The safety model (non-negotiable)

PHOENIX inherits the family's fail-closed doctrine. An action auto-executes only
when **all** hold; otherwise it is proposed for approval or escalated:

| Requirement | Enforced by |
|---|---|
| Safe-listed **and** reversible action | `PLAYBOOKS` + `RecoveryAction.reversible` |
| Risk `< 70` (0–100 band, mirrors commerce governance) | `gate()` / `RISK_HIGH` |
| Detection confidence `≥ tau` (default 0.6) | `gate()`; `None` ⇒ escalate |
| Not exhausted for this signature (loop prevention) | `IncidentMemory.exhausted` |

Irreversible or high-risk remediations (`rollback_release`, `failover_primary`)
are **PROPOSE-only** — they run only when their key is supplied in `approvals`.
Security / data-integrity / unverifiable incidents **escalate** with a drafted
plan and zero side effects. Every decision and step is written to the
hash-chained, tamper-evident `audit.AuditLog`.

## The recovery ladder

| Class | Trigger | Default disposition |
|---|---|---|
| **RETRYABLE** | transient timeout / 5xx | AUTO — backoff+jitter, restart, cache flush |
| **FALLBACK** | dependency down + standby available | AUTO — reroute, degrade, serve cached |
| **CONTAINMENT** | spreading blast radius (≥3 services) | AUTO contain first; rollback/failover ⇒ PROPOSE |
| **ESCALATION** | security / integrity / no confidence / exhausted | HUMAN — drafted plan |

## Components

- **`AnomalyDetector`** — robust median/MAD scoring (spike-resistant) + per-metric
  error budgets; fail-quiet until a baseline exists, low-confidence when thin.
- **`classify()`** — routes an `Incident` onto the ladder; unknown ⇒ escalate.
- **`backoff_delays()`** — exponential backoff with decorrelated jitter,
  deterministic under an injected RNG.
- **`CircuitBreaker`** — CLOSED/OPEN/HALF_OPEN guard on a repair budget.
- **`IncidentMemory`** — blends a prior with observed success rate to rank
  actions, and exhausts fixes that keep failing (no thrash loops).
- **`gate()`** — the policy heart; returns AUTO / PROPOSE / ESCALATE with reasons.
- **`SelfHealEngine.handle()`** — orchestrates the loop for one incident; all IO
  runs through injected `executor` / `verifier` adapters so the engine itself
  performs no real side effects (safe to test, safe to embed).

## Wiring it to real systems

The engine is intentionally adapter-driven. To make the private dashboard live:

1. Feed real metrics/health probes as `Signal`s into an `AnomalyDetector`.
2. Build `Incident`s from breached anomalies + dependency/topology context.
3. Provide an `executor(action, incident)` that performs the real remediation
   (k8s cordon, breaker toggle, feature-flag flip, queue drain, …) and a
   `verifier(incident)` that re-probes health.
4. Persist `IncidentMemory` and stream `AuditLog` entries to durable storage.
5. Regenerate the dashboard snapshot with `python -m sentinel.selfheal --json`.

Nothing here moves money, changes pricing, or performs an irreversible action
without an explicit human approval — by construction and by test.
