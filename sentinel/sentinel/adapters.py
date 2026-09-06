"""SENTINEL — production VectorStore adapters (Pinecone + Milvus).

Both implement the same ``VectorStore`` protocol as the in-memory reference, so
the retrieval trust loop is unchanged when you swap providers. The filter/expr
*builders* are pure functions and unit-tested without any client installed; the
store classes import their SDK lazily so this module loads everywhere.

Mapping (per ADR 0001):
  * tenant  -> Pinecone namespace        / Milvus partition (partition-key)
  * ACL     -> Pinecone metadata filter  / Milvus boolean expr

Neither is the authority — `rbac.authorize_documents` re-checks every doc_id.
"""
from __future__ import annotations

from typing import Any

from .vectorstore import AclFilter, Hit

# Sentinel that matches nothing — provider equivalent of `WHERE false`.
_DENY_ALL_PINECONE: dict[str, Any] = {"doc_id": {"$in": []}}
_DENY_ALL_MILVUS = "1 == 0"


def pinecone_filter(acl: AclFilter) -> dict[str, Any]:
    """Translate an AclFilter to a Pinecone metadata filter expression."""
    if acl.deny_all:
        return dict(_DENY_ALL_PINECONE)
    return {
        "$and": [
            {"sensitivity": {"$lte": acl.max_sensitivity}},
            {"allowed_roles": {"$in": sorted(acl.roles)}},
        ]
    }


def milvus_expr(acl: AclFilter) -> str:
    """Translate an AclFilter to a Milvus boolean expression string."""
    if acl.deny_all:
        return _DENY_ALL_MILVUS
    roles = ", ".join(f'"{r}"' for r in sorted(acl.roles))
    return f"sensitivity <= {acl.max_sensitivity} and array_contains_any(allowed_roles, [{roles}])"


def _meta_to_hit(score: float, meta: dict[str, Any]) -> Hit:
    return Hit(
        doc_id=meta["doc_id"],
        text=meta.get("text", ""),
        score=float(score),
        tenant_id=meta["tenant_id"],
        sensitivity=int(meta.get("sensitivity", 0)),
        source=meta.get("source", ""),
    )


class PineconeVectorStore:
    """Adapter for Pinecone. ``namespace`` == tenant partition.

    Usage:
        from pinecone import Pinecone
        index = Pinecone(api_key=...).Index("sentinel")
        store = PineconeVectorStore(index)
    """

    def __init__(self, index: Any) -> None:  # pragma: no cover - needs SDK + creds
        self._index = index

    def query(self, *, namespace: str, vector: list[float], k: int, acl: AclFilter) -> list[Hit]:  # pragma: no cover
        if acl.deny_all:
            return []
        res = self._index.query(
            namespace=namespace,
            vector=vector,
            top_k=k,
            filter=pinecone_filter(acl),
            include_metadata=True,
        )
        matches = res.get("matches", []) if isinstance(res, dict) else res.matches
        return [_meta_to_hit(m["score"], m["metadata"]) for m in matches]


class MilvusVectorStore:
    """Adapter for Milvus. Tenant isolation via partition (partition-key).

    Usage:
        from pymilvus import Collection
        store = MilvusVectorStore(Collection("sentinel"))
    """

    def __init__(self, collection: Any, *, vector_field: str = "embedding") -> None:  # pragma: no cover
        self._col = collection
        self._vector_field = vector_field

    def query(self, *, namespace: str, vector: list[float], k: int, acl: AclFilter) -> list[Hit]:  # pragma: no cover
        if acl.deny_all:
            return []
        results = self._col.search(
            data=[vector],
            anns_field=self._vector_field,
            param={"metric_type": "IP", "params": {"nprobe": 16}},
            limit=k,
            expr=milvus_expr(acl),
            partition_names=[namespace],
            output_fields=["doc_id", "tenant_id", "sensitivity", "text", "source"],
        )
        hits: list[Hit] = []
        for hit in results[0]:
            ent = hit.entity
            hits.append(_meta_to_hit(hit.score, {
                "doc_id": ent.get("doc_id"),
                "tenant_id": ent.get("tenant_id"),
                "sensitivity": ent.get("sensitivity"),
                "text": ent.get("text"),
                "source": ent.get("source"),
            }))
        return hits
