# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""ARTEMIS // FAWL — governed self-healing lifecycle control plane.

This is the *governance spine* the PHOENIX recovery engines (``phoenix.py`` /
``selfheal.py``) plug into. Those modules decide *what* to remediate; ARTEMIS //
FAWL decides *whether an action is allowed to run at all*, drives the incident
through an **enforced** state machine, and mints a single-use, short-lived,
narrowly-scoped capability for each approved action.

It adds the three controls the recovery engines assume but do not themselves
enforce:

1. **Enforced lifecycle state machine.** The full
   DETECTED → … → CLOSED lifecycle (plus the ROLLBACK / QUARANTINE / ESCALATION
   failure paths) with an explicit allowed-transition table. Illegal
   transitions raise :class:`InvalidTransition`; every accepted transition is
   persisted to the hash-chained audit log with actor, timestamp, evidence,
   correlation id, and reason.

2. **Automation safety levels 0–4 + a fail-closed Policy Decision Point.** Every
   action is scored 0 (observe) … 4 (prohibited). The PDP evaluates actor,
   confidence, blast radius, recovery budget, the emergency kill switch, and
   the AI-safety boundary, and returns PERMIT / REQUIRE_APPROVAL / DENY. Any
   unverifiable term denies. Level-4 never runs. AI-originated actions can
   never self-authorize at level ≥ 2.

3. **Short-lived capability tokens.** An approved decision mints one token bound
   to exactly one action against one target, with an expiry and an idempotency
   key, redeemable exactly once. No token ⇒ no execution.

Pure stdlib, no side effects: all real remediation happens through injected
``executor`` / ``verifier`` callables, so the whole spine is testable offline.
"""
from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Callable, Optional

from .audit import AuditLog

# --------------------------------------------------------------------------- #
# Lifecycle state machine
# --------------------------------------------------------------------------- #


class LifecycleState(str, Enum):
    """The ARTEMIS // FAWL incident lifecycle. Happy path then failure paths."""

    DETECTED = "DETECTED"
    VALIDATING = "VALIDATING"
    CORRELATED = "CORRELATED"
    CLASSIFIED = "CLASSIFIED"
    CONTAINMENT_PENDING = "CONTAINMENT_PENDING"
    CONTAINED = "CONTAINED"
    PLAN_GENERATED = "PLAN_GENERATED"
    AUTHORIZATION_PENDING = "AUTHORIZATION_PENDING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    RECOVERED = "RECOVERED"
    MONITORING = "MONITORING"
    CLOSED = "CLOSED"
    # failure / safety paths
    ESCALATED = "ESCALATED"
    ROLLBACK_PENDING = "ROLLBACK_PENDING"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    QUARANTINED = "QUARANTINED"
    MANUAL_INTERVENTION_REQUIRED = "MANUAL_INTERVENTION_REQUIRED"


_S = LifecycleState

# Explicit allowed transitions. Anything not listed is rejected (fail-closed).
TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    _S.DETECTED: frozenset({_S.VALIDATING, _S.QUARANTINED}),
    _S.VALIDATING: frozenset({_S.CORRELATED, _S.ESCALATED, _S.QUARANTINED}),
    _S.CORRELATED: frozenset({_S.CLASSIFIED, _S.ESCALATED}),
    _S.CLASSIFIED: frozenset({_S.CONTAINMENT_PENDING, _S.ESCALATED}),
    _S.CONTAINMENT_PENDING: frozenset({_S.CONTAINED, _S.ESCALATED, _S.QUARANTINED}),
    _S.CONTAINED: frozenset({_S.PLAN_GENERATED, _S.ESCALATED}),
    _S.PLAN_GENERATED: frozenset({_S.AUTHORIZATION_PENDING, _S.ESCALATED}),
    _S.AUTHORIZATION_PENDING: frozenset(
        {_S.EXECUTING, _S.ESCALATED, _S.MANUAL_INTERVENTION_REQUIRED}
    ),
    _S.EXECUTING: frozenset({_S.VERIFYING, _S.ROLLBACK_PENDING}),
    _S.VERIFYING: frozenset({_S.RECOVERED, _S.ROLLBACK_PENDING, _S.ESCALATED}),
    _S.RECOVERED: frozenset({_S.MONITORING}),
    _S.MONITORING: frozenset({_S.CLOSED, _S.ROLLBACK_PENDING}),
    _S.ROLLBACK_PENDING: frozenset({_S.ROLLING_BACK}),
    _S.ROLLING_BACK: frozenset({_S.ROLLED_BACK, _S.MANUAL_INTERVENTION_REQUIRED}),
    _S.ROLLED_BACK: frozenset({_S.CLOSED, _S.ESCALATED}),
    _S.ESCALATED: frozenset({_S.CLOSED, _S.MANUAL_INTERVENTION_REQUIRED}),
    # terminal
    _S.CLOSED: frozenset(),
    _S.QUARANTINED: frozenset(),
    _S.MANUAL_INTERVENTION_REQUIRED: frozenset(),
}

