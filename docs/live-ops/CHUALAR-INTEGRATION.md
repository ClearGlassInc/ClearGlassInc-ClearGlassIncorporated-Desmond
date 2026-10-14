# Chualar — Monterey County Live Operations

## Files
- `app/chualar/page.tsx`: dashboard route at `/chualar`
- `app/chualar/ChualarOperations.tsx`, `chualar.module.css`: independent layer toggles, 10-second refresh, OpenStreetMap raster tiles, selectable markers and inspector
- `app/api/live/ops/route.ts`: validated unified API, best-effort request limiting
- `lib/live-ops/types.ts`: normalized types, radius geometry and sanitizers
- `lib/live-ops/cache.ts`: provider TTL cache, single-flight requests, timeout/retry, inbound and per-provider process-local request budgets
- `lib/live-ops/opensky.ts`: OpenSky state-vector adapter
- `lib/live-ops/adsbexchange.ts`: ADS-B Exchange adapter; the current implementation classifies a response as military when bit 0 of numeric/integer-string `dbFlags` is set, or when the provider exposes `mil === true`. Confirm the current provider schema, semantics, and account terms before treating classification as production-validated.
- `lib/live-ops/satellites.ts`: N2YO `/above` adapter
- `lib/live-ops/cctv.ts`: Caltrans District 5 public CCTV feed adapter

## Environment
Copy the following keys into the hosting environment (never commit real values):
```dotenv
OPENSKY_CLIENT_ID=
OPENSKY_CLIENT_SECRET=
ADSBX_API_KEY=
SATELLITE_API_KEY=
```
OpenSky can be queried anonymously subject to its current service policy and quotas when both credentials are absent; if only one of `OPENSKY_CLIENT_ID` or `OPENSKY_CLIENT_SECRET` is configured, the adapter fails closed. When both are configured, it uses the OAuth2 client-credentials flow and caches the bearer token server-side. ADS-B Exchange and N2YO layers are OFFLINE until their respective valid API keys are configured. Caltrans District 5 CCTV does not require a key for the public feed. Credential presence and provider access in the actual hosting environment have not been verified by this document.

## API
`GET /api/live/ops?lat=36.57&lon=-121.525&radius_nm=40`
- Validates coordinate ranges and a 1–150 NM radius.
- OpenSky cache: 7 seconds; ADS-B Exchange: 7 seconds; N2YO: 45 seconds; Caltrans CCTV: 180 seconds.
- Provider errors return empty arrays and an `offline` status when no cached result exists. Cached last-good provider data is returned as `degraded` when refresh fails.
- Counts are derived only from returned, normalized records. A count is `null` when that provider is offline without usable cached data.
- Radius filtering uses great-circle distance after bounding-box/provider queries. The bounding-box implementation clamps longitude at ±180°; antimeridian crossing behavior is not implemented and needs a regression test/fix before claiming global coordinate correctness.
- Inbound and outbound provider request budgets are per Node.js process, with an in-memory cache. Multi-instance/serverless production needs a shared rate-limit/cache backend (e.g. Redis) for enforceable global quotas. Configure the reverse proxy to strip client-supplied forwarding headers and append the actual client IP before relying on IP-based throttling.

## Data/coverage caveats
- OpenSky is a public state-vector source; its results are not a guarantee of all aircraft in the radius. The adapter and returned coverage have not been live-validated here.
- ADS-B Exchange military classification uses `dbFlags` bit 0 when present and falls back to explicit `mil === true`; no callsign-pattern inference is used. This implementation behavior is covered by unit tests, but provider API compatibility, account entitlements, and live record coverage are not verified. Keep its status unverified until tested against a controlled current response.
- N2YO's `/above` search radius is an angular radius from zenith, not a ground-distance radius. The adapter uses a bounded sky cone, then filters each provider-supplied satellite ground footprint with great-circle distance. If no footprint lies within the configured radius, it widens the sky cone and includes only footprints within a capped expanded geographic radius, labelled `NEARBY`. The response includes satellite ID/name/position/altitude; velocity, azimuth, elevation, provider observation timestamp and pass predictions are unavailable in this response shape and are left null rather than fabricated. This provider is not a complete satellite catalogue and has not been live-validated here.
- CCTV coverage comes from the Caltrans District 5 public status feed, not an asserted county-wide count. Missing or invalid coordinates are skipped. Status is `UNKNOWN` unless the feed provides an explicit service flag. Feed schema, availability, and preview URLs still require controlled live validation.
- Current source renders OpenStreetMap raster tiles (`https://tile.openstreetmap.org`) and places markers using Web Mercator coordinates. Attribution is visible in the UI. `next.config.ts` `img-src` allows the OSM tile host and Caltrans camera image host; `connect-src` is same-origin, with provider requests handled server-side. The public OSM tile service is best-effort and does not provide a production SLA; review its tile usage policy and expected traffic before launch, and use an appropriate hosted tile provider for sustained/high-volume production traffic.
- Counts are derived from normalized response records, not target counts. No provider count, source availability, tile availability, build success, or deployment status should be described as verified without evidence from the actual environment.

## Verification status — 2026-10-14
- GitHub PR #225 is merged, commit `001e4576ad4bbb52516aea9f8e0f542432be371b`.
- GitHub Actions run [38474468201](https://github.com/ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond/actions/runs/38474468201) is failed. The available job response has no usable step metadata/log URL, and the log/step retrieval APIs did not expose actionable execution output. Therefore the specific failure cause and npm/typecheck/test/build results remain UNVERIFIED; do not infer a root cause or claim successful tests.
- No live provider call, credential injection, staging deployment, or production deployment is evidenced by this audit.

## Production checklist
1. Recover executable GitHub Actions logs/steps and fix the verified cause; run `npm ci`, `npm run typecheck`, `npm test`, and `npm run build` successfully in CI.
2. Configure `ADSBX_API_KEY` and `SATELLITE_API_KEY` in authorized server-side secret storage; add OpenSky credentials only if provisioned. Never put secrets in source, client bundles, issues, or chat.
3. Make controlled live calls to OpenSky, ADS-B Exchange, N2YO and Caltrans. Record timestamp, sanitized HTTP status, schema validation, normalized counts, cache behavior, timeout/retry, and sanitized failure modes.
4. Confirm least-privilege CSP by observing expected Caltrans camera preview and OSM tile requests; add no wildcard origins. Review the map provider policy, attribution, privacy implications, quotas and SLA.
5. Add/fix tests for antimeridian bounds, strict coordinate/timestamp validation, provider isolation, retry/cache behavior, API validation, and UI health/degradation/accessibility. Run all tests in CI.
6. Deploy shared cache and rate limiting/circuit breaking (Redis or equivalent), or have an authorized owner explicitly approve a documented deferral and its risk before production.
7. Validate health endpoints, independent provider failure handling, stale-cache behavior, and the all-providers-offline UI state from staging.
8. Verify hosting project access, stage deployment, execute smoke tests, and test/document rollback. Do not inject secrets or deploy until the authorized project is confirmed.
9. Record only reproducible commands, outputs, sanitized evidence, verified provider results and current architecture in this document and any release notes.
10. Open a follow-up PR only for reviewable source/docs/tests after its checks run; do not label it release-ready or deploy production until each required gate is evidenced and explicitly reviewed.
