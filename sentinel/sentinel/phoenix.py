# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""PHOENIX — governed autonomous recovery / self-healing agent.

PHOENIX is the SENTINEL family's site-reliability persona. It closes the loop
that every incident needs and that ad-hoc automation skips:

    detect -> classify -> contain -> plan -> gate -> execute -> verify -> learn

Doctrine (identical in spirit to the rest of the control plane):

* **Fail-closed.** If any variable needed to authorize a remediation cannot be
  computed — no handler for the action, missing confidence, an audit-write
  failure — the step is *denied and escalated to a human*, never run.
* **Safety over autonomy.** Only reversible, low-blast-radius, high-confidence
  steps auto-execute. Pricing/payment/data-destroying/mass-outbound-class
  actions are escalation-only by policy, exactly like the commerce governor.
* **Contain before you fix.** For containment-class incidents the blast-radius
  limiter (feature-flag off / traffic shed / circuit open) runs *before* any
  remediation, so a bad fix can't widen the outage.
* **No repeated failure loops.** A per-signature circuit breaker + incident
  memory stop PHOENIX from re-running a fix that just failed; after the recovery
  budget is spent it escalates instead of thrashing.
* **Verify, then close.** An incident is only RESOLVED when an independent
  health probe confirms restoration. A remediation that "ran" but didn't restore
  health is treated as a failure and re-routed.
* **Everything is audited.** Every decision and outcome is appended to the
  hash-chained ledger (`audit.py`) so the whole recovery is replayable.

Stdlib only (no third-party deps) so it runs in the same minimal CI environments
as `governance.py`, `governor.py`, and `daily_loop.py`. Time and randomness are
injectable so recovery runs are deterministic under test.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .audit import AuditLog
from .models import Confidence

# --------------------------------------------------------------------------- #
# Domain enums
# --------------------------------------------------------------------------- #


class FailureClass(str, Enum):
    """How an incident should be handled. Order matters: later = more contained."""

    RETRYABLE = "RETRYABLE"      # transient; retry with backoff
    FALLBACK = "FALLBACK"        # degrade gracefully to a secondary path
    CONTAINMENT = "CONTAINMENT"  # limit blast radius first, then remediate
    ESCALATION = "ESCALATION"    # unsafe/unknown/critical -> human-in-the-loop


class IncidentState(str, Enum):
    DETECTED = "DETECTED"
    CLASSIFIED = "CLASSIFIED"
    CONTAINED = "CONTAINED"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"


# --------------------------------------------------------------------------- #
# Telemetry + anomaly detection
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Signal:
    """A single health telemetry sample with an inline SLO band.

    ``healthy_max`` / ``healthy_min`` define the acceptable band; either may be
    ``None`` (open-ended). ``tags`` carry failure signatures used by the
    classifier (e.g. ``("timeout",)``, ``("dependency_down",)``)."""

    name: str
    value: float
    healthy_max: Optional[float] = None
    healthy_min: Optional[float] = None
    weight: float = 1.0
    tags: tuple[str, ...] = ()

    @property
    def breached(self) -> bool:
        if self.healthy_max is not None and self.value > self.healthy_max:
            return True
        if self.healthy_min is not None and self.value < self.healthy_min:
            return True
        return False

    def deviation(self) -> float:
        """How far outside the band (0.0 when healthy), normalized by the bound."""
        if self.healthy_max is not None and self.value > self.healthy_max:
            base = abs(self.healthy_max) or 1.0
            return (self.value - self.healthy_max) / base
        if self.healthy_min is not None and self.value < self.healthy_min:
            base = abs(self.healthy_min) or 1.0
            return (self.healthy_min - self.value) / base
        return 0.0


@dataclass(frozen=True)
class Anomaly:
    signal: str
    value: float
    deviation: float
    weight: float
    tags: tuple[str, ...]


@dataclass(frozen=True)
class ErrorBudget:
    """SLO error budget. ``consumed``/``total`` in the same unit (e.g. minutes)."""

    name: str
    total: float
    consumed: float

    @property
    def burned(self) -> float:
        if self.total <= 0:
            return 1.0
        return min(1.0, self.consumed / self.total)

    @property
    def exhausted(self) -> bool:
        return self.consumed >= self.total


