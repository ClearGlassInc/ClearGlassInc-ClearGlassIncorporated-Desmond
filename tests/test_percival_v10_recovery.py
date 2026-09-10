# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Percival v10 policy-boundary and recovery semantics."""

from __future__ import annotations

import pytest

from percival_v9 import (
    AuditLedger,
    Capability,
    ExecutionGraph,
    PlanNode,
    PolicyGovernor,
    RetryPolicy,
    SignedApproval,
    TraceContext,
)
from percival_v9.internal.audit import FailingLedger
from percival_v9.internal.graph.plan import NodeStatus
from percival_v9.internal.policy.engine import Risk


def test_deny_overrides_allow_rules() -> None:
    governor = PolicyGovernor(ledger=AuditLedger())
    governor.grant("agent-1", Capability("read_metrics", Risk.LOW))
    governor.deny("agent-1", "read_metrics")

    decision = governor.evaluate("agent-1", "read_metrics")

    assert not decision.allow
    assert "explicit-deny" in decision.reason


def test_stale_policy_bundle_cannot_execute_until_cache_refresh() -> None:
    governor = PolicyGovernor(ledger=AuditLedger())
    governor.grant("agent-1", Capability("read_metrics", Risk.LOW))
    governor.require_policy_version("bundle-v10.1")

    stale = governor.evaluate("agent-1", "read_metrics")
    assert not stale.allow
    assert stale.recovery == "refresh_policy_cache"

    governor.refresh_policy_cache()
    fresh = governor.evaluate("agent-1", "read_metrics")
    assert fresh.allow
    assert fresh.policy_version == "bundle-v10.1"


def test_sensitive_action_requires_valid_signed_approval() -> None:
    governor = PolicyGovernor(ledger=AuditLedger())
    governor.deploy_policy_bundle("bundle-v10.0")
    governor.grant("agent-1", Capability("execute_external", Risk.HIGH))

    denied = governor.evaluate("agent-1", "execute_external")
    assert not denied.allow
    assert "signed approval" in denied.reason

    governor.approve_signed(
        SignedApproval(
            identity="agent-1",
            capability="execute_external",
            signer="operator:commander-7",
            signature="sig:detached-ed25519-placeholder",
            policy_version="bundle-v10.0",
        )
    )
    assert governor.evaluate("agent-1", "execute_external").allow
    assert not governor.evaluate("agent-1", "execute_external").allow


def test_audit_outage_fails_closed_for_policy() -> None:
    governor = PolicyGovernor(ledger=FailingLedger())
    governor.grant("agent-1", Capability("read_metrics", Risk.LOW))

    decision = governor.evaluate("agent-1", "read_metrics")

    assert not decision.allow
    assert decision.recovery == "deny_all"
    assert governor.deny_all


def test_graph_requires_dependencies_and_rewinds_to_safe_checkpoint() -> None:
    ledger = AuditLedger()
    graph = ExecutionGraph(
        graph_id="graph-1",
        ledger=ledger,
        nodes={
            "triage": PlanNode(
                node_id="triage",
                input_ref="event.raw",
                output_ref="event.triaged",
                required_capability="read_metrics",
                timeout_ms=1_000,
                retry_policy=RetryPolicy(max_attempts=1, timeout_ms=1_000),
            ),
            "external": PlanNode(
                node_id="external",
                input_ref="event.triaged",
                output_ref="package.prepared",
                required_capability="execute_external",
                timeout_ms=2_000,
                retry_policy=RetryPolicy(max_attempts=2, timeout_ms=2_000),
                approval_state="signed_required",
                failure_fallback="rewind_last_safe_checkpoint",
                dependencies=("triage",),
            ),
        },
    )
    trace = TraceContext.new("corr-1")

    with pytest.raises(RuntimeError):
        graph.mark_started("external", trace.trace_id)
    assert graph.recovery_mode

    graph.mark_started("triage", trace.trace_id)
    graph.mark_succeeded("triage", trace.trace_id)
    graph.mark_started("external", trace.trace_id)
    checkpoint = graph.rewind_last_safe_checkpoint(trace.trace_id)

    assert checkpoint == "triage"
    assert graph.status["triage"] is NodeStatus.SUCCEEDED
    assert graph.status["external"] is NodeStatus.PENDING
    assert any(e.payload["type"] == "recovery_rewind" for e in ledger.entries())


def test_graph_audit_outage_halts_execution() -> None:
    graph = ExecutionGraph(
        graph_id="graph-2",
        ledger=FailingLedger(),
        nodes={
            "triage": PlanNode(
                node_id="triage",
                input_ref="event.raw",
                output_ref="event.triaged",
                required_capability="read_metrics",
                timeout_ms=1_000,
                retry_policy=RetryPolicy(max_attempts=1, timeout_ms=1_000),
            )
        },
    )

    with pytest.raises(RuntimeError, match="fail-closed"):
        graph.mark_started("triage", "trace-1")
    assert graph.recovery_mode
