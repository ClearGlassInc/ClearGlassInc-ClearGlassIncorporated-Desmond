# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Append-only, tamper-evident audit logging."""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class HashChainAuditLog:
    """JSONL audit log where every record commits to the prior record hash."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._last_hash = self._read_last_hash()

    def append(self, event: dict[str, Any]) -> str:
        with self._lock:
            record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "previous_hash": self._last_hash,
                "event": event,
            }
            canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
            record_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            envelope = {**record, "hash": record_hash}
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(envelope, sort_keys=True, default=str) + "\n")
                handle.flush()
            self._last_hash = record_hash
            return record_hash

    def verify(self) -> tuple[bool, int]:
        previous = "GENESIS"
        count = 0
        if not self.path.exists():
            return True, count
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                envelope = json.loads(line)
                supplied_hash = envelope.pop("hash")
                if envelope.get("previous_hash") != previous:
                    return False, count
                canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":"), default=str)
                calculated = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                if not hmac.compare_digest(calculated, supplied_hash):
                    return False, count
                previous = supplied_hash
                count += 1
        return True, count

    def _read_last_hash(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return "GENESIS"
        last_line = ""
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last_line = line
        return json.loads(last_line).get("hash", "GENESIS") if last_line else "GENESIS"