TERMINAL_STATES = frozenset({_S.CLOSED, _S.QUARANTINED, _S.MANUAL_INTERVENTION_REQUIRED})


class InvalidTransition(Exception):
    """Raised when a lifecycle transition is not in the allowed table."""


@dataclass(frozen=True)
class Transition:
    seq: int
    frm: LifecycleState
    to: LifecycleState
    actor: str
    reason: str
    correlation_id: str
    ts: float


class StateMachine:
    """An enforced, audited incident lifecycle.

    ``to()`` rejects any transition not in :data:`TRANSITIONS` and records every
    accepted transition to the hash-chained audit log. The emergency kill switch
    (:meth:`quarantine`) is the *only* way to leave the happy path from an
    arbitrary active state, and it too is audited.
    """

    def __init__(self, correlation_id: str, *, audit: Optional[AuditLog] = None,
                 clock: Callable[[], float] = time.time) -> None:
        self.correlation_id = correlation_id
        self.state = LifecycleState.DETECTED
        self.audit = audit or AuditLog()
        self._clock = clock
        self.history: list[Transition] = []

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def can(self, target: LifecycleState) -> bool:
        return target in TRANSITIONS.get(self.state, frozenset())

    def to(self, target: LifecycleState, *, actor: str, reason: str,
           evidence: Optional[dict] = None) -> Transition:
        if not self.can(target):
            raise InvalidTransition(
                f"{self.state.value} → {target.value} is not permitted"
            )
        return self._commit(target, actor=actor, reason=reason, evidence=evidence or {})

    def quarantine(self, *, actor: str, reason: str) -> Transition:
        """Emergency kill switch: halt automation for this incident from any
        active state. Observation/audit continue; no further remediation runs."""
        if self.terminal:
            raise InvalidTransition(f"already terminal ({self.state.value})")
        return self._commit(LifecycleState.QUARANTINED, actor=actor,
                            reason=reason, evidence={"kill_switch": True})

    def _commit(self, target: LifecycleState, *, actor: str, reason: str,
                evidence: dict) -> Transition:
        t = Transition(
            seq=len(self.history), frm=self.state, to=target, actor=actor,
            reason=reason, correlation_id=self.correlation_id, ts=self._clock(),
        )
        self.audit.record(actor=actor, action=f"transition:{self.state.value}->{target.value}",
                          detail={"correlation_id": self.correlation_id, "reason": reason,
                                  "evidence": evidence})
        self.state = target
        self.history.append(t)
        return t


# --------------------------------------------------------------------------- #
# Automation safety levels
# --------------------------------------------------------------------------- #


class SafetyLevel(IntEnum):
    OBSERVE = 0            # read-only; always allowed, even under kill switch
    LOW_REVERSIBLE = 1    # safe, reversible, low-impact
    BOUNDED_PRODUCTION = 2  # bounded prod action; strong evidence + approval
    HUMAN_AUTHORIZED = 3  # high-impact; explicit human authorization
    PROHIBITED = 4        # automation must NEVER execute


# Risk thresholds mirror the commerce/PHOENIX 0–100 governance band.
_RISK_LOW = 30
_RISK_HIGH = 70
_RISK_PROHIBITED = 95


@dataclass(frozen=True)
class Action:
    key: str
    target: str
    risk: int                    # 0..100
    reversible: bool
    kind: str = "remediate"      # observe | remediate | contain | rollback | …
    ai_originated: bool = False  # proposed by a model → extra scrutiny
    prohibited: bool = False     # hard deny-list entry

    def safety_level(self) -> SafetyLevel:
        if self.prohibited or self.risk >= _RISK_PROHIBITED:
            return SafetyLevel.PROHIBITED
        if self.kind == "observe":
            return SafetyLevel.OBSERVE
        if self.reversible and self.risk < _RISK_LOW:
            return SafetyLevel.LOW_REVERSIBLE
        if self.reversible and self.risk < _RISK_HIGH:
            return SafetyLevel.BOUNDED_PRODUCTION
        return SafetyLevel.HUMAN_AUTHORIZED


