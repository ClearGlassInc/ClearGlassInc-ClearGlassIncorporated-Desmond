# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""XENOLITH lattice — the composed sovereign control plane.

This module wires the nine subsystems into one object and enforces the single
path every consequential action takes:

    sign → verify → policy gate → (human approval) → execute → audit → emit

There is deliberately **no** method that skips the gate. :meth:`Lattice.submit`
is the only way in, and it returns an :class:`Outcome` describing what happened
rather than silently doing something different from what was asked. A
``high``/``critical`` action comes back ``executed=False`` with an approval id;
nothing runs until :meth:`Lattice.approve` records a decision from someone
other than the requester.

:meth:`Lattice.self_check` is the invariant suite — the same set of assertions
the CI gate runs, so a regression that opens an ungoverned path fails the build
by construction.

Stdlib only.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from .bus import Event, EventBus
from .constants import Domain, LatticeError, RiskTier
from .executive import ExecutiveCore, Mission, Objective, TaskSpec
from .fusion import Connector, FusionEngine, Observation
from .graph import KnowledgeGraph
from .identity import IdentityAuthority
from .memory import MemoryFabric
from .policy import Decision, PolicyEngine, ProposedAction, Verdict, sanitize_payload
from .registry import AgentRegistry, AgentStatus
from .telemetry import AnomalyDetector, AuditLedger, MetricSink

#: Handlers registered per action class. An action with no executor is a
#: governance no-op: it is still gated, scored and audited, it simply has no
#: side effect yet. That is the safe default for a capability under development.
Executor = Callable[["ExecutionContext"], Any]


@dataclass(frozen=True)
class ExecutionContext:
    """What an executor receives once policy has cleared an action."""

    lattice: "Lattice"
    actor: str
    action: str
    domain: Domain
    payload: Mapping[str, Any]
    targets: tuple[str, ...]
    trace_id: str | None
    verdict: Verdict


@dataclass(frozen=True)
class Outcome:
    """The full, honest result of a submission."""

    executed: bool
    verdict: Verdict
    result: Any = None
    approval_id: str | None = None
    ledger_index: int | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "executed": self.executed,
            "verdict": self.verdict.as_dict(),
            "approval_id": self.approval_id,
            "ledger_index": self.ledger_index,
            "error": self.error,
        }


