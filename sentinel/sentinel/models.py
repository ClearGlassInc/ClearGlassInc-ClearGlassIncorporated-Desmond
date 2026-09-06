"""SENTINEL — domain models for the Phase-One Governance Shell.

Pure stdlib (dataclasses + typing) so the trust loop is testable without any
third-party dependency. The FastAPI layer (``app.py``) is an optional adapter
on top of these types.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Decision(str, Enum):
    PERMITTED = "PERMITTED"
    DENIED = "DENIED"


class Confidence(str, Enum):
    """Calibrated confidence band attached to every answer/recommendation."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNVERIFIED = "UNVERIFIED"

    @staticmethod
    def band(score: Optional[float]) -> "Confidence":
        if score is None:
            return Confidence.UNVERIFIED
        if score >= 0.85:
            return Confidence.HIGH
        if score >= 0.6:
            return Confidence.MEDIUM
        return Confidence.LOW


@dataclass(frozen=True)
class Principal:
    """The authenticated requester. Resolved server-side from the bearer token —
    NEVER from client-supplied tenant/role fields."""

    user_id: str
    tenant_id: str
    roles: frozenset[str]
    clearance: int  # numeric sensitivity ceiling (>= document sensitivity to read)


@dataclass(frozen=True)
class PermissionBoundary:
    """P_user — the authoritative scope, resolved from Postgres RBAC."""

    tenant_id: str
    roles: frozenset[str]
    clearance: int


@dataclass(frozen=True)
class AssuranceThresholds:
    tau: float = 0.60       # minimum agent/query confidence (C >= tau)
    epsilon: float = 0.50   # maximum adversarial-injection score (S_threat < epsilon)


@dataclass(frozen=True)
class AssuranceDecision:
    """Output of the Governance Shell boolean gate. Always carries rationale."""

    decision: Decision
    reasons: tuple[str, ...]
    confidence: Optional[float] = None
    threat_score: Optional[float] = None

    @property
    def permitted(self) -> bool:
        return self.decision is Decision.PERMITTED


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    text: str
    score: float            # retrieval similarity
    tenant_id: str
    sensitivity: int
    source: str             # provenance pointer (file/url/log path)


@dataclass(frozen=True)
class Provenance:
    doc_id: str
    source: str
    score: float
    sensitivity: int
    confidence: Confidence


@dataclass
class RetrieveResponse:
    decision: Decision
    reasons: tuple[str, ...]
    chunks: list[Chunk] = field(default_factory=list)
    provenance: list[Provenance] = field(default_factory=list)
    threat_score: Optional[float] = None

    @property
    def permitted(self) -> bool:
        return self.decision is Decision.PERMITTED
