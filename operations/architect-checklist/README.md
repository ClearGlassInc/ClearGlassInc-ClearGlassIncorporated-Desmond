# Architect Checklist

Weekly architecture review records, one file per ISO week (`YYYY-Www.md`).

Each record covers the week's checklist items and, for every item, states what
was actually verified, what changed in the repo, and what remains open with an
owner and a target date. Open actions carry forward until closed — the
"Consolidated open actions" table at the foot of each record is the working
backlog.

## Conventions

- **Ground findings in the repository.** Cite the file and the behaviour. An
  audit finding that cannot be pointed at is an opinion.
- **Record blockers rather than substituting proxies.** If an item cannot be
  completed as written, say why and record the trigger that would unblock it. An
  item marked blocked with a clear reason is more useful than one that looks
  finished but rests on invented inputs.
- **Note the verification you ran.** Each record ends with the gates executed
  against its own changes, so a reader can tell what was checked from what was
  asserted.

## Records

| Week | Dates | Focus |
|------|-------|-------|
| [2026-W31](2026-W31.md) | 2026-07-27 → 2026-08-02 | CI/CD permission + secret audit; agent permission enforcement; K8s AI radar; CodeQL trial |
