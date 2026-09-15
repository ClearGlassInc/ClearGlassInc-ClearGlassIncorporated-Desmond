# ClearGlass 24-Hour Website & GitHub Deployment Rescue Sales Kit

> A truthful, fixed-scope sales and delivery system for diagnosing and repairing website and deployment blockers. No outcome guarantees. Written scope and authorized access required before repair work.

## 1. Landing Page

### Website or GitHub deployment broken?
Get a clear diagnosis, a safe repair plan, and one focused fix—often within 24 hours of scope approval.

ClearGlass fixes high-friction launch blockers for founders, creators, and small businesses:

- Broken GitHub Pages deployments and Actions workflow failures
- Mobile layout and responsive CSS bugs
- Broken navigation, 404s, and dead checkout links
- Contact forms, webhook errors, and email-delivery failures
- Performance bottlenecks blocking launch
- Safe rollback of failed updates

### How It Works

1. **Rapid Audit — $125 upfront.** Submit a public URL or repository. Receive a written root-cause diagnosis, effort/risk assessment, and exact fix specification. If rescue repair is approved within 48 hours, 100% of the audit fee is credited toward the repair balance.
2. **Safe Repair — from $400.** A 50% deposit is required before repair work. ClearGlass establishes a rollback point, works within the approved scope, and isolates the change.
3. **Verified Live Delivery.** Validate the affected workflow on desktop/mobile, verify live functionality, deliver evidence and rollback instructions, and provide 7 calendar days of support for the repaired defect.

### What the Client Receives

- Root-cause assessment with affected files/configurations and impact
- Fixed-scope repair plan
- Backup branch, tag, or deployment restore point
- Post-deploy validation
- Delivery report with changelog, evidence, and rollback instructions
- 7-day warranty for the exact repaired defect

### Pricing

| Tier | Price | Payment | Typical Scope |
|---|---:|---|---|
| Rapid Audit | $125 | 100% upfront; credited toward rescue if booked within 48h | Root-cause diagnosis and repair specification |
| Tier 1: Config & Link Rescue | $400 | $200 deposit / $200 on delivery | Single layout, domain/CNAME, checkout-link, or simple static-form defect |
| Tier 2: Build & Workflow Rescue | $650 | $325 deposit / $325 on delivery | GitHub Actions, Pages/Vercel/Netlify pipeline, dependency or asset-build failure |
| Tier 3: Complex Multi-Component Rescue | $950 | $475 deposit / $475 on delivery | Multiple linked issues, responsive restoration, webhook/API form triage |

Bespoke systems, legacy repositories, and extensive database interventions require a separate written quote before work starts.

### Exclusions and Non-Guarantees

ClearGlass does not guarantee SEO rankings, conversion lifts, traffic, sales, advertising approvals, or other business outcomes. Excluded unless separately scoped: full redesigns, database migrations, payment-account/KYC approval, formal security certifications, and unrelated refactoring.

Delivery windows begin only after authorized access, written scope approval, and the required payment are confirmed.

### CTA

Send a public URL or repository and one sentence describing the observable problem.

- Intake / booking: `{{EMAIL_OR_BOOKING_LINK}}`
- Audit payment: `{{STRIPE_OR_PAYPAL_LINK}}`
- Terms / privacy: `{{POLICY_URL}}`

---

## 2. Client Intake

Mandatory fields:

- Full Name
- Business / Project Name
- Email Address
- Public Website URL
- Public GitHub Repository URL or deployment-provider link
- Specific Issue: observed behavior versus expected behavior
- Timeline of Issue: when it last worked normally
- Preceding Changes: commit, merge, configuration, dependency, or deployment change immediately before failure
- Critical Launch Deadline
- Authorization: client confirms they are authorized to approve technical work
- Rollback Availability: Git backup, hosting snapshot, or unsure
- Scope Awareness: client confirms this is an isolated repair, not a redesign or open-ended development engagement

### Intake Validation Rules