def detect(signals: list[Signal]) -> list[Anomaly]:
    """Pure threshold detection: emit an :class:`Anomaly` per breached signal.

    Kept deliberately simple and stdlib-only; a statistical (z-score/EWMA)
    detector can be swapped in behind the same return type."""
    out: list[Anomaly] = []
    for s in signals:
        if s.breached:
            out.append(Anomaly(s.name, s.value, s.deviation(), s.weight, s.tags))
    return out


def blast_radius(anomalies: list[Anomaly]) -> int:
    """Correlated failure count — how many distinct signals are unhealthy.

    Correlation across many signals is what turns a blip into an outage, so this
    feeds both classification and the policy blast-radius budget."""
    return len({a.signal for a in anomalies})


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #

# Signature tag -> failure class. Deny-biased: the most contained class wins when
# an incident carries several signatures, and anything unknown escalates.
_SIGNATURE_CLASS: dict[str, FailureClass] = {
    "timeout": FailureClass.RETRYABLE,
    "5xx": FailureClass.RETRYABLE,
    "rate_limited": FailureClass.RETRYABLE,
    "connection_reset": FailureClass.RETRYABLE,
    "dependency_down": FailureClass.FALLBACK,
    "stale_cache": FailureClass.FALLBACK,
    "degraded_provider": FailureClass.FALLBACK,
    "cascading_failure": FailureClass.CONTAINMENT,
    "resource_exhaustion": FailureClass.CONTAINMENT,
    "poison_message": FailureClass.CONTAINMENT,
    "data_corruption": FailureClass.ESCALATION,
    "security_incident": FailureClass.ESCALATION,
    "payment_anomaly": FailureClass.ESCALATION,
}

_CLASS_RANK = {
    FailureClass.RETRYABLE: 0,
    FailureClass.FALLBACK: 1,
    FailureClass.CONTAINMENT: 2,
    FailureClass.ESCALATION: 3,
}


def classify(
    anomalies: list[Anomaly],
    *,
    error_budget: Optional[ErrorBudget] = None,
    blast_radius_escalate: int = 4,
) -> FailureClass:
    """Route an incident to a handling class. Fail-safe: unknown => ESCALATION.

    Escalation-forcing conditions (any one wins):
      * an anomaly carries no recognized signature (we don't guess at unknowns),
      * the error budget for the SLO is exhausted (no room to experiment),
      * correlated blast radius is wide enough to look like a systemic outage.
    Otherwise the *most contained* matched class is returned.
    """
    if not anomalies:
        return FailureClass.RETRYABLE  # nothing wrong; a no-op retry is safe

    if error_budget is not None and error_budget.exhausted:
        return FailureClass.ESCALATION
    if blast_radius(anomalies) >= blast_radius_escalate:
        return FailureClass.ESCALATION

    best: Optional[FailureClass] = None
    for a in anomalies:
        matched = [_SIGNATURE_CLASS[t] for t in a.tags if t in _SIGNATURE_CLASS]
        if not matched:
            return FailureClass.ESCALATION  # unknown signature -> human
        top = max(matched, key=lambda c: _CLASS_RANK[c])
        if best is None or _CLASS_RANK[top] > _CLASS_RANK[best]:
            best = top
    return best or FailureClass.ESCALATION


# --------------------------------------------------------------------------- #
# Recovery plan + policy
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RemediationStep:
    """A single safe(ish) action. ``action`` names a handler registered on the
    :class:`SelfHealingLoop`; a step with no handler cannot run (fail-closed)."""

    action: str
    target: str
    reversible: bool
    risk: float              # 0.0 (benign) .. 1.0 (dangerous)
    blast_radius: int = 1    # how many entities this step touches
    note: str = ""


