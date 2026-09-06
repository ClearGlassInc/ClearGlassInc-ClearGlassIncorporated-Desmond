"""Proof tests for PHOENIX — the governed autonomous recovery loop.

Each test asserts a safety or recovery property of the self-healing loop:
  * healthy signals -> no-op resolution
  * breached signals are detected, classified, and (when safe) auto-remediated
  * verification gates closure — a fix that doesn't restore health escalates
  * the policy gate fails closed on irreversible / risky / wide-blast / unknown
    actions and on escalation-class incidents
  * containment runs before remediation
  * the circuit breaker + incident memory stop repeated-failure loops
  * incident memory learns fix effectiveness and lifts confidence over tau
  * an audit-ledger failure degrades PHOENIX to deny-all
  * the audit chain is tamper-evident
"""
from __future__ import annotations

import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.phoenix import (
    CircuitBreaker,
    ErrorBudget,
    FailureClass,
    IncidentMemory,
    IncidentState,
    RecoveryPolicy,
    RemediationStep,
    Signal,
    SelfHealingLoop,
    backoff_delays,
    blast_radius,
    classify,
    detect,
)

# --------------------------------------------------------------- fixtures ----

HEALTHY = [Signal("latency_ms", 120.0, healthy_max=500.0, tags=("timeout",))]
LATENCY_BREACH = [Signal("latency_ms", 900.0, healthy_max=500.0, tags=("timeout",))]
DEP_DOWN = [Signal("dep_errors", 30.0, healthy_max=5.0, tags=("dependency_down",))]
CASCADE = [Signal("saturation", 0.99, healthy_max=0.8, tags=("cascading_failure",))]
CORRUPTION = [Signal("checksum_fail", 3.0, healthy_max=0.0, tags=("data_corruption",))]


def _step(action, *, reversible=True, risk=0.1, br=1):
    return RemediationStep(action=action, target="svc", reversible=reversible, risk=risk, blast_radius=br)


def _loop(**kw):
    """A loop with a passing verifier and a succeeding retry handler by default."""
    handlers = kw.pop("handlers", {"retry": lambda s: True})
    verifier = kw.pop("verifier", lambda _id: True)
    return SelfHealingLoop(handlers=handlers, verifier=verifier, rng=random.Random(7), **kw)


RETRY_PLAYBOOK = {FailureClass.RETRYABLE: [_step("retry")]}


# ------------------------------------------------------------ detection ------

def test_detect_flags_only_breached_signals():
    assert detect(HEALTHY) == []
    anomalies = detect(LATENCY_BREACH)
    assert len(anomalies) == 1
    assert anomalies[0].signal == "latency_ms"
    assert anomalies[0].deviation > 0


def test_blast_radius_counts_distinct_signals():
    anomalies = detect([
        Signal("a", 10, healthy_max=1, tags=("timeout",)),
        Signal("b", 10, healthy_max=1, tags=("timeout",)),
    ])
    assert blast_radius(anomalies) == 2


# --------------------------------------------------------- classification ----

def test_classify_known_signatures():
    assert classify(detect(LATENCY_BREACH)) is FailureClass.RETRYABLE
    assert classify(detect(DEP_DOWN)) is FailureClass.FALLBACK
    assert classify(detect(CASCADE)) is FailureClass.CONTAINMENT
    assert classify(detect(CORRUPTION)) is FailureClass.ESCALATION


def test_unknown_signature_escalates():
    unknown = detect([Signal("mystery", 10, healthy_max=1, tags=("???",))])
    assert classify(unknown) is FailureClass.ESCALATION


def test_exhausted_error_budget_forces_escalation():
    budget = ErrorBudget("api", total=60.0, consumed=60.0)
    assert classify(detect(LATENCY_BREACH), error_budget=budget) is FailureClass.ESCALATION


def test_wide_blast_radius_escalates():
    wide = detect([Signal(f"s{i}", 10, healthy_max=1, tags=("timeout",)) for i in range(4)])
    assert classify(wide, blast_radius_escalate=4) is FailureClass.ESCALATION


# ----------------------------------------------------- happy-path recovery ---

def test_healthy_signals_resolve_without_action():
    out = _loop().handle(HEALTHY, incident_id="i1", playbook=RETRY_PLAYBOOK)
    assert out.state is IncidentState.RESOLVED
    assert out.steps == []


