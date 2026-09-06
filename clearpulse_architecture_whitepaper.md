# ClearPulse Architecture Whitepaper
### Forensic AI for Healthcare — A Reference Architecture for Provable Healthcare Intelligence Infrastructure

> **ClearGlass Inc · ClearPulse Platform · v2026.06**
> Authored for healthcare CISOs, compliance officers, regulators, and platform architects evaluating evidence-grade intelligence systems for HIPAA-regulated environments.

---

## 0. Executive Position

Most healthcare anomaly platforms optimize for **detection accuracy**.
ClearPulse optimizes for **investigative truth**.

That difference is structural, not cosmetic. A SIEM tells you *something happened*. A fraud tool tells you *something looks wrong*. ClearPulse produces an artifact a court, a regulator, an OIG auditor, or an internal investigator can carry into a deposition: a cryptographically anchored, end-to-end traceable, replayable record that proves what happened, who acted, what data they touched, what rule fired, and why the score landed where it did.

We call this category **Provable Healthcare Intelligence Infrastructure (PHII)**. ClearPulse is its reference implementation.

This document is the authoritative architecture specification: pipeline, data model, four upgrade priorities (Entity Resolution, Graph Intelligence, Cryptographic Audit Chain, Incident Abstraction), security posture, deployment topology, and KPI targets.

---

## 1. Design Pillars

The pillars are non-negotiable. Every design decision in ClearPulse is validated against them.

| # | Pillar | Operative Definition |
|---|--------|----------------------|
| 1 | **Traceability-first** | A UUID7 `trace_id` is minted at ingestion and propagated through every stage. Every downstream artifact — score, alert, incident, dashboard cell — can be replayed back to the originating byte. |
| 2 | **Explainable scoring** | Every Risk Envelope is a structured object: weighted factors, contributing facts, rule version, source events. No black-box scores reach an analyst surface. |
| 3 | **Unified signal plane** | Billing anomalies, behavioral anomalies, and at-rest PHI exposures converge into one stream, one envelope schema, one investigation graph. |
| 4 | **Forensic-grade lineage** | The ledger is hash-chained, append-only, and verifiable independently of the runtime. The audit trail is the product. |
| 5 | **Deterministic-first, ML-augmented** | Rules carry compliance weight and explainability. ML widens recall on novel patterns without surrendering defensibility. |
| 6 | **Identity-aware** | Every event resolves to a stable entity (patient, provider, device, payer) — not a transient identifier. |
| 7 | **Relationship-aware** | The graph is a first-class store, not a derived view. Fraud rings and insider collusion live in edges, not rows. |

---

## 2. Reference Pipeline

```text
                FHIR · HL7v2 · X12 837 · EHR audit logs · DLP scanner
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │  01 · Ingestion Parser        │
                        │  validate → trace_id (UUID7)  │
                        │  → canonical envelope         │
                        │  → Parquet ledger (S3, WORM)  │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
                          Redis Streams (at-least-once, replayable)
                  stream:tx:new    stream:access    stream:phi:scan
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
    ┌───────────────┐         ┌────────────────┐         ┌──────────────────┐
    │ 02 · Risk     │         │ 03 · Access    │         │ 04 · PHI Auto-   │
    │     Engine    │         │     Engine     │         │     Scanner      │
    │ (rules + ML)  │         │ Bloom + HLL    │         │ at-rest DLP      │
    └───────┬───────┘         └────────┬───────┘         └────────┬─────────┘
            │                          │                          │
            └──────────────────────────┼──────────────────────────┘
                                       ▼
                           ┌────────────────────────┐
                           │ 05 · Entity Resolver   │   ← Priority 1
                           │ probabilistic MPI +    │
                           │ provider reconciliation│
                           └────────────┬───────────┘
                                        ▼
                           ┌────────────────────────┐
                           │ 06 · Graph Intelligence│   ← Priority 2
                           │ Neo4j / Memgraph       │
                           │ rings · collusion · ts │
                           └────────────┬───────────┘
                                        ▼
                           ┌────────────────────────┐
                           │ 07 · Incident Aggregator│  ← Priority 4
                           │ 1 incident ⇆ N events  │
                           │ risk decay · root cause│
                           └────────────┬───────────┘
                                        ▼
                           ┌────────────────────────┐
                           │ 08 · Cryptographic     │   ← Priority 3
                           │     Audit Chain        │
                           │ SHA-256 hash-linked,   │
                           │ Merkle-anchored        │
                           └────────────┬───────────┘
                                        ▼
                              PostgreSQL  +  S3 (WORM)
                                        │
                                        ▼
                        WebSocket / REST API (FastAPI)
                                        │
                                        ▼
                          NEXUS-Med Analyst Surface
                  triage · graph · timeline · forensic replay
```

