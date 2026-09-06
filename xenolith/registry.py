# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""XENOLITH agent registry — the civilization model.

Every actor in the lattice occupies exactly one registry slot describing who it
is, what it may touch, where it may remember, and whether it is still alive:

    codename · domain · role · mission scope · permissions · memory partition
    · status · health · last heartbeat · parent

The registry is the authority on **capability** (does this agent hold this
permission?) and on **liveness** (has it checked in recently?). It deliberately
does not decide whether an action is *safe* — that is :mod:`xenolith.policy`.
Separating the two means a compromised agent with valid permissions still can't
push a high-risk action through without approval.

Permissions are dot-scoped with tail wildcards: ``intel.read`` is granted by
``intel.read``, ``intel.*`` or ``*``, and never by ``intel.readonly``.

Stdlib only.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

from .constants import Domain, RegistryError

#: An agent that has not checked in for this long is considered DEGRADED.
DEFAULT_HEARTBEAT_TTL_SECONDS = 90.0


class AgentStatus(str, Enum):
    """Lifecycle state. Only ``ACTIVE`` agents may act."""

    PROVISIONED = "provisioned"
    ACTIVE = "active"
    DEGRADED = "degraded"
    QUARANTINED = "quarantined"
    RETIRED = "retired"

    @property
    def can_act(self) -> bool:
        return self is AgentStatus.ACTIVE


@dataclass
class AgentRecord:
    """One slot in the agent civilization."""

    codename: str
    domain: Domain
    role: str
    mission_scope: str
    permissions: frozenset[str]
    memory_partition: str
    status: AgentStatus = AgentStatus.PROVISIONED
    last_heartbeat: float | None = None
    health: float = 1.0
    key_fingerprint: str | None = None
    parent: str | None = None
    spawned: tuple[str, ...] = ()
    registered_at: float = field(default_factory=time.time)

    def as_dict(self) -> dict[str, Any]:
        return {
            "codename": self.codename,
            "domain": self.domain.value,
            "role": self.role,
            "mission_scope": self.mission_scope,
            "permissions": sorted(self.permissions),
            "memory_partition": self.memory_partition,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat,
            "health": round(self.health, 3),
            "key_fingerprint": self.key_fingerprint,
            "parent": self.parent,
            "spawned": list(self.spawned),
            "registered_at": self.registered_at,
        }