def test_retryable_incident_auto_remediates_and_verifies():
    out = _loop().handle(LATENCY_BREACH, incident_id="i2", playbook=RETRY_PLAYBOOK)
    assert out.resolved
    assert out.failure_class is FailureClass.RETRYABLE
    assert out.steps[0].success and out.steps[0].executed


def test_unrestored_health_escalates_even_if_step_ran():
    """A remediation that 'succeeds' but doesn't restore health must NOT close."""
    loop = _loop(verifier=lambda _id: False)
    out = loop.handle(LATENCY_BREACH, incident_id="i3", playbook=RETRY_PLAYBOOK)
    assert out.state is IncidentState.ESCALATED
    assert out.escalated
    assert "not restored" in out.reason


def test_missing_verifier_fails_closed():
    loop = SelfHealingLoop(handlers={"retry": lambda s: True}, verifier=None)
    out = loop.handle(LATENCY_BREACH, incident_id="i4", playbook=RETRY_PLAYBOOK)
    assert out.state is IncidentState.ESCALATED
    assert "unverifiable" in out.reason


# ------------------------------------------------------------ policy gate ----

def test_escalation_class_never_auto_runs():
    ran = []
    loop = _loop(handlers={"purge": lambda s: ran.append(s) or True})
    out = loop.handle(CORRUPTION, incident_id="i5",
                      playbook={FailureClass.ESCALATION: [_step("purge")]})
    assert out.escalated and out.state is IncidentState.ESCALATED
    assert ran == []  # nothing executed


def test_irreversible_step_is_gated():
    loop = _loop(handlers={"retry": lambda s: True})
    out = loop.handle(LATENCY_BREACH, incident_id="i6",
                      playbook={FailureClass.RETRYABLE: [_step("retry", reversible=False)]})
    assert out.escalated
    assert "irreversible" in out.steps[0].reason


def test_high_risk_step_is_gated():
    loop = _loop()
    out = loop.handle(LATENCY_BREACH, incident_id="i7",
                      playbook={FailureClass.RETRYABLE: [_step("retry", risk=0.9)]})
    assert out.escalated
    assert "risk" in out.steps[0].reason


def test_wide_blast_step_is_gated():
    loop = _loop(policy=RecoveryPolicy(max_blast_radius=2))
    out = loop.handle(LATENCY_BREACH, incident_id="i8",
                      playbook={FailureClass.RETRYABLE: [_step("retry", br=5)]})
    assert out.escalated
    assert "blast radius" in out.steps[0].reason


def test_missing_handler_fails_closed():
    loop = SelfHealingLoop(handlers={}, verifier=lambda _id: True)
    out = loop.handle(LATENCY_BREACH, incident_id="i9", playbook=RETRY_PLAYBOOK)
    assert out.escalated
    assert "no handler" in out.steps[0].reason


def test_low_confidence_plan_is_gated():
    # Prime memory so the fix has a poor track record -> confidence below tau.
    # loop_guard is raised so the confidence check (not the loop guard) is what
    # gates this step.
    mem = IncidentMemory(loop_guard=99)
    for _ in range(6):
        mem.record("timeout", "retry", success=False)
    loop = _loop(memory=mem, breaker=CircuitBreaker(threshold=99))
    out = loop.handle(LATENCY_BREACH, incident_id="i10", playbook=RETRY_PLAYBOOK)
    assert out.escalated
    assert "confidence" in out.steps[-1].reason


# ------------------------------------------------------------ containment ----

def test_containment_runs_before_remediation():
    order = []
    loop = _loop(handlers={
        "shed_traffic": lambda s: order.append("contain") or True,
        "restart": lambda s: order.append("remediate") or True,
    })
    out = loop.handle(
        CASCADE, incident_id="i11",
        playbook={FailureClass.CONTAINMENT: [_step("restart")]},
        containment=_step("shed_traffic"),
    )
    assert out.resolved
    assert order == ["contain", "remediate"]


def test_failed_containment_escalates_without_remediating():
    order = []
    loop = _loop(handlers={
        "shed_traffic": lambda s: False,
        "restart": lambda s: order.append("remediate") or True,
    })
    out = loop.handle(
        CASCADE, incident_id="i12",
        playbook={FailureClass.CONTAINMENT: [_step("restart")]},
        containment=_step("shed_traffic"),
    )
    assert out.escalated
    assert order == []  # remediation never reached


