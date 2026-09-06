# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Deterministic policy and signed approval controls."""
from __future__ import annotations

import base64
import fnmatch
import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .models import (
    ApprovalChallenge,
    ApprovalGrant,
    CapabilitySpec,
    ExecutionContext,
    PolicyDecision,
    RiskLevel,
)


def arguments_digest(arguments: dict[str, Any]) -> str:
    payload = json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class PolicyResult:
    decision: PolicyDecision
    reason: str


@dataclass(slots=True)
class AgentPolicy:
    """Fail-closed policy with role and glob-based overrides."""

    denied_capabilities: set[str] = field(default_factory=set)
    approval_capabilities: set[str] = field(default_factory=set)
    privileged_roles: set[str] = field(default_factory=lambda: {"operator", "admin"})
    risk_decisions: dict[RiskLevel, PolicyDecision] = field(
        default_factory=lambda: {
            RiskLevel.SAFE: PolicyDecision.ALLOW,
            RiskLevel.READ: PolicyDecision.ALLOW,
            RiskLevel.WRITE: PolicyDecision.REQUIRE_APPROVAL,
            RiskLevel.EXTERNAL: PolicyDecision.REQUIRE_APPROVAL,
            RiskLevel.DESTRUCTIVE: PolicyDecision.DENY,
            RiskLevel.FINANCIAL: PolicyDecision.DENY,
        }
    )

    def evaluate(self, spec: CapabilitySpec, context: ExecutionContext) -> PolicyResult:
        if self._matches(spec.name, self.denied_capabilities):
            return PolicyResult(PolicyDecision.DENY, "Capability denied by explicit policy")
        if self._matches(spec.name, self.approval_capabilities):
            return PolicyResult(
                PolicyDecision.REQUIRE_APPROVAL,
                "Capability requires explicit approval",
            )

        decision = self.risk_decisions.get(spec.risk, PolicyDecision.DENY)
        if decision is PolicyDecision.REQUIRE_APPROVAL and not (
            context.roles & self.privileged_roles
        ):
            return PolicyResult(
                decision,
                f"Risk level '{spec.risk}' requires a privileged operator",
            )
        if decision is PolicyDecision.DENY:
            return PolicyResult(decision, f"Risk level '{spec.risk}' is disabled by policy")
        return PolicyResult(decision, f"Risk level '{spec.risk}' accepted")

    @staticmethod
    def _matches(name: str, patterns: set[str]) -> bool:
        return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


