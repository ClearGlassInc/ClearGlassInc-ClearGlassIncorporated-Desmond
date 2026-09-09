# ClearGlass Truth Fabric Forensics

## Purpose

Truth Fabric is a defensive media-integrity and provenance architecture inspired by the problem of surveillance forgery and synthetic media. It is an original ClearGlass implementation and is not an implementation of any fictional program.

## System boundaries

The system is designed to **detect, document and govern uncertainty**. It does not provide covert surveillance, unauthorized access, political manipulation, biometric targeting, or techniques for creating/deploying deceptive media.

## Architecture

```text
                 ┌─────────────────────────┐
                 │ Evidence Intake         │
                 │ media · metadata · hash │
                 └────────────┬────────────┘
                              ↓
                 ┌─────────────────────────┐
                 │ Provenance Ledger        │
                 │ source · time · lineage  │
                 └────────────┬────────────┘
                              ↓
          ┌───────────────────┴──────────────────┐
          ↓                                      ↓
   ┌───────────────┐                      ┌───────────────┐
   │ Channel A     │                      │ Channel B     │
   │ independent   │                      │ independent   │
   └───────┬───────┘                      └───────┬───────┘
           └────────────────┬─────────────────────┘
                            ↓
                 ┌─────────────────────────┐
                 │ Consistency Engine     │
                 │ deterministic checks    │
                 └────────────┬────────────┘
                              ↓
                 ┌─────────────────────────┐
                 │ Analyst / Human Gate    │
                 └────────────┬────────────┘
                              ↓
                 ┌─────────────────────────┐
                 │ Finding + Audit Event   │
                 └─────────────────────────┘
```

## Core controls

- Preserve source evidence; never mutate the original during analysis.
- Hash evidence at intake and record timestamps and source lineage.
- Prefer independent evidence channels where available.
- Separate deterministic integrity checks from probabilistic media-analysis models.
- Treat model output as an input to review, not as proof.
- Require human authorization for material conclusions and actions.
- Keep an append-oriented audit trail with case ID, evidence IDs, policy, result and trace context.
- Fail closed when required evidence or authorization is missing.

## API

`POST /api/truth-fabric/assess` accepts a Zod-validated forensic case and returns a bounded integrity score, status and reasons. The current implementation intentionally performs metadata/provenance consistency checks only; it does not alter or synthesize media.

## Roadmap

1. Evidence manifest and immutable object-storage adapter.
2. Signed provenance attestations.
3. Temporal alignment and metadata anomaly detection.
4. Pluggable synthetic-media classifiers with calibrated evaluation datasets.
5. Analyst review queue and approval ledger.
6. OpenTelemetry-compatible traces and operational metrics.
7. Regression corpus and adversarial evaluation harness.
8. Deployment gates for typecheck, tests, dependency/security scanning and smoke validation.

## Relationship to the supplied series recap

The supplied recap describes fictional concepts including Project Fix, dual-lens capture, Correction and an AI called Simon. Truth Fabric translates the **defensive engineering problem**—how to preserve trustworthy evidence when media can be manipulated—into an original, safety-bounded ClearGlass architecture.