def test_containment_without_handler_escalates():
    loop = _loop(handlers={"restart": lambda s: True})
    out = loop.handle(
        CASCADE, incident_id="i13",
        playbook={FailureClass.CONTAINMENT: [_step("restart")]},
        containment=None,
    )
    assert out.escalated
    assert "containment" in out.reason


# ------------------------------------------------ anti-thrash + learning -----

def test_circuit_breaker_opens_after_repeated_failures():
    cb = CircuitBreaker(threshold=2)
    cb.record_failure()
    assert cb.closed
    cb.record_failure()
    assert cb.opened
    cb.record_success()
    assert cb.closed


def test_failing_handler_trips_breaker_and_escalates():
    loop = _loop(handlers={"retry": lambda s: False},
                 policy=RecoveryPolicy(max_attempts=2),
                 breaker=CircuitBreaker(threshold=1))
    out = loop.handle(LATENCY_BREACH, incident_id="i14", playbook=RETRY_PLAYBOOK)
    assert out.escalated
    assert out.steps[0].attempts == 2  # exhausted the recovery budget
    assert loop.breaker.opened


def test_repeated_failure_loop_is_guarded():
    mem = IncidentMemory(loop_guard=1)
    mem.record("timeout", "retry", success=False)
    loop = _loop(memory=mem)
    out = loop.handle(LATENCY_BREACH, incident_id="i15", playbook=RETRY_PLAYBOOK)
    assert out.escalated
    assert "repeated-failure loop" in out.steps[0].reason


def test_incident_memory_learns_and_lifts_confidence():
    mem = IncidentMemory()
    base = mem.confidence_for("timeout", "retry")
    for _ in range(5):
        mem.record("timeout", "retry", success=True)
    assert mem.confidence_for("timeout", "retry") > base
    assert not mem.should_escalate("timeout", "retry")


# ------------------------------------------------------------- backoff -------

def test_backoff_is_exponential_bounded_and_deterministic():
    a = backoff_delays(5, base=0.5, cap=10.0, rng=random.Random(1))
    b = backoff_delays(5, base=0.5, cap=10.0, rng=random.Random(1))
    assert a == b                                  # deterministic under a seed
    assert all(0.0 <= d <= 10.0 for d in a)        # bounded by the cap
    assert len(a) == 5


def test_backoff_sleep_is_invoked_between_retries():
    slept = []
    loop = SelfHealingLoop(
        handlers={"retry": lambda s: len(slept) >= 1},  # fail first, then succeed
        verifier=lambda _id: True,
        policy=RecoveryPolicy(max_attempts=3),
        rng=random.Random(3),
        sleep=slept.append,
    )
    out = loop.handle(LATENCY_BREACH, incident_id="i16", playbook=RETRY_PLAYBOOK)
    assert out.resolved
    assert len(slept) >= 1  # backoff slept before the retry that succeeded


# --------------------------------------------------------------- audit -------

def test_audit_chain_is_tamper_evident():
    loop = _loop()
    loop.handle(LATENCY_BREACH, incident_id="i17", playbook=RETRY_PLAYBOOK)
    assert loop.verify_audit()
    assert len(loop.audit.entries) >= 2
    object.__setattr__(loop.audit._entries[0], "detail", {"tampered": True})
    assert loop.verify_audit() is False


def test_audit_write_failure_degrades_to_deny_all():
    class BrokenAudit:
        def record(self, **_):
            raise RuntimeError("ledger down")

        def verify(self):
            return True

    loop = SelfHealingLoop(handlers={"retry": lambda s: True},
                           verifier=lambda _id: True, audit=BrokenAudit())
    # First call trips the degraded flag while logging classification.
    loop.handle(LATENCY_BREACH, incident_id="i18", playbook=RETRY_PLAYBOOK)
    assert loop.degraded
    # Subsequent calls fail closed regardless of how safe the incident looks.
    out = loop.handle(HEALTHY, incident_id="i19", playbook=RETRY_PLAYBOOK)
    assert out.escalated
    assert "deny-all" in out.reason
