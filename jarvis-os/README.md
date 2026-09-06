# JARVIS OS — Reference Implementation Package

Working artifacts that turn the [`JARVIS_OS_BLUEPRINT.md`](../JARVIS_OS_BLUEPRINT.md)
architecture into something runnable and inspectable.

| Artifact | What it is |
|---|---|
| [`../jarvis-os.html`](../jarvis-os.html) | **Live command HUD** — the UI/UX concept as a real interactive page: system-health ring, KPI dashboard, daily briefing, agent-swarm activity stream with approval ladder, kill switch, command palette (`⌘K`), and voice control. |
| [`system-prompt.md`](./system-prompt.md) | The **AI-core system prompt** — cached preamble for the supervisor agent. |
| [`agent-config.json`](./agent-config.json) | **Claude Agent SDK config** — supervisor + 4 specialist agents, model tiers, risk ladder, memory tiers, guardrails. |
| [`connectors/`](./connectors) | **MCP connector manifests** — each tool declares a risk class, scopes, reversibility, and dry-run support so the policy layer can gate it. |

## How the pieces fit

```
jarvis-os.html  ──visualizes──►  the running system
        │
agent-config.json  ──configures──►  supervisor + Researcher/Executor/Monitor/Reporter
        │                                   │
system-prompt.md  ──governs behavior──►  every agent
        │                                   │
connectors/*.json  ──expose tools──►  gated by GREEN / AMBER / RED risk ladder
        │
   POLICY · APPROVAL · AUDIT · VAULT  (every action passes through)
```

## The risk ladder (enforced everywhere)

| Class | Behavior | Examples |
|---|---|---|
| **GREEN** | auto-execute | read, search, summarize, draft, analyze, dry-run |
| **AMBER** | one-tap approval | send email, modify records, run code, schedule, spend, change perms |
| **RED** | typed-phrase confirmation | delete data, identity/security changes, bulk external actions |

Every tool in every connector manifest is tagged with one of these. The Operator
is always in command; nothing AMBER/RED runs unattended.

## Connectors included

- [`gmail.json`](./connectors/gmail.json) — inbox triage, draft (GREEN), send (AMBER), bulk delete (RED)
- [`security-watch.json`](./connectors/security-watch.json) — monitoring + incident timelines (GREEN), quarantine (AMBER), force re-auth (RED)
- [`code-sandbox.json`](./connectors/code-sandbox.json) — generate + dry-run (GREEN), sandboxed execute (AMBER)
- [`vault-broker.json`](./connectors/vault-broker.json) — secrets by handle; values injected at egress only, never seen by the model
- [`_manifest.schema.json`](./connectors/_manifest.schema.json) — schema all manifests validate against

> **Try the HUD:** open `jarvis-os.html` and press `⌘K` (or `Ctrl+K`) — type
> `brief me`, `system status`, or `automate customer emails`. Tap the orb to talk.

*ClearGlass Inc. — Clarity Is Power.*
