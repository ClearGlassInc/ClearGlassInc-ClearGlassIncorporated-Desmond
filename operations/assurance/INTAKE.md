# Pre-Engagement Intake

AI Agent Attack-Surface and Control Assurance. Complete and return this before
day 1.

The assessment is evidence-based. Every item below exists so the first day is
spent looking at your environment rather than waiting for access. Where an item
cannot be provided, say so and say why. A refusal with a reason is workable. A
silence is not.

| Field | Value |
|---|---|
| Client | [CLIENT] |
| Engagement ID | [ENGAGEMENT ID] |
| Tier | [TIER] |
| Intake completed by (name, title) | [UNKNOWN - NOT YET VALIDATED] |
| Date returned | [DATE] |
| Target engagement start | [DATE] |

---

## 1. Access and read-only credentials

ClearGlass requests **read-only** access. No write, no admin, no configuration
change. Where a platform cannot issue a read-only role, say so and propose the
alternative: a client-operated screen-share walkthrough, or an export produced
by your team.

| # | Platform | What is needed | Provisioned (Y/N) | Account / role issued | Date issued | Client contact |
|---|---|---|---|---|---|---|
| 1 | Identity provider (Entra ID, Okta, Google Workspace, other) | Read-only directory role sufficient to list enterprise applications, service principals, OAuth grants, and consented permissions | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] | [UNKNOWN - NOT YET VALIDATED] |
| 2 | Cloud accounts (Azure, AWS, GCP) | Read-only / viewer role at the subscription, account, or project level, covering IAM, service accounts, and key metadata | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] | [UNKNOWN - NOT YET VALIDATED] |
| 3 | SaaS admin consoles in scope (M365, Google Workspace, Salesforce, ServiceNow, Slack, HR, finance, other) | Read-only admin or audit role, sufficient to list installed apps, connectors, bots, and their granted scopes | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] | [UNKNOWN - NOT YET VALIDATED] |
| 4 | Source repository organization (GitHub, GitLab, Azure DevOps) | Read-only org-level access sufficient to list installed apps, bots, deploy keys, PATs, and Actions/pipeline integrations | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] | [UNKNOWN - NOT YET VALIDATED] |
| 5 | Logging / SIEM (Sentinel, Splunk, Elastic, cloud-native audit logs) | Read-only query access, or a scoped export covering the agreed test window | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] | [UNKNOWN - NOT YET VALIDATED] |
| 6 | AI platform tenants (model provider consoles, agent builders, automation platforms) | Read-only access to agent/workflow definitions, connected tools, and credential configuration | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] | [UNKNOWN - NOT YET VALIDATED] |
| 7 | Other in-scope systems | [UNKNOWN - NOT YET VALIDATED] | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] | [UNKNOWN - NOT YET VALIDATED] |

Access is issued to a named ClearGlass account, is time-boxed to the engagement,
and is revoked by the client on the agreed end date. ClearGlass will confirm
revocation in the closure note.

---

## 2. Documents requested

| # | Document | Provided (Y/N) | If not, why | Date received |
|---|---|---|---|---|
| 1 | Existing AI use / acceptable use policy, if one exists | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] |
| 2 | Existing agent, bot, or integration register, in whatever form it exists, including a spreadsheet | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] |
| 3 | Data processing agreements with AI and automation vendors | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] |
| 4 | Incident response plan, and any runbook covering automated systems | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] |
| 5 | Access management / privileged access policy | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] |
| 6 | Change approval process covering integrations and connected apps | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] |
| 7 | Data classification standard, if one exists | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] |
| 8 | Most recent audit or assessment report touching system access (SOC 2, internal audit, other) | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] |
| 9 | Log retention policy and current retention configuration | [TBD] | [UNKNOWN - NOT YET VALIDATED] | [DATE] |

A missing document is a finding, not a blocker. Say it is missing rather than
producing one for the engagement.

---

## 3. People to interview

Roles, not names, at intake. Names are filled in during scheduling. Each
interview is 30 to 45 minutes.

