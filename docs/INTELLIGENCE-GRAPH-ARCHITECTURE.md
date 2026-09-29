# Intelligence Graph — Architecture Assessment and Roadmap

> **Status: assessment (2026-09-29).** Sections A and B describe what exists
> and were measured from `data/site-index.json` by the code in
> `station-chat.js`. Sections C–J describe the **target** design. None of it is
> provisioned. The benchmark in §K compares design concepts, not measured
> performance.

## Summary

The Intelligence Graph in Sentinel Core is a **site map rendered as a graph**:
167 web pages, 861 related links, 12 editorial clusters. That's all it is. It
has no threat actors, no infrastructure, no sources, no timestamps and no
evidence. The redesign in this change makes it an honest structural analysis
surface. Every number on screen comes from that graph, and the panels say so.

Asking it to behave like OpenCTI or Maltego is a category error. Those tools
rank relationships about the world, supported by evidence. This one ranks
relationships between marketing pages. The roadmap below gets you to a real
intelligence graph. Its first recommendation is to **not build most of it**.

---

## A. Current state assessment

### What is on disk

| Component | Path | State |
|---|---|---|
| Console graph (redesigned here) | `station-chat.js`, "Intelligence Graph" section | Live on every mapped page. Reads `data/site-index.json` |
| Graph source | `tools/internal_links.py` → `data/site-index.json` | Generated; pillar-and-cluster information architecture |
| Evidence-backed collector | `tools/site_intelligence_graph.py` (1,426 lines) | Written: GitHub HTML + sitemap + optional Playwright crawl, NetworkX analytics, per-record hashes, snapshot chain |
| Collector output | `data/intelligence-graph/` | **Empty except README.** The collector has never produced a committed snapshot |
| Standalone page | `intelligence-graph.html`, `assets/intelligence-graph/` | Separate implementation, 23-line script |

### Measured structure (computed by the redesigned console, same on every load)

| Metric | Value | Reading |
|---|---|---|
| Entities | 167 | Pages |
| Directed links | 861 | `related` entries |
| Undirected relationships | 782 | |
| Reciprocal relationships | 79 (10%) | 90% of relationships run one way |
| Density | 5.6% | 9.4 relationships per entity |
| Degree centralisation | 0.10 | No single dominant hub; flat |
| Components | 1 | Everything is connected |
| Reach from home | 100% | Every page reachable from `index.html` |
| Mean shortest path / diameter | 3.18 / 6 hops | |
| Modularity of declared clusters | 0.701 | Clusters are real communities, not labels |
| Cut points (Tarjan) | 3 | Authority Network, ClearPulse, Web Design & Development |
| Top PageRank | Self-Evolving Platform, Agent Mesh, BLUEDESK | |
| Top betweenness | Legal Infrastructure, Cyber Defense Console, Authority Network | |

The feed reports 44 observations: 3 cut points (medium), 34 pages more than
three links from home (low), 3 bridges and 4 forecast links (info). No page
has zero or one inbound link.

### What the redesign delivers (this change)

- Command-centre layout: Sentinel Core readout (6 KPIs), Collection panel
  (coverage, cluster streams, priority targets, directory), canvas, Analysis
  panel (entity profile, 12×12 correlation matrix, link forecast, model
  registry), and a timestamped observation feed.
- Canvas: range rings and bearings, radar sweep, cluster boundaries at
  1.5 standard deviations, PageRank as an influence heatmap, corroboration
  rings, red dashed rings on cut points, severity markers, Adamic–Adar
  forecast links, in/out link routing, and a 2-hop neighbourhood on selection.
- Propagation playback: a hop slider and **Trace** that replay how far a
  change on the selected page reaches, link by link.
- Seven models, all run on the device in about 30–140 ms: PageRank, Brandes
  betweenness, Tarjan cut points, reciprocity, modularity, Adamic–Adar and a
  seeded radial layout.
- Mobile: one scrolling column: KPIs, canvas, profile, feed, collection.

### What it deliberately does not show

These requested elements are left out because showing them would mean making
data up:

