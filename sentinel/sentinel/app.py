"""SENTINEL — FastAPI adapter exposing the Phase-One retrieval trust loop.

Optional layer: the core (governance/rbac/vectorstore/retrieval) is pure stdlib
and is what the test suite exercises. This module wires an HTTP surface with a
bearer-token -> Principal resolver. The Principal's tenant/roles/clearance are
ALWAYS derived server-side from the token, never read from the request body.

Run:  uvicorn sentinel.app:app --reload
"""
from __future__ import annotations

from typing import Optional

try:
    from fastapi import Depends, FastAPI, Header, HTTPException
    from pydantic import BaseModel
except Exception as exc:  # pragma: no cover - import guard for test envs
    raise ImportError(
        "sentinel.app requires fastapi + pydantic (see sentinel/requirements.txt)"
    ) from exc

from .audit import AuditLog
from .models import Principal
from .rbac import DocumentACL, InMemoryRBAC
from .retrieval import retrieve
from .vectorstore import InMemoryVectorStore, Record, embed

app = FastAPI(title="SENTINEL Governance Shell", version="0.1.0")

# --- demo wiring (replace with Postgres RBAC + Pinecone/Milvus in production) ---
_AUDIT = AuditLog()
_TOKENS = {
    "tok-acme-analyst": Principal("u-an", "acme", frozenset({"analyst"}), 2),
    "tok-acme-admin": Principal("u-ad", "acme", frozenset({"admin"}), 5),
    "tok-beta-analyst": Principal("u-bn", "beta", frozenset({"analyst"}), 2),
}
_DOCS = [
    ("a-public", "acme", 1, ["analyst", "admin"], "acme quarterly revenue report", "s3://acme/q.pdf"),
    ("a-secret", "acme", 5, ["admin"], "acme board secret merger memo", "s3://acme/secret.pdf"),
    ("b-public", "beta", 1, ["analyst", "admin"], "beta revenue numbers", "s3://beta/q.pdf"),
]
_RBAC = InMemoryRBAC([DocumentACL(d[0], d[1], d[2], frozenset(d[3])) for d in _DOCS])
_VSTORE = InMemoryVectorStore()
for _d in _DOCS:
    _VSTORE.upsert(
        f"tenant::{_d[1]}",
        [Record(_d[0], embed(_d[4]), {
            "doc_id": _d[0], "tenant_id": _d[1], "sensitivity": _d[2],
            "allowed_roles": frozenset(_d[3]), "text": _d[4], "source": _d[5],
        })],
    )


class RetrieveRequest(BaseModel):
    query: str
    k: int = 5
    request_confidence: float = 0.9
    # NOTE: deliberately no tenant/role/clearance fields — those come from auth.


def principal_from_token(authorization: Optional[str] = Header(default=None)) -> Principal:
    token = (authorization or "").removeprefix("Bearer ").strip()
    principal = _TOKENS.get(token)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")
    return principal


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "audit_intact": _AUDIT.verify()}


@app.post("/v1/retrieve")
def v1_retrieve(req: RetrieveRequest, principal: Principal = Depends(principal_from_token)) -> dict:
    resp = retrieve(
        principal, req.query,
        vstore=_VSTORE, rbac=_RBAC, audit=_AUDIT,
        k=req.k, request_confidence=req.request_confidence,
    )
    return {
        "decision": resp.decision.value,
        "reasons": list(resp.reasons),
        "threat_score": resp.threat_score,
        "chunks": [
            {"doc_id": c.doc_id, "text": c.text, "score": round(c.score, 4),
             "sensitivity": c.sensitivity, "source": c.source}
            for c in resp.chunks
        ],
        "provenance": [
            {"doc_id": p.doc_id, "source": p.source, "confidence": p.confidence.value}
            for p in resp.provenance
        ],
    }