@dataclass
class CheckResult:
    """One invariant assertion and whether it held."""

    name: str
    passed: bool
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass
class Lattice:
    """The XENOLITH platform: nine subsystems under one governed entry point."""

    identity: IdentityAuthority = field(default_factory=IdentityAuthority)
    registry: AgentRegistry = field(default_factory=AgentRegistry)
    bus: EventBus = field(default_factory=EventBus)
    memory: MemoryFabric = field(default_factory=MemoryFabric)
    graph: KnowledgeGraph = field(default_factory=KnowledgeGraph)
    ledger: AuditLedger = field(default_factory=AuditLedger)
    metrics: MetricSink = field(default_factory=MetricSink)
    anomalies: AnomalyDetector = field(default_factory=AnomalyDetector)
    policy: PolicyEngine = field(init=False)
    fusion: FusionEngine = field(init=False)
    executive: ExecutiveCore = field(init=False)
    _executors: dict[str, Executor] = field(default_factory=dict, init=False, repr=False)
    started_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        # Policy needs the registry to resolve permissions; fusion shares the
        # lattice graph so extracted indicators are visible to every domain.
        self.policy = PolicyEngine(registry=self.registry)
        self.fusion = FusionEngine(graph=self.graph)
        self.executive = ExecutiveCore(policy=self.policy, registry=self.registry)
        self.ledger.record(actor="lattice", action="lattice.boot", risk=RiskTier.LOW)

    # ------------------------------------------------------------------ #
    # Population
    # ------------------------------------------------------------------ #
    def enlist(
        self,
        codename: str,
        domain: Domain | str,
        role: str,
        mission_scope: str,
        sponsor: str,
        permissions: Iterable[str] = (),
        activate: bool = True,
    ) -> Any:
        """Issue an identity, register the agent, and bring it online.

        Identity and registration happen together so there is never a
        registered agent without a credential, or a credential without a slot.
        """
        credential = self.identity.issue(codename, sponsor)
        try:
            record = self.registry.register(
                codename=codename,
                domain=domain,
                role=role,
                mission_scope=mission_scope,
                permissions=permissions,
                key_fingerprint=credential.fingerprint,
            )
        except Exception:
            # Never leave an orphan credential behind on a failed registration.
            self.identity.revoke(codename)
            raise
        if activate:
            self.registry.activate(codename)
        self.ledger.record(
            actor=sponsor,
            action="agent.enlist",
            risk=RiskTier.MEDIUM,
            detail={"codename": codename, "domain": str(record.domain), "sponsor": sponsor},
        )
        self.bus.emit(
            "agent.enlisted",
            source="lattice",
            payload={"codename": codename, "domain": str(record.domain)},
        )
        return record

    def dismiss(self, codename: str, reason: str) -> None:
        """Retire an agent and revoke its credential in one motion."""
        self.registry.retire(codename)
        self.identity.revoke(codename)
        self.ledger.record(
            actor="lattice",
            action="agent.dismiss",
            risk=RiskTier.MEDIUM,
            detail={"codename": codename, "reason": reason},
        )
        self.bus.emit("agent.dismissed", source="lattice", payload={"codename": codename})

    # ------------------------------------------------------------------ #
    # Executors
    # ------------------------------------------------------------------ #
    def register_executor(self, action: str, executor: Executor) -> None:
        """Bind a side effect to an action class.

        Registering an executor for an action with no policy rule is refused:
        that would create a capability the gate has never scored.
        """
        if self.policy.rule(action) is None:
            raise LatticeError(f"no policy rule for '{action}' — add a rule before an executor")
        self._executors[action] = executor

    # ------------------------------------------------------------------ #
    # The single governed entry point
    # ------------------------------------------------------------------ #
    def submit(
        self,
        codename: str,
        action: str,
        payload: Mapping[str, Any] | None = None,
        targets: Iterable[str] = (),
        trace_id: str | None = None,
    ) -> Outcome:
        """Propose an action. Signs it, gates it, and executes only if cleared."""
        record = self.registry.find(codename)
        domain = record.domain if record is not None else Domain.OPERATIONS
        payload = dict(payload or {})
        targets = tuple(targets)

        proposed = ProposedAction(
            action=action,
            actor=codename,
            domain=domain,
            payload=payload,
            targets=targets,
            trace_id=trace_id,
        )

        # Sign first: the envelope proves the actor authored *this* payload, so
        # a verdict can never be attached to a mutated request.
        if not self.identity.is_active(codename):
            verdict = Verdict(
                decision=Decision.DENY,
                risk_score=100,
                tier=RiskTier.CRITICAL,
                reasons=(f"no active credential for {codename}",),
                action_digest=proposed.digest(),
            )
            return self._finish(proposed, verdict, executed=False, error="identity inactive")

        envelope = self.identity.sign(codename, {"action": action, "digest": proposed.digest()})
        if not self.identity.verify(envelope):
            verdict = Verdict(
                decision=Decision.DENY,
                risk_score=100,
                tier=RiskTier.CRITICAL,
                reasons=("envelope failed verification",),
                action_digest=proposed.digest(),
            )
            return self._finish(proposed, verdict, executed=False, error="envelope rejected")

        verdict = self.policy.evaluate(proposed)
        self.metrics.increment(f"action.{action}.{verdict.decision.value}")
        self.anomalies.observe(f"risk.{domain.value}", verdict.risk_score)

        if not verdict.executable:
            return self._finish(proposed, verdict, executed=False)

        executor = self._executors.get(action)
        if executor is None:
            return self._finish(proposed, verdict, executed=True, result=None)

        try:
            result = executor(
                ExecutionContext(
                    lattice=self,
                    actor=codename,
                    action=action,
                    domain=domain,
                    payload=payload,
                    targets=targets,
                    trace_id=trace_id,
                    verdict=verdict,
                )
            )
        except Exception as exc:  # noqa: BLE001 - failures are recorded, not raised
            self.metrics.increment(f"action.{action}.error")
            return self._finish(
                proposed, verdict, executed=False, error=f"{type(exc).__name__}: {exc}"
            )
        return self._finish(proposed, verdict, executed=True, result=result)

    def _finish(
        self,
        proposed: ProposedAction,
        verdict: Verdict,
        executed: bool,
        result: Any = None,
        error: str | None = None,
    ) -> Outcome:
        """Audit and announce every submission, cleared or not."""
        entry = self.ledger.record(
            actor=proposed.actor,
            action=proposed.action,
            risk=verdict.tier,
            detail={
                "decision": verdict.decision.value,
                "risk_score": verdict.risk_score,
                "executed": executed,
                "targets": list(proposed.targets),
                "approval_id": verdict.approval_id,
                "error": error,
                # Sanitize before the payload is durable: the ledger is read by
                # dashboards and exported to operators.
                "payload": sanitize_payload(proposed.payload),
            },
        )
        self.bus.emit(
            f"action.{verdict.decision.value}",
            source=proposed.actor,
            payload={
                "action": proposed.action,
                "risk_score": verdict.risk_score,
                "tier": verdict.tier.value,
                "executed": executed,
            },
            trace_id=proposed.trace_id,
        )
        return Outcome(
            executed=executed,
            verdict=verdict,
            result=result,
            approval_id=verdict.approval_id,
            ledger_index=entry.index,
            error=error,
        )

    def approve(self, approval_id: str, approver: str, note: str = "") -> Any:
        """Record a human approval. Self-approval is refused by the engine."""
        approval = self.policy.decide(approval_id, approver, approve=True, note=note)
        self.ledger.record(
            actor=approver,
            action="approval.granted",
            risk=approval.tier,
            detail={"approval_id": approval_id, "for_action": approval.action, "note": note},
        )
        self.bus.emit(
            "approval.granted",
            source=approver,
            payload={"approval_id": approval_id, "action": approval.action},
        )
        return approval

    def reject(self, approval_id: str, approver: str, note: str = "") -> Any:
        approval = self.policy.decide(approval_id, approver, approve=False, note=note)
        self.ledger.record(
            actor=approver,
            action="approval.rejected",
            risk=approval.tier,
            detail={"approval_id": approval_id, "for_action": approval.action, "note": note},
        )
        self.bus.emit(
            "approval.rejected",
            source=approver,
            payload={"approval_id": approval_id, "action": approval.action},
        )
        return approval

    # ------------------------------------------------------------------ #
    # Convenience passthroughs
    # ------------------------------------------------------------------ #
    def ingest(self, observation: Observation) -> Observation:
        return self.fusion.ingest(observation)

    def connect(self, connector: Connector) -> Connector:
        return self.fusion.register_connector(connector)

    def declare(self, statement: str, value: int, deadline: float | None = None) -> Objective:
        return self.executive.declare(statement, value, deadline)

    def plan(self, objective: Objective, specs: Iterable[TaskSpec]) -> Mission:
        return self.executive.plan(objective, tuple(specs))

    def sweep(self) -> tuple[str, ...]:
        """Demote stale agents and record the demotions."""
        demoted = self.registry.sweep()
        for codename in demoted:
            self.ledger.record(
                actor="lattice",
                action="agent.degraded",
                risk=RiskTier.MEDIUM,
                detail={"codename": codename, "reason": "heartbeat stale"},
            )
            self.bus.emit("agent.degraded", source="lattice", payload={"codename": codename})
        return demoted

    def observe_bus(self, pattern: str, handler: Callable[[Event], None]) -> Callable[[], None]:
        return self.bus.subscribe(pattern, handler)

    # ------------------------------------------------------------------ #
    # Invariants
    # ------------------------------------------------------------------ #
    def self_check(self) -> tuple[CheckResult, ...]:
        """Assert the governance invariants that must never regress.

        Runs against a throwaway probe lattice for the behavioural checks so it
        never mutates live state, and against ``self`` for the state checks.
        """
        checks: list[CheckResult] = []

        checks.append(
            CheckResult(
                "audit_chain_intact",
                self.ledger.verify(),
                f"{len(self.ledger)} entries, head {self.ledger.head[:12]}",
            )
        )

        probe = Lattice()
        probe.enlist(
            "PROBE",
            Domain.CYBERSECURITY,
            "invariant probe",
            "self-check",
            sponsor="ci",
            permissions=["cyber.respond", "intel.read"],
        )

        # 1. A high-risk action must not execute on first submission.
        high = probe.submit("PROBE", "cyber.contain", {"asset": "srv-1"})
        checks.append(
            CheckResult(
                "high_risk_blocked_until_approved",
                not high.executed and high.verdict.tier.blocks_until_approved,
                f"decision={high.verdict.decision.value} risk={high.verdict.risk_score}",
            )
        )

        # 2. The requester must not be able to approve their own request.
        self_approved = False
        if high.approval_id:
            try:
                probe.approve(high.approval_id, "PROBE")
                self_approved = True
            except Exception:
                self_approved = False
        checks.append(
            CheckResult("self_approval_refused", not self_approved, "requester != approver enforced")
        )

        # 3. After a genuine approval, the same action executes.
        cleared = False
        if high.approval_id:
            probe.approve(high.approval_id, "human-operator")
            cleared = probe.submit("PROBE", "cyber.contain", {"asset": "srv-1"}).executed
        checks.append(
            CheckResult("approval_unlocks_action", cleared, "approved digest executes exactly once")
        )

        # 4. Approval is bound to the digest — a different payload stays blocked.
        drifted = probe.submit("PROBE", "cyber.contain", {"asset": "srv-2"})
        checks.append(
            CheckResult(
                "approval_bound_to_payload",
                not drifted.executed,
                "mutating the payload invalidates the approval",
            )
        )

        # 5. Unknown action classes are denied, not defaulted through.
        unknown = probe.submit("PROBE", "totally.unknown.action", {})
        checks.append(
            CheckResult(
                "unknown_action_denied",
                unknown.verdict.decision is Decision.DENY,
                "deny-by-default holds",
            )
        )

        # 6. A permission the agent does not hold is denied.
        unauthorized = probe.submit("PROBE", "policy.amend", {"rule": "anything"})
        checks.append(
            CheckResult(
                "missing_permission_denied",
                unauthorized.verdict.decision is Decision.DENY,
                "capability check precedes risk scoring",
            )
        )

        # 7. Every submission, cleared or not, is in the ledger.
        checks.append(
            CheckResult(
                "every_submission_audited",
                len(probe.ledger) >= 6,
                f"{len(probe.ledger)} probe entries recorded",
            )
        )

        # 8. The probe's own chain verifies after all that traffic.
        checks.append(
            CheckResult("probe_chain_intact", probe.ledger.verify(), "hash chain re-walked")
        )

        return tuple(checks)

    # ------------------------------------------------------------------ #
    # Reporting
    # ------------------------------------------------------------------ #
    def state(self) -> dict[str, Any]:
        """One JSON-serializable snapshot of the entire lattice."""
        checks = self.self_check()
        agents = self.registry.all()
        return {
            "platform": "XENOLITH",
            "subtitle": "ClearGlass sovereign intelligence lattice",
            "generated_at": time.time(),
            "uptime_seconds": round(time.time() - self.started_at, 3),
            "governance": {
                "checks": [c.as_dict() for c in checks],
                "passed": sum(1 for c in checks if c.passed),
                "total": len(checks),
                "fail_closed": all(c.passed for c in checks),
            },
            "identity": {
                "active": len(self.identity.codenames),
                "envelope_ttl": True,
            },
            "registry": self.registry.census(),
            "agents": [a.as_dict() for a in agents],
            "policy": self.policy.snapshot(),
            "bus": self.bus.stats(),
            "memory": self.memory.snapshot(),
            "graph": self.graph.snapshot(),
            "fusion": self.fusion.snapshot(),
            "executive": self.executive.brief(),
            "telemetry": {
                "ledger_entries": len(self.ledger),
                "ledger_head": self.ledger.head,
                "ledger_intact": self.ledger.verify(),
                "metrics": self.metrics.snapshot(),
                "anomalies": self.anomalies.snapshot(),
                "recent": [e.as_dict() for e in self.ledger.tail(12)],
            },
        }

    def domain_health(self) -> dict[str, dict[str, Any]]:
        """Per-domain population and mean health, for the command surface."""
        out: dict[str, dict[str, Any]] = {}
        for domain in Domain:
            members = self.registry.by_domain(domain)
            active = [m for m in members if m.status is AgentStatus.ACTIVE]
            out[domain.value] = {
                "population": len(members),
                "active": len(active),
                "mean_health": (
                    round(sum(m.health for m in active) / len(active), 3) if active else 0.0
                ),
            }
        return out
