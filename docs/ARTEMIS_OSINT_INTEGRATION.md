# ARTEMIS / AEGIS — Public-Source Intelligence Fabric

Integration principle: additive, provenance-first, read-only by default, and fail-closed for sources without an explicit automation right.

## 1. Executive Summary

ARTEMIS now has a dedicated OSINT fabric under artemis/osint that normalizes public-source metadata, provides guarded HTTP connectors, records provenance hashes, supports GeoJSON event normalization, and exposes a read-only FastAPI catalog at /v1/osint. A new Next.js route at /artemis provides the executive dashboard shell.

No existing product, workflow, or deployment path is replaced.

## 2. Source Inventory

The registry contains all 30 requested sources. The reliability value is an integration reliability score for API/documentation stability and machine-readability, not a claim that source content is inherently true.

| Source | Category | API / ingestion | Auth | Risk | Complexity | Effort |
|---|---|---|---|---|---|---|
| Zoom Earth | Weather / Real-Time Geospatial | web-only | — | High | High | 2-4d |
| Flightradar24 | Aviation | licensed API | token | High | High | 3-5d |
| MarineTraffic | Maritime | licensed API | key | High | High | 3-5d |
| Windy | Weather | developer API/SDK | key | Medium | Medium | 2-4d |
| LightningMaps | Weather | web-only | — | High | High | 2-3d |
| USGS Earthquake Feed | Earth Observation | GeoJSON | none | Low | Low | 1-2d |
| Submarine Cable Map | Real-Time Geospatial | web/licensed | — | High | High | 3-5d |
| Global Forest Watch | Environmental Intelligence | official API | token where required | Medium | Medium | 2-4d |
| Worldometer | Statistics | web-only | — | High | High | 2-3d |
| Internet Live Stats | Statistics | web-only | — | High | High | 2-3d |
| OpenStreetMap | Real-Time Geospatial | official ecosystem APIs | service-specific | Medium | Medium | 2-4d |
| Atlas Obscura | Cultural Heritage | web-only | — | High | High | 2-3d |
| NASA Eyes | Space Intelligence | reference app | — | Low | Medium | 1-3d |
| Stellarium | Space Intelligence | local software | — | Medium | Medium | 2-4d |
| NASA APOD | Space Intelligence | official API | optional key | Low | Low | 1-2d |
| NASA Image Library | Space Intelligence | official API | none | Low | Low | 1-2d |
| Our World in Data | Public Data | CSV + metadata JSON | none | Low | Low | 1-2d |
| Gapminder | Statistics | downloadable datasets | — | Low | Low | 1-2d |
| Information Is Beautiful | Statistics | web-only | — | High | High | 2-3d |
| World Bank Open Data | Public Data | official API | none | Low | Low | 1-2d |
| Internet Archive | Historical Archives | search/metadata APIs | none | Low | Low | 1-3d |
| Project Gutenberg | Historical Archives | feeds/files | — | Medium | Medium | 2-4d |
| Open Library | Historical Archives | public API | none | Low | Low | 1-2d |
| Library of Congress | Historical Archives | loc.gov API | none for loc.gov | Low | Low | 1-3d |
| Europeana | Cultural Heritage | API/OAI-PMH | API key | Medium | Medium | 2-4d |
| Digital Public Library of America | Cultural Heritage | API | API key | Medium | Medium | 2-4d |
| Google Arts & Culture | Cultural Heritage | web-only | — | High | High | 2-3d |
| Rijksmuseum | Cultural Heritage | official API | API key | Medium | Low | 1-3d |
| WikiArt | Cultural Heritage | web-only | — | High | High | 2-3d |
| Open Culture | Education | web-only/index | — | Medium | Medium | 1-2d |

Current verification anchors: NASA documents the current APOD WordPress endpoint and says the legacy APOD API is scheduled for retirement on 2026-12-01; NASA also documents a default keyed rate limit of 1,000 requests/hour and response rate-limit headers. Open Library currently documents 1 request/second for non-identified clients and up to 3 requests/second for identified applications. These values are treated as guardrails, not universal limits.

## 3. Architecture Design

Public sources → connector layer → auth/rate/retry policy → schema validation → normalization → provenance envelope → queue/worker → PostgreSQL/PostGIS → FastAPI read API → Next.js dashboard.

A production event flow should use topics such as:
osint.raw.<source> → osint.normalized.<category> → osint.alerts → osint.reports.

Use durable partitions keyed by source and logical geography. Dead letters must retain the error class and provenance hash/reference. Do not persist secrets in event payloads.