---

## 3. Canonical Data Model — The Risk Envelope

Every signal in ClearPulse is normalized into a single envelope schema before it enters scoring. This is the contract that makes the system explainable end-to-end.

```json
{
  "trace_id": "018f9b2e-7c41-7a40-ae21-f9c2d2c43e1a",
  "envelope_version": "2026.06.01",
  "ingested_at": "2026-06-02T14:09:11.482Z",
  "source": {
    "system": "epic.audit",
    "feed": "phi_access_v2",
    "ledger_offset": 884213,
    "ledger_hash": "sha256:9af3...e21c"
  },
  "subject": {
    "patient_eid":  "eid:pat:7c1a...09",
    "provider_eid": "eid:prv:0044...b2",
    "device_eid":   "eid:dev:ws-42",
    "payer_eid":    null,
    "resolution_confidence": 0.97
  },
  "facts": {
    "cpt": "73721",
    "encounter_id": "P-9912",
    "off_hours": true,
    "window_minutes": 15
  },
  "score": 78,
  "severity": "CRITICAL",
  "factors": {
    "temporal_overlap":  { "weight": 40, "ratio": 0.71 },
    "access_spike":      { "weight": 28, "z": 4.3 },
    "off_hours":         { "weight": 10 }
  },
  "triggers": [
    { "type": "claim",  "id": "abc123", "cpt": "73721" },
    { "type": "claim",  "id": "def456", "cpt": "99213" }
  ],
  "rule_version": "2026.06.01",
  "ml_overlay":  { "model": "iforest-v3", "p_anomaly": 0.94 },
  "incident_id": "inc:2026-06-02:0007",
  "audit": {
    "prev_hash": "sha256:71d2...c0aa",
    "self_hash": "sha256:bb40...91ef",
    "merkle_root_ref": "anchor:2026-06-02T14:10:00Z"
  }
}
```

**Why this matters:** every analyst-facing field in the UI is sourced from this envelope. There is no "phantom data" in ClearPulse — if it shows on a screen, it has a trace_id and a hash.

---

## 4. Priority 1 — Entity Resolution

> Without identity, every other layer is fragmented. Entity Resolution is the single highest-leverage upgrade in the platform.

### 4.1 Problem
A single patient appears under multiple MRNs across affiliated systems. A single provider has a NPI, an EHR userid, a badge id, and a payroll id. Without reconciliation, behavioral baselines are wrong, fraud rings are invisible, and "this user accessed 41 records" is meaningless when the user is actually three personas.

### 4.2 Approach — Hybrid Deterministic + Probabilistic MPI

1. **Deterministic pass.** Exact matches on strong keys: NPI, government-issued patient identifier, verified SSN hash.
2. **Probabilistic pass.** Fellegi-Sunter scoring over (name n-grams, DOB, address tokens, phone hash, device fingerprint). Per-attribute m/u probabilities calibrated on labeled pairs.
3. **Active-learning loop.** Borderline pairs (0.65 ≤ p < 0.92) are surfaced to compliance reviewers; their decisions retrain the model weekly.
4. **Provider/device parallel pipeline.** Same algorithm, different feature set: workstation MAC, browser fingerprint, badge swipe correlation, shift schedule.

### 4.3 Output — The Entity ID (EID)
Every envelope carries:
```
patient_eid · provider_eid · device_eid · payer_eid · resolution_confidence
```
EIDs are stable, opaque, and reversible only via the entity service with proper authorization. Behavioral baselines (Z-score windows, HLL sketches) key on EID, not source identifiers.

