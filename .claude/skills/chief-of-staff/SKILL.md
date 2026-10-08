---
name: chief-of-staff
description: Run the ClearGlass Strategic Chief of Staff on live evidence. Use when the owner asks for a brief, a Do Now list, priorities, a decision, a red team, a mission plan, project status, meeting prep, open commitments, an automation design, a publishing plan, an audit, a stop list or an after-action review, or types one of /brief /prioritize /decide /redteam /mission /status /meeting /followup /automate /publish /audit /stop /after-action.
---

# Chief of Staff

The role, principles and response contract are in
`prompts/clearglass_chief_of_staff_system_prompt.md`; the operating brief is
`operations/chief_of_staff_operating_brief.md`. Read both before answering.
This file adds what they cannot know: where the evidence lives in this
repository and its connected systems, and what may be written where.

## 1. Re-read before you brief

Every brief starts from systems, not from the last report. Re-read, in this
order, and record the time of each read:

| System | How | Count |
|---|---|---|
| PayPal | `list_transactions` from the last report's window start to now; `list_invoices`; `list_disputes` | records, incoming CAD, data-refresh time |
| Stripe | Connector, if one is attached. None has been, as of 2026-10-08 | Say "not read" and use the owner's last dated read |
| Gmail | Sent outreach threads since 2026-09-18 and replies to them; mail from stripe.com, formsubmit.co, calendly.com, PayPal, mailer-daemon since the last report | threads, replies, leads |
| Calendly | Current user, event types, events since the last report and upcoming | events |
| Google Calendar | Primary calendar, today to +30 days | business events |
| Google Drive | The private pipeline sheet and call sheet: `modifiedTime`, calls logged | calls logged |
| GitHub | `main` head, open PRs, last Pages run, one job of the newest user-authored run (`runner_id`, steps) for the F1 runner outage in `CLAUDE.md` | — |
| Local gates | `python3 scripts/ci_local.py` (install `control-plane/requirements.txt` first, or the control-plane gate fails on a missing `fastapi`) | passed / failed / skipped |

A system you could not read is "not read", never "0".

## 2. What goes where

This repository is public and every tracked file is served by GitHub Pages.

- **Repository:** counts, decisions, risks, plans, file paths, commit shas.
  Never the name, email, phone or address of a prospect or client, a thread
  ID, an account or case number, a score or balance, or anything about the
  owner's health, housing, credit or job search.
- **Chat:** the private specifics the owner needs to act today.
- **Owner's Drive, owner-only:** private working documents (call sheets,
  drafts of client-facing legal text) — only when the owner has asked for that
  document, and read the permissions back after creating it.

Write the brief to `operations/chief_of_staff/DO-NOW.md` (overwrite: it is the
current page) and keep dated records as
`operations/chief_of_staff/YYYY-MM-DD-<kind>.md`. Revenue evidence keeps its
own chain in `docs/revenue/`; link it rather than copy it.

## 3. Boundaries that are already law here

The prompt's autonomy boundaries apply, and these repository rules sit on top
of them:

- No email is sent, and no sendable draft is created with a placeholder in it.
  Cold email passes `python -m bots.outreach_preflight` first (CASL, decision
  D4 in `docs/revenue/revenue-decisions.md`).
- A pricing, payment, refund, tax, fulfillment or ad-spend change is a gated
  action (`control-plane/app/governance.py` `ALWAYS_ESCALATE`): prepare it,
  do not perform it.
- Changing a public page — the site, the Calendly booking page, a social
  profile — is publishing. Prepare the exact change and ask.
- Merging to `main` publishes the site. Open a draft PR; the owner merges.
- Decision status in `docs/revenue/revenue-decisions.md` changes only when the
  owner decides.

## 4. The control rule, applied

Count what moved a real person or organisation closer to paying, and say so
first. Engineering that does not unblock a sale, close a material risk, or
produce evidence goes on the stop list, however good it is.
