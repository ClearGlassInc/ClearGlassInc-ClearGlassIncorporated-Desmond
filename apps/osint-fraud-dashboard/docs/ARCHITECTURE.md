# Architecture and evidence model

## Layout

```
apps/osint-fraud-dashboard/
  prisma/schema.prisma, prisma/migrations/   data model and SQL migration
  prisma/seed.ts                             loads the synthetic seed via src/lib/seed.ts
  rules/templates/*.v1.json                  six illustrative rule templates
  rules/derived/syn-r-001.v{1,2}.json        rule derived from the synthetic incident
  examples/imports/                          example CSV/JSON (valid, duplicate, invalid)
  src/app/                                   Next.js App Router pages, server actions, API routes
  src/components/                            labels, layout pieces, review forms
  src/lib/rules/                             rule schema (zod), engine, record view
  src/lib/import/                            CSV parser, field mapping, row validation
  src/lib/services/                          every read/write that needs authorization
  src/lib/auth/                              role matrix, auth interface, demo provider
  src/lib/entities/, export/, osint/         entity resolution, redaction, source adapters
  tests/unit/, tests/integration/            vitest projects
```

Stack: Next.js 16 (App Router, server components and server actions),
TypeScript, Tailwind CSS 4, PostgreSQL 16 through Prisma 7 with the `pg`
driver adapter, zod 4, vitest.

## Request flow

```
page / server action / route handler
  -> requireCtx()            resolves the actor through the configured AuthProvider
  -> service function        requirePermission(role), zod validation, business rules
       -> Prisma transaction  writes + AuditEvent in the same transaction
  -> render or redirect      flash text rendered as text
```

Authorization lives in the service layer (`src/lib/services/*`), not in the
pages. A page hiding a button is a convenience; the service refuses the call
regardless, records a `security.access_denied` audit event, and throws
`ForbiddenError`. The integration tests call services directly as each role.

## Authentication

`src/lib/auth/actor.ts` defines the interface:

```ts
interface AuthProvider {
  name: string;
  isDemo: boolean;
  resolve(cookie: (name: string) => string | undefined): Promise<Actor | null>;
}
```

- `UnconfiguredAuthProvider` (the default) resolves nobody, so every page
  redirects to `/login` and every action is refused.
- `DemoAuthProvider` signs a user id and expiry into an HMAC-SHA256 cookie
  (`httpOnly`, `SameSite=Strict`, 8 hours). It resolves only users with
  `isDemo = true`. `loadConfig()` refuses `DEMO_AUTH_ENABLED=true` unless
  `APP_ENV` is `local` or `test`; an unset `APP_ENV` counts as production.
  `src/instrumentation.ts` runs that check at server start.
- A production provider would verify an OIDC/SAML session, map the verified
  subject to a `User` row, and take the role from that row, never from the
  token or the browser.

### Roles

| Permission | read-only | analyst | reviewer | administrator |
|---|:-:|:-:|:-:|:-:|
| View workspace | ✓ | ✓ | ✓ | ✓ |
| Read confidential/restricted excerpts | | ✓ | ✓ | ✓ |
| Import, add evidence, open cases | | ✓ | | ✓ |
| Propose rules, run active rules, propose entity links | | ✓ | | ✓ |
| Triage alerts and cases, add notes | | ✓ | ✓ | ✓ |
| Closing decisions, approve rule versions, verify evidence, review entity links | | | ✓ | ✓ |
| Redacted export | | ✓ | ✓ | ✓ |
| Unredacted export | | | | ✓ |
| Audit view | | | ✓ | ✓ |

Separation of duties: the proposer of a rule version can never approve or
reject it, whatever their role.

## Evidence model

Three layers are stored separately on purpose:

| Layer | Table | Holds |
|---|---|---|
| Original evidence | `Source`, `Evidence` | The material as collected: verbatim excerpt, URL, location in the document, timestamps, content hash, classification, extraction method, limitations |
| Extracted facts | `ExtractedFact` | A statement pulled from one evidence record, labelled allegation, source-supported observation, or (reviewer only) reviewed finding |
| Interpretation | `InvestigationNote` (`INTERPRETATION`) | What an analyst thinks it means, labelled as interpretation |

Provenance fields on `Evidence`: stable `recordId`, source, `url`,
`documentLocation`, `publishedAt`, `observedAt`, `collectedAt`, `ingestedAt`,
`contentHash` (+ algorithm), `verificationStatus`, `verifiedBy`/`verifiedAt`,
`accessClassification`, `extractionMethod`, `origin`, `limitations`,
`providedFields` and `missingFields`.

**A content hash is not proof.** It is SHA-256 over the canonical collected
content (excerpt, URL, location, publication date). It lets you detect that
stored content changed later. It says nothing about whether the content is
true; the UI and exports say so next to every hash.

