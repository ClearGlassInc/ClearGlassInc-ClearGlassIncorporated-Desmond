from datetime import datetime, timedelta, timezone

from agents.artemis_social_growth.policy import (
    Action,
    Approval,
    authorize,
    canonical_artifact_hash,
)


NOW = datetime(2026, 7, 26, 12, tzinfo=timezone.utc)
ARTIFACT = {"content_id": "post-001", "copy": "Evidence-supported draft"}
ACCOUNT = "linkedin:clearglassinc-artemis"


def approval(**overrides: object) -> Approval:
    values = {
        "approval_id": "approval-001",
        "artifact_sha256": canonical_artifact_hash(ARTIFACT),
        "actions": frozenset({Action.PUBLISH, Action.SPEND}),
        "accounts": frozenset({ACCOUNT}),
        "expires_at": NOW + timedelta(hours=1),
        "maximum_spend_minor": 2_500,
    }
    values.update(overrides)
    return Approval(**values)  # type: ignore[arg-type]


def test_drafts_are_allowed_without_approval() -> None:
    decision = authorize(action=Action.DRAFT, artifact=ARTIFACT, now=NOW)
    assert decision.allowed
    assert decision.code == "LOW_RISK"


def test_external_action_fails_closed_without_approval() -> None:
    decision = authorize(
        action=Action.PUBLISH, artifact=ARTIFACT, account=ACCOUNT, now=NOW
    )
    assert not decision.allowed
    assert decision.code == "APPROVAL_REQUIRED"


def test_exact_approved_artifact_can_publish() -> None:
    decision = authorize(
        action=Action.PUBLISH,
        artifact=ARTIFACT,
        account=ACCOUNT,
        approval=approval(),
        now=NOW,
    )
    assert decision.allowed
    assert decision.code == "APPROVED"


def test_edit_after_approval_is_blocked() -> None:
    changed = {**ARTIFACT, "copy": "Unapproved edit"}
    decision = authorize(
        action=Action.PUBLISH,
        artifact=changed,
        account=ACCOUNT,
        approval=approval(),
        now=NOW,
    )
    assert not decision.allowed
    assert decision.code == "ARTIFACT_CHANGED"


def test_expired_approval_and_excess_spend_are_blocked() -> None:
    expired = authorize(
        action=Action.PUBLISH,
        artifact=ARTIFACT,
        account=ACCOUNT,
        approval=approval(expires_at=NOW),
        now=NOW,
    )
    excess = authorize(
        action=Action.SPEND,
        artifact=ARTIFACT,
        account=ACCOUNT,
        spend_minor=2_501,
        approval=approval(),
        now=NOW,
    )
    assert (expired.allowed, expired.code) == (False, "APPROVAL_EXPIRED")
    assert (excess.allowed, excess.code) == (False, "BUDGET_EXCEEDED")
