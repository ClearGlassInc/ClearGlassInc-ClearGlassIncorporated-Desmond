# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""Controlled vocabulary for ClearGlass Truth Forensics.

Every status the engine can emit is listed here, so no module invents a new
word for certainty. `assets/js/truth-forensics-engine.js` carries the same
tables; `tests/test_truth_forensics_parity.py` fails if they drift.
"""
from __future__ import annotations

ENGINE_NAME = "clearglass-truth-forensics"
ENGINE_VERSION = "1.0.0"
CASE_SCHEMA = "clearglass.truth-forensics.case/1"
RESULT_SCHEMA = "clearglass.truth-forensics.result/1"

# Evidence status after analysis and human review.
VERIFIED = "VERIFIED"
SUPPORTED = "SUPPORTED"
INCONCLUSIVE = "INCONCLUSIVE"
UNVERIFIED = "UNVERIFIED"
SIMULATED = "SIMULATED"
EVIDENCE_STATUSES = (VERIFIED, SUPPORTED, INCONCLUSIVE, UNVERIFIED, SIMULATED)

# Claim and proposition verdicts.
PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
CONTRADICTED = "CONTRADICTED"
CLAIM_VERDICTS = (SUPPORTED, PARTIALLY_SUPPORTED, CONTRADICTED, INCONCLUSIVE, UNVERIFIED)

# Finding / anomaly states.
NORMAL = "NORMAL"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
ANOMALY_DETECTED = "ANOMALY_DETECTED"
CORROBORATION_CONFLICT = "CORROBORATION_CONFLICT"
PROVENANCE_GAP = "PROVENANCE_GAP"
CRYPTOGRAPHICALLY_VERIFIED = "CRYPTOGRAPHICALLY_VERIFIED"
STATES = (
    NORMAL,
    REVIEW_REQUIRED,
    ANOMALY_DETECTED,
    CORROBORATION_CONFLICT,
    PROVENANCE_GAP,
    INCONCLUSIVE,
    CRYPTOGRAPHICALLY_VERIFIED,
)

# Job states for the intake -> analysis -> review pipeline.
JOB_STATES = ("QUEUED", "PROCESSING", "ANALYZING", "REVIEW_REQUIRED", "COMPLETE", "FAILED")

# Confidence is a label with a documented rule behind it, never a percentage.
CONFIDENCE = ("NONE", "LOW", "MODERATE", "HIGH")

# Evidence object kinds. An original is never modified; every transformation
# produces a new DERIVATIVE with its own hash.
ORIGINAL = "ORIGINAL"
DERIVATIVE = "DERIVATIVE"
ANALYSIS_RESULT = "ANALYSIS_RESULT"
OBJECT_KINDS = (ORIGINAL, DERIVATIVE, ANALYSIS_RESULT)

SOURCE_TYPES = ("image", "video", "audio", "document", "url", "text", "event", "manual")

# Report statements are always one of these three.
STATEMENT_KINDS = ("OBSERVATION", "INTERPRETATION", "CONCLUSION")

# Indicator categories (adversarial media analysis, section 10 of the spec).
CATEGORIES = ("SPATIAL", "TEMPORAL", "SYNTHETIC", "AUDIO", "METADATA", "CONTAINER", "PROVENANCE")

# Evidence-graph relation bases. A relation the engine recorded itself is
# FACTUAL; anything read from metadata, asserted by an analyst or produced by
# an analyzer is an INFERENCE and is rendered as one.
FACTUAL = "FACTUAL"
INFERENCE = "INFERENCE"

PIPELINE = (
    "SOURCE",
    "ACQUISITION",
    "HASH",
    "PROVENANCE",
    "METADATA",
    "CONTENT_ANALYSIS",
    "TEMPORAL_ANALYSIS",
    "CROSS_SOURCE_CORRELATION",
    "MANIPULATION_INDICATORS",
    "CONFIDENCE_ASSESSMENT",
    "EVIDENCE_GRAPH",
    "AUDIT_RECORD",
    "HUMAN_REVIEW",
)

DISCLAIMER = (
    "The ClearGlass Truth Forensics system provides analytical indicators and provenance "
    "analysis. It does not independently establish the truth of real-world events and should "
    "not replace qualified forensic, legal, investigative, or evidentiary review."
)
BIFOCAL_DISCLAIMER = "This score is an analytical heuristic and is not proof of authenticity."
CRYPTO_NOTE = (
    "Cryptographic verification proves integrity relative to a known hash or signature. It does "
    "not prove that the content depicts what it claims to depict."
)
INDICATORS_FOUND = "Manipulation indicators detected; human review required."
NO_INDICATORS = (
    "No manipulation indicators detected by the available analyzers. Authenticity cannot be "
    "established solely from this analysis."
)
DEMO_LABEL = "DEMONSTRATION DATA — NOT REAL EVIDENCE"