@dataclass(frozen=True)
class RecoveryPlan:
    incident_id: str
    failure_class: FailureClass
    steps: tuple[RemediationStep, ...]
    confidence: float        # calibrated 0..1 confidence this plan restores health

    @property
    def band(self) -> Confidence:
        return Confidence.band(self.confidence)


@dataclass(frozen=True)
class RecoveryPolicy:
    """Guardrails the governor enforces before any step runs. Tighten, never
    loosen, these in production."""

    tau: float = 0.60            # minimum plan confidence to auto-execute
    max_risk: float = 0.50       # per-step risk ceiling for auto-execution
    max_blast_radius: int = 3    # per-step entity budget for auto-execution
    max_attempts: int = 3        # recovery budget per incident
    require_reversible: bool = True
    # Classes that are never auto-executed regardless of score.
    escalation_only: frozenset[FailureClass] = frozenset({FailureClass.ESCALATION})


# --------------------------------------------------------------------------- #
# Retry / backoff, circuit breaker, incident memory
# --------------------------------------------------------------------------- #


def backoff_delays(
    attempts: int,
    *,
    base: float = 0.5,
    cap: float = 30.0,
    rng: Optional[random.Random] = None,
) -> list[float]:
    """Exponential backoff with full jitter. Deterministic when ``rng`` is seeded.

    delay_i = uniform(0, min(cap, base * 2**i)) — the AWS 'full jitter' recipe,
    which spreads retries and avoids thundering-herd re-failure."""
    r = rng or random.Random()
    delays: list[float] = []
    for i in range(max(0, attempts)):
        ceiling = min(cap, base * (2 ** i))
        delays.append(round(r.uniform(0.0, ceiling), 4))
    return delays


class CircuitBreaker:
    """Trips open after ``threshold`` consecutive failures; blocks execution
    while open so PHOENIX can't hammer a broken dependency. A single success
    (typically a verified recovery) closes it again."""

    def __init__(self, threshold: int = 3) -> None:
        self.threshold = threshold
        self._failures = 0
        self.opened = False

    @property
    def closed(self) -> bool:
        return not self.opened

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self.opened = True

    def record_success(self) -> None:
        self._failures = 0
        self.opened = False


@dataclass
class _FixStats:
    attempts: int = 0
    successes: int = 0
    consecutive_failures: int = 0


class IncidentMemory:
    """Root-cause memory: learns which (signature, action) fixes actually work.

    Feeds two decisions:
      * confidence for a proposed step (Bayesian-ish smoothed success rate), and
      * whether a fix has failed enough times in a row that PHOENIX should stop
        trying it and escalate (repeated-failure-loop guard).
    In production this is a durable table; here it is in-process and replayable.
    """

    # The prior defaults to the policy tau (0.60): a playbook step with no track
    # record is trusted *just* enough to attempt once, sitting exactly at the
    # auto-execute threshold. Every observed failure pulls it below tau (the next
    # occurrence escalates); every success lifts it clear.
    def __init__(self, *, loop_guard: int = 2, prior: float = 0.60, prior_weight: float = 2.0) -> None:
        self.loop_guard = loop_guard
        self.prior = prior
        self.prior_weight = prior_weight
        self._stats: dict[tuple[str, str], _FixStats] = {}

    @staticmethod
    def _key(signature: str, action: str) -> tuple[str, str]:
        return (signature, action)

    def confidence_for(self, signature: str, action: str) -> float:
        """Smoothed historical success rate, blended with a neutral prior so a
        brand-new fix starts at ``prior`` rather than 0 or 1."""
        st = self._stats.get(self._key(signature, action))
        succ = st.successes if st else 0
        att = st.attempts if st else 0
        return (succ + self.prior * self.prior_weight) / (att + self.prior_weight)

    def should_escalate(self, signature: str, action: str) -> bool:
        st = self._stats.get(self._key(signature, action))
        return bool(st and st.consecutive_failures >= self.loop_guard)

    def record(self, signature: str, action: str, *, success: bool) -> None:
        st = self._stats.setdefault(self._key(signature, action), _FixStats())
        st.attempts += 1
        if success:
            st.successes += 1
            st.consecutive_failures = 0
        else:
            st.consecutive_failures += 1


