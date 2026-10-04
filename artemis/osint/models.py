from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, Field


class SourceDefinition(BaseModel):
    source_id: str
    name: str
    categories: list[str]
    integration_mode: str
    public_api: str
    authentication: str
    auth_env: str | None = None
    rate_limit: str
    rate_limit_rps: float | None = None
    license: str
    terms_concern: str
    metadata: list[str]
    update_frequency: str
    ingestion_method: str
    endpoint: str | None = None
    adapter: str
    value: str
    risk_level: str
    integration_reliability_score: int = Field(ge=0, le=100)
    integration_complexity: str
    effort_days: str
    phase: int
    enabled_by_default: bool = False


class ProvenanceRecord(BaseModel):
    source_id: str
    source_name: str
    source_url: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    retrieved_via: str
    parser_version: str
    content_sha256: str
    etag: str | None = None
    last_modified: str | None = None
    license_snapshot: str
    terms_snapshot: str
    raw_reference: str | None = None

    @classmethod
    def from_payload(
        cls,
        source: SourceDefinition,
        payload: Any,
        *,
        retrieved_via: str,
        parser_version: str = "1.0.0",
        source_url: str | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> "ProvenanceRecord":
        encoded = repr(payload).encode("utf-8")
        return cls(
            source_id=source.source_id,
            source_name=source.name,
            source_url=source_url or source.endpoint,
            retrieved_via=retrieved_via,
            parser_version=parser_version,
            content_sha256=sha256(encoded).hexdigest(),
            etag=etag,
            last_modified=last_modified,
            license_snapshot=source.license,
            terms_snapshot=source.terms_concern,
        )


class LocationRecord(BaseModel):
    location_id: str
    latitude: float
    longitude: float
    geometry_type: str = "Point"
    properties: dict[str, Any] = Field(default_factory=dict)


class ObservationRecord(BaseModel):
    observation_id: str
    source_id: str
    observed_at: datetime
    kind: str
    value: Any
    location: LocationRecord | None = None
    provenance: ProvenanceRecord
    confidence: float | None = Field(default=None, ge=0, le=1)


class EventRecord(BaseModel):
    event_id: str
    source_id: str
    event_type: str
    occurred_at: datetime
    title: str | None = None
    location: LocationRecord | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceRecord
