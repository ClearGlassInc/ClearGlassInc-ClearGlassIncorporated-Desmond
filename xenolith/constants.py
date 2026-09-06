# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Shared vocabulary for the XENOLITH lattice.

Every module speaks these types, which is what lets independently-built
subsystems interlock: one domain enum, one risk ladder, one error family, one
canonical serializer for anything that gets hashed or signed.

Stdlib only.
"""
from __future__ import annotations

import json
from enum import Enum
from typing import Any, Mapping


class LatticeError(Exception):
    """Base class for every XENOLITH failure. Callers may catch this alone."""


class PolicyViolation(LatticeError):
    """A gated action was attempted without the authority to perform it."""


class IdentityError(LatticeError):
    """An identity, signature, or replay check failed."""


class RegistryError(LatticeError):
    """An agent record was missing, duplicated, or in the wrong state."""


class Domain(str, Enum):
    """The six sovereign domains of the lattice.

    Domains are memory and authority boundaries, not just labels: an agent's
    domain constrains which memory partitions it may read and which event
    types it may publish.
    """

    EXECUTIVE = "executive"
    INTELLIGENCE = "intelligence"
    CYBERSECURITY = "cybersecurity"
    THREAT_INTEL = "threat-intel"
    OPERATIONS = "operations"
    AUTONOMY = "autonomy"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


class RiskTier(str, Enum):
    """Risk ladder shared with the ClearGlass commerce control plane.

    ``LOW`` auto-executes and logs. ``MEDIUM`` queues for approval.
    ``HIGH`` and ``CRITICAL`` are blocked until an approval is recorded —
    there is no code path that bypasses this.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_score(cls, score: int) -> "RiskTier":
        """Map a 0–100 risk score onto the ladder.

        Boundaries match ``clearglass-commerce/control-plane/app/governance.py``
        so a risk score means the same thing in both systems.
        """
        if score >= 85:
            return cls.CRITICAL
        if score >= 60:
            return cls.HIGH
        if score >= 30:
            return cls.MEDIUM
        return cls.LOW

    @property
    def requires_approval(self) -> bool:
        """True when an action at this tier may not auto-execute."""
        return self in (RiskTier.MEDIUM, RiskTier.HIGH, RiskTier.CRITICAL)

    @property
    def blocks_until_approved(self) -> bool:
        """True when the action is hard-blocked, not merely queued."""
        return self in (RiskTier.HIGH, RiskTier.CRITICAL)


#: Ordering helper for sorting/comparing tiers without exposing raw ints.
RISK_ORDER: dict[RiskTier, int] = {
    RiskTier.LOW: 0,
    RiskTier.MEDIUM: 1,
    RiskTier.HIGH: 2,
    RiskTier.CRITICAL: 3,
}


def canonical(payload: Mapping[str, Any]) -> bytes:
    """Serialize a mapping deterministically for hashing and signing.

    Two structurally equal payloads must produce byte-identical output on every
    platform and Python build, or signatures and ledger hashes stop verifying.
    Sorted keys, no insignificant whitespace, UTF-8, no ASCII escaping.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