# --------------------------------------------------------------------------- #
# Outcomes
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class StepResult:
    step: RemediationStep
    executed: bool
    success: bool
    reason: str
    attempts: int = 0


@dataclass
class RecoveryOutcome:
    incident_id: str
    failure_class: FailureClass
    state: IncidentState
    steps: list[StepResult] = field(default_factory=list)
    escalated: bool = False
    reason: str = ""
    confidence: Optional[float] = None

    @property
    def resolved(self) -> bool:
        return self.state is IncidentState.RESOLVED

    def summary(self) -> dict[str, object]:
        return {
            "incident_id": self.incident_id,
            "failure_class": self.failure_class.value,
            "state": self.state.value,
            "escalated": self.escalated,
            "reason": self.reason,
            "confidence": self.confidence,
            "steps": [
                {
                    "action": r.step.action,
                    "target": r.step.target,
                    "executed": r.executed,
                    "success": r.success,
                    "attempts": r.attempts,
                    "reason": r.reason,
                }
                for r in self.steps
            ],
        }


# handler(step) -> True on success, False on failure. Raising is treated as
# a failed attempt (fail-closed), never a crash of the loop.
Handler = Callable[[RemediationStep], bool]
# verifier(incident_id) -> True once an independent health probe passes.
Verifier = Callable[[str], bool]


# --------------------------------------------------------------------------- #
# The governed self-healing loop
# --------------------------------------------------------------------------- #


