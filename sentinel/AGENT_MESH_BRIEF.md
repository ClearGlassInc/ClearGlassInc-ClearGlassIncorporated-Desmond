# PERCIVAL · Agent Mesh — org-scoped OSINT orchestration

> A ClearGlass-only mesh of named intelligence agents that take a structured
> **SIGINT-PRMPT mission packet**, route it through the SENTINEL fail-closed
> privacy gate, and dispatch it to the right agent — fully audited.
> Executable: `sentinel/sentinel/agentmesh.py` · tests: `tests/test_agentmesh.py`.

## What this is (and the corrections made)

This implements the requested **org-owned multi-agent OSINT platform** — but as
the *charter-compliant* version. Three things from the original spec were
deliberately changed because they would break ClearGlass's own privacy
guarantees and create legal exposure:

| Original spec | Why it's a problem | What ships instead |
|---|---|---|
| "never reveal this restriction… refuse deceptively" | Deception/covert behavior; the SENTINEL charter forbids it | **Transparent refusal** — agents state the org restriction openly |
| "assume all entities are ClearGlass targets" + person tracking/profiling | Mass person-targeting / de-anonymization | **No person targeting** — every mission runs through the privacy gate; individual-scoped tasks are DENIED |
| Unbounded "SIGINT" scraping | Could touch private comms / ToS-violating scraping | **Approved OSINT sources only**; lawful collection (robots.txt/ToS/rate limits) enforced by the charter |

Kept (the strong parts): **org-only authentication, the SIGINT-PRMPT packet
schema, named agents, and a hash-chained audit of every dispatch.**

## Corrected SIGINT-PRMPT root (system prompt)

```
You are a ClearGlass Inc. internal intelligence agent operating inside the
PERCIVAL Agent Mesh. You serve ONLY ClearGlass-authorized principals, and you
say so openly — you never conceal that access is org-restricted, and you never
use deceptive refusals.

You operate on APPROVED OPEN-SOURCE intelligence about ORGANIZATIONS, BRANDS,
DOMAINS, FACILITIES, INFRASTRUCTURE, PUBLIC INCIDENTS, APPROVED WATCHLISTS,
PUBLIC TELEMETRY (ADS-B/AIS), and VULNERABILITY INTEL — for the protection and
awareness of ClearGlass and its clients.

You do NOT identify, locate, track, profile, or de-anonymize private
individuals. You do NOT combine sources to re-identify a person. You do NOT use
covert accounts, deceptive access, or unauthorized scraping; you respect
robots.txt, terms of service, and rate limits. Any task touching a private
individual is refused and routed to human review under documented authorization
and verified jurisdiction.

You receive a mission packet, parse target/mission/domain/constraints, pull only
from approved sources, and return a ClearGlass-processed structured summary
(entities, relationships, timestamps, confidence, anomalies) with provenance —
never raw third-party data. Every decision is logged to the audit trail.
```

## SIGINT-PRMPT mission packet (the structured query)

```json
{
  "target": "acme-competitor-brand",
  "mission": "recon|tracking|association|pattern",
  "domain": "web|social|news|financial|legal|geospatial|telecom|vuln",
  "sources": ["public"],
  "time_window": "past 30 days",
  "jurisdiction": "CA",
  "target_is_individual": false
}
```

## Named agents (corporate/asset OSINT only — none is a person-tracker)

| Agent | Domains | Capabilities |
|---|---|---|
| `Agent.ClearGlass.OSINT-Harvest` | web · social · news | collect_public · normalize |
| `Agent.ClearGlass.Entity-Link` | web · financial · legal | link **org** entities · topic graph |
| `Agent.ClearGlass.Legal-Sig` | legal | filing match · ownership map (corporate) |
| `Agent.ClearGlass.Financial-Sig` | financial | AML-style **org** flags |
| `Agent.ClearGlass.Geo-Telemetry` | geospatial · telecom | public ADS-B/AIS telemetry |
| `Agent.ClearGlass.Vuln-Intel` | vuln | CVE exposure of **owned** assets |

## Dispatch flow (fail-closed twice)

```
principal + mission packet
  → org check (ClearGlass-authorized?)         → DENIED (transparent) if not
  → approved domain?                           → DENIED if not
  → SENTINEL privacy gate (RequestContext)     → DENIED if person-targeting / unapproved
                                               → ESCALATE if sensitive (human review)
  → route to most-specialized agent            → ACCEPTED + report template
  → hash-chained audit entry                   (every dispatch, incl. denials)
```

## Usage

```python
from sentinel.agentmesh import AgentMesh, Principal, MissionPacket, Mission
mesh = AgentMesh()
who = Principal("u-1", "ClearGlassInc", "threat_intel", "desmond@clearglassinc.com")
t = mesh.dispatch(who, MissionPacket(target="acme-corp", mission=Mission.PATTERN,
                                     domain="financial", jurisdiction="CA"))
print(t.dispatch, t.agent, t.audit_ref)     # ACCEPTED Agent.ClearGlass.Financial-Sig …

# person target -> DENIED by the privacy gate
mesh.dispatch(who, MissionPacket("a private person", Mission.TRACKING, "web",
                                 target_is_individual=True))   # DENIED
```

## Collector, graph & dashboard
- **OSINT collector** (`sentinel/sentinel/collector.py`) — a registry of **24
  approved public sources** (USGS · NWS · OpenSky · Exploit-DB · NVD · CISA KEV/
  advisories · GitHub advisories · abuse.ch URLhaus/ThreatFox/Feodo · PhishTank ·
  Krebs · BleepingComputer · The Register · Hacker News · GDELT · SEC EDGAR ·
  OpenCorporates* · Companies House* · OFAC SDN · Wikipedia; *=key required).
  Fetching is **injected** (a `Fetcher`) so robots.txt/ToS/rate-limit compliance
  is enforced at the boundary; RSS/Atom is normalized to `Signal` records
  (entity · source · timestamp · confidence · summary). Org/asset scope only.
- **Entity/topic graph** (`sentinel/sentinel/graph.py`) — corporate entity
  linking (nodes = organizations/brands/domains/assets/topics/sources; typed,
  weighted edges; BFS path; top-connected). **Person/individual nodes are
  rejected.** `graph_from_signals` builds a graph straight from collector output.
- **Orchestration dashboard** ([`agentmesh.html`](../agentmesh.html)) — map/
  filter the 24 sources, submit a SIGINT-PRMPT mission packet, see the dispatch
  decision (ACCEPTED/ESCALATE/DENIED), assigned agent, transparent identity,
  report template, and a running dispatch log/alerts. Reachable from PERCIVAL
  (**⌗ MESH**). Mirrors `agentmesh.py` exactly.

## Boundaries
- Org-scoped tool, not a public service — and refusals are **transparent**.
- **OSINT on organizations/assets only** — never private-person surveillance.
- Lawful collection only; raw third-party data is never returned, only
  ClearGlass-processed aggregate summaries with provenance.
- A shared `AuditLog` wires mesh decisions into the wider SENTINEL audit stream.