### 4.4 KPI Targets
| Metric | Baseline | Target (90 days) |
|---|---|---|
| Patient match precision | n/a | ≥ 0.995 |
| Patient match recall | n/a | ≥ 0.92 |
| Provider duplicate-collapse rate | n/a | ≥ 85% |
| Manual reviewer queue / 1M events | n/a | ≤ 50 |

---

## 5. Priority 2 — Graph Intelligence Layer

> Event correlation is linear thinking. Relationship intelligence is the multiplier.

### 5.1 Problem
Fraud rings, insider collusion, kickback schemes, and credential-sharing are **graph-shaped problems**. Row-by-row scoring cannot see them.

### 5.2 Graph Model

**Nodes:**
- `Patient`, `Provider`, `Device`, `Workstation`, `Claim`, `Encounter`, `Payer`, `Diagnosis`, `Procedure`

**Edges:**
- `(Provider)-[:BILLED {ts, amount}]->(Claim)`
- `(Provider)-[:ACCESSED {ts, scope}]->(Patient)`
- `(Patient)-[:HAS_ENCOUNTER {ts}]->(Encounter)`
- `(Device)-[:USED_BY {ts}]->(Provider)`
- `(Workstation)-[:LOGGED_IN {ts, source_ip}]->(Provider)`
- `(Claim)-[:DERIVED_FROM]->(Encounter)`
- `(Provider)-[:CO_TREATS {patient_count, jaccard}]->(Provider)`

### 5.3 Detection Patterns (Cypher excerpts)

**Fraud ring — shared-patient billing collusion:**
```cypher
MATCH (p1:Provider)-[:BILLED]->(c1:Claim)-[:DERIVED_FROM]->(e:Encounter)
       <-[:DERIVED_FROM]-(c2:Claim)<-[:BILLED]-(p2:Provider)
WHERE p1.eid < p2.eid
  AND duration.between(c1.ts, c2.ts).seconds < 900
WITH p1, p2, count(DISTINCT e) AS overlap
WHERE overlap >= 12
RETURN p1.eid, p2.eid, overlap
ORDER BY overlap DESC
```

**Insider collusion — shared-workstation anomaly:**
```cypher
MATCH (w:Workstation)-[l1:LOGGED_IN]->(p1:Provider),
      (w)-[l2:LOGGED_IN]->(p2:Provider)
WHERE p1.eid <> p2.eid
  AND abs(duration.between(l1.ts, l2.ts).seconds) < 300
RETURN w.id, p1.eid, p2.eid, l1.ts, l2.ts
```

**Identity spoofing — geographic impossibility:**
```cypher
MATCH (p:Provider)-[l1:LOGGED_IN]->(w1:Workstation),
      (p)-[l2:LOGGED_IN]->(w2:Workstation)
WHERE duration.between(l1.ts, l2.ts).seconds < 600
  AND distance(w1.geo, w2.geo) > 200000
RETURN p.eid, w1.id, w2.id, l1.ts, l2.ts
```

### 5.4 The Real Leverage — Graph as Feature Store
The graph is not a side database. It is the **feature store** for ML.

For every (provider, 15-min window) we materialize:
- `degree_patients_15m`, `degree_patients_24h`, `degree_patients_7d`
- `pagerank_in_billing_subgraph`
- `co_billing_jaccard_max`
- `shared_device_count_24h`
- `ring_membership_score` (community detection: Louvain on co-billing edges)

These features feed both rule weights and ML overlays — every prediction carries a graph-context vector that an investigator can interrogate.

### 5.5 KPI Targets
| Metric | Target |
|---|---|
| Multi-entity ring detection | ≥ 1 ring/quarter at pilot scale |
| Investigative depth (avg hops explored per case) | 3 → 7 |
| Anomaly recall lift vs. rules-only baseline | +25–40% |
| False-positive delta | ≤ +10% (controlled) |

---

## 6. Priority 3 — Cryptographic Audit Chain

> This is the legal moat. SIEM vendors compete on dashboards; we compete on admissible evidence.

### 6.1 Structure — Hash-Linked, Merkle-Anchored

Every envelope is appended to a per-tenant ledger. Each record stores:

```text
record_n = {
  payload:  <Risk Envelope, canonical JSON, RFC 8785>
  prev_hash: SHA-256(record_{n-1}.self_hash)
  self_hash: SHA-256(payload || prev_hash)
  ts:        monotonic ingest timestamp
}
```

