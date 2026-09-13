# AI Agent Attack-Surface and Control Assurance Assessment

**This template ships empty. Every field below is a placeholder.** Nothing in
this file is a finding. Fill it only from evidence gathered in a real
engagement.

---

## Assessor working notes - DELETE THIS SECTION BEFORE DELIVERY

This section documents the placeholder markers used throughout the template.
`python3 tools/assurance_pack.py --check <file>` fails while any of them remain,
including the ones printed here, which is how the tool forces this section to be
removed before a document goes to a client.

Markers:

- `[EVIDENCE REQUIRED]` - a field that must carry an evidence reference and does
  not yet.
- `[UNKNOWN - NOT YET VALIDATED]` - a field the assessor has not established.
  Resolve it to a real value, or to the bare confidence value `UNKNOWN`, which
  is a legitimate finding and passes the check.
- `[ASSUMPTION - REQUIRES CONFIRMATION]` - a working assumption that must be
  confirmed with a named client contact or removed.
- `[TBD]`, `[CLIENT]`, `[DATE]`, `[ENGAGEMENT ID]`, `[TIER]`, `[ASSESSOR]`,
  `[SCOPE]` - header scaffolding.
- `[EXAMPLE - DELETE BEFORE DELIVERY]` - illustrative rows. Delete them.

The bare word `UNKNOWN` in a Confidence cell is a real, permitted value. The
checker does not fail on it. Only bracketed markers fail.

---

## Engagement header

| Field | Value |
|---|---|
| Client | [CLIENT] |
| Engagement ID | [ENGAGEMENT ID] |
| Tier | [TIER] |
| Assessor | [ASSESSOR] |
| Engagement start date | [DATE] |
| Fieldwork completed | [DATE] |
| Report issued | [DATE] |
| Report version | [TBD] |
| Client sponsor (name, title) | [UNKNOWN - NOT YET VALIDATED] |

### Scope boundary

Scope is agreed in writing before fieldwork begins and is not changed mid
engagement without a written amendment.

**Systems in scope:**

| # | System / Platform | Tenant or Account Identifier | Read-only access granted (Y/N) | Access granted date |
|---|---|---|---|---|
| 1 | [SCOPE] | [UNKNOWN - NOT YET VALIDATED] | [TBD] | [DATE] |
| 2 |  |  |  |  |
| 3 |  |  |  |  |

**Systems explicitly out of scope:**

| # | System / Platform | Reason for exclusion | Agreed by (client contact) |
|---|---|---|---|
| 1 | [SCOPE] | [UNKNOWN - NOT YET VALIDATED] | [UNKNOWN - NOT YET VALIDATED] |
| 2 |  |  |  |

**Assessment method:** read-only review of client consoles, exports, logs, and
configuration, plus interviews with named client personnel, plus control
validation by client-executed test under assessor observation. No offensive
testing. No changes made to client systems.

---

## Evidence standard

This is what makes the deliverable defensible. It applies to every row in every
artifact below.

**Every row must carry an evidence reference.** An evidence reference names a
specific artifact and the date it was obtained, for example
`EV-014 / Entra ID enterprise applications export / 2026-03-04`. A row with no
evidence reference is not a finding and must not be delivered.

**Three confidence labels are permitted. No others.**

| Label | Means | Requires |
|---|---|---|
| `VERIFIED` | Observed directly by the assessor in the client's console, logs, or export. | A named evidence artifact and the date it was observed. |
| `REPORTED` | Stated by a named client contact. Not independently observed by the assessor. | The contact's name and role, and the date of the statement. |
| `UNKNOWN` | Not established. | A note on what was attempted and why it could not be established. |

**An UNKNOWN is a finding, not a gap in the report.** Record it, do not hide it,
do not guess a value to fill the cell.

**An assessment with no UNKNOWNs is a red flag, not a clean result.** In a real
environment some things cannot be established in the time available. A report
claiming full knowledge of an agent estate invites the question of how, and
rarely survives it.

### Evidence register