# --------------------------------------------------------------------------- #
# Policy Decision Point
# --------------------------------------------------------------------------- #


class Verdict(str, Enum):
    PERMIT = "PERMIT"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"


@dataclass(frozen=True)
class PolicyContext:
    actor: str = "automation"          # human | automation | ai
    confidence: Optional[float] = None  # None ⇒ unverifiable ⇒ deny
    blast_radius: int = 1
    blast_ceiling: int = 5
    recovery_budget_remaining: int = 3
    kill_switch: bool = False           # emergency freeze active
    approval_token: Optional[str] = None
    tau: float = 0.60
    tau_high: float = 0.80


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    action: Action
    level: SafetyLevel
    reasons: tuple[str, ...]

    @property
    def permitted(self) -> bool:
        return self.verdict is Verdict.PERMIT


class PolicyDecisionPoint:
    """Fail-closed authorization. Every branch that cannot verify a term denies
    or downgrades to REQUIRE_APPROVAL — never silently permits."""

    def evaluate(self, action: Action, ctx: PolicyContext) -> Decision:
        level = action.safety_level()

        # Observation is always allowed — even under the kill switch — because
        # halting automation must never blind the operator.
        if level is SafetyLevel.OBSERVE:
            return Decision(Verdict.PERMIT, action, level, ("observation is always permitted",))

        # Emergency freeze halts all mutating automation.
        if ctx.kill_switch:
            return Decision(Verdict.DENY, action, level, ("kill switch active: automation frozen",))

        # Prohibited actions never run, by anyone, ever.
        if level is SafetyLevel.PROHIBITED:
            return Decision(Verdict.DENY, action, level,
                            (f"action '{action.key}' is safety level 4 (prohibited)",))

        # Unverifiable confidence ⇒ deny.
        if ctx.confidence is None:
            return Decision(Verdict.DENY, action, level, ("confidence unverifiable (fail-closed)",))

        # Recovery budget exhausted ⇒ escalate for approval, do not loop.
        if ctx.recovery_budget_remaining <= 0:
            return Decision(Verdict.REQUIRE_APPROVAL, action, level,
                            ("recovery budget exhausted → human approval required",))

        # Blast radius over the ceiling ⇒ approval.
        if ctx.blast_radius > ctx.blast_ceiling:
            return Decision(Verdict.REQUIRE_APPROVAL, action, level,
                            (f"blast radius {ctx.blast_radius} > ceiling {ctx.blast_ceiling}",))

        # AI-safety boundary: a model-proposed action can never self-authorize a
        # bounded-production-or-higher change. It must go to a human.
        if action.ai_originated and level >= SafetyLevel.BOUNDED_PRODUCTION:
            if not (ctx.actor == "human" and ctx.approval_token):
                return Decision(Verdict.REQUIRE_APPROVAL, action, level,
                                ("AI-originated level ≥ 2 action requires human approval",))

        reasons: list[str] = []
        if level is SafetyLevel.LOW_REVERSIBLE:
            if ctx.confidence >= ctx.tau:
                return Decision(Verdict.PERMIT, action, level,
                                ("level 1 reversible, confidence ≥ tau → auto",))
            reasons.append(f"confidence {ctx.confidence:.2f} < tau {ctx.tau:.2f}")
            return Decision(Verdict.REQUIRE_APPROVAL, action, level, tuple(reasons))

        if level is SafetyLevel.BOUNDED_PRODUCTION:
            if ctx.approval_token and ctx.confidence >= ctx.tau_high:
                return Decision(Verdict.PERMIT, action, level,
                                ("level 2 with approval + high confidence → permit",))
            if ctx.confidence < ctx.tau_high:
                reasons.append(f"confidence {ctx.confidence:.2f} < tau_high {ctx.tau_high:.2f}")
            if not ctx.approval_token:
                reasons.append("bounded production action requires approval")
            return Decision(Verdict.REQUIRE_APPROVAL, action, level, tuple(reasons))

        # HUMAN_AUTHORIZED (level 3)
        if ctx.actor == "human" and ctx.approval_token:
            return Decision(Verdict.PERMIT, action, level,
                            ("level 3 with explicit human authorization → permit",))
        return Decision(Verdict.REQUIRE_APPROVAL, action, level,
                        ("high-impact action requires explicit human authorization",))


