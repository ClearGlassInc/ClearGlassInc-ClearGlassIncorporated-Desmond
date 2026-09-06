from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class Mission(str, Enum):
    RECON = "recon"
    ASSOCIATION = "association"
    PATTERN = "pattern"
    COMPLIANCE = "compliance"
    RISK_BRIEF = "risk_brief"


class Domain(str, Enum):
    WEB = "web"
    CORPORATE = "corporate"
    LEGAL = "legal"
    FINANCIAL = "financial"
    CYBER = "cyber"
    VENDOR = "vendor"
    NEWS = "news"


class SourceCategory(str, Enum):
    PUBLIC_WEB = "public_web"
    PUBLIC_REGISTRY = "public_registry"
    VENDOR_ADVISORY = "vendor_advisory"
    NEWS = "news"
    NVD = "nvd"
    CISA_KEV = "cisa_kev"
    INTERNAL_AUTHORIZED = "internal_authorized"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Impact(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SignalConstraint(BaseModel):
    sources: list[SourceCategory] = Field(default_factory=list)
    time_window: str = Field(default="past_30_days", min_length=3, max_length=80)
    jurisdiction: str = Field(default="US", min_length=2, max_length=40)
    max_results: int = Field(default=25, ge=1, le=100)
    lawful_basis: str = Field(default="public-source risk analysis", min_length=8, max_length=160)


class SignalPacket(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    target: str = Field(..., min_length=2, max_length=180)
    mission: Mission
    domain: Domain
    constraints: SignalConstraint = Field(default_factory=SignalConstraint)
    analyst_note: str | None = Field(default=None, max_length=500)

    @field_validator("target")
    @classmethod
    def reject_private_targeting_language(cls, value: str) -> str:
        banned = ["dox", "stalk", "track person", "private messages", "intercept", "wiretap"]
        lowered = value.lower()
        if any(term in lowered for term in banned):
            raise ValueError("target contains disallowed private-targeting language")
        return value.strip()


class EvidenceItem(BaseModel):
    source: SourceCategory
    title: str
    summary: str
    freshness: str
    confidence: int = Field(..., ge=0, le=100)
    url: str | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Finding(BaseModel):
    title: str
    impact: Impact
    confidence: int = Field(..., ge=0, le=100)
    rationale: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    recommended_action: str


class AgentReport(BaseModel):
    request_id: UUID
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    owner: Literal["ClearGlassInc"] = "ClearGlassInc"
    mission: Mission
    domain: Domain
    target: str
    executive_summary: str
    findings: list[Finding]
    compliance_note: str
    audit: dict[str, Any]


class HealthResponse(BaseModel):
    service: str = "clearglass-agent-service"
    status: Literal["ok"] = "ok"
    version: str
    utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