Every evidence reference used in this report resolves to a row here.

| Evidence Ref | Description | Type (export / screenshot / log / interview / config) | Source System | Obtained By | Date Obtained | Storage Location |
|---|---|---|---|---|---|---|
| EV-001 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [ASSESSOR] | [DATE] | [TBD] |
| EV-002 |  |  |  |  |  |  |
| EV-003 |  |  |  |  |  |  |

---

## Artifact 1 - Agent Inventory Register

Every AI agent, copilot, assistant, automation, or model-driven integration
connected to an in-scope system.

| ID | Agent Name | Platform | Function | Business Owner | Technical Owner | Credential Model | Privilege Level | External Dependencies | Confidence | Evidence Ref | Risk Rating |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A-001 | [EVIDENCE REQUIRED] | [EVIDENCE REQUIRED] | [EVIDENCE REQUIRED] | [UNKNOWN - NOT YET VALIDATED] | [UNKNOWN - NOT YET VALIDATED] | [EVIDENCE REQUIRED] | [EVIDENCE REQUIRED] | [UNKNOWN - NOT YET VALIDATED] | UNKNOWN | [EVIDENCE REQUIRED] | [TBD] |
| A-002 |  |  |  |  |  |  |  |  |  |  |  |
| A-003 |  |  |  |  |  |  |  |  |  |  |  |

Field guidance:

- **Credential model:** service principal, OAuth delegated (whose account?), API
  key, personal access token, embedded credential, shared secret.
- **Privilege level:** read, write, admin, tenant-wide admin.
- **External dependencies:** third-party services the agent calls or is called
  by, including model providers.
- **Risk rating:** assessor judgement, stated with the reasoning in the notes.
  Do not assign a rating to a row whose Confidence is UNKNOWN without saying so.

### Inventory completeness statement

| Field | Value |
|---|---|
| Discovery method(s) used | [EVIDENCE REQUIRED] |
| Systems enumerated | [EVIDENCE REQUIRED] |
| Systems not enumerable, and why | [UNKNOWN - NOT YET VALIDATED] |
| Shadow / unsanctioned agent discovery attempted (Y/N + method) | [TBD] |
| Estimated completeness of this inventory (%) | [UNKNOWN - NOT YET VALIDATED] |
| Basis for that completeness estimate | [EVIDENCE REQUIRED] |

The completeness percentage is an assessor estimate with a stated basis. It is
not a measurement. If the basis cannot be stated, record `UNKNOWN`.

---

## Artifact 2 - Identity and Accountability Register

Who each agent is, and which human is accountable for it.

| Agent ID | Authentication Method | Service Account | Named Human Owner | Approval Authority | Admin Privileges (Y/N) | Third-Party Delegated Access | Orphaned (Y/N) | Governance Gap | Confidence | Evidence Ref |
|---|---|---|---|---|---|---|---|---|---|---|
| A-001 | [EVIDENCE REQUIRED] | [EVIDENCE REQUIRED] | [UNKNOWN - NOT YET VALIDATED] | [UNKNOWN - NOT YET VALIDATED] | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [TBD] | [UNKNOWN - NOT YET VALIDATED] | UNKNOWN | [EVIDENCE REQUIRED] |
| A-002 |  |  |  |  |  |  |  |  |  |  |
| A-003 |  |  |  |  |  |  |  |  |  |  |

Field guidance:

- **Orphaned:** the named owner has left the organization, changed role, or
  cannot be identified. An orphaned agent with write access is a material
  finding on its own.
- **Approval authority:** who is permitted to approve a change to this agent's
  access. If nobody holds that authority in writing, that is the governance gap.

---

## Artifact 3 - Permission and Tool Access Map

What each agent can actually reach, and what it could reach next.