A Merkle tree is built every **5 minutes** over all `self_hash` values in the window. The Merkle root is:

1. Written to PostgreSQL with the time bucket.
2. Mirrored to S3 with Object Lock (WORM, governance mode, 7-year retention).
3. **Anchored** to a public timestamping authority (RFC 3161) and, optionally, to a permissioned blockchain — never on-chain PHI, only the root.

### 6.2 Verification Workflow

An auditor receives an envelope and:
1. Recomputes `self_hash` from `payload` and `prev_hash`.
2. Walks the hash chain back to the most recent anchored Merkle root.
3. Independently verifies the root against the timestamping authority.
4. Confirms the WORM ledger copy matches.

If any byte of payload changed at any point, verification fails. If the operator tried to delete a record, the chain breaks at that position. Both conditions are detectable without trusting the runtime.

### 6.3 Compliance Mapping

| Control | Coverage |
|---|---|
| HIPAA §164.312(b) — Audit controls | Hash-linked ledger of every PHI access event |
| HIPAA §164.312(c)(1) — Integrity | SHA-256 + Merkle anchoring proves non-tampering |
| HIPAA §164.312(c)(2) — Authentication of EHI | RFC 3161 timestamps verify temporal authenticity |
| SOC 2 CC7.2 — System monitoring | Continuous, immutable evidence stream |
| 21st Century Cures §4004 — Information blocking | Verifiable access trail per request |
| Federal Rules of Evidence 901 / 902(13)–(14) | Self-authenticating records (digital signature + system process) |

### 6.4 KPI Targets
| Metric | Target |
|---|---|
| Anchor cadence | 5-min Merkle roots, 24/7 |
| Verification time per envelope | < 250 ms |
| Ledger gap detection (synthetic) | 100% over 90-day test |
| Independent third-party verification report | Annual, public |

---

## 7. Priority 4 — Incident Abstraction Layer

> Analysts do not investigate alerts. They investigate incidents.

### 7.1 Problem
A single fraud event can generate 30–200 underlying events (billing collisions, access spikes, PHI hits). Surfacing them as 200 alerts produces fatigue, slow MTTR, and burned credibility. Surfacing them as 1 incident produces action.

### 7.2 Incident Model

```text
Incident
  ├── incident_id          inc:2026-06-02:0007
  ├── status               OPEN | TRIAGED | INVESTIGATING | CLOSED | ESCALATED
  ├── severity             aggregate (max-decay over events)
  ├── opened_at / updated_at
  ├── primary_entities[]   provider_eid, patient_eid, device_eid
  ├── root_cause_event_id  earliest contributing trace_id
  ├── contributing_events[] (trace_ids, with weights)
  ├── graph_context        subgraph snapshot at time of escalation
  ├── narrative            auto-generated, analyst-editable
  └── audit_chain_ref      Merkle root covering all contributing events
```

### 7.3 Aggregation Rules

1. **Entity affinity.** Events sharing ≥ 1 EID within a 30-min sliding window cluster.
2. **Graph affinity.** Events on a connected subgraph within 2 hops cluster, even without shared EIDs.
3. **Pattern affinity.** Same rule-version + same factor signature within 6 hours clusters.
4. **Risk decay.** Severity = `max(event.score) · e^(-λ · age_minutes)`. Old contributing events depreciate; new ones lift.
5. **Reopen window.** Closed incidents reopen if a matching event arrives within 7 days.

### 7.4 Narrative Generation
For each incident, ClearPulse emits a one-paragraph deterministic narrative (no LLM hallucination risk for the canonical version) plus an optional LLM-augmented draft for review. Example deterministic output:

> *Incident inc:2026-06-02:0007 opened at 09:10:24 UTC. Provider eid:prv:0044...b2 submitted 4 billing collisions with Provider eid:prv:91aa...ce within a 15-minute window across Patient eid:pat:7c1a...09. Access spike (z=4.3) preceded billing by 6 minutes. All 12 contributing events anchored under Merkle root anchor:2026-06-02T14:10:00Z.*

### 7.5 KPI Targets
| Metric | Target |
|---|---|
| Alert → Incident compression ratio | ≥ 15:1 |
| Analyst-reported fatigue (survey) | -70% within 60 days |
| Mean time to triage | -60% |
| Incident closure auto-suggested correctly | ≥ 80% |

