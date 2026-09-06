# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Proof tests for PHOENIX — the governed self-healing engine.

Each test asserts a safety or recovery property:
  * detection is robust and fail-closed on confidence
  * classification routes onto the correct recovery ladder rung
  * the policy gate never auto-executes an irreversible / high-risk action
  * proposed high-risk actions run ONLY with an explicit approval
  * incident memory prevents repeated failure loops (thrash → escalate)
  * the audit chain is tamper-evident across a full incident
  * integrity/security incidents escalate instead of being silently "fixed"
"""
from __future__ import annotations

import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.selfheal import (
    RISK_HIGH,
    AnomalyDetector,
    CircuitBreaker,
    Disposition,
    Incident,
    IncidentClass,
    IncidentMemory,
    Outcome,
    PLAYBOOKS,
    RecoveryAction,
    SelfHealEngine,
    Severity,
    Signal,
    backoff_delays,
    classify,
    gate,
    run_self_check,
)


# ------------------------------------------------------------- helpers ----

def _anomaly(det: AnomalyDetector, source="svc", metric="latency", baseline=100.0, spike=900.0):
    for _ in range(10):
        det.observe(Signal(metric, baseline, source))
    return det.observe(Signal(metric, spike, source))


def _incident(anomalies=(), **kw):
    kw.setdefault("severity", Severity.WARN)
    return Incident("INC-T", "test", kw.pop("severity"), tuple(anomalies), **kw)


# --------------------------------------------------------- detection ----

def test_detector_silent_until_min_samples():
    det = AnomalyDetector(min_samples=8)
    outs = [det.observe(Signal("m", 5.0, "s")) for _ in range(7)]
    assert all(o is None for o in outs)  # no baseline yet → no anomaly (fail-quiet)


def test_detector_flags_spike_with_confidence():
    det = AnomalyDetector(min_samples=4, window=20)
    a = _anomaly(det)
    assert a is not None
    assert a.score >= 3.5
    assert 0.0 < a.confidence <= 1.0


def test_detector_budget_breach_after_sustained_anomaly():
    det = AnomalyDetector(min_samples=4, window=50, budget=3)
    for _ in range(10):
        det.observe(Signal("m", 100.0, "s"))
    breached = False
    for _ in range(6):
        a = det.observe(Signal("m", 900.0, "s"))
        breached = breached or (a is not None and a.breached_budget)
    assert breached  # error budget is consumed and eventually reported


# ---------------------------------------------------- classification ----

def test_classify_fail_closed_without_confidence():
    assert classify(_incident()) is IncidentClass.ESCALATION  # no anomalies → no confidence


def test_classify_retryable():
    det = AnomalyDetector(min_samples=4)
    inc = _incident([_anomaly(det)], error_kind="timeout", affected_services=("api",))
    assert classify(inc) is IncidentClass.RETRYABLE


def test_classify_fallback_only_when_available():
    det = AnomalyDetector(min_samples=4)
    a = _anomaly(det)
    with_fb = _incident([a], error_kind="dependency_down", dependency_down=True,
                        fallback_available=True, affected_services=("dep",))
    without_fb = _incident([a], error_kind="dependency_down", dependency_down=True,
                           fallback_available=False, affected_services=("dep",))
    assert classify(with_fb) is IncidentClass.FALLBACK
    assert classify(without_fb) is IncidentClass.ESCALATION


def test_classify_spreading_is_containment():
    det = AnomalyDetector(min_samples=4)
    inc = _incident([_anomaly(det)], error_kind="5xx", spreading=True,
                    affected_services=("a", "b", "c", "d"))
    assert classify(inc) is IncidentClass.CONTAINMENT


def test_classify_integrity_and_security_escalate():
    det = AnomalyDetector(min_samples=4)
    a = _anomaly(det)
    integrity = _incident([a], error_kind="unknown", data_integrity_risk=True)
    security = _incident([a], error_kind="security", affected_services=("auth",))
    assert classify(integrity) is IncidentClass.ESCALATION
    assert classify(security) is IncidentClass.CONTAINMENT


# ------------------------------------------------- retry / breaker ----

def test_backoff_deterministic_bounded_and_capped():
    rng = random.Random(7)
    d1 = backoff_delays(6, base=0.2, cap=2.0, jitter=0.5, rng=random.Random(7))
    d2 = backoff_delays(6, base=0.2, cap=2.0, jitter=0.5, rng=rng)
    assert d1 == d2                       # deterministic under seeded rng
    assert all(0.0 <= x <= 2.0 for x in d1)  # jittered, never above cap
    assert max(d1) <= 2.0


def test_circuit_breaker_open_halfopen_close():
    now = {"t": 0.0}
    cb = CircuitBreaker(threshold=2, cool_down=10.0, clock=lambda: now["t"])
    assert cb.allows()
    cb.record(False)
    cb.record(False)                       # hit threshold → OPEN
    assert cb.state == cb.OPEN
    assert not cb.allows()                 # blocked during cool-down
    now["t"] = 11.0
    assert cb.allows() and cb.state == cb.HALF_OPEN
    cb.record(True)                        # probe succeeds → CLOSED
    assert cb.state == cb.CLOSED


# ---------------------------------------------------- memory / loop ----

def test_memory_effectiveness_updates_with_outcomes():
    mem = IncidentMemory()
    act = RecoveryAction("x", "d", risk=10, reversible=True, kind="retry", base_effectiveness=0.5)
    base = mem.effectiveness("sig", act)
    for _ in range(5):
        mem.record("sig", act, True)
    assert mem.effectiveness("sig", act) > base  # learns that it works


def test_memory_exhaustion_prevents_loops():
    mem = IncidentMemory(max_failures=3)
    act = RecoveryAction("x", "d", risk=10, reversible=True, kind="retry")
    for _ in range(3):
        mem.record("sig", act, False)
    assert mem.exhausted("sig", act)
    mem.record("sig", act, True)           # a success resets the streak
    assert not mem.exhausted("sig", act)


# ---------------------------------------------------------- gating ----

def test_gate_auto_only_for_safe_reversible_confident():
    det = AnomalyDetector(min_samples=4)
    inc = _incident([_anomaly(det)], error_kind="timeout", affected_services=("api",))
    safe = PLAYBOOKS[IncidentClass.RETRYABLE][0]           # retry_backoff, low risk
    v = gate(safe, inc, IncidentMemory(), tau=0.0)
    assert v.disposition is Disposition.AUTO


def test_gate_proposes_high_risk_and_irreversible():
    det = AnomalyDetector(min_samples=4)
    inc = _incident([_anomaly(det)], error_kind="5xx", spreading=True,
                    affected_services=("a", "b", "c"))
    rollback = next(a for a in PLAYBOOKS[IncidentClass.CONTAINMENT] if a.key == "rollback_release")
    failover = next(a for a in PLAYBOOKS[IncidentClass.CONTAINMENT] if a.key == "failover_primary")
    assert gate(rollback, inc, IncidentMemory(), tau=0.0).disposition is Disposition.PROPOSE
    assert gate(failover, inc, IncidentMemory(), tau=0.0).disposition is Disposition.PROPOSE


def test_gate_escalates_when_confidence_unverifiable():
    inc = _incident()  # no anomalies → confidence None
    safe = PLAYBOOKS[IncidentClass.RETRYABLE][0]
    assert gate(safe, inc, IncidentMemory()).disposition is Disposition.ESCALATE


# ---------------------------------------------------- engine loop ----

def _det_inc(**kw):
    det = AnomalyDetector(min_samples=4, window=20)
    return _incident([_anomaly(det)], **kw)


def test_engine_retryable_recovers_and_audits():
    eng = SelfHealEngine()
    inc = _det_inc(error_kind="timeout", affected_services=("api",))
    rep = eng.handle(inc, executor=lambda a, i: True, verifier=lambda i: True)
    assert rep.outcome is Outcome.RECOVERED
    assert rep.audit_verified
    assert any(s.executed and s.disposition is Disposition.AUTO for s in rep.steps)


def test_engine_never_auto_executes_high_risk():
    """With a verifier that never confirms, the engine climbs the whole
    containment ladder — the high-risk rungs must be PROPOSED, not executed."""
    eng = SelfHealEngine()
    inc = _det_inc(error_kind="5xx", spreading=True,
                   affected_services=("a", "b", "c", "d"))
    rep = eng.handle(inc, executor=lambda a, i: True, verifier=lambda i: False)
    executed_high = [s for s in rep.steps if s.executed and _risk(s.action_key) >= RISK_HIGH]
    assert not executed_high
    assert "rollback_release" in rep.approvals_required
    assert "failover_primary" in rep.approvals_required


def test_engine_executes_high_risk_only_with_approval():
    eng = SelfHealEngine()
    inc = _det_inc(error_kind="5xx", spreading=True, affected_services=("a", "b", "c"))
    seen = {}

    def executor(a, i):
        seen[a.key] = True
        return a.key == "rollback_release"  # only the approved rollback "works"

    rep = eng.handle(inc, executor=executor, verifier=lambda i: seen.get("rollback_release", False),
                     approvals={"rollback_release"})
    assert seen.get("rollback_release") is True
    assert rep.outcome is Outcome.RECOVERED


def test_engine_integrity_incident_escalates_without_side_effects():
    eng = SelfHealEngine()
    inc = _det_inc(error_kind="unknown", data_integrity_risk=True, affected_services=("ledger",))
    calls = []
    rep = eng.handle(inc, executor=lambda a, i: calls.append(a.key) or True,
                     verifier=lambda i: True)
    assert rep.outcome is Outcome.ESCALATED
    assert calls == []  # nothing executed
    assert rep.incident_class is IncidentClass.ESCALATION


def test_engine_loop_prevention_escalates_after_repeated_failure():
    mem = IncidentMemory(max_failures=2)
    eng = SelfHealEngine(memory=mem)

    def make():
        return _det_inc(error_kind="timeout", affected_services=("api",))

    # Fail every remediation repeatedly for the same signature.
    for _ in range(4):
        eng.handle(make(), executor=lambda a, i: False, verifier=lambda i: False)
    final = eng.handle(make(), executor=lambda a, i: True, verifier=lambda i: True)
    # All retryable actions exhausted → nothing left to auto-run → escalate.
    assert final.outcome is Outcome.ESCALATED
    assert all(not s.executed for s in final.steps)


def test_engine_audit_tamper_is_detected():
    eng = SelfHealEngine()
    inc = _det_inc(error_kind="timeout", affected_services=("api",))
    eng.handle(inc, executor=lambda a, i: True, verifier=lambda i: True)
    assert eng.audit.verify()
    # Corrupt a committed entry: chain must no longer verify.
    entry = eng.audit.entries[0]
    object.__setattr__(entry, "action", "tampered")
    eng.audit._entries[0] = entry
    assert not eng.audit.verify()


def test_engine_records_mttr():
    ticks = iter([100.0, 100.5])
    eng = SelfHealEngine(clock=lambda: next(ticks))
    inc = _det_inc(error_kind="timeout", affected_services=("api",))
    rep = eng.handle(inc, executor=lambda a, i: True, verifier=lambda i: True)
    assert rep.mttr_seconds == 0.5


def _risk(key):
    for actions in PLAYBOOKS.values():
        for a in actions:
            if a.key == key:
                return a.risk
    return 0


# ------------------------------------------------------- self-check ----

def test_self_check_invariants_hold():
    _reports, failures = run_self_check()
    assert failures == []


# ------------------------------------------------- memory persistence ----

def test_memory_state_roundtrip_preserves_learning():
    mem = IncidentMemory(max_failures=4)
    act = RecoveryAction("retry_backoff", "d", risk=10, reversible=True, kind="retry",
                         base_effectiveness=0.5)
    for ok in (True, True, False, True):
        mem.record("sig-A", act, ok)
    restored = IncidentMemory.from_state(mem.to_state())
    # Effectiveness (attempts/successes) and config survive the round-trip.
    assert restored.effectiveness("sig-A", act) == mem.effectiveness("sig-A", act)
    assert restored.max_failures == 4


def test_memory_save_load_survives_restart(tmp_path):
    path = str(tmp_path / "phoenix_memory.json")
    mem = IncidentMemory(max_failures=2)
    act = RecoveryAction("clear_cache", "d", risk=20, reversible=True, kind="remediate")
    # Two consecutive failures → exhausted (loop prevention must persist).
    mem.record("sig-B", act, False)
    mem.record("sig-B", act, False)
    assert mem.exhausted("sig-B", act)
    mem.save(path)

    reloaded = IncidentMemory.load(path)
    assert reloaded.exhausted("sig-B", act)          # streak survived restart
    assert reloaded.max_failures == 2


def test_memory_load_missing_file_is_fresh(tmp_path):
    missing = str(tmp_path / "does_not_exist.json")
    mem = IncidentMemory.load(missing, max_failures=5)
    act = RecoveryAction("x", "d", risk=10, reversible=True, kind="retry")
    assert not mem.exhausted("sig", act)             # fail-open on learning only
    assert mem.max_failures == 5


def test_cli_memory_flag_persists_across_runs(tmp_path):
    from sentinel.selfheal import main
    path = str(tmp_path / "mem.json")
    assert main(["--memory", path]) == 0             # gate still passes
    assert (tmp_path / "mem.json").exists()          # learning was written
    # A second run loads the prior file and still passes cleanly.
    assert main(["--memory", path]) == 0