| Agent ID | Connected System | Access Type (read/write/admin) | Scope (user/tenant-wide) | Granted By | Granted Date | Business Justification | Lateral Movement Potential | Excessive Privilege (Y/N) | Confidence | Evidence Ref |
|---|---|---|---|---|---|---|---|---|---|---|
| A-001 | [EVIDENCE REQUIRED] | [EVIDENCE REQUIRED] | [EVIDENCE REQUIRED] | [UNKNOWN - NOT YET VALIDATED] | [UNKNOWN - NOT YET VALIDATED] | [UNKNOWN - NOT YET VALIDATED] | [ASSUMPTION - REQUIRES CONFIRMATION] | [TBD] | UNKNOWN | [EVIDENCE REQUIRED] |
| A-002 |  |  |  |  |  |  |  |  |  |  |
| A-003 |  |  |  |  |  |  |  |  |  |  |

**Excessive privilege** means the granted access exceeds what the stated
business function requires. Judge it against the documented justification, not
against what feels reasonable.

### Critical dependency chains

Write each chain as `Agent -> System -> System`, following write access and
credential reuse, not network reachability.

| Chain ID | Chain | Impact if the first link is compromised or misbehaves | Confidence | Evidence Ref |
|---|---|---|---|---|
| C-001 | [EVIDENCE REQUIRED] | [EVIDENCE REQUIRED] | UNKNOWN | [EVIDENCE REQUIRED] |
| C-002 |  |  |  |  |

Example of chain formatting only, not a finding:
`[EXAMPLE - DELETE BEFORE DELIVERY] A-000 -> Placeholder-System-One -> Placeholder-System-Two`

---

## Artifact 4 - Data Classification and Egress Report

What data each agent touches, and where that data goes.

| Agent ID | Data Source | Data Classification | Regulated (PIPEDA/PHIPA/PCI/other) | Crosses Trust Boundary (Y/N) | Destination | Third-Party Processor | Retention Control | Leakage Pathway | Confidence | Evidence Ref |
|---|---|---|---|---|---|---|---|---|---|---|
| A-001 | [EVIDENCE REQUIRED] | [EVIDENCE REQUIRED] | [ASSUMPTION - REQUIRES CONFIRMATION] | [TBD] | [EVIDENCE REQUIRED] | [UNKNOWN - NOT YET VALIDATED] | [UNKNOWN - NOT YET VALIDATED] | [UNKNOWN - NOT YET VALIDATED] | UNKNOWN | [EVIDENCE REQUIRED] |
| A-002 |  |  |  |  |  |  |  |  |  |  |
| A-003 |  |  |  |  |  |  |  |  |  |  |

### Regulatory regimes to consider

For Ontario and Canadian engagements the regimes most often raised are PIPEDA
(federal private-sector personal information) and, where personal health
information is involved, PHIPA (Ontario). Sector-specific and contractual
regimes such as PCI DSS may also apply.

These are listed as **items for the assessor to confirm applicability with the
client and the client's counsel**, not as a determination that any of them
applies. Record the client's own position on applicability, attributed to a
named contact, in the row above.

**ClearGlass Inc. does not provide legal advice.** Nothing in this report is a
legal or regulatory opinion, and it must not be relied on as one.

| Regime | Client position on applicability | Stated by (name, role, date) | Confidence | Evidence Ref |
|---|---|---|---|---|
| PIPEDA | [UNKNOWN - NOT YET VALIDATED] | [UNKNOWN - NOT YET VALIDATED] | UNKNOWN | [EVIDENCE REQUIRED] |
| PHIPA | [UNKNOWN - NOT YET VALIDATED] | [UNKNOWN - NOT YET VALIDATED] | UNKNOWN | [EVIDENCE REQUIRED] |
| Other | [UNKNOWN - NOT YET VALIDATED] | [UNKNOWN - NOT YET VALIDATED] | UNKNOWN | [EVIDENCE REQUIRED] |

---

## Artifact 5 - Telemetry and Auditability Assessment

Whether agent activity can be seen, retained, investigated, and reconstructed.

### Maturity rubric (0-4)

Used for Artifact 5 and Artifact 6. Defined once, here.