**Claim status** appears on incidents, facts, relationships and cases:
`ALLEGATION`, `SOURCE_SUPPORTED_OBSERVATION`, `ANALYST_INTERPRETATION`,
`REVIEWED_FINDING`. Only a reviewer decision produces `REVIEWED_FINDING`.

**Origin** separates `SYNTHETIC` fixtures, `PUBLIC_SOURCE` material,
`INTERNAL_RECORD`s and `ANALYST_ENTERED` data. A public-source import may hold
only `PUBLIC` evidence.

### Supplied, blank and unknown

Each imported transaction records `providedFields`: the canonical fields the
source actually supplied. A CSV column that exists is supplied even when a
cell is empty ("blank"); a column or JSON key that is absent is "not
supplied". The rule engine reads every field as one of `UNKNOWN`, `BLANK` or
a value, so "the export did not include the PO column" never becomes "the
payment had no PO".

## Rules

A rule definition is JSON validated by `ruleDefinitionSchema`
(`src/lib/rules/schema.ts`). It carries id, name, description, version (on
the `RuleVersion` row), supporting incident and evidence ids, required input
fields, a pattern, named thresholds with value, unit, basis and rationale,
entity-matching method, missing-data behaviour (always `INSUFFICIENT_DATA`),
benign explanations, false-positive considerations, and a review priority
(not a probability).

The schema refuses a rule when:

- a condition cites neither evidence, an incident, nor an explicitly stated
  analyst assumption;
- a threshold is referenced but not defined, has no rationale, or claims a
  policy/evidence basis without citing the evidence;
- a field the pattern uses is missing from `requiredFields`;
- a non-illustrative rule cites nothing, or an illustrative one has no
  disclaimer;
- any `TODO` placeholder remains (the "draft from incident" skeleton is full
  of them, so it cannot be activated unedited).

The service layer then refuses the rule if any cited evidence or incident id
does not exist, and writes one `RuleSupport` row per (condition, evidence or
incident) with foreign keys. That is the source-to-rule traceability: from a
rule version to its evidence, and from evidence to every rule that relies on
it.

### Patterns

| Kind | Evaluates | Used by |
|---|---|---|
| `sequence_within_window` | Per explicit vendor id: a record of type A followed by type B, strictly after and at most N days later (end inclusive) | CG-T-001, SYN-R-001 |
| `aggregate_within_window` | Per explicit vendor id: at least K records, each below X, totalling at least X within N days (end inclusive) | CG-T-002 |
| `record_checks` | Per record: scope conditions, then conditions `is_blank`, `date_after` (with grace days), `list_missing_any`, `gte`, `lt` | CG-T-003 to CG-T-006 |

### Semantics

- Conditions are three-valued: TRUE, FALSE or UNKNOWN. They combine with
  Kleene AND: any FALSE gives `NO_MATCH`, else any UNKNOWN gives
  `INSUFFICIENT_DATA`, else `MATCH`.
- `NO_MATCH` means "conditions not met on the supplied records". Its
  explanation says it is not a determination that the activity is legitimate.
  No record is ever labelled safe.
- `INSUFFICIENT_DATA` lists each missing `record.field`. Its alert starts in
  **Needs evidence**, so incomplete records are never silently cleared.
- Records without an explicit vendor id cannot be grouped and return
  `INSUFFICIENT_DATA`; names are never used to guess the entity.
- The engine has no I/O and takes the clock as a parameter: the same records
  and rule version always give the same result.

Each result carries the outcome, rule version id, matched record ids, every
evaluated condition with expected and actual values, missing fields,
supporting evidence references, a human-readable explanation and the
evaluation timestamp. All results are stored in `RuleEvaluation`; `MATCH` and
`INSUFFICIENT_DATA` also create an `Alert`.

### Versions and approval

- Creating a rule or editing it creates a new `RuleVersion` in
  `PENDING_APPROVAL`. Earlier versions are never edited.
- Only `ACTIVE` versions run. A reviewer other than the proposer approves
  (activating it and marking the previous active version `SUPERSEDED`) or
  rejects, with a rationale stored as a `ReviewDecision`.
- A pending version can be previewed against current records without creating
  alerts.
- Alerts keep the `ruleVersionId` that produced them. Re-running evaluation
  does not duplicate an alert: the dedupe key is
  `sha256(ruleVersionId | outcome | subject | matched record ids)`.

## Incident-to-rule workflow

