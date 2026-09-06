"""Deterministic approval policy for the Artemis social growth agent.

This module intentionally performs no network or platform operations. It is a
small reference control that a real server-side adapter can call immediately
before any side effect.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import hmac
import json
from typing import Any, Mapping


class Action(StrEnum):
    ANALYZE = "analyze"
    DRAFT = "draft"
    PUBLISH = "publish"
    SCHEDULE = "schedule"
    SPEND = "spend"
    MESSAGE = "message"
    CONNECT_ACCOUNT = "connect_account"
    PROCESS_PERSONAL_DATA = "process_personal_data"
    PROMOTE_SELF_IMPROVEMENT = "promote_self_improvement"


LOW_RISK_ACTIONS = frozenset({Action.ANALYZE, Action.DRAFT})


@dataclass(frozen=True)
class Approval:
    approval_id: str
    artifact_sha256: str
    actions: frozenset[Action]
    accounts: frozenset[str]
    expires_at: datetime
    maximum_spend_minor: int = 0


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str
    reason: str


def canonical_artifact_hash(artifact: Mapping[str, Any]) -> str:
    """Hash an artifact using stable JSON so approval binds to exact content."""
    serialized = json.dumps(
        artifact, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def authorize(
    *,
    action: Action,
    artifact: Mapping[str, Any],
    account: str | None = None,
    spend_minor: int = 0,
    approval: Approval | None = None,
    now: datetime | None = None,
) -> Decision:
    """Fail closed unless the requested side effect exactly matches approval."""
    if spend_minor < 0:
        return Decision(False, "INVALID_SPEND", "Spend cannot be negative.")
    if action in LOW_RISK_ACTIONS:
        return Decision(True, "LOW_RISK", "Read-only analysis and drafts are allowed.")
    if approval is None:
        return Decision(False, "APPROVAL_REQUIRED", "External actions require approval.")

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        return Decision(False, "INVALID_TIME", "Current time must be timezone-aware.")
    if approval.expires_at.tzinfo is None or current_time >= approval.expires_at:
        return Decision(False, "APPROVAL_EXPIRED", "Approval is expired or invalid.")
    if action not in approval.actions:
        return Decision(False, "ACTION_MISMATCH", "Action is not in the approval scope.")
    if account is None or account not in approval.accounts:
        return Decision(False, "ACCOUNT_MISMATCH", "Account is not in the approval scope.")
    if spend_minor > approval.maximum_spend_minor:
        return Decision(False, "BUDGET_EXCEEDED", "Spend exceeds the approved cap.")

    actual_hash = canonical_artifact_hash(artifact)
    if not hmac.compare_digest(actual_hash, approval.artifact_sha256):
        return Decision(False, "ARTIFACT_CHANGED", "Artifact changed after approval.")
    return Decision(True, "APPROVED", "The exact action is covered by valid approval.")
