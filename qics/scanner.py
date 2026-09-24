"""Quantum-readiness scanner over an explicit cryptographic inventory.

No inventory -> INSUFFICIENT_DATA. Never emits "quantum safe."
"""

from __future__ import annotations

from .evidence import require_tenant, utc_now
from .schema import (
    PQC_STANDARDIZED,
    QUANTUM_VULNERABLE_PUBLIC_KEY,
    SYMMETRIC_CLASSICAL,
    ExposureRating,
    Inventory,
    ScoreBreakdown,
)


def _norm(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def scan_inventory(inventory: Inventory) -> ScoreBreakdown:
    tenant_id = require_tenant(inventory.tenant_id)
    now = utc_now()
    assets = inventory.assets or []

    if not assets:
        return ScoreBreakdown(
            rating=ExposureRating.INSUFFICIENT_DATA.value,
            methodology=(
                "Count public-key algorithms that are in the Shor-vulnerable class "
                "(RSA, finite-field DH, ECDH, ECDSA, Ed25519, X25519) versus "
                "NIST FIPS 203/204/205 names. Incomplete inventories fail closed."
            ),
            inputs={"asset_count": len(assets), "inventory_complete": inventory.inventory_complete},
            calculation="no usable inventory -> INSUFFICIENT_DATA",
            evidence_ids=[],
            timestamp=now,
            confidence=0.0,
            limitations=["Scanner does not probe live hosts. It only scores declared assets."],
            tenant_id=tenant_id,
        )

    vuln = []
    pqc = []
    symmetric = []
    unknown = []
    for asset in assets:
        algo = _norm(str(asset.get("algorithm") or ""))
        if not algo:
            unknown.append(asset)
        elif algo in QUANTUM_VULNERABLE_PUBLIC_KEY:
            vuln.append(algo)
        elif algo in PQC_STANDARDIZED:
            pqc.append(algo)
        elif algo in SYMMETRIC_CLASSICAL:
            symmetric.append(algo)
        else:
            unknown.append(algo)

    long_lived = bool(inventory.long_lived_sensitive_data)
    complete = bool(inventory.inventory_complete)
    agile = inventory.crypto_agile is True

    if unknown and not complete:
        rating = ExposureRating.INSUFFICIENT_DATA
        calc = "unknown algorithms present and inventory marked incomplete"
        confidence = 0.2
    elif vuln and long_lived:
        rating = ExposureRating.CRITICAL_EXPOSURE
        calc = f"{len(vuln)} Shor-vulnerable public-key assets + long-lived sensitive data"
        confidence = 0.85 if complete else 0.55
    elif vuln and not agile:
        rating = ExposureRating.HIGH_EXPOSURE
        calc = f"{len(vuln)} Shor-vulnerable public-key assets and crypto_agile is not true"
        confidence = 0.8 if complete else 0.5
    elif vuln:
        rating = ExposureRating.MODERATE_EXPOSURE
        calc = f"{len(vuln)} Shor-vulnerable public-key assets; crypto-agility declared"
        confidence = 0.75 if complete else 0.45
    elif pqc and not vuln:
        rating = ExposureRating.LOW_EXPOSURE
        calc = f"{len(pqc)} PQC-named assets and 0 Shor-vulnerable public-key assets"
        confidence = 0.7 if complete else 0.4
    else:
        rating = ExposureRating.INSUFFICIENT_DATA
        calc = "no classified public-key algorithms"
        confidence = 0.2

    limitations = [
        "Does not prove algorithms are correctly implemented.",
        "Does not inspect certificate chains or HSMs.",
        "Symmetric algorithms are recorded but do not by themselves produce LOW_EXPOSURE.",
        "LOW_EXPOSURE is not a certification and is not 'quantum safe.'",
    ]
    if not complete:
        limitations.append("Inventory is incomplete; rating confidence is reduced.")

    return ScoreBreakdown(
        rating=rating.value,
        methodology=(
            "Classify each declared algorithm against frozen sets "
            "QUANTUM_VULNERABLE_PUBLIC_KEY, PQC_STANDARDIZED, SYMMETRIC_CLASSICAL. "
            "Escalate when long-lived data or missing crypto-agility is declared."
        ),
        inputs={
            "asset_count": len(assets),
            "vulnerable_public_key": vuln,
            "pqc_named": pqc,
            "symmetric": symmetric,
            "unknown": unknown,
            "long_lived_sensitive_data": inventory.long_lived_sensitive_data,
            "crypto_agile": inventory.crypto_agile,
            "inventory_complete": inventory.inventory_complete,
        },
        calculation=calc,
        evidence_ids=["inventory-declaration"],
        timestamp=now,
        confidence=confidence,
        limitations=limitations,
        tenant_id=tenant_id,
    )
