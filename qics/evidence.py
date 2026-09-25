"""Provenance helpers. AI text is a hypothesis until evidence is attached."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from .schema import EvidenceItem, SourceTier, ValidityStatus


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def content_hash(payload: Any) -> str:
    raw = payload if isinstance(payload, (bytes, bytearray)) else json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def require_tenant(tenant_id: str | None) -> str:
    if not tenant_id or not str(tenant_id).strip():
        raise PermissionError("TENANT_REQUIRED")
    return str(tenant_id).strip()


def assert_same_tenant(object_tenant: str, request_tenant: str) -> None:
    if object_tenant != request_tenant:
        raise PermissionError("TENANT_ISOLATION_VIOLATION")


def hypothesis_item(*, tenant_id: str, claim: str, actor: str) -> EvidenceItem:
    """Model output is UNVERIFIED until a Tier 1-3 source is attached."""
    now = utc_now()
    return EvidenceItem(
        source_id=f"hypothesis:{content_hash(claim)[7:19]}",
        source_type="model_hypothesis",
        source_url="",
        publisher=actor,
        publication_date=now[:10],
        retrieved_at=now,
        content_hash=content_hash({"claim": claim, "actor": actor}),
        evidence_timestamp=now,
        claim=claim,
        claim_type="hypothesis",
        confidence=0.0,
        confidence_method="model_hypothesis",
        supporting_evidence=(),
        contradicting_evidence=(),
        jurisdiction="unspecified",
        technology_scope="unspecified",
        validity_status=ValidityStatus.UNVERIFIED.value,
        review_status="REQUIRES_REVIEW",
        source_tier=SourceTier.TIER_4.value,
        tenant_id=tenant_id,
    )


def detect_conflicts(items: list[EvidenceItem]) -> list[EvidenceItem]:
    """If two Tier-1 items contradict the same claim_type, mark both for review."""
    by_type: dict[str, list[EvidenceItem]] = {}
    for item in items:
        by_type.setdefault(item.claim_type, []).append(item)
    flagged: list[EvidenceItem] = []
    for group in by_type.values():
        claims = {i.claim for i in group}
        tiers = {i.source_tier for i in group}
        if len(claims) > 1 and SourceTier.TIER_1.value in tiers:
            flagged.extend(group)
    return flagged