---

## 8. Dual-Layer Intelligence — Rules + ML

ClearPulse is **deterministic-first**. ML augments; it does not replace.

### 8.1 Layer 1 — Rules
- Authored in a YAML DSL with versioning.
- Each rule emits weighted factors that compose the envelope score.
- Every rule version is signed and ledger-anchored.
- Auditable: a regulator can read the rule that fired and reproduce the result.

### 8.2 Layer 2 — ML Overlay
- **Models:** Isolation Forest (unsupervised baseline), XGBoost (supervised on labeled incidents), Graph Neural Network (node-classification on co-billing/access graphs).
- **Features:** sourced from the graph feature store (§5.4), never from raw events directly.
- **Output:** `p_anomaly` attached to envelope as `ml_overlay`. Never overrides rule severity; can promote a borderline rule score or generate a "ML-flagged, no rule match" review queue.
- **Governance:** every model has a model card; every deployment is gated by an offline eval (precision/recall on holdout, fairness checks by provider specialty and patient demographic).

### 8.3 Composite Score

```
final_score = clamp_0_100(
    rule_score
    + α · ml_lift(p_anomaly, rule_score)
    + β · graph_context_score
)

where α = 0.30, β = 0.20  (tenant-configurable, ledger-anchored)
```

α and β are themselves audit artifacts — a regulator can verify which weights were active for any historical incident.

---

## 9. Security & Compliance Posture

| Domain | Implementation |
|---|---|
| Encryption in transit | TLS 1.3, mTLS between internal services |
| Encryption at rest | AES-256-GCM, per-tenant DEK wrapped by KMS CMK |
| Key management | AWS KMS / Azure Key Vault with HSM, separation of duties on CMK rotation |
| Tenancy | Hard per-tenant Redis stream namespaces, per-tenant ledgers, per-tenant CMKs |
| AuthN | OIDC, SCIM provisioning, FIDO2 enforced for admin |
| AuthZ | Attribute-based access control; minimum necessary enforced at envelope field level |
| PHI minimization | Field-level redaction in transit to analyst UI unless break-glass invoked; break-glass itself is a ledger event |
| Logging | Every read of an envelope by a ClearPulse user produces an envelope. The platform audits itself. |
| Region | Configurable; US, Canada (PIPEDA / Ontario PHIPA), EU residency available |
| Certifications target | SOC 2 Type II (Y1), HITRUST CSF (Y2), FedRAMP Moderate roadmap (Y2–3) |

---

## 10. Deployment Topology

```text
┌──────────────────────────── Customer VPC / Tenant ────────────────────────────┐
│                                                                                │
│  Ingestion   ─►  Redis Streams  ─►  Engines  ─►  Resolver  ─►  Graph  ─►  Agg │
│   (Python)        (Cluster)        (Rust+Py)     (Python)      (Neo4j)   (Rust)│
│      │                                                                         │
│      └─► Parquet Ledger (S3 + Object Lock, WORM)                              │
│                                                                                │
│  PostgreSQL (incidents, envelopes index, rule store)                          │
│  Audit Anchorer (Merkle, RFC 3161 timestamp client)                           │
│                                                                                │
│  FastAPI Gateway  ─►  WebSocket Fan-out  ─►  NEXUS-Med UI                     │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

Out-of-tenant (shared, no PHI):
  · Public timestamp authority
  · Optional permissioned blockchain anchor
  · Model registry (model cards + signed binaries)
  · ClearGlass control plane (orchestration, telemetry — metadata only)
```

Reference SLOs at single-tenant pilot scale:
- Throughput: **≥ 5 k eps** sustained ingest
- Score latency p95: **≤ 750 ms** end-to-end (ingest → envelope persisted)
- Incident materialization p95: **≤ 2 s** from triggering event
- Forensic replay (any envelope, any age): **≤ 3 s**

---

## 11. Six-Month Execution Roadmap

### Phase 1 (Days 0–60)
- Entity Resolution v1 (deterministic + Fellegi-Sunter probabilistic).
- Incident Aggregator v1 (entity + pattern affinity; risk decay).
- Public whitepaper + SEO pillar pages live.

