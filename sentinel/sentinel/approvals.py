# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Percival approvals — signed, single-use, expiring human approvals.

The v10 boundary doctrine requires that external or sensitive actions carry a
**signed, single-use approval** — an approval that authorizes exactly one action,
cannot be replayed, and expires. This is the redeemable token the Escalation Gate
issues once a human signs off, and that the executor must present before acting.

Guarantees (all fail-closed):

  * **Bound.** An approval authorizes one (action_kind, scope, subject) triple.
    Presenting it for anything else is denied — you cannot repurpose an approval
    for a "publish copy" grant into a "move money" action.
  * **Single-use.** Redeeming marks it spent; a second redemption is denied
    (replay protection).
  * **Expiring.** Past its TTL, it is dead.
  * **Signed.** Each token is HMAC-signed over its bound fields, so it cannot be
    forged or its fields tampered with. Unknown/altered tokens are denied.
  * **Traceable.** Every approval carries a correlation/trace id so allow, deny,
    and redeem events can be stitched across boundaries.

Stdlib only (`hmac`, `hashlib`, `secrets`, `time`), matching the other governed
sentinel modules.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from typing import Optional


def new_trace_id() -> str:
    """A fresh correlation/trace id for stitching events across boundaries."""
    return "tr_" + secrets.token_hex(8)


def _nonce() -> str:
    return secrets.token_hex(16)


@dataclass(frozen=True)
class Approval:
    """A signed, single-use authorization for exactly one action."""

    token: str                    # nonce identifying this approval
    action_kind: str              # e.g. "external_send", "modify_system"
    scope: str                    # the capability/lane it applies to
    subject: str                  # the concrete target (payload id, path, …)
    approver: str                 # human who signed it
    trace_id: str
    issued_ts: float
    expires_ts: float
    signature: str

    def bound_fields(self) -> str:
        """The exact string the signature commits to."""
        return "|".join([
            self.token, self.action_kind, self.scope, self.subject,
            self.approver, self.trace_id, f"{self.issued_ts:.6f}", f"{self.expires_ts:.6f}",
        ])


@dataclass
class RedeemResult:
    ok: bool
    reason: str
    trace_id: Optional[str] = None


class ApprovalGate:
    """Issues and redeems signed, single-use approvals.

    Parameters
    ----------
    secret:
        HMAC key. Generated randomly if omitted (per-process), so tokens issued
        by one gate cannot be redeemed by another — approvals do not leak across
        trust boundaries.
    """

    def __init__(self, secret: Optional[bytes] = None) -> None:
        self._secret = secret or secrets.token_bytes(32)
        self._issued: dict[str, Approval] = {}
        self._redeemed: set[str] = set()

    def _sign(self, payload: str) -> str:
        return hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()

    # ------------------------------------------------------------------ #
    # issue
    # ------------------------------------------------------------------ #
    def issue(
        self,
        action_kind: str,
        scope: str,
        *,
        subject: str,
        approver: str,
        ttl_seconds: float = 300.0,
        trace_id: Optional[str] = None,
        now: Optional[float] = None,
    ) -> Approval:
        """Mint a signed, single-use approval for one (action, scope, subject)."""
        if not approver or not approver.strip():
            raise ValueError("approver (human signer) is required")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        ts = time.time() if now is None else now
        token = _nonce()
        tid = trace_id or new_trace_id()
        unsigned = Approval(
            token=token, action_kind=action_kind, scope=scope, subject=subject,
            approver=approver.strip(), trace_id=tid,
            issued_ts=ts, expires_ts=ts + ttl_seconds, signature="",
        )
        signed = Approval(**{**unsigned.__dict__, "signature": self._sign(unsigned.bound_fields())})
        self._issued[token] = signed
        return signed

    # ------------------------------------------------------------------ #
    # redeem (single-use, fail-closed)
    # ------------------------------------------------------------------ #
    def redeem(
        self,
        token: str,
        action_kind: str,
        scope: str,
        subject: str,
        *,
        now: Optional[float] = None,
    ) -> RedeemResult:
        """Consume an approval for a specific action. Any mismatch, expiry,
        forgery, or reuse is denied. On success the token is spent."""
        approval = self._issued.get(token)
        if approval is None:
            return RedeemResult(False, "unknown approval token")
        if token in self._redeemed:
            return RedeemResult(False, "approval already redeemed (replay)", approval.trace_id)

        # Verify signature first — a tampered token is not trusted for anything.
        expected = self._sign(approval.bound_fields())
        if not hmac.compare_digest(expected, approval.signature):
            return RedeemResult(False, "invalid signature", approval.trace_id)

        ts = time.time() if now is None else now
        if ts > approval.expires_ts:
            return RedeemResult(False, "approval expired", approval.trace_id)

        # Bound to exactly one action/scope/subject.
        if (action_kind, scope, subject) != (approval.action_kind, approval.scope, approval.subject):
            return RedeemResult(
                False,
                "approval does not authorize this action/scope/subject",
                approval.trace_id,
            )

        self._redeemed.add(token)  # single-use: spend it
        return RedeemResult(True, "approved", approval.trace_id)

    def is_spent(self, token: str) -> bool:
        return token in self._redeemed
