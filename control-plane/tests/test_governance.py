"""No high or critical action may execute without a human approval.

``CLAUDE.md``: "Do not add a code path that lets a high/critical action execute
without an approval — ``daily_loop.py``'s governance self-check (and
``tests/test_governance.py``) will fail if you do, by design." This is that
file.

The invariant is stated three ways on purpose, because each fails differently:

* **Fail closed on the unknown.** An action nobody scored must gate. A new
  action added to a router but not to ``ACTION_RISK`` is the likeliest way for
  an ungoverned path to appear, and the failure is silent.
* **The always-escalate set is a floor, not a hint.** Money, fulfilment and
  outbound actions gate regardless of score, and no payload or flag lowers
  that.
* **Low confidence hard-gates on its own.** A score bump alone would leave a
  low-base action under the HIGH threshold — the reason string would claim an
  escalation the code did not perform.

``governance.py`` is stdlib-only so it imports in the minimal CI environments
that run this gate without the web stack. Keep this file stdlib-only too.
"""

from __future__ import annotations

import pytest

from app.governance import (
    ACTION_RISK,
    ALWAYS_ESCALATE,
    RiskTier,
    score_action,
)
from app.daily_loop import governance_selfcheck

# Payloads that raise a score. If any of these could talk an action *down*, the
# gate could be argued out of existence one field at a time.
ESCALATING_PAYLOADS = [
    {},
    {"old_price": 100, "new_price": 500},
    {"audience": "all"},
    {"bulk": True},
    {"note": "approved verbally"},
    {"requires_approval": False},
    {"approved": True},
    {"tier": "low"},
    {"score": 0},
    {"printful_auto_confirm": True},
]


def test_the_daily_loop_self_check_reports_no_failures() -> None:
    """The same gate the scheduled Commerce Daily Loop runs."""
    failures = governance_selfcheck()
    assert failures == [], f"governance self-check failed: {failures}"


def test_an_unknown_action_fails_closed() -> None:
    assessment = score_action("some_action_nobody_has_scored_yet")
    assert assessment.requires_approval, "an unscored action must gate, never auto-execute"
    assert assessment.score >= 60, f"unknown actions must land at least HIGH, got {assessment.score}"
    assert assessment.tier in (RiskTier.HIGH, RiskTier.CRITICAL)


@pytest.mark.parametrize("payload", ESCALATING_PAYLOADS)
def test_an_unknown_action_stays_closed_whatever_the_payload_claims(payload: dict) -> None:
    assert score_action("still_not_a_known_action", payload).requires_approval, (
        f"a caller-supplied payload talked an unknown action past the gate: {payload}"
    )


@pytest.mark.parametrize("action", sorted(ALWAYS_ESCALATE))
def test_every_always_escalate_action_requires_approval(action: str) -> None:
    assert score_action(action).requires_approval, (
        f"{action} is in ALWAYS_ESCALATE but did not require approval"
    )


@pytest.mark.parametrize("action", sorted(ALWAYS_ESCALATE))
@pytest.mark.parametrize("flag", [True, False])
def test_always_escalate_survives_the_hard_gate_flag(action: str, flag: bool) -> None:
    """``require_approval_for_high_risk`` changes the wording, not the verdict.

    It selects which reason is recorded. If it ever gated the decision itself,
    passing False would auto-execute a refund.
    """
    assert score_action(action, require_approval_for_high_risk=flag).requires_approval, (
        f"{action} escaped the gate with require_approval_for_high_risk={flag}"
    )


@pytest.mark.parametrize("action", sorted(ALWAYS_ESCALATE))
@pytest.mark.parametrize("payload", ESCALATING_PAYLOADS)
def test_no_payload_can_talk_an_escalated_action_down(action: str, payload: dict) -> None:
    assert score_action(action, payload).requires_approval, (
        f"{action} escaped the gate with payload {payload}"
    )


def test_every_high_or_critical_scored_action_requires_approval() -> None:
    ungated = [
        action
        for action, score in ACTION_RISK.items()
        if score >= 60 and not score_action(action).requires_approval
    ]
    assert not ungated, f"high/critical actions that auto-execute: {ungated}"


def test_low_confidence_hard_gates_even_a_low_risk_action() -> None:
    """Operating rule 8, on the lowest-scoring action in the table.

    A score bump alone would leave it under the HIGH threshold; only an
    independent condition actually escalates it.
    """
    lowest = min(ACTION_RISK, key=lambda action: ACTION_RISK[action])
    assert not score_action(lowest).requires_approval, (
        f"{lowest} is the lowest-risk action and should auto-execute normally; "
        "this test needs a different fixture"
    )
    assert score_action(lowest, low_confidence=True).requires_approval, (
        f"{lowest} auto-executed despite low confidence — rule 8 is not enforced"
    )


def test_every_money_or_fulfillment_action_is_in_the_always_escalate_set() -> None:
    """Catch a money-moving action added to ACTION_RISK but not to the floor.

    Scoring it high is not enough: a future payload rule or threshold change
    could drop it under the line, and the always-escalate set is what makes
    that impossible.
    """
    money_words = ("payment", "refund", "pricing", "tax", "reorder", "fulfillment")
    missing = [
        action
        for action in ACTION_RISK
        if any(word in action for word in money_words) and action not in ALWAYS_ESCALATE
    ]
    assert not missing, (
        f"money/fulfilment actions scored but not always-escalated: {missing}"
    )


def test_the_always_escalate_set_is_not_empty_and_covers_the_named_actions() -> None:
    """Guard against the set being emptied, which would make every test above vacuous."""
    assert len(ALWAYS_ESCALATE) >= 5
    for required in ("update_pricing", "trigger_refund", "update_payment_settings",
                     "update_tax_settings", "update_fulfillment_rules", "inventory_reorder"):
        assert required in ALWAYS_ESCALATE, f"{required} dropped out of ALWAYS_ESCALATE"


def test_tiers_are_ordered_and_the_thresholds_hold() -> None:
    assert score_action("update_payment_settings").tier is RiskTier.CRITICAL
    for action, score in ACTION_RISK.items():
        assessment = score_action(action)
        assert assessment.score >= score, (
            f"{action}: scoring returned {assessment.score}, below its base {score}"
        )


def test_every_assessment_records_why() -> None:
    """An audit entry without a reason is not an audit entry."""
    for action in list(ALWAYS_ESCALATE)[:5]:
        assessment = score_action(action)
        assert assessment.reasons, f"{action}: no reasons recorded"
        assert assessment.to_dict()["requires_approval"] is True