# --------------------------------------------------------------------------- #
# Short-lived capability tokens
# --------------------------------------------------------------------------- #


class CapabilityError(Exception):
    """Raised when a capability token is invalid, expired, mismatched, or reused."""


@dataclass
class CapabilityToken:
    token_id: str
    action_key: str
    target: str
    idempotency_key: str
    issued_at: float
    expires_at: float
    _used: bool = field(default=False, repr=False)


class CapabilityBroker:
    """Mints single-action, single-target, short-lived, single-use capabilities.

    A token authorizes exactly one ``action_key`` against exactly one
    ``target``, expires after ``ttl`` seconds, and can be redeemed only once —
    the least-privilege boundary between "approved" and "executed".
    """

    def __init__(self, *, ttl: float = 30.0, clock: Callable[[], float] = time.time) -> None:
        self.ttl = ttl
        self._clock = clock

    def issue(self, decision: Decision) -> CapabilityToken:
        if not decision.permitted:
            raise CapabilityError(
                f"cannot issue capability for non-permitted decision ({decision.verdict.value})"
            )
        now = self._clock()
        seed = f"{decision.action.key}|{decision.action.target}|{now}|{uuid.uuid4()}"
        return CapabilityToken(
            token_id="CAP-" + hashlib.sha256(seed.encode()).hexdigest()[:16].upper(),
            action_key=decision.action.key,
            target=decision.action.target,
            idempotency_key=hashlib.sha256(seed.encode()).hexdigest()[:24],
            issued_at=now,
            expires_at=now + self.ttl,
        )

    def redeem(self, token: CapabilityToken, action: Action) -> None:
        """Validate + burn a token for exactly one action. Fail-closed."""
        now = self._clock()
        if token._used:
            raise CapabilityError("capability already redeemed (single-use)")
        if now > token.expires_at:
            raise CapabilityError("capability expired")
        if token.action_key != action.key or token.target != action.target:
            raise CapabilityError("capability scope mismatch (action/target)")
        token._used = True


# --------------------------------------------------------------------------- #
# Orchestrator — drive an incident through the enforced lifecycle
# --------------------------------------------------------------------------- #


@dataclass
class IncidentInput:
    incident_id: str
    signal_valid: bool = True          # False ⇒ validation fails ⇒ escalate
    signal_malicious: bool = False     # True ⇒ quarantine (poisoned telemetry)
    action: Optional[Action] = None
    ctx: PolicyContext = field(default_factory=PolicyContext)


@dataclass
class Receipt:
    incident_id: str
    final_state: LifecycleState
    verdict: Optional[Verdict]
    level: Optional[SafetyLevel]
    executed: bool
    verified: Optional[bool]
    reasons: list[str] = field(default_factory=list)
    transitions: list[str] = field(default_factory=list)
    audit_verified: bool = True

    def to_dict(self) -> dict:
        return {
            "incident_id": self.incident_id,
            "final_state": self.final_state.value,
            "verdict": self.verdict.value if self.verdict else None,
            "safety_level": int(self.level) if self.level is not None else None,
            "executed": self.executed,
            "verified": self.verified,
            "reasons": list(self.reasons),
            "transitions": list(self.transitions),
            "audit_verified": self.audit_verified,
        }


Executor = Callable[[Action, CapabilityToken], bool]
Verifier = Callable[[Action], bool]


