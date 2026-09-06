# ClearPulse — Healthcare Intelligence Pipeline Architecture

> Real-time fraud, insider-threat, and PHI-exposure detection for healthcare
> environments. Every alert is traceable from dashboard back to the originating
> byte.

## 1. Design Pillars

1. **Traceability-first** — an immutable `trace_id` (UUID7) is attached at
   ingestion and propagated through every stage: parse, score, correlate,
   alert, dashboard, forensic replay.
2. **Explainable scoring** — every Risk Envelope carries the rule weights,
   contributing facts, and source events that produced its score.
3. **Unified signal plane** — billing anomalies, user-behavior anomalies, and
   at-rest PHI exposures converge into one alert stream and one investigation
   graph.

## 2. Pipeline Overview

```text
  FHIR / HL7 / 837 Claims
            │
            ▼
   ┌────────────────────┐
   │ Ingestion Parser   │  validate → trace_id → enrich → ledger
   └────────────────────┘
            │
            ▼
       Redis Streams
   stream:tx:new   stream:access
            │
   ┌────────┼────────────────────────┐
   ▼        ▼                        ▼
 Risk     Access-Spike         Compliance Auto-Scan
 Engine   Sub-Engine           (at-rest PHI scanner)
   └────────┼────────────────────────┘
            ▼
       stream:alerts
            │
            ▼
    Alert Router (Rust)
    dedupe · correlate · persist
            │
            ▼
       PostgreSQL  ◄──── Parquet ledger (S3)
            │
            ▼
    WebSocket / REST API
            │
            ▼
    NEXUS-Med Dashboard
```

## 3. Stage Reference

| Stage | Tech | Responsibility |
|---|---|---|
| Ingestion Parser | Python, pydantic | Schema validation, trace_id assignment, fact extraction, ledger write |
| Stream Backbone | Redis Streams + consumer groups | At-least-once, replayable event transport |
| Risk Engine | Python + RocksDB | 15-min sliding window, overlap detection, weighted scoring |
| Access Engine | Python + Bloom/HLL sketches | Per-user volume anomaly via rolling Z-score |
| Compliance Scanner | PowerShell + SQLite | At-rest PII/PHI regex sweep on file shares |
| Alert Router | Rust | Dedupe (5-min window), correlation, PostgreSQL persistence, WS fan-out |
| Dashboard | React SPA | Live triage feed, alert map, compliance widget, investigation workspace |

## 4. Risk Envelope

Every scored transaction emits a Risk Envelope. Auditors can unpack any score
into the rule weights and source events that produced it.

```json
{
  "trace_id": "018f9b2e-7c41-7a40-ae21-f9c2d2c43e1a",
  "score": 78,
  "severity": "HIGH",
  "factors": {
    "temporal_overlap": 40,
    "access_spike": 28,
    "off_hours": 10
  },
  "triggers": [
    { "type": "claim", "id": "abc123", "cpt": "73721" },
    { "type": "claim", "id": "def456", "cpt": "99213" }
  ],
  "rule_version": "2026.06.01"
}
```

| Factor | Max | Source |
|---|---|---|
| Temporal Billing Overlap | 40 | Risk Engine |
| Unusual Procedure Mix | 20 | Risk Engine |
| Access Volume Spike | 50 | Access Engine |
| High-Risk Patient (VIP) | 10 | Reference data |
| Off-Hours Activity | 10 | Risk Engine |
| **Cap** | **100** | |

## 5. Strengthening Additions

These extensions move the platform from "real-time scoring" to "enterprise
healthcare intelligence."

### 5.1 Entity Resolution Layer
Master Patient Index + Provider Identity Resolution. Reconciles `P-9912`,
`MRN-44721`, and `GUID-889` to a single canonical entity before scoring.
Without this, longitudinal anomaly detection silently fragments.

### 5.2 Graph Correlation Engine
Replace flat alert correlation with a property graph (Neo4j or Memgraph).
Nodes: Provider, Patient, Claim, AccessEvent, Workstation. Edges expose
fraud rings, shared-workstation collusion, and repeat-offender clustering
that row-based correlation cannot see.

### 5.3 Hybrid ML Risk Layer
Keep rule-based scoring as the primary, explainable signal. Add a secondary
ML score (Isolation Forest for outliers; XGBoost / LightGBM for supervised
patterns) blended at `0.7 * rules + 0.3 * model`. Catches novel patterns
without sacrificing the audit story.

### 5.4 Alert Aggregation & Decay
Group related alerts into Incidents. Analysts work `1 incident · 127
contributing events`, not 127 raw alerts. Apply exponential risk decay so
stale scores age out automatically.