| # | Role | Why | Scheduled (Y/N) | Date | Duration |
|---|---|---|---|---|---|
| 1 | Executive sponsor (CIO / CISO / VP IT) | Scope confirmation, risk appetite, what the board is asking for | [TBD] | [DATE] | 30 min |
| 2 | Identity / directory administrator | How agents authenticate, how access is granted and reviewed | [TBD] | [DATE] | 45 min |
| 3 | Cloud / infrastructure lead | Service accounts, keys, workload identity, cloud-side agent access | [TBD] | [DATE] | 45 min |
| 4 | Application or SaaS owner for each major in-scope platform | Which connectors and bots exist, who approved them, what they do | [TBD] | [DATE] | 30 min each |
| 5 | Security operations / incident response lead | Alerting, investigation, what happens at 2am | [TBD] | [DATE] | 45 min |
| 6 | Development / platform engineering lead | Agents in the pipeline, repository integrations, deploy-path access | [TBD] | [DATE] | 45 min |
| 7 | Internal audit or risk representative | What evidence they need, in what form, and for whom | [TBD] | [DATE] | 30 min |
| 8 | Privacy officer or legal contact, if one exists | Regulatory applicability position, vendor agreements | [TBD] | [DATE] | 30 min |
| 9 | Business owner of the highest-risk automated workflow | What the agent is actually for, and what happens if it is wrong | [TBD] | [DATE] | 30 min |

---

## 4. Scope boundary agreement

Agreed in writing before fieldwork. Changes require a written amendment signed
by both sides.

**Systems in scope:**

| # | System / Platform | Tenant or account identifier | Notes |
|---|---|---|---|
| 1 | [UNKNOWN - NOT YET VALIDATED] | [UNKNOWN - NOT YET VALIDATED] | [TBD] |
| 2 |  |  |  |
| 3 |  |  |  |

**Systems explicitly out of scope:**

| # | System / Platform | Reason | Agreed by |
|---|---|---|---|
| 1 | [UNKNOWN - NOT YET VALIDATED] | [UNKNOWN - NOT YET VALIDATED] | [UNKNOWN - NOT YET VALIDATED] |
| 2 |  |  |  |

**Testing constraints:**

| Field | Value |
|---|---|
| Control validation window (dates and hours) | [DATE] |
| Systems where live control testing is not permitted | [UNKNOWN - NOT YET VALIDATED] |
| Change freeze or blackout periods | [UNKNOWN - NOT YET VALIDATED] |
| Client approver for each control test | [UNKNOWN - NOT YET VALIDATED] |
| Escalation contact if a test causes disruption | [UNKNOWN - NOT YET VALIDATED] |

**Confirmed method:** read-only review, interviews, and control validation
performed by client personnel under assessor observation. No offensive testing.
No changes made to client systems by ClearGlass. No legal or regulatory opinion
is provided.

---

## 5. Data handling statement

- ClearGlass requests **read-only** access for the minimum period required, and
  confirms revocation at engagement close.
- ClearGlass **does not export client data beyond what is needed for the
  evidence record**. Where a full export would be disproportionate, a redacted
  extract or a screenshot of the relevant configuration is taken instead.
- Personal information is not collected unless it is the subject of a finding,
  and is minimized and redacted where it is.
- Evidence artifacts are stored encrypted, access-restricted to the assessor,
  and listed in the report's evidence register.
- **Retention and destruction:** evidence artifacts are retained for
  **[TBD] days** after report issue, to support questions on the findings, and
  are then returned to the client or destroyed at the client's written
  election. ClearGlass confirms destruction in writing. Agree the number of days
  and the election before day 1.

| Field | Value |
|---|---|
| Evidence retention period agreed (days) | [TBD] |
| Client election at end of retention (return / destroy) | [TBD] |
| Client data-handling contact | [UNKNOWN - NOT YET VALIDATED] |
| Any client-specific handling requirements (residency, encryption, named storage) | [UNKNOWN - NOT YET VALIDATED] |

---

## Intake sign-off

| Field | Value |
|---|---|
| Client signature (name, title) | [TBD] |
| Date | [DATE] |
| ClearGlass assessor | [ASSESSOR] |
| Date | [DATE] |

---

ClearGlass Inc. - Security Before Convenience. Evidence Before Assumption.
Verify Before Claiming Success.
