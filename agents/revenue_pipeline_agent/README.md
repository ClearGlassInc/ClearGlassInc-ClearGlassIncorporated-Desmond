# ClearGlass Revenue Pipeline Agent

Purpose: convert commercial intent into measurable pipeline execution without confusing research, drafts, or software activity with revenue.

## Operating states

`RESEARCHED -> CONTACTED -> RESPONDED -> MEETING -> PROPOSAL -> CUSTOMER -> REVENUE -> MRR`

Only evidence-backed transitions are accepted.

## Guardrails

- Never invent contacts, consent, vulnerabilities, meetings, proposals, customers, payments, revenue, MRR, testimonials, or delivery outcomes.
- Publicly published business contact details may be considered for outreach only after a human/operator confirms the message is relevant and the applicable Canadian CASL basis is documented.
- Never send bulk unsolicited commercial messages.
- Never follow up after an unsubscribe request.
- A sent message is `CONTACTED`; delivery/read/response are separate states.
- A `CUSTOMER` requires verified payment or a signed engagement.
- `REVENUE` requires verified payment evidence.
- `MRR` requires an active recurring commercial agreement/payment evidence.
- Default mode is dry-run for automation. External sending requires an explicit allowlist and `OUTREACH_SEND_ENABLED=true` in a separately secured runtime; this repository does not contain credentials.

## Current verified first-wave execution

As of 2026-09-13, two public business channels were contacted from the connected Outlook mailbox:

- URtech Manufacturing — `sales@urtechmfg.com`
- PV Labs — `info@pv-labs.com`

The agent records these as `CONTACTED`, not as meetings, customers, or revenue.

## Local invocation

```text
python agents/revenue_pipeline_agent/agent.py --report
python agents/revenue_pipeline_agent/agent.py --validate
```

The agent is intentionally conservative: missing evidence produces `NOT VERIFIED` instead of a guessed value.
