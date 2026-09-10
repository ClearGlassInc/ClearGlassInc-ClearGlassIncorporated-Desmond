# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Memory Agent — ranked, persistent recall.

Deterministic, stdlib-only memory store. Retrieval ranks records by the OS's
three mandated priorities:

    score = accuracy (term overlap) x recency x authority

Recency uses a monotonic insertion sequence (not wall-clock) so retrieval is
reproducible in tests and CI. Missing memory is reported as missing — the store
never invents a record.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


@dataclass(frozen=True)
class MemoryRecord:
    """A single remembered fact/decision/lesson."""

    seq: int
    kind: str          # semantic | project | decision | architecture | failure | lesson
    text: str
    authority: float   # 0..1 — source trustworthiness

    def to_dict(self) -> dict[str, object]:
        return {"seq": self.seq, "kind": self.kind, "text": self.text,
                "authority": self.authority}


@dataclass
class MemoryStore:
    """Append-only ranked memory. Persist via :meth:`to_json`."""

    records: list[MemoryRecord] = field(default_factory=list)
    _seq: int = 0

    def remember(self, kind: str, text: str, *, authority: float = 0.5) -> MemoryRecord:
        if not text.strip():
            raise ValueError("cannot remember empty text")
        authority = max(0.0, min(1.0, authority))
        rec = MemoryRecord(self._seq, kind, text, authority)
        self.records.append(rec)
        self._seq += 1
        return rec

    def retrieve(self, query: str, *, k: int = 3) -> list[tuple[MemoryRecord, float]]:
        """Return up to ``k`` records ranked by accuracy x recency x authority.

        Records with zero term overlap are excluded — the store reports "nothing
        relevant" rather than padding with unrelated memories.
        """
        q = _tokens(query)
        if not q or not self.records:
            return []
        newest = self._seq - 1 if self._seq else 0
        scored: list[tuple[MemoryRecord, float]] = []
        for rec in self.records:
            overlap = len(q & _tokens(rec.text))
            if overlap == 0:
                continue
            accuracy = overlap / len(q)
            # recency in (0,1]: newest == 1.0, decaying by age with a gentle floor
            age = newest - rec.seq
            recency = 1.0 / (1.0 + age)
            score = accuracy * recency * (0.5 + 0.5 * rec.authority)
            scored.append((rec, round(score, 6)))
        scored.sort(key=lambda x: (-x[1], -x[0].seq))
        return scored[:k]

    def to_json(self) -> str:
        return json.dumps([r.to_dict() for r in self.records], indent=2)

    @classmethod
    def from_records(cls, rows: list[dict[str, object]]) -> MemoryStore:
        store = cls()
        for r in rows:
            store.records.append(
                MemoryRecord(int(r["seq"]), str(r["kind"]), str(r["text"]),
                             float(r["authority"]))  # type: ignore[arg-type]
            )
        store._seq = (store.records[-1].seq + 1) if store.records else 0
        return store
