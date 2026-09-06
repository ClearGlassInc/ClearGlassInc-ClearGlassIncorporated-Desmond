# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Fail-closed and boundary-violation tests for the Percival v9 scaffold.

These are the ``/tests/policy`` cases from ``docs/PERCIVAL_V9_ARCHITECTURE.md``:
deny-by-default, the Escalation Gate, fail-closed audit sync, and tamper
detection on the hash-chained ledger. If any of these fail, a code path exists
that lets an ungoverned action execute — which is a release blocker by design.
"""

from __future__ import annotations

import dataclasses

import pytest

from percival_v9 import (
    AuditLedger,
    Capability,
    EscalationError,
    PolicyGovernor,
    WorkflowRun,
    WorkflowState,
)
from percival_v9.internal.audit import FailingLedger
from percival_v9.internal.policy.engine import Risk


@pytest.fixture()
def governor() -> PolicyGovernor:
    return PolicyGovernor(ledger=AuditLedger())


# -- deny-by-default ------------------------------------------------------


def test_unknown_capability_is_denied(governor: PolicyGovernor) -> None:
    decision = governor.evaluate("agent-1", "external_system_write")
    assert not decision.allow
    assert "deny-by-default" in decision.reason


def test_grant_is_identity_scoped(governor: PolicyGovernor) -> None:
    governor.grant("agent-1", Capability("read_metrics"))
    assert governor.evaluate("agent-1", "read_metrics").allow
    assert not governor.evaluate("agent-2", "read_metrics").allow


def test_revoked_capability_is_denied(governor: PolicyGovernor) -> None:
    governor.grant("agent-1", Capability("read_metrics"))
    governor.revoke("agent-1", "read_metrics")
    assert not governor.evaluate("agent-1", "read_metrics").allow


# -- escalation gate -------------------------------------------------------


def test_high_risk_blocked_without_approval(governor: PolicyGovernor) -> None:
    governor.grant("agent-1", Capability("update_pricing", Risk.HIGH))
    decision = governor.evaluate("agent-1", "update_pricing")
    assert not decision.allow
    assert "escalation gate" in decision.reason


def test_high_risk_allowed_with_approval_and_approval_is_single_use(
    governor: PolicyGovernor,
) -> None:
    governor.grant("agent-1", Capability("update_pricing", Risk.HIGH))
    governor.approve("agent-1", "update_pricing")
    assert governor.evaluate("agent-1", "update_pricing").allow
    # The approval is consumed; a second execution must be re-approved.
    assert not governor.evaluate("agent-1", "update_pricing").allow


def test_low_risk_needs_no_approval(governor: PolicyGovernor) -> None:
    governor.grant("agent-1", Capability("generate_copy", Risk.LOW))
    assert governor.evaluate("agent-1", "generate_copy").allow


# -- fail-closed audit sync -------------------------------------------------


def test_ledger_failure_engages_deny_all() -> None:
    governor = PolicyGovernor(ledger=FailingLedger())
    governor.grant("agent-1", Capability("read_metrics"))
    decision = governor.evaluate("agent-1", "read_metrics")
    assert not decision.allow
    assert "fail-closed" in decision.reason
    assert governor.deny_all


def test_deny_all_persists_after_ledger_recovers() -> None:
    governor = PolicyGovernor(ledger=FailingLedger())
    governor.grant("agent-1", Capability("read_metrics"))
    governor.evaluate("agent-1", "read_metrics")  # trips deny-all
    governor.ledger = AuditLedger()  # ledger heals ...
    decision = governor.evaluate("agent-1", "read_metrics")
    assert not decision.allow  # ... but deny-all needs explicit incident reset
    assert "deny-all" in decision.reason


# -- audit ledger integrity --------------------------------------------------


def test_every_decision_is_recorded(governor: PolicyGovernor) -> None:
    governor.grant("agent-1", Capability("read_metrics"))
    governor.evaluate("agent-1", "read_metrics")
    governor.evaluate("agent-1", "not_granted")
    payloads = [e.payload for e in governor.ledger.entries()]
    assert [p["allow"] for p in payloads] == [True, False]
    assert governor.ledger.verify()


def test_tampered_ledger_fails_verification() -> None:
    ledger = AuditLedger()
    ledger.append({"type": "policy_decision", "allow": True})
    ledger.append({"type": "policy_decision", "allow": False})
    entries = list(ledger.entries())
    forged = dataclasses.replace(entries[0], payload={"type": "policy_decision", "allow": False})
    ledger._entries[0] = forged  # simulate direct tampering
    assert not ledger.verify()


# -- workflow escalation gate -------------------------------------------------


def test_execution_unreachable_without_approval() -> None:
    run = WorkflowRun("run-1", AuditLedger())
    with pytest.raises(EscalationError):
        run.execute(actor="agent-1")  # DRAFT -> EXECUTED has no edge
    run.transition(WorkflowState.PENDING_APPROVAL, actor="agent-1")
    with pytest.raises(EscalationError):
        run.execute(actor="agent-1")  # still gated
    assert run.state is WorkflowState.PENDING_APPROVAL


def test_governed_path_reaches_execution_and_is_audited() -> None:
    ledger = AuditLedger()
    run = WorkflowRun("run-2", ledger)
    run.transition(WorkflowState.PENDING_APPROVAL, actor="agent-1")
    run.transition(WorkflowState.APPROVED, actor="operator")
    assert run.execute(actor="agent-1") is WorkflowState.EXECUTED
    transitions = [e.payload for e in ledger.entries() if e.payload["type"] == "state_transition"]
    assert [t["allowed"] for t in transitions] == [True, True, True]
    assert ledger.verify()


def test_rejected_run_is_terminal() -> None:
    run = WorkflowRun("run-3", AuditLedger())
    run.transition(WorkflowState.PENDING_APPROVAL, actor="agent-1")
    run.transition(WorkflowState.REJECTED, actor="operator")
    with pytest.raises(EscalationError):
        run.execute(actor="agent-1")


def test_denied_transition_is_still_audited() -> None:
    ledger = AuditLedger()
    run = WorkflowRun("run-4", ledger)
    with pytest.raises(EscalationError):
        run.execute(actor="agent-1")
    assert ledger.entries()[-1].payload["allowed"] is False
