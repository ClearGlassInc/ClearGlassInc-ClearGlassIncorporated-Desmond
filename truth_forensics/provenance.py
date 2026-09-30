# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Provenance ledger: SOURCE -> ACQUISITION -> TRANSFORMATION -> DERIVATIVE ->
ANALYSIS -> REVIEW -> REPORT.

Append-only and hash-chained the same way as the RFED audit trail
(`bots/rfed_audit_bot.py`): record_hash = sha256(prev_hash || canonical(body)).
Changing any past record breaks every hash after it, and `verify()` names the
first broken sequence number. Nothing in this module edits evidence: a
transformation produces a new evidence record with its own hash and a
DERIVED_FROM link to its parent.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from . import vocab
from .canonical import GENESIS_HASH, canonical_json, sha256_text

EVENT_TYPES = ("ACQUIRED", "TRANSFORMED", "DERIVED", "ANALYZED", "REVIEWED", "REPORTED")


@dataclass(frozen=True)
class LedgerRecord:
    seq: int
    event: str
    subject_id: str
    parent_ids: tuple[str, ...]
    actor: str
    at: str
    detail: dict
    software: str
    prev_hash: str
    record_hash: str

    def body(self) -> dict:
        return {
            "seq": self.seq, "event": self.event, "subject_id": self.subject_id,
            "parent_ids": list(self.parent_ids), "actor": self.actor, "at": self.at,
            "detail": self.detail, "software": self.software,
        }

    def to_dict(self) -> dict:
        return {**self.body(), "prev_hash": self.prev_hash, "record_hash": self.record_hash}


def chain_hash(prev_hash: str, body: dict) -> str:
    return sha256_text(prev_hash + canonical_json(body))


class ProvenanceLedger:
    def __init__(self) -> None:
        self._records: list[LedgerRecord] = []

    @property
    def records(self) -> tuple[LedgerRecord, ...]:
        return tuple(self._records)

    @property
    def head(self) -> str:
        return self._records[-1].record_hash if self._records else GENESIS_HASH

    def append(self, event: str, subject_id: str, *, actor: str, at: str,
               parent_ids: tuple[str, ...] = (), detail: dict | None = None) -> LedgerRecord:
        if event not in EVENT_TYPES:
            raise ValueError(f"unknown provenance event {event}")
        if not actor.strip():
            raise ValueError("every provenance event needs an actor")
        body = {
            "seq": len(self._records) + 1, "event": event, "subject_id": subject_id,
            "parent_ids": list(parent_ids), "actor": actor, "at": at,
            "detail": detail or {}, "software": f"{vocab.ENGINE_NAME}/{vocab.ENGINE_VERSION}",
        }
        # Round-trip through JSON so the stored detail cannot alias caller state.
        body = json.loads(canonical_json(body))
        rec = LedgerRecord(
            seq=body["seq"], event=event, subject_id=subject_id, parent_ids=tuple(parent_ids),
            actor=actor, at=at, detail=body["detail"], software=body["software"],
            prev_hash=self.head, record_hash=chain_hash(self.head, body),
        )
        self._records.append(rec)
        return rec

    def acquired(self, record, *, actor: str | None = None) -> LedgerRecord:
        return self.append("ACQUIRED", record.evidence_id, actor=actor or record.acquired_by,
                           at=record.acquired_at, detail={
                               "content_sha256": record.content_sha256,
                               "size_bytes": record.size_bytes,
                               "mime": record.mime_sniffed,
                               "object_kind": record.object_kind,
                               "method": record.acquisition_method,
                           })

    def derived(self, record, *, parent_sha256: str) -> LedgerRecord:
        return self.append("DERIVED", record.evidence_id, actor=record.acquired_by,
                           at=record.acquired_at, parent_ids=(record.parent_id,), detail={
                               "content_sha256": record.content_sha256,
                               "parent_sha256": parent_sha256,
                               "transformation": record.transformation,
                           })

    def verify(self) -> tuple[bool, int | None]:
        return verify_records([r.to_dict() for r in self._records])

    def lineage(self, evidence_id: str) -> list[str]:
        """Evidence ids from this item back to its root original."""
        parents = {r.subject_id: r.parent_ids[0] for r in self._records
                   if r.event == "DERIVED" and r.parent_ids}
        chain, seen = [evidence_id], {evidence_id}
        while chain[-1] in parents:
            nxt = parents[chain[-1]]
            if nxt in seen:
                break
            chain.append(nxt)
            seen.add(nxt)
        return chain

    def to_jsonl(self) -> str:
        return "".join(canonical_json(r.to_dict()) + "\n" for r in self._records)


def verify_records(records: list[dict]) -> tuple[bool, int | None]:
    """Replay a chain. Returns (ok, first_bad_seq)."""
    prev = GENESIS_HASH
    for i, rec in enumerate(records, start=1):
        body = {k: rec.get(k) for k in ("seq", "event", "subject_id", "parent_ids", "actor",
                                         "at", "detail", "software")}
        if rec.get("seq") != i or rec.get("prev_hash") != prev:
            return False, i
        if chain_hash(prev, body) != rec.get("record_hash"):
            return False, i
        prev = rec["record_hash"]
    return True, None


def verify_jsonl(text: str) -> tuple[bool, int | None]:
    records = [json.loads(line) for line in text.splitlines() if line.strip()]
    return verify_records(records)
