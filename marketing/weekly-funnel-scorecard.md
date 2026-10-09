# Weekly Growth Scorecard — ClearGlass Inc.

**Owner:** ClearGlass leadership  
**Review cadence:** Every Monday; compare the latest complete 7-day period with the prior 7-day period and a rolling 4-week baseline.  
**Status:** Template only. Analytics, Search Console, CRM, finance and attribution data have not yet been connected or independently verified in this work.

## 1. Weekly scorecard

Use `Unknown` when the source is unavailable, the event is not instrumented, or the definition cannot be reconciled. Do not convert missing tracking into zero.

| Metric | Definition | Current week | Previous week | 4-week trend | Source / verification |
|---|---|---:|---:|---|---|
| Qualified site sessions | Sessions from a relevant audience or intent; document the rule used | Unknown | Unknown | Unknown | Analytics |
| Quick-Audit page visits | Page views of `/offers/security-quick-audit.html` | Unknown | Unknown | Unknown | Analytics / web logs |
| Primary CTA clicks | Clicks to Quick-Audit page from homepage | Unknown | Unknown | Unknown | Analytics event |
| Quick-Audit checkout starts | Click-throughs to Stripe checkout; not a completed payment | Unknown | Unknown | Unknown | Analytics + Stripe event reconciliation |
| Scope-check submissions | Valid, consented scope requests received | Unknown | Unknown | Unknown | Corporate inbox / form provider |
| Qualified leads | Meets documented segment/problem/authority/next-step criteria | Unknown | Unknown | Unknown | CRM or lead register |
| Meetings booked / held | Unique meetings, with cancellations separated | Unknown | Unknown | Unknown | Calendar |
| Proposals sent | Formal scoped proposal shared with buyer | Unknown | Unknown | Unknown | Proposal register |
| Signed engagements | Executed agreement; record value separately | Unknown | Unknown | Unknown | Contract register |
| Cash collected | Settled money received, net of refunds where applicable | Unknown | Unknown | Unknown | Stripe / bank reconciliation |
| Active recurring revenue | Active, contracted monthly recurring charges under a consistent policy | Unknown | Unknown | Unknown | Billing + contract register |
| Delivery hours / direct cost | Time and directly attributable delivery costs for fulfilled work | Unknown | Unknown | Unknown | Time/cost records |
| Gross margin | (Collected revenue allocated to delivery − direct delivery cost) ÷ that revenue | Unknown | Unknown | Unknown | Reconciled finance records |

## 2. Weekly narrative

- **What changed:** [Describe the largest verified movement, not an assumption.]
- **Best-performing source or page:** [Only with adequate sample and reliable attribution.]
- **Primary funnel leak:** [Identify one stage with measured evidence.]
- **Customer language heard:** [Record anonymized wording; do not put personal data here.]
- **Experiment:** [One variable, one hypothesis, a named owner, and a review date.]
- **Decision:** [Keep, change, or stop based on the evidence.]
- **Data-quality gaps:** [Missing sources, tracking defects, duplicate leads, attribution uncertainty.]

## 3. Funnel definitions

1. **Visitor:** a valid session/page visit after filtering obvious bots where the analytics platform supports it.
2. **Inquiry:** a person explicitly asks for a response through a form, email, or booking step.
3. **Qualified lead:** documented fit with the target segment, a plausible problem, a person able to sponsor the next step, and a realistic timeline or action.
4. **Meeting held:** a real conversation occurred; a booking alone is not a held meeting.
5. **Opportunity:** buyer, problem, scope, budget path and next step are recorded.
6. **Proposal:** a specific scope, price, acceptance path and expiration/review date were shared.
7. **Won engagement:** agreement accepted under the company's contracting policy.
8. **Cash collected:** funds settled and reconciled. Pipeline, quoted value, bookings and signed value are not cash.
9. **MRR:** active recurring contract value normalized monthly; exclude one-time services and unsigned proposals.
10. **CAC:** do not calculate until both attributable acquisition cost and acquired-customer count are available for the same defined cohort and period.

## 4. Minimal attribution convention

Use consistent UTMs for authorized campaign links; never put names, email addresses, client identifiers, or sensitive issue descriptions in query strings.

- `utm_source`: `linkedin`, `referral`, `organic`, or another truthful source label.
- `utm_medium`: `social`, `referral`, `organic`, `email`.
- `utm_campaign`: `security_quick_audit_2026q4` or a similarly stable campaign identifier.
- `utm_content`: a specific approved post/creative variant.

Suggested event names (not yet implemented or verified): `primary_cta_click`, `quick_audit_page_view`, `checkout_outbound_click`, `scope_request_submit`, `meeting_booked`. Capture event metadata only when appropriate consent and platform configuration are confirmed. Never send form field values or sensitive content to analytics.

## 5. Governance

- Every number needs a reporting period, definition, source and reconciliation status.
- Keep an audit trail for manual adjustments.
- Separate leading indicators (clicks, inquiries, meetings) from commercial outcomes (signed work, cash, margin, retention).
- Do not present sample data as actual results.
- Review consent, retention, access and anti-spam requirements before adding tracking or outreach.
- No paid advertising, billing changes, third-party account connections, or outbound messages are authorized by this template.
