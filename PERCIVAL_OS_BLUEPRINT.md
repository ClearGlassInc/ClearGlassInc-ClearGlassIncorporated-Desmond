# PERCIVAL OS — Master Architecture & Product Blueprint

> **Codename:** PERCIVAL — an Iron Man / JARVIS-class always-on intelligent command center.
> *(Named for the knight of the Grail quest — relentless, loyal, and built to find the answer.)*
> **Class:** Autonomous command center for a power user / executive operator
> **Owner:** ClearGlass Inc.
> **Reference HUD:** [`percival-os.html`](./percival-os.html)

---

## 1. Product Vision Summary

PERCIVAL is a single, always-on intelligence layer that sits above every tool an
operator already uses — email, chat, calendar, files, CRM, code, cloud, security
telemetry — and turns the chaos of modern work into a calm, prioritized, executable
stream of decisions.

It is not a chatbot. It is a **command center**. The operator gives intent; PERCIVAL
decomposes it into tasks, routes those tasks to specialized agents, executes the safe
ones autonomously, escalates the risky ones for one-tap approval, and reports back
with citations, confidence, and the next best action.

**Three promises:**

1. **Nothing important is missed.** Inboxes, alerts, deadlines, and anomalies are
   triaged continuously. The operator wakes up to a briefing, not a backlog.
2. **Intent → outcome with minimum friction.** "Draft the investor update,"
   "watch this endpoint," "research this entity" — each becomes a tracked mission
   with a visible plan and an audit trail.
3. **Trust is built in, not bolted on.** Every action is logged, every recommendation
   is explainable, every destructive step requires confirmation, and every secret is
   vaulted.

**North-star metric:** *operator decisions accelerated per day* (briefings consumed,
drafts approved, missions completed, threats neutralized) at zero unreviewed-action
incidents.

---

## 2. Feature Architecture

PERCIVAL is organized into seven cooperating subsystems orbiting a central reasoning
core (the "Brain").

```
                         ┌───────────────────────────┐
                         │        BRAIN (Core)        │
                         │  reasoning · planning ·    │
                         │  memory · policy · routing │
                         └─────────────┬─────────────┘
        ┌──────────────┬───────────────┼───────────────┬──────────────┐
        ▼              ▼               ▼               ▼              ▼
 ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
 │ COMMAND    │ │ ORCHESTR-  │ │ KNOWLEDGE  │ │  SECURITY  │ │ AUTOMATION │
 │ CENTER     │ │ ATION      │ │ INTEL      │ │  & MONITOR │ │  ENGINE    │
 │ inbox·tasks│ │ agent swarm│ │ RAG·graph  │ │ anomaly·IR │ │ workflows  │
 │ briefings  │ │ tool router│ │ entities   │ │ zero-trust │ │ triggers   │
 └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘
        └──────────────┴───────────────┬───────────────┴──────────────┘
                                        ▼
                  ┌───────────────────────────────────────┐
                  │  INTERFACE LAYER (HUD · Voice · Multi)  │
                  │  holographic dashboards · voice · files │
                  └───────────────────────────────────────┘
```

### 2.1 Brain (Reasoning Core)
- **Planner/Decomposer** — turns goals into a DAG of tasks with dependencies, owners
  (agents), tools, and approval gates.
- **Router** — selects the right model, agent, and tool per task (cost/latency/skill aware).
- **Policy engine** — applies permission boundaries, approval modes, and rate limits
  *before* any action is dispatched.
- **Memory manager** — short-term session state vs. long-term structured memory.
- **Reflection loop** — self-critiques plans, retries failures, optimizes prompts/workflows.

### 2.2 Command Center
- Unified inbox/chat/task/meeting feed with **triage scoring** (urgency × impact × deadline).
- Reply drafting in the operator's voice; escalation of urgent items; opportunity/risk tagging.
- Generated **daily briefing**, **weekly strategy report**, and **live KPI dashboard**.

### 2.3 AI Orchestration Layer
- **Agent swarm**: Research, Execution, Monitoring, Reporting, plus domain agents
  (Legal, OSINT, Brand, Finance).
- Tool use, retrieval, memory, and multi-step workflows with **checkpointing**.
- Goal decomposition with live plan visualization and per-step status.

### 2.4 Knowledge Intelligence
- Hybrid search (semantic + keyword + recency) across files, notes, email, browser
  history, docs, databases.