### Phase 2 (Days 60–120)
- Graph Intelligence Layer v1 (Neo4j cluster, top-5 Cypher detectors in production).
- ML Overlay v1 (Isolation Forest baseline, XGBoost on labeled incidents).
- First pilot conversion to paid contract.

### Phase 3 (Days 120–180)
- Cryptographic Audit Chain GA (5-min Merkle anchoring, RFC 3161, WORM mirror).
- Standards engagement (HL7 / FHIR audit-extension working group submission).
- Independent third-party verification report published.

---

## 12. Category & Positioning

ClearPulse does not compete with SIEM. It does not compete with traditional fraud-detection tools. It absorbs them.

| Layer | Vendor Today | Under ClearPulse |
|---|---|---|
| Endpoint / network telemetry | CrowdStrike, Splunk | **Data source** |
| Payer fraud heuristics | Optum, Codoxo | **Signal input** |
| Compliance reporting | Internal GRC, vendor toolchains | **Downstream consumer** |
| Investigative truth | — | **ClearPulse** |

Messaging anchors:
- *"We don't detect anomalies — we prove them."*
- *"Every alert is traceable, explainable, and verifiable."*
- *"Built for auditors, not just analysts."*

---

## 13. KPI Dashboard (Platform Health)

| KPI | Phase 1 | Phase 3 |
|---|---|---|
| Trace_id propagation coverage | 100% | 100% |
| Alert → Incident compression | 8:1 | 15:1+ |
| Multi-entity ring detection | — | ≥ 1 per quarter |
| Anomaly recall lift vs. rules-only | +10% | +25–40% |
| False-positive delta | flat | ≤ +10% |
| Forensic replay p95 | 3 s | 1 s |
| Merkle anchor cadence | hourly | 5-min |
| Third-party verifiable | partial | yes (annual report) |

---

## 14. Appendix — Rule DSL (excerpt)

```yaml
id: rule.billing.temporal_overlap
version: 2026.06.01
description: Two CPT codes from the same provider on the same patient within
             a 15-minute window where the procedures are mutually exclusive.
when:
  all:
    - event.type == "claim"
    - join:
        on: [provider_eid, patient_eid]
        window_minutes: 15
        other:
          - event.type == "claim"
          - cpt_pair_is_mutually_exclusive(event.cpt, other.cpt)
emit:
  factor: temporal_overlap
  weight: 40
  evidence:
    - this.trace_id
    - other.trace_id
explain:
  human: "Mutually exclusive CPTs billed within 15 minutes for same patient/provider."
  citation: "CMS NCCI PTP Edits, 2026-Q2"
```

---

## 15. Appendix — Envelope JSON Schema (abbreviated)

```yaml
$schema: https://json-schema.org/draft/2020-12/schema
$id:     https://www.clearglassinc.com/schemas/risk-envelope-2026.06.json
type: object
required: [trace_id, envelope_version, source, subject, score, severity,
           factors, rule_version, audit]
properties:
  trace_id:          { type: string, pattern: "^[0-9a-f-]{36}$" }
  envelope_version:  { type: string }
  ingested_at:       { type: string, format: date-time }
  source:
    type: object
    required: [system, ledger_offset, ledger_hash]
  subject:
    type: object
    required: [resolution_confidence]
  score:    { type: integer, minimum: 0, maximum: 100 }
  severity: { enum: [LOW, MEDIUM, HIGH, CRITICAL] }
  factors:  { type: object, additionalProperties: { type: object } }
  ml_overlay:
    type: object
    properties:
      model:     { type: string }
      p_anomaly: { type: number, minimum: 0, maximum: 1 }
  audit:
    type: object
    required: [prev_hash, self_hash]
```

---

## 16. Closing

ClearPulse is the central intelligence layer of the healthcare ecosystem.

Detection accuracy is the table stakes other vendors fight over. We compete on a higher axis: **provable, explainable, identity-aware, relationship-aware investigative truth**, delivered at streaming latency, with an audit trail that survives a courtroom.

Execute the four priorities in this whitepaper, ship the roadmap, and the market will not have a name for what ClearPulse is — they will adopt ours.

— *ClearGlass Inc · ClearPulse Architecture Office · 2026*
