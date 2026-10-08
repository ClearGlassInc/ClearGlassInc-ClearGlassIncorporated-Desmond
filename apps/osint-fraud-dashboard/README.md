# ClearGlass OSINT Fraud Detection Dashboard (prototype)

An evidence-first investigation workspace. It turns authorized incident
records into explainable, versioned detection rules, evaluates them
deterministically against imported records, and gives analysts a traceable
review workflow.

> **Status: local prototype on synthetic data.**
>
> - The "suppressed incidents" this work was asked to model have **not been
>   supplied or verified**. Nothing in this app describes them, and no record
>   here is labelled suppressed.
> - All bundled data is **synthetic**: fictional names, `.example` domains, and
>   records prefixed `SYN-`. Every screen labels it.
> - The six rule templates are **illustrative investigative checks**, not
>   patterns from any real incident. A match is a reason to review, not a
>   finding of fraud.
> - No detection accuracy, fraud probability, savings or prevented loss has
>   been measured, and none is displayed.
> - Nothing is deployed. Demo sign-in works only with `APP_ENV=local` or `test`.

## Screens

| Screen | What it shows |
|---|---|
| Overview | Imported records, alerts awaiting review, evidence completeness, ingestion errors. Every number is a database count. |
| Investigations | Searchable cases with filters, owners, timelines, evidence-linked notes, review states and redacted export. |
| Alert queue | Rule matches and insufficient-data results, with conditions, actual values, matched records, missing inputs, supporting evidence and decision history. |
| Evidence library | Source records, excerpts, provenance, hashes, timestamps, verification status, and which rules and cases use them. |
| Incidents | The incident-to-rule workflow (steps A-G) for each documented incident. |
| Pattern registry | Versioned rules with condition-to-evidence mapping, thresholds and their rationale, approval history and a preview for pending versions. |
| Entity explorer | People, organizations, vendors and domains; every relationship shows its basis and review state. |
| Import center | CSV/JSON validation, field mapping, duplicate handling and ingestion reports. |
| Audit view | Imports, rule changes, evaluations, review decisions, exports, sign-ins and denied access. |

Every screen distinguishes **Synthetic**, **Allegation**,
**Source-supported observation**, **Analyst interpretation** and **Reviewed
finding** with text labels.

## Start it

### With Docker (recommended)

Needs Docker with Compose v2. Everything binds to `127.0.0.1`.

```bash
cd apps/osint-fraud-dashboard
cp .env.example .env
# Put a random 32+ character value in SESSION_SECRET, for example:
sed -i.bak "s/^SESSION_SECRET=$/SESSION_SECRET=$(openssl rand -hex 32)/" .env && rm .env.bak
docker compose up --build
```

Then open <http://127.0.0.1:3050> and pick a demo user. The `migrate` service
applies migrations and loads the synthetic seed once. To start over:
`docker compose down -v`.

### Without Docker

Needs Node 22 and PostgreSQL 16.

```bash
cd apps/osint-fraud-dashboard
npm ci
cp .env.example .env              # set DATABASE_URL and SESSION_SECRET
npx prisma generate
npm run db:migrate                # prisma migrate deploy
npm run db:seed                   # synthetic fixtures; skipped if users exist
npm run build && npm start        # http://127.0.0.1:3050  (or: npm run dev)
```

`npm run db:reset` drops the database, re-applies migrations and re-seeds.

### Demo users

| User | Role | Can |
|---|---|---|
| Demo Analyst | analyst | import, add evidence, propose rules, run active rules, triage alerts, open cases, add notes, propose entity links, redacted export |
| Demo Reviewer | reviewer | approve or reject rule versions (not their own), make closing decisions, verify evidence, confirm/reject/reverse entity links, audit view |
| Demo Administrator | administrator | everything, including unredacted export; still cannot approve a rule version they proposed |
| Demo Read-only | read-only | view; confidential and restricted excerpts are withheld |

Demo sign-in has no password. It is refused at startup when `APP_ENV` is
`production` or unset, and it only resolves users flagged as demo users.

## Test it

```bash
npm test                                   # unit tests, no database needed
npm run typecheck
TEST_DATABASE_URL=postgresql://USER:PASS@127.0.0.1:5434/cg_osint_test npm run test:integration
npm run build
npm run audit:deps
```

Integration tests reset the database in `TEST_DATABASE_URL`, so they refuse
any database whose name does not end in `_test`, and they fail (not skip)
when the variable is unset. With the compose stack running, create one with
`docker compose exec db createdb -U cg_osint cg_osint_test`.

The latest results are in [docs/TEST_REPORT.md](docs/TEST_REPORT.md). They are
synthetic-fixture results only; real-world detection performance has not been
measured.

## Try the workflow

1. **Overview** as the analyst: 26 synthetic records, alerts in each review state.
2. **Alert queue** → the escalated `SYN-R-001` alert: each condition, its actual
   values and the evidence behind it.
3. **Incidents** → `SYN-INC-001`: observations, actors, sequence, the evidence
   gap and the contradiction, and the rule versions derived from it.
4. **Pattern registry** → `SYN-R-001` v2 is pending. Sign in as the reviewer,
   preview it, and approve it with a rationale; v1 is superseded and its alerts
   keep pointing at v1.
5. **Import center** → run `examples/imports/invalid-transactions.csv` (row-level
   errors, nothing imported) and `duplicate-transactions.csv` (duplicates
   skipped).
6. **Evidence library** → `SYN-EV-004` holds `<script>` markup that renders as
   inert text.
7. **Entity explorer**: the incorrect "Northwind" name-similarity link was
   rejected by the reviewer; the shared-address link awaits review.

## Data formats

Example files live in [`examples/imports/`](examples/imports):

| File | Purpose |
|---|---|
| `synthetic-vendors.csv`, `synthetic-transactions.csv`, `synthetic-evidence.json`, `synthetic-transactions-partial.json`, `synthetic-incident.json` | The seed. Valid imports. |
| `duplicate-transactions.csv` | One identical re-import, one in-file duplicate, one new row. |
| `invalid-transactions.csv` | Conflicting id, unknown type, ambiguous amount and date, missing id, short row. |
| `public-evidence-template.json` | A starting point for real public-source evidence. |

- Dates are ISO 8601: `YYYY-MM-DD` (read as UTC midnight) or a date-time with
  `Z` or an offset. `03/04/2026` is refused as ambiguous.
- Amounts are plain decimals with at most two places; no symbols or thousands
  separators.
- Lists (`documents`) are JSON arrays, or `;`-separated in CSV.
- **A column that is present but empty is "blank". A column that is absent is
  "not supplied"**, and rules treat it as unknown, never as a negative.
- A batch with any invalid row is rejected as a whole. Identical re-imports
  are skipped and reported.

Rules: [`rules/templates/`](rules/templates) holds the six illustrative
templates; [`rules/derived/`](rules/derived) holds `SYN-R-001` v1 and v2,
derived from the synthetic incident.

## Further reading

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): architecture, evidence model,
  rule semantics, security design.
- [docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md): what must
  change before real data or a deployment.
- [docs/TEST_REPORT.md](docs/TEST_REPORT.md): what was run and what passed.

## Boundaries

This prototype does not contact third parties, block payments, accuse
individuals or report to authorities. It does not fetch URLs server-side, and
it does not bypass logins, paywalls, CAPTCHAs or rate limits. Deploying it, or
loading real personal or incident data into it, needs an explicit decision on
the destination and the data scope first.
