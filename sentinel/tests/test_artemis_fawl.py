# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Proof tests for the ARTEMIS // FAWL governance spine.

Properties asserted:
  * the lifecycle state machine rejects every illegal transition and audits legal ones
  * automation safety levels are assigned correctly (0..4)
  * the Policy Decision Point is fail-closed (unverifiable → deny/approval)
  * level-4 (prohibited) never permits; AI level≥2 never self-authorizes
  * the kill switch freezes mutating automation but never observation
  * capability tokens are single-use, expiring, and scope-bound
  * the orchestrator rolls back + escalates when verification fails
  * malicious telemetry is quarantined; the audit chain stays intact
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest

from sentinel.artemis_fawl import (
    TERMINAL_STATES,
    TRANSITIONS,
    Action,
    CapabilityBroker,
    CapabilityError,
    Decision,
    FawlOrchestrator,
    IncidentInput,
    InvalidTransition,
    LifecycleState,
    PolicyContext,
    PolicyDecisionPoint,
    SafetyLevel,
    StateMachine,
    Verdict,
    run_self_check,
)

_S = LifecycleState


# ------------------------------------------------------- state machine ----

def test_transition_table_targets_are_known_states():
    for src, targets in TRANSITIONS.items():
        assert isinstance(src, LifecycleState)
        for t in targets:
            assert isinstance(t, LifecycleState)


def test_terminal_states_have_no_outgoing_transitions():
    for term in TERMINAL_STATES:
        assert TRANSITIONS[term] == frozenset()


def test_legal_transition_is_recorded_and_audited():
    sm = StateMachine("INC-1")
    sm.to(_S.VALIDATING, actor="automation", reason="go")
    assert sm.state is _S.VALIDATING
    assert len(sm.history) == 1
    assert sm.audit.verify()
    assert sm.history[0].correlation_id == "INC-1"


def test_illegal_transition_raises_and_does_not_mutate():
    sm = StateMachine("INC-2")
    with pytest.raises(InvalidTransition):
        sm.to(_S.CLOSED, actor="automation", reason="skip ahead")
    assert sm.state is _S.DETECTED
    assert sm.history == []


def test_quarantine_is_reachable_from_active_state_and_terminal():
    sm = StateMachine("INC-3")
    sm.to(_S.VALIDATING, actor="automation", reason="go")
    sm.quarantine(actor="operator", reason="kill switch")
    assert sm.state is _S.QUARANTINED
    assert sm.terminal
    with pytest.raises(InvalidTransition):
        sm.quarantine(actor="operator", reason="again")


# ------------------------------------------------------- safety levels ----

def test_safety_level_assignment():
    assert Action("look", "svc", risk=0, reversible=True, kind="observe").safety_level() is SafetyLevel.OBSERVE
    assert Action("restart", "svc", risk=20, reversible=True).safety_level() is SafetyLevel.LOW_REVERSIBLE
    assert Action("reroute", "svc", risk=55, reversible=True).safety_level() is SafetyLevel.BOUNDED_PRODUCTION
    assert Action("failover", "svc", risk=90, reversible=False).safety_level() is SafetyLevel.HUMAN_AUTHORIZED
    assert Action("wipe", "svc", risk=99, reversible=False).safety_level() is SafetyLevel.PROHIBITED
    assert Action("x", "svc", risk=10, reversible=True, prohibited=True).safety_level() is SafetyLevel.PROHIBITED


# --------------------------------------------------------------- PDP ----

def _pdp():
    return PolicyDecisionPoint()


def test_pdp_observe_permitted_even_under_kill_switch():
    a = Action("read_metrics", "svc", risk=0, reversible=True, kind="observe")
    d = _pdp().evaluate(a, PolicyContext(kill_switch=True, confidence=None))
    assert d.verdict is Verdict.PERMIT