- Answers with **citations + confidence levels**; flags contradictions and missing info.
- Builds **semantic memory, topic graphs, and entity profiles**; extracts action items.

### 2.5 Cybersecurity & Monitoring
- Ingests endpoint, log, account, and alert telemetry.
- Detects anomalies, suspicious access, phishing, and policy violations.
- Produces **threat summaries, incident timelines, response recommendations**.
- Supports zero-trust workflows, scoped permissions, and immutable audit logging.

### 2.6 Automation Engine
- Visual + code workflows for email, CRM, reports, scheduling, OSINT, content, admin.
- Triggers, scheduled jobs, webhooks, APIs, browser automation.
- Auto-generates Python / Node.js / Bash / SQL with **sandboxed execution + approval modes**.

### 2.7 Interface Layer
- Dark, cinematic HUD: status rings, holographic dashboards, activity stream, mission panels.
- Voice + text + screenshots + files + live telemetry in; voice + text out.
- Wake word, push-to-talk, hotkeys. Desktop-first, responsive to tablet/mobile.

---

## 3. UI / UX Concept

**Design language:** *"Calm power."* High-contrast dark canvas, cyan/orange arc-reactor
palette, Orbitron display + IBM Plex Mono telemetry + Inter body. Motion is purposeful:
rings rotate to show liveness, panels glow on state change, nothing flashes for its own sake.

**Primary screen — the Brain Hub (see `percival-os.html`):**

```
┌───────────────────────────────────────────────────────────────────────┐
│  ◐ PERCIVAL OS      [ STATUS RING x4 ]            16:09  ·  ALL SYSTEMS │
├───────────────┬───────────────────────────────────┬───────────────────┤
│  MISSION RAIL │        CENTRAL BRAIN CORE          │  ACTIVITY STREAM   │
│  • briefing   │   (arc reactor + neural field)     │  live agent log    │
│  • triage     │   subsystem orbit · health rings   │  + threat ticker   │
│  • missions   │                                    │                    │
│  • agents     │   ┌─────────────────────────────┐  │  KPI TILES         │
│  • security   │   │  COMMAND CONSOLE (voice/text)│  │  revenue · uptime  │
│  • knowledge  │   └─────────────────────────────┘  │  threats · tasks   │
└───────────────┴───────────────────────────────────┴───────────────────┘
```

- **Left — Mission Rail:** modes/missions; click to focus a subsystem.
- **Center — Brain Core:** the "living" arc-reactor brain; orbiting nodes = subsystems
  with health rings; the command console docks here.
- **Right — Streams & KPIs:** real-time activity log, threat ticker, KPI tiles, deadlines.
- **Interaction:** type or speak a command → PERCIVAL shows a *plan* (decomposed steps) →
  executes safe steps, requests approval for sensitive ones → reports with confidence.
- **Modes:** Formal / Tactical / Technical change tone and density; a single toggle.
- **Approval surface:** sensitive actions surface a clear card ("APPROVE / DENY / EXPLAIN").

---

## 4. Data & Memory Architecture

```
INGEST → NORMALIZE → INDEX → REASON → ACT → AUDIT
```

**Stores:**
- **Session memory (short-term):** rolling context window + working scratchpad per mission.
- **Long-term structured memory:** entities, preferences, projects, goals, contacts,
  recurring workflows — stored as typed records (Postgres) and an entity/topic **graph**.
- **Vector index:** embeddings of documents, emails, notes, transcripts for semantic recall.
- **Episodic log:** every action, tool call, and decision (append-only, signed) for audit + replay.
- **Secrets vault:** encrypted KV (envelope encryption), never in plaintext memory or logs.

**Memory policy:**
- Clear short-term vs long-term boundary; promotion to long-term requires salience scoring.
- **User control:** view, edit, export (JSON), and delete any memory; "forget" cascades to vectors.
- Provenance on every fact (source, timestamp, confidence); contradictions flagged on write.
- PII tagging + redaction tiers; sensitive memories require step-up auth to read.

**Retrieval:** hybrid (BM25 + vector + graph expansion) with recency decay and a reranker;
every answer carries `[source, confidence]` and a "why this" trace.

---

## 5. Technical Stack Recommendation

