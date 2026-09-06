# PHOENIX — Governed Autonomous Recovery (Self-Healing) Agent

**Family:** SENTINEL / PERCIVAL named agents · **Persona:** site-reliability
**Executable:** `sentinel/sentinel/phoenix.py` (+ `tests/test_phoenix.py`, `phoenix_demo.py`)
**Doctrine:** fail-closed · safety over autonomy · contain → verify → learn

PHOENIX is the recovery persona of the SENTINEL control plane. Where SENTINEL
governs *retrieval* and PERCIVAL governs *website change*, PHOENIX governs
*incident recovery*: it turns raw health telemetry into a safe, auditable,
self-healing loop and escalates to a human the moment autonomy stops being safe.

It is stdlib-only (no third-party deps) so it runs in the same minimal CI
environments as `governance.py`, `governor.py`, and the commerce `daily_loop.py`.
Time and randomness are injectable, so a recovery run is fully deterministic
under test.

## The loop

```
detect → classify → contain → plan → gate → execute → verify → learn
```

| Stage | What happens | Code |
|---|---|---|
| **detect** | Threshold check on health `Signal`s (SLO bands + failure-signature tags); correlated breach count = blast radius | `detect`, `blast_radius` |
| **classify** | Route to `RETRYABLE` / `FALLBACK` / `CONTAINMENT` / `ESCALATION`. Unknown signature, exhausted error budget, or wide blast radius all force escalation | `classify`, `_SIGNATURE_CLASS` |
| **contain** | For containment-class incidents, run the blast-radius limiter (shed traffic / open circuit / flag off) **before** any remediation | `SelfHealingLoop.handle` |
| **plan** | Assemble the class's playbook steps; score plan confidence = *min* per-step confidence from incident memory | `SelfHealingLoop.plan`, `RecoveryPlan` |
| **gate** | Fail-closed policy check: escalation-class blocked; irreversible / over-risk / over-blast / low-confidence / no-handler / breaker-open / loop-guarded → **escalate, never run** | `SelfHealingLoop._gate`, `RecoveryPolicy` |
| **execute** | Run the handler with a recovery budget; retries use exponential backoff + full jitter | `_execute_step`, `backoff_delays` |
| **verify** | Independent health probe must confirm restoration; a fix that "ran" but didn't restore health escalates. No verifier = unverifiable = escalate | `SelfHealingLoop.handle` (verify block) |
| **learn** | Record `(signature, action) → success/failure`; success lifts confidence, failure pulls it below tau and, after `loop_guard` repeats, forces escalation | `IncidentMemory`, `CircuitBreaker` |

Every stage appends to the hash-chained audit ledger (`audit.py`); an audit-write
failure degrades PHOENIX to **deny-all** (it cannot act un-loggably), mirroring
the `PolicyGovernor` posture.

## Safety invariants (enforced in code, proven in tests)

1. **Escalation-class incidents never auto-remediate** — data corruption, security
   and payment anomalies are human-in-the-loop by policy, regardless of score.
2. **Only reversible, low-risk, low-blast, high-confidence steps auto-run.** Every
   other step is refused and escalated.
3. **Contain before you fix** — a bad remediation can't widen a cascading outage.
4. **No repeated-failure loops** — a circuit breaker and per-signature loop guard
   stop PHOENIX from re-running a fix that just failed.
5. **Verify before you close** — restoration is confirmed by an independent probe,
   not assumed from a step returning success.
6. **Unverifiable ⇒ denied** — missing handler, missing verifier, raised probe, or
   an audit outage all fail closed.

`tests/test_phoenix.py` proves each of these (27 tests).

## Run

```bash
cd sentinel
python -m pytest tests/test_phoenix.py -q      # 27 proof tests, no external deps
python -m sentinel.phoenix_demo                # narrated recovery scenarios
python -m sentinel.phoenix_demo --json         # machine-readable outcomes
```

## Wiring PHOENIX to a real system

`SelfHealingLoop` is deliberately side-effect-free at its core: you inject the
capabilities, it enforces the policy.

```python
from sentinel.phoenix import SelfHealingLoop, RecoveryPolicy, Signal, RemediationStep, FailureClass

loop = SelfHealingLoop(
    handlers={                                   # action name -> safe side effect
        "retry_backoff": lambda step: call_upstream_with_retry(step.target),
        "shed_traffic":  lambda step: feature_flag_off(step.target),
    },
    verifier=lambda incident_id: probe_health(incident_id),   # independent probe
    policy=RecoveryPolicy(tau=0.7, max_risk=0.4, max_blast_radius=3, max_attempts=3),
)

outcome = loop.handle(
    signals=[Signal("p99_ms", 900, healthy_max=500, tags=("timeout",))],
    incident_id="INC-42",
    playbook={FailureClass.RETRYABLE: [RemediationStep("retry_backoff", "checkout-api", reversible=True, risk=0.1)]},
)
```

### Production swap-ins

| Reference | Production |
|---|---|
| threshold `detect()` | statistical detector (EWMA / z-score) behind the same `Anomaly` return type |
| in-process `IncidentMemory` | durable table keyed on `(signature, action)`, anchored periodically |
| in-memory `AuditLog` | append-only Postgres ledger + periodic anchoring |
| lambda handlers | real runbook actions (feature flags, autoscaler, circuit config, redeploy/rollback) behind the same fail-closed gate |
| `verifier` lambda | synthetic-probe / SLO re-check against live telemetry |

## Boundaries

PHOENIX inherits the SENTINEL hard rules: it acts only on **owned/authorized**
systems, never fabricates telemetry or incidents, and treats *any* ambiguity as a
reason to escalate rather than act. It does not identify people and does not move
money, price, tax, refund, or fulfillment — those remain behind the commerce
control plane's own approval gate.