class SelfHealingLoop:
    """Orchestrates the full recovery loop under a fail-closed policy gate.

    Wiring:
      * ``handlers`` — action name -> callable performing the (safe) side effect.
        An action with no handler cannot execute and forces escalation.
      * ``verifier`` — independent health probe; an incident only resolves when
        it returns True. Absent verifier == unverifiable == escalate (fail-closed).
      * ``policy`` — the guardrails (confidence/risk/blast-radius/budget).
      * ``memory`` / ``breaker`` — learning + anti-thrash controls.
      * ``audit`` — hash-chained ledger; a write failure degrades to deny-all.
    """

    def __init__(
        self,
        *,
        handlers: Optional[dict[str, Handler]] = None,
        verifier: Optional[Verifier] = None,
        policy: Optional[RecoveryPolicy] = None,
        memory: Optional[IncidentMemory] = None,
        breaker: Optional[CircuitBreaker] = None,
        audit: Optional[AuditLog] = None,
        rng: Optional[random.Random] = None,
        sleep: Optional[Callable[[float], None]] = None,
    ) -> None:
        self.handlers = dict(handlers or {})
        self.verifier = verifier
        self.policy = policy or RecoveryPolicy()
        self.memory = memory or IncidentMemory()
        self.breaker = breaker or CircuitBreaker()
        self.audit = audit or AuditLog()
        self.rng = rng or random.Random()
        # Injected so tests never actually block; a real deployment passes
        # ``time.sleep`` to space out retries with the computed backoff.
        self.sleep = sleep
        self.degraded = False  # tripped when the audit ledger can't be written

    # ---- planning ---------------------------------------------------------- #

    def plan(
        self,
        incident_id: str,
        failure_class: FailureClass,
        steps: list[RemediationStep],
        *,
        signature: str,
    ) -> RecoveryPlan:
        """Score a proposed plan using incident memory. Plan confidence is the
        *minimum* per-step confidence (a chain is only as strong as its weakest
        link), so one historically-flaky step drags the whole plan below tau."""
        if not steps:
            return RecoveryPlan(incident_id, failure_class, (), 0.0)
        confidences = [self.memory.confidence_for(signature, s.action) for s in steps]
        return RecoveryPlan(incident_id, failure_class, tuple(steps), min(confidences))

    # ---- the gate ---------------------------------------------------------- #

    def _gate(self, plan: RecoveryPlan, step: RemediationStep, signature: str) -> tuple[bool, str]:
        """Fail-closed authorization for a single step. Returns (allow, reason)."""
        p = self.policy
        if plan.failure_class in p.escalation_only:
            return False, f"{plan.failure_class.value} is escalation-only by policy"
        if self.breaker.opened:
            return False, "circuit breaker open (repeated failures) — escalate"
        if self.memory.should_escalate(signature, step.action):
            return False, "fix in a repeated-failure loop — escalate"
        if step.action not in self.handlers:
            return False, f"no handler for action {step.action!r} (fail-closed)"
        if p.require_reversible and not step.reversible:
            return False, "step is irreversible — escalate"
        if step.risk >= p.max_risk:
            return False, f"risk {step.risk:.2f} >= ceiling {p.max_risk:.2f} — escalate"
        if step.blast_radius > p.max_blast_radius:
            return False, f"blast radius {step.blast_radius} > budget {p.max_blast_radius} — escalate"
        if plan.confidence < p.tau:
            return False, f"confidence {plan.confidence:.2f} < tau {p.tau:.2f} — escalate"
        return True, "within policy"

    # ---- execution with retry + backoff ----------------------------------- #

    def _execute_step(self, step: RemediationStep, signature: str) -> StepResult:
        handler = self.handlers[step.action]
        delays = backoff_delays(self.policy.max_attempts, rng=self.rng)
        attempts = 0
        for attempts in range(1, self.policy.max_attempts + 1):
            if attempts > 1 and self.sleep is not None:
                self.sleep(delays[attempts - 1])  # exponential backoff + jitter
            try:
                ok = bool(handler(step))
            except Exception as exc:  # noqa: BLE001 — a raising handler is a failed attempt
                ok = False
                last = f"handler raised {type(exc).__name__}"
            else:
                last = "ok" if ok else "handler returned failure"
            if ok:
                self.breaker.record_success()
                self.memory.record(signature, step.action, success=True)
                return StepResult(step, executed=True, success=True, reason=last, attempts=attempts)
        # exhausted the recovery budget
        self.breaker.record_failure()
        self.memory.record(signature, step.action, success=False)
        return StepResult(step, executed=True, success=False, reason=last, attempts=attempts)

    # ---- the loop ---------------------------------------------------------- #

    def handle(
        self,
        signals: list[Signal],
        *,
        incident_id: str,
        playbook: dict[FailureClass, list[RemediationStep]],
        containment: Optional[RemediationStep] = None,
        error_budget: Optional[ErrorBudget] = None,
    ) -> RecoveryOutcome:
        """Run one full recovery cycle for a set of health signals.

        ``playbook`` maps a failure class to its ordered remediation steps.
        ``containment`` (optional) is a blast-radius limiter run *before*
        remediation for CONTAINMENT-class incidents."""
        anomalies = detect(signals)
        signature = _signature_of(anomalies)

        if self.degraded:
            return self._escalate(incident_id, FailureClass.ESCALATION,
                                  "audit ledger unavailable — degraded to deny-all")

        # No breach -> nothing to do. Record a healthy heartbeat and return.
        if not anomalies:
            self._log("healthy", {"incident_id": incident_id})
            return RecoveryOutcome(incident_id, FailureClass.RETRYABLE,
                                   IncidentState.RESOLVED, reason="no anomaly detected")

        fclass = classify(anomalies, error_budget=error_budget)
        self._log("classified", {
            "incident_id": incident_id, "class": fclass.value,
            "signature": signature, "blast_radius": blast_radius(anomalies),
        })

        outcome = RecoveryOutcome(incident_id, fclass, IncidentState.CLASSIFIED)

        # Escalation-class incidents never auto-remediate.
        if fclass in self.policy.escalation_only:
            return self._escalate(incident_id, fclass,
                                  "classified escalation-only — human approval required")

        # Contain first (limit blast radius) for containment-class incidents.
        if fclass is FailureClass.CONTAINMENT:
            if containment is None or containment.action not in self.handlers:
                return self._escalate(incident_id, fclass,
                                      "containment required but no containment handler — escalate")
            contain_res = self._execute_step(containment, signature)
            outcome.steps.append(contain_res)
            if not contain_res.success:
                outcome.state = IncidentState.ESCALATED
                outcome.escalated = True
                outcome.reason = "containment failed — escalate"
                self._log("escalate", {"incident_id": incident_id, "reason": outcome.reason})
                return outcome
            outcome.state = IncidentState.CONTAINED

        steps = list(playbook.get(fclass, []))
        if not steps:
            return self._escalate(incident_id, fclass, "no remediation in playbook — escalate")

        plan = self.plan(incident_id, fclass, steps, signature=signature)
        outcome.confidence = plan.confidence
        outcome.state = IncidentState.REMEDIATING

        for step in plan.steps:
            allow, reason = self._gate(plan, step, signature)
            if not allow:
                outcome.steps.append(StepResult(step, executed=False, success=False, reason=reason))
                self._log("gate_deny", {"incident_id": incident_id, "action": step.action, "reason": reason})
                outcome.state = IncidentState.ESCALATED
                outcome.escalated = True
                outcome.reason = reason
                return self._record_outcome(outcome)
            res = self._execute_step(step, signature)
            outcome.steps.append(res)
            self._log("remediate", {
                "incident_id": incident_id, "action": step.action,
                "success": res.success, "attempts": res.attempts,
            })
            if not res.success:
                outcome.state = IncidentState.ESCALATED
                outcome.escalated = True
                outcome.reason = f"remediation {step.action!r} failed after {res.attempts} attempts — escalate"
                return self._record_outcome(outcome)

        # ---- verify before closing ---------------------------------------- #
        outcome.state = IncidentState.VERIFYING
        if self.verifier is None:
            outcome.state = IncidentState.ESCALATED
            outcome.escalated = True
            outcome.reason = "no health verifier — restoration unverifiable, escalate (fail-closed)"
            return self._record_outcome(outcome)
        try:
            restored = bool(self.verifier(incident_id))
        except Exception as exc:  # noqa: BLE001 — an unverifiable probe fails closed
            restored = False
            outcome.reason = f"verifier raised {type(exc).__name__} — escalate"
        if restored:
            outcome.state = IncidentState.RESOLVED
            outcome.reason = "remediation verified — health restored"
        else:
            outcome.state = IncidentState.ESCALATED
            outcome.escalated = True
            outcome.reason = outcome.reason or "remediation ran but health not restored — escalate"
        return self._record_outcome(outcome)

    # ---- helpers ----------------------------------------------------------- #

    def _escalate(self, incident_id: str, fclass: FailureClass, reason: str) -> RecoveryOutcome:
        out = RecoveryOutcome(incident_id, fclass, IncidentState.ESCALATED, escalated=True, reason=reason)
        self._log("escalate", {"incident_id": incident_id, "class": fclass.value, "reason": reason})
        return out

    def _record_outcome(self, outcome: RecoveryOutcome) -> RecoveryOutcome:
        self._log("outcome", outcome.summary())
        return outcome

    def _log(self, action: str, detail: dict[str, object]) -> None:
        try:
            self.audit.record(actor="phoenix", action=action, detail=detail)
        except Exception:  # noqa: BLE001 — auditability is mandatory; degrade to deny-all
            self.degraded = True

    def verify_audit(self) -> bool:
        return self.audit.verify()


def _signature_of(anomalies: list[Anomaly]) -> str:
    """A stable signature for the incident: sorted union of signal tags (falling
    back to signal names) — the key incident memory learns against."""
    tags: set[str] = set()
    for a in anomalies:
        tags.update(a.tags or (a.signal,))
    return "|".join(sorted(tags)) if tags else "unknown"


__all__ = [
    "FailureClass",
    "IncidentState",
    "Signal",
    "Anomaly",
    "ErrorBudget",
    "detect",
    "blast_radius",
    "classify",
    "RemediationStep",
    "RecoveryPlan",
    "RecoveryPolicy",
    "backoff_delays",
    "CircuitBreaker",
    "IncidentMemory",
    "StepResult",
    "RecoveryOutcome",
    "SelfHealingLoop",
]
