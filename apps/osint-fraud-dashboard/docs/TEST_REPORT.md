# Test report

Run on 2026-10-08 in a Linux container with Node 22.22.0 and a native
PostgreSQL 16 server. Docker was installed but its daemon was not running, so
the Docker image and `docker compose up` were **not** built or started; the
compose file was validated with `docker compose config` only.

## Real-world detection performance

**Not measured.** No real incident, transaction or evidence data was
supplied, and the referenced "suppressed incidents" were not available. There
is no precision, recall, false-positive rate, fraud probability or loss figure
for any rule. The results below show that the code behaves as designed on
synthetic fixtures; they say nothing about how well any rule detects fraud.

## Synthetic-fixture results

| Check | Command | Result |
|---|---|---|
| Type check | `npm run typecheck` | pass |
| Unit tests | `npm test` | 62 passed, 0 failed (5 files) |
| Integration tests (PostgreSQL) | `npm run test:integration` | 18 passed, 0 failed (2 files) |
| Production build | `npm run build` | pass, 20 routes, no warnings |
| Build without database or `.env` | `next build` with neither set | pass (mirrors the Docker image build) |
| Fresh migrate + seed | `prisma migrate deploy && prisma db seed` on an empty database | pass, 12 alerts |
| Dependency audit | `npm audit` | 0 vulnerabilities (after overriding `mysql2` 3.24.5 and `deepmerge-ts` 8.0.2, pulled in by the Prisma CLI) |
| Compose file | `docker compose config` | valid; refuses to start without `SESSION_SECRET` |
| Repository CI gates | `python3 scripts/ci_local.py` (offline) | all 11 offline gates pass with this change in the tree (see note) |

Note on the repository gates: the first run reported two failures, both
environmental and both reproduced with this change stashed. "Generated search
assets are current" refuses to run in a shallow clone, and it passed after
`git fetch --unshallow`. "Control-plane tests" lacked `fastapi` and
`pydantic_settings`; after `pip install -r control-plane/requirements.txt` it
passed with 735 passed and 5 skipped.

### What the tests cover

| Requirement | Where |
|---|---|
| Supported rule match | `engine.test.ts` (sequence, aggregate, record checks); `workflow.test.ts` (`SYN-R-001` on `SYN-V-001`) |
| Legitimate transaction with similar characteristics | `SYN-V-002`: bank change verified, payment 69 days later, gives `NO_MATCH`; purchase pair below the total gives `NO_MATCH` |
| Missing critical fields | `SYN-PAY-005`, `SYN-PAY-006`, `SYN-CO-303` give `INSUFFICIENT_DATA`; an absent column is unknown, a blank one is not |
| Temporal boundaries | window end inclusive (`+0 ms` in, `+1 ms` out), same-instant and earlier events excluded, grace days |
| Duplicate imports | identical re-import and in-file duplicate skipped; same id with different content rejected |
| Incorrect candidate entity link | name-similar vendors with different identifiers stay `CANDIDATE`, are rejected by the reviewer, and are not recreated |
| Rule-version change | approving v2 supersedes v1; old alerts keep v1; re-evaluation creates v2 alerts and no duplicates |
| Unauthorized access | read-only refused on 7 write paths with audited denials; analysts cannot approve or close; no self-approval, even for administrators; tampered or expired demo tokens are rejected, and only demo users resolve |
| Malicious markup in imported evidence | stored verbatim, rendered escaped, `javascript:` URLs refused, no `dangerouslySetInnerHTML` anywhere |
| Rule evaluation and missing-data outcomes | Kleene three-valued logic; `NO_MATCH` never labelled safe |
| Source-to-rule traceability | every `SYN-R-001` condition maps to stored evidence or the incident through `RuleSupport` rows; rules citing unknown evidence are refused |
| Import validation | row, line and field errors with fixes; size, type, encoding and row limits; field mapping |
| Safe rendering | `rendering.test.tsx` and the browser check below |
| Export redaction | names, approvers, contact details, account numbers and confidential excerpts removed; unredacted export administrator-only and audited |
| Overview counts | every overview figure equals a direct database count |
| No outbound fetching | `fetch` spy shows zero calls while collecting evidence; the allowlist guard refuses private hosts, IP literals, http and non-443 ports |

A mutation check was run on the authorization layer: with the server-side
permission check disabled, 6 integration tests failed. With it restored, all
pass.

### Browser walkthrough (Chromium via Playwright, production build)

- All 8 main screens and the detail pages return 200 for the analyst.
- `SYN-EV-004`'s `<script>` excerpt shows as text; no dialog fired and no
  injected `<img>` element exists.
- The invalid import lists 8 errors and imports nothing.
- Read-only: no audit link, the confidential excerpt is withheld, and `/audit`
  redirects with an error.
- The reviewer approves a pending rule version through the UI; the analyst
  proposes a new version through the JSON editor; a broken definition shows
  the validation errors.
- No horizontal overflow on 11 pages at 1440 px or 390 px wide.
- No browser console errors.
- With `npm start`, the server listens on 127.0.0.1 only.
