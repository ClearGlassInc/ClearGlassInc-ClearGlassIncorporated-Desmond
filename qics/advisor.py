"""Post-quantum advisor. Recommendations always require human approval."""

from __future__ import annotations

from .schema import ExposureRating, Recommendation, ScoreBreakdown


def advise(score: ScoreBreakdown) -> list[Recommendation]:
    tenant_id = score.tenant_id
    if score.rating == ExposureRating.INSUFFICIENT_DATA.value:
        return [
            Recommendation(
                current_state=score.rating,
                target_state="COMPLETE_INVENTORY",
                rationale="No complete algorithm inventory; migration advice would be a guess.",
                evidence_ids=score.evidence_ids,
                dependencies=["cryptographic asset register"],
                compatibility_considerations=[],
                migration_risk="unknown",
                rollback_considerations=[],
                validation_requirements=["Declare algorithms, key locations, and data lifetimes."],
                human_approval_required=True,
                tenant_id=tenant_id,
                status="INSUFFICIENT_DATA",
            )
        ]

    recs: list[Recommendation] = []
    vuln = list(score.inputs.get("vulnerable_public_key") or [])
    if vuln:
        recs.append(
            Recommendation(
                current_state=",".join(sorted(set(vuln))),
                target_state="Investigate hybrid TLS and ML-KEM (FIPS 203) for key establishment; ML-DSA or SLH-DSA (FIPS 204/205) for signatures.",
                rationale=(
                    "Declared public-key algorithms are in the Shor-vulnerable class. "
                    "NIST finalized FIPS 203/204/205 on 2024-08-13. This is an investigation "
                    "path, not an executed migration and not a compliance statement."
                ),
                evidence_ids=["nist-fips-203", "nist-fips-204", "nist-fips-205", *score.evidence_ids],
                dependencies=["certificate inventory", "library support", "client compatibility"],
                compatibility_considerations=[
                    "TLS stacks and devices may not yet negotiate ML-KEM.",
                    "Hybrid classical+PQC is often required during transition.",
                ],
                migration_risk="high" if score.rating == ExposureRating.CRITICAL_EXPOSURE.value else "medium",
                rollback_considerations=[
                    "Keep classical algorithms available until interoperability is measured.",
                    "Do not cut over production cryptography without an approved change window.",
                ],
                validation_requirements=[
                    "Interop test against current clients.",
                    "Confirm library versions against the FIPS document, not against an LLM summary.",
                ],
                human_approval_required=True,
                tenant_id=tenant_id,
            )
        )
    else:
        recs.append(
            Recommendation(
                current_state=score.rating,
                target_state="MAINTAIN_INVENTORY_AND_WATCH_STANDARDS",
                rationale="No Shor-vulnerable public-key algorithms were declared. Continue inventory hygiene.",
                evidence_ids=score.evidence_ids,
                dependencies=[],
                compatibility_considerations=[],
                migration_risk="low",
                rollback_considerations=[],
                validation_requirements=["Re-scan when libraries or certificates change."],
                human_approval_required=True,
                tenant_id=tenant_id,
            )
        )
    return recs
