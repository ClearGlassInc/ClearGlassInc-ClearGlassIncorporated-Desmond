# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Append-only, hash-chained audit ledger for Percival v9.

Every policy decision is appended here *before* it takes effect. Each entry
carries the SHA-256 of its predecessor, so any tampering (edit, deletion,
reordering) breaks the chain and is detected by :meth:`AuditLedger.verify`.
In production this is Kafka + S3 WORM; the interface is identical.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

GENESIS_HASH = "0" * 64


class LedgerError(RuntimeError):
    """Raised when the ledger cannot durably record an entry."""


def _entry_hash(prev_hash: str, payload: dict[str, Any]) -> str:
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{prev_hash}:{canon}".encode()).hexdigest()


@dataclass(frozen=True)
class LedgerEntry:
    """One immutable audit record."""

    index: int
    timestamp: float
    payload: dict[str, Any]
    prev_hash: str
    entry_hash: str


@dataclass
class AuditLedger:
    """In-memory append-only ledger with a verifiable hash chain."""

    _entries: list[LedgerEntry] = field(default_factory=list)

    def append(self, payload: dict[str, Any]) -> LedgerEntry:
        """Append ``payload`` and return the sealed entry."""
        prev = self._entries[-1].entry_hash if self._entries else GENESIS_HASH
        body = {"index": len(self._entries), "payload": payload}
        entry = LedgerEntry(
            index=len(self._entries),
            timestamp=time.time(),
            payload=dict(payload),
            prev_hash=prev,
            entry_hash=_entry_hash(prev, body),
        )
        self._entries.append(entry)
        return entry

    def verify(self) -> bool:
        """Return True iff the whole chain is intact."""
        prev = GENESIS_HASH
        for i, entry in enumerate(self._entries):
            body = {"index": i, "payload": entry.payload}
            if entry.prev_hash != prev or entry.entry_hash != _entry_hash(prev, body):
                return False
            prev = entry.entry_hash
        return True

    def entries(self) -> tuple[LedgerEntry, ...]:
        return tuple(self._entries)

    def __len__(self) -> int:
        return len(self._entries)


class FailingLedger(AuditLedger):
    """Test double simulating Audit Ledger backpressure (Kafka down).

    Any append raises :class:`LedgerError`; the Policy Governor must react
    by failing closed (deny-all), never by executing unlogged actions.
    """

    def append(self, payload: dict[str, Any]) -> LedgerEntry:
        raise LedgerError("audit ledger unavailable (simulated backpressure)")