class ApprovalManager:
    """Issues durable, one-use, HMAC approvals bound to actor and arguments."""

    def __init__(
        self,
        secret: str | bytes | None = None,
        ttl_seconds: int = 300,
        state_path: str | Path | None = None,
    ) -> None:
        raw_secret = secret.encode("utf-8") if isinstance(secret, str) else secret
        self._secret = raw_secret or secrets.token_bytes(32)
        self._ttl = timedelta(seconds=ttl_seconds)
        self._state_path = Path(state_path) if state_path is not None else None
        self._challenges: dict[str, ApprovalChallenge] = {}
        self._consumed: set[str] = set()
        self._lock = threading.RLock()
        if self._state_path is not None:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize_state()

    def challenge(
        self,
        capability: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
        reason: str,
    ) -> ApprovalChallenge:
        item = ApprovalChallenge(
            capability=capability,
            arguments_digest=arguments_digest(arguments),
            actor=context.actor,
            reason=reason,
            expires_at=datetime.now(UTC) + self._ttl,
        )
        with self._lock:
            self._challenges[item.approval_id] = item
            self._save_challenge(item)
        return item

    def grant(self, approval_id: str) -> ApprovalGrant:
        challenge = self._get_live_challenge(approval_id)
        claims = {
            "approval_id": approval_id,
            "capability": challenge.capability,
            "arguments_digest": challenge.arguments_digest,
            "actor": challenge.actor,
            "expires": int(challenge.expires_at.timestamp()),
        }
        payload = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
        encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        signature = hmac.new(self._secret, encoded.encode("ascii"), hashlib.sha256).hexdigest()
        return ApprovalGrant(
            approval_id=approval_id,
            token=f"{encoded}.{signature}",
            expires_at=challenge.expires_at,
        )

    def validate_and_consume(
        self,
        token: str,
        capability: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
    ) -> bool:
        try:
            encoded, signature = token.split(".", 1)
            expected = hmac.new(
                self._secret,
                encoded.encode("ascii"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return False

            padding = "=" * (-len(encoded) % 4)
            claims = json.loads(base64.urlsafe_b64decode(encoded + padding))
            approval_id = str(claims["approval_id"])
            challenge = self._get_live_challenge(approval_id)
            valid = (
                int(claims["expires"]) >= int(datetime.now(UTC).timestamp())
                and claims["capability"] == challenge.capability == capability
                and claims["arguments_digest"]
                == challenge.arguments_digest
                == arguments_digest(arguments)
                and claims["actor"] == challenge.actor == context.actor
            )
            return valid and self._consume_challenge(approval_id)
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            return False

    def _get_live_challenge(self, approval_id: str) -> ApprovalChallenge:
        with self._lock:
            challenge = self._challenges.get(approval_id) or self._load_challenge(approval_id)
            if challenge is None or challenge.expires_at < datetime.now(UTC):
                self._delete_challenge(approval_id)
                raise KeyError(approval_id)
            self._challenges[approval_id] = challenge
            return challenge

    def _consume_challenge(self, approval_id: str) -> bool:
        with self._lock:
            if self._state_path is not None:
                with self._connection() as connection:
                    cursor = connection.execute(
                        "DELETE FROM approval_challenges WHERE approval_id=?",
                        (approval_id,),
                    )
                    consumed = cursor.rowcount == 1
            else:
                consumed = approval_id not in self._consumed
                if consumed:
                    self._consumed.add(approval_id)
            if consumed:
                self._challenges.pop(approval_id, None)
            return consumed

    def _initialize_state(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_challenges(
                    approval_id TEXT PRIMARY KEY,
                    capability TEXT NOT NULL,
                    arguments_digest TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_approval_expiry "
                "ON approval_challenges(expires_at)"
            )
            connection.execute(
                "DELETE FROM approval_challenges WHERE expires_at < ?",
                (datetime.now(UTC).isoformat(),),
            )

    def _save_challenge(self, challenge: ApprovalChallenge) -> None:
        if self._state_path is None:
            return
        with self._connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO approval_challenges(
                    approval_id, capability, arguments_digest, actor, reason, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    challenge.approval_id,
                    challenge.capability,
                    challenge.arguments_digest,
                    challenge.actor,
                    challenge.reason,
                    challenge.expires_at.isoformat(),
                ),
            )

    def _load_challenge(self, approval_id: str) -> ApprovalChallenge | None:
        if self._state_path is None:
            return None
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT capability, arguments_digest, actor, reason, expires_at
                FROM approval_challenges WHERE approval_id=?
                """,
                (approval_id,),
            ).fetchone()
        if row is None:
            return None
        return ApprovalChallenge(
            approval_id=approval_id,
            capability=row[0],
            arguments_digest=row[1],
            actor=row[2],
            reason=row[3],
            expires_at=datetime.fromisoformat(row[4]),
        )

    def _delete_challenge(self, approval_id: str) -> None:
        self._challenges.pop(approval_id, None)
        if self._state_path is not None:
            with self._connection() as connection:
                connection.execute(
                    "DELETE FROM approval_challenges WHERE approval_id=?",
                    (approval_id,),
                )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        if self._state_path is None:
            raise RuntimeError("Persistent approval state is not configured")
        connection = sqlite3.connect(self._state_path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        try:
            with connection:
                yield connection
        finally:
            connection.close()
