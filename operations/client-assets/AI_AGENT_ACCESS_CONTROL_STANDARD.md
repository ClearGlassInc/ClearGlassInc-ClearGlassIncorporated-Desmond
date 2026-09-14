# ClearGlass AI Agent Access Control Standard

**Purpose:** A practical baseline for AI agents that can access internal systems, data, or tools.

## Executive rule

An AI agent must never receive more authority than a specifically identified, trained, and accountable human operator would receive for the same task.

## Scope

Apply this standard before an AI agent is permitted to read internal documents, records, tickets, source code, or knowledge bases; use SaaS applications, APIs, databases, browsers, command lines, or workflow tools; create, modify, approve, transmit, delete, or publish information; initiate payments, customer communications, access changes, infrastructure actions, or security actions; or share data with an external AI model, service provider, subcontractor, or plug-in.

## Minimum control requirements

| Control area | Mandatory control | Evidence to retain |
|---|---|---|
| Business owner | One accountable business owner and one technical owner per production agent | Approved ownership record |
| Approved purpose | Define workflow, permitted/prohibited actions, inputs, outputs, and success criteria | Agent use-case record |
| Identity | Unique, non-shared service identity | Identity inventory and authentication configuration |
| Least privilege | Minimum required permissions, systems, datasets, API scopes, and time window | Role, scope, and entitlement review |
| Secrets | Approved secrets-management system; no credentials in prompts, repositories, or browser sessions | Secret-storage and rotation record |
| Data classification | Identify data entering prompts, context, logs, outputs, and external tools | Data-flow map and classification review |
| Human authorization | Named human approval for irreversible, financial, legal, external-facing, privileged, or production-changing actions | Approval workflow and audit trail |
| Action boundaries | Allow-list tools, endpoints, domains, commands, and workflows; block free-form execution where feasible | Policy configuration and test results |
| Logging | Record task requests, context references, tool calls, permissions, actions, approver, outputs, and errors | Centralized immutable activity log |
| Monitoring | Detect anomalous access, excessive tool use, unusual data volume, failed authorization, destinations, and repeated high-impact actions | Alert rules, review process, incident tickets |
| Testing | Test prompt injection, exfiltration, excessive privilege, unsafe tool use, hallucinated instructions, and provider failure recovery | Test plan, findings, remediation record |
| Vendor assurance | Document provider, processing terms, retention, training use, hosting, incident reporting, subprocessors, and continuity | Vendor assessment and contract review |
| Change management | Reassess model, tools, permissions, data sources, workflow, provider, or environment changes | Change record and reapproval |
| Termination | Disable agent, revoke credentials, remove integrations, preserve evidence, and restore manual operations | Tested kill-switch and recovery procedure |

## High-impact actions requiring human approval

A human must explicitly approve, through a logged workflow, before an agent:

- Sends an external email, message, report, quote, proposal, or social post.
- Changes a customer, employee, supplier, financial, legal, security, or production record.
- Creates or changes user access, API credentials, cloud resources, code deployments, firewall rules, or endpoint controls.
- Transfers sensitive, confidential, personal, regulated, or proprietary information outside the approved environment.
- Executes a payment, purchase, refund, contract action, or binding business commitment.
- Deletes records, disables services, or alters backups, logs, or retention settings.

## Production deployment gate

Do not approve production deployment until the use case has an accountable owner and documented purpose; data flows and tool permissions are mapped and approved; the agent uses unique identity, scoped access, and centrally managed secrets; high-impact actions have human approval gates; logging and monitoring are operational and tested; security testing has documented findings and remediation decisions; a kill-switch and manual fallback process have been tested; and the responsible executive accepts residual risk in writing.

## Board-level questions

1. Which AI agents can act in our environment, not merely generate text?
2. What systems, data, credentials, and external destinations can each agent reach?
3. Which actions can occur without human approval?
4. Can we reconstruct a material agent action from evidence?
5. Can we immediately revoke access and continue the underlying business process manually?

**ClearGlass operating principle:** Evidence before assertion. Provenance before convenience. Human accountability by design.