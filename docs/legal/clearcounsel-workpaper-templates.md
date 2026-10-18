# ClearCounsel Canada — Workpaper and Approval Templates

**Use:** Reusable templates for a controlled legal-operations workflow.  
**Important:** This repository is public. Keep all templates generic here. Never place matter-specific privileged, confidential, personal, customer, incident-response, or security-sensitive records in this repository, a public Slack channel, or public issue comments. Use an approved restricted system for actual legal workpapers.

## 1. Matter intake record

| Field | Entry |
|---|---|
| Matter ID | `CC-YYYY-NNN` |
| Working title | |
| Verified client entity / registry source | |
| Authorized instruction owner | |
| Conflict/personal-interest flag | |
| Relevant jurisdictions / forum | |
| Purpose and intended decision | |
| Urgent trigger / source / date observed | |
| Counsel / retainer scope verified? | |
| Data sensitivity and approved storage location | |
| Current status | `PRELIMINARY` / `URGENT ESCALATION` / `COUNSEL REQUIRED` / `CLOSED WITH EVIDENCE` |
| Next action / accountable owner / internal target date | |

## 2. Risk register

| Risk ID | Issue / affected entity | Evidence IDs | Assumptions / gaps | Jurisdiction | Likelihood + rationale | Impact + rationale | Urgency source | Existing controls | Remediation / owner | Dependency / effort | Counsel review | Residual risk | Status / next review / closure evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CC-R-001 | Example only — replace after intake | E-001 | Example assumption; verify | To verify | Qualitative only | Qualitative only | None known | To inventory | Assign owner | Estimate only | Yes/No + rationale | Not scored | Open / date / evidence |

**Rating rule:** Use descriptive categories (low / medium / high / critical) only with a short rationale. “Critical” should describe immediate consequence or gating significance, not be used as a substitute for legal assessment. No numeric precision without reliable data.

## 3. Evidence and source register

| Evidence ID | Item / proposition supported | Source URL or approved restricted reference | Publisher / custodian | Source type | Jurisdiction | Creation/publication date | Captured/check date | File/version/hash where appropriate | Integrity/provenance notes | Verification status | Access restriction | Related risks / decisions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E-001 | Example official source | Add verified URL | Official publisher | Legislation / case / guidance / contract / business record / testimony / other | To verify | To verify | YYYY-MM-DD | Use approved storage reference | Not reviewed | `UNVERIFIED` | Restricted as required | CC-R-001 |

Do not log a legal source as verified merely because a search result was returned. Preserve the source document/version and the relevant pinpoint where permitted; record the exact proposition it supports and its limitations.

## 4. Decision and approval log

| Decision ID | Decision required | Options / trade-offs | Recommendation and grounds | Adversarial objection | Decision owner | Counsel reviewer / date | Required approvals | Decision / date | Authorized external action? | Evidence of action or reason not executed |
|---|---|---|---|---|---|---|---|---|---|---|
| CC-D-001 | Example only | A / B / defer | Preliminary only | Record strongest objection | To assign | Not reviewed | Counsel / leadership as applicable | Pending | No | No action taken |

Record the actual decision and its date. A draft, verbal expectation, open issue, or AI-generated recommendation does not count as approval or execution evidence.

## 5. Counsel-review gate

| Gate | Required evidence | Allowed status before approval | Approver | Evidence required to pass |
|---|---|---|---|---|
| G-01 — client identity | Registry evidence and authorized instruction owner | `BLOCKED — IDENTITY UNVERIFIED` | Authorized corporate decision-maker and counsel as appropriate | Confirmed entity/authority record |
| G-02 — source verification | Primary source, effective date/status, pinpoint, fact mapping | `PRELIMINARY` / `REQUIRES VERIFICATION` | Analyst + reviewer | Source-register record with review evidence |
| G-03 — adverse review | Three strongest objections and disposition | `REVIEW REQUIRED` | Independent reviewer; counsel where consequential | Recorded resolution or preserved disagreement |
| G-04 — draft approval | Version, scope, jurisdiction, risk notes and counsel comments | `DRAFT — FOR COUNSEL REVIEW` | Licensed counsel for legal position; leadership for business decision | Written approval tied to exact version |
| G-05 — external execution | Authorized action, exact recipient, final approved version, execution owner | `APPROVAL PENDING` | Authorized human; counsel when appropriate | Record of explicit authorization and completed action |
| G-06 — closeout | Evidence preserved, action verified, residual risk, next review | `OPEN` | Matter owner + counsel where required | Closure evidence and recorded residual risk |

Never infer that an approval gate passed because an issue was marked “done” unless the evidence required by that gate exists.

## 6. Version and retention notes

- Use append-only or controlled version history for material decisions and evidence metadata.
- Do not delete, backdate, rewrite or conceal potentially relevant records.
- For legal holds, preservation duties, retention conflicts, and disposition of originals, obtain counsel advice as required. Only record a hold as issued when an authorized person actually issued it.
- Store sensitive documents only in the approved restricted system, with least privilege and a documented custodian.
- Do not upload secrets, passwords, private keys, production credentials, or unnecessary sensitive personal data into AI tools.
