# ClearGlass Operations Platform — Repository Discovery

## Verified findings
- Repository: `ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond`
- Default branch: `main`
- Discovery baseline: `7478b15714e23529f349ab77c3ec4c1b912be6d8`
- Application stack: Next.js 15 App Router, React 19, TypeScript, Zod.
- Existing server-side security primitives exist in `lib/security.ts`, including tenant-aware `Principal`, classification checks, origin validation, and log redaction.
- Existing request identity resolution in `lib/request.ts` is intentionally inert: it returns an anonymous principal and documents that a deployment identity proxy must replace it.
- Existing rate limiting exists in `lib/rate-limit.ts`.
- Existing motion/design primitives live under `components/motion`.
- Existing automated tests use Node's test runner for TypeScript and pytest for Python.
- CI already contains broad Python, TypeScript/application, security, site-audit, and workflow validation.
- No Prisma, Drizzle, Supabase, SQLite, Postgres client, or database migration directory was detected during repository discovery.
- No existing generic object-storage adapter was identified.
- Existing Truth Forensics / ARTEMIS surfaces already use evidence integrity, provenance, and human-gating language, so this extension should reuse those concepts without claiming legal admissibility or law-enforcement equivalence.

## Existing integration boundaries
The safest initial extension point is a new App Router surface:
- UI: `/operations`
- API: `/api/operations`
- Domain library: `lib/operations/*`
- Tests: `tests/operations.test.ts`

This avoids changing existing public HTML pages, navigation, workflows, or deployed static assets.

## Current persistence posture
There is no verified durable application database or evidence object store in the existing stack. Therefore the first vertical slice uses an explicit in-memory mock repository for development/test only. Production live mode remains blocked until an approved persistence adapter and authenticated request identity boundary are configured.

## Current identity posture
The current `principalFromRequest` implementation cannot establish a trusted authenticated identity. The new operations API therefore:
1. Allows a synthetic principal only when the operations service is explicitly in mock mode.
2. Never treats arbitrary client headers as authentication.
3. Returns blocked/unauthorized behavior for live mode until the existing identity proxy is wired.

## Non-goals for this phase
- No police/CAD/RMS integration.
- No government or restricted databases.
- No device unlocking, passcode bypass, credential theft, or unauthorized acquisition.
- No public-camera biometric identification.
- No real LPR source connections.
- No live telephony/SMS/AI vendor activation.
- No production evidence persistence claims.
