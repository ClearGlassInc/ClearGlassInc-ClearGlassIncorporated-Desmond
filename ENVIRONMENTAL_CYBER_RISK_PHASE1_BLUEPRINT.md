# ClearGlassInc Artemis — Environmental Cyber-Risk Phase 1 Blueprint

## Operational Directive
ClearGlassInc Artemis will treat ionospheric and space-weather effects as a governed **Environmental Cyber-Risk** vector. The first 48 hours focus on a lightweight, defensive, public-data dashboard and a Burlington/GTA pilot brief. The primary follow-on path is **Phase 2 Option A: Environmental Cyber-Risk Framework**, implemented through the same Palantir Gotham, Foundry, AIP, and Apollo architecture used by the broader Artemis intelligence platform.

## System Architecture

### Palantir Role Mapping
- **Gotham**: investigation cases, entity tracking, anomaly timelines, and client-specific incident workspaces.
- **Foundry**: public feed ingestion, normalized datasets, Ontology objects, risk scoring transforms, and dashboard applications.
- **AIP**: analyst copilot, alert triage agents, brief-generation agents, evaluation harnesses, and human-approved self-improvement proposals.
- **Apollo**: release channels for dashboard services, prompt packs, workflow bundles, policy bundles, canary deployment, rollback, and runtime control.

### Phase 1 Data Flow
```text
CSA / NOAA SWPC / public ionospheric models / public incident notes
        │
        ▼
Foundry raw datasets ──► normalization transforms ──► Environmental Cyber-Risk Ontology
        │                         │                               │
        │                         ▼                               ▼
        │                 risk scoring service              Gotham case views
        │                         │                               │
        └─────────────────────────▼───────────────────────────────┘
                              AIP triage agents
                                      │
                                      ▼
                         dashboard alerts + pilot brief
```

## Data and Ontology

### Core Entities
| Entity | Purpose | Key fields |
| --- | --- | --- |
| `SpaceWeatherObservation` | Normalized public feed sample | source, timestamp, Kp, F10.7, flare class, radio burst metadata, lineage |
| `IonosphericObservation` | Ionospheric state estimate | station/model, foF2, TEC, S4 scintillation, hmF2, confidence |
| `InfrastructureDependency` | Client dependency on propagation-sensitive systems | client, GNSS reliance, HF reliance, timing reliance, business function |
| `EnvironmentalCyberRiskAlert` | Actionable risk object | risk band, score, threshold reason, affected systems, recommended mitigations |
| `PilotBrief` | Client-facing intelligence product | audience, assumptions, risk table, mitigations, caveats, approval state |

### Relationships
- `Observation DERIVED_FROM SourceFeed`
- `RiskAlert SUPPORTED_BY Observation`
- `RiskAlert AFFECTS InfrastructureDependency`
- `PilotBrief SUMMARIZES RiskAlert`
- `OperatorFeedback CORRECTS RiskAlert`
- `WorkflowVersion PRODUCED RiskAlert`

### Thresholds
The Phase 1 threshold contract is intentionally simple, auditable, and suitable for early client education:

| Band | Condition | Meaning |
| --- | --- | --- |
| GREEN | `log_nf2 < 5.4` | Normal environmental cyber-risk posture |
| YELLOW | `5.4 <= log_nf2 <= 5.8` | Elevated propagation uncertainty; watch GNSS/HF timing dependencies |
| RED | `log_nf2 > 5.8` | High environmental cyber-risk; prepare mitigations and client notification |

## AI and Agent Design

### Agents
1. **Environmental Triage Agent**
   - Reads new observations and computes threshold bands.
   - Deduplicates alerts by geography, client dependency, and time window.
   - Opens Gotham cases only when policy and approval state allow it.

2. **Client Impact Agent**
   - Maps risk alerts to logistics, surveying, aviation-support, utilities, and timing dependencies.
   - Produces practical mitigation language: GNSS fallback, inertial backup, timing holdover, HF frequency agility, and manual dispatch procedures.

