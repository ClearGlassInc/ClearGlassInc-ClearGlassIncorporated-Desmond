# ClearGlass Intelligence Graph

The graph is a source-backed, temporal export of the public ClearGlass information architecture.

Runtime: python3 tools/site_intelligence_graph.py crawl

Sources: GitHub repository HTML at an immutable commit; live sitemap.xml; rendered DOM via Playwright when available.

A source failure is recorded. The collector never silently converts a missing source into high confidence.

Analytics: NetworkX PageRank, betweenness centrality, Louvain communities, modularity, and density-based cohesion.

Integrity: each node, edge, and cluster carries a record hash. Each snapshot carries payload_hash and snapshot_hash. Verify with python3 tools/verify_site_graph_chain.py. Tamper self-test: python3 tools/site_intelligence_graph.py self-test.

Temporal query: diff(date_a,date_b)

Versioned snapshots live under data/intelligence-graph/snapshots/ and are indexed by snapshots/index.json.

No live snapshot is committed by hand. A snapshot is valid only when produced by the collector against reachable sources.
