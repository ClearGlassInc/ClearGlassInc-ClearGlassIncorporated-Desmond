# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""XENOLITH memory fabric — partitioned, least-privilege agent memory.

Agent memory is a security boundary, not a cache. A partition is a path
(``cybersecurity/BASTION/subtask-3``) and access is decided structurally:

* An agent may always read and write **its own** partition and anything
  beneath it — a parent can see what its sub-agents remembered.
* Reading **outside** that subtree requires an explicit grant, and grants are
  read-only. There is no cross-partition write, ever, so one compromised agent
  cannot poison a sibling's memory.
* Every record carries provenance (who wrote it, when, with what confidence)
  and an optional TTL, because stale intelligence that looks fresh is worse
  than no intelligence.

Stdlib only.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Iterator

from .constants import LatticeError


class MemoryAccessError(LatticeError):
    """An agent reached outside its memory boundary."""


@dataclass
class MemoryRecord:
    """One remembered fact, with provenance."""

    key: str
    value: Any
    partition: str
    author: str
    confidence: float = 1.0
    written_at: float = field(default_factory=time.time)
    expires_at: float | None = None

    def expired(self, now: float | None = None) -> bool:
        if self.expires_at is None:
            return False
        return (time.time() if now is None else now) >= self.expires_at

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "partition": self.partition,
            "author": self.author,
            "confidence": round(self.confidence, 3),
            "written_at": self.written_at,
            "expires_at": self.expires_at,
        }


class MemoryFabric:
    """Partitioned key–value memory with structural access control."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, MemoryRecord]] = {}
        self._grants: dict[str, set[str]] = {}

    # ------------------------------------------------------------------ #
    # Access control
    # ------------------------------------------------------------------ #
    def grant_read(self, partition: str, reader_partition: str) -> None:
        """Let ``reader_partition`` read ``partition``. Read-only, by design."""
        self._grants.setdefault(_norm(partition), set()).add(_norm(reader_partition))

    def revoke_read(self, partition: str, reader_partition: str) -> None:
        self._grants.get(_norm(partition), set()).discard(_norm(reader_partition))

    def may_read(self, actor_partition: str, target_partition: str) -> bool:
        actor = _norm(actor_partition)
        target = _norm(target_partition)
        if _within(target, actor):
            return True
        # A grant on an ancestor covers everything beneath it: granting the
        # `intelligence` root is what lets the executive read every agent under
        # it without enumerating each sub-partition as it is created.
        for scope in _ancestors(target):
            for grantee in self._grants.get(scope, ()):
                if _within(actor, grantee):
                    return True
        return False

    def may_write(self, actor_partition: str, target_partition: str) -> bool:
        """Writes are confined to the actor's own subtree. No exceptions."""
        return _within(_norm(target_partition), _norm(actor_partition))

    # ------------------------------------------------------------------ #
    # Read / write
    # ------------------------------------------------------------------ #
    def write(
        self,
        actor_partition: str,
        key: str,
        value: Any,
        author: str,
        confidence: float = 1.0,
        ttl: float | None = None,
        partition: str | None = None,
    ) -> MemoryRecord:
        """Write into ``partition`` (defaults to the actor's own)."""
        target = _norm(partition or actor_partition)
        if not self.may_write(actor_partition, target):
            raise MemoryAccessError(
                f"{actor_partition} may not write to {target} — writes are subtree-confined"
            )
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        record = MemoryRecord(
            key=key,
            value=value,
            partition=target,
            author=author,
            confidence=confidence,
            expires_at=time.time() + ttl if ttl is not None else None,
        )
        self._records.setdefault(target, {})[key] = record
        return record

    def read(self, actor_partition: str, partition: str, key: str) -> MemoryRecord | None:
        """Read one record, honouring boundaries and TTL."""
        target = _norm(partition)
        if not self.may_read(actor_partition, target):
            raise MemoryAccessError(f"{actor_partition} may not read {target}")
        record = self._records.get(target, {}).get(key)
        if record is None:
            return None
        if record.expired():
            del self._records[target][key]
            return None
        return record

    def scan(self, actor_partition: str, partition: str | None = None) -> tuple[MemoryRecord, ...]:
        """Every live record the actor may see, optionally scoped to a partition."""
        target = _norm(partition) if partition else None
        out: list[MemoryRecord] = []
        for part in sorted(self._records):
            if target is not None and not _within(part, target):
                continue
            if not self.may_read(actor_partition, part):
                continue
            for record in self._records[part].values():
                if not record.expired():
                    out.append(record)
        return tuple(sorted(out, key=lambda r: (r.partition, r.key)))

    def forget(self, actor_partition: str, partition: str, key: str) -> bool:
        """Delete a record. Requires write authority over the partition."""
        target = _norm(partition)
        if not self.may_write(actor_partition, target):
            raise MemoryAccessError(f"{actor_partition} may not modify {target}")
        return self._records.get(target, {}).pop(key, None) is not None

    def purge_expired(self) -> int:
        """Drop every expired record. Returns how many were removed."""
        now = time.time()
        removed = 0
        for part, records in self._records.items():
            stale = [k for k, r in records.items() if r.expired(now)]
            for key in stale:
                del records[key]
            removed += len(stale)
        return removed

    # ------------------------------------------------------------------ #
    # Inspection
    # ------------------------------------------------------------------ #
    def partitions(self) -> tuple[str, ...]:
        return tuple(sorted(self._records))

    def __iter__(self) -> Iterator[MemoryRecord]:
        for part in sorted(self._records):
            yield from self._records[part].values()

    def snapshot(self) -> dict[str, Any]:
        live = [r for r in self if not r.expired()]
        return {
            "partitions": len(self._records),
            "records": len(live),
            "grants": sum(len(v) for v in self._grants.values()),
            "mean_confidence": (
                round(sum(r.confidence for r in live) / len(live), 3) if live else 0.0
            ),
            "by_partition": {
                part: len([r for r in recs.values() if not r.expired()])
                for part, recs in sorted(self._records.items())
            },
        }


def _norm(partition: str) -> str:
    if not partition or not partition.strip():
        raise MemoryAccessError("partition is required")
    return partition.strip().strip("/")


def _ancestors(partition: str) -> tuple[str, ...]:
    """``a/b/c`` → ``('a/b/c', 'a/b', 'a')``, most specific first."""
    parts = partition.split("/")
    return tuple("/".join(parts[: i + 1]) for i in reversed(range(len(parts))))


def _within(candidate: str, root: str) -> bool:
    """True when ``candidate`` is ``root`` or lives beneath it.

    Compares path segments, not string prefixes — ``a/bc`` is not inside
    ``a/b``, and treating it as such would silently merge two partitions.
    """
    if candidate == root:
        return True
    return candidate.startswith(root + "/")