| Requested | Why it is absent | What would make it real |
|---|---|---|
| Threat matrix, threat relationships | No threat data exists in the index | A STIX feed (§C, §G) |
| Geospatial overlay | No entity has a location | `located-at` relationships from sourced records |
| Temporal layer / last observed | The index carries no timestamps | Add git `lastmod` (already computed by `tools/generate_search_assets.py`) to `site-index.json`, or run the collector |
| Probability forecasts | No outcome history to calibrate against | Labelled outcomes over time. Until then, call it a heuristic |
| Source confidence per record | Only one source (the generator) | The collector's multi-source corroboration |

Correlation matrix, link forecast and "risk" are shown under honest names:
link counts between clusters, Adamic–Adar, and **exposure**, which is
structural fragility.

---

## B. Architectural weaknesses

1. **It is not an intelligence graph.** The node type is "page" and the edge
   type is "related". There is no ontology, so none of the analyses in the
   brief (threat, procurement, financial, influence) has anything to run on.
2. **Two graph implementations, and neither has provenance.** The console
   reads the generator output. The provenance-grade collector exists but has
   never shipped a snapshot. Close one path; don't add a third.
3. **Edges are 90% one-way.** Only 10% of relationships are reciprocated.
   For a site that means weak return paths. For an intelligence graph the
   same measure would mean uncorroborated claims.
4. **No time dimension.** Nothing is timestamped, so change detection,
   decay, "last observed" and every predictive feature are impossible.
5. **Scale ceiling.** SVG in the DOM handles about 2–5k nodes. Brandes is
   O(V·E). Both are fine at 167 nodes and fail long before 1M.
6. **Scale is the wrong worry.** No data source in this repository could
   produce 1M entities. Designing for 1M before there are 1,000 sourced
   entities is waste.
7. **Blind spot: who is the user?** ClearGlass sells advisory engagements. An
   analyst-grade CTI platform is a product for a SOC, and building one isn't
   what the business model calls for. The graph pays off when it helps an
   engagement: a client's AI-governance and cyber exposure map, delivered as
   evidence.

---

## C. Recommended graph schema

A labelled property graph aligned to **STIX 2.1** (OASIS). Adopting the
standard buys interoperability with OpenCTI, MISP and ATT&CK for free.

```
(:Entity {id, type, name, aliases[], created, modified, first_seen, last_seen,
          confidence 0-100, tlp, marking, record_hash})
  types: organization, individual (role only), infrastructure, system,
         software, vulnerability, attack_pattern, threat_actor, campaign,
         indicator, regulation, contract, location, page (the site graph)

(:Source {id, name, kind: osint|client|feed|internal, reliability A-F})
(:Evidence {id, uri, captured_at, sha256, content_type, collector, custody[]})
(:Observation {id, observed_at, value, credibility 1-6})

(a)-[:REL {type, first_seen, last_seen, weight, confidence, evidence_ids[]}]->(b)
(:Observation)-[:SUPPORTS]->(:REL | :Entity)
(:Evidence)-[:DERIVED_FROM]->(:Source)
```

Rules:

- **Every edge must cite at least one evidence record**, or it is stored as a
  `hypothesis` and drawn dashed. That is the forecast-link convention this
  change already uses.
- **Time is on the relationship**, not only the node: `first_seen`,
  `last_seen`, plus `valid_from` / `valid_to` for facts with a legal term,
  such as contracts and directorships.
- **Geography** goes through `located-at` edges to `location` entities that
  carry coordinates and a precision field. It never goes on a free-text node
  attribute.

## D. Intelligence ontology

| Domain | Core relationships (STIX name where one exists) |
|---|---|
| Threat / cyber | `uses`, `targets`, `attributed-to`, `indicates`, `exploits`, `mitigates` |
| Infrastructure | `depends-on`, `hosts`, `resolves-to`, `communicates-with` |
| Corporate / competitive | `subsidiary-of`, `supplier-of`, `competitor-of`, `acquired` |
| Procurement | `awarded`, `bid-on`, `issued-by` (tender → buyer) |
| Financial | `paid`, `funded-by`, `invoiced` (from verified processor events only) |
| AI governance | `deploys-model`, `governed-by`, `assessed-under` (e.g. an AI-risk framework) |
| Legal / compliance | `subject-to`, `violates`, `complies-with` |
| Entity resolution | `same-as {method, score}`. It merges on read and never deletes |
| Influence | `mentions`, `amplifies`, derived only from sourced observations |

