# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Percival identity & authority layer — scoped, sponsor-owned agent instances.

The v7 control doctrine: every Percival instance has a distinct identity, a
named human sponsor, and a defined purpose. It knows what it may touch, what it
may not, and when it must stop. Default authority is **read-only**; anything
above that requires an explicit, scoped capability grant.

This module binds an :class:`AgentIdentity` to the deny-by-default
:class:`sentinel.capability.CapabilityBroker`, so authority always traces back
to an identity, a sponsor, and a scope — never inferred from context.

Stdlib only, to match the other governed sentinel modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .capability import CapabilityBroker, Tier


@dataclass
class AgentIdentity:
    """A scoped, sponsor-owned Percival instance.

    Parameters
    ----------
    instance_id:
        Distinct identifier for this instance.
    sponsor:
        The human owner accountable for it. Required — an unsponsored instance
        is not permitted.
    purpose:
        What this instance exists to do. Required.
    allowed_scopes:
        Capabilities this instance may touch at all (deny-by-default: anything
        not listed is unavailable).
    denied_scopes:
        Explicit denials. A denied scope wins over an allowed one.
    default_tier:
        Authority floor for allowed scopes. Defaults to READ_ONLY; write /
        deploy tiers must be elevated explicitly and per-scope.
    """

    instance_id: str
    sponsor: str
    purpose: str
    allowed_scopes: frozenset[str] = field(default_factory=frozenset)
    denied_scopes: frozenset[str] = field(default_factory=frozenset)
    default_tier: Tier = Tier.READ_ONLY
    active: bool = True

    def __post_init__(self) -> None:
        if not self.instance_id or not self.instance_id.strip():
            raise ValueError("instance_id is required")
        if not self.sponsor or not self.sponsor.strip():
            raise ValueError("sponsor (human owner) is required — no unsponsored instances")
        if not self.purpose or not self.purpose.strip():
            raise ValueError("purpose is required")
        self.allowed_scopes = frozenset(self.allowed_scopes)
        self.denied_scopes = frozenset(self.denied_scopes)
        self.default_tier = Tier(self.default_tier)

    # ------------------------------------------------------------------ #
    # Scope checks (deny-by-default; explicit denials win)
    # ------------------------------------------------------------------ #
    def may_touch(self, scope: str) -> bool:
        """True only if `scope` is explicitly allowed, not denied, and active."""
        if not self.active:
            return False
        if scope in self.denied_scopes:
            return False
        return scope in self.allowed_scopes

    def stop(self) -> None:
        """Halt the instance. After stop, it may touch nothing (fail-closed)."""
        self.active = False

    # ------------------------------------------------------------------ #
    # Bind to the capability broker
    # ------------------------------------------------------------------ #
    def new_broker(self) -> CapabilityBroker:
        """Return a CapabilityBroker seeded from this identity.

        Each allowed (and not-denied) scope is granted at the identity's
        `default_tier` — READ_ONLY by convention, so write/deploy authority must
        be elevated deliberately. A stopped instance grants nothing.
        """
        broker = CapabilityBroker()
        if not self.active:
            return broker
        for scope in sorted(self.allowed_scopes):
            if scope in self.denied_scopes:
                continue
            broker.grant(scope, self.default_tier, reason=f"identity:{self.instance_id} sponsor:{self.sponsor}")
        return broker

    def describe(self) -> dict[str, object]:
        """Human/audit-readable summary of who owns this and what it may do."""
        return {
            "instance_id": self.instance_id,
            "sponsor": self.sponsor,
            "purpose": self.purpose,
            "active": self.active,
            "default_tier": self.default_tier.name,
            "allowed_scopes": sorted(self.allowed_scopes),
            "denied_scopes": sorted(self.denied_scopes),
        }
