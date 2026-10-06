# Assumptions and Verification Register

## Verified
- The current repository uses Next.js 15, React 19, TypeScript, and Zod.
- Existing `Principal` authorization checks are tenant-aware.
- Existing request identity resolution is intentionally a placeholder and does not trust client-supplied role headers.
- No database or object-storage provider was found during repository discovery.

## Assumptions selected for the safe vertical slice
- The operations domain can be introduced without changing the existing application architecture.
- An in-memory repository is acceptable only for a synthetic development/test workflow.
- Production persistence and authenticated identity are blockers, not gaps to paper over.
- SHA-256 is suitable for recording byte-level integrity of an ingested file; it is not by itself a legal-admissibility determination.

## Requires external verification before activation
- Telephony, STT, TTS, SMS providers.
- Model and model-weight licenses.
- Vendor account eligibility and regional availability.
- Data retention / deletion semantics.
- Regional processing and data residency.
- Security controls and incident response commitments.
- LPR provider capabilities and lawful source provenance.
- Biometric model licensing, evaluation evidence, calibration, and privacy controls.
- Object-storage immutability/WORM capabilities if stronger integrity guarantees are required.

No vendor is selected or represented as equivalent to police, CAD, RMS, forensic, or biometric systems in this phase.
