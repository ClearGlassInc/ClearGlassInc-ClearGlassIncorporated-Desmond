# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Append-only, tamper-evident audit ledger.

Every material decision the OS makes is written here with a SHA-256 hash chain,
so the log cannot be silently edited after the fact: each entry commits to the
previous entry's digest. :meth:`AuditLedger.verify` recomputes the chain and
reports the first break. Stdlib only; JSON-serializable for persistence.

This is the code backing the governance rule "maintain complete audit logs" and
the Audit Agent's regression-detection duties.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

GENESIS = "0" * 64


def _digest(index: int, prev_hash: str, kind: str, payload: dict[str, object]) -> str:
    body = json.dumps(
        {"index": index, "prev": prev_hash, "kind": kind, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditEntry:
    """One immutable, chained ledger record."""

    index: int
    kind: str
    payload: dict[str, object]
    prev_hash: str
    hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "kind": self.kind,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }


@dataclass
class AuditLedger:
    """In-memory append-only hash chain (persist via :meth:`to_json`)."""

    entries: list[AuditEntry] = field(default_factory=list)

    @property
    def head(self) -> str:
        """Digest of the most recent entry (GENESIS if empty)."""
        return self.entries[-1].hash if self.entries else GENESIS

    def append(self, kind: str, payload: dict[str, object]) -> AuditEntry:
        """Record an event, chaining it to the current head."""
        if not isinstance(kind, str) or not kind:
            raise ValueError("audit entry kind must be a non-empty string")
        index = len(self.entries)
        prev = self.head
        entry = AuditEntry(index, kind, dict(payload), prev, _digest(index, prev, kind, payload))
        self.entries.append(entry)
        return entry

    def verify(self) -> tuple[bool, int | None]:
        """Recompute the chain. Returns ``(ok, first_bad_index_or_None)``."""
        prev = GENESIS
        for i, entry in enumerate(self.entries):
            if entry.index != i or entry.prev_hash != prev:
                return False, i
            if entry.hash != _digest(entry.index, entry.prev_hash, entry.kind, entry.payload):
                return False, i
            prev = entry.hash
        return True, None

    def to_json(self) -> str:
        return json.dumps([e.to_dict() for e in self.entries], indent=2)

    @classmethod
    def from_entries(cls, rows: list[dict[str, object]]) -> AuditLedger:
        ledger = cls()
        ledger.entries = [
            AuditEntry(
                int(r["index"]),  # type: ignore[arg-type]
                str(r["kind"]),
                dict(r["payload"]),  # type: ignore[arg-type]
                str(r["prev_hash"]),
                str(r["hash"]),
            )
            for r in rows
        ]
        return ledger