def test_pdp_denies_unverifiable_confidence():
    a = Action("restart", "svc", risk=20, reversible=True)
    d = _pdp().evaluate(a, PolicyContext(confidence=None))
    assert d.verdict is Verdict.DENY


def test_pdp_level4_always_denied():
    a = Action("wipe", "svc", risk=99, reversible=False)
    d = _pdp().evaluate(a, PolicyContext(actor="human", confidence=1.0, approval_token="APV"))
    assert d.verdict is Verdict.DENY


def test_pdp_level1_auto_when_confident():
    a = Action("restart", "svc", risk=20, reversible=True)
    assert _pdp().evaluate(a, PolicyContext(confidence=0.9)).verdict is Verdict.PERMIT
    assert _pdp().evaluate(a, PolicyContext(confidence=0.4)).verdict is Verdict.REQUIRE_APPROVAL


def test_pdp_level2_needs_approval_and_high_confidence():
    a = Action("reroute", "svc", risk=55, reversible=True)
    assert _pdp().evaluate(a, PolicyContext(confidence=0.95, approval_token="APV")).verdict is Verdict.PERMIT
    assert _pdp().evaluate(a, PolicyContext(confidence=0.95)).verdict is Verdict.REQUIRE_APPROVAL
    assert _pdp().evaluate(a, PolicyContext(confidence=0.7, approval_token="APV")).verdict is Verdict.REQUIRE_APPROVAL


def test_pdp_level3_requires_human_authorization():
    a = Action("failover", "svc", risk=90, reversible=False)
    assert _pdp().evaluate(a, PolicyContext(actor="automation", confidence=0.99)).verdict is Verdict.REQUIRE_APPROVAL
    assert _pdp().evaluate(a, PolicyContext(actor="human", confidence=0.99, approval_token="APV")).verdict is Verdict.PERMIT


def test_pdp_ai_cannot_self_authorize_level2():
    a = Action("scale", "svc", risk=55, reversible=True, ai_originated=True)
    # even with high confidence, an AI-proposed L2 needs a human approver
    d = _pdp().evaluate(a, PolicyContext(actor="automation", confidence=0.99, approval_token="APV"))
    assert d.verdict is Verdict.REQUIRE_APPROVAL
    d2 = _pdp().evaluate(a, PolicyContext(actor="human", confidence=0.99, approval_token="APV"))
    assert d2.verdict is Verdict.PERMIT


def test_pdp_kill_switch_denies_mutation():
    a = Action("restart", "svc", risk=20, reversible=True)
    assert _pdp().evaluate(a, PolicyContext(confidence=0.9, kill_switch=True)).verdict is Verdict.DENY


def test_pdp_budget_and_blast_radius_gates():
    a = Action("restart", "svc", risk=20, reversible=True)
    assert _pdp().evaluate(a, PolicyContext(confidence=0.9, recovery_budget_remaining=0)).verdict is Verdict.REQUIRE_APPROVAL
    assert _pdp().evaluate(a, PolicyContext(confidence=0.9, blast_radius=99, blast_ceiling=5)).verdict is Verdict.REQUIRE_APPROVAL


# ------------------------------------------------------ capabilities ----

def _permit(action):
    return Decision(Verdict.PERMIT, action, action.safety_level(), ("ok",))


def test_capability_single_use():
    a = Action("restart", "svc", risk=20, reversible=True)
    broker = CapabilityBroker()
    tok = broker.issue(_permit(a))
    broker.redeem(tok, a)
    with pytest.raises(CapabilityError):
        broker.redeem(tok, a)


def test_capability_scope_mismatch_rejected():
    a = Action("restart", "svc", risk=20, reversible=True)
    other = Action("delete", "svc", risk=20, reversible=True)
    broker = CapabilityBroker()
    tok = broker.issue(_permit(a))
    with pytest.raises(CapabilityError):
        broker.redeem(tok, other)


