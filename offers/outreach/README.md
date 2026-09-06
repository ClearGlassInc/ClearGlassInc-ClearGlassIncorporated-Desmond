# ClearGlass — Outreach Playbook (CASL-compliant)

Lawful, consent-respecting B2B outreach for the four fixed-scope offerings.
**Burlington, Ontario.** Read this before sending anything.

## Hard rules (non-negotiable)
1. **Permitted sources only.** Build the lead list from *public, conspicuously published*
   business information (company website "Contact" page, public business directories,
   association member lists, public LinkedIn company pages). **No scraping of private or
   gated data. No purchased lists. No personal/private addresses.**
2. **CASL on every message.** Each email must include:
   - Clear sender identity: **ClearGlass Inc.**, Burlington, Ontario
   - A valid physical mailing address
   - A working unsubscribe / opt-out that is honoured within 10 business days
   - A message relevant to the recipient's business role
3. **Consent basis recorded** per lead (see lead-list `Consent_basis` column). For cold
   B2B, rely on CASL's published-business-email provision **only** when: the address is
   conspicuously published, there's no "no unsolicited email" statement, and the message
   relates to their role. Otherwise seek express consent first.
4. **No over-promising.** Reference only the written deliverables (findings report /
   remediation report / readiness roadmap). No outcome guarantees.
5. **Volume & rate discipline.** Personalize each message. No bulk blasting. Respect any
   opt-out immediately and permanently.
6. **Written authorization** is required before any hands-on security work — say so.

## Workflow
1. Populate `lead-list-template.csv` from permitted public sources (10 to start).
2. For each lead, record the `Public_source_URL` and `Consent_basis`.
3. Pick the best-fit offering and the matching template in `email-templates.md`.
4. Personalize the **first line** with a specific, *public* observation (e.g., "your site
   lists patient intake forms" → PHIPA relevance). Never reference non-public data.
5. Send from a ClearGlass domain address. Log `Status` and `Next_action`.
6. Follow up at most twice, spaced out, then stop unless they engage.

## Suggested target segments (Ontario SMB)
- Accounting / bookkeeping firms (M365 heavy) → Quick-Audit / Hardening Sprint
- Law firms & paralegals → Hardening Sprint
- Physiotherapy / dental / clinics (health sector) → **PHIPA Readiness** (flag for human)
- Property management & real estate brokerages → Hardening Sprint / Automation
- Non-profits & associations → Quick-Audit
- Small MSPs / IT shops needing overflow → Automation-as-a-Service

## What I will NOT do
- Invent real company names, contacts, or emails.
- Imply endorsement or fabricate references.
- Send anything that can't satisfy the CASL checklist above.
