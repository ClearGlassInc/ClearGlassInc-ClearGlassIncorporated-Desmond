"""Bundled Tier-1 references. Not a live connector.

Entries are PARTIALLY_VERIFIED: the URLs and titles match official NIST/CISA
pages retrieved during authoring (2026-09-24). QICS does not claim a live
fetch succeeded until connectors.fetch_source returns a verified body.
"""

from __future__ import annotations

from .evidence import content_hash, utc_now
from .schema import EvidenceItem, SourceTier, ValidityStatus

BUNDLED_SOURCES: tuple[dict[str, str], ...] = (
    {
        "source_id": "nist-fips-203",
        "source_url": "https://csrc.nist.gov/pubs/fips/203/final",
        "publisher": "NIST",
        "publication_date": "2024-08-13",
        "claim": "FIPS 203 specifies ML-KEM (Module-Lattice-Based Key-Encapsulation Mechanism).",
        "claim_type": "pqc_standard_kem",
        "technology_scope": "ML-KEM",
        "jurisdiction": "US",
    },
    {
        "source_id": "nist-fips-204",
        "source_url": "https://csrc.nist.gov/pubs/fips/204/final",
        "publisher": "NIST",
        "publication_date": "2024-08-13",
        "claim": "FIPS 204 specifies ML-DSA (Module-Lattice-Based Digital Signature Algorithm).",
        "claim_type": "pqc_standard_signature",
        "technology_scope": "ML-DSA",
        "jurisdiction": "US",
    },
    {
        "source_id": "nist-fips-205",
        "source_url": "https://csrc.nist.gov/pubs/fips/205/final",
        "publisher": "NIST",
        "publication_date": "2024-08-13",
        "claim": "FIPS 205 specifies SLH-DSA (Stateless Hash-Based Digital Signature Algorithm).",
        "claim_type": "pqc_standard_signature_backup",
        "technology_scope": "SLH-DSA",
        "jurisdiction": "US",
    },
    {
        "source_id": "nist-pqc-announcement-2024-08-13",
        "source_url": "https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards",
        "publisher": "NIST",
        "publication_date": "2024-08-13",
        "claim": "NIST finalized three PQC FIPS on 2024-08-13: FIPS 203/204/205.",
        "claim_type": "pqc_publication_event",
        "technology_scope": "PQC",
        "jurisdiction": "US",
    },
    {
        "source_id": "cisa-quantum",
        "source_url": "https://www.cisa.gov/quantum",
        "publisher": "CISA",
        "publication_date": "2023-01-01",
        "claim": "CISA publishes quantum-readiness guidance for critical infrastructure.",
        "claim_type": "pqc_guidance",
        "technology_scope": "PQC-migration-planning",
        "jurisdiction": "US",
    },
)


def bundled_catalog(tenant_id: str) -> list[EvidenceItem]:
    now = utc_now()
    items: list[EvidenceItem] = []
    for row in BUNDLED_SOURCES:
        body = {**row, "bundled": True}
        items.append(
            EvidenceItem(
                source_id=row["source_id"],
                source_type="bundled_official_reference",
                source_url=row["source_url"],
                publisher=row["publisher"],
                publication_date=row["publication_date"],
                retrieved_at=now,
                content_hash=content_hash(body),
                evidence_timestamp=now,
                claim=row["claim"],
                claim_type=row["claim_type"],
                confidence=0.7,
                confidence_method="bundled_catalog",
                supporting_evidence=(row["source_url"],),
                contradicting_evidence=(),
                jurisdiction=row["jurisdiction"],
                technology_scope=row["technology_scope"],
                validity_status=ValidityStatus.PARTIALLY_VERIFIED.value,
                review_status="catalog",
                source_tier=SourceTier.TIER_1.value,
                tenant_id=tenant_id,
            )
        )
    return items
