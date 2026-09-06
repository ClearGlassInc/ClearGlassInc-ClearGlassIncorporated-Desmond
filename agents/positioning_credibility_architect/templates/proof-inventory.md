# Proof inventory

Source of truth for what can be claimed publicly. An artifact that cannot point
at a row here is not ready to draft. Update before each weekly deep artifact.

Provenance values: `measured` (a number from a named system), `shipped` (exists
and is inspectable), `designed` (target state, not deployed), `opinion` (argued
from stated reasoning).

| ID | Asset | Domain | Provenance | Anchor (path / commit / run / source) | Public? | Redaction needed | Best use |
|----|-------|--------|-----------|----------------------------------------|---------|------------------|----------|
| P-001 | | software-architecture | shipped | | yes/no | | architecture breakdown |
| P-002 | | ai-automation | designed | | | | contrast piece |
| P-003 | | cybersecurity | shipped | | | | threat model |
| P-004 | | technical-leadership | measured | | | | decision journal |

## Rules

1. `measured` rows must name the source system and the measurement window. No
   remembered numbers.
2. `designed` rows may only produce artifacts that say the design is not
   deployed.
3. Rows marked "Public? no" require principal approval before any external use,
   even anonymized.
4. Client, partner, and customer identities never enter this file. Record the
   pattern, not the party.
5. A row that has produced three artifacts is exhausted — find new evidence
   rather than restating it.

## Candidate sources in this repository

- `clearglass-commerce/control-plane/app/` — governance risk scoring, approval
  routing, append-only audit ledger, admin auth, rate limiting, webhook
  idempotency. Strong `shipped` material for AI-automation and governance
  artifacts.
- `.github/workflows/` — CI gates that encode the invariants; good evidence that
  policy is enforced rather than documented.
- `tools/internal_links.py` — deterministic generator with a `--check` freshness
  gate; a clean example of "clarity as a reliability feature".
- `sentinel/` — named-agent stack; honor the status banners, the v9
  distributed-architecture documents are `designed`.
- `operations/` — generated reports; usable for `measured` claims where the
  generating job and window are named.
