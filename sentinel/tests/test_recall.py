"""SENTINEL — recall harness (ADR 0001 Phase-One exit gate).

Claim under test: applying the in-partition ACL pre-filter does NOT degrade
retrieval quality for documents the user is allowed to see. Formally, for an
authorized principal:

    recall@k(filtered store)  ==  recall@k(oracle restricted to authorized set)

i.e. the filter only ever removes UNAUTHORIZED candidates, never authorized
ones. We also assert that no unauthorized doc ever appears post-recheck.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.audit import AuditLog
from sentinel.models import Principal
from sentinel.rbac import DocumentACL, InMemoryRBAC
from sentinel.retrieval import retrieve
from sentinel.vectorstore import (
    AclFilter,
    InMemoryVectorStore,
    Record,
    embed,
    tenant_namespace,
)

TENANT = "acme"
TOPICS = ["revenue forecast", "incident response", "merger strategy",
          "hiring plan", "security audit", "product roadmap"]


def _build_corpus(n_per_topic: int = 10):
    """60 docs; even index = analyst-visible (sensitivity 1), odd = admin-only
    (sensitivity 5)."""
    docs, records = [], []
    i = 0
    for topic in TOPICS:
        for j in range(n_per_topic):
            doc_id = f"d{i}"
            sensitivity = 1 if i % 2 == 0 else 5
            roles = ["analyst", "admin"] if sensitivity == 1 else ["admin"]
            text = f"{topic} memo number {j} for {TENANT}"
            docs.append(DocumentACL(doc_id, TENANT, sensitivity, frozenset(roles)))
            records.append(Record(doc_id, embed(text), {
                "doc_id": doc_id, "tenant_id": TENANT, "sensitivity": sensitivity,
                "allowed_roles": frozenset(roles), "text": text, "source": f"s3://{doc_id}",
            }))
            i += 1
    rbac = InMemoryRBAC(docs)
    vstore = InMemoryVectorStore()
    vstore.upsert(tenant_namespace(Principal("x", TENANT, frozenset(), 0)), records)
    return rbac, vstore, records


ANALYST = Principal("u-an", TENANT, frozenset({"analyst"}), clearance=2)
ADMIN = Principal("u-ad", TENANT, frozenset({"admin"}), clearance=5)


def _oracle_topk(records, principal, query, k):
    """Ground truth: cosine top-k computed ONLY over records the principal is
    authorized to read (tenant + clearance + role)."""
    qv = embed(query)
    authorized = [
        r for r in records
        if r.metadata["tenant_id"] == principal.tenant_id
        and r.metadata["sensitivity"] <= principal.clearance
        and (r.metadata["allowed_roles"] & principal.roles)
    ]
    scored = sorted(authorized, key=lambda r: sum(a * b for a, b in zip(qv, r.vector)), reverse=True)
    return [r.metadata["doc_id"] for r in scored[:k]]


def test_filter_is_lossless_for_authorized_docs():
    rbac, vstore, records = _build_corpus()
    k = 8
    for query in TOPICS:
        resp = retrieve(ANALYST, query, vstore=vstore, rbac=rbac, audit=AuditLog(), k=k)
        got = [c.doc_id for c in resp.chunks]
        oracle = _oracle_topk(records, ANALYST, query, k)
        # filtered retrieval == oracle over authorized set -> zero recall loss
        assert got == oracle, f"recall loss on '{query}': {got} != {oracle}"


def test_no_unauthorized_doc_ever_returned():
    rbac, vstore, records = _build_corpus()
    for query in TOPICS:
        resp = retrieve(ANALYST, query, vstore=vstore, rbac=rbac, audit=AuditLog(), k=20)
        for c in resp.chunks:
            assert c.sensitivity <= ANALYST.clearance       # never over-clearance
            assert c.doc_id.startswith("d")


def test_admin_recall_superset_of_analyst():
    rbac, vstore, _ = _build_corpus()
    q = "merger strategy"
    # k larger than the corpus so truncation can't confound the set comparison.
    an = {c.doc_id for c in retrieve(ANALYST, q, vstore=vstore, rbac=rbac, audit=AuditLog(), k=80).chunks}
    ad = {c.doc_id for c in retrieve(ADMIN, q, vstore=vstore, rbac=rbac, audit=AuditLog(), k=80).chunks}
    assert an <= ad                                          # admin sees superset of analyst
    assert len(ad) > len(an)                                 # and strictly more (admin-only docs)


# ----------------------------------------------------- adapter filter builders ----

def test_pinecone_filter_builder():
    from sentinel.adapters import pinecone_filter
    f = pinecone_filter(AclFilter(roles=frozenset({"analyst", "admin"}), max_sensitivity=2))
    assert f["$and"][0] == {"sensitivity": {"$lte": 2}}
    assert f["$and"][1] == {"allowed_roles": {"$in": ["admin", "analyst"]}}
    # deny-all must match nothing
    assert pinecone_filter(AclFilter.from_boundary(None)) == {"doc_id": {"$in": []}}


def test_milvus_expr_builder():
    from sentinel.adapters import milvus_expr
    e = milvus_expr(AclFilter(roles=frozenset({"analyst"}), max_sensitivity=2))
    assert "sensitivity <= 2" in e
    assert 'array_contains_any(allowed_roles, ["analyst"])' in e
    assert milvus_expr(AclFilter.from_boundary(None)) == "1 == 0"