- Reject submissions without an actionable public URL/repository or sufficient issue description.
- Do not request passwords, private keys, recovery codes, or account-owner credentials.
- Treat third-party access as least-privilege and time-bounded where supported.
- Do not begin paid repair work until authorization, SOW, deposit, and access prerequisites are satisfied.

---

## 3. Scope of Work Template

```text
# ClearGlass Rescue Scope of Work (SOW)

Client: [Client Name]
Business/Project: [Business Name]
Website: [URL]
Repository: [Repo URL]
Primary Contact: [Email]

## 1. Problem Statement
Observed behavior: [current behavior]
Expected behavior: [expected behavior]
Affected scope: [pages/viewports/workflows]
Issue began: [date]

## 2. Agreed Deliverable
[Exact 1–2 sentence description of the single focused fix.]

## 3. Completion Criteria
[ ] Backup branch/tag/restore point created
[ ] Root cause documented
[ ] Only approved files/configurations changed
[ ] Build/deployment succeeds in the agreed environment
[ ] Desktop 1440px validation completed
[ ] Mobile 375px validation completed
[ ] Affected link/form/webhook/workflow verified
[ ] Delivery report and rollback instructions delivered

## 4. Exclusions
Anything not explicitly named above is excluded, including redesigns, unrelated bugs,
net-new features, third-party outages, payment-account verification, and unrelated refactoring.

## 5. Pricing
Service tier: [Audit / Tier 1 / Tier 2 / Tier 3]
SOW value: $_____
Audit credit: -$_____
Deposit: $_____
Final balance: $_____
Payment link: [verified payment link]

## 6. Delivery Window
Target: 24 hours from the point at which written approval, required payment, and authorized
working access are all confirmed.

## 7. Rollback
Backup branch/tag: clearglass-backup-[date]
Rollback method: [git revert / provider rollback / restore snapshot]

## 8. Warranty
7 calendar days for the exact defect repaired under this SOW.

Client approval: __________________
Date: __________________
```

---

## 4. Delivery Report Template

```text
# ClearGlass Delivery Report

Client: [Client]
Project: [Project]
Completed: [YYYY-MM-DD HH:MM UTC]
SOW ID: [SOW-####]
Target URL: [Production URL]

## 1. Reported Issue
[One-sentence recap.]

## 2. Root Cause
Root cause: [plain-language explanation]
Diagnostic proof: [log line, failed action, configuration conflict, or reproducible evidence]

## 3. Work Completed
Safety snapshot: clearglass-pre-fix-[date]
Files/configurations changed: [list]
Deployment status: [verified status]
Commit/PR: [reference]

## 4. Validation Evidence
[ ] Build has no fatal errors
[ ] Mobile validation completed
[ ] Desktop validation completed
[ ] Affected links/forms/webhooks/workflows verified
Evidence artifacts: [links]

## 5. Rollback
Restore backup branch/tag or use the documented provider rollback procedure.
Rollback reference: [commit/tag/snapshot]

## 6. Closeout
SOW fee: $_____
Deposit paid: $_____
Balance due: $_____
Warranty expiration: [date]

ClearGlass sign-off: [verified / not verified]
```

**Important:** never mark a validation item complete without evidence. If evidence is unavailable, report **Not Verified**.

---

## 5. Lead Sheet

| Lead | Business / Project | Public URL | Public Contact Path | Observable Need | Personalization Context | Status |
|---|---|---|---|---|---|---|
| `{{NAME}}` | `{{PROJECT}}` | `{{URL}}` | `{{EMAIL_OR_CONTACT_FORM}}` | `{{VERIFIED_ISSUE}}` | `{{CONTEXT}}` | Draft |
| Alex Rivera | DevFlow Tools | devflowtools.io | founders@devflowtools.io | GitHub Pages 404 on docs subdomain | Product Hunt launch context | Ready to Send |
| Sarah Chen | Chen Ceramics | chenceramics.com | Instagram DM / contact form | Mobile navigation drawer issue on iOS Safari | Summer collection launch context | Ready to Send |

Only use publicly observable, verifiable issues and lawful contact paths. Do not fabricate defects, contacts, or personalization.

---

## 6. Outreach Drafts

### A — Warm Contact

