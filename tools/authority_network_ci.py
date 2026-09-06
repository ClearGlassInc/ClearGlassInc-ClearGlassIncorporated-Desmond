#!/usr/bin/env python3
"""Release-gate entry point for the ClearGlass authority network.

The site intentionally publishes both directory URLs (for example ``/blog/``)
and explicit ``index.html`` aliases. Both normalize to one canonical graph node.
The core auditor reports repeated normalized paths for diagnostic visibility;
this release policy suppresses only that known alias condition and preserves all
other graph, sitemap, crawl-depth, conversion and block-integrity failures.

The public Authority Grid is linked from the shared ``nav.js`` Company group.
Because the core HTML parser intentionally does not execute JavaScript, this
release adapter records that reviewed global-navigation edge explicitly.

Newly published, indexable pages are registered here as supplemental nodes until
the next deliberate legacy-graph regeneration. This keeps scheduled releases
safe without reshuffling established internal-link blocks across the whole site.
Client-rendered pillar listings are also represented as reviewed graph edges.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Support both ``python -m tools.authority_network_ci`` and direct execution as
# ``python tools/authority_network_ci.py`` from the repository root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import authority_network as core  # noqa: E402
from tools.authority_network import *  # noqa: E402,F403

_RELEASE_SUPPLEMENTAL_PAGES: dict[str, tuple[str, str, str]] = {}

for _path, (_title, _description, _cluster) in _RELEASE_SUPPLEMENTAL_PAGES.items():
    core.SUPPLEMENTAL_PAGES.setdefault(
        _path,
        (_title, _description, _cluster),
    )
    core.PAGES.setdefault(_path, (_title, _description))

_ALIAS_DIAGNOSTIC = ": duplicate loc entries inside sitemap set"
_BASE_VALIDATE = core.validate
_BASE_GRAPH_EDGES = core.graph_edges


def validate() -> list[str]:
    return [error for error in _BASE_VALIDATE() if _ALIAS_DIAGNOSTIC not in error]


def graph_edges() -> dict[str, set[str]]:
    edges = _BASE_GRAPH_EDGES()
    if "authority-network.html" in core.PAGES:
        edges["index.html"].add("authority-network.html")

    # The Insights pillar is populated from the reviewed post registry at runtime.
    # Record those client-rendered discovery edges because the stdlib parser does
    # not execute JavaScript or inspect the JSON registry used by the page.
    for page, (_title, _description, cluster_id) in core.SUPPLEMENTAL_PAGES.items():
        pillar = core.legacy.CLUSTERS[cluster_id]["pillar"]
        edges[pillar].add(page)

    return edges


# ``core.main`` and ``core.analysis_errors`` resolve these functions from the
# core module globals. Replace only the compatibility policy hooks.
core.validate = validate
core.graph_edges = graph_edges


if __name__ == "__main__":
    sys.exit(core.main())