class AgentRegistry:
    """Registration, capability lookup, liveness, delegation and quarantine."""

    def __init__(self, heartbeat_ttl: float = DEFAULT_HEARTBEAT_TTL_SECONDS) -> None:
        if heartbeat_ttl <= 0:
            raise ValueError("heartbeat_ttl must be positive")
        self._ttl = heartbeat_ttl
        self._agents: dict[str, AgentRecord] = {}

    # ------------------------------------------------------------------ #
    # Registration & lifecycle
    # ------------------------------------------------------------------ #
    def register(
        self,
        codename: str,
        domain: Domain | str,
        role: str,
        mission_scope: str,
        permissions: Iterable[str] = (),
        memory_partition: str | None = None,
        key_fingerprint: str | None = None,
        parent: str | None = None,
    ) -> AgentRecord:
        """Create a slot. Codenames are unique across the whole lattice."""
        codename = _require(codename, "codename")
        if codename in self._agents:
            raise RegistryError(f"codename already registered: {codename}")
        domain = Domain(domain)
        if parent is not None and parent not in self._agents:
            raise RegistryError(f"unknown parent agent: {parent}")

        record = AgentRecord(
            codename=codename,
            domain=domain,
            role=_require(role, "role"),
            mission_scope=_require(mission_scope, "mission_scope"),
            permissions=frozenset(permissions),
            # Default partition is domain-scoped, so an agent that never asks
            # for a partition still cannot read across a domain boundary.
            memory_partition=memory_partition or f"{domain.value}/{codename}",
            key_fingerprint=key_fingerprint,
            parent=parent,
        )
        self._agents[codename] = record
        if parent is not None:
            par = self._agents[parent]
            par.spawned = par.spawned + (codename,)
        return record

    def activate(self, codename: str) -> AgentRecord:
        """Bring an agent online and start its heartbeat clock."""
        record = self.get(codename)
        if record.status is AgentStatus.RETIRED:
            raise RegistryError(f"cannot activate a retired agent: {codename}")
        if record.status is AgentStatus.QUARANTINED:
            raise RegistryError(f"agent is quarantined and must be released first: {codename}")
        record.status = AgentStatus.ACTIVE
        record.last_heartbeat = time.time()
        return record

    def heartbeat(self, codename: str, health: float | None = None) -> AgentRecord:
        """Record a check-in, optionally with a 0.0–1.0 self-reported health."""
        record = self.get(codename)
        if record.status is AgentStatus.RETIRED:
            raise RegistryError(f"retired agent cannot heartbeat: {codename}")
        if record.status is AgentStatus.QUARANTINED:
            # A quarantined agent may still report liveness; it just can't act.
            record.last_heartbeat = time.time()
            return record
        record.last_heartbeat = time.time()
        if health is not None:
            if not 0.0 <= health <= 1.0:
                raise ValueError("health must be between 0.0 and 1.0")
            record.health = health
        if record.status is AgentStatus.DEGRADED and record.health >= 0.5:
            record.status = AgentStatus.ACTIVE
        return record

    def quarantine(self, codename: str, reason: str) -> AgentRecord:
        """Isolate an agent. It keeps its slot and history but cannot act."""
        if not reason.strip():
            raise ValueError("quarantine requires a reason")
        record = self.get(codename)
        record.status = AgentStatus.QUARANTINED
        return record

    def release(self, codename: str) -> AgentRecord:
        """Return a quarantined agent to service."""
        record = self.get(codename)
        if record.status is not AgentStatus.QUARANTINED:
            raise RegistryError(f"agent is not quarantined: {codename}")
        record.status = AgentStatus.ACTIVE
        record.last_heartbeat = time.time()
        return record

    def retire(self, codename: str) -> AgentRecord:
        """Permanently decommission an agent. Terminal state."""
        record = self.get(codename)
        record.status = AgentStatus.RETIRED
        return record

    # ------------------------------------------------------------------ #
    # Delegation
    # ------------------------------------------------------------------ #
    def spawn(
        self,
        parent: str,
        codename: str,
        role: str,
        mission_scope: str,
        permissions: Iterable[str] = (),
    ) -> AgentRecord:
        """Spawn a sub-agent under ``parent``.

        A child can never exceed its parent: requested permissions are
        intersected with the parent's, and the child inherits the parent's
        domain and memory partition prefix. This is what keeps recursive
        delegation from becoming privilege escalation.
        """
        par = self.get(parent)
        if not par.status.can_act:
            raise RegistryError(f"parent must be ACTIVE to spawn: {parent} is {par.status.value}")

        requested = frozenset(permissions)
        granted = frozenset(p for p in requested if _permits(par.permissions, p))
        denied = requested - granted
        if denied:
            raise RegistryError(
                f"sub-agent {codename} requested permissions its parent lacks: {sorted(denied)}"
            )
        return self.register(
            codename=codename,
            domain=par.domain,
            role=role,
            mission_scope=mission_scope,
            permissions=granted,
            memory_partition=f"{par.memory_partition}/{codename}",
            parent=parent,
        )

    # ------------------------------------------------------------------ #
    # Capability & liveness
    # ------------------------------------------------------------------ #
    def has_permission(self, codename: str, permission: str) -> bool:
        """True only if the agent is ACTIVE *and* holds a matching grant."""
        record = self._agents.get(codename)
        if record is None or not record.status.can_act:
            return False
        return _permits(record.permissions, permission)

    def require_permission(self, codename: str, permission: str) -> AgentRecord:
        """Capability check that raises — for call sites that must fail closed."""
        if not self.has_permission(codename, permission):
            raise RegistryError(f"{codename} lacks permission: {permission}")
        return self.get(codename)

    def sweep(self, now: float | None = None) -> tuple[str, ...]:
        """Demote agents whose heartbeat has gone stale.

        Returns the codenames that were demoted, so the caller can log or alert
        on them. Run this before reading health — liveness is only true as of
        the last sweep.
        """
        now = time.time() if now is None else now
        demoted: list[str] = []
        for record in self._agents.values():
            if record.status is not AgentStatus.ACTIVE:
                continue
            last = record.last_heartbeat
            if last is None or now - last > self._ttl:
                record.status = AgentStatus.DEGRADED
                record.health = min(record.health, 0.25)
                demoted.append(record.codename)
        return tuple(sorted(demoted))

    # ------------------------------------------------------------------ #
    # Lookup
    # ------------------------------------------------------------------ #
    def get(self, codename: str) -> AgentRecord:
        try:
            return self._agents[codename]
        except KeyError:
            raise RegistryError(f"unknown agent: {codename}") from None

    def find(self, codename: str) -> AgentRecord | None:
        return self._agents.get(codename)

    def by_domain(self, domain: Domain | str) -> tuple[AgentRecord, ...]:
        domain = Domain(domain)
        return tuple(
            sorted(
                (a for a in self._agents.values() if a.domain is domain),
                key=lambda a: a.codename,
            )
        )

    def all(self) -> tuple[AgentRecord, ...]:
        return tuple(sorted(self._agents.values(), key=lambda a: a.codename))

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, codename: object) -> bool:
        return codename in self._agents

    # ------------------------------------------------------------------ #
    # Reporting
    # ------------------------------------------------------------------ #
    def census(self) -> dict[str, Any]:
        """Population and health roll-up, grouped by domain and status."""
        by_domain: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for record in self._agents.values():
            by_domain[record.domain.value] = by_domain.get(record.domain.value, 0) + 1
            by_status[record.status.value] = by_status.get(record.status.value, 0) + 1
        actionable = [a for a in self._agents.values() if a.status.can_act]
        mean_health = round(sum(a.health for a in actionable) / len(actionable), 3) if actionable else 0.0
        return {
            "population": len(self._agents),
            "actionable": len(actionable),
            "mean_health": mean_health,
            "by_domain": dict(sorted(by_domain.items())),
            "by_status": dict(sorted(by_status.items())),
        }


def _permits(grants: frozenset[str], permission: str) -> bool:
    """Match ``permission`` against dot-scoped grants with tail wildcards."""
    if "*" in grants or permission in grants:
        return True
    parts = permission.split(".")
    for idx in range(len(parts) - 1, 0, -1):
        if ".".join(parts[:idx]) + ".*" in grants:
            return True
    return False


def _require(value: str, label: str) -> str:
    if not value or not value.strip():
        raise RegistryError(f"{label} is required")
    return value.strip()
