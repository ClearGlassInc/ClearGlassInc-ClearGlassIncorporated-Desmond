# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Percival Policy Governor — sovereign, deny-all-by-default request enforcement.

This is the v8 control-plane keystone: the single gate every inbound request
passes before routing. It validates the request against the machine-readable
capability schema (`sentinel/schemas/capabilities.json`), maps the requested
`action_scope` to a capability tier, checks it against the caller's scoped
:class:`~sentinel.identity.AgentIdentity` and
:class:`~sentinel.capability.CapabilityBroker`, and enforces the policy matrix:

    * Deny-all by default — anything not explicitly permitted is denied.
    * Deny rules override allow rules.
    * High-power scopes (external execution / system modification) are blocked
      pending human escalation, never auto-run.
    * Fail closed on any ambiguity, missing field, or schema violation.

Every decision is written to the append-only, hash-chained audit ledger.

Stdlib only (schema validation is hand-rolled) so it runs in minimal CI
environments alongside the other governed sentinel modules.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .approvals import new_trace_id
from .audit import AuditLog
from .capability import CapabilityBroker, Tier
from .identity import AgentIdentity

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "capabilities.json"

# action_scope (schema enum) -> capability tier required to perform it.
_SCOPE_TIER = {
    "read_only": Tier.READ_ONLY,
    "draft_proposal": Tier.DRAFT,
    "execute_internal": Tier.CHANGE,
    "execute_external": Tier.DEPLOY,
    "modify_system": Tier.DEPLOY,
}

# Scopes that must never auto-run; they are blocked pending human escalation.
_ESCALATION_SCOPES = frozenset({"execute_external", "modify_system"})

_VALID_LANES = frozenset({"strategy", "architecture", "implementation", "security", "operations"})

_DEFAULT_CONFIDENCE_THRESHOLD = 0.95


@dataclass
class GovernorDecision:
    allowed: bool
    escalate: bool
    reason: str
    action_scope: str = ""
    required_tier: Optional[Tier] = None
    lanes: list[str] = field(default_factory=list)
    trace_id: str = ""            # correlation id stitched across the boundary

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "escalate": self.escalate,
            "reason": self.reason,
            "action_scope": self.action_scope,
            "required_tier": self.required_tier.name if self.required_tier is not None else None,
            "lanes": list(self.lanes),
            "trace_id": self.trace_id,
        }


class PolicyViolation(Exception):
    """Raised only for programming errors; policy denials are returned, not raised."""


