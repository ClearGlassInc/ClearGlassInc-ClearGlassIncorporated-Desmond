from __future__ import annotations

from pathlib import Path

from tools import authority_network_ci as authority


def test_every_indexable_sitemap_page_is_registered() -> None:
    sitemap_pages, _provenance = authority.discover_sitemap_pages()
    assert sitemap_pages == set(authority.PAGES)
    assert authority.validate() == []


def test_supplemental_pages_have_stable_pillars_and_curated_bridges() -> None:
    for page, (_title, _description, cid) in authority.SUPPLEMENTAL_PAGES.items():
        targets, ctas, pillar = authority.related_targets(page)
        assert authority.cluster_of(page) == cid
        assert pillar == authority.legacy.CLUSTERS[cid]["pillar"]
        assert pillar in targets or page == "authority-network.html"
        assert 1 <= len(targets) <= 16
        assert len(ctas) == 2
        assert len(targets) == len(set(targets))
        assert page not in targets


def test_public_discovery_surfaces_expose_every_registered_page() -> None:
    records = authority.native_link_records()
    grid_targets = {
        record.target
        for record in records
        if record.source == "authority-network.html"
    }
    assert set(authority.legacy.PAGES) - {"authority-network.html"} <= grid_targets

    edges = authority.graph_edges()
    for page, (_title, _description, cid) in authority.SUPPLEMENTAL_PAGES.items():
        pillar = authority.legacy.CLUSTERS[cid]["pillar"]
        assert page in edges[pillar]


def test_graph_has_no_orphans_and_reaches_conversion() -> None:
    errors, metrics = authority.analysis_errors()
    assert errors == []
    assert metrics["minimum_inbound"] >= 1
    assert metrics["maximum_crawl_depth"] <= authority.MAX_CRAWL_DEPTH


def test_legacy_blocks_remain_byte_stable() -> None:
    assert authority.block_errors() == []


def test_authority_grid_uses_descriptive_anchors() -> None:
    records = [
        record
        for record in authority.native_link_records()
        if record.source == "authority-network.html"
    ]
    assert records
    assert all(
        record.anchor.strip().casefold() not in authority.GENERIC_ANCHORS
        for record in records
    )
    assert all(record.anchor.strip() for record in records)


def test_authority_fingerprint_is_deterministic() -> None:
    first = authority.graph_fingerprint()
    second = authority.graph_fingerprint()
    assert first == second
    assert len(first) == 64


def test_shared_navigation_exposes_authority_grid() -> None:
    # The CI adapter (authority_network_ci.graph_edges) records a home ->
    # authority-network.html edge on the strength of the shared navigation
    # linking the Authority Network on every page. Assert that durable edge
    # (the link target) rather than a specific label/emoji, so a legitimate
    # nav redesign cannot silently make that recorded edge dishonest while a
    # cosmetic rename cannot spuriously fail the gate.
    nav = Path("nav.js").read_text(encoding="utf-8")
    assert '"authority-network.html"' in nav