class FawlOrchestrator:
    """Runs one incident through the enforced state machine + PDP + broker.

    Composition, not replacement: the PHOENIX engines decide the ``Action``;
    this class governs whether/how it runs and records the receipt.
    """

    def __init__(self, *, pdp: Optional[PolicyDecisionPoint] = None,
                 broker: Optional[CapabilityBroker] = None,
                 audit: Optional[AuditLog] = None,
                 clock: Callable[[], float] = time.time) -> None:
        self.pdp = pdp or PolicyDecisionPoint()
        self.broker = broker or CapabilityBroker(clock=clock)
        self.audit = audit or AuditLog()
        self._clock = clock

    def run(self, inc: IncidentInput, *, executor: Executor, verifier: Verifier) -> Receipt:
        sm = StateMachine(inc.incident_id, audit=self.audit, clock=self._clock)
        rec = Receipt(inc.incident_id, sm.state, None, None, executed=False, verified=None)

        def record(state: LifecycleState) -> None:
            rec.transitions.append(state.value)
            rec.final_state = state

        # DETECT → VALIDATE
        sm.to(_S.VALIDATING, actor="automation", reason="begin validation")
        record(_S.VALIDATING)
        if inc.signal_malicious:
            sm.quarantine(actor="automation", reason="malicious/poisoned telemetry")
            record(_S.QUARANTINED)
            rec.reasons.append("signal flagged malicious → quarantined")
            rec.audit_verified = self.audit.verify()
            return rec
        if not inc.signal_valid:
            sm.to(_S.ESCALATED, actor="automation", reason="signal failed validation")
            record(_S.ESCALATED)
            rec.reasons.append("signal invalid → escalated")
            rec.audit_verified = self.audit.verify()
            return rec

        # VALIDATE → CORRELATE → CLASSIFY → CONTAIN
        sm.to(_S.CORRELATED, actor="automation", reason="signals correlated")
        record(_S.CORRELATED)
        sm.to(_S.CLASSIFIED, actor="automation", reason="incident classified")
        record(_S.CLASSIFIED)
        sm.to(_S.CONTAINMENT_PENDING, actor="automation", reason="containment planned")
        record(_S.CONTAINMENT_PENDING)
        sm.to(_S.CONTAINED, actor="automation", reason="blast radius contained")
        record(_S.CONTAINED)

        # PLAN → AUTHORIZE (PDP)
        sm.to(_S.PLAN_GENERATED, actor="automation", reason="recovery plan generated")
        record(_S.PLAN_GENERATED)
        action = inc.action
        if action is None:
            sm.to(_S.AUTHORIZATION_PENDING, actor="automation", reason="no action to authorize")
            record(_S.AUTHORIZATION_PENDING)
            sm.to(_S.ESCALATED, actor="automation", reason="no remediation available")
            record(_S.ESCALATED)
            rec.reasons.append("no action → escalated")
            rec.audit_verified = self.audit.verify()
            return rec

        sm.to(_S.AUTHORIZATION_PENDING, actor="automation", reason="policy evaluation")
        record(_S.AUTHORIZATION_PENDING)
        decision = self.pdp.evaluate(action, inc.ctx)
        rec.verdict, rec.level = decision.verdict, decision.level
        rec.reasons.extend(decision.reasons)

        if decision.verdict is not Verdict.PERMIT:
            target = (_S.MANUAL_INTERVENTION_REQUIRED
                      if decision.verdict is Verdict.DENY
                      else _S.ESCALATED)
            sm.to(target, actor="policy", reason=f"PDP {decision.verdict.value}")
            record(target)
            rec.audit_verified = self.audit.verify()
            return rec

        # EXECUTE under a single-use capability token.
        token = self.broker.issue(decision)
        sm.to(_S.EXECUTING, actor="automation", reason=f"capability {token.token_id}")
        record(_S.EXECUTING)
        try:
            self.broker.redeem(token, action)
            ok = bool(executor(action, token))
        except CapabilityError as exc:
            sm.to(_S.ROLLBACK_PENDING, actor="automation", reason=f"capability error: {exc}")
            record(_S.ROLLBACK_PENDING)
            ok = False
        rec.executed = ok

        if not ok:
            self._rollback(sm, rec)
            return rec

        # VERIFY independently.
        sm.to(_S.VERIFYING, actor="automation", reason="independent verification")
        record(_S.VERIFYING)
        verified = bool(verifier(action))
        rec.verified = verified
        if not verified:
            sm.to(_S.ROLLBACK_PENDING, actor="automation", reason="verification failed")
            record(_S.ROLLBACK_PENDING)
            self._rollback(sm, rec, from_pending=True)
            return rec

        # RECOVER → MONITOR → CLOSE
        sm.to(_S.RECOVERED, actor="automation", reason="restoration verified")
        record(_S.RECOVERED)
        sm.to(_S.MONITORING, actor="automation", reason="post-recovery monitoring")
        record(_S.MONITORING)
        sm.to(_S.CLOSED, actor="automation", reason="incident closed")
        record(_S.CLOSED)
        rec.audit_verified = self.audit.verify()
        return rec

    def _rollback(self, sm: StateMachine, rec: Receipt, *, from_pending: bool = False) -> None:
        if not from_pending:
            # came straight from EXECUTING failure
            if sm.state is _S.EXECUTING:
                sm.to(_S.ROLLBACK_PENDING, actor="automation", reason="execution failed")
                rec.transitions.append(_S.ROLLBACK_PENDING.value)
        sm.to(_S.ROLLING_BACK, actor="automation", reason="rolling back remediation")
        rec.transitions.append(_S.ROLLING_BACK.value)
        sm.to(_S.ROLLED_BACK, actor="automation", reason="rollback complete")
        rec.transitions.append(_S.ROLLED_BACK.value)
        sm.to(_S.ESCALATED, actor="automation", reason="rolled back → escalate for review")
        rec.transitions.append(_S.ESCALATED.value)
        rec.final_state = _S.ESCALATED
        rec.reasons.append("remediation failed → rolled back → escalated")
        rec.audit_verified = self.audit.verify()


