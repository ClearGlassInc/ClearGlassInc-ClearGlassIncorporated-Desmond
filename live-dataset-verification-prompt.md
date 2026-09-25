# Live Dataset / Live Feed Verification Prompt
Target repos: `ClearGlasslabs/ClearGlassInc.` and `ClearGlasslabs/Opal-Koboi` (OPAL production site)

---

## PROMPT (paste into Claude Code / Cursor / Copilot agent / any repo-aware coding agent)

You are auditing the ClearGlass live-data dashboard for functional correctness. This site pulls "live dashboard data" from identified public third-party feeds (camera grid, airspace/aircraft tracking, and any Foundry/Artemis dataset connectors referenced in the docs). Your job is to prove — with evidence, not assumptions — whether every live dataset is actually live, functional, and returning fresh data right now. Do not report success unless you have verified it directly.

### Step 1 — Inventory every live data source
- Search the full repo (`assets/`, `modules/`, `intelligence/`, `docs/`) for every fetch/XHR/WebSocket/API call, every `data-camera-*` / `data-airspace-*` attribute handler, and every reference to `dataset`, `feed`, `foundry://`, or third-party API keys/URLs.
- Produce a table: source name, file + line number, endpoint URL, expected update frequency, auth requirement (API key / public / none).

### Step 2 — Test each feed live, right now
For every source found:
- Make the actual request (respecting rate limits and auth) and capture the raw response.
- Compare the response's timestamp/last-updated field against current wall-clock time. Flag anything stale (data older than its expected refresh interval).
- If the endpoint returns HTTP errors, empty payloads, or malformed JSON/XML, log the exact error and status code.
- For the camera grid (`cam-grid`, `data-camera-refresh`): confirm images actually load (not 404/broken), and confirm the `refreshCams` handler re-fetches on click rather than reusing cached DOM state.
- For the airspace/aircraft filter (`data-airspace-filter`): confirm the underlying tracking feed returns current aircraft/position data, not a fixture or hardcoded sample array.

### Step 3 — Audit failure handling
- Identify what the UI does when a feed is down, rate-limited, or returns bad data. Does it fail silently (bad — user sees stale data with no warning) or show a visible "feed unavailable" state?
- Check whether there's any retry/backoff logic, or whether a single failed request permanently breaks that panel until page reload.

### Step 4 — Check licensing/ToS compliance for each live source
- Cross-reference `legal.html` and any Acceptable Use Policy language against how each feed is actually being called (e.g., scraping vs. authorized API, attribution requirements, rate limits respected).

### Step 5 — Report and fix
Output a structured report with three sections:
1. **CONFIRMED LIVE** — sources verified working with fresh data, timestamped evidence.
2. **BROKEN / STALE / MOCKED** — sources that failed, with exact file, line, error, and root cause (not just symptom).
3. **FIX PLAN** — for each broken item, propose the minimal root-cause code change (not a patch/workaround) needed to restore live functionality, in priority order by user-facing impact.

Do not mark anything "working" unless you executed the request yourself and saw a fresh, valid response. If a live check is impossible from this environment (e.g., feed requires production credentials), say so explicitly instead of guessing.
