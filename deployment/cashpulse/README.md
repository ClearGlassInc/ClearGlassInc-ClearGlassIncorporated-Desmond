# CashPulse Deployment

n8n workflow exports and runbook for deploying CashPulse to a new client in
under 7 days. Pair with the design spec at
`docs/cashpulse_revenue_recovery_bot_spec.md` and the logic core at
`bots/cashpulse_revenue_bot.py`.

## Files
- `workflow_invoice_dunning.json` — Workflow B (highest $ recovery)
- `workflow_lead_capture.json` — Workflow A (speed-to-lead)
- `audit_log.sql` — Supabase append-only audit table
- `env.example` — required credentials and IDs

## Deploy order (Day 1–2)
1. Provision a self-hosted n8n instance (Docker) or Make.com workspace.
2. Provision Supabase project; run `audit_log.sql` to create `bot_actions`.
3. Create credentials in n8n:
   - Gmail OAuth2 (or Outlook Graph)
   - Stripe API key (read invoices, write payment links)
   - QuickBooks Online OAuth2 (or Xero)
   - Twilio (SID + token + from-number)
   - Slack (incoming webhook + interactive buttons app)
   - Anthropic API key (Claude Haiku 4.5 for drafting, Sonnet 4.6 for triage)
4. Import each workflow JSON. Map credentials and replace placeholder IDs
   listed in `env.example`.
5. Run each workflow in **dry-run mode** (set `DRY_RUN=true`) for 72 hours.
   Drafted outbound goes to a Slack channel for owner review only.
6. Flip to live after owner signs off on 10+ drafted messages.

## Risk controls baked into every workflow
- Stop-on-reply: webhook listens to inbound mail/SMS; sets `stop=true` on the lead/invoice.
- Idempotency keys on all webhook handlers.
- Rate limit: max 3 outbound emails per recipient per 7 days (per-workflow guardrail).
- Unsubscribe honored across email + SMS in a single suppression list.
- Every action writes a row to `bot_actions` with payload SHA-256 hash.

## Approvals
Approvals are routed via Slack interactive buttons. Approval payload is signed
and verified before the workflow proceeds. Approvers and timestamps are written
to `bot_actions.approved_by`.
