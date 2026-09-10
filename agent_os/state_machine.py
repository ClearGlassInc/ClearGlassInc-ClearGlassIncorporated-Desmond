# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Incident state machine for governed self-healing workflows.

This module is intentionally stdlib-only and side-effect free except for the
caller-provided audit ledger. It codifies ARTEMIS // FAWL's recovery control
flow so invalid automation jumps fail closed before any executor can act.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from .audit import AuditLedger


class IncidentState(str, Enum):
    """Permitted lifecycle states for an incident/recovery workflow."""

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
    ESCALATED = "ESCALATED"
    ROLLBACK_PENDING = "ROLLBACK_PENDING"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    QUARANTINED = "QUARANTINED"
    MANUAL_INTERVENTION_REQUIRED = "MANUAL_INTERVENTION_REQUIRED"


TERMINAL_STATES = frozenset(
    {
        IncidentState.CLOSED,
        IncidentState.ESCALATED,
        IncidentState.ROLLED_BACK,
        IncidentState.QUARANTINED,
        IncidentState.MANUAL_INTERVENTION_REQUIRED,
    }
)

ALLOWED_TRANSITIONS: dict[IncidentState, frozenset[IncidentState]] = {
    IncidentState.DETECTED: frozenset({IncidentState.VALIDATING, IncidentState.ESCALATED}),
    IncidentState.VALIDATING: frozenset({IncidentState.CORRELATED, IncidentState.ESCALATED, IncidentState.QUARANTINED}),
    IncidentState.CORRELATED: frozenset({IncidentState.CLASSIFIED, IncidentState.ESCALATED}),
    IncidentState.CLASSIFIED: frozenset({IncidentState.CONTAINMENT_PENDING, IncidentState.PLAN_GENERATED, IncidentState.ESCALATED}),
    IncidentState.CONTAINMENT_PENDING: frozenset({IncidentState.CONTAINED, IncidentState.ESCALATED, IncidentState.MANUAL_INTERVENTION_REQUIRED}),
    IncidentState.CONTAINED: frozenset({IncidentState.PLAN_GENERATED, IncidentState.ESCALATED}),
    IncidentState.PLAN_GENERATED: frozenset({IncidentState.AUTHORIZATION_PENDING, IncidentState.ESCALATED}),
    IncidentState.AUTHORIZATION_PENDING: frozenset({IncidentState.EXECUTING, IncidentState.ESCALATED, IncidentState.MANUAL_INTERVENTION_REQUIRED}),
    IncidentState.EXECUTING: frozenset({IncidentState.VERIFYING, IncidentState.ROLLBACK_PENDING, IncidentState.ESCALATED}),
    IncidentState.VERIFYING: frozenset({IncidentState.RECOVERED, IncidentState.ROLLBACK_PENDING, IncidentState.ESCALATED}),
    IncidentState.RECOVERED: frozenset({IncidentState.MONITORING, IncidentState.ROLLBACK_PENDING}),
    IncidentState.MONITORING: frozenset({IncidentState.CLOSED, IncidentState.ROLLBACK_PENDING, IncidentState.ESCALATED}),
    IncidentState.ROLLBACK_PENDING: frozenset({IncidentState.ROLLING_BACK, IncidentState.MANUAL_INTERVENTION_REQUIRED}),
    IncidentState.ROLLING_BACK: frozenset({IncidentState.ROLLED_BACK, IncidentState.MANUAL_INTERVENTION_REQUIRED}),
    IncidentState.CLOSED: frozenset(),
    IncidentState.ESCALATED: frozenset(),
    IncidentState.ROLLED_BACK: frozenset(),
    IncidentState.QUARANTINED: frozenset(),
    IncidentState.MANUAL_INTERVENTION_REQUIRED: frozenset(),
}


@dataclass(frozen=True)
class TransitionRecord:
    """Auditable evidence for one accepted state transition."""

    incident_id: str
    from_state: IncidentState | None
    to_state: IncidentState
    actor: str
    timestamp: str
    evidence: tuple[str, ...]
    policy_decision: str
    correlation_id: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        row = asdict(self)
        row["from_state"] = self.from_state.value if self.from_state else None
        row["to_state"] = self.to_state.value
        row["evidence"] = list(self.evidence)
        return row


@dataclass
class IncidentStateMachine:
    """Fail-closed state tracker with tamper-evident transition audit."""

    incident_id: str
    ledger: AuditLedger = field(default_factory=AuditLedger)
    state: IncidentState = IncidentState.DETECTED
    history: list[TransitionRecord] = field(default_factory=list)

    @classmethod
    def start(
        cls,
        *,
        actor: str,
        evidence: tuple[str, ...],
        reason: str,
        incident_id: str | None = None,
        correlation_id: str | None = None,
        policy_decision: str = "intake_observation_only",
        ledger: AuditLedger | None = None,
    ) -> IncidentStateMachine:
        machine = cls(incident_id=incident_id or f"inc-{uuid4().hex}", ledger=ledger or AuditLedger())
        machine._record(
            None,
            IncidentState.DETECTED,
            actor=actor,
            evidence=evidence,
            policy_decision=policy_decision,
            correlation_id=correlation_id or machine.incident_id,
            reason=reason,
        )
        return machine

    def transition(
        self,
        to_state: IncidentState | str,
        *,
        actor: str,
        evidence: tuple[str, ...],
        policy_decision: str,
        correlation_id: str,
        reason: str,
    ) -> TransitionRecord:
        target = IncidentState(to_state)
        allowed = ALLOWED_TRANSITIONS[self.state]
        if target not in allowed:
            raise ValueError(f"invalid incident transition {self.state.value} -> {target.value}")
        return self._record(
            self.state,
            target,
            actor=actor,
            evidence=evidence,
            policy_decision=policy_decision,
            correlation_id=correlation_id,
            reason=reason,
        )

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def _record(
        self,
        from_state: IncidentState | None,
        to_state: IncidentState,
        *,
        actor: str,
        evidence: tuple[str, ...],
        policy_decision: str,
        correlation_id: str,
        reason: str,
    ) -> TransitionRecord:
        if not actor or not evidence or not policy_decision or not correlation_id or not reason:
            raise ValueError("transition requires actor, evidence, policy_decision, correlation_id, and reason")
        record = TransitionRecord(
            incident_id=self.incident_id,
            from_state=from_state,
            to_state=to_state,
            actor=actor,
            timestamp=datetime.now(UTC).isoformat(),
            evidence=tuple(evidence),
            policy_decision=policy_decision,
            correlation_id=correlation_id,
            reason=reason,
        )
        self.state = to_state
        self.history.append(record)
        self.ledger.append("incident_state_transition", record.to_dict())
        return record