class PolicyGovernor:
    """Sovereign enforcer. Constructed with the caller identity + its broker."""

    def __init__(
        self,
        identity: AgentIdentity,
        broker: Optional[CapabilityBroker] = None,
        *,
        audit: Optional[AuditLog] = None,
        schema_path: Optional[Path | str] = None,
    ) -> None:
        self.identity = identity
        self.broker = broker if broker is not None else identity.new_broker()
        self.audit = audit or AuditLog()
        self.schema = json.loads(Path(schema_path or _SCHEMA_PATH).read_text())
        # Fail-closed audit sync (v9): if the audit ledger becomes unavailable,
        # the governor transitions to deny-all. Auditability is a precondition
        # for action — an un-loggable decision must not proceed.
        self.degraded = False

    # ------------------------------------------------------------------ #
    # Schema validation (hand-rolled subset of draft-07: required/enum/type)
    # ------------------------------------------------------------------ #
    def validate_request(self, request: dict[str, Any]) -> Optional[str]:
        """Return an error string if the request violates the schema, else None."""
        if not isinstance(request, dict):
            return "request must be an object"
        for key in self.schema.get("required", []):
            if key not in request:
                return f"missing required field: {key}"

        ctx = request.get("request_context")
        if not isinstance(ctx, dict):
            return "request_context must be an object"
        for key in ("mission_id", "auth_token"):
            if not ctx.get(key):
                return f"request_context.{key} is required"
        urgency = ctx.get("urgency_level")
        if urgency is not None and not (isinstance(urgency, int) and 1 <= urgency <= 5):
            return "request_context.urgency_level must be an integer in [1, 5]"

        scope = request.get("action_scope")
        if scope not in _SCOPE_TIER:
            return f"action_scope must be one of {sorted(_SCOPE_TIER)}"

        lanes = request.get("target_lane")
        if not isinstance(lanes, list) or not lanes:
            return "target_lane must be a non-empty array"
        for lane in lanes:
            if lane not in _VALID_LANES:
                return f"invalid lane {lane!r}; valid: {sorted(_VALID_LANES)}"

        threshold = request.get("confidence_threshold", _DEFAULT_CONFIDENCE_THRESHOLD)
        if not isinstance(threshold, (int, float)) or not (0.0 <= threshold <= 1.0):
            return "confidence_threshold must be a number in [0.0, 1.0]"
        return None

    # ------------------------------------------------------------------ #
    # The gate
    # ------------------------------------------------------------------ #
    def evaluate(self, request: dict[str, Any], *, confidence: float = 1.0,
                 trace_id: Optional[str] = None) -> GovernorDecision:
        """Decide a request. Deny-all default; deny overrides allow; fail closed.

        A correlation/trace id is stitched onto the decision and its audit entry.
        Pass an inbound `trace_id` to continue a caller's trace across the
        boundary; one is generated when absent (never fabricated data — it is an
        opaque correlation handle)."""
        tid = trace_id or new_trace_id()
        # Fail-closed audit sync: once the ledger is unreachable, deny everything
        # until it recovers. This decision itself cannot be audited, so return it
        # directly without attempting another (failing) write.
        if self.degraded:
            return GovernorDecision(
                False, True,
                "DENY: audit ledger unavailable — governor degraded to deny-all (incident)",
                str(request.get("action_scope", "")), trace_id=tid,
            )

        err = self.validate_request(request)
        if err is not None:
            return self._deny(f"schema violation: {err}", request.get("action_scope", ""), trace_id=tid)

        scope = str(request["action_scope"])
        required = _SCOPE_TIER[scope]
        lanes = list(request["target_lane"])
        threshold = float(request.get("confidence_threshold", _DEFAULT_CONFIDENCE_THRESHOLD))

        # Identity must be active.
        if not self.identity.active:
            return self._deny("identity is stopped (fail-closed)", scope, required, lanes, trace_id=tid)

        # EvalOps: confidence below the request's threshold downgrades — never
        # ship a low-confidence answer as if it were execution-grade.
        if confidence < threshold:
            return self._deny(
                f"confidence {confidence:.2f} below threshold {threshold:.2f} — downgraded to verification",
                scope, required, lanes, trace_id=tid,
            )

        # Every lane must be an allowed (non-denied) scope for this identity, and
        # the broker must authorize it at the required tier. Deny wins.
        for lane in lanes:
            if not self.identity.may_touch(lane):
                return self._deny(f"lane {lane!r} not in identity scope (deny-by-default)",
                                  scope, required, lanes, trace_id=tid)
            decision = self.broker.check(lane, required)
            if not decision.allowed:
                return self._deny(f"lane {lane!r}: {decision.reason}", scope, required, lanes, trace_id=tid)

        # High-power scopes are blocked pending human escalation, never auto-run.
        if scope in _ESCALATION_SCOPES:
            return self._escalate(scope, required, lanes, trace_id=tid)

        return self._allow(scope, required, lanes, trace_id=tid)

    # ------------------------------------------------------------------ #
    # Decision helpers (each writes an audit entry)
    # ------------------------------------------------------------------ #
    def _record(self, decision: GovernorDecision) -> GovernorDecision:
        try:
            self.audit.record(
                actor=f"governor:{self.identity.instance_id}",
                action="evaluate",
                detail=decision.as_dict(),
            )
        except Exception:  # noqa: BLE001 — any audit failure trips fail-closed
            # The action could not be logged. Auditability is mandatory, so the
            # governor degrades to deny-all and this request is denied too.
            self.degraded = True
            return GovernorDecision(
                False, True,
                "DENY: audit write failed — governor degraded to deny-all (incident)",
                decision.action_scope, decision.required_tier, decision.lanes,
                trace_id=decision.trace_id,
            )
        return decision

    def _deny(self, reason: str, scope: str, tier: Optional[Tier] = None,
              lanes: Optional[list[str]] = None, *, trace_id: str = "") -> GovernorDecision:
        return self._record(GovernorDecision(False, False, f"DENY: {reason}", scope, tier, lanes or [], trace_id))

    def _escalate(self, scope: str, tier: Tier, lanes: list[str], *, trace_id: str = "") -> GovernorDecision:
        return self._record(GovernorDecision(
            False, True, f"ESCALATE: {scope} requires human approval before execution",
            scope, tier, lanes, trace_id))

    def _allow(self, scope: str, tier: Tier, lanes: list[str], *, trace_id: str = "") -> GovernorDecision:
        return self._record(GovernorDecision(
            True, False, f"ALLOW: within scope at {tier.name}", scope, tier, lanes, trace_id))

    def verify(self) -> bool:
        """True if the audit chain is intact."""
        return self.audit.verify()