| Step | Where it lives |
|---|---|
| A. Documented observations | `IncidentStep` kind `OBSERVATION`, each citing evidence |
| B. Actors and entities | `IncidentStep` kind `ACTOR`; the text states what the evidence does not establish |
| C. Event sequence | `IncidentStep` kind `EVENT`, ordered, with `occurredAt` |
| D. Unavailable or contradictory evidence | `IncidentStep` kinds `EVIDENCE_GAP` and `CONTRADICTION` |
| E. Proposed rule | `/rules/new?incident=…` drafts a skeleton citing the incident |
| F. Condition-to-evidence mapping | each condition's `support`, persisted as `RuleSupport` rows |
| G. Approval before activation | `RuleVersion.status` and `ReviewDecision` |

Import refuses an incident step that cites no evidence unless it is an
evidence gap or explicitly flagged `isAssumption`, and the UI marks
assumptions as such.

## Entity resolution

`src/lib/entities/resolve.ts`:

- A link that the source record states (a vendor naming its organization) is
  stored as `CONFIRMED` with basis `EXPLICIT_IDENTIFIER`.
- Equal registration or tax identifiers, name similarity (token Jaccard ≥ 0.75
  after removing legal suffixes), equal normalised addresses and equal domains
  create `CANDIDATE` links only. Each records its basis and the statement that
  similarity is not evidence of ownership, control, collusion or wrongdoing.
- Reviewers confirm, reject, reverse a confirmed link, or reopen. Every move
  is a `ReviewDecision`; rows are never deleted, so a merge can be reversed
  and its history stays visible.
- Regenerating candidates never overwrites a link a reviewer has decided.

## OSINT adapters and untrusted content

`SourceAdapter` (`src/lib/osint/adapters.ts`) has two implementations, both
with `live: false`:

- `manual-url` records an analyst-supplied public URL and verbatim excerpt.
  The URL must be http(s) without embedded credentials. **The server never
  fetches it.**
- `mock-registry` returns fictional registry entries for demonstration.

`assertOutboundAllowed()` is the guard a future live adapter must call before
any request: https only, port 443, no IP literals or private/local hosts
(decimal and hex IPv4 forms are normalised by URL parsing first), and the host
must be on `OSINT_FETCH_ALLOWLIST`, which is empty by default. Redirects must
be re-checked per hop.

Imported and collected text is data. It is stored verbatim (control
characters stripped) and rendered only as React text nodes, so markup shows
as text. No component uses `dangerouslySetInnerHTML` (a unit test enforces
this). Links render only for http(s) URLs, with `rel="noopener noreferrer
nofollow"`. There is no AI component in the prototype; if one is added,
evidence text must be passed to it as quoted data and never as instructions.

## Review workflow

| From | To | Who |
|---|---|---|
| New | Needs evidence, Under review | analyst or reviewer |
| Needs evidence | Under review | analyst or reviewer |
| Under review | Needs evidence, Escalated for review | analyst or reviewer |
| Under review | Explained / no further action, Closed | reviewer |
| Escalated for review | Under review, Needs evidence, Explained, Closed | reviewer |
| Explained / no further action | Under review, Closed | reviewer |
| Closed | Under review | reviewer |

Every move needs a rationale of at least 10 characters and is appended to
`ReviewDecision` with the rule version in force. Updates are conditional on
the state the user saw, so a concurrent decision fails instead of being
overwritten. Nothing in the workflow contacts third parties, blocks payments
or reports anyone.

## Imports

`src/lib/import/validate.ts` (pure) and `src/lib/services/imports.ts` (database):

- File checks: extension matches the format; size ≤ `IMPORT_MAX_BYTES` (512 KB
  default); strict UTF-8; rows ≤ `IMPORT_MAX_ROWS`. Files are parsed in memory
  and never written to disk.
- Field mapping: explicit JSON mapping, or header matching that ignores case,
  spaces, `_` and `-`. Unmapped columns are reported and ignored.
- Row validation: zod per record type, with row, line, field and a fix in
  each message.
- Duplicates: identical content under the same id (in the file or already
  stored) is skipped and reported; the same id with different content is an
  error; identical content under a different id is a warning.
- Commit is all-or-nothing in one transaction, and the batch report is kept
  on `ImportBatch`.

## Exports

`GET /api/export/investigations/:id?mode=redacted|unredacted` returns JSON with
disclaimers and a `containsSyntheticData` flag. Redaction replaces user names
with roles, removes `approvedBy`, masks emails, phone numbers and 8+ digit
numbers in free text, and withholds confidential and restricted excerpts. It
is pattern-based and says so in the file. Unredacted export is
administrator-only. Every export is audited.

## Audit log

`AuditEvent` records imports, rule proposals and decisions, evaluations, alert
creation, review decisions, evidence collection and verification, entity
decisions, exports, sign-ins and denied access. It is an ordinary table that
a database administrator can modify. It is **not** immutable or tamper-proof;
see the production checklist.