def test_capability_expiry():
    now = {"t": 100.0}
    a = Action("restart", "svc", risk=20, reversible=True)
    broker = CapabilityBroker(ttl=10.0, clock=lambda: now["t"])
    tok = broker.issue(_permit(a))
    now["t"] = 200.0
    with pytest.raises(CapabilityError):
        broker.redeem(tok, a)


def test_capability_not_issued_for_denied_decision():
    a = Action("wipe", "svc", risk=99, reversible=False)
    d = Decision(Verdict.DENY, a, SafetyLevel.PROHIBITED, ("no",))
    with pytest.raises(CapabilityError):
        CapabilityBroker().issue(d)


# ------------------------------------------------------ orchestrator ----

def _orch():
    return FawlOrchestrator()


def test_orchestrator_happy_path_closes():
    a = Action("restart", "svc", risk=20, reversible=True)
    rec = _orch().run(IncidentInput("INC", action=a, ctx=PolicyContext(confidence=0.9)),
                      executor=lambda act, tok: True, verifier=lambda act: True)
    assert rec.final_state is _S.CLOSED
    assert rec.executed and rec.verified
    assert rec.audit_verified


def test_orchestrator_rolls_back_on_failed_verification():
    a = Action("restart", "svc", risk=20, reversible=True)
    rec = _orch().run(IncidentInput("INC", action=a, ctx=PolicyContext(confidence=0.9)),
                      executor=lambda act, tok: True, verifier=lambda act: False)
    assert rec.final_state is _S.ESCALATED
    assert _S.ROLLING_BACK.value in rec.transitions
    assert _S.ROLLED_BACK.value in rec.transitions
    assert rec.audit_verified


def test_orchestrator_rolls_back_on_failed_execution():
    a = Action("restart", "svc", risk=20, reversible=True)
    rec = _orch().run(IncidentInput("INC", action=a, ctx=PolicyContext(confidence=0.9)),
                      executor=lambda act, tok: False, verifier=lambda act: True)
    assert rec.final_state is _S.ESCALATED
    assert rec.executed is False
    assert _S.ROLLED_BACK.value in rec.transitions


def test_orchestrator_denied_action_never_executes():
    a = Action("wipe", "svc", risk=99, reversible=False)
    calls = []
    rec = _orch().run(IncidentInput("INC", action=a, ctx=PolicyContext(confidence=0.9)),
                      executor=lambda act, tok: calls.append(act.key) or True,
                      verifier=lambda act: True)
    assert rec.final_state is _S.MANUAL_INTERVENTION_REQUIRED
    assert calls == []


def test_orchestrator_malicious_signal_quarantined():
    a = Action("restart", "svc", risk=20, reversible=True)
    rec = _orch().run(IncidentInput("INC", action=a, signal_malicious=True,
                                    ctx=PolicyContext(confidence=0.9)),
                      executor=lambda act, tok: True, verifier=lambda act: True)
    assert rec.final_state is _S.QUARANTINED
    assert not rec.executed


def test_orchestrator_invalid_signal_escalates():
    a = Action("restart", "svc", risk=20, reversible=True)
    rec = _orch().run(IncidentInput("INC", action=a, signal_valid=False,
                                    ctx=PolicyContext(confidence=0.9)),
                      executor=lambda act, tok: True, verifier=lambda act: True)
    assert rec.final_state is _S.ESCALATED
    assert not rec.executed


def test_orchestrator_executor_receives_valid_token():
    a = Action("restart", "svc", risk=20, reversible=True)
    seen = {}

    def executor(act, tok):
        seen["token"] = tok.token_id
        seen["idem"] = tok.idempotency_key
        return True

    rec = _orch().run(IncidentInput("INC", action=a, ctx=PolicyContext(confidence=0.9)),
                      executor=executor, verifier=lambda act: True)
    assert seen["token"].startswith("CAP-")
    assert seen["idem"] and rec.final_state is _S.CLOSED


# --------------------------------------------------------- self-check ----

def test_self_check_invariants_hold():
    _receipts, failures = run_self_check()
    assert failures == []
