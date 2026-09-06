# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Tests for sentinel/sentinel/approvals.py — signed, single-use, expiring
human approvals (v10 boundary doctrine)."""
from __future__ import annotations

import pytest

from sentinel.approvals import Approval, ApprovalGate, new_trace_id


def _issue(gate: ApprovalGate, *, now: float = 1000.0, ttl: float = 300.0):
    return gate.issue(
        "external_send", "operations",
        subject="payload-42", approver="Desmond",
        ttl_seconds=ttl, now=now,
    )


# --------------------------------------------------------------------------- #
# issue
# --------------------------------------------------------------------------- #
def test_issue_returns_signed_bound_approval():
    gate = ApprovalGate()
    appr = _issue(gate)
    assert isinstance(appr, Approval)
    assert appr.action_kind == "external_send"
    assert appr.subject == "payload-42"
    assert appr.approver == "Desmond"
    assert appr.signature and appr.trace_id.startswith("tr_")


def test_issue_requires_human_approver():
    gate = ApprovalGate()
    with pytest.raises(ValueError):
        gate.issue("external_send", "operations", subject="x", approver="   ")


def test_issue_rejects_nonpositive_ttl():
    gate = ApprovalGate()
    with pytest.raises(ValueError):
        gate.issue("external_send", "operations", subject="x", approver="d", ttl_seconds=0)


# --------------------------------------------------------------------------- #
# happy path
# --------------------------------------------------------------------------- #
def test_redeem_succeeds_for_exact_action():
    gate = ApprovalGate()
    appr = _issue(gate, now=1000.0)
    res = gate.redeem(appr.token, "external_send", "operations", "payload-42", now=1100.0)
    assert res.ok is True
    assert res.trace_id == appr.trace_id


# --------------------------------------------------------------------------- #
# single-use / replay
# --------------------------------------------------------------------------- #
def test_second_redeem_is_denied_replay():
    gate = ApprovalGate()
    appr = _issue(gate, now=1000.0)
    assert gate.redeem(appr.token, "external_send", "operations", "payload-42", now=1100.0).ok
    second = gate.redeem(appr.token, "external_send", "operations", "payload-42", now=1101.0)
    assert second.ok is False
    assert "replay" in second.reason
    assert gate.is_spent(appr.token) is True


# --------------------------------------------------------------------------- #
# binding: cannot repurpose an approval
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "action,scope,subject",
    [
        ("modify_system", "operations", "payload-42"),   # wrong action
        ("external_send", "security", "payload-42"),     # wrong scope
        ("external_send", "operations", "payload-99"),   # wrong subject
    ],
)
def test_redeem_denied_when_not_exactly_matching(action, scope, subject):
    gate = ApprovalGate()
    appr = _issue(gate, now=1000.0)
    res = gate.redeem(appr.token, action, scope, subject, now=1100.0)
    assert res.ok is False
    assert "does not authorize" in res.reason
    assert gate.is_spent(appr.token) is False  # a mismatch does not spend it


# --------------------------------------------------------------------------- #
# expiry
# --------------------------------------------------------------------------- #
def test_expired_approval_is_denied():
    gate = ApprovalGate()
    appr = _issue(gate, now=1000.0, ttl=300.0)
    res = gate.redeem(appr.token, "external_send", "operations", "payload-42", now=1000.0 + 301)
    assert res.ok is False
    assert "expired" in res.reason


# --------------------------------------------------------------------------- #
# forgery / tampering
# --------------------------------------------------------------------------- #
def test_unknown_token_is_denied():
    gate = ApprovalGate()
    res = gate.redeem("nope", "external_send", "operations", "payload-42")
    assert res.ok is False
    assert "unknown" in res.reason


def test_tampered_fields_fail_signature():
    gate = ApprovalGate()
    appr = _issue(gate, now=1000.0)
    # Forge a higher-privilege action by swapping the stored approval's fields
    # while keeping the original signature — must fail signature verification.
    forged = Approval(**{**appr.__dict__, "action_kind": "modify_system"})
    gate._issued[appr.token] = forged
    res = gate.redeem(appr.token, "modify_system", "operations", "payload-42", now=1100.0)
    assert res.ok is False
    assert "invalid signature" in res.reason


def test_approvals_do_not_cross_gates():
    # A token minted by one gate cannot be redeemed by another (different key).
    g1, g2 = ApprovalGate(), ApprovalGate()
    appr = _issue(g1, now=1000.0)
    g2._issued[appr.token] = appr  # even if the token leaks to another gate
    res = g2.redeem(appr.token, "external_send", "operations", "payload-42", now=1100.0)
    assert res.ok is False
    assert "invalid signature" in res.reason


# --------------------------------------------------------------------------- #
# trace ids
# --------------------------------------------------------------------------- #
def test_trace_id_is_propagated_and_unique():
    a, b = new_trace_id(), new_trace_id()
    assert a != b and a.startswith("tr_")
    gate = ApprovalGate()
    appr = gate.issue("external_send", "ops", subject="s", approver="d", trace_id="tr_fixed")
    assert appr.trace_id == "tr_fixed"
    assert gate.redeem(appr.token, "external_send", "ops", "s").trace_id == "tr_fixed"
