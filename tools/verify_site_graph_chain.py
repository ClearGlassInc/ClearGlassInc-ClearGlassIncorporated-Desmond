#!/usr/bin/env python3
"""Dedicated verifier for the ClearGlass Intelligence Graph hash chain."""
import sys
from pathlib import Path

# Run as `python3 tools/verify_site_graph_chain.py` (intelligence-graph.yml),
# sys.path[0] is tools/, not the repository root, so `tools` is not importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.site_intelligence_graph import verify_chain  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(verify_chain())