# --------------------------------------------------------------------------- #
# Reference scenarios + self-check  —  python -m sentinel.artemis_fawl [--json]
# --------------------------------------------------------------------------- #


def _scenarios() -> list[IncidentInput]:
    safe = Action("restart_worker", "checkout-api", risk=20, reversible=True)
    bounded = Action("reroute_standby", "payments", risk=55, reversible=True)
    high = Action("failover_primary", "ledger-db", risk=90, reversible=False)
    prohibited = Action("wipe_volume", "ledger-db", risk=99, reversible=False, prohibited=True)
    ai_bounded = Action("scale_out", "search", risk=50, reversible=True, ai_originated=True)
    return [
        IncidentInput("INC-A", action=safe,
                      ctx=PolicyContext(confidence=0.9)),
        IncidentInput("INC-B", action=bounded,
                      ctx=PolicyContext(confidence=0.9, approval_token="APV-1")),
        IncidentInput("INC-C", action=high,
                      ctx=PolicyContext(actor="automation", confidence=0.95)),
        IncidentInput("INC-D", action=prohibited,
                      ctx=PolicyContext(actor="human", confidence=0.99, approval_token="APV-9")),
        IncidentInput("INC-E", action=ai_bounded,
                      ctx=PolicyContext(actor="automation", confidence=0.95)),
        IncidentInput("INC-F", action=safe, signal_malicious=True,
                      ctx=PolicyContext(confidence=0.9)),
        IncidentInput("INC-G", action=safe,
                      ctx=PolicyContext(confidence=0.9, kill_switch=True)),
    ]


def run_self_check() -> tuple[list[Receipt], list[tuple[str, bool]]]:
    orch = FawlOrchestrator()
    receipts = [
        orch.run(inc, executor=lambda a, t: a.risk < _RISK_HIGH, verifier=lambda a: True)
        for inc in _scenarios()
    ]
    invariants: list[tuple[str, bool]] = []

    # Prohibited (level 4) action is never executed.
    prohibited = next(r for r in receipts if r.incident_id == "INC-D")
    invariants.append(("level-4 never executes", not prohibited.executed))

    # AI-originated level-2 without human approval is not auto-permitted.
    ai = next(r for r in receipts if r.incident_id == "INC-E")
    invariants.append(("AI level≥2 not self-authorized", ai.verdict is not Verdict.PERMIT))

    # Kill switch freezes mutating automation.
    frozen = next(r for r in receipts if r.incident_id == "INC-G")
    invariants.append(("kill switch halts automation", not frozen.executed))

    # Malicious telemetry is quarantined.
    mal = next(r for r in receipts if r.incident_id == "INC-F")
    invariants.append(("malicious signal quarantined", mal.final_state is _S.QUARANTINED))

    # Every incident's audit chain verifies.
    invariants.append(("audit chains intact", all(r.audit_verified for r in receipts)))

    return receipts, [(name, ok) for name, ok in invariants if not ok]


def main(argv: Optional[list[str]] = None) -> int:
    import json
    import sys

    argv = argv if argv is not None else sys.argv[1:]
    receipts, failures = run_self_check()

    if "--json" in argv:
        print(json.dumps({
            "platform": "ARTEMIS//FAWL",
            "receipts": [r.to_dict() for r in receipts],
            "invariant_failures": [name for name, _ in failures],
            "ok": not failures,
        }, indent=2))
    else:
        for r in receipts:
            v = r.verdict.value if r.verdict else "-"
            lvl = int(r.level) if r.level is not None else "-"
            print(f"[{r.incident_id}] {r.final_state.value:<26} verdict={v:<16} "
                  f"L{lvl} exec={r.executed} verified={r.verified}")
        print(f"\nself-check: {'PASS' if not failures else 'FAIL ' + ','.join(n for n, _ in failures)}")

    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