## 4. Data Ingestion

Each connector follows the same contract:
- read-only network access;
- bounded timeout;
- 429/5xx retry with exponential backoff and Retry-After;
- source-specific authentication from environment secrets;
- source-specific rate limiter;
- response schema validation before normalization;
- provenance hash recorded before downstream persistence;
- web-only/reference-only connectors fail closed instead of scraping.

Caching strategy:
- Redis or equivalent for hot dashboard reads;
- ETag/Last-Modified conditional requests for supported feeds;
- PostgreSQL/PostGIS for normalized observations and events;
- immutable object storage for licensed/raw artifacts where the license permits retention.

## 5. Database Design

artemis/osint/schema.sql defines:
osint_sources
osint_datasets
osint_source_metadata
osint_locations
osint_observations
osint_events
osint_assets
osint_alerts
osint_audit_log

Key decisions:
1. PostGIS geometry(Point,4326) for normalized point locations.
2. JSONB for provider-specific payloads while indexed fields support search.
3. SHA-256 content hashes link observations/events to a provenance envelope.
4. Audit records are append-only and hash chained.
5. Rights/license metadata lives beside source/dataset records.

## 6. FastAPI Design

The deployment service mounts:
GET /v1/osint/health
GET /v1/osint/sources
GET /v1/osint/sources/{source_id}

The external polling trigger is intentionally not exposed through the public API. Worker execution must remain internal, credentialed and policy-controlled.

## 7. Frontend Design

New Next.js route: /artemis

Modules:
Situation Room
Global Operations Map
Aviation Layer
Maritime Layer
Weather Layer
Earthquake Layer
Space Layer
Environmental Monitoring
Historical Archive Explorer
Data Explorer
Intelligence Reports

Provider credentials never reach the browser. The browser consumes ClearGlass's normalized read API.

## 8. Security

RBAC roles: viewer, analyst, operator, admin.

API security:
- TLS at the edge;
- authenticated internal worker calls;
- schema validation;
- request IDs;
- bounded timeouts;
- per-route rate limiting;
- deny-by-default outbound access for connector workers.

Secrets:
- environment/secret manager only;
- no credentials in repository or client bundles.

Supply chain:
- retain existing lockfiles;
- keep GitHub Actions pinned where repository policy already requires it;
- Dependabot and dependency/security scanning;
- SBOM generation as the pipeline matures.

SOC 2 alignment:
logical access, change management, monitoring, incident response, vendor management, evidence retention.

NIST CSF alignment:
Govern, Identify, Protect, Detect, Respond, Recover, plus OSINT-specific source-rights and provenance controls.

## 9. Roadmap

Phase 1:
OpenStreetMap, USGS, NASA APOD, NASA Image Library, Our World in Data, World Bank. Add PostGIS schema, provenance ledger, catalog API, tests and dashboard shell.

Phase 2:
Windy, Global Forest Watch, MarineTraffic after licensed plan review. Add weather/forest adapters and alert policies.

Phase 3:
Flightradar24 and deeper NASA earth-observation/satellite datasets after licensing and provider-contract review.

Phase 4:
Advanced correlation, anomaly detection, source reliability weighting, geospatial clustering, AI-assisted summaries and human-reviewed risk scoring.

## 10. Risk Register

| Risk | Severity | Control |
|---|---|---|
| Provider ToS changes | High | registry + legal review + feature flags |
| Commercial API cost/quota | High | disabled-by-default + limiter |
| Web scraping drift | High | no scraping fallback |
| Attribution error | High | mandatory provenance |
| API key leakage | Critical | server-side env only |
| Coordinate/schema error | High | validation + EPSG:4326 bounds |
| Stale data treated as live | High | observed_at + retrieved_at |
| License mismatch | High | dataset-level rights snapshot |
| Cross-source contradiction | Medium | preserve both; do not silently overwrite |
| Queue duplication | Medium | idempotent ids and persistence |

## 11. Recommended MVP Build Order

1. Land the additive registry, provenance and connector contracts.
2. Enable OSM + USGS + NASA + OWID + World Bank.
3. Add durable worker scheduling and conditional caching.
4. Add dashboard read models and map clustering.
5. Add licensed weather/environment/maritime integrations.
6. Add aviation and advanced analytics last.

## 12. Timeline Estimate

One senior full-stack engineer plus part-time GIS/data support:
Phase 1: 5-8 working days
Phase 2: 7-12
Phase 3: 7-12
Phase 4: 10-15

These are engineering estimates and exclude provider procurement/contract delays.