**Subject:** Quick diagnostic for your site launch blocker

Hi `{{FIRST_NAME}}`,

I noticed `{{SPECIFIC_VERIFIABLE_ISSUE}}` on `{{URL}}` while you were preparing for launch.

I run ClearGlass 24-Hour Deployment Rescue. We diagnose and repair isolated website and deployment blockers such as failed GitHub workflows, responsive layout failures, form failures, and deployment configuration issues.

We start with a $125 Rapid Audit. If you approve the repair within 48 hours, the full audit fee is credited toward the repair balance, which starts at $400.

If useful, send over the repository or URL and a short description of what you're seeing.

Best regards,
`[Your Name]`
ClearGlass Technical Rescue
`{{EMAIL_OR_BOOKING_LINK}}`

### B — Cold, Verifiable Problem

**Subject:** ClearGlass deployment rescue for `{{BUSINESS_OR_PROJECT}}`

Hi `{{FIRST_NAME}}`,

I found `{{BUSINESS_OR_PROJECT}}` through `{{SOURCE_WHERE_FOUND}}` and observed `{{SPECIFIC_VERIFIABLE_CONTEXT}}`.

ClearGlass diagnoses and repairs focused website and deployment blockers within 24 hours of approved scope. Repairs include a rollback point, desktop/mobile validation, and a delivery report.

If the issue is blocking launch, reply with the public link and one sentence describing the problem, or use `{{EMAIL_OR_BOOKING_LINK}}`.

Best,
`[Your Name]`
ClearGlass Rescue
`{{POLICY_URL}}`

### C — Community Post

Taking on 3 ClearGlass 24-Hour Deployment Rescue slots this week for founders facing launch blockers.

Common problems:
- GitHub Actions / GitHub Pages build failures
- Mobile CSS breakage
- Broken contact forms or checkout buttons
- Production assets failing to load

Rapid Audit: $125. Rescue repairs: from $400. The audit fee is credited toward a repair approved within 48 hours.

Send a public link and one sentence describing what is broken.

### D — Founder DM

Website deployment broken before launch? ClearGlass diagnoses and repairs failed GitHub builds, mobile layout bugs, and broken forms within 24 hours of approved scope. Starts with a $125 audit, credited toward repair. Send the link and what's broken.

---

## 7. Objection Handling

### Why pay for an audit?
The audit separates diagnosis from repair, establishes the root cause, and produces a defined repair boundary. The $125 fee is credited toward an approved rescue within 48 hours.

### Can't I use an AI coding assistant?
AI can assist diagnosis and implementation, but a production rescue still requires environment-specific inspection, controlled access, validation, rollback planning, and evidence of the live result.

### Why repository or hosting access?
Authorized technical access is required for relevant diagnostics and deployment work. Use least-privilege collaborator permissions where possible. Never request passwords or account-owner credentials.

### What if the fix breaks something else?
Create and verify a pre-fix rollback point before modifying production-relevant code. Keep changes within the approved scope and document the exact restoration procedure.

### Can you guarantee a conversion increase?
No. Technical repair can address a verified defect; traffic, conversion, SEO, sales, and third-party approvals depend on factors outside the repair scope.

---

## 8. Follow-Up Sequences

### Sequence 1 — Intake Submitted, Audit Not Paid
**Timing:** 12–16 hours after intake.

**Subject:** Next steps to diagnose `{{PROJECT}}`

Thanks for submitting the details on `{{PROJECT}}`. To begin the formal diagnostic review, complete the $125 Rapid Audit payment at `{{STRIPE_PAYMENT_LINK}}` and provide the authorized repository/hosting access required by the intake. The diagnostic report and fixed-price repair plan follow within the agreed 24-hour window after prerequisites are confirmed.

### Sequence 2 — Audit Delivered
**Timing:** 24 hours after audit delivery.

**Subject:** Repair plan for `{{PROJECT}}` — $125 credit active

Following the Rapid Audit, the documented root cause is `{{BRIEF_ROOT_CAUSE}}`. Proposed repair value: $`{{REPAIR_TOTAL}}`. Audit credit: $125. Net: $`{{NET_TOTAL}}`. Deposit: $`{{DEPOSIT_AMOUNT}}`.

