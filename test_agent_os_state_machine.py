# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Regression tests for ARTEMIS // FAWL incident state safety."""
from __future__ import annotations

import pytest

from agent_os.state_machine import IncidentState, IncidentStateMachine


def _machine() -> IncidentStateMachine:
    return IncidentStateMachine.start(
        actor="signal-gateway",
        evidence=("schema:v1",),
        reason="fresh authenticated signal accepted",
        incident_id="inc-test",
        correlation_id="corr-test",
    )


def test_happy_path_detect_to_close_is_audited() -> None:
    machine = _machine()
    for state in [
        IncidentState.VALIDATING,
        IncidentState.CORRELATED,
        IncidentState.CLASSIFIED,
        IncidentState.CONTAINMENT_PENDING,
        IncidentState.CONTAINED,
        IncidentState.PLAN_GENERATED,
        IncidentState.AUTHORIZATION_PENDING,
        IncidentState.EXECUTING,
        IncidentState.VERIFYING,
        IncidentState.RECOVERED,
        IncidentState.MONITORING,
        IncidentState.CLOSED,
    ]:
        machine.transition(
            state,
            actor="policy-engine",
            evidence=(f"evidence:{state.value}",),
            policy_decision="allowed_by_test_policy",
            correlation_id="corr-test",
            reason=f"advance to {state.value}",
        )

    assert machine.state is IncidentState.CLOSED
    assert machine.is_terminal is True
    assert len(machine.history) == 13
    assert machine.ledger.verify() == (True, None)


def test_invalid_transition_fails_closed_without_audit_mutation() -> None:
    machine = _machine()
    before_head = machine.ledger.head
    with pytest.raises(ValueError, match="invalid incident transition"):
        machine.transition(
            IncidentState.EXECUTING,
            actor="executor",
            evidence=("attempted-skip",),
            policy_decision="denied",
            correlation_id="corr-test",
            reason="cannot execute before validation and authorization",
        )

    assert machine.state is IncidentState.DETECTED
    assert machine.ledger.head == before_head
    assert len(machine.history) == 1


def test_transition_requires_attribution_evidence_policy_and_reason() -> None:
    machine = _machine()
    with pytest.raises(ValueError, match="transition requires"):
        machine.transition(
            IncidentState.VALIDATING,
            actor="",
            evidence=("schema:v1",),
            policy_decision="allowed",
            correlation_id="corr-test",
            reason="advance",
        )


def test_rollback_failure_path_reaches_terminal_state() -> None:
    machine = _machine()
    for state in [
        IncidentState.VALIDATING,
        IncidentState.CORRELATED,
        IncidentState.CLASSIFIED,
        IncidentState.PLAN_GENERATED,
        IncidentState.AUTHORIZATION_PENDING,
        IncidentState.EXECUTING,
        IncidentState.VERIFYING,
        IncidentState.ROLLBACK_PENDING,
        IncidentState.ROLLING_BACK,
        IncidentState.ROLLED_BACK,
    ]:
        machine.transition(
            state,
            actor="recovery-controller",
            evidence=(f"evidence:{state.value}",),
            policy_decision="allowed_by_test_policy",
            correlation_id="corr-test",
            reason=f"advance to {state.value}",
        )

    assert machine.state is IncidentState.ROLLED_BACK
    assert machine.is_terminal is True
    assert machine.ledger.verify()[0] is True
