"""Tests for the OSINT collector + entity/topic graph."""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sentinel.collector import (
    APPROVED_SOURCES,
    Collector,
    CollectorError,
    parse_feed,
    sources_by_domain,
)
from sentinel.graph import EntityGraph, GraphError, Node, graph_from_signals

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Sec News</title>
<item><title>Acme Corp discloses breach</title><link>https://news/1</link>
<pubDate>Wed, 04 Jun 2026 10:00:00 +0000</pubDate>
<description>Acme Corp confirmed a data incident.</description></item>
<item><title>Unrelated outage</title><link>https://news/2</link>
<pubDate>Wed, 04 Jun 2026 09:00:00 +0000</pubDate>
<description>A cloud provider had downtime.</description></item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Acme advisory CVE-2026-1</title>
<link href="https://adv/1"/><updated>2026-06-04T10:00:00Z</updated>
<summary>Affects Acme product line.</summary></entry></feed>"""


class FakeFetcher:
    def __init__(self, text): self.text = text
    def get(self, url, *, key=None): return self.text


# ---- collector -------------------------------------------------------------

def test_registry_has_20_plus_sources():
    assert len(APPROVED_SOURCES) >= 20
    # sanity: known feeds present
    assert "exploit_db" in APPROVED_SOURCES and "krebs" in APPROVED_SOURCES


def test_parse_rss_relevance_confidence():
    sigs = parse_feed(RSS, source_name="Sec News", entity="Acme Corp")
    assert len(sigs) == 2
    rel = [s for s in sigs if "Acme" in s.title][0]
    irrel = [s for s in sigs if "Acme" not in s.title][0]
    assert rel.confidence > irrel.confidence
    assert rel.url == "https://news/1"
    assert rel.published_utc.startswith("2026-06-04")


def test_parse_atom_feed():
    sigs = parse_feed(ATOM, source_name="Advisories", entity="Acme")
    assert len(sigs) == 1 and sigs[0].url == "https://adv/1"


def test_collector_rejects_unapproved_source():
    c = Collector(FakeFetcher(RSS))
    with pytest.raises(CollectorError, match="not an approved"):
        c.collect("darkweb_market", "Acme")


def test_collector_requires_key_when_needed():
    c = Collector(FakeFetcher(RSS))
    with pytest.raises(CollectorError, match="requires an API key"):
        c.collect("opencorporates", "Acme")            # needs_key=True


def test_collector_collects_rss_source():
    c = Collector(FakeFetcher(RSS))
    sigs = c.collect("krebs", "Acme Corp")
    assert sigs and sigs[0].source == "Krebs on Security"


def test_invalid_xml_raises():
    with pytest.raises(CollectorError, match="not valid XML"):
        parse_feed("<not-xml", source_name="x", entity="y")


def test_sources_by_domain_groups():
    grouped = sources_by_domain()
    assert "vuln" in grouped and "news" in grouped


# ---- graph -----------------------------------------------------------------

def test_graph_rejects_person_nodes():
    g = EntityGraph()
    with pytest.raises(GraphError, match="not permitted"):
        g.add_node(Node("p1", "person", "someone"))
    with pytest.raises(GraphError):
        g.add_node(Node("p2", "individual"))


def test_graph_add_and_path():
    g = EntityGraph()
    for nid in ("acme", "beta", "gamma"):
        g.add_node(Node(nid, "organization", nid))
    g.add_edge("acme", "beta", "supplier", 0.8)
    g.add_edge("beta", "gamma", "subsidiary", 0.9)
    assert g.path("acme", "gamma") == ["acme", "beta", "gamma"]
    assert g.path("acme", "acme") == ["acme"]
    g.add_node(Node("lonely", "domain"))
    assert g.path("acme", "lonely") is None


def test_graph_edge_requires_nodes():
    g = EntityGraph()
    g.add_node(Node("a", "organization"))
    with pytest.raises(GraphError, match="endpoints must be added"):
        g.add_edge("a", "missing", "rel")


def test_top_connected_and_to_dict():
    g = EntityGraph()
    for nid in ("hub", "a", "b", "c"):
        g.add_node(Node(nid, "organization"))
    for leaf in ("a", "b", "c"):
        g.add_edge("hub", leaf, "linked", 0.7)
    assert g.top_connected(1)[0][0] == "hub"
    d = g.to_dict()
    assert len(d["nodes"]) == 4 and len(d["edges"]) == 3   # dedup undirected


def test_graph_from_signals_links_sources():
    c = Collector(FakeFetcher(RSS))
    sigs = c.collect("krebs", "Acme Corp")
    g = graph_from_signals("Acme Corp", sigs, topics=["data breach"])
    d = g.to_dict()
    ids = {n["id"] for n in d["nodes"]}
    assert "Acme Corp" in ids
    assert any(i.startswith("src:") for i in ids)
    assert "topic:data breach" in ids
