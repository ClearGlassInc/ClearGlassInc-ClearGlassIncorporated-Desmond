"""SENTINEL — append-only, hash-chained audit log.

Every retrieval decision is recorded. Each entry commits to the previous
entry's hash, so any tampering with history is detectable (tamper-evident).
In production this is persisted to immutable storage (Postgres append-only
table + periodic anchoring); here it is in-memory and verifiable.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuditEntry:
    seq: int
    ts: float
    actor: str
    action: str
    detail: dict[str, Any]
    prev_hash: str
    entry_hash: str


class AuditLog:
    GENESIS = "0" * 64

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(self, *, actor: str, action: str, detail: dict[str, Any]) -> AuditEntry:
        prev = self._entries[-1].entry_hash if self._entries else self.GENESIS
        seq = len(self._entries)
        ts = time.time()
        payload = json.dumps(
            {"seq": seq, "ts": ts, "actor": actor, "action": action, "detail": detail, "prev": prev},
            sort_keys=True,
            default=str,
        )
        entry_hash = hashlib.sha256(payload.encode()).hexdigest()
        entry = AuditEntry(seq, ts, actor, action, detail, prev, entry_hash)
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    def verify(self) -> bool:
        """Re-walk the chain; return False if any link is broken."""
        prev = self.GENESIS
        for e in self._entries:
            payload = json.dumps(
                {"seq": e.seq, "ts": e.ts, "actor": e.actor, "action": e.action,
                 "detail": e.detail, "prev": prev},
                sort_keys=True,
                default=str,
            )
            if hashlib.sha256(payload.encode()).hexdigest() != e.entry_hash:
                return False
            if e.prev_hash != prev:
                return False
            prev = e.entry_hash
        return True
