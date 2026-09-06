# ClearGlass Intelligence Platform — Brand & Platform Architecture

> **Status: brand architecture (adopted).** This document defines the naming
> taxonomy and platform structure for the ClearGlass ecosystem. It moves the
> organization beyond ad‑hoc "bot names" to a coherent architecture that scales
> from a handful of agents to hundreds. A name appearing here does **not** mean
> the system is provisioned — provisioned systems live in their own subtrees
> (`sentinel/`, `clearglass-commerce/`, `apps/`) with their own status banners.
>
> **Canonical machine-readable source:** [`data/platform/registry.json`](../data/platform/registry.json),
> enforced by `tools/validate_platform_registry.py` and `tests/test_platform_registry.py`.
> Change the registry first; this document explains it.

---

## 1. Executive Layer

The five platform-tier systems every other name hangs off:

| Platform | Role |
|---|---|
| **ClearGlass Nexus** | Central intelligence and orchestration platform |
| **ClearGlass Command** | Executive operations center |
| **ClearGlass Cortex** | AI reasoning engine |
| **ClearGlass Core** | Platform runtime |
| **ClearGlass Fabric** | Distributed services layer |

## 2. Autonomous Agent Framework

Nine domains, 85 reserved agent codenames. A codename is a *slot* in the
namespace: it may be assigned to an implemented agent, a product line, or held
in reserve. Within a domain, codenames are unique.

| Domain | Codenames |
|---|---|
| **Executive AI** | Executive · Director · Governor · Steward · Prime |
| **Intelligence** | Oracle · Spectra · Prism · Vector · Meridian · Horizon · Atlas · Helix · Pulse · Axiom |
| **Cybersecurity** | Bastion · Citadel · Fortress · Rampart · ShieldCore · LockPoint · GuardianX · IronGate · SentinelOne · BlackMirror |
| **Threat Intelligence** | Recon · Hunter · Watchtower · DeepTrace · Signal · Echo · ShadowNet · RedScope · BlueWatch · ThreatGrid |
| **OSINT** | Pathfinder · Observer · Discovery · Cartographer · Surveyor · Scout · AtlasOS · IntelMap · OpenIntel · TraceNet |
| **Digital Forensics** | Evidence · Ledger · Chronicle · Timeline · Recover · Integrity · Veritas · Provenance · Archive · Chain |
| **AI Automation** | Catalyst · Forge · Reactor · VectorFlow · Assembly · Pipeline · Conductor · Maestro · Architect · Builder |
| **Business Intelligence** | Polaris · Compass · Lighthouse · Navigator · Beacon · MarketPulse · RevenueIQ · GrowthCore · Opportunity · Forecast |
| **Development** | Foundry · Workshop · ForgeWorks · DevCore · CodePilot · StackEngine · Compiler · Runtime · BuilderAI · LaunchPad |

## 3. Enterprise Multi-Agent Hierarchy

Fifteen first-class agents report to ClearGlass Nexus. Each carries a canonical
agent ID under the naming standard (`CGA-<Name>-01` for the prime instance).

```
ClearGlass Nexus
│
├── Cortex      (Reasoning)        CGA-Cortex-01
├── Sentinel    (Cyber Defense)    CGA-Sentinel-01
├── Recon       (OSINT)            CGA-Recon-01
├── Forge       (Automation)       CGA-Forge-01
├── Oracle      (Strategic AI)     CGA-Oracle-01
├── Ledger      (Compliance)       CGA-Ledger-01
├── Beacon      (Monitoring)       CGA-Beacon-01
├── Navigator   (Business)         CGA-Navigator-01
├── Foundry     (Development)      CGA-Foundry-01
├── Pulse       (Telemetry)        CGA-Pulse-01
├── Chronicle   (Knowledge)        CGA-Chronicle-01
├── Catalyst    (Workflow)         CGA-Catalyst-01
├── Vector      (Analytics)        CGA-Vector-01
├── Bastion     (Infrastructure)   CGA-Bastion-01
└── Horizon     (Forecasting)      CGA-Horizon-01
```