**Multi-hop paths** are queries over these types, for example
`vendor -depends-on-> system -exploits<- vulnerability -uses<- actor`. Each hop
multiplies confidence (see H), so long chains lose certainty visibly.

## E. Advanced UI/UX concepts

The redesign already implements the shell. Next steps, in order of value:

1. **Evidence drawer.** Selecting an edge opens its evidence: source,
   capture time, hash, excerpt. Without this every score is a claim.
2. **Time slider on real timestamps.** It replaces hop playback when
   `last_seen` exists.
3. **Layer registry.** Each layer names the query and model that drew it.
   The Analytic Models panel does this now; extend it to every overlay.
4. **WebGL renderer above about 3k nodes.** Keep SVG below that for
   accessibility. Sigma.js and Cosmograph are the usual choices.
5. **Contradiction view.** Two edges with the same endpoints and opposite
   claims get flagged side by side, never averaged.
6. **Brief export.** The selected subgraph plus its evidence becomes a signed
   PDF brief: the deliverable a client pays for.

## F. Security and governance model

Reuse what the repository already enforces. Don't invent a parallel scheme.

- **Audit.** Every write to the graph (ingest, merge, analyst note, score
  change) is an RFED record (`bots/rfed_audit_bot.py`): Request → Facts →
  Evidence → Decision, SHA-256 chained. `modify_audit_log` is already blocked.
- **Gating.** Ingest from a new source, entity merges and any export of
  personal data are high-risk actions under the existing governance scoring
  (read-only analysis → draft → human approval → execution).
- **Chain of custody.** Evidence is content-addressed (`sha256`). The custody
  list is append-only: who captured, transformed or viewed it, and when.
- **Handling.** TLP 2.0 marking on every node and edge. Filters apply before
  render and before any model prompt.
- **Privacy.** Individuals appear by role unless the engagement's legal basis
  covers naming them (Ontario / PIPEDA context). No scraping of private
  individuals.
- **Injection defence.** Text captured from sources is untrusted. It never
  reaches a model as instructions (the RFED injection-marker gate already
  exists).

## G. AI agent integration

```
OBSERVE → INGEST → CORRELATE → ANALYZE → VERIFY → SCORE → PREDICT → RECOMMEND → MONITOR → AUDIT
 collectors  normalise  entity      graph      evidence  H-model  link-pred  draft brief  watchlists  RFED chain
 (connectors) to STIX   resolution  algorithms check     scores   (flagged)  → human      diff alerts every step
```

- Agents **draft**; humans approve anything published, sent or merged. That
  is the same invariant as the commerce OS.
- **VERIFY is a gate.** A model-generated relationship with no evidence ID is
  stored as `hypothesis`, confidence at most 30, and drawn dashed.
- Sentinel's existing `/sentinel/ask` becomes the RECOMMEND step. Its answers
  cite node and evidence IDs, or it declines.
- **MONITOR** is a scheduled diff of snapshots (`diff(date_a, date_b)` already
  exists in the collector). It will need the Actions runner problem fixed
  first; see `CLAUDE.md`.

## H. Risk scoring framework

Separate the three things most dashboards conflate:

| Quantity | Definition | Scale |
|---|---|---|
| **Confidence** in a record | Admiralty Code: source reliability A–F × information credibility 1–6, mapped to 0–100; corroboration by an independent source raises it, age decays it | 0–100 |
| **Impact** of an entity | Business criticality (analyst-set, cited) × structural centrality (PageRank, betweenness) | 0–100 |
| **Exposure** | Evidence-backed weaknesses (vulnerabilities, single points of failure, cut points) | 0–100 |

`risk = impact × exposure × confidence / 10⁴`, reported with its three inputs,
never as a bare number. Propagation along `depends-on` multiplies by edge
confidence at each hop and stops below 10.

