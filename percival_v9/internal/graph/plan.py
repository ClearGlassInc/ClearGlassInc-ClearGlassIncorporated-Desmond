# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Percival v10 graph planner contracts and recovery semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from percival_v9.internal.audit import AuditLedger, LedgerError


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    HALTED = "halted"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 2
    timeout_ms: int = 5_000


@dataclass(frozen=True)
class PlanNode:
    node_id: str
    input_ref: str
    output_ref: str
    required_capability: str
    timeout_ms: int
    retry_policy: RetryPolicy
    approval_state: str = "not_required"
    failure_fallback: str = "halt"
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.timeout_ms <= 0:
            raise ValueError("node timeout must be explicit and positive")
        if self.retry_policy.max_attempts < 0:
            raise ValueError("retry attempts cannot be negative")


@dataclass
class ExecutionGraph:
    graph_id: str
    ledger: AuditLedger
    nodes: dict[str, PlanNode]
    status: dict[str, NodeStatus] = field(default_factory=dict)
    safe_checkpoints: list[str] = field(default_factory=list)
    recovery_mode: bool = False

    def __post_init__(self) -> None:
        self.status = {node_id: NodeStatus.PENDING for node_id in self.nodes}

    def runnable(self, node_id: str) -> bool:
        node = self.nodes[node_id]
        return all(self.status[d] is NodeStatus.SUCCEEDED for d in node.dependencies)

    def mark_started(self, node_id: str, trace_id: str) -> None:
        if not self.runnable(node_id):
            self.halt("dependency_not_satisfied", trace_id)
            raise RuntimeError(f"node {node_id} prerequisites are not satisfied")
        self.status[node_id] = NodeStatus.RUNNING
        self._audit("execution_node_start", node_id=node_id, trace_id=trace_id)

    def mark_succeeded(self, node_id: str, trace_id: str) -> None:
        self.status[node_id] = NodeStatus.SUCCEEDED
        self.safe_checkpoints.append(node_id)
        self._audit(
            "execution_node_stop", node_id=node_id, trace_id=trace_id, result="succeeded"
        )

    def halt(self, reason: str, trace_id: str) -> None:
        self.recovery_mode = True
        self._audit("recovery_halt", reason=reason, trace_id=trace_id)

    def rewind_last_safe_checkpoint(self, trace_id: str) -> str | None:
        if not self.safe_checkpoints:
            self.halt("no_safe_checkpoint", trace_id)
            return None
        checkpoint = self.safe_checkpoints[-1]
        seen_checkpoint = False
        for node_id in self.nodes:
            if node_id == checkpoint:
                seen_checkpoint = True
                continue
            if seen_checkpoint:
                self.status[node_id] = NodeStatus.PENDING
        self.recovery_mode = False
        self._audit("recovery_rewind", checkpoint=checkpoint, trace_id=trace_id)
        return checkpoint

    def _audit(self, event_type: str, **payload: object) -> None:
        try:
            self.ledger.append({"type": event_type, "graph_id": self.graph_id, **payload})
        except LedgerError as exc:
            self.recovery_mode = True
            raise RuntimeError("fail-closed: audit ledger unavailable") from exc
