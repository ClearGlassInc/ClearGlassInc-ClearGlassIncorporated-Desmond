# DELOS OS data model, state machine, and repository map

## Repository file tree

This is the additive DELOS application area inside the existing ClearGlass repository. Existing site files, root package scripts, other workflows, and current product routes are intentionally left in place.

~~~text
ClearGlassInc-ClearGlassIncorporated-Desmond/
├── [existing ClearGlass site, assets, agents, CI, Netlify, docs and scripts — preserved]
├── .github/
│   └── workflows/
│       ├── [existing workflows — preserved]
│       └── delos-os-ci.yml
└── delos-os/
    ├── README.md
    ├── package.json
    ├── tsconfig.json
    ├── next.config.ts
    ├── postcss.config.mjs
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   └── globals.css
    ├── lib/
    │   ├── model.ts
    │   ├── scenario.ts
    │   ├── agent-runtime.ts
    │   ├── policy.ts
    │   └── engine.ts
    ├── prisma/
    │   └── schema.prisma
    ├── schemas/
    │   └── persona.schema.json
    ├── tests/
    │   ├── engine.test.ts
    │   └── policy.test.ts
    └── docs/
        ├── ARCHITECTURE.md
        ├── DATA-MODELS.md
        ├── API.md
        ├── GOVERNANCE.md
        └── 30-DAY-PLAN.md
~~~

## Agent state machine

~~~text
READY --start--> RUNNING --pause--> PAUSED --resume--> RUNNING
  |                  |                   |
  |                  +----terminate-----+----> TERMINATED
  |                                      |
  +--------------------------------------+
RUNNING --72h reached--> COMPLETED

READY / RUNNING / PAUSED --emergency stop--> STOPPED (global freeze)
STOPPED --normal commands--> DENIED
TERMINATED / COMPLETED --advance or inject--> DENIED
~~~

Agent lifecycle within a running scenario:

~~~text
STANDBY -> MONITORING -> ACTIVE
                         |
                         +-- high-risk proposal --> AWAITING_APPROVAL
                                                     | approve -> ACTIVE
                                                     | reject  -> MONITORING
Any status + global stop -> FROZEN
~~~

The prototype executes state transitions deterministically. The personas produce synthetic decision proposals; they do not invoke external tools. Model-backed reasoning can only be added behind a server-side policy gateway and strict output validation.

## World state data model

A WorldState aggregate contains the canonical run record plus current metrics and append-only arrays. The current local prototype persists this aggregate in browser storage; the production design stores normalized records plus a transactionally versioned state document in PostgreSQL.

~~~json
{
  "runId": "run-glassfall-baseline",
  "scenarioId": "OP-GLASSFALL-72",
  "scenarioName": "Operation Glassfall",
  "branchName": "GLASSFALL-BASELINE",
  "status": "running",
  "safetyStop": false,
  "simHour": 6,
  "threatLevel": 39,
  "supplierCapacity": 78,
  "reputation": 94,
  "liquidity": 88,
  "integrity": 100,
  "missionProgress": 8,
  "decisionCount": 6,
  "lastUpdatedAt": "ISO-8601 timestamp",
  "agents": [],
  "events": [],
  "agentDecisions": [],
  "approvals": [],
  "audit": [],
  "snapshots": [],
  "checkpoints": []
}
~~~

World metrics are bounded to 0–100. The simulated-hour clock is an integer from 0 to 72. Changes are made through validated engine commands rather than arbitrary client mutations. In the production service, each command also supplies expectedStateVersion and an idempotency key.

## Persona schema

Personas are synthetic by construction. The schema at schemas/persona.schema.json requires:
- a clearly synthetic identity marker and display name;
- a role, mission objective, personality summary, expertise, and scoped relationships;
- allow-listed permissions and tool names;
- a declared knowledge boundary and memory scope;
- a 1–5 persona risk class and per-action approval requirements.

The current scenario uses seven personas: Incident Commander, Security Analyst, Communications Director, Finance Officer, Threat Actor Simulator, Board Advisor, and Autonomous Response Agent. The threat actor is constrained to non-executable scenario pressure and synthetic indicators. Real-person identities, credential material, live-target details, and unapproved tools are not valid persona inputs.

## Event record

~~~json
{
  "id": "evt-unique-id",
  "recordedAt": "ISO-8601 timestamp",
  "simHour": 6,
  "category": "incident",
  "title": "Critical supplier service unavailable",
  "detail": "Synthetic supplier endpoint reports a scenario outage.",
  "severity": 79,
  "riskScore": 72,
  "source": "Scenario Director"
}
~~~

Event ordering uses a monotonically increasing per-run sequence in the production database. The client prototype uses IDs and simulated hours for timeline replay. User-generated text is data, not executable instructions.

## Agent decision record

Every proposal carries:
- UTC timestamp, source event ID and simulated hour;
- persona/agent ID, intent, proposed action and rationale;
- input summary (synthetic event ID/category/metrics) and output summary;
- tool name, explicitly null in the MVP because no tools are invoked;
- bounded risk score, approval state, and externalSideEffect=false.

Raw hidden reasoning is never logged or exported. Production systems should log concise rationale and evidence references, not chain-of-thought or sensitive prompt payloads.

## Audit record and integrity

Audit events identify timestamp, actor, action, detail, risk score, and approval status. Important command types include world.initialized, simulation.started, event.injected, agent.proposals.generated, approval.requested, approval.accepted, approval.rejected, snapshot.created, branch.forked, checkpoint.restored, simulation.terminated, and emergency.stop.

The local browser list is not an immutable ledger. In production, append audit events in the same transaction as the authorized state transition, include previousHash and eventHash, write with a server-only database role, monitor access independently, and establish retention, backup, and legal-hold rules. Avoid putting secrets or personal data into audit details.

## UI component plan

- Application shell: navigation, active world, environment label, and operator state.
- Command overview: run status, clock, risk/capacity KPIs, topology schematic, objectives, persona status board, recent events, and lifecycle controls.
- World Forge: scenario rules, type, constraints, success/failure conditions, revision/snapshot entry points.
- Persona Engine: persona roster, mission, expertise, permissions, knowledge boundary, memory scope, and approvals.
- Narrative Director: canonical event timeline and allow-listed synthetic event injection.
- Governance Core: approval queue, decision history, operator activity, emergency stop.
- Intelligence: persona proposals, risk scoring, executive recommendations, KPI report, branch checkpoint comparison, and Markdown/JSON downloads.

The interface uses a deep navy palette, luminous cyan accent, restrained amber/red risk states, a compact mono label system, responsive layouts, and reduced-motion-aware entrance animation. Tailwind is installed for utility classes; core console panels retain explicit design-token CSS to preserve their intended visual precision.

## Production persistence invariants

1. A run references one immutable world revision.
2. Events, decisions, approvals, and audit entries have sequence order and cannot be silently rewritten.
3. Forking creates a child run anchored to a parent snapshot; it must not overwrite another branch.
4. Approval is bound to actor, tenant, run, state version, action digest, scope, and expiry.
5. Emergency stop is atomic, dominates all other commands, freezes workers, and retains current state.
6. Reads and writes are tenant-scoped. Client-provided organization IDs never establish authorization.
7. Model output is treated as untrusted proposal data; schema validation and policy evaluation occur server-side before any transition.