3. **Briefing Agent**
   - Drafts a 12-page pilot brief with source caveats.
   - Requires analyst approval before external delivery.

4. **Self-Improvement Agent**
   - Converts operator corrections into eval examples and candidate prompt/workflow changes.
   - Cannot deploy changes directly; it submits proposals to an approval queue.

## Self-Improvement Loop

1. **Capture**: store operator accepts/rejects, edited brief sections, threshold overrides, false positives, false negatives, client outcome labels, and dashboard latency.
2. **Convert**: generate eval cases covering alert banding, mitigation relevance, citation coverage, and client-impact mapping.
3. **Propose**: create prompt, workflow, heuristic, or model-router candidates with diffs and expected metric improvements.
4. **Evaluate**: run offline evals, shadow replay against historical periods, drift checks, and policy regression tests.
5. **Approve**: human reviewer approves, rejects, or requests revision for each candidate.
6. **Deploy**: Apollo promotes approved bundles through dev, staging, canary, and production rings.
7. **Rollback**: every promoted prompt/workflow/model-router config stores a rollback pointer and immutable audit record.

## Full-Stack Implementation

### Services
- `feed-ingestor`: pulls public CSA/NOAA/model data and writes raw observations.
- `normalizer`: validates schema, units, timestamps, station metadata, and lineage hashes.
- `risk-scorer`: computes `log_nf2` bands and composite disruption scores.
- `alert-service`: creates, deduplicates, updates, and closes environmental risk alerts.
- `brief-service`: builds analyst-reviewed pilot briefs and client PDFs.
- `feedback-service`: captures operator and client labels for eval generation.
- `improvement-service`: proposes controlled self-upgrades.

### API Surface
```http
POST /v1/environmental/observations
GET  /v1/environmental/alerts?client_id=&band=&since=
POST /v1/environmental/alerts/{alert_id}/feedback
POST /v1/environmental/briefs/pilot
POST /v1/improvements/proposals/{proposal_id}/approve
POST /v1/improvements/proposals/{proposal_id}/rollback
```

### Dashboard Widgets
- Current risk band and threshold rationale.
- Time series for `log_nf2`, Kp, S4, TEC, and alert state.
- Burlington/GTA dependency map for GNSS/HF/timing exposure.
- Open Gotham case links and AIP explanation panel.
- Pilot brief draft status and approval queue.

## Security and Governance

- Public-feed data is still governed with source provenance, integrity hashes, and transformation lineage.
- Client dependency data is compartmented by client and mission.
- AIP tools enforce need-to-know checks before reading client dependencies or generating external briefs.
- Generated client deliverables require human approval and export policy checks.
- Prompt and workflow changes are treated as controlled artifacts with review, eval evidence, and rollback.

## Scenario Walkthrough

1. NOAA and public ionospheric feeds show elevated conditions over southern Ontario.
2. Foundry normalizes the samples and creates `IonosphericObservation` objects.
3. The risk scorer computes `log_nf2 = 5.92`, producing a RED `EnvironmentalCyberRiskAlert`.
4. AIP maps the alert to a Burlington surveying pilot with high GNSS reliance.
5. The Client Impact Agent drafts mitigations: schedule critical survey windows around lower-risk periods, validate GNSS fixes against known control points, and keep manual quality gates for high-precision work.
6. An analyst reviews the recommendation, edits the client language, and approves a pilot brief.
7. Feedback service records the edits and outcome.
8. The Self-Improvement Agent proposes a wording and routing update because the analyst repeatedly strengthened GNSS quality-control mitigations.
9. Offline evals pass, a reviewer approves, and Apollo promotes the new prompt pack through canary deployment with rollback available.

## Phase 1 Success Criteria

- Dashboard can display current GREEN/YELLOW/RED posture from public or simulated feed samples.
- Burlington/GTA pilot brief can be generated with source caveats and mitigation table.
- Every alert has lineage, confidence, threshold explanation, policy context, and feedback capture.
- No operationally significant action, external client brief, or self-upgrade is executed without explicit human approval.
