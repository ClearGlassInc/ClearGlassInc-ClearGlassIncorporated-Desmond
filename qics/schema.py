"""QICS provenance, scoring, and decision schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ValidityStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    STALE = "STALE"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


class SourceTier(str, Enum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"
    TIER_4 = "TIER_4"


class ConfidenceMethod(str, Enum):
    BUNDLED_CATALOG = "bundled_catalog"
    INVENTORY_SCAN = "inventory_scan"
    HUMAN_REVIEW = "human_review"
    LIVE_FETCH = "live_fetch"
    MODEL_HYPOTHESIS = "model_hypothesis"


class ExposureRating(str, Enum):
    LOW_EXPOSURE = "LOW_EXPOSURE"
    MODERATE_EXPOSURE = "MODERATE_EXPOSURE"
    HIGH_EXPOSURE = "HIGH_EXPOSURE"
    CRITICAL_EXPOSURE = "CRITICAL_EXPOSURE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class OpportunityKind(str, Enum):
    OBSERVED = "OBSERVED_OPPORTUNITY"
    DERIVED = "DERIVED_OPPORTUNITY"
    HYPOTHETICAL = "HYPOTHETICAL_OPPORTUNITY"


class FailClosed(str, Enum):
    UNVERIFIED_CLAIM = "UNVERIFIED_CLAIM"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INSUFFICIENT_BASELINE_DATA = "INSUFFICIENT_BASELINE_DATA"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    VALIDATION_REQUIRED = "VALIDATION_REQUIRED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    TENANT_REQUIRED = "TENANT_REQUIRED"


QUANTUM_VULNERABLE_PUBLIC_KEY = frozenset(
    {
        "rsa",
        "rsa-1024",
        "rsa-2048",
        "rsa-3072",
        "rsa-4096",
        "ecdsa",
        "ecdsa-p256",
        "ecdsa-p384",
        "ecdsa-p521",
        "ecdh",
        "ecdh-p256",
        "ecdh-p384",
        "x25519",
        "ed25519",
        "dsa",
        "dh",
    }
)

SYMMETRIC_CLASSICAL = frozenset(
    {"aes-128", "aes-256", "aes-128-gcm", "aes-256-gcm", "chacha20-poly1305"}
)

PQC_STANDARDIZED = frozenset(
    {
        "ml-kem",
        "ml-kem-512",
        "ml-kem-768",
        "ml-kem-1024",
        "ml-dsa",
        "ml-dsa-44",
        "ml-dsa-65",
        "ml-dsa-87",
        "slh-dsa",
        "slh-dsa-sha2-128s",
        "slh-dsa-sha2-128f",
        "slh-dsa-shake-128s",
    }
)


@dataclass(frozen=True)
class EvidenceItem:
    source_id: str
    source_type: str
    source_url: str
    publisher: str
    publication_date: str
    retrieved_at: str
    content_hash: str
    evidence_timestamp: str
    claim: str
    claim_type: str
    confidence: float
    confidence_method: str
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]
    jurisdiction: str
    technology_scope: str
    validity_status: str
    review_status: str
    source_tier: str
    tenant_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoreBreakdown:
    rating: str
    methodology: str
    inputs: dict[str, Any]
    calculation: str
    evidence_ids: list[str]
    timestamp: str
    confidence: float
    limitations: list[str]
    tenant_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Recommendation:
    current_state: str
    target_state: str
    rationale: str
    evidence_ids: list[str]
    dependencies: list[str]
    compatibility_considerations: list[str]
    migration_risk: str
    rollback_considerations: list[str]
    validation_requirements: list[str]
    human_approval_required: bool
    tenant_id: str
    status: str = "PENDING_APPROVAL"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Opportunity:
    kind: str
    title: str
    assumption_list: list[str]
    financial_projection_guaranteed: bool
    classical_baseline: dict[str, Any] | None
    tenant_id: str
    status: str = "OK"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ApprovalRecord:
    request_id: str
    actor: str
    role: str
    action: str
    reason: str
    timestamp: str
    evidence_version: str
    decision: str
    previous_state: str
    new_state: str
    tenant_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditEvent:
    event_id: str
    timestamp: str
    tenant_id: str
    actor: str
    agent: str
    action: str
    input_hash: str
    evidence_hash: str
    previous_state: str
    new_state: str
    decision: str
    confidence: float
    approval_reference: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Inventory:
    tenant_id: str
    assets: list[dict[str, Any]] = field(default_factory=list)
    inventory_complete: bool = False
    long_lived_sensitive_data: bool | None = None
    crypto_agile: bool | None = None