| Score | Definition |
|---|---|
| 0 | No capability. The thing does not exist. |
| 1 | Ad hoc. Exists in some places by accident of platform defaults, not by design, not consistent, not owned. |
| 2 | Documented but unproven. Designed and written down, but never tested, or tested so long ago that the result is not evidence. |
| 3 | Implemented and verified once. Works, and the assessor observed it working, but it is not exercised on a schedule and coverage has gaps. |
| 4 | Comprehensive and tested. Covers the in-scope estate, is exercised on a defined schedule, has a named owner, and the most recent test result is available as evidence. |

A capability that exists only as a policy document scores no higher than 2.

### Dimension scores

| Dimension | Score (0-4) | Evidence Ref | Confidence | Notes |
|---|---|---|---|---|
| Action logging coverage | [TBD] | [EVIDENCE REQUIRED] | UNKNOWN | [UNKNOWN - NOT YET VALIDATED] |
| Decision traceability | [TBD] | [EVIDENCE REQUIRED] | UNKNOWN | [UNKNOWN - NOT YET VALIDATED] |
| Log retention period | [TBD] | [EVIDENCE REQUIRED] | UNKNOWN | [UNKNOWN - NOT YET VALIDATED] |
| Alerting on anomalous agent action | [TBD] | [EVIDENCE REQUIRED] | UNKNOWN | [UNKNOWN - NOT YET VALIDATED] |
| Investigation readiness | [TBD] | [EVIDENCE REQUIRED] | UNKNOWN | [UNKNOWN - NOT YET VALIDATED] |
| Forensic reconstructability | [TBD] | [EVIDENCE REQUIRED] | UNKNOWN | [UNKNOWN - NOT YET VALIDATED] |
| Evidence preservation integrity | [TBD] | [EVIDENCE REQUIRED] | UNKNOWN | [UNKNOWN - NOT YET VALIDATED] |

### Reconstruction test

The single test that decides whether the telemetry is real.

| Field | Value |
|---|---|
| Can the assessor reconstruct, from logs alone, the full action chain of one selected agent over a 24-hour window? (Y/N) | [TBD] |
| Agent selected | [UNKNOWN - NOT YET VALIDATED] |
| Window tested (start / end, with timezone) | [DATE] |
| Who performed the reconstruction | [ASSESSOR] |
| What could be reconstructed | [EVIDENCE REQUIRED] |
| What could not be reconstructed, and why | [EVIDENCE REQUIRED] |
| Evidence Ref | [EVIDENCE REQUIRED] |

---

## Artifact 6 - Control Validation Report

**Controls are validated by test, not by policy document review.** A documented
control that has never been tested scores no higher than 2 on the rubric above,
regardless of how well written the document is. If a control could not be
tested, record `Tested = N` and say why. Do not score an untested control on the
strength of the documentation.

| Control | Exists (Y/N) | Tested (Y/N) | Test Method | Test Date | Result | Score (0-4) | Evidence Ref |
|---|---|---|---|---|---|---|---|
| Human approval gate on high-risk actions | [TBD] | [TBD] | [EVIDENCE REQUIRED] | [DATE] | [EVIDENCE REQUIRED] | [TBD] | [EVIDENCE REQUIRED] |
| Break-glass procedure | [TBD] | [TBD] | [EVIDENCE REQUIRED] | [DATE] | [EVIDENCE REQUIRED] | [TBD] | [EVIDENCE REQUIRED] |
| Kill switch / emergency disablement | [TBD] | [TBD] | [EVIDENCE REQUIRED] | [DATE] | [EVIDENCE REQUIRED] | [TBD] | [EVIDENCE REQUIRED] |
| Rollback capability | [TBD] | [TBD] | [EVIDENCE REQUIRED] | [DATE] | [EVIDENCE REQUIRED] | [TBD] | [EVIDENCE REQUIRED] |
| Agent offboarding process | [TBD] | [TBD] | [EVIDENCE REQUIRED] | [DATE] | [EVIDENCE REQUIRED] | [TBD] | [EVIDENCE REQUIRED] |
| Incident response integration | [TBD] | [TBD] | [EVIDENCE REQUIRED] | [DATE] | [EVIDENCE REQUIRED] | [TBD] | [EVIDENCE REQUIRED] |
| Governance escalation path | [TBD] | [TBD] | [EVIDENCE REQUIRED] | [DATE] | [EVIDENCE REQUIRED] | [TBD] | [EVIDENCE REQUIRED] |