Today's console uses the structural half only, and labels it that way:
importance is PageRank, bridge is betweenness, exposure is `100 / (1 + in²/2)`,
corroboration is the reciprocal share, and
`priority = 0.45·importance + 0.35·bridge + 0.2·exposure`.

## I. Technical architecture

```
 Sources                    Ingest                 Store                    Analyse               Present
 ───────                    ──────                 ─────                    ───────               ───────
 OSINT feeds  ──┐                                   ┌─ Graph DB (Neo4j or   ┌─ GDS / MAGE:        ┌─ Sentinel console
 Client data  ──┼─► connectors ─► STIX normaliser ─►│  Memgraph)            │  PageRank, Louvain, │  (this redesign)
 ATT&CK/MISP  ──┤   (queued)      + entity          ├─ Evidence store       │  betweenness,       ├─ Brief export (PDF)
 Site crawl   ──┘                 resolution        │  (object storage,     │  link prediction    └─ Analyst API
 (collector)                        │               │   sha256-addressed)   └─ Scheduled diffs
                                    ▼               └─ RFED ledger (hash chain)
                              Governance gate ───────────────── approvals / audit ──────────────────┘
```

Near-term (months 1–3) it stays static: the collector writes versioned JSON
snapshots that the console reads. A database is justified only when there are
more than about 50k sourced records or a need for concurrent analysts.

## J. 12-month implementation roadmap

| Phase | Months | Deliverable | Exit test |
|---|---|---|---|
| 0. Truth | 1 | Run `tools/site_intelligence_graph.py crawl`; commit the first verified snapshot; console reads it; add `lastmod` to nodes | `verify-chain` passes; console shows real "last observed" |
| 1. One graph | 1–2 | Retire the duplicate `intelligence-graph.html` renderer or point it at the same snapshot | One code path, one data file |
| 2. Schema | 2–3 | STIX-aligned entity/edge/evidence schema; evidence drawer | Every edge in the UI opens its evidence |
| 3. Adopt | 3–5 | Deploy **OpenCTI** for threat data; import ATT&CK; Sentinel reads it through its API | ATT&CK techniques are browsable in the console |
| 4. Client graph | 4–6 | Engagement template: a client's systems, vendors, AI models and regulations as a graph with cited evidence | One paid engagement delivered with a graph brief |
| 5. Scale | 6–8 | WebGL renderer; graph DB if the record count justifies it | 10k-node graph interactive on a mid-range phone |
| 6. Monitor | 8–10 | Scheduled snapshot diffs → watchlist alerts (needs Actions runners restored) | An alert fires on a real, verified change |
| 7. Predict | 10–12 | Link prediction and emerging-risk scoring, calibrated against logged outcomes | Reported precision/recall on held-out history, or the feature stays labelled "heuristic" |

## K. Benchmark

| System | Its core idea | What ClearGlass should take | Gap today |
|---|---|---|---|
| Neo4j Enterprise | Property graph DB, Cypher, Graph Data Science library, RBAC | GDS algorithms server-side when scale demands | No database; algorithms run in the browser |
| Palantir-style ontology | Typed objects, typed links and governed **actions** over them | Actions tied to approvals (already the repo's model) | No object types beyond "page" |
| MITRE ATT&CK | Shared vocabulary of adversary tactics and techniques | Import it; don't reinvent it | Not present |
| OpenCTI | Open-source, STIX 2.1-native CTI platform with connectors | **Adopt** as the threat-data store | Not deployed |
| Maltego | Investigative link analysis driven by source "transforms" | Transform-style connectors with provenance | No connectors |
| GraphXR | Browser-based visual graph exploration | Layer and filter ergonomics | Partly met by this redesign |
| Linkurious | Investigation UI and alerting on top of a graph DB | Saved queries → alerts | No alerting |
| Memgraph | In-memory, Cypher-compatible, streaming ingest | Option if real-time feeds arrive | Not needed yet |

**Bottom line.** The redesign is best-in-class for the data it has. To earn
the name "intelligence platform", the next step isn't more visuals. It is
Phase 0: one verified, timestamped, evidence-carrying snapshot.