| Layer | Recommendation |
|---|---|
| **AI core** | Claude (Opus for planning/reasoning, Sonnet for routing/drafting, Haiku for triage/classification); Claude Agent SDK for the orchestration loop, tool use, and memory |
| **Orchestration** | Agent SDK / task graph executor; queue (Redis/SQS); checkpointing in Postgres |
| **Backend** | Python (FastAPI) for AI services; Node.js for integrations/webhooks |
| **Data** | Postgres (structured + episodic), pgvector / dedicated vector DB (Qdrant/Weaviate), Redis (cache/queue), object store (S3) for files |
| **Knowledge graph** | Postgres + graph layer or Neo4j for entity/topic graphs |
| **Frontend** | The reference HUD is dependency-free HTML/CSS/JS (this repo). Production app: React + TypeScript, Web Speech API for voice, WebSocket/SSE for live streams, Tailwind/CSS variables for the HUD theme |
| **Desktop/mobile** | Electron / Tauri (desktop), React Native or PWA (mobile), with offline cache + sync |
| **Automation** | Workflow engine (Temporal or n8n-style), sandboxed code exec (gVisor/Firecracker), headless browser (Playwright) |
| **Security infra** | Vault/KMS for secrets, OIDC/SSO, RBAC, signed audit log, SIEM ingestion |
| **Observability** | OpenTelemetry traces on every agent step, structured logs, cost/latency dashboards |

---

## 6. Phased MVP → v1 Roadmap

**Phase 0 — Brain Hub (this deliverable).** Cinematic HUD, command console, simulated
agents, KPI/activity/threat streams, voice push-to-talk, mode switching. Validates the UX.

**Phase 1 — MVP (intelligence in, drafts out).**
- Connect 1 inbox + calendar + files (read-only).
- Daily briefing + inbox triage + reply drafts (approval required to send).
- Long-term memory v1 (preferences, contacts, projects) with user edit/delete.
- Audit log + approval cards live.

**Phase 2 — Orchestration & Knowledge.**
- Agent swarm (Research/Execution/Monitoring/Reporting) with plan visualization.
- Hybrid retrieval with citations + confidence; entity/topic graph.
- Automation engine v1: scheduled jobs, webhooks, code-gen with sandbox + approval.

**Phase 3 — Security & Autonomy.**
- Telemetry ingestion, anomaly/phishing detection, incident timelines.
- Zero-trust permissions, secrets vault, step-up auth.
- Autonomous safe-action execution with policy-gated escalation.

**Phase 4 — v1 (multi-device, self-improving).**
- Desktop + mobile sync with offline fallback.
- Plugin architecture, brand/legal/OSINT modes.
- Self-improving prompt/workflow optimizer (offline eval harness).

---

## 7. Sample System Prompt for the AI Core

```
You are PERCIVAL — an always-on intelligent command center for a single power user
(the Operator). You are calm, highly intelligent, concise, proactive, and precise.
You speak like an elite executive assistant and systems architect. You never overexplain
unless asked. You optimize for speed, accuracy, and actionable insight.

OPERATING PRINCIPLES
1. Intent → plan → action. For any non-trivial request, decompose into explicit steps,
   choose the right agent/tool per step, and show the plan before executing.
2. Safety first. Never take destructive, irreversible, financial, or outbound-communication
   actions without explicit Operator confirmation. Surface an APPROVE/DENY/EXPLAIN card.
3. Provenance always. Every factual claim carries a source and a confidence level
   (HIGH/MED/LOW). Flag contradictions and missing information rather than guessing.
4. Respect boundaries. Honor permissions, secrets, and privacy. Never reveal vaulted
   secrets. Log every action to the audit trail.
5. Be brief by default. Lead with the answer or the recommendation. Offer depth on request.

MODES (Operator may switch at any time)
- FORMAL: polished executive prose, for external-facing or stakeholder content.
- TACTICAL: terse, decision-first, bullet-led, for live operations.
- TECHNICAL: precise, with code, schemas, and exact parameters.

OUTPUT CONTRACT
- When acting: state the plan, the steps you executed, the steps awaiting approval,
  and the next best action.
- When answering: answer first, then [sources + confidence], then optional detail.
- When uncertain: say so, give your best estimate with confidence, and propose how to verify.

You have access to: the Operator's connected inboxes, calendar, files, knowledge base,
security telemetry, and a swarm of specialized agents (Research, Execution, Monitoring,
Reporting, Legal, OSINT, Brand, Finance). Route work to them; you remain the single
point of contact and accountability.
```

