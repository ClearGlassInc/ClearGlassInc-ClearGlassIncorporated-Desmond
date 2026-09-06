"""SENTINEL — vector store abstraction (namespace-per-tenant + ACL metadata).

Tenant isolation is a *hard partition* (one namespace/collection per tenant).
Finer-grained (role/sensitivity) access is an ACL metadata pre-filter applied
inside the tenant partition. Neither is the final authority — see ``rbac.py``.

Provider mapping:
  * Pinecone : namespace == tenant_id; ``filter=`` metadata predicate.
  * Milvus   : partition-key == tenant_id (or collection-per-tenant);
               boolean expr on scalar fields for the ACL predicate.

``InMemoryVectorStore`` is a runnable reference using a tiny hashing embedding
and cosine similarity, so the trust loop is exercisable with no external DB.
``LeakyVectorStore`` (in tests) deliberately ignores the filter to prove the
Postgres recheck — not the vector filter — is what contains a breach.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Iterable, Protocol

from .models import Principal

_DIM = 64


def embed(text: str) -> list[float]:
    """Deterministic hashing embedding (bag-of-tokens -> fixed dim, L2-normed).

    Stand-in for a real embedding model; keeps the reference store dependency
    free and tests deterministic.
    """
    vec = [0.0] * _DIM
    for tok in _tokenize(text):
        h = int.from_bytes(hashlib.blake2b(tok.encode(), digest_size=8).digest(), "big")
        vec[h % _DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _tokenize(text: str) -> list[str]:
    return [t for t in "".join(c.lower() if c.isalnum() else " " for c in text).split() if t]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))  # both are L2-normalized


@dataclass(frozen=True)
class AclFilter:
    """Metadata predicate. ``deny_all`` is the fail-closed sentinel: it matches
    nothing (the equivalent of ``WHERE false``), used when P_user is unresolved."""

    roles: frozenset[str]
    max_sensitivity: int
    deny_all: bool = False

    @staticmethod
    def from_boundary(boundary) -> "AclFilter":
        if boundary is None:
            return AclFilter(frozenset(), -1, deny_all=True)
        return AclFilter(roles=boundary.roles, max_sensitivity=boundary.clearance)

    def matches(self, meta: dict) -> bool:
        if self.deny_all:
            return False
        if meta.get("sensitivity", 1_000_000) > self.max_sensitivity:
            return False
        allowed = meta.get("allowed_roles", frozenset())
        return bool(set(allowed) & self.roles)


@dataclass(frozen=True)
class Record:
    id: str
    vector: list[float]
    metadata: dict  # must include: doc_id, tenant_id, sensitivity, allowed_roles, text, source


@dataclass(frozen=True)
class Hit:
    doc_id: str
    text: str
    score: float
    tenant_id: str
    sensitivity: int
    source: str


class VectorStore(Protocol):
    def query(
        self, *, namespace: str, vector: list[float], k: int, acl: AclFilter
    ) -> list[Hit]: ...


class InMemoryVectorStore:
    """Namespace-partitioned reference store."""

    def __init__(self) -> None:
        self._ns: dict[str, list[Record]] = {}

    def upsert(self, namespace: str, records: Iterable[Record]) -> None:
        self._ns.setdefault(namespace, []).extend(records)

    def query(self, *, namespace: str, vector: list[float], k: int, acl: AclFilter) -> list[Hit]:
        records = self._ns.get(namespace, [])
        scored: list[tuple[float, Record]] = []
        for r in records:
            if not acl.matches(r.metadata):  # ACL pre-filter inside the partition
                continue
            scored.append((_cosine(vector, r.vector), r))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [_to_hit(s, r) for s, r in scored[:k]]


def _to_hit(score: float, r: Record) -> Hit:
    m = r.metadata
    return Hit(
        doc_id=m["doc_id"],
        text=m.get("text", ""),
        score=score,
        tenant_id=m["tenant_id"],
        sensitivity=int(m.get("sensitivity", 0)),
        source=m.get("source", ""),
    )


def tenant_namespace(principal: Principal) -> str:
    """Tenant partition selector — derived server-side from the authenticated
    principal, never from a client-supplied value."""
    return f"tenant::{principal.tenant_id}"
