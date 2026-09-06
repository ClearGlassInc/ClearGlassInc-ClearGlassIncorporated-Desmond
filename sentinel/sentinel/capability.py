# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Percival capability layer — deny-by-default object-capability gating.

The Percival control-plane model grants power explicitly, per task, rather than
assuming it from role or context. This module is that gate: a task may only use
a capability that has been explicitly granted, and only up to the tier it was
granted at. Anything ungranted, or requested above its granted tier, is denied —
fail-closed.

Approval tiers (increasing power):

    READ_ONLY  — inspect / analyze / summarize; no changes
    DRAFT      — produce a proposed change for human review; still no live effect
    CHANGE     — apply a reversible, non-production change (needs approval grant)
    DEPLOY     — production / irreversible / money-moving (needs explicit confirm)

Policy always wins: :class:`CapabilityBroker` never infers a grant it was not
given, and a missing grant is a denial, not an error to route around.

Stdlib only, to match the other governed sentinel modules.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Tier(IntEnum):
    """Ordered approval tiers. Higher = more power required."""

    READ_ONLY = 0
    DRAFT = 1
    CHANGE = 2
    DEPLOY = 3


# Default tier required for a given action kind. Unknown kinds fail closed to the
# highest tier (DEPLOY) so nothing sensitive slips through as low-risk.
_ACTION_TIER = {
    "read": Tier.READ_ONLY,
    "analyze": Tier.READ_ONLY,
    "summarize": Tier.READ_ONLY,
    "recall": Tier.READ_ONLY,
    "draft": Tier.DRAFT,
    "propose": Tier.DRAFT,
    "content_edit": Tier.CHANGE,
    "catalog_edit": Tier.CHANGE,
    "config_change": Tier.CHANGE,
    "pricing_change": Tier.DEPLOY,
    "payment": Tier.DEPLOY,
    "refund": Tier.DEPLOY,
    "fulfillment": Tier.DEPLOY,
    "money_movement": Tier.DEPLOY,
    "production_deploy": Tier.DEPLOY,
    "external_send": Tier.DEPLOY,
    "credential_access": Tier.DEPLOY,
    "destructive": Tier.DEPLOY,
}


def required_tier(action_kind: str) -> Tier:
    """Tier an action kind demands. Unknown kinds fail closed to DEPLOY."""
    return _ACTION_TIER.get(action_kind, Tier.DEPLOY)


@dataclass(frozen=True)
class Grant:
    """An explicit capability grant: this capability, up to this tier."""

    capability: str
    max_tier: Tier
    reason: str = ""


@dataclass(frozen=True)
class Decision:
    allowed: bool
    capability: str
    requested_tier: Tier
    reason: str


class CapabilityBroker:
    """Holds explicit grants and decides whether a task may act.

    Deny-by-default: with no grants, every request is denied. A grant authorizes
    a named capability up to a maximum tier; requests above that tier are denied.
    """

    def __init__(self) -> None:
        self._grants: dict[str, Grant] = {}

    def grant(self, capability: str, max_tier: Tier, *, reason: str = "") -> Grant:
        """Explicitly authorize `capability` up to `max_tier`."""
        if not capability or not capability.strip():
            raise ValueError("capability name is required")
        g = Grant(capability.strip(), Tier(max_tier), reason.strip())
        self._grants[g.capability] = g
        return g

    def revoke(self, capability: str) -> bool:
        """Remove a grant. Returns False if it wasn't present."""
        return self._grants.pop(capability, None) is not None

    def check(self, capability: str, requested_tier: Tier) -> Decision:
        """Decide whether `capability` may act at `requested_tier`. Fail-closed."""
        requested_tier = Tier(requested_tier)
        grant = self._grants.get(capability)
        if grant is None:
            return Decision(False, capability, requested_tier,
                            "denied: no explicit grant (deny-by-default)")
        if requested_tier > grant.max_tier:
            return Decision(False, capability, requested_tier,
                            f"denied: requested {requested_tier.name} exceeds granted "
                            f"{grant.max_tier.name}")
        return Decision(True, capability, requested_tier,
                        f"allowed: within granted {grant.max_tier.name}")

    def authorize_action(self, capability: str, action_kind: str) -> Decision:
        """Convenience: check a named action kind at its required tier."""
        return self.check(capability, required_tier(action_kind))
