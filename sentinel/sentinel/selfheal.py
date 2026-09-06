# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""PHOENIX — governed self-healing / autonomous recovery engine.

PHOENIX is the resilience persona in the PERCIVAL/SENTINEL family. It closes
the operational loop that the rest of the mesh leaves open:

    detect → classify → plan → GATE → contain → remediate → verify → learn

Doctrine (inherited from the family, non-negotiable):
  * **Fail-closed.** Any term that cannot be computed (missing confidence,
    unknown action, exhausted budget) routes to ESCALATION, never to a silent
    auto-execution.
  * **Safe-listed reversibility only.** Only reversible, low-risk actions on a
    safe-list may auto-execute. Everything irreversible or high-risk is
    PROPOSED and blocked until a human approval is supplied — exactly the
    "read-only → draft → human approval → execution" invariant the commerce OS
    enforces, applied to remediation.
  * **Containment before remediation.** When blast radius is spreading, PHOENIX
    contains (isolate / reroute / degrade) *before* attempting a fix.
  * **No repeated failure loops.** Incident memory records fix effectiveness;
    an action that has failed too many times for a signature is exhausted and
    forces escalation instead of thrashing.
  * **Everything is audited.** Every decision and step is written to the
    hash-chained, tamper-evident :class:`~sentinel.audit.AuditLog`.

