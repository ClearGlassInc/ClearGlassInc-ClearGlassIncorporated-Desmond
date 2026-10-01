# ADR 0003: Truth Forensics as a stdlib engine with a browser twin

- **Status:** Proposed (owner acceptance required)
- **Date:** 2026-09-30
- **Context layer:** ClearGlass Truth Forensics (media and evidence integrity)
- **Decision owners:** ClearGlass Inc.
- **Related:** `docs/TRUTH_FORENSICS.md`, `docs/TRUTH_FABRIC_FORENSICS.md`, `docs/BASELINE.md`, `CLAUDE.md`

## Context

The specification asks for evidence intake, hashing, provenance, media analysis, claim verification, human review and a report, delivered on the ClearGlass site. The system has to handle sensitive evidence, and it must never overclaim.

Two constraints decide where this can run:

1. **GitHub Pages deploys from a branch, and Actions dispatches no runners.** See `docs/BASELINE.md` F1 and the notice at the top of `CLAUDE.md`. The site is static, so nothing server-side ships with it.
2. **An existing prototype cannot host it.** The repository already contains "Truth Fabric" (`lib/truth-fabric/schema.ts`, `app/api/truth-fabric/assess/route.ts`, `app/reality-forensics/page.tsx`). It lives in the root Next.js app, which `docs/BASELINE.md` lists as "not currently deployed by any registered workflow". Its scoring also:
   - counts two items with identical hashes as independent channels;
   - returns `verified` with no recorded human decision;
   - sits behind a page that shows a fixed 98.7% score its code cannot produce.

   Findings and reproduction are in `docs/TRUTH_FORENSICS.md` §12.

## Decision

- **Reference engine.** Build Truth Forensics as a stdlib-only Python package (`truth_forensics/`). It is deterministic, float-free and emits canonical JSON. This matches the RFED audit-trail conventions already in the repository (`bots/rfed_audit_bot.py`).
- **Browser port.** Port it to one UMD file (`assets/js/truth-forensics-engine.js`) that runs in a Web Worker on the static site. Evidence never leaves the visitor's browser.
- **Parity gate.** Hold the two implementations together with a byte-for-byte parity test (`tests/test_truth_forensics_parity.py`), the same pattern as `tests/test_rfed_hash_parity.py`.
- **Truth Fabric untouched.** Leave the prototype unchanged and document its defects for the owner. Do not delete it, and do not rewrite its test's expected verdict.

## Consequences

- The console works on GitHub Pages today, with no backend, no key and no data transfer.
- Every engine change must land in both languages. The parity test fails otherwise.
- **Heavy analysis cannot run in the browser.** A trained classifier, C2PA signature validation or RFC 3161 verification would need a server, which does not exist on Pages. These are listed as unimplemented adapters, not implied.
- **Two media-integrity codebases now exist.** Consolidating them, or retiring Truth Fabric, is an owner decision.

## Rollback

The system is additive. Reverting the Truth Forensics commits removes:
- the package;
- the tests;
- the console assets and page;
- the three briefs;
- their site-graph registration.

Nothing else depends on them.
