"""SENTINEL — Phase-One permission-aware retrieval pipeline.

The trust loop, end to end:

  1. Ingest  : score the query for adversarial intent (S_threat), fail-closed.
  2. Resolve : fetch P_user from RBAC authority, fail-closed (outage -> None).
  3. Gate    : Governance Shell boolean (C >= tau ∧ scope-resolved ∧ S < eps).
  4. Partition: select tenant namespace SERVER-SIDE from the principal.
  5. Filter  : build fail-closed ACL pre-filter (deny-all if P_user is None).
  6. Query   : vector store returns candidates (optimization only).
  7. RE-AUTHORIZE: every returned doc_id is re-checked against RBAC — the
                   authoritative gate. Poisoned/leaked candidates are dropped.
  8. Assemble: attach provenance + confidence band.
  9. Audit   : append every step to the hash-chained log.

Returns a RetrieveResponse whose ``chunks`` are guaranteed ⊆ P_user.
"""
from __future__ import annotations

from typing import Optional

from .audit import AuditLog
from .governance import assess
from .models import (
    AssuranceThresholds,
    Chunk,
    Confidence,
    Decision,
    Principal,
    Provenance,
    RetrieveResponse,
)
from .rbac import RBACAuthority, RBACError
from .redteam import HeuristicRedTeam, ThreatScorer
from .vectorstore import AclFilter, VectorStore, embed, tenant_namespace


def retrieve(
    principal: Principal,
    query: str,
    *,
    vstore: VectorStore,
    rbac: RBACAuthority,
    audit: AuditLog,
    k: int = 5,
    request_confidence: float = 0.9,
    redteam: Optional[ThreatScorer] = None,
    thresholds: AssuranceThresholds = AssuranceThresholds(),
) -> RetrieveResponse:
    redteam = redteam or HeuristicRedTeam()
    actor = f"{principal.tenant_id}/{principal.user_id}"

    # 1. adversarial scoring (fail-closed)
    try:
        threat = redteam.score(query)
    except Exception:
        threat = None

    # 2. resolve P_user (fail-closed: outage -> unverifiable, not "empty")
    try:
        boundary = rbac.permission_boundary(principal)
        scope_resolved: Optional[bool] = True
    except RBACError:
        boundary = None
        scope_resolved = None  # unverifiable -> Governance Shell denies fail-closed

    # 3. Governance Shell gate
    decision = assess(
        confidence=request_confidence,
        threat_score=threat,
        data_in_scope=scope_resolved,
        thresholds=thresholds,
    )
    audit.record(
        actor=actor,
        action="assurance_gate",
        detail={
            "query_tokens": len(query.split()),
            "decision": decision.decision.value,
            "reasons": list(decision.reasons),
            "threat": threat,
            "confidence": request_confidence,
        },
    )
    if not decision.permitted:
        return RetrieveResponse(decision.decision, decision.reasons, threat_score=threat)

    # 4-5. tenant partition (server-side) + fail-closed ACL filter
    namespace = tenant_namespace(principal)
    acl = AclFilter.from_boundary(boundary)

    # 6. candidate retrieval (optimization)
    hits = vstore.query(namespace=namespace, vector=embed(query), k=k, acl=acl)

    # 7. AUTHORITATIVE re-authorization against RBAC
    try:
        allowed_ids = rbac.authorize_documents(principal, [h.doc_id for h in hits])
    except RBACError:
        audit.record(actor=actor, action="reauthorize", detail={"error": "rbac_unavailable_failclosed"})
        return RetrieveResponse(
            Decision.DENIED,
            ("re-authorization unavailable (fail-closed)",),
            threat_score=threat,
        )

    chunks: list[Chunk] = []
    provenance: list[Provenance] = []
    dropped = 0
    for h in hits:
        # defense-in-depth: tenant match AND authoritative grant
        if h.tenant_id != principal.tenant_id or h.doc_id not in allowed_ids:
            dropped += 1
            continue
        chunks.append(Chunk(h.doc_id, h.text, h.score, h.tenant_id, h.sensitivity, h.source))
        provenance.append(
            Provenance(h.doc_id, h.source, h.score, h.sensitivity, Confidence.band(h.score))
        )

    audit.record(
        actor=actor,
        action="retrieve",
        detail={
            "namespace": namespace,
            "candidates": len(hits),
            "returned": len(chunks),
            "dropped_by_reauth": dropped,
            "doc_ids": [c.doc_id for c in chunks],
        },
    )
    return RetrieveResponse(Decision.PERMITTED, ("authorized",), chunks, provenance, threat)
