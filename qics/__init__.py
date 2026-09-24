"""ClearGlass Quantum Intelligence Command System (QICS) v2.0.

A fail-closed, evidence-first intelligence layer. It does not talk to a
quantum computer, does not claim quantum advantage, and does not mark a
tenant "quantum safe."

This package is stdlib-only so it can run without the control-plane
runtime. Control-plane approvals and the append-only Event ledger remain
the production gates when that service is deployed.
"""

from .schema import (
    ConfidenceMethod,
    EvidenceItem,
    ExposureRating,
    OpportunityKind,
    ValidityStatus,
)

__version__ = "2.0.0"
__all__ = [
    "ConfidenceMethod",
    "EvidenceItem",
    "ExposureRating",
    "OpportunityKind",
    "ValidityStatus",
    "__version__",
]