### 5.5 Cryptographic Audit Chain
Every ledger write records `event_hash = SHA-256(payload || previous_hash)`,
producing a tamper-evident chain. Tampering with any historic record breaks
the chain and is detectable on routine verification sweeps. Required-grade
evidence for HIPAA, litigation, and insurance disputes.

## 6. End-to-End Trace Example

```text
09:00:05  FHIR MRI claim → trace_id=abc123 → stream:tx:new
09:00:10  Risk Engine: no overlap → score 0
09:10:22  Office consult claim (same patient) → trace_id=def456
09:10:23  Engine: overlap_ratio 0.71 → both claims rescored to 78
          → CRITICAL alerts published
09:10:24  Alert Router → PostgreSQL → WebSocket
          → NEXUS-Med flashes "Billing Collision: P-9912"
09:30:00  Compliance Auto-Scan: unencrypted CSV with 200 MRNs found
09:30:05  Compliance widget updates → analyst opens investigation,
          ledger replay reconstructs full timeline from raw bytes
```

## 7. Horizon 2030 — Advanced Capability Layer

The §5 additions take ClearPulse to a 9.5+ enterprise tier. The 2030 horizon
moves the platform to sovereign-grade healthcare intelligence: quantum-safe,
privacy-preserving, field-verifiable, and autonomously triaged.

### 7.1 Post-Quantum Audit Chain
Replace SHA-256 hash-linking with **SHA3-512 + ML-DSA-65 (Dilithium)**
signatures (NIST FIPS-204). Block keys are wrapped in **ML-KEM-768** under an
HSM. Neutralizes harvest-now-decrypt-later attacks against 30-year retention.

### 7.2 Federated Learning Mesh
Hospitals train fraud / snooping models locally; only DP-perturbed gradients
(`ε = 2.5`, `δ = 1e-6`, clipped) leave the edge. Secure aggregation via
Paillier + masking. 200+ facility coverage, zero PHI movement.

### 7.3 Confidential Compute Enclaves
Risk Engine pinned inside Intel TDX / AMD SEV-SNP TEEs. PHI is decrypted only
inside the enclave. Hospitals demand a remote attestation (RA-TLS) against a
Sigstore-anchored transparency log before any record is forwarded.

### 7.4 Agentic Investigator Copilot
Every CRITICAL alert spawns an LLM agent constrained to 14 tools:
`get_trace`, `walk_graph`, `replay_ledger`, `query_access_log`, etc.
It produces a draft forensic timeline with mandatory `trace_id`
citations. Analysts review, never start from blank. Human-in-the-loop
gating on all proposed containment actions.

### 7.5 Zero-Knowledge Audit Proofs
Halo2 / Plonk circuits compiled from the rules engine. A regulator verifies
"this score was produced by approved rule v2030.06 against ledger-anchored
events" in `< 250 ms` with an `8 KB` proof — **without seeing the PHI**.
Eliminates the audit/privacy trade-off.

### 7.6 Temporal Graph Neural Network
A TGN over Provider · Patient · Claim · Workstation · Device nodes detects
repeating subgraphs across weeks: fraud rings, shared-device collusion,
money-mule provider chains. Streamed inference `< 80 ms / event` over a
12M-node graph.

### 7.7 Synthetic Data Twin
Continuously-running shadow pipeline replays a GAN-generated patient
population with planted fraud scenarios. Provides live MTTD / MTTR per rule
and per model, with weekly red-team regression scorecards.

### 7.8 Edge Inference at Point of Care
ONNX-Runtime risk model on workstation NPUs (`4 ms` latency). Inline
soft-blocks on off-roster billing or unusual code pairs **before
submission** — prevention, not detection.

### 7.9 Sovereign Data Plane
Region-pinned control plane with OPA / Rego policies for HIPAA, EU GDPR
Art.9, UK DSPT, Canada PIPEDA, AU My Health Records. Replication never
crosses a jurisdiction without a signed policy attestation; each routing
decision is recorded for per-route audit.

## 8. Maturity Targets

| Area | Current | With §5 additions |
|---|---|---|
| Ingestion | 9 | 9 |
| Streaming | 9 | 9 |
| Explainability | 10 | 10 |
| Compliance Monitoring | 9 | 9 |
| Fraud Detection | 8 | 9.5 |
| Insider Threat | 8 | 9.5 |
| Forensic Readiness | 8 | 10 |
| ML Capability | 5 | 9 |
| Graph Intelligence | 4 | 9 |
| **Overall** | **8.3** | **9.5+** |
