"""SENTINEL — RBAC authority (the *authoritative* access gate).

The vector store's metadata filter is an optimization that narrows the
candidate set. THIS module is the gate: every retrieved ``doc_id`` is
re-authorized here against the source-of-truth ACL before any chunk is
allowed into the LLM context. A vector-layer bug or poisoned/stale embedding
metadata therefore degrades to "missed results", never "leaked results".

``InMemoryRBAC`` is a runnable reference. ``PostgresRBAC`` is a documented
adapter stub showing the production-equivalent queries (see ``schema.sql``).
All failures raise ``RBACError`` so callers fail-closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from .models import PermissionBoundary, Principal


class RBACError(Exception):
    """Raised when the permission boundary cannot be authoritatively resolved."""


@dataclass(frozen=True)
class DocumentACL:
    doc_id: str
    tenant_id: str
    sensitivity: int
    allowed_roles: frozenset[str]


class RBACAuthority(Protocol):
    def permission_boundary(self, principal: Principal) -> PermissionBoundary: ...

    def authorize_documents(
        self, principal: Principal, doc_ids: Iterable[str]
    ) -> set[str]: ...


class InMemoryRBAC:
    """Reference RBAC backed by an in-memory ACL table.

    Set ``available=False`` to simulate a database outage and prove the
    caller fails closed.
    """

    def __init__(self, acls: Iterable[DocumentACL], *, available: bool = True) -> None:
        self._acls: dict[str, DocumentACL] = {a.doc_id: a for a in acls}
        self.available = available

    def permission_boundary(self, principal: Principal) -> PermissionBoundary:
        if not self.available:
            raise RBACError("RBAC store unavailable")
        return PermissionBoundary(
            tenant_id=principal.tenant_id,
            roles=principal.roles,
            clearance=principal.clearance,
        )

    def authorize_documents(
        self, principal: Principal, doc_ids: Iterable[str]
    ) -> set[str]:
        if not self.available:
            raise RBACError("RBAC store unavailable")
        allowed: set[str] = set()
        for doc_id in doc_ids:
            acl = self._acls.get(doc_id)
            if acl is None:
                continue  # unknown doc -> deny by omission
            if acl.tenant_id != principal.tenant_id:
                continue  # hard tenant boundary
            if acl.sensitivity > principal.clearance:
                continue  # clearance ceiling
            if not (acl.allowed_roles & principal.roles):
                continue  # role intersection required
            allowed.add(doc_id)
        return allowed


class PostgresRBAC:
    """Production adapter stub. Wire to psycopg/asyncpg with a short statement
    timeout; on ANY exception raise ``RBACError`` (never silently allow).

    authorize_documents() should run, parameterized:

        SELECT d.doc_id
        FROM   documents d
        JOIN   doc_acl a   ON a.doc_id = d.doc_id
        WHERE  d.doc_id   = ANY(%(doc_ids)s)
          AND  d.tenant_id = %(tenant_id)s
          AND  d.sensitivity <= %(clearance)s
          AND  a.role = ANY(%(roles)s)

    Returning the intersection of requested doc_ids with the user's grants.
    """

    def __init__(self, dsn: str) -> None:  # pragma: no cover - infra adapter
        self.dsn = dsn

    def permission_boundary(self, principal: Principal) -> PermissionBoundary:  # pragma: no cover
        raise RBACError("PostgresRBAC.permission_boundary not wired in Phase-One scaffold")

    def authorize_documents(self, principal: Principal, doc_ids):  # pragma: no cover
        raise RBACError("PostgresRBAC.authorize_documents not wired in Phase-One scaffold")