Every hierarchy node must resolve to an agent-framework codename, an executive
platform, or a product anchor — the validator enforces this, so a node can't be
invented without also reserving its name.

## 4. Premium Product Family

Product lines take the `ClearGlass <Anchor>` form, and every product anchor
must have a hierarchy node under Nexus (also enforced):

| Product | Domain |
|---|---|
| **ClearGlass Sentinel** | Cybersecurity |
| **ClearGlass Oracle** | AI Decision Intelligence |
| **ClearGlass Forge** | Automation Platform |
| **ClearGlass Vector** | Data Analytics |
| **ClearGlass Chronicle** | Knowledge Management |
| **ClearGlass Recon** | OSINT Suite |
| **ClearGlass Ledger** | Compliance & Audit |
| **ClearGlass Beacon** | Monitoring & Alerting |
| **ClearGlass Pulse** | Infrastructure Observability |
| **ClearGlass Navigator** | Executive Dashboard |
| **ClearGlass Foundry** | Developer Platform |
| **ClearGlass Horizon** | Predictive Intelligence |

## 5. Naming Standard

Every named thing resolves to exactly one tier. Prefixes are reserved and
unique; instance identifiers must match the tier pattern.

| Tier | Prefix | Pattern | Example |
|---|---|---|---|
| Platform | `ClearGlass` | `ClearGlass <Name>` | ClearGlass Nexus |
| AI Engine | `Cortex` | `Cortex-<n>` | Cortex-1 |
| Agent | `CGA` | `CGA-<Name>-<nn>` | CGA-Sentinel-01 |
| Workflow | `Flow` | `Flow-<Name>-<nnn>` | Flow-Incident-001 |
| Knowledge | `Chronicle` | `Chronicle-<Name>` | Chronicle-Alpha |
| Security | `Sentinel` | `Sentinel-<Name>` | Sentinel-Edge |
| Analytics | `Vector` | `Vector-<Name>` | Vector-X |
| Automation | `Forge` | `Forge-<Name>` | Forge-Auto |
| Infrastructure | `Bastion` | `Bastion-<Name>` | Bastion-Cloud |
| Executive | `Oracle` | `Oracle-<Name>` | Oracle-Prime |

### Rules

1. **Registry first.** A new platform, product, agent, or codename is added to
   `data/platform/registry.json` before it is used anywhere else. CI fails if
   the registry breaks the standard.
2. **One tier per name.** If a name could plausibly live in two tiers, the
   registry entry decides.
3. **Instances are numbered.** The prime instance of an agent is `-01`;
   replicas and successors increment. Workflows use three digits.
4. **Existing systems keep their names.** PERCIVAL, AEGIS, ARTEMIS, and the
   commerce OS predate this standard and remain valid legacy names; new systems
   adopt the taxonomy. Where a legacy name collides with a reserved codename
   (e.g. the `sentinel/` stack and the Sentinel product line), the registry's
   product anchor is authoritative for branding.

## 6. How this maps to the repo today

| Registry concept | Existing implementation |
|---|---|
| Sentinel (Cyber Defense) | `sentinel/` keyless, fail-closed agent stack |
| Ledger (Compliance) | commerce OS append-only audit ledger (`clearglass-commerce/control-plane/app/audit.py`) |
| Governor (Executive AI) | commerce OS governance gate (`app/governance.py`) |
| Recon (OSINT) | PERCIVAL agent mesh / OSINT surfaces |
| Beacon / Pulse | `data/control-surface/*` health + metrics feeds |
| Forge / Catalyst | `bots/` + scheduled workflow loops |

## 7. Verifying

```bash
python tools/validate_platform_registry.py          # human-readable report
python tools/validate_platform_registry.py --json   # machine-readable report
python -m pytest tests/test_platform_registry.py -q # CI enforcement
```
