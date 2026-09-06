from datetime import datetime, timezone

from artemis_platform.self_evolving_platform import (
    CryptographicAsset,
    advise_post_quantum_migration,
    post_quantum_readiness_score,
)


def test_pqc_advisor_prioritizes_external_rsa_long_lived_secret() -> None:
    asset = CryptographicAsset(
        asset_id="api-gateway-cert-1",
        owner="platform-security",
        algorithm="RSA",
        key_size_bits=2048,
        protocol="TLS",
        data_classification="CUI",
        stores_long_lived_secrets=True,
        external_exposure=True,
        business_criticality=0.94,
        certificate_expires_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        evidence_refs=("foundry.crypto_inventory.api_gateway", "ct-log:leaf-42"),
    )

    finding = advise_post_quantum_migration(asset)

    assert finding.urgency == "migrate"
    assert finding.risk_score >= 0.78
    assert "ML-KEM/ML-DSA" in finding.recommended_target
    assert finding.evidence_sources == asset.evidence_refs
    assert "algorithm=RSA" in finding.confidence_drivers


def test_pqc_advisor_monitors_standardized_pqc_asset() -> None:
    asset = CryptographicAsset(
        asset_id="service-mesh-hybrid-1",
        owner="platform-security",
        algorithm="ML-KEM",
        key_size_bits=768,
        protocol="TLS",
        data_classification="CUI",
        stores_long_lived_secrets=False,
        external_exposure=False,
        business_criticality=0.8,
    )

    assert post_quantum_readiness_score(asset) < 0.3
    assert advise_post_quantum_migration(asset).urgency == "monitor"