Test method must name what was actually done, who executed it, and what was
observed. "Reviewed the policy" is not a test method. "Client engineer disabled
agent A-00x in the admin console at 14:12 while assessor observed; agent's next
scheduled action at 14:15 did not execute; console state captured as EV-0xx" is
a test method.

---

## Executive summary

All three lists are blank until the artifacts above are complete. Each entry
must trace to a row in an artifact and to an evidence reference.

### Top 5 material risks

| # | Risk | Severity | Finding Ref | Evidence Ref |
|---|---|---|---|---|
| 1 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |
| 2 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |
| 3 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |
| 4 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |
| 5 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |

### Top 5 governance deficiencies

| # | Deficiency | Severity | Finding Ref | Evidence Ref |
|---|---|---|---|---|
| 1 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |
| 2 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |
| 3 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |
| 4 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |
| 5 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |

### Top 5 operational exposures

| # | Exposure | Severity | Finding Ref | Evidence Ref |
|---|---|---|---|---|
| 1 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |
| 2 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |
| 3 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |
| 4 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |
| 5 | [EVIDENCE REQUIRED] | [TBD] | [TBD] | [EVIDENCE REQUIRED] |

Severity scale: Critical / High / Medium / Low. State the basis for the rating
in the finding, not just the label.

---

## Prioritized remediation roadmap

| Priority | Finding Ref | Recommended Action | Effort | Owner | Target Date |
|---|---|---|---|---|---|
| 1 | [TBD] | [EVIDENCE REQUIRED] | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] |
| 2 |  |  |  |  |  |
| 3 |  |  |  |  |  |
| 4 |  |  |  |  |  |
| 5 |  |  |  |  |  |

Recommended actions describe what the client should do. ClearGlass does not
implement them. Owner is a client role or named person, agreed with the client
before the report is issued.

---

## Quality control sign-off

Completed by the assessor before delivery. The report does not ship until every
field here is filled.

### Evidence quality counts

Run `python3 tools/assurance_pack.py --summary <this file>` and record the
output.

| Count | Value |
|---|---|
| Rows with Confidence = VERIFIED | [TBD] |
| Rows with Confidence = REPORTED | [TBD] |
| Rows with Confidence = UNKNOWN | [TBD] |
| Total rows carrying a confidence label | [TBD] |
| VERIFIED as a share of total (%) | [TBD] |

### Evidence gaps

Everything that could not be established, and what was attempted.

| # | Gap | What was attempted | Why it could not be established |
|---|---|---|---|
| 1 | [UNKNOWN - NOT YET VALIDATED] | [EVIDENCE REQUIRED] | [EVIDENCE REQUIRED] |
| 2 |  |  |  |

### Areas requiring further validation

| # | Area | Why it needs further validation | Recommended next step |
|---|---|---|---|
| 1 | [UNKNOWN - NOT YET VALIDATED] | [EVIDENCE REQUIRED] | [TBD] |
| 2 |  |  |  |

### Assessor statement

> I confirm that no finding in this document is unsupported by a referenced
> evidence artifact. Every row carries a confidence label of VERIFIED, REPORTED,
> or UNKNOWN, applied according to the evidence standard stated in this report.
> No value in this document has been inferred, estimated, or supplied to fill a
> blank. Where a fact could not be established it is recorded as UNKNOWN.

| Field | Value |
|---|---|
| Assessor | [ASSESSOR] |
| Signature | [TBD] |
| Date | [DATE] |
| Pre-delivery check run (`--check` exit 0) | [TBD] |

---

ClearGlass Inc. - Security Before Convenience. Evidence Before Assumption.
Verify Before Claiming Success.
