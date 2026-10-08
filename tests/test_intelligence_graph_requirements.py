"""The Intelligence Graph collector must install from its own requirements file.

`intelligence-graph.yml` installs only `tools/intelligence_graph_requirements.txt`
before `python3 tools/site_intelligence_graph.py crawl`. That file declared
NetworkX but not the NumPy and SciPy that `nx.pagerank` needs in NetworkX 3.x,
so on a clean install the crawl fetched every source and then died computing
analytics. No snapshot was ever published, and the graph page could only ever
show its empty state.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "tools" / "site_intelligence_graph.py"
REQUIREMENTS = ROOT / "tools" / "intelligence_graph_requirements.txt"
# Import name -> distribution name, where they differ.
DISTRIBUTION = {"bs4": "beautifulsoup4"}


def declared() -> set[str]:
    names = set()
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.add(re.split(r"[<>=!~;\[ ]", line, maxsplit=1)[0].lower())
    return names


def imported_third_party() -> set[str]:
    tree = ast.parse(COLLECTOR.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.add(node.module.split(".")[0])
    return {
        DISTRIBUTION.get(m, m).lower()
        for m in modules
        if m not in sys.stdlib_module_names
        and m != "__future__"
        # First-party: a package or module of this repository.
        and not (ROOT / m).is_dir()
        and not (ROOT / f"{m}.py").is_file()
        and not (COLLECTOR.parent / f"{m}.py").is_file()
    }


def test_every_third_party_import_is_declared() -> None:
    missing = imported_third_party() - declared()
    assert not missing, f"collector imports undeclared packages: {sorted(missing)}"


def test_pagerank_backends_are_declared() -> None:
    if "nx.pagerank(" in COLLECTOR.read_text(encoding="utf-8"):
        assert {"numpy", "scipy"} <= declared(), "nx.pagerank needs numpy and scipy in NetworkX 3.x"
