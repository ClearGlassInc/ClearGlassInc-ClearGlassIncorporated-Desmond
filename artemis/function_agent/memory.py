# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
"""Working, episodic, semantic, and durable memory abstractions."""
from __future__ import annotations

import json
import math
import sqlite3
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    key: str
    value: Any
    score: float = 1.0
    metadata: dict[str, Any] | None = None


class Memory(ABC):
    """Common retrieval contract used by agent memory adapters."""

    @abstractmethod
    def add(self, key: str, value: Any, metadata: dict[str, Any] | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 3) -> list[MemoryRecord]:
        raise NotImplementedError


class WorkingMemory(Memory):
    """Bounded in-process memory for recent messages and intermediate state."""

    def __init__(self, capacity: int = 100) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self._items: deque[MemoryRecord] = deque(maxlen=capacity)

    def add(self, key: str, value: Any, metadata: dict[str, Any] | None = None) -> None:
        self._items.append(MemoryRecord(key=key, value=value, metadata=metadata))

    def retrieve(self, query: str, top_k: int = 3) -> list[MemoryRecord]:
        query_terms = set(query.casefold().split())
        ranked: list[MemoryRecord] = []
        for item in reversed(self._items):
            text = f"{item.key} {item.value}".casefold()
            score = float(sum(term in text for term in query_terms)) if query_terms else 1.0
            if score > 0:
                ranked.append(MemoryRecord(item.key, item.value, score, item.metadata))
        return ranked[:top_k]


class SQLiteMemory:
    """Durable namespaced key-value store with TTL and WAL journaling."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def set(self, namespace: str, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=ttl_seconds) if ttl_seconds else None
        payload = json.dumps(value, sort_keys=True, default=str)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO agent_memory(namespace, key, value, expires_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(namespace, key) DO UPDATE SET
                    value=excluded.value,
                    expires_at=excluded.expires_at,
                    updated_at=excluded.updated_at
                """,
                (
                    namespace,
                    key,
                    payload,
                    expires_at.isoformat() if expires_at else None,
                    now.isoformat(),
                ),
            )

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT value, expires_at FROM agent_memory WHERE namespace=? AND key=?",
                (namespace, key),
            ).fetchone()
            if row is None:
                return default
            if row[1] and datetime.fromisoformat(row[1]) < datetime.now(UTC):
                connection.execute(
                    "DELETE FROM agent_memory WHERE namespace=? AND key=?", (namespace, key)
                )
                return default
            return json.loads(row[0])

    def delete(self, namespace: str, key: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM agent_memory WHERE namespace=? AND key=?", (namespace, key)
            )
            return cursor.rowcount > 0

    def list_namespace(self, namespace: str, limit: int = 100) -> dict[str, Any]:
        self.prune_expired()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT key, value FROM agent_memory WHERE namespace=? ORDER BY updated_at DESC LIMIT ?",
                (namespace, limit),
            ).fetchall()
        return {key: json.loads(value) for key, value in rows}

    def prune_expired(self) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM agent_memory WHERE expires_at IS NOT NULL AND expires_at < ?",
                (datetime.now(UTC).isoformat(),),
            )
            return cursor.rowcount

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_memory(
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    expires_at TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(namespace, key)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_agent_memory_expiry ON agent_memory(expires_at)"
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()


class EpisodicMemory(Memory):
    """Session-scoped durable event memory backed by SQLite."""

    def __init__(self, store: SQLiteMemory, session_id: str) -> None:
        self.store = store
        self.namespace = f"episode:{session_id}"

    def add(self, key: str, value: Any, metadata: dict[str, Any] | None = None) -> None:
        event_key = f"{datetime.now(UTC).isoformat()}:{key}:{uuid4().hex}"
        self.store.set(self.namespace, event_key, {"value": value, "metadata": metadata or {}})

    def retrieve(self, query: str, top_k: int = 3) -> list[MemoryRecord]:
        query_terms = set(query.casefold().split())
        rows = self.store.list_namespace(self.namespace, limit=max(top_k * 10, 30))
        ranked: list[MemoryRecord] = []
        for key, payload in rows.items():
            text = f"{key} {payload.get('value')}".casefold()
            score = float(sum(term in text for term in query_terms)) if query_terms else 1.0
            if score > 0:
                ranked.append(
                    MemoryRecord(key, payload.get("value"), score, payload.get("metadata"))
                )
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:top_k]


EmbeddingFunction = Callable[[str], Sequence[float]]


class VectorMemory(Memory):
    """Dependency-free semantic memory using caller-supplied embeddings."""

    def __init__(self, embed: EmbeddingFunction) -> None:
        self._embed = embed
        self._items: dict[str, tuple[list[float], Any, dict[str, Any] | None]] = {}

    def add(self, key: str, value: Any, metadata: dict[str, Any] | None = None) -> None:
        vector = [float(item) for item in self._embed(str(value))]
        if not vector:
            raise ValueError("embedding function returned an empty vector")
        self._items[key] = (vector, value, metadata)

    def retrieve(self, query: str, top_k: int = 3) -> list[MemoryRecord]:
        query_vector = [float(item) for item in self._embed(query)]
        if not query_vector:
            return []
        ranked: list[MemoryRecord] = []
        for key, (vector, value, metadata) in self._items.items():
            ranked.append(MemoryRecord(key, value, self._cosine(query_vector, vector), metadata))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    @staticmethod
    def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
        if len(left) != len(right):
            raise ValueError("embedding dimensions do not match")
        numerator = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