The engine is pure orchestration and pure stdlib. All real side effects happen
inside injected ``executor`` / ``verifier`` callables (adapters), so the trust
loop is fully testable without touching production systems.
"""
from __future__ import annotations

import random
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Sequence

from .audit import AuditLog

# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


class IncidentClass(str, Enum):
    """How an incident should be recovered. Order = escalation ladder."""

    RETRYABLE = "RETRYABLE"      # transient; back off and retry
    FALLBACK = "FALLBACK"        # degrade gracefully / reroute to standby
    CONTAINMENT = "CONTAINMENT"  # isolate blast radius, then remediate
    ESCALATION = "ESCALATION"    # confidence/authority insufficient → human


class Disposition(str, Enum):
    """Policy verdict for a single proposed recovery action."""

    AUTO = "AUTO"          # safe-listed, reversible, confident → execute + log
    PROPOSE = "PROPOSE"    # needs human approval before execution
    ESCALATE = "ESCALATE"  # cannot be executed safely under any auto-path


class Outcome(str, Enum):
    RECOVERED = "RECOVERED"    # verified healthy again
    CONTAINED = "CONTAINED"    # blast radius stopped, not yet fully healed
    DEGRADED = "DEGRADED"      # running on a fallback path
    ESCALATED = "ESCALATED"    # handed to a human with a drafted plan
    FAILED = "FAILED"          # remediation attempted and did not verify


# Risk scoring mirrors the commerce governance band (0–100).
RISK_LOW = 30
RISK_HIGH = 70


# --------------------------------------------------------------------------- #
# Signals & detection
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Signal:
    """A single observation: a metric sample, a health probe, or an error."""

    name: str
    value: float
    source: str
    ts: float = field(default_factory=time.time)
    kind: str = "metric"  # metric | health | error


@dataclass(frozen=True)
class Anomaly:
    metric: str
    source: str
    value: float
    baseline: float
    score: float          # robust z-score (deviation in MADs); >=0
    confidence: float      # 0..1 — how trustworthy the detection is
    breached_budget: bool


class AnomalyDetector:
    """Rolling, robust anomaly detector with a per-metric error budget.

    Uses a median + MAD (median absolute deviation) baseline — resistant to the
    very spikes we are trying to catch, unlike a mean/stddev. Detection is
    fail-closed on *confidence*: with too few samples to form a baseline the
    reported confidence is low, which downstream gating treats as unverifiable.
    """

    def __init__(self, *, window: int = 50, mad_threshold: float = 3.5,
                 min_samples: int = 8, budget: int = 5) -> None:
        self.window = window
        self.mad_threshold = mad_threshold
        self.min_samples = min_samples
        self.budget = budget
        self._history: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=window))
        self._breaches: dict[str, int] = defaultdict(int)

    def observe(self, signal: Signal) -> Optional[Anomaly]:
        key = f"{signal.source}:{signal.name}"
        hist = self._history[key]
        samples = list(hist)
        hist.append(signal.value)

        if len(samples) < self.min_samples:
            return None  # not enough history to judge — stays silent (low confidence)

        median = _median(samples)
        mad = _median([abs(x - median) for x in samples]) or 1e-9
        # 0.6745 scales MAD to a standard-deviation-equivalent z-score.
        score = abs(signal.value - median) * 0.6745 / mad
        if score < self.mad_threshold:
            self._breaches[key] = 0
            return None

        self._breaches[key] += 1
        breached_budget = self._breaches[key] > self.budget
        # Confidence grows with history depth and deviation magnitude.
        depth = min(1.0, len(samples) / self.window)
        sharpness = min(1.0, score / (self.mad_threshold * 2))
        confidence = round(0.5 * depth + 0.5 * sharpness, 3)
        return Anomaly(
            metric=signal.name,
            source=signal.source,
            value=signal.value,
            baseline=round(median, 4),
            score=round(score, 3),
            confidence=confidence,
            breached_budget=breached_budget,
        )


def _median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


# --------------------------------------------------------------------------- #
# Incidents
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Incident:
    incident_id: str
    title: str
    severity: Severity
    anomalies: tuple[Anomaly, ...]
    error_kind: str = ""           # e.g. "timeout", "5xx", "dependency_down", "security"
    dependency_down: bool = False
    fallback_available: bool = False
    spreading: bool = False        # blast radius growing across services
    data_integrity_risk: bool = False
    affected_services: tuple[str, ...] = ()

    def signature(self) -> str:
        """Stable fingerprint for memory/loop-prevention (not time-varying)."""
        metrics = ",".join(sorted({a.metric for a in self.anomalies}))
        svc = ",".join(sorted(self.affected_services))
        return f"{self.error_kind}|{metrics}|{svc}"

    @property
    def confidence(self) -> Optional[float]:
        if not self.anomalies:
            return None
        return round(sum(a.confidence for a in self.anomalies) / len(self.anomalies), 3)


def classify(incident: Incident) -> IncidentClass:
    """Route an incident onto the recovery ladder — fail-closed to ESCALATION.

    The order of checks *is* the safety policy: unknown / security / integrity
    and spreading blast radius are pulled toward containment/escalation before
    the cheaper retry & fallback paths are considered.
    """
    # Unverifiable detection → escalate. Never auto-act on a guess.
    if incident.confidence is None:
        return IncidentClass.ESCALATION
    if incident.error_kind == "security" or incident.data_integrity_risk:
        return IncidentClass.ESCALATION if incident.data_integrity_risk else IncidentClass.CONTAINMENT
    if incident.spreading or len(incident.affected_services) >= 3:
        return IncidentClass.CONTAINMENT
    if incident.dependency_down:
        return IncidentClass.FALLBACK if incident.fallback_available else IncidentClass.ESCALATION
    if incident.error_kind in {"timeout", "5xx", "connection_reset", "throttled", ""}:
        return IncidentClass.RETRYABLE
    return IncidentClass.ESCALATION


# --------------------------------------------------------------------------- #
# Recovery actions & playbooks
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RecoveryAction:
    key: str
    description: str
    risk: int                 # 0..100 (commerce governance band)
    reversible: bool
    kind: str                 # retry | fallback | contain | remediate | rollback
    base_effectiveness: float = 0.6  # prior success rate before memory adjusts it


# Safe-listed, reversible, low-risk actions may auto-execute. Anything not on
# this list — or above RISK_HIGH, or irreversible — is proposed for approval.
PLAYBOOKS: dict[IncidentClass, tuple[RecoveryAction, ...]] = {
    IncidentClass.RETRYABLE: (
        RecoveryAction("retry_backoff", "Retry with exponential backoff + jitter",
                       risk=10, reversible=True, kind="retry", base_effectiveness=0.7),
        RecoveryAction("restart_worker", "Restart the affected stateless worker",
                       risk=25, reversible=True, kind="remediate", base_effectiveness=0.65),
        RecoveryAction("clear_cache", "Flush a poisoned local cache",
                       risk=20, reversible=True, kind="remediate", base_effectiveness=0.5),
    ),
    IncidentClass.FALLBACK: (
        RecoveryAction("reroute_standby", "Drain and reroute traffic to a healthy standby",
                       risk=30, reversible=True, kind="fallback", base_effectiveness=0.75),
        RecoveryAction("degrade_feature", "Disable a non-critical feature flag (graceful degrade)",
                       risk=20, reversible=True, kind="fallback", base_effectiveness=0.7),
        RecoveryAction("serve_cached", "Serve last-known-good cached responses",
                       risk=15, reversible=True, kind="fallback", base_effectiveness=0.6),
    ),
    IncidentClass.CONTAINMENT: (
        RecoveryAction("isolate_node", "Cordon/quarantine the unhealthy node",
                       risk=35, reversible=True, kind="contain", base_effectiveness=0.7),
        RecoveryAction("open_circuit", "Open the circuit breaker to the failing dependency",
                       risk=25, reversible=True, kind="contain", base_effectiveness=0.75),
        RecoveryAction("rate_limit_shed", "Shed load via aggressive rate limiting",
                       risk=30, reversible=True, kind="contain", base_effectiveness=0.6),
        # High-risk / irreversible remediations are PROPOSE-only by construction.
        RecoveryAction("rollback_release", "Roll back the most recent release",
                       risk=75, reversible=False, kind="rollback", base_effectiveness=0.8),
        RecoveryAction("failover_primary", "Fail over the primary datastore",
                       risk=90, reversible=False, kind="remediate", base_effectiveness=0.85),
    ),
    IncidentClass.ESCALATION: (),  # nothing auto-executable; humans own it
}


# --------------------------------------------------------------------------- #
# Retry / circuit-breaker / budget primitives
# --------------------------------------------------------------------------- #


def backoff_delays(attempts: int, *, base: float = 0.2, cap: float = 30.0,
                   jitter: float = 0.5, rng: Optional[random.Random] = None) -> list[float]:
    """Exponential backoff with decorrelated jitter. Deterministic under an
    injected ``rng`` so recovery timing is testable."""
    rng = rng or random.Random()
    delays: list[float] = []
    for i in range(max(0, attempts)):
        raw = min(cap, base * (2 ** i))
        delays.append(round(raw * (1 - jitter + jitter * rng.random()), 4))
    return delays


class CircuitBreaker:
    """Standard three-state breaker guarding a repair budget.

    CLOSED → (failures ≥ threshold) → OPEN → (cool-down) → HALF_OPEN →
    success → CLOSED, or failure → OPEN. Prevents PHOENIX from hammering a
    dependency that is already down.
    """

    CLOSED, OPEN, HALF_OPEN = "CLOSED", "OPEN", "HALF_OPEN"

    def __init__(self, *, threshold: int = 3, cool_down: float = 30.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.threshold = threshold
        self.cool_down = cool_down
        self._clock = clock
        self._failures = 0
        self._opened_at = 0.0
        self.state = self.CLOSED

    def allows(self) -> bool:
        if self.state == self.OPEN:
            if self._clock() - self._opened_at >= self.cool_down:
                self.state = self.HALF_OPEN
                return True
            return False
        return True

    def record(self, ok: bool) -> None:
        if ok:
            self._failures = 0
            self.state = self.CLOSED
            return
        self._failures += 1
        if self.state == self.HALF_OPEN or self._failures >= self.threshold:
            self.state = self.OPEN
            self._opened_at = self._clock()


# --------------------------------------------------------------------------- #
# Incident memory — root-cause recall, effectiveness learning, loop prevention
# --------------------------------------------------------------------------- #


@dataclass
class _Stat:
    attempts: int = 0
    successes: int = 0

    @property
    def rate(self) -> float:
        return self.successes / self.attempts if self.attempts else 0.0


class IncidentMemory:
    """Durable-in-spirit memory of what worked. Two jobs:

    1. **Learn** — blend a prior with observed success rate per
       (signature, action) so ranking improves after every incident.
    2. **Prevent loops** — an action that has failed ``max_failures`` times in a
       row for a signature is *exhausted* and excluded, forcing the ladder to
       climb toward escalation rather than repeating a known-bad fix.
    """

    def __init__(self, *, max_failures: int = 3) -> None:
        self.max_failures = max_failures
        self._stats: dict[tuple[str, str], _Stat] = defaultdict(_Stat)
        self._consecutive_fail: dict[tuple[str, str], int] = defaultdict(int)

    def effectiveness(self, signature: str, action: RecoveryAction) -> float:
        st = self._stats[(signature, action.key)]
        if st.attempts == 0:
            return action.base_effectiveness
        # Bayesian-ish blend: prior counts as 2 pseudo-observations.
        prior_w = 2.0
        return round(
            (action.base_effectiveness * prior_w + st.successes) / (prior_w + st.attempts), 3
        )

    def exhausted(self, signature: str, action: RecoveryAction) -> bool:
        return self._consecutive_fail[(signature, action.key)] >= self.max_failures

    def record(self, signature: str, action: RecoveryAction, ok: bool) -> None:
        st = self._stats[(signature, action.key)]
        st.attempts += 1
        if ok:
            st.successes += 1
            self._consecutive_fail[(signature, action.key)] = 0
        else:
            self._consecutive_fail[(signature, action.key)] += 1

    def snapshot(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for (sig, key), st in self._stats.items():
            out.setdefault(sig, {})[key] = st.rate
        return out

    # -- persistence: learning survives restarts (stdlib-only, atomic write) --

    def to_state(self) -> dict:
        """Serialize the *full* learning state (attempts/successes + fail
        streaks). ``snapshot`` is lossy (rates only); this preserves everything
        needed to resume ranking and loop-prevention exactly after a restart, so
        the engine keeps learning across process boundaries instead of forgetting
        every incident on redeploy."""
        keys = set(self._stats) | set(self._consecutive_fail)
        records = [
            {
                "signature": sig,
                "action": key,
                "attempts": self._stats.get((sig, key), _Stat()).attempts,
                "successes": self._stats.get((sig, key), _Stat()).successes,
                "consecutive_fail": self._consecutive_fail.get((sig, key), 0),
            }
            for sig, key in sorted(keys)
        ]
        return {"version": 1, "max_failures": self.max_failures, "records": records}

    def load_state(self, state: dict) -> "IncidentMemory":
        """Merge a serialized state into this memory in place. Returns self."""
        for rec in state.get("records", []):
            k = (str(rec["signature"]), str(rec["action"]))
            st = self._stats[k]
            st.attempts = int(rec.get("attempts", 0))
            st.successes = int(rec.get("successes", 0))
            self._consecutive_fail[k] = int(rec.get("consecutive_fail", 0))
        return self

    @classmethod
    def from_state(cls, state: dict, *, max_failures: Optional[int] = None) -> "IncidentMemory":
        mem = cls(max_failures=int(state.get("max_failures", 3)) if max_failures is None else max_failures)
        return mem.load_state(state)

    def save(self, path: str) -> None:
        """Atomically persist learning state to ``path`` as JSON (write-temp +
        rename, so a crash mid-write never leaves a half-written memory file)."""
        import json
        import os
        import tempfile

        data = json.dumps(self.to_state(), indent=2, sort_keys=True)
        directory = os.path.dirname(os.path.abspath(path)) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(data)
            os.replace(tmp, path)  # atomic on POSIX
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                # Best-effort temp cleanup; ignore its failure so the original
                # write error below is re-raised unmasked.
                pass
            raise

    @classmethod
    def load(cls, path: str, *, max_failures: Optional[int] = None) -> "IncidentMemory":
        """Load memory from ``path``. A missing file yields fresh memory — this
        fail-open is on *learning quality only* (an empty prior), never on a
        safety decision; gating still fails closed regardless of memory state."""
        import json
        import os

        if not os.path.exists(path):
            return cls(max_failures=max_failures if max_failures is not None else 3)
        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)
        return cls.from_state(state, max_failures=max_failures)


# --------------------------------------------------------------------------- #
# Policy gate — the safety heart
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Verdict:
    disposition: Disposition
    action: RecoveryAction
    confidence: float
    rank_score: float
    reasons: tuple[str, ...]


def gate(action: RecoveryAction, incident: Incident, memory: IncidentMemory,
         *, tau: float = 0.6) -> Verdict:
    """Decide how a single action may run. Fail-closed at every branch.

    AUTO requires *all* of: safe-listed reversibility, risk < RISK_HIGH,
    detection confidence ≥ tau, not exhausted. Otherwise PROPOSE (if it could
    run under human approval) or ESCALATE (if it never can).
    """
    conf = incident.confidence
    eff = memory.effectiveness(incident.signature(), action)
    # Rank = expected value per unit risk. Higher is better.
    rank = round(eff * (conf or 0.0) / max(1, action.risk), 5)

    reasons: list[str] = []
    if conf is None:
        return Verdict(Disposition.ESCALATE, action, 0.0, rank,
                       ("detection confidence unverifiable (fail-closed)",))
    if memory.exhausted(incident.signature(), action):
        return Verdict(Disposition.ESCALATE, action, conf, rank,
                       (f"'{action.key}' exhausted for this signature (loop prevention)",))
    if not action.reversible:
        reasons.append("irreversible action requires approval")
    if action.risk >= RISK_HIGH:
        reasons.append(f"risk {action.risk} ≥ {RISK_HIGH} (high) requires approval")
    if conf < tau:
        reasons.append(f"confidence {conf:.2f} < tau {tau:.2f} requires approval")

    if not reasons:
        return Verdict(Disposition.AUTO, action, conf, rank,
                       ("safe-listed, reversible, confident → auto-execute + log",))
    # Could still run with a human in the loop.
    return Verdict(Disposition.PROPOSE, action, conf, rank, tuple(reasons))


# --------------------------------------------------------------------------- #
# The engine
# --------------------------------------------------------------------------- #


@dataclass
class Step:
    action_key: str
    disposition: Disposition
    executed: bool
    verified: Optional[bool]
    reasons: tuple[str, ...]


@dataclass
class IncidentReport:
    incident_id: str
    incident_class: IncidentClass
    outcome: Outcome
    steps: list[Step] = field(default_factory=list)
    approvals_required: list[str] = field(default_factory=list)
    mttr_seconds: float = 0.0
    audit_verified: bool = True

    def to_dict(self) -> dict:
        return {
            "incident_id": self.incident_id,
            "class": self.incident_class.value,
            "outcome": self.outcome.value,
            "mttr_seconds": round(self.mttr_seconds, 4),
            "audit_verified": self.audit_verified,
            "approvals_required": list(self.approvals_required),
            "steps": [
                {
                    "action": s.action_key,
                    "disposition": s.disposition.value,
                    "executed": s.executed,
                    "verified": s.verified,
                    "reasons": list(s.reasons),
                }
                for s in self.steps
            ],
        }


# An executor performs one action and returns success. A verifier confirms the
# incident is actually resolved. Both are injected so the engine never performs
# real side effects itself.
Executor = Callable[[RecoveryAction, Incident], bool]
Verifier = Callable[[Incident], bool]


class SelfHealEngine:
    """Orchestrates the governed recovery loop for a single incident.

    ``approvals`` is the set of action keys a human has pre-approved; a proposed
    high-risk action executes only if its key is present. Without it the action
    is recorded as an outstanding approval and the incident escalates.
    """

    def __init__(self, *, memory: Optional[IncidentMemory] = None,
                 audit: Optional[AuditLog] = None, tau: float = 0.6,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.memory = memory or IncidentMemory()
        self.audit = audit or AuditLog()
        self.tau = tau
        self._clock = clock

    def _log(self, incident: Incident, action: str, detail: dict) -> None:
        self.audit.record(actor=f"PHOENIX:{incident.incident_id}", action=action, detail=detail)

    def handle(self, incident: Incident, *, executor: Executor, verifier: Verifier,
               approvals: Optional[set[str]] = None) -> IncidentReport:
        approvals = approvals or set()
        start = self._clock()
        klass = classify(incident)
        report = IncidentReport(incident.incident_id, klass, Outcome.FAILED)
        self._log(incident, "detect", {
            "class": klass.value, "confidence": incident.confidence,
            "signature": incident.signature(), "severity": incident.severity.value,
        })

        if klass is IncidentClass.ESCALATION:
            report.outcome = Outcome.ESCALATED
            self._log(incident, "escalate", {"reason": "classified non-autonomous"})
            report.mttr_seconds = self._clock() - start
            report.audit_verified = self.audit.verify()
            return report

        # Rank candidate actions by expected value, dropping exhausted ones.
        candidates = [
            a for a in PLAYBOOKS.get(klass, ())
            if not self.memory.exhausted(incident.signature(), a)
        ]
        candidates.sort(
            key=lambda a: self.memory.effectiveness(incident.signature(), a)
            * (incident.confidence or 0.0) / max(1, a.risk),
            reverse=True,
        )

        contained = False
        for action in candidates:
            verdict = gate(action, incident, self.memory, tau=self.tau)

            if verdict.disposition is Disposition.AUTO:
                ok = bool(executor(action, incident))
                self.memory.record(incident.signature(), action, ok)
                verified = bool(verifier(incident)) if ok else False
                report.steps.append(Step(action.key, verdict.disposition, True, verified, verdict.reasons))
                self._log(incident, "remediate", {
                    "action": action.key, "risk": action.risk, "executed": True,
                    "verified": verified, "rank": verdict.rank_score,
                })
                if action.kind == "contain" and ok:
                    contained = True
                if verified:
                    report.outcome = Outcome.RECOVERED
                    self._log(incident, "verify", {"action": action.key, "healthy": True})
                    break
                # not verified → keep climbing the ladder
                continue

            # PROPOSE: execute only under an explicit approval, else record + skip.
            if verdict.disposition is Disposition.PROPOSE:
                if action.key in approvals:
                    ok = bool(executor(action, incident))
                    self.memory.record(incident.signature(), action, ok)
                    verified = bool(verifier(incident)) if ok else False
                    report.steps.append(Step(action.key, verdict.disposition, True, verified, verdict.reasons))
                    self._log(incident, "remediate_approved", {
                        "action": action.key, "risk": action.risk, "verified": verified,
                    })
                    if verified:
                        report.outcome = Outcome.RECOVERED
                        break
                    continue
                report.approvals_required.append(action.key)
                report.steps.append(Step(action.key, verdict.disposition, False, None, verdict.reasons))
                self._log(incident, "propose", {"action": action.key, "reasons": list(verdict.reasons)})
                continue

            # ESCALATE
            report.steps.append(Step(action.key, verdict.disposition, False, None, verdict.reasons))
            self._log(incident, "escalate_action", {"action": action.key, "reasons": list(verdict.reasons)})

        # Post-loop disposition.
        if report.outcome is not Outcome.RECOVERED:
            if klass is IncidentClass.FALLBACK and any(s.executed for s in report.steps):
                report.outcome = Outcome.DEGRADED
            elif contained:
                report.outcome = Outcome.CONTAINED
            elif report.approvals_required:
                report.outcome = Outcome.ESCALATED
            else:
                report.outcome = Outcome.ESCALATED
                self._log(incident, "escalate", {"reason": "no autonomous fix verified"})

        report.mttr_seconds = self._clock() - start
        report.audit_verified = self.audit.verify()
        return report


# --------------------------------------------------------------------------- #
# Demo / self-check CLI  —  python -m sentinel.selfheal [--json] [--check]
# --------------------------------------------------------------------------- #


def _scenarios() -> list[Incident]:
    det = AnomalyDetector(min_samples=4, window=20)
    # feed a stable baseline then a spike so the anomaly is real & confident
    for _ in range(10):
        det.observe(Signal("p99_latency_ms", 120.0, "checkout-api"))
    spike = det.observe(Signal("p99_latency_ms", 900.0, "checkout-api"))
    anomalies = (spike,) if spike else ()
    return [
        Incident("INC-1001", "checkout p99 latency spike", Severity.WARN, anomalies,
                 error_kind="timeout", affected_services=("checkout-api",)),
        Incident("INC-1002", "payments dependency down", Severity.CRITICAL, anomalies,
                 error_kind="dependency_down", dependency_down=True,
                 fallback_available=True, affected_services=("payments",)),
        Incident("INC-1003", "cascading 5xx across mesh", Severity.CRITICAL, anomalies,
                 error_kind="5xx", spreading=True,
                 affected_services=("checkout-api", "catalog", "search", "payments")),
        Incident("INC-1004", "suspected data-integrity anomaly", Severity.CRITICAL, anomalies,
                 error_kind="unknown", data_integrity_risk=True,
                 affected_services=("ledger",)),
    ]


def run_self_check(memory: Optional[IncidentMemory] = None) -> tuple[list[IncidentReport], list[str]]:
    """Run the reference scenarios and assert PHOENIX's safety invariants.

    An optional ``memory`` lets the caller carry learned effectiveness across
    runs (see the ``--memory`` CLI flag)."""
    engine = SelfHealEngine(memory=memory)
    reports = [
        engine.handle(inc, executor=lambda a, i: a.risk < RISK_HIGH, verifier=lambda i: True)
        for inc in _scenarios()
    ]
    invariants: list[str] = []

    # 1. No irreversible/high-risk action ever auto-executed without approval.
    high_risk_auto = [
        s.action_key for r in reports for s in r.steps
        if s.executed and s.disposition is Disposition.AUTO
        and _risk_of(s.action_key) >= RISK_HIGH
    ]
    invariants.append(("no high-risk auto-exec", not high_risk_auto))

    # 2. The audit chain is intact and tamper-evident across all incidents.
    invariants.append(("audit chain intact", engine.audit.verify()))

    # 3. Data-integrity / security incidents escalate (never silently fixed).
    integrity = reports[3]
    invariants.append(("integrity risk escalated", integrity.outcome is Outcome.ESCALATED))

    failures = [name for name, ok in invariants if not ok]
    return reports, failures


def _risk_of(action_key: str) -> int:
    for actions in PLAYBOOKS.values():
        for a in actions:
            if a.key == action_key:
                return a.risk
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    import json
    import sys

    argv = argv if argv is not None else sys.argv[1:]

    # Optional persistent learning: `--memory PATH` loads prior effectiveness,
    # runs, then durably saves it back so learning survives restarts.
    mem_path: Optional[str] = None
    if "--memory" in argv:
        i = argv.index("--memory")
        if i + 1 < len(argv):
            mem_path = argv[i + 1]
    memory = IncidentMemory.load(mem_path) if mem_path else None

    reports, failures = run_self_check(memory)

    if mem_path and memory is not None:
        memory.save(mem_path)

    if "--json" in argv:
        print(json.dumps({
            "agent": "PHOENIX",
            "reports": [r.to_dict() for r in reports],
            "invariant_failures": failures,
            "ok": not failures,
            "memory": mem_path or None,
        }, indent=2))
    else:
        for r in reports:
            print(f"[{r.incident_id}] {r.incident_class.value:<12} → {r.outcome.value:<10} "
                  f"MTTR={r.mttr_seconds*1000:.2f}ms  approvals={r.approvals_required or '-'}")
        print(f"\nself-check: {'PASS' if not failures else 'FAIL ' + ','.join(failures)}")

    # --check makes it a gate: non-zero exit if any invariant is violated.
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
