# Root application CI diagnostics implementation plan

> **For agentic workers:** Use superpowers:executing-plans for inline execution of the user's authorized debugging task.

**Goal:** Repair the two reproduced root application type-check failures without changing runtime behavior or deployment controls.

**Architecture:** The root Next.js 15 application and Delos Next.js 16 application retain their separate manifests and compiler projects. Correct the root API's invalid type predicate and restore that existing package boundary.

**Tech stack:** TypeScript 5.7.2, Next.js 15.5.25, npm; Node.js 20 as configured in Chualar CI.

**Spec:** User's repository diagnostic and minimal-patch request, 2026-10-26; repository AGENTS.md and CLAUDE.md.

## Constraints and review focus

- Scope A: correct validation directly related to this task; no dependency, deployment, permissions, secrets, or production changes.
- Preserve the API's provider error filtering, response shape, count semantics, and headers.
- Keep the Chualar API in root validation and the Delos page in its own project and existing CI workflow.
- Keep tests, security checks, and assertions enabled.
- Record the billing-lock annotation, missing runner logs, unrelated baseline failures, and actual verification results.

## Tasks

1. Add compiler-based regression tests in `tests/typecheck-boundaries.test.ts`.
   - [x] Confirm both tests fail on the baseline for the reproduced reasons.
2. Correct `app/api/live/ops/route.ts`'s invalid filter type predicate without changing its Boolean filter.
   - [x] Re-run the API compiler regression.
3. Correct root `tsconfig.json`'s standalone project boundary, matching its existing independent-app exclusions.
   - [x] Re-run both regressions and `npm run typecheck`.
4. Verify the complete root Node suite and production build on Node.js 20; run workflow and focused Python checks.
   - [x] Inspect the final diff and document other failing gates separately.
   - [x] Prepare only the focused patch, tests and required evidence documents for a dedicated fix branch and reviewable draft PR; publication state is recorded in GitHub.

## Rollback

Revert the patch commit through a new pull request. No migration or configuration outside the repository is involved. This restores the two known compile failures and does not resolve the independent account billing lock.

## Execution evidence

- Both regressions failed before the patch and passed after it.
- Node 20.20.2: typecheck, all 42 Node tests and production build passed.
- Independent read-only review found no Critical, Important or Minor findings; reviewer reran both regressions and a nonincremental typecheck successfully.
- Ruling: preserve the Delos package boundary rather than installing its unrelated dependencies into the root package; regression tests retain both projects in their own validation. If this ownership model changes, both compiler configurations and CI must change together.
- Hosted execution, account restoration, independent Delos build, live providers and production behavior remain unverified. No merge or release is authorized by these local results.
