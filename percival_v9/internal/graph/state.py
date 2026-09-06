# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Governed workflow state machine for Percival v9.

Deterministic transitions with a hard-wired Escalation Gate:

    DRAFT -> PENDING_APPROVAL -> APPROVED -> EXECUTED
                                          -> REJECTED (terminal)

``EXECUTED`` is reachable *only* through ``APPROVED``; there is no edge from
``DRAFT`` or ``PENDING_APPROVAL`` to ``EXECUTED``, so no caller can skip the
gate. Every transition is appended to the audit ledger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from percival_v9.internal.audit import AuditLedger


class WorkflowState(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class EscalationError(RuntimeError):
    """Raised on any attempt to make an illegal state transition."""


#: The only legal edges in the graph. Nothing outside this map is possible.
_EDGES: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.DRAFT: frozenset({WorkflowState.PENDING_APPROVAL}),
    WorkflowState.PENDING_APPROVAL: frozenset({WorkflowState.APPROVED, WorkflowState.REJECTED}),
    WorkflowState.APPROVED: frozenset({WorkflowState.EXECUTED, WorkflowState.REJECTED}),
    WorkflowState.REJECTED: frozenset(),
    WorkflowState.EXECUTED: frozenset(),
}


@dataclass
class WorkflowRun:
    """One governed workflow instance."""

    run_id: str
    ledger: AuditLedger
    state: WorkflowState = WorkflowState.DRAFT
    history: list[WorkflowState] = field(default_factory=lambda: [WorkflowState.DRAFT])

    def transition(self, target: WorkflowState, actor: str) -> WorkflowState:
        """Move to ``target`` if the edge exists; record it either way."""
        allowed = target in _EDGES[self.state]
        self.ledger.append(
            {
                "type": "state_transition",
                "run_id": self.run_id,
                "actor": actor,
                "from": self.state.value,
                "to": target.value,
                "allowed": allowed,
            }
        )
        if not allowed:
            raise EscalationError(
                f"illegal transition {self.state.value} -> {target.value} (run {self.run_id})"
            )
        self.state = target
        self.history.append(target)
        return self.state

    def execute(self, actor: str) -> WorkflowState:
        """Convenience: attempt execution. Fails unless state is APPROVED."""
        return self.transition(WorkflowState.EXECUTED, actor)