If you want ClearGlass to proceed, approve the SOW at `{{SOW_APPROVAL_LINK}}` and complete the required deposit.

### Sequence 3 — Repair Closeout
**Timing:** Day 7 after delivery.

**Subject:** 7-day warranty wrap-up for `{{PROJECT}}`

The 7-day support period for the repaired defect is complete. If ongoing monitoring is useful, ClearGlass offers a $149/month maintenance plan covering synthetic uptime/form checks, monthly dependency health checks, one Tier-1-equivalent emergency repair credit per quarter, and a monthly status report. Activate at `{{MAINTENANCE_CHECKOUT_LINK}}`.

---

## 9. Maintenance & Monitoring Add-On

**Price:** $149/month or $1,490/year.

### Deliverables

- Synthetic uptime and form checks at a defined interval (target: every 5 minutes where the monitoring platform supports it)
- Monthly dependency and security health check on an isolated update path
- One Tier-1-equivalent emergency repair incident per quarter with priority initial response target of 4 hours
- Monthly one-page status report

### Exclusions

No net-new page design, feature development, or custom marketing integrations unless separately scoped.

### SLA and Truthfulness Controls

- Monitoring frequency is a target, not a guarantee of provider execution under outage conditions.
- Response targets are service targets, not guarantees of resolution time.
- Warranty covers only the exact defect fixed under the associated SOW.
- All commercial claims must be supported by actual service capability and payment configuration.

---

## 10. Revenue / CRM Data Model

Use these fields for the ClearGlass revenue pipeline:

```json
{
  "lead_id": "CG-LEAD-####",
  "status": "new|qualified|audit_paid|audit_delivered|repair_proposed|deposit_paid|in_delivery|completed|warranty|maintenance|closed",
  "source": "public_web|referral|community|inbound|other",
  "contact_path_verified": true,
  "observable_issue_verified": true,
  "authorization_confirmed": false,
  "sow_approved": false,
  "deposit_confirmed": false,
  "audit_fee_cad": 125,
  "repair_value_cad": 0,
  "revenue_collected_cad": 0,
  "mrr_cad": 0,
  "evidence_refs": [],
  "next_action": "",
  "owner_approval_required": true
}
```

Pipeline metrics:

- Leads
- Qualified leads
- Contacted
- Conversations
- Audits paid
- Audits delivered
- Proposals / SOWs
- Deposits collected
- Customers
- Revenue CAD
- MRR CAD
- Gross margin
- Warranty incidents
- Maintenance conversions
- Retention

No pipeline metric should be incremented without an auditable event or payment/CRM evidence.

---

## 11. Execution Guardrails

1. **Inspect → baseline → diagnose → scope → approve → snapshot → patch → test → deploy → validate → report.**
2. Preserve existing working pages, animations, integrations, and deployment behavior unless the approved defect requires a change.
3. Never claim completion from a code change alone; verify the live result.
4. Never expose secrets, credentials, client data, or private repository contents in sales materials or evidence artifacts.
5. Never fabricate a lead, defect, customer, payment, testimonial, contact, or result.
6. Use explicit client authorization for repository, hosting, domain, and deployment actions.
7. Keep changes atomic and rollback-capable.
8. Production changes require the repository's existing protection/approval gates where applicable.
9. If a check cannot be performed, mark it **Not Verified** rather than assuming success.
10. Separate technical resolution from business-outcome claims.

## 12. Operational Definition of Done

A rescue is commercially and technically closed only when:

- Approved SOW exists.
- Required payment is confirmed.
- Authorized access was used within scope.
- Pre-fix rollback point exists.
- Root cause is documented.
- Approved defect is repaired.
- Build/deployment validation is evidenced.
- Affected user path is tested.
- Delivery report is issued.
- Final balance status is recorded.
- Warranty start/end dates are recorded.
- Pipeline metrics reflect actual evidence.

**ClearGlass principle:** Evidence before assertion. Provenance before convenience. Human accountability by design.