---

## 8. APIs, Integrations & Automation Modules

**Communication & productivity:** Gmail/Outlook (Graph), Slack, Teams, Discord,
Google/Microsoft Calendar, Google Drive/OneDrive/Notion, Linear/Jira/Asana.
**CRM & business:** HubSpot, Salesforce, Stripe, QuickBooks/Xero, DocuSign.
**Knowledge & web:** web search, web fetch/scrape, Playwright browser automation, RSS.
**Dev & cloud:** GitHub, CI/CD, AWS/GCP/Azure, Postgres/SQL, container/exec sandbox.
**Security:** SIEM (Splunk/Sentinel), EDR, identity (Okta/Entra), VirusTotal, threat feeds.
**Comms-out:** email send, SMS/voice (Twilio), push notifications.
**Aggregators:** Zapier/MCP for the long tail of 8,000+ apps.

**Automation modules (shippable units):** Inbox Triage, Reply Drafter, Daily Briefing,
Weekly Strategy Report, KPI Dashboard Builder, Meeting Summarizer, Calendar Optimizer,
OSINT Entity Tracker, Threat Monitor, Incident Responder, Contract Reviewer, CRM Updater,
Content Repurposer (LinkedIn/X/Threads), Report Generator, Code/Script Generator.

---

## 9. Security Model

- **SENTINEL privacy charter.** The security-intelligence persona operates under a
  privacy-first charter (`sentinel/SENTINEL_CHARTER.md`) whose hard rules are
  **enforced in code** by a fail-closed policy gate (`sentinel/sentinel/policy.py`):
  no identifying/tracking of private individuals without documented authority; no
  face-recognition / re-identification / cross-source matching on non-consenting
  people; no OSINT de-anonymization; role + purpose + approved-source checks before
  any analysis; human review for sensitive inference; an `audit_ref` on every decision.
- **Zero-trust by default.** Every tool/agent runs with the narrowest scope; permissions
  are explicit, time-boxed, and revocable.
- **Approval modes:** AUTO (safe, reversible), CONFIRM (sensitive — APPROVE/DENY card),
  BLOCK (destructive/irreversible without step-up auth). Operator sets per-category policy.
- **Secrets vault:** envelope-encrypted KV; secrets injected at execution time only;
  never logged, never returned to the model in plaintext.
- **Immutable audit log:** append-only, signed record of every action, tool call, input,
  and decision — replayable for forensics and compliance.
- **Identity & access:** SSO/OIDC, RBAC, step-up auth for sensitive reads/actions.
- **Sandboxed execution:** generated code runs in isolated, network-egress-controlled
  sandboxes with resource and time limits.
- **Data protection:** encryption in transit + at rest, PII tagging/redaction, data-residency
  controls, configurable retention + right-to-delete.
- **Recovery:** every automated change is reversible or checkpointed; one-tap rollback;
  incident "kill switch" to pause all autonomous action.
- **Explainability:** any recommendation answers "why?" with its inputs, sources, and confidence.

---

## 10. Roadmap to Enterprise-Grade

1. **Multi-tenant & teams:** organizations, workspaces, shared missions, delegated agents,
   per-team policy and audit segregation.
2. **Compliance & governance:** SOC 2 / ISO 27001 / GDPR posture, data-residency regions,
   retention policies, legal hold, exportable audit packages.
3. **Admin & policy console:** central RBAC, approval-policy management, integration
   allow-lists, spend/rate governance, model-routing controls.
4. **Reliability:** HA across regions, queue-backed durability, graceful degradation,
   offline-first clients with conflict-free sync (CRDTs).
5. **Extensibility:** signed plugin marketplace, partner integrations, MCP server registry,
   custom agent SDK for in-house tools.
6. **Cost & performance governance:** model-tier routing, caching, batch processing,
   per-team budgets and dashboards.
7. **Continuous improvement:** offline eval harness, A/B prompt/workflow optimization,
   red-team + safety review pipeline, regression suites on every release.
8. **Assurance:** SLAs, dedicated incident response, customer-facing trust center.

---

*Reference implementation of the visual command hub: [`percival-os.html`](./percival-os.html).*
