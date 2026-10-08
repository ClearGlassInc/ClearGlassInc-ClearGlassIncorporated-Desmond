# Production-readiness checklist

The prototype runs locally on synthetic data. Before it holds real incident
records or personal information, or runs anywhere but a developer machine,
work through this list. Ticked items are in place today.

## In place

- [x] Server-side authorization on every service call, with denials audited
- [x] Separation of duties: a rule version's proposer cannot approve it
- [x] Input validation (zod) for imports, rules, notes and decisions
- [x] Untrusted content rendered as text; no `dangerouslySetInnerHTML`; links only for http(s)
- [x] Upload limits: type, size, UTF-8, row count; parsed in memory, never stored as files
- [x] No server-side URL fetching; an allowlist guard for any future live adapter
- [x] Secrets only from environment variables; `.env` is git-ignored; compose refuses to start without `SESSION_SECRET`
- [x] Demo sign-in refused unless `APP_ENV` is `local` or `test`
- [x] Redacted exports by default; unredacted export administrator-only and audited
- [x] Security headers (CSP, frame-ancestors none, nosniff, no-referrer)
- [x] Dependency audit clean (`npm audit`: 0 known vulnerabilities on 2026-10-08, after overriding `mysql2` and `deepmerge-ts` pulled in by the Prisma CLI)

## Before real data

- [ ] **Authorization to hold the data**: a documented legal basis and scope for every dataset, and a privacy impact assessment for any personal information
- [ ] **Retention and deletion**: a retention schedule, deletion path and legal-hold handling; today nothing is ever deleted
- [ ] **Per-case access control**: today any signed-in role can view every case; add case membership and classification-based row filtering
- [ ] **Encryption and backups**: encrypted storage, tested restores, key management
- [ ] **Validate rules on labelled data**: no precision, recall or false-positive rate has been measured. Thresholds in the templates are labelled assumptions
- [ ] **Currency handling**: amounts are compared without conversion; mixed-currency vendors need normalisation
- [ ] **Upload scanning**: add malware scanning if files are ever stored

## Before deployment

- [ ] **Identity provider**: implement `AuthProvider` against OIDC or SAML with MFA; build production images without the demo provider
- [ ] **Tamper-evident audit**: write audit events to append-only storage (a database role without UPDATE/DELETE on `AuditEvent`, plus an external write-once log), or hash-chain them as `bots/rfed_audit_bot.py` does for RFED. Until then the log is not evidence-grade
- [ ] **Nonce-based CSP** instead of `'unsafe-inline'` scripts
- [ ] **Rate limiting** on sign-in, imports, evaluation and exports
- [ ] **Background evaluation**: evaluation runs synchronously and loads every transaction into memory; move it to a job queue with pagination before volumes grow
- [ ] **Observability**: structured logs without personal data, error tracking, alerting on failed imports and denied-access spikes
- [ ] **CI**: no workflow was added. The repository's GitHub Actions runners are not being dispatched (see the root `CLAUDE.md`), so a workflow would report nothing. Add one once runners work: typecheck, unit and integration tests against a service Postgres, build, `npm audit`
- [ ] **Container hardening**: pinned base image digest, non-root user (already used), read-only filesystem, image scanning
- [ ] **Hosting decision**: destination, data residency and data scope approved explicitly. Nothing has been deployed, and no infrastructure was created or changed
