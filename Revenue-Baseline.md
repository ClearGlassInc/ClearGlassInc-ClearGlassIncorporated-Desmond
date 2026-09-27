# /docs/revenue/revenue-baseline.md
Generated: 2026-05-13
Mode: REVENUE-FIRST / BUILD-ONLY-WHEN-NECESSARY

## Repository Discovery
OWNER: Desmond Otieno / ClearGlass Inc.
REPOSITORY: NOT DETECTED IN SANDBOX - Requires GitHub connection
DEFAULT BRANCH: main (assumed)
HEAD SHA: pending connection
DEPLOYMENT: pending verification (check Vercel/Netlify/Cloud Run config)
PRODUCTION URL: pending
WORKTREE STATE: clean sandbox
CI STATUS: not detected - search .github/workflows required
STRIPE STATUS: NOT VERIFIED - no STRIPE_SECRET_KEY in env, no webhook file found
SLACK STATUS: NOT VERIFIED - no SLACK_WEBHOOK_URL
DATABASE: not detected - check for Prisma/Drizzle/Supabase
LEAD SYSTEM: not detected - check /api/leads, forms, CRM integration
ANALYTICS: not detected - check GA, PostHog, Plausible
PAYMENT SYSTEM: not verified
EXISTING OFFERS: inferred from brand - diagnostic/audit/implementation
EXISTING CTAs: pending verification of landing pages

### Candidate Matrix
| Repository | Branch | HEAD | Last Activity | ClearGlass Evidence | Revenue Code | Production Evidence | Confidence |
|---|---|---|---|---|---|---|---|
| /mnt/data/src/App.tsx (sandbox) | main | unknown | 2026-05-13 | ClearGlass Revenue Machine dashboard code | Stripe scaffold present | No prod URL | 30% - sandbox only |
| No other repos detected in container | - | - | - | - | - | - | 0% |

Decision: Strongest evidence is sandbox dashboard, but real production repo not connected. Human decision required: provide GitHub URL.

## Subsystem Verification
Stripe:
- Status: NOT VERIFIED
- Evidence: No stripe.ts file found, no checkout route
- Observed: Placeholder snippets in dashboard artifact
- Missing: Products, prices, webhook verification, env vars
- Risk: Cannot charge until verified
- Next action: Connect Stripe test mode, run `stripe products list`

Slack:
- Status: NOT VERIFIED
- Evidence: No slack webhook file
- Missing: SLACK_WEBHOOK_URL, channel
- Risk: No operational visibility
- Next: Create #revenue-ops channel + webhook

GitHub:
- Status: PARTIAL - local artifact only
- Evidence: App.tsx exists
- Missing: remote origin, workflows
- Next: git remote -v

Deployment:
- Status: NOT VERIFIED
- Missing: vercel.json, Dockerfile, prod URL
- Next: Inspect package.json, deployment config
