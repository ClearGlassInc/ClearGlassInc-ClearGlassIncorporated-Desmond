# Chualar — Monterey County Live Operations

## Files
- `app/chualar/page.tsx`: dashboard route at `/chualar`
- `app/chualar/ChualarOperations.tsx`, `chualar.module.css`: independent layer toggles, 10-second refresh, selectable markers and inspector
- `app/api/live/ops/route.ts`: validated unified API, best-effort request limiting
- `lib/live-ops/types.ts`: normalized types, radius geometry and sanitizers
- `lib/live-ops/cache.ts`: provider TTL cache, single-flight requests, timeout/retry, inbound and per-provider process-local request budgets
- `lib/live-ops/opensky.ts`: OpenSky state-vector adapter
- `lib/live-ops/adsbexchange.ts`: ADS-B Exchange adapter; military classification uses the documented `dbFlags & 1` bit or an explicit boolean `mil === true`
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
OpenSky can be queried anonymously subject to its current service policy and quotas; when credentials are configured, the adapter uses the documented OAuth2 client-credentials flow and caches the bearer token server-side. ADS-B Exchange and N2YO layers are OFFLINE until their respective valid API keys are configured. Caltrans District 5 CCTV does not require a key for the public feed.

## API
`GET /api/live/ops?lat=36.57&lon=-121.525&radius_nm=40`
- Validates coordinate ranges and a 1–150 NM radius.
- OpenSky cache: 7 seconds; ADS-B Exchange: 7 seconds; N2YO: 45 seconds; Caltrans CCTV: 180 seconds.
- Provider errors return empty arrays and an `offline` status when no cached result exists. Cached last-good provider data is returned as `degraded` when refresh fails.
- Counts are derived only from returned, normalized records. A count is `null` when that provider is offline without usable cached data.
- Radius filtering uses great-circle distance after bounding-box/provider queries.
- Inbound and outbound provider request budgets are per Node.js process. Multi-instance production needs a shared rate-limit/cache backend (e.g. Redis) for enforceable global quotas. Configure the reverse proxy to strip client-supplied forwarding headers and append the actual client IP before relying on IP-based throttling.

## Data/coverage caveats
- OpenSky is a public state-vector source; its results are not a guarantee of all aircraft in the radius.
- ADS-B Exchange military records are included only when the response's explicit `mil` flag is boolean true. No callsign-pattern inference is used.
- N2YO's `/above` search radius is an angular radius from zenith, not a ground-distance radius. The adapter uses a bounded sky cone, then filters each provider-supplied satellite ground footprint with great-circle distance. If no footprint lies within the configured radius, it widens the sky cone and includes only footprints within a capped expanded geographic radius, labelled `NEARBY`. The response includes satellite ID/name/position/altitude; velocity, azimuth, elevation, provider observation timestamp and pass predictions are unavailable in this response shape and are left null rather than fabricated. This provider is not a complete satellite catalogue.
- CCTV coverage comes from the Caltrans District 5 public status feed, not an asserted county-wide count. Status is `UNKNOWN` unless the feed provides an explicit service flag.
- The map background is currently a schematic operational plot, not a street/terrain basemap. Markers use provider coordinates. A production basemap remains a release gate: select an approved tile provider, add visible attribution, and review CSP, provider usage terms, caching and tile-request policies before deployment.
- “Live flights 9.6K”, “Military 171”, “Satellites 838” and “CCTV 800” are not hardcoded. The dashboard displays only actual returned counts or “—”.

## Production checklist
1. Configure ADSBX_API_KEY and SATELLITE_API_KEY in hosting secret storage.
2. Add OpenSky credentials if provisioned; never put credentials in client code.
3. Configure a shared Redis-backed cache and rate limiter for serverless/multi-region deployment.
4. Confirm current provider terms, quota, retention and attribution obligations.
5. Run `npm run typecheck`, `npm test`, and `npm run build` in CI; do not treat a workflow that starts but executes zero steps as a successful test run.
6. Verify endpoint connectivity and provider schemas from the actual deployment environment; mark the deployment as a prototype until checks pass.
7. The current map is schematic; do not advertise it as a full geographic basemap until a licensed/approved tile layer is integrated and verified.
